import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cme_backend import (
    REFERENCE_CONDITION_PRESETS,
    absolute_pressure_units,
    build_reference_condition,
    flow_family,
    flow_units,
    fluid_names,
    line_pressure_units,
    requires_reference_condition,
    solve_cme_flow,
    temperature_units,
)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.title = "CME Assessment"
        self.setWindowTitle(self.title)
        self.table_widget = CMEAssessmentWidget(self)
        self.setCentralWidget(self.table_widget)
        self.show()


def make_row(*widgets):
    row_widget = QWidget()
    row_layout = QHBoxLayout()
    row_layout.setContentsMargins(0, 0, 0, 0)
    row_layout.setSpacing(8)

    for index, widget in enumerate(widgets):
        stretch = 2 if index == 0 else 1
        row_layout.addWidget(widget, stretch)

    row_widget.setLayout(row_layout)
    return row_widget


class ReferenceConditionWidget(QWidget):

    def __init__(self, title, default_preset, parent=None):
        super().__init__(parent)

        self._loading_preset = False
        self._title_text = title

        self.title = QLabel(title)
        self.title.setFont(sectionfont)

        self.preset_label = QLabel("Reference Definition")
        self.preset_label.setFont(menufont)

        self.preset = QComboBox()
        self.preset.addItems(list(REFERENCE_CONDITION_PRESETS.keys()))
        self.preset.currentTextChanged.connect(self.apply_preset)

        self.temperature_label = QLabel("Reference Temperature")
        self.temperature_label.setFont(menufont)

        self.temperature_value = QLineEdit()
        self.temperature_value.setPlaceholderText("20")
        self.temperature_value.editingFinished.connect(self.mark_custom)

        self.temperature_unit = QComboBox()
        self.temperature_unit.addItems(temperature_units)
        self.temperature_unit.currentTextChanged.connect(self.mark_custom)

        self.pressure_label = QLabel("Reference Pressure")
        self.pressure_label.setFont(menufont)

        self.pressure_value = QLineEdit()
        self.pressure_value.setPlaceholderText("14.72")
        self.pressure_value.editingFinished.connect(self.mark_custom)

        self.pressure_unit = QComboBox()
        self.pressure_unit.addItems(absolute_pressure_units)
        self.pressure_unit.currentTextChanged.connect(self.mark_custom)

        self.temperature_row = make_row(self.temperature_value, self.temperature_unit)
        self.pressure_row = make_row(self.pressure_value, self.pressure_unit)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self.title)
        layout.addWidget(self.preset_label)
        layout.addWidget(self.preset)
        layout.addWidget(self.temperature_label)
        layout.addWidget(self.temperature_row)
        layout.addWidget(self.pressure_label)
        layout.addWidget(self.pressure_row)

        self.setLayout(layout)

        self.preset.setCurrentText(default_preset)
        self.apply_preset(default_preset)

    def apply_preset(self, preset_name):
        preset = REFERENCE_CONDITION_PRESETS[preset_name]
        if preset is None:
            return

        self._loading_preset = True
        self.temperature_value.setText(f"{preset['temperature_value']:g}")
        self.temperature_unit.setCurrentText(preset["temperature_unit"])
        self.pressure_value.setText(f"{preset['pressure_value']:g}")
        self.pressure_unit.setCurrentText(preset["pressure_unit"])
        self._loading_preset = False

    def mark_custom(self):
        if self._loading_preset:
            return
        if self.preset.currentText() != "Custom":
            self.preset.setCurrentText("Custom")

    def set_inputs_enabled(self, enabled):
        widgets = [
            self.title,
            self.preset_label,
            self.preset,
            self.temperature_label,
            self.temperature_value,
            self.temperature_unit,
            self.pressure_label,
            self.pressure_value,
            self.pressure_unit,
        ]

        for widget in widgets:
            widget.setEnabled(enabled)

    def current_reference_condition(self):
        return build_reference_condition(
            name=self.preset.currentText(),
            temperature_value=float(self.temperature_value.text()),
            temperature_unit=self.temperature_unit.currentText(),
            pressure_value=float(self.pressure_value.text()),
            pressure_unit=self.pressure_unit.currentText(),
        )


