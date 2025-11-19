import secrets
import string
from typing import Dict

class PasswordGenerator:
    """Генератор паролей"""

    @staticmethod
    def generate_password(settings: Dict) -> str:
        """Генерация пароля по настройкам"""
        length = settings.get('length', 16)
        char_categories = {
            'use_uppercase': string.ascii_uppercase,
            'use_lowercase': string.ascii_lowercase,
            'use_digits': string.digits,
            'use_special': '!@#$%^&*()_+-=[]{}|;:,.<>?'
        }

        characters = ''.join(
            chars for setting, chars in char_categories.items() 
            if settings.get(setting, True)
        )

        if not characters:
            raise ValueError("Не выбран ни один тип символов для генерации пароля")

        # Гарантируем наличие хотя бы одного символа из каждой выбранной категории
        password = [
            secrets.choice(char_categories[category])
            for category in char_categories 
            if settings.get(category, True)
        ]

        # Добиваем до нужной длины
        while len(password) < length:
            password.append(secrets.choice(characters))

        secrets.SystemRandom().shuffle(password)
        return ''.join(password[:length])