import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

dp = Dispatcher()


def get_language_keyboard(uuid_str):
    buttons = [
        [
            InlineKeyboardButton(
                text="🇺🇿 O'zbekcha (Lotin)", callback_data=f"lang:uz_latn:{uuid_str}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🇺🇿 Ўзбекча (Кирил)", callback_data=f"lang:uz_cyrl:{uuid_str}"
            )
        ],
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"lang:ru:{uuid_str}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@dp.message(CommandStart())
async def start_command_handler(message: types.Message):
    payload = message.text.split(" ")
    if len(payload) > 1:
        uuid_str = payload[1].strip()
        from apps.users.models import User

        try:
            user = await sync_to_async(User.objects.get)(id=uuid_str)
            await message.reply(
                "🇺🇿 <b>Iltimos, o'zingizga qulay tilni tanlang:</b>\n"
                "🇺🇿 <b>Илтимос, ўзингизга қулай тилни танланг:</b>\n"
                "🇷🇺 <b>Пожалуйста, выберите удобный для вас язык:</b>",
                reply_markup=get_language_keyboard(uuid_str),
                parse_mode="HTML",
            )
        except User.DoesNotExist:
            await message.reply(
                "❌ <b>Foydalanuvchi topilmadi!</b>\n\nIltimos, tizim orqali qayta urinib ko'ring.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error in telegram start handler: {e}")
            await message.reply(
                "⚠️ <b>Xatolik yuz berdi!</b>\n\nIltimos, birozdan so'ng qaytadan urinib ko'ring.",
                parse_mode="HTML",
            )
    else:
        await message.reply(
            "👋 <b>Assalomu alaykum!</b>\n\nBotdan foydalanish uchun iltimos, dastur orqali <b>Telegramga ulanish</b> tugmasini bosing.",
            parse_mode="HTML",
        )


@dp.callback_query(F.data.startswith("lang:"))
async def language_selection_handler(callback_query: types.CallbackQuery):
    _, lang, uuid_str = callback_query.data.split(":")

    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(id=uuid_str)
        user.telegram_id = callback_query.from_user.id
        user.language = lang
        await sync_to_async(user.save)(update_fields=["telegram_id", "language"])

        if lang == "uz_latn":
            text = (
                f"✅ <b>Profilingiz muvaffaqiyatli ulandi.</b> "
                f"Endi bildirishnomalarni aynan shu yerda qabul qilib borasiz."
            )
        elif lang == "uz_cyrl":
            text = (
                f"✅ <b>Профилингиз муваффақиятли уланди.</b> "
                f"Энди билдиришномаларни айнан шу ерда қабул қилиб борасиз."
            )
        else:
            text = (
                f"✅ <b>Ваш профиль успешно привязан.</b> "
                f"Теперь вы будете получать уведомления прямо здесь."
            )

        await callback_query.message.edit_text(text, parse_mode="HTML")
        await callback_query.answer()
    except User.DoesNotExist:
        await callback_query.answer("Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in language selection: {e}")
        await callback_query.answer("Xatolik yuz berdi!", show_alert=True)


@csrf_exempt
async def telegram_webhook_view(request):
    if request.method == "POST":
        try:
            if not settings.TELEGRAM_BOT_TOKEN:
                return JsonResponse(
                    {"status": "error", "message": "Bot token is missing"}
                )

            bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
            update_data = json.loads(request.body)
            update = Update(**update_data)

            await dp.feed_update(bot=bot, update=update)

            await bot.session.close()

            return JsonResponse({"status": "ok"})
        except Exception as e:
            logger.error(f"Telegram webhook error: {e}")
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "ok"})
