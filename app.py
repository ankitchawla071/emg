from flask import (
    Flask,
    request,
    jsonify,
    render_template_string,
    redirect,
    url_for,
    session,
    Response
)

import csv
import os
import json
from datetime import datetime, timedelta, timezone
from functools import wraps


# ============================================================
# FLASK CONFIGURATION
# ============================================================

app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)

PORT = int(os.environ.get("PORT", 5050))


# ============================================================
# LOGIN
# ============================================================

USERNAME = os.environ.get("DASHBOARD_USER", "admin")
PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "admin123")


# ============================================================
# AREAS
# ============================================================

AREAS = [
    "LMS",
    "HMS",
    "Transmission Assembly",
    "Tractor Assembly",
    "Paintshop"
]


# ============================================================
# FILES
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_FILE = os.path.join(
    BASE_DIR,
    "environment_data.csv"
)

THRESHOLD_FILE = os.path.join(
    BASE_DIR,
    "thresholds.json"
)


# ============================================================
# DEFAULT TEMPERATURE THRESHOLDS
# ============================================================

DEFAULT_THRESHOLDS = {
    "warning": 35.0,
    "critical": 40.0
}


# ============================================================
# INITIALIZE DATA FILE
# ============================================================

def initialize_data_file():

    if not os.path.exists(DATA_FILE):

        with open(
            DATA_FILE,
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                "timestamp",
                "area",
                "temperature"
            ])


# ============================================================
# LOAD THRESHOLDS
# ============================================================

def load_thresholds():

    if not os.path.exists(THRESHOLD_FILE):

        thresholds = {
            area: DEFAULT_THRESHOLDS.copy()
            for area in AREAS
        }

        save_thresholds(thresholds)

        return thresholds


    try:

        with open(
            THRESHOLD_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            thresholds = json.load(f)


        # Make sure all areas exist

        for area in AREAS:

            if area not in thresholds:

                thresholds[area] = DEFAULT_THRESHOLDS.copy()

            else:

                thresholds[area].setdefault(
                    "warning",
                    DEFAULT_THRESHOLDS["warning"]
                )

                thresholds[area].setdefault(
                    "critical",
                    DEFAULT_THRESHOLDS["critical"]
                )


        return thresholds


    except Exception:

        return {
            area: DEFAULT_THRESHOLDS.copy()
            for area in AREAS
        }


# ============================================================
# SAVE THRESHOLDS
# ============================================================

def save_thresholds(thresholds):

    with open(
        THRESHOLD_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            thresholds,
            f,
            indent=4
        )


# ============================================================
# INITIALIZE
# ============================================================

initialize_data_file()

thresholds = load_thresholds()


# ============================================================
# LOGIN DECORATOR
# ============================================================

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):

            return redirect(
                url_for("login")
            )

        return func(*args, **kwargs)

    return wrapper


# ============================================================
# LOGIN PAGE
# ============================================================

LOGIN_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Environmental Monitoring</title>

<style>

body {

    margin: 0;

    font-family: Arial, sans-serif;

    background:
        linear-gradient(
            135deg,
            #101827,
            #18253b
        );

    color: white;

    min-height: 100vh;

    display: flex;

    justify-content: center;

    align-items: center;
}


.login-box {

    width: 90%;

    max-width: 380px;

    padding: 30px;

    background: rgba(
        255,
        255,
        255,
        0.08
    );

    border-radius: 20px;

    backdrop-filter: blur(15px);

    box-shadow:
        0 20px 60px
        rgba(0,0,0,0.4);

}


h2 {

    text-align: center;

    margin-bottom: 25px;

}


input {

    width: 100%;

    box-sizing: border-box;

    padding: 13px;

    margin-bottom: 15px;

    border: none;

    border-radius: 10px;

    background: rgba(
        255,
        255,
        255,
        0.12
    );

    color: white;

    font-size: 15px;

}


button {

    width: 100%;

    padding: 13px;

    border: none;

    border-radius: 10px;

    background: #2563eb;

    color: white;

    font-size: 16px;

    cursor: pointer;

}


.error {

    color: #ff7777;

    text-align: center;

    margin-bottom: 15px;

}

</style>

</head>


<body>


<div class="login-box">

<h2>🌡 Environmental Monitor</h2>


{% if error %}

<div class="error">
{{ error }}
</div>

{% endif %}


<form method="POST">

<input
    type="text"
    name="username"
    placeholder="Username"
    required
>


<input
    type="password"
    name="password"
    placeholder="Password"
    required
>


<button type="submit">
Login
</button>

</form>


</div>

</body>

</html>

