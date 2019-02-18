import multiprocessing, traceback, sys, os, pickle
from basic_ops import *


def handler(handler_function, handler_queue, extra_args, progress_max, progress_current, db):
    process_id = multiprocessing.current_process().name
    while True:
        entry = handler_queue.get()
        try:
            log_output, k, v = handler_function(entry, *extra_args)
            if k and db:
                if v != None:
                    db.set(k, pickle.dumps(v))
                else:
                    db.append(k, b'')
        except Exception:
            print('Failed to handle {}'.format(entry))
            traceback.print_exc(file=sys.stdout)
            os._exit(10)
        if progress_max:
            progress_current.value += 1
            stdout('{:6.2f}% Process {}: {}'.format(progress_current.value/progress_max, process_id, log_output))
        else:
            stdout('Process {}: {}'.format(process_id, log_output))
        handler_queue.task_done()


def iter_threaded(iter_funtion, handler_function, db=None, handler_args=(), num_threads=8, size_queue=10, iter_args=(), progress_max=None):
    processes = []
    progress_current = None
    if progress_max:
        progress_max /= 100
        progress_current = multiprocessing.Value('i', 0)
    handler_queue = multiprocessing.JoinableQueue(size_queue)
    for i in range(0, num_threads):
        process = multiprocessing.Process(name = '{}'.format(i), target=handler, args=(handler_function, handler_queue, handler_args, progress_max, progress_current, db))
        process.start()
        processes.append(process)
    for request in iter_funtion(*iter_args):
        handler_queue.put(request)
    handler_queue.join()
    handler_queue.close()
    for process in processes:
        process.terminate()
        process.join()
    if progress_max:
        sys.stdout.write('\r100.00%')
    print('\n')
