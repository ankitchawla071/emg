import os
import pandas as pd
from flask import Flask, request, jsonify, send_file, render_template_string
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import threading

# ------------------ CONFIG ------------------
# Hardcoded Telegram bot token and chat id
TELEGRAM_TOKEN = "8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w"
CHAT_ID = "802173334"
THRESHOLD_FILE = "threshold.txt"
CSV_FILE = "data.csv"

# Default threshold
if not os.path.exists(THRESHOLD_FILE):
    with open(THRESHOLD_FILE, "w") as f:
        f.write("32")  # default threshold 32°C

# ------------------ FLASK APP ------------------
app = Flask(__name__)

# HTML Dashboard
dashboard_html = """
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
    data: { labels: [], datasets: [{ label: 'Temperature (°C)', data: [], borderColor: 'blue', borderWidth: 2, fill: false, tension: 0.1 }]},
    options: { animation: false, responsive: true, scales: { y: { beginAtZero:false } } }
});

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
setInterval(updateLive, 2000);
</script>
</body>
</html>
"""

# ------------------ FLASK ROUTES ------------------
@app.route('/')
def dashboard():
    return render_template_string(dashboard_html)

@app.route('/data', methods=['GET','POST'])
def data():
    if request.method == 'POST':
        content = request.get_json()
        temp = float(content.get("temp"))
        health = content.get("health", "Unknown")
        
        # Save to CSV
        df = pd.DataFrame([[pd.Timestamp.now(), temp, health]], columns=["datetime","temp","health"])
        if not os.path.exists(CSV_FILE):
            df.to_csv(CSV_FILE, index=False)
        else:
            df.to_csv(CSV_FILE, mode='a', index=False, header=False)
        
        # Telegram alert
        with open(THRESHOLD_FILE) as f:
            threshold = float(f.read().strip())
        if temp >= threshold:
            bot = Bot(token=TELEGRAM_TOKEN)
            bot.send_message(chat_id=CHAT_ID, text=f"🚨 ALERT: Temp {temp:.1f}°C exceeded threshold {threshold}°C!")
        
        return jsonify({"status":"ok"})
    
    else:  # GET
        if not os.path.exists(CSV_FILE):
            return jsonify({"temp":0,"health":"No Data"})
        df = pd.read_csv(CSV_FILE)
        last = df.iloc[-1]
        return jsonify({"temp": last["temp"], "health": last["health"]})

@app.route('/download', methods=['GET'])
def download():
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
        if os.path.exists(CSV_FILE):
            await context.bot.send_document(chat_id=query.from_user.id, document=open(CSV_FILE,'rb'), filename='data.csv')
        else:
            await query.edit_message_text("No CSV file yet.")
    
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
    app_bot = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CallbackQueryHandler(button))
    app_bot.add_handler(CommandHandler("threshold", change_threshold))
    app_bot.add_handler(CommandHandler("setthreshold", change_threshold))
    app_bot.run_polling()

# ------------------ START BOT IN BACKGROUND ------------------
threading.Thread(target=run_telegram, daemon=True).start()

# ------------------ RUN FLASK ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5050)
