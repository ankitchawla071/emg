from flask import Flask, request, jsonify, render_template_string, send_file
import pandas as pd
import os

app = Flask(__name__)
CSV_FILE = "data.csv"

@app.route('/data', methods=['POST'])
def post_data():
    content = request.get_json()
    temp = float(content.get("temp", 0))
    # append to CSV
    df = pd.DataFrame([[pd.Timestamp.now(), temp]], columns=["datetime","temp"])
    if not os.path.exists(CSV_FILE):
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, index=False, mode='a', header=False)
    return jsonify({"status":"ok"})

# returns full history for chart.js
@app.route('/history')
def history():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        return jsonify({
            "labels": df["datetime"].tolist(),
            "temps": df["temp"].tolist()
        })
    return jsonify({"labels":[],"temps":[]})

@app.route('/')
def index():
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>KOD Pump Monitoring</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="font-family: Arial; text-align:center; padding:20px;">
    <h2>KOD Pump Monitoring</h2>
    <canvas id="tempChart" width="400" height="200"></canvas>

    <script>
    const ctx = document.getElementById('tempChart').getContext('2d');
    const tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature (°C)',
                data: [],
                borderColor: 'blue',
                borderWidth: 2,
                fill: false,
                tension: 0.1
            }]
        },
        options: {
            animation: false,
            responsive: true,
            scales: { y: { beginAtZero:false } }
        }
    });

    async function fetchHistory(){
        const res = await fetch('/history');
        const data = await res.json();
        tempChart.data.labels = data.labels;
        tempChart.data.datasets[0].data = data.temps;
        tempChart.update();
    }

    // load initially
    fetchHistory();
    // update every 5 seconds
    setInterval(fetchHistory, 5000);
    </script>
    <p><a href="/download">Download CSV</a></p>
    </body>
    </html>
    """
    return render_template_string(html)

@app.route('/download')
def download_csv():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No data yet"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5050)))
