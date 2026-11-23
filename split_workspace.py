"""A single native parent for every browser; split layouts never reparent CEF."""
from PySide6.QtCore import Qt, Signal, QRect, QPoint, QSize
from PySide6.QtWidgets import (QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QComboBox, QListWidget, QListWidgetItem, QDialogButtonBox, QToolButton, QStackedWidget)
from ui_widgets import Dialog, MessageBox, icon


class SplitDialog(Dialog):
    def __init__(self, parent, accounts, group_for, selected=()):
        super().__init__(parent)
        self.setWindowTitle('Dividir tela')
        self.resize(520, 510)
        layout=QVBoxLayout(self)
        intro=QLabel('Escolha de 2 a 4 perfis. Você pode combinar grupos diferentes.')
        intro.setWordWrap(True);layout.addWidget(intro)
        row=QHBoxLayout();row.addWidget(QLabel('Adicionar grupo:'))
        self.groups=QComboBox();self.groups.addItem('Selecionar grupo…','')
        catalog={}
        for account in accounts:
            name=group_for(account) or 'Sem grupo'
            catalog.setdefault(name,[]).append(account['id'])
        for name in sorted(catalog,key=str.casefold):self.groups.addItem(name,name)
        row.addWidget(self.groups,1)
        add=QToolButton();add.setIcon(icon('list-add'));add.setToolTip('Marcar os perfis deste grupo')
        row.addWidget(add);layout.addLayout(row)
        self.profiles=QListWidget();self.profiles.setObjectName('splitProfilePicker');self.profiles.setSpacing(4);self.profiles.setAccessibleName('Perfis para dividir a tela')
        for account in accounts:
            item=QListWidgetItem(account['name']+' · '+(group_for(account) or 'Sem grupo'))
            item.setData(Qt.ItemDataRole.UserRole,account['id']);item.setSizeHint(QSize(0,30))
            item.setCheckState(Qt.CheckState.Checked if account['id'] in selected else Qt.CheckState.Unchecked)
            self.profiles.addItem(item)
        layout.addWidget(self.profiles,1)
        def add_group():
            identifiers=catalog.get(self.groups.currentData(),[])
            for index in range(self.profiles.count()):
                item=self.profiles.item(index)
                if item.data(Qt.ItemDataRole.UserRole) in identifiers:item.setCheckState(Qt.CheckState.Checked)
        add.clicked.connect(add_group)
        self.arrangement=QComboBox()
        for label,value in [('Lado a lado','columns'),('Um acima do outro','rows'),('Grade 2 × 2','grid')]:self.arrangement.addItem(label,value)
        form=QHBoxLayout();form.addWidget(QLabel('Organização:'));form.addWidget(self.arrangement,1);layout.addLayout(form)
        self.counter=QLabel();layout.addWidget(self.counter)
        self.profiles.itemChanged.connect(self.update_count)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('Dividir tela')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Cancelar')
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject)
        layout.addWidget(buttons);self.update_count()
    def selected_ids(self):
        return [self.profiles.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.profiles.count()) if self.profiles.item(i).checkState()==Qt.CheckState.Checked]
    def update_count(self,*_):self.counter.setText(f'{len(self.selected_ids())} perfis selecionados · limite de 4')
    def accept(self):
        if not 2<=len(self.selected_ids())<=4:
            MessageBox.information(self,'Escolha os perfis','Selecione de 2 a 4 perfis para dividir a tela.');return
        super().accept()


class Divider(QWidget):
    def __init__(self,area,axis):
        super().__init__(area)
        self.area,self.axis=area,axis
        self.setObjectName('splitDivider')
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self.setCursor(Qt.CursorShape.SizeHorCursor if axis=='x' else Qt.CursorShape.SizeVerCursor)
        self.setToolTip('Arraste para ajustar os painéis')
        self.dragging=False
    def mousePressEvent(self,event):
        if event.button()==Qt.MouseButton.LeftButton:self.dragging=True;event.accept()
    def mouseMoveEvent(self,event):
        if self.dragging:
            point=self.area.mapFromGlobal(event.globalPosition().toPoint())
            total=self.area.width() if self.axis=='x' else self.area.height()
            value=(point.x() if self.axis=='x' else point.y())/max(1,total)
            setattr(self.area,'ratio_'+self.axis,max(.2,min(.8,value)))
            self.area.arrange();event.accept()
    def mouseReleaseEvent(self,event):self.dragging=False;event.accept()


