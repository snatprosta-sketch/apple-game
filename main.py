import os
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
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

# Веб-сервери хурд барои Render ва гирифтани баланс тавассути бозӣ (Web App)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # API барои гирифтани баланси корбар аз бозӣ: /balance?game_id=12345
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
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)
            return

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

# Токени бот ва ID-и админ
TOKEN = "8942662207:AAHSM8rvX7pBLTCLrXWY4OjfFZkEXxgE2yU"
ADMIN_ID = 5108777990

bot = telebot.TeleBot(TOKEN)
GAME_URL = "https://snatprosta-sketch.github.io/apple-game/"

# Холатҳои муваққатии корбарон ва админ
user_data = {}
admin_state = {}

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

    # Захира кардани ҳолат то корбар ID бозиашро нависад
    user_data[call.from_user.id] = {
        "bank_name": bank_name,
        "step": "waiting_game_id"
    }

    text = (
        f"Бонки интихобшуда: **{bank_name}**\n"
        f"Рақами карта:\n`{card_number}`\n\n"
        "✍️ **Қадами 1:** Лутфан **ID бозии худро** (рақами ID-и дар дохили бозӣ доштаатонро) ба инҷо нависед ва фиристед:"
    )
    bot.edit_message_text(
        text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )

@bot.message_handler(func=lambda message: message.from_user.id in user_data and user_data[message.from_user.id].get("step") == "waiting_game_id")
def receive_game_id(message):
    game_id = message.text.strip()
    user_data[message.from_user.id]["game_id"] = game_id
    user_data[message.from_user.id]["step"] = "waiting_photo"

    bot.reply_to(
        message,
        f"✅ ID бозии шумо қабул шуд: `{game_id}`\n\n"
        "📸 **Қадами 2:** Акнун скриншоти чеки пардохтро ба ҳаминҷо фиристед!",
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=["photo"])
def receive_photo(message):
    user_id = message.from_user.id
    if user_id not in user_data or user_data[user_id].get("step") != "waiting_photo":
        bot.reply_to(message, "Лутфан аввал тугмаи «Пополнить баланс»-ро пахш кунед ва усули пардохтро интихоб намоед.")
        return

    game_id = user_data[user_id].get("game_id", "Номаълум")
    bank_name = user_data[user_id].get("bank_name", "Банк")
    photo_id = message.photo[-1].file_id

    admin_markup = InlineKeyboardMarkup()
    btn_approve = InlineKeyboardButton("✅ Тасдиқ ва илова ба баланс", callback_data=f"approve_{user_id}_{game_id}")
    btn_reject = InlineKeyboardButton("❌ Рад кардан", callback_data=f"reject_{user_id}")
    admin_markup.add(btn_approve, btn_reject)

    bot.send_photo(
        ADMIN_ID,
        photo_id,
        caption=(
            f"📥 **Чек аз муштарӣ!**\n"
            f"Ном: {message.from_user.first_name}\n"
            f"Telegram ID: `{user_id}`\n"
            f"🎮 **ID Бозӣ:** `{game_id}`\n"
            f"Бонк: {bank_name}\n\n"
            f"⚠️ *Барои илова кардани маблағ, тугмаи сабзро зер кунед.*"
        ),
        reply_markup=admin_markup,
        parse_mode="Markdown",
    )
    bot.reply_to(
        message,
        "✅ Чек ва ID бозии шумо қабул шуд! Администратор чекро санҷида истодааст. Лутфан интизор шавед.",
    )
    user_data.pop(user_id, None)

@bot.callback_query_handler(func=lambda call: call.data.startswith("approve_") or call.data.startswith("reject_"))
def admin_decision(call):
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Шумо ҳуқуқи иҷрои ин амалро надоред!", show_alert=True)
        return

    parts = call.data.split("_")
    action = parts[0]
    target_user_id = int(parts[1])

    if action == "approve":
        game_id = parts[2]
        admin_state[ADMIN_ID] = {
            "target_user_id": target_user_id,
            "game_id": game_id,
            "message_id": call.message.message_id
        }
        bot.answer_callback_query(call.id, "Лутфан маблағро нависед")
        bot.send_message(
            ADMIN_ID,
            f"✍️ Лутфан миқдори маблағеро (бо сомонӣ), ки бояд ба ID бозии **{game_id}** илова шавад, бо рақам нависед (масалан: `50`):",
            parse_mode="Markdown"
        )
    elif action == "reject":
        bot.answer_callback_query(call.id, "Пардохт рад карда шуд.")
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

# Қабули маблағ аз админ ва автоматӣ илова ба баланс
@bot.message_handler(func=lambda message: message.from_user.id == ADMIN_ID and ADMIN_ID in admin_state)
def admin_enter_amount(message):
    try:
        amount = float(message.text.strip())
    except ValueError:
        bot.reply_to(message, "⚠️ Лутфан танҳо рақам нависед (масалан: 50 ё 100):")
        return

    state = admin_state.pop(ADMIN_ID)
    target_user_id = state["target_user_id"]
    game_id = state["game_id"]
    msg_id = state["message_id"]

    # Илова кардани маблағ ба баланси файлии сервер
    balances = load_balances()
    current_balance = balances.get(str(game_id), 0)
    new_balance = current_balance + amount
    balances[str(game_id)] = new_balance
    save_balances(balances)

    # Нав кардани хабари админ
    try:
        bot.edit_message_caption(
            chat_id=ADMIN_ID,
            message_id=msg_id,
            caption=f"✅ **ҲОЛАТ: ТАСДИҚ ШУД**\n💰 Маблағи иловашуда: **{amount} сомонӣ**\n🎮 ID Бозӣ: `{game_id}`",
            parse_mode="Markdown",
        )
    except:
        pass

    bot.reply_to(message, f"✅ Муваффақият! {amount} сомонӣ ба ID бозии `{game_id}` илова шуд. Баланси умумии ин ID: {new_balance} сом.", parse_mode="Markdown")
    
    # Хабар додан ба худи корбар
    bot.send_message(
        target_user_id,
        f"🎉 Чек тасдиқ шуд! Ба миқдори **{amount} сомонӣ** ба баланси бозии шумо (ID: `{game_id}`) илова гардид. Баланси нави шумо: **{new_balance} сомонӣ**.",
        parse_mode="Markdown",
    )

bot.polling(none_stop=True)
    
