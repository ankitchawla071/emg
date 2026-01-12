from flask import Flask, request, jsonify, render_template_string, redirect, session
import csv, os, json
from datetime import datetime
import pytz

app = Flask(__name__)
app.secret_key = "pump-secret"

DATA_FILE = "pump_data.csv"
THRESH_FILE = "thresholds.json"
IST = pytz.timezone("Asia/Kolkata")

PUMPS = ["KOD Pump", "Degrease Pump", "Cold Rinse Pump", "Hot Rinse Pump"]

DEFAULT_THRESH = {
    p: {"warning": 38, "critical": 45} for p in PUMPS
}

if not os.path.exists(THRESH_FILE):
    json.dump(DEFAULT_THRESH, open(THRESH_FILE, "w"), indent=2)

# ---------------- AUTH ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["user"] == "admin" and request.form["pass"] == "admin123":
            session["user"] = "admin"
            return redirect("/")
    return render_template_string("""
<form method=post style='max-width:300px;margin:auto;margin-top:100px'>
<h3>Login</h3>
<input name=user placeholder=Username required><br><br>
<input name=pass placeholder=Password type=password required><br><br>
<button>Login</button>
</form>
""")

@app.before_request
def auth():
    if request.path.startswith("/static") or request.path == "/login" or request.path.startswith("/data"):
        return
    if "user" not in session:
        return redirect("/login")

# ---------------- DATA API ----------------

@app.route("/data", methods=["POST"])
def receive_data():
    d = request.get_json()
    now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

    file_exists = os.path.isfile(DATA_FILE)
    with open(DATA_FILE, "a", newline="") as f:
        w = csv.writer(f)
        if not file_exists:
            w.writerow(["time", "pump", "temp", "vibration"])
        w.writerow([now, d.get("pump"), d.get("temp"), d.get("vibration", "")])

    return jsonify({"status": "ok"})

@app.route("/latest")
def latest():
    res = {p: None for p in PUMPS}
    if os.path.exists(DATA_FILE):
        rows = list(csv.DictReader(open(DATA_FILE)))
        for r in reversed(rows):
            if res[r["pump"]] is None:
                res[r["pump"]] = r
    return jsonify(res)

@app.route("/history/<pump>")
def history(pump):
    l, t, v = [], [], []
    if os.path.exists(DATA_FILE):
        for r in csv.DictReader(open(DATA_FILE)):
            if r["pump"] == pump:
                l.append(r["time"])
                t.append(float(r["temp"]))
                v.append(float(r["vibration"]) if r["vibration"] else 0)
    return jsonify({"labels": l[-50:], "temps": t[-50:], "vibes": v[-50:]})

# ---------------- THRESHOLDS ----------------

@app.route("/thresholds", methods=["GET", "POST"])
def thresholds():
    if request.method == "POST":
        data = json.load(open(THRESH_FILE))
        for p in PUMPS:
            data[p]["warning"] = float(request.form[f"{p}_w"])
            data[p]["critical"] = float(request.form[f"{p}_c"])
        json.dump(data, open(THRESH_FILE, "w"), indent=2)
        return redirect("/")

    t = json.load(open(THRESH_FILE))
    return render_template_string("""
<h2>Threshold Settings</h2>
<form method=post>
{% for p in pumps %}
<b>{{p}}</b><br>
Warning <input name='{{p}}_w' value='{{t[p]["warning"]}}'>
Critical <input name='{{p}}_c' value='{{t[p]["critical"]}}'><br><br>
{% endfor %}
<button>Save</button>
</form>
""", pumps=PUMPS, t=t)

# ---------------- DASHBOARD ----------------

@app.route("/")
def dash():
    thresh = json.load(open(THRESH_FILE))
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<meta name=viewport content="width=device-width, initial-scale=1">
<script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<script src=https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom></script>
<style>
body{font-family:sans-serif;margin:0;padding:10px}
.dark{background:#0f172a;color:white}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.card{padding:15px;border-radius:10px;text-align:center;font-weight:bold}
.normal{background:#16a34a}
.warning{background:#facc15;color:black}
.critical{background:#dc2626}
.top{display:flex;justify-content:space-between}
</style>
</head>
<body id=body class=dark>
<div class=top>
<h3>Pump Dashboard</h3>
<div>
<button onclick="toggle()">🌙/☀</button>
<a href=/thresholds>⚙</a>
</div>
</div>
<div class=grid id=grid></div>
<script>
const pumps={{pumps|safe}};
const thresh={{thresh|safe}};
const grid=document.getElementById("grid");

pumps.forEach(p=>{
 let d=document.createElement("div");
 d.className="card normal";
 d.id=p;
 d.onclick=()=>location=`/pump/${p}`;
 d.innerText=p;
 grid.appendChild(d);
});

function cls(p,t){
 if(t>=thresh[p].critical) return "critical";
 if(t>=thresh[p].warning) return "warning";
 return "normal";
}

async function refresh(){
 const r=await fetch('/latest');
 const d=await r.json();
 pumps.forEach(p=>{
  if(d[p]){
   const t=parseFloat(d[p].temp);
   const c=document.getElementById(p);
   c.className=`card ${cls(p,t)}`;
   c.innerText=`${p}\n${t}°C`;
  }
 });
}
setInterval(refresh,2000);refresh();

function toggle(){document.getElementById('body').classList.toggle('dark')}
</script>
</body></html>
""", pumps=PUMPS, thresh=thresh)

@app.route("/pump/<pump>")
def pump_page(pump):
    return render_template_string("""
<html><head>
<script src=https://cdn.jsdelivr.net/npm/chart.js></script>
<script src=https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom></script>
</head><body>
<h3>{{pump}}</h3>
<canvas id=t></canvas><canvas id=v></canvas>
<script>
const p="{{pump}}";
const tc=new Chart(t,{type:'line',data:{labels:[],datasets:[{label:'Temp',data:[]}]} ,options:{plugins:{zoom:{zoom:{wheel:{enabled:true}},pan:{enabled:true}}}}});
const vc=new Chart(v,{type:'line',data:{labels:[],datasets:[{label:'Vibration',data:[]}]} ,options:{plugins:{zoom:{zoom:{wheel:{enabled:true}},pan:{enabled:true}}}}});
async function load(){
 const r=await fetch(`/history/${p}`);
 const d=await r.json();
 tc.data.labels=d.labels;tc.data.datasets[0].data=d.temps;
 vc.data.labels=d.labels;vc.data.datasets[0].data=d.vibes;
 tc.update();vc.update();}
setInterval(load,2000);load();
</script></body></html>
""", pump=pump)

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5050)
