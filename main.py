import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

# Файли нигоҳдории балансҳо дар сервер
BALANCES_FILE = "balances.json"

def load_balances():
    if os.path.exists(BALANCES_FILE):
        try:
            with open(BALANCES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_balances(balances):
    with open(BALANCES_FILE, "w", encoding="utf-8") as f:
        json.dump(balances, f, ensure_ascii=False, indent=4)

# Веб-сервер барои Render (барои бозӣ)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/balance"):
            import urllib.parse as up
            parsed_url = up.urlparse(self.path)
            query_params = up.parse_qs(parsed_url.query)
            game_id = query_params.get("game_id", [None])[0]
            balances = load_balances()
            balance = balances.get(str(game_id), 0)
            response = json.dumps({"balance": balance}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(response)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args): pass

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# Танзимоти Бот
TOKEN = "8942662207:AAHSM8rvX7pBLTCLrXWY4OjfFZkEXxgE2yU"
ADMIN_ID = 5108777990
bot = telebot.TeleBot(TOKEN)
GAME_URL = "https://snatprosta-sketch.github.io/apple-game/"

user_data = {}
admin_state = {}

@bot.message_handler(commands=["start"])
def start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎮 Бозӣ кардан", web_app=WebAppInfo(url=GAME_URL)))
    markup.add(InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit"))
    bot.send_message(message.chat.id, "Хуш омадед ба Apple Game Casino!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def deposit(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("DC (Dushanbe City)", callback_data="pay_dc"),
               InlineKeyboardButton("Alif Bank", callback_data="pay_alif"))
    bot.edit_message_text("Усули пардохтро интихоб кунед:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data in ["pay_dc", "pay_alif"])
def payment_method(call):
    bank_name = "Dushanbe City" if call.data == "pay_dc" else "Alif Bank"
    card = "9762 0001 2684 9958" if call.data == "pay_dc" else "9876 5432 1098 7654"
    user_data[call.from_user.id] = {"bank_name": bank_name, "step": "waiting_game_id"}
    bot.edit_message_text(f"Бонк: {bank_name}\nРақами карта: `{card}`\n\nЛутфан ID бозиатонро нависед:", 
                          call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "waiting_game_id")
def receive_game_id(message):
    user_data[message.from_user.id]["game_id"] = message.text.strip()
    user_data[message.from_user.id]["step"] = "waiting_photo"
    bot.reply_to(message, "✅ ID қабул шуд. Акнун скриншоти чекро фиристед!")

@bot.message_handler(content_types=["photo"])
def receive_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id].get("step") != "waiting_photo":
        return
    game_id = user_data[user_id]["game_id"]
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(InlineKeyboardButton("✅ Тасдиқ ва илова", callback_data=f"approve_{user_id}_{game_id}"),
                     InlineKeyboardButton("❌ Рад кардан", callback_data=f"reject_{user_id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, 
                   caption=f"📥 Чек аз {message.from_user.first_name}\nID Бозӣ: `{game_id}`", 
                   reply_markup=admin_markup, parse_mode="Markdown")
    bot.reply_to(message, "✅ Чек фиристода шуд, интизор шавед.")
    user_data.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    action, user_id = parts[0], int(parts[1])
    if action == "approve":
        game_id = parts[2]
        admin_state[ADMIN_ID] = {"target_user_id": user_id, "game_id": game_id, "message_id": call.message.message_id}
        bot.send_message(ADMIN_ID, f"✍️ Лутфан миқдори маблағро барои ID {game_id} нависед:")
    else:
        bot.send_message(user_id, "❌ Чек рад карда шуд.")
        bot.edit_message_caption(chat_id=ADMIN_ID, message_id=call.message.message_id, caption=call.message.caption + "\n\n❌ РАД ШУД")

@bot.message_handler(func=lambda m: m.from_user.id == ADMIN_ID and ADMIN_ID in admin_state)
def admin_enter_amount(message):
    try:
        amount = float(message.text.strip())
    except:
        bot.reply_to(message, "⚠️ Танҳо рақам нависед!")
        return
    
    state = admin_state.pop(ADMIN_ID)
    game_id = state["game_id"]
    balances = load_balances()
    balances[game_id] = balances.get(str(game_id), 0) + amount
    save_balances(balances)
    
    bot.send_message(state["target_user_id"], f"🎉 Чек тасдиқ шуд! {amount} сомонӣ илова гардид.")
    bot.edit_message_caption(chat_id=ADMIN_ID, message_id=state["message_id"], caption=f"✅ ТАСДИҚ ШУД: {amount} сомонӣ")
    bot.reply_to(message, "✅ Муваффақият! Баланс нав карда шуд.")

bot.polling(none_stop=True)
