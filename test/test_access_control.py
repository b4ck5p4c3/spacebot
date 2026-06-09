import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.access_control import AccessControlInterface, DebugAlwaysAllowAccessControl


class TestDebugAlwaysAllowAccessControl(unittest.TestCase):

    def setUp(self):
        self.ac = DebugAlwaysAllowAccessControl()

    def test_allows_zero(self):
        self.assertTrue(self.ac.allow_access(0))

    def test_allows_arbitrary_id(self):
        self.assertTrue(self.ac.allow_access(123456789))

    def test_allows_negative_id(self):
        self.assertTrue(self.ac.allow_access(-1))

    def test_is_access_control_interface(self):
        self.assertIsInstance(self.ac, AccessControlInterface)


class TestAccessControlMeta(unittest.TestCase):

    def test_class_without_allow_access_is_not_interface(self):
        class NoMethod:
            pass
        self.assertNotIsInstance(NoMethod(), AccessControlInterface)

    def test_class_with_non_callable_allow_access_is_not_interface(self):
        class NonCallable:
            allow_access = 'not_a_method'
        self.assertNotIsInstance(NonCallable(), AccessControlInterface)

    def test_class_with_allow_access_method_is_interface(self):
        class ProperImpl:
            def allow_access(self, user_id: int) -> bool:
                return False
        self.assertIsInstance(ProperImpl(), AccessControlInterface)


if __name__ == '__main__':
    unittest.main()
