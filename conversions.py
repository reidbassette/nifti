import sys
from PyQt6.QtWidgets import (
    QComboBox,
    QApplication,
    QMainWindow,
    QLabel,
    QLineEdit,
    QGridLayout,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QSpacerItem,
    QSizePolicy,
    QTabWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from utilities import (
    unit_convert,
    area_units,
    distance_units,
    pressure_units,
    volume_units,
    temperature_units,
    mass_flow_units,
    fluid_names,
    flow_capacity_units,
    density_units,
    mass_units
)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'Unit Converter'
        self.left = 0
        self.top = 0
        self.width = 1200
        self.height = 900
        self.setWindowTitle(self.title)
        #self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.table_widget = Conversions(self)
        self.setCentralWidget(self.table_widget)
        
        self.show()

class Conversions(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        window_layout = QGridLayout()
        
        window_layout.addWidget(PressureConverter(self), 0, 0)
        window_layout.addWidget(TemperatureConverter(self), 0, 2)
        window_layout.addWidget(DensityConverter(self), 0, 4)
        window_layout.addWidget(DistanceConverter(self), 1, 0)
        window_layout.addWidget(AreaConverter(self), 1, 2)
        window_layout.addWidget(VolumeConverter(self), 1, 4)
        window_layout.addWidget(FlowCapacityConverter(self), 2, 0)
        window_layout.addWidget(MassFlowConverter(self), 2, 2)
        window_layout.addWidget(MassConverter(self), 2, 4)


        column_spacer = QSpacerItem(10,1)
        window_layout.addItem(column_spacer, 0, 1)
        window_layout.addItem(column_spacer, 0, 3)
        window_layout.addItem(column_spacer, 1, 1)
        window_layout.addItem(column_spacer, 1, 3)
        self.setLayout(window_layout)
    # mass flow converter


class MassFlowConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Mass Flow Rate")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)

        self.fluid_label = QLabel("Fluid")
        self.fluid_label.setFont(menufont)
        layout.addWidget(self.fluid_label)

        self.fluid_name = QComboBox()
        self.fluid_name.addItems(fluid_names)
        layout.addWidget(self.fluid_name)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(mass_flow_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.setFont(menufont)
        self.output.selectedText()
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(mass_flow_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)
        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText(),
                        fluid=self.fluid_name.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class MassConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Mass")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)

        self.fluid_label = QLabel("Fluid")
        self.fluid_label.setFont(menufont)
        layout.addWidget(self.fluid_label)

        self.fluid_name = QComboBox()
        self.fluid_name.addItems(fluid_names)
        layout.addWidget(self.fluid_name)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(mass_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.setFont(menufont)
        self.output.selectedText()
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(mass_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)
        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText(),
                        fluid=self.fluid_name.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class PressureConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Pressure")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(pressure_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(pressure_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class TemperatureConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Temperature")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(temperature_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(temperature_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class AreaConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Area")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(area_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(area_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class VolumeConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Volume")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(volume_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(volume_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

class DistanceConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Distance")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(distance_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(distance_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")
#region FlowCapacityConverter
class FlowCapacityConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        
        self.tabs = QTabWidget()
        self.tab1 = Cv_to_CdAConverter(self)
        self.tab2 = Cv_to_DoConverter(self)
        self.tab3 = CdA_to_DoConverter(self)

        self.tabs.addTab(self.tab1, "Cv <> CdA")
        self.tabs.addTab(self.tab2, "Cv <> Do")
        self.tabs.addTab(self.tab3, "CdA <> Do")

        self.layout = QVBoxLayout()
        self.title = QLabel("Flow Capacity")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        self.layout.addWidget(self.title)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        """
        layout = QVBoxLayout()

        self.title = QLabel("Flow Capacity")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input, inches or Cv")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)
        self.input = QLineEdit()
        self.input.selectedText()
        self.input.setPlaceholderText("Input")
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(flow_capacity_units)
        layout.addWidget(self.input_unit)

        self.Cd_note = QLabel("Cd, only if using \"Cd, Do\"\n for either input or output")
        self.Cd_note.setFont(menufont)
        layout.addWidget(self.Cd_note)

        self.discharge_coefficient = QLineEdit()
        self.discharge_coefficient.selectedText()
        self.discharge_coefficient.setPlaceholderText("Cd: Discharge Coefficient")
        layout.addWidget(self.discharge_coefficient)

        self.output_label = QLabel("Output, inches or Cv")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output_label.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(flow_capacity_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText(),
                        Cd=float(self.discharge_coefficient.text())
                    )
                )
            )
        except:
            self.output.setText("Didn't work")
        """
#region CvtoCdA
class Cv_to_CdAConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()

        self.input_label = QLabel("Input: ")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input_unit = QComboBox()
        self.input_unit.addItems(["Cv", "CdA"])
        self.input_unit.currentTextChanged.connect(self.input_unit_changed)
        layout.addWidget(self.input_unit)

        self.input = QLineEdit()
        self.input.selectedText()
        self.input.setPlaceholderText("Input")
        layout.addWidget(self.input)

        self.input_unit_2_label = QLabel("Area Units")
        layout.addWidget(self.input_unit_2_label)

        self.input_unit_2 = QComboBox()
        self.input_unit_2.addItems(area_units)
        layout.addWidget(self.input_unit_2)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QLabel()
        self.output_unit.setText("CdA")#new 12/13/24
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)
    def input_unit_changed(self):
        if self.input_unit.currentText() == "CdA":
            self.output_unit.setText("Cv")
        elif self.input_unit.currentText() == "Cv":
            self.output_unit.setText("CdA")
        self.output_unit.setFont(menufont)

    def update_button_clicked(self):
        try:
            if self.input_unit.currentText() == "CdA":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                float(self.input.text()),
                                self.input_unit_2.currentText(),
                                "in^2"
                            ),
                            self.input_unit.currentText(),
                            self.output_unit.text()
                        )
                    )
                )
            elif self.input_unit.currentText() == "Cv":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                float(self.input.text()),
                                self.input_unit.currentText(),
                                self.output_unit.text()
                            ),
                            "in^2",
                            self.input_unit_2.currentText()
                        )
                    )
                )
            else:
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            float(self.input.text()),
                            self.input_unit.currentText(),
                            self.output_unit.text()
                        )
                    )
                )
            if self.input_unit.currentText() == "CdA":
                self.output_unit.setText("Cv")
            elif self.input_unit.currentText() == "Cv":
                self.output_unit.setText("CdA")
            self.output_unit.setFont(menufont)
        except:
            self.output.setText("Didn't work")
