import os
import asyncio
from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """Ти — розумний репетитор з фізики. Допомагай учням розуміти фізику.
- Відповідай чітко і зрозуміло
- Розв'язуй задачі покроково: Дано → Знайти → Розв'язання
- Пиши формули текстом: F = m * a
- Відповідай мовою запитання
- Якщо питання не про фізику — ввічливо відмов"""

user_histories: dict[int, list] = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Привіт, {user.first_name}!\n\n"
        "⚛️ Я репетитор з фізики на базі Gemini AI!\n\n"
        "Можу допомогти з:\n"
        "• 📐 Розв'язанням задач покроково\n"
        "• 📚 Поясненням законів та формул\n"
        "• 🔬 Механіка, термодинаміка, електрика, оптика...\n\n"
        "Просто напиши запитання! 🚀\n\n"
        "/clear — очистити чат\n"
        "/help — приклади запитань"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Приклади запитань:\n\n"
        "— Тіло масою 5 кг рухається зі швидкістю 10 м/с. Знайди кінетичну енергію\n"
        "— Поясни закон Ома простими словами\n"
        "— Що таке термодинаміка?\n"
        "— Як розрахувати силу Архімеда?\n\n"
        "/clear — почати нову тему"
    )

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_histories[update.effective_user.id] = []
    await update.message.reply_text("🗑️ Історію очищено!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []
    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    user_histories[user_id].append(
        types.Content(role="user", parts=[types.Part(text=user_message)])
    )

    thinking_msg = await update.message.reply_text("🔄 Думаю...")

    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-3.6-flash",
            contents=user_histories[user_id],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=1500,
            )
        )
        reply = response.text
        user_histories[user_id].append(
            types.Content(role="model", parts=[types.Part(text=reply)])
        )
        await thinking_msg.delete()
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])
    except Exception as e:
        print(f"Error: {e}")
        await thinking_msg.edit_text("❌ Помилка. Спробуй ще раз або /clear")

async def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущено!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
