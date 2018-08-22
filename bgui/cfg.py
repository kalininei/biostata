from PyQt5 import QtGui, QtCore
import resources   # noqa


class ViewConfig(object):
    _conf = None

    @classmethod
    def get(cls):
        if cls._conf is None:
            cls._conf = cls()
        return cls._conf

    def __init__(self):
        self._basic_font_size = 10
        self._margin = 3

        self.caption_color = QtGui.QColor(230, 250, 250)
        self.bg_color = QtGui.QColor(255, 255, 255)

        # boolean icons
        self._boolpics = [QtGui.QPixmap(':/red-minus'),
                          QtGui.QPixmap(':/green-plus'),
                          QtGui.QPixmap(':/red-minus-border'),
                          QtGui.QPixmap(':/green-plus-border')]

        # add some extra white space to make final icons smaller
        def add_w_space(pm, coef):
            height = pm.size().height()
            delta = coef * height
            pm2 = QtGui.QImage(height + 2*delta, height + 2*delta,
                               QtGui.QImage.Format_ARGB32_Premultiplied)
            pm2.fill(QtCore.Qt.transparent)
            painter = QtGui.QPainter(pm2)
            painter.drawPixmap(delta, delta, height, height, pm)
            painter.end()
            return QtGui.QPixmap.fromImage(pm2)

        for i in range(4):
            self._boolpics[i] = add_w_space(self._boolpics[i], 0.1)

        self._boolpics_data = [None] * 4
        self._boolpics_subdata = [None] * 4

        self.refresh()

    def refresh(self):
        self._main_font = QtGui.QFont()
        self._main_font.setPointSize(self._basic_font_size)
        self._caption_font = QtGui.QFont(self._main_font)
        self._caption_font.setBold(True)
        self._caption_font.setPointSize(self._main_font.pointSize() + 2)

        self._subcaption_font = QtGui.QFont(self._main_font)
        self._subcaption_font.setBold(True)

        self._subdata_font = QtGui.QFont(self._main_font)
        self._subdata_font.setItalic(True)
        self._subdata_font.setPointSize(self._main_font.pointSize() - 2)

        def font_height(fnt):
            return QtGui.QFontMetrics(fnt).height()
        self._data_font_height = font_height(self.data_font())
        self._subdata_font_height = font_height(self.subdata_font())
        self._caption_font_height = font_height(self.caption_font())
        self._subcaption_font_height = font_height(self.subcaption_font())

        for i in range(4):
            self._boolpics_data[i] = self._boolpics[i].scaledToHeight(
                    self.data_font_height(),
                    mode=QtCore.Qt.SmoothTransformation)
            self._boolpics_subdata[i] = self._boolpics[i].scaledToHeight(
                    self.subdata_font_height(),
                    mode=QtCore.Qt.SmoothTransformation)

    @staticmethod
    def ftos(v):
        return format(v, '.6g')

    def data_font(self):
        return self._main_font

    def caption_font(self):
        return self._caption_font

    def subcaption_font(self):
        return self._subcaption_font

    def subdata_font(self):
        return self._subdata_font

    def data_font_height(self):
        return self._data_font_height

    def subdata_font_height(self):
        return self._subdata_font_height

    def caption_font_height(self):
        return self._caption_font_height

    def subcaption_font_height(self):
        return self._subcaption_font_height

    def margin(self):
        return self._margin

    def true_icon(self, w_border=False):
        if w_border:
            return self._boolpics_data[3]
        else:
            return self._boolpics_data[1]

    def false_icon(self, w_border=False):
        if w_border:
            return self._boolpics_data[2]
        else:
            return self._boolpics_data[0]

    def true_subicon(self, w_border=False):
        if w_border:
            return self._boolpics_subdata[3]
        else:
            return self._boolpics_subdata[1]

    def false_subicon(self, w_border=False):
        if w_border:
            return self._boolpics_subdata[2]
        else:
            return self._boolpics_subdata[0]
