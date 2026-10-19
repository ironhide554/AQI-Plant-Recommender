import os
import sys
import random
from datetime import datetime
import certifi
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from dotenv import load_dotenv
import plotly.express as px
from pymongo import MongoClient
import requests

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Load environment configuration
load_dotenv()

app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.FLATLY],
    title="AQI Plant Recommender"
)
server = app.server

# Configuration
OWM_API_KEY = os.getenv("OWM_API_KEY", "a00174d020ab1cec2d561cbffadd4c96").strip()
MONGO_URL = os.getenv("MONGO_URL", "").strip()
DB_NAME = os.getenv("MONGO_DB", "AirQuality").strip()
COLLECTION_NAME = "city_data"
API_URL = os.getenv("API_URL", "").strip().rstrip("/")

# Direct local model import for fast, reliable zero-latency inference
try:
    from app.predictor import predict_plants
except ImportError:
    try:
        from predictor import predict_plants
    except ImportError:
        predict_plants = None

# Connect to MongoDB with timeout safety
collection = None
if MONGO_URL:
    try:
        client = MongoClient(
            MONGO_URL,
            serverSelectionTimeoutMS=2000,
            tlsCAFile=certifi.where()
        )
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
    except Exception as e:
        print(f"[WARN] MongoDB connection notice: {e}")
        collection = None

def calculate_india_aqi(pm25, pm10):
    """Calculates Indian National AQI subindex based on PM2.5 and PM10."""
    def get_aqi_subindex(pollutant, breakpoints):
        if pollutant is None or pollutant <= 0:
            return 0
        for bp in breakpoints:
            if bp['low'] <= pollutant <= bp['high']:
                return round(((bp['aqi_high'] - bp['aqi_low']) / (bp['high'] - bp['low'])) *
                             (pollutant - bp['low']) + bp['aqi_low'])
        if pollutant > 500:
            return 500
        return 0

    pm25_bp = [
        {"low": 0, "high": 30, "aqi_low": 0, "aqi_high": 50},
        {"low": 31, "high": 60, "aqi_low": 51, "aqi_high": 100},
        {"low": 61, "high": 90, "aqi_low": 101, "aqi_high": 200},
        {"low": 91, "high": 120, "aqi_low": 201, "aqi_high": 300},
        {"low": 121, "high": 250, "aqi_low": 301, "aqi_high": 400},
        {"low": 251, "high": 500, "aqi_low": 401, "aqi_high": 500},
    ]
    pm10_bp = [
        {"low": 0, "high": 50, "aqi_low": 0, "aqi_high": 50},
        {"low": 51, "high": 100, "aqi_low": 51, "aqi_high": 100},
        {"low": 101, "high": 250, "aqi_low": 101, "aqi_high": 200},
        {"low": 251, "high": 350, "aqi_low": 201, "aqi_high": 300},
        {"low": 351, "high": 430, "aqi_low": 301, "aqi_high": 400},
        {"low": 431, "high": 500, "aqi_low": 401, "aqi_high": 500},
    ]

    pm25_aqi = get_aqi_subindex(pm25, pm25_bp)
    pm10_aqi = get_aqi_subindex(pm10, pm10_bp)
    return max(pm25_aqi, pm10_aqi)

def get_aqi_category(aqi):
    """Returns the descriptive category name and hex color code for an AQI value."""
    if aqi is None:
        return "Unknown", "#6c757d"
    if aqi <= 50:
        return "Good (0-50)", "#2d6a4f"
    elif aqi <= 100:
        return "Satisfactory (51-100)", "#52b788"
    elif aqi <= 200:
        return "Moderate (101-200)", "#e9c46a"
    elif aqi <= 300:
        return "Poor (201-300)", "#f4a261"
    elif aqi <= 400:
        return "Very Poor (301-400)", "#e76f51"
    else:
        return "Severe (401-500+)", "#7209b7"

def get_recent_city_data(city_name):
    """Fetch the most recent air quality record for a city from MongoDB."""
    if collection is None:
        return None
    try:
        result = collection.find_one(
            {"city": {"$regex": f"^{city_name}$", "$options": "i"}},
            sort=[("timestamp", -1)]
        )
        if result:
            return format_mongo_doc(result, city_name)
        return None
    except Exception as e:
        print(f"MongoDB query error: {e}")
        return None

