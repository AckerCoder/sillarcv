import json
import base64
import boto3
import os
import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client('s3')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function to handle file upload to S3 from API Gateway

    Args:
        event: API Gateway event
        context: Lambda context

    Returns:
        API Gateway response
    """
    try:
        logger.info("Processing new file upload request")
        logger.info(f"Event: {json.dumps(event)}")

        # Get the bucket name from environment variable
        bucket_name = os.environ['S3_BUCKET_NAME']
        logger.info(f"Using bucket: {bucket_name}")

        # Get the file content from the request body
        if 'body' not in event:
            raise ValueError("No body found in the request")

        # API Gateway always sends binary content as base64
        body = event['body']
        try:
            body = base64.b64decode(body)
            logger.info("Successfully decoded base64 body")
        except Exception as e:
            logger.error(f"Error decoding base64: {str(e)}")
            raise ValueError("Invalid base64 content")

        # Get the filename from headers or generate one
        headers = event.get('headers', {})
        logger.info(f"Request headers: {headers}")

        content_disposition = headers.get('Content-Disposition', '')
        if 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"')
        else:
            # Generate a unique filename if none provided
            filename = f"upload_{context.aws_request_id}.pdf"

        logger.info(f"Using filename: {filename}")

        # Upload file to S3
        response = s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=body,
            ContentType=headers.get('Content-Type', 'application/pdf')
        )

        logger.info(f"S3 upload response: {response}")
        logger.info(f"File {filename} uploaded successfully to {bucket_name}")

        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # Enable CORS
            },
            'body': json.dumps({
                'message': 'File uploaded successfully',
                'filename': filename,
                'bucket': bucket_name
            })
        }

    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'  # Enable CORS
            },
            'body': json.dumps({
                'error': str(e),
                'type': str(type(e).__name__)
            })
        }
