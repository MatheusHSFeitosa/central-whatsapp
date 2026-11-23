"""Application-owned resize edges and safe dragging, including native CEF children."""
import ctypes
from PySide6.QtCore import QObject, Qt, QEvent, QRect, QPoint, Signal, QSocketNotifier
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QAbstractItemView


def resize_edges(point,width,height,margin=7):
    edges=Qt.Edge(0)
    if point.x()<margin:edges|=Qt.Edge.LeftEdge
    elif point.x()>=width-margin:edges|=Qt.Edge.RightEdge
    if point.y()<margin:edges|=Qt.Edge.TopEdge
    elif point.y()>=height-margin:edges|=Qt.Edge.BottomEdge
    return edges


class EdgeHandle(QWidget):
    def __init__(self,window,edges,cursor):
        super().__init__(window)
        self.owner,self.edges=window,edges
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setCursor(cursor);self.setMouseTracking(True)
        self.setAccessibleName('Redimensionar janela')
        self.manual=False
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        self.origin=event.globalPosition().toPoint();self.initial=self.owner.geometry()
        handle=self.owner.windowHandle()
        self.manual=not (handle and handle.startSystemResize(self.edges))
        event.accept()
    def mouseMoveEvent(self,event):
        if self.manual and event.buttons()&Qt.MouseButton.LeftButton:
            delta=event.globalPosition().toPoint()-self.origin;rect=QRect(self.initial)
            if self.edges&Qt.Edge.LeftEdge:rect.setLeft(min(rect.right()-self.owner.minimumWidth()+1,rect.left()+delta.x()))
            if self.edges&Qt.Edge.RightEdge:rect.setRight(max(rect.left()+self.owner.minimumWidth()-1,rect.right()+delta.x()))
            if self.edges&Qt.Edge.TopEdge:rect.setTop(min(rect.bottom()-self.owner.minimumHeight()+1,rect.top()+delta.y()))
            if self.edges&Qt.Edge.BottomEdge:rect.setBottom(max(rect.top()+self.owner.minimumHeight()-1,rect.bottom()+delta.y()))
            self.owner.setGeometry(rect);event.accept()
    def mouseReleaseEvent(self,event):self.manual=False;event.accept()


class NativeAltDrag(QObject):
    """An Alt+left-button grab scoped to this app's X11 ancestor window only."""
    moveRequested=Signal(int,int)
    def __init__(self,window):
        super().__init__(window)
        self.display=None;self.notifier=None
        if QApplication.platformName()!='xcb':return
        self.window=window
        self.x=ctypes.CDLL('libX11.so.6')
        x=self.x
        x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
        self.display=x.XOpenDisplay(None)
        if not self.display:return
        x.XConnectionNumber.argtypes=[ctypes.c_void_p];x.XConnectionNumber.restype=ctypes.c_int
        x.XGrabButton.argtypes=[ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_ulong,ctypes.c_int,ctypes.c_uint,ctypes.c_int,ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong]
        x.XPending.argtypes=[ctypes.c_void_p];x.XPending.restype=ctypes.c_int
        x.XNextEvent.argtypes=[ctypes.c_void_p,ctypes.c_void_p]
        x.XFlush.argtypes=[ctypes.c_void_p];x.XCloseDisplay.argtypes=[ctypes.c_void_p]
        x.XUngrabPointer.argtypes=[ctypes.c_void_p,ctypes.c_ulong]
        x.XDefaultRootWindow.argtypes=[ctypes.c_void_p];x.XDefaultRootWindow.restype=ctypes.c_ulong
        x.XInternAtom.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int];x.XInternAtom.restype=ctypes.c_ulong
        x.XSendEvent.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_long,ctypes.c_void_p]
        self.wid=int(window.winId())
        for modifier in (8,8|2,8|16,8|2|16):
            x.XGrabButton(self.display,1,modifier,self.wid,0,(1<<2)|(1<<3)|(1<<6),1,1,0,0)
        x.XFlush(self.display)
        self.notifier=QSocketNotifier(x.XConnectionNumber(self.display),QSocketNotifier.Type.Read,self)
        self.notifier.activated.connect(self.receive)
    def receive(self,*_):
        class Button(ctypes.Structure):
            _fields_=[('type',ctypes.c_int),('serial',ctypes.c_ulong),('send_event',ctypes.c_int),('display',ctypes.c_void_p),('window',ctypes.c_ulong),('root',ctypes.c_ulong),('subwindow',ctypes.c_ulong),('time',ctypes.c_ulong),('x',ctypes.c_int),('y',ctypes.c_int),('x_root',ctypes.c_int),('y_root',ctypes.c_int),('state',ctypes.c_uint),('button',ctypes.c_uint),('same_screen',ctypes.c_int)]
        class Data(ctypes.Union):_fields_=[('longs',ctypes.c_long*5),('bytes',ctypes.c_char*20)]
        class Client(ctypes.Structure):
            _fields_=[('type',ctypes.c_int),('serial',ctypes.c_ulong),('send_event',ctypes.c_int),('display',ctypes.c_void_p),('window',ctypes.c_ulong),('message_type',ctypes.c_ulong),('format',ctypes.c_int),('data',Data)]
        class Event(ctypes.Union):_fields_=[('button',Button),('client',Client),('padding',ctypes.c_long*24)]
        while self.display and self.x.XPending(self.display):
            event=Event();self.x.XNextEvent(self.display,ctypes.byref(event))
            if event.button.type!=4 or event.button.button!=1:continue
            self.x.XUngrabPointer(self.display,0)
            if self.window.isFullScreen():continue
            request=Event();request.client.type=33;request.client.send_event=1;request.client.display=self.display
            request.client.window=self.wid;request.client.message_type=self.x.XInternAtom(self.display,b'_NET_WM_MOVERESIZE',0);request.client.format=32
            values=(event.button.x_root,event.button.y_root,8,1,1)
            for index,value in enumerate(values):request.client.data.longs[index]=value
            self.moveRequested.emit(event.button.x_root,event.button.y_root)
            root=self.x.XDefaultRootWindow(self.display)
            self.x.XSendEvent(self.display,root,0,(1<<19)|(1<<20),ctypes.byref(request));self.x.XFlush(self.display)
    def close(self):
        if self.notifier:self.notifier.setEnabled(False)
        if self.display:self.x.XCloseDisplay(self.display);self.display=None