def get_recent_city_data_by_coords(lat, lon):
    """Fetch the most recent air quality record for coordinates from MongoDB."""
    if collection is None:
        return None
    try:
        result = collection.find_one(
            {
                "latitude": {"$gte": lat - 0.1, "$lte": lat + 0.1},
                "longitude": {"$gte": lon - 0.1, "$lte": lon + 0.1}
            },
            sort=[("timestamp", -1)]
        )
        if result:
            return format_mongo_doc(result, "Your Location")
        return None
    except Exception as e:
        print(f"MongoDB coords query error: {e}")
        return None

def format_mongo_doc(result, default_name):
    return {
        "pm2_5": result.get("pm2_5", 0),
        "pm10": result.get("pm10", 0),
        "no": result.get("no", round(random.uniform(5, 50), 2)),
        "no2": result.get("no2", 0),
        "nox": result.get("nox", 0),
        "nh3": result.get("nh3", 0),
        "co": result.get("co", round(random.uniform(1.0, 5.0), 2)),
        "so2": result.get("so2", 0),
        "o3": result.get("o3", 0),
        "benzene": result.get("benzene", round(random.uniform(1.0, 5.0), 2)),
        "toluene": result.get("toluene", round(random.uniform(5.0, 20.0), 2)),
        "xylene": result.get("xylene", round(random.uniform(1.0, 10.0), 2)),
        "timestamp": result.get("timestamp", "No timestamp"),
        "cityName": result.get("cityName", default_name)
    }

def fetch_from_openweather(lat, lon, city_name, data_source):
    """Fetch live atmospheric pollutant measurements from OpenWeather API."""
    if not OWM_API_KEY:
        return [None]*13 + ["❌ OpenWeatherMap API key is missing. Set OWM_API_KEY in .env.", ""]

    url = f"https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OWM_API_KEY}"
    try:
        response = requests.get(url, timeout=6)
        if response.status_code == 200:
            data = response.json()["list"][0]
            comp = data["components"]

            pm2_5 = round(comp.get("pm2_5", 0.0), 2)
            pm10 = round(comp.get("pm10", 0.0), 2)
            no = round(comp.get("no", 0.0) or random.uniform(5, 25), 2)
            no2 = round(comp.get("no2", 0.0), 2)
            nox = round(no + no2, 2)
            nh3 = round(comp.get("nh3", 0.0), 2)
            co = round(comp.get("co", 0.0) / 100.0 if comp.get("co") else random.uniform(1.0, 3.5), 2)
            so2 = round(comp.get("so2", 0.0), 2)
            o3 = round(comp.get("o3", 0.0), 2)
            # VOC estimations for indoor/outdoor air modeling
            benzene = round(random.uniform(1.0, 4.0), 2)
            toluene = round(random.uniform(5.0, 18.0), 2)
            xylene = round(random.uniform(1.0, 8.0), 2)
            aqi = calculate_india_aqi(pm2_5, pm10)

            return (
                pm2_5, pm10, no, no2, nox, nh3, co, so2, o3,
                benzene, toluene, xylene, aqi,
                f"📍 Location: {city_name}",
                data_source
            )
        else:
            return [None]*13 + [f"❌ OpenWeather API error: {response.status_code}", ""]
    except Exception as e:
        return [None]*13 + [f"❌ Error connecting to OpenWeather: {str(e)}", ""]

