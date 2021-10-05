import argparse
import sys
import json
import boto3
import os
import time

parser = argparse.ArgumentParser(description='Automatically generate VMAF-scores for a variety of transcoded variants.')

parser.add_argument("profile", type=str, help="A json-file which contains the configuration for this run.")
parser.add_argument("--skip-reference-upload", action="store_true", default=False, help="Do not upload reference to S3. This is useful if the file is already there.")
parser.add_argument("--skip-transcoding", action="store_true", default=False, help="Skip transcoding of variants. This is useful if this step has been done before.")
parser.add_argument("--skip-vmaf", action="store_true", default=False, help="Skip VMAF-analysis of variants. This is useful if VMAF-analysis has already been conducted.")
parser.add_argument("--dryrun", action="store_true", default=False, help="Do not do anything. Only print what we would have done.")
args = parser.parse_args()

# Verify profile
with open(args.profile) as json_file:
    profile = json.load(json_file)
    required_fields = ["resolutions", "reference", "aws", "name", "encodeSettings"]
    if not all(field in profile for field in required_fields):
        print("Profile is missing required fields.")
        sys.exit(1)

    required_aws_fields = ["s3Bucket", "mediaConvertEndpoint", "mediaConvertRole", "ecsSubnet", "ecsSecurityGroup", "ecsCluster", "ecsTaskDefinition"]
    if not all(field in profile["aws"] for field in required_aws_fields):
        print("Profile is missing required fields from AWS.")
        sys.exit(1)

# Parse resolutions
resolutions = []
for resolution_str in profile["resolutions"]:
    parts = resolution_str.split("x")
    if len(parts) != 2 or any(not part.isdigit() for part in parts):
        print("Unable to parse resolutions. Resolutions should be in format WIDTHxHEIGHT. Example: \"1920x1080\"")
        sys.exit(1)

    width = int(parts[0])
    height = int(parts[1])
    
    resolutions.append((width, height))

profile_name = profile["name"]
bucket = profile["aws"]["s3Bucket"]
reference_file = profile["reference"]
media_convert_endpoint = profile["aws"]["mediaConvertEndpoint"]
media_convert_role = profile["aws"]["mediaConvertRole"]
ecs_subnet = profile["aws"]["ecsSubnet"]
ecs_security_group = profile["aws"]["ecsSecurityGroup"]
ecs_cluster = profile["aws"]["ecsCluster"]
ecs_task_definition = profile["aws"]["ecsTaskDefinition"]

s3 = boto3.client("s3")
mediaconvert = boto3.client("mediaconvert", endpoint_url=media_convert_endpoint)
ecs = boto3.client("ecs")
session = boto3.Session()
aws_credentials = session.get_credentials()

# Upload reference to s3
reference = bucket + "/" + profile_name + "/reference.mp4"

if not args.skip_reference_upload:
    print("Uploading reference to " + reference + "...")

    if not args.dryrun:
        s3.upload_file(reference_file, bucket[5:], profile_name + "/" + "reference.mp4")

    print("Finished uploading.")

# Encode variants for each resolution using MediaConvert
variants = []
for resolution in resolutions:
    w = resolution[0]
    h = resolution[1]

    bitrate_floor = int((w*h)/2)
    bitrate_ceil = int((w*h)/0.1)
    bitrate_step = int((w*h)/1)

    for bitrate in range(bitrate_floor, bitrate_ceil, bitrate_step):
        output = str(w) + "x" + str(h) + "_" + str(bitrate)

        output_file = bucket + "/" + profile_name + "/distorted/" + output

        settings_str = json.dumps(profile["encodeSettings"])
        settings_str = settings_str.replace("$INPUT", reference)
        settings_str = settings_str.replace("$OUTPUT", output_file)
        settings_str = settings_str.replace("$NAME", profile_name)
        settings_str = settings_str.replace("\"$WIDTH\"", str(w))
        settings_str = settings_str.replace("\"$HEIGHT\"", str(h))
        settings_str = settings_str.replace("\"$BITRATE\"", str(bitrate))

        settings = json.loads(settings_str)

        if not args.skip_transcoding:
            print("Starting transcoding for " + output + "...")

            if args.dryrun:
                print("Transcoding " + reference + " to destination " + output_file + ".mp4")
            else:
                job = mediaconvert.create_job(
                    Role=media_convert_role,
                    Settings=settings,
                )
        
        variants.append(output_file)

if not args.skip_transcoding:
    print("Waiting for transcoding to be finished...")

while len(variants) > 0:
    res = s3.list_objects_v2(Bucket=bucket[5:], Prefix=profile_name + "/distorted/")
    if "Contents" in res:
        objects_in_bucket = list(map(lambda o: str(o["Key"]), res["Contents"]))
    else:
        objects_in_bucket = []

    for variant in variants:
        object = variant.replace(bucket + "/", "") + ".mp4"
        if object in objects_in_bucket or args.dryrun:
            distorted = variant + ".mp4"
            vmaf_output = variant + "_vmaf.json"
            print(distorted + " is finished transcoding.")

            variants.remove(variant)

            credentials = aws_credentials.get_frozen_credentials()
            access_key = credentials.access_key
            secret_key = credentials.secret_key

            print("Running VMAF on " + os.path.basename(variant) + ". Outputting VMAF to " + vmaf_output)
            if not args.dryrun:
                ecs.run_task(
                    taskDefinition="easyvmaf-s3:1",
                    cluster="vmaf-runner",
                    launchType="FARGATE",
                    networkConfiguration={
                        'awsvpcConfiguration': {
                            'subnets': [
                                ecs_subnet,
                            ],
                            'securityGroups': [
                                ecs_security_group,
                            ],
                            'assignPublicIp': 'ENABLED'
                        }
                    },
                    overrides={
                        'containerOverrides': [
                            {
                                'name': 'easyvmaf-s3',
                                'command': [
                                    "-r",
                                    reference,
                                    "-d",
                                    distorted,
                                    "-o",
                                    vmaf_output
                                ],
                                'environment': [
                                    {
                                        'name': 'AWS_ACCESS_KEY_ID',
                                        'value': access_key
                                    },
                                    {
                                        'name': 'AWS_SECRET_ACCESS_KEY',
                                        'value': secret_key
                                    }
                                ]
                            },
                        ],
                    }
                )
    
    if len(variants) > 0:
        time.sleep(5)