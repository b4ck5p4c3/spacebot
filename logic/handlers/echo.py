from aiogram import types

from logic.handlers import router


@router.message()
async def echo_handler(message: types.Message) -> None:
    await message.answer("/start - сброс состояния (начало работы бота)\n"
                         "/tranlog - показ лога транзакций\n"
                         "/open - открытие двери (потребуется дополнительное подтверждение)")
