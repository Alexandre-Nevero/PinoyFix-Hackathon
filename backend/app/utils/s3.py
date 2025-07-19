import boto3
import uuid
from fastapi import UploadFile
from ..config import settings

s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION
)

async def upload_file_to_s3(file: UploadFile, prefix: str = "uploads") -> str:
    """
    Upload a file to AWS S3 bucket
    
    Args:
        file: The file to upload
        prefix: The prefix to use for the object key
        
    Returns:
        The URL of the uploaded file
    """
    # Generate a unique filename
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{prefix}/{str(uuid.uuid4())}.{file_extension}"
    
    # Read file content
    contents = await file.read()
    
    # Upload to S3
    s3_client.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=unique_filename,
        Body=contents,
        ContentType=file.content_type
    )
    
    # Return the URL
    url = f"https://{settings.S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{unique_filename}"
    return url