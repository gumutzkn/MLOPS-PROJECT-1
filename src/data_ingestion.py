import os
import pandas as pd
from google.cloud import storage
from sklearn.model_selection import train_test_split
from src.logger import get_logger
from src.custom_exception import CustomException
from config.paths_config import *
from utils.common_functions import read_yaml

logger = get_logger(__name__)

class DataIngestion:
    def __init__(self, config):
        self.config = config["data_ingestion"]
        self.bucket_name = os.getenv("GCS_BUCKET_NAME", self.config["bucket_name"])
        
        if not self.bucket_name or "PLACEHOLDER" in self.bucket_name:
             raise ValueError("HATA: Bucket ismi bulunamadı! 'GCS_BUCKET_NAME' environment variable tanımlı değil.")
        self.file_name = self.config["bucket_file_name"]
        self.train_ratio = self.config["train_ratio"]

        os.makedirs(RAW_DIR, exist_ok=True)

        logger.info(f"Data ingestion started for bucket {self.bucket_name} and file is {self.file_name}")
    
    def download_csv_from_gcp(self):
        try:
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self.file_name)
            blob.download_to_filename(RAW_FILE_PATH)
            logger.info(f"CSV file downloaded successfully from bucket {self.bucket_name} to {RAW_FILE_PATH}")
        except Exception as e:
            logger.error(f"Error downloading CSV file from bucket {self.bucket_name} and file is {self.file_name}: {str(e)}")
            raise CustomException("Failed to download CSV file from bucket", e)
        
    def split_data(self):
        try:
            logger.info(f"Starting splitting the data into train and test files")
            df = pd.read_csv(RAW_FILE_PATH)
            train_df, test_df = train_test_split(df, test_size=1 - self.train_ratio, random_state=42)
            train_df.to_csv(TRAIN_FILE_PATH)
            test_df.to_csv(TEST_FILE_PATH)
            logger.info(f"Data split successfully into train and test files and saved to {TRAIN_FILE_PATH} and {TEST_FILE_PATH}")
        except Exception as e:
            logger.error(f"Error splitting data into train and test files: {str(e)}")
            raise CustomException("Failed to split data into train and test files", e)
    
    def run(self):
        try:
            logger.info("Starting data ingestion")
            self.download_csv_from_gcp()
            self.split_data()
            logger.info("Data ingestion completed successfully")
        except CustomException as ce:
            logger.error(f"Error in data ingestion: {str(ce)}")
            raise CustomException("Failed to ingest data", ce)

if __name__ == "__main__":
    data_ingestion = DataIngestion(read_yaml(CONFIG_PATH))
    data_ingestion.run()