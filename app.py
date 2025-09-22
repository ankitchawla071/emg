from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import os

app = Flask(__name__)

CSV_FILE = "data.csv"

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>ESP32 Temperature</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body style="font-family:Arial;text-align:center;">
<h2>ESP32 Temperature Live</h2>
<canvas id="tempChart" width="600" height="300"></canvas>
<script>
const ctx = document.getElementById('tempChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [{
        label: 'Temperature (°C)',
        data: [],
        borderColor: 'blue',
        borderWidth: 2,
        fill: false,
        tension: 0.1
    }]},
    options: {
        animation:false,
        scales: { y: { beginAtZero:false } }
    }
});

async function fetchData() {
    const res = await fetch('/data');
    const d = await res.json();
    const now = new Date().toLocaleTimeString();
    chart.data.labels.push(now);
    chart.data.datasets[0].data.push(d.temp);
    if(chart.data.labels.length>50){
      chart.data.labels.shift();
      chart.data.datasets[0].data.shift();
    }
    chart.update();
}
setInterval(fetchData, 2000);
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML)

@app.route("/data", methods=["GET", "POST"])
def data():
    if request.method == "POST":
        content = request.get_json()
        temp = float(content.get("temp"))
        df = pd.DataFrame([[pd.Timestamp.now(), temp]], columns=["datetime","temp"])
        if not os.path.exists(CSV_FILE):
            df.to_csv(CSV_FILE, index=False)
        else:
            df.to_csv(CSV_FILE, index=False, mode="a", header=False)
        return jsonify({"status":"ok"})
    else:
        if not os.path.exists(CSV_FILE):
            return jsonify({"temp":0})
        df = pd.read_csv(CSV_FILE)
        last = df.iloc[-1]
        return jsonify({"temp": last["temp"]})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
