""" Usage:
    1) comment/uncomment alltests_run[...] to define needed tests
    2) from root project directory run:
       > python3 -m utest.guitest

    Creating a new test:
    1) test name should start with 'test_'
    2) add test name to alltests list
    3) add a new line to "alltests[<test name>] = False" in order to
       easily switch it
    4) create a <test name> functon in TestRunner class
    5) this function should start with

        if not alltests_run[<test name>]:
            return
        tt.eval_now(win._close_database, ())
        w = tt.wait_window(mainwin.MainWindow)
"""
import sys
import unittest
from PyQt5 import QtWidgets, QtCore
from prog import basic, projroot, bopts, command
from bgui import mainwin, dlgs, importdlgs, dictdlg, filtdlg, colinfodlg, joindlg  # noqa
from utest import testutils     # noqa

basic.set_log_message('file: ' + bopts.BiostataOptions.logfile())
basic.set_ignore_exception(False)

alltests = ['test_import_txt', 'test_import_xls', 'test_changedict',
            'test_changecols', 'test_jointabs']
alltests_run = {x: True for x in alltests}

# alltests_run['test_import_txt'] = False
# alltests_run['test_import_xls'] = False
# alltests_run['test_changedict'] = False
# alltests_run['test_changecols'] = False
# alltests_run['test_jointabs'] = False


