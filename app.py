
from flask import Flask, request, jsonify, render_template_string
import csv
import os
from datetime import datetime
import pytz

app = Flask(__name__)
DATA_FILE = "pump_data.csv"
IST = pytz.timezone("Asia/Kolkata")

PUMPS = [
    "KOD Pump",
    "Degrease Pump",
    "Cold Rinse Pump",
    "Hot Rinse Pump"
]

# ------------------- Data API -------------------

@app.route("/data", methods=["POST"])
def receive_data():
    data = request.get_json()
    pump = data.get("pump")
    temp = data.get("temp")
    vibration = data.get("vibration", "")

    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["time", "pump", "temp", "vibration"])
        writer.writerow([now, pump, temp, vibration])

    return jsonify({"status": "ok"})


@app.route("/latest")
def latest_status():
    result = {p: None for p in PUMPS}

    if not os.path.exists(DATA_FILE):
        return jsonify(result)

    with open(DATA_FILE) as f:
        rows = list(csv.DictReader(f))

    for row in reversed(rows):
        if result[row["pump"]] is None:
            result[row["pump"]] = row

    return jsonify(result)


@app.route("/history/<pump>")
def history(pump):
    labels, temps, vibes = [], [], []

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            for r in csv.DictReader(f):
                if r["pump"] == pump:
                    labels.append(r["time"])
                    temps.append(float(r["temp"]))
                    vibes.append(float(r["vibration"]) if r["vibration"] else 0)

    return jsonify({
        "labels": labels[-50:],
        "temps": temps[-50:],
        "vibes": vibes[-50:]
    })


# ------------------- UI -------------------

@app.route("/")
def dashboard():
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>Pump Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
<style>
body{font-family:Arial;background:#0f172a;color:white}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}
.card{padding:20px;border-radius:12px;cursor:pointer;text-align:center;font-weight:bold}
.normal{background:#16a34a}
.warning{background:#facc15;color:black}
.critical{background:#dc2626}
</style>
</head>
<body>
<h2>Machine Health Dashboard</h2>
<div class="grid" id="pumpGrid"></div>

<script>
const pumps = ["KOD Pump","Degrease Pump","Cold Rinse Pump","Hot Rinse Pump"];

const grid = document.getElementById("pumpGrid");

// Create fixed cards once
pumps.forEach(p => {
  const div = document.createElement("div");
  div.className = "card normal";
  div.id = p;
  div.innerText = p;
  div.onclick = () => window.location = `/pump/${p}`;
  grid.appendChild(div);
});

function statusClass(temp){
  if(temp > 45) return "critical";
  if(temp > 38) return "warning";
  return "normal";
}

async function refreshStatus(){
  const res = await fetch("/latest");
  const data = await res.json();

  pumps.forEach(p => {
    const card = document.getElementById(p);
    if(data[p]){
      card.className = `card ${statusClass(data[p].temp)}`;
      card.innerText = `${p}\n${data[p].temp}°C`;
    }
  });
}

setInterval(refreshStatus, 2000);
refreshStatus();
</script>
</body>
</html>
""")


@app.route("/pump/<pump>")
def pump_page(pump):
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<title>{{pump}}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
</head>
<body>
<h2>{{pump}}</h2>
<canvas id="temp"></canvas>
<canvas id="vibe"></canvas>

<script>
const pump = "{{pump}}";

const tempChart = new Chart(document.getElementById('temp'),{
 type:'line',
 data:{labels:[],datasets:[{label:'Temperature',data:[]}]},
 options:{plugins:{zoom:{zoom:{wheel:{enabled:true},mode:'x'},pan:{enabled:true,mode:'x'}}}}
});

const vibeChart = new Chart(document.getElementById('vibe'),{
 type:'line',
 data:{labels:[],datasets:[{label:'Vibration',data:[]}]},
 options:{plugins:{zoom:{zoom:{wheel:{enabled:true},mode:'x'},pan:{enabled:true,mode:'x'}}}}
});

async function load(){
 const r = await fetch(`/history/${pump}`);
 const d = await r.json();
 tempChart.data.labels = d.labels;
 tempChart.data.datasets[0].data = d.temps;
 vibeChart.data.labels = d.labels;
 vibeChart.data.datasets[0].data = d.vibes;
 tempChart.update();
 vibeChart.update();
}

setInterval(load,2000);
load();
</script>
</body>
</html>
""", pump=pump)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
