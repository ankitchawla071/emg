from flask import Flask, request, jsonify, render_template_string, send_file
import pandas as pd
import os
from datetime import datetime
import pytz

app = Flask(__name__)
CSV_FILE = "data.csv"
IST = pytz.timezone("Asia/Kolkata")


@app.route('/data', methods=['POST'])
def post_data():
    content = request.get_json()
    temp = float(content.get("temp", 0))

    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")
    df = pd.DataFrame([[now, temp]], columns=["datetime", "temp"])

    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, index=False, mode='a', header=False)

    return jsonify({"status": "ok"})


@app.route('/history')
def history():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return jsonify({
            "labels": df["datetime"].tolist(),
            "temps": df["temp"].tolist()
        })
    return jsonify({"labels": [], "temps": []})


@app.route('/latest')
def latest():
    """Return the most recent reading for heading display."""
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        if not df.empty:
            last_row = df.iloc[-1]
            return jsonify({
                "temp": last_row["temp"],
                "datetime": last_row["datetime"]
            })
    return jsonify({"temp": None, "datetime": None})


@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>KOD Pump Monitoring</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="font-family: Arial; text-align:center; padding:20px;">
    <h2 id="heading">KOD Pump Monitoring</h2>
    <canvas id="tempChart" width="300" height="180"></canvas>

    <script>
    const ctx = document.getElementById('tempChart').getContext('2d');
    const tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature (°C)',
                data: [],
                borderColor: 'red',
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

    async function fetchHistory(){
        const res = await fetch('/history');
        const data = await res.json();
        tempChart.data.labels = data.labels;
        tempChart.data.datasets[0].data = data.temps;
        tempChart.update();
    }

    async function fetchLatest(){
        const res = await fetch('/latest');
        const data = await res.json();
        if(data.temp !== null){
            // Simple "health" status
            const health = data.temp > 34 ? '⚠️ Abnormal' : '✅ Normal';
            document.getElementById('heading').innerText =
              `KOD Pump Monitoring | Temp: ${data.temp}°C | ${health}`;
        }
    }

    // initial load
    fetchHistory();
    fetchLatest();

    // refresh every 5s
    setInterval(fetchHistory, 500);
    setInterval(fetchLatest, 500);
    </script>
    <p><a href="/download">Download CSV</a></p>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route('/download')
def download_csv():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No data yet"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5050)))
