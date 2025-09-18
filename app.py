#!/usr/bin/env python3
# app.py
import os
import csv
import json
import threading
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file, abort
import requests
from io import BytesIO
from functools import wraps
from threading import Lock

# Telegram imports (python-telegram-bot v13)
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext

# -------- CONFIG & FILES --------
CSV_FILE = os.path.join(os.path.dirname(__file__), "data.csv")
SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
# threshold default if not present in env or settings
DEFAULT_THRESHOLD = float(os.environ.get("THRESHOLD", 32.0))

BOT_TOKEN = os.environ.get("8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w")  
ADMIN_CHAT_ID = os.environ.get("802173334")  

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable must be set (get from BotFather)")

# Flask app
app = Flask(__name__)

# In-memory last reading/state (thread-safe)
state_lock = Lock()
last_reading = {"temp": None, "health": "Unknown", "timestamp": None}
# alert flags to avoid repeat spam
alert_flags = {"bad_sent": False, "abnormal_sent": False}

# ensure settings persistence
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"threshold": DEFAULT_THRESHOLD}

def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f)

settings = load_settings()

# Ensure CSV has header
def ensure_csv_header():
    write_header = not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0
    if write_header:
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["DateTime", "Temperature", "Health"])

ensure_csv_header()

# Logging helper (thread-safe)
csv_lock = Lock()
def append_csv(ts, temp, health):
    with csv_lock:
        write_header = not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(["DateTime", "Temperature", "Health"])
            writer.writerow([ts, f"{temp:.4f}", health])

# Determine health given temp and threshold
def compute_health(temp, threshold):
    if temp is None:
        return "Unknown"
    abnormal_low = threshold * 0.8
    if temp > threshold:
        return "Bad"
    elif temp >= abnormal_low:
        return "Abnormal"
    else:
        return "Good"

# Telegram helper
bot = Bot(token=BOT_TOKEN)

def send_telegram_message(text, chat_id=None):
    try:
        target = int(chat_id) if chat_id else (int(ADMIN_CHAT_ID) if ADMIN_CHAT_ID else None)
        if target is None:
            print("No chat specified and ADMIN_CHAT_ID not set; cannot send Telegram message.")
            return False
        bot.send_message(chat_id=target, text=text)
        return True
    except Exception as e:
        print("Error sending telegram message:", e)
        return False

def send_csv_to_chat(chat_id):
    # Reads CSV and sends as document
    try:
        with open(CSV_FILE, "rb") as f:
            bot.send_document(chat_id=chat_id, document=f, filename="temperature_log.csv")
        return True
    except Exception as e:
        print("Error sending CSV:", e)
        return False

# Authorization decorator for sensitive commands (optional)
def restricted(func):
    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = str(update.effective_user.id)
        if ADMIN_CHAT_ID and user_id != str(ADMIN_CHAT_ID):
            update.message.reply_text("You are not authorized to perform this action.")
            return
        return func(update, context, *args, **kwargs)
    return wrapped

# -------- Flask endpoints --------

# Dashboard HTML (your Chart.js HTML integrated, loads /history and /data)
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>KOD Pump Monitoring</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body style="font-family: Arial; text-align:center; padding:20px;">
<h2>KOD Pump Monitoring</h2>
<p id="health" style="font-weight:bold; font-size:18px;">Health: Loading...</p>
<canvas id="tempChart" width="400" height="200"></canvas>

<script>
const ctx = document.getElementById('tempChart').getContext('2d');
const tempChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Temperature (°C)',
            data: [],
            borderColor: 'blue',
            borderWidth: 2,
            fill: false,
            tension: 0.1
        }]
    },
    options: {
        animation: false,
        responsive: true,
        scales: { y: { beginAtZero:false } }
    }
});

// load history on startup
async function loadHistory() {
    try {
        const res = await fetch('/history');
        const arr = await res.json();
        arr.forEach(d => {
            tempChart.data.labels.push(d.time.split(' ')[1]);
            tempChart.data.datasets[0].data.push(d.temp);
        });
        tempChart.update();
    } catch(e) { console.error("Error loading history:", e); }
}

async function updateLive() {
    try {
        const res = await fetch('/data');
        const data = await res.json();
        document.getElementById("health").innerText =
            "Health: " + data.health + " (" + data.temp.toFixed(1) + "°C)";

        const now = new Date().toLocaleTimeString();
        tempChart.data.labels.push(now);
        tempChart.data.datasets[0].data.push(data.temp);
        if(tempChart.data.labels.length > 50){
            tempChart.data.labels.shift();
            tempChart.data.datasets[0].data.shift();
        }
        tempChart.update();
    } catch(e) { console.error("Error fetching live data:", e); }
}

