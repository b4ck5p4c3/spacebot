import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault('TREASURER_USER_ID', '100')
os.environ.setdefault('SWYNCA_API_TOKEN', 'test_token')
os.environ.setdefault('SWYNCA_API_HOST', 'http://localhost')
os.environ.setdefault('MQTT_URL', '')
os.environ.setdefault('GOOGLE_SHEET_URL', '')
os.environ.setdefault('TG_BOT_TOKEN', '0:test')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import bot
from bot import (
    Form,
    cached_answers,
    cached_tran_log,
    cancel_handler,
    command_balance,
    command_start_handler,
    command_transaction_log,
    commend_open_handler,
    echo_handler,
    open_the_door,
    parse_csv_line,
    process_dont_like_write_bots,
    process_unknown_write_bots,
    request_csv,
    send_deposit_notifications,
)

TREASURER_ID = 100


def make_message(user_id=123, username='testuser', text='/start', full_name='Test User'):
    msg = AsyncMock()
    msg.from_user.id = user_id
    msg.from_user.username = username
    msg.from_user.full_name = full_name
    msg.text = text
    return msg


def make_state(current_state=None):
    state = AsyncMock()
    state.get_state = AsyncMock(return_value=current_state)
    return state


def make_callback_query(data='tran:break', user_id=123):
    query = AsyncMock()
    query.data = data
    query.from_user.id = user_id
    query.message = AsyncMock()
    return query


class TestCancelHandler(unittest.IsolatedAsyncioTestCase):

    async def test_clears_state_and_answers_when_state_is_active(self):
        msg = make_message()
        state = make_state(current_state='Form:open')

        await cancel_handler(msg, state)

        state.clear.assert_called_once()
        msg.answer.assert_called_once()

    async def test_does_nothing_when_no_active_state(self):
        msg = make_message()
        state = make_state(current_state=None)

        await cancel_handler(msg, state)

        state.clear.assert_not_called()
        msg.answer.assert_not_called()


class TestCommandStartHandler(unittest.IsolatedAsyncioTestCase):

    async def test_clears_state_and_greets_user(self):
        msg = make_message(full_name='Иван')
        state = make_state()

        await command_start_handler(msg, state)

        state.clear.assert_called_once()
        msg.answer.assert_called_once()
        call_args = msg.answer.call_args[0][0]
        self.assertIn('Иван', call_args)


