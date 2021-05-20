from decimal import Decimal
import argparse
import logging
import sys
from .trading import trade, print_instruments, SIDE_BUY, SIDE_SELL, ApplicationError

DEBUG = False


logger = logging.getLogger(__name__)

if __name__ == '__main__':

    # Parses CLI
    parser = argparse.ArgumentParser()
    parser.add_argument('instrument', help='Name of the instrument to use')
    parser.add_argument('quantity', type=Decimal, help='Quantity of tokens to trade')
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

    logging.basicConfig(
        level=logging.DEBUG if args.debug or DEBUG else logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        **({'stream':sys.stdout} if args.debug or DEBUG else {'filename':args.logfile or 'orders.log'}),
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
