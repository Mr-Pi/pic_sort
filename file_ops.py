import os
import hashlib
import exifread
import shutil
import re
import location_ops
from datetime import datetime


def prepare_dest(dest_dir):
    for directory in [ os.path.join(dest_dir, sub_dir) for sub_dir in ['hashed/with_extension', 'by_date', 'hashed/raw', 'by_location/_unknown_'] ]:
        os.makedirs(directory, exist_ok=True)


def iter_files(paths, valid_extensions):
    for path in paths:
        for folder, _, files in os.walk(path):
            for filename in files:
                filename = os.path.join(folder, filename)
                if os.path.splitext(filename)[-1].lower() in valid_extensions:
                    yield(filename)


def sha512sum_file(filename):
    with open(filename, 'rb') as f:
        sha512 = hashlib.sha512()
        for block in iter(lambda: f.read(32768), b''):
            sha512.update(block)
        return sha512.hexdigest()


def link_file(source, destination):
    try:
        os.symlink(os.path.relpath(source, destination)[3:], destination)
    except FileExistsError:
        if os.stat(source).st_ino != os.stat(destination).st_ino:
            os.remove(destination)
            os.symlink(os.path.relpath(source, destination)[3:], destination)
