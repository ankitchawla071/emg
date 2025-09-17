from flask import Flask, request, jsonify, render_template_string
import csv, os, time

app = Flask(__name__)
history = []  # in-memory buffer

THRESHOLD = 32.0  # for alerts (optional)

@app.route("/data", methods=["POST"])
def receive_data():
    data = request.get_json(force=True)
    temp = float(data.get("temp", 0))
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    record = {"timestamp": timestamp, "temp": temp}
    history.append(record)

    # append to CSV
    file_exists = os.path.isfile("data.csv")
    with open("data.csv", "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp","temp"])
        writer.writerow([timestamp, temp])

    # optional telegram alert
    if temp > THRESHOLD:
        print(f"ALERT! Temperature {temp} > {THRESHOLD}")

    return jsonify({"status": "ok"})

@app.route("/")
def dashboard():
    html = """
    <html>
    <head>
      <meta name="viewport" content="width=device-width,initial-scale=1">
      <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="font-family:Arial;text-align:center;">
      <h2>ESP32 Temperature Dashboard</h2>
      <canvas id="chart" width="600" height="300"></canvas>
      <script>
        async function load() {
          let res = await fetch('/history');
          let json = await res.json();
          let labels = json.map(r => r.timestamp);
          let temps  = json.map(r => r.temp);
          const ctx = document.getElementById('chart').getContext('2d');
          new Chart(ctx, {
            type:'line',
            data:{labels:labels,datasets:[{label:'Temp °C',data:temps,borderColor:'blue'}]},
            options:{responsive:true,animation:false,scales:{y:{beginAtZero:false}}}
          });
        }
        load();
      </script>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route("/history")
def get_history():
    # send last 200 rows
    return jsonify(history[-200:])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
