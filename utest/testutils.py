import time
import unittest
from PyQt5 import QtCore, QtTest


def print_dtab(dt):
    for i in range(dt.n_rows()):
        line = []
        for j in range(dt.n_cols()):
            v = dt.get_value(i, j)
            if v is None:
                v = '<None>'
            line.append("{0: >8}".format(v))
        print(''.join(line))


def get_dtab_column(dt, icol):
    ret = []
    for i in range(dt.n_rows()):
        ret.append(dt.get_value(i, icol))
    return ret


def get_dtab(dt):
    ret = []
    for i in range(dt.n_cols()):
        ret.append(get_dtab_column(dt, i))
    return ret


def get_dtab_raw(dt):
    ret = []
    for i in range(dt.n_cols()):
        ret.append(get_dtab_raw_column(dt, i))
    return ret


def get_dtab_raw_column(dt, icol):
    ret = []
    for i in range(dt.n_rows()):
        ret.append(dt.get_raw_value(i, icol))
    return ret


def get_tmodel_column(tm, icol):
    ret = []
    for i in range(2, tm.rowCount()):
        index = tm.createIndex(i, icol)
        dt = tm.data(index, QtCore.Qt.DisplayRole)
        ret.append(dt)
    return ret


def get_tmodel(tm):
    ret = []
    for i in range(tm.columnCount()):
        ret.append(get_tmodel_column(tm, i))
    return ret


def get_tmodel_raw(tm):
    ret = []
    for i in range(tm.columnCount()):
        ret.append(get_tmodel_raw_column(tm, i))
    return ret


def get_tmodel_raw_column(tm, icol):
    from bgui import tmodel
    ret = []
    for i in range(2, tm.rowCount()):
        index = tm.createIndex(i, icol)
        dt = tm.data(index, tmodel.TabModel.RawValueRole)
        ret.append(dt)
    return ret


def print_thread(cap):
    print("{}: {}".format(cap, int(QtCore.QThread.currentThreadId())))


class MainThreadObject(QtCore.QObject):
    emitter = QtCore.pyqtSignal(object)
    sleepafter = 0.0

    def __init__(self):
        super().__init__()
        self.emitter.connect(self._execute_fun)

    def _execute_fun(self, fun):
        fun()

    def press_enter(self, wid=None):
        def func():
            QtTest.QTest.keyPress(wid, QtCore.Qt.Key_Enter)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def press_contextmenu(self, wid=None):
        def func():
            QtTest.QTest.keyPress(wid, QtCore.Qt.Key_Menu)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def type_text(self, txt, wid=None):
        def func():
            QtTest.QTest.keyClicks(wid, txt)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def table_cell_dclick(self, row, col, wtab):
        def func():
            viewport = wtab.viewport()
            w = wtab.columnWidth(col)
            h = wtab.rowHeight(row)
            pos = QtCore.QPoint(wtab.columnViewportPosition(col) + w/2,
                                wtab.rowViewportPosition(row) + h/2)
            QtTest.QTest.mouseClick(viewport, QtCore.Qt.LeftButton,
                                    QtCore.Qt.NoModifier, pos)
            QtTest.QTest.mouseDClick(viewport, QtCore.Qt.LeftButton,
                                     QtCore.Qt.NoModifier, pos)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def table_cell_check(self, row, col, wtab, status):
        def func():
            wtab.model().setData(
                wtab.model().createIndex(row, col),
                QtCore.Qt.Checked if status else QtCore.Qt.Unchecked,
                QtCore.Qt.CheckStateRole)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def tree_item_click(self, tree, stritm, button=QtCore.Qt.RightButton):
        pass

    def button_click(self, button):
        def func():
            QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def dialog_okclick(self, bbox):
        b = bbox.button(type(bbox).Ok)
        self.button_click(b)

    def dialog_applyclick(self, bbox):
        b = bbox.button(type(bbox).Apply)
        self.button_click(b)

    def efunc(self, method, *args):
        def func():
            method(*args)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)


