#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import time
import json
import pprint
import argparse

import boto3

SHARD_ITER_TYPE = ('TRIM_HORIZON', 'LATEST')

def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--region-name', action='store', default='us-east-1', help='region name')
  parser.add_argument('--stream-name', action='store', help='kinesis stream-name')
  parser.add_argument('--iter-type', choices=SHARD_ITER_TYPE, default='TRIM_HORIZON',
    help='kinesis stream shard iterator type: [{}]'.format(', '.join(SHARD_ITER_TYPE)))

  options = parser.parse_args()

  stream_name, shard_iter_type = options.stream_name, options.iter_type

  kinesis_client = boto3.client('kinesis', region_name=options.region_name)
  response = kinesis_client.describe_stream(StreamName=stream_name)
  shard_id = response['StreamDescription']['Shards'][0]['ShardId']

  shard_iterator = kinesis_client.get_shard_iterator(StreamName=stream_name,
                                                     ShardId=shard_id,
                                                     ShardIteratorType=shard_iter_type)

  shard_iter = shard_iterator['ShardIterator']
  record_response = kinesis_client.get_records(ShardIterator=shard_iter, Limit=123)
  print(record_response.get('Records', {}))

  while 'NextShardIterator' in record_response:
    record_response = kinesis_client.get_records(ShardIterator=record_response['NextShardIterator'], Limit=123)
    print(record_response.get('Records', {}))

    # wait for 5 seconds
    time.sleep(5)

if __name__ == '__main__':
  main()
