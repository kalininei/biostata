import sys
import time
import unittest
from PyQt5 import QtWidgets, QtCore, QtTest
from prog import basic, projroot
from bgui import mainwin, dlgs, importdlgs, dictdlg
from utest import testutils

basic.set_log_message('file: ~log')
basic.set_ignore_exception(False)


def print_thread(cap):
    print("{}: {}".format(cap, int(QtCore.QThread.currentThreadId())))


class MainThreadObject(QtCore.QObject):
    emitter = QtCore.pyqtSignal(object)
    sleepafter = 0.1

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

    def type_text(self, txt, wid=None):
        def func():
            QtTest.QTest.keyClicks(wid, txt)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def table_cell_dclick(self, row, col, wtab):
        def func():
            viewport = wtab.viewport()
            pos = QtCore.QPoint(wtab.columnViewportPosition(col) + 2,
                                wtab.rowViewportPosition(row) + 2)
            QtTest.QTest.mouseClick(viewport, QtCore.Qt.LeftButton,
                                    QtCore.Qt.NoModifier, pos)
            QtTest.QTest.mouseDClick(viewport, QtCore.Qt.LeftButton,
                                     QtCore.Qt.NoModifier, pos)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)

    def efunc(self, method, *args):
        def func():
            method(*args)
        self.emitter.emit(func)
        time.sleep(self.sleepafter)


# class TestThread:
class TestThread(QtCore.QThread):
    sleepsec = 0.1
    maxwait = 1

    def __init__(self):
        super().__init__()
        self.wait_flag = False

    def wait_for_window(self, tp):
        s = 0
        while s < self.maxwait:
            time.sleep(self.sleepsec)
            s += self.sleepsec
            for w in qApp.topLevelWidgets():
                if isinstance(w, tp):
                    return w

    def wait_for_focus_widget(self, tp):
        s = 0
        while s < self.maxwait:
            time.sleep(self.sleepsec)
            s += self.sleepsec
            w = qApp.focusWidget()
            if isinstance(w, tp):
                return w

    def wait_for_signal(self, sig):
        self.wait_flag = False
        sig.connect(self._receiver)
        s = 0
        while s < self.maxwait and not self.wait_flag:
            time.sleep(self.sleepsec)
            s += self.sleepsec
        sig.disconnect(self._receiver)

    def _receiver(self, *args):
        self.wait_flag = True

    def run(self):
        unittest.TextTestRunner(verbosity=2).run(
            unittest.TestLoader().loadTestsFromTestCase(TestRunner))


class TestRunner(unittest.TestCase):
    def setUp(self):
        pass

    def test_import_txt(self):
        # import table
        w = tt.wait_for_window(mainwin.MainWindow)
        w.filemenu.acts['Import tables...'].trigger()

        # enter filename
        w = tt.wait_for_window(dlgs.ImportTablesDlg)
        w.sig_set_odata_entry.emit('filename', 'test_db/t2.dat')
        w.buttonbox.accepted.emit()

        # edit import options, load
        w = tt.wait_for_window(importdlgs.ImportPlainText)
        w.spec.sig_set_odata_entry.emit('col_sep', 'tabular')
        w.load_button.click()

        # modify first column (TEXT->ENUM)
        tt.wait_for_signal(w.data_was_loaded)
        ind = w.table.model().createIndex(1, 0)
        ind2 = ind.sibling(ind.row() + 1, ind.column())
        mto.efunc(w.table.model().setData, ind, 'ENUM', QtCore.Qt.EditRole)
        mto.efunc(w.table.dataChanged, ind, ind2)

        # ask for create_new_dictionary
        mto.table_cell_dclick(2, 0, w.table)
        wid = tt.wait_for_focus_widget(QtWidgets.QComboBox)
        mto.efunc(wid.setCurrentIndex, wid.count()-1)
        mto.press_enter()

        # create a dictionary named bt
        w = tt.wait_for_window(dictdlg.CreateNewDictionary)
        mto.table_cell_dclick(0, 1, w.e_table)
        mto.type_text('no')
        mto.press_enter()
        mto.efunc(w.e_spin.setValue, 5)
        mto.efunc(w.e_name.setText, 'bt')
        w.buttonbox.accepted.emit()

        # ok
        w = tt.wait_for_window(importdlgs.ImportPlainText)
        w.buttonbox.accepted.emit()

        # - check column values
        tt.wait_for_signal(win.active_model_changed)
        w = win
        col = testutils.get_tmodel_column(w.active_model, 2)
        self.assertListEqual(col, [1, 2, 1, 3, 4, 2, 5, 2, 1, 1, 10])
        col = testutils.get_tmodel_column(w.active_model, 4)
        self.assertListEqual(col, ['noF', 'F', 'noF', 'F', 'F', 'F',
                                   'noF', 'noF', 'noF', 'noF', ''])
        col = testutils.get_tmodel_column(w.active_model, 1)
        self.assertListEqual(col, ['no', 'b4p', 'b5p', 'b4p', 'b4p', 'b4g',
                                   'b5p', 'b4p', 'b5g', 'b5p', None])
        col = testutils.get_tmodel_raw_column(w.active_model, 1)
        self.assertListEqual(col, [0, 2, 4, 2, 2, 1, 4, 2, 3, 4, None])

        # collapse
        w = win
        mto.efunc(w._act_collapse_all)
        tt.wait_for_signal(win.active_model_repr_changed)
        col = testutils.get_tmodel_raw_column(w.active_model, 1)
        self.assertListEqual(
            col, ['no-1-2-noF', 'b4p-2-5-F', 'b5p-1-5-noF', 'b4p-3-5-F',
                  'b4p-4-5-F', 'b4g-2-5-F', 'b5p-5-3-noF', 'b4p-2-5-noF',
                  'b5g-1-3-noF', 'b5p-1-5-noF', '##-10-20-'])
        col = testutils.get_tmodel_raw_column(w.active_model, 2)
        self.assertListEqual(col, [0.22, 1.01, 0.12, 1.51, 2.23, 0.24, 3.42,
                                   0.41, 0.22, 2.22, None])


proj = projroot.ProjectDB()
qApp = QtWidgets.QApplication(sys.argv)
win = mainwin.MainWindow(proj)
win.show()

mto = MainThreadObject()
tt = TestThread()
tt.start()
# thr = threading.Thread(target=tt.run)
# thr.start()
qApp.exec_()
