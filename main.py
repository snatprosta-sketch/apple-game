import os
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Веб-сервери хурд барои Render то хатогии Timed out набарояд
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        response = b"Bot is running!"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
        
    def log_message(self, format, *args):
        pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Коди боти шумо
TOKEN = "8942662207:AAHSM8rvX7pBLTCLrXWY4OjfFZkEXxgE2yU"
ADMIN_ID = 5108777990

bot = telebot.TeleBot(TOKEN)
GAME_URL = "https://snatprosta-sketch.github.io/apple-game/"


@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    btn_game = InlineKeyboardButton("🎮 Бозӣ кардан", web_app=WebAppInfo(url=GAME_URL))
    btn_deposit = InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit")
    markup.add(btn_game)
    markup.add(btn_deposit)
    bot.send_message(
        message.chat.id,
        "Хуш омадед ба Apple Game Casino! Бозӣ кунед ва баъд балансатонро пур кунед:",
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def deposit(call):
    markup = InlineKeyboardMarkup()
    btn1 = InlineKeyboardButton("DC (Dushanbe City)", callback_data="pay_dc")
    btn2 = InlineKeyboardButton("Alif Bank", callback_data="pay_alif")
    markup.add(btn1, btn2)
    bot.edit_message_text(
        "Усули пардохтро интихоб кунед:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=markup,
    )


@bot.callback_query_handler(func=lambda call: call.data in ["pay_dc", "pay_alif"])
def payment_method(call):
    if call.data == "pay_dc":
        bank_name = "Dushanbe City"
        card_number = "9762 0001 2684 9958"
    else:
        bank_name = "Alif Bank"
        card_number = "9876 5432 1098 7654"

    text = (
        f"Бонки интихобшуда: **{bank_name}**\n\n"
        f"Рақами карта:\n`{card_number}`\n\n"
        "⏱ **Диққат!** Шумо то **5 дақиқа** вақт доред, ки маблағро гузаронед.\n"
        "Пас аз гузаронидани маблағ, скриншоти чекро ба ҳаминҷо фиристед!"
    )
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )


@bot.message_handler(content_types=["photo"])
def receive_photo(message):
    user = message.from_user
    photo_id = message.photo[-1].file_id

    admin_markup = InlineKeyboardMarkup()
    btn_approve = InlineKeyboardButton("✅ Тасдиқ (Пур кардан)", callback_data=f"approve_{user.id}")
    btn_reject = InlineKeyboardButton("❌ Рад кардан", callback_data=f"reject_{user.id}")
    admin_markup.add(btn_approve, btn_reject)

    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=f"📥 **Чек аз муштарӣ!**\nНом: {user.first_name}\nID: `{user.id}`",
        reply_markup=admin_markup,
        parse_mode="Markdown",
    )
    bot.reply_to(
        message,
        "✅ Чек қабул шуд! Администратор онро тафтиш карда истодааст. Лутфан интизор шавед.",
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Шумо ҳуқуқи иҷрои ин амалро надоред!", show_alert=True)
        return

    action, target_user_id = call.data.split("_")
    target_user_id = int(target_user_id)

    if action == "approve":
        bot.answer_callback_query(call.id, "Пардохт тасдиқ шуд!")
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n✅ **ҲОЛАТ: ТАСДИҚ ШУД**",
            parse_mode="Markdown",
        )
        bot.send_message(
            target_user_id,
            "✅ Чек тасдиқ шуд! Баланси шумо бомуваффақият пур карда шуд. 🎉",
        )
    elif action == "reject":
        bot.answer_callback_query(call.id, "Пардохт рад карда шуд!")
        bot.edit_message_caption(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            caption=call.message.caption + "\n\n❌ **ҲОЛАТ: РАД ШУД (Чек нодуруст)**",
            parse_mode="Markdown",
        )
        bot.send_message(
            target_user_id,
            "❌ Чек рад карда шуд ё нодуруст аст. Маблағ ба баланс ворид нашуд.",
        )


bot.polling(none_stop=True)
