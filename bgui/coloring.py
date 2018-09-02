import copy
import collections
from PyQt5 import QtGui, QtCore
from bgui import cfg


def luminocity(rgb):
    return 0.2126*rgb[0] + 0.7151*rgb[1] + 0.0721*rgb[2]


def get_foreground(background):
    """ calculate best fit foreground color from given background
        background (QColor)
        returns (QColor)
    """
    r = background.red()
    g = background.green()
    b = background.blue()
    if luminocity((r, g, b)) < 140:
        return QtGui.QColor(255, 255, 255)
    else:
        return QtGui.QColor(0, 0, 0)


def get_group_color_light(igr):
    m = igr % len(Random220.c)
    return QtGui.QColor(*Random220.c[m])


class Coloring:
    def __init__(self, datatab):
        self.use = False
        self.absolute_limits = True
        self.limits = [None, None]

        self.conf = cfg.ViewConfig.get()
        self._row_colors = []
        self._row_values = []
        self.color_scheme = ColorScheme.default()

        self.set_column(datatab, "id")

    def get_color(self, irow):
        "returns QtGui.QColor from numerical value"
        if not self.use:
            return None
        else:
            if self._row_colors[irow] is None:
                self._row_colors[irow] = self._calculate_color(irow)
            return self._row_colors[irow]

    def set_column(self, datatab, cname):
        self.color_by = cname
        self.dt_type = datatab.columns[cname].dt_type

        if self.dt_type in ["REAL", "INTEGER"]:
            self._global_limits = list(datatab.get_raw_minmax(cname, True))
        elif self.dt_type in ["BOOLEAN", "TEXT", "ENUM"]:
            # raw_value -> (index, representation value)
            posible_values = sorted(
                    datatab.get_distinct_column_raw_vals(cname))
            col = datatab.columns[cname]
            self._global_values_dictionary = collections.OrderedDict()
            for i, pv in enumerate(posible_values):
                self._global_values_dictionary[pv] = (i, col.repr(pv))
            self._global_limits = [0, len(posible_values) - 1]
        else:
            raise NotImplementedError

    def update(self, datatab):
        if not self.use:
            return
        # check if datatab contains column, otherwise switch to id
        if self.color_by not in datatab.columns:
            self.set_column(datatab, 'id')

        self._row_colors = [None] * datatab.n_rows()
        self._row_values = datatab.get_raw_column_values(self.color_by)

        if self.dt_type in ["REAL", "INTEGER"]:
            # limits
            if not self.absolute_limits:
                dd = [x for x in self._row_values if x is not None]
                if not dd:
                    dd = [0]
                self.limits[0] = min(dd)
                self.limits[1] = max(dd)
            else:
                self.limits = self._global_limits

            # normalize self._row_values
            fl = self.limits[1] - self.limits[0]

            def nrm(a):
                if a is None:
                    return None
                elif fl == 0:
                    return 0
                else:
                    return (a - self.limits[0])/fl
            self._row_values = list(map(nrm, self._row_values))
        elif self.dt_type in ["BOOLEAN", "ENUM", "TEXT"]:
            dd = set([x for x in self._row_values if x is not None])
            if not dd:
                anyval = next(iter(self._global_values_dictionary.keys()),
                              None)
                if anyval is not None:
                    dd.add(anyval)
                else:
                    # Just in case. We should not get here.
                    # Maybe only if a whole column is None or smth.
                    dd = set([None])
            # limits
            if not self.absolute_limits:
                self._values_dictionary = collections.OrderedDict()
                i = 0
                for k, v in self._global_values_dictionary.items():
                    if k in dd:
                        self._values_dictionary[k] = (i, v[1])
                        i += 1
            else:
                self._values_dictionary = copy.deepcopy(
                        self._global_values_dictionary)
            # Add values which do not present in global dictionary.
            # This could happen f.e. for collapsed TEXT data types
            col = datatab.columns[self.color_by]
            for v in sorted(dd):
                if v not in self._values_dictionary:
                    self._values_dictionary[v] = (
                            len(self._values_dictionary), col.repr(v))

            # normalize self._row_values
            self.limits[0] = 0
            self.limits[1] = len(self._values_dictionary) - 1
            fl = self.limits[1] - self.limits[0]

            def nrm(a):
                if a is None:
                    return None
                elif fl == 0:
                    return 0
                else:
                    return (self._values_dictionary[a][0] - self.limits[0])/fl
            self._row_values = list(map(nrm, self._row_values))

    def _calculate_color(self, irow):
        return self.color_scheme.get_color(self._row_values[irow])

    def draw_legend(self, size):
        height = size.height()
        width = size.width()
        fh = self.conf.data_font_height()
        margin = int(0.5 * self.conf.data_font_height())
        rwidth = 1.5 * fh

        ret = QtGui.QImage(size, QtGui.QImage.Format_ARGB32_Premultiplied)
        ret.fill(QtCore.Qt.white)
        if self.use is False:
            return QtGui.QPixmap.fromImage(ret)

        # start drawing
        painter = QtGui.QPainter(ret)
        # caption
        maxw = 0
        cur_y = margin
        painter.setFont(self.conf.caption_font())
        rect = QtCore.QRect(
                margin, cur_y,
                width, cur_y + self.conf.caption_font_height())
        bb = painter.drawText(rect, 0, self.color_by)
        maxw = max(maxw, bb.right())
        cur_y += self.conf.caption_font_height() + margin

        rheight = height - cur_y - margin
        painter.setFont(self.conf.data_font())
        if self.dt_type in ["REAL", "INTEGER"]:
            # rectangle
            pm = self.color_scheme.pic(rheight, rwidth, False)
            painter.drawPixmap(QtCore.QPoint(margin, cur_y), pm)

            # text values: (weight -> value)
            tvals = self.get_optimal_capslist(rheight, fh, self.limits)
            for w, v in tvals:
                px = margin + rwidth + margin
                py = cur_y + (1-w) * rheight
                trect = QtCore.QRect(
                        px, py - int(fh/2), width, py + int(fh/2))
                bb = painter.drawText(trect, 0, v)
                maxw = max(maxw, bb.right())
                sd = int(margin/2)
                painter.drawLine(QtCore.QPoint(margin-sd, py),
                                 QtCore.QPoint(margin+rwidth+sd, py))
        elif self.dt_type in ["BOOLEAN", "TEXT", "ENUM"]:
            # temporary equidistant colorscheme for drawing
            w = list(range(self.limits[0], self.limits[1]+1))
            nrm = [x/self.limits[1] for x in w] if self.limits[1] > 0 else [0]
            c = [self.color_scheme.get_rgb_color(x) for x in nrm]
            _tsc = ColorScheme(nrm, c)
            _tsc.set_discrete(True)
            # rectangle
            pm = _tsc.pic(rheight, rwidth, False)
            painter.drawPixmap(QtCore.QPoint(margin, cur_y), pm)
            # zone bounds
            for y in range(self.limits[0], self.limits[1]+2):
                w = y/(self.limits[1]+1)
                py = cur_y + (1-w) * rheight
                sd = int(margin/2)
                painter.drawLine(QtCore.QPoint(margin-sd, py),
                                 QtCore.QPoint(margin+rwidth+sd, py))
            # text captions
            it = iter(self._values_dictionary.values())
            for y in range(self.limits[0], self.limits[1]+1):
                w = (y+0.5)/(self.limits[1]+1)
                px = margin + rwidth + margin
                py = cur_y + (1-w) * rheight
                trect = QtCore.QRect(
                        px, py - int(fh/2), width, py + int(fh/2))
                bb = painter.drawText(trect, 0, next(it)[1])
                maxw = max(maxw, bb.right())
        else:
            raise NotImplementedError

        painter.end()
        ret = ret.copy(QtCore.QRect(0, 0, maxw, height))
        return QtGui.QPixmap.fromImage(ret)

    def get_optimal_capslist(self, ht, fh, lims):
        fl = lims[1] - lims[0]
        # a minimum margin between two records
        comf_margin = 0.8 * fh
        # how many records can we draw
        num_records = ht/(fh+comf_margin) + 1
        if self.dt_type == 'INTEGER':
            # we dont't want steps lower than 1 for integer data
            num_records = min(num_records, lims[1] - lims[0] + 1)
        # get best values
        st = self.get_best_steping(num_records + 1, lims)
        # assemble caplist
        ret = []
        ret.append((0, self.conf.ftos(lims[0])))
        for s in st:
            ret.append(((s-lims[0])/fl, self.conf.ftos(s)))

        ret.append((1, self.conf.ftos(lims[1])))
        return ret

    def get_best_steping(self, mostticks, lims):
        import bisect
        import math
        largest = lims[1] - lims[0]
        if largest == 0:
            return []
        minimum = largest / mostticks
        magnitude = 10 ** math.floor(math.log(minimum, 10))
        residual = minimum / magnitude
        # this table must begin with 1 and end with 10
        table = [1, 2, 2.5, 5, 10]
        if residual < 10:
            tick = table[bisect.bisect_right(table, residual)]
        else:
            tick = 10
        tick = tick * magnitude

        r0 = math.floor(lims[0]/tick)*tick
        # r0 = math.floor(lims[0]/magnitude)*magnitude
        ret = [r0]
        while ret and ret[-1] < lims[1]:
            ret.append(ret[-1] + tick)
        while ret and ret[0] - lims[0] < 0.8*tick:
            ret.pop(0)
        while ret and lims[1] - ret[-1] < 0.8*tick:
            ret.pop()
        return ret


