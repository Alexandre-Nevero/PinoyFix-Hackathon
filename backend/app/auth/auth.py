from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from ..utils.dynamodb import get_dynamodb_resource
from .jwt import create_access_token, get_current_user
import uuid
import boto3
import bcrypt

router = APIRouter()

# Models
class UserBase(BaseModel):
    email: str
    full_name: str

class UserCreate(UserBase):
    password: str
    user_type: str  # "owner" or "customer"

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(UserBase):
    user_id: str
    user_type: str
    created_at: str

class Token(BaseModel):
    access_token: str
    token_type: str

# DynamoDB resource
dynamodb = get_dynamodb_resource()
users_table = dynamodb.Table("food_stall_finder_users")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    # Check if user already exists
    response = users_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("email").eq(user.email)
    )
    if response["Items"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Validate user type
    if user.user_type not in ["owner", "customer"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User type must be either 'owner' or 'customer'"
        )
    
    # Hash password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Create user
    user_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    new_user = {
        "user_id": user_id,
        "email": user.email,
        "full_name": user.full_name,
        "password": hashed_password,
        "user_type": user.user_type,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    users_table.put_item(Item=new_user)
    
    return {
        "user_id": user_id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
        "created_at": timestamp
    }

@router.post("/login", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # Get user
    response = users_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("email").eq(form_data.username)
    )
    
    if not response["Items"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = response["Items"][0]
    
    # Verify password
    if not bcrypt.checkpw(form_data.password.encode('utf-8'), user["password"].encode('utf-8')):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=60 * 24 * 7)  # 7 days
    access_token = create_access_token(
        data={"sub": user["user_id"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {
        "user_id": current_user["user_id"],
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "user_type": current_user["user_type"],
        "created_at": current_user["created_at"]
    }