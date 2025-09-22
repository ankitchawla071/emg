

import os
import pandas as pd
import asyncio
from flask import Flask, request, jsonify, send_file
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

# ---------------- CONFIG ----------------
CSV_FILE = "data.csv"
THRESHOLD_FILE = "threshold.txt"
TELEGRAM_TOKEN = "8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w"
CHAT_ID = "802173334"        

# Default threshold
if not os.path.exists(THRESHOLD_FILE):
    with open(THRESHOLD_FILE, "w") as f:
        f.write("32")  # default threshold 32°C

# ---------------- FLASK -----------------
app = Flask(__name__)

# Keep track of last alert sent to avoid spamming
last_alert_sent = False

@app.route('/data', methods=['POST'])
def post_data():
    global last_alert_sent
    content = request.get_json()
    temp = float(content.get("temp"))
    health = content.get("health", "Unknown")

    # Save to CSV
    df = pd.DataFrame([[pd.Timestamp.now(), temp, health]], columns=["datetime","temp","health"])
    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, index=False, mode='a', header=False)

    # Check threshold
    with open(THRESHOLD_FILE) as f:
        threshold = float(f.read().strip())
    
    if temp >= threshold and not last_alert_sent:
        last_alert_sent = True
        asyncio.create_task(send_telegram_alert(temp, threshold))
    elif temp < threshold:
        last_alert_sent = False

    return jsonify({"status":"ok"})

@app.route('/data', methods=['GET'])
def get_data():
    if not os.path.exists(CSV_FILE):
        return jsonify({"temp":0, "health":"No Data"})
    df = pd.read_csv(CSV_FILE)
    last = df.iloc[-1]
    return jsonify({"temp": last["temp"], "health": last["health"]})

@app.route('/history', methods=['GET'])
def get_history():
    if not os.path.exists(CSV_FILE):
        return jsonify([])
    df = pd.read_csv(CSV_FILE)
    return jsonify(df.to_dict(orient="records"))

@app.route('/download', methods=['GET'])
def download_csv():
    if not os.path.exists(CSV_FILE):
        return "No data yet"
    return send_file(CSV_FILE, as_attachment=True)

# ---------------- TELEGRAM BOT -----------------
bot = Bot(token=TELEGRAM_TOKEN)

async def send_telegram_alert(temp, threshold):
    await bot.send_message(chat_id=CHAT_ID,
                           text=f"🚨 ALERT: Temp {temp:.1f}°C exceeded threshold {threshold}°C!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📊 Current Status", callback_data='status')],
        [InlineKeyboardButton("⬇️ Download CSV", callback_data='csv')],
        [InlineKeyboardButton("⚙️ Change Threshold", callback_data='threshold')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Welcome to KOD Pump Bot", reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'status':
        if not os.path.exists(CSV_FILE):
            await query.edit_message_text(text="No data yet.")
        else:
            df = pd.read_csv(CSV_FILE)
            last = df.iloc[-1]
            with open(THRESHOLD_FILE) as f:
                threshold = float(f.read().strip())
            await query.edit_message_text(
                text=f"Current Temp: {last['temp']:.1f}°C\nHealth: {last['health']}\nThreshold: {threshold}°C"
            )
    elif query.data == 'csv':
        if not os.path.exists(CSV_FILE):
            await query.edit_message_text(text="No CSV file yet.")
        else:
            await context.bot.send_document(chat_id=query.from_user.id,
                                            document=open(CSV_FILE,'rb'),
                                            filename='data.csv')
    elif query.data == 'threshold':
        await query.edit_message_text(text="Send me new threshold value (°C). Example: 35")

async def change_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_threshold = float(update.message.text)
        with open(THRESHOLD_FILE,"w") as f:
            f.write(str(new_threshold))
        await update.message.reply_text(f"✅ Threshold changed to {new_threshold}°C")
    except:
        await update.message.reply_text("Send a valid number")

def run_telegram():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("setthreshold", change_threshold))
    application.run_polling()

# Start telegram bot in a separate thread
threading.Thread(target=run_telegram, daemon=True).start()

# ---------------- RUN FLASK -----------------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv("PORT",5050)))
