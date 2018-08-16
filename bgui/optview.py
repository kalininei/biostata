#!/usr/bin/env python3
""" Tree like options representation widget.

Defined public classes:
1) Basic classes
    OptionsView - widget derived from QTreeView

    OptionsList - driver which sets a match between
        value member in a user class and option caption/name and display/edit
        representation in the widget

    OptionWidgetConfigure - color, font, indent widget configuation.
        Default configuration is stored in OptionWidgetConfigure.default.

"""
import collections
from PyQt5 import QtGui, QtCore, QtWidgets

_tmp = None


# ================ Configurations
class OptionWidgetConfigure(object):
    "defines color, font etc. of option table widget "
    _default = None

    def __init__(self):
        self.palette = QtWidgets.QWidget().palette()
        # colors
        self.bgcolor1 = QtGui.QColor(255, 255, 0, 70)
        self.bgcolor2 = QtGui.QColor(255, 255, 0, 40)
        self.captioncolor = QtGui.QColor(150, 150, 150, 100)
        self.selectcolor = QtGui.QColor(38, 169, 149, 10)
        self.active_font_color = self.palette.color(
                QtGui.QPalette.Active, QtGui.QPalette.WindowText)
        self.inactive_font_color = QtGui.QColor(100, 100, 100)
        # font
        self.font = QtGui.QFont()
        self.font.setPointSize(10)
        # cell standard height
        self.row_height = 20
        # indentation
        self.font_indent = 5
        self.branch_indent = 20
        self.vert_gap = 2

    @classmethod
    def default(cls):
        if cls._default is None:
            cls._default = cls()
        return cls._default

    def _string_width(self, s):
        m = QtGui.QFontMetrics(self.font)
        return m.width(s)

    def _label(self, text="", parent=None):
        wdg = QtWidgets.QLabel(text, parent)
        wdg.setIndent(self.font_indent)
        wdg.setFont(self.font)
        return wdg

    def _chbox(self, text="", parent=None):
        wdg = QtWidgets.QCheckBox(text, parent)
        wdg.setFont(self.font)
        return wdg


class OptionsHolderInterface(object):
    "Abstract dialog for option set"
    def odata(self):
        """returns options struct child class singleton which stores
        last dialog execution"""
        raise NotImplementedError

    def odata_status(self):
        """returns options status struct child class singleton which stores
        last dialog execution"""
        raise NotImplementedError


# ================ Option Entries
class OptionEntry(object):
    "Options entry base class "
    def __init__(self, data, member_name):
        """ (OptionsSet data, String dict_name) """
        self.data = data.odata()
        self.data_status = data.odata_status()
        self.member_name = member_name
        self._check(self.get())
        self.conf = OptionWidgetConfigure.default()

    def set_configuration(self, conf):
        "set OptionWidgetConfigure for the item"
        self.conf = conf

    def _check(self, val):
        "throws ValueError if val is not correct"
        if not self._check_proc(val):
            raise ValueError

    def _check_proc(self, val):
        "function for overriding: -> True if value is ok"
        return True

    # widgets
    def display_widget(self):
        " generates display widget with data "
        raise NotImplementedError

    def fill_dispaly_widget(self):
        " fills widget with actual data "
        raise NotImplementedError

    def edit_widget(self, parent=None):
        " genenerates edit widget with initial data"
        raise NotImplementedError

    def display_lines(self):
        "number of lines in display widget is used to define cell size"
        return 1

    def edit_lines(self):
        "number of lines in editor widget is used to define cell size"
        return self.display_lines()

    # values manipulations
    def get(self):
        return self.data.__dict__[self.member_name]

    def set(self, val):
        'check value and pass it to data'
        self._check(val)
        self.data.__dict__[self.member_name] = val

    def get_status(self):
        try:
            return self.data_status.__dict__[self.member_name]
        except:
            return True

    def set_status(self, val):
        try:
            self.data_status.__dict__[self.member_name] = val
        except:
            pass

    def have_status(self):
        try:
            self.data_status.__dict__[self.member_name]
            return True
        except:
            return False

    def set_from_widget(self, editor):
        "set value from edit_widget"
        raise NotImplementedError

    # value to string
    def __str__(self):
        return str(self.get())


