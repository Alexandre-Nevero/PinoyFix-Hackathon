from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import uuid
import boto3
from ..auth.jwt import get_current_user, get_current_owner
from ..utils.dynamodb import get_dynamodb_resource
from ..utils.s3 import upload_file_to_s3

router = APIRouter()

# Models
class MenuItemBase(BaseModel):
    name: str
    price: float
    description: str
    category: str

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemResponse(MenuItemBase):
    item_id: str
    stall_id: str
    image_url: str
    created_at: str
    updated_at: str

# DynamoDB resource
dynamodb = get_dynamodb_resource()
stalls_table = dynamodb.Table("food_stall_finder_stalls")
menu_items_table = dynamodb.Table("food_stall_finder_menu_items")

@router.post("/stalls/{stall_id}/menu", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    stall_id: str,
    name: str = Form(...),
    price: float = Form(...),
    description: str = Form(...),
    category: str = Form(...),
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_owner)
):
    # Check if stall exists and belongs to the current user
    response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Upload image to S3
    image_url = await upload_file_to_s3(image, prefix=f"menu_items/{stall_id}")
    
    # Create menu item
    item_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    
    new_menu_item = {
        "item_id": item_id,
        "stall_id": stall_id,
        "name": name,
        "price": price,
        "description": description,
        "category": category,
        "image_url": image_url,
        "created_at": timestamp,
        "updated_at": timestamp
    }
    
    menu_items_table.put_item(Item=new_menu_item)
    
    return new_menu_item

@router.get("/stalls/{stall_id}/menu", response_model=List[MenuItemResponse])
async def get_menu_items(
    stall_id: str,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Check if stall exists
    response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    # Get menu items
    if category:
        response = menu_items_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id) & 
                            boto3.dynamodb.conditions.Attr("category").eq(category)
        )
    else:
        response = menu_items_table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id)
        )
    
    menu_items = response.get("Items", [])
    
    return menu_items

@router.put("/stalls/{stall_id}/menu/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    stall_id: str,
    item_id: str,
    name: Optional[str] = Form(None),
    price: Optional[float] = Form(None),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_owner)
):
    # Check if stall exists and belongs to the current user
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Check if menu item exists
    menu_response = menu_items_table.get_item(Key={"item_id": item_id})
    menu_item = menu_response.get("Item")
    
    if not menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    if menu_item["stall_id"] != stall_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menu item does not belong to this stall"
        )
    
    # Update fields
    update_expression = "SET updated_at = :updated_at"
    expression_attribute_values = {
        ":updated_at": datetime.utcnow().isoformat()
    }
    
    if name:
        update_expression += ", #name = :name"
        expression_attribute_values[":name"] = name
    
    if price is not None:
        update_expression += ", price = :price"
        expression_attribute_values[":price"] = price
    
    if description:
        update_expression += ", description = :description"
        expression_attribute_values[":description"] = description
    
    if category:
        update_expression += ", category = :category"
        expression_attribute_values[":category"] = category
    
    # Upload new image if provided
    if image:
        image_url = await upload_file_to_s3(image, prefix=f"menu_items/{stall_id}")
        update_expression += ", image_url = :image_url"
        expression_attribute_values[":image_url"] = image_url
    
    # Update menu item in DynamoDB
    response = menu_items_table.update_item(
        Key={"item_id": item_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_attribute_values,
        ExpressionAttributeNames={
            "#name": "name"
        } if name else {},
        ReturnValues="ALL_NEW"
    )
    
    updated_menu_item = response.get("Attributes")
    
    return updated_menu_item

@router.delete("/stalls/{stall_id}/menu/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    stall_id: str,
    item_id: str,
    current_user: dict = Depends(get_current_owner)
):
    # Check if stall exists and belongs to the current user
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Check if menu item exists
    menu_response = menu_items_table.get_item(Key={"item_id": item_id})
    menu_item = menu_response.get("Item")
    
    if not menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    if menu_item["stall_id"] != stall_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Menu item does not belong to this stall"
        )
    
    # Delete menu item
    menu_items_table.delete_item(Key={"item_id": item_id})
    
    return None

@router.delete("/stalls/{stall_id}/menu/category/{category}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_items_by_category(
    stall_id: str,
    category: str,
    current_user: dict = Depends(get_current_owner)
):
    # Check if stall exists and belongs to the current user
    stall_response = stalls_table.get_item(Key={"stall_id": stall_id})
    stall = stall_response.get("Item")
    
    if not stall:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stall not found"
        )
    
    if stall["owner_id"] != current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not the owner of this stall"
        )
    
    # Get all menu items in the category
    response = menu_items_table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr("stall_id").eq(stall_id) & 
                        boto3.dynamodb.conditions.Attr("category").eq(category)
    )
    
    menu_items = response.get("Items", [])
    
    # Delete all menu items in the category
    for item in menu_items:
        menu_items_table.delete_item(Key={"item_id": item["item_id"]})
    
    return None