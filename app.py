from flask import Flask, request, jsonify
import pandas as pd, os
from datetime import datetime
import pytz

app = Flask(__name__)
DATA_DIR="data"
IST=pytz.timezone("Asia/Kolkata")
os.makedirs(DATA_DIR,exist_ok=True)

ALARM_LIMITS={
"KOD Pump":{"warn":40,"critical":45},
"Degrease Pump":{"warn":42,"critical":48},
"Cold Water Rinse Pump":{"warn":35,"critical":40},
"Hot Water Rinse Pump":{"warn":55,"critical":60}
}

def csv_path(p):
    return os.path.join(DATA_DIR,p.lower().replace(" ","_")+".csv")

# ---------------- DATA ----------------
@app.route("/data",methods=["POST"])
def data():
    j=request.get_json()
    pump=j.get("pump")
    temp=float(j.get("temp",0))
    now=datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    df=pd.DataFrame([[now,temp]],columns=["datetime","temp"])
    f=csv_path(pump)
    if not os.path.exists(f): df.to_csv(f,index=False)
    else: df.to_csv(f,mode="a",header=False,index=False)

    return jsonify({"status":"ok"})

@app.route("/history/<pump>")
def history(pump):
    f=csv_path(pump)
    if os.path.exists(f):
        df=pd.read_csv(f)
        return jsonify({"labels":df["datetime"].tolist(),"temps":df["temp"].tolist()})
    return jsonify({"labels":[],"temps":[]})

@app.route("/latest/<pump>")
def latest(pump):
    f=csv_path(pump)
    lim=ALARM_LIMITS.get(pump,{"warn":999,"critical":999})
    if os.path.exists(f):
        df=pd.read_csv(f)
        if not df.empty:
            t=float(df.iloc[-1]["temp"])
            s="NORMAL"
            if t>=lim["critical"]: s="CRITICAL"
            elif t>=lim["warn"]: s="WARNING"
            return jsonify({"temp":t,"datetime":df.iloc[-1]["datetime"],"status":s})
    return jsonify({"temp":None,"datetime":None,"status":"UNKNOWN"})

@app.route("/limits/<pump>")
def limits(pump):
    return jsonify(ALARM_LIMITS.get(pump,{"warn":0,"critical":0}))

# ---------------- DASHBOARD ----------------
@app.route("/")
def dash():
    return """
<html><head><title>Pumps</title>
<style>
body{font-family:Arial;background:#0f172a;color:white;text-align:center}
.card{display:inline-block;background:#1e293b;padding:20px;margin:15px;border-radius:12px;cursor:pointer;width:200px}
.card:hover{background:#334155}
</style></head><body>
<h1>Pump Monitoring</h1>
<div class=card onclick="go('KOD Pump')">KOD Pump</div>
<div class=card onclick="go('Degrease Pump')">Degrease Pump</div>
<div class=card onclick="go('Cold Water Rinse Pump')">Cold Water Rinse Pump</div>
<div class=card onclick="go('Hot Water Rinse Pump')">Hot Water Rinse Pump</div>
<script>
function go(p){location='/pump?name='+encodeURIComponent(p);}
</script>
</body></html>
"""

# ---------------- PUMP PAGE ----------------
@app.route("/pump")
def pump():
    from flask import request
    pump=request.args.get("name","KOD Pump")
    return f"""
<html>
<head>
<title>{pump}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{font-family:Arial;background:#020617;color:white;text-align:center}}
</style>
</head>
<body>

<h2>{pump}</h2>
<div id="status">Loading...</div>
<canvas id="c"></canvas>

<script>
const pumpName="{pump}";
let warn=0,crit=0;

const ctx=document.getElementById("c");
const chart=new Chart(ctx,{{
type:"line",
data:{{labels:[],datasets:[
{{label:"Temp",data:[]}},
{{label:"Warn",data:[],borderDash:[5,5]}},
{{label:"Critical",data:[],borderDash:[5,5]}}
]}},
options:{{animation:false}}
}});

async function limits(){{
let r=await fetch(`/limits/${{pumpName}}`);
let d=await r.json();
warn=d.warn;crit=d.critical;
}}

async function history(){{
let r=await fetch(`/history/${{pumpName}}`);
let d=await r.json();
chart.data.labels=d.labels;
chart.data.datasets[0].data=d.temps;
chart.data.datasets[1].data=d.temps.map(()=>warn);
chart.data.datasets[2].data=d.temps.map(()=>crit);
chart.update();
}}

async function latest(){{
let r=await fetch(`/latest/${{pumpName}}`);
let d=await r.json();
let c="lime";
if(d.status=="WARNING") c="orange";
if(d.status=="CRITICAL") c="red";
document.getElementById("status").innerHTML=
`Temp: <b style="color:${{c}}">${{d.temp}}°C</b> | ${{d.status}}`;
}}

async function refresh(){{ await limits(); await history(); await latest(); }}

refresh();
setInterval(refresh,3000);
</script>

</body>
</html>
"""

if __name__=="__main__":
    app.run(host="0.0.0.0",port=5050)
