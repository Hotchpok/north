from bot import PasswordManagerBot
from config import BOT_TOKEN

def main():
    bot = PasswordManagerBot(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()