import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeChat,
)
from aiogram.filters import CommandStart, Command
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


def get_connect_keyboard(uuid_str, lang="uz_latn"):
    if lang == "uz_latn":
        text = "✅ Telegramga ulanish"
    elif lang == "uz_cyrl":
        text = "✅ Telegram га уланиш"
    else:
        text = "✅ Привязать к Telegram"
    buttons = [
        [
            InlineKeyboardButton(
                text=text, callback_data=f"connect:{uuid_str}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_disconnect_keyboard(uuid_str, lang="uz_latn"):
    if lang == "uz_latn":
        text = "❌ Telegramdan uzish"
    elif lang == "uz_cyrl":
        text = "❌ Telegram дан узиш"
    else:
        text = "❌ Отключить от Telegram"
    buttons = [
        [
            InlineKeyboardButton(
                text=text, callback_data=f"disconnect:{uuid_str}"
            )
        ]
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

            if user.telegram_id:
                lang = user.language or "uz_latn"
                if lang == "uz_latn":
                    text = "✅ <b>Profilingiz allaqachon Telegramga ulangan!</b>\n\nAgar profilni Telegramdan uzmoqchi bo'lsangiz, quyidagi tugmani bosing:"
                elif lang == "uz_cyrl":
                    text = "✅ <b>Профилингиз аллақачон Telegram га уланган!</b>\n\nАгар профилни Telegram дан узмоқчи бўлсангиз, қуйидаги тугмани босинг:"
                else:
                    text = "✅ <b>Ваш профиль уже привязан к Telegram!</b>\n\nЕсли вы хотите отключить профиль от Telegram, нажмите кнопку ниже:"
                
                await message.answer(
                    text,
                    reply_markup=get_disconnect_keyboard(uuid_str, lang),
                    parse_mode="HTML",
                )
            else:
                await message.answer(
                    "🇺🇿 <b>Iltimos, o'zingizga qulay tilni tanlang:</b>\n"
                    "🇺🇿 <b>Илтимос, ўзингизга қулай тилни танланг:</b>\n"
                    "🇷🇺 <b>Пожалуйста, выберите удобный для вас язык:</b>",
                    reply_markup=get_language_keyboard(uuid_str),
                    parse_mode="HTML",
                )
        except User.DoesNotExist:
            await message.answer(
                "❌ <b>Foydalanuvchi topilmadi!</b>\n\nIltimos, tizim orqali qayta urinib ko'ring.",
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Error in telegram start handler: {e}")
            await message.answer(
                "⚠️ <b>Xatolik yuz berdi!</b>\n\nIltimos, birozdan so'ng qaytadan urinib ko'ring.",
                parse_mode="HTML",
            )
    else:
        from apps.users.models import User
        
        try:
            user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)
            lang = user.language or "uz_latn"
            if lang == "uz_latn":
                text = "✅ <b>Profilingiz allaqachon Telegramga ulangan!</b>\n\nAgar profilni Telegramdan uzmoqchi bo'lsangiz, quyidagi tugmani bosing:"
            elif lang == "uz_cyrl":
                text = "✅ <b>Профилингиз аллақачон Telegram га уланган!</b>\n\nАгар профилни Telegram дан узмоқчи бўлсангиз, қуйидаги тугмани босинг:"
            else:
                text = "✅ <b>Ваш профиль уже привязан к Telegram!</b>\n\nЕсли вы хотите отключить профиль от Telegram, нажмите кнопку ниже:"

            await message.answer(
                text,
                reply_markup=get_disconnect_keyboard(user.id, lang),
                parse_mode="HTML",
            )
        except User.DoesNotExist:
            await message.answer(
                "👋 <b>Assalomu alaykum!</b>\n\nBotdan foydalanish uchun iltimos, dastur (sayt) orqali <b>Telegramga ulanish</b> tugmasini bosing.",
                parse_mode="HTML",
            )


@dp.message(Command("language"))
async def language_command_handler(message: types.Message):
    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(telegram_id=message.from_user.id)
        await message.answer(
            "🇺🇿 <b>Iltimos, o'zingizga qulay tilni tanlang:</b>\n"
            "🇺🇿 <b>Илтимос, ўзингизга қулай тилни танланг:</b>\n"
            "🇷🇺 <b>Пожалуйста, выберите удобный для вас язык:</b>",
            reply_markup=get_language_keyboard(user.id),
            parse_mode="HTML",
        )
    except User.DoesNotExist:
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\nSiz hali tizimga ulanmagansiz. Iltimos, dastur orqali <b>Telegramga ulanish</b> tugmasini bosing.",
            parse_mode="HTML",
        )


@dp.callback_query(F.data.startswith("connect:"))
async def connect_selection_handler(callback_query: types.CallbackQuery):
    _, uuid_str = callback_query.data.split(":")
    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(id=uuid_str)
        user.telegram_id = callback_query.from_user.id
        await sync_to_async(user.save)(update_fields=["telegram_id"])

        await callback_query.message.delete()

        lang = user.language or "uz_latn"
        if lang == "uz_latn":
            text = f"✅ <b>Profilingiz muvaffaqiyatli ulandi!</b>\n\nEndi barcha bildirishnomalarni aynan shu yerda qabul qilib borasiz."
        elif lang == "uz_cyrl":
            text = f"✅ <b>Профилингиз муваффақиятли уланди!</b>\n\nЭнди барча билдиришномаларни айнан шу ерда қабул қилиб борасиз."
        else:
            text = f"✅ <b>Ваш профиль успешно привязан!</b>\n\nТеперь вы будете получать уведомления прямо здесь."

        await callback_query.message.answer(text, parse_mode="HTML")
    except User.DoesNotExist:
        await callback_query.answer("Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in connect selection: {e}")
        await callback_query.answer("Xatolik yuz berdi!", show_alert=True)


@dp.callback_query(F.data.startswith("disconnect:"))
async def disconnect_selection_handler(callback_query: types.CallbackQuery):
    _, uuid_str = callback_query.data.split(":")
    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(id=uuid_str)
        user.telegram_id = None
        await sync_to_async(user.save)(update_fields=["telegram_id"])

        await callback_query.message.delete()

        lang = user.language or "uz_latn"
        if lang == "uz_latn":
            text = "❌ <b>Profilingiz Telegramdan uzildi.</b>"
        elif lang == "uz_cyrl":
            text = "❌ <b>Профилингиз Telegram дан узилди.</b>"
        else:
            text = "❌ <b>Ваш профиль отключен от Telegram.</b>"

        await callback_query.message.answer(text, parse_mode="HTML")

        await callback_query.bot.delete_my_commands(
            scope=BotCommandScopeChat(chat_id=callback_query.from_user.id)
        )

    except User.DoesNotExist:
        await callback_query.answer("Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in disconnect selection: {e}")
        await callback_query.answer("Xatolik yuz berdi!", show_alert=True)


@dp.callback_query(F.data.startswith("lang:"))
async def language_selection_handler(callback_query: types.CallbackQuery):
    _, lang, uuid_str = callback_query.data.split(":")

    from apps.users.models import User

    try:
        user = await sync_to_async(User.objects.get)(id=uuid_str)
        user.language = lang
        await sync_to_async(user.save)(update_fields=["language"])

        await callback_query.message.delete()

        if not user.telegram_id:
            if lang == "uz_latn":
                text = f"✅ <b>Til tanlandi.</b>\n\nEndi profilingizni Telegramga ulash uchun pastdagi tugmani bosing."
            elif lang == "uz_cyrl":
                text = f"✅ <b>Тил танланди.</b>\n\nЭнди профилингизни Telegram га улаш учун пастдаги тугмани босинг."
            else:
                text = f"✅ <b>Язык выбран.</b>\n\nТеперь нажмите кнопку ниже, чтобы привязать ваш профиль к Telegram."

            await callback_query.message.answer(
                text, reply_markup=get_connect_keyboard(uuid_str, lang), parse_mode="HTML"
            )
        else:
            if lang == "uz_latn":
                text = f"✅ <b>Til muvaffaqiyatli tanlandi.</b>\n\nEndi barcha bildirishnomalarni o'zbek tilida qabul qilib borasiz."
            elif lang == "uz_cyrl":
                text = f"✅ <b>Тил муваффақиятли танланди.</b>\n\nЭнди барча билдиришномаларни ўзбек тилида қабул қилиб борасиз."
            else:
                text = f"✅ <b>Язык успешно выбран.</b>\n\nТеперь вы будете получать все уведомления на русском языке."

            await callback_query.message.answer(text, parse_mode="HTML")

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

        await callback_query.bot.set_my_commands(
            commands=commands,
            scope=BotCommandScopeChat(chat_id=callback_query.from_user.id),
        )

    except User.DoesNotExist:
        await callback_query.answer("Foydalanuvchi topilmadi!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in language selection: {e}")
        await callback_query.answer("Xatolik yuz berdi!", show_alert=True)