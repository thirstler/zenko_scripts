#!/usr/bin/python3
# Command-line search tool that uses the Zenko metadata search API. Search your
# buckets with Python the way God intended. No boutique imports.
import sys, os, base64, hashlib, urllib, hmac, argparse, requests, configparser, boto3, json
import xml.dom.minidom as MD
from datetime import datetime
from boto3.s3.transfer import TransferConfig


def get_profile(profile):
    """
    Just open the ~/.aws/credentials file and get the creds, this is
    easier than digging from boto
    """
    config = configparser.ConfigParser()
    config.read("{0}/.aws/credentials".format(os.environ["HOME"]))

    if (
        "aws_access_key_id" not in config[profile]
        or "aws_secret_access_key" not in config[profile]
    ):
        # Make sure we have credentials
        access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        if access_key is None or secret_key is None:
            print("No access key is available.")
            sys.exit()
    else:
        access_key = config[profile]["aws_access_key_id"]
        secret_key = config[profile]["aws_secret_access_key"]

    return {"access_key": access_key, "secret_key": secret_key}


def parse_endpoint(endpointstr):
    """ divied endpoint into useable parts """
    proto = endpointstr[: endpointstr.find("//") - 1]

    hostport = endpointstr[(endpointstr.find("//") + 2) :]
    if hostport.find(":") > 0:
        host = hostport[: hostport.find(":")]
        port = hostport[(hostport.find(":") + 1) :]
    else:
        host = hostport
        port = None

    return {"hostport": hostport, "proto": proto, "port": port, "host": host}


##
#  Ripped right out of the AWS code examples
def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


##
# Ripped right out of the AWS code examples
def getSignatureKey(key, dateStamp, regionName, serviceName):
    kDate = sign(("AWS4" + key).encode("utf-8"), dateStamp)
    kRegion = sign(kDate, regionName)
    kService = sign(kRegion, serviceName)
    kSigning = sign(kService, "aws4_request")
    return kSigning


def bucket_location(args):
    """
    Get bucket location so we can query it, we load-up boto3 just for this. :-)
    """
    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)
    response = s3.get_bucket_location(Bucket=args.bucket)
    return response


def location_noboto():
    pass


# God forgive me for the sheer number of positional arguments
def get_signed_headers(
    service,
    method,
    canonical_uri,
    canonical_querystring,
    host,
    region,
    access_key,
    secret_key,
    put_data="",
):
    """
    v4 signing process is documented here:
    https://docs.aws.amazon.com/AmazonS3/latest/API/sig-v4-authenticating-requests.html

    This function will likely only work for S3 GET requests so don't try to use
    it for anything else.

    Params:
        method: GET/PUT/POST/HEAD
        canonical_uri: everything between the query and the host, don't forget
            the leading '/' (e.g. /mybucket)
        canonical_querystring: ordered (by key) list of query items
        host: endpoint host, remember to include the port if using a non-
            standard port for http/https
        region: aws region you're accessing
        access_key/secret_key: you know
        put_data: if there's a payload, put it here. It needs to be signed.
    """

    if put_data == None:
        signed_headers = "host;x-amz-date"
    else:
        signed_headers = "host;x-amz-content-sha256;x-amz-date"

    # We're at now now (Q: when will then be now? A: soon):
    t = datetime.utcnow()
    amzdate = t.strftime("%Y%m%dT%H%M%SZ")
    datestamp = t.strftime("%Y%m%d")
    algorithm = "AWS4-HMAC-SHA256"
    payload_hash = hashlib.sha256((put_data).encode("utf-8")).hexdigest()
    canonical_headers = "host:{0}\nx-amz-content-sha256:{1}\nx-amz-date:{2}\n".format(
        host, payload_hash, amzdate
    )
    canonical_request = "{0}\n{1}\n{2}\n{3}\n{4}\n{5}".format(
        method,
        canonical_uri,
        canonical_querystring,
        canonical_headers,
        signed_headers,
        payload_hash,
    )
    credential_scope = "{0}/{1}/{2}/aws4_request".format(datestamp, region, service)
    string_to_sign = "{0}\n{1}\n{2}\n{3}".format(
        algorithm,
        amzdate,
        credential_scope,
        hashlib.sha256(canonical_request.encode("utf-8")).hexdigest(),
    )
    signing_key = getSignatureKey(secret_key, datestamp, region, service)
    signature = hmac.new(
        signing_key, (string_to_sign).encode("utf-8"), hashlib.sha256
    ).hexdigest()
    authorization_header = "{0} Credential={1}/{2}, SignedHeaders={3}, Signature={4}".format(
        algorithm, access_key, credential_scope, signed_headers, signature
    )
    return {
        "x-amz-date": amzdate,
        "x-amz-content-sha256": payload_hash,
        "Authorization": authorization_header,
    }


