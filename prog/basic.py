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
        if lv == "INFO":
            logging.info(txt)
        elif lv == "ERROR":
            logging.error(txt)
        elif lv == "WARNING":
            logging.warning(txt)

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
