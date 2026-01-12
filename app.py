from flask import Flask, request, jsonify, render_template_string
import pandas as pd
import os
from datetime import datetime

app = Flask(__name__)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

def path(pump):
    return os.path.join(DATA_DIR, pump.replace(" ", "_") + ".csv")

@app.route("/data", methods=["POST"])
def data():
    j = request.get_json()

    pump = j["pump"]
    temp = float(j["temp"])
    vibration = int(j.get("vibration", -1))
    dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    p = path(pump)

    df = pd.DataFrame([[dt, temp, vibration]],
                      columns=["datetime", "temp", "vibration"])

    if not os.path.exists(p):
        df.to_csv(p, index=False)
    else:
        df.to_csv(p, mode="a", header=False, index=False)

    return jsonify({"ok": True})

@app.route("/history/<pump>")
def history(pump):
    p = path(pump)
    if not os.path.exists(p):
        return jsonify({"labels": [], "temps": [], "vibration": []})

    df = pd.read_csv(p)

    return jsonify({
        "labels": df["datetime"].tolist(),
        "temps": df["temp"].tolist(),
        "vibration": df["vibration"].tolist()
    })

@app.route("/")
def index():
    return render_template_string(HTML)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Pump Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{font-family:Segoe UI;background:#0f172a;color:#e5e7eb;padding:20px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(380px,1fr));gap:20px}
.card{background:#1e293b;padding:18px;border-radius:14px}
.normal{color:#22c55e}
.warn{color:#facc15}
.critical{color:#ef4444}
</style>
</head>
<body>

<h1>Industrial Pump Monitoring</h1>

<div class="grid" id="grid"></div>

<script>
const pumps = [
"KOD Pump",
"Degrease Pump",
"Cold Water Rinse Pump",
"Hot Water Rinse Pump"
];

function vibStatus(v){
 if(v<0) return ["N/A",""];
 if(v<500) return ["Normal","normal"];
 if(v<1200) return ["Warning","warn"];
 return ["Critical","critical"];
}

function createCard(pump){
 const d=document.createElement("div");
 d.className="card";
 d.innerHTML=`
 <h2>${pump}</h2>
 <div id="stat_${pump}">Loading...</div>
 <canvas id="chart_${pump}"></canvas>
 `;
 document.getElementById("grid").appendChild(d);

 const ctx=document.getElementById("chart_"+pump).getContext("2d");

 const chart=new Chart(ctx,{
  type:"line",
  data:{labels:[],datasets:[
   {label:"Temperature (°C)",data:[],borderWidth:2},
   {label:"Vibration",data:[],borderWidth:2}
  ]},
  options:{animation:false}
 });

 async function update(){
  const h=await fetch("/history/"+pump).then(r=>r.json());

  chart.data.labels=h.labels;
  chart.data.datasets[0].data=h.temps;
  chart.data.datasets[1].data=h.vibration;
  chart.update();

  const lastV=h.vibration.length?h.vibration[h.vibration.length-1]:-1;
  const lastT=h.temps.length?h.temps[h.temps.length-1]:"--";

  const [txt,cls]=vibStatus(lastV);

  document.getElementById("stat_"+pump).innerHTML=
   `Temp: ${lastT} °C | Vibration: ${lastV} 
    <span class="${cls}">${txt}</span>`;
 }

 setInterval(update,3000);
 update();
}

pumps.forEach(createCard);
</script>

</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