# ======================== Color schemes
class ColorScheme:
    def __init__(self, w, c):
        self.__orig_weights = w
        self.__orig_colors = c
        self._dcount = -1
        self._weights = copy.deepcopy(w)
        self._colors = copy.deepcopy(c)
        self._continuous = True
        self._reversed = False
        self._default_color = (0, 0, 0)

    def _continuous_to_discrete(self):
        self._colors.append(self._colors[-1])
        w = []
        for x, y in zip(self._weights[1:], self._weights[:-1]):
            w.append((x+y)/2.0)
        w.append(2 - w[-1])
        w.insert(0, -w[0])
        self._weights = [(x-w[0])/(w[-1]-w[0]) for x in w]

    def _set_discrete_reversed(self, is_discrete, is_reversed, dcount):
        self._weights = copy.deepcopy(self.__orig_weights)
        self._colors = copy.deepcopy(self.__orig_colors)
        self._continuous = not is_discrete
        self._reversed = is_reversed
        self._dcount = dcount
        if is_reversed:
            self._colors.reverse()
            self._weights.reverse()
            for i, w in enumerate(self._weights):
                self._weights[i] = 1 - w
        if is_discrete:
            if dcount == 1 or len(self._weights) < 2:
                self._weights = [0, 1]
                self._colors = [self._colors[0], self._colors[0]]
                return
            elif dcount > 1:
                w = [x/(dcount-1) for x in range(dcount)]
                self._continuous = True
                c = [self.get_rgb_color(x) for x in w]
                self._continuous = False
                self._weights = w
                self._colors = c

            self._continuous_to_discrete()

    def set_discrete(self, is_discrete=None, count=-1):
        if is_discrete is None:
            is_discrete = self._continuous
        if self._continuous is is_discrete or count != self._dcount:
            self._set_discrete_reversed(
                    is_discrete, self._reversed, count)

    def set_reversed(self, is_reversed=None):
        if is_reversed is None:
            is_reversed = not self._reversed
        if self._reversed is not is_reversed:
            self._set_discrete_reversed(
                    not self._continuous, is_reversed, self._dcount)

    def is_reversed(self):
        return self._reversed

    def is_discrete(self):
        return not self._continuous

    def get_rgb_color(self, val):
        if val is None:
            return self._default_color
        if val <= 0.0:
            return self._colors[0]
        if val >= 1.0:
            return self._colors[-1]

        for i, w in enumerate(self._weights):
            if val < w:
                break

        if not self._continuous:
            return self._colors[i-1]
        else:
            w = (val-self._weights[i-1])/(self._weights[i]-self._weights[i-1])
            r = int(w*self._colors[i][0]+(1-w)*self._colors[i-1][0])
            g = int(w*self._colors[i][1]+(1-w)*self._colors[i-1][1])
            b = int(w*self._colors[i][2]+(1-w)*self._colors[i-1][2])
            return (r, g, b)

    def get_color(self, val):
        return self.qcolor(self.get_rgb_color(val))

    def qcolor(self, rgb):
        return QtGui.QColor(*rgb)

    def default_color(self):
        return self.qcolor(self._default_color)

    def set_default_color(self, rgb):
        self._default_color = copy.deepcopy(rgb)

    def pic(self, height, width, is_horizontal):
        " -> QPixmap "
        if not is_horizontal:
            height, width = width, height

        ret = QtGui.QImage(QtCore.QSize(width, height),
                           QtGui.QImage.Format_ARGB32_Premultiplied)
        ret.fill(QtCore.Qt.white)
        painter = QtGui.QPainter(ret)
        if self._continuous:
            # continuous
            rect = ret.rect()
            gradient = QtGui.QLinearGradient(rect.topLeft(), rect.topRight())
            for w, c in zip(self._weights, self._colors):
                gradient.setColorAt(w, QtGui.QColor(*c))
            painter.fillRect(rect, gradient)
        else:
            # discrete
            xcur = 0
            for i in range(len(self._weights))[:-1]:
                delta = (self._weights[i+1] - self._weights[i]) * width
                rect = QtCore.QRect(xcur, 0, delta+1, height)
                painter.fillRect(rect, QtGui.QColor(*self._colors[i]))
                xcur += delta

        painter.drawRect(0, 0, width-1, height-1)
        painter.end()

        ret = QtGui.QPixmap.fromImage(ret)

        if not is_horizontal:
            tr = QtGui.QTransform()
            tr.rotate(-90)
            ret = ret.transformed(tr)
        return ret

    def copy_settings_from(self, other):
        self._set_discrete_reversed(not other._continuous,
                                    other._reversed, other._dcount)
        self._default_color = copy.deepcopy(other._default_color)

    @classmethod
    def default(cls):
        return RainbowCS()

    @classmethod
    def scheme_by_order(cls, order):
        lst = cls.cs_list()
        order = (order-1) % len(lst) + 1
        for v in lst.values():
            if v.order == order:
                return v
        raise KeyError

    @classmethod
    def cs_list(cls):
        """ -> OrderedSet {name: class}
        """
        ret = collections.OrderedDict()
        for c in sorted(cls.__subclasses__(), key=lambda v: v.order):
            ret[c.name] = c
        return ret


