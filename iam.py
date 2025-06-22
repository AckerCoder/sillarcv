import pulumi
import pulumi_aws as aws
import json
from utils import tags
from s3 import cv_bucket

lambda_role = aws.iam.Role("upload-cv-lambda-role",
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

aws_lambda_vpc_access = aws.iam.RolePolicyAttachment("lambda-vpc-policy",
    role=lambda_role.name,
    policy_arn="arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
)

lambda_policy = aws.iam.RolePolicy("upload-cv-lambda-policy",
    role=lambda_role.id,
    policy=pulumi.Output.all(cv_bucket.arn).apply(
        lambda args: json.dumps({
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject"
                    ],
                    "Resource": [
                        f"{args[0]}/*"
                    ]
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    "Resource": [
                        "arn:aws:logs:*:*:*",
                        "arn:aws:logs:*:*:/aws/lambda/upload-cv-lambda-*"
                    ]
                }
            ]
        })
    )
)