def print_xml(xmltxt):
    """ Print pertty XML """
    parsed = MD.parseString(xmltxt)
    print(parsed.toprettyxml(indent="    "))


def get_json(xmltxt):
    """
    Parsing the DOM is stupid, so let's do that only once here.
    """
    xmlout = MD.parseString(xmltxt)
    output = {
        "MaxKeys": int(xmlout.getElementsByTagName("MaxKeys")[0].firstChild.nodeValue),
        "Name": xmlout.getElementsByTagName("Name")[0].firstChild.nodeValue,
        "IsTruncated": xmlout.getElementsByTagName("IsTruncated")[
            0
        ].firstChild.nodeValue,
        "Contents": [],
    }
    for node in xmlout.getElementsByTagName("Contents"):
        output["Contents"].append(
            {
                "Key": node.getElementsByTagName("Key")[0].firstChild.nodeValue,
                "LastModified": node.getElementsByTagName("LastModified")[
                    0
                ].firstChild.nodeValue,
                "Size": int(node.getElementsByTagName("Size")[0].firstChild.nodeValue),
                "ETag": node.getElementsByTagName("ETag")[0].firstChild.nodeValue,
                "StorageClass": node.getElementsByTagName("StorageClass")[
                    0
                ].firstChild.nodeValue,
                "Owner": {
                    "ID": node.getElementsByTagName("ID")[0].firstChild.nodeValue,
                    "DisplayName": node.getElementsByTagName("DisplayName")[
                        0
                    ].firstChild.nodeValue,
                },
            }
        )
    return output


def print_csv(objdata):
    print("Name,MaxKeys,IsTruncated")
    print(
        "{0},{1},{2}".format(
            objdata["Name"], objdata["MaxKeys"], objdata["IsTruncated"]
        )
    )
    print("")
    print("Owner ID,Owner DisplayName,ETag,StorageClass,LastModified,Size,Key")
    for item in objdata["Contents"]:
        print(
            "{0},{1},{2},{3},{4},{5},{6}".format(
                item["Owner"]["ID"],
                item["Owner"]["DisplayName"],
                item["ETag"],
                item["StorageClass"],
                item["LastModified"],
                item["Size"],
                item["Key"],
            )
        )


def just_the_keys_please(objdata):
    """ Sometimes you just want the list of keys """
    for item in objdata["Contents"]:
        print(item["Key"])


def canonical_query_me(keyvalues):
    if len(keyvalues) == 0:
        return ""
    query_str = ""
    for key in sorted(keyvalues.keys()):
        query_str = "{0}&{1}".format(
            query_str,
            "{0}={1}".format(
                key, urllib.parse.quote_plus(keyvalues[key]).replace("+", "%20")
            ),
        )
    return query_str[1:]


def show_error(xmltext):
    xmlout = MD.parseString(xmltext)
    codemsg = xmlout.getElementsByTagName("Code")[0].firstChild.nodeValue
    errmsg = xmlout.getElementsByTagName("Message")[0].firstChild.nodeValue
    sys.stderr.write("{0} - {1}\n".format(codemsg, errmsg))


