#!/usr/bin/env python3
"""
MRKT Sticker Image Generator / Генератор стикер-изображений MRKT.

EN: Generates 512x512 WebP/PNG sticker cards with live gift price data.
    Includes: neon pulse line, collection name, gift thumbnail, USD price
    (colored by trend), change badge, TON/Stars info, supply, watermark,
    and visual effects (glow, particles) for growth/drop states.
    Used by sticker_pack.py (auto-update) and bot.py (on-demand).

RU: Создаёт карточки 512x512 (WebP/PNG) с данными о цене подарка:
    неоновый пульс, название, миниатюра, цена USD (цвет по тренду),
    плашка изменения, TON/Stars, supply, watermark, эффекты свечения.
    Используется в sticker_pack.py (автообновление) и bot.py (по запросу).
"""

import io
import math
import re
import random
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

W, H = 512, 512
WHITE = (255, 255, 255)
GREEN = (0, 220, 110)
RED = (255, 70, 70)
GRAY = (160, 160, 175)
GOLD = (255, 208, 0)
BLUE_TON = (50, 140, 255)
ORANGE = (255, 180, 0)
STAR_USD = 0.015
CORNER = 48

# Slugs that should show "unboxed" label
UNBOXED_SLUGS = {"ufcstrike"}


# Ручные override'ы для имён, которые regex не может правильно разбить
SLUG_DISPLAY_NAMES = {
    "durovscap": "DUROV'S CAP",
    "khabibspapakha": "KHABIB'S PAPAKHA",
    "ufcstrike": "UFC STRIKE",
    "snoopdogg": "SNOOP DOGG",
    "plushpepe": "PLUSH PEPE",
    "eternalrose": "ETERNAL ROSE",
    "recordplayer": "RECORD PLAYER",
    "swisswatch": "SWISS WATCH",
    "poolfloat": "POOL FLOAT",
    "moodpack": "MOOD PACK",
    "santahat": "SANTA HAT",
    "heartlocket": "HEART LOCKET",
    "signetring": "SIGNET RING",
    "diamondring": "DIAMOND RING",
    "magicpotion": "MAGIC POTION",
    "lovepotion": "LOVE POTION",
    "sakuraflower": "SAKURA FLOWER",
    "preciouspeach": "PRECIOUS PEACH",
    "kissedfrog": "KISSED FROG",
    "madpumpkin": "MAD PUMPKIN",
    "eternalcandle": "ETERNAL CANDLE",
    "toybear": "TOY BEAR",
    "minioscar": "MINI OSCAR",
    "tophat": "TOP HAT",
    "jesterhat": "JESTER HAT",
    "evileye": "EVIL EYE",
    "hexpot": "HEX POT",
    "scaredcat": "SCARED CAT",
    "skullflower": "SKULL FLOWER",
    "trappedheart": "TRAPPED HEART",
    "homemadecake": "HOMEMADE CAKE",
    "sharptongue": "SHARP TONGUE",
    "spyagaric": "SPY AGARIC",
    "hangingstar": "HANGING STAR",
    "bonedring": "BONED RING",
    "bondedring": "BONDED RING",
    "gingerman": "GINGER MAN",
    "gingercookie": "GINGER COOKIE",
    "jellybunny": "JELLY BUNNY",
    "victorymedal": "VICTORY MEDAL",
    "rarebird": "RARE BIRD",
    "timelessbook": "TIMELESS BOOK",
    "chillflame": "CHILL FLAME",
    "vicecream": "VICE CREAM",
    "jackinthebox": "JACK IN THE BOX",
    "petsnake": "PET SNAKE",
    "snakebox": "SNAKE BOX",
    "easteregg": "EASTER EGG",
}


def format_slug(slug):
    """Превращает camelCase/PascalCase slug в читаемое название.

    Примеры: DurovsCap -> DUROV'S CAP, PlushPepe -> PLUSH PEPE,
    UFCStrike -> UFC STRIKE, SnoopDogg -> SNOOP DOGG
    """
    override = SLUG_DISPLAY_NAMES.get(slug.lower())
    if override:
        return override
    # Вставляем пробел перед заглавной буквой, если перед ней строчная
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', slug)
    # Аббревиатуры: UFCStrike -> UFC Strike
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    return s.upper()


