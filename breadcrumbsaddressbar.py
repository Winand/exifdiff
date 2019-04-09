from pathlib import Path
import os
from qtpy import QtWidgets, QtGui, QtCore
from qtpy.QtCore import Qt

class BreadcrumbsAddressBar(QtWidgets.QFrame):
    "Windows Explorer-like address bar"
    listdir_error = QtCore.Signal(Path)  # failed to list a directory
    path_error = QtCore.Signal(Path)  # entered path does not exist

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QtWidgets.QHBoxLayout(self)

        pal = self.palette()
        pal.setColor(QtGui.QPalette.Background,
                     pal.color(QtGui.QPalette.Base))
        self.setPalette(pal)
        self.setAutoFillBackground(True)
        self.setFrameShape(self.StyledPanel)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)

        self.line_address = QtWidgets.QLineEdit(self)
        self.line_address.setFrame(False)
        self.line_address.hide()
        self.line_address.keyPressEvent_super = self.line_address.keyPressEvent
        self.line_address.keyPressEvent = self.line_address_keyPressEvent
        self.completer = QtWidgets.QCompleter(self)  # FIXME:
        self.completer.setModel(QtCore.QStringListModel())
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.activated.connect(self.__set_path_slot)
        self.line_address.setCompleter(self.completer)
        # print(self.line_address.geometry())
        layout.addWidget(self.line_address)

        self.crumbs_panel = QtWidgets.QWidget(self)
        crumbs_layout = QtWidgets.QHBoxLayout(self.crumbs_panel)
        crumbs_layout.setContentsMargins(0, 0, 0, 0)
        crumbs_layout.setSpacing(0)
        layout.addWidget(self.crumbs_panel)

        self.btn_browse = QtWidgets.QToolButton(self)
        self.btn_browse.setText("...")
        # self.btn_browse.clicked.connect(...)  # FIXME:
        layout.addWidget(self.btn_browse)

        self.setMaximumHeight(self.line_address.height())  # FIXME:

        self.path_ = None
        self.set_path(Path())

    def line_address_keyPressEvent(self, event):
        "Actions to take after a key press in text address field"
        if event.key() == Qt.Key_Escape:
            self.line_address.setText(str(self.path()))  # revert changes
            self.__show_address_field(False)
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.set_path(self.line_address.text())
            self.__show_address_field(False)
        elif event.text() == os.path.sep:  # FIXME: separator cannot be pasted
            print('fill completer data here')
            paths = [str(i) for i in
                     Path(self.line_address.text()).iterdir() if i.is_dir()]
            self.completer.model().setStringList(paths)
        self.line_address.keyPressEvent_super(event)

    def __clear_crumbs(self):
        layout = self.crumbs_panel.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        layout.addStretch()

    def __insert_crumb(self, path):
        btn = QtWidgets.QToolButton(self.crumbs_panel)
        btn.setAutoRaise(True)
        btn.setPopupMode(btn.MenuButtonPopup)
        crumb_text = path.name or str(path).upper().rstrip(os.path.sep)
        btn.setText(crumb_text)  # C:\ has no name
        btn.path = path
        btn.clicked.connect(self.crumb_clicked)
        menu = QtWidgets.QMenu(btn)
        menu.aboutToShow.connect(self.crumb_menu_show)
        menu.aboutToHide.connect(self.crumb_menu_hide)
        # scrollable menu https://stackoverflow.com/a/14719633/1119602
        menu.setStyleSheet("QMenu { menu-scrollable: 1; }")
        btn.setMenu(menu)
        self.crumbs_panel.layout().insertWidget(0, btn)

    def crumb_clicked(self):
        "SLOT: breadcrumb was clicked"
        self.set_path(self.sender().path)

    def crumb_menu_show(self):
        "SLOT: fill subdirectory list on menu open"
        menu = self.sender()
        context_root = menu.parent().path
        try:
            for i in context_root.iterdir():
                if not i.is_dir():
                    continue
                action = menu.addAction(i.name)
                action.path = i
                action.triggered.connect(self.__set_path_slot)
        except PermissionError:
            self.listdir_error.emit(context_root)

    def crumb_menu_hide(self):
        "SLOT: Clear sub-dir menu on hide but let action trigger first"
        QtCore.QTimer.singleShot(0, self.sender().clear)

    def __set_path_slot(self, p=None):
        "SLOT: Set path from breadcrumb menu or completer"
        self.__show_address_field(False)  # FIXME: put here for completer tests
        self.set_path(p or self.sender().path)

    def set_path(self, path):
        """
        Set path displayed in this BreadcrumbsAddressBar
        Returns `False` if path does not exist.
        """
        path, emit_err = Path(path), None
        try:  # C: -> C:\, folder\..\folder -> folder
            path = path.resolve()
        except PermissionError:
            emit_err = self.listdir_error
        if not path.exists():
            emit_err = self.path_error
        if emit_err:  # permission error or path does not exist
            self.line_address.setText(str(self.path()))  # revert path
            emit_err.emit(path)
            return False
        self.__clear_crumbs()
        self.path_ = path
        self.line_address.setText(str(path))
        self.__insert_crumb(path)
        while path.parent != path:
            path = path.parent
            self.__insert_crumb(path)
        # self.crumbs_panel.layout().addStretch()
        return True

    def path(self):
        "Get path displayed in this BreadcrumbsAddressBar"
        return self.path_

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton:  # left click only
            return
        self.__show_address_field(True)

    def __show_address_field(self, b_show):
        "Show text address field"
        if b_show:
            self.crumbs_panel.hide()
            self.line_address.show()
            self.line_address.setFocus()
            self.line_address.selectAll()
        else:
            self.line_address.hide()
            self.crumbs_panel.show()

if __name__ == '__main__':
    from qtapp import QtForm

    class Form(QtWidgets.QWidget):
        _layout_ = QtWidgets.QHBoxLayout
        _loop_ = True

        def perm_err(self, path):
            print('perm err', path)

        def path_err(self, path):
            print('path err', path)

        def __init__(self):
            self.address = BreadcrumbsAddressBar()
            self.layout().addWidget(self.address)
            self.address.listdir_error.connect(self.perm_err)
            self.address.path_error.connect(self.path_err)
            # self.address.set_path(r"C:\Windows\System32\drivers\etc")

    QtForm(Form)