import asyncio
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from aiogram import Bot

from apps.telegram_bot.views import dp

logger = logging.getLogger(__name__)

async def start_bot():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    logger.info("Bot is running in Polling mode...")
    try:
        await bot.delete_webhook(drop_pending_updates=True)
    except Exception as e:
        logger.warning(f"Failed to delete webhook: {e}")
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
