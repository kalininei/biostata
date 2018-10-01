import functools
from PyQt5 import QtCore, QtWidgets
from bgui import dlgs, qtcommon, dictdlg
from bdata import convert


@qtcommon.hold_position
class TablesInfo(dlgs.OkCancelDialog):
    def __init__(self, proj, parent):
        super().__init__("Tables information", parent, "horizontal")
        self.resize(400, 300)
        self.proj = proj
        # array of TableConverters
        self.titems = [convert.TableConverter(t) for t in proj.data_tables]

        # mainframe = table tree + info_frame
        self.e_tree = TablesTree(self, self.titems)
        self.info_frame = TablesFrame(self, self.titems)
        self.e_tree.item_changed.connect(self.info_frame.set)
        self.info_frame.item_edited.connect(self.reset_tree_item)
        if self.e_tree.topLevelItemCount() > 0:
            self.e_tree.topLevelItem(0).setSelected(True)

        self.mainframe.layout().addWidget(self.e_tree)
        self.mainframe.layout().addWidget(self.info_frame)

        self.orig_dictionaries = self.proj.dictionaries[:]

    def reset_tree_item(self, item):
        self.e_tree.fill()

    def new_dictionaries(self):
        """ somewhere within this dialogs new dictionaries are added into
            the project. At the end of it we remove thoise dictionaries
            and sent these dictionaries as return values.
        """
        ret = []
        for d in self.proj.dictionaries:
            if d not in self.orig_dictionaries:
                ret.append(d)
        for d in ret:
            self.proj.dictionaries.remove(d)
        return ret

    def reject(self):
        self.new_dictionaries()
        return super().reject()

    def accept(self):
        try:
            self._ret_value = []
            # assemble result
            for r in filter(lambda x: x.has_changes(), self.titems):
                self._ret_value.append(r)
            # ---- CHECKS
            # check table names
            nms = [r.new_name for r in self.titems if not r.do_remove]
            for n in nms:
                self.proj.is_possible_table_name(n)
            if len(set(nms)) < len(nms):
                raise Exception("Repeating table names are not valid.")
            # check column names
            for r in self._ret_value:
                cnms = [c.new_name for c in r.citems if not c.do_remove]
                for c in cnms:
                    self.proj.is_possible_column_name(c)
                if len(set(cnms)) < len(cnms):
                    raise Exception("Repeating column names are not valid.")
            self._ret_value = self.new_dictionaries(), self._ret_value
            # return
            return super().accept()
        except Exception as e:
            qtcommon.message_exc(self, "Invalid input", e=e)

    def ret_value(self):
        ''' -> new dictionaries, list of converters '''
        return self._ret_value


class TablesTree(QtWidgets.QTreeWidget):
    item_changed = QtCore.pyqtSignal(object)
    ItemRole = QtCore.Qt.UserRole + 1

    def __init__(self, parent, titems):
        super().__init__(parent)
        self.titems = titems
        self.selected_item = None
        self.fill()
        self.setFixedWidth(200)
        self.setHeaderHidden(True)

        # context menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def fill(self):
        self.clear()
        self.setColumnCount(2)
        for r in filter(lambda x: not x.do_remove, self.titems):
            itm = QtWidgets.QTreeWidgetItem(self)
            itm.setData(0, QtCore.Qt.DisplayRole, self.viewed_name(r))
            itm.setData(0, TablesTree.ItemRole, r)
            for c in filter(lambda x: not x.do_remove, r.citems):
                itm1 = QtWidgets.QTreeWidgetItem(itm)
                itm1.setData(0, QtCore.Qt.DisplayRole, self.viewed_name(c))
                itm1.setData(1, QtCore.Qt.DisplayRole, c.new_col_type())
                itm1.setData(0, TablesTree.ItemRole, c)
        self.expandAll()
        self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        if self.selected_item is not None:
            itm = self.find_item(self.selected_item)
            if itm is None and self.topLevelItemCount() > 0:
                self.topLevelItem(0).setSelected(True)
            elif itm is not None:
                itm.setSelected(True)

    def selectionChanged(self, selected, deselected):   # noqa
        super().selectionChanged(selected, deselected)
        if len(selected.indexes()) > 0:
            d = selected.indexes()[0].data(self.ItemRole)
            self.selected_item = d
            self.item_changed.emit(d)

    def find_item(self, itm):
        for i in range(self.topLevelItemCount()):
            r = self.topLevelItem(i)
            if r.data(0, TablesTree.ItemRole) is itm:
                return r
            for j in range(r.childCount()):
                r2 = r.child(j)
                if r2.data(0, TablesTree.ItemRole) is itm:
                    return r2
        return None

    def _context_menu(self, pnt):
        index = self.indexAt(pnt)
        menu = QtWidgets.QMenu(self)
        act_rem = QtWidgets.QAction("Remove", self)
        act_rem.triggered.connect(functools.partial(self._act_rem, index))
        menu.addAction(act_rem)
        menu.popup(self.viewport().mapToGlobal(pnt))

    def _act_rem(self, index):
        twitem = self.itemFromIndex(index)
        titem = twitem.data(0, TablesTree.ItemRole)
        titem.do_remove = True
        self.fill()

    def viewed_name(self, conv):
        ret = conv.new_name
        if conv.has_changes():
            ret += ' *'
        return ret


