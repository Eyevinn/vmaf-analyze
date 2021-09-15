import os
import json
import subprocess
import argparse
import sys

parser = argparse.ArgumentParser(description="Download all video variants from a manifest.")
parser.add_argument("input", type=str, help="A link to the manifest to download.")
parser.add_argument("output", type=str, help="The folder in which to save the downloaded files.")

args = parser.parse_args()
manifest = args.input
name = args.output

print("Creating directory \"" + name + "\"")

try:
    os.mkdir(name)
except FileExistsError:
    print("Directory \"" + name + "\" already exists.")
    sys.exit(1)

print("Reading from manifest...")
output = subprocess.run(["ffprobe", manifest, "-print_format", "json", "-v", "quiet", "-show_entries", "streams"], text=True, capture_output=True).stdout
data = json.loads(output)
stream_count = len(data["programs"])
print("Found " + str(stream_count) + " variants.")

files = []

for i in range(stream_count):
    filename = name + "/" + name + "_" + str(i) + ".mp4"
    print("Downloading variant " + str(i+1) + "/" + str(stream_count) + "...")
    subprocess.run(["ffmpeg", "-i", manifest, "-map", "0:p:" + str(i) + ":v", "-c", "copy", filename], capture_output=True)
    print("Finished download to " + filename + ".")
    files.append(filename)