import asyncio
import json
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton
import os
from dotenv import load_dotenv
import database

logging.basicConfig(level=logging.INFO)
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
WEB_APP_URL = 'https://brxhh.github.io/cafebot/?v=7'
ADMIN_ID = 951795337

bot = Bot(token=TOKEN)
dp = Dispatcher()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# заглушка
@app.get("/")
def read_root():
    return {"status": "Сервер працює успішно!"}

@app.get("/api/products")
def get_products_api():
    return database.get_active_products()

@dp.message(CommandStart())
async def start_command(message: types.Message):
    markup = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Відкрити меню кав'ярні ☕️", web_app=WebAppInfo(url=WEB_APP_URL))]],
        resize_keyboard=True
    )
    await message.answer(
        "👋 <b>Ласкаво просимо до нашої кав'ярні!</b>\n\nНатисніть кнопку нижче, щоб відкрити меню.",
        reply_markup=markup, parse_mode="HTML"
    )

@dp.message(F.web_app_data)
async def web_app_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        items = data.get('items', [])
        total = data.get('total', 0)

        database.save_order(message.from_user.id, message.from_user.username, items, total)

        receipt = "🧾 <b>ТЫ ЕБАННЫЙ ХУЕСОС И ЧМО</b>\n\n"

        for item in items:
            receipt += f"▪️ {item.get('name')}  x{item.get('quantity')} — <b>{item.get('sum'):.2f} €</b>\n"
        receipt += f"\n💰 <b>Разом до сплати: {total:.2f} €</b>\n\n👨‍🍳 Бариста вже готує ваші напої!"
        await message.answer(receipt, parse_mode="HTML")

        admin_text = f"🔔 <b>НОВЕ ЗАМОВЛЕННЯ!</b>\nКлієнт: @{message.from_user.username or 'id_' + str(message.from_user.id)}\n\n"
        for item in items:
            admin_text += f"▪️ {item.get('name')} x{item.get('quantity')} ({item.get('sum'):.2f} €)\n"
        admin_text += f"\n💵 <b>Сума: {total:.2f} €</b>"
        await bot.send_message(chat_id=ADMIN_ID, text=admin_text, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Помилка: {e}")
        await message.answer("❌ Сталася помилка під час обробки замовлення.")

async def run_bot():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

async def run_api():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    database.init_db()
    await asyncio.gather(run_bot(), run_api())

if __name__ == "__main__":
    asyncio.run(main())