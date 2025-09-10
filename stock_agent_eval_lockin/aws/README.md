# AWS Deployment for Stock Agent Backtest

This directory contains all AWS-related configuration and deployment files for running the stock agent backtest on AWS infrastructure.

## Directory Structure

```
aws/
├── scripts/
│   └── deploy.sh       # Deployment script
├── templates/
│   └── cloudformation.yaml  # AWS CloudFormation template
├── Dockerfile          # Docker configuration
└── README.md          # This file
```

## Prerequisites

1. AWS CLI installed and configured
2. Docker installed (for local testing)
3. AWS credentials with appropriate permissions

## Configuration

1. Set up AWS credentials:
```bash
aws configure
AWS Access Key ID: [Your Access Key]
AWS Secret Access Key: [Your Secret Key]
Default region name: eu-west-2
Default output format: json
```

2. Make the deployment script executable:
```bash
chmod +x scripts/deploy.sh
```

## Deployment

1. Navigate to the scripts directory:
```bash
cd scripts
```

2. Run the deployment script:
```bash
./deploy.sh
```

This will:
- Create necessary AWS resources (EC2, S3, CloudWatch, SNS)
- Deploy the application
- Start the backtest process

## Infrastructure

The deployment creates:
- EC2 instance (t3.medium) for running the backtest
- S3 bucket for storing results
- CloudWatch log group for monitoring
- SNS topic for notifications

## Monitoring

- CloudWatch Logs: `/stock-agent/prod/`
- S3 Bucket: `stock-agent-backtest-prod`
- SNS Topic: `stock-agent-alerts-prod`

## Cleanup

To delete all AWS resources:
```bash
aws cloudformation delete-stack --stack-name stock-agent-backtest
``` 