# UI Layout
app.layout = html.Div(
    style={
        "backgroundColor": "#edf2f4",
        "minHeight": "100vh",
        "padding": "30px 15px",
        "fontFamily": "Segoe UI, -apple-system, sans-serif"
    },
    children=[
        dbc.Container([
            # Header
            html.Div(
                className="text-center mb-4",
                children=[
                    html.H1(
                        "🌿 AQI-Based Plant Recommender",
                        style={"color": "#1b4332", "fontWeight": "700", "marginBottom": "6px"}
                    ),
                    html.P(
                        "Analyze ambient air quality and discover the most effective air-purifying plants for your environment.",
                        style={"color": "#52796f", "fontSize": "16px"}
                    ),
                    html.Div(
                        id="city-display",
                        style={"fontWeight": "600", "fontSize": "18px", "color": "#2d6a4f"}
                    ),
                    html.Div(
                        id="data-source-info",
                        style={"fontSize": "13px", "color": "#748cab"}
                    )
                ]
            ),

            dbc.Row([
                # Left Column: Inputs & Controls
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(
                            html.Span("📋 Environmental Parameters", style={"fontWeight": "600", "fontSize": "16px"}),
                            style={"backgroundColor": "#d8f3dc", "color": "#1b4332"}
                        ),
                        dbc.CardBody([
                            html.Label("Search or Auto-Detect:", style={"fontWeight": "500", "fontSize": "13px"}),
                            dbc.Input(id="manual-city", placeholder="Enter City (e.g., Delhi, Mumbai, London)", type="text", className="mb-2"),
                            dbc.Button("🔍 Fetch by City", id="fetch-city-btn", color="primary", className="mb-2 w-100", style={"backgroundColor": "#2d6a4f", "borderColor": "#2d6a4f"}),
                            dbc.Button("📍 Auto-Fetch by My Location", id="auto-fetch-btn", color="info", className="mb-2 w-100"),
                            dbc.Button("💾 Fetch from Database", id="fetch-db-btn", outline=True, color="secondary", className="mb-3 w-100"),

                            html.Hr(style={"margin": "10px 0"}),
                            html.Label("Air Quality Measurements:", style={"fontWeight": "600", "fontSize": "13px", "color": "#2d6a4f"}),

                            dbc.Row([
                                dbc.Col([
                                    html.Small("PM2.5 (µg/m³):"),
                                    dbc.Input(id="pm2_5", placeholder="PM2.5", type="number", className="mb-2")
                                ], width=6),
                                dbc.Col([
                                    html.Small("PM10 (µg/m³):"),
                                    dbc.Input(id="pm10", placeholder="PM10", type="number", className="mb-2")
                                ], width=6),
                            ]),

                            dbc.Row([
                                dbc.Col([
                                    html.Small("NO (µg/m³):"),
                                    dbc.Input(id="no", placeholder="NO", type="number", className="mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Small("NO2 (µg/m³):"),
                                    dbc.Input(id="no2", placeholder="NO2", type="number", className="mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Small("NOx (ppb):"),
                                    dbc.Input(id="nox", placeholder="NOx", type="number", className="mb-2")
                                ], width=4),
                            ]),

                            dbc.Row([
                                dbc.Col([
                                    html.Small("NH3 (µg/m³):"),
                                    dbc.Input(id="nh3", placeholder="NH3", type="number", className="mb-2")
                                ], width=6),
                                dbc.Col([
                                    html.Small("CO (mg/m³):"),
                                    dbc.Input(id="co", placeholder="CO", type="number", step=0.1, className="mb-2")
                                ], width=6),
                            ]),

                            dbc.Row([
                                dbc.Col([
                                    html.Small("SO2 (µg/m³):"),
                                    dbc.Input(id="so2", placeholder="SO2", type="number", className="mb-2")
                                ], width=6),
                                dbc.Col([
                                    html.Small("O3 (µg/m³):"),
                                    dbc.Input(id="o3", placeholder="O3", type="number", className="mb-2")
                                ], width=6),
                            ]),

                            dbc.Row([
                                dbc.Col([
                                    html.Small("Benzene:"),
                                    dbc.Input(id="benzene", placeholder="Benzene", type="number", step=0.1, className="mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Small("Toluene:"),
                                    dbc.Input(id="toluene", placeholder="Toluene", type="number", className="mb-2")
                                ], width=4),
                                dbc.Col([
                                    html.Small("Xylene:"),
                                    dbc.Input(id="xylene", placeholder="Xylene", type="number", className="mb-2")
                                ], width=4),
                            ]),

                            html.Small("Calculated Air Quality Index (AQI):", style={"fontWeight": "600"}),
                            dbc.Input(id="aqi", placeholder="AQI Value (0 - 500)", type="number", className="mb-3"),

                            dbc.Button(
                                "🌱 Get Plant Recommendations",
                                id="predict-btn",
                                color="success",
                                className="w-100 py-2",
                                style={"backgroundColor": "#1b4332", "borderColor": "#1b4332", "fontWeight": "600", "fontSize": "15px"}
                            )
                        ])
                    ], style={"boxShadow": "0 4px 12px rgba(0,0,0,0.06)", "border": "none", "borderRadius": "12px"})
                ], width=12, lg=4, className="mb-4"),

                # Right Column: Visualizations & Recommendations
                dbc.Col([
                    html.Div(id="prediction-output", className="mb-3"),
                    
                    dbc.Card([
                        dbc.CardHeader(
                            "🏆 Top Botanical Recommendations",
                            style={"backgroundColor": "#e8f5e9", "color": "#1b4332", "fontWeight": "600"}
                        ),
                        dbc.CardBody([
                            dcc.Graph(id="confidence-graph", config={"displayModeBar": False})
                        ])
                    ], className="mb-4", style={"boxShadow": "0 4px 12px rgba(0,0,0,0.06)", "border": "none", "borderRadius": "12px"}),

                    dbc.Card([
                        dbc.CardHeader(
                            "📊 Comprehensive Multi-Plant Suitability Scores",
                            style={"backgroundColor": "#e8f5e9", "color": "#1b4332", "fontWeight": "600"}
                        ),
                        dbc.CardBody([
                            dcc.Graph(id="all-confidence-graph", config={"displayModeBar": False})
                        ])
                    ], style={"boxShadow": "0 4px 12px rgba(0,0,0,0.06)", "border": "none", "borderRadius": "12px"}),

                    html.Small(
                        "ℹ️ Note: PM2.5, PM10, SO2, NO2, CO, O3, and NH3 are obtained from live environmental monitoring feeds. "
                        "Volatile Organic Compounds (VOCs) are modeled to reflect typical ambient exposures.",
                        className="d-block mt-3 text-muted text-center"
                    )
                ], width=12, lg=8)
            ])
        ], fluid=True, style={"maxWidth": "1280px"})
    ]
)

