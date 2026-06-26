import logging
from django.conf import settings
import telebot

from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeChat,
)
from apps.users.models import User

logger = logging.getLogger(__name__)

bot = telebot.TeleBot(settings.TELEGRAM_BOT_TOKEN)

def get_language_keyboard(uuid_str):
    """Foydalanuvchiga Telegram bot tilini tanlash uchun Inline klaviaturani (keyboard) qaytaradi."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🇺🇿 O'zbekcha (Lotin)", callback_data=f"lang:uz_latn:{uuid_str}"))
    markup.add(InlineKeyboardButton("🇺🇿 Ўзбекча (Кирил)", callback_data=f"lang:uz_cyrl:{uuid_str}"))
    markup.add(InlineKeyboardButton("🇷🇺 Русский", callback_data=f"lang:ru:{uuid_str}"))
    return markup


def get_connect_keyboard(uuid_str, lang="uz_latn"):
    """Tilni tanlagandan keyin profilni botga ulash tugmasini (Tilga moslab) qaytaruvchi funksiya."""
    if lang == "uz_latn":
        text = "✅ Telegramga ulanish"
    elif lang == "uz_cyrl":
        text = "✅ Telegram га уланиш"
    else:
        text = "✅ Привязать к Telegram"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text, callback_data=f"connect:{uuid_str}"))
    return markup


def get_disconnect_keyboard(uuid_str, lang="uz_latn"):
    """Profil allaqachon ulangan bo'lsa, uni uzish (disconnect) qilish tugmasini qaytaradi."""
    if lang == "uz_latn":
        text = "❌ Telegramdan uzish"
    elif lang == "uz_cyrl":
        text = "❌ Telegram дан узиш"
    else:
        text = "❌ Отключить от Telegram"
        
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(text, callback_data=f"disconnect:{uuid_str}"))
    return markup


@bot.message_handler(commands=['start'])
def start_command_handler(message):
    """
    Botning /start komandasini qabul qilib, foydalanuvchini identifikatsiya qiladigan asosiy funksiya.
    Agar u link orqali (Deep link) kirgan bo'lsa ID sini taniydi va til tanlashni taklif qiladi.
    """
    payload = message.text.split(" ")
    if len(payload) > 1:
        uuid_str = payload[1].strip()
        try:
            user = User.objects.get(id=uuid_str)
            if user.telegram_id:
                lang = user.language or "uz_latn"
                if lang == "uz_latn":
                    text = "✅ <b>Profilingiz allaqachon Telegramga ulangan!</b>\n\nAgar profilni Telegramdan uzmoqchi bo'lsangiz, quyidagi tugmani bosing:"
                elif lang == "uz_cyrl":
                    text = "✅ <b>Профилингиз аллақачон Telegram га уланган!</b>\n\nАгар профилни Telegram дан узмоқчи бўлсангиз, қуйидаги тугмани босинг:"
                else:
                    text = "✅ <b>Ваш профиль уже привязан к Telegram!</b>\n\nЕсли вы хотите отключить профиль от Telegram, нажмите кнопку ниже:"
                
                bot.send_message(
                    message.chat.id,
                    text,
                    reply_markup=get_disconnect_keyboard(uuid_str, lang),
                    parse_mode="HTML",
                )
            else:
                bot.send_message(
                    message.chat.id,
                    "🇺🇿 <b>Iltimos, o'zingizga qulay tilni tanlang:</b>\n"
                    "🇺🇿 <b>Илтимос, ўзингизга қулай тилни танланг:</b>\n"
                    "🇷🇺 <b>Пожалуйста, выберите удобный для вас язык:</b>",
                    reply_markup=get_language_keyboard(uuid_str),
                    parse_mode="HTML",
                )
        except User.DoesNotExist:
            bot.send_message(
                message.chat.id,
                "❌ <b>Foydalanuvchi topilmadi!</b>\n\nIltimos, tizim orqali qayta urinib ko'ring.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error in telegram start handler: {e}")
            bot.send_message(
                message.chat.id,
                "⚠️ <b>Xatolik yuz berdi!</b>\n\nIltimos, birozdan so'ng qaytadan urinib ko'ring.",
                parse_mode="HTML",
            )
    else:
        try:
            user = User.objects.get(telegram_id=message.from_user.id)
            lang = user.language or "uz_latn"
            if lang == "uz_latn":
                text = "✅ <b>Profilingiz allaqachon Telegramga ulangan!</b>\n\nAgar profilni Telegramdan uzmoqchi bo'lsangiz, quyidagi tugmani bosing:"
            elif lang == "uz_cyrl":
                text = "✅ <b>Профилингиз аллақачон Telegram га уланган!</b>\n\nАгар профилни Telegram дан узмоқчи бўлсангиз, қуйидаги тугмани босинг:"
            else:
                text = "✅ <b>Ваш профиль уже привязан к Telegram!</b>\n\nЕсли вы хотите отключить профиль от Telegram, нажмите кнопку ниже:"

            bot.send_message(
                message.chat.id,
                text,
                reply_markup=get_disconnect_keyboard(user.id, lang),
                parse_mode="HTML",
            )
        except User.DoesNotExist:
            bot.send_message(
                message.chat.id,
                "👋 <b>Assalomu alaykum!</b>\n\nBotdan foydalanish uchun iltimos, dastur (sayt) orqali <b>Telegramga ulanish</b> tugmasini bosing.",
                parse_mode="HTML",
            )


