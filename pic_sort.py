#!/usr/bin/env python3
import argparse
import file_ops
import os
import shutil
import threading
import queue
import traceback
import sys
import json

description='''
Search pictures at given paths and sorts them based on there exif data.


use -- to end optional arguments section
'''

parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=description)
parser.add_argument('-p', '--paths', type=str, help='search for pictures at the given path', required=True, nargs='+')
parser.add_argument('-e', '--extensions', type=str, help='extensions which should recognized as pictures', nargs='+', default=['jpg', 'cr2'])
parser.add_argument('-m', '--move', help='move all found pictures to destination path (the default is to copy them)', action='store_true')
parser.add_argument('-s', '--symlink', help='create symlinks for all sorted files instead of hardlinks', action='store_true')
parser.add_argument('-t', '--threads', type=int, help='number of threads to use to process files', default=4)
parser.add_argument('-q', '--queue-size', dest='queue_size', type=int, help='queue size to use to stack files to process', default=10)
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
            sha512 = file_ops.handle_file_copy_move(filename, dest_dir, move_file)
            json_str = json.dumps([os.path.basename(filename), filename, os.path.abspath(filename), os.path.splitext(filename)[1], sha512])
            log_file.write('{}\n'.format(json_str))
        except Exception:
            print("Failed to handle file {}".format(filename))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        print('Thread {}: prepared {}'.format(thread_id, filename))
        handler_queue.task_done()
    print('Thread {} finished'.format(thread_id))

if __name__ == "__main__":
    args = parser.parse_args()
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

    with open(log_file_path) as log_file:
        for line in log_file:
            data = json.loads(line)
            basename = data[0]
            extension = data[3]
            sha512 = data[4]
            file_ops.create_links(args.destination, sha512, extension, basename, link_file)
            print("linked file {}".format(basename))
