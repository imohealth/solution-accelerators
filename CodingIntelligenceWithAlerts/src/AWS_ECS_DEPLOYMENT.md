# AWS ECS Deployment Guide - Ambient AI Solution

This guide provides step-by-step instructions to deploy the Ambient AI Solution as a Docker container to AWS ECS (Elastic Container Service) in a **private, VPN-only accessible** configuration.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Architecture Overview](#architecture-overview)
3. [Step 1: Prepare Your AWS Account](#step-1-prepare-your-aws-account)
4. [Step 2: Create VPC and Network Infrastructure](#step-2-create-vpc-and-network-infrastructure)
5. [Step 3: Build and Push Docker Image](#step-3-build-and-push-docker-image)
6. [Step 4: Create IAM Roles](#step-4-create-iam-roles)
7. [Step 5: Create ECS Cluster](#step-5-create-ecs-cluster)
8. [Step 6: Configure Application Load Balancer](#step-6-configure-application-load-balancer)
9. [Step 7: Create ECS Task Definition](#step-7-create-ecs-task-definition)
10. [Step 8: Create ECS Service](#step-8-create-ecs-service)
11. [Step 9: Configure VPN Access](#step-9-configure-vpn-access)
12. [Step 10: Testing and Validation](#step-10-testing-and-validation)
13. [Monitoring and Maintenance](#monitoring-and-maintenance)
14. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
- AWS CLI installed and configured (`aws --version`)
- Docker installed (`docker --version`)
- Git installed
- Access to AWS account with administrative permissions
- VPN solution credentials (AWS Client VPN or existing corporate VPN)

### Required Information
- **Internal Network CIDR ranges** (e.g., `10.0.0.0/8` or specific IP ranges)
- **VPN CIDR block** (e.g., `172.16.0.0/22`)
- **AWS Region** (e.g., `us-east-1`)
- **IMO Health API Credentials** (Client ID and Secret)
- **AWS Bedrock Access** (ensure Amazon Nova Pro model is enabled)

### AWS Service Limits
Verify you have adequate service limits for:
- VPCs (default: 5 per region)
- Elastic IPs (default: 5 per region)
- NAT Gateways (default: 5 per AZ)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Account                           │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                    VPC (10.0.0.0/16)                   │ │
│  │                                                        │ │
│  │  ┌──────────────────┐      ┌──────────────────┐      │ │
│  │  │ Private Subnet A │      │ Private Subnet B │      │ │
│  │  │   10.0.1.0/24    │      │   10.0.2.0/24    │      │ │
│  │  │                  │      │                  │      │ │
│  │  │  ┌────────────┐  │      │  ┌────────────┐  │      │ │
│  │  │  │ ECS Task   │  │      │  │ ECS Task   │  │      │ │
│  │  │  │ (Container)│  │      │  │ (Container)│  │      │ │
│  │  │  └────────────┘  │      │  └────────────┘  │      │ │
│  │  │        ▲         │      │        ▲         │      │ │
│  │  └────────┼─────────┘      └────────┼─────────┘      │ │
│  │           │                         │                │ │
│  │           └─────────┬───────────────┘                │ │
│  │                     │                                │ │
│  │              ┌──────▼──────┐                         │ │
│  │              │ Internal    │                         │ │
│  │              │     ALB     │                         │ │
│  │              └──────▲──────┘                         │ │
│  │                     │                                │ │
│  │  ┌──────────────────┴──────────────────┐            │ │
│  │  │        Security Group (ALB)         │            │ │
│  │  │  Inbound: Internal IPs only         │            │ │
│  │  └─────────────────────────────────────┘            │ │
│  │                                                      │ │
│  │  ┌────────────────┐      ┌────────────────┐        │ │
│  │  │  NAT Gateway   │      │  NAT Gateway   │        │ │
│  │  │  (Public       │      │  (Public       │        │ │
│  │  │   Subnet A)    │      │   Subnet B)    │        │ │
│  │  └────────────────┘      └────────────────┘        │ │
│  │           │                       │                 │ │
│  └───────────┼───────────────────────┼─────────────────┘ │
│              │                       │                   │
│              └───────┬───────────────┘                   │
│                      │                                   │
│              ┌───────▼────────┐                          │
│              │ Internet       │                          │
│              │ Gateway        │                          │
│              └───────┬────────┘                          │
│                      │                                   │
└──────────────────────┼───────────────────────────────────┘
                       │
                       ▼
                   Internet
                (IMO APIs, AWS Bedrock)

Corporate VPN ──────────► Internal ALB (via Private IP)
```

**Key Components:**
- **Private Subnets**: ECS tasks run here (no direct internet access)
- **NAT Gateways**: Allow outbound internet for API calls (IMO, Bedrock)
- **Internal ALB**: Only accessible from internal network IPs
- **Security Groups**: Restrict access to specified IP ranges
- **VPN**: Provides secure access to internal resources

---

## Step 1: Prepare Your AWS Account

### 1.1 Enable Amazon Bedrock Access

```bash
# Check if Bedrock is available in your region
aws bedrock list-foundation-models --region us-east-1

# Request access to Amazon Nova Pro model (if not already enabled)
# Go to AWS Console → Bedrock → Model access → Request model access
# Select "Amazon Nova Pro" and submit request
```

### 1.2 Set Environment Variables

```bash
# Set your AWS region
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Set your internal network CIDR (update with your actual range)
export INTERNAL_CIDR="10.0.0.0/8"

# Or specific IP ranges (comma-separated)
export INTERNAL_IPS="10.10.10.0/24,10.20.30.0/24,192.168.1.0/24"

echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo "AWS Region: $AWS_REGION"
```

### 1.3 Install Required AWS CLI Plugins

```bash
# Ensure AWS CLI v2 is installed
aws --version  # Should be 2.x

# Install Session Manager plugin (optional, for debugging)
curl "https://s3.amazonaws.com/session-manager-downloads/plugin/latest/mac/sessionmanager-bundle.zip" -o "sessionmanager-bundle.zip"
unzip sessionmanager-bundle.zip
sudo ./sessionmanager-bundle/install -i /usr/local/sessionmanagerplugin -b /usr/local/bin/session-manager-plugin
```

---

## Step 2: Create VPC and Network Infrastructure

### 2.1 Create VPC

```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ambient-ai-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text)

echo "VPC ID: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
  --vpc-id $VPC_ID \
  --enable-dns-hostnames
```

### 2.2 Create Internet Gateway

```bash
# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=ambient-ai-igw}]' \
  --query 'InternetGateway.InternetGatewayId' \
  --output text)

echo "Internet Gateway ID: $IGW_ID"

# Attach to VPC
aws ec2 attach-internet-gateway \
  --vpc-id $VPC_ID \
  --internet-gateway-id $IGW_ID
```

### 2.3 Create Subnets

```bash
# Get availability zones
AZ1=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[0].ZoneName' --output text)
AZ2=$(aws ec2 describe-availability-zones --region $AWS_REGION --query 'AvailabilityZones[1].ZoneName' --output text)

echo "Using AZs: $AZ1, $AZ2"

# Create Public Subnet A (for NAT Gateway)
PUBLIC_SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.10.0/24 \
  --availability-zone $AZ1 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ambient-ai-public-a}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create Public Subnet B (for NAT Gateway)
PUBLIC_SUBNET_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.11.0/24 \
  --availability-zone $AZ2 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ambient-ai-public-b}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create Private Subnet A (for ECS tasks)
PRIVATE_SUBNET_A=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone $AZ1 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ambient-ai-private-a}]' \
  --query 'Subnet.SubnetId' \
  --output text)

# Create Private Subnet B (for ECS tasks)
PRIVATE_SUBNET_B=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone $AZ2 \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=ambient-ai-private-b}]' \
  --query 'Subnet.SubnetId' \
  --output text)

echo "Public Subnet A: $PUBLIC_SUBNET_A"
echo "Public Subnet B: $PUBLIC_SUBNET_B"
echo "Private Subnet A: $PRIVATE_SUBNET_A"
echo "Private Subnet B: $PRIVATE_SUBNET_B"
```

### 2.4 Create and Configure Route Tables

```bash
# Create public route table
PUBLIC_RT=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=ambient-ai-public-rt}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Add route to Internet Gateway
aws ec2 create-route \
  --route-table-id $PUBLIC_RT \
  --destination-cidr-block 0.0.0.0/0 \
  --gateway-id $IGW_ID

# Associate public subnets with public route table
aws ec2 associate-route-table \
  --subnet-id $PUBLIC_SUBNET_A \
  --route-table-id $PUBLIC_RT

aws ec2 associate-route-table \
  --subnet-id $PUBLIC_SUBNET_B \
  --route-table-id $PUBLIC_RT
```

### 2.5 Create NAT Gateways

```bash
# Allocate Elastic IPs for NAT Gateways
EIP_A=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=ambient-ai-nat-eip-a}]' \
  --query 'AllocationId' \
  --output text)

EIP_B=$(aws ec2 allocate-address \
  --domain vpc \
  --tag-specifications 'ResourceType=elastic-ip,Tags=[{Key=Name,Value=ambient-ai-nat-eip-b}]' \
  --query 'AllocationId' \
  --output text)

# Create NAT Gateways
NAT_GW_A=$(aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_A \
  --allocation-id $EIP_A \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=ambient-ai-nat-a}]' \
  --query 'NatGateway.NatGatewayId' \
  --output text)

