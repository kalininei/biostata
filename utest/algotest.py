import copy
import unittest
from prog import basic, projroot
from fileproc import import_tab
from bdata import derived_tabs, filt, convert
from prog import valuedict
from utest import testutils

basic.set_log_message('file: ~log')
basic.set_ignore_exception(False)

proj = projroot.ProjectDB()


class Object:
    pass


class Test1(unittest.TestCase):
    def setUp(self):
        ''
        proj.close_main_database()

    def tearDown(self):
        ''
        proj.relocate_and_commit_all_changes('~a.db')

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

    def test_adddict(self):
        # load dictionaries
        dct = valuedict.Dictionary('a', 'BOOL', [0, 1],
                                   ['', 'Q'])
        proj.add_dictionary(dct)
        dct = valuedict.Dictionary('b', 'ENUM', [0, 10, 20, 30, 40],
                                   ['A', 'B', 'AA', 'AB', 'BB'])
        proj.add_dictionary(dct)

        # load database from t3.dat
        opt = Object()
        opt.firstline = 4
        opt.lastline = 5
        opt.comment_sign = '#'
        opt.ignore_blank = 'True'
        opt.col_sep = 'in double quotes'
        opt.row_sep = 'no (use column count)'
        opt.colcount = 3

        t = import_tab.split_plain_text('test_db/t3.dat', opt)
        self.assertEqual(len(t), 6)
        self.assertEqual(len(t[0]), 3)

        frm = [('c1', 'BOOL', 'a'), ('c2', 'REAL', None), ('c3', 'ENUM', 'b')]

        # import with dictionaries
        dt = derived_tabs.explicit_table('t1', frm, t, proj)
        dt.update()
        proj.add_table(dt)

        self.assertListEqual(testutils.get_dtab(dt),
                             [[1, 2, 3, 4, 5, 6],
                              ['', '', 'Q', 'Q', 'Q', ''],
                              ['A', 'B', None, 'AB', 'BB', 'AB'],
                              [3.0, 43.0, None, 3.0, 22.0, None]])

        self.assertListEqual(testutils.get_dtab_raw(dt),
                             [[1, 2, 3, 4, 5, 6],
                              [0, 0, 1, 1, 1, 0],
                              [0, 10, None, 30, 40, 30],
                              [3.0, 43.0, None, 3.0, 22.0, None]])

        # save database
        self.assertTrue(dt.need_rewrite)
        proj.relocate_and_commit_all_changes('~a.db')
        self.assertFalse(dt.need_rewrite)

        # change dictionaries values only
        anew = valuedict.Dictionary('a', 'BOOL', [0, 1], ['A', 'B'])
        bnew = valuedict.Dictionary('b2', 'ENUM', [0, 10, 30, 40],
                                    ['A', 'B', 'C', 'D'])
        proj.change_dictionaries({'a': anew, 'b': bnew})
        self.assertFalse(dt.need_rewrite)
        dt.update()
        self.assertListEqual(testutils.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', 'B', None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        self.assertListEqual(testutils.get_dtab_raw(dt), [[1, 2, 3, 4, 5, 6], [0, 0, 1, 1, 1, 0], [0, 10, None, 30, 40, 30], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa

        # change dictionaries with converting to None
        bnew = valuedict.Dictionary('b2', 'ENUM', [0, 20, 30, 40],
                                    ['A', 'B', 'C', 'D'])
        proj.change_dictionaries({'b2': bnew})
        self.assertTrue(dt.need_rewrite)
        dt.update()
        self.assertListEqual(testutils.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', None, None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        self.assertListEqual(testutils.get_dtab_raw(dt), [[1, 2, 3, 4, 5, 6], [0, 0, 1, 1, 1, 0], [0, None, None, 30, 40, 30], [3.0, 43.0, None, 3.0, 22.0, None]])   # noqa

        # remove dictionaries with filters and convert to int
        flt1 = filt.Filter.from_xml_string("""<F><NAME>f1</NAME><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c1', 'BOOL', 'a')",'==','0']</E></F>""")    # noqa
        flt2 = filt.Filter.from_xml_string("""<F><NAME/><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'REAL', None)",'>',"('c3', 'ENUM', 'b2')"]</E></F>""")    # noqa
        dt.add_filter(flt1, True)
        dt.add_filter(flt2, True)
        dt.update()
        self.assertEqual(len(dt.all_anon_filters), 1)
        self.assertEqual(len(dt.used_filters), 2)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertListEqual(testutils.get_dtab(dt), [[4, 5], ['B', 'B'], ['C', 'D'], [3.0, 22.0]])   # noqa

        proj.change_dictionaries({'a': None})
        dt.update()
        self.assertEqual(len(dt.all_anon_filters), 1)
        self.assertEqual(len(dt.used_filters), 1)
        self.assertEqual(len(proj.named_filters), 0)
        self.assertListEqual(testutils.get_dtab(dt), [[4, 5], [1, 1], ['C', 'D'], [3.0, 22.0]])  # noqa

        # rename dictionary: all filters should remain
        bnew = valuedict.Dictionary('b3', 'ENUM', [0, 20, 30, 40],
                                    ['A', 'BB', 'CC', 'DD'])
        proj.change_dictionaries({'b2': bnew})
        dt.update()
        self.assertListEqual(testutils.get_dtab(dt), [[4, 5], [1, 1], ['CC', 'DD'], [3.0, 22.0]])  # noqa

        # change key structure: filters should be removed
        bnew = valuedict.Dictionary('b3', 'ENUM', [0, 20, 30, 40, 50],
                                    ['A', 'B', 'C', 'D', 'E'])
        proj.change_dictionaries({'b3': bnew})
        dt.update()
        self.assertEqual(len(dt.used_filters), 0)

        # remove dict: all columns should be numeric
        proj.change_dictionaries({'b3': None})
        dt.update()
        self.assertListEqual(testutils.get_dtab(dt),
                             testutils.get_dtab_raw(dt))

    def test_converts(self):
        opt = Object()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'whitespaces'
        opt.row_sep = 'newline'
        opt.colcount = -1

        # load all as TEXT
        t = import_tab.split_plain_text('test_db/t1.dat', opt)
        frm = [('c1', 'TEXT', None), ('c2', 'TEXT', None),
               ('c3', 'TEXT', None)]
        dt1 = derived_tabs.explicit_table('t1', frm, copy.deepcopy(t[1:]),
                                          proj)
        dt1.update()
        proj.add_table(dt1)
        self.assertListEqual(testutils.get_dtab_raw(dt1), [[1, 2, 3, 4, 5, 6], ['0', '1', '1', '0', '1', '0'], ['0', '1', '2', '3', '4', '5'], ['1.1', '2.34', '3.33', '4.33', '6.28', '3.54']])  # noqa

        # load all as INT
        frm = [('c1', 'INT', None), ('c2', 'INT', None),
               ('c3', 'INT', None)]
        dt2 = derived_tabs.explicit_table('t2', frm, copy.deepcopy(t[1:]),
                                          proj)
        dt2.update()
        proj.add_table(dt2)
        self.assertListEqual(testutils.get_dtab_raw(dt2), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [0, 1, 2, 3, 4, 5], [1, 2, 3, 4, 6, 4]])  # noqa

        # swap table names
        conv1 = convert.TableConverter(dt1)
        conv2 = convert.TableConverter(dt2)
        conv1.new_name = 't2'
        conv1.new_comment = 'This was a t1 table'
        conv2.new_name = 't1'
        conv1.apply()
        conv2.apply()
        self.assertListEqual(testutils.get_dtab(dt1),
                             testutils.get_dtab(proj.get_table('t2')))
        self.assertEqual(proj.get_table('t2').comment, 'This was a t1 table')
        self.assertEqual(proj.get_table('t1').comment, '')

        # add global filters
        # (anon for dt2): c2(int) < 3
        flt1 = filt.Filter.from_xml_string("""<F><NAME/><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'INT', None)",'&lt;','3']</E></F>""")    # noqa
        # f2: c2(int) > c3(int)
        flt2 = filt.Filter.from_xml_string("""<F><NAME>f2</NAME><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'INT', None)",'&gt;',"('c3', 'INT', None)"]</E></F>""")    # noqa
        dt2.add_filter(flt1, True)
        dt2.add_filter(flt2, True)
        dt2.update()
        try:
            dt1.add_filter(flt2, True)
            self.assertTrue(False)
        except:
            pass
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.used_filters), 0)
        self.assertEqual(len(dt2.used_filters), 2)
        self.assertListEqual(testutils.get_dtab(dt2), [[4, 5], [0, 1], [3, 4], [4, 6]])   # noqa

        # (anon for dt1): id filter
        flt3 = filt.IdFilter()
        filt.IdFilter.set_from_ilist(flt3, [1, 3, 4])
        dt1.add_filter(flt3, True)
        dt1.update()

        # swap columns of dt1
        cconv1 = convert.ColumnConverter(dt1, dt1.columns['c1'])
        cconv1.new_dim = 'm2'
        cconv1.new_comment = "This was a 'c1' column"
        cconv1.new_name = 'c2'
        cconv2 = convert.ColumnConverter(dt1, dt1.columns['c2'])
        cconv2.new_dim = 'm2'
        cconv2.new_comment = "This was a 'c2' column"
        cconv2.new_name = 'c1'
        conv = convert.TableConverter(dt1)
        conv.citems = [cconv1, cconv2]
        conv.apply()
        self.assertListEqual(testutils.get_dtab_column(dt1, 'c2'), ['1', '1', '0'])   # noqa
        self.assertEqual(dt1.columns['c2'].comment, "This was a 'c1' column")

        # c1-c2 collapse
        cc = dt2.merge_categories([dt2.columns['c2'], dt2.columns['c3']], '-')

        # rename columns of dt2
        conv = convert.TableConverter(dt2)
        cconv1 = convert.ColumnConverter(dt2, dt2.columns['c2'])
        cconv1.new_name = 'new name'
        cconv2 = convert.ColumnConverter(dt2, cc)
        cconv2.new_name = 'collapse23'
        conv.citems = [cconv1, cconv2]
        conv.apply()
        dt2.update()
        self.assertListEqual(testutils.get_dtab(dt2), [[4, 5, 6], [0, 1, 0], [3, 4, 5], [4, 6, 4], ['3-4', '4-6', '5-4']])   # noqa
        self.assertListEqual(testutils.get_dtab_column(dt2, 'collapse23'), ['3-4', '4-6', '5-4'])   # noqa
        try:
            dt2.add_filter(flt2)
            self.assertTrue(False)
        except:
            pass

        # rename back
        cconv1.new_name = 'c2'
        conv.apply()
        dt2.add_filter(flt2)
        dt2.update()
        self.assertListEqual(testutils.get_dtab(dt2), [[4, 5], [0, 1], [3, 4], [4, 6], ['3-4', '4-6']])   # noqa

        # remove columns
        conv = convert.TableConverter(dt2)
        conv1 = conv.colitem('c2')
        conv1.do_remove = True
        self.assertEqual(len(conv.implicit_removes()), 1)
        conv.apply()
        dt2.update()
        self.assertEqual(len(dt2.used_filters), 0)
        self.assertEqual(len(dt2.all_anon_filters), 0)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertListEqual(testutils.get_dtab(dt2), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [1, 2, 3, 4, 6, 4]])   # noqa

        # convert columns of dt1 (now it is text and has only id filter)
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c1')
        conv1.set_conversation(['INT', '', ''])
        conv.apply()
        dt1.update()
        self.assertListEqual(testutils.get_dtab(dt1),
                             testutils.get_dtab_raw(dt1))
        self.assertListEqual(testutils.get_dtab_column(dt1, "c1"), [1, 4, 5])

        # convert to bool dictionary
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.set_conversation(['BOOL', '0-1', 'text to values'])
        conv.apply()
        dt1.update()
        self.assertListEqual(testutils.get_dtab_column(dt1, 'c2'), ['1', '1', '0'])  # noqa
        self.assertListEqual(testutils.get_dtab_raw_column(dt1, 'c2'), [1, 1, 0])    # noqa

        # convert to another bool dictionary
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.set_conversation(['BOOL', 'Yes/No', 'keys to keys'])
        conv.apply()
        dt1.update()
        self.assertListEqual(testutils.get_dtab_column(dt1, 'c2'), ['Yes', 'Yes', 'No'])  # noqa
        self.assertListEqual(testutils.get_dtab_raw_column(dt1, 'c2'), [1, 1, 0])    # noqa

        # convert to enum
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c3')
        k, v = conv1.dictionary_prototype('real to keys')
        self.assertListEqual(k, [1, 2, 3, 4, 6])
        self.assertListEqual(v, ['', '', '', '', ''])
        k, v = conv1.dictionary_prototype('real to values')
        self.assertListEqual(k, [0, 1, 2, 3, 4, 5])
        self.assertListEqual(v, ['1.1', '2.34', '3.33', '3.54', '4.33', '6.28'])   # noqa

        dct = valuedict.Dictionary('tdict', 'ENUM', [1, 4], ['ONE', "FOUR"])
        proj.add_dictionary(dct)

        conv1.set_conversation(['ENUM', 'tdict', 'real to keys'])
        conv1.new_name = 'ccc'
        conv.apply()
        dt1.used_filters.clear()
        dt1.all_anon_filters.clear()
        dt1.update()
        self.assertListEqual(testutils.get_dtab_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa
        self.assertListEqual(testutils.get_dtab_raw_column(dt1, 'ccc'), [1, None, None, 4, None, 4])   # noqa

        conv1.set_conversation(['TEXT', '', 'values to text'])
        conv.apply()
        dt1.update()
        self.assertListEqual(testutils.get_dtab_raw_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa

        conv1.set_conversation(['ENUM', 'tdict', 'text to values'])
        conv.apply()
        dt1.update()
        self.assertListEqual(testutils.get_dtab_raw_column(dt1, 'ccc'), [1, None, None, 4, None, 4])   # noqa
        self.assertListEqual(testutils.get_dtab_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa

        conv1 = conv.colitem('ccc')
        conv1.set_conversation(['INT', '', 'keys to int'])
        conv1.new_name = 'c3'

        conv1 = conv.colitem('c2')
        conv1.new_shortname = 'b'
        conv1.set_conversation(['INT', '', 'keys to int'])

        conv1 = conv.colitem('c1')
        conv1.new_shortname = 'a'
        conv.apply()
        dt1.update()

        dt1.merge_categories([dt1.columns['c1'], dt1.columns['c2']], '-')
        dt1.merge_categories([dt1.columns['a-b'], dt1.columns['c3']], '-')
        dt1.update()
        self.assertListEqual(testutils.get_dtab(dt1), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [0, 1, 2, 3, 4, 5], [1, None, None, 4, None, 4], ['0-0', '1-1', '2-1', '3-0', '4-1', '5-0'], ['0-0-1', '1-1-##', '2-1-##', '3-0-4', '4-1-##', '5-0-4']])   # noqa

        self.assertTrue(flt2.is_applicable(dt1))
        dt1.add_filter(flt1, True)
        dt1.add_filter(flt2, True)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.all_anon_filters), 1)
        self.assertEqual(len(dt1.used_filters), 2)
        dt1.update()
        self.assertListEqual(testutils.get_dtab(dt1), [[], [], [], [], [], []])   # noqa

        # implicit removes
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c1')
        conv1.set_conversation(['REAL', '', ''])
        self.assertEqual(len(conv.implicit_removes()), 2)
        conv.apply()
        dt1.update()
        self.assertEqual(dt1.n_cols(), 4)
        self.assertEqual(len(dt1.used_filters), 2)

        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.do_remove = True
        conv.apply()
        dt1.update()
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.all_anon_filters), 0)
        self.assertEqual(len(dt1.used_filters), 0)


if __name__ == '__main__':
    unittest.main()
    # a = Test1()
    # a.test_converts()