class TestRunner(unittest.TestCase):
    def tearDown(self):
        ''
        tt.eval_now(win.acts['Save as...'].saveto, ('dbg.db'))

    def test_import_txt(self):
        if not alltests_run['test_import_txt']:
            return
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        w = tt.wait_window(mainwin.MainWindow)

        # open import dialog import table
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
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
        tt.eval_and_wait_signal(w.run_act, "Collapse all categories",
                                w.active_model_repr_changed)
        col = testutils.get_tmodel_raw_column(w.active_model, 1)
        self.assertListEqual(
            col, ['no-1-2-noF', 'b4p-2-5-F', 'b5p-1-5-noF', 'b4p-3-5-F',
                  'b4p-4-5-F', 'b4g-2-5-F', 'b5p-5-3-noF', 'b4p-2-5-noF',
                  'b5g-1-3-noF', 'b5p-1-5-noF', '##-10-20-'])
        col = testutils.get_tmodel_raw_column(w.active_model, 2)
        self.assertListEqual(col, [0.22, 1.01, 0.12, 1.51, 2.23, 0.24, 3.42,
                                   0.41, 0.22, 2.22, None])

    def test_import_xls(self):
        if not alltests_run['test_import_xls']:
            return
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
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
        self.assertEqual(w.wtab.tabText(0).replace('&', ''), 'Table1')

    def test_changedict(self):
        if not alltests_run['test_changedict']:
            return
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
            dlgs.ImportTablesDlg)

        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t2.xlsx'),
            "w.odata().format == 'xlsx'", {'w': w})

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportXlsx)

        tt.emit_now(w.spec.sig_set_odata_entry, ('range', ''))
        tt.emit_now(w.spec.sig_set_odata_entry, ('read_cap', True))
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
            w.run_act, 'Add filter...', filtdlg.EditFilterDialog)
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
            w.run_act, "Add filter...", filtdlg.EditFilterDialog)
        tt.eval_now(w.frows[0].cb[2].setCurrentText, '"biochar type"')
        tt.eval_now(w.frows[0].cb[3].setCurrentText, '!=')
        tt.eval_now(w.frows[0].cb[4].setCurrentText, 'b5p')
        tt.eval_now(w.filter_cb.setChecked, QtCore.Qt.Unchecked)
        tt.eval_now(w.filter_name.setText, 'FLT')
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[3, 7, 10], ['b5p', 'b5p', 'b5p'], [1.2, 2.2, 2.2]])   # noqa

        # change dictionary values
        w = tt.eval_and_wait_window(w.run_act, "Dictionaries...",
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
        w = tt.eval_and_wait_window(w.run_act, "Dictionaries...",
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
        w = tt.eval_and_wait_window(w.run_act, "Dictionaries...",
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
        tt.eval_and_wait_signal(w.run_act, 'Collapse all categories',
                                w.active_model_repr_changed)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), ["cont-1-2-noF", "b4p-2-5-F", "##-1-5-noF", "b4p-3-5-F", "b4p-4-5-F", "b4g-2-5-F", "##-5-3-noF", "b4p-2-5-noF", "b5g-1-3-noF", "##-1-5-noF", "##-10-20-"])   # noqa
        w = tt.eval_and_wait_window(w.run_act, 'Dictionaries...',
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
        # self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), ["CONT-1-2-noF", "b4p-2-5-F", "##-1-5-noF", "b4p-3-5-F", "b4p-4-5-F", "b4g-2-5-F", "##-5-3-noF", "b4p-2-5-noF", "##-1-3-noF", "##-1-5-noF", "##-10-20-"])   # noqa
        self.assertEqual(w.active_model.columnCount(), 2)
        tt.eval_and_wait_signal(w.run_act, 'Undo',
                                w.active_model_repr_changed)
        tt.eval_and_wait_signal(w.run_act, 'Remove all collapses',
                                w.active_model_repr_changed)

        # remove dictionary
        w = tt.eval_and_wait_window(w.run_act, 'Dictionaries...',
                                    dictdlg.DictInformation)
        tt.eval_now(w.tree.setFocus, QtCore.Qt.MouseFocusReason)
        ind = w.tree.index_by_cap('enum2')
        tt.eval_now(w.tree._act_rem, ind)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), [0, 2, None, 2, 2, 1, None, 2, 3, None, None])  # noqa

    def test_changecols(self):
        if not alltests_run['test_changecols']:
            return
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
            dlgs.ImportTablesDlg)

        # enter filename
        tt.emit_now(w.sig_set_odata_entry, ('filename', 'test_db/t3.xlsx'))

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    importdlgs.ImportXlsx)
        # load
        tt.emit_now(w.spec.sig_set_odata_entry, ('read_cap', False))
        tt.emit_now(w.spec.sig_set_odata_entry, ('range', 'C7:H16'))
        tt.eval_and_wait_signal(w.load_button.click, (),
                                w.data_was_loaded)
        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 1), ['A', 'H', 'K', '', 'E', 'H', 'G', 'F', 'F', 'Q'])   # noqa)

        # Column 5 to ENUM and change shortname
        w = tt.eval_and_wait_window(
            w.run_act, 'Tables && columns...',
            colinfodlg.TablesInfo)

        tt.eval_and_wait_signal(mto.view_item_click, (w.e_tree, 'Column 5'),
                                w.e_tree.item_changed)
        frame = w.info_frame.frames['t3,Column 5']
        self.assertTrue(frame.isVisible())
        # rename
        mto.focus_widget(frame.e_name)
        mto.press_ctrl_a()
        tt.eval_and_wait_true(mto.press_delete, (),
                              "f.e_name.text() == ''", {'f': frame})
        tt.eval_and_wait_true(mto.type_text, 'Col5',
                              "f.e_name.text() == 'Col5'", {'f': frame})
        mto.focus_widget(frame.e_shortname)
        mto.press_ctrl_a()
        tt.eval_and_wait_true(mto.press_delete, (),
                              "f.e_shortname.text() == ''", {'f': frame})
        tt.eval_and_wait_true(mto.type_text, '5',
                              "f.e_shortname.text() == '5'", {'f': frame})
        # press configure
        w = tt.eval_and_wait_window(mto.button_click, frame.tpconv_button,
                                    colinfodlg.ConvertDialog)
        tt.eval_and_wait_true(w.cb.setCurrentIndex, 3,
                              "w.cb.currentText().endswith('real to keys')",
                              {'w': w})
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox),
                                    colinfodlg.TablesInfo)
        # final ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 4), ['C', 'J', 'C', 'I', 'C', 'K', 'C', 'H', None, 'C'])  # noqa

        # collapse all
        tt.eval_and_wait_signal(w.run_act, 'Collapse all categories',
                                w.active_model_repr_changed)
        self.assertEqual(w.active_model.dt.visible_columns[1].name, 'Column 1-Column 2-Column 3-5')   # noqa
        # uncollapse all
        tt.eval_and_wait_signal(
                w.run_act, 'Remove all collapses',
                w.active_model_repr_changed)
        self.assertEqual(w.active_model.dt.n_cols(), 7)

        # add a global filter
        w = tt.eval_and_wait_window(
                w.run_act, 'Add filter...',
                filtdlg.EditFilterDialog)
        tt.eval_and_wait_true(w.filter_cb.setChecked, (QtCore.Qt.Unchecked),
                              "w.filter_name.isEnabled()", {'w': w})
        tt.eval_now(w.frows[0].cb[2].setCurrentText, ('"Col5"'))
        tt.eval_now(w.frows[0].cb[3].setCurrentText, ('NULL'))
        tt.eval_now(w.frows[1].cb[0].setCurrentText, ('OR'))
        tt.eval_now(w.frows[1].cb[2].setCurrentText, ('"Column 3"'))
        tt.eval_now(w.frows[1].cb[3].setCurrentText, ('=='))
        tt.eval_now(w.frows[1].cb[4].setCurrentText, ("No"))

        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    filtdlg.EditFilterDialog)
        tt.eval_now(w.frows[1].cb[4].setCurrentText, ("'No'"))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertEqual(w.active_model.dt.n_rows(), 4)

        # show only two columns: Col5 and Column 4
        tt.eval_now(w.dock_colinfo.setVisible, (True))
        tt.eval_now(w.dock_colinfo.tab.model().set_checked,
                    ['Col5', 'Column 4'])
        tt.eval_now(mto.dialog_applyclick, (w.dock_colinfo.buttonbox))
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[1, 5, 6, 10], ['C', 'C', 'K', 'C'], [2.94117647058823, 20.5882352941176, 17.6470588235294, 11.7647058823529]])   # noqa

        # make a copied table
        w = tt.eval_and_wait_window(
                w.run_act, 'New table from visible...',
                dlgs.NewTableFromVisible)
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('include_source_id', True),
            'w.odata().include_source_id', {'w': w})
        tt.eval_and_wait_signal(
                mto.dialog_okclick, (w.buttonbox),
                win.active_model_changed)
        w = win
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[1, 2, 3, 4], [1, 5, 6, 10], ['C', 'C', 'K', 'C'], [2.94117647058823, 20.5882352941176, 17.6470588235294, 11.7647058823529]])  # noqa

        # rename Table 1 to t3 (repeating name)
        w = tt.eval_and_wait_window(
                w.run_act, 'Tables && columns...',
                colinfodlg.TablesInfo)
        frame = w.info_frame.frames['Table 1']
        tt.eval_and_wait_true(
                mto.view_item_click, (w.e_tree, 'Table 1'),
                'f.isVisible()', {'f': frame})
        mto.focus_widget(frame.e_name)
        mto.press_ctrl_a()
        tt.eval_and_wait_true(mto.press_delete, (),
                              "f.e_name.text() == ''", {'f': frame})
        tt.eval_and_wait_true(mto.type_text, 't3',
                              "f.e_name.text() == 't3'", {'f': frame})
        # repeating names warning
        w = tt.eval_and_wait_window(
                mto.dialog_okclick, w.buttonbox,
                QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(
                mto.dialog_okclick, w, colinfodlg.TablesInfo)
        frame = w.info_frame.frames['t3']
        tt.eval_and_wait_true(
                mto.view_item_click, (w.e_tree, 't3'),
                'f.isVisible()', {'f': frame})
        mto.focus_widget(frame.e_name)
        mto.press_ctrl_a()
        tt.eval_and_wait_true(mto.press_delete, (),
                              "f.e_name.text() == ''", {'f': frame})
        tt.eval_and_wait_true(mto.type_text, 't2',
                              "f.e_name.text() == 't2'", {'f': frame})
        w = tt.eval_and_wait_window(
                mto.dialog_okclick, w.buttonbox, mainwin.MainWindow)

        # modify dictionary A-Z
        w = tt.eval_and_wait_window(
                w.run_act, 'Dictionaries...',
                dictdlg.DictInformation)
        ind = testutils.search_index_by_contents(w.tree, 'A-Z')
        w = tt.eval_and_wait_window(w.tree._act_edit, (ind),
                                    dictdlg.CreateNewDictionary)
        ind = testutils.search_index_by_contents(w.e_table, 10)
        tt.eval_now(mto.table_cell_dclick,
                    (ind.row(), ind.column(), w.e_table))
        tt.eval_now(mto.type_text, '101')
        tt.eval_now(mto.press_enter, ())
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox),
                                    dictdlg.DictInformation)
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox),
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 'Col5'), ['C', 'C', None, 'C'])   # noqa
        tt.eval_and_wait_signal(w.wtab.setCurrentIndex, 0,
                                w.active_model_changed)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 'Col5'), ['C', 'J', 'C', 'I', 'C', None, 'C', 'H', None, 'C'])  # noqa

        # remove dictionary A-Z
        w = tt.eval_and_wait_window(
                w.run_act, 'Dictionaries...',
                dictdlg.DictInformation)
        ind = testutils.search_index_by_contents(w.tree, 'A-Z')
        tt.eval_now(w.tree._act_rem, (ind))
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox),
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 'Col5'), [2, 9, 2, 8, 2, None, 2, 7, None, 2])   # noqa
        tt.eval_and_wait_signal(w.wtab.setCurrentIndex, 1,
                                w.active_model_changed)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 'Col5'), [2, 2, None, 2])   # noqa

        # group rows
        tt.eval_and_wait_signal(w.wtab.setCurrentIndex, 0,
                                w.active_model_changed)
        w = tt.eval_and_wait_window(
                w.run_act, 'Group rows...',
                dlgs.GroupRowsDlg)
        e = w.odata().cat
        e['All categories']['Col5'] = True
        tt.emit_now(w.sig_set_odata_entry, ('cat', e))
        w = tt.eval_and_wait_window(
                mto.dialog_okclick, w.buttonbox, mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel_column(w.active_model, 'id'), [None, 2, 4, None, 8])  # noqa
        # fold/unfold
        w = tt.eval_and_wait_window(
                mto.view_context_menu, (w.tabframes[0], (2, 1)),
                QtWidgets.QMenu)
        w = tt.eval_and_wait_window(mto.menu_item_click, (w, 'Fold/Unfold'),
                                    mainwin.MainWindow)
        # copy id with subdatas to clipboard
        w = tt.eval_and_wait_window(
                mto.view_context_menu, (w.tabframes[0], (2, 0)),
                QtWidgets.QMenu)
        w = tt.eval_and_wait_window(mto.menu_item_click,
                                    (w, 'Copy to clipboard'),
                                    mainwin.MainWindow)
        self.assertEqual(qApp.clipboard().text(), '(1, 3, 5, 7, 10)')

        # fold/unfold for a None item
        w = tt.eval_and_wait_window(
                mto.view_context_menu, (w.tabframes[0], (5, 0)),
                QtWidgets.QMenu)
        w = tt.eval_and_wait_window(mto.menu_item_click, (w, 'Fold/Unfold'),
                                    mainwin.MainWindow)
        # copy id with subdatas to clipboard
        w = tt.eval_and_wait_window(
                mto.view_context_menu, (w.tabframes[0], (5, 0)),
                QtWidgets.QMenu)
        w = tt.eval_and_wait_window(mto.menu_item_click,
                                    (w, 'Copy to clipboard'),
                                    mainwin.MainWindow)
        self.assertEqual(qApp.clipboard().text(), '(6, 9)')

    def test_jointabs(self):
        if not alltests_run['test_jointabs']:
            return
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        w = tt.wait_window(mainwin.MainWindow)

        # import dialog
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
            dlgs.ImportTablesDlg)
        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t4.xlsx'),
            "w.odata().format == 'xlsx'", {'w': w})
        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportXlsx)
        tt.emit_now(w.spec.sig_set_odata_entry, ('range', ''))
        tt.emit_now(w.spec.sig_set_odata_entry, ('read_cap', True))
        tt.emit_now(w.spec.sig_set_odata_entry, ('sheetname', 'Sheet1'))
        tt.emit_now(w.spec.sig_set_odata_entry, ('tabname', 'Tab1'))
        tt.eval_now(mto.button_click, (w.load_button))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        # import dialog
        w = tt.eval_and_wait_window(
            w.run_act, 'Import tables...',
            dlgs.ImportTablesDlg)
        # enter filename
        tt.emit_and_wait_true(
            w.sig_set_odata_entry, ('filename', 'test_db/t4.xlsx'),
            "w.odata().format == 'xlsx'", {'w': w})
        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, (w.buttonbox,),
                                    importdlgs.ImportXlsx)
        tt.emit_now(w.spec.sig_set_odata_entry, ('range', ''))
        tt.emit_now(w.spec.sig_set_odata_entry, ('read_cap', True))
        tt.emit_now(w.spec.sig_set_odata_entry, ('sheetname', 'Sheet2'))
        tt.emit_now(w.spec.sig_set_odata_entry, ('tabname', 'Tab2'))
        tt.eval_now(mto.button_click, (w.load_button))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        # join dialog
        w = tt.eval_and_wait_window(
                w.run_act, 'Join tables...',
                joindlg.JoinTablesDialog)
        tt.eval_now(w.e_tabname.setText, 'JoinTab')
        itm1 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab1')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm1, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        itm2 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab2')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm2, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        # set keys
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[0].setCurrentText, ("А.4"))
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[1].setCurrentText, ("Б.2"))
        # tt.eval_now(mto.button_click, (w.e_tabkeys.frows[0].b_add))
        # tt.eval_now(w.e_tabkeys.frows[1].cb_col[0].setCurrentText, ("А.2"))
        # tt.eval_now(w.e_tabkeys.frows[1].cb_col[1].setCurrentText, ("Б.1"))

        # check columns
        tt.eval_now(mto.table_cell_check, (0, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (4, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (0, 0, w.e_tabcols.tabs[1].wtab))

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[1, 2], [1, 2], [2, 8], [2.3, 3.1]])  # noqa
        self.assertEqual(
            w.wtab.tabText(w.wtab.currentIndex()).replace('&', ''), "JoinTab")

        tt.eval_and_wait_signal(
                w.run_act, 'Remove active table',
                w.active_model_changed)

        # join dialog
        w = tt.eval_and_wait_window(
                w.run_act, 'Join tables...',
                joindlg.JoinTablesDialog)
        itm1 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab1')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm1, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        itm2 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab2')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm2, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        # set keys
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[0].setCurrentText, ("А.1"))
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[1].setCurrentText, ("А.1"))
        tt.eval_now(mto.button_click, (w.e_tabkeys.frows[0].b_add))
        tt.eval_now(w.e_tabkeys.frows[1].cb_col[0].setCurrentText, ("А.4"))
        tt.eval_now(w.e_tabkeys.frows[1].cb_col[1].setCurrentText, ("Б.2"))

        # check columns
        tt.eval_now(mto.table_cell_check, (0, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (1, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (4, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (0, 0, w.e_tabcols.tabs[1].wtab))

        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    QtWidgets.QMessageBox)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w, mainwin.MainWindow)
        self.assertListEqual(testutils.get_tmodel(w.active_model), [[1], [1], ['Да'], [2], [2.3]])  # noqa

        # create dictionaries
        w = tt.eval_and_wait_window(
                w.run_act, 'Tables && columns...',
                colinfodlg.TablesInfo)
        tt.eval_now(mto.view_item_click, (w.e_tree, 'А.1'))
        frame = w.info_frame.frames['Tab1,А.1']
        w = tt.eval_and_wait_window(mto.button_click, (frame.tpconv_button),
                                    colinfodlg.ConvertDialog)
        tt.eval_now(w.cb.setCurrentIndex, 5)
        w = tt.eval_and_wait_window(
                w.dictcb.setCurrentText, '_ create new dict',
                dictdlg.CreateNewDictionary)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    colinfodlg.ConvertDialog)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    colinfodlg.TablesInfo)
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        # join dialog
        w = tt.eval_and_wait_window(
                w.run_act, 'Join tables...',
                joindlg.JoinTablesDialog)
        itm1 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab1')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm1, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        itm2 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab2')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm2, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        # set keys
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[0].setCurrentText, ("А.1"))
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[1].setCurrentText, ("А.1"))
        self.assertTrue(w.e_tabkeys.frows[0].w_label.isVisible())
        # check
        tt.eval_now(mto.table_cell_check, (1, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (1, 0, w.e_tabcols.tabs[1].wtab))
        # rename Tab1.A1
        tt.eval_now(mto.table_cell_dclick, (1, 2, w.e_tabcols.tabs[1].wtab))
        tt.eval_now(mto.type_text, ('AAAA'))
        tt.eval_now(mto.press_enter, ())
        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertEqual(w.active_model.dt.n_rows(), 22)

        # with grouping
        tt.eval_and_wait_signal(
                w.wtab.setCurrentIndex, 0, w.active_model_changed)
        w = tt.eval_and_wait_window(
                w.run_act, 'Group rows...',
                dlgs.GroupRowsDlg)
        e = w.odata().cat
        e['All categories']['А.1'] = True
        tt.emit_now(w.sig_set_odata_entry, ('cat', e))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)

        tt.eval_and_wait_signal(
                w.wtab.setCurrentIndex, 1, w.active_model_changed)
        w = tt.eval_and_wait_window(
                w.run_act, 'Group rows...',
                dlgs.GroupRowsDlg)
        e = w.odata().cat
        e['All categories']['А.1'] = True
        tt.emit_now(w.sig_set_odata_entry, ('cat', e))
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        w = tt.eval_and_wait_window(
                w.run_act, 'Join tables...',
                joindlg.JoinTablesDialog)
        itm1 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab1')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm1, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        itm2 = testutils.search_index_by_contents(w.e_tabchoice, 'Tab2')
        tt.eval_now(w.e_tabchoice.model().setData,
                    (itm2, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole))
        # set keys
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[0].setCurrentText, ("А.1"))
        tt.eval_now(w.e_tabkeys.frows[0].cb_col[1].setCurrentText, ("А.1"))
        self.assertTrue(w.e_tabkeys.frows[0].w_label.isVisible())
        # check
        tt.eval_now(mto.table_cell_check, (1, 0, w.e_tabcols.tabs[0].wtab))
        tt.eval_now(mto.table_cell_check, (1, 0, w.e_tabcols.tabs[1].wtab))
        # rename Tab1.A1
        tt.eval_now(mto.table_cell_dclick, (1, 2, w.e_tabcols.tabs[1].wtab))
        tt.eval_now(mto.type_text, ('AAAA'))
        tt.eval_now(mto.press_enter, ())
        # ok
        w = tt.eval_and_wait_window(mto.dialog_okclick, w.buttonbox,
                                    mainwin.MainWindow)
        self.assertEqual(w.active_model.dt.n_rows(), 3)

        # save and load
        tt.set_tmp_wait_times(1, 10)
        tt.eval_and_wait_signal(w.acts['Save as...'].saveto, ('dbg.db'),
                                w.database_saved)
        self.assertEqual(w.windowTitle(), 'dbg.db - BioStat Analyser')
        tt.eval_and_wait_signal(win.run_act, 'New database',
                                win.database_closed)
        tt.eval_and_wait_signal(win.acts['Open database'].load, 'dbg.db',
                                win.database_opened)
        tt.recover_wait_times()

        self.assertEqual(w.active_model.dt.n_rows(), 3)
        d = [next((x.name for x in y.dt.all_columns)) for y in w.models]
        self.assertListEqual(['id']*5, d)

proj = projroot.ProjectDB()
opts = bopts.BiostataOptions()
opts.load()
flow = command.CommandFlow()
qApp = QtWidgets.QApplication(sys.argv)
win = mainwin.MainWindow(flow, proj, opts)
win.show()

mto = testutils.MainThreadObject()
tt = testutils.TestThread(mto, TestRunner, qApp)
tt.start()
qApp.exec_()
