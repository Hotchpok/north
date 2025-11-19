import sqlite3
import logging
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Менеджер базы данных"""

    def __init__(self, db_path: str = 'password_manager.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Инициализация базы данных"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    master_password_hash TEXT NOT NULL,
                    salt BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS password_settings (
                    user_id INTEGER PRIMARY KEY,
                    length INTEGER DEFAULT 16,
                    use_uppercase BOOLEAN DEFAULT 1,
                    use_lowercase BOOLEAN DEFAULT 1,
                    use_digits BOOLEAN DEFAULT 1,
                    use_special BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS passwords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    service_name TEXT NOT NULL,
                    encrypted_password BLOB NOT NULL,
                    salt BLOB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_reminder_sent TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            conn.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    password_id INTEGER NOT NULL,
                    reminder_date DATE NOT NULL,
                    sent BOOLEAN DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    FOREIGN KEY (password_id) REFERENCES passwords (id)
                )
            ''')

    def user_exists(self, user_id: int) -> bool:
        """Проверка существования пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute(
                'SELECT 1 FROM users WHERE user_id = ?', 
                (user_id,)
            ).fetchone() is not None

    def create_user(self, user_id: int, master_password_hash: str, salt: bytes):
        """Создание нового пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'INSERT INTO users (user_id, master_password_hash, salt) VALUES (?, ?, ?)',
                (user_id, master_password_hash, salt)
            )
            conn.execute(
                'INSERT INTO password_settings (user_id) VALUES (?)',
                (user_id,)
            )

    def verify_master_password(self, user_id: int, password: str) -> bool:
        """Проверка мастер-пароля"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                'SELECT master_password_hash, salt FROM users WHERE user_id = ?',
                (user_id,)
            ).fetchone()
            
            if not result:
                return False

            stored_hash, salt = result
            computed_hash = self._hash_password(password, salt)
            return hmac.compare_digest(stored_hash, computed_hash)

    def _hash_password(self, password: str, salt: bytes) -> str:
        """Хеширование пароля"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            100000
        ).hex()

    def get_user_settings(self, user_id: int) -> Dict:
        """Получение настроек пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                '''SELECT length, use_uppercase, use_lowercase, use_digits, use_special
                   FROM password_settings WHERE user_id = ?''',
                (user_id,)
            ).fetchone()
            
            return {
                'length': result[0] if result else 16,
                'use_uppercase': bool(result[1]) if result else True,
                'use_lowercase': bool(result[2]) if result else True,
                'use_digits': bool(result[3]) if result else True,
                'use_special': bool(result[4]) if result else False
            }

    def update_user_settings(self, user_id: int, settings: Dict):
        """Обновление настроек пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT OR REPLACE INTO password_settings 
                (user_id, length, use_uppercase, use_lowercase, use_digits, use_special)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, *[int(settings[key]) for key in 
                ['length', 'use_uppercase', 'use_lowercase', 'use_digits', 'use_special']]))

    def save_password(self, user_id: int, service_name: str, encrypted_data: bytes, salt: bytes) -> int:
        """Сохранение зашифрованного пароля"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('''
                INSERT INTO passwords (user_id, service_name, encrypted_password, salt)
                VALUES (?, ?, ?, ?)
            ''', (user_id, service_name, encrypted_data, salt))
            return cursor.lastrowid

    def get_user_passwords(self, user_id: int) -> List[Tuple]:
        """Получение списка паролей пользователя"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute('''
                SELECT id, service_name, encrypted_password, salt, created_at
                FROM passwords WHERE user_id = ? ORDER BY created_at DESC
            ''', (user_id,)).fetchall()

    def get_password_by_id(self, password_id: int, user_id: int) -> Optional[Tuple]:
        """Получение пароля по ID"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute('''
                SELECT id, service_name, encrypted_password, salt
                FROM passwords WHERE id = ? AND user_id = ?
            ''', (password_id, user_id)).fetchone()

    def delete_password(self, password_id: int, user_id: int):
        """Удаление пароля"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                'DELETE FROM passwords WHERE id = ? AND user_id = ?',
                (password_id, user_id)
            )

    def schedule_annual_reminder(self, user_id: int, password_id: int):
        """Планирование ежегодного напоминания"""
        reminder_date = datetime.now() + timedelta(days=365)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO reminders (user_id, password_id, reminder_date)
                VALUES (?, ?, ?)
            ''', (user_id, password_id, reminder_date.date()))

    def get_pending_reminders(self) -> List[Tuple]:
        """Получение ожидающих напоминаний"""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute('''
                SELECT r.id, r.user_id, r.password_id, p.service_name
                FROM reminders r
                JOIN passwords p ON r.password_id = p.id
                WHERE r.reminder_date <= date('now') AND r.sent = 0
            ''').fetchall()

    def mark_reminder_sent(self, reminder_id: int):
        """Пометить напоминание как отправленное"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('UPDATE reminders SET sent = 1 WHERE id = ?', (reminder_id,))