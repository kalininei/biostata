import traceback


def ignore_exception(e, pretext=None):
    traceback.print_exc()
    if pretext:
        print(pretext)
