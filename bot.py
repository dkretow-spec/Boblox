import asyncio
import json
import os
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "8584968006:AAE6xuhOQ9cbFlG3YCPH6oo7XXSz9g6R5A8"
ADMIN_ID = 6673569777

DATA_FILE = os.path.join(os.path.dirname(__file__), "bot_data.json")
ONLINE_MINUTES = 5

if not TOKEN:
    raise SystemExit("Oshibka: vpishi TOKEN v bot.py")

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
active_users: dict[int, datetime] = {}


def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        default = {"script": "Skript poka ne zagruzhen.", "reviews": []}
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def track(user_id: int):
    active_users[user_id] = datetime.now()


def avg_rating(reviews: list) -> float:
    if not reviews:
        return 0.0
    return sum(r["rating"] for r in reviews) / len(reviews)


def rating_bar(rating: float, size: int = 10) -> str:
    filled = round(rating / 5 * size)
    return "🟩" * filled + "⬜" * (size - filled)


class ReviewSM(StatesGroup):
    rating = State()
    text = State()


class AdminSM(StatesGroup):
    script = State()


def main_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="📜 Skript", callback_data="tab_script")
    b.button(text="📝 Otzyvy", callback_data="tab_reviews")
    b.adjust(2)
    return b.as_markup()


def back_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Nazad", callback_data="back_main")
    return b.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✏️ Redaktirovat skript", callback_data="admin_script")
    b.button(text="👥 Onlayn", callback_data="admin_online")
    b.button(text="📋 Vse otzyvy", callback_data="admin_reviews")
    b.adjust(1)
    b.button(text="◀️ Na glavnuyu", callback_data="back_main")
    return b.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="❌ Otmena", callback_data="cancel")
    return b.as_markup()


@dp.message(CommandStart())
async def start(message: Message):
    track(message.from_user.id)
    await message.answer(
        f"👋 Privet, {message.from_user.first_name}!\nVyberi vkladku:",
        reply_markup=main_kb(),
    )


@dp.callback_query(F.data == "back_main")
async def back(callback: CallbackQuery):
    track(callback.from_user.id)
    await callback.message.edit_text("👋 Vyberi vkladku:", reply_markup=main_kb())
    await callback.answer()


@dp.callback_query(F.data == "tab_script")
async def script_tab(callback: CallbackQuery):
    track(callback.from_user.id)
    data = load_data()
    await callback.message.edit_text(
        f"📜 <b>Skript</b>\n\n<code>{data['script']}</code>",
        reply_markup=back_kb(),
    )
    await callback.answer()


@dp.callback_query(F.data == "tab_reviews")
async def reviews_tab(callback: CallbackQuery):
    track(callback.from_user.id)
    data = load_data()
    reviews = data["reviews"]
    avg = avg_rating(reviews)

    text = f"📝 <b>Otzyvy</b>\n\n"
    text += f"Sredniy ball: {avg:.1f}/5\n{rating_bar(avg)}\n"
    text += f"Vsego: {len(reviews)}\n\n"

    if reviews:
        text += "📌 <b>Poslednie:</b>\n"
        for r in reviews[-3:]:
            name = r.get("username", "Anonim")
            t = r["text"]
            text += f"• {r['rating']}⭐ {t[:40]}{'...' if len(t) > 40 else ' '} — {name}\n"

    b = InlineKeyboardBuilder()
    b.button(text="✍️ Napisat otzyv", callback_data="write_review")
    b.button(text="◀️ Nazad", callback_data="back_main")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())
    await callback.answer()


@dp.callback_query(F.data == "write_review")
async def write_review(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReviewSM.rating)
    await callback.message.edit_text(
        "⭐ Oceni skript ot 1 do 5 (otpravi chislo):",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@dp.message(ReviewSM.rating)
async def get_rating(message: Message, state: FSMContext):
    try:
        r = int(message.text)
        if not 1 <= r <= 5:
            raise ValueError
    except ValueError:
        await message.reply("❌ Otprav chislo ot 1 do 5.")
        return
    await state.update_data(rating=r)
    await state.set_state(ReviewSM.text)
    await message.answer("✍️ Napishi tekst otzyva:", reply_markup=cancel_kb())


@dp.message(ReviewSM.text)
async def get_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.reply("❌ Otzyv ne mozhet byt pustym.")
        return
    data = await state.get_data()
    user = message.from_user
    review = {
        "rating": data["rating"],
        "text": text,
        "username": user.full_name,
        "user_id": user.id,
        "date": datetime.now().isoformat(),
    }
    bot_data = load_data()
    bot_data["reviews"].append(review)
    save_data(bot_data)
    await state.clear()
    await message.answer("✅ Spasibo! Otzyv sohranyon.", reply_markup=main_kb())


@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return await message.reply("❌ Net dostupa.")
    await message.answer("🔐 <b>Admin-panel</b>", reply_markup=admin_kb())


@dp.callback_query(F.data == "admin_script")
async def admin_edit(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Net dostupa", show_alert=True)
    data = load_data()
    await state.set_state(AdminSM.script)
    await callback.message.edit_text(
        f"📜 Tekushiy:\n<code>{data['script']}</code>\n\nOtprav noviy tekst:",
        reply_markup=cancel_kb(),
    )
    await callback.answer()


@dp.message(AdminSM.script)
async def admin_save(message: Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = load_data()
    data["script"] = message.text
    save_data(data)
    await state.clear()
    await message.answer("✅ Skript obnovlyon!", reply_markup=admin_kb())


@dp.callback_query(F.data == "admin_online")
async def admin_online(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Net dostupa", show_alert=True)
    now = datetime.now()
    count = sum(1 for t in active_users.values() if (now - t) < timedelta(minutes=ONLINE_MINUTES))
    await callback.message.edit_text(
        f"👥 <b>Onlayn (5 min):</b> {count}", reply_markup=admin_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_reviews")
async def admin_reviews(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("❌ Net dostupa", show_alert=True)
    data = load_data()
    reviews = data["reviews"]
    if not reviews:
        text = "📋 Otzyvov net."
    else:
        text = f"📋 <b>Vse otzyvy ({len(reviews)}):</b>\n\n"
        for i, r in enumerate(reviews, 1):
            t = r["text"]
            text += f"{i}. {r['rating']}⭐ {t[:80]}{'...' if len(t) > 80 else ' '}\n"
            text += f"   👤 {r['username']} (ID: {r['user_id']})\n\n"
    await callback.message.edit_text(text[:4000], reply_markup=admin_kb())
    await callback.answer()


@dp.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Otmeneno.", reply_markup=main_kb())
    await callback.answer()


async def main():
    print("Bot zapushchen!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