# ======================= Predefined Color schemes
class RainbowCS(ColorScheme):
    name = "Rainbow"
    order = 1

    def __init__(self):
        w = [x/4.0 for x in range(5)]
        c = [(0, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0),
             (255, 0, 0)]
        super().__init__(w, c)


class RedWhiteBlueCS(ColorScheme):
    name = "Cool to Warm"
    order = 2

    def __init__(self):
        w = [0, 0.5, 1.0]
        c = [(0, 0, 220), (220, 220, 220), (220, 0, 0)]
        super().__init__(w, c)


class GrayScaleCS(ColorScheme):
    name = "Grayscale"
    order = 3

    def __init__(self):
        w = [0, 1.0]
        c = [(15, 15, 15), (240, 240, 240)]
        super().__init__(w, c)


class MagmaCS(ColorScheme):
    name = "Magma"
    order = 4

    def __init__(self):
        w = [x/8.0 for x in range(9)]
        c = [(0, 0, 0), (28, 16, 70), (80, 18, 123), (130, 37, 129),
             (182, 54, 121), (230, 81, 98), (251, 136, 97), (254, 196, 136),
             (251, 252, 191)]
        super().__init__(w, c)


class TricolorCS(ColorScheme):
    name = "Tricolor"
    order = 5

    def __init__(self):
        w = [0, 0.5, 1]
        c = [(213, 43, 30), (0, 57, 166), (255, 255, 255)]
        super().__init__(w, c)


