from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import boto3
from ..auth.jwt import get_current_user
from ..utils.dynamodb import get_dynamodb_resource

router = APIRouter()

# Models
class ReviewBase(BaseModel):
    rating: int
    comment: str

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    review_id: str
    stall_id: str
    user_id: str
    user_name: str
    created_at: str
    updated_at: str

# DynamoDB resource
dynamodb = get_dynamodb_resource()
stalls_table = dynamodb.Table("food_stall_finder_stalls")
reviews_table = dynamodb.Table("food_stall_finder_reviews")
users_table = dynamodb.Table("food_stall_finder_users")

@router.post("/stalls/{stall_id}/reviews", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    stall_id: str,
    review: ReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    # Check if stall exists
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Check if the current user is the owner of the stall (can't review own stall)
    if stall["owner_id"] == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot review your own stall"
        )
    
    # Check if the user already has a review for this stall
    response = reviews_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id) & 
                        boto3.dynamodb.conditions.Attr("user_id").eq(current_user["user_id"])
    )
    
    if response.get("Items"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this stall. Please edit your existing review."
        )
    
    # Validate rating
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Create review
    review_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    new_review = {
        "review_id": review_id,
        "stall_id": stall_id,
        "user_id": current_user["user_id"],
        "user_name": current_user["full_name"],
        "rating": review.rating,
        "comment": review.comment,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    reviews_table.put_item(Item=new_review)
    
    return new_review

@router.get("/stalls/{stall_id}/reviews", response_model=List[ReviewResponse])
async def get_reviews(
    stall_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Check if stall exists
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Get reviews
    response = reviews_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id)
    )
    
    reviews = response.get("Items", [])
    
    return reviews

@router.put("/stalls/{stall_id}/reviews/{review_id}", response_model=ReviewResponse)
async def update_review(
    stall_id: str,
    review_id: str,
    review: ReviewCreate,
    current_user: dict = Depends(get_current_user)
):
    # Check if stall exists
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Check if review exists
    review_response = reviews_table.get_item(Key={"review_id": review_id})
    existing_review = review_response.get("Item")
    
    if not existing_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if the review belongs to the stall
    if existing_review["stall_id"] != stall_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review does not belong to this stall"
        )
    
    # Check if the current user is the author of the review
    if existing_review["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the author of this review"
        )
    
    # Validate rating
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rating must be between 1 and 5"
        )
    
    # Update review
    timestamp = datetime.utcnow().isoformat()
    
    updated_review = reviews_table.update_item(
        Key={"review_id": review_id},
        UpdateExpression="SET rating = :rating, comment = :comment, updated_at = :updated_at",
        ExpressionAttributeValues={
            ":rating": review.rating,
            ":comment": review.comment,
            ":updated_at": timestamp
        },
        ReturnValues="ALL_NEW"
    )
    
    return updated_review.get("Attributes")

@router.delete("/stalls/{stall_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    stall_id: str,
    review_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Check if stall exists
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Check if review exists
    review_response = reviews_table.get_item(Key={"review_id": review_id})
    existing_review = review_response.get("Item")
    
    if not existing_review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found"
        )
    
    # Check if the review belongs to the stall
    if existing_review["stall_id"] != stall_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Review does not belong to this stall"
        )
    
    # Check if the current user is the author of the review
    if existing_review["user_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the author of this review"
        )
    
    # Delete review
    reviews_table.delete_item(Key={"review_id": review_id})
    
    return None