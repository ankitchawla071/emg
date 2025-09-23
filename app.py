import os
import csv
import threading
import time
from datetime import datetime
import requests
import pandas as pd
from flask import Flask, request, jsonify, render_template_string, send_file

# telegram-ext (v20+)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# ========== CONFIG ==========
CSV_FILE = "data.csv"
THRESHOLD_FILE = "threshold.txt"

# HARD-CODE (replace with your real values)
TELEGRAM_TOKEN = "8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w"
ADMIN_CHAT_ID = "802173334"   # numeric chat id where alerts and bot replies go

# Default threshold file create
if not os.path.exists(THRESHOLD_FILE):
    with open(THRESHOLD_FILE, "w") as f:
        f.write("32")  # default 32°C

# Ensure CSV header exists
if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE) == 0:
    with open(CSV_FILE, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["datetime", "temp", "health"])

# Keep track to avoid repeated alerts
alert_state = {"alert_sent": False}

# ========== FLASK ==========
app = Flask(__name__)

# Simple dashboard HTML (loads last 50 points via /history)
DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>KOD Pump Monitoring</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body style="font-family:Arial;text-align:center;padding:18px;">
  <h2>KOD Pump Monitoring</h2>
  <p id="health" style="font-weight:bold;">Health: Loading...</p>
  <canvas id="tempChart" width="800" height="300"></canvas>
  <p><a href="/download">Download CSV</a></p>

<script>
async function loadHistory(){
  const res = await fetch('/history');
  const arr = await res.json();
  return arr;
}

function makeChart(labels, data){
  const ctx = document.getElementById('tempChart').getContext('2d');
  return new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Temperature (°C)',
        data: data,
        borderColor: 'blue',
        borderWidth: 2,
        fill: false,
        tension: 0.1
      }]
    },
    options: { animation: false, responsive: true, scales:{ y:{ beginAtZero:false } } }
  });
}

let chart = null;
async function init(){
  const hist = await loadHistory();
  const labels = hist.map(r => r.datetime.split(' ')[1]);
  const temps  = hist.map(r => r.temp);
  chart = makeChart(labels, temps);
  updateLive(); // initial populate latest health
  setInterval(pollLatest, 2000);
}

async function pollLatest(){
  try {
    const res = await fetch('/data');
    const j = await res.json();
    document.getElementById('health').innerText = "Health: " + j.health + " (" + j.temp.toFixed(1) + "°C)";
    const now = new Date().toLocaleTimeString();
    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(j.temp);
    if(chart.data.labels.length > 50){
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update();
  } catch(e){
    console.error("pollLatest error", e);
  }
}

async function updateLive(){
  const res = await fetch('/data');
  const j = await res.json();
  document.getElementById('health').innerText = "Health: " + j.health + " (" + j.temp.toFixed(1) + "°C)";
}

window.addEventListener('load', init);
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(DASHBOARD_HTML)

@app.route("/history", methods=["GET"])
def history():
    # return all stored rows as JSON
    rows = []
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline='') as f:
            reader = csv.DictReader(f)
            for r in reader:
                try:
                    rows.append({"datetime": r["datetime"], "temp": float(r["temp"]), "health": r.get("health","")})
                except:
                    continue
    return jsonify(rows)

@app.route("/download", methods=["GET"])
def download():
    if not os.path.exists(CSV_FILE):
        return "No data", 404
    return send_file(CSV_FILE, as_attachment=True)