class CMEAssessmentWidget(QWidget):

    def __init__(self, parent):
        super().__init__(parent)

        outerlayout = QHBoxLayout()
        outerlayout.setContentsMargins(8, 8, 8, 8)
        outerlayout.setSpacing(10)
        layout = QVBoxLayout()
        layout2 = QVBoxLayout()
        layout.setSpacing(6)
        layout2.setSpacing(8)

        self.title = QLabel("CME Assessment")
        self.title.setFont(titlefont)
        self.title.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.calibration_section = QLabel("Calibration Basis")
        self.calibration_section.setFont(sectionfont)

        self.calibration_gas_label = QLabel("Calibration Gas")
        self.calibration_gas_label.setFont(menufont)

        self.calibration_gas = QComboBox()
        self.calibration_gas.addItems(fluid_names)
        self.calibration_gas.setCurrentText("NITROGEN")

        self.measured_gas_label = QLabel("Measured Gas")
        self.measured_gas_label.setFont(menufont)

        self.measured_gas = QComboBox()
        self.measured_gas.addItems(fluid_names)
        self.measured_gas.setCurrentText("CARBON DIOXIDE")

        self.input_value_label = QLabel("Indicated CME Reading")
        self.input_value_label.setFont(menufont)

        self.input_value = QLineEdit()
        self.input_value.setPlaceholderText("25")

        self.input_unit_label = QLabel("Input Flow Unit")
        self.input_unit_label.setFont(menufont)

        self.input_unit = QComboBox()
        self.input_unit.addItems(flow_units)
        self.input_unit.setCurrentText("Nm^3/hr")
        self.input_unit.currentTextChanged.connect(self.refresh_reference_widgets)

        self.input_reference = ReferenceConditionWidget(
            "Input Reference",
            "NIFTI Normal: 20 C, 14.72 psia",
            self,
        )

        self.line_section = QLabel("Measured Stream Conditions")
        self.line_section.setFont(sectionfont)

        self.line_temperature_label = QLabel("Measured Gas Temperature")
        self.line_temperature_label.setFont(menufont)

        self.line_temperature = QLineEdit()
        self.line_temperature.setPlaceholderText("23")

        self.line_temperature_unit = QComboBox()
        self.line_temperature_unit.addItems(temperature_units)
        self.line_temperature_unit.setCurrentText("C")
        self.line_temperature_row = make_row(
            self.line_temperature,
            self.line_temperature_unit,
        )

        self.line_pressure_label = QLabel("Measured Gas Pressure")
        self.line_pressure_label.setFont(menufont)

        self.line_pressure = QLineEdit()
        self.line_pressure.setPlaceholderText("14.72")

        self.line_pressure_unit = QComboBox()
        self.line_pressure_unit.addItems(line_pressure_units)
        self.line_pressure_unit.setCurrentText("psia")
        self.line_pressure_row = make_row(
            self.line_pressure,
            self.line_pressure_unit,
        )

        self.output_section = QLabel("Output Basis")
        self.output_section.setFont(sectionfont)

        self.output_unit_label = QLabel("Requested Output Unit")
        self.output_unit_label.setFont(menufont)

        self.output_unit = QComboBox()
        self.output_unit.addItems(flow_units)
        self.output_unit.setCurrentText("SLPM")
        self.output_unit.currentTextChanged.connect(self.refresh_reference_widgets)

        self.output_reference = ReferenceConditionWidget(
            "Output Reference",
            "STP: 0 C, 1 atm",
            self,
        )

        self.update_button = QPushButton("Solve CME Conversion")
        self.update_button.clicked.connect(self.update_button_clicked)

        self.status_label = QLabel(
            "Viscosity-driven actual-flow correction with density-based conversion "
            "between actual, standard/normal, and mass flow bases."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.corrected_flow_label = QLabel("Corrected Flow: --")
        self.corrected_flow_label.setFont(titlefont)
        self.corrected_flow_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.actual_ratio_label = QLabel("Actual-flow gas correction ratio: --")
        self.actual_ratio_label.setFont(sectionfont)
        self.actual_ratio_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.mass_ratio_label = QLabel("Mass-flow ratio: --")
        self.mass_ratio_label.setFont(sectionfont)
        self.mass_ratio_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.display_factor_label = QLabel("Selected-unit factor: --")
        self.display_factor_label.setFont(sectionfont)
        self.display_factor_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self.results_tabs = QTabWidget()
        self.results_text = QPlainTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(monofont)

        self.equations_text = QPlainTextEdit()
        self.equations_text.setReadOnly(True)
        self.equations_text.setFont(monofont)

        self.notes_text = QPlainTextEdit()
        self.notes_text.setReadOnly(True)
        self.notes_text.setFont(monofont)
        self.notes_text.setPlainText(self.default_notes_text())

        self.results_tabs.addTab(self.results_text, "Results")
        self.results_tabs.addTab(self.equations_text, "Equations")
        self.results_tabs.addTab(self.notes_text, "Method Notes")

        left_panel = QWidget()
        left_panel.setLayout(layout)

        self.left_scroll = QScrollArea()
        self.left_scroll.setWidgetResizable(True)
        self.left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.left_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.left_scroll.setWidget(left_panel)

        verticalSpacer = QSpacerItem(
            5,
            5,
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Expanding,
        )

        layout.addWidget(self.title)
        layout.addWidget(self.calibration_section)
        layout.addWidget(self.calibration_gas_label)
        layout.addWidget(self.calibration_gas)
        layout.addWidget(self.measured_gas_label)
        layout.addWidget(self.measured_gas)
        layout.addWidget(self.input_value_label)
        layout.addWidget(self.input_value)
        layout.addWidget(self.input_unit_label)
        layout.addWidget(self.input_unit)
        layout.addWidget(self.input_reference)
        layout.addWidget(self.line_section)
        layout.addWidget(self.line_temperature_label)
        layout.addWidget(self.line_temperature_row)
        layout.addWidget(self.line_pressure_label)
        layout.addWidget(self.line_pressure_row)
        layout.addWidget(self.output_section)
        layout.addWidget(self.output_unit_label)
        layout.addWidget(self.output_unit)
        layout.addWidget(self.output_reference)
        layout.addWidget(self.update_button)
        layout.addWidget(self.status_label)
        layout.addItem(verticalSpacer)

        layout2.addWidget(self.corrected_flow_label)
        layout2.addWidget(self.actual_ratio_label)
        layout2.addWidget(self.mass_ratio_label)
        layout2.addWidget(self.display_factor_label)
        layout2.addWidget(self.results_tabs, 1)

        outerlayout.addWidget(self.left_scroll, 1)
        outerlayout.addLayout(layout2, 2)
        self.setLayout(outerlayout)

        self.refresh_reference_widgets()

    def refresh_reference_widgets(self):
        self.input_reference.set_inputs_enabled(
            requires_reference_condition(self.input_unit.currentText())
        )
        self.output_reference.set_inputs_enabled(
            requires_reference_condition(self.output_unit.currentText())
        )

    def default_notes_text(self):
        return (
            "Assumptions and intent\n"
            "\n"
            "1. The CME laminar element is treated in the Hagen-Poiseuille sense, so at a fixed\n"
            "   differential-pressure operating point the actual volumetric flow scales with 1/mu.\n"
            "2. The gas correction ratio is therefore evaluated as mu_calibration / mu_measured\n"
            "   at the reported line temperature and pressure.\n"
            "3. Density is then used to move between actual volumetric, standard/normal volumetric,\n"
            "   and mass-flow bases.\n"
            "4. The tab uses the same REFPROP-first / CoolProp-fallback property path already used\n"
            "   elsewhere in NIFTI.\n"
            "\n"
            "Practical note\n"
            "\n"
            "Enter the measured gas temperature and pressure as close as possible to the CME read\n"
            "location. For standard/normal volumetric units, the selected reference definition controls\n"
            "the density used for the flow-basis conversion.\n"
        )

    def update_button_clicked(self):
        try:
            input_value = float(self.input_value.text())
            line_temperature = float(self.line_temperature.text())
            line_pressure = float(self.line_pressure.text())

            input_reference = None
            if requires_reference_condition(self.input_unit.currentText()):
                input_reference = self.input_reference.current_reference_condition()

            output_reference = None
            if requires_reference_condition(self.output_unit.currentText()):
                output_reference = self.output_reference.current_reference_condition()

            result = solve_cme_flow(
                calibration_gas=self.calibration_gas.currentText(),
                measured_gas=self.measured_gas.currentText(),
                input_value=input_value,
                input_unit=self.input_unit.currentText(),
                line_temperature_value=line_temperature,
                line_temperature_unit=self.line_temperature_unit.currentText(),
                line_pressure_value=line_pressure,
                line_pressure_unit=self.line_pressure_unit.currentText(),
                output_unit=self.output_unit.currentText(),
                input_reference=input_reference,
                output_reference=output_reference,
            )

            self.corrected_flow_label.setText(
                f"Corrected Flow: {self.format_scalar(result.output_value)} "
                f"{result.output_unit}"
            )
            self.actual_ratio_label.setText(
                "Actual-flow gas correction ratio: "
                f"{self.format_scalar(result.actual_flow_ratio)} "
                "(mu_cal / mu_meas)"
            )
            self.mass_ratio_label.setText(
                "Mass-flow ratio: "
                f"{self.optional_scalar(result.mass_flow_ratio)} "
                "(mdot_meas / mdot_eq)"
            )
            if result.display_factor is None:
                self.display_factor_label.setText("Selected-unit factor: n/a")
            else:
                self.display_factor_label.setText(
                    "Selected-unit factor: "
                    f"{self.format_scalar(result.display_factor)} "
                    f"[{result.output_unit} / {result.input_unit}]"
                )

            self.results_text.setPlainText(self.results_report(result))
            self.equations_text.setPlainText(self.equations_report(result))
            self.status_label.setText(
                "Solved successfully using the selected gases, line state, and "
                "reference-condition definitions."
            )
        except Exception as exc:
            self.corrected_flow_label.setText("Corrected Flow: --")
            self.actual_ratio_label.setText("Actual-flow gas correction ratio: --")
            self.mass_ratio_label.setText("Mass-flow ratio: --")
            self.display_factor_label.setText("Selected-unit factor: --")
            self.results_text.setPlainText("")
            self.equations_text.setPlainText("")
            self.status_label.setText(f"Unable to solve CME conversion: {exc}")

    def results_report(self, result):
        input_reference = "n/a"
        if result.input_reference is not None:
            input_reference = result.input_reference.summary

        output_reference = "n/a"
        if result.output_reference is not None:
            output_reference = result.output_reference.summary

        return (
            "Summary\n"
            "\n"
            f"Calibration gas: {result.calibration_gas}\n"
            f"Measured gas: {result.measured_gas}\n"
            f"Input reading: {self.format_scalar(result.input_value)} {result.input_unit}\n"
            f"Input reference: {input_reference}\n"
            f"Output unit: {result.output_unit}\n"
            f"Output reference: {output_reference}\n"
            "\n"
            "Line state\n"
            "\n"
            f"T_line = {self.format_scalar(result.line_state.temperature_k)} K\n"
            f"P_line = {self.format_scalar(result.line_state.pressure_pa)} Pa\n"
            "\n"
            "Property snapshot\n"
            "\n"
            f"rho_cal,line = {self.format_scalar(result.calibration_density_line_kgpm3)} kg/m^3\n"
            f"rho_meas,line = {self.format_scalar(result.measured_density_line_kgpm3)} kg/m^3\n"
            f"mu_cal,line = {self.format_scalar(result.calibration_viscosity_line_pas)} Pa*s\n"
            f"mu_meas,line = {self.format_scalar(result.measured_viscosity_line_pas)} Pa*s\n"
            f"rho_cal,ref,in = {self.optional_density(result.input_reference_density_kgpm3)}\n"
            f"rho_meas,ref,out = {self.optional_density(result.output_reference_density_kgpm3)}\n"
            "\n"
            "Derived rates\n"
            "\n"
            f"Equivalent calibration actual flow = "
            f"{self.format_scalar(result.equivalent_actual_flow_m3ps * 3600)} m^3/hr\n"
            f"Corrected measured actual flow = "
            f"{self.format_scalar(result.measured_actual_flow_m3ps * 3600)} m^3/hr\n"
            f"Equivalent calibration mass flow = "
            f"{self.format_scalar(result.equivalent_mass_flow_kgps)} kg/s\n"
            f"Corrected measured mass flow = "
            f"{self.format_scalar(result.measured_mass_flow_kgps)} kg/s\n"
            "\n"
            "Solved ratios\n"
            "\n"
            f"R_actual = {self.format_scalar(result.actual_flow_ratio)} = "
            "Q_actual,meas / Q_actual,eq\n"
            f"R_mass = {self.optional_scalar(result.mass_flow_ratio)} = "
            "mdot_meas / mdot_eq\n"
            f"Selected-basis factor = {self.optional_scalar(result.display_factor)}\n"
        )

    def equations_report(self, result):
        input_family = flow_family(result.input_unit)
        output_family = flow_family(result.output_unit)

        lines = [
            "Hagen-Poiseuille correction basis",
            "",
            "At the same CME differential-pressure operating point:",
            "    DeltaP proportional to mu * Q_actual",
            "    R_actual = Q_actual,meas / Q_actual,eq = mu_cal,line / mu_meas,line",
            "",
            "Applied sequence",
            "",
        ]

        if input_family == "standard_volume":
            lines.extend(
                [
                    "1) Convert the indicated standard/normal volumetric flow into an equivalent",
                    "   calibration-gas mass flow using the selected input reference density.",
                    f"   mdot_eq = Q_ref,in * rho_cal,ref,in",
                    f"   mdot_eq = {self.format_scalar(result.equivalent_mass_flow_kgps)} kg/s",
                    "",
                ]
            )
        elif input_family == "actual_volume":
            lines.extend(
                [
                    "1) Treat the indicated reading as an equivalent calibration-gas actual",
                    "   volumetric flow at the reported line state.",
                    f"   mdot_eq = Q_actual,eq * rho_cal,line",
                    f"   mdot_eq = {self.format_scalar(result.equivalent_mass_flow_kgps)} kg/s",
                    "",
                ]
            )
        else:
            lines.extend(
                [
                    "1) Convert the indicated reading directly to an equivalent calibration-gas",
                    "   mass flow.",
                    f"   mdot_eq = {self.format_scalar(result.equivalent_mass_flow_kgps)} kg/s",
                    "",
                ]
            )

        lines.extend(
            [
                "2) Recover the equivalent calibration-gas actual flow at the line state.",
                "   Q_actual,eq = mdot_eq / rho_cal,line",
                f"   Q_actual,eq = {self.format_scalar(result.equivalent_actual_flow_m3ps)} m^3/s",
                "",
                "3) Apply the CME gas-correction ratio from viscosity.",
                "   R_actual = mu_cal,line / mu_meas,line",
                f"   R_actual = {self.format_scalar(result.calibration_viscosity_line_pas)} / "
                f"{self.format_scalar(result.measured_viscosity_line_pas)}",
                f"   R_actual = {self.format_scalar(result.actual_flow_ratio)}",
                "",
                "4) Solve the measured-gas actual flow.",
                "   Q_actual,meas = Q_actual,eq * R_actual",
                f"   Q_actual,meas = {self.format_scalar(result.measured_actual_flow_m3ps)} m^3/s",
                "",
                "5) Convert to measured-gas mass flow at the same line state.",
                "   mdot_meas = Q_actual,meas * rho_meas,line",
                f"   mdot_meas = {self.format_scalar(result.measured_mass_flow_kgps)} kg/s",
                "",
            ]
        )

        if output_family == "standard_volume":
            lines.extend(
                [
                    "6) Convert to the requested standard/normal volumetric basis.",
                    "   Q_ref,out = mdot_meas / rho_meas,ref,out",
                    f"   value_out = {self.format_scalar(result.output_value)} {result.output_unit}",
                ]
            )
        elif output_family == "actual_volume":
            lines.extend(
                [
                    "6) Convert to the requested actual volumetric basis.",
                    "   Q_actual,out = mdot_meas / rho_meas,line",
                    f"   value_out = {self.format_scalar(result.output_value)} {result.output_unit}",
                ]
            )
        else:
            lines.extend(
                [
                    "6) Report the requested mass-flow basis.",
                    f"   value_out = {self.format_scalar(result.output_value)} {result.output_unit}",
                ]
            )

        return "\n".join(lines)

    def optional_density(self, value):
        if value is None:
            return "n/a"
        return f"{self.format_scalar(value)} kg/m^3"

    def optional_scalar(self, value):
        if value is None:
            return "n/a"
        return self.format_scalar(value)

    def format_scalar(self, value):
        magnitude = abs(value)
        if magnitude == 0:
            return "0"
        if magnitude >= 1e4 or magnitude < 1e-3:
            return f"{value:0.6e}"
        return f"{value:0.6f}".rstrip("0").rstrip(".")


verticalSpacer = QSpacerItem(5, 5, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
titlefont = QFont("Arial", 16)
titlefont.setBold(True)

sectionfont = QFont("Arial", 11)
sectionfont.setBold(True)

menufont = QFont("Arial", 10)
monofont = QFont("Courier New", 12)


def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