NAT_GW_B=$(aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_B \
  --allocation-id $EIP_B \
  --tag-specifications 'ResourceType=natgateway,Tags=[{Key=Name,Value=ambient-ai-nat-b}]' \
  --query 'NatGateway.NatGatewayId' \
  --output text)

echo "NAT Gateway A: $NAT_GW_A"
echo "NAT Gateway B: $NAT_GW_B"

# Wait for NAT Gateways to become available (takes 1-2 minutes)
echo "Waiting for NAT Gateways to become available..."
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_A $NAT_GW_B
echo "NAT Gateways are ready!"
```

### 2.6 Create Private Route Tables

```bash
# Create private route table A
PRIVATE_RT_A=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=ambient-ai-private-rt-a}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Add route to NAT Gateway A
aws ec2 create-route \
  --route-table-id $PRIVATE_RT_A \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_A

# Associate private subnet A
aws ec2 associate-route-table \
  --subnet-id $PRIVATE_SUBNET_A \
  --route-table-id $PRIVATE_RT_A

# Create private route table B
PRIVATE_RT_B=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=ambient-ai-private-rt-b}]' \
  --query 'RouteTable.RouteTableId' \
  --output text)

# Add route to NAT Gateway B
aws ec2 create-route \
  --route-table-id $PRIVATE_RT_B \
  --destination-cidr-block 0.0.0.0/0 \
  --nat-gateway-id $NAT_GW_B

