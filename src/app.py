from decimal import Decimal
import argparse
import logging
import sys
from .trading import B2C2Api, ApiError, ApplicationError, SIDE_BUY, SIDE_SELL
from .utils import countdown, parse_instrument

DEBUG = False


logger = logging.getLogger(__name__)


def print_instruments():
    """ Prints valid instruments """

    api = B2C2Api()
    try:
        instruments = api.get_instruments()
    except ApiError as err:
        raise ApplicationError(f'Could not get valid instruments: {err}') from err

    print('Valid instruments are:')
    for i in instruments:
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



if __name__ == '__main__':

    # Parses CLI
    parser = argparse.ArgumentParser()
    parser.add_argument('instrument', nargs='?', help='Name of the instrument to use')
    parser.add_argument('quantity', nargs='?', type=Decimal, help='Quantity of tokens to trade')
    parser.add_argument(
        '-s', '--side',
        help='Order side',
        choices=[SIDE_BUY, SIDE_SELL], default=SIDE_BUY
    )
    parser.add_argument(
        '-d', '--debug',
        help='Display debugging informations',
        dest='debug',
        action="store_true"
    )
    parser.add_argument(
        '-i', '--show-instruments',
        help='Only show valid trading instruments and exits',
        dest='show_instruments',
        action="store_true"
    )
    parser.add_argument(
        '-f', '--logfile',
        help='Logging file'
    )
    args = parser.parse_args()
    if (not args.instrument or args.quantity is None) and not args.show_instruments:
        parser.error('`instrument` and `quantity` are required unless showing valid instruments')

    logging.basicConfig(
        level=logging.DEBUG if args.debug or DEBUG else logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        **({'stream':sys.stdout} if args.debug or DEBUG else {'filename':args.logfile or 'logs/orders.log'}),
    )

    try:
        if args.show_instruments:
            print_instruments()
        else:
            trade(args.instrument, args.side, args.quantity)
    except ApplicationError as err:
        print(err, file=sys.stdout)
        logger.error(err)
        exit(1)
