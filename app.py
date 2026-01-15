

from flask import Flask, request, jsonify, render_template_string, redirect import csv, os, json from datetime import datetime import pytz

app = Flask(name) DATA_FILE = "pump_data.csv" THRESH_FILE = "thresholds.json" IST = pytz.timezone("Asia/Kolkata")

PUMPS = ["KOD Pump", "Degrease Pump", "Cold Rinse Pump", "Hot Rinse Pump", "DryOff Burner"]

DEFAULT_THRESH = {p: {"warning": 38, "critical": 45} for p in PUMPS}

def load_thresholds(): if not os.path.exists(THRESH_FILE): with open(THRESH_FILE, "w") as f: json.dump(DEFAULT_THRESH, f, indent=2) return json.load(open(THRESH_FILE))

@app.route("/data", methods=["POST"]) def receive_data(): d = request.get_json() now = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S")

exists = os.path.isfile(DATA_FILE)
with open(DATA_FILE, "a", newline="") as f:
    w = csv.writer(f)
    if not exists:
        w.writerow(["time", "pump", "temp", "vibration"])
    w.writerow([now, d["pump"], d["temp"], d.get("vibration", 0)])

return jsonify({"ok": True})

@app.route("/latest") def latest(): result = {p: None for p in PUMPS}

if os.path.exists(DATA_FILE):
    rows = list(csv.DictReader(open(DATA_FILE)))
    for r in reversed(rows):
        if r["pump"] in result and result[r["pump"]] is None:
            result[r["pump"]] = r

return jsonify({"data": result, "thresholds": load_thresholds()})

@app.route("/history/<pump>") def history(pump): labels, temps, vibes = [], [], []

if os.path.exists(DATA_FILE):
    for r in csv.DictReader(open(DATA_FILE)):
        if r["pump"] == pump:
            labels.append(r["time"])
            temps.append(float(r["temp"]))
            vibes.append(float(r["vibration"]))

return jsonify({"labels": labels[-50:], "temps": temps[-50:], "vibes": vibes[-50:]})

@app.route("/thresholds", methods=["GET", "POST"]) def thresholds(): if request.method == "POST": t = {} for p in PUMPS: t[p] = { "warning": float(request.form[f"{p}_w"]), "critical": float(request.form[f"{p}_c"]) } json.dump(t, open(THRESH_FILE, "w"), indent=2) return redirect("/thresholds")

th = load_thresholds()

return render_template_string(THRESH_HTML, pumps=PUMPS, th=th)

@app.route("/") def home(): return render_template_string(DASHBOARD_HTML, pumps=PUMPS)

@app.route("/pump/<pump>") def pump_page(pump): return render_template_string(PUMP_HTML, pump=pump)

-------------------- HTML --------------------

TOGGLE_CSS = """ .toggle{width:50px;height:26px;border-radius:20px;background:#ccc;position:relative;cursor:pointer;transition:.3s} .toggle::after{content:'';width:22px;height:22px;border-radius:50%;background:#fff;position:absolute;top:2px;left:2px;transition:.3s} .toggle.on{background:#22c55e} .toggle.on::after{left:26px} """

DASHBOARD_HTML = f"""

<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
body{{font-family:Arial;background:#0f172a;color:white}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}
.card{{padding:20px;border-radius:12px;cursor:pointer;text-align:center;font-weight:bold}}
.normal{{background:#16a34a}}
.warning{{background:#facc15;color:black}}
.critical{{background:#dc2626}}
{TOGGLE_CSS}
</style></head>
<body>
<h2>Pump Monitoring</h2>
<div class="grid" id="grid"></div>
<script>
const pumps = {PUMPS};
const grid = document.getElementById('grid');pumps.forEach(p=>{{ let d=document.createElement('div'); d.className='card normal'; d.id=p; d.innerText=p; d.onclick=()=>location='/pump/'+p; grid.appendChild(d); }});

async function refresh(){{ const r=await fetch('/latest'); const j=await r.json();

pumps.forEach(p=>{{ const d=j.data[p]; if(!d) return; const t=parseFloat(d.temp); const th=j.thresholds[p]; let cls='normal'; if(t>=th.critical) cls='critical'; else if(t>=th.warning) cls='warning';

const c=document.getElementById(p); c.className='card '+cls; c.innerText=p+"\n"+t.toFixed(1)+"°C"; }}); }} setInterval(refresh,2000);refresh(); </script></body></html> """