def get_font(size):
    for name in ["DejaVuSans-Bold.ttf", "Inter-Bold.ttf", "arial.ttf", "DejaVuSans.ttf"]:
        try:
            return ImageFont.truetype(name, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def _center(draw, text, font, y, fill):
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    draw.text(((W - tw) // 2, y), text, fill=fill, font=font)


def _fit_font(draw, text, max_width, start_size, min_size=20):
    for size in range(start_size, min_size - 1, -2):
        f = get_font(size)
        bb = draw.textbbox((0, 0), text, font=f)
        if bb[2] - bb[0] <= max_width:
            return f
    return get_font(min_size)


def draw_heartbeat(draw, y_center, accent, alpha=35):
    points = []
    mid = W // 2
    for x in range(20, mid - 70):
        points.append((x, y_center))
    pulse = [
        (mid - 70, y_center),
        (mid - 50, y_center + 15),
        (mid - 35, y_center - 50),
        (mid - 10, y_center + 30),
        (mid + 15, y_center - 22),
        (mid + 35, y_center + 8),
        (mid + 55, y_center),
    ]
    points.extend(pulse)
    for x in range(mid + 55, W - 20):
        points.append((x, y_center))
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha), width=3)
    for i in range(len(points) - 1):
        draw.line([points[i], points[i + 1]], fill=(*accent, alpha // 4), width=8)


def draw_top_pulse(img, yc, accent):
    """Неоновая линия пульса вверху карточки с ярким свечением."""
    mid = W // 2
    left = CORNER + 20
    right = W - CORNER - 20
    pts = []
    for x in range(left, mid - 25):
        pts.append((x, yc))
    pts += [
        (mid - 25, yc), (mid - 15, yc + 5), (mid - 8, yc - 14),
        (mid, yc + 9), (mid + 8, yc - 7), (mid + 15, yc + 3),
        (mid + 25, yc),
    ]
    for x in range(mid + 25, right + 1):
        pts.append((x, yc))

    # Layer 1: wide blurred glow
    glow3 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(glow3)
    for i in range(len(pts) - 1):
        d3.line([pts[i], pts[i + 1]], fill=(*accent, 80), width=20)
    glow3 = glow3.filter(ImageFilter.GaussianBlur(radius=10))
    img = Image.alpha_composite(img, glow3)

    # Layer 2: medium glow
    glow2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(glow2)
    for i in range(len(pts) - 1):
        d2.line([pts[i], pts[i + 1]], fill=(*accent, 140), width=10)
    glow2 = glow2.filter(ImageFilter.GaussianBlur(radius=5))
    img = Image.alpha_composite(img, glow2)

    # Layer 3: bright near glow
    glow1 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(glow1)
    for i in range(len(pts) - 1):
        d1.line([pts[i], pts[i + 1]], fill=(*accent, 200), width=6)
    glow1 = glow1.filter(ImageFilter.GaussianBlur(radius=2))
    img = Image.alpha_composite(img, glow1)

    # Layer 4: white-hot core
    core = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dc = ImageDraw.Draw(core)
    bright = (min(accent[0] + 180, 255), min(accent[1] + 180, 255), min(accent[2] + 180, 255))
    for i in range(len(pts) - 1):
        dc.line([pts[i], pts[i + 1]], fill=(*bright, 255), width=2)
    img = Image.alpha_composite(img, core)

    return img


def draw_gold_glow(img):
    """Золотистое свечение в верхней части карточки (зона картинки подарка)."""
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 130
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.2) ** 2)
            if dist < 160:
                t = 1.0 - (dist / 160)
                t = t * t * t
                a = int(t * 50)
                glow.putpixel((x, y), (GOLD[0], GOLD[1], GOLD[2], a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=8))
    return Image.alpha_composite(img, glow)


def draw_mrkt_watermark(img):
    """Диагональный MRKT watermark на заднем фоне."""
    f = get_font(270)
    text = "MRKT"
    tmp = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    bb = d.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]

    txt_layer = Image.new("RGBA", (tw + 80, th + 80), (0, 0, 0, 0))
    txt_draw = ImageDraw.Draw(txt_layer)
    txt_draw.text((40, 40), text, font=f, fill=(42, 42, 42, 255))

    rotated = txt_layer.rotate(55, expand=True, resample=Image.BICUBIC)

    wm = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    rx, ry = rotated.size
    wm.paste(rotated, ((W - rx) // 2 - 5, (H - ry) // 2 + 10), rotated)

    # Clip to card shape
    mask = Image.new("L", (W, H), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([4, 4, W - 5, H - 5], radius=CORNER - 2, fill=255)
    wm_r, wm_g, wm_b, wm_a = wm.split()
    clipped_a = ImageChops.multiply(wm_a, mask)
    wm = Image.merge("RGBA", (wm_r, wm_g, wm_b, clipped_a))

    return Image.alpha_composite(img, wm)


def draw_growth_effects(img, accent):
    """Эффекты роста: свечение за ценой + искры/частицы вверх."""
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 270
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.5) ** 2)
            if dist < 140:
                t = 1.0 - (dist / 140)
                t = t * t
                a = int(t * 40)
                glow.putpixel((x, y), (accent[0], accent[1], accent[2], a))
    fx = Image.alpha_composite(fx, glow)
    draw = ImageDraw.Draw(fx)

    random.seed(42)
    for _ in range(18):
        x = random.randint(80, W - 80)
        y = random.randint(180, 310)
        size = random.randint(2, 5)
        alpha = random.randint(60, 160)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(accent[0], accent[1], accent[2], alpha))

    for _ in range(8):
        x = random.randint(100, W - 100)
        y = random.randint(200, 300)
        length = random.randint(8, 20)
        alpha = random.randint(50, 120)
        draw.line([(x, y), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x - 3, y - length + 4), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x + 3, y - length + 4), (x, y - length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)

    return Image.alpha_composite(img, fx)


