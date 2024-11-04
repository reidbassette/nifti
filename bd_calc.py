
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
    QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from utilities import *
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.image import imread

basedir = os.path.dirname(__file__)

class MplCanvas(FigureCanvas):

    def __init__(self, parent=None, width=10, height=8, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = 'Blowdown Calculator'
        self.left = 0
        self.top = 0
        self.width = 1200
        self.height = 900
        self.setWindowTitle(self.title)
        #self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.table_widget = BlowdownCalculator(self)
        self.setCentralWidget(self.table_widget)
        
        self.show()

class BlowdownCalculator(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__(parent)

        self.canvas = MplCanvas(self, width=5,height=4, dpi=100)
        outerlayout = QHBoxLayout()
        
        layout = QVBoxLayout()
        layout2 = QVBoxLayout()

        #Add list of fluid names

        self.fluid_name_label = QLabel("Fluid")
        self.pressure_units_label = QLabel("Pressure Units")
        self.temperature_units_label = QLabel("Temperature Units")
        self.volume_units_label = QLabel("Volume Units")
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

        self.volume_units = QComboBox()
        self.volume_units.addItems(volume_units)
        self.volume_units.currentTextChanged.connect( self.updatevolumeunits)

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
        self.pressure_input_label = QLabel("Vessel Pressure, " + self.pressure_units.currentText())

        #Add text box for vessel volume
        self.vessel_volume = QLineEdit()
        self.vessel_volume.setMaxLength(5)
        self.vessel_volume.setPlaceholderText("10")

        # Add text box for pressure input
        self.downstream_pressure_input = QLineEdit()
        self.downstream_pressure_input.setMaxLength(10)
        self.downstream_pressure_input.setPlaceholderText("101325")
        self.downstream_pressure_input.selectedText()
        
        #Label for pressure input
        self.downstream_pressure_input_label = QLabel("Downstream Pressure, " + self.pressure_units.currentText())

        #Label for Vessel Volume
        self.vessel_volume_label = QLabel("Vessel Volume, " + str(self.volume_units.currentText()))

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
        self.vessel_temperature_label = QLabel("Vessel Temperature, " + self.temperature_units.currentText())

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

        # Add label for picture
        self.diagram = QLabel()
        pixmap = QPixmap(os.path.join(basedir, 'blowdown_diagram.jpg')).scaledToWidth(500)
        self.diagram.setPixmap(pixmap)
        self.diagram.setAlignment(Qt.AlignmentFlag.AlignHCenter)


        self.minor_grid_checkbox = QCheckBox('Minor Grid On')


        #Update Button

        self.update_button = QPushButton('Update Plot')
        self.update_button.clicked.connect(self.update_button_clicked)

        #Save Report
        self.report_button = QPushButton('Save Report')
        self.report_button.clicked.connect(self.report_button_clicked)

        verticalSpacer = QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        #Define layout
        
        layout.addWidget(self.analyst_name)
        layout.addWidget(self.date)
        layout.addWidget(self.fluid_name_label)
        layout.addWidget(self.fluid_name_selection)
        layout.addWidget(self.pressure_units_label)
        layout.addWidget(self.pressure_units)
        layout.addWidget(self.temperature_units_label)
        layout.addWidget(self.temperature_units)
        layout.addWidget(self.volume_units_label)
        layout.addWidget(self.volume_units)
        layout.addWidget(self.area_units_label)
        layout.addWidget(self.area_units)
        layout.addWidget(self.mass_flow_units_label)
        layout.addWidget(self.mass_flow_units)
        layout.addWidget(self.vessel_volume_label)
        layout.addWidget(self.vessel_volume)
        layout.addWidget(self.pressure_input_label)
        layout.addWidget(self.pressure_input)
        layout.addWidget(self.vessel_temperature_label)
        layout.addWidget(self.vessel_temperature)
        layout.addWidget(self.downstream_pressure_input_label)
        layout.addWidget(self.downstream_pressure_input)
        layout.addWidget(self.orifice_area_label)
        layout.addWidget(self.orifice_area)
        layout.addWidget(self.minor_grid_checkbox)
        layout.addWidget(self.update_button)
        layout.addWidget(self.mass_flow_rate)
        layout.addWidget(self.report_button)
        layout.addItem(verticalSpacer)
        layout2.addWidget(self.diagram, 1)
        layout2.addWidget(self.canvas, 2)

        outerlayout.addLayout(layout, 1)
        outerlayout.addLayout(layout2, 2)
        
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

    def update_pressure_plot(self, time_series, pressure_series, time_units):
        """
        update plot
        """
        self.canvas.axes.cla()
        self.canvas.axes.plot(time_series, pressure_series)
        self.canvas.axes.set_ylabel("Pressure, " + self.pressure_units.currentText())
        self.canvas.axes.set_xlabel("Time, " + str(time_units))
        self.canvas.axes.set_title("Vessel Pressure vs. Time")
        self.canvas.axes.grid(True)
        if self.minor_grid_checkbox.isChecked():
            self.canvas.axes.minorticks_on()
            self.canvas.axes.grid(True, which='minor')
        self.canvas.draw()

    def update_button_clicked(self):
        """ 
        solve the initial value problem
        returns 
            soln.t: time series
            soln.y[0]: mass in upstream volume
            soln.y[1]: density in upstream volume
        """
        try:
            soln = solve_problem(
                func= func, 
                t_span= [
                    0,
                    moody_tau(
                        P1= unit_convert(
                            float(self.pressure_input.text()),
                            self.pressure_units.currentText(),
                            "Pa"
                        ),
                        P2= unit_convert(
                            float(self.downstream_pressure_input.text()),
                            self.pressure_units.currentText(),
                            "Pa"
                        ),
                        T1= unit_convert(
                            float(self.vessel_temperature.text()),
                            self.temperature_units.currentText(),
                            "K"
                        ),
                        CdA= unit_convert(
                            float(self.orifice_area.text()),
                            self.area_units.currentText(),
                            "m^2"
                        ),
                        Volume= unit_convert(
                            float(self.vessel_volume.text()),
                            self.volume_units.currentText(),
                            "m^3"
                        ),
                        fluid= self.fluid_name_selection.currentText()
                    ) * 2
                ], 
                event= event, 
                volume= unit_convert(
                    float(self.vessel_volume.text()),
                    self.volume_units.currentText(),
                    "m^3"
                ), 
                P0= unit_convert(
                    float(self.pressure_input.text()),
                    self.pressure_units.currentText(),
                    "Pa"
                ), 
                T0= unit_convert(
                    float(self.vessel_temperature.text()),
                    self.temperature_units.currentText(),
                    "K"
                ), 
                Pb= unit_convert(
                    float(self.downstream_pressure_input.text()),
                    self.pressure_units.currentText(),
                    "Pa"
                ), 
                CdA=unit_convert(
                    float(self.orifice_area.text()),
                    self.area_units.currentText(),
                    "m^2"
                ), 
                fluid= self.fluid_name_selection.currentText()
            )
            P = np.zeros(len(soln.y[1]))
            for i in range(len(soln.y[1])):
                P[i] = unit_convert(
                    getfluidproperty(
                        self.fluid_name_selection.currentText(),
                        "P",
                        "D",
                        soln.y[1][i],
                        "S",
                        getfluidproperty(
                            self.fluid_name_selection.currentText(),
                            "S",
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
                            ),
                        )
                    ),
                    "Pa",
                    self.pressure_units.currentText()
                )
            if soln.t_events[0] > 1800:
                t = soln.t / 60
                time_units = "mins"
            else:
                t = soln.t
                time_units = "s"
            # update the pressure vs time plot
            self.update_pressure_plot(t, P, time_units)
            # update the peak mass flow rate text
            self.mass_flow_rate.setText(
                "Peak mass flow rate: " 
                + '{:0.3e}'.format(
                    unit_convert(
                        mdotidealgas(
                            upstream_pressure=unit_convert(
                                P[0],
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            upstream_density= soln.y[1][0],
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

    def report_button_clicked(self):
        filedialog = QFileDialog()
        filedialog.setOption(filedialog.Option.DontUseNativeDialog, True)
        fileName, _ = filedialog.getSaveFileName(self, 
            "Save File", "", "PDF Files (*.pdf)")
        if fileName:
            """ 
            solve the initial value problem
            returns 
                soln.t: time series
                soln.y[0]: mass in upstream volume
                soln.y[1]: density in upstream volume
            """
            try:
                soln = solve_problem(
                    func= func, 
                    t_span= [
                        0,
                        moody_tau(
                            P1= unit_convert(
                                float(self.pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            P2= unit_convert(
                                float(self.downstream_pressure_input.text()),
                                self.pressure_units.currentText(),
                                "Pa"
                            ),
                            T1= unit_convert(
                                float(self.vessel_temperature.text()),
                                self.temperature_units.currentText(),
                                "K"
                            ),
                            CdA= unit_convert(
                                float(self.orifice_area.text()),
                                self.area_units.currentText(),
                                "m^2"
                            ),
                            Volume= unit_convert(
                                float(self.vessel_volume.text()),
                                self.volume_units.currentText(),
                                "m^3"
                            ),
                            fluid= self.fluid_name_selection.currentText()
                        ) * 2
                    ], 
                    event= event, 
                    volume= unit_convert(
                        float(self.vessel_volume.text()),
                        self.volume_units.currentText(),
                        "m^3"
                    ), 
                    P0= unit_convert(
                        float(self.pressure_input.text()),
                        self.pressure_units.currentText(),
                        "Pa"
                    ), 
                    T0= unit_convert(
                        float(self.vessel_temperature.text()),
                        self.temperature_units.currentText(),
                        "K"
                    ), 
                    Pb= unit_convert(
                        float(self.downstream_pressure_input.text()),
                        self.pressure_units.currentText(),
                        "Pa"
                    ), 
                    CdA=unit_convert(
                        float(self.orifice_area.text()),
                        self.area_units.currentText(),
                        "m^2"
                    ), 
                    fluid= self.fluid_name_selection.currentText()
                )
                P = np.zeros(len(soln.y[1]))
                for i in range(len(soln.y[1])):
                    P[i] = unit_convert(
                        getfluidproperty(
                            self.fluid_name_selection.currentText(),
                            "P",
                            "D",
                            soln.y[1][i],
                            "S",
                            getfluidproperty(
                                self.fluid_name_selection.currentText(),
                                "S",
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
                                ),
                            )
                        ),
                        "Pa",
                        self.pressure_units.currentText()
                    )

                mfr = unit_convert(
                    mdotidealgas(
                        upstream_pressure=unit_convert(
                            P[0],
                            self.pressure_units.currentText(),
                            "Pa"
                        ),
                        upstream_density= soln.y[1][0],
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
                )
                if soln.t_events[0] > 1800:
                    t = soln.t / 60
                    time_units = "mins"
                else:
                    t = soln.t
                    time_units = "s"
                generate_report(
                    t,
                    P,
                    self.analyst_name.text(),
                    self.date.text(),
                    self.fluid_name_selection.currentText(),
                    self.vessel_volume.text(),
                    self.pressure_input.text(),
                    self.vessel_temperature.text(),
                    self.downstream_pressure_input.text(),
                    self.orifice_area.text(),
                    '{:0.3e}'.format(mfr),
                    self.pressure_units.currentText(),
                    self.volume_units.currentText(),
                    self.temperature_units.currentText(),
                    self.area_units.currentText(),
                    self.mass_flow_units.currentText(),
                    time_units, 
                    fileName
                )
                self.mass_flow_rate.setText(
                    "Saved to " + fileName
                )
            except:
                self.mass_flow_rate.setText(
                    "Could not generate report"
                )


    


def func(t, y, volume, upstream_entropy, downstream_pressure, CdA, fluid):
    upstream_pressure = getfluidproperty(
        fluid,
        "P",
        "D",
        y[1],
        "S",
        upstream_entropy
    )
    return [
        -mdotidealgas(
            upstream_pressure,
            y[1],
            downstream_pressure,
            CdA,
            fluid
        ),
        -mdotidealgas(
            upstream_pressure,
            y[1],
            downstream_pressure,
            CdA,
            fluid
        )/volume
    ]

def event(
    t,
    y,
    volume,
    upstream_entropy, 
    downstream_pressure, 
    CdA, 
    fluid):
    upstream_pressure = getfluidproperty(
        fluid,
        "P",
        "D",
        y[1],
        "S",
        upstream_entropy
    )
    return mdotidealgas(
            upstream_pressure,
            y[1],
            downstream_pressure,
            CdA,
            fluid
        )
event.terminal = True 

def solve_problem(func, t_span, event, volume, P0, T0, Pb, CdA, fluid):
    times = np.linspace(t_span[0], t_span[1], 100)
    # initial values
    D0 = getfluidproperty(
            fluid,
            "D",
            "P",
            P0,
            "T",
            T0
        )
    S0 = getfluidproperty(
        fluid,
        "S",
        "P",
        P0,
        "T",
        T0
    )
    m0 = D0 * volume
    return solve_ivp(
        func, 
        t_span, 
        [m0,D0], 
        method='RK45', 
        t_eval=times, 
        events=event, 
        args=(volume, S0, Pb, CdA, fluid), 
        max_step = t_span[1] / len(times)
    )

#plotting functions
def generate_report(
    time_array, 
    pressure_array, 
    analyst_name, 
    date, 
    fluid_name, 
    volume, 
    bottle_pressure, 
    bottle_temperature, 
    low_pressure, 
    cda, 
    flow_rate, 
    pressure_units,
    volume_units,
    temperature_units,
    area_units,
    mass_flow_units,
    time_units,
    file_name
):
    print(file_name)
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = 'STIXGeneral'
    plt.rcParams['figure.dpi'] = 300
    num_rows = 5
    num_cols = 3
    fig, axs = plt.subplots(
        num_rows, 
        num_cols, 
        figsize=(8.5, 11), 
        width_ratios=[0.1, 0.8, 0.1], 
        height_ratios=[0.05, 0.3, 0.2, 0.4, 0.05]
    )
    for i in range(num_rows):
        for j in range(num_cols):
            axs[i, j].set_facecolor('white')
            axs[i, j].axis('off')
    Header = "Vessel Blowdown Calculation"
    Contact = "Analyst: " + str(analyst_name) +"\nDate: " + str(date)
    fluid = "Fluid: " + str(fluid_name)
    vessel_volume = "Vessel Volume: " + str(volume) + " " + str(volume_units)
    vessel_pressure = "Vessel Pressure: " + str(bottle_pressure) + " " + str(pressure_units)
    vessel_temperature = "Vessel Temperature: " + str(bottle_temperature) + " " + str(temperature_units)
    downstream_pressure = "Downstream Pressure: " + str(low_pressure) + " " + str(pressure_units)
    orifice_cda = "Orifice Cda: " + str(cda) + " " + str(area_units)
    peak_flow = "Peak Mass Flow Rate: " + str(flow_rate) + "  " + str(mass_flow_units)
    axs[1, 1].annotate(Header, (0.15, 1), weight='regular', fontsize=20, alpha=0.8)
    axs[1, 1].annotate(Contact, (0.25, 0.8), weight='bold', fontsize=14, alpha=0.6)
    axs[1, 1].annotate(
        fluid + "\n" + vessel_volume + "\n" 
        + vessel_pressure + "\n" + vessel_temperature + "\n"
        + downstream_pressure + "\n" + orifice_cda
        + "\n\n" + peak_flow,
        (0, 0),
        fontsize=12,
        alpha=1.0,
        weight='regular'
    )
    axs[2, 1].imshow(imread('blowdown_diagram.jpg'))
    axs[3, 1].plot(time_array, pressure_array)
    axs[3, 1].axis('on')
    axs[3, 1].ticklabel_format(useOffset=False)
    axs[3, 1].grid()
    axs[3, 1].set_xlabel("Time, " + str(time_units))
    axs[3, 1].set_ylabel("Pressure, " + str(pressure_units))
    fig.canvas.draw()
    image_array = np.array(fig.canvas.renderer.buffer_rgba())
    image = Image.fromarray(image_array)

    if file_name[-3:] == "pdf": 
        image.save(file_name, dpi=(300, 300))
    else:
        image.save(file_name + ".pdf", dpi=(300, 300))
    plt.close(fig)

def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