class WindowChrome(QObject):
    def __init__(self,window):
        super().__init__(window)
        self.window=window;self.handles=[]
        edges=[(Qt.Edge.LeftEdge,Qt.CursorShape.SizeHorCursor),(Qt.Edge.RightEdge,Qt.CursorShape.SizeHorCursor),
               (Qt.Edge.TopEdge,Qt.CursorShape.SizeVerCursor),(Qt.Edge.BottomEdge,Qt.CursorShape.SizeVerCursor),
               (Qt.Edge.LeftEdge|Qt.Edge.TopEdge,Qt.CursorShape.SizeFDiagCursor),(Qt.Edge.RightEdge|Qt.Edge.BottomEdge,Qt.CursorShape.SizeFDiagCursor),
               (Qt.Edge.RightEdge|Qt.Edge.TopEdge,Qt.CursorShape.SizeBDiagCursor),(Qt.Edge.LeftEdge|Qt.Edge.BottomEdge,Qt.CursorShape.SizeBDiagCursor)]
        for edge,cursor in edges:self.handles.append(EdgeHandle(window,edge,cursor))
        QApplication.instance().installEventFilter(self)
        self.alt=NativeAltDrag(window)
        self.refresh()
    def refresh(self):
        w,h=self.window.width(),self.window.height();m=7
        rects=[QRect(0,m,m,max(0,h-2*m)),QRect(w-m,m,m,max(0,h-2*m)),QRect(m,0,max(0,w-2*m),m),QRect(m,h-m,max(0,w-2*m),m),QRect(0,0,m,m),QRect(w-m,h-m,m,m),QRect(w-m,0,m,m),QRect(0,h-m,m,m)]
        enabled=not self.window.isMaximized() and not self.window.isFullScreen()
        for handle,rect in zip(self.handles,rects):handle.setGeometry(rect);handle.setVisible(enabled);handle.raise_()
    def eventFilter(self,watched,event):
        if watched is self.window and event.type() in (QEvent.Type.Resize,QEvent.Type.Show,QEvent.Type.WindowStateChange):self.refresh()
        if event.type()!=QEvent.Type.MouseButtonPress or event.button()!=Qt.MouseButton.LeftButton:return False
        if not isinstance(watched,QWidget) or watched.window() is not self.window or isinstance(watched,EdgeHandle):return False
        if self.window.isFullScreen():return False
        alt=bool(event.modifiers()&Qt.KeyboardModifier.AltModifier)
        blank=(type(watched) is QWidget and watched.objectName() not in ('splitDivider',)) or (isinstance(watched,QLabel) and watched.textInteractionFlags()==Qt.TextInteractionFlag.NoTextInteraction)
        if isinstance(watched.parent(),QAbstractItemView):
            parent=watched.parent();blank=not parent.indexAt(event.position().toPoint()).isValid()
        if not alt and not blank:return False
        handle=self.window.windowHandle()
        return bool(handle and handle.startSystemMove())
    def close(self):
        QApplication.instance().removeEventFilter(self);self.alt.close()
