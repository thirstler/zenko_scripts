#!/usr/bin/python3
"""
Tag tool can be used to mass-tag objects in buckets (or clear them) using a 
keylist as input (from a file or stdin). It can also append tags using any new
tags in favor of existing key/value pairs where collisions exist.
"""
import os, sys, time
import boto3
import argparse
import multiprocessing

##
# Some defaults
PROFILE_DEF = "default"
DEBUG = False
WORKERS = 5
RETRIES = 5

def logme(level, text):
    """ level == 0 is always logged, level == 1 logged during debug """
    if level == 0:
        print(text)
    elif level > 0 and DEBUG == True:
        print(text)


def _cleartags(args, ovs, s3):

    count = 0
    for keyitem in ovs["Contents"]:

        for r in range(RETRIES):
            try:
                response = s3.delete_object_tagging(
                    Bucket=args.bucket, Key=keyitem["Key"]
                )
            except Exception as e:
                logme(0, "error: {0} {1}".format(keyitem["Key"], str(e)))
                continue
            break

        if (
            response["ResponseMetadata"]["HTTPStatusCode"] == 200
            or response["ResponseMetadata"]["HTTPStatusCode"] == 204
        ):
            logme(1, "SUCCESS: {0}".format(keyitem["Key"]))
        else:
            logme(1, "FAILED: {0}: {1}".format(keyitem["Key"], str(response)))

        count += 1

    logme(1, "{0} keys cleared".format(count))
    
    return count


def _applytagging(args, ovs, s3):
    tagitems = args.tagging.split(",")
    tagset = []
    count = 0

    for item in tagitems:
        keyval = item.split("=")
        tagset.append({"Key": keyval[0], "Value": keyval[1]})

    for keyitem in ovs["Contents"]:

        for r in range(RETRIES):
            try:
                response = s3.put_object_tagging(
                    Bucket=args.bucket, Key=keyitem["Key"], Tagging={"TagSet": tagset}
                )
            except Exception as e:
                logme(0, "error: {0} {1}".format(keyitem["Key"], str(e)))
                continue
            break

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logme(1, "SUCCESS: {0}".format(keyitem["Key"]))
        else:
            logme(1, "FAILED: {0} {1}".format(keyitem["Key"], str(response)))
        count += 1

    logme(1, "{0} keys tagged".format(count))
    return count


def _merge_taglists(source_t, dest_t, noreplace=False):
    if noreplace:
        merged = dest_t + source_t
    else:
        merged = source_t + dest_t
    keys = []
    rdest = []
    for m in merged:
        if m["Key"] in keys:
            continue
        else:
            rdest.append(m)
        keys.append(m["Key"])
    return rdest


def _retag(args, ovs, s3, append=False):

    a_tagset = []

    if append:
        tagitems = args.append.split(",")
        for item in tagitems:
            keyval = item.split("=")
            a_tagset.append({"Key": keyval[0], "Value": keyval[1]})

    count = 0
    for keyitem in ovs["Contents"]:

        for r in range(RETRIES):
            try:
                tags = s3.get_object_tagging(Bucket=args.bucket, Key=keyitem["Key"])
            except Exception as e:
                logme(0, "error: {0} {1}".format(keyitem["Key"], str(e)))
                continue
            break

        if append:
            tags["TagSet"] = _merge_taglists(a_tagset, tags["TagSet"], noreplace=args.noreplace)

        for r in range(RETRIES):
            try:
                response = s3.put_object_tagging(
                    Bucket=args.bucket,
                    Key=keyitem["Key"],
                    Tagging={"TagSet": tags["TagSet"]},
                )
            except Exception as e:
                logme(0, "error: {0} {1}".format(keyitem["Key"], str(e)))
                continue
            break

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            logme(1, "SUCCESS: {0}".format(keyitem["Key"]))
        else:
            logme(1, "FAILED: {0} {1}".format(keyitem["Key"], str(response)))
        count += 1

    logme(1, "{0} keys re-tagged".format(count))

    return count


def _run_batch(args, ovs, wrkrcnt, mng_ret):
    """
    Page worker for relabeling
    """
    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    """ I dunno man, what are we doing here? """
    if args.cleartags:
        count = _cleartags(args, ovs, s3)

    elif args.tagging != None:
        count = _applytagging(args, ovs, s3)

    elif args.append != None:
        count = _retag(args, ovs, s3, append=True)

    elif args.retag == True:
        count = _retag(args, ovs, s3, append=False)

    mng_ret[wrkrcnt] = count


def a_key(args):

    #try:
    _run_batch(args,  {"Contents": [{"Key": args.key}]}, 0, {})
    #except Exception as e:
    #    print("barf: {0}".format(str(e)))
    print("ok")

