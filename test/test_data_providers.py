import os
import sys
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from logic.data_providers import (
    ActiveMembersFromReSwyncaDataSource,
    BalanceFromReSwynca,
    BaseDataSource,
    OpenApiDataSource,
    TransactionsFromReSwynca,
)
from openapi_client.models.member_dto import MemberDTO
from openapi_client.models.telegram_metadata_dto import TelegramMetadataDTO


def make_context_manager_mock():
    mock = MagicMock()
    mock.__enter__ = MagicMock(return_value=mock)
    mock.__exit__ = MagicMock(return_value=False)
    return mock


def make_member_dto(tg_id='123', tg_name='user1', status='active', balance='500', member_id='m1'):
    return MemberDTO(
        id=member_id,
        name='Test Member',
        email='test@test.com',
        username='testuser',
        status=status,
        balance=balance,
        joined_at=datetime(2024, 1, 1),
        telegram_metadata=TelegramMetadataDTO(telegram_id=tg_id, telegram_name=tg_name),
    )


def make_member_dto_no_tg(member_id='m2'):
    return MemberDTO(
        id=member_id,
        name='No TG Member',
        email='notg@test.com',
        username='notg',
        status='active',
        balance='0',
        joined_at=datetime(2024, 1, 1),
        telegram_metadata=None,
    )


class TestBaseDataSource(unittest.TestCase):

    def setUp(self):
        BaseDataSource._cache = []

    def tearDown(self):
        BaseDataSource._cache = []

    def test_get_record_raises_on_empty_cache(self):
        with self.assertRaises(ValueError):
            BaseDataSource.get_record(0)

    def test_get_record_raises_when_index_exceeds_length(self):
        BaseDataSource._cache = ['a', 'b']
        with self.assertRaises(ValueError):
            BaseDataSource.get_record(5)

    def test_get_record_returns_correct_item(self):
        BaseDataSource._cache = ['first', 'second']
        self.assertEqual(BaseDataSource.get_record(0), 'first')
        self.assertEqual(BaseDataSource.get_record(1), 'second')

    def test_get_records_count_calls_get_records_when_cache_empty(self):
        with patch.object(BaseDataSource, 'get_records', return_value=['a', 'b', 'c']) as mock_get:
            count = BaseDataSource.get_records_count()
        mock_get.assert_called_once()
        self.assertEqual(count, 3)

    def test_get_records_count_uses_existing_cache_without_calling_get_records(self):
        BaseDataSource._cache = ['x', 'y']
        with patch.object(BaseDataSource, 'get_records') as mock_get:
            count = BaseDataSource.get_records_count()
        mock_get.assert_not_called()
        self.assertEqual(count, 2)


class TestBalanceFromReSwynca(unittest.TestCase):

    def _run(self, user_id, members):
        mock_api = make_context_manager_mock()
        members_api_mock = MagicMock()
        members_api_mock.members_controller_find_all.return_value = members
        with patch.object(OpenApiDataSource, 'init_api_client', return_value=mock_api):
            with patch('logic.data_providers.MembersApi', return_value=members_api_mock):
                BalanceFromReSwynca(host='http://test', access_token='tok', user_id=user_id)
                return BalanceFromReSwynca.get_records()

    def test_returns_balance_for_matching_user(self):
        member = make_member_dto(tg_id='123', balance='500')
        result = self._run('123', [member])
        self.assertEqual(result, [{'123': '500'}])

    def test_returns_empty_when_telegram_id_does_not_match(self):
        member = make_member_dto(tg_id='456', balance='200')
        result = self._run('123', [member])
        self.assertEqual(result, [])

    def test_returns_empty_when_member_list_is_empty(self):
        result = self._run('123', [])
        self.assertEqual(result, [])

    def test_ignores_members_without_telegram_metadata(self):
        member = make_member_dto_no_tg()
        result = self._run('123', [member])
        self.assertEqual(result, [])

    def test_returns_first_match_when_multiple_members(self):
        m1 = make_member_dto(tg_id='456', balance='100', member_id='m1')
        m2 = make_member_dto(tg_id='123', balance='999', member_id='m2')
        result = self._run('123', [m1, m2])
        self.assertEqual(result, [{'123': '999'}])


