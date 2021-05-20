from datetime import datetime, timedelta, timezone
import os
from time import sleep
import threading


def utcnow():
    """ Returns time zone aware datetime as of now """

    return datetime.utcnow().replace(tzinfo=timezone.utc)

def parse_instrument(instrument):
    """ Parses an instrument string """

    pair, method = instrument.split('.')
    return (pair[0:3], pair[3:6]), method

def countdown(end, formatter='{}...', prompt='?', end_prompt='terminated'):
    """ Displays a prompt with a countdown """

    # pylint: disable=invalid-name
    CURSOR_UP_TWO = '\x1b[2F'
    CURSOR_DOWN = '\x1b[1B'
    ERASE_LINE = '\x1b[2K'

    def timer(end):
        stopped = False
        while utcnow() < end - timedelta(seconds=1) and not stopped:
            expire = int((end - utcnow()).total_seconds())
            print(CURSOR_UP_TWO + ERASE_LINE  + formatter.format(expire) + CURSOR_DOWN)
            sleep(1)
            t = threading.currentThread()
            stopped = getattr(t, 'stopped', False)
        if not stopped:
            print(end_prompt)
            # pylint: disable=protected-access
            os._exit(1)

    print(formatter)
    print(prompt)
    t = threading.Thread(target=timer,args=(end,))
    t.start()
    val = input()
    t.stopped = True
    t.join()
    return val