"""


# ============================================================
# LOGIN ROUTE
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)

def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        )

        password = request.form.get(
            "password",
            ""
        )


        if (
            username == USERNAME
            and
            password == PASSWORD
        ):

            session["logged_in"] = True

            return redirect(
                url_for("dashboard")
            )


        return render_template_string(
            LOGIN_HTML,
            error="Invalid username or password."
        )


    return render_template_string(
        LOGIN_HTML,
        error=None
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")

def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# RECEIVE DATA FROM ESP32
# ============================================================

@app.route(
    "/data",
    methods=["POST"]
)

def receive_data():

    try:

        data = request.get_json(
            force=True
        )


        if not data:

            return jsonify({
                "status": "error",
                "message": "No JSON data received"
            }), 400


        area = data.get("area")

        temperature = data.get(
            "temperature"
        )


        # ----------------------------------------------------
        # Validate area
        # ----------------------------------------------------

        if area not in AREAS:

            return jsonify({
                "status": "error",
                "message": "Invalid area"
            }), 400


        # ----------------------------------------------------
        # Validate temperature
        # ----------------------------------------------------

        if temperature is None:

            return jsonify({
                "status": "error",
                "message": "Temperature missing"
            }), 400


        temperature = float(
            temperature
        )


        # ----------------------------------------------------
        # Timestamp
        # ----------------------------------------------------

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()


        # ----------------------------------------------------
        # Save
        # ----------------------------------------------------

        with open(
            DATA_FILE,
            "a",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.writer(f)

            writer.writerow([
                timestamp,
                area,
                temperature
            ])


        print(
            f"[DATA] {area}: "
            f"{temperature:.2f} °C"
        )


        return jsonify({
            "status": "success",
            "area": area,
            "temperature": temperature
        })


    except Exception as e:

        print(
            "DATA ERROR:",
            str(e)
        )

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


# ============================================================
# READ ALL DATA
# ============================================================

def read_data():

    rows = []

    if not os.path.exists(DATA_FILE):

        return rows


    try:

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            reader = csv.DictReader(f)


            for row in reader:

                try:

                    rows.append({
                        "timestamp":
                            row["timestamp"],

                        "area":
                            row["area"],

                        "temperature":
                            float(
                                row["temperature"]
                            )
                    })

                except Exception:

                    continue


    except Exception as e:

        print(
            "READ ERROR:",
            str(e)
        )


    return rows


# ============================================================
# LATEST READING FOR EACH AREA
# ============================================================

def get_latest():

    data = read_data()

    latest = {}


    for area in AREAS:

        latest[area] = None


    for row in data:

        area = row["area"]


        if area not in AREAS:

            continue


        if (
            latest[area] is None
            or
            row["timestamp"]
            >
            latest[area]["timestamp"]
        ):

            latest[area] = row


    return latest


# ============================================================
# TEMPERATURE STATUS
# ============================================================

def get_status(area, temperature, timestamp):

    if temperature is None:

        return "OFFLINE"


    # --------------------------------------------------------
    # Offline after 2 minutes
    # --------------------------------------------------------

    try:

        dt = datetime.fromisoformat(
            timestamp.replace(
                "Z",
                "+00:00"
            )
        )


        now = datetime.now(
            timezone.utc
        )


        age = (
            now - dt
        ).total_seconds()


        if age > 120:

            return "OFFLINE"


    except Exception:

        pass


    area_thresholds = thresholds.get(
        area,
        DEFAULT_THRESHOLDS
    )


    if temperature >= area_thresholds["critical"]:

        return "CRITICAL"


    if temperature >= area_thresholds["warning"]:

        return "WARNING"


    return "NORMAL"


# ============================================================
# LATEST API
# ============================================================

@app.route("/latest")

def latest_api():

    latest = get_latest()

    result = {}


    for area in AREAS:

        item = latest.get(area)


        if item is None:

            result[area] = {
                "temperature": None,
                "timestamp": None,
                "status": "OFFLINE"
            }

        else:

            result[area] = {

                "temperature":
                    item["temperature"],

                "timestamp":
                    item["timestamp"],

                "status":
                    get_status(
                        area,
                        item["temperature"],
                        item["timestamp"]
                    )
            }


    return jsonify(result)


# ============================================================
# HISTORY API
# ============================================================

@app.route(
    "/history/<path:area>"
)

def history_api(area):

    if area not in AREAS:

        return jsonify({
            "error": "Invalid area"
        }), 404


    minutes = request.args.get(
        "minutes",
        default=60,
        type=int
    )


    # Maximum 30 days

    minutes = min(
        minutes,
        43200
    )


    cutoff = (
        datetime.now(timezone.utc)
        -
        timedelta(
            minutes=minutes
        )
    )


    result = []


    for row in read_data():

        if row["area"] != area:

            continue


        try:

            timestamp = datetime.fromisoformat(
                row["timestamp"].replace(
                    "Z",
                    "+00:00"
                )
            )


            if timestamp >= cutoff:

                result.append({

                    "timestamp":
                        row["timestamp"],

                    "temperature":
                        row["temperature"]
                })


        except Exception:

            continue


    return jsonify(result)


# ============================================================
# DASHBOARD HTML
# ============================================================

DASHBOARD_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Environmental Monitoring</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    font-family:
        Arial,
        sans-serif;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );

    color: white;

    min-height: 100vh;
}


.header {

    padding: 20px;

    display: flex;

    justify-content: space-between;

    align-items: center;

    flex-wrap: wrap;

    gap: 10px;
}


.title {

    font-size: 25px;

    font-weight: bold;
}


.subtitle {

    color: #aeb9cc;

    margin-top: 5px;

    font-size: 13px;
}


.logout {

    text-decoration: none;

    color: white;

    padding:
        9px 15px;

    border-radius: 10px;

    background:
        rgba(
            255,
            255,
            255,
            0.10
        );

}


.container {

    max-width: 1400px;

    margin: auto;

    padding: 15px;
}


.cards {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(
                230px,
                1fr
            )
        );

    gap: 18px;
}


.card {

    padding: 22px;

    border-radius: 20px;

    background:
        rgba(
            255,
            255,
            255,
            0.08
        );

    border:
        1px solid
        rgba(
            255,
            255,
            255,
            0.08
        );

    backdrop-filter:
        blur(15px);

    cursor: pointer;

    transition:
        transform 0.2s,
        background 0.2s;

}


.card:hover {

    transform:
        translateY(-4px);

    background:
        rgba(
            255,
            255,
            255,
            0.13
        );

}


.area {

    font-size: 17px;

    font-weight: bold;

    margin-bottom: 20px;

}


.temperature {

    font-size: 42px;

    font-weight: bold;

}


.unit {

    font-size: 20px;

    color: #aeb9cc;

}


.status {

    margin-top: 15px;

    font-size: 12px;

    font-weight: bold;

    letter-spacing: 1px;

}


.status.NORMAL {

    color: #58d68d;

}


.status.WARNING {

    color: #f5c542;

}


.status.CRITICAL {

    color: #ff6b6b;

}


.status.OFFLINE {

    color: #9ca3af;

}


.updated {

    margin-top: 8px;

    font-size: 11px;

    color: #94a3b8;

}


.footer {

    text-align: center;

    margin-top: 35px;

    padding-bottom: 20px;

    color: #64748b;

    font-size: 12px;

}


</style>

</head>


<body>


<div class="header">

<div>

<div class="title">
🌡 Shop Floor Temperature Monitoring
</div>

<div class="subtitle">
MLX90614 • ESP32-C3 • Real-time monitoring
</div>

</div>


<a
    class="logout"
    href="/logout"
>
Logout
</a>

</div>


<div class="container">

<div
    id="cards"
    class="cards"
>
</div>


<div class="footer">

Automatic refresh every 10 seconds

</div>

</div>


<script>


const AREAS = {{ areas | tojson }};


function formatTime(timestamp) {

    if (!timestamp) {
        return "No data received";
    }


    const date =
        new Date(timestamp);


    return date.toLocaleString(
        undefined,
        {
            day: "2-digit",
            month: "short",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        }
    );
}



function createCards(data) {

    const container =
        document.getElementById(
            "cards"
        );


    container.innerHTML = "";


    AREAS.forEach(
        function(area) {

            const item =
                data[area];


            let temperature =
                "--";


            let status =
                "OFFLINE";


            let timestamp =
                null;


            if (item) {

                if (
                    item.temperature !== null
                ) {

                    temperature =
                        Number(
                            item.temperature
                        ).toFixed(1);
                }


                status =
                    item.status ||
                    "OFFLINE";


                timestamp =
                    item.timestamp;
            }


            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "card";


            card.onclick =
                function() {

                    window.location.href =
                        "/area/" +
                        encodeURIComponent(
                            area
                        );
                };


            card.innerHTML = `

                <div class="area">
                    ${area}
                </div>

                <div class="temperature">
                    ${temperature}
                    <span class="unit">°C</span>
                </div>

                <div class="status ${status}">
                    ● ${status}
                </div>

                <div class="updated">
                    ${formatTime(timestamp)}
                </div>

            `;


            container.appendChild(
                card
            );

        }
    );
}



async function updateDashboard() {

    try {

        const response =
            await fetch(
                "/latest",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        createCards(data);


    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );
    }
}


updateDashboard();


setInterval(
    updateDashboard,
    10000
);


</script>


</body>

</html>

"""


