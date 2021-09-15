import argparse
import os
import sys
import subprocess
import shutil

parser = argparse.ArgumentParser(description="Encode reference video for VMAF analysis.")
parser.add_argument("filename", type=str, help="The reference file to encode.")
parser.add_argument("--overwrite", action="store_true")
parser.set_defaults(overwrite=False)

args = parser.parse_args()
filename = args.filename
overwrite = args.overwrite

directory = os.path.splitext(filename)[0]

if overwrite and os.path.isdir(directory):
    shutil.rmtree(directory)

try:
    os.mkdir(directory)
except:
    print("Could not create directory \"" + directory + "\".")
    sys.exit(1)

def encode_video(reference, width, height, bitrate, output):
    subprocess.run(["ffmpeg", "-i", reference, "-vf", "scale=" + str(width) + ":" + str(height), "-c:v", "libx264", "-b:v", str(bitrate), "-maxrate", str(bitrate), "-bufsize", str(2*bitrate), "-pass", "2", output])

class Resolution:
    def __init__(self, directory, reference, width, height, initial_bitrate):
        self.directory = directory
        self.reference = reference
        self.width = width
        self.height = height
        self.initial_bitrate = initial_bitrate
    
    def encode_for_bitrate(self, bitrate):
        output_file = directory + "_" + str(self.width) + "x" + str(self.height) + "_" + str(int(bitrate)) + ".mp4"
        encode_video(self.reference, self.width, self.height, bitrate, os.path.join(directory, output_file))

    def encode(self, step, below, above):
        self.encode_for_bitrate(self.initial_bitrate)
        for i in range(1, below+1):
            bitrate = self.initial_bitrate * ((1-step)**i)
            self.encode_for_bitrate(bitrate)
        for i in range(1, above+1):
            bitrate = self.initial_bitrate * ((1+step)**i)
            self.encode_for_bitrate(bitrate)


resolutions = [
    Resolution(directory, filename, 416, 234, 145000),
    Resolution(directory, filename, 640, 360, 365000),
    Resolution(directory, filename, 768, 432, 1100000),
    Resolution(directory, filename, 960, 540, 2000000),
    Resolution(directory, filename, 1280, 720, 4500000),
    Resolution(directory, filename, 1920, 1080, 7800000)
]

for resolution in resolutions:
    resolution.encode(0.2, 4, 4)