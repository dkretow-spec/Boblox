import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Токен вашего бота (получить у @BotFather)
BOT_TOKEN = "8584968006:AAE6xuhOQ9cbFlG3YCPH6oo7XXSz9g6R5A8"

# Кого упоминать
TARGET_USERNAME = "kiti510"

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает любое сообщение и отвечает упоминанием."""
    # Игнорируем сообщения от самого бота, чтобы избежать бесконечного цикла
    if update.effective_user and update.effective_user.username == "ваш_бот_юзернейм":
        return

    # Отвечаем в тот же чат упоминанием
    await update.message.reply_text(f"@{TARGET_USERNAME}")

def main():
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()

    # Добавляем обработчик на ВСЕ текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота (поллинг)
    print("Бот запущен...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()