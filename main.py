import exiftool
from qtapp import QtForm, QtWidgets, QtCore, Qt, QtGui, signal, options

# TODO:
# Скрытие тегов + отобразить скрытые
# --фильтрация, сохранение фильтров?
# Синхронизация выделения тегов
# Копирование выбранных тегов между файлами

class DictModel(QtCore.QAbstractTableModel):
    "Model to display Python dict in a Qt widget"
    def __init__(self, d=None):
        super().__init__()
        self.keys = tuple(d.keys())
        self.source = d
        self.other = {}

    def rowCount(self, parent):  # pylint: disable=invalid-name
        "Dict length"
        return len(self.keys)

    @staticmethod
    def columnCount(parent):  # pylint: disable=invalid-name
        "key, value - 2 columns"
        return 2

    def data(self, index, role):
        "Return data to display"
        row, col = index.row(), index.column()
        k = self.keys[row]
        if role in (Qt.DisplayRole, Qt.ToolTipRole):
            return str(self.source[k] if col else k)
        elif role == Qt.BackgroundRole:
            v_this = self.source[k]
            v_other = self.other.get(k)
            color = None
            if v_other is None:
                color = "#ffd0d0"
            elif v_this != v_other and col == 1:
                color = "#efe4b0"  # pale yellow
            return QtGui.QBrush(QtGui.QColor(color)) if color else None

    @staticmethod
    def headerData(section, orientation, role):  # pylint: disable=invalid-name
        "Header captions"
        if role != Qt.DisplayRole or orientation != Qt.Horizontal:
            return
        captions = "Key", "Value"
        return captions[section]

    def compare(self, other):
        self.other = other


class FormMain(QtWidgets.QWidget):
    "Container widget"
    _loop_ = True
    _layout_ = QtWidgets.QHBoxLayout

    def __init__(self):  # pylint: disable=super-init-not-called
        first, second = QtForm(Form1), QtForm(Form1)
        self.control = QtForm(PnlControl, panel1=first, panel2=second)
        self.layout().addWidget(first)
        self.layout().addWidget(self.control)
        self.layout().addWidget(second)

    def app_aboutToQuit(self):
        self.control.stop()

class Form1(QtWidgets.QWidget):
    model_changed = QtCore.Signal()

    def __init__(self, secondary=None):  # pylint: disable=super-init-not-called
        self.control = None
        p1 = r"C:\Users\Андрей\Pictures\_trash"
        model = QtWidgets.QFileSystemModel()
        model.setFilter(QtCore.QDir.Files)
        self.treeFiles.setModel(model)
        self.treeFiles.setRootIndex(model.setRootPath(p1))
        self.treeFiles.selectionModel().currentChanged.connect(self.selected)

        self.secondary = secondary
        if secondary:
            secondary.pnlControl.setVisible(False)

    def selected(self, current, previous):
        fpath = current.model().filePath(current)
        meta = self.control.exiftool.get_metadata(fpath.encode())
        self.treeTags.setModel(DictModel(meta))
        self.treeTags.resizeColumnToContents(0)
        self.model_changed.emit()

    def btnChooseFolder_clicked(self):
        p = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose folder", self.treeFiles.model().rootPath())
        if p:
            self.treeFiles.setRootIndex(self.treeFiles.model().setRootPath(p))

    def set_controller(self, widget):
        self.control = widget

    def get_current_meta(self):
        model = self.treeTags.model()
        return model.source if model else {}

    def update_comparison(self, other):
        model = self.treeTags.model()
        if model:
            model.compare(other)

class PnlControl():
    def __init__(self, panel1, panel2):
        self.panel1 = panel1
        self.panel2 = panel2
        panel1.set_controller(self)
        panel2.set_controller(self)
        panel1.model_changed.connect(self.model_changed)
        panel2.model_changed.connect(self.model_changed)

        self.exiftool = exiftool.ExifTool()
        self.exiftool.start()
    
    def stop(self):
        self.exiftool.terminate()
    
    def model_changed(self):
        self.panel1.update_comparison(self.panel2.get_current_meta())
        self.panel2.update_comparison(self.panel1.get_current_meta())


options['debug'] = True
QtForm(FormMain)
