#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_s3 as s3,
  aws_lambda as _lambda,
  aws_logs
)
from constructs import Construct

from aws_cdk.aws_lambda_event_sources import (
  KinesisEventSource
)

S3_BUCKET_LAMBDA_LAYER_LIB = os.getenv('S3_BUCKET_LAMBDA_LAYER_LIB', 'lambda-layer-resources-use1')

class UpsertToESStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, vpc, trans_kinesis_stream, sg_use_opensearch, ops_domain_endpoint, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

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
        'ES_HOST': ops_domain_endpoint,
        #TODO: MUST set appropriate environment variables for your workloads.
        'ES_INDEX': 'retail',
        'ES_TYPE': 'trans',
        'REQUIRED_FIELDS': 'Invoice,StockCode,Customer_ID',
        'REGION_NAME': kwargs['env'].region,
        'DATE_TYPE_FIELDS': 'InvoiceDate'
      },
      timeout=cdk.Duration.minutes(5),
      layers=[es_lib_layer],
      security_groups=[sg_use_opensearch],
      vpc=vpc
    )

    trans_kinesis_event_source = KinesisEventSource(trans_kinesis_stream, batch_size=1000, starting_position=_lambda.StartingPosition.LATEST)
    upsert_to_es_lambda_fn.add_event_source(trans_kinesis_event_source)

    log_group = aws_logs.LogGroup(self, "UpsertToESLogGroup",
      log_group_name="/aws/lambda/UpsertToES",
      retention=aws_logs.RetentionDays.THREE_DAYS)
    log_group.grant_write(upsert_to_es_lambda_fn)
