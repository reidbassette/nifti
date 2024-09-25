import os, sys

from PyQt6.QtWidgets import (
    QComboBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QFileDialog,
    QSpacerItem,
    QSizePolicy,
    QMainWindow,
    QApplication,
    QGridLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QFont
from utilities import *
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.image import imread

basedir = os.path.dirname(__file__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'Orifice Calculator'
        self.left = 0
        self.top = 0
        self.width = 1200
        self.height = 900
        self.setWindowTitle(self.title)
        #self.setGeometry(self.left, self.top, self.width, self.height)
        self.table_widget = OrificeTableWidget(self)
        self.setCentralWidget(self.table_widget)
        
        self.show()

class OrificeTableWidget(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__()
        top_layout = QVBoxLayout()
        window_layout = QGridLayout()
                # Add label for picture
        self.diagram = QLabel()
        pixmap = QPixmap(os.path.join(basedir, 'orifice_diagram.png')).scaledToWidth(500)
        self.diagram.setPixmap(pixmap)
        self.diagram.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        top_layout.addWidget(self.diagram)
        window_layout.addWidget(MassFlowCalculator(self), 0, 0)
        window_layout.addWidget(OrificeSizeCalculator(self), 0, 2)


        column_spacer = QSpacerItem(10,1)
        window_layout.addItem(column_spacer, 0, 1)
        window_layout.addItem(column_spacer, 0, 3)
        top_layout.addLayout(window_layout)
        self.setLayout(top_layout)
    # mass flow converter


class MassFlowCalculator(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        outerlayout = QHBoxLayout()
        
        layout = QVBoxLayout()

        #Add list of fluid names

        self.title = QLabel("Mass Flow Rate")
        self.title.setFont(titlefont)
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.fluid_name_label = QLabel("Fluid")
        self.pressure_units_label = QLabel("Pressure Units")
        self.temperature_units_label = QLabel("Temperature Units")
        self.area_units_label = QLabel("Area Units")
        self.mass_flow_units_label = QLabel("Mass Flow Rate Units")

        self.fluid_name_selection = QComboBox()
        self.fluid_name_selection.addItems(fluid_names)
        
        self.pressure_units = QComboBox()
        self.pressure_units.addItems(pressure_units)
        self.pressure_units.currentTextChanged.connect( self.updatepressureunits)
        
        self.temperature_units = QComboBox()
        self.temperature_units.addItems(temperature_units)
        self.temperature_units.currentTextChanged.connect( self.updatetemperatureunits)

        self.area_units = QComboBox()
        self.area_units.addItems(area_units)
        self.area_units.currentTextChanged.connect( self.updateareaunits)

        self.mass_flow_units = QComboBox()
        self.mass_flow_units.addItems(mass_flow_units)

        # Add text box for pressure input
        self.pressure_input = QLineEdit()
        self.pressure_input.setMaxLength(10)
        self.pressure_input.setPlaceholderText("101325")
        self.pressure_input.selectedText()

        #Label for pressure input
        self.pressure_input_label = QLabel("Upstream Pressure, " + self.pressure_units.currentText())

        # Add text box for pressure input
        self.downstream_pressure_input = QLineEdit()
        self.downstream_pressure_input.setMaxLength(10)
        self.downstream_pressure_input.setPlaceholderText("101325")
        self.downstream_pressure_input.selectedText()
        
        #Label for pressure input
        self.downstream_pressure_input_label = QLabel("Downstream Pressure, " + self.pressure_units.currentText())
 
        #Add text box for vessel temperature
        self.vessel_temperature = QLineEdit()
        self.vessel_temperature.setMaxLength(5)
        self.vessel_temperature.setPlaceholderText("300")

        self.analyst_name = QLineEdit()
        self.analyst_name.setMaxLength(40)
        self.analyst_name.setPlaceholderText("Your Name")

        self.date = QLineEdit()
        self.date.setMaxLength(10)
        self.date.setPlaceholderText("Date (##-##-####)")

        #Label for Vessel temperature
        self.vessel_temperature_label = QLabel("Upstream Temperature, " + self.temperature_units.currentText())

        #Add text box for orifice area
        self.orifice_area = QLineEdit()
        self.orifice_area.setMaxLength(10)
        self.orifice_area.setPlaceholderText("0.1")

        #Label for orifice area
        self.orifice_area_label = QLabel(
            "Equivalent Orifice Area (CdA), " +
            self.area_units.currentText()
        )

        #Add Label
        self.mass_flow_rate = QLabel("0.0")

        #Update Button

        self.update_button = QPushButton('Update')
        self.update_button.clicked.connect(self.update_button_clicked)


        verticalSpacer = QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        #Define layout
        layout.addWidget(self.title)
        layout.addWidget(self.analyst_name)
        layout.addWidget(self.date)
        layout.addWidget(self.fluid_name_label)
        layout.addWidget(self.fluid_name_selection)
        layout.addWidget(self.pressure_units_label)
        layout.addWidget(self.pressure_units)
        layout.addWidget(self.temperature_units_label)
        layout.addWidget(self.temperature_units)
        layout.addWidget(self.area_units_label)
        layout.addWidget(self.area_units)
        layout.addWidget(self.mass_flow_units_label)
        layout.addWidget(self.mass_flow_units)
        layout.addWidget(self.pressure_input_label)
        layout.addWidget(self.pressure_input)
        layout.addWidget(self.vessel_temperature_label)
        layout.addWidget(self.vessel_temperature)
        layout.addWidget(self.downstream_pressure_input_label)
        layout.addWidget(self.downstream_pressure_input)
        layout.addWidget(self.orifice_area_label)
        layout.addWidget(self.orifice_area)
        layout.addWidget(self.update_button)
        layout.addWidget(self.mass_flow_rate)
        layout.addItem(verticalSpacer)

        outerlayout.addLayout(layout, 1)
        
        self.setLayout(outerlayout)


    def updatepressureunits(self, s):
        self.pressure_input_label.setText(
            "Vessel Pressure, " + f'{s}'
        )
        self.downstream_pressure_input_label.setText(
            "Downstream Pressure, " + f'{s}'
        )
    
    def updatetemperatureunits(self, s):
        self.vessel_temperature_label.setText(
            "Vessel Temperature, " + f'{s}'
        )

    def updatevolumeunits(self, s):
        self.vessel_volume_label.setText(
            "Vessel Volume, " + f'{s}'
        )

    def updateareaunits(self, s):
        self.orifice_area_label.setText(
            "Equivalent Orifice Area (CdA), " + f'{s}'
        )

    def updateLabel(self, s):
        self.mass_flow_rate.setText(f'{s}')


    def update_button_clicked(self):
        """ 
        solve the initial value problem
        returns 
            soln.t: time series
            soln.y[0]: mass in upstream volume
            soln.y[1]: density in upstream volume
        """
        try:
            # update the peak mass flow rate text
            print("start")
            density = getfluidproperty(
                self.fluid_name_selection.currentText(),
                "D",
                "P",
                unit_convert(
                    float(self.pressure_input.text()),
                    self.pressure_units.currentText(),
                    "Pa"
                ),
                "T",
                unit_convert(
                    float(self.vessel_temperature.text()),
                    self.temperature_units.currentText(),
                    "K"
                )
            )
            print(density)
            self.mass_flow_rate.setText(
                "Mass flow rate: " 
                + '{:0.3e}'.format(
                    unit_convert(
                        mdotidealgas(
                            upstream_pressure=unit_convert(
                                float(self.pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            upstream_density= density,
                            downstream_pressure=unit_convert(
                                float(self.downstream_pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            CdA= unit_convert(
                                float(self.orifice_area.text()),
                                self.area_units.currentText(),
                                "m^2"
                            ),
                            fluid= self.fluid_name_selection.currentText()
                        ),
                        "kg/s",
                        self.mass_flow_units.currentText(),
                        self.fluid_name_selection.currentText()
                    ),
                ) 
                + " " + str(self.mass_flow_units.currentText())
            )
        except:
            self.mass_flow_rate.setText(
                "Invalid inputs or other error"
            )

class OrificeSizeCalculator(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        outerlayout = QHBoxLayout()
        
        layout = QVBoxLayout()

        #Add list of fluid names
        self.title = QLabel("Orifice Size")
        self.title.setFont(titlefont)
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.fluid_name_label = QLabel("Fluid")
        self.pressure_units_label = QLabel("Pressure Units")
        self.temperature_units_label = QLabel("Temperature Units")
        self.area_units_label = QLabel("Area Units")
        self.mass_flow_units_label = QLabel("Mass Flow Rate Units")

        self.fluid_name_selection = QComboBox()
        self.fluid_name_selection.addItems(fluid_names)
        
        self.pressure_units = QComboBox()
        self.pressure_units.addItems(pressure_units)
        self.pressure_units.currentTextChanged.connect( self.updatepressureunits)
        
        self.temperature_units = QComboBox()
        self.temperature_units.addItems(temperature_units)
        self.temperature_units.currentTextChanged.connect( self.updatetemperatureunits)

        self.area_units = QComboBox()
        self.area_units.addItems(area_units)
        self.area_units.currentTextChanged.connect( self.updateareaunits)

        self.mass_flow_units = QComboBox()
        self.mass_flow_units.addItems(mass_flow_units)
        self.mass_flow_units.currentTextChanged.connect(self.updatemassflowunits)

        # Add text box for pressure input
        self.pressure_input = QLineEdit()
        self.pressure_input.setMaxLength(10)
        self.pressure_input.setPlaceholderText("101325")
        self.pressure_input.selectedText()

        #Label for pressure input
        self.pressure_input_label = QLabel("Upstream Pressure, " + self.pressure_units.currentText())

        # Add text box for pressure input
        self.downstream_pressure_input = QLineEdit()
        self.downstream_pressure_input.setMaxLength(10)
        self.downstream_pressure_input.setPlaceholderText("101325")
        self.downstream_pressure_input.selectedText()
        
        #Label for pressure input
        self.downstream_pressure_input_label = QLabel("Downstream Pressure, " + self.pressure_units.currentText())
 
        #Add text box for vessel temperature
        self.vessel_temperature = QLineEdit()
        self.vessel_temperature.setMaxLength(5)
        self.vessel_temperature.setPlaceholderText("300")

        self.analyst_name = QLineEdit()
        self.analyst_name.setMaxLength(40)
        self.analyst_name.setPlaceholderText("Your Name")

        self.date = QLineEdit()
        self.date.setMaxLength(10)
        self.date.setPlaceholderText("Date (##-##-####)")

        #Label for Vessel temperature
        self.vessel_temperature_label = QLabel("Upstream Temperature, " + self.temperature_units.currentText())

        #Add text box for orifice area
        self.orifice_area = QLineEdit()
        self.orifice_area.setMaxLength(10)
        self.orifice_area.setPlaceholderText("0.1")

        #Label for orifice area
        self.orifice_area_label = QLabel(
            "Mass Flow Rate, " +
            self.mass_flow_units.currentText()
        )

        #Add Label
        self.mass_flow_rate = QLabel("0.0")
        self.mass_flow_rate.selectedText()

        # Add label for picture
        self.diagram = QLabel()
        pixmap = QPixmap(os.path.join(basedir, 'blowdown_diagram.jpg')).scaledToWidth(500)
        self.diagram.setPixmap(pixmap)
        self.diagram.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        #Update Button

        self.update_button = QPushButton('Update')
        self.update_button.clicked.connect(self.update_button_clicked)


        verticalSpacer = QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        #Define layout
        
        layout.addWidget(self.title)
        layout.addWidget(self.analyst_name)
        layout.addWidget(self.date)
        layout.addWidget(self.fluid_name_label)
        layout.addWidget(self.fluid_name_selection)
        layout.addWidget(self.pressure_units_label)
        layout.addWidget(self.pressure_units)
        layout.addWidget(self.temperature_units_label)
        layout.addWidget(self.temperature_units)
        layout.addWidget(self.area_units_label)
        layout.addWidget(self.area_units)
        layout.addWidget(self.mass_flow_units_label)
        layout.addWidget(self.mass_flow_units)
        layout.addWidget(self.pressure_input_label)
        layout.addWidget(self.pressure_input)
        layout.addWidget(self.vessel_temperature_label)
        layout.addWidget(self.vessel_temperature)
        layout.addWidget(self.downstream_pressure_input_label)
        layout.addWidget(self.downstream_pressure_input)
        layout.addWidget(self.orifice_area_label)
        layout.addWidget(self.orifice_area)
        layout.addWidget(self.update_button)
        layout.addWidget(self.mass_flow_rate)
        layout.addItem(verticalSpacer)

        outerlayout.addLayout(layout, 1)
        
        self.setLayout(outerlayout)


    def updatepressureunits(self, s):
        self.pressure_input_label.setText(
            "Upstream Pressure, " + f'{s}'
        )
        self.downstream_pressure_input_label.setText(
            "Downstream Pressure, " + f'{s}'
        )
    
    def updatetemperatureunits(self, s):
        self.vessel_temperature_label.setText(
            "Upstream Temperature, " + f'{s}'
        )

    def updateareaunits(self, s):
        self.orifice_area_label.setText(
            "Equivalent Orifice Area (CdA), " + f'{s}'
        )

    def updatemassflowunits(self, s):
        self.orifice_area_label.setText(
            "Mass Flow Rate, " +
            self.mass_flow_units.currentText()
        )

    def updateLabel(self, s):
        self.mass_flow_rate.setText(f'{s}')


    def update_button_clicked(self):
        """ 
        solve the initial value problem
        returns 
            soln.t: time series
            soln.y[0]: mass in upstream volume
            soln.y[1]: density in upstream volume
        """
        try:
            # update the peak mass flow rate text
            print("start")
            density = getfluidproperty(
                self.fluid_name_selection.currentText(),
                "D",
                "P",
                unit_convert(
                    float(self.pressure_input.text()),
                    self.pressure_units.currentText(),
                    "Pa"
                ),
                "T",
                unit_convert(
                    float(self.vessel_temperature.text()),
                    self.temperature_units.currentText(),
                    "K"
                )
            )
            print(density)
            self.mass_flow_rate.setText(
                "Orifice CdA: " 
                + '{:0.3e}'.format(
                    unit_convert(
                        mdot2CdA(
                            upstream_pressure=unit_convert(
                                float(self.pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            upstream_density= density,
                            downstream_pressure=unit_convert(
                                float(self.downstream_pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            mdot= unit_convert(
                                float(self.orifice_area.text()),
                                self.mass_flow_units.currentText(),
                                "kg/s",
                                fluid= self.fluid_name_selection.currentText()
                            ),
                            fluid= self.fluid_name_selection.currentText()
                        ),
                        "m^2",
                        self.area_units.currentText()
                    ),
                ) 
                + " " + str(self.area_units.currentText())
            )
        except:
            self.mass_flow_rate.setText(
                "Invalid inputs or other error"
            )

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
