from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, CallbackQueryHandler, ConversationHandler
import json
import os
import difflib

NOMBRE, LINK = range(2)
ADMIN_ID= [1853918304, 5815326573]

# Base de datos en archivo JSON
DATA_FILE = "peliculas.json"

def cargar_peliculas():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_peliculas(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
# Comando /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_bienvenido=(
        "🎬 ¡Bienvenido a Cine+💭Bot Series y Películas!\n\n"
        "📌 Este bot te permite buscar enlaces de películas almacenadas por el administrador.\n\n"
        "🔍 Escribe el nombre de la pelicula que se desea buscar.\n\n" 
        "➕ Solo el administrador puede usar /agregar para añadir nuevas películas.\n"
        "🆘 Escribe /ayuda para ver los comandos disponibles."
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
            " buscar <nombre de la pelicula deseada>\n"
            "/agregar <nombre> <link> – Agregar una película (admin)\n"
            "/start – Ver mensaje de bienvenida\n"
            "/cancelar – Cancelar operación de agregar película por el adminstrador\n\n"
            "/ayuda – Mostrar esta ayuda",
            parse_mode='Markdown'
        )

async def iniciar_agregar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_ID:
        await update.message.reply_text("🚫 No tienes permiso para usar este comando.")
        return ConversationHandler.END
    await update.message.reply_text("🎬 ¿Cómo se llama la película o serie que quieres agregar?")
    return NOMBRE

async def recibir_nombre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["titulo"] = update.message.text.lower().strip()
    await update.message.reply_text("🔗 Ahora, por favor envíame el link de la película o serie.")
    return LINK

async def recibir_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    titulo = context.user_data.get("titulo")
    link = update.message.text.strip()
    data = cargar_peliculas()
    data[titulo] = link
    guardar_peliculas(data)

    await update.message.reply_text(f"✅ Película o serie '{titulo}' agregada con éxito.")
    
    context.user_data.clear()  
    return ConversationHandler.END  
    
async def cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Operación cancelada.")
    return ConversationHandler.END
    
async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("titulo"):
        return
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
            await update.message.reply_text("❌ No se encontró la película ")
            
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📚 *Comandos disponibles:*\n\n"
        " buscar <nombre de la pelicula deseada>\n"
        "/start – Ver mensaje de bienvenida\n"
        "/cancelar – Cancelar operación de agregar película por el adminstrador\n\n"
        "/ayuda – Mostrar esta ayuda",
        parse_mode='Markdown'
    )

BOT_TOKEN = "8077951983:AAHL3cV_CLdC_Nb7KNQ_CG0U_al0XpS6eag"

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ayuda", ayuda))
app.add_handler(CallbackQueryHandler(manejar_callback))
conv_handler = ConversationHandler(
    entry_points=[CommandHandler("agregar", iniciar_agregar)],
    states={
        NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_nombre)],
        LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, recibir_link)],
    },
    fallbacks=[CommandHandler("cancelar", cancelar)],
)
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, buscar))
app.run_polling()

