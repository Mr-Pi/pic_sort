import os
import hashlib
import exifread
import shutil
from datetime import datetime

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

def prepare_dest(dest_dir):
    for directory in [ os.path.join(dest_dir, sub_dir) for sub_dir in ['hashed/with_extension', 'by_date', 'by_tags'] ]:
        try:
            shutil.rmtree(directory)
        except FileNotFoundError:
            pass
    for directory in [ os.path.join(dest_dir, sub_dir) for sub_dir in ['hashed/with_extension', 'by_date', 'by_tags', 'hashed/raw'] ]:
        try:
            os.makedirs(directory)
        except FileExistsError:
            pass

def get_image_date_str(source):
    with open(source, 'rb') as f:
        exif_data = exifread.process_file(f)
    for date_key in ['Image DateTimeOriginal', 'Image DateTime']:
        if date_key in exif_data:
            date_str = exif_data[date_key]
            break
    try:
        date_str
    except NameError:
        date_str = datetime.fromtimestamp(os.stat(source).st_mtime)
        date_str = date_str.strftime('%Y%m%d_%H%M%S')
    date_str = str(date_str).replace(':','').replace(' ','_')
    return date_str

def get_unique_date_path(dest_dir, hashed_path, extension, date_str):
    index = 0
    date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    while os.path.exists(date_path):
        if os.stat(date_path).st_ino == os.stat(hashed_path).st_ino:
            break
        index += 1
        date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    return date_path

def handle_file_copy_move(source, dest_dir, move_file):
    source = os.path.abspath(source)
    dest_dir = os.path.abspath(dest_dir)
    sha512 = sha512sum_file(source)

    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)
    if not os.path.exists(hashed_path):
        shutil.copy2(source, hashed_path)

    if move_file and not dest_dir == source[0:len(dest_dir)]:
        os.remove(source)

    return sha512

def create_links(dest_dir, sha512, extension, basename, link_file):
    hashed_path = os.path.abspath( os.path.join(dest_dir, 'hashed/raw', sha512) )
    hashed_ext_path = os.path.abspath( os.path.join(dest_dir, 'hashed/with_extension', sha512) + extension )
    if os.path.exists(hashed_ext_path):
        return
    link_file(hashed_path, hashed_ext_path)

    date_str = get_image_date_str(hashed_path)
    date_path = get_unique_date_path(dest_dir, hashed_path, extension, date_str)
    if not os.path.exists(date_path):
        link_file(hashed_ext_path, date_path)
