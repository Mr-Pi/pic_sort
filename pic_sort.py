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


IMPORTANT: Do not delete the log.txt file at the destination!!!
           This file is required to update all links and keeps track of the
           corrected extension and original name.

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
def handler(handler_queue, dest_dir, move_file, log_file):
    thread_id = threading.currentThread().getName()
    print('Thread {} started'.format(thread_id))
    while not exit_flag:
        if handler_queue.empty():
            continue
        filename = handler_queue.get()
        try:
            extension = os.path.splitext(filename)[1]
            if extension != '.gpx':
                sha512 = file_ops.handle_file_copy_move(filename, dest_dir, move_file)
                json_str = json.dumps([os.path.basename(filename), filename, os.path.abspath(filename), extension, sha512])
                log_file.write('{}\n'.format(json_str))
            else:
                location_ops.parse_gpx_file(filename)
                print('parsed gpx file')
        except Exception:
            print('Failed to handle file {}'.format(filename))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        print('Thread {}: prepared {}'.format(thread_id, filename))
        handler_queue.task_done()
    print('Thread {} finished'.format(thread_id))

if __name__ == '__main__':
    args = parser.parse_args()
    print(args)
    if args.move:
        print('Move all files to destination path')
        move_file = True
    else:
        print('Copy all files to destination path')
        move_file = False

    file_ops.prepare_dest(args.destination)
    print('Destination is prepared')

    threads = []
    handler_queue = queue.Queue(args.queue_size)

    log_file_path_temp = os.path.join(args.destination, 'log.in.txt')
    log_file_path = os.path.join(args.destination, 'log.txt')
    try:
        shutil.copy(log_file_path, log_file_path_temp)
    except FileNotFoundError:
        pass
    log_file = open(log_file_path_temp, 'a+')

    for i in range(0,args.threads):
        thread = threading.Thread(name = '{}'.format(i), target=handler,
                args=(handler_queue, args.destination, move_file, log_file,))
        thread.start()
        threads.append(thread)

    for filename in file_ops.iter_files(args.paths, [ '.' + extension.lower() for extension in args.extensions ]):
        handler_queue.put(filename)

    handler_queue.join()
    exit_flag = True

    log_file.close()
    os.system('sort -u -o {} {}'.format(log_file_path, log_file_path_temp))
    os.remove(log_file_path_temp)

    lines = 0
    with open(log_file_path) as log_file:
        for _ in log_file:
            lines += 1

    linec = 0
    with open(log_file_path) as log_file:
        for line in log_file:
            linec += 1
            data = json.loads(line)
            basename = data[0]
            extension = data[3]
            sha512 = data[4]
            file_ops.create_links(args.destination, sha512, extension, basename, args.update, args.max_diff)
            print('{:6.2f}% linked file {}'.format(linec/lines*100, basename))