# Associate private subnet B
aws ec2 associate-route-table \
  --subnet-id $PRIVATE_SUBNET_B \
  --route-table-id $PRIVATE_RT_B

echo "Route tables configured successfully!"
```

### 2.7 Save Network Configuration

```bash
# Save all IDs to a file for future reference
cat > network-config.txt <<EOF
VPC_ID=$VPC_ID
IGW_ID=$IGW_ID
PUBLIC_SUBNET_A=$PUBLIC_SUBNET_A
PUBLIC_SUBNET_B=$PUBLIC_SUBNET_B
PRIVATE_SUBNET_A=$PRIVATE_SUBNET_A
PRIVATE_SUBNET_B=$PRIVATE_SUBNET_B
NAT_GW_A=$NAT_GW_A
NAT_GW_B=$NAT_GW_B
PUBLIC_RT=$PUBLIC_RT
PRIVATE_RT_A=$PRIVATE_RT_A
PRIVATE_RT_B=$PRIVATE_RT_B
EOF

echo "Network configuration saved to network-config.txt"
```

---

## Step 3: Build and Push Docker Image

### 3.1 Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository \
  --repository-name ambient-ai-solution \
  --region $AWS_REGION \
  --image-scanning-configuration scanOnPush=true \
  --encryption-configuration encryptionType=AES256

# Get repository URI
ECR_REPO=$(aws ecr describe-repositories \
  --repository-names ambient-ai-solution \
  --region $AWS_REGION \
  --query 'repositories[0].repositoryUri' \
  --output text)

echo "ECR Repository: $ECR_REPO"
```

### 3.2 Build Docker Image

```bash
# Navigate to application directory
cd /Users/mshahzad/Documents/source/Solution\ Engineering/SolutionAccelertors/Ambient-AI-Solution

# Build the Docker image
docker build -t ambient-ai-solution:latest .

# Tag the image for ECR
docker tag ambient-ai-solution:latest $ECR_REPO:latest
docker tag ambient-ai-solution:latest $ECR_REPO:v1.0.0
```

### 3.3 Push Image to ECR

```bash
# Authenticate Docker to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Push the image
docker push $ECR_REPO:latest
docker push $ECR_REPO:v1.0.0

echo "Docker image pushed successfully!"
echo "Image URI: $ECR_REPO:latest"
```

---

## Step 4: Create IAM Roles

### 4.1 Create ECS Task Execution Role

```bash
# Create trust policy for ECS tasks
cat > ecs-task-execution-trust-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the execution role
aws iam create-role \
  --role-name ecsTaskExecutionRole-AmbientAI \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Attach AWS managed policy for ECS task execution
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole-AmbientAI \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Attach ECR read access
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole-AmbientAI \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
```

### 4.2 Create ECS Task Role (for application permissions)

```bash
# Create task role policy for Bedrock and CloudWatch
cat > ecs-task-role-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": [
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/amazon.nova-pro-v1:0",
        "arn:aws:bedrock:${AWS_REGION}::foundation-model/us.amazon.nova-pro-v1:0"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:${AWS_REGION}:${AWS_ACCOUNT_ID}:log-group:/ecs/ambient-ai-solution:*"
    }
  ]
}
EOF

# Create the task role
aws iam create-role \
  --role-name ecsTaskRole-AmbientAI \
  --assume-role-policy-document file://ecs-task-execution-trust-policy.json

# Create and attach the policy
aws iam put-role-policy \
  --role-name ecsTaskRole-AmbientAI \
  --policy-name AmbientAI-Permissions \
  --policy-document file://ecs-task-role-policy.json

echo "IAM roles created successfully!"
```

---

## Step 5: Create ECS Cluster

### 5.1 Create ECS Cluster

```bash
# Create ECS cluster with Fargate capacity provider
aws ecs create-cluster \
  --cluster-name ambient-ai-cluster \
  --capacity-providers FARGATE FARGATE_SPOT \
  --default-capacity-provider-strategy \
    capacityProvider=FARGATE,weight=1,base=1 \
    capacityProvider=FARGATE_SPOT,weight=4 \
  --configuration executeCommandConfiguration="{logging=DEFAULT}" \
  --tags key=Application,value=AmbientAI key=Environment,value=Production

echo "ECS cluster created: ambient-ai-cluster"
```

### 5.2 Create CloudWatch Log Group

```bash
# Create log group for container logs
aws logs create-log-group \
  --log-group-name /ecs/ambient-ai-solution \
  --region $AWS_REGION

# Set retention period (30 days)
aws logs put-retention-policy \
  --log-group-name /ecs/ambient-ai-solution \
  --retention-in-days 30

echo "CloudWatch log group created"
```

---

## Step 6: Configure Application Load Balancer

### 6.1 Create Security Groups

