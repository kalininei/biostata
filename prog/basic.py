import traceback
import logging


def _ignore_exception(e, text=None):
    traceback.print_exc()
    if text:
        print(text)


def _do_not_ignore_exception(e, text=None):
    traceback.print_exc()
    if text:
        print(text)
    raise e


def _log_message(txt):
    print('* ' + txt + '\n')


def _no_log_message(txt):
    pass


def _log_to_file(fname):
    logging.basicConfig(filename=fname, filemode='w', level=logging.DEBUG)

    def msg(txt):
        logging.info(txt)

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
