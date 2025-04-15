import os
import mlflow
import mlflow.pyfunc
import boto3
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()  # Ensure .env file is loaded

# Get the necessary environment variables
mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
model_name = "doordash_best_model"
s3_bucket = os.getenv("TF_VAR_mlflow_models_bucket")
region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

# Set MLflow tracking URI
mlflow.set_tracking_uri(mlflow_uri)

# Initialize the MlflowClient
client = MlflowClient()

def load_registered_model(model_name):
    """Loads a registered model from MLflow's Model Registry."""
    try:
        # Fetch all versions of the model (without using the "stages" filter)
        versions = client.search_model_versions(f"name='{model_name}'")
        
        if not versions:
            print(f"No model found for {model_name}.")
            return None, None
        
        # Get the latest version by comparing version numbers (version is an integer)
        latest_version = max(versions, key=lambda v: int(v.version))
        model_version = latest_version.version
        model_uri = f"models:/{model_name}/{model_version}"
        print(f"Loading model from {model_uri}")
        
        # Load the model using mlflow.pyfunc
        model = mlflow.pyfunc.load_model(model_uri)
        return model, model_uri
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None

def save_model_artifacts_to_s3(model, model_uri, s3_bucket):
    """Saves model artifacts to S3."""
    try:
        # Define the local path to save the model artifact
        local_artifact_dir = f"./model_artifacts/{model_uri.replace('/', '_')}"
        
        # Download the model from the MLflow registry (artifact path)
        print(f"Saving model artifacts to local path: {local_artifact_dir}")
        mlflow.artifacts.download_artifacts(model_uri, dst_path=local_artifact_dir)

        # Initialize S3 client
        s3_client = boto3.client("s3", region_name=region)
        
        # Upload each file in the local artifact directory to S3
        for root, dirs, files in os.walk(local_artifact_dir):
            for file in files:
                local_file_path = os.path.join(root, file)
                s3_file_path = os.path.join(f"models/{model_uri}/artifacts", file)

                # Upload to S3
                print(f"Uploading {file} to S3 path: s3://{s3_bucket}/{s3_file_path}")
                s3_client.upload_file(local_file_path, s3_bucket, s3_file_path)
        print(f"Model artifacts successfully uploaded to S3 bucket: {s3_bucket}")
    except ClientError as e:
        print(f"Error uploading model artifacts to S3: {e}")

def main():
    """Main function to load and save model artifacts."""
    model, model_uri = load_registered_model(model_name)
    if model:
        save_model_artifacts_to_s3(model, model_uri, s3_bucket)
    else:
        print("Failed to load the model.")

if __name__ == "__main__":
    main()
