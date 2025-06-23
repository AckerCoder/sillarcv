import pulumi
import pulumi_aws as aws
import json
from utils import tags
from dynamo import dynamo_table
from lambda_function import upload_cv_lambda
from s3 import cv_bucket
from analyze_lambda import analyze_cv_lambda
from notify_lambda import notify_lambda


# Frontend infrastructure
frontend_bucket = aws.s3.Bucket("frontend-bucket",
    bucket=f"sillar-cv-frontend-{pulumi.get_stack()}",
    website={
        "index_document": "index.html",
        "error_document": "404.html"
    },
    force_destroy=True,  # Permite eliminar el bucket aunque no esté vacío
    tags=tags
)

# Configure public access block for frontend bucket
frontend_bucket_public_access_block = aws.s3.BucketPublicAccessBlock("frontend-bucket-public-access-block",
    bucket=frontend_bucket.id,
    block_public_acls=True,
    block_public_policy=False,  # Necesitamos esto en false para permitir la política del bucket
    ignore_public_acls=True,
    restrict_public_buckets=False  # Necesitamos esto en false para permitir acceso desde CloudFront
)

# Create Origin Access Identity for CloudFront
cloudfront_oai = aws.cloudfront.OriginAccessIdentity("frontend-oai",
    comment=f"OAI for Sillar CV Frontend {pulumi.get_stack()}"
)

# Create bucket policy to allow CloudFront access
frontend_bucket_policy = aws.s3.BucketPolicy("frontend-bucket-policy",
    bucket=frontend_bucket.id,
    policy=pulumi.Output.all(bucket_name=frontend_bucket.id, oai_arn=cloudfront_oai.iam_arn).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AllowCloudFrontAccess",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": args['oai_arn']
                    },
                    "Action": [
                        "s3:GetObject",
                        "s3:ListBucket"
                    ],
                    "Resource": [
                        f"arn:aws:s3:::{args['bucket_name']}",
                        f"arn:aws:s3:::{args['bucket_name']}/*"
                    ]
                }
            ]
        })
    )
)

# Create CloudFront distribution
frontend_cdn = aws.cloudfront.Distribution("frontend-cdn",
    enabled=True,
    is_ipv6_enabled=True,
    default_root_object="index.html",
    origins=[{
        "originId": frontend_bucket.id,
        "domainName": frontend_bucket.bucket_regional_domain_name,
        "s3_origin_config": {
            "originAccessIdentity": cloudfront_oai.cloudfront_access_identity_path
        }
    }],
    default_cache_behavior={
        "allowedMethods": ["GET", "HEAD", "OPTIONS"],
        "cachedMethods": ["GET", "HEAD", "OPTIONS"],
        "targetOriginId": frontend_bucket.id,
        "forwardedValues": {
            "queryString": False,
            "cookies": {
                "forward": "none"
            }
        },
        "viewerProtocolPolicy": "redirect-to-https",
        "minTtl": 0,
        "defaultTtl": 3600,
        "maxTtl": 86400
    },
    custom_error_responses=[
        {
            "errorCode": 404,
            "responseCode": 200,
            "responsePagePath": "/index.html"
        },
        {
            "errorCode": 403,
            "responseCode": 200,
            "responsePagePath": "/index.html"
        }
    ],
    restrictions={
        "geoRestriction": {
            "restrictionType": "none"
        }
    },
    viewer_certificate={
        "cloudfrontDefaultCertificate": True
    },
    price_class="PriceClass_100",  # Use only North America and Europe edge locations
    tags=tags,
    opts=pulumi.ResourceOptions(depends_on=[frontend_bucket_policy, frontend_bucket_public_access_block])
)

# 1. Crear el rol IAM para API Gateway CloudWatch logs
api_gateway_log_role = aws.iam.Role("api-gateway-log-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "apigateway.amazonaws.com"
            },
            "Effect": "Allow"
        }]
    }),
    tags=tags
)

# 2. Adjuntar política para permitir escribir logs
api_gateway_log_policy = aws.iam.RolePolicy("api-gateway-log-policy",
    role=api_gateway_log_role.id,
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:DescribeLogGroups",
                "logs:DescribeLogStreams",
                "logs:PutLogEvents",
                "logs:GetLogEvents",
                "logs:FilterLogEvents"
            ],
            "Resource": "*"
        }]
    })
)

# 3. Configurar la cuenta de API Gateway (esto debe ser lo primero)
account_settings = aws.apigateway.Account("api-gateway-account",
    cloudwatch_role_arn=api_gateway_log_role.arn
)

# 4. API Gateway REST API
rest_api = aws.apigateway.RestApi("api",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "execute-api:/*/*/*"
            }
        ]
    }),
    binary_media_types=["application/pdf", "application/octet-stream"],
    tags=tags
)

upload_cv_resource = aws.apigateway.Resource("upload_cv",
    rest_api=rest_api.id,
    parent_id=rest_api.root_resource_id,
    path_part="upload-cv",
)

upload_cv_method = aws.apigateway.Method("upload-cv-method",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method="POST",
    authorization="NONE",
    request_parameters={
        "method.request.header.Content-Type": True,
        "method.request.header.Content-Disposition": True
    }
)

