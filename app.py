#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from data_analytics_system import (
  VpcStack,
  BastionHostStack,
  KinesisDataStreamStack,
  ElasticSearchStack,
  ##XXX: For using Amazon OpenSearch Service, remove comments from both the below code
  # OpenSearchStack,
  KinesisFirehoseStack,
  UpsertToESStack,
  MergeSmallFilesLambdaStack
)

ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT', '')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
AWS_ENV = cdk.Environment(account=ACCOUNT, region=REGION)

app = cdk.App()
vpc_stack = VpcStack(app, 'DataAnalyticsVpcStack',
  env=AWS_ENV)

bastion_host_stack = BastionHostStack(app, 'DataAnalyticsBastionHostStack',
  vpc_stack.vpc,
  #XXX: YOU SHOULD pass `region` and `account` values in the `env` of the StackProps
  # in order to prevent the following error:
  #   Cross stack references are only supported for stacks deployed
  # to the same environment or between nested stacks and their parent stack
  env=AWS_ENV)

kds_stack = KinesisDataStreamStack(app, 'DataAnalyticsKinesisStreamStack')

firehose_stack = KinesisFirehoseStack(app, 'DataAnalyticsFirehoseStack',
  kds_stack.kinesis_stream)

search_stack = ElasticSearchStack(app, 'DataAnalyticsElasticSearchStack',
  vpc_stack.vpc,
  bastion_host_stack.sg_bastion_host,
  #XXX: YOU SHOULD pass `region` and `account` values in the `env` of the StackProps
  # in order to prevent the following error:
  #   Cross stack references are only supported for stacks deployed
  # to the same environment or between nested stacks and their parent stack
  env=AWS_ENV)

#XXX: For using Amazon OpenSearch Service,
# remove comments from both the below codes and the dependent codes,
# then comments out `search_stack = ElasticSearchStack(...)` codes
#
# search_stack = OpenSearchStack(app, 'DataAnalyticsOpenSearchStack',
#   vpc_stack.vpc,
#   bastion_host_stack.sg_bastion_host,
#   #XXX: YOU SHOULD pass `region` and `account` values in the `env` of the StackProps
#   # in order to prevent the following error:
#   #   Cross stack references are only supported for stacks deployed
#   # to the same environment or between nested stacks and their parent stack
#   env=AWS_ENV)

upsert_to_es_stack = UpsertToESStack(app, 'DataAnalyticsUpsertToESStack',
  vpc_stack.vpc,
  kds_stack.kinesis_stream,
  search_stack.sg_search_client,
  search_stack.search_domain_endpoint,
  env=AWS_ENV
)

merge_small_files_stack = MergeSmallFilesLambdaStack(app, 'DataAnalyticsMergeSmallFilesStack',
  firehose_stack.s3_bucket_name
)

app.synth()

