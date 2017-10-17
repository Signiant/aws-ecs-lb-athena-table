CREATE EXTERNAL TABLE IF NOT EXISTS $table_name (
 type string,
 time string,
 elb string,
 client_ip string,
 client_port int,
 target_ip string,
 target_port int,
 request_processing_time double,
 target_processing_time double,
 response_processing_time double,
 elb_status_code string,
 target_status_code string,
 received_bytes bigint,
 sent_bytes bigint,
 request_verb string,
 request_url string,
 request_proto string,
 user_agent string,
 ssl_cipher string,
 ssl_protocol string,
 target_group_arn string,
 trace_id string
)
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.RegexSerDe'
WITH SERDEPROPERTIES (
 'serialization.format' = '1',
 'input.regex' = '([^ ]*) ([^ ]*) ([^ ]*) ([^ ]*):([0-9]*) ([^ ]*)[:\-]([0-9]*) ([-.0-9]*) ([-.0-9]*) ([-.0-9]*) (|[-0-9]*) (-|[-0-9]*) ([-0-9]*) ([-0-9]*) \"([^ ]*) ([^ ]*) (- |[^ ]*)\" (\"[^\"]*\") ([A-Z0-9-]+) ([A-Za-z0-9.-]*) ([^ ]*) (.*)' )
LOCATION '$s3_location';
