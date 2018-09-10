import copy
import unittest
from prog import basic, projroot
from fileproc import import_tab
from bdata import derived_tabs
from prog import valuedict
from utest import testutils

basic.set_log_message('file: ~log')
basic.set_ignore_exception(False)

proj = projroot.ProjectDB()


class Object:
    pass


class Test1(unittest.TestCase):
    def setUp(self):
        proj.close_main_database()

    def tearDown(self):
        proj.relocate_and_commit_all_changes('a.db')

    def test_load_from_txt_1(self):
        opt = Object()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = 'True'
        opt.col_sep = 'whitespaces'
        opt.row_sep = 'newline'
        opt.colcount = -1

        t = import_tab.split_plain_text('test_db/t1.dat', opt)
        self.assertEqual(len(t), 7)
        self.assertEqual(len(t[0]), 3)

        cp1 = import_tab.autodetect_types(t)
        self.assertListEqual(cp1, ['TEXT', 'TEXT', 'TEXT'])
        cp1 = import_tab.autodetect_types(t[1:])
        self.assertListEqual(cp1, ['INT', 'INT', 'REAL'])

        frm = [("c{}".format(i), tp, None) for i, tp in enumerate(cp1)]
        dt = derived_tabs.explicit_table('t1', frm, t[1:], proj)
        dt.update()
        self.assertEqual(dt.n_cols(), 4)
        self.assertEqual(dt.n_rows(), 6)
        self.assertTrue(dt.need_rewrite)

        try:
            proj.commit_all_changes()
            self.assertTrue(False)
        except:
            self.assertTrue(True)

    def test_load_from_txt_2(self):
        opt = Object()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = 'True'
        opt.col_sep = 'tabular'
        opt.row_sep = 'newline'
        opt.colcount = -1

        t = import_tab.split_plain_text('test_db/t2.dat', opt)
        self.assertEqual(len(t), 12)
        self.assertEqual(len(t[0]), 7)

        cp1 = import_tab.autodetect_types(t[1:])
        self.assertListEqual(cp1, ['TEXT', 'INT', 'INT', 'TEXT', 'REAL',
                                   'REAL', 'REAL'])

        # import as TEXT
        frm = [("c{}".format(i), tp, None) for i, tp in enumerate(cp1)]
        dt = derived_tabs.explicit_table('t1', frm, copy.deepcopy(t[1:]), proj)
        dt.update()

        self.assertEqual(dt.n_cols(), 8)
        self.assertEqual(dt.n_rows(), 11)
        self.assertTrue(dt.need_rewrite)
        self.assertEqual(dt.get_value(10, 1), '')
        self.assertEqual(dt.get_value(10, 2), 10)
        self.assertEqual(dt.get_value(10, 3), 20)
        self.assertEqual(dt.get_value(10, 4), '')
        self.assertEqual(dt.get_value(10, 5), None)
        self.assertEqual(dt.get_value(9, 5), 2.22)
        self.assertEqual(dt.get_value(4, 1), 'b4p')

        # import with dictionaries
        dct = valuedict.Dictionary('ff', 'BOOL', [0, 1],
                                   ['noF', 'F'])
        proj.add_dictionary(dct)
        dct = valuedict.Dictionary('bio', 'ENUM', [0, 1, 2],
                                   ['no', 'b4g', 'b5p'])
        proj.add_dictionary(dct)
        frm[3] = ("c3", 'BOOL', 'ff')
        frm[0] = ("c0", 'ENUM', 'bio')
        dt = derived_tabs.explicit_table('t2', frm, copy.deepcopy(t[1:]), proj)
        dt.update()

        self.assertListEqual(testutils.get_dtab_column(dt, 1),
                             ['no', None, 'b5p', None, None, 'b4g',
                              'b5p', None, None, 'b5p', None])
        self.assertListEqual(testutils.get_dtab_raw_column(dt, 1),
                             [0, None, 2, None, None,
                              1, 2, None, None, 2, None])

    def test_load_from_xlsx(self):
        opt1 = Object()
        opt1.sheetname = 'tab1'
        opt1.range = ''

        opt2 = Object()
        opt2.firstline = 0
        opt2.lastline = -1
        opt2.comment_sign = '#'
        opt2.ignore_blank = 'True'
        opt2.col_sep = 'tabular'
        opt2.row_sep = 'newline'
        opt2.colcount = -1

        txls = import_tab.parse_xlsx_file('test_db/t2.xlsx', opt1)
        tdat = import_tab.split_plain_text('test_db/t2.dat', opt2)

        # import from text and xls gives same result
        self.assertListEqual(tdat, txls)

        dct = valuedict.Dictionary('bio', 'ENUM', [0, 1, 2, 3, 4, 5],
                                   ['', 'no', 'b4g', 'b5p', 'b4p', 'b5g'])
        proj.add_dictionary(dct)

        cp1 = import_tab.autodetect_types(txls[1:])
        frm = [("c{}".format(i), tp, None) for i, tp in enumerate(cp1)]
        frm[0] = ("c0", "ENUM", "bio")
        dt = derived_tabs.explicit_table('t2', frm, txls[1:], proj)
        dt.update()
        # import with dictionary with an empty value
        self.assertListEqual(testutils.get_dtab_column(dt, 1),
                             ['no', 'b4p', 'b5p', 'b4p', 'b4p', 'b4g',
                              'b5p', 'b4p', 'b5g', 'b5p', ''])
        self.assertListEqual(testutils.get_dtab_raw_column(dt, 1),
                             [1, 4, 3, 4, 4, 2, 3, 4, 5, 3, 0])

if __name__ == '__main__':
    unittest.main()