upload_cv_integration = aws.apigateway.Integration("upload-cv-integration",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method=upload_cv_method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=upload_cv_lambda.invoke_arn,
    content_handling="CONVERT_TO_BINARY"
)

# Add OPTIONS method for CORS
upload_cv_options = aws.apigateway.Method("upload-cv-options",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method="OPTIONS",
    authorization="NONE"
)

upload_cv_options_integration = aws.apigateway.Integration("upload-cv-options-integration",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method=upload_cv_options.http_method,
    type="MOCK",
    request_templates={
        "application/json": "{\"statusCode\": 200}"
    }
)

upload_cv_options_response = aws.apigateway.MethodResponse("upload-cv-options-response",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method=upload_cv_options.http_method,
    status_code="200",
    response_parameters={
        "method.response.header.Access-Control-Allow-Headers": True,
        "method.response.header.Access-Control-Allow-Methods": True,
        "method.response.header.Access-Control-Allow-Origin": True
    },
    response_models={
        "application/json": "Empty"
    }
)

upload_cv_options_integration_response = aws.apigateway.IntegrationResponse("upload-cv-options-integration-response",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method=upload_cv_options.http_method,
    status_code=upload_cv_options_response.status_code,
    response_parameters={
        "method.response.header.Access-Control-Allow-Headers": "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token,Content-Disposition'",
        "method.response.header.Access-Control-Allow-Methods": "'GET,POST,OPTIONS'",
        "method.response.header.Access-Control-Allow-Origin": "'*'"
    },
    response_templates={
        "application/json": ""
    }
)

# 5. Deployment y Stage con logging habilitado (después de la configuración de la cuenta)
api_deployment = aws.apigateway.Deployment("api-deployment",
    rest_api=rest_api.id,
    opts=pulumi.ResourceOptions(depends_on=[
        upload_cv_integration,
        account_settings  # Aseguramos que la cuenta esté configurada primero
    ])
)

api_stage = aws.apigateway.Stage("prod",
    deployment=api_deployment.id,
    rest_api=rest_api.id,
    stage_name="prod",
    xray_tracing_enabled=True,
    access_log_settings={
        "destination_arn": pulumi.Output.concat("arn:aws:logs:", aws.get_region().name, ":", aws.get_caller_identity().account_id, ":log-group:/aws/api-gateway/", rest_api.name),
        "format": json.dumps({
            "requestId": "$context.requestId",
            "ip": "$context.identity.sourceIp",
            "caller": "$context.identity.caller",
            "user": "$context.identity.user",
            "requestTime": "$context.requestTime",
            "httpMethod": "$context.httpMethod",
            "resourcePath": "$context.resourcePath",
            "status": "$context.status",
            "protocol": "$context.protocol",
            "responseLength": "$context.responseLength",
            "error": {
                "message": "$context.error.message",
                "type": "$context.error.responseType",
                "validationErrorString": "$context.error.validationErrorString"
            }
        })
    },
    opts=pulumi.ResourceOptions(depends_on=[account_settings]),  # Aseguramos que la cuenta esté configurada primero
    tags=tags
)

# 6. Configuración de método
stage_settings = aws.apigateway.MethodSettings("all-methods",
    rest_api=rest_api.id,
    stage_name=api_stage.stage_name,
    method_path="*/*",
    settings={
        "metricsEnabled": True,
        "loggingLevel": "INFO",
        "dataTraceEnabled": True,
        "throttlingBurstLimit": 5000,
        "throttlingRateLimit": 10000
    },
    opts=pulumi.ResourceOptions(depends_on=[api_stage, account_settings])  # Aseguramos el orden correcto
)

# 7. Permiso para que API Gateway invoque la Lambda
lambda_permission = aws.lambda_.Permission("api-gateway-permission",
    action="lambda:InvokeFunction",
    function=upload_cv_lambda.name,
    principal="apigateway.amazonaws.com",
    source_arn=pulumi.Output.concat(rest_api.execution_arn, "/*/*/upload-cv")
)

# Add Lambda trigger for CV analysis
cv_bucket_notification = aws.s3.BucketNotification("cv-bucket-notification",
    bucket=cv_bucket.id,
    lambda_functions=[{
        "lambda_function_arn": analyze_cv_lambda.arn,
        "events": ["s3:ObjectCreated:*"],
        "filter_prefix": "",
        "filter_suffix": ".pdf"
    }],
    opts=pulumi.ResourceOptions(depends_on=[cv_bucket, analyze_cv_lambda])
)

# Export outputs
pulumi.export("bucket_name", cv_bucket.bucket)
pulumi.export("dynamodb_table", dynamo_table.name)
pulumi.export("lambda_name", upload_cv_lambda.name)
pulumi.export("analyze_lambda_name", analyze_cv_lambda.name)
pulumi.export("notify_lambda_name", notify_lambda.name)
pulumi.export("api_url",
    pulumi.Output.concat(
        "https://",
        rest_api.id,
        ".execute-api.",
        aws.get_region().name,
        ".amazonaws.com/prod/upload-cv"
    )
)

# Frontend exports
pulumi.export("frontend_bucket_name", frontend_bucket.id)
pulumi.export("frontend_url", pulumi.Output.concat("https://", frontend_cdn.domain_name))