@bot.message_handler(commands=['language'])
def language_command_handler(message):
    """
    Foydalanuvchi ixtiyoriy ravishda /language komandasi orqali bot tilini 
    o'zgartirishni so'raganda ishga tushadigan funksiya.
    """
    try:
        user = User.objects.get(telegram_id=message.from_user.id)
        bot.send_message(
            message.chat.id,
            "🇺🇿 <b>Iltimos, o'zingizga qulay tilni tanlang:</b>\n"
            "🇺🇿 <b>Илтимос, ўзингизга қулай тилни танланг:</b>\n"
            "🇷🇺 <b>Пожалуйста, выберите удобный для вас язык:</b>",
            reply_markup=get_language_keyboard(user.id),
            parse_mode="HTML",
        )
    except User.DoesNotExist:
        bot.send_message(
            message.chat.id,
            "👋 <b>Assalomu alaykum!</b>\n\nSiz hali tizimga ulanmagansiz. Iltimos, dastur orqali <b>Telegramga ulanish</b> tugmasini bosing.",
            parse_mode="HTML",
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith("connect:"))
def connect_selection_handler(call):
    """
    'Telegramga ulanish' tugmasi bosilganda ishlaydigan Callback.
    Foydalanuvchining ID sini olib, uni telegram_id bilan bog'laydi (Saqlaydi).
    """
    _, uuid_str = call.data.split(":")
    try:
        user = User.objects.get(id=uuid_str)
        user.telegram_id = call.from_user.id
        user.save(update_fields=["telegram_id"])

        bot.delete_message(call.message.chat.id, call.message.message_id)

        lang = user.language or "uz_latn"
        if lang == "uz_latn":
            text = f"✅ <b>Profilingiz muvaffaqiyatli ulandi!</b>\n\nEndi barcha bildirishnomalarni aynan shu yerda qabul qilib borasiz."
        elif lang == "uz_cyrl":
            text = f"✅ <b>Профилингиз муваффақиятли уланди!</b>\n\nЭнди барча билдиришномаларни айнан шу ерда қабул қилиб борасиз."
        else:
            text = f"✅ <b>Ваш профиль успешно привязан!</b>\n\nТеперь вы будете получать уведомления прямо здесь."

        bot.send_message(call.message.chat.id, text, parse_mode="HTML")
    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in connect selection: {e}")
        bot.answer_callback_query(call.id, "Xatolik yuz berdi!", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("disconnect:"))
def disconnect_selection_handler(call):
    """
    Foydalanuvchi botdan uzilish tugmasini bosganda ishlaydi. 
    Uning telegram_id maydonini tozalab (None), tizimdan uzib qo'yadi.
    """
    _, uuid_str = call.data.split(":")
    try:
        user = User.objects.get(id=uuid_str)
        user.telegram_id = None
        user.save(update_fields=["telegram_id"])

        bot.delete_message(call.message.chat.id, call.message.message_id)

        lang = user.language or "uz_latn"
        if lang == "uz_latn":
            text = "❌ <b>Profilingiz Telegramdan uzildi.</b>"
        elif lang == "uz_cyrl":
            text = "❌ <b>Профилингиз Telegram дан узилди.</b>"
        else:
            text = "❌ <b>Ваш профиль отключен от Telegram.</b>"

        bot.send_message(call.message.chat.id, text, parse_mode="HTML")
        bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=call.from_user.id))

    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in disconnect selection: {e}")
        bot.answer_callback_query(call.id, "Xatolik yuz berdi!", show_alert=True)


@bot.callback_query_handler(func=lambda call: call.data.startswith("lang:"))
def language_selection_handler(call):
    """
    Klaviaturadan tillaridan birortasi (O'zbek, Rus) bosilganda ishlaydigan Callback.
    Tanlangan tilni bazaga saqlaydi hamda Telegram Menu Buyruqlarini o'sha tilga o'zgartiradi.
    """
    _, lang, uuid_str = call.data.split(":")
    try:
        user = User.objects.get(id=uuid_str)
        user.language = lang
        user.save(update_fields=["language"])

        bot.delete_message(call.message.chat.id, call.message.message_id)

        if not user.telegram_id:
            if lang == "uz_latn":
                text = f"✅ <b>Til tanlandi.</b>\n\nEndi profilingizni Telegramga ulash uchun pastdagi tugmani bosing."
            elif lang == "uz_cyrl":
                text = f"✅ <b>Тил танланди.</b>\n\nЭнди профилингизни Telegram га улаш учун пастдаги тугмани босинг."
            else:
                text = f"✅ <b>Язык выбран.</b>\n\nТеперь нажмите кнопку ниже, чтобы привязать ваш профиль к Telegram."

            bot.send_message(
                call.message.chat.id, text, reply_markup=get_connect_keyboard(uuid_str, lang), parse_mode="HTML"
            )
        else:
            if lang == "uz_latn":
                text = f"✅ <b>Til muvaffaqiyatli tanlandi.</b>\n\nEndi barcha bildirishnomalarni o'zbek tilida qabul qilib borasiz."
            elif lang == "uz_cyrl":
                text = f"✅ <b>Тил муваффақиятли танланди.</b>\n\nЭнди барча билдиришномаларни ўзбек тилида қабул қилиб борасиз."
            else:
                text = f"✅ <b>Язык успешно выбран.</b>\n\nТеперь вы будете получать все уведомления на русском языке."

            bot.send_message(call.message.chat.id, text, parse_mode="HTML")

        commands = []
        if lang == "uz_latn":
            commands = [
                BotCommand(command="start", description="Botni qayta ishga tushirish"),
                BotCommand(command="language", description="Tilni o'zgartirish"),
            ]
        elif lang == "uz_cyrl":
            commands = [
                BotCommand(command="start", description="Ботни қайта ишга тушириш"),
                BotCommand(command="language", description="Тилни ўзгартириш"),
            ]
        else:
            commands = [
                BotCommand(command="start", description="Перезапустить бота"),
                BotCommand(command="language", description="Изменить язык"),
            ]

        bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeChat(chat_id=call.from_user.id),
        )

    except User.DoesNotExist:
        bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in language selection: {e}")
        bot.answer_callback_query(call.id, "Xatolik yuz berdi!", show_alert=True)