class OptionsList(object):
    'list of objects derived from OptionEntry class'

    def __init__(self, opt_array):
        """ should be initialized from the list of tuples:
            ([(Caption1, OptionName1, OptionEntry1),
            (Caption2, OptionName2, OptionEntry2),...]
        """
        self.caps = [x[0] for x in opt_array]
        self.names = [x[1] for x in opt_array]
        self.opts = [x[2] for x in opt_array]

    def set_configuration(self, conf):
        'set OptionWidgetConfigure for all entries'
        for v in self.opts:
            v.set_configuration(conf)

    def captions(self):
        " -> list of captions"
        return list(collections.OrderedDict.fromkeys(self.caps))

    def cap_options(self, caption):
        """-> [(OptionName1, OptionEntry1), (OptionName2, OptionEntry2), ...]
        returns set of options for certain caption
        """
        zp = zip(self.caps, self.names, self.opts)
        return [(y, z) for x, y, z in zp if x == caption]

    def __str__(self):
        lines = ["------- OPTIONS"]
        for i in range(len(self.opts)):
            lines.append(self.names[i] + ": " + str(self.opts[i]))
        return '\n'.join(lines)


# ============================ Delegate
class OptionsValueDelegate(QtWidgets.QItemDelegate):

    'representation of options in a widget'
    def __init__(self, conf):
        super(OptionsValueDelegate, self).__init__()
        self.conf = conf
        # widgets by index
        self.widget_dict = {}
        self.__edited_index = None

    # --- index categories
    def address(self, index):
        # i index of caption
        # j index of row within caption: (-1 for captions itself)
        # k index of column
        k = index.column()
        if index.internalPointer().childCount() == 1:
            i = index.row()
            j = -1
        else:
            i = index.parent().row()
            j = index.row()
        return [i, j, k]

    def _index_position(self, index):
        """-> int:
            0 - no data, 1 - group caption,
            2 - option name, 3 - option data
        """
        if index.column() == 0:
            return 2 if index.internalPointer().childCount() == 0 else 1
        else:
            return 3 if index.internalPointer().data(1) is not None else 0

    def u_address(self, index):
        return ".".join(map(str, self.address(index)))

    def widget_by_index(self, index):
        try:
            return self.widget_dict[self.u_address(index)]
        except KeyError:
            pos = self._index_position(index)
            ch = index.data(QtCore.Qt.CheckStateRole)
            # construct widget
            if pos == 1:
                # group caption
                wdg = self.conf._label(index.data())
                wdg.font().setBold(True)
            elif pos == 2:
                # option caption
                if ch is None:
                    wdg = self.conf._label(index.data())
                else:
                    wdg = self.conf._chbox(index.data())
                    wdg.setChecked(ch)
                    index.internalPointer().setchecked_receivers.append(
                            wdg.setChecked)
            else:
                # option value
                wdg = self._option_data(index).display_widget()
                if ch is not None:
                    wdg.setEnabled(ch)
                    index.internalPointer().setchecked_receivers.append(
                            wdg.setEnabled)
            # save widget to a map to access it through indexes
            self.widget_dict[self.u_address(index)] = wdg
            return wdg

    def _bg_color(self, index):
        "bg color for the tree row"
        if self._index_position(index) in [0, 1]:
            return self.conf.captioncolor
        else:
            return self.conf.bgcolor1 if index.row() % 2 == 0 \
                    else self.conf.bgcolor2

    def _option_data(self, index):
        "option value from the index"
        return index.internalPointer().data(1)

    def _set_palette(self, index, widget, option):
        # p = QtGui.QPalette(self.conf.palette)
        p = QtGui.QPalette(widget.palette())
        enabled = bool(QtWidgets.QStyle.State_Enabled & option.state) and\
            widget.isEnabled()
        selected = bool(QtWidgets.QStyle.State_Selected & option.state)
        # background
        if enabled:
            if selected:
                p.setColor(QtGui.QPalette.Window, self.conf.selectcolor)
            else:
                p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0, 0))
        else:
            p.setColor(QtGui.QPalette.Window, QtGui.QColor(0, 0, 0, 100))
        # font color
        if enabled:
            p.setColor(QtGui.QPalette.WindowText,
                       self.conf.active_font_color)
        else:
            p.setColor(QtGui.QPalette.WindowText,
                       self.conf.inactive_font_color)
        widget.setPalette(p)

    def _set_data(self, index, wdg):
        pos = self._index_position(index)
        if pos == 1:
            # group caption
            wdg.setText(index.data())
        elif pos == 2:
            # option caption
            wdg.setText(index.data())
            ch = index.data(QtCore.Qt.CheckStateRole)
            if ch is not None:
                wdg.setChecked(ch)
        else:
            # option value
            self._option_data(index).fill_display_widget(wdg)

    def paint(self, painter, option, index):
        "overriden"
        if index == self.__edited_index:
            return
        pos = self._index_position(index)
        # gridlines and color
        pen = QtGui.QPen()
        pen.setColor(QtCore.Qt.lightGray)
        painter.setPen(pen)
        rect = QtCore.QRect(option.rect)
        if pos in [1, 2]:
            rect.setLeft(0)
        painter.fillRect(rect, QtGui.QBrush(self._bg_color(index)))
        if pos in [2, 3]:
            painter.drawRect(rect)
        else:
            painter.drawLine(rect.topLeft(), rect.topRight())

        # display widgets
        if pos == 0:
            # blank square
            return super().paint(painter, option, index)
        wdg = self.widget_by_index(index)
        self._set_palette(index, wdg, option)
        self._set_data(index, wdg)

        # TODO: consider usage of
        # self.drawCheck(painter, option, option.rect, QtCore.Qt.Checked)

        # paint widget
        painter.save()
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.translate(option.rect.topLeft())
        wdg.resize(option.rect.size())
        wdg.render(painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):   # noqa
        # mouse press on checkable items: send a signal
        if event.type() == QtCore.QEvent.MouseButtonPress and\
                event.button() == QtCore.Qt.LeftButton and\
                index.flags() & QtCore.Qt.ItemIsUserCheckable:
            f = index.data(QtCore.Qt.CheckStateRole)
            item = index.internalPointer()
            item.setChecked(not f)
            # ###### this has little effect
            model.dataChanged.emit(index, index.sibling(index.row(), 1))
        return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):   # noqa
        "overriden"
        ed = self._option_data(index).edit_widget(parent)
        # emit size hint in case editor has more lines then display widget
        self.sizeHintChanged.emit(index)
        self.__edited_index = index
        return ed

    def destroyEditor(self, editor, index):   # noqa
        self.__edited_index = None
        # emit size hint in case of change of display lines
        self.sizeHintChanged.emit(index)
        super().destroyEditor(editor, index)

    def sizeHint(self, option, index):   # noqa
        "overriden"
        # only cell height is defined manually so we deal only with second
        # column because its widgth is defined by total widget width
        pos = self._index_position(index)
        if pos == 3:
            if self.__edited_index != index:
                dl = self._option_data(index).display_lines()
            else:
                dl = self._option_data(index).edit_lines()
            addl = max(1, dl) - 1
            delta = (self.conf.row_height - 2 * self.conf.vert_gap) * addl
            return QtCore.QSize(-1, self.conf.row_height + delta)
        elif pos in [1, 2]:
            w = self.conf._string_width(index.data())
            w += 2 * self.conf.branch_indent + self.conf.font_indent
            return QtCore.QSize(w, self.conf.row_height)
        else:
            return QtCore.QSize(-1, -1)

    def setModelData(self, editor, model, index):   # noqa
        "overriden"
        self._option_data(index).set_from_widget(editor)

    def updateEditorGeometry(self, editor, option, index):   # noqa
        "overriden"
        # place external editor in the center of the screen
        if editor.parent() is None:
            r = QtWidgets.QApplication.desktop().screenGeometry()
            x = (r.left() + r.right() - editor.geometry().width()) / 2
            y = (r.bottom() + r.top() - editor.geometry().height()) / 2
            cnt = QtCore.QPoint(x, y)
            editor.move(cnt)
        else:
            super().updateEditorGeometry(editor, option, index)
            ###################
            # temporary solution.
            # Otherwise checked editors are moved to the right
            # if index.data(QtCore.Qt.CheckStateRole is not None):
            #     editor.move(editor.pos().x()-26, editor.pos().y())
            #     editor.resize(option.rect.size())
            if index.data(QtCore.Qt.CheckStateRole) is not None:
                editor.move(option.rect.x(), editor.pos().y())
                editor.resize(option.rect.width(), editor.height())


