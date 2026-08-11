import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Веб-сервери хурд барои Render то хатогии Timed out набарояд
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Серверро дар замина ба кор медарорем
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Коди боти шумо
TOKEN = "8942662207:AAHSM8rvX7pBLTCLrXWY40jf..."
ADMIN_ID = 5108777990

bot = telebot.TeleBot(TOKEN)
GAME_URL = "https://snatprosta-sketch.github.io/apple-game/"

@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    btn_game = InlineKeyboardButton(
        "🎮 Бозӣ кардан", web_app=WebAppInfo(url=GAME_URL)
    )
    btn_deposit = InlineKeyboardButton(
        "💳 Пополнить баланс", callback_data="deposit"
    )
    markup.add(btn_game)
    markup.add(btn_deposit)
    bot.send_message(
        message.chat.id,
        "Хуш омадед ба Apple Game Casino! Бозӣ кунед:",
        reply_markup=markup,
    )

bot.infinity_polling()