#region CvtoDo
class Cv_to_DoConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()

        self.input_label = QLabel("Input: ")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input_unit = QComboBox()
        self.input_unit.addItems(["Cv", "Cd, Do"])
        self.input_unit.currentTextChanged.connect(self.input_unit_changed)
        layout.addWidget(self.input_unit)

        self.input = QLineEdit()
        self.input.selectedText()
        self.input.setPlaceholderText("Input")
        layout.addWidget(self.input)

        self.input_unit_2_label = QLabel("Diameter Units")
        layout.addWidget(self.input_unit_2_label)

        self.input_unit_2 = QComboBox()
        self.input_unit_2.addItems(distance_units)
        layout.addWidget(self.input_unit_2)

        self.Cd_note = QLabel("Cd, 0 < Cd < 1")
        self.Cd_note.setFont(menufont)
        layout.addWidget(self.Cd_note)

        self.discharge_coefficient = QLineEdit()
        self.discharge_coefficient.selectedText()
        self.discharge_coefficient.setPlaceholderText("Cd: Discharge Coefficient")
        layout.addWidget(self.discharge_coefficient)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QLabel()
        self.output_unit.setText("Cd, Do")#new 12/13/24
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def input_unit_changed(self):
        if self.input_unit.currentText() == "Cd, Do":
            self.output_unit.setText("Cv")
        elif self.input_unit.currentText() == "Cv":
            self.output_unit.setText("Cd, Do")
        self.output_unit.setFont(menufont)

    def update_button_clicked(self):
        try:
            if self.input_unit.currentText() == "Cd, Do":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                float(self.input.text()),
                                self.input_unit_2.currentText(),
                                "in"
                            ),
                            self.input_unit.currentText(),
                            self.output_unit.text(),
                            Cd= float(self.discharge_coefficient.text())
                        )
                    )
                )
            elif self.input_unit.currentText() == "Cv":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                float(self.input.text()),
                                self.input_unit.currentText(),
                                self.output_unit.text(),
                                Cd= float(self.discharge_coefficient.text())
                            ),
                            "in",
                            self.input_unit_2.currentText()
                        )
                    )
                )
            else:
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            float(self.input.text()),
                            self.input_unit.currentText(),
                            self.output_unit.text(),
                            Cd= float(self.discharge_coefficient.text())
                        )
                    )
                )
            if self.input_unit.currentText() == "Cd, Do":
                self.output_unit.setText("Cv")
            elif self.input_unit.currentText() == "Cv":
                self.output_unit.setText("Cd, Do")
            self.output_unit.setFont(menufont)
        except:
            self.output.setText("Didn't work")

