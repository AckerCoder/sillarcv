import pulumi
import pulumi_aws as aws
import json
from utils import tags
from dynamo import dynamo_table

# Create IAM role for the Lambda
notify_lambda_role = aws.iam.Role("notify-lambda-role",
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
notify_lambda_policy = aws.iam.RolePolicy("notify-lambda-policy",
    role=notify_lambda_role.id,
    policy=pulumi.Output.all(stream_arn=dynamo_table.stream_arn).apply(
        lambda values: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "ses:SendEmail",
                        "ses:SendRawEmail"
                    ],
                    "Resource": "*"  # Restringe esto a tu ARN de SES específico en producción
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:GetRecords",
                        "dynamodb:GetShardIterator",
                        "dynamodb:DescribeStream",
                        "dynamodb:ListStreams"
                    ],
                    "Resource": [
                        values['stream_arn']
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": "arn:aws:logs:*:*:*"
                }
            ]
        })
    )
)

# Create the Lambda function
notify_lambda = aws.lambda_.Function("notify-lambda",
    runtime="python3.9",
    handler="notify.lambda_handler",
    role=notify_lambda_role.arn,
    code=pulumi.AssetArchive({
        ".": pulumi.FileArchive("./lambdas")
    }),
    timeout=30,
    memory_size=128,
    environment={
        "variables": {
            "SENDER_EMAIL": pulumi.Config().require("sender_email"),
            "RECIPIENT_EMAIL": pulumi.Config().require("recipient_email")
        }
    },
    tags=tags
)

# Add DynamoDB Stream trigger to Lambda
stream_trigger = aws.lambda_.EventSourceMapping("dynamo-stream-trigger",
    event_source_arn=dynamo_table.stream_arn,
    function_name=notify_lambda.name,
    starting_position="LATEST",
    batch_size=1,  # Procesar un registro a la vez
    maximum_retry_attempts=3
)

# Export the Lambda ARN
pulumi.export("notify_lambda_arn", notify_lambda.arn)