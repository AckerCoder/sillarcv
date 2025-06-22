import pulumi
import pulumi_aws as aws
import json
from utils import tags
from dynamo import dynamo_table
from lambda_function import upload_cv_lambda
from s3 import cv_bucket

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

# 4. API Gateway REST con restricción a IP específica
rest_api = aws.apigateway.RestApi("api",
    policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "execute-api:/*/*/*"
            },
            {
                "Effect": "Deny",
                "Principal": "*",
                "Action": "execute-api:Invoke",
                "Resource": "execute-api:/*/*/*",
                "Condition": {
                    "NotIpAddress": {
                        "aws:SourceIp": "45.177.197.199/32"
                    }
                }
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
        "method.request.header.Content-Type": True
    }
)

upload_cv_integration = aws.apigateway.Integration("upload-cv-integration",
    rest_api=rest_api.id,
    resource_id=upload_cv_resource.id,
    http_method=upload_cv_method.http_method,
    integration_http_method="POST",
    type="AWS_PROXY",
    uri=upload_cv_lambda.invoke_arn
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

# Export outputs
pulumi.export("bucket_name", cv_bucket.bucket)
pulumi.export("dynamodb_table", dynamo_table.name)
pulumi.export("lambda_name", upload_cv_lambda.name)
pulumi.export("api_url",
    pulumi.Output.concat(
        "https://",
        rest_api.id,
        ".execute-api.",
        aws.get_region().name,
        ".amazonaws.com/prod/upload-cv"
    )
)
