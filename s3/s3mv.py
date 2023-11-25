#!/usr/bin/python3

import os
import sys
import glob
import boto3
from botocore.exceptions import ClientError
import logging

def showBuckets(brs3):
    for bucket in brs3.buckets.all():
        print(bucket.name)
    return

def showBucketContents(bn):
    print("showBucketContents bucket=%s" % bn)
    bucket = s3resource.Bucket(bn)
    for obj in bucket.objects.all():
        print(obj.key)

def showBucketContentsWithFilter(bn, pfx):
    print("showBucketContentsWithFilter bucket=%s prefix=%s" % (bn, pfx))
    bucket = s3resource.Bucket(bn)
    for obj in bucket.objects.filter(Prefix=pfx):
        print(obj.key)

def uploadFile(bcs3, fn, bucket, objn):
    try:
        #response = bcs3.meta.client.upload_file(fn, bucket, objn)
        response = bcs3.upload_file(fn, bucket, objn)
    except ClientError as e:
        logging.error(e)
        return False
    return True

def uploadFilesInDir(srcDir, bucket, prefixName):
    d = os.path.join(srcDir, "*")
    flist = glob.glob(d)

    for fn in flist:
        objFn = prefixUsed + os.path.basename(fn)
        print("%s -> %s" % (fn, objFn))
        uploadFile(s3client, fn, bucket, objFn)

def uploadInvoiceUsedDir():
    uploadFilesInDir(srcDirUsed, bucketInvoice, prefixUsed)

# --- main ---

print("s3mv boto3 version=%s" % boto3.__version__)

s3resource = boto3.resource('s3')
s3client = boto3.client('s3')

bucketCsv="fmllc-csv"
bucketInvoice="fmllc-invoice"

OBJ_DELIM="/"
prefixNew = "new" + OBJ_DELIM
prefixUsed = "used" + OBJ_DELIM

srcInvoiceDirNew  = "/home/mike/dev/fm/invoices/2023/new/"
srcInvoiceDirUsed = "/home/mike/dev/fm/invoices/2023/used/"

srcCsvDirNew  = "/home/mike/dev/fm/csv/2023/new/"
srcCsvDirUsed = "/home/mike/dev/fm/csv/2023/used/"

showBuckets(s3resource)

showBucketContentsWithFilter(bucketInvoice, prefixUsed)
showBucketContentsWithFilter(bucketInvoice, prefixNew)
