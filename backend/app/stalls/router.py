from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import boto3
from ..auth.jwt import get_current_user, get_current_owner
from ..utils.dynamodb import get_dynamodb_resource
from ..utils.s3 import upload_file_to_s3
from ..utils.location import calculate_distance

router = APIRouter()

# Models
class LocationModel(BaseModel):
    latitude: float
    longitude: float
    address: str

class StallBase(BaseModel):
    name: str
    description: str
    location: LocationModel

class StallCreate(StallBase):
    pass

class StallResponse(StallBase):
    stall_id: str
    owner_id: str
    image_url: str
    created_at: str
    updated_at: str
    distance: Optional[float] = None

# DynamoDB resource
dynamodb = get_dynamodb_resource()
stalls_table = dynamodb.Table("food_stall_finder_stalls")
menu_items_table = dynamodb.Table("food_stall_finder_menu_items")
reviews_table = dynamodb.Table("food_stall_finder_reviews")

@router.post("/", response_model=StallResponse, status_code=status.HTTP_201_CREATED)
async def create_stall(
    name: str = Form(...),
    description: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    address: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_owner)
):
    # Upload image to S3
    image_url = await upload_file_to_s3(image, prefix=f"stalls/{current_user['user_id']}")
    
    # Create stall
    stall_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    new_stall = {
        "stall_id": stall_id,
        "owner_id": current_user["user_id"],
        "name": name,
        "description": description,
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "address": address
        },
        "image_url": image_url,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    stalls_table.put_item(Item=new_stall)
    
    return {
        **new_stall,
        "location": {
            "latitude": latitude,
            "longitude": longitude,
            "address": address
        }
    }

@router.get("/", response_model=List[StallResponse])
async def get_stalls(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius: Optional[float] = 5.0,  # Radius in kilometers
    current_user: dict = Depends(get_current_user)
):
    # Get all stalls
    response = stalls_table.scan()
    stalls = response.get("Items", [])
    
    # If location is provided, filter and sort by distance
    if latitude is not None and longitude is not None:
        user_location = (latitude, longitude)
        
        # Calculate distance for each stall
        for stall in stalls:
            stall_location = (
                stall["location"]["latitude"],
                stall["location"]["longitude"]
            )
            distance = calculate_distance(user_location, stall_location)
            stall["distance"] = distance
        
        # Filter stalls within the specified radius
        stalls = [stall for stall in stalls if stall["distance"] <= radius]
        
        # Sort by distance
        stalls.sort(key=lambda x: x["distance"])
    
    return stalls

@router.get("/{stall_id}", response_model=StallResponse)
async def get_stall(
    stall_id: str,
    current_user: dict = Depends(get_current_user)
):
    # Get stall
    response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    return stall

@router.put("/{stall_id}", response_model=StallResponse)
async def update_stall(
    stall_id: str,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    address: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_owner)
):
    # Get stall
    response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Check if the current user is the owner
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Update fields
    update_expression = "SET updated_at = :updated_at"
    expression_attribute_values = {
        ":updated_at": datetime.utcnow().isoformat()
    }
    
    if name:
        update_expression += ", #name = :name"
        expression_attribute_values[":name"] = name
    
    if description:
        update_expression += ", description = :description"
        expression_attribute_values[":description"] = description
    
    # Update location if any component is changed
    if any([latitude, longitude, address]):
        current_location = stall["location"]
        new_location = {
            "latitude": latitude if latitude is not None else current_location["latitude"],
            "longitude": longitude if longitude is not None else current_location["longitude"],
            "address": address if address is not None else current_location["address"]
        }
        update_expression += ", #location = :location"
        expression_attribute_values[":location"] = new_location
    
    # Upload new image if provided
    if image:
        image_url = await upload_file_to_s3(image, prefix=f"stalls/{current_user['user_id']}")
        update_expression += ", image_url = :image_url"
        expression_attribute_values[":image_url"] = image_url
    
    # Update stall in DynamoDB
    response = stalls_table.update_item(
        Key={"stall_id": stall_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames={
            "#name": "name",
            "#location": "location"
        },
        ReturnValues="ALL_NEW"
    )
    
    updated_stall = response.get("Attributes")
    
    return updated_stall

@router.delete("/{stall_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stall(
    stall_id: str,
    current_user: dict = Depends(get_current_owner)
):
    # Get stall
    response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Check if the current user is the owner
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Delete stall
    stalls_table.delete_item(Key={"stall_id": stall_id})
    
    # Delete all menu items associated with this stall
    menu_response = menu_items_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id)
    )
    
    for item in menu_response.get("Items", []):
        menu_items_table.delete_item(Key={"item_id": item["item_id"]})
    
    # Delete all reviews associated with this stall
    reviews_response = reviews_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id)
    )
    
    for review in reviews_response.get("Items", []):
        reviews_table.delete_item(Key={"review_id": review["review_id"]})
    
    return None