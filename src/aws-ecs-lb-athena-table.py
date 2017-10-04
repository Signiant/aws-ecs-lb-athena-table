import argparse
import pprint
import boto3

## mainFile
def main(argv):
    parser = argparse.ArgumentParser(description='Create Athena tables for each load balancer used by an ECS service')
    parser.add_argument('-c','--cluster', help='ECS cluster to iterate services on',required=True)
    parser.add_argument('-r','--region', help='AWS region containing the cluster and where Athena tables will be created',required=True)
    parser.add_argument('-b','--bucket', help='S3 bucket that will contain the ELB access logs (service name will be appended)',required=True)
    parser.add_argument('-f','--force', help='Force re-creation of Athena table',action='store_true')
    parser.add_argument('-v','--verbose', help='Turn on verbose output',action='store_true')

    args = parser.parse_args()


    print "Complete"

if __name__ == "__main__":
   main(sys.argv[1:])
