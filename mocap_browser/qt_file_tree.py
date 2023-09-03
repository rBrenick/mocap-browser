import os
import sys
import traceback

# Icons
from . import resources
from .ui_utils import create_qicon

from .ui_utils import QtCore, QtGui, QtWidgets

# quicker access to properties
_qt = QtCore.Qt


class FolderConfig(object):
    def __init__(self, root_folder):
        self.dir_path = root_folder
        self.top_folder_name = os.path.basename(root_folder)
        self.file_extensions = [] # if left blank, will show all

        # icons
        self.file_icon = create_qicon(resources.get_image_path("unknown_icon"))
        self.folder_icon = create_qicon(resources.get_image_path("folder_icon"))
        self.root_folder_icon = create_qicon(resources.get_image_path("root_folder_icon"))

    def get_file_icon(self, for_file_path):
        return self.file_icon

    def get_folder_icon(self, for_folder_path):
        return self.folder_icon

    def file_double_clicked(self, file_path):
        # print(file_path)
        pass
    
    def add_files_to_model(self, on_file_found):
        if not os.path.exists(self.dir_path):
            print(f"path not found: {self.dir_path}")
            return
        
        for dir_path, _, file_names in os.walk(self.dir_path):
            for file_name in file_names:
                if self.file_extensions:
                    if os.path.splitext(file_name)[-1] not in self.file_extensions:
                        continue
                file_path = os.path.join(dir_path, file_name)
                on_file_found.emit(file_path, self)


class PerforceFolderConfig(FolderConfig):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.file_icon = create_qicon(resources.get_image_path("p4_icon"))
        self.folder_icon = create_qicon(resources.get_image_path("p4_folder_icon"))

    def add_files_to_model(self, on_file_found):
        import p4cmd
        client = p4cmd.P4Client(self.dir_path)
        for p4file in client.folder_to_p4files(self.dir_path): # type: p4cmd.P4File
            local_path = p4file.get_local_file_path()

            if self.file_extensions:
                if os.path.splitext(local_path)[-1] not in self.file_extensions:
                    continue
            
            on_file_found.emit(local_path, self)


# QThread setup yoinked from https://www.pythonguis.com/tutorials/multithreading-pyside-applications-qthreadpool/

class FileConfigWorkerSignals(QtCore.QObject):
    finished = QtCore.Signal()
    error = QtCore.Signal(tuple)
    file_found = QtCore.Signal(str, FolderConfig)


