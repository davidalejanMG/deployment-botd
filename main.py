from flask import Flask, request, abort
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes,
    filters, CallbackQueryHandler, ConversationHandler
)
import os
import difflib
import asyncio
import nest_asyncio
import psycopg
from dotenv import load_dotenv

nest_asyncio.apply()

NOMBRE, LINK = range(2)
ADMIN_ID = [1853918304, 5815326573]

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = f"https://deployment-botd-2.onrender.com/webhook/{BOT_TOKEN}"

def crear_tabla_si_no_existe():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS peliculas (
                    titulo TEXT PRIMARY KEY,
                    link TEXT NOT NULL
                );
            """)
        conn.commit()
crear_tabla_si_no_existe()

def cargar_peliculas():
    data = {}
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT titulo, link FROM peliculas;")
            rows = cur.fetchall()
            for titulo, link in rows:
                data[titulo] = link
    return data

# Handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_bienvenido = (
        "🎬 ¡Bienvenido a Cine+💭Bot Series y Películas!\n\n"
        "📌 Este bot te permite buscar enlaces de películas almacenadas por el administrador.\n\n"
        "🔍 Escribe el nombre de la película que deseas buscar.\n\n"
        "➕ Solo los administradores pueden usar /agregar.\n"
        "🆘 Usa /ayuda para ver los comandos disponibles."
    )
    keyboard = [
        [InlineKeyboardButton("Ver ayuda", callback_data="ayuda")],
        [InlineKeyboardButton("👥 Unirse a la Comunidad", url="https://t.me/addlist/3d5veWGOzdZiMzI5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(mensaje_bienvenido, reply_markup=reply_markup)

async def manejar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "ayuda":
        await query.edit_message_text(
            "📚 *Comandos disponibles:*\n\n"
            " buscar <nombre de la película deseada>\n"
            "/agregar – Agregar una película (admin)\n"
            "/cancelar – Cancelar operación\n"
            "/eliminar – eliminar película agregada solo por (admin)\n"
            "/ayuda – Mostrar esta ayuda",
            parse_mode='Markdown'
        )

async def iniciar_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return ConversationHandler.END

    context.user_data.clear()
    await update.message.reply_text("🎬 ¿Cómo se llama la película o serie que quieres agregar?")
    return NOMBRE

async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nombre = update.message.text.lower().strip()
    if not nombre:
        await update.message.reply_text("⚠️ El nombre no puede estar vacío. Inténtalo de nuevo.")
        return NOMBRE

    context.user_data["titulo"] = nombre
    await update.message.reply_text("🔗 Ahora, por favor envíame el link de la película o serie.")
    return LINK

async def recibir_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    titulo = context.user_data.get("titulo")
    link = update.message.text.strip()

    if not titulo:
        await update.message.reply_text("⚠️ No se encontró el título. Usa /agregar de nuevo.")
        return ConversationHandler.END

    if not link.startswith("http"):
        await update.message.reply_text("🚫 El link no es válido. Asegúrate de que empiece con http o https.")
        return LINK

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO peliculas (titulo, link) VALUES (%s, %s) ON CONFLICT (titulo) DO UPDATE SET link = EXCLUDED.link;",
                (titulo, link)
            )
        conn.commit()

    await update.message.reply_text(f"✅ Película o serie '{titulo}' agregada con éxito.")
    context.user_data.clear()
    return ConversationHandler.END

async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    consulta = update.message.text.lower().strip()
    data = cargar_peliculas()
    if consulta in data:
        await update.message.reply_text(f"🎬 Aquí tienes el link de '{consulta}':\n{data[consulta]}")
    else:
        sugerencias = difflib.get_close_matches(consulta, data.keys(), n=3, cutoff=0.4)
        if sugerencias:
            mensaje = "❌ No encontré esa película exactamente.\n"
            mensaje += "🔍 ¿Quizás quisiste decir alguna de estas?\n"
            mensaje += "\n".join(f"• {sug}" for sug in sugerencias)
            await update.message.reply_text(mensaje)
        else:
            await update.message.reply_text("❌ No se encontró la película")

async def borrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return ConversationHandler.END

    args = context.args
    if not args:
        await update.message.reply_text("❌ Debes escribir el nombre de la película a borrar.")
        return

    titulo = " ".join(args).lower().strip()

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM peliculas WHERE titulo = %s;", (titulo,))
        conn.commit()

    await update.message.reply_text(f"✅ '{titulo}' ha sido eliminado.")

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Comandos disponibles:*\n\n"
        " buscar <nombre de la película deseada>\n"
        "/start – Ver mensaje de bienvenida\n"
        "/agregar – Agregar una película (admin)\n"
        "/cancelar – Cancelar operación\n"
        "/eliminar – Eliminar película (admin)",
        parse_mode='Markdown'
    )

telegram_app = Application.builder().token(BOT_TOKEN).updater(None).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("agregar", iniciar_agregar)],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_link)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)

telegram_app.add_handler(conv_handler)
telegram_app.add_handler(CommandHandler("eliminar", borrar))
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("ayuda", ayuda))
telegram_app.add_handler(CallbackQueryHandler(manejar_callback))
telegram_app.add_handler(MessageHandler(
    filters.TEXT & ~filters.COMMAND & ~filters.Regex(r"^https?://"),
    buscar
))

app = Flask(__name__)

#  inicializar webhook solo una vez
webhook_configured = False

@app.before_request
def setup_webhook_once():
    global webhook_configured
    if not webhook_configured:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(telegram_app.initialize())
        loop.run_until_complete(telegram_app.bot.set_webhook(WEBHOOK_URL))
        print(f"✅ Webhook configurado en: {WEBHOOK_URL}")
        webhook_configured = True

@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(telegram_app.process_update(update))
        return "OK"
    else:
        abort(403)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)







