# application.py
import joblib
import numpy as np
import os
from google.cloud import storage # <--- EKLENDI
from config.paths_config import MODEL_OUTPUT_PATH
from flask import Flask, render_template, request

app = Flask(__name__)

def download_model_from_gcs():
    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
    
    GCS_SOURCE_BLOB_NAME = "models/lgbm_model.pkl"
    
    LOCAL_DESTINATION_PATH = MODEL_OUTPUT_PATH

    print(f"Checking for model at {LOCAL_DESTINATION_PATH}...")

    os.makedirs(os.path.dirname(LOCAL_DESTINATION_PATH), exist_ok=True)

    try:
        print(f"Downloading model from google storage...")
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(GCS_SOURCE_BLOB_NAME)
        blob.download_to_filename(LOCAL_DESTINATION_PATH)
        print("Model downloaded successfully!")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not download model from GCS. Error: {e}")

if not os.path.exists(MODEL_OUTPUT_PATH):
    download_model_from_gcs()
else:
    print("Model file found locally, skipping download (or forcing download if explicitly requested).")

try:
    loaded_model = joblib.load(MODEL_OUTPUT_PATH)
    print("Model loaded into memory.")
except Exception as e:
    print(f"Error loading model file: {e}")
    loaded_model = None

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if loaded_model is None:
            return render_template("index.html", prediction="Error: Model not loaded")

        try:
            lead_time = int(request.form["lead_time"])
            no_of_special_request = int(request.form["no_of_special_request"])
            avg_price_per_room = float(request.form["avg_price_per_room"])
            arrival_month = int(request.form["arrival_month"])
            arrival_date = int(request.form["arrival_date"])

            market_segment_type = int(request.form["market_segment_type"])
            no_of_week_nights = int(request.form["no_of_week_nights"])
            no_of_weekend_nights = int(request.form["no_of_weekend_nights"])

            type_of_meal_plan = int(request.form["type_of_meal_plan"])
            room_type_reserved = int(request.form["room_type_reserved"])

            features = np.array([[lead_time, no_of_special_request, avg_price_per_room, arrival_month, arrival_date, market_segment_type, no_of_week_nights, no_of_weekend_nights, type_of_meal_plan, room_type_reserved]])

            prediction = loaded_model.predict(features)

            return render_template("index.html", prediction=prediction[0])
        except Exception as e:
            return render_template("index.html", prediction=f"Error in prediction: {e}")
            
    return render_template("index.html" , prediction=None)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)