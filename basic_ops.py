import sys


def print_bold(string):
    print('[1m{}[0m'.format(string))


def stdout(string):
    sys.stdout.write('{}           \r'.format(string))


def merge_dict(a, b):
    '''
    Merges two dicts.
    If the key is present in both dicts, the key from the second dict is used.
    This goes unless the key contains a list or a dict.
    For dicts, this function is called recursively.
    For lists, the lists are appended and only unique values are preserved(the order is not changed)
    :param dict a: The dict to merge into
    :param dict b: The dict to merge into a, overriding with the rules specified above
    '''
    if not b:
        return a
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                mergeDict(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key] = a[key] + b[key]
                seen = set()
                a = [ x for x in a if x not in seen and not seen.add(x) ]
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
