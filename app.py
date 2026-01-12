# app.py
from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

PUMPS = [
    "KOD Pump",
    "Degrease Pump",
    "Cold Water Rinse Pump",
    "Hot Water Rinse Pump"
]

# ---------------- Utils ----------------

def path(pump):
    return os.path.join(DATA_DIR, pump.replace(" ", "_") + ".csv")


def read_last(pump, limit=50):
    p = path(pump)
    if not os.path.exists(p):
        return pd.DataFrame(columns=["datetime", "temp", "vibration"])
    df = pd.read_csv(p)
    return df.tail(limit)


def pump_status(pump, last_row):
    if last_row is None:
        return "normal"

    temp = float(last_row["temp"])
    vib = int(last_row.get("vibration", -1))

    # KOD uses vibration
    if pump == "KOD Pump":
        if vib < 500:
            return "normal"
        elif vib < 1200:
            return "warning"
        else:
            return "critical"
    else:
        # temperature based status for others
        if temp < 40:
            return "normal"
        elif temp < 60:
            return "warning"
        else:
            return "critical"

# ---------------- API ----------------

@app.route("/data", methods=["POST"])
def data():
    j = request.get_json()

    pump = j["pump"]
    temp = float(j["temp"])
    vibration = int(j.get("vibration", -1))
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p = path(pump)
    df = pd.DataFrame([[dt, temp, vibration]], columns=["datetime", "temp", "vibration"])

    if not os.path.exists(p):
        df.to_csv(p, index=False)
    else:
        df.to_csv(p, mode="a", header=False, index=False)

    return jsonify({"ok": True})


@app.route("/history/<pump>")
def history(pump):
    df = read_last(pump, 50)
    return jsonify({
        "labels": df["datetime"].tolist(),
        "temps": df["temp"].tolist(),
        "vibration": df["vibration"].tolist()
    })


@app.route("/latest/<pump>")
def latest(pump):
    df = read_last(pump, 1)
    if df.empty:
        return jsonify({})
    row = df.iloc[-1].to_dict()
    row["status"] = pump_status(pump, row)
    return jsonify(row)

# ---------------- UI ----------------

@app.route("/")
def home():
    return render_template_string(HOME_HTML, pumps=PUMPS)


@app.route("/pump/<pump>")
def pump_page(pump):
    return render_template_string(PUMP_HTML, pump=pump)


HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Pump Dashboard</title>
<style>
body{font-family:Segoe UI;background:#0f172a;color:#e5e7eb;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}
.card{padding:20px;border-radius:14px;text-decoration:none;color:white}
.normal{background:#16a34a}
.warning{background:#ca8a04}
.critical{background:#dc2626}
</style>
</head>
<body>
<h1>Pump Monitoring System</h1>
<div class="grid" id="grid"></div>

<script>
const pumps = {{ pumps|tojson }};

async function load(){
  const grid = document.getElementById("grid");
  grid.innerHTML="";

  for(const p of pumps){
    const r = await fetch(`/latest/${p}`);
    const j = await r.json();
    const status = j.status || "normal";

    const a = document.createElement("a");
    a.href = `/pump/${p}`;
    a.className = `card ${status}`;
    a.innerHTML = `<h2>${p}</h2><p>Status: ${status.toUpperCase()}</p>`;

    grid.appendChild(a);
  }
}

setInterval(load, 3000);
load();
</script>
</body>
</html>
"""


PUMP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{{pump}}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
<style>
body{font-family:Segoe UI;background:#0f172a;color:#e5e7eb;padding:20px}
.card{background:#1e293b;padding:20px;border-radius:14px}
</style>
</head>
<body>
<a href="/">⬅ Back</a>
<h1>{{pump}}</h1>

<div class="card">
<h3>Temperature</h3>
<canvas id="tempChart"></canvas>
</div>
<br>
<div class="card">
<h3>Vibration</h3>
<canvas id="vibChart"></canvas>
</div>

<script>
const pump = "{{pump}}";

const tempChart = new Chart(document.getElementById('tempChart'),{
  type:'line',
  data:{labels:[],datasets:[{label:'Temp °C',data:[],borderWidth:2}]},
  options:{
    animation:false,
    plugins:{
      zoom:{
        zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},
        pan:{enabled:true,mode:'x'}
      }
    }
  }
});

const vibChart = new Chart(document.getElementById('vibChart'),{
  type:'line',
  data:{labels:[],datasets:[{label:'Vibration',data:[],borderWidth:2}]},
  options:{
    animation:false,
    plugins:{
      zoom:{
        zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},
        pan:{enabled:true,mode:'x'}
      }
    }
  }
});

async function update(){
  const r = await fetch(`/history/${pump}`);
  const j = await r.json();

  tempChart.data.labels = j.labels;
  tempChart.data.datasets[0].data = j.temps;
  tempChart.update();

  vibChart.data.labels = j.labels;
  vibChart.data.datasets[0].data = j.vibration;
  vibChart.update();
}

setInterval(update, 3000);
update();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
    vib = int(last_row.get("vibration", -1))

    # KOD uses vibration
    if pump == "KOD Pump":
        if vib < 500:
            return "normal"
        elif vib < 1200:
            return "warning"
        else:
            return "critical"
    else:
        # temperature based status for others
        if temp < 40:
            return "normal"
        elif temp < 60:
            return "warning"
        else:
            return "critical"

# ---------------- API ----------------

@app.route("/data", methods=["POST"])
def data():
    j = request.get_json()

    pump = j["pump"]
    temp = float(j["temp"])
    vibration = int(j.get("vibration", -1))
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p = path(pump)
    df = pd.DataFrame([[dt, temp, vibration]], columns=["datetime", "temp", "vibration"])

    if not os.path.exists(p):
        df.to_csv(p, index=False)
    else:
        df.to_csv(p, mode="a", header=False, index=False)

    return jsonify({"ok": True})


@app.route("/history/<pump>")
def history(pump):
    df = read_last(pump, 50)
    return jsonify({
        "labels": df["datetime"].tolist(),
        "temps": df["temp"].tolist(),
        "vibration": df["vibration"].tolist()
    })


@app.route("/latest/<pump>")
def latest(pump):
    df = read_last(pump, 1)
    if df.empty:
        return jsonify({})
    row = df.iloc[-1].to_dict()
    row["status"] = pump_status(pump, row)
    return jsonify(row)

# ---------------- UI ----------------

@app.route("/")
def home():
    return render_template_string(HOME_HTML, pumps=PUMPS)


@app.route("/pump/<pump>")
def pump_page(pump):
    return render_template_string(PUMP_HTML, pump=pump)


HOME_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Pump Dashboard</title>
<style>
body{font-family:Segoe UI;background:#0f172a;color:#e5e7eb;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}
.card{padding:20px;border-radius:14px;text-decoration:none;color:white}
.normal{background:#16a34a}
.warning{background:#ca8a04}
.critical{background:#dc2626}
</style>
</head>
<body>
<h1>Pump Monitoring System</h1>
<div class="grid" id="grid"></div>

<script>
const pumps = {{ pumps|tojson }};

async function load(){
  const grid = document.getElementById("grid");
  grid.innerHTML="";

  for(const p of pumps){
    const r = await fetch(`/latest/${p}`);
    const j = await r.json();
    const status = j.status || "normal";

    const a = document.createElement("a");
    a.href = `/pump/${p}`;
    a.className = `card ${status}`;
    a.innerHTML = `<h2>${p}</h2><p>Status: ${status.toUpperCase()}</p>`;

    grid.appendChild(a);
  }
}

setInterval(load, 3000);
load();
</script>
</body>
</html>
"""


PUMP_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{{pump}}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.0.1"></script>
<style>
body{font-family:Segoe UI;background:#0f172a;color:#e5e7eb;padding:20px}
.card{background:#1e293b;padding:20px;border-radius:14px}
</style>
</head>
<body>
<a href="/">⬅ Back</a>
<h1>{{pump}}</h1>

<div class="card">
<h3>Temperature</h3>
<canvas id="tempChart"></canvas>
</div>
<br>
<div class="card">
<h3>Vibration</h3>
<canvas id="vibChart"></canvas>
</div>

<script>
const pump = "{{pump}}";

const tempChart = new Chart(document.getElementById('tempChart'),{
  type:'line',
  data:{labels:[],datasets:[{label:'Temp °C',data:[],borderWidth:2}]},
  options:{
    animation:false,
    plugins:{
      zoom:{
        zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},
        pan:{enabled:true,mode:'x'}
      }
    }
  }
});

const vibChart = new Chart(document.getElementById('vibChart'),{
  type:'line',
  data:{labels:[],datasets:[{label:'Vibration',data:[],borderWidth:2}]},
  options:{
    animation:false,
    plugins:{
      zoom:{
        zoom:{wheel:{enabled:true},pinch:{enabled:true},mode:'x'},
        pan:{enabled:true,mode:'x'}
      }
    }
  }
});

async function update(){
  const r = await fetch(`/history/${pump}`);
  const j = await r.json();

  tempChart.data.labels = j.labels;
  tempChart.data.datasets[0].data = j.temps;
  tempChart.update();

  vibChart.data.labels = j.labels;
  vibChart.data.datasets[0].data = j.vibration;
  vibChart.update();
}

setInterval(update, 3000);
update();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
