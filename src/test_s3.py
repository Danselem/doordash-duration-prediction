import os
import uuid
import boto3
import click
import mlflow
import mlflow.pyfunc
import pandas as pd
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from mlflow.tracking import MlflowClient
import utils

# Load environment variables
load_dotenv()

# Load region and MLflow URI only once
region = os.getenv("AWS_DEFAULT_REGION")
mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"))

def generate_uuids(n):
    """Generates trip IDs"""
    return [str(uuid.uuid4()) for _ in range(n)]  # List comprehension for efficiency

def load_best_model(model_bucket, model_name, experiment_name):
    """Loads best model from MLflow registry and fetches from S3."""
    client = MlflowClient()
    
    # Fetch the experiment ID using the experiment name
    experiment = client.get_experiment_by_name(experiment_name)
    if not experiment:
        raise ValueError(f"No experiment found with name '{experiment_name}'")

    experiment_id = experiment.experiment_id

    # Fetch the latest run based on the test_rmse metric
    runs = client.search_runs(
        experiment_ids=[experiment_id], order_by=["metric.test_rmse ASC"], max_results=1
    )
    if not runs:
        raise ValueError("No runs found for the given experiment ID.")
    
    # Get the most recent run's run_id
    most_recent_run = runs[0]
    run_id = most_recent_run.info.run_id

    # Construct the model URI using the registered model and run_id
    model_uri = f"models:/{model_name}/4"  # Use the correct model version here

    # Log the model URI
    print(f"Loading model from MLflow registry URI: {model_uri}")

    # Load the model
    model = mlflow.pyfunc.load_model(model_uri)
    return model, run_id

def save_results(df, y_pred, y_test, run_id, output_file):
    """Saves the df to a parquet file in output file location."""
    trip_ids = generate_uuids(df.shape[0])
    results_df = pd.DataFrame(
        {
            "trip_id": trip_ids,
            "actual_duration": y_test,
            "predicted_duration": y_pred,
            "diff": y_test - y_pred,
            "model_version": run_id,
        }
    )

    final_df = pd.concat([df.reset_index(drop=True), results_df], axis=1)
    final_df.to_parquet(output_file, index=False)

def create_s3_bucket(bucket_name, region=None):
    """Creates S3 bucket if it doesn't exist."""
    s3_client = boto3.client("s3", region_name=region)
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Bucket '{bucket_name}' already exists.")
    except ClientError as e:
        if int(e.response["Error"]["Code"]) == 404:
            try:
                s3_client.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": region} if region and region != "us-east-1" else {}
                )
                print(f"Bucket '{bucket_name}' created successfully.")
            except ClientError as e:
                print(f"Error occurred while creating bucket: {e}")
        else:
            print(f"Error occurred: {e}")

def apply_model(test_data_path: str, model_bucket: str, model_name: str, dest_bucket: str):
    """Applies the predictions."""
    print(f'Reading the prepared data from {os.path.join(test_data_path, "test.pkl")}...')
    X_test, y_test = utils.load_pickle(os.path.join(test_data_path, "test.pkl"))

    print(f"Loading the model from bucket={model_bucket}...")
    model, run_id = load_best_model(model_bucket, model_name, "best-models")

    print("Applying the model...")
    y_pred = model.predict(X_test)

    print(f"Region = {region}")
    create_s3_bucket(dest_bucket, region)

    dv = utils.load_pickle("../data/processed_data/dv.pkl")

    print("Decoding Dataframes...")
    X_test = utils.decode_dataframe(dv, X_test)

    output_file = f"s3://{dest_bucket}/{run_id}.parquet"
    print(f"Saving the result to {output_file}...")

    save_results(X_test, y_pred, y_test, run_id, output_file)
    return output_file

@click.command()
@click.option(
    "--test_data_path",
    default="../data/processed_data",
    help="Location where the raw DoorDash data is saved",
)
@click.option(
    "--model_bucket",
    default="doordash-modell",
    help="Location where the raw DoorDash data is saved",
)
@click.option(
    "--model_name",
    default="doordash_best_model",
    help="Location where the raw DoorDash data is saved",
)
@click.option(
    "--dest_bucket",
    default="doordash-dur-predd",
    help="Location where the resulting files will be saved",
)
def run(test_data_path: str, model_bucket: str, model_name: str, dest_bucket: str):
    """Runs flow."""
    apply_model(test_data_path, model_bucket, model_name, dest_bucket)

if __name__ == "__main__":
    run()
