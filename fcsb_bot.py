import logging
import os
import re
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

TOKEN = os.environ.get("TOKEN", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

warnings_data = {}
active_contest = {}
scheduled_match = {}
bad_words_custom = []

BAD_WORDS = [
    "pula", "pizda", "muie", "futu", "futut", "fututi", "futu-ti",
    "cacat", "rahat", "curva", "curvă", "proasto", "idiot", "idioata",
    "imbecil", "handicap", "retard", "dracu", "dracului", "mama ta",
    "ma-ta", "mata", "prost", "proasta", "fraier", "fraiera",
    "shit", "fuck", "bitch", "asshole", "cunt", "dick", "bastard",
    "mortii", "mortii ma-tii", "ba prostu"
]

RIVAL_POSITIVE = [
    "hai dinamo", "hai rapid", "hai cfr", "hai craiova", "hai farul",
    "hai sepsi", "hai uta", "hai otelul", "hai petrolul", "hai voluntari",
    "hai hermannstadt", "hai poli", "hai slobozia", "hai buzau",
    "dinamo campioana", "rapid campioana", "cfr campioana",
    "dinamo e mai bun", "rapid e mai bun", "cfr e mai bun",
    "dinamo cel mai bun", "rapid cel mai bun", "cfr cel mai bun",
    "dinamo forever", "rapid forever", "forza dinamo", "forza rapid",
    "dinamo invinge", "rapid invinge", "up dinamo", "up rapid"
]

FCSB_LINKS = [
    "shop.fcsb.ro", "fcsb.ro", "t.me/comunitateaFCSB",
    "whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46",
    "instagram.com/fcsb.shop", "tiktok.com/@fcsb.shop",
    "facebook.com/p/FCSB-Shop"
]

SOCIAL_BUTTONS = [
    [
        InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/fcsb.shop/"),
        InlineKeyboardButton("🎵 TikTok", url="https://www.tiktok.com/@fcsb.shop"),
    ],
    [
        InlineKeyboardButton("👥 Facebook", url="https://www.facebook.com/p/FCSB-Shop-Oficial-61557942045101/"),
        InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
    ],
    [
        InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")
    ]
]

async def delete_after(message, seconds=30):
    await asyncio.sleep(seconds)
    try:
        await message.delete()
    except:
        pass

# ── Bun venit ──────────────────────────────────────────────────────
async def new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        if member.is_bot:
            continue
        name = member.first_name
        keyboard = [
            [
                InlineKeyboardButton("📋 Regulile grupului", callback_data="reguli"),
                InlineKeyboardButton("🎟️ Concurs activ", callback_data="concurs")
            ],
            [
                InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
                InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")
            ]
        ]
        msg = await update.message.reply_text(
            f"👋 Bun venit în *Comunitatea FCSB*, {name}! 🔴🔵\n\n"
            f"Ești acum parte din cea mai tare comunitate de fani FCSB din România! 🏆\n\n"
            f"Aici găsești:\n"
            f"🎟️ Concursuri cu bilete la meciuri\n"
            f"🏆 Premii și produse oficiale FCSB\n"
            f"🔥 Discuții live la meciuri\n"
            f"👕 Noutăți despre colecții și shop\n\n"
            f"Alături de FCSB! 💪🔴🔵",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        asyncio.create_task(delete_after(msg, 30))
        try:
            await update.message.delete()
        except:
            pass

# ── Moderare ───────────────────────────────────────────────────────
async def check_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower()
    user = update.message.from_user
    user_id = user.id
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
            msg = await context.bot.send_message(chat_id, warn_text, parse_mode="Markdown")
            asyncio.create_task(delete_after(msg, 30))
        else:
            await context.bot.ban_chat_member(chat_id, user_id)
            msg = await context.bot.send_message(
                chat_id,
                f"🚫 *{user.first_name}* a fost eliminat din Comunitatea FCSB.\n"
                f"3 avertismente = ban permanent.\n"
                f"Regulile există pentru toți. 🔴🔵",
                parse_mode="Markdown"
            )
            asyncio.create_task(delete_after(msg, 30))
            del warnings_data[user_id]
        return

    if "concurs" in text and not text.startswith("/"):
        keyboard = [
            [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")],
            [InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]
        ]
        if active_contest:
            reply_text = (
                f"🎟️ *CONCURS ACTIV FCSB!* 🔴🔵\n\n"
                f"{active_contest.get('descriere', '')}\n\n"
                f"⏰ Termen: {active_contest.get('termen', '')}\n\n"
                f"Scrie cea mai tare amintire cu FCSB! 💬\n\nAlături de FCSB! 💪🔴🔵"
            )
        else:
            reply_text = (
                "🎟️ *CONCURSURI FCSB* 🔴🔵\n\n"
                "Momentan nu există un concurs activ.\n\n"
                "Stai aproape — urmează ceva special! 👀🔥\n\n"
                "Alături de FCSB! 💪🔴🔵"
            )
        msg = await update.message.reply_text(reply_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after(msg, 30))

# ── /start ─────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📋 Regulile grupului", callback_data="reguli"),
            InlineKeyboardButton("🎟️ Concurs activ", callback_data="concurs")
        ],
        [
            InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
            InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")
        ]
    ]
    msg = await update.message.reply_text(
        "🔴🔵 *Comunitatea FCSB — Bot Oficial*\n\n"
        "Comenzi disponibile:\n"
        "/reguli — Regulile grupului\n"
        "/shop — Shop oficial FCSB\n"
        "/concurs — Concursul activ\n"
        "/social — Urmărește-ne pe social media\n"
        "/ajutor — Toate comenzile\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── /ajutor ────────────────────────────────────────────────────────
async def ajutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "📋 *Comenzile disponibile* 🔴🔵\n\n"
        "/start — Mesaj de bun venit\n"
        "/reguli — Regulile comunității\n"
        "/shop — Shop oficial FCSB\n"
        "/concurs — Concursul activ\n"
        "/social — Urmărește-ne pe social media\n"
        "/ajutor — Lista comenzilor\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown"
    )
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── /reguli ────────────────────────────────────────────────────────
async def reguli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✅ Am înțeles!", callback_data="ok_reguli")]]
    msg = await update.message.reply_text(
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
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── /shop ──────────────────────────────────────────────────────────
async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 Deschide Shop FCSB", url="https://shop.fcsb.ro")],
        [
            InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/fcsb.shop/"),
            InlineKeyboardButton("🎵 TikTok", url="https://www.tiktok.com/@fcsb.shop")
        ]
    ]
    msg = await update.message.reply_text(
        "🛒 *SHOP OFICIAL FCSB* 🔴🔵\n\n"
        "Găsești aici tot ce ai nevoie ca fan adevărat!\n\n"
        "👕 Tricouri și echipamente oficiale\n"
        "🧣 Esarfe și accesorii\n"
        "👶 Colecție copii și bebeluși\n"
        "🎁 Cadouri pentru fanii FCSB\n\n"
        "Membrii comunității primesc oferte exclusive! 🔥\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── /social ────────────────────────────────────────────────────────
async def social(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = await update.message.reply_text(
        "📱 *URMĂREȘTE FCSB SHOP* 🔴🔵\n\n"
        "Fii primul care află noutăți, oferte și surprize!\n\n"
        "📸 Instagram: @fcsb.shop\n"
        "🎵 TikTok: @fcsb.shop\n"
        "👥 Facebook: FCSB Shop Oficial\n"
        "🛒 Shop: shop.fcsb.ro\n"
        "📲 WhatsApp: Comunitatea FCSB\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(SOCIAL_BUTTONS)
    )
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── /concurs ───────────────────────────────────────────────────────
async def concurs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")],
        [InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]
    ]
    if active_contest:
        text = (
            f"🎟️ *CONCURS ACTIV FCSB!* 🔴🔵\n\n"
            f"{active_contest.get('descriere', '')}\n\n"
            f"📋 *Cum participi:*\n"
            f"Scrie mai jos cea mai tare amintire cu FCSB! 💬\n\n"
            f"⏰ Termen: {active_contest.get('termen', '')}\n"
            f"🏆 Câștigătorii sunt anunțați pe canalul WhatsApp\n\n"
            f"Alături de FCSB! 💪🔴🔵"
        )
    else:
        text = (
            "🎟️ *CONCURSURI FCSB* 🔴🔵\n\n"
            "Momentan nu există un concurs activ.\n\n"
            "Stai aproape — urmează ceva special pentru fanii adevărați! 👀🔥\n\n"
            "Activează notificările ca să fii primul care află! 🔔\n\n"
            "Alături de FCSB! 💪🔴🔵"
        )
    msg = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    asyncio.create_task(delete_after(update.message, 5))
    asyncio.create_task(delete_after(msg, 30))

# ── ADMIN: /welcome ────────────────────────────────────────────────
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    keyboard = [
        [
            InlineKeyboardButton("📋 Regulile grupului", callback_data="reguli"),
            InlineKeyboardButton("🎟️ Concurs activ", callback_data="concurs")
        ],
        [
            InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro"),
            InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")
        ],
        [
            InlineKeyboardButton("📸 Instagram", url="https://www.instagram.com/fcsb.shop/"),
            InlineKeyboardButton("🎵 TikTok", url="https://www.tiktok.com/@fcsb.shop"),
            InlineKeyboardButton("👥 Facebook", url="https://www.facebook.com/p/FCSB-Shop-Oficial-61557942045101/")
        ]
    ]
    await context.bot.send_message(
        update.message.chat_id,
        "👋 Bun venit în *Comunitatea FCSB!* 🔴🔵\n\n"
        "Ești acum parte din cea mai tare comunitate de fani FCSB din România! 🏆\n\n"
        "📌 *Înainte să scrii, citește regulile!*\n\n"
        "Aici câștigi:\n"
        "🎟️ Bilete la meciuri prin concursuri exclusive\n"
        "🏆 Premii și produse oficiale FCSB\n\n"
        "Urmărește-ne pe toate platformele 👇\n\n"
        "Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /anunt ──────────────────────────────────────────────────
async def anunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        return
    text = " ".join(context.args)
    await context.bot.send_message(
        update.message.chat_id,
        f"📣 *ANUNȚ OFICIAL* 🔴🔵\n\n{text}\n\nAlături de FCSB! 💪🔴🔵",
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
        return
    text = " ".join(context.args)
    parts = text.split("|")
    descriere = parts[0].strip()
    termen = parts[1].strip() if len(parts) > 1 else "În curând"
    active_contest["descriere"] = descriere
    active_contest["termen"] = termen
    keyboard = [
        [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")],
        [InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]
    ]
    await context.bot.send_message(
        update.message.chat_id,
        f"🎟️ *CONCURS FCSB!* 🔴🔵\n\n"
        f"{descriere}\n\n"
        f"📋 *Cum participi:*\n"
        f"Scrie mai jos cea mai tare amintire cu FCSB! 💬\n\n"
        f"⏰ Termen: {termen}\n"
        f"🏆 Câștigătorii sunt anunțați pe canalul WhatsApp\n\n"
        f"Alături de FCSB! 💪🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /castigator ─────────────────────────────────────────────
async def castigator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        return
    text = " ".join(context.args)
    winners = [w.strip() for w in text.split("|")][:3]
    medals = ["🥇", "🥈", "🥉"]
    if len(winners) == 1:
        text = (
            f"🏆 *AVEM CÂȘTIGĂTORUL!* 🔴🔵\n\n"
            f"Felicitări fanului adevărat! 🎟️\n\n"
            f"🥇 {winners[0]}\n\n"
            f"📲 Contactează-ne pe Instagram pentru a primi premiul:\n"
            f"👉 @fcsb.shop\n\n"
            f"Alături de FCSB! 💪🔴🔵"
        )
    else:
        winners_text = "\n".join([f"{medals[i]} {w}" for i, w in enumerate(winners)])
        text = (
            f"🏆 *AVEM CÂȘTIGĂTORII!* 🔴🔵\n\n"
            f"Felicitări celor {len(winners)} fani adevărați! 🎟️\n\n"
            f"{winners_text}\n\n"
            f"📲 Contactați-ne pe Instagram pentru a primi premiul:\n"
            f"👉 @fcsb.shop\n\n"
            f"Alături de FCSB! 💪🔴🔵"
        )
    active_contest.clear()
    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    await context.bot.send_message(
        update.message.chat_id, text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /setmeci ────────────────────────────────────────────────
async def setmeci(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if len(context.args) < 3:
        return
    scheduled_match["data"] = context.args[0]
    scheduled_match["ora"] = context.args[1]
    scheduled_match["adversar"] = " ".join(context.args[2:])
    await context.bot.send_message(
        update.message.from_user.id,
        f"✅ Meci setat cu succes!\n"
        f"📅 {scheduled_match['data']} ora {scheduled_match['ora']}\n"
        f"⚽ FCSB vs {scheduled_match['adversar']}\n\n"
        f"Trimite /meci în ziua meciului! 🔴🔵"
    )
    await update.message.delete()

# ── ADMIN: /meci ───────────────────────────────────────────────────
async def meci(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    ora = scheduled_match.get("ora", "21:00")
    adversar = scheduled_match.get("adversar", "adversarul")
    keyboard = [[InlineKeyboardButton("🛒 Îmbracă-te roș-albastru!", url="https://shop.fcsb.ro")]]
    await context.bot.send_message(
        update.message.chat_id,
        f"🔴🔵 *AZI E ZIUA NOASTRĂ!* 🔴🔵\n\n"
        f"⚽ *FCSB vs {adversar}*\n"
        f"⏰ Ora {ora}\n\n"
        f"Pe stadion sau acasă — noi suntem *AL 12-LEA JUCĂTOR!* 💪\n\n"
        f"Vocea noastră ajunge pe teren! 🔥\n\n"
        f"👕 Îmbracă-te roș-albastru:\n"
        f"🛒 shop.fcsb.ro\n\n"
        f"Alături de FCSB! 🔴🔵",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    await update.message.delete()

# ── ADMIN: /rezultat ───────────────────────────────────────────────
async def rezultat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        return
    scor = context.args[0]
    adversar = scheduled_match.get("adversar", "adversarul")
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
    await context.bot.send_message(
        update.message.chat_id,
        f"{emoji} *FINAL! FCSB vs {adversar} {scor}*\n\n{mesaj}\n\n"
        f"🛒 Arată că ești fan adevărat:\nshop.fcsb.ro\n\nAlături de FCSB! 🔴🔵",
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
        return
    username = " ".join(context.args)
    keyboard = [[InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]]
    await context.bot.send_message(
        update.message.chat_id,
        f"🌟 *FANUL SĂPTĂMÂNII!* 🔴🔵\n\n"
        f"Cel mai dedicat fan al acestei săptămâni este:\n\n"
        f"👑 *{username}*\n\n"
        f"Ești un exemplu pentru toți fanii roș-albaștri! 🔥\n"
        f"Activitatea ta nu a trecut neobservată!\n\n"
        f"Vrei să fii următorul fan al săptămânii?\n"
        f"Fii activ și arată că ești fan adevărat! 💪\n\n"
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
        return
    text = " ".join(context.args)
    parts = text.split("|")
    produs = parts[0].strip()
    link = parts[1].strip() if len(parts) > 1 else "shop.fcsb.ro"
    termen = parts[2].strip() if len(parts) > 2 else "În curând"
    url = f"https://{link}" if not link.startswith("http") else link
    keyboard = [[InlineKeyboardButton("🛒 Comandă acum!", url=url)]]
    await context.bot.send_message(
        update.message.chat_id,
        f"🛒 *OFERTĂ EXCLUSIVĂ FCSB!* 🔴🔵\n\n"
        f"*{produs}*\n\n"
        f"Disponibilă DOAR pentru membrii comunității! 🔥\n\n"
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
        return
    cuvant = context.args[0].lower()
    bad_words_custom.append(cuvant)
    await context.bot.send_message(update.message.from_user.id, f"✅ Cuvântul '{cuvant}' adăugat!")
    await update.message.delete()

async def stergecuvant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    if not context.args:
        return
    cuvant = context.args[0].lower()
    if cuvant in bad_words_custom:
        bad_words_custom.remove(cuvant)
        await context.bot.send_message(update.message.from_user.id, f"✅ Cuvântul '{cuvant}' șters!")
    else:
        await context.bot.send_message(update.message.from_user.id, f"❌ Cuvântul '{cuvant}' nu a fost găsit.")
    await update.message.delete()

async def listacuvinte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    member = await context.bot.get_chat_member(update.message.chat_id, update.message.from_user.id)
    if member.status not in ["administrator", "creator"]:
        await update.message.delete()
        return
    text = f"📋 Cuvinte personalizate:\n{', '.join(bad_words_custom)}" if bad_words_custom else "📋 Lista personalizată e goală."
    await context.bot.send_message(update.message.from_user.id, text)
    await update.message.delete()

# ── Callback butoane ───────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "reguli":
        keyboard = [[InlineKeyboardButton("✅ Am înțeles!", callback_data="ok_reguli")]]
        msg = await query.message.reply_text(
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
        asyncio.create_task(delete_after(msg, 30))

    elif query.data == "ok_reguli":
        msg = await query.message.reply_text(
            f"✅ *{query.from_user.first_name}*, ai citit regulile!\n"
            f"Bun venit în comunitate! 🔴🔵",
            parse_mode="Markdown"
        )
        asyncio.create_task(delete_after(msg, 15))

    elif query.data == "concurs":
        keyboard = [
            [InlineKeyboardButton("📲 Canal WhatsApp", url="https://whatsapp.com/channel/0029Vb8AmMBAO7RAEYE2af46")],
            [InlineKeyboardButton("🛒 Shop oficial", url="https://shop.fcsb.ro")]
        ]
        if active_contest:
            text = (
                f"🎟️ *CONCURS ACTIV!* 🔴🔵\n\n"
                f"{active_contest.get('descriere', '')}\n\n"
                f"⏰ Termen: {active_contest.get('termen', '')}\n\n"
                f"Scrie cea mai tare amintire cu FCSB! 💬\n\nAlături de FCSB! 💪🔴🔵"
            )
        else:
            text = "🎟️ Momentan nu există un concurs activ.\n\nUrmează ceva special! Stai aproape! 👀🔴🔵"
        msg = await query.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        asyncio.create_task(delete_after(msg, 30))

# ── Main ───────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_member))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_message))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ajutor", ajutor))
    app.add_handler(CommandHandler("reguli", reguli))
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CommandHandler("social", social))
    app.add_handler(CommandHandler("concurs", concurs))
    app.add_handler(CommandHandler("welcome", welcome))
    app.add_handler(CommandHandler("anunt", anunt))
    app.add_handler(CommandHandler("concursnou", concursnou))
    app.add_handler(CommandHandler("castigator", castigator))
    app.add_handler(CommandHandler("setmeci", setmeci))
    app.add_handler(CommandHandler("meci", meci))
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
