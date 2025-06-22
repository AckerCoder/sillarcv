import json
import boto3
import os
import logging
from typing import Dict, Any
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SES client
ses_client = boto3.client('ses')

def create_email_body(cv_info: Dict[str, Any]) -> str:
    """
    Create a formatted HTML email body with the CV information
    """
    recommendations = cv_info.get('additional_info', {}).get('recommendations', [])
    recommendations_html = "\n".join([f"<li>{pos}</li>" for pos in recommendations])

    return f"""
    <html>
    <body>
        <h2>Nuevo CV Analizado</h2>
        <p><strong>Nombre:</strong> {cv_info.get('name')}</p>
        <p><strong>Email:</strong> {cv_info.get('email')}</p>
        <p><strong>Teléfono:</strong> {cv_info.get('additional_info', {}).get('phone')}</p>
        <p><strong>País:</strong> {cv_info.get('additional_info', {}).get('country')}</p>
        <p><strong>Archivo:</strong> {cv_info.get('cv_file')}</p>
        <h3>Posiciones Recomendadas:</h3>
        <ul>
            {recommendations_html}
        </ul>
        <p><em>Analizado en: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>
    </body>
    </html>
    """

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler that processes DynamoDB Stream events and sends email notifications
    """
    try:
        for record in event['Records']:
            # Solo nos interesan los registros nuevos
            if record['eventName'] != 'INSERT':
                continue

            # Obtener la nueva imagen del registro
            new_image = record['dynamodb']['NewImage']

            # Convertir la imagen de DynamoDB a un diccionario Python
            cv_info = {
                'cv_file': new_image['cv_file']['S'],
                'name': new_image['name']['S'],
                'email': new_image['email']['S'],
                'additional_info': json.loads(new_image['additional_info']['S'])
            }

            # Crear el cuerpo del email
            email_body = create_email_body(cv_info)

            # Enviar el email
            response = ses_client.send_email(
                Source=os.environ['SENDER_EMAIL'],
                Destination={
                    'ToAddresses': [os.environ['RECIPIENT_EMAIL']]
                },
                Message={
                    'Subject': {
                        'Data': f'Nuevo CV Analizado: {cv_info["name"]}'
                    },
                    'Body': {
                        'Html': {
                            'Data': email_body
                        }
                    }
                }
            )

            logger.info(f"Email sent successfully: {response['MessageId']}")

        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Notifications processed successfully'
            })
        }

    except Exception as e:
        logger.error(f"Error processing notifications: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }