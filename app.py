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

PORT = int(
    os.environ.get(
        "PORT",
        5050
    )
)


# ============================================================
# LOGIN
# ============================================================

USERNAME = os.environ.get(
    "DASHBOARD_USER",
    "admin"
)

PASSWORD = os.environ.get(
    "DASHBOARD_PASSWORD",
    "admin123"
)


# ============================================================
# SHOP FLOOR AREAS
# ============================================================

AREAS = [
    "LMS",
    "HMS",
    "Transmission Assembly",
    "Tractor Assembly",
    "Paintshop"
]


# ============================================================
# DATA FILE
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATA_FILE = os.path.join(
    BASE_DIR,
    "environment_data.csv"
)


# ============================================================
# INITIALIZE CSV
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


initialize_data_file()


# ============================================================
# LOGIN DECORATOR
# ============================================================

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if not session.get(
            "logged_in"
        ):

            return redirect(
                url_for("login")
            )

        return func(
            *args,
            **kwargs
        )

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

<title>
Shop Floor Temperature Monitoring
</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    display: flex;

    align-items: center;

    justify-content: center;

    font-family:
        Arial,
        sans-serif;

    color: white;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );
}


.login-box {

    width: 90%;

    max-width: 380px;

    padding: 30px;

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

    box-shadow:
        0 20px 60px
        rgba(
            0,
            0,
            0,
            0.4
        );
}


h2 {

    text-align: center;

    margin-top: 0;

    margin-bottom: 25px;

}


input {

    width: 100%;

    padding: 13px;

    margin-bottom: 15px;

    border: none;

    border-radius: 10px;

    outline: none;

    background:
        rgba(
            255,
            255,
            255,
            0.12
        );

    color: white;

    font-size: 15px;
}


input::placeholder {

    color:
        #aeb9cc;
}


button {

    width: 100%;

    padding: 13px;

    border: none;

    border-radius: 10px;

    background:
        #2563eb;

    color: white;

    font-size: 16px;

    cursor: pointer;

}


.error {

    color:
        #ff7777;

    text-align: center;

    margin-bottom: 15px;

}

</style>

</head>


<body>


<div class="login-box">


<h2>
🌡 Temperature Monitor
</h2>


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
# LOGIN
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
# RECEIVE ESP32 DATA
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
                "message":
                    "No JSON data received"
            }), 400


        # ----------------------------------------------------
        # AREA
        # ----------------------------------------------------

        area = data.get(
            "area"
        )


        if area not in AREAS:

            return jsonify({
                "status": "error",
                "message":
                    "Invalid area"
            }), 400


        # ----------------------------------------------------
        # TEMPERATURE
        # ----------------------------------------------------

        temperature = data.get(
            "temperature"
        )


        if temperature is None:

            return jsonify({
                "status": "error",
                "message":
                    "Temperature missing"
            }), 400


        temperature = float(
            temperature
        )


        # ----------------------------------------------------
        # TIMESTAMP
        # ----------------------------------------------------

        timestamp = datetime.now(
            timezone.utc
        ).isoformat()


        # ----------------------------------------------------
        # SAVE TO CSV
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
            f"[DATA] "
            f"{area} → "
            f"{temperature:.2f} °C"
        )


        return jsonify({

            "status":
                "success",

            "area":
                area,

            "temperature":
                temperature
        })


    except Exception as e:

        print(
            "DATA ERROR:",
            str(e)
        )


        return jsonify({

            "status":
                "error",

            "message":
                str(e)

        }), 500


# ============================================================
# READ CSV DATA
# ============================================================

def read_data():

    rows = []


    if not os.path.exists(
        DATA_FILE
    ):

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
                            row[
                                "timestamp"
                            ],

                        "area":
                            row[
                                "area"
                            ],

                        "temperature":
                            float(
                                row[
                                    "temperature"
                                ]
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
# GET LATEST READING
# ============================================================

def get_latest():

    data = read_data()


    latest = {

        area:
            None

        for area in AREAS

    }


    for row in data:

        area = row[
            "area"
        ]


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
# OFFLINE DETECTION
# ============================================================

def get_status(
    timestamp
):

    if not timestamp:

        return "OFFLINE"


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


        # Offline if no data for 2 minutes

        if age > 120:

            return "OFFLINE"


        return "ONLINE"


    except Exception:

        return "OFFLINE"


# ============================================================
# LATEST API
# ============================================================

@app.route("/latest")

def latest_api():

    latest = get_latest()


    result = {}


    for area in AREAS:

        item = latest.get(
            area
        )


        if item is None:

            result[area] = {

                "temperature":
                    None,

                "timestamp":
                    None,

                "status":
                    "OFFLINE"

            }


        else:

            result[area] = {

                "temperature":
                    item[
                        "temperature"
                    ],

                "timestamp":
                    item[
                        "timestamp"
                    ],

                "status":
                    get_status(
                        item[
                            "timestamp"
                        ]
                    )

            }


    return jsonify(
        result
    )


# ============================================================
# HISTORY API
# ============================================================

@app.route(
    "/history/<path:area>"
)

def history_api(
    area
):

    if area not in AREAS:

        return jsonify({

            "error":
                "Invalid area"

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
        datetime.now(
            timezone.utc
        )
        -
        timedelta(
            minutes=minutes
        )
    )


    result = []


    for row in read_data():

        if row[
            "area"
        ] != area:

            continue


        try:

            timestamp = datetime.fromisoformat(
                row[
                    "timestamp"
                ].replace(
                    "Z",
                    "+00:00"
                )
            )


            if timestamp >= cutoff:

                result.append({

                    "timestamp":
                        row[
                            "timestamp"
                        ],

                    "temperature":
                        row[
                            "temperature"
                        ]

                })


        except Exception:

            continue


    return jsonify(
        result
    )


# ============================================================
# DASHBOARD
# ============================================================

DASHBOARD_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>
Shop Floor Temperature Monitoring
</title>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    font-family:
        Arial,
        sans-serif;

    color: white;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );
}


.header {

    max-width: 1400px;

    margin: auto;

    padding: 22px;

    display: flex;

    align-items: center;

    justify-content: space-between;

    flex-wrap: wrap;

    gap: 15px;
}


.title {

    font-size: 25px;

    font-weight: bold;

}


.subtitle {

    margin-top: 5px;

    color:
        #94a3b8;

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

    padding:
        10px 20px 30px;
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

    padding: 24px;

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

    font-size: 18px;

    font-weight: bold;

    min-height: 44px;

}


.temperature {

    margin-top: 15px;

    font-size: 43px;

    font-weight: bold;

}


.unit {

    font-size: 20px;

    color:
        #94a3b8;

}


.status {

    margin-top: 15px;

    font-size: 12px;

    font-weight: bold;

    letter-spacing: 1px;

}


.status.ONLINE {

    color:
        #58d68d;
}


.status.OFFLINE {

    color:
        #9ca3af;
}


.updated {

    margin-top: 8px;

    font-size: 11px;

    color:
        #64748b;
}


.footer {

    text-align: center;

    margin-top: 35px;

    color:
        #64748b;

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


const AREAS =
    {{ areas | tojson }};



function formatTime(
    timestamp
) {

    if (!timestamp) {

        return "No data received";
    }


    const date =
        new Date(
            timestamp
        );


    return date.toLocaleString(
        undefined,
        {

            day:
                "2-digit",

            month:
                "short",

            hour:
                "2-digit",

            minute:
                "2-digit",

            second:
                "2-digit"

        }
    );
}



function createCards(
    data
) {

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
                    item.temperature
                    !== null
                ) {

                    temperature =
                        Number(
                            item.temperature
                        ).toFixed(1);
                }


                status =
                    item.status
                    ||
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
                    <span class="unit">
                        °C
                    </span>
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
                    cache:
                        "no-store"
                }
            );


        const data =
            await response.json();


        createCards(
            data
        );


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
# DASHBOARD ROUTE
# ============================================================

@app.route("/")

