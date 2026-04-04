# MRKT Stickers

Auto-updating Telegram sticker pack system for the **MRKT** gift marketplace.
Stickers display live floor prices (USD, TON, Stars), 24h price changes, supply, and gift thumbnails.
Packs refresh every 60 seconds.

Система автообновляемых Telegram-стикерпаков для маркетплейса подарков **MRKT**.
Стикеры отображают актуальные floor-цены (USD, TON, Stars), изменение за 24ч, supply и картинку подарка.
Обновление каждые 60 секунд.

---

## How it works / Как это работает

```
giftstat API  ──→  floor prices, 24h change, supply
Binance API   ──→  TON/USD rate
changes.tg    ──→  gift images (by MTProto gift ID)
                        │
                        ▼
              ┌─────────────────────┐
              │  sticker_image.py   │  ← generates 512x512 WebP card
              └─────────┬───────────┘
                        │
                        ▼
              ┌─────────────────────┐
              │  sticker_pack.py    │  ← creates/updates 3 Telegram sticker packs (50 each)
              └─────────┬───────────┘    via Telegram Bot API, loop every 60s
                        │
                        ▼
              ┌─────────────────────┐
              │  bot.py             │  ← interactive bot: /sticker, /price, /list
              └─────────────────────┘
```

---

## Project structure / Структура

```
mrkt_sticker/
├── sticker_image.py      # Image generator (512x512 WebP) / Генератор изображений
├── sticker_pack.py       # Pack manager (3×50, auto-update) / Менеджер стикерпаков
├── bot.py                # Telegram bot commands / Команды бота
├── requirements.txt      # aiogram, aiohttp, Pillow
├── .env.example          # Template / Шаблон конфигурации
├── .env                  # Credentials (git-ignored) / Токен и ID
├── gift_overrides/       # Manual image overrides / Замены картинок вручную
├── gift_cache/           # Auto-downloaded images (git-ignored)
└── sticker_state.json    # Runtime state (git-ignored)
```

---

## Setup & run / Установка и запуск

```bash
cd mrkt_sticker
pip install -r requirements.txt
```

Create `.env` / Создайте `.env`:
```env
TELEGRAM_BOT_TOKEN=<from @BotFather>
OWNER_USER_ID=<from @userinfobot>
```

Run / Запуск:
```bash
python sticker_pack.py    # auto-updating packs / автообновляемые паки
python bot.py             # interactive bot / интерактивный бот
```

---

## What each file does / Что делает каждый файл

### `sticker_image.py` (469 lines)

Generates a single 512x512 sticker card. / Генерирует одну карточку 512x512.

**Input:** collection dict (`slug`, `floor_price`, `supply`, `change_24h`) + TON/USD rate + optional gift image.
**Output:** WebP/PNG bytes.

Key functions / Ключевые функции:
| Function | Purpose / Назначение |
|---|---|
| `generate_sticker()` | Main entry point — assembles full card / Точка входа — собирает карточку |
| `format_slug()` | `DurovsCap` → `DUROV'S CAP` / Форматирование имени |
| `draw_top_pulse()` | Neon pulse line (4-layer glow) / Неоновый пульс вверху |
| `draw_gold_glow()` | Radial gold glow under gift image / Золотое свечение |
| `draw_mrkt_watermark()` | Diagonal "MRKT" text, clipped to card / Водяной знак |
| `draw_growth_effects()` | Green glow + sparkles + arrows / Эффекты роста |
| `draw_drop_effects()` | Red glow + falling particles / Эффекты падения |
| `draw_heartbeat()` | ECG-style line behind price / Линия пульса за ценой |

Visual logic / Визуальная логика:
- Price **rising** → green neon pulse, green price text, green glow + sparkles
- Price **falling** → red neon pulse, red price text, red glow + particles
- Price **stable** → gold pulse, white price text

### `sticker_pack.py` (606 lines)

Creates and maintains 3 Telegram sticker packs (150 stickers total).
Создаёт и обновляет 3 стикерпака (150 стикеров).

Key logic / Ключевая логика:
| Function | Purpose / Назначение |
|---|---|
| `fetch_collections()` | Fetches data from giftstat API / Получает данные из giftstat |
| `fetch_ton_rate()` | TON/USD from Binance / Курс TON/USD |
| `load_gift_images()` | Downloads & caches gift PNGs / Скачивает картинки подарков |
| `sync_sticker_pack()` | Creates or updates one pack / Создаёт или обновляет пак |
| `match_gift_image()` | Returns cached PIL.Image for slug / Возвращает картинку по slug |

Data structures / Структуры данных:
- `SLUG_TO_GIFT_ID` — dict mapping 165+ slugs → MTProto gift IDs (for image URLs)
- `SLUG_DISPLAY_NAMES` — dict mapping slugs → formatted display names
- `EMOJI_MAP` — dict mapping slugs → emoji (for sticker pack metadata)
- `gift_images_cache` — runtime dict slug → PIL.Image

Image loading priority / Приоритет загрузки картинок:
1. `gift_overrides/<slug>.{png,webp,jpg}` — manual override
2. `gift_cache/<slug>.png` — disk cache
3. Download from `api.changes.tg/original/{gift_id}.png`

### `bot.py` (355 lines)

Interactive Telegram bot. / Интерактивный Telegram-бот.

| Command | What it does / Что делает |
|---|---|
| `/sticker <slug>` | Generates and sends sticker image / Генерирует и отправляет стикер |
| `/price <slug>` | Text response with price data / Текстовый ответ с ценой |
| `/list` | Shows all available collections / Список всех коллекций |
| `/start` | Welcome message / Приветствие |

---

## Key constants / Ключевые константы

| Constant | Value | Location | Purpose / Назначение |
|---|---|---|---|
| `NUM_PACKS` | 3 | sticker_pack.py | Sticker packs count / Кол-во паков |
| `MAX_STICKERS` | 50 | sticker_pack.py | Per pack limit / Лимит на пак |
| `UPDATE_INTERVAL` | 60s | sticker_pack.py | Refresh cycle / Цикл обновления |
| `STAR_USD` | 0.015 | sticker_image.py | Stars→USD rate / Курс Stars |
| `CORNER` | 48px | sticker_image.py | Card corner radius / Скругление углов |
| `W, H` | 512×512 | sticker_image.py | Sticker dimensions / Размер стикера |

---

## Dependencies / Зависимости

| Package | Version | Purpose / Назначение |
|---|---|---|
| `aiogram` | ≥3.0 | Telegram Bot API framework |
| `aiohttp` | ≥3.9 | Async HTTP client for API calls / HTTP-клиент |
| `Pillow` | ≥10.0 | Image generation (PIL) / Генерация изображений |

---

## External APIs / Внешние API

| API | Endpoint | Data / Данные |
|---|---|---|
| giftstat | `api.giftstat.app/current/collections/floor` | Floor prices + 24h change / Цены + изменение |
| giftstat | `api.giftstat.app/current/collections` | Supply data / Данные о supply |
| Binance | `api.binance.com/api/v3/ticker/price` | TON/USD rate / Курс TON |
| changes.tg | `api.changes.tg/original/{gift_id}.png` | Gift images / Картинки подарков |
| Telegram | Bot API | Pack CRUD / Управление паками |