class CdA_to_DoConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()

        self.input_label = QLabel("Input: ")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input_unit = QComboBox()
        self.input_unit.addItems(["CdA", "Cd, Do"])
        self.input_unit.currentTextChanged.connect(self.input_unit_changed)
        layout.addWidget(self.input_unit)

        self.input = QLineEdit()
        self.input.selectedText()
        self.input.setPlaceholderText("Input")
        layout.addWidget(self.input)

        self.input_unit_2_label = QLabel("Diameter Units")
        layout.addWidget(self.input_unit_2_label)

        self.input_unit_2 = QComboBox()
        self.input_unit_2.addItems(distance_units)
        layout.addWidget(self.input_unit_2)

        self.input_unit_3_label = QLabel("Area Units")
        layout.addWidget(self.input_unit_3_label)

        self.input_unit_3 = QComboBox()
        self.input_unit_3.addItems(area_units)
        layout.addWidget(self.input_unit_3)

        self.Cd_note = QLabel("Cd, 0 < Cd < 1")
        self.Cd_note.setFont(menufont)
        layout.addWidget(self.Cd_note)

        self.discharge_coefficient = QLineEdit()
        self.discharge_coefficient.selectedText()
        self.discharge_coefficient.setPlaceholderText("Cd: Discharge Coefficient")
        layout.addWidget(self.discharge_coefficient)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QLabel()
        self.output_unit.setText("Cd, Do")#new
        layout.addWidget(self.output_unit)

        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def input_unit_changed(self):
        if self.input_unit.currentText() == "Cd, Do":
            self.output_unit.setText("CdA")
        elif self.input_unit.currentText() == "CdA":
            self.output_unit.setText("Cd, Do")
        self.output_unit.setFont(menufont)

    def update_button_clicked(self):
        try:
            if self.input_unit.currentText() == "Cd, Do":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                unit_convert(
                                    float(self.input.text()),
                                    self.input_unit_2.currentText(),
                                    "in"
                                ),
                                self.input_unit.currentText(),
                                self.output_unit.text(), #bug?
                                Cd= float(self.discharge_coefficient.text())
                            ),
                            "in^2",
                            self.input_unit_3.currentText()
                        )
                    )
                )
            elif self.input_unit.currentText() == "CdA":
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            unit_convert(
                                unit_convert(
                                    float(self.input.text()),
                                    self.input_unit_3.currentText(),
                                    "in^2"
                                ),
                                self.input_unit.currentText(),
                                self.output_unit.text(),
                                Cd= float(self.discharge_coefficient.text())
                            ),
                            "in",
                            self.input_unit_2.currentText()
                        )
                    )
                )
            else:
                self.output.setText(
                    '{:0.3e}'.format(
                        unit_convert(
                            float(self.input.text()),
                            self.input_unit.currentText(),
                            self.output_unit.text(),
                            Cd= float(self.discharge_coefficient.text())
                        )
                    )
                )
            if self.input_unit.currentText() == "Cd, Do":
                self.output_unit.setText("CdA")
            elif self.input_unit.currentText() == "CdA":
                self.output_unit.setText("Cd, Do")
            self.output_unit.setFont(menufont)
        except:
            self.output.setText("Didn't work")

class DensityConverter(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        layout = QVBoxLayout()
        
        self.title = QLabel("Density")
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.title.setFont(titlefont)
        layout.addWidget(self.title)
        
        self.input_label = QLabel("Input")
        self.input_label.setFont(menufont)
        layout.addWidget(self.input_label)

        self.input = QLineEdit()
        self.input.selectedText()
        layout.addWidget(self.input)

        self.input_unit = QComboBox()
        self.input_unit.addItems(density_units)
        layout.addWidget(self.input_unit)

        self.output_label = QLabel("Output")
        self.output_label.setFont(menufont)
        layout.addWidget(self.output_label)

        self.output = QLabel()
        self.output.selectedText()
        self.output.setFont(menufont)
        self.output.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.output)

        self.output_unit = QComboBox()
        self.output_unit.addItems(density_units)
        layout.addWidget(self.output_unit)
        
        self.update_button = QPushButton("Update")
        self.update_button.clicked.connect(self.update_button_clicked)
        layout.addWidget(self.update_button)

        layout.addItem(verticalSpacer)

        self.setLayout(layout)

    def update_button_clicked(self):
        try:
            self.output.setText(
                '{:0.3e}'.format(
                        unit_convert(
                        float(self.input.text()),
                        self.input_unit.currentText(),
                        self.output_unit.currentText()
                    )
                )
            )
        except:
            self.output.setText("Didn't work")

verticalSpacer = QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
titlefont = QFont("Arial", 16)
titlefont.setBold(True)

menufont = QFont("Arial", 10)


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()

