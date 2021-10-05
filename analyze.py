from scipy.spatial import ConvexHull
import matplotlib.pyplot as plt
import numpy as np
import argparse
import subprocess
import os
import json
import sys
import csv

# Returns the distance between p0 and the line that spans p1 and p2
def distance(p0, p1, p2):
    return np.linalg.norm(np.cross(p2-p1, p1-p0))/np.linalg.norm(p2-p1)

def bitrate_from_filename(path):
    filename = os.path.splitext(os.path.basename(path))[0]
    data = filename.split("_")[1]
    return int(data)

def resolution_from_filename(path):
    filename = os.path.splitext(os.path.basename(path))[0]
    data = filename.split("_")[0].split("x")
    return (int(data[0]), int(data[1]))

parser = argparse.ArgumentParser(description="Analyze VMAF scores.")
parser.add_argument("directories", type=str, nargs='+', help="A list of directories with VMAF scores.")
parser.add_argument("--plot", action='store_true', dest="should_plot", help="Whether or not to display a plot with VMAF scores.")
parser.add_argument("--export-csv", type=str, help="Export the best bitrates as CSV to this file.", dest="csv_export")
parser.add_argument("--export-csv-raw", type=str, help="Export all data to this CSV-file.", dest="csv_export_raw")
parser.add_argument("--ignore-resolutions", type=str, help="List of all resolutions to ignore.")
parser.set_defaults(should_plot=False)

args = parser.parse_args()
directories = args.directories
should_plot = args.should_plot
csv_export = args.csv_export
csv_export_raw = args.csv_export_raw
ignore_resolutions_str = args.ignore_resolutions

ignore_resolutions = []
if ignore_resolutions:
    for resolution_str in ignore_resolutions_str.split(","):
        parts = resolution_str.split("x")
        if len(parts) != 2 or any(not part.isdigit() for part in parts):
            print("Unable to parse resolutions. Resolutions should be in format WIDTHxHEIGHT. Example: \"1920x1080\"")
            sys.exit(1)

        width = int(parts[0])
        height = int(parts[1])
        ignore_resolutions.append((width, height))

vmaf_for_resolution = {}
i = 1
for directory in directories:
    files = os.listdir(directory)
    k = 1
    print("Loading " + str(len(files)) + " files from directory " + str(i) + "/" + str(len(directories)) + "...")
    for file in files:
        filename = os.path.join(directory, file)
        if os.path.isfile(filename):
            extension = os.path.splitext(filename)[1]
            if extension == ".json":
                bitrate = bitrate_from_filename(filename)
                width, height = resolution_from_filename(filename)
                resolution = str(width) + "x" + str(height)

                if (width, height) in ignore_resolutions:
                    continue

                try:
                    with open(filename) as f:
                        vmaf_data = json.load(f)
                        vmaf = vmaf_data["pooled_metrics"]["vmaf"]["harmonic_mean"]

                        if resolution in vmaf_for_resolution:
                            vmaf_for_resolution[resolution][bitrate] = vmaf
                        else:
                            vmaf_for_resolution[resolution] = {bitrate: vmaf}
                except:
                    print("Unable to load VMAF scores from " + filename + ".")
                    sys.exit(1)
        print("Directory " + str(i) + ": Processed file " + str(k) + "/" + str(len(files)))
        k += 1
    i += 1

points = []
points_for_resolution = {}
for resolution, vmaf_for_bitrate in vmaf_for_resolution.items():
    bitrates = list(vmaf_for_bitrate.keys())
    vmafs = list(vmaf_for_bitrate.values())
    sorted_vmaf_by_bitrate = [vmaf for bitrate, vmaf in sorted(zip(bitrates, vmafs))]
    plt.plot(sorted(bitrates), sorted_vmaf_by_bitrate, 'o-', label=resolution)
    for bitrate, vmaf in vmaf_for_bitrate.items():
        point = [bitrate, vmaf]
        points.append(point)
        if resolution in points_for_resolution:
            points_for_resolution[resolution].append(point)
        else:
            points_for_resolution[resolution] = [point]

points = np.asarray(points)
hull = ConvexHull(points)

optimal_bitrate_for_resolution = {}

for resolution, current_points in points_for_resolution.items():
    distances = []
    for point in current_points:
        for simplex in hull.simplices:
            d = distance(point, points[simplex][0], points[simplex][1])
            # Add tuples of (distance, bitrate, vmaf)
            distances.append((d, point[0], point[1]))
    
    # Remove duplicates
    distances = list(dict.fromkeys(distances))
    # Sort by distance
    distances.sort(key=lambda val: val[0])

    best = distances[0]
    second_best = distances[1]

    optimal_bitrate_for_resolution[resolution] = [(bitrate, vmaf) for distance, bitrate, vmaf in distances]
    plt.plot(best[1], best[2], 'kx')
    # plt.plot(second_best[1], second_best[2], 'wx')

# for simplex in hull.simplices:
#     plt.plot(points[simplex, 0], points[simplex, 1], 'k-')

print("Finished processing.")

if should_plot:
    print("Showing plot.")
    plt.title("VMAF/Bitrate")
    plt.ylabel("VMAF")
    plt.xlabel("Bitrate")
    plt.legend(loc="lower right")
    plt.ylim(0, 100)
    plt.show()

print("--------")
print("Optimal bitrates:")
for resolution, optimal_bitrate in optimal_bitrate_for_resolution.items():
    print(resolution + ": " + str(optimal_bitrate[0][0]) + " bits/second")
print("--------")

if csv_export:
    with open(csv_export, 'w') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(["Resolution", "Optimal bit rate", "Second best bit rate", "Third best bit rate", "Fourth best bit rate", "Fifth best bit rate"])
        for resolution, optimal_bitrate in optimal_bitrate_for_resolution.items():
            csv_writer.writerow([resolution, optimal_bitrate[0][0], optimal_bitrate[1][0], optimal_bitrate[2][0], optimal_bitrate[3][0], optimal_bitrate[4][0]])
    print("Exported results to \"" + csv_export + "\"")

if csv_export_raw:
    with open(csv_export_raw, 'w') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(["Resolution", "Bit rate", "VMAF"])
        for resolution, vmaf_for_bitrate in vmaf_for_resolution.items():
            for bitrate, vmaf in vmaf_for_bitrate.items():
                csv_writer.writerow([resolution, bitrate, vmaf])
    print("Exported raw data to \"" + csv_export_raw + "\"")