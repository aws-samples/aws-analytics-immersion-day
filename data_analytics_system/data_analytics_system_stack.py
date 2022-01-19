#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os
import random

from aws_cdk import (
  core,
  aws_ec2,
  aws_iam,
  aws_s3 as s3,
  aws_lambda as _lambda,
  aws_kinesis as kinesis,
  aws_kinesisfirehose,
  aws_logs,
  aws_elasticsearch,
  aws_events,
  aws_events_targets
)

from aws_cdk.aws_lambda_event_sources import (
  KinesisEventSource
)

random.seed(47)

S3_BUCKET_LAMBDA_LAYER_LIB = os.getenv('S3_BUCKET_LAMBDA_LAYER_LIB', 'lambda-layer-resources-use1')

class DataAnalyticsSystemStack(core.Stack):

  def __init__(self, scope: core.Construct, id: str, **kwargs) -> None:
    super().__init__(scope, id, **kwargs)

    # The code that defines your stack goes here
    vpc = aws_ec2.Vpc(self, "AnalyticsWorkshopVPC",
      max_azs=2,
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
    core.Tags.of(sg_bastion_host).add('Name', 'bastion-host-sg')

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
    core.Tags.of(sg_use_es).add('Name', 'use-es-cluster-sg')

    sg_es = aws_ec2.SecurityGroup(self, "ElasticSearchSG",
      vpc=vpc,
      allow_all_outbound=True,
      description='security group for an elasticsearch cluster',
      security_group_name='es-cluster-sg'
    )
    core.Tags.of(sg_es).add('Name', 'es-cluster-sg')

    sg_es.add_ingress_rule(peer=sg_es, connection=aws_ec2.Port.all_tcp(), description='es-cluster-sg')
    sg_es.add_ingress_rule(peer=sg_use_es, connection=aws_ec2.Port.all_tcp(), description='use-es-cluster-sg')
    sg_es.add_ingress_rule(peer=sg_bastion_host, connection=aws_ec2.Port.all_tcp(), description='bastion-host-sg')

    s3_bucket = s3.Bucket(self, "s3bucket",
      bucket_name="aws-analytics-immersion-day-{region}-{account}".format(
        region=kwargs['env'].region, account=kwargs['env'].account))

    trans_kinesis_stream = kinesis.Stream(self, "AnalyticsWorkshopKinesisStreams", stream_name='retail-trans')

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
        resource_name="{}:log-stream:*".format(firehose_log_group_name), sep=":")],
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

    #XXX: aws cdk elastsearch example - https://github.com/aws/aws-cdk/issues/2873
    es_domain_name = 'retail'
    es_cfn_domain = aws_elasticsearch.CfnDomain(self, "ElasticSearch",
      elasticsearch_cluster_config={
        "dedicatedMasterCount": 3,
        "dedicatedMasterEnabled": True,
        "dedicatedMasterType": "t2.medium.elasticsearch",
        "instanceCount": 2,
        "instanceType": "t2.medium.elasticsearch",
        "zoneAwarenessEnabled": True
      },
      ebs_options={
        "ebsEnabled": True,
        "volumeSize": 10,
        "volumeType": "gp2"
      },
      domain_name=es_domain_name,
      elasticsearch_version="7.8",
      encryption_at_rest_options={
        "enabled": False
      },
      access_policies={
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {
              "AWS": "*"
            },
            "Action": [
              "es:Describe*",
              "es:List*",
              "es:Get*",
              "es:ESHttp*"
            ],
            "Resource": self.format_arn(service="es", resource="domain", resource_name="{}/*".format(es_domain_name))
          }
        ]
      },
      snapshot_options={
        "automatedSnapshotStartHour": 17
      },
      vpc_options={
        "securityGroupIds": [sg_es.security_group_id],
        "subnetIds": vpc.select_subnets(subnet_type=aws_ec2.SubnetType.PRIVATE).subnet_ids
      }
    )
    core.Tags.of(es_cfn_domain).add('Name', 'analytics-workshop-es')

    #XXX: https://github.com/aws/aws-cdk/issues/1342
    s3_lib_bucket = s3.Bucket.from_bucket_name(self, id, S3_BUCKET_LAMBDA_LAYER_LIB)
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
      code=_lambda.Code.asset("./src/main/python/UpsertToES"),
      environment={
        'ES_HOST': es_cfn_domain.attr_domain_endpoint,
        #TODO: MUST set appropriate environment variables for your workloads.
        'ES_INDEX': 'retail',
        'ES_TYPE': 'trans',
        'REQUIRED_FIELDS': 'Invoice,StockCode,Customer_ID',
        'REGION_NAME': kwargs['env'].region,
        'DATE_TYPE_FIELDS': 'InvoiceDate'
      },
      timeout=core.Duration.minutes(5),
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
      code=_lambda.Code.asset("./src/main/python/MergeSmallFiles"),
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
      timeout=core.Duration.minutes(5)
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

