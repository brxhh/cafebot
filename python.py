import asyncio
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8682577922:AAEjHCq4lZuntpfE3Ol3lQuSXHaOdmEJ9Zo'
WEB_APP_URL = 'https://your-site.github.io/coffee-menu/'

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start_command(message: types.Message):
    markup = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open Menu ☕️", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    await message.answer("Welcome to our coffee shop! Click the button below to place an order.",
                         reply_markup=markup)

@dp.message(lambda message: message.web_app_data)
async def web_app_handler(message: types.Message):
    try:
        data = json.loads(message.web_app_data.data)
        product = data.get('product')
        qty = data.get('quantity')
        total = data.get('totalPrice')

        response_text = f"✅ <b>Order accepted!</b>\n\nDrink: {product}\nQuantity: {qty}\nTotal to pay: €{total}\n\nThe barista has started preparing your order!"

        await message.answer(response_text, parse_mode="HTML")
    except Exception as e:
        await message.answer("An error occurred while processing your order.")

async def main():
    print("Bot is running...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())