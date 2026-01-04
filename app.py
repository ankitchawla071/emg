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

THRESHOLDS = {
    "temp": [35, 45],
    "vibration": [4, 7],
    "current": [6, 8]
}


@app.route('/data', methods=['POST'])
def post_data():
    d = request.get_json()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    row = pd.DataFrame([[now, d["pump"], d["temp"], d["vibration"], d["current"]]],
        columns=["datetime", "pump", "temp", "vibration", "current"])

    if not os.path.exists(CSV_FILE):
        row.to_csv(CSV_FILE, index=False)
    else:
        row.to_csv(CSV_FILE, mode='a', index=False, header=False)

    return jsonify({"status": "ok"})


@app.route('/history/<pump>')
def history(pump):
    if not os.path.exists(CSV_FILE):
        return jsonify({})

    df = pd.read_csv(CSV_FILE)
    df = df[df["pump"] == pump]

    return jsonify({
        "labels": df["datetime"].tolist(),
        "temp": df["temp"].tolist(),
        "vibration": df["vibration"].tolist(),
        "current": df["current"].tolist()
    })


@app.route('/')
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
body { margin:0; font-family:Segoe UI; background:#f4f6f9 }
.header { background:#0f172a; color:#fff; padding:18px; font-size:20px }
.container { padding:20px; max-width:1200px; margin:auto }

select { padding:10px; border-radius:8px; font-size:14px }

.cards {
 display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
 gap:16px; margin:20px 0
}

.card {
 background:#fff; border-radius:14px; padding:16px;
 box-shadow:0 4px 10px rgba(0,0,0,.08)
}

.value { font-size:26px; font-weight:600 }
.normal { color:#16a34a }
.warn { color:#d97706 }
.alarm { color:#dc2626 }

.chart-box {
 background:#fff; border-radius:14px; padding:20px;
 box-shadow:0 4px 10px rgba(0,0,0,.08)
}
</style>
</head>

<body>

<div class="header">Multi-Pump Condition Monitoring</div>

<div class="container">

<select id="pumpSelect" onchange="loadData()">
{% for p in pumps %}
<option value="{{p}}">{{p}}</option>
{% endfor %}
</select>

<div class="cards">
  <div class="card"><div>Temperature</div><div id="tVal" class="value">--</div></div>
  <div class="card"><div>Vibration</div><div id="vVal" class="value">--</div></div>
  <div class="card"><div>Current</div><div id="cVal" class="value">--</div></div>
</div>

<div class="chart-box">
<canvas id="chart" height="120"></canvas>
</div>

</div>

<script>
const thresholds = {
 temp:[35,45], vibration:[4,7], current:[6,8]
};

function color(val,[w,a]) {
 if(val<=w) return "normal";
 if(val<=a) return "warn";
 return "alarm";
}

const chart = new Chart(document.getElementById("chart"),{
 type:'line',
 data:{labels:[],datasets:[
  {label:"Temp (°C)", data:[], borderWidth:2},
  {label:"Vibration (mm/s)", data:[], borderWidth:2},
  {label:"Current (A)", data:[], borderWidth:2}
 ]},
 options:{responsive:true}
});

async function loadData(){
 let pump = pumpSelect.value;
 let r = await fetch("/history/"+pump);
 let d = await r.json();
 chart.data.labels = d.labels;
 chart.data.datasets[0].data = d.temp;
 chart.data.datasets[1].data = d.vibration;
 chart.data.datasets[2].data = d.current;
 chart.update();

 if(d.temp.length){
  let i=d.temp.length-1;
  setVal("tVal",d.temp[i],thresholds.temp,"°C");
  setVal("vVal",d.vibration[i],thresholds.vibration," mm/s");
  setVal("cVal",d.current[i],thresholds.current," A");
 }
}

function setVal(id,val,t,u){
 let e=document.getElementById(id);
 e.innerText=val+u;
 e.className="value "+color(val,t);
}

loadData();
setInterval(loadData,5000);
</script>

</body>
</html>
""", pumps=PUMPS)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
