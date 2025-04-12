import uvicorn
from fastapi import FastAPI, HTTPException
from data import Data
import joblib
import pandas as pd
import numpy as np

app = FastAPI()

# Load the model and multi-label binarizer
try:
    pipe_voting = joblib.load("Voting_model.pkl")
    mlb = joblib.load("mlb.pkl")  # Ensure you have saved this object too
except Exception as e:
    print(f"❌ Error loading model or mlb: {str(e)}")
    pipe_voting = None
    mlb = None

def predict_top_plants(input_data):
    try:
        input_df = pd.DataFrame([input_data])
        print(f"✅ Input DataFrame:\n{input_df}")

        if pipe_voting is None or mlb is None:
            raise ValueError("Model or label binarizer not loaded")

        probs = pipe_voting.predict_proba(input_df)
        avg_probs = np.array([p[0] if isinstance(p, list) else p for p in probs]).flatten()
        top3_indices = avg_probs.argsort()[::-1][:3]

        top_plants = [
            {"plant": mlb.classes_[i], "confidence": round(avg_probs[i], 2)}
            for i in top3_indices
        ]

        return top_plants
    except Exception as e:
        print(f"❌ Prediction error: {str(e)}")
        return []

@app.post("/predict")
async def predict(data: Data):
    try:
        input_data = data.dict(by_alias=True)
        print(f"📩 Received input: {input_data}")

        top_plants = predict_top_plants(input_data)

        if not top_plants:
            raise HTTPException(status_code=500, detail="Prediction failed.")

        return {"top_3_plants": top_plants}
    except Exception as e:
        print(f"❌ Exception in /predict: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

# To run the app
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