def from_file(args, fh):
    """
    Start tagging jobs from file input
    """
    jobs = []
    count = 0
    wrkrcnt = 0
    keylist = {"Contents": []}
    manager = multiprocessing.Manager()
    mng_ret = manager.dict()
    tss = time.time()
    tse = tss
    ttlc = 0

    while True:
        key = fh.readline().strip()
        if not key: break

        keylist["Contents"].append({"Key": key})
        if count >= args.maxkeys:
            jobs.append(multiprocessing.Process(target=_run_batch, args=(args, keylist, wrkrcnt, mng_ret)))
            jobs[wrkrcnt].start()
            wrkrcnt += 1
            if wrkrcnt >= int(args.workers):
                for job in jobs:
                    job.join()
                tse = time.time()
                wrkrcnt = 0
                jobs = []
            for c in mng_ret:
                ttlc += mng_ret[c]

            print("processed {0} keys in {1:.2f} sec".format(ttlc, (tse - tss)))

            mng_ret = manager.dict()
            count = 0
            keylist = {"Contents": []}
        count += 1


    # Stragglers and small operations
    for job in jobs:
        job.join()

    for c in mng_ret:
        ttlc += mng_ret[c]

    # the straggling stragglers
    _run_batch(args, keylist, -1, mng_ret)

    tse = time.time()
    print("(final) processed {0} keys in {1:.2f} sec".format(ttlc + len(keylist["Contents"]), (tse - tss)))


def tagbucket(args):
    """
    Bucket listing and worker distribution entry.
    """
    jobs = []
    wrkrcnt = 0
    manager = multiprocessing.Manager()
    mng_ret = manager.dict()
    tss = time.time()
    tse = tss
    ttlc = 0

    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    lspgntr = s3.get_paginator("list_objects_v2")
    page_iterator = lspgntr.paginate(
        Bucket=args.bucket, Prefix=args.prefix, MaxKeys=args.maxkeys
    )

    for ovs in page_iterator:
        jobs.append(multiprocessing.Process(target=_run_batch, args=(args, ovs, wrkrcnt, mng_ret)))
        jobs[wrkrcnt].start()
        wrkrcnt += 1
        if wrkrcnt >= int(args.workers):
            for job in jobs:
                job.join()
            tse = time.time()
            wrkrcnt = 0
            jobs = []
            for c in mng_ret:
                ttlc += mng_ret[c]
            mng_ret = manager.dict()
            print("processed {0} keys in {1:.2f} sec".format(ttlc, (tse - tss)))

    # Stragglers and small operations
    for job in jobs:
        job.join()
    tse = time.time()

    for c in mng_ret:
        ttlc += mng_ret[c]

    print("(final) processed {0} keys in {1:.2f} sec".format(ttlc, (tse - tss)))

def just_go(args):

    if args.wholebucket:
        tagbucket(args)

    elif args.input:

        with open(args.input, "r") as fh:
            from_file(args, fh)
        fh.close()

    elif args.key:
        a_key(args)

    else:
        with sys.stdin as fh:
            from_file(args, fh)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Mass tag objects in the specified keylist file (or stdin)"
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--profile", default=PROFILE_DEF)
    parser.add_argument("--endpoint", default="https://s3.amazonaws.com")
    parser.add_argument("--ca-bundle", default=False, dest="cabundle")
    parser.add_argument(
        "--prefix",
        default="",
        dest="prefix",
        help="use prefix when tagging whole buckets",
    )
    parser.add_argument(
        "--retag",
        action="store_true",
        help="re-write existing tags (useless unless you have a good reason)",
    )
    parser.add_argument("--input", default=False, help="tag files from keylist")
    parser.add_argument(
        "--wholebucket",
        action="store_true",
        help="tag all keys in bucket (or prefix if supplied)",
    )
    parser.add_argument(
        "--key",
        default=None,
        help="just process a single key (shouldn't you be using awscli or something?)",
        required=False,
    )
    parser.add_argument(
        "--cleartags", action="store_true", help="clear tags from objects"
    )
    parser.add_argument("--verbose", action="store_true", help="be noisy")
    parser.add_argument(
        "--maxkeys", default=1000, type=int, help="number of keys to feed per worker"
    )
    parser.add_argument(
        "--workers",
        default=WORKERS,
        help="number of workers to run (default: {0})".format(WORKERS),
    )
    parser.add_argument("--quiet", action="store_true", help="suppress output")
    parser.add_argument(
        "--tagging",
        default=None,
        help="comma-delimited list of key=value pairs to apply",
        required=False,
    )
    parser.add_argument(
        "--append",
        default=None,
        help="comma-delimited list of key=value pairs to append to existing tags (replacing values where keys already exist unless --noreplace is used)",
        required=False,
    )
    parser.add_argument(
        "--noreplace",
        action="store_true",
        help="when using --append, keep the value of existing tags rather than overwritting them",
        required=False
    )
    args = parser.parse_args()

    # No idea why boto can't get this via API
    if args.cabundle:
        os.environ["AWS_CA_BUNDLE"] = args.cabundle

    if args.verbose:
        DEBUG = True

    # Why are you always preparing?
    just_go(args)
