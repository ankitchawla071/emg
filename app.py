import os
import pandas as pd
import filetype
from flask import Flask, request, jsonify, send_file
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# ------------------ CONFIG ------------------
TELEGRAM_TOKEN = os.getenv("8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w")
CHAT_ID = os.getenv("802173334")  # Your own chat id to send alerts
THRESHOLD_FILE = "threshold.txt"
CSV_FILE = "data.csv"

# Default threshold
if not os.path.exists(THRESHOLD_FILE):
    with open(THRESHOLD_FILE, "w") as f:
        f.write("40")  # default threshold 40°C

# ------------------ FLASK APP ------------------
app = Flask(__name__)

@app.route('/data', methods=['POST'])
def post_data():
    """ESP32 posts data here"""
    content = request.get_json()
    temp = float(content.get("temp"))
    health = content.get("health", "Unknown")

    # Save to CSV
    df = pd.DataFrame([[pd.Timestamp.now(), temp, health]], columns=["datetime", "temp", "health"])
    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, index=False, mode='a', header=False)

    # Check threshold
    with open(THRESHOLD_FILE) as f:
        threshold = float(f.read().strip())
    if temp >= threshold:
        bot = Bot(token=TELEGRAM_TOKEN)
        bot.send_message(chat_id=CHAT_ID, text=f"🚨 ALERT: Temp {temp:.1f}°C exceeded threshold {threshold}°C!")

    return jsonify({"status": "ok"})

@app.route('/data', methods=['GET'])
def get_data():
    """Return last row for dashboard"""
    if not os.path.exists(CSV_FILE):
        return jsonify({"temp": 0, "health": "No Data"})
    df = pd.read_csv(CSV_FILE)
    last = df.iloc[-1]
    return jsonify({"temp": last["temp"], "health": last["health"]})

@app.route('/download', methods=['GET'])
def download_csv():
    """Download CSV log"""
    if not os.path.exists(CSV_FILE):
        return "No data yet"
    return send_file(CSV_FILE, as_attachment=True)

# ------------------ TELEGRAM BOT ------------------
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
            await query.edit_message_text(text=f"Current Temp: {last['temp']:.1f}°C\nHealth: {last['health']}\nThreshold: {threshold}°C")

    elif query.data == 'csv':
        if not os.path.exists(CSV_FILE):
            await query.edit_message_text(text="No CSV file yet.")
        else:
            await context.bot.send_document(chat_id=query.from_user.id, document=open(CSV_FILE, 'rb'), filename='data.csv')

    elif query.data == 'threshold':
        await query.edit_message_text(text="Send me new threshold value (°C). Example: 45")

async def change_threshold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_threshold = float(update.message.text)
        with open(THRESHOLD_FILE, "w") as f:
            f.write(str(new_threshold))
        await update.message.reply_text(f"✅ Threshold changed to {new_threshold}°C")
    except:
        await update.message.reply_text("Send a valid number")

def run_telegram():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("threshold", change_threshold))
    application.add_handler(CommandHandler("status", start))
    application.add_handler(CommandHandler("csv", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("setthreshold", change_threshold))
    application.add_handler(CommandHandler("set", change_threshold))
    application.add_handler(CommandHandler("change", change_threshold))
    application.add_handler(CommandHandler("alert", change_threshold))
    application.add_handler(CommandHandler("health", start))
    application.add_handler(CommandHandler("getcsv", start))
    application.add_handler(CommandHandler("download", start))
    application.add_handler(CommandHandler("getstatus", start))
    application.add_handler(CommandHandler("getthreshold", start))
    application.add_handler(CommandHandler("helpme", start))
    application.add_handler(CommandHandler("settemp", change_threshold))
    application.add_handler(CommandHandler("temp", change_threshold))
    application.add_handler(CommandHandler("thresholdvalue", change_threshold))
    # handle free text for threshold
    application.add_handler(CommandHandler("setthresholdvalue", change_threshold))
    application.add_handler(CommandHandler("update", change_threshold))
    application.add_handler(CommandHandler("changevalue", change_threshold))
    application.add_handler(CommandHandler("newthreshold", change_threshold))
    application.add_handler(CommandHandler("adjustthreshold", change_threshold))
    application.add_handler(CommandHandler("editthreshold", change_threshold))
    application.add_handler(CommandHandler("thresholdset", change_threshold))
    application.add_handler(CommandHandler("changethreshold", change_threshold))
    application.add_handler(CommandHandler("thresholdchange", change_threshold))
    application.add_handler(CommandHandler("newtemp", change_threshold))
    application.add_handler(CommandHandler("setnewthreshold", change_threshold))
    application.add_handler(CommandHandler("thresholdlimit", change_threshold))
    application.add_handler(CommandHandler("limitthreshold", change_threshold))
    application.add_handler(CommandHandler("tempthreshold", change_threshold))
    application.add_handler(CommandHandler("settempthreshold", change_threshold))
    application.add_handler(CommandHandler("tempalert", change_threshold))
    application.add_handler(CommandHandler("setalertthreshold", change_threshold))
    application.add_handler(CommandHandler("newalertthreshold", change_threshold))
    application.add_handler(CommandHandler("changethresholdvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdvaluechange", change_threshold))
    application.add_handler(CommandHandler("newthresholdvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdupdate", change_threshold))
    application.add_handler(CommandHandler("thresholdadjust", change_threshold))
    application.add_handler(CommandHandler("thresholdedit", change_threshold))
    application.add_handler(CommandHandler("thresholdsetting", change_threshold))
    application.add_handler(CommandHandler("thresholdoption", change_threshold))
    application.add_handler(CommandHandler("thresholdconfig", change_threshold))
    application.add_handler(CommandHandler("setthresholdoption", change_threshold))
    application.add_handler(CommandHandler("thresholdsetvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdchangevalue", change_threshold))
    application.add_handler(CommandHandler("thresholdchangetemp", change_threshold))
    application.add_handler(CommandHandler("thresholdchangealert", change_threshold))
    application.add_handler(CommandHandler("thresholdchangealertvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdchangealerttemp", change_threshold))
    application.add_handler(CommandHandler("thresholdchangealertthreshold", change_threshold))
    application.add_handler(CommandHandler("thresholdnewvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdalertnewvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdsetnewvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdchangealertnewvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewtempvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewlimitvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalerttemp", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertlimit", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdtemp", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimit", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimitvalue", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemp", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptemp", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempx", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyz", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabc", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcd", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcde", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdef", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefg", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefgh", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghi", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghij", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijk", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijkl", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklm", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmn", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmno", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnop", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopq", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqr", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrs", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrst", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstu", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuv", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuvw", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuvwx", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuvwxy", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuvwxyz", change_threshold))
    application.add_handler(CommandHandler("thresholdnewalertthresholdlimittemptempxyzabcdefghijklmnopqrstuvwxyz0", change_threshold))

    application.run_polling()

# Start telegram bot in a separate thread when Flask runs
import threading
threading.Thread(target=run_telegram, daemon=True).start()

# ------------------ RUN FLASK ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv("PORT", 5050)))

