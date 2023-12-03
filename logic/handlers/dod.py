import os

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from logic.handlers import router


@router.message(Command(commands=["invite"]))
async def invite(message: Message, state: FSMContext) -> None:
    link = os.getenv('DOD_CHAT_LINK')
    if link is None or link == '':
        await message.reply('Похоже, что ДОД еще не анонсирован, ссылки на чат нет.')
        return
    await message.reply(f'Линк на чат: {link}.')
