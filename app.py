#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import os

import aws_cdk as cdk

from data_analytics_system.data_analytics_system_stack import DataAnalyticsSystemStack

ACCOUNT = os.getenv('CDK_DEFAULT_ACCOUNT', '')
REGION = os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
AWS_ENV = cdk.Environment(account=ACCOUNT, region=REGION)

app = cdk.App()
DataAnalyticsSystemStack(app, "data-analytics-system", env=AWS_ENV)

app.synth()
