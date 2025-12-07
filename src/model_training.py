# model_training.py
import os
import pandas as pd
import joblib
from sklearn.model_selection import RandomizedSearchCV
import lightgbm as lgb
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from src.logger import get_logger
from src.custom_exception import CustomException
from config.paths_config import *
from config.model_params import *
from utils.common_functions import read_yaml, load_data
from scipy.stats import randint
from google.cloud import storage

import mlflow
import mlflow.sklearn

logger = get_logger(__name__)

class ModelTraining:
    def __init__(self, train_path, test_path, model_output_path):
        self.train_path = train_path
        self.test_path = test_path
        self.model_output_path = model_output_path

        self.params_dist = LIGHTGBM_PARAMS
        self.random_search_params = RANDOM_SEARCH_PARAMS
        
        self.config = read_yaml(CONFIG_PATH)
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", self.config['data_ingestion']['bucket_name'])

    def load_and_split_data(self):
        try:
            logger.info(f"Loading data from {self.train_path}")
            train_df = load_data(self.train_path)

            logger.info(f"Loading data from {self.test_path}")
            test_df = load_data(self.test_path)

            X_train = train_df.drop(columns=["booking_status"])
            y_train = train_df["booking_status"]

            X_test = test_df.drop(columns=["booking_status"])
            y_test = test_df["booking_status"]

            logger.info("Data splitted successfuly for Model Training")

            return X_train, y_train, X_test, y_test
        
        except Exception as e:
            logger.error(f"Error while loading data {e}")
            raise CustomException("Failed to load data", e)
        
    def train_lgbm(self, X_train, y_train):
        try:
            logger.info("Initializing our model!")

            lgbm_model = lgb.LGBMClassifier(random_state=self.random_search_params["random_state"])

            logger.info("Starting our Hyperparameter tuning")

            random_search = RandomizedSearchCV(
                estimator = lgbm_model,
                param_distributions = self.params_dist,
                n_iter = self.random_search_params["n_iter"],
                cv = self.random_search_params["cv"],
                n_jobs = self.random_search_params["n_jobs"],
                verbose = self.random_search_params["verbose"],
                random_state = self.random_search_params["random_state"],
                scoring = self.random_search_params["scoring"]
            )

            logger.info("Starting our Model training")

            random_search.fit(X_train, y_train)

            logger.info("Hyperparameter tuning completed")

            best_params = random_search.best_params_
            best_lgbm_model = random_search.best_estimator_

            logger.info(f"Best parameters are: {best_params}")
            return best_lgbm_model
        
        except Exception as e:
            logger.error(f"Error while training the model {e}")
            raise CustomException("Failed to train the model", e)
        
    def evaluate_model(self, model, X_test, y_test):
        try:
            logger.info("Evaluating model")

            y_pred = model.predict(X_test)

            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)

            logger.info(f"Accuracy Score: {accuracy}")
            logger.info(f"precision Score: {precision}")
            logger.info(f"recall Score: {recall}")
            logger.info(f"f1 Score: {f1}")

            return {
                "accuracy": accuracy,
                "precision": precision,
                "recall": recall,
                "f1": f1
            }
        
        except Exception as e:
            logger.error(f"Error while evaluating the model {e}")
            raise CustomException("Failed to evaluate the model", e)

    # --- KRITIK DEGISIKLIK BURADA ---
    def save_model(self, model):
        try:
            # 1. Local Kayıt
            os.makedirs(os.path.dirname(self.model_output_path), exist_ok=True)
            logger.info("Saving the model locally")
            joblib.dump(model, self.model_output_path)
            logger.info(f"Model saved locally to {self.model_output_path}")

            # 2. Google Cloud Storage Upload
            logger.info(f"Uploading model to GCS Bucket: {self.bucket_name}")
            
            storage_client = storage.Client()
            bucket = storage_client.bucket(self.bucket_name)
            
            # GCS'de kaydedilecek yol (artifacts/models/lgbm_model.pkl -> models/lgbm_model.pkl olarak kısaltabiliriz)
            destination_blob_name = "models/lgbm_model.pkl"
            blob = bucket.blob(destination_blob_name)
            
            blob.upload_from_filename(self.model_output_path)
            
            logger.info(f"Model successfully uploaded to gs://{self.bucket_name}/{destination_blob_name}")
        
        except Exception as e:
            logger.error(f"Error while saving/uploading the model {e}")
            raise CustomException("Failed to save the model", e)
        
    def run(self):
        try:
            # MLflow ayarlarını environment variable veya hardcoded olarak ayarlamayı unutma
            # MLFLOW_TRACKING_URI Jenkinsfile'dan geliyor olmalı
            
            with mlflow.start_run():
                logger.info("Starting our model training pipeline")

                logger.info("Starting our MLFlow experimentation")

                # Artifact loglama işlemleri opsiyoneldir, dosya boyutuna göre yavaşlatabilir
                # mlflow.log_artifact(self.train_path, artifact_path="datasets")
                # mlflow.log_artifact(self.test_path, artifact_path="datasets")

                X_train, y_train, X_test, y_test = self.load_and_split_data()

                best_lgbm_model = self.train_lgbm(X_train, y_train)
                metrics = self.evaluate_model(best_lgbm_model, X_test, y_test)
                
                # Hem locale kaydet hem de GCS'ye yükle
                self.save_model(best_lgbm_model)

                logger.info("Logging Params and metrics to MLFlow")
                mlflow.log_params(best_lgbm_model.get_params())
                mlflow.log_metrics(metrics)
                
                # MLflow'a da modeli artifact olarak kaydedebilirsin (Alternatif backup)
                mlflow.sklearn.log_model(best_lgbm_model, "model")

                logger.info("Model training completed successfully")
        
        except Exception as e:
            logger.error(f"Error while running the model pipeline {e}")
            raise CustomException("Failed to run the model pipeline", e)
        
if __name__ == "__main__":
    trainer = ModelTraining(PROCESSED_TRAIN_DATA_PATH, PROCESSED_TEST_DATA_PATH, MODEL_OUTPUT_PATH)
    trainer.run()