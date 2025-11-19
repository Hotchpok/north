import os
import hashlib
from typing import Dict

class EncryptionManager:
    """Менеджер шифрования для паролей"""

    @staticmethod
    def generate_key(password: str, salt: bytes) -> bytes:
        """Генерация ключа из пароля с использованием PBKDF2"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000,
            32
        )

    @staticmethod
    def encrypt(data: str, key: bytes) -> Dict[str, bytes]:
        """Шифрование данных"""
        salt = os.urandom(16)
        encryption_key = EncryptionManager.generate_key(key.hex(), salt)

        encrypted = bytes(
            byte ^ encryption_key[i % len(encryption_key)]
            for i, byte in enumerate(data.encode('utf-8'))
        )
        return {'encrypted_data': encrypted, 'salt': salt}

    @staticmethod
    def decrypt(encrypted_data: bytes, salt: bytes, key: bytes) -> str:
        """Дешифрование данных"""
        encryption_key = EncryptionManager.generate_key(key.hex(), salt)

        decrypted = bytes(
            byte ^ encryption_key[i % len(encryption_key)]
            for i, byte in enumerate(encrypted_data)
        )
        return decrypted.decode('utf-8')