@app.route("/data", methods=["GET", "POST"])
def data_endpoint():
    """
    POST: ESP32 posts {"temp":31.2, "health":"Good"} as JSON
    GET: return last reading as JSON {"temp":..., "health":...}
    """
    global alert_state
    if request.method == "POST":
        payload = request.get_json(force=True, silent=True)
        if not payload or "temp" not in payload:
            return jsonify({"error":"bad payload"}), 400
        temp = float(payload["temp"])
        health = payload.get("health", "")
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        # append to CSV
        with open(CSV_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([ts, f"{temp:.4f}", health])

        # threshold check & alert logic (use threshold file)
        try:
            with open(THRESHOLD_FILE) as tf:
                threshold = float(tf.read().strip())
        except:
            threshold = 32.0

        # Abnormal zone margin 20% below threshold
        abnormal_low = threshold * 0.8

        # Send alert once on crossing threshold (Bad), and once for abnormal if needed
        if temp > threshold and not alert_state.get("bad_sent", False):
            # synchronous HTTP call to Telegram API (safe from Flask sync context)
            send_telegram_sync(f"⚠️ ALERT: Temp {temp:.1f}°C > threshold {threshold:.1f}°C")
            alert_state["bad_sent"] = True
            alert_state["abnormal_sent"] = False
        elif abnormal_low <= temp <= threshold and not alert_state.get("abnormal_sent", False):
            send_telegram_sync(f"⚠️ Warning: Temp {temp:.1f}°C in abnormal zone (≥ {abnormal_low:.1f}°C).")
            alert_state["abnormal_sent"] = True
            alert_state["bad_sent"] = False
        elif temp < abnormal_low:
            # recovered to Good
            if alert_state.get("bad_sent") or alert_state.get("abnormal_sent"):
                send_telegram_sync(f"ℹ️ Recovery: Temp {temp:.1f}°C back to Good.")
            alert_state["bad_sent"] = False
            alert_state["abnormal_sent"] = False

        return jsonify({"status":"ok"}), 201

    else:  # GET -> return last row
        if not os.path.exists(CSV_FILE):
            return jsonify({"temp":0.0, "health":"No Data"})
        with open(CSV_FILE, newline='') as f:
            reader = list(csv.DictReader(f))
            if not reader:
                return jsonify({"temp":0.0, "health":"No Data"})
            last = reader[-1]
            return jsonify({"temp": float(last["temp"]), "health": last.get("health","")})

# ========== Telegram helpers ==========
def send_telegram_sync(text, chat_id=None):
    token = TELEGRAM_TOKEN
    cid = chat_id or ADMIN_CHAT_ID
    if not token or not cid:
        print("Telegram token/chat not configured")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": cid, "text": text})
        return r.status_code == 200
    except Exception as e:
        print("send_telegram_sync error:", e)
        return False

# ========== Bot handlers (for interactive commands) ==========
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = [
        [ InlineKeyboardButton("📊 Current Status", callback_data="status") ],
        [ InlineKeyboardButton("⬇️ Download CSV", callback_data="csv") ],
        [ InlineKeyboardButton("⚙️ Set Threshold", callback_data="setthreshold") ]
    ]
    await update.message.reply_text("KOD Pump Bot", reply_markup=InlineKeyboardMarkup(kb))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "status":
        # send latest reading
        if not os.path.exists(CSV_FILE):
            await query.message.reply_text("No data yet.")
            return
        with open(CSV_FILE, newline='') as f:
            last = list(csv.DictReader(f))[-1]
        with open(THRESHOLD_FILE) as tf:
            threshold = float(tf.read().strip())
        await query.message.reply_text(f"Current: {float(last['temp']):.1f}°C | Health: {last.get('health','')} | Threshold: {threshold:.1f}°C")
    elif data == "csv":
        if not os.path.exists(CSV_FILE):
            await query.message.reply_text("No CSV yet.")
            return
        # send as document
        await context.bot.send_document(chat_id=query.from_user.id, document=open(CSV_FILE, "rb"))
    elif data == "setthreshold":
        await query.message.reply_text("Send new threshold as a number, e.g. `35`")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Accept numeric messages to change threshold
    txt = update.message.text.strip()
    try:
        val = float(txt)
        with open(THRESHOLD_FILE, "w") as f:
            f.write(str(val))
        await update.message.reply_text(f"Threshold updated to {val:.1f}°C")
    except:
        await update.message.reply_text("Send a valid number to set threshold.")

def run_bot():
    """Start telegram bot polling (runs in separate thread)."""
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), text_handler))
    # run polling (blocking) inside thread
    application.run_polling()

# Start bot thread
threading.Thread(target=run_bot, daemon=True).start()

# ========== RUN FLASK ==========
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("Starting Flask on port", port)
    app.run(host="0.0.0.0", port=port)