# ============================= Model
class TreeItem(object):
    """item in a option tree. Base abstract class.
    Item is represented as a row in a QTreeView"""

    def __init__(self, data, parent=None):
        self.parentItem = parent
        self.itemData = data
        self.childItems = []
        self.setchecked_receivers = []
        self.check_status = None
        if parent is not None:
            parent.appendChild(self)

    def appendChild(self, item):   # noqa
        self.childItems.append(item)

    def child(self, row):
        return self.childItems[row]

    def childCount(self):   # noqa
        return len(self.childItems)

    def columnCount(self):   # noqa
        return 2

    def data(self, column):
        return None

    def parent(self):
        return self.parentItem

    def row(self):
        return self.parentItem.childItems.index(self) \
                if self.parentItem else 0

    def is_checked(self):
        return None

    def setChecked(self, val):   # noqa
        self.check_status = val
        for r in self.setchecked_receivers:
            r(val)


class CaptionTreeItem(TreeItem):
    "Caption row in a treeview"
    def __init__(self, data, parent=None):
        "(caption string, root item)"
        super(CaptionTreeItem, self).__init__(data, parent)

    def data(self, column):
        return self.itemData if column == 0 else None


class ValueTreeItem(TreeItem):
    "name: option row in a tree view"
    def __init__(self, data, parent):
        "((name, option entry), CaptionTreeItem)"
        super(ValueTreeItem, self).__init__(data, parent)
        if self.itemData[1].have_status():
            self.check_status = self.itemData[1].get_status()

    def data(self, column):
        return self.itemData[column]

    def is_checked(self):
        return self.check_status

    def setChecked(self, val):   # noqa
        super().setChecked(val)
        self.itemData[1].set_status(val)


