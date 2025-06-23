#!/bin/bash

# Asegurarnos de estar en el directorio correcto
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

# Obtener las variables de Pulumi
cd ../
API_URL=$(pulumi stack output api_url)
BUCKET_NAME=$(pulumi stack output frontend_bucket_name)

if [ -z "$BUCKET_NAME" ] || [ -z "$API_URL" ]; then
    echo "Error: Could not get required values from Pulumi stack"
    exit 1
fi

# Volver al directorio del frontend
cd $SCRIPT_DIR

# Crear archivo .env.production con la URL de la API
echo "Creating .env.production with API URL..."
echo "NEXT_PUBLIC_API_URL=$API_URL" > .env.production

# Construir la aplicación
echo "Building Next.js application..."
npm run build

# Sincronizar los archivos con el bucket de S3
echo "Deploying to S3 bucket: $BUCKET_NAME"
aws s3 sync out/ s3://$BUCKET_NAME/

# Limpiar archivo .env.production
rm .env.production

# Obtener y mostrar la URL de CloudFront
cd ../
CLOUDFRONT_URL=$(pulumi stack output frontend_url)

echo "Deployment complete!"
echo "Your application is available at: $CLOUDFRONT_URL"
echo "API URL configured: $API_URL"