def get_objects(result_json, args):
    """
    Get objects listed in JSON output. Yeah, I get it, it's just as easy to
    pipe key output to something but... shut up.
    """
    session = boto3.Session(profile_name=args.profile)
    s3 = session.client("s3", endpoint_url=args.endpoint)

    for item in result_json["Contents"]:
        if args.basename:
            destpath = os.path.basename(item["Key"])
        else:
            destpath = item["Key"]
            mkme = item["Key"][: item["Key"].rfind("/")]
            os.makedirs("{0}/{1}".format(args.path, mkme), exist_ok=True)
        s3.download_file(
            args.bucket, item["Key"], "{0}/{1}".format(args.path, destpath)
        )
        print(item["Key"])


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Search a bucket. Go ahead. Try it.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument(
        "--profile", default="default", help="boto3 profile name to use for credentials"
    )
    parser.add_argument(
        "--endpoint", default="https://s3.amazonaws.com", help="zenko endpoint URL"
    )
    parser.add_argument("--ca-bundle", default=False, dest="cabundle")
    parser.add_argument(
        "--query", default="", help="Zenko md search query (e.g. tags.color=green)"
    )
    parser.add_argument(
        "--output",
        default="keys",
        help="one of: raw, xml, json, csv or keys (for bare keylist)",
    )
    parser.add_argument(
        "--download",
        default=False,
        dest="path",
        help="get objects returned by the search, download to PATH",
    )
    parser.add_argument(
        "--basename",
        action="store_true",
        help="when downloading objects with prefixes, use only the basename of the key as the destination file name; collisions unhandled",
    )
    args = parser.parse_args()

    # CA bundles are only configurable via environment
    if args.cabundle:
        os.environ["AWS_CA_BUNDLE"] = args.cabundle
        os.environ["REQUESTS_CA_BUNDLE"] = args.cabundle

    location_info = bucket_location(args)

    if "LocationConstraint" not in location_info:
        sys.stderr.write("can't get location info; does the bucket exist?\n")
        sys.exit(1)

    region = location_info["LocationConstraint"]
    if region == None:
        region = "us-east-1"

    creds = get_profile(args.profile)
    epdata = parse_endpoint(args.endpoint)
    query_items = {"search": args.query, "max-keys": "2000"}
    marker = ""
    isTruncated = True  # Let's get this party started
    while isTruncated == True:
        if marker != "":
            query_items["marker"] = marker

        canonical_querystring = canonical_query_me(query_items)

        # Set up the headers complete with signature
        headers = get_signed_headers(
            "s3",
            "GET",
            "/{0}".format(args.bucket),
            canonical_querystring,
            epdata["hostport"],
            region,
            creds["access_key"],
            creds["secret_key"],
        )

        request_url = "{0}/{1}?{2}".format(
            args.endpoint, args.bucket, canonical_querystring
        )

        # Moment of truth
        result = requests.get(request_url, headers=headers)

        if result.status_code >= 400:
            show_error(result.text)
            sys.exit(1)

        try:
            result_json = get_json(result.text)
        except Exception as e:
            sys.stderr.write("{0}\n".format(e))
            sys.exit(1)

        if result_json["IsTruncated"] == "true":
            isTruncated = True
            marker = result_json["Contents"][-1]["Key"]
        else:
            isTruncated = False

        # Various output formats. Kind of only care about JSON. This does not
        # compile pages into a single object for XML and JSON output.
        if args.path:
            get_objects(result_json, args)
        elif args.output == "xml":
            print_xml(result.text)
        elif args.output == "json":
            print(json.dumps(result_json))
        elif args.output == "csv":
            print_csv(result_json)
        elif args.output == "keys":
            just_the_keys_please(result_json)
        else:
            print(result.text)
