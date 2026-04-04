#!/usr/bin/env python3
"""
MRKT Sticker Bot — Telegram bot for on-demand sticker generation.
MRKT Sticker Bot — Telegram-бот для генерации стикеров по запросу.

Commands / Команды:
  /start          — welcome / приветствие
  /sticker <slug> — sticker with current price / стикер с ценой (e.g. /sticker PlushPepe)
  /list           — list collections / список коллекций
  /price <slug>   — text price response / текстовый ответ с ценой

Setup / Запуск:
  1. pip install -r requirements.txt
  2. Create .env file / Создайте .env:
     TELEGRAM_BOT_TOKEN=your_token
     OWNER_USER_ID=your_id
  3. python bot.py
"""

import os
import io
import json
import asyncio
import logging
from datetime import datetime

import aiohttp
from PIL import Image, ImageDraw, ImageFont
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile

# ─── Load .env ────────────────────────────────────────────────────
def load_dotenv(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())

load_dotenv()

# ─── Config ───────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
GIFTSTAT_API = "https://api.giftstat.app/current/collections/floor"
BINANCE_API = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
STAR_USD = 0.015

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mrkt-bot")

if not BOT_TOKEN:
    raise SystemExit("❌ TELEGRAM_BOT_TOKEN не задан! Установите переменную окружения.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ─── Кэш данных ─────────────────────────────────────────────────
collections_cache = {}  # slug -> col data
ton_usd = 7.2
cache_ts = 0
CACHE_TTL = 30  # секунд


async def fetch_data():
    """Загружает коллекции и курс TON."""
    global collections_cache, ton_usd, cache_ts

    now = asyncio.get_event_loop().time()
    if cache_ts and now - cache_ts < CACHE_TTL:
        return

    async with aiohttp.ClientSession() as session:
        # Курс TON
        try:
            async with session.get(BINANCE_API, timeout=aiohttp.ClientTimeout(total=10)) as r:
                data = await r.json()
                ton_usd = float(data.get("price", 7.2))
        except Exception as e:
            log.warning(f"TON rate error: {e}")

        # Коллекции
        for market in ["mrkt", "fragment"]:
            try:
                url = f"{GIFTSTAT_API}?marketplace={market}&limit=500"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    data = await r.json()
                    cols = data.get("data", data) if isinstance(data, dict) else data
                    if isinstance(cols, list):
                        for col in cols:
                            slug = col.get("slug", "")
                            if slug:
                                col["_market"] = market
                                collections_cache[slug.lower()] = col
            except Exception as e:
                log.warning(f"Collections error ({market}): {e}")

    cache_ts = now
    log.info(f"Cache updated: {len(collections_cache)} collections, TON=${ton_usd:.2f}")


# ─── Генератор изображений ───────────────────────────────────────

# Размер стикера (Telegram рекомендует 512x512 для стикеров)
W, H = 512, 512
BG_COLOR = (10, 10, 10)
GOLD = (255, 208, 0)
WHITE = (255, 255, 255)
GREEN = (0, 230, 118)
RED = (255, 68, 68)
GRAY = (255, 255, 255, 70)
DARK_GRAY = (40, 40, 40)


def get_font(size, bold=False):
    """Пробуем загрузить Inter или системный шрифт."""
    for name in ["Inter-Bold.ttf", "Inter-Regular.ttf", "arial.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def generate_sticker_image(col):
    """Генерирует PNG-стикер 512x512 для коллекции."""
    slug = col.get("slug", "???")
    floor = col.get("floor_price", 0)
    supply = col.get("supply") or col.get("total_supply") or "—"
    change = col.get("change_24h") if col.get("change_24h") is not None else col.get("price_change_24h")
    market = col.get("_market", "mrkt").upper()

    usd = floor * ton_usd
    stars = int(usd / STAR_USD) if STAR_USD > 0 else 0

    img = Image.new("RGBA", (W, H), BG_COLOR + (255,))
    draw = ImageDraw.Draw(img)

    # Рамка
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=40, outline=GOLD, width=3)

    # Header: MRKT pill + LIVE badge
    font_sm = get_font(16)
    font_xs = get_font(12)
    font_lg = get_font(48)
    font_md = get_font(20)
    font_label = get_font(13)
    font_val = get_font(16)

    # MRKT pill
    draw.rounded_rectangle([16, 16, 90, 44], radius=14, outline=GOLD, width=2)
    draw.text((28, 20), "MRKT", fill=GOLD, font=font_sm)

    # LIVE badge
    draw.rounded_rectangle([W - 80, 16, W - 16, 42], radius=13, fill=GOLD)
    draw.text((W - 66, 20), "LIVE", fill=(0, 0, 0), font=font_xs)
    draw.ellipse([W - 76, 25, W - 70, 31], fill=(0, 0, 0))

    # Growth badge
    if change is not None:
        badge_color = GREEN if change >= 0 else RED
        badge_text = f"{'▲ +' if change >= 0 else '▼ '}{abs(change):.1f}%"
    else:
        badge_color = GOLD
        badge_text = "● STABLE"

    bbox = draw.textbbox((0, 0), badge_text, font=font_xs)
    bw = bbox[2] - bbox[0] + 20
    bx = W - bw - 16
    draw.rounded_rectangle([bx, 52, W - 16, 76], radius=8, outline=badge_color, width=1)
    draw.text((bx + 10, 56), badge_text, fill=badge_color, font=font_xs)

    # Центральная зона — эмодзи подарка
    gift_emoji = "🎁"
    font_gift = get_font(72)
    gbbox = draw.textbbox((0, 0), gift_emoji, font=font_gift)
    gw = gbbox[2] - gbbox[0]
    draw.text(((W - gw) // 2, 100), gift_emoji, font=font_gift, fill=WHITE)

    # Название коллекции
    label = f"{slug.upper()} — FLOOR PRICE"
    draw.text((20, 250), label, fill=(255, 255, 255, 80), font=font_label)

    # Основная цена
    price_text = f"{floor:.2f}"
    draw.text((20, 270), "TON", fill=(255, 255, 255, 120), font=font_md)
    ton_bbox = draw.textbbox((20, 270), "TON", font=font_md)
    draw.text((ton_bbox[2] + 10, 255), price_text, fill=WHITE, font=font_lg)

    # Разделитель
    draw.line([(20, 320), (W - 20, 320)], fill=(255, 255, 255, 20), width=1)

    # Нижние значения: USD | STARS | 24H | SUPPLY
    col_w = (W - 40) // 4
    stats = [
        ("USD", f"${usd:.2f}", GOLD),
        ("STARS", f"★{stars}", GOLD),
        ("24H", f"{'+' if change and change >= 0 else ''}{change:.1f}%" if change is not None else "≈ 0%",
         GREEN if change and change > 0 else RED if change and change < 0 else GOLD),
        ("SUPPLY", f"{int(supply):,}" if supply != "—" else "—", (255, 255, 255, 130)),
    ]

    for i, (label, val, color) in enumerate(stats):
        cx = 20 + col_w * i + col_w // 2
        draw.text((cx - draw.textbbox((0, 0), label, font=font_xs)[2] // 2, 335),
                  label, fill=(255, 255, 255, 70), font=font_xs)
        draw.text((cx - draw.textbbox((0, 0), val, font=font_val)[2] // 2, 352),
                  val, fill=color, font=font_val)

        # Разделители
        if i < 3:
            dx = 20 + col_w * (i + 1)
            draw.line([(dx, 335), (dx, 375)], fill=(255, 255, 255, 20), width=1)

    # Футер
    draw.rectangle([0, H - 50, W, H], fill=(17, 17, 17, 255))
    draw.line([(0, H - 50), (W, H - 50)], fill=(*GOLD, 30), width=1)
    draw.text((20, H - 40), "MRKT", fill=GOLD, font=font_sm)
    slogan_bbox = draw.textbbox((20, H - 40), "MRKT", font=font_sm)
    draw.text((slogan_bbox[2] + 6, H - 36), "- Best place to trade gifts", fill=(255, 255, 255, 140), font=font_xs)

    # Updated timestamp
    now_str = datetime.now().strftime("%d.%m.%y %H:%M")
    draw.text((W - 20 - draw.textbbox((0, 0), now_str, font=font_xs)[2], H - 22),
              now_str, fill=(*GOLD, 230), font=font_xs)
    draw.text((W - 20 - draw.textbbox((0, 0), "UPDATED", font=font_xs)[2], H - 38),
              "UPDATED", fill=(*GOLD, 130), font=font_xs)

    # Конвертируем в PNG bytes
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


# ─── Хендлеры бота ───────────────────────────────────────────────

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "🎁 <b>MRKT Sticker Bot</b>\n\n"
        "Генерирую стикеры с ценами подарков Telegram!\n\n"
        "📋 <b>Команды:</b>\n"
        "<code>/sticker PlushPepe</code> — стикер с ценой\n"
        "<code>/price PlushPepe</code> — текстовая цена\n"
        "<code>/list</code> — все коллекции\n",
        parse_mode="HTML"
    )


@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    await fetch_data()
    if not collections_cache:
        await message.answer("❌ Нет данных. Попробуйте позже.")
        return

    # Группируем по маркету
    mrkt = []
    fragment = []
    for slug, col in sorted(collections_cache.items(), key=lambda x: -(x[1].get("floor_price", 0))):
        line = f"<code>{col['slug']}</code> — {col.get('floor_price', 0):.2f} TON"
        if col.get("_market") == "fragment":
            fragment.append(line)
        else:
            mrkt.append(line)

    text = "📋 <b>Доступные коллекции:</b>\n\n"
    if mrkt:
        text += "<b>🟡 MRKT:</b>\n" + "\n".join(mrkt[:30]) + "\n\n"
    if fragment:
        text += "<b>🔵 Fragment:</b>\n" + "\n".join(fragment[:30]) + "\n"

    text += f"\n💡 Используй: <code>/sticker название</code>"
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("price"))
async def cmd_price(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/price PlushPepe</code>", parse_mode="HTML")
        return

    slug = args[1].strip()
    await fetch_data()

    col = collections_cache.get(slug.lower())
    if not col:
        await message.answer(f"❌ Коллекция <b>{slug}</b> не найдена.\nИспользуй /list для списка.", parse_mode="HTML")
        return

    floor = col.get("floor_price", 0)
    change = col.get("change_24h") if col.get("change_24h") is not None else col.get("price_change_24h")
    usd = floor * ton_usd
    stars = int(usd / STAR_USD) if STAR_USD > 0 else 0
    supply = col.get("supply") or col.get("total_supply") or "—"

    chg_str = f"{'+' if change >= 0 else ''}{change:.1f}%" if change is not None else "≈ 0%"
    chg_emoji = "🟢" if change and change > 0 else "🔴" if change and change < 0 else "🟡"

    text = (
        f"🎁 <b>{col['slug']}</b>\n\n"
        f"💎 <b>{floor:.2f} TON</b> (${usd:.2f})\n"
        f"⭐ {stars:,} Stars\n"
        f"{chg_emoji} 24h: {chg_str}\n"
        f"📦 Supply: {int(supply):,}\n" if supply != "—" else ""
        f"\n🏪 {col.get('_market', 'mrkt').upper()}"
    )
    await message.answer(text, parse_mode="HTML")


@dp.message(Command("sticker"))
async def cmd_sticker(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/sticker PlushPepe</code>", parse_mode="HTML")
        return

    slug = args[1].strip()
    await fetch_data()

    col = collections_cache.get(slug.lower())
    if not col:
        await message.answer(f"❌ Коллекция <b>{slug}</b> не найдена.\nИспользуй /list для списка.", parse_mode="HTML")
        return

    wait_msg = await message.answer("⏳ Генерирую стикер...")

    try:
        png_data = generate_sticker_image(col)
        photo = BufferedInputFile(png_data, filename=f"{col['slug']}_mrkt.png")
        await message.answer_photo(photo, caption=f"🎁 {col['slug']} — {col.get('floor_price', 0):.2f} TON")
    except Exception as e:
        log.error(f"Sticker generation error: {e}")
        await message.answer(f"❌ Ошибка генерации: {e}")
    finally:
        await wait_msg.delete()


# ─── Запуск ──────────────────────────────────────────────────────

async def main():
    log.info("🚀 MRKT Sticker Bot запущен!")
    log.info("Загружаем данные...")
    await fetch_data()
    log.info(f"✓ Загружено {len(collections_cache)} коллекций")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