class TablesFrame(QtWidgets.QFrame):
    item_edited = QtCore.pyqtSignal(object)

    def __init__(self, parent, ditems):
        super().__init__(parent)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.frames = {}

        for d in ditems:
            nm = d.table.name
            self.frames[nm] = TableInfoFrame(self, d)
            for c in d.citems:
                nmc = nm + ',' + c.col.name
                self.frames[nmc] = ColumnInfoFrame(self, d, c)

        for f in self.frames.values():
            f.setVisible(False)
            self.layout().addWidget(f)

    def set(self, item):
        if isinstance(item, convert.TableConverter):
            nm = item.table.name
        elif isinstance(item, convert.ColumnConverter):
            nm = item.table.name + ',' + item.col.name
        for f in self.frames.values():
            f.setVisible(False)

        self.frames[nm].init_fill()
        self.frames[nm].setVisible(True)


class TableInfoFrame(QtWidgets.QFrame):
    def __init__(self, parent, tabitem):
        super().__init__(parent)
        self.item = tabitem
        self.setLayout(QtWidgets.QGridLayout())
        # name
        self.e_name = qtcommon.BLineEdit('', self)
        self.e_name.text_changed.connect(self.changed)
        self.layout().addWidget(QtWidgets.QLabel('Name'), 0, 0)
        self.layout().addWidget(self.e_name, 0, 1)
        # comments
        self.e_comment = qtcommon.BTextEdit('', self)
        self.e_comment.text_changed.connect(self.changed)
        # button
        self.bbox = QtWidgets.QDialogButtonBox(self)
        self.discard_button = QtWidgets.QPushButton("Discard")
        self.discard_button.clicked.connect(self.discard)
        self.discols_button = QtWidgets.QPushButton("Discard columns")
        self.discols_button.clicked.connect(self.discard_columns)
        self.bbox.addButton(self.discard_button,
                            QtWidgets.QDialogButtonBox.NoRole)
        self.bbox.addButton(self.discols_button,
                            QtWidgets.QDialogButtonBox.NoRole)

        self.layout().addWidget(QtWidgets.QLabel("Comment"), 1, 0)
        self.layout().addWidget(self.e_comment, 1, 1)
        self.layout().addWidget(self.bbox, 2, 0, 1, 2)
        self.layout().setRowStretch(1, 1)

    def changed(self):
        self.item.new_name = self.e_name.text()
        self.item.new_comment = self.e_comment.toPlainText()
        self.parent().item_edited.emit(self.item)

    def discard(self):
        self.item.discard()
        self.parent().item_edited.emit(self.item)

    def discard_columns(self):
        for c in self.item.citems:
            c.discard()
        self.parent().item_edited.emit(self.item)

    def init_fill(self):
        self.e_name.setText(self.item.new_name)
        self.e_comment.setText(self.item.new_comment)


class ColumnInfoFrame(QtWidgets.QFrame):
    def __init__(self, parent, tabitem, colitem):
        super().__init__(parent)
        self.item = colitem
        self.proj = tabitem.table.proj
        self.setLayout(QtWidgets.QGridLayout())
        self.__ignore_changes = False
        i = -1

        # origin
        i += 1
        # self.e_origin = QtWidgets.QLineEdit()
        # self.e_origin.setReadOnly(True)
        self.e_origin = QtWidgets.QLabel(self)
        self.layout().addWidget(QtWidgets.QLabel("Origin"), i, 0)
        self.layout().addWidget(self.e_origin, i, 1)

        # name
        i += 1
        self.e_name = qtcommon.BLineEdit('', self)
        self.e_name.text_changed.connect(self.changed)
        self.layout().addWidget(QtWidgets.QLabel('Name'), i, 0)
        self.layout().addWidget(self.e_name, i, 1)

        # shortname
        i += 1
        self.e_shortname = qtcommon.BLineEdit('', self)
        self.e_shortname.text_changed.connect(self.changed)
        self.layout().addWidget(QtWidgets.QLabel("Short name"), i, 0)
        self.layout().addWidget(self.e_shortname, i, 1)

        # dim
        i += 1
        self.e_dim = qtcommon.BLineEdit('', self)
        self.e_dim.text_changed.connect(self.changed)
        self.layout().addWidget(QtWidgets.QLabel("Dimension"), i, 0)
        self.layout().addWidget(self.e_dim, i, 1)

        # type
        i += 1
        etpframe = QtWidgets.QFrame(self)
        etpframe.setLayout(QtWidgets.QHBoxLayout())
        etpframe.layout().setContentsMargins(0, 0, 0, 0)
        # self.e_type = QtWidgets.QLineEdit(self)
        # self.e_type.setReadOnly(True)
        self.e_type = QtWidgets.QLabel(self)
        self.tpconv_button = QtWidgets.QPushButton("Convert")
        self.tpconv_button.clicked.connect(self._act_tpconv)
        # Conversion is availible only for original columns.
        # I don't see any reason why it should present for functional columns.
        # but maybe i'm wrong.
        self.tpconv_button.setEnabled(colitem.col.is_original())

        etpframe.layout().addWidget(self.e_type)
        etpframe.layout().addWidget(self.tpconv_button)
        etpframe.layout().setStretch(0, 1)
        etpframe.layout().setStretch(1, 0)
        self.layout().addWidget(QtWidgets.QLabel("Type"), i, 0)
        self.layout().addWidget(etpframe, i, 1)

        # comments
        i += 1
        self.e_comment = qtcommon.BTextEdit('', self)
        self.e_comment.text_changed.connect(self.changed)
        self.layout().addWidget(QtWidgets.QLabel("Comment"), i, 0)
        self.layout().addWidget(self.e_comment, i, 1)
        self.layout().setRowStretch(i, 1)

        # overview
        i += 1
        self.e_overview = ColumnOverview(self)
        self.layout().addWidget(self.e_overview, i, 0, 1, 2)

        # buttonbox
        i += 1
        self.bbox = QtWidgets.QDialogButtonBox(self)
        self.discard_button = QtWidgets.QPushButton('Discard', self)
        self.overview_button = QtWidgets.QPushButton('Overview', self)
        self.bbox.addButton(self.overview_button,
                            QtWidgets.QDialogButtonBox.NoRole)
        self.bbox.addButton(self.discard_button,
                            QtWidgets.QDialogButtonBox.NoRole)
        self.discard_button.clicked.connect(self.discard)
        self.overview_button.clicked.connect(self.overview)
        self.layout().addWidget(self.bbox, i, 0, 1, 2)

    def discard(self):
        self.item.discard()
        self.parent().item_edited.emit(self.item)

    def overview(self):
        self.overview_button.setEnabled(False)
        self.e_overview.calc(self.item.table, self.item.col)

    def init_fill(self):
        self.__ignore_changes = True
        cc = self.item.col
        # origin
        if cc.is_original():
            self.e_origin.setText("Database column")
        else:
            self.e_origin.setText(
                "Function column: {}".format(cc.sql_delegate.function_type))

        # line data
        self.e_name.setText(self.item.new_name)
        self.e_shortname.setText(self.item.new_shortname)
        self.e_dim.setText(self.item.new_dim)
        self.e_comment.setText(self.item.new_comment)
        self.e_type.setText(self.item.type_conversation_string())
        self.__ignore_changes = False

    def changed(self, *args):
        if self.__ignore_changes:
            return
        self.item.new_name = self.e_name.text()
        self.item.new_dim = self.e_dim.text()
        self.item.new_shortname = self.e_shortname.text()
        self.item.new_comment = self.e_comment.toPlainText()
        self.parent().item_edited.emit(self.item)

    def _act_tpconv(self):
        dialog = ConvertDialog(self.item, self)
        if dialog.exec_():
            conv_type = dialog.ret_value()
            self.item.set_conversation(conv_type)
            self.parent().item_edited.emit(self.item)