class PlasmaCS(ColorScheme):
    name = "Plasma"
    order = 6

    def __init__(self):
        w = [x/8.0 for x in range(9)]
        c = [(0, 0, 255), (0, 255, 255), (0, 255, 0), (255, 255, 0),
             (255, 0, 0)]
        c = [(12, 7, 134), (76, 2, 161), (126, 3, 167), (169, 35, 149),
             (203, 71, 119), (229, 108, 91), (248, 149, 64), (253, 196, 39),
             (239, 248, 33)]
        super().__init__(w, c)


class ColdAndHotCS(ColorScheme):
    name = "Cold and Hot"
    order = 7

    def __init__(self):
        w = [0, 0.45, 0.5, 0.55, 1.0]
        c = [(0, 255, 255), (0, 0, 255), (0, 0, 128), (255, 0, 0),
             (255, 255, 0)]
        super().__init__(w, c)


class BlotCS(ColorScheme):
    name = "Blot"
    order = 8

    def __init__(self):
        w = [x/5.0 for x in range(6)]
        c = [(0, 0, 255), (255, 0, 255), (0, 255, 255), (0, 255, 0),
             (255, 255, 0), (255, 0, 0)]
        super().__init__(w, c)


class RandomCS(ColorScheme):
    name = "Random"
    order = 9

    def __init__(self):
        w = [x/99.0 for x in range(100)]
        c = [(212, 143, 82), (105, 155, 99), (21, 188, 111), (8, 188, 232), (10, 113, 167), (194, 173, 234), (91, 110, 246), (44, 107, 124), (12, 20, 184), (59, 32, 199), (160, 99, 136), (63, 110, 88), (216, 245, 88), (80, 46, 89), (113, 144, 187), (115, 222, 8), (205, 8, 75), (203, 93, 140), (65, 210, 26), (119, 144, 73), (37, 239, 240), (20, 137, 142), (163, 17, 95), (60, 108, 95), (67, 227, 10), (70, 59, 131), (28, 136, 169), (149, 207, 24), (37, 174, 39), (129, 91, 231), (5, 40, 117), (186, 55, 24), (22, 101, 191), (159, 20, 194), (203, 103, 92), (95, 105, 175), (201, 213, 179), (205, 245, 203), (189, 33, 195), (156, 188, 149), (193, 225, 201), (176, 65, 126), (91, 232, 147), (56, 244, 169), (29, 179, 47), (128, 92, 95), (8, 139, 77), (128, 144, 60), (233, 191, 148), (179, 69, 85), (149, 75, 137), (76, 148, 217), (26, 58, 233), (220, 202, 222), (158, 232, 104), (68, 27, 100), (193, 130, 116), (197, 66, 57), (112, 118, 205), (14, 148, 175), (93, 36, 103), (69, 99, 245), (157, 146, 230), (225, 76, 41), (76, 211, 74), (66, 178, 89), (131, 28, 89), (240, 241, 248), (5, 102, 183), (116, 73, 230), (113, 138, 135), (158, 20, 68), (11, 188, 213), (214, 106, 204), (10, 111, 179), (59, 173, 61), (66, 107, 117), (131, 149, 82), (7, 243, 213), (148, 26, 103), (68, 237, 60), (19, 16, 92), (47, 193, 90), (157, 180, 76), (224, 35, 98), (224, 149, 158), (168, 175, 78), (21, 116, 212), (191, 65, 217), (241, 215, 215), (23, 142, 146), (233, 113, 187), (27, 26, 99), (47, 245, 26), (53, 40, 146), (117, 128, 32), (235, 6, 137), (70, 154, 131), (123, 18, 74), (44, 87, 229)]   # noqa
        super().__init__(w, c)
        # disable continuous schemes
        self._continuous = False

    def set_discrete(self, is_discrete, count=-1):
        if is_discrete is True:
            super().set_discrete(True, count)


