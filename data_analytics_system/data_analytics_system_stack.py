#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import json
import random

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_ec2,
  aws_iam,
  aws_s3 as s3,
  aws_lambda as _lambda,
  aws_kinesis as kinesis,
  aws_kinesisfirehose,
  aws_logs,
  aws_opensearchservice,
  aws_secretsmanager,
  aws_events,
  aws_events_targets
)
from constructs import Construct

from aws_cdk.aws_lambda_event_sources import (
  KinesisEventSource
)

random.seed(47)

S3_BUCKET_LAMBDA_LAYER_LIB = os.getenv('S3_BUCKET_LAMBDA_LAYER_LIB', 'lambda-layer-resources-use1')

class DataAnalyticsSystemStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    vpc = aws_ec2.Vpc(self, "AnalyticsWorkshopVPC",
      max_azs=3,
      gateway_endpoints={
        "S3": aws_ec2.GatewayVpcEndpointOptions(
          service=aws_ec2.GatewayVpcEndpointAwsService.S3
        )
      }
    )

    sg_bastion_host = aws_ec2.SecurityGroup(self, "BastionHostSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an bastion host',
      security_group_name='bastion-host-sg'
    )
    cdk.Tags.of(sg_bastion_host).add('Name', 'bastion-host-sg')

    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceClass.html
    #XXX: https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/InstanceSize.html#aws_cdk.aws_ec2.InstanceSize
    ec2_instance_type = aws_ec2.InstanceType.of(aws_ec2.InstanceClass.BURSTABLE3, aws_ec2.InstanceSize.MEDIUM)

    #XXX: As there are no SSH public keys deployed on this machine,
    # you need to use EC2 Instance Connect with the command
    #  'aws ec2-instance-connect send-ssh-public-key' to provide your SSH public key.
    # https://aws.amazon.com/de/blogs/compute/new-using-amazon-ec2-instance-connect-for-ssh-access-to-your-ec2-instances/
    bastion_host = aws_ec2.BastionHostLinux(self, "BastionHost",
      vpc=vpc,
      instance_type=ec2_instance_type,
      subnet_selection=aws_ec2.SubnetSelection(subnet_type=aws_ec2.SubnetType.PUBLIC),
      security_group=sg_bastion_host
    )

    #TODO: SHOULD restrict IP range allowed to ssh acces
    bastion_host.allow_ssh_access_from(aws_ec2.Peer.ipv4("0.0.0.0/0"))

    #XXX: In order to test data pipeline, add {Kinesis, KinesisFirehose}FullAccess Policy to the bastion host.
    bastion_host.role.add_to_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["kinesis:*"]))
    bastion_host.role.add_to_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["firehose:*"]))

    sg_use_es = aws_ec2.SecurityGroup(self, "ElasticSearchClientSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an elasticsearch client',
      security_group_name='use-es-cluster-sg'
    )
    cdk.Tags.of(sg_use_es).add('Name', 'use-es-cluster-sg')

    sg_opensearch_cluster = aws_ec2.SecurityGroup(self, "ElasticSearchSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an elasticsearch cluster',
      security_group_name='es-cluster-sg'
    )
    cdk.Tags.of(sg_opensearch_cluster).add('Name', 'es-cluster-sg')

    sg_opensearch_cluster.add_ingress_rule(peer=sg_opensearch_cluster, connection=aws_ec2.Port.all_tcp(), description='es-cluster-sg')

    sg_opensearch_cluster.add_ingress_rule(peer=sg_use_es, connection=aws_ec2.Port.tcp(443), description='use-es-cluster-sg')
    sg_opensearch_cluster.add_ingress_rule(peer=sg_use_es, connection=aws_ec2.Port.tcp_range(9200, 9300), description='use-es-cluster-sg')

    sg_opensearch_cluster.add_ingress_rule(peer=sg_bastion_host, connection=aws_ec2.Port.tcp(443), description='bastion-host-sg')
    sg_opensearch_cluster.add_ingress_rule(peer=sg_bastion_host, connection=aws_ec2.Port.tcp_range(9200, 9300), description='bastion-host-sg')

    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name="aws-analytics-immersion-day-{region}-{account}".format(
        region=kwargs['env'].region, account=kwargs['env'].account))

    trans_kinesis_stream = kinesis.Stream(self, "AnalyticsWorkshopKinesisStreams",
      # specify the ON-DEMAND capacity mode.
      # default: StreamMode.PROVISIONED
      stream_mode=kinesis.StreamMode.ON_DEMAND,
      stream_name='retail-trans')

    firehose_role_policy_doc = aws_iam.PolicyDocument()
    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(**{
      "effect": aws_iam.Effect.ALLOW,
      "resources": [s3_bucket.bucket_arn, "{}/*".format(s3_bucket.bucket_arn)],
      "actions": ["s3:AbortMultipartUpload",
        "s3:GetBucketLocation",
        "s3:GetObject",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads",
        "s3:PutObject"]
    }))

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["glue:GetTable",
        "glue:GetTableVersion",
        "glue:GetTableVersions"]
    ))

    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=[trans_kinesis_stream.stream_arn],
      actions=["kinesis:DescribeStream",
        "kinesis:GetShardIterator",
        "kinesis:GetRecords"]
    ))

    firehose_log_group_name = "/aws/kinesisfirehose/retail-trans"
    firehose_role_policy_doc.add_statements(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      #XXX: The ARN will be formatted as follows:
      # arn:{partition}:{service}:{region}:{account}:{resource}{sep}}{resource-name}
      resources=[self.format_arn(service="logs", resource="log-group",
        resource_name="{}:log-stream:*".format(firehose_log_group_name),
        arn_format=cdk.ArnFormat.COLON_RESOURCE_NAME)],
      actions=["logs:PutLogEvents"]
    ))

    firehose_role = aws_iam.Role(self, "FirehoseDeliveryRole",
      role_name="FirehoseDeliveryRole",
      assumed_by=aws_iam.ServicePrincipal("firehose.amazonaws.com"),
      #XXX: use inline_policies to work around https://github.com/aws/aws-cdk/issues/5221
      inline_policies={
        "firehose_role_policy": firehose_role_policy_doc
      }
    )

    trans_to_s3_delivery_stream = aws_kinesisfirehose.CfnDeliveryStream(self, "KinesisFirehoseToS3",
      delivery_stream_name="retail-trans",
      delivery_stream_type="KinesisStreamAsSource",
      kinesis_stream_source_configuration={
        "kinesisStreamArn": trans_kinesis_stream.stream_arn,
        "roleArn": firehose_role.role_arn
      },
      extended_s3_destination_configuration={
        "bucketArn": s3_bucket.bucket_arn,
        "bufferingHints": {
          "intervalInSeconds": 60,
          "sizeInMBs": 1
        },
        "cloudWatchLoggingOptions": {
          "enabled": True,
          "logGroupName": firehose_log_group_name,
          "logStreamName": "S3Delivery"
        },
        "compressionFormat": "UNCOMPRESSED", # [GZIP | HADOOP_SNAPPY | Snappy | UNCOMPRESSED | ZIP]
        "prefix": "json-data/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/",
        "errorOutputPrefix": "error-json/year=!{timestamp:yyyy}/month=!{timestamp:MM}/day=!{timestamp:dd}/hour=!{timestamp:HH}/!{firehose:error-output-type}",
        "roleArn": firehose_role.role_arn
      }
    )

    es_domain_name = 'retail'

    master_user_secret = aws_secretsmanager.Secret(self, "OpenSearchMasterUserSecret",
      generate_secret_string=aws_secretsmanager.SecretStringGenerator(
        secret_string_template=json.dumps({"username": "admin"}),
        generate_string_key="password",
        # Master password must be at least 8 characters long and contain at least one uppercase letter,
        # one lowercase letter, one number, and one special character.
        password_length=8
      )
    )

    #XXX: aws cdk elastsearch example - https://github.com/aws/aws-cdk/issues/2873
    # You should camelCase the property names instead of PascalCase
    es_cfn_domain = aws_opensearchservice.Domain(self, "OpenSearch",
      domain_name=es_domain_name,
      version=aws_opensearchservice.EngineVersion.OPENSEARCH_1_3,
      capacity={
        "master_nodes": 3,
        "master_node_instance_type": "r6g.large.search",
        "data_nodes": 3,
        "data_node_instance_type": "r6g.large.search"
      },
      ebs={
        "volume_size": 10,
        "volume_type": aws_ec2.EbsDeviceVolumeType.GP2
      },
      #XXX: az_count must be equal to vpc subnets count.
      zone_awareness={
        "availability_zone_count": 3
      },
      logging={
        "slow_search_log_enabled": True,
        "app_log_enabled": True,
        "slow_index_log_enabled": True
      },
      fine_grained_access_control=aws_opensearchservice.AdvancedSecurityOptions(
        master_user_name=master_user_secret.secret_value_from_json("username").to_string(),
        master_user_password=master_user_secret.secret_value_from_json("password")
      ),
      # Enforce HTTPS is required when fine-grained access control is enabled.
      enforce_https=True,
      # Node-to-node encryption is required when fine-grained access control is enabled
      node_to_node_encryption=True,
      # Encryption-at-rest is required when fine-grained access control is enabled.
      encryption_at_rest={
        "enabled": True
      },
      use_unsigned_basic_auth=True,
      security_groups=[sg_opensearch_cluster],
      automated_snapshot_start_hour=17, # 2 AM (GTM+9)
      vpc=vpc,
      vpc_subnets=[aws_ec2.SubnetSelection(one_per_az=True, subnet_type=aws_ec2.SubnetType.PRIVATE_WITH_NAT)],
      removal_policy=cdk.RemovalPolicy.DESTROY # default: cdk.RemovalPolicy.RETAIN
    )
    cdk.Tags.of(es_cfn_domain).add('Name', 'analytics-workshop-es')

    #XXX: https://github.com/aws/aws-cdk/issues/1342
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, construct_id, S3_BUCKET_LAMBDA_LAYER_LIB)
    es_lib_layer = _lambda.LayerVersion(self, "ESLib",
      layer_version_name="es-lib",
      compatible_runtimes=[_lambda.Runtime.PYTHON_3_7],
      code=_lambda.Code.from_bucket(s3_lib_bucket, "var/es-lib.zip")
    )

    #XXX: add more than 2 security groups
    # https://github.com/aws/aws-cdk/blob/ea10f0d141a48819ec0000cd7905feda993870a9/packages/%40aws-cdk/aws-lambda/lib/function.ts#L387
    # https://github.com/aws/aws-cdk/issues/1555
    # https://github.com/aws/aws-cdk/pull/5049
    #XXX: Deploy lambda in VPC - https://github.com/aws/aws-cdk/issues/1342
    upsert_to_es_lambda_fn = _lambda.Function(self, "UpsertToES",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="UpsertToES",
      handler="upsert_to_es.lambda_handler",
      description="Upsert records into elasticsearch",
      code=_lambda.Code.from_asset("./src/main/python/UpsertToES"),
      environment={
        'ES_HOST': es_cfn_domain.domain_endpoint,
        #TODO: MUST set appropriate environment variables for your workloads.
        'ES_INDEX': 'retail',
        'ES_TYPE': 'trans',
        'REQUIRED_FIELDS': 'Invoice,StockCode,Customer_ID',
        'REGION_NAME': kwargs['env'].region,
        'DATE_TYPE_FIELDS': 'InvoiceDate'
      },
      timeout=cdk.Duration.minutes(5),
      layers=[es_lib_layer],
      security_groups=[sg_use_es],
      vpc=vpc
    )

    trans_kinesis_event_source = KinesisEventSource(trans_kinesis_stream, batch_size=1000, starting_position=_lambda.StartingPosition.LATEST)
    upsert_to_es_lambda_fn.add_event_source(trans_kinesis_event_source)

    log_group = aws_logs.LogGroup(self, "UpsertToESLogGroup",
      log_group_name="/aws/lambda/UpsertToES",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(upsert_to_es_lambda_fn)

    merge_small_files_lambda_fn = _lambda.Function(self, "MergeSmallFiles",
      runtime=_lambda.Runtime.PYTHON_3_7,
      function_name="MergeSmallFiles",
      handler="athena_ctas.lambda_handler",
      description="Merge small files in S3",
      code=_lambda.Code.from_asset("./src/main/python/MergeSmallFiles"),
      environment={
        #TODO: MUST set appropriate environment variables for your workloads.
        'OLD_DATABASE': 'mydatabase',
        'OLD_TABLE_NAME': 'retail_trans_json',
        'NEW_DATABASE': 'mydatabase',
        'NEW_TABLE_NAME': 'ctas_retail_trans_parquet',
        'WORK_GROUP': 'primary',
        'OLD_TABLE_LOCATION_PREFIX': 's3://{}'.format(os.path.join(s3_bucket.bucket_name, 'json-data')),
        'OUTPUT_PREFIX': 's3://{}'.format(os.path.join(s3_bucket.bucket_name, 'parquet-retail-trans')),
        'STAGING_OUTPUT_PREFIX': 's3://{}'.format(os.path.join(s3_bucket.bucket_name, 'tmp')),
        'COLUMN_NAMES': 'invoice,stockcode,description,quantity,invoicedate,price,customer_id,country',
      },
      timeout=cdk.Duration.minutes(5)
    )

    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["athena:*"]))
    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["s3:Get*",
        "s3:List*",
        "s3:AbortMultipartUpload",
        "s3:PutObject",
      ]))
    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["glue:CreateDatabase",
        "glue:DeleteDatabase",
        "glue:GetDatabase",
        "glue:GetDatabases",
        "glue:UpdateDatabase",
        "glue:CreateTable",
        "glue:DeleteTable",
        "glue:BatchDeleteTable",
        "glue:UpdateTable",
        "glue:GetTable",
        "glue:GetTables",
        "glue:BatchCreatePartition",
        "glue:CreatePartition",
        "glue:DeletePartition",
        "glue:BatchDeletePartition",
        "glue:UpdatePartition",
        "glue:GetPartition",
        "glue:GetPartitions",
        "glue:BatchGetPartition"
      ]))
    merge_small_files_lambda_fn.add_to_role_policy(aws_iam.PolicyStatement(
      effect=aws_iam.Effect.ALLOW,
      resources=["*"],
      actions=["lakeformation:GetDataAccess"]))

    lambda_fn_target = aws_events_targets.LambdaFunction(merge_small_files_lambda_fn)
    aws_events.Rule(self, "ScheduleRule",
      schedule=aws_events.Schedule.cron(minute="5"),
      targets=[lambda_fn_target]
    )

    log_group = aws_logs.LogGroup(self, "MergeSmallFilesLogGroup",
      log_group_name="/aws/lambda/MergeSmallFiles",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(merge_small_files_lambda_fn)

    cdk.CfnOutput(self, 'BastionHostId', value=bastion_host.instance_id, export_name='BastionHostId')
    cdk.CfnOutput(self, 'BastionHostPublicDNSName', value=bastion_host.instance_public_dns_name, export_name='BastionHostPublicDNSName')
    cdk.CfnOutput(self, 'ESDomainEndpoint', value=es_cfn_domain.domain_endpoint, export_name='ESDomainEndpoint')
    cdk.CfnOutput(self, 'ESDashboardsURL', value=f"{es_cfn_domain.domain_endpoint}/_dashboards/", export_name='ESDashboardsURL')