PUMP_HTML = f"""

<!DOCTYPE html><html><head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
<style>{TOGGLE_CSS}</style>
</head>
<body>
<h2>{{{{pump}}}}</h2>
<div class="toggle" id="tg"></div> Enable Alerts
<canvas id="t"></canvas>
<canvas id="v"></canvas><script>
let alerts=true;
const tg=document.getElementById('tg');
tg.onclick=()=>{{alerts=!alerts;tg.classList.toggle('on')}};
tg.classList.add('on');

const tempChart=new Chart(t.getContext('2d'),{{type:'line',data:{{labels:[],datasets:[{{label:'Temp',data:[],borderColor:'red'}}]}},options:{{plugins:{{zoom:{{zoom:{{wheel:{{enabled:true}},mode:'x'}},pan:{{enabled:true,mode:'x'}}}}}}}}}});

const vibChart=new Chart(v.getContext('2d'),{{type:'line',data:{{labels:[],datasets:[{{label:'Vibration',data:[],borderColor:'#22c55e'}}]}},options:{{plugins:{{zoom:{{zoom:{{wheel:{{enabled:true}},mode:'x'}},pan:{{enabled:true,mode:'x'}}}}}}}}}});

async function load(){{
 const r=await fetch('/history/{{{{pump}}}}');
 const d=await r.json();
 const th=(await (await fetch('/latest')).json()).thresholds['{{{{pump}}}}'];

 tempChart.data.labels=d.labels;
 tempChart.data.datasets[0].data=d.temps;
 vibChart.data.labels=d.labels;
 vibChart.data.datasets[0].data=d.vibes;

 tempChart.options.plugins.annotation={{annotations:{{w:{{type:'line',yMin:th.warning,yMax:th.warning,borderColor:'yellow'}},c:{{type:'line',yMin:th.critical,yMax:th.critical,borderColor:'red'}}}}}};

 tempChart.update();vibChart.update();
}}
setInterval(load,2000);load();
</script></body></html>"""

THRESH_HTML = f"""

<!DOCTYPE html><html><head><style>body{{font-family:Arial;background:#0f172a;color:white}} .card{{background:#1e293b;padding:15px;margin:10px;border-radius:10px}} input{{width:60px}} button{{padding:10px;background:#22c55e;border:none}} </style></head><body>

<h2>Threshold Settings</h2>
<form method=post>
{{% for p in pumps %}}
<div class=card>
<b>{{{{p}}}}</b><br>
Warning <input name="{{{{p}}}}_w" value="{{{{th[p]['warning']}}}}">
Critical <input name="{{{{p}}}}_c" value="{{{{th[p]['critical']}}}}">
</div>
{{% endfor %}}
<button>Save</button>
</form>
</body></html>
"""if name=='main': app.run(host='0.0.0.0',port=5050)@app.route("/pump/<pump>")
def pump_page(pump):
    return render_template_string("""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom"></script>
</head>
<body>
<h3>{{pump}}</h3>
<canvas id="t"></canvas>
<canvas id="v"></canvas>
<script>
const pump = "{{pump}}";

const tc = new Chart(t, {
  type:'line',
  data:{labels:[],datasets:[{label:'Temperature',data:[]}]},
  options:{plugins:{zoom:{zoom:{wheel:{enabled:true}},pan:{enabled:true}}}}
});

const vc = new Chart(v, {
  type:'line',
  data:{labels:[],datasets:[{label:'Vibration',data:[]}]},
  options:{plugins:{zoom:{zoom:{wheel:{enabled:true}},pan:{enabled:true}}}}
});

async function load(){
  const r = await fetch(`/history/${pump}`);
  const d = await r.json();
  tc.data.labels = d.labels;
  tc.data.datasets[0].data = d.temps;
  vc.data.labels = d.labels;
  vc.data.datasets[0].data = d.vibes;
  tc.update();
  vc.update();
}

setInterval(load, 1000);
load();
</script>
</body>
</html>
""", pump=pump)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
