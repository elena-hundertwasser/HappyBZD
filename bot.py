import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

app_server = Flask("fake_server")

@app_server.route("/")
def home():
    return "Bot is running!"

def run_server():
    port = int(os.getenv("PORT", 10000))
    app_server.run(host="0.0.0.0", port=port)

threading.Thread(target=run_server).start()

TOKEN = "8734555092:AAHbG9ei99cAPBnObkA77A9DWUUH2gJlTlw"

DATA_FILE = "birthdays.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(data, user_id):
    if user_id not in data:
        data[user_id] = {
            "birthdays": [],
            "reminder_days": 3
        }
    return data[user_id]

def main_menu():
    keyboard = [
        [InlineKeyboardButton("❤️ Добавить", callback_data="add")],
        [InlineKeyboardButton("💋 Список", callback_data="list")],
        [InlineKeyboardButton("❌ Удалить", callback_data="delete")],
        [InlineKeyboardButton("⚙ Настройки", callback_data="settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_button():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Приветули, я бот от Лены Денисовой. Я напомню тебе о днях рождениях твоих близких 💋❤️\n\nВыберите действие:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data = load_data()
    user_data = get_user_data(data, user_id)

    if query.data == "add":
        context.user_data["state"] = "waiting_add"
        await query.message.reply_text(
            "Введите данные:\nИмя ДД-ММ-ГГГГ\n\nПример:\nЕлена 17-12-2001",
            reply_markup=back_button()
        )

    elif query.data == "list":
        if not user_data["birthdays"]:
            text = "Список пуст."
        else:
            text = "❤️ Ваши дни рождения:\n\n"
            for entry in user_data["birthdays"]:
                text += f"{entry['name']} — {entry['date']}\n"

        await query.message.reply_text(text, reply_markup=main_menu())

    elif query.data == "delete":
        if not user_data["birthdays"]:
            await query.message.reply_text("Список пуст.", reply_markup=main_menu())
            return

        keyboard = []
        for entry in user_data["birthdays"]:
            keyboard.append([
                InlineKeyboardButton(
                    f"{entry['name']} — {entry['date']}",
                    callback_data=f"del_{entry['name']}"
                )
            ])

        keyboard.append([InlineKeyboardButton("⬅ Назад", callback_data="back")])
        await query.message.reply_text(
            "Выберите кого удалить:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("del_"):
        name_to_delete = query.data.replace("del_", "")
        user_data["birthdays"] = [
            b for b in user_data["birthdays"]
            if b["name"] != name_to_delete
        ]
        save_data(data)

        await query.message.reply_text(
            f"🗑 {name_to_delete} удалён.",
            reply_markup=main_menu()
        )

    elif query.data == "settings":
        keyboard = [
            [InlineKeyboardButton("1 день", callback_data="rem_1")],
            [InlineKeyboardButton("3 дня", callback_data="rem_3")],
            [InlineKeyboardButton("7 дней", callback_data="rem_7")],
            [InlineKeyboardButton("⬅ Назад", callback_data="back")]
        ]
        await query.message.reply_text(
            f"Текущее напоминание: за {user_data['reminder_days']} дня(ей)",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif query.data.startswith("rem_"):
        days = int(query.data.replace("rem_", ""))
        user_data["reminder_days"] = days
        save_data(data)

        await query.message.reply_text(
            f"Теперь напоминание за {days} дня(ей).",
            reply_markup=main_menu()
        )

    elif query.data == "back":
        context.user_data["state"] = None
        await query.message.reply_text("Главное меню:", reply_markup=main_menu())

def validate_date(date_text):
    try:
        datetime.strptime(date_text, "%d-%m-%Y")
        return True
    except:
        return False


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("state")

    if state != "waiting_add":
        return

    text = update.message.text.strip()
    parts = text.split()

    if len(parts) < 2:
        await update.message.reply_text("Введите имя и дату через пробел.")
        return

    name = " ".join(parts[:-1])
    date = parts[-1]

    if not validate_date(date):
        await update.message.reply_text("Неверный формат даты.")
        return

    user_id = str(update.effective_user.id)
    data = load_data()
    user_data = get_user_data(data, user_id)

    user_data["birthdays"].append({
        "name": name,
        "date": date
    })

    save_data(data)

    await update.message.reply_text(
        "❤️ День рождения добавлен!",
        reply_markup=main_menu()
    )

    context.user_data["state"] = None

async def check_birthdays(context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    today = datetime.now()

    for user_id, user_data in data.items():
        reminder_days = user_data.get("reminder_days", 3)

        for entry in user_data["birthdays"]:
            birth_date = datetime.strptime(entry["date"], "%d-%m-%Y")
            next_birthday = birth_date.replace(year=today.year)

            if next_birthday < today:
                next_birthday = next_birthday.replace(year=today.year + 1)

            days_left = (next_birthday - today).days

            if days_left == reminder_days:
                await context.bot.send_message(
                    chat_id=int(user_id),
                    text=f"❤️ Через {reminder_days} дня(ей) день рождения у {entry['name']}!"
                )

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    job_queue = app.job_queue
    job_queue.run_repeating(check_birthdays, interval=86400, first=10)

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
