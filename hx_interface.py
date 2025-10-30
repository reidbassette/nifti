# hx_interface.py
import sys
import io
from contextlib import redirect_stdout
import numpy as np

# Utilities (contract must match your utilities.py)
from utilities import (
    unit_convert,
    pressure_units, temperature_units, distance_units, area_units,
    volume_units, mass_flow_units, energy_units, fluid_names
)

from PyQt6.QtWidgets import (
    QApplication, QLabel, QPushButton, QWidget, QLineEdit, QVBoxLayout, QHBoxLayout,
    QMainWindow, QComboBox, QGridLayout, QToolButton, QFrame, QMessageBox,
    QPlainTextEdit, QSizePolicy, QMenu
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

import hx_solver as hx

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# ────────────────────────────────────────────────────────────────────────────────
# Plot Canvas
# ────────────────────────────────────────────────────────────────────────────────
class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=4.0, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        self.ax = fig.add_subplot(111)
        self.ax.set_title("Temperature Profiles")
        self.ax.grid(True)
        super().__init__(fig)


# ────────────────────────────────────────────────────────────────────────────────
# Small helpers
# ────────────────────────────────────────────────────────────────────────────────
LOCK_CLOSED = "🔒"
LOCK_OPEN = "🔓"


def _float_or_none(text: str):
    try:
        return float(text)
    except Exception:
        return None


def _to_bool(flow_text: str) -> bool:
    # "COUNTERCURRENT" -> True, "PARALLEL" -> False
    return flow_text.upper().startswith("COUNTER")


def lbl_key(s: str) -> str:
    return s.strip().upper().replace(" ", "_")


def _energy_key_for_util(ui_unit: str) -> str:
    # utilities.to_W/from_W map 'BTU', UI shows 'BTUphr'
    return "BTU" if ui_unit.upper().startswith("BTU") else "W"


# ────────────────────────────────────────────────────────────────────────────────
# Lockable field
# ────────────────────────────────────────────────────────────────────────────────
class LockField(QWidget):
    """
    Composite: [QLineEdit or QComboBox] + [Lock button]
    """
    def __init__(self, kind='line', parent=None):
        super().__init__(parent)
        self.kind = kind
        lay = QHBoxLayout()
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        if kind == 'line':
            self.editor = QLineEdit()
        elif kind == 'combo':
            self.editor = QComboBox()
        else:
            raise ValueError("Unsupported kind for LockField")
        self.lock_btn = QToolButton()
        self.lock_btn.setCheckable(True)
        self.lock_btn.setText(LOCK_OPEN)
        self.lock_btn.setToolTip("Toggle lock")
        lay.addWidget(self.editor, 1)
        lay.addWidget(self.lock_btn, 0)
        self.setLayout(lay)
        self.lock_btn.toggled.connect(self._on_lock_toggled)

    def _on_lock_toggled(self, checked: bool):
        self.lock_btn.setText(LOCK_CLOSED if checked else LOCK_OPEN)

    def is_locked(self) -> bool:
        return self.lock_btn.isChecked()

    def set_locked(self, locked: bool):
        self.lock_btn.setChecked(locked)

    def setText(self, txt: str):
        if isinstance(self.editor, QLineEdit):
            self.editor.setText(txt)
        else:
            idx = self.editor.findText(txt)
            if idx < 0:
                self.editor.addItem(txt)
                idx = self.editor.findText(txt)
            self.editor.setCurrentIndex(idx)

    def text(self) -> str:
        return self.editor.text() if isinstance(self.editor, QLineEdit) else self.editor.currentText()

    def setItems(self, items):
        if isinstance(self.editor, QComboBox):
            self.editor.clear()
            self.editor.addItems(items)

    def set_placeholder(self, txt: str):
        if isinstance(self.editor, QLineEdit):
            self.editor.setPlaceholderText(txt)

    def connect_changed(self, slot):
        if isinstance(self.editor, QLineEdit):
            self.editor.editingFinished.connect(slot)
        else:
            self.editor.currentTextChanged.connect(slot)
        self.lock_btn.toggled.connect(slot)

    def mark_solved(self, solved: bool):
        if isinstance(self.editor, QLineEdit):
            # solved values → green tint
            self.editor.setStyleSheet("color: #2ca02c;" if solved else "")


# ────────────────────────────────────────────────────────────────────────────────
# Main window
# ────────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Heat Exchanger Tools')
        self.setCentralWidget(HxSolver(self))
        self.show()


# ────────────────────────────────────────────────────────────────────────────────
# HxSolver UI
# ────────────────────────────────────────────────────────────────────────────────
class HxSolver(QWidget):
    """
    UI for PLATE / SHELL & TUBE / AIR-COOLED; locks and tooltips included.
    """
    def __init__(self, parent):
        super().__init__()
        super(QWidget, self).__init__(parent)

        # Top-level grid
        self.grid = QGridLayout()
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(6)
        self.setLayout(self.grid)
        self._solve_count = 0

        # Title + Units bars
        self.titleLayout = QHBoxLayout()
        self.unitsBar = QHBoxLayout()
        self.unitsBar.setSpacing(12)

        # Three columns below the units bar
        self.left_col = QVBoxLayout()
        self.mid_col = QVBoxLayout()
        self.right_col = QVBoxLayout()

        # Sub-sections
        self.hotSideLayout = QVBoxLayout()
        self.coldSideLayout = QVBoxLayout()
        self.coreLayout = QVBoxLayout()
        self.dimensionsLayout = QVBoxLayout()
        self.plateBox = QWidget();  self.plateBox.setLayout(QVBoxLayout())
        self.stBox    = QWidget();  self.stBox.setLayout(QVBoxLayout())
        self.acBox    = QWidget();  self.acBox.setLayout(QVBoxLayout())
        self.buttonsLayout = QHBoxLayout()
        self.outputsLayout = QVBoxLayout()

        # Unit pickers
        self.pressureUnits = QComboBox();    self.pressureUnits.addItems(pressure_units)
        self.temperatureUnits = QComboBox(); self.temperatureUnits.addItems(temperature_units)
        self.volumeUnits = QComboBox();      self.volumeUnits.addItems(volume_units)
        self.energyUnits = QComboBox();      self.energyUnits.addItems(energy_units)
        self.areaUnits = QComboBox();        self.areaUnits.addItems(area_units)
        self.distanceUnits = QComboBox();    self.distanceUnits.addItems(distance_units)
        self.massFlowUnitsHot = QComboBox(); self.massFlowUnitsHot.addItems(mass_flow_units)
        self.massFlowUnitsCold = QComboBox(); self.massFlowUnitsCold.addItems(mass_flow_units)

        self._prev_mdot_hot_units = self.massFlowUnitsHot.currentText()
        self._prev_mdot_cold_units = self.massFlowUnitsCold.currentText()

        def chip(label, widget):
            row = QHBoxLayout(); row.setContentsMargins(0,0,0,0); row.setSpacing(6)
            t = QLabel(label); t.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row.addWidget(t); row.addWidget(widget)
            w = QWidget(); w.setLayout(row); return w

        for lbl, wid in [
            ("Temp", self.temperatureUnits), ("Press", self.pressureUnits),
            ("Dist", self.distanceUnits), ("Area", self.areaUnits),
            ("Vol", self.volumeUnits), ("Energy", self.energyUnits),
            ("ṁ (Hot)", self.massFlowUnitsHot), ("ṁ (Cold)", self.massFlowUnitsCold)
        ]:
            self.unitsBar.addWidget(chip(lbl, wid))
        self.unitsBar.addStretch(1)

        # Unit change wiring
        self.pressureUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.temperatureUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.volumeUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.energyUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.areaUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.distanceUnits.currentTextChanged.connect(self._refresh_all_labels)
        self.massFlowUnitsHot.currentTextChanged.connect(self._on_hot_mdot_units_changed)
        self.massFlowUnitsCold.currentTextChanged.connect(self._on_cold_mdot_units_changed)
        self.temperatureUnits.currentTextChanged.connect(self.solve)

        # Title bar
        self.nameLabel = QLabel("HX NAME")
        self.nameInput = QLineEdit()
        self.hxTypeLabel = QLabel("HX TYPE")
        self.hxTypeSelection = QComboBox(); self.hxTypeSelection.addItems(["PLATE", "SHELL & TUBE", "AIR-COOLED"])
        self.flowDirectionLabel = QLabel("FLOW DIRECTION")
        self.flowDirectionSelection = QComboBox(); self.flowDirectionSelection.addItems(["COUNTERCURRENT", "PARALLEL"])

        self.titleLayout.addWidget(self.nameLabel); self.titleLayout.addWidget(self.nameInput, 1)
        self.titleLayout.addWidget(self.hxTypeLabel); self.titleLayout.addWidget(self.hxTypeSelection)
        self.titleLayout.addWidget(self.flowDirectionLabel); self.titleLayout.addWidget(self.flowDirectionSelection)
        self.titleLayout.addStretch(1)

        # Field registry
        self.label_map = {}
        self.attr_for_label = {}
        self.row_for_attr = {} 

        # HOT
        self._Thi         = self._make_field_row(self.hotSideLayout, "TEMP HOT IN", 'line', solver_attr="_Thi")
        self._Tho         = self._make_field_row(self.hotSideLayout, "TEMP HOT OUT", 'line', solver_attr="_Tho")
        self._Pres_H_in   = self._make_field_row(self.hotSideLayout, "HOT INLET PRESSURE", 'line', solver_attr="_Pres_H_in")
        self._H_inlet_ID  = self._make_field_row(self.hotSideLayout, "HOT INLET I.D.", 'line', solver_attr="_H_inlet_ID")
        self._H_outlet_ID = self._make_field_row(self.hotSideLayout, "HOT OUTLET I.D.", 'line', solver_attr="_H_outlet_ID")
        self._mdot_h      = self._make_field_row(self.hotSideLayout, "HOT MASS FLOW", 'line', solver_attr="_mdot_h")
        self._H_in_nm3_hr = self._make_field_row(self.hotSideLayout, "HOT VOL FLOW (Nm^3/hr)", 'line', solver_attr="_H_in_nm3_hr")
        self._H_Fluid     = self._make_field_row(self.hotSideLayout, "HOT FLUID", 'combo', solver_attr="_H_Fluid")
        self._H_Fluid.lock_btn.setVisible(False)
        try:
            self._H_Fluid.setItems(fluid_names)
        except Exception:
            self._H_Fluid.setItems(["AIR", "NITROGEN", "HYDROGEN", "HELIUM", "ARGON"])

        # COLD
        self._Tci         = self._make_field_row(self.coldSideLayout, "TEMP COLD IN", 'line', solver_attr="_Tci")
        self._Tco         = self._make_field_row(self.coldSideLayout, "TEMP COLD OUT", 'line', solver_attr="_Tco")
        self._Pres_C_in   = self._make_field_row(self.coldSideLayout, "COLD INLET PRESSURE", 'line', solver_attr="_Pres_C_in")
        self._C_inlet_ID  = self._make_field_row(self.coldSideLayout, "COLD INLET I.D.", 'line', solver_attr="_C_inlet_ID")
        self._C_outlet_ID = self._make_field_row(self.coldSideLayout, "COLD OUTLET I.D.", 'line', solver_attr="_C_outlet_ID")
        self._mdot_c      = self._make_field_row(self.coldSideLayout, "COLD MASS FLOW", 'line', solver_attr="_mdot_c")
        self._C_in_nm3_hr = self._make_field_row(self.coldSideLayout, "COLD VOL FLOW (Nm^3/hr)", 'line', solver_attr="_C_in_nm3_hr")
        self._C_Fluid     = self._make_field_row(self.coldSideLayout, "COLD FLUID", 'combo', solver_attr="_C_Fluid")
        self._C_Fluid.lock_btn.setVisible(False)
        try:
            self._C_Fluid.setItems(fluid_names)
        except Exception:
            self._C_Fluid.setItems(["AIR", "NITROGEN", "HYDROGEN", "HELIUM", "ARGON"])

        # CORE
        self._q        = self._make_field_row(self.coreLayout, "HEAT TRANSFER RATE q", 'line', solver_attr="_q")
        self._q_max    = self._make_field_row(self.coreLayout, "THEORETICAL MAX q", 'line', solver_attr="_q_max")
        self._UA       = self._make_field_row(self.coreLayout, "OVERALL UA", 'line', solver_attr="_UA")
        self._NTU      = self._make_field_row(self.coreLayout, "NTU", 'line', solver_attr="_NTU")
        self._F_sub_T  = self._make_field_row(self.coreLayout, "LMTD CORR FACTOR F", 'line', solver_attr="_F_sub_T")
        self._epsilon  = self._make_field_row(self.coreLayout, "EFFECTIVENESS ε", 'line', solver_attr="_effectiveness_epsilon")

        # GEOMETRY / Plate
        self.plateMaterialLabel = QLabel("PLATE MATERIAL")
        self.plateMaterialSelection = QComboBox(); self.plateMaterialSelection.addItems(["SS316"])
        self.plateBox.layout().addWidget(self.plateMaterialLabel)
        self.plateBox.layout().addWidget(self.plateMaterialSelection)
        self._Plate_count             = self._make_field_row(self.plateBox.layout(), "PLATE COUNT", 'line', solver_attr="_Plate_count")
        self._Plate_Distribution_Bias = self._make_field_row(self.plateBox.layout(), "ODD CH ASSIGN (Bias)", 'combo', solver_attr="_Plate_Distribution_Bias")

        self._Plate_Distribution_Bias.setItems(["hot", "cold"])
        self._Hot_Passes              = self._make_field_row(self.plateBox.layout(), "HOT PASSES", 'line', solver_attr="_Hot_Passes")
        self._Lv   = self._make_field_row(self.plateBox.layout(), "VERT PORT DIST L_v", 'line', solver_attr="_Lv")
        self._Lh   = self._make_field_row(self.plateBox.layout(), "HORIZ PORT DIST L_h", 'line', solver_attr="_Lh")
        self._Dp   = self._make_field_row(self.plateBox.layout(), "PORT DIAMETER D_p", 'line', solver_attr="_Dp")
        self._pitch= self._make_field_row(self.plateBox.layout(), "PLATE PITCH p", 'line', solver_attr="_pitch")
        self._t_m  = self._make_field_row(self.plateBox.layout(), "PLATE THICKNESS t", 'line', solver_attr="_t_m")
        self._b    = self._make_field_row(self.plateBox.layout(), "MEAN CHANNEL GAP b", 'line', solver_attr="_mean_channel_gap")
        self._phi  = self._make_field_row(self.plateBox.layout(), "ENLARGEMENT φ", 'line', solver_attr="_enlargement_phi")
        self._fouling_hot  = self._make_field_row(self.plateBox.layout(), "FOULING HOT", 'line', solver_attr="_fouling_hot")
        self._fouling_cold = self._make_field_row(self.plateBox.layout(), "FOULING COLD", 'line', solver_attr="_fouling_cold")
        # SHELL & TUBE
        self.stHeader = self._section_header("Shell & Tube Geometry")
        self.stBox.layout().addWidget(self.stHeader)
        self._ST_hot_in_tube   = self._make_field_row(self.stBox.layout(), "HOT IN TUBE? (1/0)", 'line', solver_attr="_ST_hot_in_tube")
        self._ST_N_tubes       = self._make_field_row(self.stBox.layout(), "TUBES (count)", 'line', solver_attr="_ST_N_tubes")
        self._ST_N_tube_passes = self._make_field_row(self.stBox.layout(), "TUBE PASSES", 'line', solver_attr="_ST_N_tube_passes")
        self._ST_N_shell_passes= self._make_field_row(self.stBox.layout(), "SHELL PASSES", 'line', solver_attr="_ST_N_shell_passes")
        self._ST_Di            = self._make_field_row(self.stBox.layout(), "TUBE Di", 'line', solver_attr="_ST_Di")
        self._ST_Do            = self._make_field_row(self.stBox.layout(), "TUBE Do", 'line', solver_attr="_ST_Do")
        self._ST_L_pass        = self._make_field_row(self.stBox.layout(), "TUBE LENGTH/PASS", 'line', solver_attr="_ST_L_pass")
        self._ST_k_wall        = self._make_field_row(self.stBox.layout(), "TUBE WALL k", 'line', solver_attr="_ST_k_wall")
        self._ST_Rf_i          = self._make_field_row(self.stBox.layout(), "FOULING (inside)", 'line', solver_attr="_ST_Rf_i")
        self._ST_Rf_o          = self._make_field_row(self.stBox.layout(), "FOULING (outside)", 'line', solver_attr="_ST_Rf_o")
        self._ST_h_o           = self._make_field_row(self.stBox.layout(), "h_o (shell side, if known)", 'line', solver_attr="_ST_h_o")

        # AIR-COOLED / Compact
        self.acHeader = self._section_header("Air‑Cooled / Compact Core")
        self.acBox.layout().addWidget(self.acHeader)
        self._ACH_A_fr     = self._make_field_row(self.acBox.layout(), "FRONTAL AREA A_fr", 'line', solver_attr="_ACH_A_fr")
        self._ACH_V        = self._make_field_row(self.acBox.layout(), "CORE VOLUME V", 'line', solver_attr="_ACH_V")
        self._ACH_sigma    = self._make_field_row(self.acBox.layout(), "FREE-FLOW RATIO σ", 'line', solver_attr="_ACH_sigma")
        self._ACH_Dh       = self._make_field_row(self.acBox.layout(), "HYDR. DIAMETER Dh", 'line', solver_attr="_ACH_Dh")
        self._ACH_alpha    = self._make_field_row(self.acBox.layout(), "AREA DENSITY α=A/V", 'line', solver_attr="_ACH_alpha")
        self._ACH_Af_over_A= self._make_field_row(self.acBox.layout(), "FIN AREA FRACTION Af/A", 'line', solver_attr="_ACH_Af_over_A")
        self._ACH_eta_f    = self._make_field_row(self.acBox.layout(), "FIN EFFICIENCY η_f (opt)", 'line', solver_attr="_ACH_eta_f")
        self._ACH_eta_o_hot= self._make_field_row(self.acBox.layout(), "OVERALL SURF. EFF. η_o (opt)", 'line', solver_attr="_ACH_eta_o_hot")
        self._ACH_jH       = self._make_field_row(self.acBox.layout(), "j-FACTOR j_H", 'line', solver_attr="_ACH_jH")
        self._ACH_f_core   = self._make_field_row(self.acBox.layout(), "CORE friction factor f", 'line', solver_attr="_ACH_f_core")

        # Derived outputs
        self.out_labels = {}
        for title in [
            "LMTD", "HOT Cp (in/out/avg)", "COLD Cp (in/out/avg)",
            "HOT HEAT CAPACITY RATE Ch", "COLD HEAT CAPACITY RATE Cc",
            "Cmin / Cmax / Cr", "HOT INLET/OUTLET VELOCITY", "COLD INLET/OUTLET VELOCITY",
            "Channels per pass (hot/cold)", "Mass flow per channel (hot/cold)",
            # Plate extras
            "Dh (hydraulic diameter)", "G (mass velocity) H/C", "Re (hot/cold)",
            "h (hot/cold)", "U (calc)", "ΔP hot / ΔP cold / ΔP total",
            "ε (from NTU, Cr)", "Tho/Tco from ε-NTU", "Entropy S_gen / N_s",
            # S&T and ACHE extras
            "UA (S&T)", "U (S&T)", "Δp core (ACHE)"
        ]:
            lab = QLabel(f"{title}: —")
            lab.setWordWrap(True)
            self.outputsLayout.addWidget(lab)
            self.out_labels[title] = lab

        # Solve Log (right)
        self.solveLogHeaderRow = QHBoxLayout()
        self.solveLogHeader = self._section_header("Solve Log")
        self.logMenuBtn = QToolButton()
        self.logMenuBtn.setText("Verbosity")
        self.logMenuBtn.setToolTip("Select what to print in the log")
        self.logMenuBtn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.logMenu = QMenu(self)
        self.actShowIter = QAction("Show iteration prints", self, checkable=True, checked=True)
        self.actPretty = QAction("Include pretty_print()", self, checkable=True, checked=False)
        self.logMenu.addAction(self.actShowIter)
        self.logMenu.addAction(self.actPretty)
        self.logMenuBtn.setMenu(self.logMenu)
        self.solveLogHeaderRow.addWidget(self.solveLogHeader)
        self.solveLogHeaderRow.addWidget(self.logMenuBtn, 0, Qt.AlignmentFlag.AlignRight)
        self.solveLog = QPlainTextEdit()
        self.solveLog.setReadOnly(True)
        self.solveLog.setPlaceholderText("Run a solve to see iteration steps here...")
        self.solveLog.setMinimumHeight(240)
        self.solveLog.setMaximumBlockCount(20000)
        self.solveLog.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # Plot
        self.canvas = MplCanvas(self, width=8, height=4.0, dpi=100)
        self.canvas.setMinimumHeight(300)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Buttons
        self.solveButton = QPushButton("SOLVE")
        self.clearAllButton = QPushButton("CLEAR ALL")
        self.buttonsLayout.addWidget(self.solveButton)
        self.buttonsLayout.addWidget(self.clearAllButton)
        self.solveButton.clicked.connect(self.solve)
        self.clearAllButton.clicked.connect(self.clearAll)
        for lf in self._all_lock_fields(): lf.connect_changed(self.solve)
        self.flowDirectionSelection.currentTextChanged.connect(self.solve)
        self.hxTypeSelection.currentTextChanged.connect(self._on_hx_type_changed)

        # Assemble grid
        self.grid.addLayout(self.titleLayout, 0, 0, 1, 3)
        self.grid.addLayout(self.unitsBar, 1, 0, 1, 3)
        self.left_col.addWidget(self._section_header("Hot Side"))
        self.left_col.addLayout(self.hotSideLayout)
        self.left_col.addWidget(self._hline())
        self.left_col.addWidget(self._section_header("Cold Side"))
        self.left_col.addLayout(self.coldSideLayout)
        self.left_col.addWidget(self._hline())
        self.left_col.addWidget(self._section_header("Core HX Properties"))
        self.left_col.addLayout(self.coreLayout)
        self.left_col.addWidget(self._hline())
        self.left_col.addWidget(self._section_header("Geometry"))
        # Mount the three geometry sub-containers; visibility is controlled by _on_hx_type_changed
        self.dimensionsLayout.addWidget(self.plateBox)
        self.dimensionsLayout.addWidget(self.stBox)
        self.dimensionsLayout.addWidget(self.acBox)
        self.left_col.addLayout(self.dimensionsLayout)
        self.left_col.addWidget(self._hline())
        self.left_col.addLayout(self.buttonsLayout)
        self.grid.addLayout(self.left_col, 2, 0, 2, 1)

        self.mid_col.addWidget(self._section_header("Derived / Read-only"))
        self.mid_col.addLayout(self.outputsLayout)
        self.grid.addLayout(self.mid_col, 2, 1)

        self.right_col.addLayout(self.solveLogHeaderRow)
        self.right_col.addWidget(self.solveLog)
        self.grid.addLayout(self.right_col, 2, 2)

        self.grid.addWidget(self.canvas, 3, 1, 1, 2)

        self.grid.setColumnStretch(0, 4)
        self.grid.setColumnStretch(1, 3)
        self.grid.setColumnStretch(2, 4)
        self.grid.setRowStretch(2, 1)
        self.grid.setRowStretch(3, 2)

        self._refresh_all_labels()
        self._on_hx_type_changed()

    # ─────────────────────────────────────────────────────────────────────
    # UI builders / helpers
    # ─────────────────────────────────────────────────────────────────────
    def _section_header(self, text: str) -> QLabel:
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        f = lab.font(); f.setBold(True); lab.setFont(f)
        return lab

    def _hline(self):
        line = QFrame(); line.setFrameShape(QFrame.Shape.HLine); line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _make_field_row(self, layout: QVBoxLayout, label_text: str, kind='line', placeholder="", solver_attr: str=None):
        """
        Create a (label + LockField) row wrapped in its own QWidget container.
        We store that container by solver_attr so we can show/hide entire rows cleanly.
        """
        row_widget = QWidget()
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        lab = QLabel(label_text)
        fld = LockField(kind=kind)
        fld.set_placeholder(placeholder)
        row.addWidget(lab, 2)
        row.addWidget(fld, 3)
        layout.addWidget(row_widget)
        self.label_map[lbl_key(label_text)] = lab
        if solver_attr:
            self.attr_for_label[lab] = solver_attr
            self.row_for_attr[solver_attr] = row_widget
        return fld

    def _all_lock_fields(self):
        # Return every input LockField we created for quick iteration (connect/clear)
        return [
            # Hot
            self._Thi, self._Tho, self._Pres_H_in, self._H_inlet_ID, self._H_outlet_ID,
            self._mdot_h, self._H_in_nm3_hr, self._H_Fluid,
            # Cold
            self._Tci, self._Tco, self._Pres_C_in, self._C_inlet_ID, self._C_outlet_ID,
            self._mdot_c, self._C_in_nm3_hr, self._C_Fluid,
            # Core
            self._q, self._q_max, self._UA, self._NTU, self._F_sub_T, self._epsilon,
            # Plate
            self._Plate_count, self._Plate_Distribution_Bias, self._Hot_Passes,
            self._Lv, self._Lh, self._Dp, self._pitch, self._t_m, self._b, self._phi,
            self._fouling_hot, self._fouling_cold,
            # Shell & Tube
            self._ST_hot_in_tube, self._ST_N_tubes, self._ST_N_tube_passes, self._ST_N_shell_passes,
            self._ST_Di, self._ST_Do, self._ST_L_pass, self._ST_k_wall, self._ST_Rf_i, self._ST_Rf_o, self._ST_h_o,
            # Air‑Cooled
            self._ACH_A_fr, self._ACH_V, self._ACH_sigma, self._ACH_Dh, self._ACH_alpha,
            self._ACH_Af_over_A, self._ACH_eta_f, self._ACH_eta_o_hot, self._ACH_jH, self._ACH_f_core
        ]

    # ─────────────────────────────────────────────────────────────────────
    # Labels / units
    # ─────────────────────────────────────────────────────────────────────
    def _refresh_all_labels(self):
        tU = self.temperatureUnits.currentText()
        pU = self.pressureUnits.currentText()
        dU = self.distanceUnits.currentText()
        eU = self.energyUnits.currentText()

        def set_lbl(key, unit):
            if key in self.label_map:
                lab = self.label_map[key]
                base = lab.text().split(',')[0]  # keep original label text
                lab.setText(f"{base}, {unit}" if unit else base)

        # Hot
        set_lbl(lbl_key("TEMP HOT IN"), tU)
        set_lbl(lbl_key("TEMP HOT OUT"), tU)
        set_lbl(lbl_key("HOT INLET PRESSURE"), pU)
        set_lbl(lbl_key("HOT INLET I.D."), dU)
        set_lbl(lbl_key("HOT OUTLET I.D."), dU)
        set_lbl(lbl_key("HOT MASS FLOW"), self.massFlowUnitsHot.currentText())
        set_lbl(lbl_key("HOT VOL FLOW (Nm^3/hr)"), "Nm^3/hr")

        # Cold
        set_lbl(lbl_key("TEMP COLD IN"), tU)
        set_lbl(lbl_key("TEMP COLD OUT"), tU)
        set_lbl(lbl_key("COLD INLET PRESSURE"), pU)
        set_lbl(lbl_key("COLD INLET I.D."), dU)
        set_lbl(lbl_key("COLD OUTLET I.D."), dU)
        set_lbl(lbl_key("COLD MASS FLOW"), self.massFlowUnitsCold.currentText())
        set_lbl(lbl_key("COLD VOL FLOW (Nm^3/hr)"), "Nm^3/hr")

        # Core
        set_lbl(lbl_key("HEAT TRANSFER RATE q"), eU)
        set_lbl(lbl_key("THEORETICAL MAX q"), eU)
        set_lbl(lbl_key("OVERALL UA"), "W/K")
        set_lbl(lbl_key("NTU"), "(dimensionless)")
        set_lbl(lbl_key("LMTD CORR FACTOR F"), "(dimensionless)")
        set_lbl(lbl_key("EFFECTIVENESS ε"), "(dimensionless)")

        # Geometry Labels
        set_lbl(lbl_key("PLATE COUNT"), "(count)")
        set_lbl(lbl_key("ODD CH ASSIGN (Bias)"), "")
        set_lbl(lbl_key("HOT PASSES"), "(count)")

        # Plate extended
        set_lbl(lbl_key("VERT PORT DIST L_v"), dU)
        set_lbl(lbl_key("HORIZ PORT DIST L_h"), dU)
        set_lbl(lbl_key("PORT DIAMETER D_p"), dU)
        set_lbl(lbl_key("PLATE PITCH p"), dU)
        set_lbl(lbl_key("PLATE THICKNESS t"), dU)
        set_lbl(lbl_key("MEAN CHANNEL GAP b"), dU)
        set_lbl(lbl_key("ENLARGEMENT φ"), "(dimensionless)")
        set_lbl(lbl_key("FOULING HOT"), "m²·K/W")
        set_lbl(lbl_key("FOULING COLD"), "m²·K/W")

        # Shell & Tube
        set_lbl(lbl_key("HOT IN TUBE? (1/0)"), "(0/1)")
        set_lbl(lbl_key("TUBES (count)"), "(count)")
        set_lbl(lbl_key("TUBE PASSES"), "(count)")
        set_lbl(lbl_key("SHELL PASSES"), "(count)")
        set_lbl(lbl_key("TUBE Di"), dU)
        set_lbl(lbl_key("TUBE Do"), dU)
        set_lbl(lbl_key("TUBE LENGTH/PASS"), dU)
        set_lbl(lbl_key("TUBE WALL k"), "W/m/K")
        set_lbl(lbl_key("FOULING (inside)"), "m²·K/W")
        set_lbl(lbl_key("FOULING (outside)"), "m²·K/W")
        set_lbl(lbl_key("h_o (shell side, if known)"), "W/m²/K")

        # Air‑Cooled / Compact
        set_lbl(lbl_key("FRONTAL AREA A_fr"), "m²")
        set_lbl(lbl_key("CORE VOLUME V"), "m³")
        set_lbl(lbl_key("FREE-FLOW RATIO σ"), "(dimensionless)")
        set_lbl(lbl_key("HYDR. DIAMETER Dh"), "m")
        set_lbl(lbl_key("AREA DENSITY α=A/V"), "1/m")
        set_lbl(lbl_key("FIN AREA FRACTION Af/A"), "(dimensionless)")
        set_lbl(lbl_key("FIN EFFICIENCY η_f (opt)"), "(dimensionless)")
        set_lbl(lbl_key("OVERALL SURF. EFF. η_o (opt)"), "(dimensionless)")
        set_lbl(lbl_key("j-FACTOR j_H"), "(dimensionless)")
        set_lbl(lbl_key("CORE friction factor f"), "(dimensionless)")

        # Update tooltips when labels/units change
        self._update_dependency_tooltips()

    # ─────────────────────────────────────────────────────────────────────
    # Unit changes for mdot
    # ─────────────────────────────────────────────────────────────────────
    def _on_hot_mdot_units_changed(self, new_unit: str):
        txt = self._mdot_h.text().strip()
        if not txt:
            self._prev_mdot_hot_units = new_unit
            return
        val = _float_or_none(txt)
        fluid = self._H_Fluid.text().strip() or "AIR"
        if val is not None:
            try:
                kgps = unit_convert(val, self._prev_mdot_hot_units, "kg/s", fluid)
                shown = unit_convert(kgps, "kg/s", new_unit, fluid)
                self._mdot_h.setText(str(round(shown, 6)))
            except Exception:
                pass
        self._prev_mdot_hot_units = new_unit
        self.solve()

    def _on_cold_mdot_units_changed(self, new_unit: str):
        txt = self._mdot_c.text().strip()
        if not txt:
            self._prev_mdot_cold_units = new_unit
            return
        val = _float_or_none(txt)
        fluid = self._C_Fluid.text().strip() or "AIR"
        if val is not None:
            try:
                kgps = unit_convert(val, self._prev_mdot_cold_units, "kg/s", fluid)
                shown = unit_convert(kgps, "kg/s", new_unit, fluid)
                self._mdot_c.setText(str(round(shown, 6)))
            except Exception:
                pass
        self._prev_mdot_cold_units = new_unit
        self.solve()

    # ─────────────────────────────────────────────────────────────────────
    # Show/hide fields by HX TYPE
    # ─────────────────────────────────────────────────────────────────────
    def _on_hx_type_changed(self):
        hx_type = (self.hxTypeSelection.currentText() or "PLATE").strip().upper()
        is_plate = (hx_type == "PLATE")
        is_st    = (hx_type == "SHELL & TUBE")
        is_ac    = (hx_type == "AIR-COOLED")

        self.plateBox.setVisible(is_plate)
        self.stBox.setVisible(is_st)
        self.acBox.setVisible(is_ac)

        self._update_dependency_tooltips()
        self.solve()

    # ─────────────────────────────────────────────────────────────────────
    # Solve
    # ─────────────────────────────────────────────────────────────────────
    def solve(self):
        """
        Build model from locked fields (fluids always included), defaults F_sub_T=1,
        call model.solve_hx(), update UI, log, and plot.
        """
        try:
            selected_type = self.hxTypeSelection.currentText().strip().lower()
            model = hx.HeatExchanger(
                Name=self.nameInput.text() or "HX",
                HX_Type=selected_type if selected_type else "plate",
                Counter_Flow=_to_bool(self.flowDirectionSelection.currentText()),
            )

            tU = self.temperatureUnits.currentText()
            pU = self.pressureUnits.currentText()
            dU = self.distanceUnits.currentText()
            eU_ui = self.energyUnits.currentText()
            eU_util = _energy_key_for_util(eU_ui)
            ui_known_attrs = set()

            # push helpers
            def push_num_locked(field: LockField, attr: str, from_unit: str, to_unit: str, fluid_for_mdot: str = None):
                if not field.is_locked(): return
                txt = field.text().strip()
                if not txt: return
                val = _float_or_none(txt)
                if val is None: return
                if fluid_for_mdot:
                    setattr(model, attr, unit_convert(val, from_unit, to_unit, fluid_for_mdot))
                else:
                    setattr(model, attr, unit_convert(val, from_unit, to_unit))
                ui_known_attrs.add(attr)

            def push_mdot_locked(field: LockField, attr: str, units_combo: QComboBox, fluid_field: LockField):
                if not field.is_locked(): return
                txt = field.text().strip()
                if not txt: return
                val = _float_or_none(txt)
                if val is None: return
                units = units_combo.currentText()
                fluid = (fluid_field.text().strip() or "AIR")
                setattr(model, attr, unit_convert(val, units, "kg/s", fluid))
                ui_known_attrs.add(attr)

            def push_nm3hr_locked(field: LockField, attr: str):
                if not field.is_locked(): return
                txt = field.text().strip()
                if not txt: return
                val = _float_or_none(txt)
                if val is None: return
                setattr(model, attr, val)
                ui_known_attrs.add(attr)

            def push_scalar_locked(field: LockField, attr: str):
                if not field.is_locked(): return
                txt = field.text().strip()
                if not txt: return
                val = _float_or_none(txt)
                if val is None: return
                setattr(model, attr, val)
                ui_known_attrs.add(attr)

            def push_str_always(field: LockField, attr: str):
                txt = field.text().strip()
                if not txt: return
                setattr(model, attr, txt)
                ui_known_attrs.add(attr)

            def push_power_locked(field: LockField, attr: str):
                if not field.is_locked(): return
                txt = field.text().strip()
                if not txt: return
                val = _float_or_none(txt)
                if val is None: return
                W = unit_convert(val, eU_util, "W")
                setattr(model, attr, W)
                ui_known_attrs.add(attr)

            # HOT
            push_num_locked(self._Thi, "_Thi", tU, "K")
            push_num_locked(self._Tho, "_Tho", tU, "K")
            push_num_locked(self._Pres_H_in, "_Pres_H_in", pU, "Pa")
            push_num_locked(self._H_inlet_ID, "_H_inlet_ID", dU, "mm")
            push_num_locked(self._H_outlet_ID, "_H_outlet_ID", dU, "mm")
            push_mdot_locked(self._mdot_h, "_mdot_h", self.massFlowUnitsHot, self._H_Fluid)
            push_nm3hr_locked(self._H_in_nm3_hr, "_H_in_nm3_hr")
            push_str_always(self._H_Fluid, "_H_Fluid")

            # COLD
            push_num_locked(self._Tci, "_Tci", tU, "K")
            push_num_locked(self._Tco, "_Tco", tU, "K")
            push_num_locked(self._Pres_C_in, "_Pres_C_in", pU, "Pa")
            push_num_locked(self._C_inlet_ID, "_C_inlet_ID", dU, "mm")
            push_num_locked(self._C_outlet_ID, "_C_outlet_ID", dU, "mm")
            push_mdot_locked(self._mdot_c, "_mdot_c", self.massFlowUnitsCold, self._C_Fluid)
            push_nm3hr_locked(self._C_in_nm3_hr, "_C_in_nm3_hr")
            push_str_always(self._C_Fluid, "_C_Fluid")

            # CORE / GEOMETRY common
            push_power_locked(self._q, "_q")
            push_power_locked(self._q_max, "_q_max")
            push_scalar_locked(self._UA, "_UA")
            push_scalar_locked(self._NTU, "_NTU")
            push_scalar_locked(self._epsilon, "_effectiveness_epsilon")
            push_scalar_locked(self._F_sub_T, "_F_sub_T")

            # HX Type specific
            if selected_type == "plate":
                push_scalar_locked(self._Plate_count, "_Plate_count")
                push_scalar_locked(self._Hot_Passes, "_Hot_Passes")
                push_str_always(self._Plate_Distribution_Bias, "_Plate_Distribution_Bias")
                # Extended geometry/fouling
                push_num_locked(self._Lv, "_Lv", dU, "m")
                push_num_locked(self._Lh, "_Lh", dU, "m")
                push_num_locked(self._Dp, "_Dp", dU, "m")
                push_num_locked(self._pitch, "_pitch", dU, "m")
                push_num_locked(self._t_m, "_t_m", dU, "m")
                # b (mean channel gap) is stored in mm in model
                if self._b.is_locked():
                    txt = self._b.text().strip()
                    if txt:
                        val = _float_or_none(txt)
                        if val is not None:
                            mm_val = unit_convert(val, dU, "mm")
                            setattr(model, "_mean_channel_gap", mm_val); ui_known_attrs.add("_mean_channel_gap")
                push_scalar_locked(self._phi, "_enlargement_phi")
                push_scalar_locked(self._fouling_hot, "_fouling_hot")
                push_scalar_locked(self._fouling_cold, "_fouling_cold")

            if selected_type == "shell & tube":
                push_scalar_locked(self._ST_hot_in_tube, "_ST_hot_in_tube")
                push_scalar_locked(self._ST_N_tubes, "_ST_N_tubes")
                push_scalar_locked(self._ST_N_tube_passes, "_ST_N_tube_passes")
                push_scalar_locked(self._ST_N_shell_passes, "_ST_N_shell_passes")
                push_num_locked(self._ST_Di, "_ST_Di", dU, "m")
                push_num_locked(self._ST_Do, "_ST_Do", dU, "m")
                push_num_locked(self._ST_L_pass, "_ST_L_pass", dU, "m")
                push_scalar_locked(self._ST_k_wall, "_ST_k_wall")
                push_scalar_locked(self._ST_Rf_i, "_ST_Rf_i")
                push_scalar_locked(self._ST_Rf_o, "_ST_Rf_o")
                push_scalar_locked(self._ST_h_o, "_ST_h_o")

            if selected_type == "air-cooled":
                push_scalar_locked(self._ACH_A_fr, "_ACH_A_fr")
                push_scalar_locked(self._ACH_V, "_ACH_V")
                push_scalar_locked(self._ACH_sigma, "_ACH_sigma")
                push_scalar_locked(self._ACH_Dh, "_ACH_Dh")
                push_scalar_locked(self._ACH_alpha, "_ACH_alpha")
                push_scalar_locked(self._ACH_Af_over_A, "_ACH_Af_over_A")
                push_scalar_locked(self._ACH_eta_f, "_ACH_eta_f")
                push_scalar_locked(self._ACH_eta_o_hot, "_ACH_eta_o_hot")
                push_scalar_locked(self._ACH_jH, "_ACH_jH")
                push_scalar_locked(self._ACH_f_core, "_ACH_f_core")

            # Ensure F_sub_T default=1.0
            if getattr(model, "_F_sub_T", None) is None:
                setattr(model, "_F_sub_T", 1.0)

            # Verbosity controls
            show_iter = self.actShowIter.isChecked()
            show_pp   = self.actPretty.isChecked()

            buf = io.StringIO()
            with redirect_stdout(buf):
                model.solve_hx(quiet=not show_iter)
                if show_pp:
                    print("-" * 60)
                    model.pretty_print()
            log_text = buf.getvalue()
            self._solve_count += 1
            if self.solveLog.toPlainText(): self.solveLog.appendPlainText("-"*80)
            self.solveLog.appendPlainText(f"Solve #{self._solve_count}")
            self.solveLog.appendPlainText(log_text)

            self._update_from_model(model, ui_known_attrs)

        except Exception as ex:
            QMessageBox.warning(self, "Solve error",
                                "Inputs are incomplete or inconsistent for solving.\n\n"
                                f"{ex}"
                                )
        finally:
            self._update_dependency_tooltips()

    # ─────────────────────────────────────────────────────────────────────
    # Read-back + Derived
    # ─────────────────────────────────────────────────────────────────────
    def _update_from_model(self, model: hx.HeatExchanger, ui_known_attrs: set):
        tU = self.temperatureUnits.currentText()
        pU = self.pressureUnits.currentText()
        dU = self.distanceUnits.currentText()

        def solved_flag(attr: str, field: LockField):
            return (attr not in ui_known_attrs) and (not field.is_locked())

        def set_text_if_solved(field: LockField, text: str, solved: bool):
            if solved:
                field.setText(text)
            field.mark_solved(solved)

        def show_num(field: LockField, attr: str, from_unit: str, to_unit: str, digits=6):
            val = getattr(model, attr, None)
            if val is None: return
            solved = solved_flag(attr, field)
            try: shown = unit_convert(val, from_unit, to_unit)
            except Exception: shown = val
            set_text_if_solved(field, str(round(shown, digits)), solved)

        def show_mdot(field: LockField, attr: str, units_combo: QComboBox, fluid_field: LockField, digits=6):
            val = getattr(model, attr, None)
            if val is None: return
            solved = solved_flag(attr, field)
            units = units_combo.currentText()
            fluid = (fluid_field.text().strip() or "AIR")
            try: shown = unit_convert(val, "kg/s", units, fluid)
            except Exception: shown = val
            set_text_if_solved(field, str(round(shown, digits)), solved)

        def show_nm3hr(field: LockField, attr: str, digits=6):
            val = getattr(model, attr, None)
            if val is None: return
            solved = solved_flag(attr, field)
            set_text_if_solved(field, str(round(val, digits)), solved)

        def show_plain(field: LockField, attr: str, digits=6):
            val = getattr(model, attr, None)
            if val is None: return
            solved = solved_flag(attr, field)
            set_text_if_solved(field, str(round(val, digits)), solved)

        def show_power(field: LockField, attr: str, digits=6):
            val = getattr(model, attr, None)
            if val is None: return
            solved = solved_flag(attr, field)
            try:
                shown = unit_convert(val, "W", _energy_key_for_util(self.energyUnits.currentText()))
            except Exception:
                shown = val
            set_text_if_solved(field, str(round(shown, digits)), solved)

        # HOT
        show_num(self._Thi, "_Thi", "K", tU)
        show_num(self._Tho, "_Tho", "K", tU)
        show_num(self._Pres_H_in, "_Pres_H_in", "Pa", pU)
        show_num(self._H_inlet_ID, "_H_inlet_ID", "mm", dU)
        show_num(self._H_outlet_ID, "_H_outlet_ID", "mm", dU)
        show_mdot(self._mdot_h, "_mdot_h", self.massFlowUnitsHot, self._H_Fluid)
        show_nm3hr(self._H_in_nm3_hr, "_H_in_nm3_hr")
        self._H_Fluid.mark_solved(False)

        # COLD
        show_num(self._Tci, "_Tci", "K", tU)
        show_num(self._Tco, "_Tco", "K", tU)
        show_num(self._Pres_C_in, "_Pres_C_in", "Pa", pU)
        show_num(self._C_inlet_ID, "_C_inlet_ID", "mm", dU)
        show_num(self._C_outlet_ID, "_C_outlet_ID", "mm", dU)
        show_mdot(self._mdot_c, "_mdot_c", self.massFlowUnitsCold, self._C_Fluid)
        show_nm3hr(self._C_in_nm3_hr, "_C_in_nm3_hr")
        self._C_Fluid.mark_solved(False)

        # CORE
        show_power(self._q, "_q")
        show_power(self._q_max, "_q_max")
        show_plain(self._UA, "_UA")
        show_plain(self._NTU, "_NTU")
        show_plain(self._epsilon, "_effectiveness_epsilon")
        show_plain(self._F_sub_T, "_F_sub_T")

        # Plate-only echoes
        show_plain(self._Plate_count, "_Plate_count")
        show_plain(self._Hot_Passes, "_Hot_Passes")
        bias = getattr(model, "_Plate_Distribution_Bias", None)
        if bias:
            self._Plate_Distribution_Bias.setText(str(bias))
            self._Plate_Distribution_Bias.mark_solved(False)

        # Derived labels (legacy)
        def fmt(x, u=None, nd=6):
            if x is None: return "—"
            try:
                s = round(float(x), nd)
            except Exception:
                return str(x)
            return f"{s} {u}" if u else f"{s}"

        self.out_labels["LMTD"].setText(
            f"LMTD: {fmt(getattr(model, '_lmtd', None), self.temperatureUnits.currentText())}"
        )
        self.out_labels["HOT Cp (in/out/avg)"].setText(
            f"H Cp (in/out/avg): "
            f"{fmt(getattr(model, '_H_I_Cp', None), 'J/kg/K')} / "
            f"{fmt(getattr(model, '_H_O_Cp', None), 'J/kg/K')} / "
            f"{fmt(getattr(model, '_H_avg_Cp', None), 'J/kg/K')}"
        )
        self.out_labels["COLD Cp (in/out/avg)"].setText(
            f"C Cp (in/out/avg): "
            f"{fmt(getattr(model, '_C_I_Cp', None), 'J/kg/K')} / "
            f"{fmt(getattr(model, '_C_O_Cp', None), 'J/kg/K')} / "
            f"{fmt(getattr(model, '_C_avg_Cp', None), 'J/kg/K')}"
        )
        self.out_labels["HOT HEAT CAPACITY RATE Ch"].setText(
            f"Ch: {fmt(getattr(model, '_Ch', None), 'W/K')}"
        )
        self.out_labels["COLD HEAT CAPACITY RATE Cc"].setText(
            f"Cc: {fmt(getattr(model, '_Cc', None), 'W/K')}"
        )
        self.out_labels["Cmin / Cmax / Cr"].setText(
            f"Cmin/Cmax/Cr: {fmt(getattr(model, '_Cmin', None), 'W/K')} / "
            f"{fmt(getattr(model, '_Cmax', None), 'W/K')} / "
            f"{fmt(getattr(model, '_Cr', None), '')}"
        )
        self.out_labels["HOT INLET/OUTLET VELOCITY"].setText(
            f"Hot v_in/v_out: {fmt(getattr(model, '_H_inlet_velocity', None), 'm/s')} / "
            f"{fmt(getattr(model, '_H_outlet_velocity', None), 'm/s')}"
        )
        self.out_labels["COLD INLET/OUTLET VELOCITY"].setText(
            f"Cold v_in/v_out: {fmt(getattr(model, '_C_inlet_velocity', None), 'm/s')} / "
            f"{fmt(getattr(model, '_C_outlet_velocity', None), 'm/s')}"
        )
        self.out_labels["Channels per pass (hot/cold)"].setText(
            f"Channels/pass (H/C): {fmt(getattr(model, '_channels_per_pass_hot', None), '')} / "
            f"{fmt(getattr(model, '_channels_per_pass_cold', None), '')}"
        )
        self.out_labels["Mass flow per channel (hot/cold)"].setText(
            f"ṁ per channel (H/C): {fmt(getattr(model, '_mdot_h_channel', None), 'kg/s')} / "
            f"{fmt(getattr(model, '_mdot_c_channel', None), 'kg/s')}"
        )

        # Plate-derived items
        self.out_labels["Dh (hydraulic diameter)"].setText(
            f"Dh: {fmt(getattr(model, '_Dh', None), 'm')}"
        )
        self.out_labels["G (mass velocity) H/C"].setText(
            f"G_h/G_c: {fmt(getattr(model, '_G_h', None), 'kg/m²/s')} / "
            f"{fmt(getattr(model, '_G_c', None), 'kg/m²/s')}"
        )
        self.out_labels["Re (hot/cold)"].setText(
            f"Re_h/Re_c: {fmt(getattr(model, '_Re_h', None), '')} / "
            f"{fmt(getattr(model, '_Re_c', None), '')}"
        )
        self.out_labels["h (hot/cold)"].setText(
            f"h_h/h_c: {fmt(getattr(model, '_h_h', None), 'W/m²/K')} / "
            f"{fmt(getattr(model, '_h_c', None), 'W/m²/K')}"
        )
        self.out_labels["U (calc)"].setText(
            f"U_calc: {fmt(getattr(model, '_U_calc', None), 'W/m²/K')}"
        )
        self.out_labels["ΔP hot / ΔP cold / ΔP total"].setText(
            f"ΔP: {fmt(getattr(model, '_dP_h', None), 'Pa')} / "
            f"{fmt(getattr(model, '_dP_c', None), 'Pa')} / "
            f"{fmt(getattr(model, '_dP_total', None), 'Pa')}"
        )
        self.out_labels["ε (from NTU, Cr)"].setText(
            f"ε_NTU: {fmt(getattr(model, '_epsilon_NTU', None), '')}"
        )
        self.out_labels["Tho/Tco from ε-NTU"].setText(
            f"Tho_eps/Tco_eps: {fmt(getattr(model, '_Tho_eps', None), self.temperatureUnits.currentText())} / "
            f"{fmt(getattr(model, '_Tco_eps', None), self.temperatureUnits.currentText())}"
        )
        self.out_labels["Entropy S_gen / N_s"].setText(
            f"S_gen/Ns: {fmt(getattr(model, '_S_gen', None), 'W/K')} / "
            f"{fmt(getattr(model, '_Ns', None), '')}"
        )

        # S&T and ACHE extras
        self.out_labels["UA (S&T)"].setText(
            f"UA_S&T: {fmt(getattr(model, '_ST_UA', None), 'W/K')}"
        )
        self.out_labels["U (S&T)"].setText(
            f"U_S&T: {fmt(getattr(model, '_ST_U', None), 'W/m²/K')}"
        )
        self.out_labels["Δp core (ACHE)"].setText(
            f"Δp_core: {fmt(getattr(model, '_ACH_dp_core', None), 'Pa')}"
        )

        # Plot
        self._draw_temperature_profile(model)

    # ─────────────────────────────────────────────────────────────────────
    # Plotting
    # ─────────────────────────────────────────────────────────────────────
    def _annotate_point(
        self, x: float, y: float, label: str, color: str,
        *, ha: str = "left", va: str = "center", dx: float = 0.015, dy: float = 0.0,
        fontsize: int = 9, marker: str = "o"
    ) -> None:
        ax = self.canvas.ax
        ax.plot([x], [y], marker=marker, color=color, markersize=5, zorder=5)
        ax.annotate(
            label, xy=(x, y), xytext=(x + dx, y + dy), textcoords="data", color=color,
            fontsize=fontsize, ha=ha, va=va,
            arrowprops=dict(arrowstyle="-", lw=0.8, color=color, shrinkA=0, shrinkB=2),
            zorder=6,
        )

    def _draw_temperature_profile(self, model) -> None:
        ax = self.canvas.ax; ax.cla()
        tU = self.temperatureUnits.currentText()
        def k2ui_s(Tk): return unit_convert(Tk, "K", tU) if Tk is not None else None
        def k2ui_a(Tarr): return np.array([unit_convert(float(v), "K", tU) for v in np.atleast_1d(Tarr)])

        # Inlet temps (always the inlets)
        ThiK = getattr(model, "_Thi", None)
        TciK = getattr(model, "_Tci", None)
        # Outlet temps: prefer locked/direct; else ε–NTU results
        ThoK = getattr(model, "_Tho", None) or getattr(model, "_Tho_eps", None)
        TcoK = getattr(model, "_Tco", None) or getattr(model, "_Tco_eps", None)
        Ch = getattr(model, "_Ch", None); Cc = getattr(model, "_Cc", None)
        UA = getattr(model, "_UA", None); NTU_m = getattr(model, "_NTU", None)
        is_counter = bool(getattr(model, "_Flow_Direction", True))

        # Fallback derive Ch/Cc from mdot*Cp when missing
        if Ch is None:
            mdot_h = getattr(model, "_mdot_h", None)
            HavgCp = getattr(model, "_H_avg_Cp", None) or getattr(model, "_H_I_Cp", None)
            if mdot_h is not None and HavgCp is not None: Ch = mdot_h * HavgCp
        if Cc is None:
            mdot_c = getattr(model, "_mdot_c", None)
            CavgCp = getattr(model, "_C_avg_Cp", None) or getattr(model, "_C_I_Cp", None)
            if mdot_c is not None and CavgCp is not None: Cc = mdot_c * CavgCp

        Thi = k2ui_s(ThiK); Tho = k2ui_s(ThoK); Tci = k2ui_s(TciK); Tco = k2ui_s(TcoK)

        def draw_axes(title=""):
            ax.set_title(f"Temperature Profiles — {title}" if title else "Temperature Profiles")
            ax.set_xlabel("Normalized length (x/L)")
            ax.set_ylabel(f"Temperature, {tU}")
            ax.grid(True)

        HOT = "#d62728"; COLD = "#1f77b4"
        have_hot = (Thi is not None and Tho is not None)
        have_cold = (Tci is not None and Tco is not None)
        x = np.linspace(0.0, 1.0, 200)
        endpoints_ready = bool(have_hot and have_cold)


        # Single-stream linear
        if have_hot and not have_cold:
            Th = Thi + (Tho - Thi) * x
            ax.plot(x, Th, color=HOT, label="Hot stream (Th)")
            draw_axes("Hot only")
            self._annotate_point(0.0, Th[0], f"Thi = {round(Th[0],3)} {tU}", HOT, ha="left")
            self._annotate_point(1.0, Th[-1], f"Tho = {round(Th[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
            ax.legend(loc="best"); self.canvas.draw(); return

        if have_cold and not have_hot:
            if is_counter:
                Tc = Tco + (Tci - Tco) * x; subtitle = "Cold only — Counterflow"
                l0, l1 = f"Tco = {round(Tc[0],3)} {tU}", f"Tci = {round(Tc[-1],3)} {tU}"
            else:
                Tc = Tci + (Tco - Tci) * x; subtitle = "Cold only — Parallel"
                l0, l1 = f"Tci = {round(Tc[0],3)} {tU}", f"Tco = {round(Tc[-1],3)} {tU}"
            ax.plot(x, Tc, color=COLD, label="Cold stream (Tc)")
            draw_axes(subtitle)
            self._annotate_point(0.0, Tc[0], l0, COLD, ha="left")
            self._annotate_point(1.0, Tc[-1], l1, COLD, ha="right", dx=-0.015)
            ax.legend(loc="best"); self.canvas.draw(); return

        # Physics-based ODE surrogate if UA/NTU available
        # If all endpoints are ready, draw straight lines that connect them.
        # Counterflow mapping of cold stream endpoints:
        #   x=0: (Thi, Tco),  x=1: (Tho, Tci)
        if endpoints_ready:
            if not is_counter:
                # parallel
                Th = Thi + (Tho - Thi) * x
                Tc = Tci + (Tco - Tci) * x
                ax.plot(x, Th, color=HOT, label="Hot stream (Th)")
                ax.plot(x, Tc, color=COLD, label="Cold stream (Tc)")
                draw_axes("Parallel")
                self._annotate_point(0.0, Th[0], f"Thi = {round(Th[0],3)} {tU}", HOT, ha="left")
                self._annotate_point(1.0, Th[-1], f"Tho = {round(Th[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
                self._annotate_point(0.0, Tc[0], f"Tci = {round(Tc[0],3)} {tU}", COLD, ha="left")
                self._annotate_point(1.0, Tc[-1], f"Tco = {round(Tc[-1],3)} {tU}", COLD, ha="right", dx=-0.015)
                ax.legend(loc="best"); self.canvas.draw(); return
            else:
                # counterflow
                Th = Thi + (Tho - Thi) * x
                Tc = Tco + (Tci - Tco) * x  # note swapped ends for cold line
                ax.plot(x, Th, color=HOT, label="Hot stream (Th)")
                ax.plot(x, Tc, color=COLD, label="Cold stream (Tc)")
                draw_axes("Counterflow")
                self._annotate_point(0.0, Th[0], f"Thi = {round(Th[0],3)} {tU}", HOT, ha="left")
                self._annotate_point(1.0, Th[-1], f"Tho = {round(Th[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
                self._annotate_point(0.0, Tc[0], f"Tco = {round(Tc[0],3)} {tU}", COLD, ha="left")
                self._annotate_point(1.0, Tc[-1], f"Tci = {round(Tc[-1],3)} {tU}", COLD, ha="right", dx=-0.015)
                ax.legend(loc="best"); self.canvas.draw(); return

        # Otherwise, use the physics-based ODE surrogate if UA/NTU are present.
        have_caps = (Ch and Ch > 0 and Cc and Cc > 0 and ThiK is not None and TciK is not None)
        NTU = None
        if NTU_m is not None and NTU_m > 0:
            NTU = float(NTU_m)
        elif UA and UA > 0 and have_caps:
            Cmin = min(Ch, Cc); NTU = UA / Cmin if Cmin > 0 else None

        if have_caps and NTU and NTU > 0:
            tau = NTU * x
            Cmin = min(Ch, Cc)
            alpha = Cmin / Ch; beta = Cmin / Cc
            if not is_counter:
                # parallel
                S = Ch * ThiK + Cc * TciK
                dT0 = ThiK - TciK
                dT_tau = dT0 * np.exp(-(alpha + beta) * tau)
                Th_tau = (S + Cc * dT_tau) / (Ch + Cc)
                Tc_tau = (S - Ch * dT_tau) / (Ch + Cc)
                Th_p = k2ui_a(Th_tau); Tc_p = k2ui_a(Tc_tau)
                ax.plot(x, Th_p, color=HOT, label="Hot stream (Th)")
                ax.plot(x, Tc_p, color=COLD, label="Cold stream (Tc)")
                draw_axes("Parallel (ODE)")
                self._annotate_point(0.0, Th_p[0], f"Thi = {round(Th_p[0],3)} {tU}", HOT, ha="left")
                self._annotate_point(1.0, Th_p[-1], f"Tho = {round(Th_p[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
                self._annotate_point(0.0, Tc_p[0], f"Tci = {round(Tc_p[0],3)} {tU}", COLD, ha="left")
                self._annotate_point(1.0, Tc_p[-1], f"Tco = {round(Tc_p[-1],3)} {tU}", COLD, ha="right", dx=-0.015)
            else:
                # counter (ODE fallback only when endpoints are not all available)
                # To avoid endpoint mismatch, drive the ODE between known inlets.
                # Simple exponential model for ΔT with constant UA/Ch/Cc:
                # ΔT(x) = (Thi - Tci)*exp(-(alpha+beta)*tau)
                dT0 = ThiK - TciK
                dT_tau = dT0 * np.exp(-(alpha + beta) * tau)
                # Enforce energy balance: mass-averaged line between inlets
                S = Ch * ThiK + Cc * TciK
                Th_tau = (S + Cc * dT_tau) / (Ch + Cc)
                Tc_tau = (S - Ch * dT_tau) / (Ch + Cc)
                Th_p = k2ui_a(Th_tau); Tc_p = k2ui_a(Tc_tau)
                ax.plot(x, Th_p, color=HOT, label="Hot stream (Th)")
                ax.plot(x, Tc_p, color=COLD, label="Cold stream (Tc)")
                draw_axes("Counter (ODE)")
                self._annotate_point(0.0, Th_p[0], f"Thi = {round(Th_p[0],3)} {tU}", HOT, ha="left")
                self._annotate_point(1.0, Th_p[-1], f"Tho = {round(Th_p[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
                self._annotate_point(0.0, Tc_p[0], f"Tco = {round(Tc_p[0],3)} {tU}", COLD, ha="left")
                self._annotate_point(1.0, Tc_p[-1], f"Tci = {round(Tc_p[-1],3)} {tU}", COLD, ha="right", dx=-0.015)
            ax.legend(loc="best"); self.canvas.draw(); return

        # Linear fallback
        subtitle = []
        if have_hot:
            Th = Thi + (Tho - Thi) * x
            ax.plot(x, Th, color=HOT, label="Hot stream (Th)")
            self._annotate_point(0.0, Th[0], f"Thi = {round(Th[0],3)} {tU}", HOT, ha="left")
            self._annotate_point(1.0, Th[-1], f"Tho = {round(Th[-1],3)} {tU}", HOT, ha="right", dx=-0.015)
        if have_cold:
            if is_counter:
                Tc = Tco + (Tci - Tco) * x; subtitle.append("Counterflow")
                l0, l1 = f"Tco = {round(Tc[0],3)} {tU}", f"Tci = {round(Tc[-1],3)} {tU}"
            else:
                Tc = Tci + (Tco - Tci) * x; subtitle.append("Parallel")
                l0, l1 = f"Tci = {round(Tc[0],3)} {tU}", f"Tco = {round(Tc[-1],3)} {tU}"
            ax.plot(x, Tc, color=COLD, label="Cold stream (Tc)")
            self._annotate_point(0.0, Tc[0], l0, COLD, ha="left")
            self._annotate_point(1.0, Tc[-1], l1, COLD, ha="right", dx=-0.015)
        draw_axes(" / ".join(subtitle) if subtitle else "Insufficient data")
        ax.legend(loc="best"); self.canvas.draw()

    # ─────────────────────────────────────────────────────────────────────
    # Clear
    # ─────────────────────────────────────────────────────────────────────
    def clearAll(self):
        for lf in self._all_lock_fields():
            lf.setText(""); lf.set_locked(False); lf.mark_solved(False)
        for lab in self.out_labels.values():
            lab.setText(lab.text().split(":")[0] + ": —")
        self.solveLog.clear()
        self.canvas.ax.cla()
        self.canvas.ax.set_title("")
        self.canvas.ax.grid(True)
        self.canvas.draw()
        self._update_dependency_tooltips()

    # ─────────────────────────────────────────────────────────────────────
    # Tooltip helpers: build known set and attach solver-generated HTML
    # ─────────────────────────────────────────────────────────────────────
    def _current_known_attributes(self, include_unlocked: bool = True) -> set:
        known = set()
        for lab, attr in self.attr_for_label.items():
            fld = getattr(self, attr, None)
            if not isinstance(fld, LockField):
                continue
            txt = (fld.text() or "").strip()
            if not txt:
                continue
            if include_unlocked or fld.is_locked():
                known.add(attr)
        return known

    def _build_ui_name_map(self) -> dict:
        name_map = {}
        for lab, attr in self.attr_for_label.items():
            base = lab.text().split(',')[0].strip()
            name_map[attr] = base
        return name_map

    def _update_dependency_tooltips(self) -> None:
        try:
            # ensure type gating matches current selection
            model_tmp = hx.HeatExchanger(HX_Type=self.hxTypeSelection.currentText().strip().lower(),
                                         Counter_Flow=_to_bool(self.flowDirectionSelection.currentText()))
            known = self._current_known_attributes(include_unlocked=True)
            ui_map = self._build_ui_name_map()
            for lab, attr in self.attr_for_label.items():
                html = model_tmp.dependency_tooltip(attr, known_attributes=known, ui_friendly_names=ui_map)
                lab.setToolTip(html)
        except Exception:
            pass
# ────────────────────────────────────────────────────────────────────────────────
# Entrypoint
# ────────────────────────────────────────────────────────────────────────────────
def main():
    app = QApplication([])
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()