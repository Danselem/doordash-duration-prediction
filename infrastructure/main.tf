# Make sure to manually create state bucket beforehand
terraform {
  required_version = ">= 1.0"
  
}

# Cloud provider
provider "aws" {
  region = var.aws_region
  profile = "default"
}


data "aws_caller_identity" "current_identity" {}

locals {
  account_id = data.aws_caller_identity.current_identity.account_id
}

module "mlflow_models_bucket" {
  source      = "./modules/s3"
  bucket_name = var.mlflow_models_bucket
}

module "predictions_data_bucket" {
  source      = "./modules/s3"
  bucket_name = var.prediction_bucket
}

module "ecr_repository" {
  source = "./modules/ecr"
  name = "var.ecr_repository_name"
}
