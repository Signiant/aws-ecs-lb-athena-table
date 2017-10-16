import argparse
import boto3
import sys


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


def enable_elb_access_logging(load_balancer, load_balancer_type, bucket, bucket_prefix, boto_session):
    print("enable_elb_access_logging")
    status = False

    if load_balancer_type == 'ALB':
        print("Enabling logging for ALB")
    elif load_balancer_type == 'ELB':
        print("Enabling logging for ELB")
        elb_client = boto_session.client('elb')

        print("enabling logging for " + load_balancer + " writing to bucket " + bucket + " prefix " + bucket_prefix)
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


def create_athena_table(force, bucket, service_name, session):
    print "create athena table"


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


def main(argv):
    parser = argparse.ArgumentParser(description='Create Athena tables for each load balancer used by an ECS service')
    parser.add_argument('-c', '--cluster', help='ECS cluster to iterate services on', required=True)
    parser.add_argument('-r', '--region', help='AWS region containing the cluster and where Athena tables will be created', required=True)
    parser.add_argument('-b', '--bucket', help='S3 bucket that will contain the ELB access logs (service name will be appended)', required=True)
    parser.add_argument('-f', '--force', help='Force re-creation of Athena table', action='store_true')

    args = parser.parse_args()

    # get a list of ECS services in the specified cluster
    session = boto3.session.Session(region_name=args.region)
    ecs = session.client("ecs")

    try:
        # have to use a paginator to handle > 10 services
        sPaginator = ecs.get_paginator('list_services')
        sIterator = sPaginator.paginate(cluster=args.cluster)
        for cluster in sIterator:
            services = []
            for service in cluster['serviceArns']:
                services.append(service)

            if len(services) == 0:
                print("There doesn't seem to be any services in the cluster " + args.cluster)

            # Describe the service to get the load balancer if there is one
            services_desc = ecs.describe_services(cluster=args.cluster, services=services)
            for service in services_desc['services']:
                service_name = service['serviceName'].rsplit('-', 1)[0]
                load_balancer_type = None
                need_to_create_athena_table = False

                if 'loadBalancers' in service:
                    if len(service['loadBalancers']) > 0:
                        # for ECS services, we only have one load balancer with the service
                        loadbalancer_info = service['loadBalancers'][0]

                        # ok, we have a load balancer - what type is it?
                        if 'targetGroupArn' in loadbalancer_info:
                            print("Found an ALB for service " + service_name)
                            load_balancer = lookup_alb_arn(loadbalancer_info['targetGroupArn'], session)
                            load_balancer_type = "ALB"
                        elif 'loadBalancerName' in loadbalancer_info:
                            print("Found an ELB Classic for service " + service_name)
                            load_balancer = loadbalancer_info['loadBalancerName']  # TODO lookup arn from name
                            load_balancer_type = "ELB"
                        else:
                            print("Unable to determine the load balancer type for service " + service_name)
                            load_balancer = None
                            load_balancer_type = None

                        if load_balancer:
                            # Check and see if logging is enabled.  If not, enable it
                            state = False
                            if not check_elb_logging_status(load_balancer, load_balancer_type, session):
                                print("Access logging is NOT enabled on " + load_balancer)
                                state = enable_elb_access_logging(
                                    load_balancer,
                                    load_balancer_type,
                                    args.bucket,
                                    service_name,
                                    session)

                                if state:
                                    print("Successfully enabled access logging on " + load_balancer)
                                    need_to_create_athena_table = True
                                else:
                                    print("ERROR enabling access logging on " + load_balancer)
                            else:
                                print("Access logging is already enabled on " + load_balancer)

                            if need_to_create_athena_table or args.force:
                                create_athena_table(args.force, args.bucket, service_name, session)
                    else:
                        print("No load balancer for " + service_name)
    except Exception as e:
        print e
        print("Cluster " + args.cluster + " was not found in region " + args.region)

    print("Complete")


if __name__ == "__main__":
    main(sys.argv[1:])
