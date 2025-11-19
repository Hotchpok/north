import html
import hashlib
import logging
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import SETTINGS, SERVICE_NAME, PASSWORD_LENGTH, PASSWORD_ACTIONS

logger = logging.getLogger(__name__)

class Handlers:
    """Класс с обработчиками команд бота"""
    
    def __init__(self, db, encryption, generator):
        self.db = db
        self.encryption = encryption
        self.generator = generator
        self.user_sessions: Dict[int, Dict] = {}

    def get_handlers(self):
        """Возвращает список обработчиков команд"""
        return [
            CommandHandler("start", self.start),
            CommandHandler("help", self.help_command),
            CommandHandler("list", self.list_passwords),
            CommandHandler("settings", self.settings_command),
            CommandHandler("generate", self.generate_command),
            CommandHandler("setmaster", self.set_master_password),
            CommandHandler("delete", self.delete_password_command),
            self.get_password_conversation_handler(),
            self.get_settings_conversation_handler(),
            CallbackQueryHandler(self.handle_button_click),
            MessageHandler(filters.COMMAND, self.unknown_command)
        ]

    def get_password_conversation_handler(self):
        """Conversation Handler для генерации пароля"""
        return ConversationHandler(
            entry_points=[CommandHandler('generate_dialog', self.start_generate_password)],
            states={
                SERVICE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_service_name)
                ],
                PASSWORD_ACTIONS: [
                    CallbackQueryHandler(self.handle_password_actions, pattern='^(save|regenerate|cancel)$')
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

    def get_settings_conversation_handler(self):
        """Conversation Handler для настроек"""
        return ConversationHandler(
            entry_points=[CommandHandler('settings_dialog', self.start_settings)],
            states={
                SETTINGS: [
                    CallbackQueryHandler(self.handle_settings,
                                         pattern='^(length|uppercase|lowercase|digits|special|save|cancel)$')
                ],
                PASSWORD_LENGTH: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_password_length)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel)]
        )

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        logger.info(f"User {user_id} called /start")

        welcome_text = """
🤖 Добро пожаловать в Password Manager Bot!

Этот бот поможет вам:
• 🔐 Генерировать безопасные пароли
• 💾 Сохранять пароли в зашифрованном виде
• 📋 Управлять паролями для разных сервисов
• 🔔 Получать напоминания о смене паролей

Для начала работы установите мастер-пароль командой /setmaster!
        """
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
📖 <b>Доступные команды:</b>

🔐 <b>Установка мастер-пароля:</b>
/setmaster пароль - Установить мастер-пароль

🔑 <b>Работа с паролями:</b>
/generate - Быстрая генерация пароля
/generate_dialog - Генерация с сохранением для сервиса
/list - Показать список паролей
/delete - Удалить пароль

