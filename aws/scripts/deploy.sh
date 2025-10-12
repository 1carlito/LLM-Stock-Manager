#!/bin/bash

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "AWS credentials not configured. Please run 'aws configure' first."
    exit 1
fi

# Set variables
STACK_NAME="stock-agent-backtest-fresh"
REGION="eu-west-2"
ENVIRONMENT="prod"

# Get OpenAI API key from environment or prompt
if [ -z "$OPENAI_API_KEY" ]; then
    echo -n "Enter your OpenAI API key: "
    read -s OPENAI_API_KEY
    echo
fi

# Create S3 bucket for deployment artifacts
DEPLOYMENT_BUCKET="stock-agent-deployment-${ENVIRONMENT}"
aws s3 mb s3://${DEPLOYMENT_BUCKET} --region ${REGION} || true

# Package CloudFormation template
echo "Packaging CloudFormation template..."
aws cloudformation package \
    --template-file ../templates/cloudformation.yaml \
    --s3-bucket ${DEPLOYMENT_BUCKET} \
    --output-template-file packaged-template.yaml

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file packaged-template.yaml \
    --stack-name ${STACK_NAME} \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        EnvironmentName=${ENVIRONMENT} \
        OpenAIApiKey=${OPENAI_API_KEY} \
    --region ${REGION}

# Get stack outputs
echo "Getting stack outputs..."
aws cloudformation describe-stacks \
    --stack-name ${STACK_NAME} \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region ${REGION}

echo "Deployment complete!" 