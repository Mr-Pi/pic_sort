#!/usr/bin/env python3
import argparse
import file_ops
import location_ops
import os
import shutil
import threading
import queue
import traceback
import sys
import json

import cv2
import face_recognition
import pickle

description='''
Search pictures at given paths and sorts them based on there exif data.

This script generates following structure at the destination directory:
    * hashed/raw/
        - all found files without an extension named by the sha512sum
    * hashed/with_extension/
        - links to hashed files with extension appended
    * by_date/
        - links to hashed files with extension appended and named by exif date
          (fallback to modification date)
          The date is converted to UTC and named by the UTC time


IMPORTANT: Do not delete the log.json file at the destination!!!
           This file is required to update all links and keeps track of the
           corrected extension and original path.

use -- to end optional arguments section
'''

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=description)
parser.add_argument('-p', '--paths', type=str, help='search for pictures at the given path', required=True, nargs='+')
parser.add_argument('-e', '--extensions', type=str, help='extensions which should be parsed', nargs='+', default=['jpg', 'jpeg', 'cr2', 'gpx'])
parser.add_argument('-m', '--move', help='move all found pictures to destination path (the default is to copy them)', action='store_true')
parser.add_argument('-t', '--threads', type=int, help='number of threads to use to process files', default=4)
parser.add_argument('-q', '--queue-size', dest='queue_size', type=int, help='queue size to use to stack files to process', default=10)
parser.add_argument('-u', '--update', help='recreate all links, this must be run once after pic_sort is updated', action='store_true')
parser.add_argument('--max-diff', dest='max_diff', help='the maximum time difference allowed to treat a gpx location as valid for picture location', default=600)
parser.add_argument('destination', help='destination path for the sorted picture tree')

exit_flag = False


keyword_map = {
        'by_camera_model': ['Image Model', 'Image Make', 'MakerNote ImageType'],
        'by_author': ['Image Artist', 'MakerNote OwnerName', 'EXIF CameraOwnerName', 'Thumbnail Artist']
        }


def stdout(string):
    sys.stdout.write('{}                        \r'.format(string))


def handler(handler_function, handler_queue, out_file, extra_args, progess_status):
    thread_id = threading.currentThread().getName()
    while not exit_flag:
        if handler_queue.empty():
            continue
        db_entry = handler_queue.get()
        try:
            log_output, db_entry = handler_function(db_entry, *extra_args)
            if db_entry and out_file:
                out_file.write('{}\n'.format(json.dumps(db_entry)))
        except Exception:
            print('Failed to handle {}'.format(db_entry))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        if progess_status:
            progess_status['current'] += 1
            stdout('{:6.2f}% Thread {}: {}'.format(progess_status['current']/progess_status['sum'], thread_id, log_output))
        else:
            stdout('Thread {}: {}'.format(thread_id, log_output))
        handler_queue.task_done()


def iter_threaded(iter_funtion, handler_function, out_file, handler_args=(), num_threads=8, size_queue=10, iter_args=(), progess_status=None):
    global exit_flag
    threads = []
    handler_queue = queue.Queue(size_queue)
    exit_flag = False
    for i in range(0, num_threads):
        thread = threading.Thread(name = '{}'.format(i), target=handler, args=(handler_function, handler_queue, out_file, handler_args, progess_status))
        thread.start()
        threads.append(thread)
    for request in iter_funtion(*iter_args):
        handler_queue.put(request)
    handler_queue.join()
    exit_flag = True
    if progess_status:
        sys.stdout.write('\r100.00%')
    print('\n')


def iter_db_file(db_path):
    with open(db_path) as db_file:
        for line in db_file:
            yield(json.loads(line))


