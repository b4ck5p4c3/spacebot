import datetime
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault('TREASURER_USER_ID', '100')
os.environ.setdefault('SWYNCA_API_TOKEN', 'test_token')
os.environ.setdefault('SWYNCA_API_HOST', 'http://localhost')
os.environ.setdefault('MQTT_URL', '')
os.environ.setdefault('GOOGLE_SHEET_URL', '')
os.environ.setdefault('TG_BOT_TOKEN', '0:test')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bot
from bot import (
    cached_answers,
    cached_tran_log,
    del_cached_tran_log_by_user_id,
    fill_inline_keyboard_by_active_members,
    gen_random_string,
    get_answer_object,
    get_cached_data,
    get_user_id,
    is_tran_key,
    is_valid_guid,
    mock_user_id,
    parse_datetime_with_utc3,
    set_cached_data,
)

VALID_UUID = '550e8400-e29b-41d4-a716-446655440000'


class TestIsValidGuid(unittest.TestCase):

    def test_valid_uuid(self):
        self.assertTrue(is_valid_guid(VALID_UUID))

    def test_invalid_string(self):
        self.assertFalse(is_valid_guid('not-a-guid'))

    def test_empty_string(self):
        self.assertFalse(is_valid_guid(''))

    def test_non_hex_char(self):
        self.assertFalse(is_valid_guid('550e8400-e29b-41d4-a716-44665544000Z'))


class TestIsTranKey(unittest.TestCase):

    def test_valid_key(self):
        self.assertTrue(is_tran_key(f'123-{VALID_UUID}'))

    def test_no_separator(self):
        self.assertFalse(is_tran_key('123' + VALID_UUID))

    def test_non_numeric_prefix(self):
        self.assertFalse(is_tran_key(f'abc-{VALID_UUID}'))

    def test_invalid_guid_suffix(self):
        self.assertFalse(is_tran_key('123-not-a-guid'))

    def test_single_part(self):
        self.assertFalse(is_tran_key('123'))


class TestCacheOperations(unittest.TestCase):

    def setUp(self):
        cached_answers.clear()

    def test_set_and_get(self):
        set_cached_data('balance', '42', '500р')
        self.assertEqual(get_cached_data('balance', '42'), '500р')

    def test_get_missing_key_returns_empty_string(self):
        self.assertEqual(get_cached_data('balance', 'nobody'), '')

    def test_set_overwrites_existing(self):
        set_cached_data('balance', '42', 'first')
        set_cached_data('balance', '42', 'second')
        self.assertEqual(get_cached_data('balance', '42'), 'second')

    def test_different_commands_do_not_collide(self):
        set_cached_data('balance', '42', 'bal')
        set_cached_data('tranlog', '42', 'tran')
        self.assertEqual(get_cached_data('balance', '42'), 'bal')
        self.assertEqual(get_cached_data('tranlog', '42'), 'tran')


class TestMockUserId(unittest.TestCase):

    def test_returns_real_id_when_env_not_set(self):
        env = os.environ.copy()
        env.pop('DEBUG_TG_USERNAME', None)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(mock_user_id(123), 123)

    def test_returns_env_id_when_set(self):
        with patch.dict(os.environ, {'DEBUG_TG_USERNAME': '999'}):
            self.assertEqual(mock_user_id(123), 999)

    def test_returns_real_id_when_env_is_empty_string(self):
        with patch.dict(os.environ, {'DEBUG_TG_USERNAME': ''}):
            self.assertEqual(mock_user_id(123), 123)


class TestGenRandomString(unittest.TestCase):

    def test_default_length_is_ten(self):
        self.assertEqual(len(gen_random_string()), 10)

    def test_custom_length(self):
        self.assertEqual(len(gen_random_string(5)), 5)

    def test_only_uppercase_alphanumeric(self):
        result = gen_random_string(50)
        self.assertTrue(result.isalnum())
        self.assertEqual(result, result.upper())


