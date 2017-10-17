# Functions for working with Athena
import time
from string import Template


# Global holding the AWS account ID this is executing in
account_id = 0


def get_aws_account_id(session):
    global account_id

    if account_id == 0:
        account_id = session.client('sts').get_caller_identity()['Account']

    return account_id


# Creates a table in Athena for a load balancer
# Uses template files as the fields are different for ALB/ELB
def create_athena_elb_table(force, database, elb_type, bucket, service_name, session):
    status = True
    # s3://BUCKET/ALB PREFIX/AWSLogs/ACCOUNT NUMBER/elasticloadbalancing/us-east-1
    s3_location = 's3://' + bucket + '/' + service_name + \
        '/AWSLogs/' + \
        str(get_aws_account_id(session)) + \
        '/elasticloadbalancing/' + \
        session.region_name

    # Tables cannot have dashes
    table_name = service_name.lower().replace('-', '_')

    # Templates are slightly different for the 2 types
    if elb_type == "ALB":
        filein = open('sql/alb.sql')
    elif elb_type == "ELB":
        filein = open('sql/elb.sql')

    if force:
        # We need to remove the table first
        print("Force option specified - recreating Athena table")
        remove_table_sql = "DROP TABLE " + table_name
        query_id = submit_query(remove_table_sql, database, session)
        if query_id:
            if wait_for_query_to_complete(query_id, session):
                status = True
            else:
                status = False

    if filein and status:
        src = Template(filein.read())
        vals = {'table_name': table_name, 's3_location': s3_location}
        create_table_query = src.safe_substitute(vals)

        query_id = submit_query(create_table_query, database, session)

        if query_id:
            if wait_for_query_to_complete(query_id, session):
                status = True
            else:
                status = False
        else:
            status = False

    return status


def create_athena_database(db_name, session):
    status = False

    query_string = "CREATE DATABASE IF NOT EXISTS " + db_name

    query_id = submit_query(query_string, 'default', session)

    if query_id:
        if wait_for_query_to_complete(query_id, session):
            status = True
        else:
            status = False
    else:
        status = False

    return status


def submit_query(query, database, session):
    output_location = 's3://aws-athena-query-results-' + str(get_aws_account_id(session)) + "-" + session.region_name
    query_id = None
    response = None

    client = session.client('athena')

    try:
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={
                'Database': database
            },
            ResultConfiguration={
                'OutputLocation': output_location,
                'EncryptionConfiguration': {
                    'EncryptionOption': 'SSE_S3'
                }
            }
        )
    except Exception as e:
        print("Error submitting query to Athena " + query + " (" + str(e) + ")")

    if response:
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            query_id = response['QueryExecutionId']

    return query_id


def wait_for_query_to_complete(query_id, session):
    status = True
    client = session.client('athena')

    is_query_still_running = True
    while is_query_still_running:
        response = None
        try:
            response = client.get_query_execution(
                QueryExecutionId=query_id
            )
        except Exception as e:
            print("Error getting query execution for " + query_id + " (" + str(e) + ")")
            status = False

        if response and status:
            query_state = response['QueryExecution']['Status']['State']

            if query_state == 'FAILED':
                print("Athena query " + query_id + " failed")
                is_query_still_running = False
                status = False
            elif query_state == 'CANCELLED':
                print("Athena query " + query_id + " was cancelled")
                is_query_still_running = False
                status = False
            elif query_state == 'SUCCEEDED':
                print("Athena query " + query_id + " completed successfully")
                is_query_still_running = False
                status = True
            else:
                time.sleep(1)

    return status
