import sys
import unittest
from PyQt5 import QtWidgets, QtCore
from prog import basic, projroot
from bgui import mainwin, dlgs, importdlgs, dictdlg, filtdlg  # noqa
from utest import testutils     # noqa

basic.set_log_message('file: ~log')
basic.set_ignore_exception(False)


class TestRunner(unittest.TestCase):
    def setUp(self):
        ''
        tt.eval_now(win._close_database, ())

    def tearDown(self):
        ''
        tt.eval_now(win._act_saveas, ('~a.db',))

    # @unittest.skip
    def test_import_txt(self):
        w = tt.wait_window(mainwin.MainWindow)

        # open import dialog import table
        w = tt.eval_and_wait_window(
            w.filemenu.acts['Import tables...'].trigger, (),
            dlgs.ImportTablesDlg)

        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t2.dat'),
            'w.odata().filename == "test_db/t2.dat"', {'w': w})
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('format', 'plain text'),
            'w.odata().format == "plain text"', {'w': w})

        # ok button
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportPlainText)

        # edit import options
        tt.emit_and_wait_true(
            w.spec.sig_set_odata_entry, ('col_sep', 'tabular'),
            'w.spec.odata().col_sep == "tabular"', {'w': w})

        # load button
        tt.eval_and_wait_signal(w.load_button.click, (),
                                w.data_was_loaded)

        # first column (TEXT -> ENUM)
        ind = w.table.model().createIndex(1, 0)
        tt.eval_and_wait_true(
            w.table.model().setData, (ind, 'ENUM', QtCore.Qt.EditRole),
            'w.table.model().data(ind, QtCore.Qt.DisplayRole) == "ENUM"',
            {'w': w, 'ind': ind, 'QtCore': QtCore})

        # ask for new dictionary
        wid = tt.eval_and_wait_focus_widget(
            mto.table_cell_dclick, (2, 0, w.table),
            QtWidgets.QComboBox)
        tt.eval_and_wait_true(
            wid.setCurrentIndex, (wid.count()-1,),
            'wid.currentText() == "_ create new dict"', {'wid': wid})
        w = tt.eval_and_wait_window(
            mto.press_enter, (),
            dictdlg.CreateNewDictionary)

        # edit dictionary
        tt.eval_now(mto.table_cell_dclick, (0, 1, w.e_table))
        tt.eval_now(mto.type_text, ('no',))
        tt.eval_now(mto.press_enter, ())
        tt.eval_and_wait_true(w.e_spin.setValue, (5,),
                              'w.e_spin.value() == 5', {'w': w})
        tt.eval_and_wait_true(w.e_name.setText, ('bt',),
                              'w.e_name.text() == "bt"', {'w': w})

        # ok with dict
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportPlainText)
        # ok with load
        tt.eval_and_wait_signal(mto.dialog_okclick, (w.buttonbox,),
                                win.active_model_changed)

        # - check column values
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
        tt.eval_and_wait_signal(w._act_collapse_all, (),
                                w.active_model_repr_changed)
        col = testutils.get_tmodel_raw_column(w.active_model, 1)
        self.assertListEqual(
            col, ['no-1-2-noF', 'b4p-2-5-F', 'b5p-1-5-noF', 'b4p-3-5-F',
                  'b4p-4-5-F', 'b4g-2-5-F', 'b5p-5-3-noF', 'b4p-2-5-noF',
                  'b5g-1-3-noF', 'b5p-1-5-noF', '##-10-20-'])
        col = testutils.get_tmodel_raw_column(w.active_model, 2)
        self.assertListEqual(col, [0.22, 1.01, 0.12, 1.51, 2.23, 0.24, 3.42,
                                   0.41, 0.22, 2.22, None])

    # @unittest.skip
    def test_import_xls(self):
        # import table
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.filemenu.acts['Import tables...'].trigger, (),
            dlgs.ImportTablesDlg)

        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t2.xlsx'),
            "w.odata().format == 'xlsx'", {'w': w})

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportXlsx)

        # edit import options, load
        tt.eval_and_wait_signal(
            w.load_button.click, (),
            w.data_was_loaded)

        # modify forth column (TEXT->BOOL)
        ind = w.table.model().createIndex(1, 3)
        tt.eval_and_wait_true(
            w.table.model().setData, (ind, 'BOOL', QtCore.Qt.EditRole),
            'True', {})

        # _ create new dict
        wid = tt.eval_and_wait_focus_widget(
            mto.table_cell_dclick, (2, 3, w.table),
            QtWidgets.QComboBox)
        tt.eval_and_wait_true(
            wid.setCurrentIndex, (wid.count()-1,),
            'wid.currentText() == "_ create new dict"', {'wid': wid})
        w = tt.eval_and_wait_window(
            mto.press_enter, (),
            dictdlg.CreateNewDictionary)

        # create a dictionary named bool1
        tt.eval_now(mto.table_cell_dclick, (0, 1, w.e_table))
        tt.eval_now(mto.type_text, ('noF',))
        tt.eval_now(mto.press_enter, ())
        tt.eval_now(w.e_name.setText, ('bool1',))
        w = tt.emit_and_wait_window(w.buttonbox.accepted, (),
                                    importdlgs.ImportXlsx)

        # change column name (repeated name, improper name, correct name)
        tt.eval_now(mto.table_cell_dclick, (0, 3, w.table))
        tt.eval_now(mto.type_text, ('result 1',))
        w = tt.eval_and_wait_window(mto.press_enter, (),
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w,),
                                    importdlgs.ImportXlsx)
        tt.eval_now(mto.table_cell_dclick, (0, 3, w.table))
        tt.eval_now(mto.type_text, ('"col"',))
        w = tt.eval_and_wait_window(mto.press_enter, (),
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w,),
                                    importdlgs.ImportXlsx)
        tt.eval_now(mto.table_cell_dclick, (0, 3, w.table))
        tt.eval_now(mto.type_text, ('bool1',))
        w = tt.eval_and_wait_window(mto.press_enter, (),
                                    importdlgs.ImportXlsx)

        # uncheck some columns
        tt.eval_now(mto.table_cell_check, (0, 1, w.table, False))
        tt.eval_now(mto.table_cell_check, (0, 4, w.table, False))

        # change table name (invalid name, good name)
        tt.emit_now(w.spec.sig_set_odata_entry, ('tabname', 'Ab&fds'))
        w = tt.eval_and_wait_window(mto.press_enter, (),
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w,),
                                    importdlgs.ImportXlsx)
        tt.emit_now(w.spec.sig_set_odata_entry, ('tabname', 'Table1'))
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    mainwin.MainWindow)

        # - check column values
        col = testutils.get_tmodel_column(w.active_model, 1)
        self.assertListEqual(col, ['no', 'b4p', 'b5p', 'b4p', 'b4p', 'b4g',
                                   'b5p', 'b4p', 'b5g', 'b5p', ''])
        col = testutils.get_tmodel_column(w.active_model, 3)
        self.assertListEqual(col, ['noF', 'F', 'noF', 'F', 'F', 'F', 'noF',
                                   'noF', 'noF', 'noF', None])
        col = testutils.get_tmodel_column(w.active_model, 4)
        self.assertListEqual(col, [0.72, 2.32, 3.32, 2.22, 2.23, 2.12,
                                   0.11, 1.12, 1.22, 0.22, None])
        col = testutils.get_tmodel_raw_column(w.active_model, 3)
        self.assertListEqual(col, [0, 1, 0, 1, 1, 1, 0, 0, 0, 0, None])

        # check shown table name
        self.assertEqual(w.wtab.tabText(0), 'Table1*')
        tt.eval_and_wait_true(w._act_saveas, ('~a.db',),
                              'w.wtab.tabText(0)=="Table1"', {'w': w})

    # @unittest.skip
    def test_changedict(self):
        # import table
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.filemenu.acts['Import tables...'].trigger, (),
            dlgs.ImportTablesDlg)

        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t2.xlsx'),
            "w.odata().format == 'xlsx'", {'w': w})

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportXlsx)

        # edit import options, load
        tt.eval_and_wait_signal(
            w.load_button.click, (),
            w.data_was_loaded)

        # modify first column (TEXT->ENUM)
        ind = w.table.model().createIndex(1, 0)
        tt.eval_now(
            w.table.model().setData, (ind, 'ENUM', QtCore.Qt.EditRole))

        # _ create new dict
        wid = tt.eval_and_wait_focus_widget(
            mto.table_cell_dclick, (2, 0, w.table),
            QtWidgets.QComboBox)
        tt.eval_and_wait_true(
            wid.setCurrentIndex, (wid.count()-1,),
            'wid.currentText() == "_ create new dict"', {'wid': wid})
        w = tt.eval_and_wait_window(
            mto.press_enter, (),
            dictdlg.CreateNewDictionary)

        # create a dictionary named enum1
        tt.eval_now(mto.table_cell_dclick, (0, 1, w.e_table))
        tt.eval_now(mto.type_text, ('no',))
        tt.eval_now(mto.press_enter, ())
        tt.eval_now(w.e_spin.setValue, (5,))
        tt.eval_now(w.e_name.setText, ('enum1',))
        w = tt.emit_and_wait_window(w.buttonbox.accepted, (),
                                    importdlgs.ImportXlsx)
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    mainwin.MainWindow)

        # change column visibility
        tt.eval_now(w.dock_colinfo.setVisible, (True))
        tt.eval_now(w.dock_colinfo.tab.model().set_checked,
                    ['id', 'biochar type', 'result 3'])
        tt.eval_now(mto.dialog_applyclick, (w.dock_colinfo.buttonbox))

        # add anon filter for enum1
        w = tt.eval_and_wait_window(
            w._act_filter, (), filtdlg.EditFilterDialog)
        tt.eval_now(w.frows[0].cb[2].setCurrentText, '"biochar type"')
        tt.eval_now(w.frows[0].cb[3].setCurrentText, '==')
        tt.eval_now(w.frows[0].cb[4].setCurrentText, 'no')
        tt.eval_now(w.frows[1].cb[0].setCurrentText, 'OR')
        tt.eval_now(w.frows[1].cb[2].setCurrentText, '"biochar type"')
        tt.eval_now(w.frows[1].cb[3].setCurrentText, '==')
        tt.eval_now(w.frows[1].cb[4].setCurrentText, 'b4p')
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        # check output
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[3, 6, 7, 9, 10], ['b5p', 'b4g', 'b5p', 'b5g', 'b5p'], [1.2, 1.2, 2.2, 2.8, 2.2]])   # noqa

        # add named filter for enum1
        w = tt.eval_and_wait_window(
            w._act_filter, (), filtdlg.EditFilterDialog)
        tt.eval_now(w.frows[0].cb[2].setCurrentText, '"biochar type"')
        tt.eval_now(w.frows[0].cb[3].setCurrentText, '!=')
        tt.eval_now(w.frows[0].cb[4].setCurrentText, 'b5p')
        tt.eval_now(w.filter_cb.setChecked, QtCore.Qt.Unchecked)
        tt.eval_now(w.filter_name.setText, 'FLT')
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[3, 7, 10], ['b5p', 'b5p', 'b5p'], [1.2, 2.2, 2.2]])   # noqa

        # change dictionary values
        w = tt.eval_and_wait_window(w._act_dictinfo, (),
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum1')
        w = tt.eval_and_wait_window(w.tree._act_edit, ind,
                                    dictdlg.CreateNewDictionary)
        tt.eval_now(mto.table_cell_dclick, (0, 1, w.e_table))
        tt.eval_now(mto.type_text, ('cont'))
        tt.eval_now(mto.table_cell_dclick, (4, 1, w.e_table))
        tt.eval_now(mto.type_text, ('B5'))
        tt.eval_now(mto.press_enter, ())
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    dictdlg.DictInformation)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        # check
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[3, 7, 10], ['B5', 'B5', 'B5'], [1.2, 2.2, 2.2]])   # noqa

        # change dictionary name
        w = tt.eval_and_wait_window(w._act_dictinfo, (),
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum1')
        w = tt.eval_and_wait_window(w.tree._act_edit, ind,
                                    dictdlg.CreateNewDictionary)
        tt.eval_now(w.e_name.setText, ('enum2',))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    dictdlg.DictInformation)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[3, 7, 10], ['B5', 'B5', 'B5'], [1.2, 2.2, 2.2]])   # noqa

        # change dictionary keys
        w = tt.eval_and_wait_window(w._act_dictinfo, (),
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum2')
        w = tt.eval_and_wait_window(w.tree._act_edit, ind,
                                    dictdlg.CreateNewDictionary)
        tt.eval_now(w.e_spin.setValue, (4,))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    dictdlg.DictInformation)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], ['cont', 'b4p', None, 'b4p', 'b4p', 'b4g', None, 'b4p', 'b5g', None, None], [1.2, 2.3, 1.2, 1.3, 2.5, 1.2, 2.2, 1.1, 2.8, 2.2, None]])  # noqa
        self.assertListEqual(testutils.get_tmodel_raw(w.active_model), [[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], [0, 2, None, 2, 2, 1, None, 2, 3, None, None], [1.2, 2.3, 1.2, 1.3, 2.5, 1.2, 2.2, 1.1, 2.8, 2.2, None]])  # noqa

        # collapse + change dict values and keys
        tt.eval_and_wait_signal(w._act_collapse_all, (),
                                w.active_model_repr_changed)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), ["cont-1-2-noF", "b4p-2-5-F", "##-1-5-noF", "b4p-3-5-F", "b4p-4-5-F", "b4g-2-5-F", "##-5-3-noF", "b4p-2-5-noF", "b5g-1-3-noF", "##-1-5-noF", "##-10-20-"])   # noqa
        w = tt.eval_and_wait_window(w._act_dictinfo, (),
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum2')
        w = tt.eval_and_wait_window(w.tree._act_edit, ind,
                                    dictdlg.CreateNewDictionary)
        tt.eval_now(w.e_spin.setValue, (3,))
        tt.eval_now(mto.table_cell_dclick, (0, 1, w.e_table))
        tt.eval_now(mto.type_text, 'CONT')
        tt.eval_now(mto.press_enter, ())
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    dictdlg.DictInformation)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), ["CONT-1-2-noF", "b4p-2-5-F", "##-1-5-noF", "b4p-3-5-F", "b4p-4-5-F", "b4g-2-5-F", "##-5-3-noF", "b4p-2-5-noF", "##-1-3-noF", "##-1-5-noF", "##-10-20-"])   # noqa
        tt.eval_and_wait_signal(w._act_uncollapse_all, (),
                                w.active_model_repr_changed)

        # remove dictionary
        w = tt.eval_and_wait_window(w._act_dictinfo, (),
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum2')
        tt.eval_now(w.tree._act_rem, ind)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), [0, 2, None, 2, 2, 1, None, 2, None, None, None])  # noqa


proj = projroot.ProjectDB()
qApp = QtWidgets.QApplication(sys.argv)
win = mainwin.MainWindow(proj)
win.show()

mto = testutils.MainThreadObject()
tt = testutils.TestThread(mto, TestRunner, qApp)
tt.start()
qApp.exec_()
