import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import logic.handlers
import logic.handlers.start
import logic.handlers.door
import logic.handlers.transaction_log
import logic.handlers.dod
import logic.handlers.echo
from logic.data_providers import ResidentDataSource

scheduler = AsyncIOScheduler()


async def main() -> None:
    dp = Dispatcher()
    bot = Bot(os.getenv('TG_BOT_TOKEN'), parse_mode="HTML")
    dp.include_router(logic.handlers.router)
    scheduler.add_job(send_deposit_notifications, "cron", day=1, minute=0, args=(dp, bot))
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def send_deposit_notifications(dp: Dispatcher, bot):
    data_source = ResidentDataSource(logic.handlers.DATA_SOURCE_TOKEN, logic.handlers.DATA_SOURCE_HOST)
    if data_source.get_records_count() <= 0:
        return
    for record in data_source.get_records():
        if record.debt <= 0:
            continue
        summ = record.debt / 100
        await bot.send_message(chat_id=record.id, text=f"Необходимо пополнить баланс на {summ} рублей")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    asyncio.run(main())
