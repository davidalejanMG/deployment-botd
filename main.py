from flask import Flask, request, abort
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import asyncio

BOT_TOKEN = os.environ.get("BOT_TOKEN")
print(f"🟢 BOT_TOKEN en runtime: {BOT_TOKEN}")

app = Flask(__name__)

telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("¡Hola! Estoy vivo 🚀")

telegram_app.add_handler(CommandHandler("start", start))

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)

    asyncio.create_task(telegram_app.process_update(update))
    return "OK"

@app.route("/set_webhook")
def set_webhook():
    bot = telegram_app.bot
    BASE_URL = request.host_url.strip("/")
    webhook_url = f"{BASE_URL}/webhook/{BOT_TOKEN}"
    asyncio.run(bot.set_webhook(url=webhook_url))
    return f"✅ Webhook configurado en: {webhook_url}"

if __name__ == "__main__":

    async def main():
        await telegram_app.initialize()
        await telegram_app.start()
        print("✅ Telegram bot iniciado...")

    loop = asyncio.get_event_loop()
    loop.create_task(main())

    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))





