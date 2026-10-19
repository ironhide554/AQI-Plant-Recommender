# 🌿 AQI-Based Plant Recommendation System

An intelligent environmental dashboard that analyzes air quality metrics and recommends the most effective air-purifying indoor and outdoor plants based on a pre-trained Machine Learning Voting Classifier.

---

## 🎯 What This Platform Does

1. **Environmental Data Acquisition**:
   - **City Search**: Enter any city name to retrieve live atmospheric pollutant measurements via the OpenWeatherMap Air Pollution API.
   - **Auto-Detection**: One-click geo-detection via IP location to fetch local air quality.
   - **Manual Input**: Fine-tune or manually input any of the 13 air quality parameters.
   - **Historical Database Lookup**: Optional integration with MongoDB to retrieve archived city measurements.

2. **Indian National AQI (NAQI) Computation**:
   - Calculates real-time AQI using Indian standard breakpoint sub-indices for PM2.5 and PM10.
   - Categorizes air quality into official color-coded bands (*Good, Satisfactory, Moderate, Poor, Very Poor, Severe*).

3. **Machine Learning Plant Recommendations**:
   - Evaluates a soft-voting ensemble (`LogisticRegression` + `DecisionTree` + `GaussianNB`) wrapped in an `sklearn` `OneVsRestClassifier`.
   - Recommends the top 3 optimal species and ranks all 12 candidate species with confidence scores.

### 🌱 Supported Plant Species
- **Aloe Vera**
- **Areca Palm**
- **Boston Fern**
- **Ficus**
- **Money Plant**
- **Neem**
- **Peace Lily**
- **Pothos**
- **Rubber Plant**
- **Snake Plant**
- **Spider Plant**
- **Tulsi**

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*Note: A working OpenWeatherMap key is pre-configured so you can run the system immediately.*

### 3. Launch the Dashboard
```bash
python dash_aqi.py
```
Open your browser at **`http://127.0.0.1:8050`**.

---

## 🔌 Optional Standalone FastAPI Service

If you wish to expose the model as a REST API microservice:

```bash
uvicorn app.main:app --reload --port 8000
```
- Interactive API documentation (Swagger UI): **`http://127.0.0.1:8000/docs`**
- Health Check: `GET http://127.0.0.1:8000/health`
- Predict Endpoint: `POST http://127.0.0.1:8000/predict`

---

## 🧪 Running Automated Tests

Run the built-in end-to-end verification suite:
```bash
python test_system.py
```
This tests model inference, schema validation, AQI formulas, live OpenWeatherMap connectivity, and Dash callback rendering.

---

## 📁 Project Structure

```
AQI-Plant-Recommender/
├── dash_aqi.py          # Interactive Plotly Dash frontend dashboard
├── requirements.txt     # Python dependencies
├── .env.example         # Environment template
├── .gitignore           # Git ignore file
├── test_system.py       # Automated test suite
├── README.md            # Documentation
└── app/
    ├── predictor.py     # Shared ML inference engine
    ├── main.py          # FastAPI REST microservice
    ├── data.py          # Pydantic input schema
    ├── Voting_model.pkl # Trained Scikit-Learn VotingClassifier pipeline
    └── mlb.pkl          # MultiLabelBinarizer with 12 plant species
```

---

## 📜 License
MIT License.
