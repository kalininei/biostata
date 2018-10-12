import traceback
import logging


class CustomObject(object):
    pass


class CustomNone(CustomObject):
    def __str__(self):
        return 'None'

    def __repr__(self):
        return 'None'


class CustomEString(CustomObject):
    def __str__(self):
        return 'empty str'

    def __repr__(self):
        return 'empty str'


def _ignore_exception(e, text=None):
    log_message(traceback.format_exc(), "ERROR")
    if text:
        log_message(text, "ERROR")


def _do_not_ignore_exception(e, text=None):
    _ignore_exception(e, text)
    raise e


def _log_message(txt, lv="INFO"):
    print('* ' + txt + '\n')


def _no_log_message(txt, lv="INFO"):
    pass


def _log_to_file(fname):
    logging.basicConfig(
        handlers=[logging.FileHandler(fname, 'w', 'utf-8')],
        format='%(asctime)s.%(msecs)03d -- %(levelname)s: %(message)s',
        datefmt='%H:%M:%S',
        level=logging.DEBUG)

    def msg(txt, lv="INFO"):
        try:
            if lv == "INFO":
                logging.info(txt)
            elif lv == "ERROR":
                logging.error(txt)
            elif lv == "WARNING":
                logging.warning(txt)
        except:
            pass

    return msg

ignore_exception = _ignore_exception
log_message = _log_message


def set_ignore_exception(ignore):
    'ignore non-critical exceptions'
    global ignore_exception, _ignore_exception, _do_not_ignore_exception

    if ignore:
        ignore_exception = _ignore_exception
    else:
        ignore_exception = _do_not_ignore_exception


def set_log_message(tplog):
    """ tplog = 'no', 'console', 'file: fname' """
    global log_message, _log_message, _no_log_message

    if tplog == 'console':
        log_message = _log_message
    elif tplog == 'no':
        log_message = _no_log_message
    elif tplog[:4] == 'file':
        log_message = _log_to_file(tplog[5:].strip())


class BSignal(object):
    def __init__(self):
        self.subscribers = []

    def add_subscriber(self, func):
        self.subscribers.append(func)

    def remove_subscriber(self, func):
        self.subscriber.remove(func)

    def emit(self, *args):
        for f in self.subscribers:
            f(*args)


# xml indent
def xmlindent(elem, level=0):
    """ http://effbot.org/zone/element-lib.htm#prettyprint.
        It basically walks your tree and adds spaces and newlines so the tree
        is printed in a nice way
    """
    tabsym = "  "
    i = "\n" + level * tabsym
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + tabsym
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for elem in elem:
            xmlindent(elem, level + 1)
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


class IdCounter:
    def __init__(self):
        self._val = 0

    def new(self):
        self._val += 1
        return self._val

    def include(self, val):
        if self._val < val:
            self._val = val

    def reset(self):
        self._val = 0


__uniint_i = 0


def uniint():
    global __uniint_i
    __uniint_i += 1
    return __uniint_i


def best_steping(mostticks, lims):
    import bisect
    import math
    largest = lims[1] - lims[0]
    if mostticks < 2:
        mostticks = 2
    if largest <= 0:
        return []
    minimum = largest / mostticks
    magnitude = 10 ** math.floor(math.log(minimum, 10))
    residual = minimum / magnitude
    # this table must begin with 1 and end with 10
    table = [1, 2, 2.5, 5, 10]
    if residual < 10:
        tick = table[bisect.bisect_right(table, residual)]
    else:
        tick = 10
    tick = tick * magnitude

    r0 = math.floor(lims[0]/tick)*tick
    return r0, tick


def get_best_steping(mostticks, lims, wends=False):
    r0, tick = best_steping(mostticks, lims)
    # r0 = math.floor(lims[0]/magnitude)*magnitude
    ret = [r0]
    while ret and ret[-1] < lims[1]:
        ret.append(ret[-1] + tick)
    if not wends:
        while ret and ret[0] - lims[0] < 0.8*tick:
            ret.pop(0)
        while ret and lims[1] - ret[-1] < 0.8*tick:
            ret.pop()
    return ret


def list_equal(lst1, lst2):
    if len(lst1) != len(lst2):
        return False
    for a, b in zip(lst1, lst2):
        if a != b:
            return False
    return True
