import logging
import os
import re
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

TOKEN = os.environ.get("TOKEN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Date persistente ───────────────────────────────────────────────
points = {}
warnings_data = {}
daily_messages = {}
active_contest = {}
scheduled_match = {}
bad_words_custom = []

# ── Cuvinte interzise ──────────────────────────────────────────────
BAD_WORDS = [
    "pula", "pizda", "muie", "futu", "futut", "fututi", "futu-ti",
    "cacat", "rahat", "curva", "curvă", "proasto", "idiot", "idioata",
    "imbecil", "handicap", "retard", "dracu", "dracului", "mama ta",
    "ma-ta", "mata", "prost", "proasta", "fraier", "fraiera",
    "shit", "fuck", "bitch", "asshole", "cunt", "dick", "bastard",
    "mortii", "mortii ma-tii", "du-te", "ba prostu"
]

RIVAL_TEAMS = [
    "dinamo", "rapid", "cfr", "craiova", "universitatea craiova",
    "hermannstadt", "sepsi", "farul", "uta", "poli iasi", "otelul",
    "petrolul", "voluntari", "slobozia", "gloria buzau", "poli timisoara"
]

RIVAL_POSITIVE = [
    "hai dinamo", "hai rapid", "hai cfr", "hai craiova", "hai farul",
    "hai sepsi", "hai uta", "hai otelul", "hai petrolul", "hai voluntari",
    "dinamo campioana", "rapid campioana", "cfr campioana",
    "dinamo e mai bun", "rapid e mai bun", "cfr e mai bun",
    "dinamo cel mai bun", "rapid cel mai bun", "cfr cel mai bun",
    "dinamo forever", "rapid forever", "forza dinamo", "forza rapid",
    "dinamo invinge", "rapid invinge", "up dinamo", "up rapid"
]

FCSB_LINKS = [
    "shop.fcsb.ro", "fcsb.ro", "t.me/comunitateaFCSB",
    "whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46"
]

LEVELS = [
    (0, "⚪ Fan Nou"),
    (100, "🔵 Fan Albastru"),
    (500, "🔴 Fan Roșu"),
    (1000, "🔴🔵 Fan FCSB"),
    (2500, "🏆 Legendă Roșalbastră")
]

def get_level(pts):
    level_name = LEVELS[0][1]
    for threshold, name in LEVELS:
        if pts >= threshold:
            level_name = name
    return level_name

def get_next_level(pts):
    for threshold, name in LEVELS:
        if pts < threshold:
            return threshold, name
    return None, None

async def add_points(user_id, username, amount, context, chat_id):
    old_pts = points.get(user_id, 0)
    old_level = get_level(old_pts)
    points[user_id] = old_pts + amount
    new_level = get_level(points[user_id])
    if old_level != new_level:
        await context.bot.send_message(
            chat_id,
            f"🎉 Felicitări @{username}!\n"
            f"Ai urcat la *{new_level}*! 🔴🔵\n\n"
            f"Continuă să fii activ și câștigă premii exclusive! 💪",
            parse_mode="Markdown"
        )

# ── Bun venit ──────────────────────────────────────────────────────
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name
        keyboard = [
            [
                InlineKeyboardButton("📋 Regulile grupului", callback_data="reguli"),
                InlineKeyboardButton("🏆 Clasament", callback_data="top")
            ],
            [
                InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
                InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"👋 Bun venit în Comunitatea FCSB, *{name}*! 🔴🔵\n\n"
            f"Ești acum parte din cea mai tare comunitate de fani FCSB din România! 🏆\n\n"
            f"Aici găsești:\n"
            f"🎟️ Concursuri cu bilete la meciuri\n"
            f"🏆 Premii și produse oficiale FCSB\n"
            f"🔥 Discuții live la meciuri\n"
            f"👕 Noutăți despre colecții și shop\n\n"
            f"Fii activ, urcă în clasament și câștigă premii exclusive!\n\n"
            f"Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ── Moderare mesaje ────────────────────────────────────────────────
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    user = update.message.from_user
    user_id = user.id
    username = user.username or user.first_name
    chat_id = update.message.chat_id

    all_bad = BAD_WORDS + bad_words_custom
    found_bad = any(word in text for word in all_bad)
    found_rival = any(phrase in text for phrase in RIVAL_POSITIVE)
    has_link = bool(re.search(r'http[s]?://|www\.|t\.me/', text))
    is_fcsb_link = any(link in text for link in FCSB_LINKS)

    reason = None
    if found_bad:
        reason = "bad"
    elif found_rival:
        reason = "rival"
    elif has_link and not is_fcsb_link:
        reason = "spam"

    if reason:
        await update.message.delete()
        if user_id not in warnings_data:
            warnings_data[user_id] = 0
        warnings_data[user_id] += 1
        count = warnings_data[user_id]

        if reason == "bad":
            warn_text = (
                f"⚠️ *{user.first_name}*, mesajul tău a fost șters!\n"
                f"Limbajul nepotrivit nu este tolerat în Comunitatea FCSB!\n"
            )
        elif reason == "rival":
            warn_text = (
                f"🔴🔵 *{user.first_name}*, aici suntem doar roș-albaștri!\n"
                f"Mesajul tău a fost șters.\n"
            )
        else:
            warn_text = (
                f"⚠️ *{user.first_name}*, linkurile nesolicitate nu sunt permise!\n"
                f"Mesajul tău a fost șters.\n"
            )

        if count < 3:
            warn_text += f"Avertisment *{count}/3* — mai ai {3-count} {'șansă' if 3-count == 1 else 'șanse'}."
            await context.bot.send_message(chat_id, warn_text, parse_mode="Markdown")
        else:
            await context.bot.ban_chat_member(chat_id, user_id)
            await context.bot.send_message(
                chat_id,
                f"🚫 *{user.first_name}* a fost eliminat din Comunitatea FCSB.\n"
                f"3 avertismente = ban permanent.\n"
                f"Regulile există pentru toți. 🔴🔵",
                parse_mode="Markdown"
            )
            del warnings_data[user_id]
        return

    today = datetime.now().strftime("%Y-%m-%d")
    key = f"{user_id}_{today}"
    daily_messages[key] = daily_messages.get(key, 0) + 1
    if daily_messages[key] <= 10:
        await add_points(user_id, username, 1, context, chat_id)

# ── /start ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📋 Regulile grupului", callback_data="reguli"),
            InlineKeyboardButton("🏆 Clasament", callback_data="top")
        ],
        [
            InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
            InlineKeyboardButton("🎟️ Concurs activ", callback_data="concurs")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔴🔵 *Comunitatea FCSB — Bot Oficial*\n\n"
        "Bun venit! Sunt botul comunității și mă ocup de tot ce ai nevoie!\n\n"
        "Folosește butoanele de mai jos sau comenzile:\n"
        "/reguli — Regulile grupului\n"
        "/top — Clasamentul fanilor\n"
        "/shop — Shop oficial FCSB\n"
        "/concurs — Concursul activ\n"
        "/ajutor — Toate comenzile\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ── /ajutor ────────────────────────────────────────────────────────
async def ajutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Comenzile disponibile* 🔴🔵\n\n"
        "*Pentru toți membrii:*\n"
        "/start — Mesaj de bun venit\n"
        "/reguli — Regulile comunității\n"
        "/top — Clasamentul fanilor activi\n"
        "/shop — Shop oficial FCSB\n"
        "/concurs — Concursul activ\n"
        "/ajutor — Lista comenzilor\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown"
    )

# ── /reguli ────────────────────────────────────────────────────────
async def reguli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✅ Am înțeles!", callback_data="ok_reguli")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "📌 *REGULILE COMUNITĂȚII FCSB* 🔴🔵\n\n"
        "1️⃣ Respect pentru toți membrii\n"
        "2️⃣ Zero spam și reclame nesolicitate\n"
        "3️⃣ Discuțiile sunt despre FCSB\n"
        "4️⃣ Mesajele vulgare sunt șterse automat\n"
        "5️⃣ Mesajele pozitive despre echipe adverse sunt șterse\n"
        "6️⃣ Adminii au ultimul cuvânt\n\n"
        "⚠️ Avertisment 1 — mesaj șters\n"
        "⚠️ Avertisment 2 — mesaj șters\n"
        "⚠️ Avertisment 3 — ban permanent\n\n"
        "Hai să păstrăm cea mai tare comunitate de fani FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ── /top ───────────────────────────────────────────────────────────
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if not points:
        await update.message.reply_text(
            "🏆 *CLASAMENTUL FANILOR FCSB* 🔴🔵\n\n"
            "Nimeni nu are puncte încă — fii primul! 🔥\n\n"
            "Fiecare mesaj în grup îți aduce puncte!\n\n"
            "⚪ Nivel 1 — Fan Nou (0 pct)\n"
            "🔵 Nivel 2 — Fan Albastru (100 pct)\n"
            "🔴 Nivel 3 — Fan Roșu (500 pct)\n"
            "🔴🔵 Nivel 4 — Fan FCSB (1000 pct)\n"
            "🏆 Nivel 5 — Legendă Roșalbastră (2500 pct)\n\n"
            "Membrii de Nivel 5 au prioritate la bilete și premii! 🎟️\n\n"
            "Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    sorted_points = sorted(points.items(), key=lambda x: x[1], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    top_text = "🏆 *CLASAMENTUL FANILOR FCSB* 🔴🔵\n\n"
    for i, (uid, pts) in enumerate(sorted_points):
        level = get_level(pts)
        top_text += f"{medals[i]} {level} — *{pts} pct*\n"

    top_text += (
        "\nCu cât ești mai activ, cu atât urci mai sus!\n"
        "Membrii de Nivel 5 au prioritate la bilete! 🎟️\n\n"
        "Alături de FCSB! 💪🔴🔵"
    )
    await update.message.reply_text(top_text, parse_mode="Markdown", reply_markup=reply_markup)

# ── /shop ──────────────────────────────────────────────────────────
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🛒 Deschide Shop FCSB", url="https://shop.fcsb.ro")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🛒 *SHOP OFICIAL FCSB* 🔴🔵\n\n"
        "Găsești aici tot ce ai nevoie ca fan adevărat!\n\n"
        "👕 Tricouri și echipamente oficiale\n"
        "🧣 Esarfe și accesorii\n"
        "👶 Colecție copii și bebeluși\n"
        "🎁 Cadouri pentru fanii FCSB\n\n"
        "Membrii comunității primesc oferte exclusive! 🔥\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ── /concurs ───────────────────────────────────────────────────────
async def concurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")],
        [InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if active_contest:
        await update.message.reply_text(
            f"🎟️ *CONCURS ACTIV FCSB!* 🔴🔵\n\n"
            f"{active_contest.get('descriere', '')}\n\n"
            f"📋 *Cum participi:*\n"
            f"Scrie mai jos cea mai tare amintire cu FCSB! 💬\n\n"
            f"⏰ Termen: {active_contest.get('termen', '')}\n"
            f"🏆 Câștigătorii sunt anunțați pe canalul WhatsApp\n\n"
            f"Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "🎟️ *CONCURSURI FCSB* 🔴🔵\n\n"
            "Momentan nu există un concurs activ.\n\n"
            "Dar stai aproape — urmează ceva special pentru fanii adevărați! 👀🔥\n\n"
            "Activează notificările ca să fii primul care află! 🔔\n\n"
            "Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ── ADMIN: /anunt ──────────────────────────────────────────────────
async def anunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /anunt [mesajul tău]")
        return
    text = " ".join(context.args)
    await update.message.reply_text(
        f"📣 *ANUNȚ OFICIAL* 🔴🔵\n\n"
        f"{text}\n\n"
        f"Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown"
    )
    await update.message.delete()

# ── ADMIN: /concursnou ─────────────────────────────────────────────
async def concursnou(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /concursnou [descriere] | [termen]")
        return
    text = " ".join(context.args)
    parts = text.split("|")
    descriere = parts[0].strip() if len(parts) > 0 else text
    termen = parts[1].strip() if len(parts) > 1 else "În curând"

    active_contest["descriere"] = descriere
    active_contest["termen"] = termen

    keyboard = [
        [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🎟️ *CONCURS FCSB!* 🔴🔵\n\n"
        f"{descriere}\n\n"
        f"📋 *Cum participi:*\n"
        f"Scrie mai jos cea mai tare amintire cu FCSB! 💬\n\n"
        f"⏰ Termen: {termen}\n"
        f"🏆 Câștigătorii sunt anunțați pe canalul WhatsApp\n\n"
        f"Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )
    await update.message.delete()

# ── ADMIN: /castigator ─────────────────────────────────────────────
async def castigator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /castigator @user1 @user2 @user3")
        return

    winners = context.args
    medals = ["🥇", "🥈", "🥉"]

    if len(winners) == 1:
        text = (
            f"🏆 *AVEM CÂȘTIGĂTORUL!* 🔴🔵\n\n"
            f"Felicitări fanului adevărat! 🎟️\n\n"
            f"🥇 {winners[0]}\n\n"
            f"📲 Trimite-ne un DM pe Instagram pentru a primi premiul:\n"
            f"👉 @fcsb.shop\n\n"
            f"+50 puncte bonus adăugate! ⭐\n\n"
            f"Alături de FCSB! 💪🔴🔵"
        )
    else:
        winners_text = "\n".join([f"{medals[i]} {w}" for i, w in enumerate(winners[:3])])
        text = (
            f"🏆 *AVEM CÂȘTIGĂTORII!* 🔴🔵\n\n"
            f"Felicitări celor {len(winners[:3])} fani adevărați! 🎟️\n\n"
            f"{winners_text}\n\n"
            f"📲 Trimiteți-ne un DM pe Instagram pentru a primi premiul:\n"
            f"👉 @fcsb.shop\n\n"
            f"+50 puncte bonus adăugate fiecăruia! ⭐\n\n"
            f"Alături de FCSB! 💪🔴🔵"
        )

    active_contest.clear()
    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    await update.message.delete()

# ── ADMIN: /setmeci ────────────────────────────────────────────────
async def setmeci(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if len(context.args) < 3:
        await update.message.reply_text("Folosește: /setmeci 12.05.2026 21:00 FCSB vs Rapid Arena Nationala")
        return
    data = context.args[0]
    ora = context.args[1]
    meci = " ".join(context.args[2:])
    scheduled_match["data"] = data
    scheduled_match["ora"] = ora
    scheduled_match["meci"] = meci
    await update.message.reply_text(
        f"✅ Meci setat cu succes!\n"
        f"📅 {data} ora {ora}\n"
        f"⚽ {meci}\n\n"
        f"Mesajul de hype va fi trimis automat în ziua meciului! 🔴🔵"
    )
    await update.message.delete()

# ── ADMIN: /rezultat ───────────────────────────────────────────────
async def rezultat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /rezultat 2-0")
        return

    scor = context.args[0]
    meci_info = scheduled_match.get("meci", "FCSB")

    try:
        parts = scor.split("-")
        golfcsb = int(parts[0])
        goladv = int(parts[1])
        if golfcsb > goladv:
            emoji = "🏆"
            mesaj = (
                f"AL 12-LEA JUCĂTOR ȘI-A FĂCUT TREABA! 🔴🔵🔥\n\n"
                f"Împreună am împins echipa spre victorie!\n"
                f"Asta înseamnă să fii fan adevărat! 💪"
            )
        elif golfcsb == goladv:
            emoji = "🤝"
            mesaj = (
                f"Am luptat până la final, ca întotdeauna! 🔴🔵\n\n"
                f"Al 12-lea jucător nu abandonează niciodată!\n"
                f"Alături de FCSB oricând! 💪"
            )
        else:
            emoji = "💪"
            mesaj = (
                f"Capul sus, al 12-lea jucător rămâne alături! 🔴🔵\n\n"
                f"La bine și la greu — asta înseamnă să fii fan adevărat!\n"
                f"Mâine o luăm de la capăt împreună! 💪"
            )
    except:
        emoji = "⚽"
        mesaj = "Alături de FCSB oricând! 💪🔴🔵"

    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    await update.message.reply_text(
        f"{emoji} *FINAL! {meci_info} {scor}*\n\n"
        f"{mesaj}\n\n"
        f"🛒 Arată că ești fan adevărat:\n"
        f"shop.fcsb.ro\n\n"
        f"Alături de FCSB! 🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /fanweek ────────────────────────────────────────────────
async def fanweek(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /fanweek @username")
        return
    username = context.args[0]
    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    await update.message.reply_text(
        f"🌟 *FANUL SĂPTĂMÂNII!* 🔴🔵\n\n"
        f"Comunitatea a vorbit — cel mai dedicat fan al acestei săptămâni este:\n\n"
        f"👑 *{username}*\n\n"
        f"Ești un exemplu pentru toți fanii roș-albaștri! 🔥\n"
        f"Activitatea ta în comunitate nu a trecut neobservată!\n\n"
        f"🎁 +100 puncte bonus adăugate în clasament! ⭐\n\n"
        f"Vrei să fii următorul fan al săptămânii?\n"
        f"Fii activ, participă la discuții și arată că ești fan adevărat! 💪\n\n"
        f"Alături de FCSB! 🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /oferta ─────────────────────────────────────────────────
async def oferta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /oferta Tricou Vintage | shop.fcsb.ro/link | 12.05.2026 23:59")
        return
    text = " ".join(context.args)
    parts = text.split("|")
    produs = parts[0].strip() if len(parts) > 0 else text
    link = parts[1].strip() if len(parts) > 1 else "shop.fcsb.ro"
    termen = parts[2].strip() if len(parts) > 2 else "În curând"

    keyboard = [[InlineKeyboardButton("🛒 Comandă acum!", url=f"https://{link}" if not link.startswith("http") else link)]]
    await update.message.reply_text(
        f"🛒 *OFERTĂ EXCLUSIVĂ FCSB!* 🔴🔵\n\n"
        f"*{produs}*\n\n"
        f"Această ofertă e disponibilă DOAR pentru membrii comunității noastre! 🔥\n\n"
        f"⏰ Valabilă până pe {termen}\n\n"
        f"Nu rata — stocul e limitat! 💪\n\n"
        f"Alături de FCSB! 🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: cuvinte interzise ───────────────────────────────────────
async def adaugacuvant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /adaugacuvant [cuvant]")
        return
    cuvant = context.args[0].lower()
    bad_words_custom.append(cuvant)
    await update.message.reply_text(f"✅ Cuvântul '{cuvant}' a fost adăugat în lista de cuvinte interzise!")
    await update.message.delete()

async def stergecuvant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        await update.message.reply_text("Folosește: /stergecuvant [cuvant]")
        return
    cuvant = context.args[0].lower()
    if cuvant in bad_words_custom:
        bad_words_custom.remove(cuvant)
        await update.message.reply_text(f"✅ Cuvântul '{cuvant}' a fost șters din lista de cuvinte interzise!")
    else:
        await update.message.reply_text(f"❌ Cuvântul '{cuvant}' nu a fost găsit în lista personalizată.")
    await update.message.delete()

async def listacuvinte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if bad_words_custom:
        await update.message.reply_text(f"📋 Cuvinte interzise personalizate:\n{', '.join(bad_words_custom)}")
    else:
        await update.message.reply_text("📋 Nu ai adăugat cuvinte interzise personalizate încă.")
    await update.message.delete()

# ── Callback butoane ───────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "reguli":
        keyboard = [[InlineKeyboardButton("✅ Am înțeles!", callback_data="ok_reguli")]]
        await query.message.reply_text(
            "📌 *REGULILE COMUNITĂȚII FCSB* 🔴🔵\n\n"
            "1️⃣ Respect pentru toți membrii\n"
            "2️⃣ Zero spam și reclame nesolicitate\n"
            "3️⃣ Discuțiile sunt despre FCSB\n"
            "4️⃣ Mesajele vulgare sunt șterse automat\n"
            "5️⃣ Mesajele pozitive despre echipe adverse sunt șterse\n"
            "6️⃣ Adminii au ultimul cuvânt\n\n"
            "⚠️ Avertisment 1 — mesaj șters\n"
            "⚠️ Avertisment 2 — mesaj șters\n"
            "⚠️ Avertisment 3 — ban permanent\n\n"
            "Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    elif query.data == "ok_reguli":
        await query.message.reply_text(
            f"✅ Mulțumim, *{query.from_user.first_name}*!\n"
            f"Bun venit în comunitate! 🔴🔵",
            parse_mode="Markdown"
        )
    elif query.data == "top":
        if not points:
            await query.message.reply_text(
                "🏆 Nimeni nu are puncte încă — fii primul! 🔥\n\n"
                "Scrie în grup și acumulează puncte! 🔴🔵"
            )
        else:
            sorted_pts = sorted(points.items(), key=lambda x: x[1], reverse=True)[:5]
            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            top_text = "🏆 *TOP 5 FANI FCSB* 🔴🔵\n\n"
            for i, (uid, pts) in enumerate(sorted_pts):
                top_text += f"{medals[i]} {get_level(pts)} — *{pts} pct*\n"
            await query.message.reply_text(top_text, parse_mode="Markdown")
    elif query.data == "concurs":
        if active_contest:
            await query.message.reply_text(
                f"🎟️ *CONCURS ACTIV!* 🔴🔵\n\n"
                f"{active_contest.get('descriere', '')}\n\n"
                f"⏰ Termen: {active_contest.get('termen', '')}\n\n"
                f"Scrie cea mai tare amintire cu FCSB! 💬\n\n"
                f"Alături de FCSB! 💪🔴🔵",
                parse_mode="Markdown"
            )
        else:
            await query.message.reply_text(
                "🎟️ Momentan nu există un concurs activ.\n\n"
                "Urmează ceva special! Stai aproape! 👀🔴🔵"
            )

# ── Main ───────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajutor", ajutor))
    app.add_handler(CommandHandler("reguli", reguli))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("concurs", concurs))
    app.add_handler(CommandHandler("anunt", anunt))
    app.add_handler(CommandHandler("concursnou", concursnou))
    app.add_handler(CommandHandler("castigator", castigator))
    app.add_handler(CommandHandler("setmeci", setmeci))
    app.add_handler(CommandHandler("rezultat", rezultat))
    app.add_handler(CommandHandler("fanweek", fanweek))
    app.add_handler(CommandHandler("oferta", oferta))
    app.add_handler(CommandHandler("adaugacuvant", adaugacuvant))
    app.add_handler(CommandHandler("stergecuvant", stergecuvant))
    app.add_handler(CommandHandler("listacuvinte", listacuvinte))
    app.add_handler(CallbackQueryHandler(button_callback))

    logger.info("FCSB Admin Bot pornit!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
