import os

# Токен бота (лучше использовать переменные окружения)
BOT_TOKEN = os.getenv('BOT_TOKEN', '7136893641:AAF7cbKGkwKmTjedZO8E7qTmRkm-Iz8gdW4')

# Константы для ConversationHandler
SETTINGS, SERVICE_NAME, PASSWORD_LENGTH, PASSWORD_ACTIONS = range(4)

# Настройки логирования
LOG_CONFIG = {
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': 'INFO'
}

# Настройки базы данных
DB_PATH = 'password_manager.db'