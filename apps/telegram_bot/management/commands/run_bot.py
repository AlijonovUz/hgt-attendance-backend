import asyncio
import logging
import socket
from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot
from aiohttp import ClientSession, TCPConnector

from apps.telegram_bot.views import dp

logger = logging.getLogger(__name__)

async def start_bot():
    session = ClientSession(connector=TCPConnector(family=socket.AF_INET))
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=session)
    logger.info("Bot is running in Polling mode...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

class Command(BaseCommand):
    help = 'Telegram botni Polling rejimida ishga tushirish'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Telegram bot (Polling)..."))
        try:
            asyncio.run(start_bot())
        except KeyboardInterrupt:
            self.stdout.write(self.style.SUCCESS("Bot stopped manually."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred: {e}"))
