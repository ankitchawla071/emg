from flask import Flask, jsonify, send_file, render_template_string, request
from datetime import datetime
import os, csv, requests

app = Flask(__name__)

# --- Telegram Bot ---
TELEGRAM_TOKEN = "8313892359:AAE2kl_X7YMqtE4aAbblatrsD87y9qWt67w"  # put your bot token here
CHAT_ID = "802173334"                   # your Telegram chat id
TEMP_THRESHOLD = 28.0                   # default threshold

CSV_FILE = "data.csv"

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": CHAT_ID, "text": msg})

# --- ESP32 posts here ---
@app.route('/post', methods=['POST'])
def post_data():
    temp = float(request.form.get('temp', 0))
    health = "OK" if temp < TEMP_THRESHOLD else "Overheating"

    ts = datetime.now().isoformat()
    file_exists = os.path.isfile(CSV_FILE)
    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['timestamp', 'temp', 'health'])
        writer.writerow([ts, temp, health])

    if temp >= TEMP_THRESHOLD:
        send_telegram(f"⚠️ High Temperature: {temp:.1f}°C at {ts}")

    return jsonify({"status": "ok"})

# --- latest data ---
@app.route('/data')
def latest_data():
    if not os.path.isfile(CSV_FILE):
        return jsonify({"health": "No Data", "temp": 0})
    with open(CSV_FILE) as f:
        rows = list(csv.DictReader(f))
        if not rows:
            return jsonify({"health": "No Data", "temp": 0})
        last = rows[-1]
    return jsonify({"health": last['health'], "temp": float(last['temp'])})

# --- full history download ---
@app.route('/history')
def history():
    return send_file(CSV_FILE, as_attachment=True)

# --- dashboard page ---
@app.route('/')
def index():
    return render_template_string("""
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
""")

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5050)
