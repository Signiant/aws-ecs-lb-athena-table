# aws-ecs-lb-athena-table
Checks each load balancer used by an ECS service to ensure logging is enabled and creates an Athena table for these logs

[![Build Status](https://travis-ci.org/Signiant/aws-ecs-lb-athena-table.svg?branch=master)](https://travis-ci.org/Signiant/aws-ecs-lb-athena-table)

# Purpose
Ensures access logging in enabled for all ECS services that use a load balancer and creates a corresponding AWS Athena table for each service