```bash
# Create ALB security group (internal access only)
ALB_SG=$(aws ec2 create-security-group \
  --group-name ambient-ai-alb-sg \
  --description "Security group for internal ALB - Ambient AI" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ambient-ai-alb-sg}]' \
  --query 'GroupId' \
  --output text)

echo "ALB Security Group: $ALB_SG"

# Add inbound rules for internal network access ONLY
# IMPORTANT: Update these IP ranges with your actual internal network CIDRs

# Option 1: Single CIDR block
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 80 \
  --cidr 10.0.0.0/8 \
  --group-description "Internal network access on port 80"

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG \
  --protocol tcp \
  --port 443 \
  --cidr 10.0.0.0/8 \
  --group-description "Internal network access on port 443"

# Option 2: Multiple specific IP ranges (uncomment and update as needed)
# for CIDR in "10.10.10.0/24" "10.20.30.0/24" "192.168.1.0/24"; do
#   aws ec2 authorize-security-group-ingress \
#     --group-id $ALB_SG \
#     --protocol tcp \
#     --port 80 \
#     --cidr $CIDR
#   
#   aws ec2 authorize-security-group-ingress \
#     --group-id $ALB_SG \
#     --protocol tcp \
#     --port 443 \
#     --cidr $CIDR
# done

# Create ECS tasks security group
ECS_SG=$(aws ec2 create-security-group \
  --group-name ambient-ai-ecs-sg \
  --description "Security group for ECS tasks - Ambient AI" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=ambient-ai-ecs-sg}]' \
  --query 'GroupId' \
  --output text)

echo "ECS Security Group: $ECS_SG"

# Allow traffic from ALB to ECS tasks on port 5000
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 5000 \
  --source-group $ALB_SG \
  --group-description "Allow traffic from ALB"

# Allow ECS tasks to make outbound HTTPS calls (for IMO APIs, Bedrock)
aws ec2 authorize-security-group-egress \
  --group-id $ECS_SG \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### 6.2 Create Internal Application Load Balancer

```bash
# Create internal ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name ambient-ai-alb \
  --subnets $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
  --security-groups $ALB_SG \
  --scheme internal \
  --type application \
  --ip-address-type ipv4 \
  --tags Key=Name,Value=ambient-ai-alb Key=Application,Value=AmbientAI \
  --query 'LoadBalancers[0].LoadBalancerArn' \
  --output text)

echo "ALB ARN: $ALB_ARN"

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

echo "ALB DNS Name: $ALB_DNS"
echo "IMPORTANT: This is an INTERNAL DNS name, only accessible from within the VPC or via VPN"
```

### 6.3 Create Target Group

```bash
# Create target group
TG_ARN=$(aws elbv2 create-target-group \
  --name ambient-ai-tg \
  --protocol HTTP \
  --port 5000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-enabled \
  --health-check-protocol HTTP \
  --health-check-path / \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 5 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --matcher HttpCode=200 \
  --tags Key=Name,Value=ambient-ai-tg \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

echo "Target Group ARN: $TG_ARN"
```

### 6.4 Create ALB Listener

```bash
# Create HTTP listener (port 80)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TG_ARN

echo "ALB listener created on port 80"

# Optional: Create HTTPS listener (requires SSL certificate)
# If you have an ACM certificate for internal use:
# CERT_ARN="arn:aws:acm:region:account:certificate/xxx"
# aws elbv2 create-listener \
#   --load-balancer-arn $ALB_ARN \
#   --protocol HTTPS \
#   --port 443 \
#   --certificates CertificateArn=$CERT_ARN \
#   --default-actions Type=forward,TargetGroupArn=$TG_ARN
```

---

## Step 7: Create ECS Task Definition

### 7.1 Prepare Secrets (Secure Credential Storage)

```bash
# Store IMO credentials in AWS Secrets Manager (recommended for production)
aws secretsmanager create-secret \
  --name ambient-ai/imo-credentials \
  --description "IMO Health API Credentials for Ambient AI" \
  --secret-string '{
    "client_id": "YOUR_IMO_CLIENT_ID",
    "client_secret": "YOUR_IMO_CLIENT_SECRET",
    "diagnostic_workflow_client_id": "YOUR_DIAGNOSTIC_CLIENT_ID",
    "diagnostic_workflow_client_secret": "YOUR_DIAGNOSTIC_CLIENT_SECRET"
  }'

echo "Secrets stored in Secrets Manager"

# Grant ECS task execution role permission to read secrets
cat > secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": [
        "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ambient-ai/imo-credentials*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name ecsTaskExecutionRole-AmbientAI \
  --policy-name SecretsManagerAccess \
  --policy-document file://secrets-policy.json
```

### 7.2 Create Task Definition JSON

```bash
# Get ECS task execution role ARN
TASK_EXECUTION_ROLE_ARN=$(aws iam get-role \
  --role-name ecsTaskExecutionRole-AmbientAI \
  --query 'Role.Arn' \
  --output text)

# Get ECS task role ARN
TASK_ROLE_ARN=$(aws iam get-role \
  --role-name ecsTaskRole-AmbientAI \
  --query 'Role.Arn' \
  --output text)

