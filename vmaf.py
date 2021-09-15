import os
import argparse

parser = argparse.ArgumentParser(description="Run easyVMAF on all videos in a directory.")
parser.add_argument("reference", type=str, help="The reference video file.")
parser.add_argument("directory", type=str, help="The folder in which the distorted videos are.")

args = parser.parse_args()
reference = args.reference
directory = args.directory

files = os.listdir(directory)
print("Found " + str(len(files)) + " videos.")

print("Starting VMAF analysis...")
for file in files:
    filename = os.path.join(directory, file)
    if os.path.isfile(filename):
        os.system("python3 ~/Developer/easyVmaf/easyVmaf.py -r " + reference + " -d " + filename + " -endsync")
print("Finished VMAF analysis.")