import traceback
import logging


class CustomObject(object):
    pass


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
    logging.basicConfig(filename=fname, filemode='w', level=logging.DEBUG)

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
