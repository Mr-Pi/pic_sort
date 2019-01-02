#!/usr/bin/env python3
import argparse
import file_ops
import os

description='''
Search pictures at given paths and sorts them based on there exif data.

use -- to end optional arguments section
'''

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=description)
parser.add_argument('-p', '--paths', type=str, help='search for pictures at the given path', required=True, nargs='+')
parser.add_argument('-e', '--extensions', type=str, help='extensions which should recognized as pictures', nargs='+', default=['jpg', 'cr2'])
parser.add_argument('-m', '--move', help='move all found pictures to destination path (the default is to copy them)', action='store_true')
parser.add_argument('-s', '--symlink', help='create symlinks for all sorted files instead of hardlinks', action='store_true')
parser.add_argument('destination', help='destination path for the sorted picture tree')
args = parser.parse_args()


if __name__ == "__main__":
    print(args)
    if args.move:
        print("Move all files to destination path")
        move_file = True
    else:
        print("Copy all files to destination path")
        move_file = False

    if args.symlink:
        print("Create symlinks to hashed file")
        link_file = os.symlink
    else:
        print("Create hardlinks between destination files")
        link_file = os.link

    file_ops.prepare_dest(args.destination)

    for filename in file_ops.iter_files(args.paths, [ '.' + extension.lower() for extension in args.extensions ]):
        file_ops.handle_file(filename, args.destination, link_file, move_file)