# Create task definition file
cat > task-definition.json <<EOF
{
  "family": "ambient-ai-solution",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "${TASK_EXECUTION_ROLE_ARN}",
  "taskRoleArn": "${TASK_ROLE_ARN}",
  "containerDefinitions": [
    {
      "name": "ambient-ai-app",
      "image": "${ECR_REPO}:latest",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 5000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "${AWS_REGION}"
        },
        {
          "name": "BEDROCK_MODEL_ID",
          "value": "us.amazon.nova-pro-v1:0"
        },
        {
          "name": "IMO_AUTH_URL",
          "value": "https://api.imohealth.com/oauth/token"
        },
        {
          "name": "IMO_ENTITY_EXTRACTION_URL",
          "value": "https://api.imohealth.com/entityextraction/pipelines/imo-clinical-comprehensive?version=3.0"
        }
      ],
      "secrets": [
        {
          "name": "IMO_CLIENT_ID",
          "valueFrom": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ambient-ai/imo-credentials:client_id::"
        },
        {
          "name": "IMO_CLIENT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ambient-ai/imo-credentials:client_secret::"
        },
        {
          "name": "IMO_DIAGNOSTIC_WORKFLOW_CLIENT_ID",
          "valueFrom": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ambient-ai/imo-credentials:diagnostic_workflow_client_id::"
        },
        {
          "name": "IMO_DIAGNOSTIC_WORKFLOW_CLIENT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:${AWS_REGION}:${AWS_ACCOUNT_ID}:secret:ambient-ai/imo-credentials:diagnostic_workflow_client_secret::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/ambient-ai-solution",
          "awslogs-region": "${AWS_REGION}",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:5000/ || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

echo "Task definition file created"
```

### 7.3 Register Task Definition

```bash
# Register the task definition
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

echo "Task definition registered successfully!"

# Get the latest task definition revision
TASK_DEF_ARN=$(aws ecs describe-task-definition \
  --task-definition ambient-ai-solution \
  --query 'taskDefinition.taskDefinitionArn' \
  --output text)

echo "Task Definition ARN: $TASK_DEF_ARN"
```

---

## Step 8: Create ECS Service

### 8.1 Create ECS Service

```bash
# Create ECS service
aws ecs create-service \
  --cluster ambient-ai-cluster \
  --service-name ambient-ai-service \
  --task-definition ambient-ai-solution \
  --desired-count 2 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={
    subnets=[$PRIVATE_SUBNET_A,$PRIVATE_SUBNET_B],
    securityGroups=[$ECS_SG],
    assignPublicIp=DISABLED
  }" \
  --load-balancers "targetGroupArn=$TG_ARN,containerName=ambient-ai-app,containerPort=5000" \
  --health-check-grace-period-seconds 60 \
  --deployment-configuration "maximumPercent=200,minimumHealthyPercent=100" \
  --tags key=Application,value=AmbientAI key=Environment,value=Production

echo "ECS service created successfully!"
echo "Service: ambient-ai-service"
echo "Desired tasks: 2"
```

### 8.2 Enable Service Auto Scaling (Optional)

```bash
# Register scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/ambient-ai-cluster/ambient-ai-service \
  --min-capacity 2 \
  --max-capacity 10

# Create scaling policy based on CPU utilization
aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --scalable-dimension ecs:service:DesiredCount \
  --resource-id service/ambient-ai-cluster/ambient-ai-service \
  --policy-name cpu-scaling-policy \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleInCooldown": 300,
    "ScaleOutCooldown": 60
  }'

echo "Auto scaling configured (2-10 tasks, target CPU: 70%)"
```

### 8.3 Verify Service Deployment

```bash
# Check service status
aws ecs describe-services \
  --cluster ambient-ai-cluster \
  --services ambient-ai-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount,Pending:pendingCount}' \
  --output table

# Wait for service to stabilize (may take 2-3 minutes)
echo "Waiting for service to become stable..."
aws ecs wait services-stable \
  --cluster ambient-ai-cluster \
  --services ambient-ai-service

echo "Service is stable and running!"
```

---

## Step 9: Configure VPN Access

### Option A: AWS Client VPN (Recommended for AWS-native solution)

#### 9.1 Generate Server and Client Certificates

```bash
# Install Easy-RSA (if not already installed)
# For macOS:
brew install easy-rsa

# Create PKI directory
cd ~
mkdir -p ambient-ai-vpn/easy-rsa
cd ambient-ai-vpn/easy-rsa
easyrsa init-pki

# Build CA
easyrsa build-ca nopass

# Generate server certificate and key
easyrsa build-server-full server nopass

# Generate client certificate and key
easyrsa build-client-full client1.domain.tld nopass

# Create certificates directory
mkdir -p ~/ambient-ai-vpn/certs

# Copy certificates
cp pki/ca.crt ~/ambient-ai-vpn/certs/
cp pki/issued/server.crt ~/ambient-ai-vpn/certs/
cp pki/private/server.key ~/ambient-ai-vpn/certs/
cp pki/issued/client1.domain.tld.crt ~/ambient-ai-vpn/certs/
cp pki/private/client1.domain.tld.key ~/ambient-ai-vpn/certs/

cd ~/ambient-ai-vpn/certs
```

#### 9.2 Import Certificates to ACM

```bash
# Import server certificate
SERVER_CERT_ARN=$(aws acm import-certificate \
  --certificate fileb://server.crt \
  --private-key fileb://server.key \
  --certificate-chain fileb://ca.crt \
  --region $AWS_REGION \
  --query 'CertificateArn' \
  --output text)

# Import client certificate
CLIENT_CERT_ARN=$(aws acm import-certificate \
  --certificate fileb://client1.domain.tld.crt \
  --private-key fileb://client1.domain.tld.key \
  --certificate-chain fileb://ca.crt \
  --region $AWS_REGION \
  --query 'CertificateArn' \
  --output text)

echo "Server Certificate ARN: $SERVER_CERT_ARN"
echo "Client Certificate ARN: $CLIENT_CERT_ARN"
```

#### 9.3 Create Client VPN Endpoint

```bash
# Create Client VPN endpoint
VPN_ENDPOINT_ID=$(aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 172.16.0.0/22 \
  --server-certificate-arn $SERVER_CERT_ARN \
  --authentication-options Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=$CLIENT_CERT_ARN} \
  --connection-log-options Enabled=true,CloudwatchLogGroup=/aws/vpn/client,CloudwatchLogStream=connections \
  --vpc-id $VPC_ID \
  --security-group-ids $ALB_SG \
  --split-tunnel \
  --tag-specifications 'ResourceType=client-vpn-endpoint,Tags=[{Key=Name,Value=ambient-ai-vpn}]' \
  --query 'ClientVpnEndpointId' \
  --output text)

