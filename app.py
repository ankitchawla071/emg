from flask import Flask, request, jsonify, render_template_string, send_file
import pandas as pd
import os

app = Flask(__name__)
CSV_FILE = "data.csv"

# ESP posts data here
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

# Dashboard page
@app.route('/')
def index():
    if os.path.exists(CSV_FILE):
        df = pd.read_csv(CSV_FILE)
        labels = df['datetime'].tolist()
        temps = df['temp'].tolist()
    else:
        labels, temps = [], []
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <title>KOD Pump Monitoring</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body style="font-family: Arial; text-align:center; padding:20px;">
    <h2>KOD Pump Monitoring</h2>
    <canvas id="tempChart" width="400" height="200"></canvas>
    <script>
    const labels = {{ labels|safe }};
    const temps = {{ temps|safe }};
    const ctx = document.getElementById('tempChart').getContext('2d');
    const tempChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Temperature (°C)',
                data: temps,
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
    </script>
    <p><a href="/download">Download CSV</a></p>
    </body>
    </html>
    """
    return render_template_string(html, labels=labels, temps=temps)

# download CSV
@app.route('/download')
def download_csv():
    if os.path.exists(CSV_FILE):
        return send_file(CSV_FILE, as_attachment=True)
    return "No data yet"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5050)))