@login_required

def dashboard():

    return render_template_string(

        DASHBOARD_HTML,

        areas=AREAS

    )


# ============================================================
# AREA DETAIL PAGE
# ============================================================

AREA_HTML = """

<!DOCTYPE html>

<html>

<head>

<meta name="viewport"
      content="width=device-width, initial-scale=1">

<title>
{{ area }}
</title>


<script src=
"https://cdn.jsdelivr.net/npm/chart.js">
</script>


<style>

* {
    box-sizing: border-box;
}


body {

    margin: 0;

    min-height: 100vh;

    font-family:
        Arial,
        sans-serif;

    color: white;

    background:
        linear-gradient(
            135deg,
            #0f172a,
            #172554
        );
}


.header {

    max-width: 1200px;

    margin: auto;

    padding: 22px;
}


.back {

    color:
        #93c5fd;

    text-decoration: none;
}


h1 {

    margin-top: 20px;

    margin-bottom: 5px;

}


.subtitle {

    color:
        #94a3b8;
}


.current {

    margin-top: 25px;

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


.current-label {

    color:
        #94a3b8;

}


.current-temp {

    margin-top: 8px;

    font-size: 48px;

    font-weight: bold;

}


.current-status {

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

    color: white;

    background:
        rgba(
            255,
            255,
            255,
            0.10
        );
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


<div class="subtitle">
Temperature History
</div>


<div class="current">


<div class="current-label">
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
    class="current-status"
>
● OFFLINE
</div>


</div>


<div class="controls">


<button
    onclick="loadHistory(15)"
>
15 min
</button>


<button
    onclick="loadHistory(30)"
>
30 min
</button>


<button
    onclick="loadHistory(60)"
>
1 hour
</button>


<button
    onclick="loadHistory(360)"
>
6 hours
</button>


<button
    onclick="loadHistory(1440)"
>
24 hours
</button>


<button
    onclick="loadHistory(10080)"
>
7 days
</button>


<button
    onclick="loadHistory(43200)"
>
30 days
</button>


</div>


<div class="chart-box">

<canvas
    id="temperatureChart"
>
</canvas>

</div>


</div>


<script>


const AREA =
    {{ area | tojson }};


let chart =
    null;



function createChart(
    labels,
    values
) {

    const canvas =
        document.getElementById(
            "temperatureChart"
        );


    const ctx =
        canvas.getContext(
            "2d"
        );


    if (chart) {

        chart.destroy();
    }


    chart =
        new Chart(
            ctx,
            {

                type:
                    "line",


                data: {

                    labels:
                        labels,


                    datasets: [{

                        label:
                            "Temperature (°C)",

                        data:
                            values,

                        borderWidth:
                            2,

                        pointRadius:
                            1,

                        tension:
                            0.25,

                        fill:
                            false

                    }]

                },


                options: {

                    responsive:
                        true,

                    maintainAspectRatio:
                        false,


                    interaction: {

                        intersect:
                            false,

                        mode:
                            "index"

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
                    cache:
                        "no-store"
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
            item.temperature
            === null
        ) {

            tempElement.innerText =
                "-- °C";

        }

        else {

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


        if (
            item.status ===
            "ONLINE"
        ) {

            statusElement.style.color =
                "#58d68d";

        }

        else {

            statusElement.style.color =
                "#9ca3af";
        }


    } catch (error) {

        console.error(
            error
        );
    }
}



loadHistory(
    60
);


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
# AREA ROUTE
# ============================================================

@app.route(
    "/area/<path:area>"
)

@login_required

def area_page(
    area
):

    if area not in AREAS:

        return redirect(
            url_for(
                "dashboard"
            )
        )


    return render_template_string(

        AREA_HTML,

        area=area

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

        return (
            "No data available.",
            404
        )


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

@app.route(
    "/health"
)

def health():

    return jsonify({

        "status":
            "ok",

        "service":
            "Shop Floor Temperature Monitor"

    })


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(

        host="0.0.0.0",

        port=PORT,

        debug=False

    )