echo "Client VPN Endpoint ID: $VPN_ENDPOINT_ID"

# Create CloudWatch log group for VPN connections
aws logs create-log-group \
  --log-group-name /aws/vpn/client

aws logs create-log-stream \
  --log-group-name /aws/vpn/client \
  --log-stream-name connections
```

#### 9.4 Associate VPN with Subnets

```bash
# Associate VPN with private subnets
aws ec2 associate-client-vpn-target-network \
  --client-vpn-endpoint-id $VPN_ENDPOINT_ID \
  --subnet-id $PRIVATE_SUBNET_A

aws ec2 associate-client-vpn-target-network \
  --client-vpn-endpoint-id $VPN_ENDPOINT_ID \
  --subnet-id $PRIVATE_SUBNET_B

# Wait for associations to complete
sleep 30
```

#### 9.5 Add Authorization Rules

```bash
# Authorize access to VPC CIDR
aws ec2 authorize-client-vpn-ingress \
  --client-vpn-endpoint-id $VPN_ENDPOINT_ID \
  --target-network-cidr 10.0.0.0/16 \
  --authorize-all-groups

echo "VPN configured successfully!"
```

#### 9.6 Download VPN Client Configuration

```bash
# Download VPN client configuration
aws ec2 export-client-vpn-client-configuration \
  --client-vpn-endpoint-id $VPN_ENDPOINT_ID \
  --output text > ~/ambient-ai-vpn/client-config.ovpn

# Add client certificate and key to config file
echo "<cert>" >> ~/ambient-ai-vpn/client-config.ovpn
cat ~/ambient-ai-vpn/certs/client1.domain.tld.crt >> ~/ambient-ai-vpn/client-config.ovpn
echo "</cert>" >> ~/ambient-ai-vpn/client-config.ovpn

echo "<key>" >> ~/ambient-ai-vpn/client-config.ovpn
cat ~/ambient-ai-vpn/certs/client1.domain.tld.key >> ~/ambient-ai-vpn/client-config.ovpn
echo "</key>" >> ~/ambient-ai-vpn/client-config.ovpn

echo "VPN client configuration saved to: ~/ambient-ai-vpn/client-config.ovpn"
echo "Install AWS VPN Client or OpenVPN client and import this configuration"
```

### Option B: Connect to Existing Corporate VPN

If you already have a corporate VPN solution:

1. **VPN Gateway Connection**: Connect your VPN gateway to the VPC using:
   - AWS Site-to-Site VPN
   - AWS Direct Connect + VPN
   - Third-party VPN appliance in EC2

2. **Route Propagation**: Ensure your VPN routes are propagated to the private route tables

3. **Security Groups**: Update the ALB security group to allow traffic from your VPN CIDR range

4. **DNS Resolution**: Configure DNS forwarding for the internal ALB DNS name

---

## Step 10: Testing and Validation

### 10.1 Verify ECS Tasks are Running

```bash
# List running tasks
aws ecs list-tasks \
  --cluster ambient-ai-cluster \
  --service-name ambient-ai-service \
  --desired-status RUNNING

# Get task details
TASK_ARN=$(aws ecs list-tasks \
  --cluster ambient-ai-cluster \
  --service-name ambient-ai-service \
  --desired-status RUNNING \
  --query 'taskArns[0]' \
  --output text)

aws ecs describe-tasks \
  --cluster ambient-ai-cluster \
  --tasks $TASK_ARN \
  --query 'tasks[0].{Status:lastStatus,Health:healthStatus,IP:containers[0].networkInterfaces[0].privateIpv4Address}'
```

### 10.2 Check Target Group Health

```bash
# Check target health
aws elbv2 describe-target-health \
  --target-group-arn $TG_ARN \
  --query 'TargetHealthDescriptions[*].{Target:Target.Id,Port:Target.Port,Health:TargetHealth.State}' \
  --output table

# Expected output: State should be "healthy" for all targets
```

### 10.3 Test Application Access

```bash
# From a machine connected to your VPN:

# Get ALB DNS name
echo "Access the application at: http://$ALB_DNS"

# Test with curl (from VPN-connected machine)
curl -I http://$ALB_DNS

