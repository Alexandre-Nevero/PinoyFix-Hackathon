import os
from pydantic import BaseSettings, AnyHttpUrl

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Food Stall Finder"
    
    # JWT Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # AWS Settings
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    
    # S3 Settings
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "food-stall-finder")
    
    # DynamoDB Settings
    DYNAMODB_USERS_TABLE: str = os.getenv("DYNAMODB_USERS_TABLE", "food_stall_finder_users")
    DYNAMODB_STALLS_TABLE: str = os.getenv("DYNAMODB_STALLS_TABLE", "food_stall_finder_stalls")
    DYNAMODB_MENU_ITEMS_TABLE: str = os.getenv("DYNAMODB_MENU_ITEMS_TABLE", "food_stall_finder_menu_items")
    DYNAMODB_REVIEWS_TABLE: str = os.getenv("DYNAMODB_REVIEWS_TABLE", "food_stall_finder_reviews")
    
    # Google Maps API Key
    GOOGLE_MAPS_API_KEY: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    
    # CORS Settings
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    class Config:
        case_sensitive = True
        env_file = ".env"

settings = Settings()