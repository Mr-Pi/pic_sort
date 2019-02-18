import threading, queue, traceback, sys, os, pickle
from basic_ops import *


def handler(handler_function, handler_queue, extra_args, progress_status, db):
    thread_id = threading.currentThread().getName()
    while not exit_flag:
        if handler_queue.empty():
            continue
        entry = handler_queue.get()
        try:
            log_output, k, v = handler_function(entry, *extra_args)
            if k and db:
                if v:
                    db.set(k, pickle.dumps(v))
                else:
                    db.append(k, b'')
        except Exception:
            print('Failed to handle {}'.format(entry))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        if progress_status:
            progress_status['current'] += 1
            stdout('{:6.2f}% Thread {}: {}'.format(progress_status['current']/progress_status['sum'], thread_id, log_output))
        else:
            stdout('Thread {}: {}'.format(thread_id, log_output))
        handler_queue.task_done()


def iter_threaded(iter_funtion, handler_function, db=None, handler_args=(), num_threads=8, size_queue=10, iter_args=(), progress_status=None):
    global exit_flag
    threads = []
    handler_queue = queue.Queue(size_queue)
    exit_flag = False
    for i in range(0, num_threads):
        thread = threading.Thread(name = '{}'.format(i), target=handler, args=(handler_function, handler_queue, handler_args, progress_status, db))
        thread.start()
        threads.append(thread)
    for request in iter_funtion(*iter_args):
        handler_queue.put(request)
    handler_queue.join()
    exit_flag = True
    if progress_status:
        sys.stdout.write('\r100.00%')
    print('\n')