class TestParseDatetimeWithUtc3(unittest.TestCase):

    def test_parses_correctly(self):
        result = parse_datetime_with_utc3('15.06.2024 14:30')
        self.assertEqual(result.year, 2024)
        self.assertEqual(result.month, 6)
        self.assertEqual(result.day, 15)
        self.assertEqual(result.hour, 14)
        self.assertEqual(result.minute, 30)

    def test_timezone_is_utc_plus_3(self):
        result = parse_datetime_with_utc3('01.01.2024 00:00')
        expected_tz = datetime.timezone(datetime.timedelta(hours=3))
        self.assertEqual(result.tzinfo, expected_tz)

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            parse_datetime_with_utc3('2024-06-15')


class TestGetAnswerObject(unittest.TestCase):

    def test_returns_query_message_when_query_given(self):
        query = MagicMock()
        message = MagicMock()
        self.assertIs(get_answer_object(query=query, message=message), query.message)

    def test_returns_message_when_query_is_none(self):
        message = MagicMock()
        self.assertIs(get_answer_object(query=None, message=message), message)


class TestGetUserId(unittest.TestCase):

    def test_returns_query_user_id_when_query_given(self):
        query = MagicMock()
        query.from_user.id = 42
        self.assertEqual(get_user_id(query=query, message=None), 42)

    def test_returns_message_user_id_when_query_is_none(self):
        message = MagicMock()
        message.from_user.id = 99
        self.assertEqual(get_user_id(query=None, message=message), 99)


class TestDelCachedTranLog(unittest.TestCase):

    def setUp(self):
        cached_tran_log.clear()

    def test_removes_exact_string_key(self):
        cached_tran_log['123'] = {'data': 1}
        del_cached_tran_log_by_user_id(123)
        self.assertNotIn('123', cached_tran_log)

    def test_removes_keys_with_user_id_prefix(self):
        cached_tran_log[f'123-{VALID_UUID}'] = {}
        cached_tran_log[f'123-aaaa-bbbb'] = {}
        del_cached_tran_log_by_user_id(123)
        self.assertNotIn(f'123-{VALID_UUID}', cached_tran_log)
        self.assertNotIn('123-aaaa-bbbb', cached_tran_log)

    def test_does_not_remove_other_users_keys(self):
        cached_tran_log['456'] = {'other': 'data'}
        del_cached_tran_log_by_user_id(123)
        self.assertIn('456', cached_tran_log)

    def test_no_error_when_key_absent(self):
        del_cached_tran_log_by_user_id(999)


class TestFillInlineKeyboard(unittest.TestCase):

    def setUp(self):
        cached_tran_log.clear()

    def _make_member(self, name='Alice', tg_name='alice', member_id='m1'):
        m = MagicMock()
        m.id = member_id
        m.name = name
        m.telegram_metadata.telegram_name = tg_name
        return m

    def test_button_count_matches_members_plus_controls(self):
        members = [self._make_member('Alice', 'alice', 'm1'), self._make_member('Bob', 'bob', 'm2')]
        tran = {'type': 'deposit', 'amount': '100'}
        builder = fill_inline_keyboard_by_active_members(members, tran, '42')
        buttons = [b for row in builder.as_markup().inline_keyboard for b in row]
        # 2 members + «Пропустить» + «Прекратить»
        self.assertEqual(len(buttons), 4)

    def test_caches_tran_copy_per_member(self):
        members = [self._make_member('Alice', 'alice', 'm1')]
        tran = {'type': 'deposit', 'amount': '200'}
        fill_inline_keyboard_by_active_members(members, tran, '42')
        cached = [v for k, v in cached_tran_log.items() if k.startswith('42-')]
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0]['amount'], '200')

    def test_sets_subject_id_in_cached_tran(self):
        member = self._make_member('Alice', 'alice', 'abc-member-id')
        tran = {'type': 'deposit', 'amount': '300'}
        fill_inline_keyboard_by_active_members([member], tran, '42')
        cached = [v for k, v in cached_tran_log.items() if k.startswith('42-')]
        self.assertEqual(cached[0]['subjectId'], 'abc-member-id')

    def test_original_tran_not_mutated(self):
        member = self._make_member()
        tran = {'type': 'deposit', 'amount': '100'}
        fill_inline_keyboard_by_active_members([member], tran, '42')
        self.assertNotIn('subjectId', tran)


if __name__ == '__main__':
    unittest.main()