# ============================================================
# DASHBOARD
# ============================================================

@app.route("/")

@login_required

def dashboard():

    return render_template_string(
        DASHBOARD_HTML,
        areas=AREAS
    )


# ============================================================
# AREA PAGE
# ============================================================

AREA_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>{{ area }}</title>


<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>


<style>

body {

    margin: 0;

    font-family: Arial, sans-serif;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );

    color: white;

}


.header {

    padding: 20px;

    max-width: 1200px;

    margin: auto;

}


.back {

    color: #93c5fd;

    text-decoration: none;

}


h1 {

    margin-bottom: 5px;

}


.current {

    margin-top: 20px;

    padding: 25px;

    border-radius: 20px;

    background:
        rgba(
            255,
            255,
            255,
            0.08
        );

}


.current-temp {

    font-size: 48px;

    font-weight: bold;

}


.status {

    margin-top: 10px;

    font-weight: bold;

}


.controls {

    margin-top: 20px;

    display: flex;

    flex-wrap: wrap;

    gap: 8px;

}


button {

    padding:
        9px 14px;

    border: none;

    border-radius: 9px;

    cursor: pointer;

    background:
        rgba(
            255,
            255,
            255,
            0.10
        );

    color: white;

}


button:hover {

    background:
        rgba(
            255,
            255,
            255,
            0.20
        );

}


