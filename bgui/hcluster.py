from bgui import qtcommon
from PyQt5 import QtWidgets, QtCore, QtGui
from prog import basic
from bgui import coloring
from bgui import hcluster_acts
import numpy as np


class DendStep:
    def __init__(self, iden, pnt, left=None, right=None):
        self.iden = iden
        self.is_selected = False
        self.pnt = pnt
        self.left = left
        self.right = right
        self.top = None
        self.poly = None
        self.pen = QtGui.QPen()
        self.pen.setWidth(2)
        self.pen.setColor(QtGui.QColor(0, 0, 0))
        self.brush = QtGui.QBrush()
        self.brush.setColor(QtGui.QColor(0, 0, 0))
        self.brush.setStyle(QtCore.Qt.SolidPattern)
        self.font = QtGui.QFont()
        self.font.setPointSize(10)
        self.influence_rect = None

    def set_color(self, color):
        self.pen.setColor(color)
        self.brush.setColor(color)

    def draw(self, painter, to_screen, clip):
        if not self.poly:
            self.poly = [None] * 4
            if self.left is not None:
                self.poly[0] = QtCore.QPointF(self.left.pnt.x(), self.pnt.y())
                self.poly[1] = QtCore.QPointF(self.right.pnt.x(), self.pnt.y())
            if self.top is not None:
                self.poly[2] = self.pnt
                self.poly[3] = QtCore.QPointF(self.pnt.x(), self.top.pnt.y())
        painter.setPen(self.pen)

        # horizontal line
        if self.poly[0] is not None:
            p1, p2 = to_screen(self.poly[0]), to_screen(self.poly[1])
            if clip.top() <= p1.y() <= clip.bottom():
                p1.setX(max(min(clip.right(), p1.x()), clip.left()))
                p2.setX(max(min(clip.right(), p2.x()), clip.left()))
                if p1.x() != p2.x():
                    painter.drawLine(p1, p2)
        # vertical line
        if self.poly[2] is not None:
            p1, p2 = to_screen(self.poly[2]), to_screen(self.poly[3])
            if clip.left() <= p1.x() <= clip.right():
                p1.setY(max(min(clip.bottom(), p1.y()), clip.top()))
                p2.setY(max(min(clip.bottom(), p2.y()), clip.top()))
                if p1.y() != p2.y():
                    painter.drawLine(p1, p2)

        # selection circle
        pc = to_screen(self.pnt)
        if clip.contains(pc):
            self.influence_rect = QtCore.QRectF(pc.x() - 5, pc.y() - 5, 10, 10)
            if self.is_selected:
                painter.setBrush(self.brush)
                painter.setFont(self.font)
                painter.drawEllipse(pc, 4, 4)
                painter.drawText(pc.x() + 4, pc.y() - 4, str(self.iden))
        else:
            self.influence_rect = None

    def influence_zone(self, pnt):
        if not self.influence_rect:
            return False
        else:
            return self.influence_rect.contains(pnt)

    @staticmethod
    def settops(lst):
        for t in lst:
            if t.left is not None:
                t.left.top = t
                t.right.top = t


