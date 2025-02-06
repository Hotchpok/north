import telebot
from telebot import types
from module2 import process_excel
import os

# Замените 'YOUR_BOT_TOKEN' на токен вашего бота
bot = telebot.TeleBot('7887527298:AAHM2EuNEhA-hDi7wQfOn-HQVNBInUMTO3w')

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! Отправь мне Excel-файл с фамилиями.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)


        # Сохраняем файл
        input_file = "input.xlsx"
        with open(input_file, 'wb') as new_file:
            new_file.write(downloaded_file)

        # Обрабатываем файл
        processed_file = process_excel(input_file)

        if processed_file:
            # Отправляем обработанный файл
            with open(processed_file, 'rb') as file_to_send:
                bot.send_document(message.chat.id, file_to_send)
            # Удаляем временные файлы
            os.remove(input_file)
            os.remove(processed_file)
        else:
            bot.reply_to(message, "Ошибка при обработке файла.")

    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {e}")


if __name__ == "__main__":
    bot.polling()