class TestTransactionsFromReSwynca(unittest.TestCase):

    def _make_page(self, transactions, total):
        page = MagicMock()
        page.transactions = transactions
        page.count = total
        return page

    def _run(self, user_id, members, pages):
        mock_api = make_context_manager_mock()
        members_api_mock = MagicMock()
        members_api_mock.members_controller_find_all.return_value = members
        tran_api_mock = MagicMock()
        tran_api_mock.member_transactions_controller_find_all_by_subject_member.side_effect = pages

        with patch.object(OpenApiDataSource, 'init_api_client', return_value=mock_api):
            with patch('logic.data_providers.MembersApi', return_value=members_api_mock):
                with patch('logic.data_providers.MemberTransactionsApi', return_value=tran_api_mock):
                    TransactionsFromReSwynca(host='http://test', access_token='tok', user_id=user_id)
                    return TransactionsFromReSwynca.get_records()

    def test_returns_transactions_for_matching_user(self):
        tran = MagicMock()
        member = make_member_dto(tg_id='123', member_id='m1')
        result = self._run('123', [member], [self._make_page([tran], 1)])
        self.assertEqual(result, [tran])

    def test_returns_empty_when_member_list_is_empty(self):
        result = self._run('123', [], [])
        self.assertEqual(result, [])

    def test_returns_empty_when_no_user_with_matching_telegram_id(self):
        member = make_member_dto(tg_id='456', member_id='m1')
        result = self._run('123', [member], [])
        self.assertEqual(result, [])

    def test_paginates_until_all_transactions_fetched(self):
        t1, t2 = MagicMock(), MagicMock()
        member = make_member_dto(tg_id='123', member_id='m1')
        pages = [
            self._make_page([t1], 2),
            self._make_page([t2], 2),
        ]
        result = self._run('123', [member], pages)
        self.assertEqual(result, [t1, t2])

    def test_single_page_when_count_matches(self):
        t1, t2 = MagicMock(), MagicMock()
        member = make_member_dto(tg_id='123', member_id='m1')
        result = self._run('123', [member], [self._make_page([t1, t2], 2)])
        self.assertEqual(result, [t1, t2])


class TestActiveMembersFromReSwyncaDataSource(unittest.TestCase):

    def _run(self, members):
        mock_api = make_context_manager_mock()
        members_api_mock = MagicMock()
        members_api_mock.members_controller_find_all.return_value = members
        with patch.object(OpenApiDataSource, 'init_api_client', return_value=mock_api):
            with patch('logic.data_providers.MembersApi', return_value=members_api_mock):
                ActiveMembersFromReSwyncaDataSource(host='http://test', access_token='tok', user_id='1')
                return ActiveMembersFromReSwyncaDataSource.get_records()

    def test_returns_active_members_with_telegram_name(self):
        member = make_member_dto(tg_id='1', tg_name='alice', status='active')
        result = self._run([member])
        self.assertEqual(result, [member])

    def test_excludes_frozen_members(self):
        member = make_member_dto(tg_id='1', tg_name='frozen_user', status='frozen')
        result = self._run([member])
        self.assertEqual(result, [])

    def test_excludes_members_without_telegram_metadata(self):
        member = make_member_dto_no_tg()
        result = self._run([member])
        self.assertEqual(result, [])

    def test_excludes_members_with_null_telegram_name(self):
        member = make_member_dto(tg_id='1', tg_name=None, status='active')
        result = self._run([member])
        self.assertEqual(result, [])

    def test_returns_empty_when_no_members(self):
        result = self._run([])
        self.assertEqual(result, [])

    def test_returns_only_active_from_mixed_list(self):
        active = make_member_dto(tg_id='1', tg_name='alice', status='active', member_id='m1')
        frozen = make_member_dto(tg_id='2', tg_name='bob', status='frozen', member_id='m2')
        result = self._run([active, frozen])
        self.assertEqual(result, [active])


if __name__ == '__main__':
    unittest.main()
