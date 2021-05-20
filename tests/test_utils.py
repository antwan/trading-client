from datetime import timedelta, datetime, timezone
from unittest import TestCase, mock

from src.utils import parse_instrument, countdown
from .utils import captured_output

class ParseInstrument(TestCase):
    """ Test parse_instrument function """

    def test_valid(self):
        """ Test valid instrument """
        valid_instrument = 'AAABBB.SPOT'
        (currency_from, currency_to), method = parse_instrument(valid_instrument)
        self.assertEqual(currency_from, 'AAA')
        self.assertEqual(currency_to, 'BBB')
        self.assertEqual(method, 'SPOT')


    def test_invalid_instrument(self):
        """ Test invalid instrument """
        valid_instrument = 'AAASPOT'
        with self.assertRaises(ValueError):
            parse_instrument(valid_instrument)


class CountDown(TestCase):
    """ Test parse_instrument function """

    now = datetime(2021, 3, 1)

    @mock.patch('builtins.input', side_effect=['y'])
    @mock.patch('src.utils.datetime')
    def test_confirms_and_quit(self, mocked_datetime, _):
        """ Test when calling and confirming """

        mocked_datetime.utcnow = mock.Mock(return_value=self.now)
        end = self.now + timedelta(seconds=2)
        with captured_output() as (stdout, _):
            res=countdown(end, 'w{}...', 'p?')
            self.assertEqual(stdout.getvalue().strip(), 'w{}...\np?')
            self.assertEqual(res, 'y')

    def test_timeouts_quit(self):
        """ Test when calling and waiting """

        end = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=2)
        with captured_output() as (stdout, _):
            countdown(end, 'w{}...', 'p?', 't')
            self.assertEqual(stdout.getvalue().strip(), 'w{}...\np?\n\x1b[2F\x1b[2Kw1...\x1b[1B\nt')