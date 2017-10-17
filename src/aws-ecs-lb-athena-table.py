import argparse
import boto3
import sys
import aws_elb  # Module in this project
import aws_athena  # Module in this project


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

    # Create an athena database if it does not exist
    # This name is hard-coded to elb_logs
    athena_database = 'elb_logs'
    if aws_athena.create_athena_database(athena_database, session):
        print("Athena database " + athena_database + " is ready to use")

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
                            load_balancer = aws_elb.lookup_alb_arn(loadbalancer_info['targetGroupArn'], session)
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
                            if not aws_elb.check_elb_logging_status(load_balancer, load_balancer_type, session):
                                print("Access logging is NOT enabled on " + load_balancer)
                                state = aws_elb.enable_elb_access_logging(
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
                                if aws_athena.create_athena_elb_table(args.force,
                                                                      athena_database,
                                                                      load_balancer_type,
                                                                      args.bucket,
                                                                      service_name,
                                                                      session):
                                                                print("Successfully created Athena table for " + service_name)
                    else:
                        print("No load balancer for " + service_name)
    except Exception as e:
        print e
        print("Cluster " + args.cluster + " was not found in region " + args.region)

    print("Complete")


if __name__ == "__main__":
    main(sys.argv[1:])