def draw_drop_effects(img, accent):
    """Эффекты падения: красное свечение + частицы вниз."""
    fx = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(fx)

    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cx, cy = W // 2, 270
    for y in range(H):
        for x in range(W):
            dist = math.sqrt((x - cx) ** 2 + ((y - cy) * 1.5) ** 2)
            if dist < 140:
                t = 1.0 - (dist / 140)
                t = t * t
                a = int(t * 40)
                glow.putpixel((x, y), (accent[0], accent[1], accent[2], a))
    fx = Image.alpha_composite(fx, glow)
    draw = ImageDraw.Draw(fx)

    random.seed(42)
    for _ in range(18):
        x = random.randint(80, W - 80)
        y = random.randint(200, 320)
        size = random.randint(2, 5)
        alpha = random.randint(60, 160)
        draw.ellipse([x - size, y - size, x + size, y + size],
                     fill=(accent[0], accent[1], accent[2], alpha))

    for _ in range(8):
        x = random.randint(100, W - 100)
        y = random.randint(210, 300)
        length = random.randint(8, 20)
        alpha = random.randint(50, 120)
        draw.line([(x, y), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x - 3, y + length - 4), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)
        draw.line([(x + 3, y + length - 4), (x, y + length)],
                  fill=(accent[0], accent[1], accent[2], alpha), width=2)

    return Image.alpha_composite(img, fx)


