import json
import os
import sqlite3
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

DB_FILE = "balances.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            game_id TEXT PRIMARY KEY,
            balance REAL
        )
    ''')
    conn.commit()
    conn.close()

def get_balance(game_id):
    if not game_id:
        return 0.0
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    clean_id = str(game_id).strip()
    cursor.execute('SELECT balance FROM balances WHERE game_id = ?', (clean_id,))
    row = cursor.fetchone()
    conn.close()
    return float(row[0]) if row else 0.0

def update_balance(game_id, amount):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    clean_id = str(game_id).strip()
    
    cursor.execute('SELECT balance FROM balances WHERE game_id = ?', (clean_id,))
    row = cursor.fetchone()
    
    if row:
        new_bal = row[0] + float(amount)
        cursor.execute('UPDATE balances SET balance = ? WHERE game_id = ?', (new_bal, clean_id))
    else:
        cursor.execute('INSERT INTO balances (game_id, balance) VALUES (?, ?)', (clean_id, float(amount)))
        
    conn.commit()
    conn.close()

init_db()

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/balance"):
            import urllib.parse as up
            parsed_url = up.urlparse(self.path)
            query_params = up.parse_qs(parsed_url.query)
            game_id = query_params.get("game_id", [None])[0]
            balance = get_balance(game_id)
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

TOKEN = "8942662207:AAHSM8rvX7pBLTCLrXWY4OjfFZkEXxgE2yU"
ADMIN_ID = 5108777990
bot = telebot.TeleBot(TOKEN)
GAME_URL = "https://snatprosta-sketch.github.io/apple-game/"

user_data = {}
admin_state = {}

@bot.message_handler(commands=["start"])
def start(message):
    text = message.text 
    if "withdraw" in text:
        parts = text.split('_')
        game_id = parts[1] if len(parts) > 1 else ""
        amount = parts[2] if len(parts) > 2 else "0"
        user_data[message.from_user.id] = {"game_id": game_id, "withdraw_amount": amount, "step": "waiting_phone"}
        bot.send_message(message.chat.id, f"📤 **Дархости вывод**\n🆔 ID: `{game_id}`\n💰 Маблағ: {amount}\n\nЛутфан рақами телефонро нависед (+992...):", parse_mode="Markdown")
        return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎮 Бозӣ кардан", web_app=WebAppInfo(url=GAME_URL)))
    markup.add(InlineKeyboardButton("💳 Пополнить баланс", callback_data="deposit"))
    markup.add(InlineKeyboardButton("📤 Вывод", callback_data="withdraw_menu"))
    bot.send_message(message.chat.id, "Хуш омадед ба Apple Game Casino!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "deposit")
def deposit(call):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("DC (Dushanbe City)", callback_data="pay_dc"),
               InlineKeyboardButton("Alif Bank", callback_data="pay_alif"))
    bot.edit_message_text("Усули пардохтро интихоб кунед:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "withdraw_menu")
def withdraw_menu(call):
    user_data[call.from_user.id] = {"step": "bot_wd_game_id"}
    bot.edit_message_text("📤 Лутфан ID бозиатонро барои вывод нависед:", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data in ["pay_dc", "pay_alif"])
def payment_method(call):
    bank_name = "Dushanbe City" if call.data == "pay_dc" else "Alif Bank"
    card = "9762 0001 2684 9958" if call.data == "pay_dc" else "9876 5432 1098 7654"
    user_data[call.from_user.id] = {"bank_name": bank_name, "step": "waiting_game_id"}
    bot.edit_message_text(f"Бонк: {bank_name}\nКарта: `{card}`\n\nЛутфан ID бозиатонро нависед:", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "waiting_game_id")
def receive_game_id(message):
    user_data[message.from_user.id]["game_id"] = message.text.strip()
    user_data[message.from_user.id]["step"] = "waiting_photo"
    bot.reply_to(message, "✅ ID қабул шуд. Акнун скриншоти чекро фиристед!")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "bot_wd_game_id")
def bot_wd_game_id(message):
    game_id = message.text.strip()
    user_data[message.from_user.id]["game_id"] = game_id
    user_data[message.from_user.id]["step"] = "bot_wd_amount"
    bot.reply_to(message, f"🆔 ID: `{game_id}` қабул шуд.\n\nЛутфан миқдори маблағеро, ки мехоҳед вывод кунед, нависед:", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "bot_wd_amount")
def bot_wd_amount(message):
    try:
        amount = float(message.text.strip())
    except:
        bot.reply_to(message, "⚠️ Танҳо рақам нависед!")
        return
    user_data[message.from_user.id]["withdraw_amount"] = amount
    user_data[message.from_user.id]["step"] = "waiting_phone"
    bot.reply_to(message, "Лутфан рақами телефони худро нависед:")

@bot.message_handler(func=lambda m: m.from_user.id in user_data and user_data[m.from_user.id].get("step") == "waiting_phone")
def receive_withdraw_phone(message):
    user_id = message.from_user.id
    phone = message.text.strip()
    data = user_data[user_id]
    game_id = data["game_id"]
    amount = data["withdraw_amount"]
    current_balance = get_balance(game_id)
    
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(InlineKeyboardButton("✅ Тасдиқ", callback_data=f"approve_wd_{user_id}_{game_id}_{amount}"),
                     InlineKeyboardButton("❌ Рад", callback_data=f"reject_wd_{user_id}"))
    
    bot.send_message(
        ADMIN_ID, 
        f"📥 **Дархости ВЫВОД!**\n"
        f"🆔 ID: `{game_id}`\n"
        f"💰 Маблағи дархостӣ: {amount} сомонӣ\n"
        f"💳 Баланси умумии ин ID: `{current_balance}` сомонӣ\n"
        f"📞 Рақам: `{phone}`", 
        reply_markup=admin_markup, 
        parse_mode="Markdown"
    )
    
    bot.reply_to(message, "✅ Дархости вывод фиристода шуд! Интизор шавед.")
    user_data.pop(user_id, None)

@bot.message_handler(content_types=["photo"])
def receive_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id].get("step") != "waiting_photo":
        return
    game_id = user_data[user_id]["game_id"]
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(InlineKeyboardButton("✅ Тасдиқ ва илова", callback_data=f"approve_{user_id}_{game_id}"),
                     InlineKeyboardButton("❌ Рад кардан", callback_data=f"reject_{user_id}"))
    bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=f"📥 Чек аз {message.from_user.first_name}\nID Бозӣ: `{game_id}`", reply_markup=admin_markup, parse_mode="Markdown")
    bot.reply_to(message, "✅ Чек фиристода шуд, интизор шавед.")
    user_data.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith(("approve_", "reject_")))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID: return
    parts = call.data.split("_")
    
    if parts[1] == "wd":
        action = parts[0]
        user_id = int(parts[2])
        if action == "approve":
            game_id = parts[3]
            amount = float(parts[4])
            if get_balance(game_id) >= amount:
                update_balance(game_id, -amount)
            bot.send_message(user_id, f"✅ Вывод ({amount} смн) тасдиқ шуд!")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.caption + "\n\n✅ ВЫВОД ТАСДИҚ ШУД")
        else:
            bot.send_message(user_id, "❌ Вывод рад шуд.")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.caption + "\n\n❌ ВЫВОД РАД ШУД")
        return

    action, user_id = parts[0], int(parts[1])
    if action == "approve":
        game_id = parts[2]
        admin_state[ADMIN_ID] = {"target_user_id": user_id, "game_id": game_id, "message_id": call.message.message_id}
        bot.send_message(ADMIN_ID, f"✍️ Миқдори маблағро барои ID {game_id} нависед:")
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
    
    update_balance(game_id, amount)
    
    bot.send_message(state["target_user_id"], f"🎉 Чек тасдиқ шуд! {amount} сомонӣ илова гардид.")
    bot.edit_message_caption(chat_id=ADMIN_ID, message_id=state["message_id"], caption=message.caption + f"\n\n✅ ТАСДИҚ ШУД: {amount} сомонӣ" if message.caption else f"✅ ТАСДИҚ ШУД: {amount} сомонӣ")
    bot.reply_to(message, "✅ Баланс бо муваффақият нав карда шуд!")

bot.polling(none_stop=True)
    
