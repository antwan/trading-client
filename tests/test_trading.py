from unittest.mock import Mock
from decimal import Decimal
from datetime import datetime, timedelta
from requests import HTTPError

from src.trading import ApiError, B2C2Api, SIDE_BUY
from .utils import PatchTestCase


class B2C2ApiTestCase(PatchTestCase):
    """ Testcase suited for B2C2Api class """

    def setUp(self):
        super().setUp()

        self.api = B2C2Api()
        self.api.headers = {'Authorization': 'Token 1234'}
        self.api.API_ROOT = 'http://server.com'
        self.mocked_logger = self.patch('src.trading.logger')


class TestGenerateClientId(B2C2ApiTestCase):
    # pylint: disable=protected-access

    def test_valid_uid(self):
        uid = self.api._generate_client_id()
        self.assertRegex(uid, r'[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}')


class TestCheckResponse(B2C2ApiTestCase):
    # pylint: disable=protected-access

    def setUp(self):
        self.response = Mock()
        super().setUp()

    def test_valid_response(self):
        data = {'key': 'value'}
        self.response.status_code = 200
        self.response.json.return_value = data

        ret = self.api._check_response(self.response)
        self.assertEqual(ret, data)

    def test_invalid_response(self):
        self.response.status_code = 200
        self.response.json.return_value = []

        with self.assertRaisesRegex(ApiError, r'No data returned'):
            self.api._check_response(self.response)

    def test_server_error(self):
        self.response.status_code = 500
        self.response.raise_for_status.side_effect = ApiError('some error')

        with self.assertRaisesRegex(ApiError, r'some error'):
            self.api._check_response(self.response)

    def test_client_error(self):
        data = {'errors': [{'field': 'non_field_errors', 'message': 'Blah'}]}
        self.response.status_code = 400
        self.response.json.return_value = data

        with self.assertRaisesRegex(ApiError, r'Blah'):
            self.api._check_response(self.response)


class TestGetInstruments(B2C2ApiTestCase):
    def setUp(self):
        super().setUp()
        self.mocked_request = self.patch('src.trading.requests.get')
        # pylint: disable=protected-access
        self.api._check_response = lambda r: r

    def test_valid_instruments(self):
        self.mocked_request.return_value = [{'name': 'XXXYYY.SPOT'}, {'name': 'AAABBB.SPOT'}]
        resp = self.api.get_instruments()
        self.assertEqual(resp, ['AAABBB.SPOT', 'XXXYYY.SPOT'])
        self.assertEqual(self.mocked_logger.debug.call_count, 1)

    def test_failing_call(self):
        self.mocked_request.side_effect = HTTPError('some error')
        with self.assertRaisesRegex(ApiError, 'API HTTP Error: some error'):
            self.api.get_instruments()

    def test_invalid_data(self):
        self.mocked_request.return_value = [{'blah': 'XXXYYY.SPOT'}]
        with self.assertRaisesRegex(ApiError, 'Invalid data'):
            self.api.get_instruments()


class TestGetBalances(B2C2ApiTestCase):
    def setUp(self):
        super().setUp()
        self.mocked_request = self.patch('src.trading.requests.get')
        # pylint: disable=protected-access
        self.api._check_response = lambda r: r

    def test_valid_balances(self):
        self.mocked_request.return_value = {'XXX': '1.234', 'YYY': '5.678'}
        resp = self.api.get_balances()
        self.assertEqual(resp, {'XXX': Decimal('1.234'), 'YYY': Decimal('5.678')})
        self.assertEqual(self.mocked_logger.debug.call_count, 1)
        self.assertEqual(self.mocked_logger.info.call_count, 1)

    def test_failing_call(self):
        self.mocked_request.side_effect = HTTPError('some error')
        with self.assertRaisesRegex(ApiError, 'API HTTP Error: some error'):
            self.api.get_balances()

    def test_invalid_data(self):
        self.mocked_request.return_value = {'XXX': 'blah'}
        with self.assertRaisesRegex(ApiError, 'Invalid data'):
            self.api.get_balances()