if __name__ == '__main__':
    args = parser.parse_args()
    dest_dir = os.path.abspath(args.destination)
    print(args)
    print('\n')
    if args.move:
        print('[1mInfo:[0m Move all files to destination path')
        move_file = True
    else:
        print('[1mInfo:[0m Copy all files to destination path')
        move_file = False

    print('\n\n')
    print('[1mPrepare destination[0m\n')
    file_ops.prepare_dest(args.destination)

    db_path = os.path.join(dest_dir, 'log.json')
    db_path_work = os.path.join(dest_dir, 'log.working.json')
    try:
        shutil.copy(db_path, db_path_work)
    except FileNotFoundError:
        pass


    # hash/parse all files and copy/move them
    with open(db_path_work, 'w+') as db_file:
        db_file.seek(0,2)  # goto end, append new data

        print('[1mhash all files, read gpx and copy/move[0m')
        iter_threaded(file_ops.iter_files, file_ops.read_copy_move_sha512, db_file, num_threads = args.threads, size_queue = args.queue_size, handler_args = ( args.destination, move_file ),
                iter_args = (args.paths, [ '.' + extension.lower() for extension in args.extensions ]))

    os.system('sort -u -o {} {}'.format(db_path, db_path_work))
    os.remove(db_path_work)


    # count items to proceed
    lines = 0
    with open(db_path) as db_file:
        for _ in db_file:
            lines += 1
    progess_status = {'current': 0, 'sum': lines/100}


    # collect meta data
    print('[1mcollect meta data[0m')
    with open(db_path_work, 'w+') as out_file:
        iter_threaded(iter_db_file, file_ops.serialize_exif_data, out_file, progess_status = progess_status,
                iter_args=(db_path,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (['EXIF', 'GPS', 'Image', 'Thumbnail'], args.max_diff,))
    os.system('sort -u -o {} {}'.format(db_path, db_path_work))
    os.remove(db_path_work)


    # create links date
    print('[1mcreate date links[0m')
    with open(db_path_work, 'w+') as out_file:
        linec = 0
        for db_entry in iter_db_file(db_path):
            log_output, db_entry = file_ops.create_links_date(db_entry, dest_dir)
            out_file.write('{}\n'.format(json.dumps(db_entry)))
            linec += 1
            stdout('{:6.2f}% date link: {}'.format(linec/lines*100, log_output))
        print('\n')
    os.system('sort -u -o {} {}'.format(db_path, db_path_work))
    os.remove(db_path_work)


    # create links geolocation
    print('[1mcreate geolocation links[0m')
    iter_threaded(iter_db_file, file_ops.create_links_geolocation, None, progess_status = progess_status,
            iter_args=(db_path,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir,))


    # create by links
    print('[1mcreate by links[0m')
    progess_status = {'current': 0, 'sum': lines/100}
    iter_threaded(iter_db_file, file_ops.create_links_by, None, progess_status = progess_status,
            iter_args=(db_path,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, keyword_map, ))


    try:
        with open('faces.db','rb') as face_db:
            known_face_encodings = pickle.load(face_db)
    except FileNotFoundError:
        known_face_encodings = {}
    with open(db_path) as db_file:
        for line in db_file:
            data = json.loads(line)
            image = face_recognition.load_image_file(data[1]['hashed_path'])
            face_locations = face_recognition.face_locations(image)
            face_encodings = face_recognition.face_encodings(image)
            print('found', len(face_locations), 'faces in', data[1]['date_basename'])
            cv2.imshow('image', image[:,:,::-1])
            if len(face_locations) <= 0:
                cv2.waitKey(1)
            for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                name = None
                known = False
                for known_person in known_face_encodings:
                    results = face_recognition.compare_faces(known_face_encodings[known_person], face_encoding)
                    if True in results:
                        name = known_person
                        known = True
                        break
                cv2.imshow('face', image[top:bottom, left:right, ::-1])
                cv2.waitKey(1)
                cv2.waitKey(1)
                if name == None:
                    name = input('Name? ')
                else:
                    print("It's", name)
                cv2.destroyWindow('face')
                if name == "":
                    name = "_unknown_"
                path = os.path.join(dest_dir, 'by_person', name)
                os.makedirs(path, exist_ok=True)
                path = os.path.join(path, data[1]['date_basename'])
                file_ops.link_file(data[1]['hashed_path'], path)
                if not known:
                    if not name in known_face_encodings:
                        known_face_encodings[name] = []
                    known_face_encodings[name].append(face_encoding)
                    with open('faces.db', 'wb') as face_db:
                        pickle.dump(known_face_encodings, face_db)

    print('\n[1;32m   finish[0m\n[0m')
    os._exit(0)