loadHistory();
setInterval(updateLive, 2000);
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route("/history", methods=["GET"])
def history():
    # return all rows (bounded to prevent huge loads)
    rows = []
    try:
        with open(CSV_FILE, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    rows.append({"time": row["DateTime"], "temp": float(row["Temperature"]), "health": row.get("Health","")})
                except:
                    continue
    except FileNotFoundError:
        pass
    # send last N rows (safe)
    N = 10000
    return jsonify(rows[-N:])

@app.route("/data", methods=["POST","GET"])
def data_endpoint():
    # POST from ESP32: {"temp":31.3, "device":"KOD"}
    if request.method == "POST":
        payload = request.get_json(force=True, silent=True)
        if not payload or "temp" not in payload:
            return jsonify({"error":"bad payload"}), 400
        temp = float(payload.get("temp"))
        device = payload.get("device", "unknown")

        threshold = settings.get("threshold", DEFAULT_THRESHOLD)
        health = compute_health(temp, threshold)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # update in-memory last reading
        with state_lock:
            last_reading["temp"] = temp
            last_reading["health"] = health
            last_reading["timestamp"] = ts

        # append to csv
        append_csv(ts, temp, health)

        # trigger telegram alerts with de-bounce logic
        with state_lock:
            # compute flags
            abnormal_low = threshold * 0.8
            # Bad alert
            if health == "Bad" and not alert_flags["bad_sent"]:
                text = f"⚠️ *ALERT*: {device} temperature {temp:.1f}°C exceeded threshold {threshold:.1f}°C — STATE: BAD"
                send_telegram_message(text)
                alert_flags["bad_sent"] = True
                alert_flags["abnormal_sent"] = False  # reset other flag
            # Abnormal alert
            elif health == "Abnormal" and not alert_flags["abnormal_sent"]:
                text = f"⚠️ *Warning*: {device} temperature {temp:.1f}°C in abnormal zone (≥ {abnormal_low:.1f}°C)."
                send_telegram_message(text)
                alert_flags["abnormal_sent"] = True
                alert_flags["bad_sent"] = False
            # Back to Good resets flags
            elif health == "Good":
                # If previously bad/abnormal, notify recovery optionally
                if alert_flags["bad_sent"] or alert_flags["abnormal_sent"]:
                    send_telegram_message(f"ℹ️ {device} recovered: {temp:.1f}°C (Good).")
                alert_flags["bad_sent"] = False
                alert_flags["abnormal_sent"] = False

        return jsonify({"status":"ok"}), 201

    # GET (used by dashboard JS) -> return current last reading
    with state_lock:
        resp = {
            "temp": (last_reading["temp"] if last_reading["temp"] is not None else 0.0),
            "health": (last_reading["health"] if last_reading["health"] else "Unknown"),
            "timestamp": last_reading["timestamp"]
        }
    return jsonify(resp)

# Download CSV route for browser (optional)
@app.route("/download", methods=["GET"])
def download_csv():
    if not os.path.exists(CSV_FILE):
        return abort(404)
    return send_file(CSV_FILE, mimetype='text/csv', as_attachment=True, attachment_filename="temperature_log.csv")

# -------- Telegram Bot (runs in background using polling) --------

def start_bot():
    # use Updater for long polling
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    def cmd_start(update: Update, context: CallbackContext):
        kb = [
            [InlineKeyboardButton("Current Status", callback_data="status")],
            [InlineKeyboardButton("Download CSV", callback_data="download")],
            [InlineKeyboardButton("Set Threshold", callback_data="setthreshold")]
        ]
        update.message.reply_text("KOD Pump Bot — choose an action:", reply_markup=InlineKeyboardMarkup(kb))

    def cmd_status(update: Update, context: CallbackContext):
        with state_lock:
            temp = last_reading.get("temp")
            health = last_reading.get("health")
            ts = last_reading.get("timestamp")
        if temp is None:
            update.message.reply_text("No readings yet.")
            return
        update.message.reply_text(f"Current: {temp:.1f}°C | Health: {health} | at {ts}")

    @restricted
    def cmd_setthreshold(update: Update, context: CallbackContext):
        # usage: /setthreshold 30
        args = context.args
        if not args:
            update.message.reply_text(f"Current threshold: {settings.get('threshold', DEFAULT_THRESHOLD)}. Usage: /setthreshold <value>")
            return
        try:
            val = float(args[0])
            settings['threshold'] = val
            save_settings(settings)
            update.message.reply_text(f"Threshold updated to {val:.2f}°C")
        except:
            update.message.reply_text("Invalid value. Example: /setthreshold 32")

    def cmd_download(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        update.message.reply_text("Preparing CSV... sending now.")
        success = send_csv_to_chat(chat_id)
        if not success:
            update.message.reply_text("Failed to send CSV.")

    def callback_query_handler(update: Update, context: CallbackContext):
        query = update.callback_query
        data = query.data
        chat_id = query.message.chat_id
        if data == "status":
            with state_lock:
                temp = last_reading.get("temp")
                health = last_reading.get("health")
                ts = last_reading.get("timestamp")
            if temp is None:
                query.answer()
                query.message.reply_text("No readings yet.")
            else:
                query.answer()
                query.message.reply_text(f"Current: {temp:.1f}°C | Health: {health} | at {ts}")
        elif data == "download":
            query.answer("Preparing CSV...")
            send_csv_to_chat(chat_id)
        elif data == "setthreshold":
            query.answer()
            query.message.reply_text("Use command: /setthreshold <value>  (e.g. /setthreshold 32)")

    # register handlers
    dp.add_handler(CommandHandler("start", cmd_start))
    dp.add_handler(CommandHandler("status", cmd_status))
    dp.add_handler(CommandHandler("setthreshold", cmd_setthreshold, pass_args=True))
    dp.add_handler(CommandHandler("download", cmd_download))
    dp.add_handler(CallbackQueryHandler(callback_query_handler))

    # start polling
    updater.start_polling()
    print("Telegram bot started (polling).")
    updater.idle()

# Start bot in background thread
t = threading.Thread(target=start_bot, daemon=True)
t.start()

# -------- Run Flask (Render will call this) --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("Starting Flask on port", port)
    app.run(host="0.0.0.0", port=port)
