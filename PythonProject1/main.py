import json
import random
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загрузка вопросов из JSON-файла
def load_questions():
    with open('questions.json', 'r', encoding='utf-8') as file:
        return json.load(file)

# Сохранение результатов в JSON-файл
def save_results(user_id, score):
    try:
        with open('results.json', 'r', encoding='utf-8') as file:
            results = json.load(file)
    except FileNotFoundError:
        results = {}

    results[user_id] = score

    with open('results.json', 'w', encoding='utf-8') as file:
        json.dump(results, file, ensure_ascii=False, indent=4)

# Получение результатов пользователя
def get_user_results(user_id):
    try:
        with open('results.json', 'r', encoding='utf-8') as file:
            results = json.load(file)
            return results.get(str(user_id), 0)
    except FileNotFoundError:
        return 0

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    score = get_user_results(user_id)
    await update.message.reply_text(
        f"Привет! Я бот-викторина. Твой текущий счёт: {score}\n"
        "Выбери уровень сложности:",
        reply_markup=ReplyKeyboardMarkup([['Лёгкий', 'Средний', 'Сложный']], one_time_keyboard=True)
    )

# Обработка выбора уровня сложности
async def choose_difficulty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    difficulty = update.message.text.lower()
    context.user_data['difficulty'] = difficulty
    context.user_data['score'] = 0
    await ask_question(update, context)

# Задать вопрос
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    questions = load_questions()
    difficulty = context.user_data['difficulty']
    available_questions = [q for q in questions if q['difficulty'] == difficulty]

    if not available_questions:
        await update.message.reply_text("Вопросы для выбранного уровня сложности закончились.")
        return

    question = random.choice(available_questions)
    context.user_data['current_question'] = question

    options = question['options']
    random.shuffle(options)

    await update.message.reply_text(
        f"Вопрос: {question['question']}\n\n" +
        "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)]),
        reply_markup=ReplyKeyboardMarkup([['1', '2', '3', '4']], one_time_keyboard=True)
    )

# Проверка ответа
async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_answer = update.message.text
    question = context.user_data['current_question']
    correct_answer = question['correct_answer']

    if user_answer == str(question['options'].index(correct_answer) + 1):
        context.user_data['score'] += 1
        await update.message.reply_text("Правильно! 🎉")
    else:
        await update.message.reply_text(f"Неправильно. Правильный ответ: {correct_answer}")

    await ask_question(update, context)

# Команда /results
async def show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    score = context.user_data.get('score', 0)
    save_results(user_id, score)
    await update.message.reply_text(f"Твой итоговый счёт: {score}")

# Основная функция
def main():
    application = Application.builder().token("7136893641:AAE_45HJZLRHFTMwBai9nCVz0Ny65jP5hrE").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    if text in ['лёгкий', 'средний', 'сложный']:
        await choose_difficulty(update, context)
    elif text in ['1', '2', '3', '4']:
        await check_answer(update, context)
    elif text == '/results':
        await show_results(update, context)
    else:
        await update.message.reply_text("Пожалуйста, выбери уровень сложности или ответь на вопрос.")

if __name__ == '__main__':
    main()