# Expected response: HTTP/1.1 200 OK
```

### 10.4 View Application Logs

```bash
# View recent logs
aws logs tail /ecs/ambient-ai-solution --follow --since 5m

# Search for errors
aws logs filter-log-events \
  --log-group-name /ecs/ambient-ai-solution \
  --filter-pattern "ERROR" \
  --start-time $(date -u -d '1 hour ago' +%s)000
```

### 10.5 Test Application Functionality

From a VPN-connected browser:

1. Navigate to `http://[ALB_DNS]`
2. Upload a sample transcript from `sample_data/sample_transcript.txt`
3. Click "Generate SOAP Note"
4. Verify the pipeline completes all 5 steps successfully
5. Check that entities are extracted and normalized

---

## Monitoring and Maintenance

### Set Up CloudWatch Alarms

```bash
# Create SNS topic for alerts
SNS_TOPIC_ARN=$(aws sns create-topic \
  --name ambient-ai-alerts \
  --query 'TopicArn' \
  --output text)

# Subscribe your email to alerts
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email

# Create alarm for unhealthy targets
aws cloudwatch put-metric-alarm \
  --alarm-name ambient-ai-unhealthy-targets \
  --alarm-description "Alert when targets are unhealthy" \
  --metric-name UnHealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --evaluation-periods 2 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=LoadBalancer,Value=$(echo $ALB_ARN | cut -d: -f6 | cut -d/ -f2-) Name=TargetGroup,Value=$(echo $TG_ARN | cut -d: -f6) \
  --alarm-actions $SNS_TOPIC_ARN

# Create alarm for high CPU
aws cloudwatch put-metric-alarm \
  --alarm-name ambient-ai-high-cpu \
  --alarm-description "Alert when CPU is high" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --evaluation-periods 2 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --dimensions Name=ServiceName,Value=ambient-ai-service Name=ClusterName,Value=ambient-ai-cluster \
  --alarm-actions $SNS_TOPIC_ARN

echo "CloudWatch alarms configured"
```

### Enable Container Insights

```bash
# Enable Container Insights for ECS cluster
aws ecs update-cluster-settings \
  --cluster ambient-ai-cluster \
  --settings name=containerInsights,value=enabled

echo "Container Insights enabled - view metrics in CloudWatch"
```

### Regular Maintenance Tasks

```bash
# Update ECS service with new image version
aws ecs update-service \
  --cluster ambient-ai-cluster \
  --service ambient-ai-service \
  --force-new-deployment

# Scale service up/down
aws ecs update-service \
  --cluster ambient-ai-cluster \
  --service ambient-ai-service \
  --desired-count 4

# View service events
aws ecs describe-services \
  --cluster ambient-ai-cluster \
  --services ambient-ai-service \
  --query 'services[0].events[:5]' \
  --output table
```

---

## Troubleshooting

### Tasks Not Starting

```bash
# Check stopped tasks
aws ecs list-tasks \
  --cluster ambient-ai-cluster \
  --service-name ambient-ai-service \
  --desired-status STOPPED \
  --max-results 5

# Get stopped task details
STOPPED_TASK=$(aws ecs list-tasks \
  --cluster ambient-ai-cluster \
  --desired-status STOPPED \
  --max-results 1 \
  --query 'taskArns[0]' \
  --output text)

aws ecs describe-tasks \
  --cluster ambient-ai-cluster \
  --tasks $STOPPED_TASK \
  --query 'tasks[0].{Reason:stoppedReason,Exit:containers[0].exitCode,Reason2:containers[0].reason}'

# Check logs
aws logs tail /ecs/ambient-ai-solution --since 1h
```

### Unhealthy Targets

```bash
# Check security groups
aws ec2 describe-security-groups \
  --group-ids $ECS_SG \
  --query 'SecurityGroups[0].IpPermissions' \
  --output table

# Verify ALB can reach tasks on port 5000
# Check health check configuration
aws elbv2 describe-target-groups \
  --target-group-arns $TG_ARN \
  --query 'TargetGroups[0].HealthCheckEnabled'
```

### Cannot Access Application via VPN

```bash
# Check VPN endpoint status
aws ec2 describe-client-vpn-endpoints \
  --client-vpn-endpoint-ids $VPN_ENDPOINT_ID \
  --query 'ClientVpnEndpoints[0].Status'

# Verify authorization rules
aws ec2 describe-client-vpn-authorization-rules \
  --client-vpn-endpoint-id $VPN_ENDPOINT_ID

# Check VPN connection logs
aws logs tail /aws/vpn/client --since 1h
```

### High Costs / NAT Gateway Optimization

```bash
# Check NAT Gateway data transfer
aws cloudwatch get-metric-statistics \
  --namespace AWS/NATGateway \
  --metric-name BytesOutToSource \
  --dimensions Name=NatGatewayId,Value=$NAT_GW_A \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum

# Consider VPC endpoints for AWS services to reduce NAT costs:
# Create Bedrock VPC endpoint
aws ec2 create-vpc-endpoint \
  --vpc-id $VPC_ID \
  --service-name com.amazonaws.$AWS_REGION.bedrock-runtime \
  --vpc-endpoint-type Interface \
  --subnet-ids $PRIVATE_SUBNET_A $PRIVATE_SUBNET_B \
  --security-group-ids $ECS_SG
```

---

## Summary of Resources Created

Save this information for future reference:

