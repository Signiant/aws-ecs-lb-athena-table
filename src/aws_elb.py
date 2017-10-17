# Functions for working with ELB/ALB


# Checks whether logging is enabled
# For an ALB, load_balancer is an ARN; it's a name for an ELB
def check_elb_logging_status(load_balancer, load_balancer_type, boto_session):
    logging_enabled = False

    if load_balancer_type == 'ALB':
        alb_client = boto_session.client("elbv2")

        try:
            response = alb_client.describe_load_balancer_attributes(
                LoadBalancerArn=load_balancer
            )
        except Exception as e:
            print("Error obtaining attributes for ALB " + load_balancer + " (" + str(e) + ")")

        if response:  # ALB attributes are a key/value list and return a STRING
            for attrib in response['Attributes']:
                if attrib['Key'] == 'access_logs.s3.enabled' and attrib['Value'] == 'true':
                    logging_enabled = True
    elif load_balancer_type == 'ELB':
        elb_client = boto_session.client('elb')

        try:
            response = elb_client.describe_load_balancer_attributes(
                LoadBalancerName=load_balancer
            )
        except Exception as e:
            print("Error obtaining attributes for ELB " + load_balancer + " (" + str(e) + ")")

        if response:  # ELB attributes are a set object and return a BOOLEAN
            logging_enabled = response['LoadBalancerAttributes']['AccessLog']['Enabled']

    return logging_enabled


# Enable access logging on an ALB/ELB
# For an ALB, load_balancer is an ARN; it's a name for an ELB
def enable_elb_access_logging(load_balancer, load_balancer_type, bucket, bucket_prefix, boto_session):
    status = False

    print("enabling access logs for " + load_balancer + " writing to bucket " + bucket + " prefix " + bucket_prefix)

    if load_balancer_type == 'ALB':
        elb_client = boto_session.client('elbv2')

        try:
            response = elb_client.modify_load_balancer_attributes(
                LoadBalancerArn=load_balancer,
                Attributes=[
                    {
                        'Key': 'access_logs.s3.enabled',
                        'Value': 'true'
                    },
                    {
                        'Key': 'access_logs.s3.bucket',
                        'Value': bucket
                    },
                    {
                        'Key': 'access_logs.s3.prefix',
                        'Value': bucket_prefix
                    }
                ]
            )

            # We don't care about the response and it will except if there's any issue
            status = True
        except Exception as e:
            print("Error setting attributes for ALB " + load_balancer + " (" + str(e) + ")")
            status = False
    elif load_balancer_type == 'ELB':
        elb_client = boto_session.client('elb')

        try:
            response = elb_client.modify_load_balancer_attributes(
                LoadBalancerAttributes={
                    'AccessLog': {
                        'Enabled': True,
                        'S3BucketName': bucket,
                        'EmitInterval': 5,
                        'S3BucketPrefix': bucket_prefix
                    },
                },
                LoadBalancerName=load_balancer,
            )

            if response:
                if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                    status = True
        except Exception as e:
            print("Error setting attributes for ELB " + load_balancer + " (" + str(e) + ")")
            status = False

    return status


# Given a target group, find the ALB it is attached to
def lookup_alb_arn(target_group_arn, boto_session):
    print("Looking up LB arn for target group " + target_group_arn)
    alb_client = boto_session.client("elbv2")

    alb_arn = None

    # This whole process kinda violates the schema since a target group can be associated with
    # multiple ALBs.  However, in our case that's not the case
    try:
        response = alb_client.describe_target_groups(
            TargetGroupArns=[
                target_group_arn
            ],
        )
    except Exception as e:
        print("Error obtaining info for target group " + target_group_arn + " (" + str(e) + ")")

    if response:
        # get ARN of the first load balancer for this target group
        alb_arn = response['TargetGroups'][0]['LoadBalancerArns'][0]

        print("ALB arn determined to be " + alb_arn)

    return alb_arn
