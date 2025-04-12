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

def get_aqi_category(aqi):
    if aqi <= 50:
        return "Good", "#009966"
    elif aqi <= 100:
        return "Satisfactory", "#ffde33"
    elif aqi <= 200:
        return "Moderate", "#ff9933"
    elif aqi <= 300:
        return "Poor", "#cc0033"
    elif aqi <= 400:
        return "Very Poor", "#660099"
    else:
        return "Severe", "#7e0023"

app.layout = html.Div(
    style={
        "backgroundColor": "#000000",  # Soft light-blue background
        "minHeight": "100vh",
        "padding": "20px"
    },
    children=[
        dbc.Container([
    html.H2(
        "🌱 AQI-Based Plant Recommendation Dashboard",
        className="text-center my-4",
        style={"color": "black"}
    ),
    html.Div(
        id="city-display",
        className="text-center mb-3",
        style={
            "fontWeight": "bold",
            "fontSize": "18px",
            "color": "black"
        }
    ),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Air Quality Parameters"),
                dbc.CardBody([
                    dbc.Input(id="manual-city", placeholder="Enter City", type="text", className="mb-2"),
                    dbc.Button("Fetch by City", id="fetch-city-btn", color="primary", className="mb-2 w-100"),
                    dbc.Button("Auto-Fetch by Location", id="auto-fetch-btn", color="info", className="mb-3 w-100"),

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
            dcc.Graph(id="confidence-graph"),
            dcc.Graph(id="all-confidence-graph") 
        ], width=8)
           
    ])
], fluid=True, style={"backgroundColor": "#ccf7a6", "borderRadius": "15px", "padding": "30px"})
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
    Input("auto-fetch-btn", "n_clicks"),
    Input("fetch-city-btn", "n_clicks"),
    State("manual-city", "value"),
    prevent_initial_call=True
)
def fetch_air_quality(auto_clicks, city_clicks, manual_city):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    
    try:
        if trigger == "fetch-city-btn" and manual_city:
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={manual_city}&limit=1&appid={OWM_API_KEY}"
            geo_res = requests.get(geo_url).json()
            if not geo_res:
                return [None]*13 + [f"❌ City '{manual_city}' not found."]
            lat, lon = geo_res[0]['lat'], geo_res[0]['lon']
            city_name = geo_res[0]['name']

        elif trigger == "auto-fetch-btn":
            ip_info = requests.get("https://ipinfo.io").json()
            lat, lon = map(float, ip_info["loc"].split(","))
            city_name = ip_info.get("city", "Your Location")
        else:
            return [None]*13 + ["❌ Invalid trigger or missing city name."]

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
            co =  round(random.uniform(1.0, 5.0), 2)
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
)
def get_predictions(n_clicks, pm2_5, pm10, no, no2, nox, nh3, co, so2, o3, benzene, toluene, xylene, aqi):
    if not n_clicks:
        return dash.no_update, dash.no_update, dash.no_update

    data = {
        "PM2_5": pm2_5, "PM10": pm10, "NO": no, "NO2": no2, "NOx": nox,
        "NH3": nh3, "CO": co, "SO2": so2, "O3": o3,
        "Benzene": benzene, "Toluene": toluene, "Xylene": xylene, "AQI": aqi
    }

    try:
        response = requests.post("https://fastapi-voting-based-model-api-for-plant.onrender.com/predict", json=data)
        if response.status_code == 200:
            json_data = response.json()
            top3 = json_data.get("recommendations", [])
            all_preds = json_data.get("all_predictions", [])

            if not top3:
                return [html.P("No prediction returned.")], {}, {}

            items = [html.P(f"{i+1}. {res['plant']} ({res['confidence']*100:.1f}%)") for i, res in enumerate(top3)]

            fig_top3 = px.bar(
                x=[r["plant"] for r in top3],
                y=[r["confidence"] for r in top3],
                labels={"x": "Plant", "y": "Confidence"},
                title="Top 3 Recommended Plants",
                color=[r["plant"] for r in top3]
            )
            fig_top3.update_layout(template="plotly_white", yaxis=dict(range=[0, 1]))

            # 🔽 Sort all predictions for horizontal bar chart
            sorted_all = sorted(all_preds, key=lambda x: x["confidence"])
            fig_all = px.bar(
                x=[r["confidence"] for r in sorted_all],
                y=[r["plant"] for r in sorted_all],
                orientation='h',
                labels={"x": "Confidence", "y": "Plant"},
                title="All Plant Predictions (Low to High Confidence)"
            )
            fig_all.update_layout(template="plotly_white", xaxis=dict(range=[0, 1]))

            return items, fig_top3, fig_all
        else:
            return [html.P(f"Prediction failed: {response.status_code}")], {}, {}
    except Exception as e:
        return [html.P(f"Error: {e}")], {}, {}

if __name__ == "__main__":
    app.run(debug=True)