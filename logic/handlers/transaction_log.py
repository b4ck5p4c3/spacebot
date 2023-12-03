import logging

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from logic.data_providers import TransactionDataSource
from logic.handlers import router, DATA_SOURCE_HOST, DATA_SOURCE_TOKEN
from logic.states import PossibleStates


@router.message(Command(commands=["tranlog"]))
async def command_transaction_log(message: Message, state: FSMContext) -> None:
    await state.set_state(PossibleStates.tranlog)
    data_source = TransactionDataSource(DATA_SOURCE_HOST, DATA_SOURCE_TOKEN, message.from_user.id)
    try:
        if data_source.get_records_count() <= 0:
            await message.answer('На текущий момент нет записей в логе транзакций.')
            return
        answer = 'Список транзакций:\n'
        for record in data_source.get_records():
            summ = record.value / 100
            answer += f"{record.datetime} на сумму {summ}"
            if record.comment is not None and len(record.comment) > 0:
                answer += f"({record.comment})"
            answer += '\n'
        await message.answer(answer)
    except Exception as e:
        logging.error("command_transaction_log error: %s" % e)
        await message.answer('При попытке запроса лога произошла ошибка. Похоже, сервис не работает.')