.chart-box {

    margin-top: 20px;

    padding: 20px;

    border-radius: 20px;

    background:
        rgba(
            255,
            255,
            255,
            0.08
        );

    height: 450px;

}


canvas {

    width: 100% !important;

    height: 100% !important;

}


</style>

</head>


<body>


<div class="header">


<a
    class="back"
    href="/"
>
← Dashboard
</a>


<h1>
{{ area }}
</h1>


<div>
Temperature Monitoring
</div>


<div
    class="current"
>

<div>
Current Temperature
</div>


<div
    id="currentTemp"
    class="current-temp"
>
-- °C
</div>


<div
    id="currentStatus"
    class="status"
>
OFFLINE
</div>


</div>


<div class="controls">

<button onclick="loadHistory(15)">
15 min
</button>

<button onclick="loadHistory(30)">
30 min
</button>

<button onclick="loadHistory(60)">
1 hour
</button>

<button onclick="loadHistory(360)">
6 hours
</button>

<button onclick="loadHistory(1440)">
24 hours
</button>

<button onclick="loadHistory(10080)">
7 days
</button>

<button onclick="loadHistory(43200)">
30 days
</button>

</div>


<div class="chart-box">

<canvas id="temperatureChart"></canvas>

</div>


</div>


<script>


const AREA =
    {{ area | tojson }};


let chart = null;



function createChart(
    labels,
    values
) {

    const ctx =
        document
        .getElementById(
            "temperatureChart"
        )
        .getContext("2d");


    if (chart) {

        chart.destroy();
    }


    chart =
        new Chart(
            ctx,
            {

                type: "line",

                data: {

                    labels: labels,

                    datasets: [{

                        label:
                            "Temperature (°C)",

                        data: values,

                        borderWidth: 2,

                        pointRadius: 1,

                        tension: 0.25,

                        fill: false

                    }]

                },

                options: {

                    responsive: true,

                    maintainAspectRatio: false,

                    interaction: {

                        intersect: false,

                        mode: "index"

                    },

                    scales: {

                        x: {

                            ticks: {

                                color:
                                    "#94a3b8",

                                maxTicksLimit:
                                    12

                            },

                            grid: {

                                color:
                                    "rgba(255,255,255,0.05)"

                            }

                        },

                        y: {

                            ticks: {

                                color:
                                    "#94a3b8"

                            },

                            grid: {

                                color:
                                    "rgba(255,255,255,0.05)"

                            }

                        }

                    },

                    plugins: {

                        legend: {

                            labels: {

                                color:
                                    "white"

                            }

                        }

                    }

                }

            }
        );
}