class ProfileArea(QWidget):
    splitChanged=Signal(bool)
    activeChanged=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
        self._widgets=[];self._current=None;self._visible=[]
        self.mode='columns';self.ratio_x=.5;self.ratio_y=.5
        self.headers={};self.labels={};self.names={};self._fullscreen=None
        self.dividers=[Divider(self,'x'),Divider(self,'y')]
        for divider in self.dividers:divider.hide()
    def addWidget(self,widget):
        if widget in self._widgets:return self._widgets.index(widget)
        widget.setParent(self);widget.hide();self._widgets.append(widget)
        if self._current is None:self.setCurrentWidget(widget)
        return len(self._widgets)-1
    def count(self):return len(self._widgets)
    def widget(self,index):return self._widgets[index] if 0<=index<len(self._widgets) else None
    def indexOf(self,widget):return self._widgets.index(widget) if widget in self._widgets else -1
    def currentWidget(self):return self._current
    def currentIndex(self):return self.indexOf(self._current)
    def is_split(self):return len(self._visible)>1
    def isDisplayed(self,widget):return widget in self._visible
    def visible_widgets(self):return list(self._visible)
    def setCurrentIndex(self,index):
        widget=self.widget(index)
        if widget is not None:self.setCurrentWidget(widget)
    def setCurrentWidget(self,widget):
        if widget not in self._widgets:raise ValueError('Perfil fora da área de conteúdo')
        before=self.is_split()
        if widget not in self._visible:self._visible=[widget]
        self._current=widget;self.arrange()
        if before!=self.is_split():self.splitChanged.emit(self.is_split())
    def refresh_icons(self):
        for header in self.headers.values():
            for button in header.findChildren(QToolButton):button.setIcon(icon('window-maximize'))
    def set_names(self,names):
        self.names=names
        for widget,label in self.labels.items():label.setText(names.get(widget,'Perfil'))
    def set_split(self,widgets,mode='columns'):
        if mode not in ('columns','rows','grid'):raise ValueError('Organização inválida')
        if not 2<=len(widgets)<=4 or len(set(widgets))!=len(widgets) or any(widget not in self._widgets for widget in widgets):raise ValueError('Selecione de 2 a 4 perfis diferentes')
        self.mode=mode;self._visible=list(widgets)
        if self._current not in widgets:self._current=widgets[0]
        self.arrange();self.splitChanged.emit(True)
    def leave_split(self,widget=None):
        widget=widget or self._current
        if widget is None:return
        self._visible=[widget];self._current=widget;self.arrange()
        self.splitChanged.emit(False);self.activeChanged.emit(widget)
    def removeWidget(self,widget):
        if widget not in self._widgets:return
        self._widgets.remove(widget)
        if widget in self._visible:self._visible.remove(widget)
        header=self.headers.pop(widget,None);self.labels.pop(widget,None)
        if header:header.deleteLater()
        if self._current is widget:self._current=self._visible[0] if self._visible else (self._widgets[0] if self._widgets else None)
        if not self._visible and self._current:self._visible=[self._current]
        widget.hide();self.arrange();self.splitChanged.emit(self.is_split())
    def begin_fullscreen(self,widget):
        if self.is_split():self._fullscreen=(list(self._visible),self.mode)
        self._visible=[widget];self._current=widget;self.arrange()
    def end_fullscreen(self):
        if self._fullscreen:
            widgets,mode=self._fullscreen;self._fullscreen=None
            widgets=[widget for widget in widgets if widget in self._widgets]
            if len(widgets)>1:self.set_split(widgets,mode)
    def header_for(self,widget):
        if widget not in self.headers:
            header=QWidget(self);header.setObjectName('splitHeader')
            header.setAttribute(Qt.WidgetAttribute.WA_NativeWindow)
            row=QHBoxLayout(header);row.setContentsMargins(10,0,4,0);row.setSpacing(6)
            label=QLabel(self.names.get(widget,'Perfil'));label.setTextFormat(Qt.TextFormat.PlainText)
            row.addWidget(label,1)
            button=QToolButton();button.setIcon(icon('window-maximize'));button.setFixedSize(26,26)
            button.setToolTip('Mostrar somente este perfil');button.setAccessibleName('Mostrar somente este perfil')
            button.clicked.connect(lambda checked=False,w=widget:self.leave_split(w))
            row.addWidget(button)
            self.headers[widget]=header;self.labels[widget]=label
        return self.headers[widget]
    def arrange(self):
        if not hasattr(self,'dividers'):return
        for widget in self._widgets:
            if widget not in self._visible:widget.hide()
        for header in self.headers.values():header.hide()
        for divider in self.dividers:divider.hide()
        if not self._visible:return
        if not self.is_split():
            widget=self._visible[0];widget.setGeometry(self.rect());widget.show();widget.raise_();return
        width,height=self.width(),self.height();gap=6;n=len(self._visible);rects=[]
        if self.mode=='grid' and n>2:
            xx=int(width*self.ratio_x);yy=int(height*self.ratio_y)
            rects=[QRect(0,0,xx-gap//2,yy-gap//2),QRect(xx+gap//2,0,width-xx-gap//2,yy-gap//2),QRect(0,yy+gap//2,xx-gap//2,height-yy-gap//2),QRect(xx+gap//2,yy+gap//2,width-xx-gap//2,height-yy-gap//2)][:n]
            self.dividers[0].setGeometry(xx-gap//2,0,gap,height);self.dividers[1].setGeometry(0,yy-gap//2,width,gap)
            for divider in self.dividers:divider.show();divider.raise_()
        elif self.mode=='rows':
            if n==2:
                yy=int(height*self.ratio_y);rects=[QRect(0,0,width,yy-gap//2),QRect(0,yy+gap//2,width,height-yy-gap//2)]
                self.dividers[1].setGeometry(0,yy-gap//2,width,gap);self.dividers[1].show()
            else:rects=[QRect(0,i*height//n+gap//2,width,(i+1)*height//n-i*height//n-gap) for i in range(n)]
        else:
            if n==2:
                xx=int(width*self.ratio_x);rects=[QRect(0,0,xx-gap//2,height),QRect(xx+gap//2,0,width-xx-gap//2,height)]
                self.dividers[0].setGeometry(xx-gap//2,0,gap,height);self.dividers[0].show()
            else:rects=[QRect(i*width//n+gap//2,0,(i+1)*width//n-i*width//n-gap,height) for i in range(n)]
        for widget,rect in zip(self._visible,rects):
            header=self.header_for(widget);header.setGeometry(rect.x(),rect.y(),max(1,rect.width()),30)
            widget.setGeometry(rect.adjusted(0,30,0,0));widget.show();header.show();header.raise_()
        for divider in self.dividers:
            if divider.isVisible():divider.raise_()
    def resizeEvent(self,event):super().resizeEvent(event);self.arrange()


class LegacyTestArea(QStackedWidget):
    """Preserve the old Qt WebEngine test harness; production splits use CEF."""
    splitChanged=Signal(bool)
    activeChanged=Signal(object)
    def isDisplayed(self,widget):return self.currentWidget() is widget
    def refresh_icons(self):pass
    def begin_fullscreen(self,widget):pass
    def end_fullscreen(self):pass
    def is_split(self):return False
    def leave_split(self):pass
    def visible_widgets(self):return [self.currentWidget()] if self.currentWidget() else []
