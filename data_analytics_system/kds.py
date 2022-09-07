#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import aws_cdk as cdk

from aws_cdk import (
  Stack,
  aws_kinesis as kinesis
)
from constructs import Construct

class KinesisDataStreamStack(Stack):

  def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
    super().__init__(scope, construct_id, **kwargs)

    trans_kinesis_stream = kinesis.Stream(self, "AnalyticsWorkshopKinesisStreams",
      # specify the ON-DEMAND capacity mode.
      # default: StreamMode.PROVISIONED
      stream_mode=kinesis.StreamMode.ON_DEMAND,
      stream_name='retail-trans')

    self.kinesis_stream_name = trans_kinesis_stream.stream_name
    self.kinesis_stream_arn = trans_kinesis_stream.stream_arn
    self.kinesis_stream = trans_kinesis_stream

    cdk.CfnOutput(self, '{}_KinesisStreamName'.format(self.stack_name), value=self.kinesis_stream.stream_name,
      export_name='KinesisStreamName')
    cdk.CfnOutput(self, '{}_KinesisStreamArn'.format(self.stack_name), value=self.kinesis_stream.stream_arn,
      export_name='KinesisStreamArn')

