import logging
import re
from telegram import Update, ChatPermissions
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ChatMemberHandler, filters, ContextTypes
)

TOKEN = "8629781530:AAEXQbkkoAt-IbSJ5WZSQWmaK4fvw5R7fXg"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Cuvinte interzise ──────────────────────────────────────────────
BAD_WORDS = [
    "pula", "pizda", "muie", "futu", "futut", "fututi", "futu-ti",
    "cacat", "rahat", "curva", "curvă", "proasto", "idiot", "idioato",
    "imbecil", "handicap", "retard", "dracu", "dracului", "mama ta",
    "ma-ta", "mata", "prost", "proasta", "fraier", "fraiera",
    "shit", "fuck", "bitch", "asshole", "cunt", "dick", "bastard"
]

# ── Avertismente per user ──────────────────────────────────────────
warnings = {}

# ── Mesaj bun venit ────────────────────────────────────────────────
async def welcome_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.chat_member.new_chat_members if hasattr(update, 'message') else []:
        pass

async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        name = member.first_name
        welcome = (
            f"👋 Bun venit în Comunitatea FCSB, {name}! 🔴🔵\n\n"
            f"Ești acum parte din cea mai tare comunitate de fani FCSB din România!\n\n"
            f"📌 Citește /reguli înainte să scrii\n"
            f"🎟️ Concursuri cu bilete doar pentru membrii activi\n"
            f"⭐ Fii activ și urcă în clasament cu /top\n"
            f"🛒 Shop oficial: shop.fcsb.ro\n\n"
            f"Suntem unul dintre ei. Haide FCSB! 🔥"
        )
        await update.message.reply_text(welcome)

# ── Detectare mesaje vulgare ───────────────────────────────────────
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    user = update.message.from_user
    user_id = user.id
    chat_id = update.message.chat_id
    name = user.first_name

    # Verifica cuvinte interzise
    found_bad = any(word in text for word in BAD_WORDS)

    # Verifica linkuri spam (non-FCSB)
    has_link = bool(re.search(r'http[s]?://|www\.|t\.me/', text))
    fcsb_links = ['shop.fcsb.ro', 'fcsb.ro', 't.me/ComunitateaFCSB',
                  'whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46']
    is_fcsb_link = any(link in text for link in fcsb_links)

    should_warn = found_bad or (has_link and not is_fcsb_link)

    if should_warn:
        await update.message.delete()

        if user_id not in warnings:
            warnings[user_id] = 0
        warnings[user_id] += 1
        count = warnings[user_id]

        if count == 1:
            msg = (
                f"⚠️ {name}, mesajul tău a fost șters.\n"
                f"Limbaj nepotrivit sau spam nu sunt tolerate!\n"
                f"Avertisment 1/3 — mai ai 2 șanse."
            )
            await context.bot.send_message(chat_id, msg)

        elif count == 2:
            msg = (
                f"⚠️ {name}, al doilea avertisment!\n"
                f"Avertisment 2/3 — urmează banul permanent!"
            )
            await context.bot.send_message(chat_id, msg)

        elif count >= 3:
            await context.bot.ban_chat_member(chat_id, user_id)
            msg = (
                f"🚫 {name} a fost eliminat din comunitate.\n"
                f"3 avertismente = ban permanent. Regulile există pentru toți. 🔴🔵"
            )
            await context.bot.send_message(chat_id, msg)
            del warnings[user_id]

# ── Comanda /reguli ────────────────────────────────────────────────
async def reguli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📌 REGULILE COMUNITĂȚII FCSB 🔴🔵\n\n"
        "1️⃣ Respect pentru toți membrii. Zero toleranță pentru insulte.\n"
        "2️⃣ Zero spam sau reclame nesolicitate. Ban imediat.\n"
        "3️⃣ Discuțiile sunt despre FCSB. Off-topic excesiv nu e permis.\n"
        "4️⃣ Știrile false sau provocările sunt șterse automat.\n"
        "5️⃣ Adminii au ultimul cuvânt în orice dispută.\n\n"
        "⚠️ Avertisment 1 — mesaj șters\n"
        "⚠️ Avertisment 2 — mute temporar\n"
        "⚠️ Avertisment 3 — ban permanent\n\n"
        "Hai să păstrăm cea mai tare comunitate de fani FCSB! 💪🔴🔵"
    )
    await update.message.reply_text(text)

# ── Comanda /top ───────────────────────────────────────────────────
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🏆 TOPUL FANILOR ACTIVI 🔴🔵\n\n"
        "Sistemul de puncte este activ!\n"
        "Cu cât ești mai activ în comunitate,\n"
        "cu atât urci în clasament.\n\n"
        "⭐ Nivel 1 — Fan Nou (0 pct)\n"
        "🔵 Nivel 2 — Fan Albastru (100 pct)\n"
        "🔴 Nivel 3 — Fan Roșu (500 pct)\n"
        "🔴🔵 Nivel 4 — Fan FCSB (1000 pct)\n"
        "🏆 Nivel 5 — Legendă Roșalbastră (2500 pct)\n\n"
        "Membrii de Nivel 5 au prioritate la bilete și premii! 🎟️"
    )
    await update.message.reply_text(text)

# ── Comanda /avertismente (doar admini) ───────────────────────────
async def check_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Folosește: /avertismente @username")
        return
    await update.message.reply_text(
        f"Sistem de avertismente activ. Folosește /ban @username pentru ban manual."
    )

# ── Comanda /start ─────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔴🔵 FCSB Admin Bot activ!\n\n"
        "Comenzi disponibile:\n"
        "/reguli — Regulile comunității\n"
        "/top — Topul fanilor activi\n\n"
        "Haide FCSB! 🔥"
    )

# ── Main ───────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reguli", reguli))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("avertismente", check_warnings))

    logger.info("FCSB Admin Bot pornit!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