class Dendrogram(QtWidgets.QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.w = 0
        self.h = 0
        self.dw = 0
        self.dh = 0
        self.bottom_order = []
        self.steps = []

    def boundingRect(self):   # noqa
        return QtCore.QRectF(0.0, 0.0, self.w, self.h)

    def paint(self, painter, option, widget):
        # manual clip within s.draw due to svg export problems
        clip = self.mapRectFromScene(self.scene().axis.graph_rect)
        for s in self.steps:
            s.draw(painter, self.to_screen, clip)

    def get_rootsteps(self, ngroups):
        if len(self.steps) == 0:
            return []
        rootsteps = [self.steps[-1]]
        ig = 1
        while ig < ngroups:
            besty = self.steps[0].pnt.y() + 1
            cand = None
            for r in rootsteps:
                if r.pnt.y() < besty:
                    besty = r.pnt.y()
                    cand = r
            assert cand is not None
            rootsteps.remove(cand)
            rootsteps.append(cand.left)
            rootsteps.append(cand.right)
            ig += 1
        return sorted(rootsteps, key=lambda x: x.pnt.x())

    def reset_group_coloring(self, ngroups):
        def color_step(s, color):
            s.set_color(color)
            if s.left is not None:
                color_step(s.left, color)
            if s.right is not None:
                color_step(s.right, color)

        rootsteps = self.get_rootsteps(ngroups)
        black = coloring.QtGui.QColor(0, 0, 0)
        for s in self.steps:
            s.set_color(black)

        for i, s in enumerate(rootsteps):
            col = coloring.get_group_color(i)
            color_step(s, col)
        self.update()

    def to_screen(self, pnt):
        return QtCore.QPointF(pnt.x() / self.dw * self.w,
                              pnt.y() / self.dh * self.h)

    def to_internal(self, pnt):
        return QtCore.QPointF(pnt.x() * self.dw / self.w,
                              pnt.y() * self.dh / self.h)

    def vis_limits(self):
        r = self.mapRectFromScene(self.scene().axis.graph_rect)
        p1 = self.to_internal(r.topLeft())
        p2 = self.to_internal(r.bottomRight())
        return [p1.x(), p2.x()], [self.dh - p2.y(), self.dh - p1.y()]

    def reset_size(self, w, h):
        self.w = w
        self.h = h

    def set_linkage(self, linkage):
        nsamp = np.size(linkage, 0) + 1
        self.dw = float(nsamp) - 1.0
        self.dh = float(np.max(linkage[:, 2]))

        # build order of bottom nodes
        def place_items(lnk, sz, left, right, ret):
            left, right = int(left), int(right)
            if left < sz:
                ret.append(left)
            else:
                l, r = lnk[left-sz, 0], lnk[left-sz, 1]
                place_items(lnk, sz, l, r, ret)
            if right < sz:
                ret.append(right)
            else:
                l, r = lnk[right-sz, 0], lnk[right-sz, 1]
                place_items(lnk, sz, l, r, ret)

        st = np.argmax(linkage[:, 3])
        self.bottom_order = []
        place_items(linkage, nsamp, linkage[st, 0], linkage[st, 1],
                    self.bottom_order)

        # build steps
        self.steps = [None] * nsamp
        m = self.dh
        iden = 0
        for i, b in enumerate(self.bottom_order):
            iden += 1
            self.steps[int(b)] = DendStep(iden, QtCore.QPointF(float(i), m))
        for p in linkage:
            iden += 1
            d1, d2 = self.steps[int(p[0])], self.steps[int(p[1])]
            x, y = (d1.pnt.x() + d2.pnt.x())/2, m - p[2]
            self.steps.append(DendStep(iden, QtCore.QPointF(x, y), d1, d2))
        DendStep.settops(self.steps)

    def try_select(self, pnt):
        pnt = self.mapFromScene(pnt)
        for s in self.steps:
            if s.influence_zone(pnt):
                s.is_selected = not s.is_selected
                self.update()
                return


class Axis(QtWidgets.QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.w, self.h = 0.0, 0.0
        self.maxy, self.maxx = 1.0, 1.0
        self.limy, self.limx = [0, 1], [0, 1]
        self.yticks = []
        self.graph_rect = QtCore.QRectF()
        self.vert_font = QtGui.QFont()
        self.vert_font.setPointSize(10)
        self.hor_font = self.vert_font
        fm = QtGui.QFontMetricsF(self.vert_font)
        self.left_margin = float(fm.width('W') * 6)
        self.bottom_margin = float(fm.width('W') * 9)
        self.top_margin = float(10)
        self.right_margin = float(10)

    def boundingRect(self):   # noqa
        return QtCore.QRectF(0.0, 0.0, self.w, self.h)

    def paint(self, painter, option, widget):
        pen = QtGui.QPen()
        pen.setWidth(1)
        painter.setPen(pen)

        # rectangle
        painter.drawRect(self.graph_rect)

        # ticks
        # vertical
        painter.setFont(self.vert_font)
        k = int((self.limy[0]-self.yticks[0])/self.yticks[1])
        y = k * self.yticks[1] + self.yticks[0]
        while y <= self.limy[1]:
            if y >= self.limy[0]:
                yy = (y - self.limy[0]) / (self.limy[1] - self.limy[0])
                ytrue = self.graph_rect.height() * yy
                ytrue = self.graph_rect.bottom() - ytrue
                painter.drawLine(QtCore.QPointF(self.left_margin, ytrue),
                                 QtCore.QPointF(self.left_margin - 5, ytrue))
                p1 = QtCore.QPointF(0, ytrue - 10)
                p2 = QtCore.QPointF(self.left_margin - 8, ytrue + 10)
                r = QtCore.QRectF(p1, p2)
                f = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                painter.drawText(r, f, '{:.5g}'.format(y))
            y += self.yticks[1]

        # horizontal ticks
        painter.setFont(self.hor_font)
        for x in range(int(self.limx[0]), int(self.limx[1])+1):
            if x >= 0 and x >= self.limx[0] and x <= self.maxx:
                xx = (x - self.limx[0]) / (self.limx[1] - self.limx[0])
                xtrue = self.graph_rect.left() + self.graph_rect.width() * xx
                y = self.h - self.bottom_margin
                painter.drawLine(QtCore.QPointF(xtrue, y),
                                 QtCore.QPointF(xtrue, y + 5))
                txt = self.scene().horizontal_caption(x)
                painter.save()
                painter.translate(xtrue, self.h)
                painter.rotate(-90)
                p1 = QtCore.QPointF(0, -10)
                p2 = QtCore.QPointF(self.bottom_margin - 8, 10)
                r = QtCore.QRectF(p1, p2)
                f = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
                painter.drawText(r, f, txt)
                painter.restore()

    def set_maxvals(self, maxx, maxy):
        self.maxx, self.maxy = maxx, maxy
        self.set_limits([0, self.maxx], [0, self.maxy])

    def set_limits(self, limx, limy):
        ylen = self.limy[1] - self.limy[0]
        self.limx, self.limy = limx, limy
        if abs(ylen - self.limy[1] + self.limy[0]) > 1e-16:
            nticks = int(self.maxy / (self.limy[1] - self.limy[0]) * 8)
            self.yticks = basic.best_steping(nticks, [0, self.maxy])
        self.update()

    def reset_size(self, w, h):
        self.w = w
        self.h = h
        self.graph_rect = QtCore.QRectF(
            self.left_margin, self.top_margin,
            w - self.left_margin - self.right_margin,
            h - self.top_margin - self.bottom_margin)
        self.set_limits([0.0, self.maxx], [0.0, self.maxy])


class GLine(QtWidgets.QGraphicsItem):
    def __init__(self):
        super().__init__()
        self.lims = [0, 1]
        self.igroup = 0
        self.ipos = 0.5
        self.screeny = -1.0

    def boundingRect(self):   # noqa
        return self.scene().axis.boundingRect()

    def paint(self, painter, option, widget):
        dendrogram = self.scene().dendrogram
        axis = self.scene().axis
        rect = axis.graph_rect
        if self.ipos > axis.limy[1]:
            return
        if self.ipos < axis.limy[0]:
            return
        pen = QtGui.QPen()
        pen.setWidth(2)
        painter.setPen(pen)
        p = QtCore.QPointF(0, dendrogram.dh - self.ipos)
        p = dendrogram.to_screen(p) + dendrogram.pos()
        p1 = QtCore.QPointF(rect.left(), p.y())
        p2 = QtCore.QPointF(rect.right(), p.y())
        self.screeny = p.y()
        painter.drawLine(p1, p2)

    def influence_zone(self, pnt):
        return abs(pnt.y() - self.screeny) < 5

    def set_group_limits(self, lims):
        self.lims = [0.0] + lims
        self.set_igroup(min(4, len(self.lims)))

    def set_igroup(self, ig):
        if ig == self.igroup:
            return
        if ig < 1:
            ig = 1
        if ig > len(self.lims):
            ig = len(self.lims)
        self.igroup = ig
        if ig == 1:
            self.ipos = self.lims[-1] + 0.5
        else:
            a = len(self.lims) - ig
            self.ipos = 0.5 * (self.lims[a] + self.lims[a + 1])
        self.scene().ncluster_changed.emit(ig)
        self.update()

    def within_group(self, ipos, ig):
        if ig == 1:
            return ipos >= self.lims[-1]
        else:
            a = len(self.lims) - ig
            return self.lims[a] <= ipos <= self.lims[a + 1]

    def set_ipos(self, ip):
        self.ipos = ip
        if not self.within_group(ip, self.igroup):
            for ig in range(1, len(self.lims) + 1):
                if self.within_group(ip, ig):
                    self.igroup = ig
                    break
            else:
                self.igroup = len(self.lims)
                self.ipos = 0
            self.scene().ncluster_changed.emit(self.igroup)
        self.update()


class HierarchicalScene(QtWidgets.QGraphicsScene):
    ncluster_changed = QtCore.pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.dendrogram = Dendrogram()
        self.ncluster_changed.connect(self.dendrogram.reset_group_coloring)
        self.axis = Axis()
        self.gline = GLine()
        self.addItem(self.dendrogram)
        self.addItem(self.axis)
        self.addItem(self.gline)

    def set_linkage(self, linkage):
        self.dendrogram.set_linkage(linkage)
        self.axis.set_maxvals(self.dendrogram.dw, self.dendrogram.dh)
        self.gline.set_group_limits(linkage[:, 2].tolist())

    def reset_size(self, w, h):
        self.setSceneRect(QtCore.QRectF(0.0, 0.0, w, h))
        self.axis.reset_size(w, h)
        self.dendrogram.reset_size(self.axis.graph_rect.width(),
                                   self.axis.graph_rect.height())
        self.dendrogram.setPos(self.axis.graph_rect.topLeft())

    def move_content(self, v):
        np = self.dendrogram.pos() + v
        self.dendrogram.setPos(np)
        self.axis.set_limits(*self.dendrogram.vis_limits())

    def zoom_content(self, r):
        if r.width() == 0 or r.height() == 0:
            return
        op = self.dendrogram.mapFromScene(r.topLeft())
        xsc = self.axis.graph_rect.width()/r.width()
        ysc = self.axis.graph_rect.height()/r.height()
        self.dendrogram.reset_size(self.dendrogram.w * xsc,
                                   self.dendrogram.h * ysc)
        x = op.x()*xsc - self.axis.graph_rect.left()
        y = op.y()*ysc - self.axis.graph_rect.top()
        self.dendrogram.setPos(-QtCore.QPointF(x, y))
        self.axis.set_limits(*self.dendrogram.vis_limits())

    def move_slider(self, ny):
        p = self.dendrogram.mapFromScene(QtCore.QPointF(0, ny))
        p.setY(self.dendrogram.h - p.y())
        p = self.dendrogram.to_internal(p)
        self.gline.set_ipos(p.y())

    def horizontal_caption(self, x):
        return str('ABCDEFGHI')


class HierarchicalView(QtWidgets.QGraphicsView):
    def __init__(self, parent):
        super().__init__(parent)
        self._mode = 'drag'
        self.rubber_band = QtWidgets.QRubberBand(
                QtWidgets.QRubberBand.Rectangle, self)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setMouseTracking(True)

    def showEvent(self, event):   # noqa
        super().showEvent(event)
        self.reset_size()

    def reset_size(self):
        w = float(self.geometry().width())
        h = float(self.geometry().height())
        self.scene().reset_size(w, h)
        # margin
        r = self.scene().axis.graph_rect
        xmar = 0.5 * r.width()/(self.scene().axis.maxx + 1)
        ymar = 0.05 * h
        p1 = QtCore.QPointF(r.left() - xmar, r.top() - ymar)
        p2 = QtCore.QPointF(r.right() + xmar, r.bottom())
        self.scene().zoom_content(QtCore.QRectF(p1, p2))

    def set_drag_mode(self):
        self._mode = 'drag'
        self.setCursor(QtCore.Qt.OpenHandCursor)

    def set_zoom_mode(self):
        self._mode = 'zoom'
        self.setCursor(QtCore.Qt.CrossCursor)

    def set_select_mode(self):
        self._mode = 'sel'
        self.setCursor(QtCore.Qt.PointingHandCursor)

    def mousePressEvent(self, event):   # noqa
        if event.buttons() == QtCore.Qt.LeftButton:
            if self._mode == 'drag':
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                self.__drag_origin = event.pos()
            elif self._mode == 'zoom':
                self.__zoom_origin = event.pos()
                r = QtCore.QRect(event.pos(), QtCore.QSize())
                self.rubber_band.setGeometry(r)
                self.rubber_band.show()
            elif self._mode == 'slider':
                pass
            elif self._mode == 'sel':
                self.scene().dendrogram.try_select(event.pos())

    def mouseMoveEvent(self, event):   # noqa
        if event.buttons() == QtCore.Qt.LeftButton:
            if self._mode == 'drag':
                oldp = self.mapToScene(self.__drag_origin)
                newp = self.mapToScene(event.pos())
                self.scene().move_content(newp - oldp)
                self.__drag_origin = event.pos()
            elif self._mode == 'zoom':
                r = QtCore.QRect(self.__zoom_origin, event.pos())
                self.rubber_band.setGeometry(r.normalized())
            elif self._mode == 'slider':
                ny = self.mapToScene(event.pos()).y()
                self.scene().move_slider(ny)
        else:
            iz = self.scene().gline.influence_zone(event.pos())
            # set slider cursor
            if self._mode != 'slider' and iz:
                self.__bu_mode = self._mode
                self.__bu_cursor = self.cursor()
                self._mode = 'slider'
                self.setCursor(QtCore.Qt.SizeVerCursor)
            elif self._mode == 'slider' and not iz:
                self._mode = self.__bu_mode
                self.setCursor(self.__bu_cursor)

    def mouseReleaseEvent(self, event):   # noqa
        if event.button() == QtCore.Qt.LeftButton:
            if self._mode == 'drag':
                self.setCursor(QtCore.Qt.OpenHandCursor)
            elif self._mode == 'zoom':
                self.rubber_band.hide()
                r = self.rubber_band.geometry()
                if r.width() > 0:
                    p = list(map(self.mapToScene, [r.topLeft(),
                                                   r.bottomRight()]))
                    r = QtCore.QRectF(p[0], p[1])
                    self.scene().zoom_content(r)
            elif self._mode == 'slider':
                self._mode = self.__bu_mode
                self.setCursor(self.__bu_cursor)

    def wheelEvent(self, event):   # noqa
        if event.angleDelta().y() > 0:
            s = 1.1
        else:
            s = 1.0/1.1
        r = self.scene().axis.graph_rect
        pos = event.pos()
        w0 = (1-s)*pos.x() + s*r.left()
        w1 = (1-s)*pos.x() + s*r.right()
        h0 = (1-s)*pos.y() + s*r.top()
        h1 = (1-s)*pos.y() + s*r.bottom()
        r = QtCore.QRectF(w0, h0, w1-w0, h1-h0)
        self.scene().zoom_content(r)


@qtcommon.hold_position
class HClusterView(QtWidgets.QWidget):
    def __init__(self, title, parent, dt, colnames, flow):
        super().__init__()
        self.setLayout(QtWidgets.QVBoxLayout())
        self.setWindowIcon(parent.windowIcon())
        self.setWindowTitle(title)
        self.view = HierarchicalView(self)
        self.scene = HierarchicalScene()
        self.scene.ncluster_changed.connect(self._act_set_igroup)
        self.view.setScene(self.scene)

        self._build_acts()
        self.spin_wdg = hcluster_acts.NClusterWidget(self)
        self.sselect_wdg = hcluster_acts.SpecSelectWidget(self)

        self.toolbar_coms = QtWidgets.QToolBar(self)
        self.toolbar_coms.addAction(self.acts['Refresh database'])
        self.toolbar_coms.addAction(self.acts['Write clusters to database'])
        self.toolbar_coms.addAction(self.acts['Inspect selection'])
        self.toolbar_coms.addAction(self.acts['Settings'])
        self.toolbar_coms.addAction(self.acts['Export picture'])
        self.toolbar_coms.addSeparator()
        self.toolbar_coms.addWidget(self.spin_wdg)
        self.toolbar_coms.addSeparator()
        self.toolbar_coms.addAction(self.acts['Fit view'])
        self.toolbar_coms.addAction(self.acts['Mouse move'])
        self.toolbar_coms.addAction(self.acts['Mouse zoom'])
        self.toolbar_coms.addAction(self.acts['Mouse select'])
        self.toolbar_coms.addWidget(self.sselect_wdg)

        self.refresh()

        self.layout().addWidget(self.toolbar_coms)
        self.layout().addWidget(self.view)

    def _build_acts(self):
        self.acts = {}
        for cls in hcluster_acts.HClusterAct.__subclasses__():
            act = cls(self)
            self.acts[act.name] = act
        self._update_menu_status()
        self.acts['Mouse move'].trigger()

    def refresh(self):
        linkage = np.array(
            [[0.0, 16.0, 0.49499413, 2.0],
             [10.0,  4.0,  0.7321348, 2.0],
             [8.0,  5.0,  0.89753341, 2.0],
             [18.0,  7.0,  0.91434718, 2.0],
             [22.0, 14.0,  1.51446632, 3.0],
             [15.0, 19.0,  1.53696267, 2.0],
             [21.0, 20.0,  1.68851011, 4.0],
             [9.0, 23.0,  2.06894465, 3.0],
             [13.0, 25.0,  2.09670853, 3.0],
             [28.0,  3.0,  2.44195772, 4.0],
             [12.0, 24.0,  3.25370934, 4.0],
             [2.0, 11.0,  3.54263112, 2.0],
             [17.0,  6.0,  3.62834961, 2.0],
             [1.0, 29.0,  3.6547446, 5.0],
             [31.0, 27.0,  5.01845013, 5.0],
             [32.0, 30.0,  9.57784247, 6.0],
             [34.0, 26.0, 11.23855384, 9.0],
             [35.0, 33.0, 15.79190506, 11.0],
             [36.0, 37.0, 35.12455954, 20.0]])
        self.spin_wdg.set_maximum(np.size(linkage, 0) + 1)
        self.scene.set_linkage(linkage)

    def _update_menu_status(self):
        for a in self.acts.values():
            a.setEnabled(a.isactive())

    def _act_set_igroup(self, val):
        self.scene.gline.set_igroup(val)
        self.spin_wdg.set_value(val)
