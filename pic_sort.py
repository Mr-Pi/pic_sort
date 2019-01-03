#!/usr/bin/env python3
import argparse
import file_ops
import os
import threading
import queue
import traceback
import sys

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
def handler(handler_queue, dest_dir, link_file, move_file):
    thread_id = threading.currentThread().getName()
    print('Thread {} started'.format(thread_id))
    while not exit_flag:
        if handler_queue.empty():
            continue
        filename, file_number = handler_queue.get()
        try:
            file_ops.handle_file(filename, dest_dir, link_file, move_file, file_number)
        except Exception:
            print("Failed to handle file {}".format(filename))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        print('Thread {}: processed {}'.format(thread_id, filename))
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

    for i in range(0,args.threads):
        thread = threading.Thread(name = '{}'.format(i), target=handler,
                args=(handler_queue, args.destination, link_file, move_file,))
        thread.start()
        threads.append(thread)

    file_number = 0
    for filename in file_ops.iter_files(args.paths, [ '.' + extension.lower() for extension in args.extensions ]):
        handler_queue.put((filename, file_number))
        if file_number < 999999999:
            file_number += 1
        else:
            file_number = 0

    handler_queue.join()
    exit_flag = True
