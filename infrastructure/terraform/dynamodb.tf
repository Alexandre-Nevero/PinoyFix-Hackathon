resource "aws_dynamodb_table" "users_table" {
  name           = "food_stall_finder_users"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "user_id"
  
  attribute {
    name = "user_id"
    type = "S"
  }
  
  tags = {
    Name        = "FoodStallFinderUsers"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "stalls_table" {
  name           = "food_stall_finder_stalls"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "stall_id"
  
  attribute {
    name = "stall_id"
    type = "S"
  }
  
  tags = {
    Name        = "FoodStallFinderStalls"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "menu_items_table" {
  name           = "food_stall_finder_menu_items"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "item_id"
  
  attribute {
    name = "item_id"
    type = "S"
  }
  
  tags = {
    Name        = "FoodStallFinderMenuItems"
    Environment = var.environment
  }
}

resource "aws_dynamodb_table" "reviews_table" {
  name           = "food_stall_finder_reviews"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "review_id"
  
  attribute {
    name = "review_id"
    type = "S"
  }
  
  tags = {
    Name        = "FoodStallFinderReviews"
    Environment = var.environment
  }
}