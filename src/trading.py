from datetime import timedelta
from decimal import Decimal, InvalidOperation
import logging
import uuid
import requests

from dateutil.parser import isoparse
from .utils import utcnow, countdown, parse_instrument

SIDE_BUY = 'buy'
SIDE_SELL = 'sell'

ORDER_TYPE_FOK = 'FOK'
ORDER_TYPE_MKT = 'MKT'

logger = logging.getLogger(__name__)


class ApplicationError(Exception):
    """ An error related to the application """

class ApiError(Exception):
    """ An error related to API communications """


class B2C2Api():
    """ B2C2 API communication utility class """

    AUTH_TOKEN = 'e13e627c49705f83cbe7b60389ac411b6f86fee7'
    API_ROOT = 'https://api.uat.b2c2.net'
    DEFAULT_ORDERS_TYPE = ORDER_TYPE_FOK
    DEFAULT_ORDERS_VALIDITY = {'seconds': 10}
    DEFAULT_EXECUTING_UNIT = 'risk-adding-strategy'

    def __init__(self):
        self.headers = {'Authorization': f'Token {self.AUTH_TOKEN}'}
        self.last_quote_valid_until = None
        self.last_quote_price = None
        self.last_quote_request = None

    def _generate_client_id(self):
        """ Returns an API client ID """

        return str(uuid.uuid4())

    def _check_response(self, response):
        """ Checks whether an API response is valid """

        if response.status_code not in [200, 400]:
            response.raise_for_status()

        data = response.json()
        if response.status_code == 400:
            err_string = ', '. join([
                f'{e["field"]}: {e["message"]}' if e["field"] != 'non_field_errors' else e["message"]
                for e in data['errors']
            ])
            raise ApiError(err_string)
        if not data:
            raise ApiError('No data returned')
        return data

    def get_instruments(self):
        """ Retrieve available instruments """

        logger.debug('Getting instruments')
        try:
            resp = requests.get(f'{self.API_ROOT}/instruments/', headers=self.headers)
            data = self._check_response(resp)
            return sorted([i['name'] for i in data])

        except requests.HTTPError as err:
            raise ApiError(f'API HTTP Error: {err}') from None

        except (KeyError, IndexError):
            raise ApiError('Invalid data') from None

    def get_balances(self):
        """ Retrieve balances for the connected user """

        logger.debug('Getting balances')
        try:
            resp = requests.get(f'{self.API_ROOT}/balance/', headers=self.headers)
            data = self._check_response(resp)

            logger.info('Requested balances: %s', data)

            return {currency: Decimal(value) for currency, value in data.items()}

        except requests.HTTPError as err:
            raise ApiError(f'API HTTP Error: {err}') from None

        except (KeyError, IndexError, ValueError, InvalidOperation) as err:
            raise ApiError(f'Invalid data: {err}') from None

    def request_quote(self, instrument, side, quantity):
        """ Request a quote for the given instrument, side and quantity """

        logger.debug('Requesting quote to %s %s using %s', side, quantity, instrument)
        try:
            client_id = self._generate_client_id()
            payload = {
                'client_rfq_id': client_id,
                'instrument': instrument,
                'side': side,
                'quantity': str(quantity),
            }
            now = utcnow()
            resp = requests.post(f'{self.API_ROOT}/request_for_quote/', headers=self.headers, json=payload)
            data = self._check_response(resp)

            if any([param not in data for param in ['created', 'price', 'valid_until', 'client_rfq_id']]):
                raise ApiError('Invalid data')

            if data['client_rfq_id'] != client_id:
                raise ApiError('Client request ID mismatch')

            # Getting an estimation of the latency with local clock
            delay = isoparse(data['created']) - now

            self.last_quote_request = (instrument, side, quantity)
            self.last_quote_valid_until = isoparse(data['valid_until']) - delay
            self.last_quote_price = Decimal(data['price'])

            logger.info('Requested quote: %s', data)
            return self.last_quote_price, self.last_quote_valid_until

        except requests.HTTPError as err:
            raise ApiError(f'API HTTP Error: {err}') from None

        except (KeyError, IndexError, ValueError, InvalidOperation) as err:
            raise ApiError(f'Invalid data: {err}') from None

    def place_order(self, instrument, side, quantity):
        """ Place a trading order using the last quote """

        logger.debug(
            'Placing order to %s %s of %s for %s',
            side, quantity, instrument, self.last_quote_price
        )

        assert self.last_quote_request == (instrument, side, quantity), 'Should get a quote first'
        assert self.last_quote_price is not None, 'Should get a quote first'
        assert utcnow() < self.last_quote_valid_until, 'Last quote should not have expired'

        valid_until = (utcnow() + timedelta(**self.DEFAULT_ORDERS_VALIDITY)).strftime("%Y-%m-%dT%H:%M:%S")

        try:
            client_id = self._generate_client_id()
            payload = {
                'instrument': instrument,
                'side': side,
                'quantity': str(quantity),
                'client_order_id': client_id,
                'price': str(self.last_quote_price),
                'order_type': self.DEFAULT_ORDERS_TYPE,
                'valid_until': valid_until,
                'executing_unit': self.DEFAULT_EXECUTING_UNIT,
            }
            resp = requests.post(f'{self.API_ROOT}/order/', headers=self.headers, json=payload)
            data = self._check_response(resp)

            logger.info('Placed order: %s', data)
            if not data['trades']:
                return None
            if sum([Decimal(t['quantity']) for t in data['trades']]) != Decimal(data['quantity']):
                raise ApiError('Quantity and trades mismatch')
            return True

        except requests.HTTPError as err:
            raise ApiError(f'API HTTP Error: {err}') from None

        except (KeyError, IndexError, ValueError, InvalidOperation) as err:
            raise ApiError(f'Invalid data: {err}') from None

