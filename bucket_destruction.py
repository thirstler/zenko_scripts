#!/usr/bin/python
#
# Multi-session clean-up of S3 buckets. Hopefully fast, absolutely bug free.
import os
import boto3
import argparse
import sys
from multiprocessing import Process

##
# Defaults
PROFILE_DEF = "default"
SHADUP = False
LOGSTUFF = True
WORKERS = 5
RETRIES = 5


def just_go(args):
    """
    Ever wonder why some people create wrapper functions with only a couple of
    lines? I don't.
    """
    if args.mpusonly != True:
        zap_objects(args)
    if args.skipmpus != True:
        zap_mpus(args)

    return True


def _run_batch(args, ovs):
    """
    Page worker for object and marker removal
    """
    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    objs = {"Objects": [], "Quiet": False}

    ##
    # Objects and versions
    if not args.skipobjects:
        try:
            for ver in ovs["Versions"]:
                if args.noncurrent and ver["IsLatest"]:
                    logme("skipping {0} ({1}".format(ver["Key"], ver["VersionId"]))
                    continue
                objs["Objects"].append({"Key": ver["Key"], "VersionId": ver["VersionId"]})
                logme("deleting {0} ({1}".format(ver["Key"], ver["VersionId"]))
        except KeyError:
            pass
        except Exception as e:
            sys.stderr.write(str(e))

    ##
    # Markers
    if not args.skipmarkers:
        try:
            for ver in ovs["DeleteMarkers"]:
                objs["Objects"].append(
                    {"Key": ver["Key"], "VersionId": ver["VersionId"]}
                )
                logme("deleting marker {0} ({1}".format(ver["Key"], ver["VersionId"]))
        except KeyError:
            pass
        except Exception as e:
            sys.stderr.write(str(e))

    if len(objs["Objects"]) == 0:
        logme("no versions or markers to delete")
    elif args.dryrun:
        logme("(skipping delete pass)")
    else:
        # Script bails sometimes so we'll do some retries
        for r in range(RETRIES):
            try:
                s3.delete_objects(Bucket=args.bucket, Delete=objs)
            except Exception as e:
                sys.stderr.write(str(e))
                logme("retrying ({0})...".format(r))
                continue
            break


def zap_objects(args):
    """
    Bucket listing and worker distribution entry.
    """
    jobs = []

    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    lspgntr = s3.get_paginator("list_object_versions")
    page_iterator = lspgntr.paginate(Bucket=args.bucket, Prefix=args.prefix, MaxKeys=args.maxkeys)

    wrkrcnt = 0
    for ovs in page_iterator:
        jobs.append(Process(target=_run_batch, args=(args, ovs)))
        jobs[wrkrcnt].start()
        wrkrcnt += 1
        if wrkrcnt >= int(args.workers):
            for job in jobs:
                job.join()
            wrkrcnt = 0
            jobs = []


def zap_mpus(args):
    """
    Clean up any dangling MPUs
    """
    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    lspgntr = s3.get_paginator("list_multipart_uploads")
    page_iterator = lspgntr.paginate(Bucket=args.bucket)

    for mpus in page_iterator:

        if "Uploads" in mpus:
            logme("Stray/unfinished MPUs found, aborting them (single threaded)....")
            for mpu in mpus["Uploads"]:
                logme("deleting {0}".format(mpu["UploadId"]))
                if not args.dryrun:
                    s3.abort_multipart_upload(
                        Bucket=args.bucket, Key=mpu["Key"], UploadId=mpu["UploadId"]
                    )


def logme(text):
    """ I know, right? """
    if LOGSTUFF:
        print(text)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Delete versions, markers and stray MPUs from an S3 a bucket. Not necessarily in that order."
    )
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--profile", default=PROFILE_DEF)
    parser.add_argument("--endpoint", default="https://s3.amazonaws.com")
    parser.add_argument("--ca-bundle", default=False, dest="cabundle")
    parser.add_argument(
        "--prefix", default="", dest="prefix", help="delete at and beyond prefix"
    )
    parser.add_argument(
        "--noncurrent",
        action="store_true",
        help="delete only non-current objects (and markers)",
    )
    parser.add_argument(
        "--skipmarkers", action="store_true", help="skip deletion of delete markers"
    )
    parser.add_argument(
        "--skipmpus", action="store_true", help="skip clean-up of unfinished MPUs"
    )
    parser.add_argument(
        "--mpusonly", action="store_true", help="just clean up unfinished MPUs"
    )
    parser.add_argument(
        "--skipobjects", action="store_true", help="Keep versioned objects when cleaning DeleteMarkers"
    )
    parser.add_argument(
        "--maxkeys", default=1000, type=int, help="Number of keys to fetch per run"
    )
    parser.add_argument(
        "--workers",
        default=WORKERS,
        help="number of workers to run (default: {0})".format(WORKERS),
    )
    parser.add_argument("--quiet", action="store_true", help="supress output")
    parser.add_argument(
        "--dryrun",
        action="store_true",
        help="show objects to be deleted but don't (useless with --quiet)",
    )
    args = parser.parse_args()

    # No idea why boto can't get this via API
    if args.cabundle:
        os.environ["AWS_CA_BUNDLE"] = args.cabundle

    if args.quiet:
        LOGSTUFF = False

    if args.dryrun:
        logme("dry-run, overriding job count (setting to 1)")
        args.workers = 1

    # Why are you always preparing?
    just_go(args)
