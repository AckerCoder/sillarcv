import json
import boto3
import os
import logging
import pdfplumber
import io
import openai
from typing import Dict, Any, List

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize clients
s3_client = boto3.client('s3')
openai.api_key = os.environ['OPENAI_API_KEY']

def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF content using pdfplumber
    """
    try:
        text_content = []
        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            for page in pdf.pages:
                text_content.append(page.extract_text())

        return "\n".join(text_content)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise

def extract_cv_info(cv_text: str) -> Dict[str, Any]:
    """
    Extract relevant information from CV text using OpenAI API.
    """
    try:
        # Create a prompt that will help GPT extract the required information
        prompt = f"""Please analyze this CV and extract the following information in a structured format:
        1. The full name of the candidate
        2. A list of recommended positions based on their experience and skills (maximum 5 positions)
        3. Their email address
        4. Their phone number
        5. Their country of residence

        CV Text:
        {cv_text}

        Please respond ONLY with a JSON object in this exact format:
        {{
            "name": "full name",
            "recommendations": ["position1", "position2", ...],
            "email": "email address",
            "phone": "phone number",
            "country": "country name"
        }}
        """

        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a CV analysis expert. Extract information from CVs accurately and format it as JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )

        # Parse the response
        result = json.loads(response.choices[0].message['content'])
        return result

    except Exception as e:
        logger.error(f"Error analyzing CV with OpenAI: {str(e)}")
        raise

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler that processes uploaded CVs and extracts information using OpenAI.
    """
    try:
        # Get bucket and key from the S3 event
        bucket = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        logger.info(f"Processing CV from bucket: {bucket}, key: {key}")

        # Get the PDF file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        pdf_content = response['Body'].read()

        # Extract text from PDF
        cv_text = extract_text_from_pdf(pdf_content)
        logger.info("Successfully extracted text from PDF")

        # Analyze CV text with OpenAI
        cv_info = extract_cv_info(cv_text)
        logger.info("Successfully analyzed CV with OpenAI")

        # Store the results in DynamoDB
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

        # Prepare the item with indexed and non-indexed fields
        item = {
            'cv_file': key,
            'analyzed_at': context.invoked_function_arn,
            'name': cv_info['name'],
            'email': cv_info['email'],
            'additional_info': json.dumps({
                'phone': cv_info['phone'],
                'country': cv_info['country'],
                'recommendations': cv_info['recommendations']
            })
        }

        table.put_item(Item=item)
        logger.info("Successfully stored CV analysis in DynamoDB")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'CV analyzed successfully',
                'cv_info': cv_info
            })
        }

    except Exception as e:
        logger.error(f"Error processing CV: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }