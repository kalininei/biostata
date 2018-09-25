""" Usage:
    1) from parent project directory execute
       > python3 -m unittest utest.algotest
    2) to run specific tests invoke
       > python3 -m unittest utest.algotest.Test1.<spec test>
"""
import copy
import unittest
from prog import basic, projroot, command, comproj, bopts, valuedict, filt
from fileproc import import_tab
from bdata import convert, funccol
from utest import testutils as tu

basic.set_log_message('file: ' + bopts.BiostataOptions.logfile())
basic.set_ignore_exception(True)
proj = projroot.ProjectDB()
flow = command.CommandFlow()


class Test1(unittest.TestCase):
    def setUp(self):
        ''
        com = comproj.NewDB(proj)
        flow.exec_command(com)

    def tearDown(self):
        ''

    def test_load_from_txt_1(self):
        basic.log_message('================= TEST LOAD FROM TXT 1 ========')
        opt = basic.CustomObject()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'whitespaces'
        opt.row_sep = 'newline'
        opt.colcount = -1
        opt.read_cap = True
        opt.tabname = 't1'

        com = import_tab.ImportTabFromTxt(proj, 'test_db/t1.dat', opt)
        com._prebuild()
        self.assertEqual(len(com.tab), 6)
        self.assertEqual(len(com.tab[0]), 3)

        self.assertListEqual(com.tps, ['INT', 'INT', 'REAL'])

        com.caps = ["c{}".format(i) for i in range(3)]
        flow.exec_command(com)
        dt = proj.data_tables[0]
        dt.update()
        self.assertEqual(dt.n_cols(), 4)
        self.assertEqual(dt.n_rows(), 6)

        try:
            proj.commit_all_changes()
            self.assertTrue(False)
        except:
            self.assertTrue(True)

    def test_load_from_txt_2(self):
        basic.log_message('================= TEST LOAD FROM TXT 2 ========')
        opt = basic.CustomObject()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'tabular'
        opt.row_sep = 'newline'
        opt.colcount = -1
        opt.read_cap = True
        opt.tabname = 't1'

        com = import_tab.ImportTabFromTxt(proj, 'test_db/t2.dat', opt)
        com._prebuild()
        self.assertEqual(len(com.tab), 11)
        self.assertEqual(len(com.tab[0]), 7)

        self.assertListEqual(com.tps, ['TEXT', 'INT', 'INT', 'TEXT', 'REAL',
                                       'REAL', 'REAL'])

        # import as TEXT
        com.caps = ["c{}".format(i) for i in range(7)]
        flow.exec_command(com)
        dt = proj.data_tables[0]
        dt.update()

        self.assertEqual(dt.n_cols(), 8)
        self.assertEqual(dt.n_rows(), 11)
        self.assertEqual(dt.get_value(10, 1), '')
        self.assertEqual(dt.get_value(10, 2), 10)
        self.assertEqual(dt.get_value(10, 3), 20)
        self.assertEqual(dt.get_value(10, 4), '')
        self.assertEqual(dt.get_value(10, 5), None)
        self.assertEqual(dt.get_value(9, 5), 2.22)
        self.assertEqual(dt.get_value(4, 1), 'b4p')

        # import with dictionaries
        dct = valuedict.Dictionary('ff', 'BOOL', [0, 1], ['noF', 'F'])
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)
        dct = valuedict.Dictionary('bio', 'ENUM', [0, 1, 2],
                                   ['no', 'b4g', 'b5p'])
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)

        opt2 = copy.deepcopy(opt)
        opt2.tabname = 't2'
        com = import_tab.ImportTabFromTxt(proj, 'test_db/t2.dat', opt2)
        com._prebuild()
        com.caps = ["c{}".format(i) for i in range(7)]
        com.tps[3], com.dnames[3] = 'BOOL', 'ff'
        com.tps[0], com.dnames[0] = 'ENUM', 'bio'
        flow.exec_command(com)
        dt = proj.get_table('t2')
        dt.update()

        self.assertListEqual(tu.get_dtab_column(dt, 1),
                             ['no', None, 'b5p', None, None, 'b4g',
                              'b5p', None, None, 'b5p', None])
        self.assertListEqual(tu.get_dtab_raw_column(dt, 1),
                             [0, None, 2, None, None,
                              1, 2, None, None, 2, None])

    def test_load_from_xlsx(self):
        basic.log_message('================= TEST LOAD FROM XLSX ========')
        opt1 = basic.CustomObject()
        opt1.sheetname = 'tab1'
        opt1.range = ''
        opt1.read_cap = True
        opt1.tabname = 't1'

        opt2 = basic.CustomObject()
        opt2.firstline = 0
        opt2.lastline = -1
        opt2.comment_sign = '#'
        opt2.ignore_blank = True
        opt2.col_sep = 'tabular'
        opt2.row_sep = 'newline'
        opt2.colcount = -1
        opt2.read_cap = True
        opt2.tabname = 't2'

        cxls = import_tab.ImportTabFromXlsx(proj, 'test_db/t2.xlsx', opt1)
        ctxt = import_tab.ImportTabFromTxt(proj, 'test_db/t2.dat', opt2)
        cxls._prebuild()
        ctxt._prebuild()

        # import from text and xls gives same result
        self.assertListEqual(ctxt.tab, cxls.tab)

        dct = valuedict.Dictionary('bio', 'ENUM', [0, 1, 2, 3, 4, 5],
                                   ['', 'no', 'b4g', 'b5p', 'b4p', 'b5g'])
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)

        cxls.tps[0], cxls.dnames[0] = 'ENUM', 'bio'
        flow.exec_command(cxls)
        dt = proj.get_table('t1')
        dt.update()
        # import with dictionary with an empty value
        self.assertListEqual(tu.get_dtab_column(dt, 1),
                             ['no', 'b4p', 'b5p', 'b4p', 'b4p', 'b4g',
                              'b5p', 'b4p', 'b5g', 'b5p', ''])
        self.assertListEqual(tu.get_dtab_raw_column(dt, 1),
                             [1, 4, 3, 4, 4, 2, 3, 4, 5, 3, 0])

    def test_adddict(self):
        basic.log_message('================= TEST ADDICT ===============')
        # load dictionaries
        dct = valuedict.Dictionary('a', 'BOOL', [0, 1], ['', 'Q'])
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)

        dct = valuedict.Dictionary('b', 'ENUM', [0, 10, 20, 30, 40],
                                   ['A', 'B', 'AA', 'AB', 'BB'])
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)

        # load database from t3.dat
        opt = basic.CustomObject()
        opt.firstline = 4
        opt.lastline = 5
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'in double quotes'
        opt.row_sep = 'no (use column count)'
        opt.colcount = 3
        opt.tabname = 't1'
        opt.read_cap = False

        com = import_tab.ImportTabFromTxt(proj, 'test_db/t3.dat', opt)
        com._prebuild()
        self.assertEqual(len(com.tab), 6)
        self.assertEqual(len(com.tab[0]), 3)
        com.caps = ['c1', 'c2', 'c3']
        com.tps = ['BOOL', 'REAL', 'ENUM']
        com.dnames = ['a', None, 'b']
        flow.exec_command(com)

        # import with dictionaries
        dt = proj.get_table(name='t1')
        self.assertListEqual(tu.get_dtab(dt),
                             [[1, 2, 3, 4, 5, 6],
                              ['', '', 'Q', 'Q', 'Q', ''],
                              ['A', 'B', None, 'AB', 'BB', 'AB'],
                              [3.0, 43.0, None, 3.0, 22.0, None]])

        self.assertListEqual(tu.get_dtab_raw(dt),
                             [[1, 2, 3, 4, 5, 6],
                              [0, 0, 1, 1, 1, 0],
                              [0, 10, None, 30, 40, 30],
                              [3.0, 43.0, None, 3.0, 22.0, None]])

        # save database
        com = comproj.SaveDBAs(proj, 'dbg.db')
        flow.exec_command(com)

        # change dictionaries values only
        anew = valuedict.Dictionary('a', 'BOOL', [0, 1], ['A', 'B'])
        bnew = valuedict.Dictionary('b2', 'ENUM', [0, 10, 30, 40],
                                    ['A', 'B', 'C', 'D'])
        com = comproj.ChangeDictionaries(proj, {'a': anew, 'b': bnew})
        flow.exec_command(com)
        dt.update()
        self.assertListEqual(tu.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', 'B', None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        self.assertListEqual(tu.get_dtab_raw(dt), [[1, 2, 3, 4, 5, 6], [0, 0, 1, 1, 1, 0], [0, 10, None, 30, 40, 30], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        flow.undo_prev()
        self.assertListEqual(tu.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['', '', 'Q', 'Q', 'Q', ''], ['A', 'B', None, 'AB', 'BB', 'AB'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        flow.exec_next()
        self.assertListEqual(tu.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', 'B', None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa

        # change dictionaries with converting to None
        bnew = valuedict.Dictionary('b2', 'ENUM', [0, 20, 30, 40],
                                    ['A', 'B', 'C', 'D'])
        com = comproj.ChangeDictionaries(proj, {'b2': bnew})
        flow.exec_command(com)
        dt.update()
        self.assertListEqual(tu.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', None, None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        self.assertListEqual(tu.get_dtab_raw(dt), [[1, 2, 3, 4, 5, 6], [0, 0, 1, 1, 1, 0], [0, None, None, 30, 40, 30], [3.0, 43.0, None, 3.0, 22.0, None]])   # noqa

        # remove dictionaries with filters and convert to int
        flt1 = filt.Filter.from_xml_string("""<F><NAME>f1</NAME><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c1', 'BOOL', 'a')",'==','0']</E></F>""")    # noqa
        flt2 = filt.Filter.from_xml_string("""<F><NAME/><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'REAL', None)",'>',"('c3', 'ENUM', 'b2')"]</E></F>""")    # noqa
        com = comproj.AddFilter(proj, flt1, [dt])
        flow.exec_command(com)
        com = comproj.AddFilter(proj, flt2, [dt])
        flow.exec_command(com)
        dt.update()
        self.assertEqual(len(dt.all_anon_filters), 1)
        self.assertEqual(len(dt.used_filters), 2)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertListEqual(tu.get_dtab(dt), [[4, 5], ['B', 'B'], ['C', 'D'], [3.0, 22.0]])   # noqa
        flow.undo_prev()
        self.assertEqual(len(dt.all_anon_filters), 0)
        self.assertEqual(len(dt.used_filters), 1)
        self.assertEqual(len(proj.named_filters), 1)
        flow.undo_prev()
        self.assertEqual(len(dt.all_anon_filters), 0)
        self.assertEqual(len(dt.used_filters), 0)
        self.assertEqual(len(proj.named_filters), 0)
        dt.update()
        self.assertListEqual(tu.get_dtab(dt), [[1, 2, 3, 4, 5, 6], ['A', 'A', 'B', 'B', 'B', 'A'], ['A', None, None, 'C', 'D', 'C'], [3.0, 43.0, None, 3.0, 22.0, None]])  # noqa
        flow.exec_next()
        flow.exec_next()
        dt.update()
        self.assertListEqual(tu.get_dtab(dt), [[4, 5], ['B', 'B'], ['C', 'D'], [3.0, 22.0]])   # noqa

        com = comproj.ChangeDictionaries(proj, {'a': None})
        flow.exec_command(com)
        dt.update()
        self.assertEqual(len(dt.all_anon_filters), 1)
        self.assertEqual(len(dt.used_filters), 1)
        self.assertEqual(len(proj.named_filters), 0)
        self.assertListEqual(tu.get_dtab(dt), [[4, 5], [1, 1], ['C', 'D'], [3.0, 22.0]])  # noqa

        # rename dictionary: all filters should remain
        bnew = valuedict.Dictionary('b3', 'ENUM', [0, 20, 30, 40],
                                    ['A', 'BB', 'CC', 'DD'])
        com = comproj.ChangeDictionaries(proj, {'b2': bnew})
        flow.exec_command(com)
        dt.update()
        self.assertListEqual(tu.get_dtab(dt), [[4, 5], [1, 1], ['CC', 'DD'], [3.0, 22.0]])  # noqa

        # change key structure: filters should be removed
        bnew = valuedict.Dictionary('b3', 'ENUM', [0, 20, 30, 40, 50],
                                    ['A', 'B', 'C', 'D', 'E'])
        com = comproj.ChangeDictionaries(proj, {'b3': bnew})
        flow.exec_command(com)
        dt.update()
        self.assertEqual(len(dt.used_filters), 0)

        # remove dict: all columns should be numeric
        com = comproj.ChangeDictionaries(proj, {'b3': None})
        flow.exec_command(com)
        dt.update()
        self.assertListEqual(tu.get_dtab(dt),
                             tu.get_dtab_raw(dt))

    def test_converts(self):
        basic.log_message('================= TEST CONVERTS ===============')
        opt = basic.CustomObject()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'whitespaces'
        opt.row_sep = 'newline'
        opt.colcount = -1
        opt.tabname = 't1'
        opt.read_cap = True

        # load all as TEXT
        com = import_tab.ImportTabFromTxt(proj, 'test_db/t1.dat', opt)
        com._prebuild()
        com.caps = ['c1', 'c2', 'c3']
        com.tps = ['TEXT', 'TEXT', 'TEXT']
        flow.exec_command(com)
        dt1 = proj.data_tables[0]
        dt1.update()
        self.assertListEqual(tu.get_dtab_raw(dt1), [[1, 2, 3, 4, 5, 6], ['0', '1', '1', '0', '1', '0'], ['0', '1', '2', '3', '4', '5'], ['1.1', '2.34', '3.33', '4.33', '6.28', '3.54']])  # noqa

        # load all as INT
        opt2 = copy.deepcopy(opt)
        opt2.tabname = 't2'
        com = import_tab.ImportTabFromTxt(proj, 'test_db/t1.dat', opt2)
        com._prebuild()
        com.caps = ['c1', 'c2', 'c3']
        com.tps = ['INT', 'INT', 'INT']
        flow.exec_command(com)
        dt2 = proj.data_tables[1]
        dt2.update()
        self.assertListEqual(tu.get_dtab_raw(dt2), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [0, 1, 2, 3, 4, 5], [1, 2, 3, 4, 6, 4]])  # noqa

        # swap table names
        conv1 = convert.TableConverter(dt1)
        conv2 = convert.TableConverter(dt2)
        conv1.new_name = 't2'
        conv1.new_comment = 'This was a t1 table'
        conv2.new_name = 't1'
        com = convert.ConvertTable(conv1)
        flow.exec_command(com)
        com = convert.ConvertTable(conv2)
        flow.exec_command(com)
        self.assertListEqual(tu.get_dtab(dt1),
                             tu.get_dtab(proj.get_table('t2')))
        self.assertEqual(proj.get_table('t2').comment, 'This was a t1 table')
        self.assertEqual(proj.get_table('t1').comment, '')

        # add global filters
        # (anon for dt2): c2(int) < 3
        flt1 = filt.Filter.from_xml_string("""<F><NAME/><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'INT', None)",'&lt;','3']</E></F>""")    # noqa
        # f2: c2(int) > c3(int)
        flt2 = filt.Filter.from_xml_string("""<F><NAME>f2</NAME><DO_REMOVE>1</DO_REMOVE><E>['AND','','',"('c2', 'INT', None)",'&gt;',"('c3', 'INT', None)"]</E></F>""")    # noqa
        com = comproj.AddFilter(proj, flt1, [dt2])
        flow.exec_command(com)
        com = comproj.AddFilter(proj, flt2, [dt2])
        flow.exec_command(com)
        dt2.update()
        try:
            com = comproj.ApplyFilter(dt1, flt2)
            flow.exec_command(com)
            self.assertTrue(False)
        except:
            pass
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.used_filters), 0)
        self.assertEqual(len(dt2.used_filters), 2)
        self.assertListEqual(tu.get_dtab(dt2), [[4, 5], [0, 1], [3, 4], [4, 6]])   # noqa

        # (anon for dt1): id filter
        flt3 = filt.IdFilter()
        filt.IdFilter.set_from_ilist(flt3, [1, 3, 4])
        com = comproj.AddFilter(proj, flt3, [dt1])
        flow.exec_command(com)
        dt1.update()

        # swap columns of dt1
        cconv1 = convert.ColumnConverter(dt1, dt1.get_column('c1'))
        cconv1.new_dim = 'm2'
        cconv1.new_comment = "This was a 'c1' column"
        cconv1.new_name = 'c2'
        cconv2 = convert.ColumnConverter(dt1, dt1.get_column('c2'))
        cconv2.new_dim = 'm2'
        cconv2.new_comment = "This was a 'c2' column"
        cconv2.new_name = 'c1'
        conv = convert.TableConverter(dt1)
        conv.citems = [cconv1, cconv2]
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        self.assertListEqual(tu.get_dtab_column(dt1, 'c2'), ['1', '1', '0'])   # noqa
        self.assertEqual(dt1.get_column('c2').comment, "This was a 'c1' column")  # noqa

        # c2-c3 collapse
        com = funccol.MergeCategories(dt2, ['c2', 'c3'], '*', True)
        flow.exec_command(com)
        self.assertListEqual([x.name for x in dt2.all_columns], ['id', 'c1', 'c2', 'c3', 'c2*c3'])  # noqa
        self.assertListEqual([x.name for x in dt2.visible_columns], ['id', 'c1', 'c2*c3'])  # noqa
        flow.undo_prev()
        com = funccol.MergeCategories(dt2, ['c2', 'c3'], '-', False)
        flow.exec_command(com)
        self.assertListEqual([x.name for x in dt2.visible_columns], ['id', 'c1', 'c2', 'c3', 'c2-c3'])  # noqa
        dt2.update()

        # rename columns of dt2
        conv = convert.TableConverter(dt2)
        cconv1 = convert.ColumnConverter(dt2, dt2.get_column('c2'))
        cconv1.new_name = 'new name'
        cconv2 = convert.ColumnConverter(dt2, dt2.get_column('c2-c3'))
        cconv2.new_name = 'collapse23'
        conv.citems = [cconv1, cconv2]
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt2.update()
        self.assertListEqual(tu.get_dtab(dt2), [[4, 5, 6], [0, 1, 0], [3, 4, 5], [4, 6, 4], ['3-4', '4-6', '5-4']])   # noqa
        self.assertListEqual(tu.get_dtab_column(dt2, 'collapse23'), ['3-4', '4-6', '5-4'])   # noqa
        try:
            com = comproj.ApplyFilter(dt2, flt2)
            flow.exec_command(com)
            self.assertTrue(False)
        except:
            pass

        # rename back
        cconv1.new_name = 'c2'
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        com = comproj.ApplyFilter(dt2, flt2)
        flow.exec_command(com)
        dt2.update()
        self.assertListEqual(tu.get_dtab(dt2), [[4, 5], [0, 1], [3, 4], [4, 6], ['3-4', '4-6']])   # noqa

        # remove columns
        conv = convert.TableConverter(dt2)
        conv1 = conv.colitem('c2')
        conv1.do_remove = True
        self.assertEqual(len(conv.implicit_removes()), 1)
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt2.update()
        self.assertEqual(len(dt2.used_filters), 0)
        self.assertEqual(len(dt2.all_anon_filters), 0)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertListEqual(tu.get_dtab(dt2), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [1, 2, 3, 4, 6, 4]])   # noqa

        # convert columns of dt1 (now it is text and has only id filter)
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c1')
        conv1.set_conversation(['INT', '', ''])
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab(dt1),
                             tu.get_dtab_raw(dt1))
        self.assertListEqual(tu.get_dtab_column(dt1, "c1"), [1, 4, 5])

        # convert to bool dictionary
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.set_conversation(['BOOL', '0-1', 'text to values'])
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab_column(dt1, 'c2'), ['1', '1', '0'])  # noqa
        self.assertListEqual(tu.get_dtab_raw_column(dt1, 'c2'), [1, 1, 0])    # noqa

        # convert to another bool dictionary
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.set_conversation(['BOOL', 'Yes/No', 'keys to keys'])
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab_column(dt1, 'c2'), ['Yes', 'Yes', 'No'])  # noqa
        self.assertListEqual(tu.get_dtab_raw_column(dt1, 'c2'), [1, 1, 0])    # noqa

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
        com = comproj.AddDictionary(proj, dct)
        flow.exec_command(com)

        conv1.set_conversation(['ENUM', 'tdict', 'real to keys'])
        conv1.new_name = 'ccc'
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        com = comproj.UnapplyFilter(dt1, 'all', True)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa
        self.assertListEqual(tu.get_dtab_raw_column(dt1, 'ccc'), [1, None, None, 4, None, 4])   # noqa

        conv1.set_conversation(['TEXT', '', 'values to text'])
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab_raw_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa

        conv1.set_conversation(['ENUM', 'tdict', 'text to values'])
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab_raw_column(dt1, 'ccc'), [1, None, None, 4, None, 4])   # noqa
        self.assertListEqual(tu.get_dtab_column(dt1, 'ccc'), ['ONE', None, None, 'FOUR', None, 'FOUR'])   # noqa

        conv1 = conv.colitem('ccc')
        conv1.set_conversation(['INT', '', 'keys to int'])
        conv1.new_name = 'c3'

        conv1 = conv.colitem('c2')
        conv1.new_shortname = 'b'
        conv1.set_conversation(['INT', '', 'keys to int'])

        conv1 = conv.colitem('c1')
        conv1.new_shortname = 'a'
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()

        com = funccol.MergeCategories(dt1, ['c1', 'c2'], '-', False)
        flow.exec_command(com)
        com = funccol.MergeCategories(dt1, ['a-b', 'c3'], '-', False)
        flow.exec_command(com)
        dt1.update()
        self.assertListEqual(tu.get_dtab(dt1), [[1, 2, 3, 4, 5, 6], [0, 1, 1, 0, 1, 0], [0, 1, 2, 3, 4, 5], [1, None, None, 4, None, 4], ['0-0', '1-1', '2-1', '3-0', '4-1', '5-0'], ['0-0-1', '1-1-##', '2-1-##', '3-0-4', '4-1-##', '5-0-4']])   # noqa

        self.assertTrue(flt2.is_applicable(dt1))
        com = comproj.ApplyFilter(dt1, flt1)
        flow.exec_command(com)
        com = comproj.ApplyFilter(dt1, flt2)
        flow.exec_command(com)
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.all_anon_filters), 1)
        self.assertEqual(len(dt1.used_filters), 2)
        dt1.update()
        self.assertListEqual(tu.get_dtab(dt1), [[], [], [], [], [], []])   # noqa

        # implicit removes
        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c1')
        conv1.set_conversation(['REAL', '', ''])
        self.assertEqual(len(conv.implicit_removes()), 2)
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertEqual(dt1.n_cols(), 4)
        self.assertEqual(len(dt1.used_filters), 2)

        conv = convert.TableConverter(dt1)
        conv1 = conv.colitem('c2')
        conv1.do_remove = True
        com = convert.ConvertTable(conv)
        flow.exec_command(com)
        dt1.update()
        self.assertEqual(len(proj.named_filters), 1)
        self.assertEqual(len(dt1.all_anon_filters), 0)
        self.assertEqual(len(dt1.used_filters), 0)

    def test_command_interface(self):
        basic.log_message('================= TEST COMMAND INTERFACE=======')
        opt = basic.CustomObject()
        opt.firstline = 0
        opt.lastline = -1
        opt.comment_sign = '#'
        opt.ignore_blank = True
        opt.col_sep = 'whitespaces'
        opt.row_sep = 'newline'
        opt.colcount = -1
        opt.tabname = 't1'
        opt.read_cap = True

        c = import_tab.ImportTabFromTxt(proj, 'test_db/t1.dat', opt)
        flow.exec_command(c)
        self.assertEqual(len(proj.data_tables), 1)
        flow.undo_prev()
        self.assertEqual(len(proj.data_tables), 0)
        flow.exec_next()
        self.assertEqual(len(proj.data_tables), 1)
        c = comproj.SaveDBAs(proj, "dbg.db")
        flow.exec_command(c)
        self.assertEqual(proj._curname, "dbg.db")
        flow.undo_prev()
        self.assertEqual(proj._curname, "New database")
        c = comproj.NewDB(proj)
        flow.exec_command(c)
        self.assertEqual(len(proj.data_tables), 0)
        c = comproj.LoadDB(proj, "dbg.db")
        flow.exec_command(c)
        self.assertEqual(proj.data_tables[0].name, 't1')
        flow.undo_prev()
        self.assertEqual(len(proj.data_tables), 0)
        flow.exec_next()
        flow.undo_prev()
        flow.exec_next()
        self.assertEqual(len(proj.data_tables), 1)
        flow.undo_prev()
        flow.undo_prev()
        self.assertEqual(len(proj.data_tables), 1)

if __name__ == '__main__':
    unittest.main()
