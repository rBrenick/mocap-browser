from .ui_utils import QtWidgets, QtCore, QtGui, ToolWindow


class TimeSliderWidget(QtWidgets.QWidget):
    value_changed = QtCore.Signal(float)

    def __init__(self, 
                 min=0, 
                 max=30, 
                 default=0.0, 
                 absolute=True, 
                 precision=0,
                 snap_to_frame=True, 
                 scroll_trigger=False,
                 *args, **kwargs):
        super(TimeSliderWidget, self).__init__(*args, **kwargs)
        self.min_value = min
        self.max_value = max
        self._value = default
        self._display_value = ""
        self._display_precision = precision
        self._snap_to_frame = snap_to_frame
        self._scroll_trigger = scroll_trigger
        self.absolute = absolute

        # internal variables
        self._multiplier = 1.0
        self._move_delta = 0
        self._on_click_x_pos = 0
        self._on_click_value = 0
        self._on_click_global_pos = None

        # selection marker
        self._selection_start = None
        self._selection_end = None

        # set some display things on init
        self.set_value(self._value)
        self.setCursor(QtCore.Qt.SplitHCursor)

    def value(self):
        return self._value

    def set_value(self, value):
        # clamp within range
        if self.min_value is not None:
            value = max(value, self.min_value)
        if self.max_value is not None:
            value = min(value, self.max_value)

        # set value for internal logic
        if self._snap_to_frame:
            value = round(value, 0)
        
        self._value = value
        self._display_value = self._get_formatted_display_value(value)

        # draw slider position
        self.repaint()

        # emit signal
        self.value_changed.emit(value)
        return value
        
    def set_minimum(self, min_value):
        self.min_value = min_value
        
    def set_maximum(self, max_value):
        self.max_value = max_value
    
    def reset_selection(self):
        self._selection_start = None
        self._selection_end = None

    def _get_formatted_display_value(self, value):
        if value == 0:
            return "0"
        else:
            precision_form = "{{:.{0}f}}".format(self._display_precision)
            return precision_form.format(value)
        
    # --------------------------------------------- LOGIC EVENTS ----------------------------------------
    def mousePressEvent(self, event):
        if event.buttons() != QtCore.Qt.LeftButton:
            return
        
        self._on_click_global_pos = event.globalPos()
        self._on_click_x_pos = event.x()
        self._on_click_value = self._value
        if self.absolute:
            snapped_val = self.ui_mouse_set_value(event)
        
            modifiers = QtWidgets.QApplication.keyboardModifiers()
            if modifiers == QtCore.Qt.ShiftModifier:
                self._selection_start = int(snapped_val)
            else:
                self.reset_selection()
        

    def mouseDoubleClickEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            val, ok = QtWidgets.QInputDialog.getDouble(self, "New Value", "Enter New Value", self._value,
                                                       decimals=self._display_precision)
            if ok:
                self.set_value(val)

    def mouseMoveEvent(self, event):
        if event.buttons() != QtCore.Qt.LeftButton:
            return
        self.setCursor(QtCore.Qt.BlankCursor)

        snapped_value = self.ui_mouse_set_value(event)
        if not self.absolute:
            QtGui.QCursor.setPos(self._on_click_global_pos)
        
        # set selection end
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self._selection_end = int(snapped_value)

    def mouseReleaseEvent(self, event):
        self._move_delta = 0
        self.setCursor(QtCore.Qt.SplitHCursor)
        if event.buttons() == QtCore.Qt.LeftButton:
            QtGui.QCursor.setPos(self._on_click_global_pos)

    def wheelEvent(self, event):
        if not self._scroll_trigger:
            return
        self.set_multiplier()
        new_value = self._value + ((event.delta() / 120) * self._multiplier)
        self.set_value(new_value)

    def keyPressEvent(self, event):
        self.set_multiplier()
        if event.key() & QtCore.Qt.LeftArrow:
            self.set_value(self._value - 1.0 * self._multiplier)
        elif event.key() & QtCore.Qt.RightArrow:
            self.set_value(self._value + 1.0 * self._multiplier)

    def ui_mouse_set_value(self, event):
        if self.absolute:
            # value as determined by point on slider
            val = self.ui_get_value_as_percent(event.x())
            val = val * self._multiplier
        else:
            # value as offset from the click position
            relative_value = self.ui_get_value_as_percent(event.x() - self._on_click_x_pos)
            relative_value = relative_value * self._multiplier
            self._move_delta += relative_value
            val = self._on_click_value + self._move_delta

            # convenience clamp so _move_delta doesn't go beyond range
            if self.min_value is not None and val < self.min_value:
                self._move_delta = self.min_value - self._on_click_value
            if self.max_value is not None and val > self.max_value:
                self._move_delta = self.max_value - self._on_click_value

        return self.set_value(val)

    def ui_get_value_as_percent(self, value):
        percent = float(value) / self.size().width()
        if self.absolute:
            return percent * (self.max_value - self.min_value) + self.min_value
        else:
            range_mult = abs(self.max_value if self.max_value is not None else 1.0)
            return range_mult * percent

    def set_multiplier(self):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == QtCore.Qt.ShiftModifier:
            self._multiplier = 10.0
        elif modifiers == QtCore.Qt.ControlModifier:
            self._multiplier = 0.1
        else:
            self._multiplier = 1.0

    # --------------------------------------------- DRAW EVENTS -----------------------------------------
    def paintEvent(self, e):
        qp = QtGui.QPainter()
        qp.begin(self)

        size = self.size()
        w = size.width()
        h = size.height()
        slider_height = h * 0.7

        font = QtGui.QFont('Serif', 8, QtGui.QFont.Normal)
        qp.setFont(font)

        # resize text to scale with widget
        h_factor = float(slider_height) / qp.fontMetrics().height()
        w_factor = float(w) / qp.fontMetrics().width(self._display_value)
        factor = min(h_factor, w_factor)  # the smaller value determines max text size
        font.setPointSizeF(font.pointSizeF() * factor)
        qp.setFont(font)

        slider_range_defined = self.max_value is not None and self.min_value is not None
        if slider_range_defined:
            # this took me way too long to figure out, even though it's just basic line equation
            m = float(w) / (self.max_value - self.min_value)
            current_value_width = int((m * self._value) - m * self.min_value)
        else:
            current_value_width = w

        # draw current frame indicator
        qp.setPen(QtGui.QColor(20, 20, 20)) # background
        qp.setBrush(QtGui.QColor(100, 100, 100)) # indicator
        qp.drawRect(0, 0, current_value_width, h)

        if slider_range_defined:
            frame_count = self.max_value - self.min_value
            frame_width_interval = w / frame_count

            # draw selection indicator
            selection_defined = self._selection_start is not None and self._selection_end is not None
            if selection_defined:
                x_start = self._selection_start * frame_width_interval
                x_width = (self._selection_end - self._selection_start) * frame_width_interval

                # selection box
                qp.setPen(QtGui.QColor(20, 20, 20))
                qp.setBrush(QtGui.QColor(60, 150, 80))
                qp.drawRect(x_start, 0, x_width, h)

            # frame lines
            for frame in range(frame_count):
                pen = QtGui.QPen(QtGui.QColor(40, 40, 40), 1, QtCore.Qt.SolidLine)
                qp.setPen(pen)
                qp.setBrush(QtCore.Qt.NoBrush)
                qp.drawRect(frame * frame_width_interval, 0, 0, h - 1)
            
            if selection_defined:
                x_start = self._selection_start * frame_width_interval
                x_width = (self._selection_end - self._selection_start) * frame_width_interval

                # frame text
                pen = QtGui.QPen(QtGui.QColor(220, 220, 220))
                qp.setPen(pen)
                qp.drawText(x_start, slider_height, str(self._selection_start))
            
                # frame text
                pen = QtGui.QPen(QtGui.QColor(220, 220, 220))
                qp.setPen(pen)
                qp.drawText(x_start + x_width, slider_height, str(self._selection_end))
            
        # frame numbers
        pen = QtGui.QPen(QtGui.QColor(220, 220, 220))
        qp.setPen(pen)
        qp.drawText(e.rect(), QtCore.Qt.AlignLeft, f" {self.min_value}")
        qp.drawText(e.rect(), QtCore.Qt.AlignRight, f"{self.max_value} ")

        # border
        pen = QtGui.QPen(QtGui.QColor(20, 20, 20), 1, QtCore.Qt.SolidLine)
        qp.setPen(pen)
        qp.setBrush(QtCore.Qt.NoBrush)
        qp.drawRect(0, 0, w - 1, h - 1)

        # draw value text
        pen = QtGui.QPen(QtGui.QColor(220, 220, 220))
        qp.setPen(pen)
        qp.drawText(e.rect(), QtCore.Qt.AlignCenter, self._display_value)

        qp.end()


class TestSliderWindow(ToolWindow):

    def __init__(self):
        super(TestSliderWindow, self).__init__()

        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addWidget(TimeSliderWidget(min=0, max=100, precision=0))

        central_widget = QtWidgets.QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.setWindowTitle('Time Slider Test Window')
        self.resize(QtCore.QSize(600, 400))
        self.show()


def open_standalone_test_window():
    import sys
    standalone_app = None
    if not QtWidgets.QApplication.instance():
        standalone_app = QtWidgets.QApplication(sys.argv)
    
    win = TestSliderWindow()
    win.main()

    if standalone_app:
        from mocap_browser.resources import stylesheets
        stylesheets.apply_standalone_stylesheet()
        sys.exit(standalone_app.exec_())


if __name__ == '__main__':
    open_standalone_test_window()
