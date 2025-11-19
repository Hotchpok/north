import os


BOT_TOKEN = os.getenv('BOT_TOKEN', '7136893641:AAF7cbKGkwKmTjedZO8E7qTmRkm-Iz8gdW4')

SETTINGS, SERVICE_NAME, PASSWORD_LENGTH, PASSWORD_ACTIONS = range(4)


LOG_CONFIG = {
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': 'INFO'
}



DB_PATH = 'password_manager.db'
