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


def read_copy_move_sha512(source, dest_dir, move_file):
    extension = os.path.splitext(source)[1]
    if extension == '.gpx':
        location_ops.parse_gpx_file(source)
        return basename, None
    basename = os.path.basename(source)
    source = os.path.abspath(source)
    dest_dir = os.path.abspath(dest_dir)
    sha512 = sha512sum_file(source)
    hashed_path = os.path.join(dest_dir, 'hashed/raw', sha512)
    hashed_path_extension = os.path.join(dest_dir, 'hashed/with_extension', sha512 + extension)
    if not os.path.exists(hashed_path):
        shutil.copy2(source, hashed_path)
    if not os.path.exists(hashed_path_extension):
        os.symlink(source, hashed_path_extension)
    if move_file and not dest_dir == source[0:len(dest_dir)]:  # don't remove from destination directory
        os.remove(source)

    return basename, [basename, {
        'sha512': sha512, 'source': source, 'hashed_path': hashed_path,
        'extension': extension
        }]


def get_image_exif_data(source):
    with open(source, 'rb') as f:
        exif_data = exifread.process_file(f)
    return exif_data


def get_image_date_str(source, meta_data):
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
    return date_str


def serialize_exif_data(db_entry, keywords, max_diff):
    hashed_path = db_entry[1]['hashed_path']
    exif_data = get_image_exif_data(hashed_path)
    if 'exif_data' in db_entry[1]:
        return db_entry[0], db_entry

    db_entry[1]['meta_data'] = {}
    for key in exif_data:
        for keyword in keywords:
            if key[0:len(keyword)] == keyword:
                if keyword == 'GPS':
                    if key == 'GPS GPSLatitudeRef':
                        latitude, longitude = location_ops.convert_to_decimal(
                                str(exif_data['GPS GPSLatitudeRef']),
                                exif_data['GPS GPSLatitude'].values[0].num / exif_data['GPS GPSLatitude'].values[0].den,
                                exif_data['GPS GPSLatitude'].values[1].num / exif_data['GPS GPSLatitude'].values[1].den,
                                exif_data['GPS GPSLatitude'].values[2].num / exif_data['GPS GPSLatitude'].values[2].den,
                                str(exif_data['GPS GPSLongitudeRef']),
                                exif_data['GPS GPSLongitude'].values[0].num / exif_data['GPS GPSLongitude'].values[0].den,
                                exif_data['GPS GPSLongitude'].values[1].num / exif_data['GPS GPSLongitude'].values[1].den,
                                exif_data['GPS GPSLongitude'].values[2].num / exif_data['GPS GPSLongitude'].values[2].den)
                        db_entry[1]['meta_data']['latitude'] = latitude
                        db_entry[1]['meta_data']['longitude'] = longitude
                elif type(exif_data[key]) == exifread.classes.IfdTag:
                    values = exif_data[key].values
                    if type(values) == list:
                        new_values = []
                        for value in values:
                            if type(value) == exifread.utils.Ratio:
                                if value.num == 0:
                                    new_values.append(0)
                                else:
                                    new_values.append(value.num/value.den)
                            else:
                                new_values.append(value)
                        values = new_values
                    db_entry[1]['meta_data'][key] = values
                else:
                    db_entry[1]['meta_data'][key] = exif_data[key]
    db_entry[1]['meta_data']['date'] = get_image_date_str(hashed_path, db_entry[1]['meta_data'])
    if not 'latitude' in db_entry[1]['meta_data']:
        timestamp = datetime.strptime(db_entry[1]['meta_data']['date'], '%Y%m%d_%H%M%S').timestamp()
        latitude, longitude = location_ops.get_gpx_location(timestamp, max_diff)
        if latitude and longitude:
            db_entry[1]['meta_data']['latitude'] = latitude
            db_entry[1]['meta_data']['longitude'] = longitude
    return db_entry[0], db_entry


def link_file(source, destination):
    try:
        os.symlink(source, destination)
    except FileExistsError:
        if os.stat(source).st_ino != os.stat(destination).st_ino:
            os.remove(destination)
            os.symlink(source, destination)


def create_links_date(db_entry, dest_dir):
    hashed_path = db_entry[1]['hashed_path']
    meta_data = db_entry[1]['meta_data']
    extension = db_entry[1]['extension']
    date_str = get_image_date_str(hashed_path, meta_data)

    index = 0
    date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    while os.path.exists(date_path):
        if os.stat(date_path).st_ino == os.stat(hashed_path).st_ino:
            break
        index += 1
        date_path = '{}_{:03}{}'.format(os.path.join(dest_dir, 'by_date', date_str), index, extension)
    link_file(hashed_path, date_path)
    db_entry[1]['date_basename'] = os.path.basename(date_path)
    return db_entry[0], db_entry


def create_links_geolocation(db_entry, dest_dir):
    hashed_path = db_entry[1]['hashed_path']
    if 'latitude' not in db_entry[1]['meta_data'] or 'longitude' not in db_entry[1]['meta_data']:
        path = os.path.join(dest_dir, 'by_location', '_unknown_', db_entry[0])
        link_file(hashed_path, path)
        return '{} has no geolocation data'.format(db_entry[0]), db_entry

    latitude = db_entry[1]['meta_data']['latitude']
    longitude = db_entry[1]['meta_data']['longitude']
    date_basename = db_entry[1]['date_basename']
    location_info = location_ops.get_location_info(latitude, longitude)['path']
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
    return '{} has geolocation info'.format(date_basename), db_entry


def create_by_link(dest_dir, meta_data, date_path_basename, hashed_path, by_type, search_list):
    for key in search_list:
        if key in meta_data:
            value = str(meta_data[key])
            break
    try:
        value
    except NameError:
        value = '_unknown_'

    value = re.sub('[^0-9A-Za-z]', '_', value)
    path = os.path.join(dest_dir, by_type, value)
    os.makedirs(path, exist_ok=True)
    path = os.path.join(path, date_path_basename)
    link_file(hashed_path, path)


def create_links_by(db_entry, dest_dir, keyword_map):
    hashed_path = db_entry[1]['hashed_path']
    date_basename = db_entry[1]['date_basename']
    meta_data = db_entry[1]['meta_data']
    for key in keyword_map:
        create_by_link(dest_dir, meta_data, date_basename, hashed_path, key, keyword_map[key])
    return db_entry[0], db_entry