class FileConfigWorker(QtCore.QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super(FileConfigWorker, self).__init__()

        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = FileConfigWorkerSignals()

        # Add the callback to our kwargs
        self.kwargs['on_file_found'] = self.signals.file_found

    @QtCore.Slot()
    def run(self):
        try:
            self.fn(*self.args, **self.kwargs)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()


class QtFileTree(QtWidgets.QTreeView):

    file_double_clicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        
        # configurable settings
        self.default_folder_config_cls = FolderConfig

        self.default_expand_depth = None
        self.header_labels = ["Name"]

        self.model = QtGui.QStandardItemModel()
        self.proxy = FileTreeSortProxyModel(self.model)
        self.setModel(self.proxy)
        self.setSortingEnabled(True)
        self._model_folders = {}
        self.model.setHorizontalHeaderLabels(self.header_labels)

        self.setSelectionMode(QtWidgets.QListView.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setDragEnabled(True)
        self.setDefaultDropAction(QtCore.Qt.IgnoreAction)
        self.setDragDropOverwriteMode(False)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.doubleClicked.connect(self._trigger_double_clicked)

        # populate ui with threads
        self.threadpool = QtCore.QThreadPool()
    
    def set_folder(self, folder_path, file_exts=None, show_root_folder=False):
        """If you only need one root folder, call this function"""
        self._reset_tree()

        folder_config = self.default_folder_config_cls(folder_path) # type: FolderConfig
        if not show_root_folder:
            folder_config.top_folder_name = ""
        
        if file_exts is not None:
            folder_config.file_extensions = file_exts
        
        self.add_folder_config(folder_config)

        if self.default_expand_depth is not None:
            self.expandToDepth(self.default_expand_depth)
    
    def add_folder_config(self, folder_config):
        if 0:
            folder_config = FolderConfig()

        worker = FileConfigWorker(folder_config.add_files_to_model)
        worker.signals.file_found.connect(self._add_path_to_model)
        self.threadpool.start(worker)
    
    def get_selected_file_paths(self):
        file_paths = []
        for index in self.selectedIndexes():
            model_index = self.proxy.mapToSource(index)
            tree_item = self.proxy.sourceModel().itemFromIndex(model_index)  # type: FileTreeModelItem
            if isinstance(tree_item, FileTreeModelItem):
                file_paths.append(tree_item.file_path)
        return file_paths

    def _reset_tree(self):
        self.model.clear()
        self.model.setHorizontalHeaderLabels(self.header_labels)
        self._model_folders = {}

    def _add_path_to_model(self, file_path, folder_config):
        if 0:
            folder_config = FolderConfig()

        root_dir_path = folder_config.dir_path
        top_folder_name = folder_config.top_folder_name

        # display path in tree view
        file_rel_path = os.path.relpath(file_path, root_dir_path)
        dir_rel_path = os.path.relpath(os.path.dirname(file_path), root_dir_path)
        display_dir_rel_path = dir_rel_path
        if top_folder_name:
            display_dir_rel_path = "{}\\{}".format(top_folder_name, display_dir_rel_path)

        parent_item = self.model

        # build needed folders
        folder_rel_split = display_dir_rel_path.split("\\")
        for i, token in enumerate(folder_rel_split):
            if token in [".", ""]:
                continue

            # combine together the token into a relative_path
            token_rel_display_path = "\\".join(folder_rel_split[:i + 1])
            token_rel_real_path = "\\".join(folder_rel_split[1:i + 1]) if top_folder_name else token_rel_display_path
            token_rel_real_path = token_rel_display_path
            token_full_path = os.path.join(root_dir_path, token_rel_real_path)

            # an Item for this folder has already been created
            existing_folder_item = self._model_folders.get(token_rel_display_path)
            if existing_folder_item is not None:
                parent_item = existing_folder_item
            else:
                new_folder_item = QtGui.QStandardItem(str(token))

                # set special icon if this is the root folder
                # new_folder_item.setIcon(self._root_folder_icon) if i == 0 else new_folder_item.setIcon(self._folder_icon)
                new_folder_item.setIcon(folder_config.get_folder_icon(token_full_path))

                # mark as folder for sorting model
                folder_path_data = PathData(
                    relative_path=token_rel_real_path,
                    full_path=token_full_path,
                    is_folder=True,
                    )
                new_folder_item.setData(folder_path_data, QtCore.Qt.UserRole)

                parent_item.appendRow(new_folder_item)
                parent_item = new_folder_item
                self._model_folders[token_rel_display_path] = new_folder_item

        item = FileTreeModelItem(file_path, folder_config)
        path_data = PathData(
            relative_path=file_rel_path,
            full_path=file_path,
            is_folder=False,
            )
        item.setData(path_data, QtCore.Qt.UserRole)

        file_icon = folder_config.get_file_icon(file_path)
        item.setIcon(file_icon)

        parent_item.appendRow(item)

    def _trigger_double_clicked(self, index):
        model_index = self.proxy.mapToSource(index)
        tree_item = self.proxy.sourceModel().itemFromIndex(model_index)  # type: FileTreeModelItem

        if isinstance(tree_item, FileTreeModelItem):
            folder_config = tree_item.folder_config # type: FolderConfig
            folder_config.file_double_clicked(tree_item.file_path)
            self.file_double_clicked.emit(tree_item.file_path)

    def set_filter(self, text=None):
        search = QtCore.QRegExp(text, QtCore.Qt.CaseInsensitive, QtCore.QRegExp.RegExp)
        self.proxy.setFilterRegExp(search)
        if not text:
            if self.default_expand_depth is None:
                self.collapseAll()
            else:
                self.expandToDepth(self.default_expand_depth)
        else:
            self.expandAll()


class FileTreeModelItem(QtGui.QStandardItem):
    def __init__(self, file_path=None, folder_config=None):
        super(FileTreeModelItem, self).__init__()
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.folder_config = folder_config
        self.setData(self.file_name, QtCore.Qt.DisplayRole)
        self.setFlags(self.flags() ^ QtCore.Qt.ItemIsDropEnabled)


class FileTreeSortProxyModel(QtCore.QSortFilterProxyModel):
    """
    Sorting proxy model that always places folders on top.
    copied from https://stackoverflow.com/a/25627929

    """

    def __init__(self, model):
        super(FileTreeSortProxyModel, self).__init__(model)
        self.setSourceModel(model)

    def lessThan(self, left, right):
        """
        Perform sorting comparison.
        Since we know the sort order, we can ensure that folders always come first.
        """
        left_path_data = left.data(_qt.UserRole)  # type: PathData
        right_path_data = right.data(_qt.UserRole)  # type: PathData
        left_is_folder = left_path_data.is_folder if left_path_data else False
        left_data = left.data(_qt.DisplayRole) or ""
        right_is_folder = right_path_data.is_folder if right_path_data else False
        right_data = right.data(_qt.DisplayRole) or ""
        sort_order = self.sortOrder()

        if left_is_folder and not right_is_folder:
            result = sort_order == _qt.AscendingOrder
        elif not left_is_folder and right_is_folder:
            result = sort_order != _qt.AscendingOrder
        else:
            result = left_data.lower() < right_data.lower()
        return result

    def filterAcceptsRow(self, source_row, source_parent):
        filter_regex = self.filterRegExp()
        if filter_regex.isEmpty():
            return True

        r = source_row  # type: int
        p = source_parent  # type: QtCore.QModelIndex
        model_index = self.sourceModel().index(r, 0, p)
        path_data = self.sourceModel().data(model_index, _qt.UserRole)  # type: PathData

        # check children
        for i in range(self.sourceModel().rowCount(model_index)):
            if self.filterAcceptsRow(i, model_index):
                return True

        result = filter_regex.indexIn(path_data.relative_path)
        if result == -1:
            return False
        return True


class PathData(object):
    def __init__(self, relative_path, full_path=None, is_folder=False):
        self.relative_path = relative_path
        self.full_path = full_path
        self.is_folder = is_folder


###############################################################################
# Debug widget things
# You probably don't need this section
from .ui_utils import ToolWindow

class TestFileTreeWindow(ToolWindow):

    def __init__(self):
        super(TestFileTreeWindow, self).__init__()

        # create widgets
        search_line_edit = QtWidgets.QLineEdit()
        search_line_edit.setFocusPolicy(QtCore.Qt.ClickFocus)
        search_line_edit.setPlaceholderText("Search...")

        file_tree = QtFileTree()
        file_tree.set_folder(r"D:\Google Drive\Maya_Home\Brekel Recordings", file_exts=[".fbx"])

        # p4_test_config = PerforceFolderConfig(r"C:\Users\Richa\Perforce\LocalWorkspace")
        # p4_test_config.file_extensions = [".py"]
        # file_tree.add_folder_config(p4_test_config)

        # connect widgets
        search_line_edit.textChanged.connect(file_tree.set_filter)

        # layout widgets
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(search_line_edit)
        main_layout.addWidget(file_tree)

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setWindowTitle('File Tree Test Window')
        self.resize(QtCore.QSize(600, 400))
        self.show()


def open_standalone_test_window():
    import sys
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)
    
    win = TestFileTreeWindow()
    win.main()

    if standalone_app:
        from mocap_browser.resources import stylesheets
        stylesheets.apply_standalone_stylesheet()
        sys.exit(standalone_app.exec_())


if __name__ == '__main__':
    open_standalone_test_window()
