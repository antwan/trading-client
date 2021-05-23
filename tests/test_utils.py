from datetime import timedelta, datetime, timezone
from unittest import TestCase
from unittest.mock import Mock

from src.utils import parse_instrument, countdown
from .utils import captured_output, PatchTestCase

class TestParseInstrument(TestCase):

    def test_valid(self):
        valid_instrument = 'AAABBB.SPOT'
        (currency_from, currency_to), method = parse_instrument(valid_instrument)
        self.assertEqual(currency_from, 'AAA')
        self.assertEqual(currency_to, 'BBB')
        self.assertEqual(method, 'SPOT')

    def test_invalid_instrument(self):
        valid_instrument = 'AAASPOT'
        with self.assertRaises(ValueError):
            parse_instrument(valid_instrument)


class TestCountDown(PatchTestCase):

    now = datetime(2021, 3, 1)

    def test_confirms_and_quit(self):
        self.patch('src.utils.utcnow', new=Mock(return_value=self.now))
        self.patch('builtins.input', new=Mock(side_effect=['y']))
        end = self.now + timedelta(seconds=3)
        with captured_output() as (stdout, _):
            res=countdown(end, 'w{}...', 'p?')
            self.assertEqual(stdout.getvalue().strip(), 'w{}...\np?\n\x1b[2F\x1b[2Kw3...\x1b[1B')
            self.assertEqual(res, 'y')

    def test_timeouts_quit(self):
        end = datetime.utcnow().replace(tzinfo=timezone.utc) + timedelta(seconds=2)
        with captured_output() as (stdout, _):
            countdown(end, 'w{}...', 'p?', 't')
            self.assertEqual(stdout.getvalue().strip(), 'w{}...\np?\n\x1b[2F\x1b[2Kw1...\x1b[1B\nt')
