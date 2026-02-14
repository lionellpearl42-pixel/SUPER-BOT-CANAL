import os
import json
import random
import re
import asyncio
import threading
from flask import Flask
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
        json.dump(DEFAULT_CONFIG, f, indent=4)

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

# ===== GERAR TEXTO HUMANO =====
async def gerar_post(style, size):
    prompt = random.choice(PROMPT_STYLES.get(style, PROMPT_STYLES["romantico"]))
    # Instruções extras para soar humano
    prompt += (
        "\nFaça o texto parecer que uma pessoa real está escrevendo. "
        "Evite repetir palavras ou frases. "
        "Use variações na construção das sentenças, inclua pausas naturais, "
        "expressões humanas e emoção. "
        "Deixe a escrita fluida e envolvente."
    )

    char_limit = TEXT_LIMITS.get(size, 220)

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"Gere UM ÚNICO TEXTO em UMA ÚNICA ESTROFE. "
                        f"O texto deve ter NO MÁXIMO {char_limit} caracteres. "
                        f"Deve ter começo, meio e fim. "
                        f"Finalize completamente a ideia. "
                        f"Não quebre linhas. "
                        f"Não pare no meio da frase. "
                        f"Faça o texto parecer humano: natural, emocional, variado e sem repetições."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            temperature=1.0,
            top_p=0.9,
            frequency_penalty=0.5,
            presence_penalty=0.3,
            max_tokens=180
        )

        texto = response.choices[0].message.content.strip()
        texto = texto.replace("\n", " ").replace("  ", " ")

        # Remove repetições consecutivas
        texto = re.sub(r'\b(\w+)( \1\b)+', r'\1', texto)

        # Finaliza pontuação
        if not texto.endswith((".", "!", "?")):
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

# ===== SERVIDOR WEB PARA UPTIME ROBOT =====
web_app = Flask('')

@web_app.route('/')
def home():
    return "Bot está vivo 🚀"

def run_web():
    web_app.run(host='0.0.0.0', port=8080)

# Roda o servidor Flask em uma thread separada
threading.Thread(target=run_web).start()

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

async def setup(application: Application):
    scheduler.add_job(postar, "interval", hours=2, id="post_job", args=[application])
    scheduler.start()

if __name__ == "__main__":
    app.post_init = setup
    app.run_polling()
