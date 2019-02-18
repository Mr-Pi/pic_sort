import os, re
import location_ops, db_ops
from basic_ops import *
from datetime import datetime
from file_ops import sha512sum_file, link_file
from exif_ops import read_exif_data, convert_exif_location_decimal, serialize_exif_data

keyword_map = {
        'by_camera_model': ['Image Model', 'Image Make', 'MakerNote ImageType'],
        'by_author': ['Image Artist', 'MakerNote OwnerName', 'EXIF CameraOwnerName', 'Thumbnail Artist']
        }


def prepare_dest(dest_dir):
    for directory in [ os.path.join(dest_dir, sub_dir) for sub_dir in ['hashed/with_extension', 'by_date', 'hashed/raw', 'by_location/_unknown_'] ]:
        os.makedirs(directory, exist_ok=True)


def hash_file(source, dest_dir):
    basename = os.path.basename(source)
    source = os.path.abspath(source)
    sha512 = sha512sum_file(source)
    extension = os.path.splitext(source)[1]

    if extension == '.gpx':
        location_ops.parse_gpx_file(source)
        return basename, None, None

    return basename, source, sha512


def copy_move_file(entry, dest_dir, move_file):
    source = entry[0]
    sha512 = entry[1]

    basename = os.path.basename(source)
    extension = os.path.splitext(source)[1]

    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)
    hashed_path_extension = os.path.join(dest_dir, 'hashed/with_extension', sha512 + extension)
    if not os.path.exists(hashed_path):
        shutil.copy2(source, hashed_path)
    if not os.path.exists(hashed_path_extension):
        os.symlink(hashed_path, hashed_path_extension)
    if move_file and not dest_dir == source[0:len(dest_dir)]:  # don't remove from destination directory
        os.remove(source)
        try:
            os.rmdir(os.path.split(source)[0])
        except OSError:
            pass
    return basename, sha512, None


def get_meta_data(entry, dest_dir, max_diff):
    source = entry[0]
    sha512 = entry[1]

    basename = os.path.basename(source)
    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)

    meta_data = read_exif_data(hashed_path)
    meta_data = serialize_exif_data(meta_data, ['EXIF', 'GPS', 'Image', 'Thumbnail'])
    if 'GPS GPSLatitudeRef' in meta_data:
        latitude, longitude = convert_exif_location_decimal(meta_data)
        meta_data['latitude'] = latitude
        meta_data['longitude'] = longitude
        meta_data.pop('GPS GPSLatitudeRef')
        meta_data.pop('GPS GPSLatitude')
        meta_data.pop('GPS GPSLongitudeRef')
        meta_data.pop('GPS GPSLongitude')

    set_image_date_str(meta_data, hashed_path)
    if not 'latitude' in meta_data:
        timestamp = datetime.strptime(meta_data['date'], '%Y%m%d_%H%M%S').timestamp()
        latitude, longitude = location_ops.get_gpx_location(timestamp, max_diff)
        if latitude and longitude:
            meta_data['latitude'] = latitude
            meta_data['longitude'] = longitude
    return basename, sha512, meta_data


def create_date_link(entry, dest_dir, db_meta):
    source = entry[0]
    sha512 = entry[1]

    basename = os.path.basename(source)
    extension = os.path.splitext(source)[1]
    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)
    
    date_str = db_ops.get(db_meta, sha512)['date']
    index = 0
    date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    while os.path.exists(date_path):
        if os.stat(date_path).st_ino == os.stat(hashed_path).st_ino:
            break
        index += 1
        date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    link_file(hashed_path, date_path)
    date_basename = os.path.basename(date_path)

    return basename, sha512, date_basename
    

def create_by_link(entry, dest_dir, db_meta, db_hash_datename):
    source = entry[0]
    sha512 = entry[1]

    basename = os.path.basename(source)
    extension = os.path.splitext(source)[1]
    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)

    meta_data = db_ops.get(db_meta, sha512)
    date_basename = db_ops.get(db_hash_datename, sha512)

    for by_tag in keyword_map:
        value = search_tag(meta_data, keyword_map[by_tag])
        value = re.sub('[^0-9A-Za-z]', '_', value)
        path = os.path.join(dest_dir, by_tag, value)
        os.makedirs(path, exist_ok=True)
        path = os.path.join(path, date_basename)
        link_file(hashed_path, path)

    return basename, None, None


def create_by_location(entry, dest_dir, db_meta, db_hash_datename):
    source = entry[0]
    sha512 = entry[1]

    basename = os.path.basename(source)
    extension = os.path.splitext(source)[1]
    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)

    meta_data = db_ops.get(db_meta, sha512)
    date_basename = db_ops.get(db_hash_datename, sha512)

    if 'latitude' not in meta_data:
        path = os.path.join(dest_dir, 'by_location', '_unknown_', date_basename)
        link_file(hashed_path, path)
        return '{} has no location data'.format(basename), None, None

    location_info = location_ops.get_location_info(meta_data['latitude'], meta_data['longitude'])['path']
    location_info.reverse()
    path = os.path.join(dest_dir, 'by_location')
    while len(location_info) > 1:
        path = os.path.join(path, location_info.pop())
        dest_path = os.path.join(path, '_all_')
        os.makedirs(dest_path, exist_ok=True)
        dest_path = os.path.join(dest_path, date_basename)
        link_file(hashed_path, dest_path)
    path = os.path.join(path, location_info.pop())
    os.makedirs(path, exist_ok=True)
    path = os.path.join(path, date_basename)
    link_file(hashed_path, path)

    return '[37;1m{} has location data[0m'.format(basename), None, None



################################################################################
# support functions
################################################################################


def search_tag(meta_data, tags):
    for tag in tags:
        if tag in meta_data:
            return str(meta_data[tag])
    return '_unknown_'


def set_image_date_str(meta_data, source):
    if 'date' in meta_data:
        return
    for date_key in ['Image DateTimeOriginal', 'Image DateTime', 'EXIF DateTimeDigitized']:
        if date_key in meta_data:
            date_str = meta_data[date_key]
            break
    try:
        date_str
    except NameError:
        date_str = datetime.fromtimestamp(os.stat(source).st_mtime)
        date_str = date_str.strftime('%Y%m%d_%H%M%S')
    date_str = str(date_str).replace(':','').replace(' ','_')
    meta_data['date'] = date_str