class TestRequestQuote(B2C2ApiTestCase):
    def setUp(self):
        super().setUp()
        self.mocked_request = self.patch('src.trading.requests.post')
        self.now = datetime.utcnow().replace(microsecond=0)
        self.patch('src.trading.utcnow', new=Mock(return_value=self.now))
        # pylint: disable=protected-access
        self.api._check_response = lambda r: r
        self.client_id = 'abcd'
        self.api._generate_client_id = Mock(return_value=self.client_id)

        self.instrument = 'AAABBB.SPOT'
        self.side = SIDE_BUY
        self.quantity = Decimal('1.5')
        self.latency = timedelta(milliseconds=50)
        self.rfq_validity = timedelta(seconds=20)
        self.price = '1.234'

    def test_valid_rfq(self):
        self.mocked_request.return_value = {
            'created': (self.now + self.latency).isoformat(),
            'price': self.price,
            'valid_until': (self.now + self.rfq_validity).isoformat(),
            'client_rfq_id': self.client_id
        }

        resp = self.api.request_quote(self.instrument, self.side, self.quantity)
        expected_price = Decimal(self.price)
        expected_expiration = self.now + self.rfq_validity - self.latency

        self.mocked_request.assert_called_once_with(
            f'{self.api.API_ROOT}/request_for_quote/',
            headers=self.api.headers,
            json={
                'client_rfq_id': self.client_id,
                'instrument': self.instrument,
                'side': self.side,
                'quantity': str(self.quantity),
            }
        )
        self.assertEqual(resp, (expected_price, expected_expiration))
        self.assertEqual(self.api.last_quote_price, expected_price)
        self.assertEqual(self.api.last_quote_valid_until, expected_expiration)
        self.assertEqual(self.api.last_quote_request, (self.instrument, self.side, self.quantity))
        self.assertEqual(self.mocked_logger.debug.call_count, 1)
        self.assertEqual(self.mocked_logger.info.call_count, 1)

    def test_invalid_client_id(self):
        self.mocked_request.return_value = {
            'created': (self.now + self.latency).isoformat(),
            'price': self.price,
            'valid_until': (self.now + self.rfq_validity).isoformat(),
            'client_rfq_id': 'wrong'
        }
        with self.assertRaisesRegex(ApiError, 'Client request ID mismatch'):
            self.api.request_quote(self.instrument, self.side, self.quantity)

    def test_failing_call(self):
        self.mocked_request.side_effect = HTTPError('some error')
        with self.assertRaisesRegex(ApiError, 'API HTTP Error: some error'):
            self.api.request_quote(self.instrument, self.side, self.quantity)

    def test_invalid_data(self):
        self.mocked_request.return_value = {
            'created': (self.now + self.latency).isoformat(),
            'valid_until': (self.now + self.rfq_validity).isoformat(),
            'client_rfq_id': self.client_id
        }
        with self.assertRaisesRegex(ApiError, 'Invalid data'):
            self.api.request_quote(self.instrument, self.side, self.quantity)

        self.mocked_request.return_value = {
            'created': 'something',
            'price': self.price,
            'valid_until': (self.now + self.rfq_validity).isoformat(),
            'client_rfq_id': self.client_id
        }
        with self.assertRaisesRegex(ApiError, 'Invalid data'):
            self.api.request_quote(self.instrument, self.side, self.quantity)


class TestPlaceOrder(B2C2ApiTestCase):
    def setUp(self):
        super().setUp()
        self.mocked_request = self.patch('src.trading.requests.post')
        self.now = datetime.utcnow().replace(microsecond=0)
        self.patch('src.trading.utcnow', new=Mock(return_value=self.now))
        # pylint: disable=protected-access
        self.api._check_response = lambda r: r
        self.client_id = 'abcd'
        self.api._generate_client_id = Mock(return_value=self.client_id)

        self.instrument = 'AAABBB.SPOT'
        self.side = SIDE_BUY
        self.quantity = Decimal('1.5')
        self.rfq_validity = timedelta(seconds=20)
        self.price = '1.234'

        self.api.last_quote_price = Decimal(self.price)
        self.api.last_quote_valid_until = self.now + self.rfq_validity
        self.api.last_quote_request = (self.instrument, self.side, self.quantity)

    def test_valid_order(self):
        self.mocked_request.return_value = {
            'quantity': '1.234',
            'trades': [{
                'quantity': '1.234'
            }]
        }

        resp = self.api.place_order(self.instrument, self.side, self.quantity)
        valid_until = (self.now + timedelta(**self.api.DEFAULT_ORDERS_VALIDITY)).strftime("%Y-%m-%dT%H:%M:%S")

        self.mocked_request.assert_called_once_with(
            f'{self.api.API_ROOT}/order/',
            headers=self.api.headers,
            json={
                'instrument': self.instrument,
                'side': self.side,
                'quantity': str(self.quantity),
                'client_order_id': self.client_id,
                'price': str(self.api.last_quote_price),
                'order_type': self.api.DEFAULT_ORDERS_TYPE,
                'valid_until': valid_until,
                'executing_unit': self.api.DEFAULT_EXECUTING_UNIT,
            }
        )
        self.assertTrue(resp)
        self.assertEqual(self.mocked_logger.debug.call_count, 1)
        self.assertEqual(self.mocked_logger.info.call_count, 1)


    def test_invalid_api_state(self):
        self.api.last_quote_request = None
        self.mocked_request.return_value = {
            'quantity': '1.234',
            'trades': [{
                'quantity': '1.234'
            }]
        }
        with self.assertRaisesRegex(AssertionError, 'Should get a quote first'):
            self.api.place_order(self.instrument, self.side, self.quantity)

    def test_invalid_response_trades(self):
        self.mocked_request.return_value = {
            'quantity': '1.234',
            'trades': [{
                'quantity': '1.05'
            }, {
                'quantity': '0.05'
            }]
        }

        with self.assertRaisesRegex(ApiError, 'Quantity and trades mismatch'):
            self.api.place_order(self.instrument, self.side, self.quantity)

    def test_failing_call(self):
        self.mocked_request.side_effect = HTTPError('some error')
        with self.assertRaisesRegex(ApiError, 'API HTTP Error: some error'):
            self.api.request_quote(self.instrument, self.side, self.quantity)

    def test_invalid_data(self):
        self.mocked_request.return_value = {
            'quantity': '1.234',
            'trades': [{
                'something': 'blah'
            }]
        }
        with self.assertRaisesRegex(ApiError, 'Invalid data'):
            self.api.request_quote(self.instrument, self.side, self.quantity)

# Test print_instruments()
# Test trade()
# ...
