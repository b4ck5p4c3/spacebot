import json
import logging

from aiogram import F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton

from logic.handlers import router, client, access_control
from logic.states import PossibleStates


@router.message(PossibleStates.open, F.text.casefold() == 'да')
async def open_the_door(message: Message, state: FSMContext) -> None:
    await state.set_state(PossibleStates.start)
    try:
        if client.is_connected() is False:
            client.reconnect()
        publish_result = client.publish('bus/telegram/message', json.dumps({'userid': message.from_user.id}))
        if publish_result.is_published() is False:
            raise IOError('mqtt publish_result._published is False')
    except (ValueError, TypeError, IOError, RuntimeError) as err:
        await message.reply(
            'Что-то пошло не так при попытке открытия :( Дверь не откроется. ',
            reply_markup=ReplyKeyboardRemove()
        )
        logging.error('mqtt publish error')
        logging.error(err)
        return
    await message.reply(
        f"*вы слышите шорох механизма в соседней комнате*"
        f"\n\n"
        f"{message.from_user.username} открыл оранжевую дверь.",
        reply_markup=ReplyKeyboardRemove()
    )


@router.message(Command(commands=["open"]))
async def command_open_handler(message: Message, state: FSMContext) -> None:
    if access_control.allow_access(message.from_user.id) is False:
        await message.answer('Похоже, что у Вас нет прав на использование команды.')
        return
    await state.update_data(name=message.text)
    await state.set_state(PossibleStates.open)
    await message.answer(
        'Точно нужно открыть дверь?',
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(text='Да'),
                    KeyboardButton(text='Нет'),
                ]
            ],
            resize_keyboard=True
        ),
    )


@router.message(PossibleStates.open, F.text.casefold() == "нет")
async def process_dont_like_write_bots(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "Хорошо, открою как-нибудь потом.",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(PossibleStates.open)
async def process_unknown_write_bots(message: Message, state: FSMContext) -> None:
    await message.reply('Принимаются только ответы "Да" или "Нет"')
