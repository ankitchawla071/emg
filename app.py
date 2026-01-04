from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import os
from datetime import datetime
import pytz

app = Flask(__name__)
CSV_FILE = "data.csv"
IST = pytz.timezone("Asia/Kolkata")

PUMPS = [
    "KOD Pump",
    "Degrease Pump",
    "Cold Water Rinse Pump",
    "Hot Water Rinse Pump"
]

# -------------------- DATA INGEST --------------------
@app.route("/data", methods=["POST"])
def post_data():
    d = request.get_json()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    row = pd.DataFrame([[now, d["pump"], float(d["temp"])]],
                       columns=["datetime", "pump", "temp"])

    if not os.path.exists(CSV_FILE):
        row.to_csv(CSV_FILE, index=False)
    else:
        row.to_csv(CSV_FILE, mode="a", index=False, header=False)

    return jsonify({"status": "ok"})


# -------------------- HISTORY --------------------
@app.route("/history/<pump>")
def history(pump):
    if not os.path.exists(CSV_FILE):
        return jsonify({"labels": [], "temps": []})

    df = pd.read_csv(CSV_FILE)
    df = df[df["pump"] == pump]

    return jsonify({
        "labels": df["datetime"].tolist(),
        "temps": df["temp"].tolist()
    })


# -------------------- LATEST --------------------
@app.route("/latest/<pump>")
def latest(pump):
    if not os.path.exists(CSV_FILE):
        return jsonify({"temp": None})

    df = pd.read_csv(CSV_FILE)
    df = df[df["pump"] == pump]

    if df.empty:
        return jsonify({"temp": None})

    last = df.iloc[-1]
    return jsonify({
        "temp": last["temp"],
        "datetime": last["datetime"]
    })


# -------------------- UI RENDER --------------------
@app.route("/")
def index():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Pump Monitoring Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<style>
body {
    margin: 0;
    font-family: "Segoe UI", Arial;
    background: #f4f6f9;
}

.header {
    background: #0f172a;
    color: white;
    padding: 18px 24px;
    font-size: 20px;
    font-weight: 600;
}

.container {
    max-width: 1100px;
    margin: auto;
    padding: 20px;
}

select {
    padding: 10px;
    border-radius: 8px;
    font-size: 14px;
    margin-bottom: 20px;
}

.cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
}

.card {
    background: white;
    border-radius: 14px;
    padding: 16px;
    box-shadow: 0 4px 10px rgba(0,0,0,.08);
}

.card-title {
    font-size: 14px;
    color: #6b7280;
}

.card-value {
    font-size: 28px;
    font-weight: 600;
    margin-top: 6px;
}

.normal { color: #16a34a; }
.warn   { color: #d97706; }
.alarm  { color: #dc2626; }

.chart-box {
    background: white;
    border-radius: 14px;
    padding: 20px;
    box-shadow: 0 4px 10px rgba(0,0,0,.08);
}
</style>
</head>

<body>

<div class="header">
    Multi-Pump Temperature Monitoring
</div>

<div class="container">

<select id="pumpSelect" onchange="loadData()">
{% for p in pumps %}
  <option value="{{p}}">{{p}}</option>
{% endfor %}
</select>

<div class="cards">
    <div class="card">
        <div class="card-title">Current Temperature</div>
        <div id="tempVal" class="card-value">-- °C</div>
    </div>

    <div class="card">
        <div class="card-title">Pump Status</div>
        <div id="statusVal" class="card-value">--</div>
    </div>

    <div class="card">
        <div class="card-title">Last Updated</div>
        <div id="timeVal" style="font-size:16px">--</div>
    </div>
</div>

<div class="chart-box">
    <canvas id="tempChart" height="120"></canvas>
</div>

</div>

<script>
const thresholds = { warn: 35, alarm: 45 };

const chart = new Chart(document.getElementById("tempChart"), {
    type: "line",
    data: {
        labels: [],
        datasets: [{
            label: "Temperature (°C)",
            data: [],
            borderWidth: 2,
            tension: 0.25
        }]
    },
    options: {
        responsive: true,
        animation: false
    }
});

function statusClass(t) {
    if (t <= thresholds.warn) return "normal";
    if (t <= thresholds.alarm) return "warn";
    return "alarm";
}

function statusText(t) {
    if (t <= thresholds.warn) return "Normal";
    if (t <= thresholds.alarm) return "Warning";
    return "Alarm";
}

async function loadData() {
    const pump = pumpSelect.value;

    const h = await fetch(`/history/${pump}`);
    const hd = await h.json();
    chart.data.labels = hd.labels;
    chart.data.datasets[0].data = hd.temps;
    chart.update();

    const l = await fetch(`/latest/${pump}`);
    const ld = await l.json();

    if (ld.temp !== null) {
        tempVal.innerText = ld.temp + " °C";
        timeVal.innerText = ld.datetime;

        const cls = statusClass(ld.temp);
        statusVal.innerText = statusText(ld.temp);
        statusVal.className = "card-value " + cls;
        tempVal.className = "card-value " + cls;
    }
}

loadData();
setInterval(loadData, 5000);
</script>

</body>
</html>
""", pumps=PUMPS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
