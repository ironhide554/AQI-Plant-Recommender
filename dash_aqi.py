import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
import requests
import plotly.express as px
import random

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
server = app.server

OWM_API_KEY = "a00174d020ab1cec2d561cbffadd4c96"

def calculate_india_aqi(pm25, pm10):
    def get_aqi_subindex(pollutant, breakpoints):
        for bp in breakpoints:
            if bp['low'] <= pollutant <= bp['high']:
                return round(((bp['aqi_high'] - bp['aqi_low']) / (bp['high'] - bp['low'])) *
                             (pollutant - bp['low']) + bp['aqi_low'])
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

app.layout = dbc.Container([
    html.H2("🌱 AQI-Based Plant Recommendation Dashboard", className="text-center my-4"),
    html.Div(id="city-display", className="text-center mb-3", style={"fontWeight": "bold", "fontSize": "18px"}),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Air Quality Parameters (Auto-Fetch or Manual)"),
                dbc.CardBody([
                    dbc.Input(id="manual-city", placeholder="Enter City (Optional)", type="text", className="mb-2"),
                    dbc.Button("Auto-Fetch Air Data", id="auto-fetch-btn", color="info", className="mb-3 w-100"),

                    dbc.Input(id="pm2_5", placeholder="PM2.5", type="number", className="mb-2"),
                    dbc.Input(id="pm10", placeholder="PM10", type="number", className="mb-2"),
                    dbc.Input(id="no", placeholder="NO", type="number", className="mb-2"),
                    dbc.Input(id="no2", placeholder="NO2", type="number", className="mb-2"),
                    dbc.Input(id="nox", placeholder="NOx", type="number", className="mb-2"),
                    dbc.Input(id="nh3", placeholder="NH3", type="number", className="mb-2"),
                    dbc.Input(id="co", placeholder="CO", type="number", className="mb-2", step=0.1),
                    dbc.Input(id="so2", placeholder="SO2", type="number", className="mb-2"),
                    dbc.Input(id="o3", placeholder="O3", type="number", className="mb-2"),
                    dbc.Input(id="benzene", placeholder="Benzene", type="number", className="mb-2", step=0.1),
                    dbc.Input(id="toluene", placeholder="Toluene", type="number", className="mb-2"),
                    dbc.Input(id="xylene", placeholder="Xylene", type="number", className="mb-2"),
                    dbc.Input(id="aqi", placeholder="AQI Value", type="number", className="mb-2"),

                    dbc.Button("Get Plant Suggestions", id="predict-btn", color="success", className="mt-2 w-100"),
                ])
            ])
        ], width=4),

        dbc.Col([
            html.Div(id="prediction-output", className="mb-4"),
            dcc.Graph(id="confidence-graph")
        ], width=8)
    ])
], fluid=True)

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
    Input("auto-fetch-btn", "n_clicks"),
    State("manual-city", "value"),
)
def autofill_air_data(n_clicks, manual_city):
    if not n_clicks:
        return [dash.no_update] * 14

    try:
        if manual_city:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={manual_city}&limit=1&appid={OWM_API_KEY}"
            geo_res = requests.get(geo_url).json()
            if not geo_res:
                return [None]*13 + [f"❌ City '{manual_city}' not found."]
            lat, lon = geo_res[0]['lat'], geo_res[0]['lon']
            city_name = geo_res[0]['name']
        else:
            ip_info = requests.get("https://ipinfo.io").json()
            lat, lon = map(float, ip_info["loc"].split(","))
            city_name = ip_info.get("city", "Your Location")

        url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={OWM_API_KEY}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()["list"][0]
            comp = data["components"]

            pm2_5 = round(comp.get("pm2_5", 0), 2)
            pm10 = round(comp.get("pm10", 0), 2)
            no = round(comp.get("no", random.uniform(5, 50)), 2) or round(random.uniform(5, 50), 2)
            no2 = round(comp.get("no2", 0), 2)
            nox = round(no + no2, 2)
            nh3 = round(comp.get("nh3", 0), 2)
            co = round(comp.get("co", 0), 2)
            so2 = round(comp.get("so2", 0), 2)
            o3 = round(comp.get("o3", 0), 2)
            benzene = round(random.uniform(1.0, 5.0), 2)
            toluene = round(random.uniform(5.0, 20.0), 2)
            xylene = round(random.uniform(1.0, 10.0), 2)
            aqi = calculate_india_aqi(pm2_5, pm10)

            return (
                pm2_5, pm10, no, no2, nox, nh3, co, so2, o3,
                benzene, toluene, xylene, aqi,
                f"🌍 Data from: {city_name}"
            )
        else:
            return [None]*13 + ["❌ Failed to fetch air quality data."]
    except Exception as e:
        return [None]*13 + [f"❌ Error: {e}"]

@app.callback(
    Output("prediction-output", "children"),
    Output("confidence-graph", "figure"),
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
)
def get_predictions(n_clicks, pm2_5, pm10, no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene, aqi):
    if not n_clicks:
        return dash.no_update, dash.no_update

    data = {
        "PM2_5": pm2_5, "PM10": pm10, "NO": no, "NO2": no2, "NOx": nox,
        "NH3": nh3, "CO": co, "SO2": so2, "O3": o3,
        "Benzene": benzene, "Toluene": toluene, "Xylene": xylene, "AQI": aqi
    }

    try:
        response = requests.post("https://fastapi-voting-based-model-api-for-plant.onrender.com/predict", json=data)
        if response.status_code == 200:
            results = response.json().get("recommendations", [])
            if not results:
                return [html.P("No prediction returned.")], {}

            items = [html.P(f"{i+1}. {res['plant']} ({res['confidence']*100:.1f}%)") for i, res in enumerate(results)]
            fig = px.bar(
                x=[r["plant"] for r in results],
                y=[r["confidence"] for r in results],
                labels={"x": "Plant", "y": "Confidence"},
                title="Prediction Confidence (%)",
                color=[r["plant"] for r in results]
            )
            fig.update_layout(template="plotly_white", yaxis=dict(range=[0, 1]))

            return items, fig
        else:
            return [html.P(f"Prediction failed: {response.status_code}")], {}
    except Exception as e:
        return [html.P(f"Error: {e}")], {}

if __name__ == "__main__":
    app.run(debug=True)