def generate_sticker(col, ton_usd=7.2, fmt="WEBP", gift_img=None):
    slug = col.get("slug", "???")
    floor = col.get("floor_price", 0)
    supply = col.get("supply") or col.get("total_supply") or col.get("total_count")

    change = col.get("change_24h")
    if change is None:
        prev1d = col.get("floor_price_prev1day")
        if prev1d and prev1d > 0 and floor > 0:
            change = round(((floor - prev1d) / prev1d) * 100, 1)
        elif col.get("price_change_24h") is not None:
            change = col.get("price_change_24h")

    usd = floor * ton_usd
    stars = int(usd / STAR_USD) if STAR_USD > 0 else 0

    if change is not None and change > 0.01:
        accent = GREEN
    elif change is not None and change < -0.01:
        accent = RED
    else:
        accent = GOLD

    # Background with rounded corners
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([0, 0, W - 1, H - 1], radius=CORNER, fill=(0, 0, 0, 255))
    draw.rounded_rectangle([2, 2, W - 3, H - 3], radius=CORNER - 2, outline=GOLD, width=3)

    # MRKT watermark
    img = draw_mrkt_watermark(img)

    # Gold glow under gift image area
    img = draw_gold_glow(img)

    # Growth/drop effects
    if change is not None and change > 0.01:
        img = draw_growth_effects(img, accent)
    elif change is not None and change < -0.01:
        img = draw_drop_effects(img, accent)

    draw = ImageDraw.Draw(img)

    # Heartbeat line
    hb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_heartbeat(ImageDraw.Draw(hb), 235, accent, 30)
    img = Image.alpha_composite(img, hb)

    # Neon pulse line at top
    img = draw_top_pulse(img, 28, accent)
    draw = ImageDraw.Draw(img)

    # Collection name (formatted from camelCase)
    display_name = format_slug(slug)
    _center(draw, display_name, _fit_font(draw, display_name, W - 50, 44, 24), 44, GOLD)

    # Gift image
    if gift_img:
        thumb_size = 140
        try:
            gift_resized = gift_img.copy().resize((thumb_size, thumb_size), Image.LANCZOS)
            if gift_resized.mode != "RGBA":
                gift_resized = gift_resized.convert("RGBA")
            img.paste(gift_resized, ((W - thumb_size) // 2, 86), gift_resized)
            draw = ImageDraw.Draw(img)
        except Exception:
            pass

    # USD Price — color reflects growth/drop
    price_text = f"${usd:,.2f}"
    f_price = _fit_font(draw, price_text, W - 50, 70, 36)
    if change is not None and change > 0.01:
        price_color = GREEN
    elif change is not None and change < -0.01:
        price_color = RED
    else:
        price_color = WHITE
    _center(draw, price_text, f_price, 242, price_color)

    # Change pill
    f_chg = get_font(30)
    cy = 320
    ch = 42
    if change is not None and change > 0.01:
        chg_text = f"\u2197 +{change:.1f}%"
    elif change is not None and change < -0.01:
        chg_text = f"\u2198 {change:.1f}%"
    else:
        chg_text = "\u2014 0.0%"
    cbb = draw.textbbox((0, 0), chg_text, font=f_chg)
    cw = cbb[2] - cbb[0] + 32
    cx = (W - cw) // 2
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch], radius=ch // 2,
                            fill=(accent[0] // 8, accent[1] // 8, accent[2] // 8, 255),
                            outline=(*accent, 140), width=2)
    _center(draw, chg_text, f_chg, cy + 5, accent)

    # Info line: ton (blue) + stars (orange)
    f_info = get_font(26)
    info_y = 378
    ton_s = f"{floor:,.2f}" if floor < 10000 else f"{floor:,.0f}"
    ton_part = f"{ton_s} ton"
    stars_part = f"{stars:,} \u2605"
    ton_bb = draw.textbbox((0, 0), ton_part, font=f_info)
    gap_bb = draw.textbbox((0, 0), "   ", font=f_info)
    stars_bb = draw.textbbox((0, 0), stars_part, font=f_info)
    ton_w = ton_bb[2] - ton_bb[0]
    gap_w = gap_bb[2] - gap_bb[0]
    stars_w = stars_bb[2] - stars_bb[0]
    sx = (W - (ton_w + gap_w + stars_w)) // 2
    draw.text((sx, info_y), ton_part, fill=BLUE_TON, font=f_info)
    draw.text((sx + ton_w + gap_w, info_y), stars_part, fill=ORANGE, font=f_info)

    # Supply
    try:
        supply_i = int(supply) if supply else 0
        supply_s = f"{supply_i:,} pcs" if supply_i > 0 else None
    except (ValueError, TypeError):
        supply_s = None
    if supply_s:
        _center(draw, f"Supply: {supply_s}", get_font(24), info_y + 36, GRAY)

    # "unboxed" label for specific gifts
    if slug.lower() in UNBOXED_SLUGS:
        _center(draw, "unboxed", get_font(20), info_y + 62, GRAY)

    # Full date with day
    now_str = datetime.now().strftime("%d %b %Y  %H:%M UTC")
    _center(draw, now_str, get_font(22), H - 42, GOLD)

    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()