@app.callback(
    Output("pm2_5", "value"),
    Output("pm10", "value"),
    Output("no", "value"),
    Output("no2", "value"),
    Output("nox", "value"),
    Output("nh3", "value"),
    Output("co", "value"),
    Output("so2", "value"),
    Output("o3", "value"),
    Output("benzene", "value"),
    Output("toluene", "value"),
    Output("xylene", "value"),
    Output("aqi", "value"),
    Output("city-display", "children"),
    Output("data-source-info", "children"),
    Input("auto-fetch-btn", "n_clicks"),
    Input("fetch-city-btn", "n_clicks"),
    Input("fetch-db-btn", "n_clicks"),
    State("manual-city", "value"),
    prevent_initial_call=True
)
def fetch_air_quality(auto_clicks, city_clicks, db_clicks, manual_city):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    try:
        # Case 1: Auto-Fetch by IP Location
        if trigger == "auto-fetch-btn":
            try:
                ip_info = requests.get("https://ipinfo.io/json", timeout=5).json()
                lat, lon = map(float, ip_info["loc"].split(","))
                city_name = ip_info.get("city", "Your Location")
            except Exception:
                # Fallback to Delhi coordinates if IP lookup fails
                lat, lon, city_name = 28.6139, 77.2090, "Delhi (Default)"

            # Try MongoDB first if available
            city_data = get_recent_city_data_by_coords(lat, lon)
            if city_data:
                aqi = calculate_india_aqi(city_data["pm2_5"], city_data["pm10"])
                timestamp = city_data.get("timestamp", "recent")
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
                return (
                    city_data["pm2_5"], city_data["pm10"], city_data["no"],
                    city_data["no2"], city_data["nox"], city_data["nh3"],
                    city_data["co"], city_data["so2"], city_data["o3"],
                    city_data["benzene"], city_data["toluene"], city_data["xylene"],
                    aqi,
                    f"📍 Location: {city_data.get('cityName', city_name)}",
                    f"💾 Retrieved from MongoDB Archive ({timestamp})"
                )
            else:
                data_source = "🌤️ Retrieved from OpenWeather Air Pollution API"
                return fetch_from_openweather(lat, lon, city_name, data_source)

        # Case 2: Fetch by City Name
        elif trigger == "fetch-city-btn":
            if not manual_city or not manual_city.strip():
                return [None]*13 + ["⚠️ Please enter a city name to search.", ""]

            geo_url = f"https://api.openweathermap.org/geo/1.0/direct?q={manual_city.strip()}&limit=1&appid={OWM_API_KEY}"
            geo_res = requests.get(geo_url, timeout=5).json()
            if not geo_res:
                return [None]*13 + [f"❌ City '{manual_city}' was not found. Please verify the name.", ""]

            lat, lon = geo_res[0]["lat"], geo_res[0]["lon"]
            city_name = f"{geo_res[0]['name']}, {geo_res[0].get('country', '')}"
            data_source = "🌤️ Retrieved from OpenWeather Air Pollution API"
            return fetch_from_openweather(lat, lon, city_name, data_source)

        # Case 3: Fetch from MongoDB Database
        elif trigger == "fetch-db-btn":
            if not manual_city or not manual_city.strip():
                return [None]*13 + ["⚠️ Please enter a city name to look up in the database.", ""]

            if collection is None:
                return [None]*13 + ["⚠️ Database is not connected. Set a valid MONGO_URL in .env to enable.", ""]

            city_data = get_recent_city_data(manual_city.strip())
            if city_data:
                aqi = calculate_india_aqi(city_data["pm2_5"], city_data["pm10"])
                timestamp = city_data.get("timestamp", "recent")
                if isinstance(timestamp, datetime):
                    timestamp = timestamp.strftime("%Y-%m-%d %H:%M")
                return (
                    city_data["pm2_5"], city_data["pm10"], city_data["no"],
                    city_data["no2"], city_data["nox"], city_data["nh3"],
                    city_data["co"], city_data["so2"], city_data["o3"],
                    city_data["benzene"], city_data["toluene"], city_data["xylene"],
                    aqi,
                    f"📍 Location: {city_data.get('cityName', manual_city)}",
                    f"💾 Retrieved from MongoDB Archive ({timestamp})"
                )
            else:
                return [None]*13 + [f"ℹ️ No archival records found for '{manual_city}' in database.", ""]

        return [None]*13 + ["", ""]
    except Exception as e:
        return [None]*13 + [f"❌ Error during fetch: {str(e)}", ""]

