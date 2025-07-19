resource "aws_s3_bucket" "food_stall_finder_bucket" {
  bucket = "food-stall-finder-${var.environment}"
  
  tags = {
    Name        = "FoodStallFinderBucket"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_cors_configuration" "food_stall_finder_cors" {
  bucket = aws_s3_bucket.food_stall_finder_bucket.id
  
  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "PUT", "POST"]
    allowed_origins = ["*"]  # In production, specify actual origins
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_public_access_block" "food_stall_finder_public_access" {
  bucket = aws_s3_bucket.food_stall_finder_bucket.id
  
  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "food_stall_finder_bucket_policy" {
  bucket = aws_s3_bucket.food_stall_finder_bucket.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.food_stall_finder_bucket.arn}/*"
      },
    ]
  })
}