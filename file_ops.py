import os
import hashlib
import exifread
import shutil
import re
import location_ops
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
    for directory in [ os.path.join(dest_dir, sub_dir) for sub_dir in ['hashed/with_extension', 'by_date', 'hashed/raw', 'hashed/original_name'] ]:
        os.makedirs(directory, exist_ok=True)


def get_image_exif_data(source):
    with open(source, 'rb') as f:
        exif_data = exifread.process_file(f)
    return exif_data


def get_image_date_str(source, exif_data):
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


def create_by_link(dest_dir, exif_data, date_path_basename, by_type, hashed_path, search_list):
    for key in search_list:
        if key in exif_data:
            value = str(exif_data[key])
            break
    try:
        value
    except NameError:
        value = '_unknown_'

    value = re.sub('[^0-9A-Za-z]', '_', value)
    path = os.path.join(dest_dir, by_type, value)
    os.makedirs(path, exist_ok=True)
    path = os.path.join(path, date_path_basename)
    if os.path.exists(path):
        os.remove(path)
    os.symlink(hashed_path, path)


def create_geolocation_links(dest_dir, exif_data, date_path_basename, hashed_path):
    if 'GPS GPSLatitude' in exif_data:
        location_info = location_ops.get_location_info(
                str(exif_data['GPS GPSLatitudeRef']),
                exif_data['GPS GPSLatitude'].values[0].num / exif_data['GPS GPSLatitude'].values[0].den,
                exif_data['GPS GPSLatitude'].values[1].num / exif_data['GPS GPSLatitude'].values[1].den,
                exif_data['GPS GPSLatitude'].values[2].num / exif_data['GPS GPSLatitude'].values[2].den,
                str(exif_data['GPS GPSLongitudeRef']),
                exif_data['GPS GPSLongitude'].values[0].num / exif_data['GPS GPSLongitude'].values[0].den,
                exif_data['GPS GPSLongitude'].values[1].num / exif_data['GPS GPSLongitude'].values[1].den,
                exif_data['GPS GPSLongitude'].values[2].num / exif_data['GPS GPSLongitude'].values[2].den)['path']
    else:
        location_info = ['_unknown_']
        latitude, longitude = location_ops.get_gpx_location(
                datetime.strptime(date_path_basename[0:15], '%Y%m%d_%H%M%S').timestamp(), 120)
        if latitude and longitude:
            location_info = location_ops.get_location_info(latitude, longitude)['path']
    location_info.reverse()
    path = os.path.join(dest_dir, 'by_location')
    while len(location_info) > 1:
        path = os.path.join(path, location_info.pop())
        dest_path = os.path.join(path, '_all_')
        os.makedirs(dest_path, exist_ok=True)
        dest_path = os.path.join(dest_path, date_path_basename)
        if os.path.exists(dest_path):
            os.remove(dest_path)
        os.symlink(hashed_path, dest_path)
    path = os.path.join(path, location_info.pop())
    os.makedirs(path, exist_ok=True)
    path = os.path.join(path, date_path_basename)
    if os.path.exists(path):
        os.remove(path)
    os.symlink(hashed_path, path)


def create_links(dest_dir, sha512, extension, basename, update):
    hashed_path = os.path.abspath( os.path.join(dest_dir, 'hashed/raw', sha512) )
    hashed_ext_path = os.path.abspath( os.path.join(dest_dir, 'hashed/with_extension', sha512) + extension )
    original_name_path = '{}__{}{}'.format(
            os.path.abspath( os.path.join(dest_dir, 'hashed/original_name', os.path.splitext(basename)[0]) ), sha512, extension )
    if os.path.exists(hashed_ext_path) and not update:
        return
    if not os.path.exists(hashed_ext_path):
        os.symlink(hashed_path, hashed_ext_path)
    if not os.path.exists(original_name_path):
        os.symlink(hashed_path, original_name_path)

    exif_data = get_image_exif_data(hashed_path)

    date_str = get_image_date_str(hashed_path, exif_data)
    date_path = get_unique_date_path(dest_dir, hashed_path, extension, date_str)
    date_path_basename = os.path.basename(date_path)
    if os.path.exists(date_path):
        os.remove(date_path)
    os.symlink(hashed_path, date_path)

    create_by_link(dest_dir, exif_data, date_path_basename, 'by_camera_model', hashed_path,
            ['Image Model', 'Image Make', 'MakerNote ImageType'])
    create_by_link(dest_dir, exif_data, date_path_basename, 'by_author', hashed_path,
            ['Image Artist', 'MakerNote OwnerName', 'EXIF CameraOwnerName'])
    create_geolocation_links(dest_dir, exif_data, date_path_basename, hashed_path)
