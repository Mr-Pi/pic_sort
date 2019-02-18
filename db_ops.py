import pickle
from redis import Redis
from multiprocessing.managers import Namespace

def init_db(restore_file, host='localhost', port=6379, db_offset=0):
    db = Namespace()
    db.source_hash = Redis(host=host, port=port, db=db_offset+0)
    db.source_hash.flushdb()
    db.hash_meta = Redis(host=host, port=port, db=db_offset+1)
    db.hash_datename = Redis(host=host, port=port, db=db_offset+2)
    db.hash_face = Redis(host=host, port=port, db=db_offset+3)
    return db

def get(db, key):
    v = None
    if db.exists(key):
        try:
            v = pickle.loads(db.get(key))
        except EOFError:
            pass
    return v


def iter_db(db):
    for k in db.scan_iter():
        try:
            v = pickle.loads(db.get(k))
        except EOFError:
            v = None
        yield(k.decode('UTF-8'), v)