class Random150CS2(ColorScheme):
    name = "Random Lt=150"
    order = 10
    c = [(41, 163, 250), (59, 249, 171), (94, 63, 245), (93, 51, 243), (50, 246, 242), (231, 103, 60), (77, 53, 249), (75, 207, 216), (72, 251, 41), (196, 251, 56), (232, 57, 244), (232, 174, 72), (134, 156, 174), (215, 222, 75), (229, 75, 161), (205, 97, 162), (115, 133, 176), (90, 168, 209), (143, 132, 162), (128, 103, 203), (79, 229, 78), (135, 97, 198), (253, 243, 41), (121, 180, 115), (210, 81, 145), (137, 192, 106), (246, 162, 55), (85, 209, 106), (154, 73, 233), (251, 54, 242), (53, 245, 149), (61, 54, 243), (63, 229, 240), (68, 124, 226), (238, 132, 56), (117, 204, 103), (224, 178, 80), (216, 191, 86), (119, 213, 80), (210, 85, 195), (198, 108, 197), (252, 52, 64), (230, 68, 148), (196, 100, 163), (246, 150, 51), (220, 73, 219), (199, 139, 103), (70, 235, 73), (111, 251, 46), (73, 121, 232), (254, 189, 45), (79, 76, 219), (80, 71, 226), (198, 102, 152), (98, 169, 210), (88, 181, 218), (119, 145, 177), (129, 176, 139), (78, 204, 220), (245, 80, 54), (59, 242, 144), (158, 105, 193), (103, 51, 249), (48, 253, 74), (254, 102, 37), (207, 119, 101), (211, 200, 82), (78, 219, 195), (237, 61, 128), (84, 232, 65), (71, 238, 69), (182, 66, 239), (192, 74, 219), (254, 79, 49), (206, 133, 90), (168, 136, 155), (49, 192, 250), (57, 103, 244), (207, 144, 87), (198, 65, 226), (216, 180, 91), (237, 179, 66), (126, 221, 76), (52, 53, 244), (143, 171, 130), (164, 124, 180), (135, 102, 205), (155, 163, 138), (174, 140, 117), (94, 202, 214), (164, 62, 230), (138, 105, 191), (67, 250, 56), (120, 176, 141), (133, 204, 104), (174, 155, 122), (124, 209, 83), (243, 225, 49), (84, 170, 217), (233, 75, 195)]   # noqa

    def __init__(self):
        w = [x/99.0 for x in range(100)]
        super().__init__(w, Random150CS2.c)
        # disable continuous schemes
        self._continuous = False

    def set_discrete(self, is_discrete, count=-1):
        if is_discrete is True:
            super().set_discrete(True, count)


