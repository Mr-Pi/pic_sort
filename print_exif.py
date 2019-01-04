#!/usr/bin/env python3
import exifread
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('src')
args = parser.parse_args()

with open(args.src, 'rb') as f:
    data = exifread.process_file(f)
    keys = list(data.keys())
    keys.sort()
    for k in keys:
        print(k, '---', str(data[k])[0:60])