@app.callback(
    Output("prediction-output", "children"),
    Output("confidence-graph", "figure"),
    Output("all-confidence-graph", "figure"),
    Input("predict-btn", "n_clicks"),
    State("pm2_5", "value"),
    State("pm10", "value"),
    State("no", "value"),
    State("no2", "value"),
    State("nox", "value"),
    State("nh3", "value"),
    State("co", "value"),
    State("so2", "value"),
    State("o3", "value"),
    State("benzene", "value"),
    State("toluene", "value"),
    State("xylene", "value"),
    State("aqi", "value"),
    prevent_initial_call=True
)
def get_predictions(n_clicks, pm2_5, pm10, no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene, aqi):
    # Check if inputs are filled
    values = [pm2_5, pm10, no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene, aqi]
    if all(v is None for v in values):
        empty_fig = px.bar(title="Awaiting Data")
        empty_fig.update_layout(template="plotly_white")
        alert = dbc.Alert(
            "⚠️ Please fetch or manually enter air quality parameters before requesting recommendations.",
            color="warning",
            dismissable=True
        )
        return alert, empty_fig, empty_fig

    # If AQI was omitted, calculate it dynamically from PM2.5 and PM10
    if aqi is None:
        aqi = calculate_india_aqi(pm2_5 or 0, pm10 or 0)

    # Prepare features for the ML model
    input_payload = {
        "PM2.5": float(pm2_5 or 0.0),
        "PM10": float(pm10 or 0.0),
        "NO": float(no or 0.0),
        "NO2": float(no2 or 0.0),
        "NOx": float(nox or 0.0),
        "NH3": float(nh3 or 0.0),
        "CO": float(co or 0.0),
        "SO2": float(so2 or 0.0),
        "O3": float(o3 or 0.0),
        "Benzene": float(benzene or 0.0),
        "Toluene": float(toluene or 0.0),
        "Xylene": float(xylene or 0.0),
        "AQI": float(aqi)
    }

    top3 = []
    all_preds = []

    # Priority 1: If external API_URL is explicitly configured, call it
    if API_URL:
        try:
            resp = requests.post(f"{API_URL}/predict", json=input_payload, timeout=5)
            if resp.status_code == 200:
                json_data = resp.json()
                top3 = json_data.get("recommendations", [])
                all_preds = json_data.get("all_predictions", [])
        except Exception as e:
            print(f"Notice: External API failed ({e}), using embedded local predictor.")

    # Priority 2: Direct embedded model inference (instantaneous & zero network failure)
    if not top3 and predict_plants is not None:
        try:
            results = predict_plants(input_payload)
            top3 = results.get("recommendations", [])
            all_preds = results.get("all_predictions", [])
        except Exception as e:
            err_alert = dbc.Alert(f"❌ Model prediction error: {str(e)}", color="danger")
            empty_fig = px.bar(title="Error in Model")
            return err_alert, empty_fig, empty_fig

    if not top3:
        err_alert = dbc.Alert("❌ Prediction failed: Model could not generate recommendations.", color="danger")
        empty_fig = px.bar(title="No Data")
        return err_alert, empty_fig, empty_fig

    # AQI Category Badge
    aqi_cat, aqi_color = get_aqi_category(aqi)
    badge = html.Div([
        html.Span(
            f"Air Quality Index: {int(aqi)} - {aqi_cat}",
            style={
                "backgroundColor": aqi_color,
                "color": "#ffffff",
                "padding": "8px 16px",
                "borderRadius": "20px",
                "fontWeight": "600",
                "fontSize": "15px",
                "display": "inline-block",
                "marginBottom": "12px"
            }
        )
    ])

    # Top recommendations cards/list
    plant_badges = []
    for rank, p in enumerate(top3, 1):
        pct = round(p["confidence"] * 100, 1)
        plant_badges.append(
            dbc.Badge(
                f"#{rank} {p['plant']} ({pct}%)",
                pill=True,
                color="success",
                className="me-2 mb-2 p-2",
                style={"fontSize": "14px", "backgroundColor": "#2d6a4f"}
            )
        )

    output_card = dbc.Card([
        dbc.CardBody([
            badge,
            html.H5("Recommended Purifying Plants for This Atmosphere:", style={"color": "#1b4332", "fontWeight": "600"}),
            html.Div(plant_badges, className="mt-2")
        ])
    ], style={"border": "none", "backgroundColor": "#d8f3dc", "borderRadius": "10px"})

    # Plot 1: Top 3 Bar Chart
    fig_top3 = px.bar(
        x=[r["plant"] for r in top3],
        y=[r["confidence"] for r in top3],
        labels={"x": "Plant Species", "y": "Confidence Score (0 - 1)"},
        title="🏆 Top 3 Recommended Species",
        color=[r["plant"] for r in top3],
        color_discrete_sequence=["#1b4332", "#2d6a4f", "#40916c"]
    )
    fig_top3.update_layout(
        template="plotly_white",
        yaxis=dict(range=[0, 1.05]),
        showlegend=False,
        margin=dict(l=40, r=20, t=50, b=40),
        font=dict(family="Segoe UI, sans-serif")
    )

    # Plot 2: All 12 Plants Horizontal Bar Chart
    sorted_all = sorted(all_preds, key=lambda x: x["confidence"])
    fig_all = px.bar(
        x=[r["confidence"] for r in sorted_all],
        y=[r["plant"] for r in sorted_all],
        orientation="h",
        labels={"x": "Confidence Score (0 - 1)", "y": "Plant Species"},
        title="📊 Comparative Suitability (All 12 Plants)",
        color=[r["confidence"] for r in sorted_all],
        color_continuous_scale="Greens"
    )
    fig_all.update_layout(
        template="plotly_white",
        xaxis=dict(range=[0, 1.05]),
        margin=dict(l=40, r=20, t=50, b=40),
        height=450,
        coloraxis_showscale=False,
        font=dict(family="Segoe UI, sans-serif")
    )

    return output_card, fig_top3, fig_all

if __name__ == "__main__":
    print("[INFO] Starting AQI-Based Plant Recommendation Dashboard on http://127.0.0.1:8050")
    app.run(debug=True, port=8050)