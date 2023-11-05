#!/usr/bin/python3

import os
import boto3
from botocore.exceptions import ClientError
import logging

def showBuckets(brs3):
    for bucket in brs3.buckets.all():
        print(bucket.name)
    return

def uploadFile(bcs3, fn, bucket, objn):
    try:
        #response = bcs3.meta.client.upload_file(fn, bucket, objn)
        response = bcs3.upload_file(fn, bucket, objn)
    except ClientError as e:
        logging.error(e)
        return False
    return True

print("sandbox boto3 version=%s" % boto3.__version__)

s3resource = boto3.resource('s3')
s3client = boto3.client('s3')

showBuckets(s3resource)

OBJ_DELIM="/"
fqfn="x3.pdf"
fn=os.path.basename(fqfn)
objFn=OBJ_DELIM + "used" + OBJ_DELIM + fn
bucketCsv="fmllc-csv"
bucketInvoice="fmllc-invoice"

print("objFn=%s" % objFn)
uploadFile(s3client, fqfn, bucketInvoice, objFn)
