from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from logic.handlers import router


@router.message(Command(commands=["start"]))
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(f"Привет, <b>{message.from_user.full_name}!</b>"
                         " У меня ты можешь посмотреть лог транзакций, "
                         "а оповещение об оплате я сделаю самостоятельно.")
