# aws-ecs-lb-athena-table
Checks each load balancer used by an ECS service to ensure logging is enabled and creates an Athena table for these logs

[![Build Status](https://travis-ci.org/Signiant/aws-ecs-lb-athena-table.svg?branch=master)](https://travis-ci.org/Signiant/aws-ecs-lb-athena-table)

# Purpose
Ensures access logging in enabled for all ECS services that use a load balancer and creates a corresponding AWS Athena table for each service

# Workings
The tool will iterate over all services in an ECS cluster.  For each service that uses a load balancer (either application or classic), it wil enable access logging to the specified S3 bucket.  It will then create an Athena table to enable easy query of load balancer access logs.

# Prerequisites
* Docker must be installed
* Either an AWS role (if running on EC2) or an access key/secret key

# Usage

The easiest way to run the tool is from docker (because docker rocks).  Arguments are:

```bash
docker pull signiant/monitor-ecs-service
```

```bash
docker run \
  -e AWS_ACCESS_KEY_ID=XXXXXX \
  -e AWS_SECRET_ACCESS_KEY=XXXXXX \
  signiant/aws-ecs-lb-athena-table \
       -c My-ECS-Cluster \
       -r us-east-1 \
       -b my-s3-bucket-for-logs
```

In this example, the arguments after the image name are

* -c <ECS cluster name>
* -r <region>
* -b <S3 bucket to place access logs in>
* Memory threshold to take action on

NOTE:  The S3 bucket must be pre-created and [configured](http://docs.aws.amazon.com/elasticloadbalancing/latest/classic/enable-access-logs.html) to accept logs for load balancers

To use an AWS access key/secret key rather than a role:

```bash
docker run \
  -e AWS_ACCESS_KEY_ID=XXXXXX \
  -e AWS_SECRET_ACCESS_KEY=XXXXXX \
  signiant/aws-ecs-lb-athena-table \
       -c My-ECS-Cluster \
       -r us-east-1 \
       -b my-s3-bucket-for-logs \
       -f
```

This example also specifies the `-f` flag which will force re-create the Athena tables.
