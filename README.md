# Automate VMAF-analysis in the cloud

To set up on your own AWS:
1. On ECS: Create a cluster and task definition that uses the Docker-container in the `easyvmaf_s3`-directory.
2. On S3: Create a bucket in which you want the transcoded videos and VMAF-scores to be in.
3. Set up a profile. Look at `example_profile.json` for inspiration.
4. Run `python3 vmaf.py` with the profile you created. Check out `python3 vmaf.py --help` for options.
5. The script will upload the reference video to S3, transcode into many different bitrates and resolutions, and run VMAF-analysis on these.
6. The resulting VMAF-files can be found in the S3-bucket under a directory with the same name as the profile name.
7. To get the "optimal" bitrates, download the `*_vmaf.json`-files from S3 and run the `python3 analyze.py` on a directory with the files. See the options on `analyze.py` by running `python3 analyze.py --help`.