```bash
cat > deployment-summary.txt <<EOF
=== Ambient AI Solution - AWS Deployment Summary ===

NETWORK:
- VPC ID: $VPC_ID
- VPC CIDR: 10.0.0.0/16
- Private Subnets: $PRIVATE_SUBNET_A, $PRIVATE_SUBNET_B
- Public Subnets: $PUBLIC_SUBNET_A, $PUBLIC_SUBNET_B
- NAT Gateways: $NAT_GW_A, $NAT_GW_B

SECURITY:
- ALB Security Group: $ALB_SG (Allows: Internal IPs only)
- ECS Security Group: $ECS_SG (Allows: ALB only)

LOAD BALANCER:
- ALB ARN: $ALB_ARN
- ALB DNS: $ALB_DNS (INTERNAL ONLY)
- Target Group: $TG_ARN

CONTAINER:
- ECR Repository: $ECR_REPO
- Image: $ECR_REPO:latest

ECS:
- Cluster: ambient-ai-cluster
- Service: ambient-ai-service
- Task Definition: ambient-ai-solution
- Desired Count: 2
- Task Execution Role: ecsTaskExecutionRole-AmbientAI
- Task Role: ecsTaskRole-AmbientAI

VPN (if using AWS Client VPN):
- VPN Endpoint: $VPN_ENDPOINT_ID
- VPN CIDR: 172.16.0.0/22
- Client Config: ~/ambient-ai-vpn/client-config.ovpn

MONITORING:
- Log Group: /ecs/ambient-ai-solution
- SNS Topic: $SNS_TOPIC_ARN

ACCESS:
- Application URL: http://$ALB_DNS
- Access Method: VPN connection required

ESTIMATED MONTHLY COST:
- ECS Fargate (2 tasks): ~$50
- ALB: ~$20
- NAT Gateways (2): ~$70
- Data Transfer: Variable
- Total: ~$150-200/month (excluding data transfer)

EOF

echo "Deployment summary saved to deployment-summary.txt"
```

---

## Clean Up / Teardown

To remove all resources (be careful!):

```bash
# Delete ECS service
aws ecs update-service --cluster ambient-ai-cluster --service ambient-ai-service --desired-count 0
aws ecs delete-service --cluster ambient-ai-cluster --service ambient-ai-service --force

# Delete ECS cluster
aws ecs delete-cluster --cluster ambient-ai-cluster

# Delete ALB and target group
aws elbv2 delete-load-balancer --load-balancer-arn $ALB_ARN
sleep 30
aws elbv2 delete-target-group --target-group-arn $TG_ARN

# Delete VPN endpoint (if created)
aws ec2 delete-client-vpn-endpoint --client-vpn-endpoint-id $VPN_ENDPOINT_ID

# Delete NAT Gateways
aws ec2 delete-nat-gateway --nat-gateway-id $NAT_GW_A
aws ec2 delete-nat-gateway --nat-gateway-id $NAT_GW_B
sleep 60

# Release Elastic IPs
aws ec2 release-address --allocation-id $EIP_A
aws ec2 release-address --allocation-id $EIP_B

# Delete security groups
aws ec2 delete-security-group --group-id $ALB_SG
aws ec2 delete-security-group --group-id $ECS_SG

# Delete subnets
aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_A
aws ec2 delete-subnet --subnet-id $PRIVATE_SUBNET_B
aws ec2 delete-subnet --subnet-id $PUBLIC_SUBNET_A
aws ec2 delete-subnet --subnet-id $PUBLIC_SUBNET_B

# Delete route tables
aws ec2 delete-route-table --route-table-id $PRIVATE_RT_A
aws ec2 delete-route-table --route-table-id $PRIVATE_RT_B
aws ec2 delete-route-table --route-table-id $PUBLIC_RT

# Delete Internet Gateway
aws ec2 detach-internet-gateway --internet-gateway-id $IGW_ID --vpc-id $VPC_ID
aws ec2 delete-internet-gateway --internet-gateway-id $IGW_ID

# Delete VPC
aws ec2 delete-vpc --vpc-id $VPC_ID

# Delete ECR repository
aws ecr delete-repository --repository-name ambient-ai-solution --force

# Delete secrets
aws secretsmanager delete-secret --secret-id ambient-ai/imo-credentials --force-delete-without-recovery

# Delete IAM roles
aws iam detach-role-policy --role-name ecsTaskExecutionRole-AmbientAI --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
aws iam detach-role-policy --role-name ecsTaskExecutionRole-AmbientAI --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly
aws iam delete-role-policy --role-name ecsTaskExecutionRole-AmbientAI --policy-name SecretsManagerAccess
aws iam delete-role --role-name ecsTaskExecutionRole-AmbientAI

aws iam delete-role-policy --role-name ecsTaskRole-AmbientAI --policy-name AmbientAI-Permissions
aws iam delete-role --role-name ecsTaskRole-AmbientAI

echo "All resources deleted"
```

---

## Support and Contact

For issues or questions:
- AWS Support: https://console.aws.amazon.com/support/
- IMO Health: https://developer.imohealth.com
- Application Issues: Check CloudWatch Logs at `/ecs/ambient-ai-solution`

---

**Document Version:** 1.0  
**Last Updated:** December 2025  
**Deployment Type:** Private/Internal (VPN-only access)