⚙️ <b>Настройки:</b>
/settings - Показать текущие настройки
/settings_dialog - Изменить настройки генерации
        """
        await update.message.reply_text(help_text, parse_mode='HTML')

    async def unknown_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик неизвестных команд"""
        await update.message.reply_text(
            "❌ Неизвестная команда. Используйте /help для просмотра доступных команд."
        )

    async def set_master_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /setmaster"""
        user_id = update.effective_user.id
        
        if self.db.user_exists(user_id):
            await update.message.reply_text("ℹ️ Мастер-пароль уже установлен.")
            return

        if not context.args:
            await update.message.reply_text(
                "🔐 Для установки мастер-пароля введите:\n"
                "/setmaster ваш_пароль\n\n"
                "⚠️ Мастер-пароль должен содержать минимум 6 символов!"
            )
            return

        master_password = ' '.join(context.args)
        
        if len(master_password) < 6:
            await update.message.reply_text("❌ Мастер-пароль должен содержать минимум 6 символов.")
            return
        
        try:
            salt = hashlib.sha256(str(user_id).encode()).digest()
            master_password_hash = self.db._hash_password(master_password, salt)
            self.db.create_user(user_id, master_password_hash, salt)

            await update.message.reply_text(
                "✅ Мастер-пароль успешно установлен!\n\n"
                "Теперь вы можете использовать все функции бота."
            )
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            await update.message.reply_text("❌ Ошибка при установке мастер-пароля.")

    async def generate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Быстрая генерация пароля"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return

        settings = self.db.get_user_settings(user_id)
        try:
            password = self.generator.generate_password(settings)
            escaped_password = html.escape(password)
            await update.message.reply_text(
                f"🔐 <b>Сгенерированный пароль:</b>\n\n"
                f"<code>{escaped_password}</code>\n\n"
                f"💡 Используйте /generate_dialog для сохранения пароля",
                parse_mode='HTML'
            )
        except ValueError as e:
            await update.message.reply_text(f"❌ Ошибка генерации: {str(e)}")

    async def start_generate_password(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало процесса генерации пароля с сохранением"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return ConversationHandler.END

        await update.message.reply_text(
            "📝 Введите название сервиса для которого генерируете пароль:"
        )
        return SERVICE_NAME

    async def handle_service_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка названия сервиса"""
        user_id = update.effective_user.id
        service_name = update.message.text.strip()

        if len(service_name) > 50:
            await update.message.reply_text("❌ Название сервиса слишком длинное. Максимум 50 символов.")
            return SERVICE_NAME

        settings = self.db.get_user_settings(user_id)
        try:
            password = self.generator.generate_password(settings)
        except ValueError as e:
            await update.message.reply_text(f"❌ Ошибка генерации: {str(e)}")
            return ConversationHandler.END

        self.user_sessions[user_id] = {
            'current_password': password,
            'service_name': service_name
        }

        keyboard = [
            [
                InlineKeyboardButton("💾 Сохранить", callback_data='save'),
                InlineKeyboardButton("🔄 Сгенерировать новый", callback_data='regenerate')
            ],
            [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
        ]

        escaped_password = html.escape(password)
        escaped_service = html.escape(service_name)
        
        await update.message.reply_text(
            f"🔐 Сгенерированный пароль для <b>{escaped_service}</b>:\n\n<code>{escaped_password}</code>",
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return PASSWORD_ACTIONS

    async def handle_password_actions(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка действий с паролем"""
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data

        if user_id not in self.user_sessions:
            await query.edit_message_text("❌ Сессия истекла. Начните заново.")
            return ConversationHandler.END

        if action == 'save':
            return await self.save_password_to_db(query, user_id)
        elif action == 'regenerate':
            return await self.regenerate_password(query, user_id)
        elif action == 'cancel':
            await query.edit_message_text("❌ Генерация пароля отменена.")
            self.user_sessions.pop(user_id, None)
            return ConversationHandler.END

        return PASSWORD_ACTIONS

    async def save_password_to_db(self, query, user_id: int) -> int:
        """Сохранение пароля в базу данных"""
        try:
            session_data = self.user_sessions[user_id]
            service_name = session_data['service_name']
            password = session_data['current_password']

            encryption_key = hashlib.sha256(str(user_id).encode()).digest()
            encrypted_data = self.encryption.encrypt(password, encryption_key)

            password_id = self.db.save_password(
                user_id,
                service_name,
                encrypted_data['encrypted_data'],
                encrypted_data['salt']
            )

            if password_id:
                self.db.schedule_annual_reminder(user_id, password_id)

            escaped_service = html.escape(service_name)
            await query.edit_message_text(
                f"✅ Пароль для <b>{escaped_service}</b> успешно сохранен!", 
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error saving password: {e}")
            await query.edit_message_text("❌ Ошибка при сохранении пароля.")
        finally:
            self.user_sessions.pop(user_id, None)

        return ConversationHandler.END

    async def regenerate_password(self, query, user_id: int) -> int:
        """Регенерация пароля"""
        service_name = self.user_sessions[user_id]['service_name']
        settings = self.db.get_user_settings(user_id)

        try:
            new_password = self.generator.generate_password(settings)
            self.user_sessions[user_id]['current_password'] = new_password

            keyboard = [
                [
                    InlineKeyboardButton("💾 Сохранить", callback_data='save'),
                    InlineKeyboardButton("🔄 Сгенерировать новый", callback_data='regenerate')
                ],
                [InlineKeyboardButton("❌ Отмена", callback_data='cancel')]
            ]

            escaped_password = html.escape(new_password)
            escaped_service = html.escape(service_name)

            await query.edit_message_text(
                f"🔐 Новый пароль для <b>{escaped_service}</b>:\n\n<code>{escaped_password}</code>",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except ValueError as e:
            await query.edit_message_text(f"❌ Ошибка генерации: {str(e)}")
            return ConversationHandler.END

        return PASSWORD_ACTIONS

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать текущие настройки"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return

        settings = self.db.get_user_settings(user_id)

        text = f"""
⚙️ <b>Текущие настройки генерации паролей:</b>

• 📏 Длина пароля: {settings['length']} символов
• 🔠 Заглавные буквы: {'✅' if settings['use_uppercase'] else '❌'}
• 🔡 Строчные буквы: {'✅' if settings['use_lowercase'] else '❌'}
• 🔢 Цифры: {'✅' if settings['use_digits'] else '❌'}
• 🔣 Специальные символы: {'✅' if settings['use_special'] else '❌'}

💡 Используйте /settings_dialog для изменения настроек
        """
        await update.message.reply_text(text, parse_mode='HTML')

    async def start_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Начало настройки параметров генерации"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return ConversationHandler.END

        settings = self.db.get_user_settings(user_id)
        return await self.show_settings_menu(update, settings)

    async def show_settings_menu(self, update, settings: Dict) -> int:
        """Показать меню настроек"""
        length = settings['length']
        symbols = {
            'uppercase': ('🔠 Заглавные', settings['use_uppercase']),
            'lowercase': ('🔡 Строчные', settings['use_lowercase']),
            'digits': ('🔢 Цифры', settings['use_digits']),
            'special': ('🔣 Специальные', settings['use_special'])
        }

        text = "⚙️ <b>Настройки генерации паролей</b>\n\nВыберите параметр для изменения:"
        
        keyboard = [
            [InlineKeyboardButton(f"📏 Длина пароля: {length}", callback_data='length')]
        ]
        
        row = []
        for key, (label, enabled) in symbols.items():
            row.append(InlineKeyboardButton(f"{label}: {'✅' if enabled else '❌'}", callback_data=key))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        keyboard.extend([
            [
                InlineKeyboardButton("💾 Сохранить", callback_data='save'),
                InlineKeyboardButton("❌ Отмена", callback_data='cancel')
            ]
        ])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if isinstance(update, Update):
            await update.message.reply_text(text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)

        return SETTINGS

    async def handle_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка настроек"""
        query = update.callback_query
        user_id = query.from_user.id
        action = query.data

        settings = self.db.get_user_settings(user_id)

        if action == 'length':
            await query.edit_message_text("📏 Введите длину пароля (от 8 до 32 символов):")
            return PASSWORD_LENGTH
        elif action in ['uppercase', 'lowercase', 'digits', 'special']:
            settings_key = f"use_{action}"
            settings[settings_key] = not settings[settings_key]
            self.db.update_user_settings(user_id, settings)
            return await self.show_settings_menu(query, settings)
        elif action == 'save':
            self.db.update_user_settings(user_id, settings)
            await query.edit_message_text("✅ Настройки успешно сохранены!")
            return ConversationHandler.END
        elif action == 'cancel':
            await query.edit_message_text("❌ Настройки отменены.")
            return ConversationHandler.END

        return SETTINGS

    async def handle_password_length(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Обработка ввода длины пароля"""
        user_id = update.effective_user.id
        try:
            length = int(update.message.text)
            if 8 <= length <= 32:
                settings = self.db.get_user_settings(user_id)
                settings['length'] = length
                self.db.update_user_settings(user_id, settings)
                return await self.show_settings_menu(update, settings)
            else:
                await update.message.reply_text("❌ Длина пароля должна быть от 8 до 32 символов.")
                return PASSWORD_LENGTH
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите число от 8 до 32.")
            return PASSWORD_LENGTH

    async def list_passwords(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список сохраненных паролей с расшифровкой"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return

        passwords = self.db.get_user_passwords(user_id)

        if not passwords:
            await update.message.reply_text("📭 У вас нет сохраненных паролей.")
            return

        encryption_key = hashlib.sha256(str(user_id).encode()).digest()
        
        text = "📋 <b>Сохраненные пароли:</b>\n\n"
        
        for i, (pwd_id, service, encrypted_pwd, salt, created_at) in enumerate(passwords, 1):
            try:
                decrypted_password = self.encryption.decrypt(encrypted_pwd, salt, encryption_key)
                
                escaped_service = html.escape(service)
                escaped_password = html.escape(decrypted_password)
                
                text += f"<b>{escaped_service}</b> - <code>{escaped_password}</code>\n"
                text += f"   📅 Создан: {created_at[:10]}\n\n"
                
            except Exception as e:
                logger.error(f"Error decrypting password for {service}: {e}")
                escaped_service = html.escape(service)
                text += f"<b>{escaped_service}</b> - ❌ Ошибка расшифровки\n\n"

        text += "\n💡 Используйте /delete для удаления паролей"
        
        if len(text) > 4096:
            parts = []
            while len(text) > 4096:
                split_index = text[:4096].rfind('\n')
                if split_index == -1:
                    split_index = 4096
                parts.append(text[:split_index])
                text = text[split_index:].lstrip()
            parts.append(text)
            
            for part in parts:
                await update.message.reply_text(part, parse_mode='HTML')
        else:
            await update.message.reply_text(text, parse_mode='HTML')

    async def delete_password_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /delete"""
        user_id = update.effective_user.id

        if not self.db.user_exists(user_id):
            await update.message.reply_text("❌ Сначала установите мастер-пароль командой /setmaster")
            return

        passwords = self.db.get_user_passwords(user_id)

        if not passwords:
            await update.message.reply_text("📭 У вас нет сохраненных паролей для удаления.")
            return

        if context.args:
            try:
                password_num = int(context.args[0])
                if 1 <= password_num <= len(passwords):
                    password_id, service_name, *_ = passwords[password_num - 1]
                    self.db.delete_password(password_id, user_id)
                    escaped_service = html.escape(service_name)
                    await update.message.reply_text(
                        f"✅ Пароль для <b>{escaped_service}</b> удален!", 
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text("❌ Неверный номер пароля.")
            except ValueError:
                await update.message.reply_text("❌ Пожалуйста, укажите номер пароля.")
        else:
            text = "🗑️ <b>Выберите пароль для удаления:</b>\n\n"
            for i, (_, service, _, _, created_at) in enumerate(passwords, 1):
                escaped_service = html.escape(service)
                text += f"{i}. <b>{escaped_service}</b> - создан {created_at[:10]}\n"
            
            text += f"\n💡 Используйте: /delete <номер>"
            await update.message.reply_text(text, parse_mode='HTML')

    async def handle_button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на inline кнопки"""
        await update.callback_query.answer()

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Отмена текущей операции"""
        user_id = update.effective_user.id
        self.user_sessions.pop(user_id, None)
        await update.message.reply_text("❌ Операция отменена.")
        return ConversationHandler.END
    