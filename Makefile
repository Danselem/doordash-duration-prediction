.PHONY: build push test quality_checks integration_test run all

include .env
export
# Set the image name and tag
IMAGE_NAME ?= $(TF_VAR_ecr_repository_name)
# IMAGE_NAME ?= doordash-ecrr
IMAGE_TAG ?= latest

# AWS ECR repository address
ECR_REPO ?= $(AWS_ACCOUNT_ID).dkr.ecr.$(TF_VAR_aws_region).amazonaws.com/$(IMAGE_NAME)

# Local Setup
setup:
	@echo "🚀 Setting up the environment..."
	# pip install pipenv==2024.0.1 && \
	# python3 -m venv .venv && \
	# source .venv/bin/activate && \
	# # pipenv install --dev && \
	# pipenv install && \
	# # pipenv run pip install pre-commit && \
	# pipenv run pre-commit install

	uv python install 3.9
	# uv init
	uv venv
	. .venv/bin/activate
	uv tool install black
	uv pip install --all-extras --requirement pyproject.toml
	uv pip install awscli
	# uv add -r requirements.txt
	

# Run pytest on the tests directory
test:
	@echo "🔍 Running tests with pytest..."
	# pipenv run pytest tests/
	uv run pytest tests/

# Placeholder for integration tests
integration_test:
	@echo "⚙️  Running integration tests..."
	# TODO: Add commands for running integration tests here

# Perform quality checks with isort and black
quality_checks:
	@echo "🔍 Performing code quality checks..."
	uv tool run isort . && \
	uv tool run black .
	# Uncomment the next line to include pylint checks
	# uv tool run pylint --recursive=y .

# Terraform commands

# Initialize Terraform
terraform-init:
	@echo "🔧 Initializing Terraform..."
	cd ./infrastructure/ && terraform init -reconfigure

# Plan Terraform changes. Test
terraform-plan:
	@echo "📋 Planning Terraform changes..."
	cd ./infrastructure/ && terraform plan

# Apply Terraform configuration
terraform-apply:
	@echo "🚀 Applying Terraform configuration..."
	cd ./infrastructure/ && terraform apply -auto-approve

# Build the Docker image only if tests and quality checks pass
build: quality_checks test
	@echo "🛠️  Building Docker image..."
	docker build -t $(IMAGE_NAME):$(IMAGE_TAG) -f Dockerfile .

# Push the Docker image only if it has been successfully built
push: build
	@echo "🚀 Pushing Docker image to ECR..."
	aws ecr get-login-password --profile default --region $(TF_VAR_aws_region) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(TF_VAR_aws_region).amazonaws.com && \
	docker tag $(IMAGE_NAME):$(IMAGE_TAG) $(ECR_REPO):$(IMAGE_TAG) && \
	docker push $(ECR_REPO):$(IMAGE_TAG)

# Start the Docker containers only after running tests
run: test
	@echo "🏃 Running Docker containers..."
	docker compose up -d

# Build and push the image
all: push