class OptionsModel(QtCore.QAbstractItemModel):
    "Tree like model for options representation"
    def __init__(self, opts, delegate):
        super(OptionsModel, self).__init__()
        self._root_item = TreeItem("Root")
        self._setup_model_data(opts, self._root_item)
        self.is_active = lambda x: True
        self.delegate = delegate

    def rowCount(self, parent):   # noqa
        "overriden"
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            return self._root_item.childCount()
        else:
            return parent.internalPointer().childCount()

    def columnCount(self, parent):   # noqa
        "overriden"
        if parent.isValid():
            return parent.internalPointer().columnCount()
        else:
            return self._root_item.columnCount()

    def index(self, row, column, parent):
        "overriden"
        if not self.hasIndex(row, column, parent):
            return QtCore.QModelIndex()

        if not parent.isValid():
            child = self._root_item.child(row)
        else:
            child = parent.internalPointer().child(row)

        if child:
            return self.createIndex(row, column, child)
        else:
            return QtCore.QModelIndex()

    def parent(self, index):
        "overriden"
        if not index.isValid():
            return QtCore.QModelIndex()

        parent = index.internalPointer().parent()
        if parent == self._root_item:
            return QtCore.QModelIndex()

        return self.createIndex(parent.row(), 0, parent)

    def data(self, index, role):
        "overriden"
        if not index.isValid():
            return None
        item = index.internalPointer()
        if role == QtCore.Qt.DisplayRole or role == QtCore.Qt.EditRole:
            return item.data(index.column())
        elif role == QtCore.Qt.CheckStateRole:
            return item.is_checked()
        else:
            return None

    def flags(self, index):
        "overriden"
        item = index.internalPointer()
        ret = QtCore.Qt.ItemIsEnabled
        # only value rows are considered
        if item.childCount() == 0:
            act = self.is_active(item.data(1)) and \
                    self.delegate.widget_by_index(index).isEnabled()
            if act:
                # active rows are selectable and editable
                ret = ret | QtCore.Qt.ItemIsSelectable
                if index.column() == 0 and\
                        index.internalPointer().is_checked() is not None:
                    ret = ret | QtCore.Qt.ItemIsUserCheckable
                if index.column() == 1:
                    ret = ret | QtCore.Qt.ItemIsEditable
            else:
                # no flags for disabled rows
                ret = QtCore.Qt.NoItemFlags

        return ret

    def _setup_model_data(self, data, root):
        "builds a model tree"
        caps = data.captions()
        for c in caps:
            newc = CaptionTreeItem(c, root)
            for v in data.cap_options(c):
                ValueTreeItem(v, newc)


# ---------------------- OptionsView
class OptionsView(QtWidgets.QTreeView):
    "options representation widget"
    def __init__(self, opt_list, conf=None, parent=None):
        "(OptionsList opt_list, OptionWidgetConfigure conf, QWidget parent)"
        super(OptionsView, self).__init__(parent)
        if conf is None:
            conf = OptionWidgetConfigure.default()
        # apply configuration
        opt_list.set_configuration(conf)
        # build model/view
        self.delegate = OptionsValueDelegate(conf)
        self.model = OptionsModel(opt_list, self.delegate)
        self.setModel(self.model)
        self.setItemDelegate(self.delegate)
        # set QTreeView options
        self.expandAll()
        self.resizeColumnToContents(0)
        self.setAllColumnsShowFocus(True)
        self.setHeaderHidden(True)
        self.setIndentation(conf.branch_indent)

    def is_active_delegate(self, func):
        """define a function which sets active status for entries
            func = bool function(OptionEntry)
        """
        self.model.is_active = func

    def keyPressEvent(self, event):   # noqa
        "overriden"
        # add enter (return key in qt notation) pressed to editor event
        if event.key() in [QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return]:
            for index in self.selectedIndexes():
                if index.flags() & QtCore.Qt.ItemIsEditable:
                    trigger = QtWidgets.QAbstractItemView.EditKeyPressed
                    self.edit(index, trigger, event)
                    break
        else:
            # using else: because otherwise it emits enter signal
            # for the whole form
            super().keyPressEvent(event)

    def mousePressEvent(self, event):   # noqa
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.pos())
            if (index.column() == 1):
                self.edit(index)
        super().mousePressEvent(event)