class TestThread(QtCore.QThread):
    sleepsec = 0.1
    ntries = 3
    maxwait = 1

    def __init__(self, main_thread_object, cls_test_runner, q_app):
        super().__init__()
        self.mto = main_thread_object
        self.cls_test_runner = cls_test_runner
        self.qApp = q_app
        self.wait_flag = False

    def _receiver(self, *args):
        self.wait_flag = True

    def _framework(self, func, funcargs, worker):
        elast = None
        for i in range(self.ntries):
            try:
                func(*funcargs)
                s = 0
                while s < self.maxwait:
                    try:
                        time.sleep(self.sleepsec)
                        s += self.sleepsec
                        return worker()
                    except Exception as e:
                        elast = e
            except Exception as e:
                elast = e
        raise elast

    def _eval_framework(self, func, funcargs, worker):
        if not isinstance(funcargs, tuple):
            funcargs = (funcargs,)
        return self._framework(self.mto.efunc, ((func,) + funcargs), worker)

    def _emit_framework(self, sig, sigargs, worker):
        if not isinstance(sigargs, tuple):
            sigargs = (sigargs,)
        return self._framework(sig.emit, sigargs, worker)

    def _wait_window_wrk(self, tp):
        def wrk():
            for w in self.qApp.topLevelWidgets():
                if w.isVisible() and isinstance(w, tp):
                    self.eval_and_wait_true(self.qApp.setActiveWindow, (w,),
                                            'w.isActiveWindow()', {'w': w})
                    return w
            raise Exception("window {} failed to show up".format(tp))
        return wrk

    def _wait_true_wrk(self, expr, kwargs):
        def wrk():
            p = eval(expr, kwargs)
            if p is not True:
                raise Exception("False expression {}".format(expr))
        return wrk

    def _wait_sig_wrk(self, sig):
        self.wait_flag = False
        sig.connect(self._receiver)

        def wrk():
            if not self.wait_flag:
                raise Exception("flag is false")
        return wrk

    def _wait_focus_widget(self, tp):
        def wrk():
            w = self.qApp.focusWidget()
            if isinstance(w, tp):
                return w
            raise Exception('focus widget was not set')
        return wrk

    def wait_window(self, tp):
        return self.eval_and_wait_window(int, (1,), tp)

    def eval_and_wait_window(self, func, fargs, tp):
        return self._eval_framework(func, fargs, self._wait_window_wrk(tp))

    def eval_and_wait_true(self, func, fargs, expr, kwargs):
        return self._eval_framework(func, fargs,
                                    self._wait_true_wrk(expr, kwargs))

    def eval_and_wait_focus_widget(self, func, fargs, tp):
        return self._eval_framework(func, fargs, self._wait_focus_widget(tp))

    def eval_and_wait_signal(self, func, fargs, sig):
        try:
            return self._eval_framework(func, fargs, self._wait_sig_wrk(sig))
        except:
            raise
        finally:
            self.wait_flag = False
            sig.disconnect(self._receiver)

    def emit_and_wait_window(self, sig, sigargs, tp):
        return self._emit_framework(sig, sigargs,
                                    self._wait_window_wrk(tp))

    def emit_and_wait_true(self, sig, sigargs, expr, kwargs):
        return self._emit_framework(sig, sigargs,
                                    self._wait_true_wrk(expr, kwargs))

    def emit_and_wait_signal(self, sig, sigargs, sig2):
        try:
            return self._emit_framework(sig, sigargs, self._wait_sig_wrk(sig2))
        except:
            raise
        finally:
            self.wait_flag = False
            sig2.disconnect(self.receiver)

    def emit_now(self, sig, sigargs):
        return self.emit_and_wait_true(sig, sigargs, "True", {})

    def eval_now(self, func, funcargs):
        return self.eval_and_wait_true(func, funcargs, "True", {})

    def run(self):
        unittest.TextTestRunner(verbosity=2).run(
            unittest.TestLoader().loadTestsFromTestCase(self.cls_test_runner))
