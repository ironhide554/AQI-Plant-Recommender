import os
import sys
import uvicorn
from fastapi import FastAPI, HTTPException

# Support execution both as 'python app/main.py' and 'uvicorn app.main:app'
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

try:
    from predictor import predict_plants
    from data import Data
except ImportError:
    from app.predictor import predict_plants
    from app.data import Data

app = FastAPI(
    title="AQI-Based Plant Recommendation API",
    description="Predicts suitable air-purifying plants based on 13 environmental AQI parameters using Scikit-Learn VotingClassifier.",
    version="1.0.0"
)

@app.get("/")
def root():
    return {
        "service": "AQI-Based Plant Recommendation API",
        "status": "online",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "docs": "/docs"
        }
    }

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "aqi-plant-recommender"}

@app.post("/predict")
async def predict(data: Data):
    try:
        # Extract dictionary with 'PM2.5' as the key
        input_data = data.model_dump(by_alias=True)
        results = predict_plants(input_data)
        
        # Include top_3_plants for backwards compatibility alongside standard schema
        return {
            "recommendations": results["recommendations"],
            "all_predictions": results["all_predictions"],
            "top_3_plants": results["recommendations"]
        }
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
