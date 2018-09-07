import traceback


def ignore_exception(e, text=None):
    traceback.print_exc()
    if text:
        print(text)


def log_message(txt):
    print('* ' + txt + '\n')