async function loadHistory(
    minutes
) {

    try {

        const response =
            await fetch(
                "/history/" +
                encodeURIComponent(
                    AREA
                ) +
                "?minutes=" +
                minutes
            );


        const data =
            await response.json();


        const labels =
            data.map(
                item =>
                    new Date(
                        item.timestamp
                    ).toLocaleString(
                        undefined,
                        {
                            hour:
                                "2-digit",

                            minute:
                                "2-digit",

                            day:
                                "2-digit",

                            month:
                                "short"
                        }
                    )
            );


        const values =
            data.map(
                item =>
                    item.temperature
            );


        createChart(
            labels,
            values
        );


    } catch (error) {

        console.error(
            error
        );
    }
}



async function updateCurrent() {

    try {

        const response =
            await fetch(
                "/latest",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        const item =
            data[AREA];


        if (!item) {

            return;
        }


        const tempElement =
            document.getElementById(
                "currentTemp"
            );


        const statusElement =
            document.getElementById(
                "currentStatus"
            );


        if (
            item.temperature === null
        ) {

            tempElement.innerText =
                "-- °C";

        } else {

            tempElement.innerText =
                Number(
                    item.temperature
                ).toFixed(1)
                +
                " °C";
        }


        statusElement.innerText =
            "● " +
            item.status;


        statusElement.style.color =
            item.status === "NORMAL"
                ? "#58d68d"
                :
            item.status === "WARNING"
                ? "#f5c542"
                :
            item.status === "CRITICAL"
                ? "#ff6b6b"
                :
                "#9ca3af";


    } catch (error) {

        console.error(
            error
        );
    }
}



loadHistory(60);

updateCurrent();


setInterval(
    updateCurrent,
    10000
);


</script>


</body>

</html>

"""


# ============================================================
# AREA PAGE ROUTE
# ============================================================

@app.route(
    "/area/<path:area>"
)

@login_required

def area_page(area):

    if area not in AREAS:

        return redirect(
            url_for("dashboard")
        )


    return render_template_string(
        AREA_HTML,
        area=area
    )


# ============================================================
# SETTINGS PAGE
# ============================================================

SETTINGS_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>Temperature Settings</title>


<style>

body {

    margin: 0;

    font-family: Arial, sans-serif;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );

    color: white;

}


.container {

    max-width: 900px;

    margin: auto;

    padding: 25px;

}


a {

    color: #93c5fd;

}


.card {

    margin-top: 20px;

    padding: 20px;

    border-radius: 18px;

    background:
        rgba(
            255,
            255,
            255,
            0.08
        );

}


input {

    width: 100px;

    padding: 9px;

    margin:
        5px 10px 5px 5px;

    border: none;

    border-radius: 8px;

}


button {

    padding:
        10px 20px;

    border: none;

    border-radius: 9px;

    background: #2563eb;

    color: white;

    cursor: pointer;

}


</style>

</head>


<body>


<div class="container">


<a href="/">
← Dashboard
</a>


<h1>
Temperature Thresholds
</h1>


<form method="POST">


{% for area in areas %}

<div class="card">

<h3>
{{ area }}
</h3>


<label>
Warning:
</label>

<input
    type="number"
    step="0.1"
    name="{{ area }}_warning"
    value="{{ thresholds[area]['warning'] }}"
>


<label>
Critical:
</label>

<input
    type="number"
    step="0.1"
    name="{{ area }}_critical"
    value="{{ thresholds[area]['critical'] }}"
>


</div>

{% endfor %}


<br>


<button type="submit">
Save Settings
</button>


</form>


</div>


</body>

</html>

"""


# ============================================================
# SETTINGS ROUTE
# ============================================================

@app.route(
    "/settings",
    methods=["GET", "POST"]
)

@login_required

def settings():

    global thresholds


    if request.method == "POST":

        for area in AREAS:

            warning =
                request.form.get(
                    area + "_warning"
                )

            critical =
                request.form.get(
                    area + "_critical"
                )


            try:

                warning =
                    float(warning)

                critical =
                    float(critical)


                thresholds[area] = {

                    "warning":
                        warning,

                    "critical":
                        critical
                }


            except Exception:

                pass


        save_thresholds(
            thresholds
        )


        return redirect(
            url_for("settings")
        )


    return render_template_string(
        SETTINGS_HTML,
        areas=AREAS,
        thresholds=thresholds
    )


# ============================================================
# CSV DOWNLOAD
# ============================================================

@app.route(
    "/download"
)

@login_required

def download():

    if not os.path.exists(
        DATA_FILE
    ):

        return "No data available."


    with open(
        DATA_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        data = f.read()


    return Response(

        data,

        mimetype="text/csv",

        headers={
            "Content-Disposition":
                "attachment; "
                "filename=temperature_data.csv"
        }
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")

def health():

    return jsonify({
        "status": "ok",
        "service":
            "Shop Floor Temperature Monitor"
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
