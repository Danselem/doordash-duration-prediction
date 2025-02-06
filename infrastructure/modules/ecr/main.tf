resource "aws_ecr_repository" "ecr_repo" {
  name = var.name
  lifecycle {
    ignore_changes = [name]  # Ignore changes to the repository name if it already exists
  }
}

