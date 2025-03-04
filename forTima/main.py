import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    PreCheckoutQueryHandler,
    ContextTypes
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Конфигурация
TOKEN = '7136893641:AAE_45HJZLRHFTMwBai9nCVz0Ny65jP5hrE'
PROVIDER_TOKEN = '1744374395:TEST:cfe04e369c98430aad94'
ADMIN_CHAT_ID = 1494753646

SERVICES = {
    "🎨 Дизайн сайта": 10000,
    "🛠️ Разработка лендинга": 20000,
    "📱 Мобильное приложение": 50000,
    "⚙️ Техническая поддержка": 15000,
    "📈 SEO-оптимизация": 30000,
}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    welcome_text = (
        "👋 Добро пожаловать в <b>Digital Solutions</b>!\n\n"
        "🚀 Мы специализируемся на:\n"
        "• Создании современных сайтов и лендингов\n"
        "• Разработке мобильных приложений\n"
        "• Технической поддержке проектов\n"
        "• Продвижении в поисковых системах\n\n"
        "👇 Выберите нужную услугу:"
    )

    keyboard = [[InlineKeyboardButton(service, callback_data=service)] for service in SERVICES]
    await update.message.reply_html(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard))


async def service_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data not in SERVICES:
        return

    selected_service = query.data
    price = SERVICES[selected_service]

    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=f"Оплата: {selected_service}",
        description="⚡ После оплаты менеджер свяжется в течение 2 часов",
        payload=f"{query.message.chat_id}_{selected_service}",
        provider_token=PROVIDER_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(selected_service, price)],
        need_name=True
    )


async def precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.message.successful_payment
    service = payment.invoice_payload.split("_")[1]
    user = update.message.from_user

    keyboard = [[InlineKeyboardButton("🔄 Выбрать другие услуги", callback_data="restart")]]
    await update.message.reply_html(
        f"✅ <b>Оплата прошла успешно!</b>\n\n"
        f"💼 Услуга: {service}\n"
        f"💳 Сумма: {payment.total_amount // 100} ₽\n\n"
        "⏳ Наш менеджер свяжется с вами в течение <b>2 часов</b>",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    await context.bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"🚨 Новый заказ!\n\n"
             f"👤 Клиент: @{user.username}\n"
             f"💼 Услуга: {service}\n"
             f"💰 Сумма: {payment.total_amount // 100} ₽",
        parse_mode="HTML"
    )


async def restart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await query.message.delete()

    welcome_text = "🔄 Выберите нужную услугу:"
    keyboard = [[InlineKeyboardButton(service, callback_data=service)] for service in SERVICES]
    await query.message.reply_html(
        welcome_text,
        reply_markup=InlineKeyboardMarkup(keyboard))


def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(restart_handler, pattern="^restart$"))
    application.add_handler(CallbackQueryHandler(service_handler))
    application.add_handler(PreCheckoutQueryHandler(precheckout))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    application.run_polling()


if __name__ == '__main__':
    main()