def print_instruments():
    """ Prints valid instruments """

    api = B2C2Api()
    print('Valid instruments are:')
    for i in api.get_instruments():
        print(i)

def trade(instrument, side, quantity):
    """ Perform a trade operation """

    logger.debug('Trying to %s %s of %s', side, quantity, instrument)
    api = B2C2Api()

    # Checking chosen instrument validity
    try:
        instruments = api.get_instruments()
    except ApiError as err:
        raise ApplicationError(f'Could not get valid instruments: {err}') from err

    if instrument not in instruments:
        raise ApplicationError('Invalid instrument "{}". Valid instruments are: {}'.format(
            instrument,
            ', '.join(instruments)
        ))
    logger.debug('%s is a valid instrument', instrument)

    (source_currency, target_currency), _ = parse_instrument(instrument)

    # Getting original balances
    try:
        balances = api.get_balances()
    except ApiError as err:
        raise ApplicationError(f'Could not get balances: {err}') from err

    original_source_balance = balances.get(source_currency, '0')
    original_target_balance = balances.get(target_currency, '0')
    print(f'You have {original_source_balance} {source_currency} and {original_target_balance} {target_currency}')

    # Acquiring quote for order
    try:
        quote_price, quote_expiration = api.request_quote(instrument, side, quantity)
        estimated_final_amount = (quantity * quote_price).quantize(Decimal('0.0001'))
    except ApiError as err:
        raise ApplicationError(f'Could not request quote: {err}') from err

    # Printing info and confirmation
    print(f'You are about to {side} {quantity} {source_currency} at {quote_price} {source_currency}/{target_currency}')
    print('{} an estimated {} {}'.format(
        'This will cost you' if side == SIDE_BUY else 'You will get',
        estimated_final_amount,
        target_currency
    ))
    print('After the trade you will have and estimated {} {} and {} {} in your wallet'.format(
        original_source_balance + (1 if side == SIDE_BUY else -1) * quantity, source_currency,
        original_target_balance + (1 if side == SIDE_SELL else -1) * estimated_final_amount, target_currency,
    ))

    confirm = countdown(
        quote_expiration,
        'You have {} seconds to accept until the quote is expired.',
        'Proceed? y/[N]',
        'The quote has expired'
    )
    if not confirm or confirm.lower() not in ['y', 'yes']:
        print('Trade aborted')
        return

    # Executing order
    try:
        order = api.place_order(instrument, side, quantity)
        if not order:
            raise ApplicationError('No order was executed')
        print('Order successfully executed')
    except ApiError as err:
        raise ApplicationError(f'Could not place order: {err}') from err

    # Getting new balances
    try:
        balances = api.get_balances()
    except ApiError as err:
        raise ApplicationError(f'Could not get balances: {err}') from err

    final_source_balance = balances.get(source_currency, '0')
    final_target_balance = balances.get(target_currency, '0')
    print(f'You now have {final_source_balance} {source_currency} and {final_target_balance} {target_currency}')