class ColumnOverview(QtWidgets.QGroupBox):
    def __init__(self, parent):
        super().__init__(parent)
        self.setTitle('Overview')
        self.setLayout(QtWidgets.QGridLayout())

        self.e_tot = QtWidgets.QLabel('--')
        self.e_nonnull = QtWidgets.QLabel('--')
        self.e_distinct = QtWidgets.QLabel('--')
        self.e_distinct_list = QtWidgets.QTextEdit()
        self.e_distinct_list.setTextInteractionFlags(
            QtCore.Qt.TextSelectableByMouse)
        self.e_distinct_list.setFixedHeight(80)

        i = -1

        i += 1
        self.layout().addWidget(QtWidgets.QLabel("Total entries"), i, 0)
        self.layout().addWidget(self.e_tot, i, 1)
        i += 1
        self.layout().addWidget(QtWidgets.QLabel("Non-NULL entries"), i, 0)
        self.layout().addWidget(self.e_nonnull, i, 1)
        i += 1
        self.layout().addWidget(QtWidgets.QLabel("Distinct entries"), i, 0)
        self.layout().addWidget(self.e_distinct, i, 1)
        i += 1
        self.layout().addWidget(QtWidgets.QLabel("Distincts list"), i, 0)
        self.layout().addWidget(self.e_distinct_list, i, 1)

    def calc(self, dt, column):
        # n1: n total
        dt.query('SELECT COUNT(id) from "{}"'.format(dt.ttab_name))
        n1 = dt.qresult()[0]
        # n2: n non null
        dt.query('SELECT COUNT({}) from "{}"'.format(column.sql_line(),
                                                     dt.ttab_name))
        n2 = dt.qresult()[0]
        # n3: distinct
        dt.query('SELECT COUNT(DISTINCT {}) from "{}"'.format(
            column.sql_line(), dt.ttab_name))
        n3 = dt.qresult()[0]
        # n4: distinct list
        dt.query("""
        SELECT DISTINCT {0} from "{1}" WHERE {0} IS NOT NULL LIMIT 21
        """.format(column.sql_line(), dt.ttab_name))
        n4 = [column.repr(x[0]) for x in dt.qresults()]

        # add to widgets
        self.e_tot.setText(str(n1))
        self.e_nonnull.setText(str(n2))
        self.e_distinct.setText(str(n3))

        for n in n4[:20]:
            self.e_distinct_list.insertPlainText(str(n) + '\n')
        if len(n4) > 20:
            self.e_distinct_list.insertPlainText('...')


@qtcommon.hold_position
class ConvertDialog(dlgs.OkCancelDialog):
    def __init__(self, colitem, parent):
        super().__init__("Column type convert", parent, "grid")
        self.colitem = colitem
        self.proj = colitem.table.proj
        self.pc = [None] + colitem.possible_conversations()
        self.cb = QtWidgets.QComboBox(self)
        self.dictcb = QtWidgets.QComboBox(self)
        self.cb.currentIndexChanged.connect(self.cb_changed)
        self.dictcb.currentTextChanged.connect(self.dictcb_changed)

        self.cb.addItem('No conversation')
        self.cb.addItems([colitem.conversation_to_string(c)
                          for c in self.pc[1:]])

        lo = self.mainframe.layout()
        lo.addWidget(QtWidgets.QLabel("Conversation"), 0, 0)
        lo.addWidget(self.cb, 0, 1)
        lo.addWidget(QtWidgets.QLabel("Dictionary"), 1, 0)
        lo.addWidget(self.dictcb, 1, 1)

    def cb_changed(self, ind):
        self.current_index = ind
        ret = self.pc[ind]
        self.dictcb.setEnabled(True)
        self.dictcb.clear()
        if ret is not None and ret[0] == 'ENUM':
            self.dictcb.addItems([x.name
                                  for x in self.proj.enum_dictionaries()])
            self.dictcb.addItem('_ create new dict')
        elif ret is not None and ret[0] == 'BOOL':
            self.dictcb.addItems([x.name
                                  for x in self.proj.bool_dictionaries()])
            self.dictcb.addItem('_ create new dict')
        else:
            self.dictcb.setEnabled(False)

    def dictcb_changed(self, dname):
        self.dictcb.currentTextChanged.disconnect(self.dictcb_changed)
        if dname == '_ create new dict':
            cc = self.pc[self.current_index]
            keys, vals = self.colitem.dictionary_prototype(cc[2])
            dialog = dictdlg.CreateNewDictionary(
                self.proj.dictionaries, self, cc[0],
                ukeys=keys, uvals=vals, can_change_type=False)
            if dialog.exec_():
                nd = dialog.ret_value()
                self.proj.add_dictionary(nd)
                self.dictcb.insertItem(self.dictcb.count()-1, nd.name)
                self.dictcb.setCurrentIndex(self.dictcb.count()-2)
            else:
                self.dictcb.setCurrentIndex(0)
        self.dictcb.currentTextChanged.connect(self.dictcb_changed)

    def ret_value(self):
        ret = self.pc[self.current_index]
        if ret is not None and ret[0] in ['ENUM', 'BOOL']:
            ret[1] = self.dictcb.currentText()
        return ret
