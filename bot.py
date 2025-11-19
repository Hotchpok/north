import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from config import BOT_TOKEN, LOG_CONFIG
from database import DatabaseManager
from encryption import EncryptionManager
from password_generator import PasswordGenerator
from handlers import Handlers

# Настройка логирования
logging.basicConfig(**LOG_CONFIG)
logger = logging.getLogger(__name__)

class PasswordManagerBot:
    """Основной класс бота для управления паролями"""

    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self.db = DatabaseManager()
        self.encryption = EncryptionManager()
        self.generator = PasswordGenerator()
        self.scheduler = None
        
        # Инициализация обработчиков
        self.handlers = Handlers(self.db, self.encryption, self.generator)
        self.setup_handlers()

    def setup_handlers(self):
        """Настройка обработчиков команд"""
        for handler in self.handlers.get_handlers():
            self.application.add_handler(handler)

    async def setup_scheduler(self):
        """Настройка планировщика для напоминаний"""
        if self.scheduler is None:
            self.scheduler = AsyncIOScheduler()
            self.scheduler.add_job(
                self.send_annual_reminders,
                'cron',
                hour=9,
                minute=0
            )
            self.scheduler.start()

    async def send_annual_reminders(self):
        """Отправка ежегодных напоминаний о смене паролей"""
        logger.info("Checking for password reminders...")
        try:
            reminders = self.db.get_pending_reminders()
            
            for reminder_id, user_id, password_id, service_name in reminders:
                try:
                    import html
                    escaped_service = html.escape(service_name)
                    await self.application.bot.send_message(
                        chat_id=user_id,
                        text=f"🔔 <b>Напоминание о смене пароля</b>\n\n"
                             f"Прошел год с момента создания пароля для <b>{escaped_service}</b>.\n"
                             f"Рекомендуем сменить пароль для обеспечения безопасности.",
                        parse_mode='HTML'
                    )
                    self.db.mark_reminder_sent(reminder_id)
                except Exception as e:
                    logger.error(f"Error sending reminder to user {user_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in send_annual_reminders: {e}")

    async def post_init(self, application: Application):
        """Выполняется после инициализации бота"""
        await self.setup_scheduler()

    def run(self):
        """Запуск бота"""
        logger.info("Starting Password Manager Bot...")
        self.application.post_init = self.post_init
        self.application.run_polling()