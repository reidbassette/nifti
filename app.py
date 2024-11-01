# Compilation mode
# nuitka-project: --standalone
# nuitka-project: --onefile
# nuitka-project: --onefile-windows-splash-screen-image={MAIN_DIRECTORY}/nifti-splash-screen.png
# nuitka-project: --include-module=matplotlib
# nuitka-project: --include-package-data=matplotlib
# nuitka-project: --include-module=PIL
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/blowdown_diagram.jpg=blowdown_diagram.jpg
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/charging_diagram.png=charging_diagram.png
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/nifti-icon.png=nifti-icon.png
# nuitka-project: --include-data-files={MAIN_DIRECTORY}/orifice_diagram.png=orifice_diagram.png
# nuitka-project: --enable-plugin=pyqt6
# nuitka-project: --windows-console-mode=disable





import sys
import tempfile, os

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QTabWidget
)
from PyQt6.QtGui import QIcon
from bd_calc import BlowdownCalculator
from charging_calc import ChargingCalculator
from conversions import Conversions
from orifice_calc import OrificeTableWidget
from t_solve import thermalSolver

# Signal splash screen removal

if "NUITKA_ONEFILE_PARENT" in os.environ:
   splash_filename = os.path.join(
      tempfile.gettempdir(),
      "onefile_%d_splash_feedback.tmp" % int(os.environ["NUITKA_ONEFILE_PARENT"]),
   )

   if os.path.exists(splash_filename):
      os.unlink(splash_filename)

basedir = os.path.dirname(__file__)

# Subclass QMainWindow to customize your application's main window
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon(os.path.join(basedir,'nifti-icon.png')))
        self.title = 'NIFTI - Numerical Integration for Fluid and Thermal Initial value problems'
        self.left = 0
        self.top = 0
        self.width = 1200
        self.height = 900
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.table_widget = MyTableWidget(self)
        self.setCentralWidget(self.table_widget)
        
        self.show()


class MyTableWidget(QWidget):

    def __init__(self, parent):
        super(QWidget, self).__init__()

        self.tabs = QTabWidget()
        self.tab1 = OrificeTableWidget(self)
        self.tab2 = BlowdownCalculator(self)
        self.tab3 = ChargingCalculator(self)
        self.tab4 = Conversions(self)
        self.tab5 = thermalSolver(self)

        self.tabs.addTab(self.tab1, "Orifice Calculator")
        self.tabs.addTab(self.tab2, "Blowdown Calculator")
        self.tabs.addTab(self.tab3, "Charging Calculator")
        self.tabs.addTab(self.tab4, "Unit Conversions")
        self.tabs.addTab(self.tab5, "Thermal Calculator")
        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)



def main():
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
