#!/usr/bin/env python3
import argparse
import db_ops, file_ops
from main_ops import *
from file_ops import iter_files
from mt_ops import handler, iter_threaded

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
parser.add_argument('-s', '--redis-db-offset', dest='db_offset', type=int, help='first redis database to use', default=0)
parser.add_argument('-f', '--no-faces', dest='skip_faces', help='Skip face recognition', action='store_true')
parser.add_argument('--max-diff', dest='max_diff', help='the maximum time difference allowed to treat a gpx location as valid for picture location', default=600)
parser.add_argument('destination', help='destination path for the sorted picture tree')

exit_flag = False


def main():
    args = parser.parse_args()
    print(args)
    print('\n')
    if args.move:
        print('[1mInfo:[0m Move all files to destination path')
        move_file = True
    else:
        print('[1mInfo:[0m Copy all files to destination path')
        move_file = False

    print('\n\n')
    print_bold('prepare destination')
    dest_dir = os.path.abspath(args.destination)
    prepare_dest(dest_dir)

    print_bold('\nprepare database\n')
    db = db_ops.init_db(os.path.join(dest_dir, 'database.bin'), db_offset=args.db_offset)

    print_bold('hash all files')
    iter_threaded(iter_files, hash_file, num_threads = args.threads, size_queue = args.queue_size, handler_args = ( args.destination, ), db = db.source_hash,
            iter_args = (args.paths, [ '.' + extension.lower() for extension in args.extensions ]))

    entries = db.source_hash.dbsize()

    print_bold('copy/move all files')
    iter_threaded(db_ops.iter_db, copy_move_file, progress_max = entries, db=db.hash_meta,
            iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, move_file, ))

    print_bold('parse meta data')
    iter_threaded(db_ops.iter_db, get_meta_data, progress_max = entries, db=db.hash_meta,
            iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, args.max_diff, ))

    print_bold('create date links')
    iter_threaded(db_ops.iter_db, create_date_link, progress_max = entries, db=db.hash_datename,
            iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, db.hash_meta, ))

    print_bold('create by links')
    iter_threaded(db_ops.iter_db, create_by_link, progress_max = entries,
            iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, db.hash_meta, db.hash_datename, ))

    print_bold('create location links')
    iter_threaded(db_ops.iter_db, create_by_location, progress_max = entries,
            iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, db.hash_meta, db.hash_datename, ))

    if not args.skip_faces:
        print_bold('detect faces')
        iter_threaded(db_ops.iter_db, detect_faces, progress_max = entries, db=db.hash_face,
                iter_args=(db.source_hash,), num_threads = args.threads, size_queue = args.queue_size, handler_args = (dest_dir, db.hash_face, db.hash_datename, ))

    print('\n[1;32m   finished [0;32mprocessed {} files[0m\n[0m'.format(entries))



if __name__ == '__main__':
    main()