class Random220(ColorScheme):
    name = "Random Lt=220"
    order = 11
    c = [(213, 246, 198), (255, 185, 181), (207, 229, 215), (212, 246, 191), (217, 224, 225), (252, 199, 179), (197, 245, 233), (239, 187, 245), (226, 225, 209), (203, 196, 236), (229, 247, 197), (253, 182, 244), (255, 245, 187), (228, 229, 209), (196, 248, 197), (199, 194, 247), (207, 226, 235), (203, 233, 201), (185, 235, 253), (206, 241, 203), (187, 249, 183), (191, 255, 199), (244, 201, 205), (228, 209, 204), (230, 241, 203), (192, 210, 255), (190, 245, 243), (196, 188, 253), (186, 243, 245), (196, 213, 235), (251, 226, 192), (221, 240, 198), (232, 199, 248), (182, 182, 252), (203, 192, 255), (209, 230, 219), (234, 217, 214), (208, 204, 233), (243, 204, 213), (197, 238, 221), (192, 242, 250), (244, 234, 202), (253, 242, 191), (205, 237, 238), (235, 200, 221), (180, 252, 200), (196, 201, 250), (243, 201, 223), (219, 191, 245), (236, 209, 216), (191, 249, 199), (192, 242, 232), (218, 192, 250), (201, 255, 190), (215, 193, 254), (187, 223, 250), (202, 217, 237), (204, 253, 194), (207, 224, 208), (226, 208, 206), (196, 235, 199), (195, 219, 242), (182, 218, 253), (238, 221, 200), (201, 238, 220), (193, 210, 241), (213, 204, 240), (186, 246, 226), (196, 197, 237), (213, 218, 224), (186, 220, 254), (236, 196, 216), (246, 235, 196), (218, 219, 214), (248, 241, 198), (243, 239, 197), (211, 237, 219), (222, 205, 227), (252, 232, 194), (212, 225, 232), (197, 248, 220), (198, 213, 245), (254, 249, 193), (247, 209, 200), (253, 192, 201), (208, 232, 239), (243, 198, 190), (243, 226, 192), (205, 230, 225), (252, 191, 227), (196, 185, 251), (198, 250, 207), (246, 188, 207), (192, 202, 248), (247, 228, 201), (244, 243, 195), (199, 191, 248), (220, 230, 203), (186, 199, 252), (210, 223, 214)]   # noqa

    def __init__(self):
        w = [x/99.0 for x in range(100)]

        super().__init__(w, Random220.c)
        # disable continuous schemes
        self._continuous = False

    def set_discrete(self, is_discrete, count=-1):
        if is_discrete is True:
            super().set_discrete(True, count)
