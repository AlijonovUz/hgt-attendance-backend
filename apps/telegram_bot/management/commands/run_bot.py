import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.telegram_bot.views import bot

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run the Telegram Bot using Long Polling (Telebot)"

    def handle(self, *args, **options):
        logger.info("Bot is running in Polling mode (Telebot)...")
        try:
            bot.remove_webhook()
        except Exception as e:
            logger.warning(f"Failed to delete webhook: {e}")

        bot.infinity_polling(timeout=90, long_polling_timeout=90)
