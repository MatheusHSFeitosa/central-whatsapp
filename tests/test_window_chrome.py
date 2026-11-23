import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import unittest
from unittest.mock import patch
from PySide6.QtCore import QPoint,QPointF,Qt,QEvent
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication,QMainWindow,QWidget,QToolButton,QLineEdit
from window_chrome import resize_edges,WindowChrome
from split_workspace import ProfileArea,SplitDialog
app=QApplication.instance() or QApplication([])

class ChromeTests(unittest.TestCase):
    def test_all_eight_resize_regions(self):
        cases=[(0,0,Qt.Edge.LeftEdge|Qt.Edge.TopEdge),(199,0,Qt.Edge.RightEdge|Qt.Edge.TopEdge),(0,99,Qt.Edge.LeftEdge|Qt.Edge.BottomEdge),(199,99,Qt.Edge.RightEdge|Qt.Edge.BottomEdge),(0,50,Qt.Edge.LeftEdge),(199,50,Qt.Edge.RightEdge),(100,0,Qt.Edge.TopEdge),(100,99,Qt.Edge.BottomEdge)]
        for x,y,expected in cases:self.assertEqual(resize_edges(QPoint(x,y),200,100),expected)
        self.assertEqual(resize_edges(QPoint(50,50),200,100),Qt.Edge(0))
    def test_resize_handles_cover_edges_and_hide_maximized(self):
        window=QMainWindow();window.resize(900,650);chrome=WindowChrome(window);window.show();app.processEvents()
        self.assertEqual(len(chrome.handles),8)
        for handle in chrome.handles:self.assertTrue(handle.isVisible())
        window.showMaximized();app.processEvents()
        self.assertTrue(all(not handle.isVisible() for handle in chrome.handles))
        chrome.close();window.close()
    def test_every_handle_requests_its_system_resize_direction(self):
        window=QMainWindow();window.show();chrome=WindowChrome(window)
        event=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(2,2),QPointF(20,20),Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        with patch.object(window.windowHandle(),'startSystemResize',return_value=True) as resize:
            for handle in chrome.handles:
                handle.mousePressEvent(event);resize.assert_called_with(handle.edges)
        chrome.close();window.close()

    def test_normal_controls_keep_their_clicks(self):
        window=QMainWindow();window.show();chrome=WindowChrome(window)
        button=QToolButton(window);field=QLineEdit(window)
        event=QMouseEvent(QEvent.Type.MouseButtonPress,QPointF(10,10),QPointF(10,10),Qt.MouseButton.LeftButton,Qt.MouseButton.LeftButton,Qt.KeyboardModifier.NoModifier)
        with patch.object(window.windowHandle(),'startSystemMove',return_value=True) as move:
            self.assertFalse(chrome.eventFilter(button,event));self.assertFalse(chrome.eventFilter(field,event));move.assert_not_called()
        chrome.close();window.close()

class SplitAreaTests(unittest.TestCase):
    def test_split_keeps_native_parents_and_active_selection(self):
        area=ProfileArea();views=[QWidget() for _ in range(4)]
        for view in views:area.addWidget(view)
        area.resize(1000,700);area.show();app.processEvents()
        parents=[view.parent() for view in views]
        area.set_split(views,'grid');app.processEvents()
        self.assertEqual([view.parent() for view in views],parents)
        self.assertTrue(all(area.isDisplayed(view) for view in views))
        area.setCurrentWidget(views[2]);self.assertTrue(area.is_split());self.assertIs(area.currentWidget(),views[2])
        area.leave_split(views[1]);self.assertEqual(area.visible_widgets(),[views[1]])
        area.close()
    def test_invalid_split_is_rejected(self):
        area=ProfileArea();one,two=QWidget(),QWidget();area.addWidget(one);area.addWidget(two)
        for values in ([one],[one,one],[one,QWidget()]):
            with self.assertRaises(ValueError):area.set_split(values)
    def test_fullscreen_restores_split(self):
        area=ProfileArea();one,two=QWidget(),QWidget();area.addWidget(one);area.addWidget(two)
        area.set_split([one,two],'rows');area.begin_fullscreen(two)
        self.assertFalse(area.is_split());area.end_fullscreen();self.assertTrue(area.is_split());self.assertEqual(area.mode,'rows')
    def test_group_picker_can_combine_distinct_groups(self):
        records=[{'id':'a','name':'Um','group':'Pessoal'},{'id':'b','name':'Dois','group':'Trabalho'}]
        dialog=SplitDialog(None,records,lambda a:a['group'],['a','b'])
        self.assertEqual(dialog.selected_ids(),['a','b']);dialog.close()
