from contextlib import contextmanager
from io import StringIO
from unittest import TestCase
from unittest.mock import Mock, patch
import sys

@contextmanager
def captured_output():
    """ Captures print() output for testing """

    new_out, new_err = StringIO(), StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = new_out, new_err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = old_out, old_err


class PatchTestCase(TestCase):
    """ Testcase ready for patching """

    def setUp(self):
        self.patchers = []
        super().setUp()

    def patch(self, target, new=None, create=None) -> Mock:
        """ Patches a target with a new object """

        if new is None:
            new = Mock()
        patcher = patch(target, new=new, create=create)
        self.patchers.append(patcher)
        return patcher.start()

    def tearDown(self):
        super().tearDown()
        for patcher in self.patchers:
            patcher.stop()
