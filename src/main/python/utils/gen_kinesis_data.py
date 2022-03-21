#!/usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim: tabstop=2 shiftwidth=2 softtabstop=2 expandtab

import sys
import csv
import json
import argparse
from collections import OrderedDict
import base64
import traceback
import random
import time
import datetime

import boto3

random.seed(47)

SCHEMA_CONV_TOOL = {
  "Invoice": str,
  "StockCode": str,
  "Description": str,
  "Quantity": int,
  "InvoiceDate": str,
  "Price": float,
  "Customer ID": str,
  "Country": str
}

DELIMETER_BY_FORMAT = {
  'csv': ',',
  'tsv': '\t'
}


def gen_records(options, reader):
  def _adjust_date(dt):
     n = len('yyyy-mm-dd_HH:')
     today = datetime.datetime.today()
     return '{}:{}'.format(today.strftime('%Y-%m-%d %H'), dt[n:])

  record_list = []
  for row in reader:
    is_skip = (random.randint(1, 47) % 19 < 5) if options.random_select else False
    if is_skip:
      continue

    if int(row['Quantity']) <= 0:
      continue

    row['InvoiceDate'] = _adjust_date(row['InvoiceDate'])
    if options.out_format in DELIMETER_BY_FORMAT:
       delimeter = DELIMETER_BY_FORMAT[options.out_format]
       data = delimeter.join([e for e in row.values()])
    else:
      try:
        data = json.dumps(OrderedDict([(k.replace(' ', '_'), SCHEMA_CONV_TOOL[k](v)) for k, v in row.items()]), ensure_ascii=False)
      except Exception as ex:
        traceback.print_exc()
        continue
    if options.max_count == len(record_list):
      yield record_list
      record_list = []

    #XXX: When records aren't separated by a newline character (\n), SELECT COUNT(*) FROM TABLE returns "1." in Athena
    #XXX: Therefore, add a newline character (\n)
    #XXX: https://aws.amazon.com/premiumsupport/knowledge-center/select-count-query-athena-json-records/
    data = '{}\n'.format(data)
    record_list.append(data)

  if record_list:
    yield record_list


def put_records_to_firehose(client, options, records):
  MAX_RETRY_COUNT = 3

  for data in records:
    if options.dry_run:
      print(data)
      continue

    for _ in range(MAX_RETRY_COUNT):
      try:
        response = client.put_record(
          DeliveryStreamName=options.stream_name,
          Record={
            'Data': '{}\n'.format(data)
          }
        )
        break
      except Exception as ex:
        traceback.print_exc()
        time.sleep(random.randint(1, 10))
    else:
      raise RuntimeError('[ERROR] Failed to put_records into stream: {}'.format(options.stream_name))


def put_records_to_kinesis(client, options, records):
  MAX_RETRY_COUNT = 3

  payload_list = []
  for data in records:
    partition_key = 'part-{:05}'.format(random.randint(1, 1024))
    payload_list.append({'Data': data, 'PartitionKey': partition_key})

  if options.dry_run:
    print(json.dumps(payload_list, ensure_ascii=False))
    return

  for _ in range(MAX_RETRY_COUNT):
    try:
      response = client.put_records(Records=payload_list, StreamName=options.stream_name)
      break
    except Exception as ex:
      traceback.print_exc()
      time.sleep(random.randint(1, 10))
  else:
    raise RuntimeError('[ERROR] Failed to put_records into stream: {}'.format(options.stream_name))


def main():
  parser = argparse.ArgumentParser()

  parser.add_argument('--region-name', action='store', default='us-east-1',
    help='aws region name (default: us-east-1)')
  parser.add_argument('-I', '--input-file', required=True, help='The input file path ex) ./resources/online_retail.csv')
  parser.add_argument('--out-format', default='json', choices=['csv', 'tsv', 'json'])
  parser.add_argument('--service-name', required=True, choices=['kinesis', 'firehose', 'console'])
  parser.add_argument('--stream-name', help='The name of the stream to put the data record into.')
  parser.add_argument('--max-count', default=10, type=int, help='The max number of records to put.')
  parser.add_argument('--random-select', action='store_true')
  parser.add_argument('--dry-run', action='store_true')

  options = parser.parse_args()
  COUNT_STEP = 10 if options.dry_run else 100

  with open(options.input_file, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    client = boto3.client(options.service_name, region_name=options.region_name) if options.service_name != 'console' else None
    counter = 0
    for records in gen_records(options, reader):
      if options.service_name == 'kinesis':
        put_records_to_kinesis(client, options, records)
      elif options.service_name == 'firehose':
        put_records_to_firehose(client, options, records)
      else:
        print('\n'.join([e for e in records]))
      counter += 1
      if counter % COUNT_STEP == 0:
        print('[INFO] {} steps are processed'.format(counter), file=sys.stderr)
        if options.dry_run:
          break
      time.sleep(random.choices([0.01, 0.03, 0.05, 0.07, 0.1])[-1])


if __name__ == '__main__':
  main()
