#!/usr/bin/env python3
import exifread
import argparse
import pickle

parser = argparse.ArgumentParser()
parser.add_argument('src')
args = parser.parse_args()

with open(args.src, 'rb') as f:
    data = exifread.process_file(f)
    keys = list(data.keys())
    keys.sort()
    for k in keys:
        if type(data[k]) == exifread.classes.IfdTag:
            values = data[k].values
            if type(values) == str:
                print(k, '---', values)
            elif type(values) == list:
                new_vals = []
                for value in values:
                    if type(value) == exifread.utils.Ratio:
                        new_vals.append(value.num/value.den)
                    else:
                        new_vals.append(value)
                print(k, '---', new_vals)
        else:
            print(k, '---', str(data[k])[0:60])