class TestCommandBalance(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        cached_answers.clear()

    async def test_sets_balance_state_and_answers_with_balance(self):
        msg = make_message(user_id=123)
        state = make_state()

        mock_ds = MagicMock()
        mock_ds.get_records.return_value = [{'123': '500р'}]

        with patch('bot.BalanceFromReSwynca', return_value=mock_ds):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEBUG_TG_USERNAME', None)
                await command_balance(msg, state)

        state.set_state.assert_called_once_with(Form.balance)
        msg.answer.assert_called_once_with('Баланс 500р')

    async def test_answers_empty_when_no_records(self):
        msg = make_message(user_id=123)
        state = make_state()

        mock_ds = MagicMock()
        mock_ds.get_records.return_value = []

        with patch('bot.BalanceFromReSwynca', return_value=mock_ds):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEBUG_TG_USERNAME', None)
                await command_balance(msg, state)

        msg.answer.assert_called_once_with('На текущий момент нет записей по балансу.')

    async def test_returns_cached_answer_without_calling_data_source(self):
        msg = make_message(user_id=42)
        state = make_state()
        cached_answers['balance-42'] = '100р'

        with patch('bot.BalanceFromReSwynca') as MockDS:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEBUG_TG_USERNAME', None)
                await command_balance(msg, state)

        MockDS.assert_not_called()
        msg.answer.assert_called_once_with('Баланс 100р')


class TestCommandTransactionLog(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        cached_answers.clear()

    def _make_record(self, date='01.01.2024', amount='100', ttype='deposit', comment='test'):
        r = MagicMock()
        r.var_date = date
        r.amount = amount
        r.type = ttype
        r.comment = comment
        return r

    async def test_sets_tranlog_state_and_sends_document(self):
        msg = make_message(user_id=123, username='alice')
        state = make_state()

        mock_ds = MagicMock()
        mock_ds.get_records_count.return_value = 1
        mock_ds.get_records.return_value = [self._make_record()]

        with patch('bot.TransactionsFromReSwynca', return_value=mock_ds):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEBUG_TG_USERNAME', None)
                await command_transaction_log(msg, state)

        state.set_state.assert_called_once_with(Form.tranlog)
        msg.answer_document.assert_called_once()

    async def test_answers_text_when_no_records(self):
        msg = make_message(user_id=123)
        state = make_state()

        mock_ds = MagicMock()
        mock_ds.get_records_count.return_value = 0

        with patch('bot.TransactionsFromReSwynca', return_value=mock_ds):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop('DEBUG_TG_USERNAME', None)
                await command_transaction_log(msg, state)

        msg.answer.assert_called_once_with('На текущий момент нет записей в логе транзакций.')
        msg.answer_document.assert_not_called()


class TestOpenHandler(unittest.IsolatedAsyncioTestCase):

    async def test_sets_open_state_and_shows_confirmation_keyboard(self):
        msg = make_message(user_id=1)
        state = make_state()

        await commend_open_handler(msg, state)

        state.set_state.assert_called_once_with(Form.open)
        msg.answer.assert_called_once()

    async def test_denies_access_for_disallowed_user(self):
        msg = make_message(user_id=99)
        state = make_state()

        with patch.object(bot.tg_access_control, 'allow_access', return_value=False):
            await commend_open_handler(msg, state)

        msg.answer.assert_any_call('Похоже, что у Вас нет прав на использование команды.')


class TestOpenDoorStateMachine(unittest.IsolatedAsyncioTestCase):

    async def test_no_answer_clears_state(self):
        msg = make_message(text='нет')
        state = make_state('Form:open')

        await process_dont_like_write_bots(msg, state)

        state.clear.assert_called_once()
        msg.answer.assert_called_once()

    async def test_unknown_answer_sends_hint(self):
        msg = make_message(text='может быть')
        state = make_state('Form:open')

        await process_unknown_write_bots(msg, state)

        msg.reply.assert_called_once()

    async def test_yes_answer_replies_error_when_no_mqtt_client(self):
        msg = make_message(text='да')
        state = make_state('Form:open')

        saved = bot.__dict__.pop('client', None)
        try:
            await open_the_door(msg, state)
        finally:
            if saved is not None:
                bot.client = saved

        msg.reply.assert_called_once()
        call_text = msg.reply.call_args[0][0]
        self.assertIn('без возможности открывать двери', call_text)

    async def test_yes_answer_publishes_mqtt_and_replies(self):
        msg = make_message(text='да', user_id=55, username='doorman')
        state = make_state('Form:open')

        mqtt_mock = MagicMock()
        mqtt_mock.is_connected.return_value = True
        publish_result = MagicMock()
        publish_result.is_published.return_value = True
        mqtt_mock.publish.return_value = publish_result

        with patch.dict(bot.__dict__, {'client': mqtt_mock}):
            await open_the_door(msg, state)

        mqtt_mock.publish.assert_called_once()
        msg.reply.assert_called_once()


class TestRequestCsv(unittest.IsolatedAsyncioTestCase):

    async def test_blocked_for_non_treasurer(self):
        msg = make_message(user_id=999)
        state = make_state()

        await request_csv(msg, state)

        msg.answer.assert_called_once_with('Команда доступна только для казначея')
        state.set_state.assert_not_called()

    async def test_sets_csv_state_for_treasurer(self):
        msg = make_message(user_id=TREASURER_ID)
        state = make_state()

        await request_csv(msg, state)

        state.set_state.assert_called_once_with(Form.csv)
        msg.answer.assert_called_once()


class TestParseCsvLine(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        cached_tran_log.clear()

    async def test_break_command_stops_processing(self):
        query = make_callback_query(data='tran:break', user_id=123)
        state = make_state()

        await parse_csv_line(query, state)

        state.clear.assert_called_once()
        query.message.answer.assert_called_once_with('Обработка файла остановлена')
        query.answer.assert_called_once()

    async def test_non_tran_key_data_skips_api_call(self):
        cached_tran_log['123'] = ['"01.01.2024 12:00";"skip"']
        query = make_callback_query(data='tran:skip', user_id=123)
        state = make_state()

        mock_ds = MagicMock()
        mock_ds.get_records.return_value = []

        with patch('bot.ActiveMembersFromReSwyncaDataSource', return_value=mock_ds):
            with patch('bot.openapi_client') as mock_api:
                await parse_csv_line(query, state)

        mock_api.MemberTransactionsApi.assert_not_called()


class TestEchoHandler(unittest.IsolatedAsyncioTestCase):

    async def test_returns_help_text(self):
        msg = MagicMock()
        msg.answer = AsyncMock()

        await echo_handler(msg)

        msg.answer.assert_called_once()
        text = msg.answer.call_args[0][0]
        self.assertIn('/start', text)
        self.assertIn('/tranlog', text)
        self.assertIn('/open', text)


class TestSendDepositNotifications(unittest.IsolatedAsyncioTestCase):

    async def test_does_nothing_when_no_records(self):
        dp = MagicMock()
        bot_mock = AsyncMock()

        mock_ds = MagicMock()
        mock_ds.get_records_count.return_value = 0

        with patch('bot.BaseDataSource', return_value=mock_ds):
            await send_deposit_notifications(dp, bot_mock)

        bot_mock.send_message.assert_not_called()

    async def test_skips_members_with_no_debt(self):
        dp = MagicMock()
        bot_mock = AsyncMock()

        record = MagicMock()
        record.debt = 0
        record.id = 999

        mock_ds = MagicMock()
        mock_ds.get_records_count.return_value = 1
        mock_ds.get_records.return_value = [record]

        with patch('bot.BaseDataSource', return_value=mock_ds):
            await send_deposit_notifications(dp, bot_mock)

        bot_mock.send_message.assert_not_called()

    async def test_sends_message_when_debt_is_positive(self):
        dp = MagicMock()
        bot_mock = AsyncMock()

        record = MagicMock()
        record.debt = 50000
        record.id = 42

        mock_ds = MagicMock()
        mock_ds.get_records_count.return_value = 1
        mock_ds.get_records.return_value = [record]

        with patch('bot.BaseDataSource', return_value=mock_ds):
            await send_deposit_notifications(dp, bot_mock)

        bot_mock.send_message.assert_called_once()
        call_kwargs = bot_mock.send_message.call_args
        self.assertEqual(call_kwargs.kwargs.get('chat_id') or call_kwargs[1].get('chat_id'), 42)


if __name__ == '__main__':
    unittest.main()
