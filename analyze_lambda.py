import pulumi
import pulumi_aws as aws
import json
from utils import tags
from vpc import vpc, private_subnet_ids, security_group_id
from dynamo import dynamo_table

# Create Lambda layer for dependencies
analyze_cv_layer = aws.lambda_.LayerVersion("analyze-cv-layer",
    compatible_runtimes=["python3.9"],
    code=pulumi.FileArchive("./layer.zip"),
    layer_name="analyze-cv-dependencies",
    description="Dependencies for CV analysis: pdfplumber, openai"
)

# Create IAM role for the Lambda
analyze_cv_role = aws.iam.Role("analyze-cv-role",
    assume_role_policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Action": "sts:AssumeRole",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Effect": "Allow"
        }]
    }),
    tags=tags
)

# Add necessary policies to the role
analyze_cv_policy = aws.iam.RolePolicy("analyze-cv-policy",
    role=analyze_cv_role.id,
    policy=pulumi.Output.all(dynamo_table.name).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:GetObject"
                    ],
                    "Resource": "arn:aws:s3:::mis-postulaciones-cv/*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem"
                    ],
                    "Resource": f"arn:aws:dynamodb:*:*:table/{args[0]}"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:CreateNetworkInterface",
                        "ec2:DescribeNetworkInterfaces",
                        "ec2:DeleteNetworkInterface"
                    ],
                    "Resource": "*"
                }
            ]
        })
    )
)

# Create the Lambda function
analyze_cv_lambda = aws.lambda_.Function("analyze-cv-lambda",
    runtime="python3.9",
    handler="analyze_cv.lambda_handler",
    role=analyze_cv_role.arn,
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./lambdas")
    }),
    layers=[analyze_cv_layer.arn],
    timeout=300,  # 5 minutes
    memory_size=512,
    environment={
        "variables": {
            "OPENAI_API_KEY": pulumi.Config().require_secret("openai_api_key"),
            "DYNAMODB_TABLE": dynamo_table.name
        }
    },
    vpc_config={
        "subnet_ids": private_subnet_ids,
        "security_group_ids": [security_group_id]
    },
    tags=tags
)

# Allow S3 to invoke the Lambda
s3_lambda_permission = aws.lambda_.Permission("analyze-cv-s3-permission",
    action="lambda:InvokeFunction",
    function=analyze_cv_lambda.name,
    principal="s3.amazonaws.com",
    source_arn=f"arn:aws:s3:::mis-postulaciones-cv"
)

# Export the Lambda ARN
pulumi.export("analyze_cv_lambda_arn", analyze_cv_lambda.arn)