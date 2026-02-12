import os
import json
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from groq import Groq

# ===== ENV =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

client = Groq(api_key=GROQ_KEY)

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "channels": [],
    "interval": 2,
    "style": "romantico",
    "enabled": True,
    "text_size": "medio"
}

if not os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "w") as f:
        json.dump(DEFAULT_CONFIG, f)

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ===== PROMPTS =====
PROMPT_STYLES = {
    "romantico": [
        "Escreva um texto romântico intenso, profundo e marcante com começo, meio e fim"
    ],
    "sensual": [
        "Escreva um texto sensual elegante, provocante e intenso com começo, meio e fim"
    ],
    "dark": [
        "Escreva um texto dark romance profundo, melancólico e intenso com começo, meio e fim"
    ],
    "fofo": [
        "Escreva um texto fofo, doce e emocional com começo, meio e fim"
    ]
}

TEXT_LIMITS = {
    "curto": 140,
    "medio": 220,
    "longo": 320,
    "gigante": 480
}

# ===== GERAR TEXTO =====
async def gerar_post(style, size):
    prompt = random.choice(PROMPT_STYLES.get(style, PROMPT_STYLES["romantico"]))
    char_limit = TEXT_LIMITS.get(size, 220)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Gere UM ÚNICO TEXTO curto, em UMA ÚNICA ESTROFE. "
                        "Deve ter começo, meio e fim. "
                        "Finalize a ideia completamente. "
                        "Não use clichês repetidos. "
                        "Não quebre linhas. "
                        "Parecer humano e emocional."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=250
        )

        texto = response.choices[0].message.content.strip()
        texto = texto.replace("\n", " ").replace("  ", " ")

        if len(texto) > char_limit:
            texto = texto[:char_limit].rsplit(" ", 1)[0] + "."

        if not texto.endswith("."):
            texto += "."

        return texto

    except Exception as e:
        print("❌ ERRO GROQ:", e)
        return "⚠️ IA temporariamente indisponível."

# ===== POSTAR =====
async def postar(app: Application):
    config = load_config()
    if not config["enabled"]:
        return

    for canal in config["channels"]:
        try:
            texto = await gerar_post(config["style"], config["text_size"])
            await app.bot.send_message(chat_id=canal, text=f"💖 {texto}")
            print(f"✅ Post enviado para {canal}")
        except Exception as e:
            print(f"❌ Erro em {canal}: {e}")

# ===== MENU =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📢 Canais", callback_data="channels")],
        [InlineKeyboardButton("⏰ Intervalo", callback_data="interval")],
        [InlineKeyboardButton("🎨 Estilo", callback_data="style")],
        [InlineKeyboardButton("📏 Tamanho Texto", callback_data="size")],
        [InlineKeyboardButton("⚡ Postar AGORA", callback_data="post_now")],
        [InlineKeyboardButton("▶️ Ligar", callback_data="enable")],
        [InlineKeyboardButton("⏸ Pausar", callback_data="disable")],
        [InlineKeyboardButton("📊 Status", callback_data="status")]
    ]

    await update.message.reply_text(
        "💘 BOT ROMÂNTICO IA\n\nTextos curtos, intensos e completos",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    config = load_config()

    if query.data == "channels":
        canais = "\n".join(config["channels"]) if config["channels"] else "Nenhum canal"
        await query.edit_message_text(f"📢 Canais:\n{canais}\n\nUse /addcanal @canal")

    elif query.data == "interval":
        await query.edit_message_text(f"⏰ Intervalo: {config['interval']}h\nUse /intervalo 2")

    elif query.data == "style":
        buttons = [
            [InlineKeyboardButton("💗 Fofo", callback_data="setstyle_fofo")],
            [InlineKeyboardButton("🔥 Romântico", callback_data="setstyle_romantico")],
            [InlineKeyboardButton("😈 Sensual", callback_data="setstyle_sensual")],
            [InlineKeyboardButton("🖤 Dark", callback_data="setstyle_dark")]
        ]
        await query.edit_message_text("🎨 Escolha o estilo:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data == "size":
        buttons = [
            [InlineKeyboardButton("✏️ Curto", callback_data="setsize_curto")],
            [InlineKeyboardButton("📝 Médio", callback_data="setsize_medio")],
            [InlineKeyboardButton("📜 Longo", callback_data="setsize_longo")],
            [InlineKeyboardButton("📖 Gigante", callback_data="setsize_gigante")]
        ]
        await query.edit_message_text("📏 Escolha o tamanho:", reply_markup=InlineKeyboardMarkup(buttons))

    elif query.data.startswith("setstyle_"):
        config["style"] = query.data.replace("setstyle_", "")
        save_config(config)
        await query.edit_message_text("✅ Estilo atualizado")

    elif query.data.startswith("setsize_"):
        config["text_size"] = query.data.replace("setsize_", "")
        save_config(config)
        await query.edit_message_text("✅ Tamanho atualizado")

    elif query.data == "enable":
        config["enabled"] = True
        save_config(config)
        await query.edit_message_text("▶️ Autopost ATIVADO")

    elif query.data == "disable":
        config["enabled"] = False
        save_config(config)
        await query.edit_message_text("⏸ Autopost PAUSADO")

    elif query.data == "post_now":
        await query.edit_message_text("⚡ Gerando agora...")
        await postar(context.application)
        await query.edit_message_text("✅ Post enviado")

    elif query.data == "status":
        status = "🟢 ATIVO" if config["enabled"] else "🔴 PAUSADO"
        await query.edit_message_text(
            f"📊 STATUS\n\n"
            f"Canais: {len(config['channels'])}\n"
            f"Intervalo: {config['interval']}h\n"
            f"Estilo: {config['style']}\n"
            f"Tamanho: {config['text_size']}\n"
            f"Status: {status}"
        )

# ===== COMANDOS =====
async def add_canal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use: /addcanal @canal")
        return

    canal = context.args[0]
    config = load_config()

    if canal not in config["channels"]:
        config["channels"].append(canal)
        save_config(config)
        await update.message.reply_text(f"✅ Canal adicionado: {canal}")

async def intervalo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    horas = int(context.args[0])
    config = load_config()
    config["interval"] = horas
    save_config(config)

    scheduler.reschedule_job("post_job", trigger="interval", hours=horas)
    await update.message.reply_text(f"⏰ Intervalo alterado para {horas}h")

# ===== APP =====
app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addcanal", add_canal))
app.add_handler(CommandHandler("intervalo", intervalo))
app.add_handler(CallbackQueryHandler(menu_handler))

scheduler = AsyncIOScheduler()

async def iniciar_scheduler():
    scheduler.add_job(postar, "interval", hours=2, id="post_job", args=[app])
    scheduler.start()

async def main():
    await iniciar_scheduler()
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
