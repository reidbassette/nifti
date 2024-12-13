
import sys
from utilities import*
from PyQt6.QtWidgets import(
     QApplication, 
     QLabel, 
     QPushButton, 
     QWidget, 
     QLineEdit, 
     QVBoxLayout, 
     QTreeWidget,
     QTreeWidgetItem,
     QMainWindow,
     QSpinBox,
     QComboBox,
     QGridLayout,
     QSizePolicy
     )

import thermal_solver as t
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

class MplCanvas(FigureCanvas):
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
            fig = Figure(figsize=(width, height), dpi = dpi) 
            self.ax = fig.add_subplot(111)
            # self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
            super(MplCanvas, self).__init__(fig) # Set the parent widget to make it behave like a QWidget

        
class MainWindow(QMainWindow): 

    def __init__(self): 

        super().__init__()
        self.title = 'Thermal Solver'
        self.setWindowTitle(self.title)
        self.table_widget = thermalSolver(self)
        self.setCentralWidget(self.table_widget)

        self.show()
class thermalSolver(QWidget): 
    
    def __init__(self,parent):
        super().__init__()
        super(QWidget, self).__init__(parent)
        self.nodes = {}
        self.paths = {}
        self.backendNodes = []
        self.backendPaths = []
        '''Layout definitions to be arranged in self.outerlayout'''    
        self.outerLayout = QGridLayout() #base layout
        self.outerLayout.setSpacing(1)
        self.nodeLayout = QVBoxLayout()
        self.attributeLayout = QVBoxLayout()
        self.pathLayout = QVBoxLayout()
        self.pathAttributeLayout = QVBoxLayout()
        self.timeEvalAndUnitLayout = QVBoxLayout()
        self.plotLayout = QVBoxLayout()
        self.unitLayout = QVBoxLayout()
        self.updateNodeLayout = QVBoxLayout()
        self.updatePathLayout = QVBoxLayout()

        #region LABELS 
        
        self.numberOfNodeLabel = QLabel("CURRENT NODE")
        self.temperatureLabel = QLabel("NODE TEMPERATURE, " + str(temperature_units[0]))
        self.mediumTypeLabel = QLabel("MEDIUM TYPE")
        self.mediumLabel = QLabel("MEDIUM")
        self.pressureLabel= QLabel("NODE PRESSURE, " + str(pressure_units[0])) 
        self.volumeLabel = QLabel("NODE VOLUME, " + str(volume_units[0])) 
        self.heatGeneratedLabel = QLabel("INTERNAL HEAT GENERATION, " + str(energy_units[0]))
        self.emissivityLabel= QLabel("EMISSIVITY")
        self.absorbivityLabel = QLabel("ABSORPTIVITY")
        self.isothermalLabel = QLabel("ISOTHERMAL")
        self.pressureUnitsLabel = QLabel("Pressure Units")
        self.temperatureUnitsLabel = QLabel("Temperature Units")
        self.volumeUnitsLabel = QLabel("Volume Units")
        self.nodeTreeTitle = QLabel("NODE TREE")
        self.pathTreeTitle = QLabel("PATH TREE")
        self.connectedNodesLabel = QLabel("CONNECTED NODES")
        self.nodeA = QLabel("NODE A")
        self.nodeB = QLabel("NODE B")
        self.heatTransferCoefficientLabel = QLabel("HEAT TRANSFER COEFFICIENT, W/m^2-K")
        self.heatTransferCoefficientLabel.setVisible(False)
        self.heatTransferAreaLabel = QLabel("HEAT TRANSFER AREA, " + str(area_units[0]))
        self.numberofPathsLabel =QLabel("CURRENT PATH")     
        self.timeInitialLabel = QLabel("TIME INITIAL,s")
        self.timeFinalLabel = QLabel("TIME DURATION, s")  
        self.dxLabel = QLabel("LENGTH OF PATH, " + str(distance_units[0]))
        self.dxLabel.setVisible(False)
        self.energyUnitsLabel = QLabel("Energy Units")
        self.areaUnitsLabel = QLabel("Area Units")
        self.densityUnitsLabel = QLabel("Density Units")
        self.distanceUnitsLabel = QLabel("Distance Units")
        self.timeUnitsLabel = QLabel("Time Units")
        self.heatTransferModeLabel = QLabel("HEAT TRANSFER MODE")
        self.ConductivityLabel = QLabel("NODE CONDUCTIVITY, W/m-K")
        self.ConductivityLabel.setVisible(False)
        self.DensityLabel = QLabel("NODE DENSITY, " + str(density_units[0]))
        self.DensityLabel.setVisible(False)
        self.SpecificHeatCapacityLabel = QLabel("NODE SPECIFIC HEAT CAPACITY, J/kg-K")
        self.SpecificHeatCapacityLabel.setVisible(False)

        #endregion LABELS

        #region UNIT DROPDOWN MENUS
        #All this region does is setup the dropdown menus for unit conversions. See the method calls in the UPDATE METHODS SECTION
        self.pressureUnits = QComboBox()
        self.pressureUnits.addItems(pressure_units)
        self.pressureUnits.currentTextChanged.connect(self.updatePressureUnits)

        self.temperatureUnits = QComboBox()
        self.temperatureUnits.addItems(temperature_units)
        self.temperatureUnits.currentTextChanged.connect(self.updateTemperatureUnits)
        
        self.volumeUnits = QComboBox()
        self.volumeUnits.addItems(volume_units)
        self.volumeUnits.currentTextChanged.connect(self.updateVolumeUnits)

        self.energyUnits = QComboBox()
        self.energyUnits.addItems(energy_units)
        self.energyUnits.currentTextChanged.connect(self.updateEnergyUnits)

        self.areaUnits = QComboBox()
        self.areaUnits.addItems(area_units)
        self.areaUnits.currentTextChanged.connect(self.updateAreaUnits)

        self.distanceUnits = QComboBox()
        self.distanceUnits.addItems(distance_units)
        self.distanceUnits.currentTextChanged.connect(self.updateDistanceUnits)

        self.timeUnits = QComboBox()
        self.timeUnits.addItems(["s", "min", "hr"])
        self.timeUnits.currentTextChanged.connect(self.updateTimeUnits)

        self.densityUnits = QComboBox()
        self.densityUnits.addItems(density_units)
        self.densityUnits.currentTextChanged.connect(self.updateDensityUnits)
        #endregion UNIT DROPDOWN MENUS
        
        #region OUTPUT TEXT PRINTING 
        self.outputText = QLabel()
        self.outputText.setVisible(False)
        #endregion OUTPUT TEXT PRINTING

        #region NODE ATTRIBUTE SELECTIONS
        #This region sets up the node attribute selection 
        self.currentNodeSelection = QSpinBox()
        self.currentNodeSelection.setRange(1,1)

        self.temperatureInput = QLineEdit()
        self.temperatureInput.setPlaceholderText("300 ")

        self.mediumTypeSelection = QComboBox()
        self.mediumTypeSelection.addItems(["FLUID","SOLID"])
        self.mediumTypeSelection.setCurrentIndex(-1)
        self.mediumTypeSelection.setPlaceholderText("Select")
        #Automatically toggles the SOLID or FLUID mediums depending on the medium type that was selected
        self.mediumTypeSelection.currentTextChanged.connect(self.changeMediumSelectionItems)
        self.mediumTypeSelection.currentTextChanged.connect(self.toggleSolidProperties)
        

        self.mediumSelection = QComboBox()
        self.mediumSelection.setPlaceholderText("Select")
        #Sets Custom property boxes visible if the custom material entry is selected. 
        self.mediumSelection.currentTextChanged.connect(self.customMaterialEntry)
        
        self.pressureInput = QLineEdit()
        self.pressureInput.setPlaceholderText("200")

        self.volumeInput = QLineEdit()
        self.volumeInput.setPlaceholderText("10")

        self.heatGeneratedInput = QLineEdit()
        self.heatGeneratedInput.setPlaceholderText("100")

        self.emissivityInput = QLineEdit()
        self.emissivityInput.setPlaceholderText("0.0")

        self.absorbivityInput = QLineEdit()
        self.absorbivityInput.setPlaceholderText("0.0")

        self.isothermalInput = QComboBox()
        self.isothermalInput.addItems(["True", "False"])
        self.isothermalInput.setCurrentIndex(1)
        #defaults to false, however if isothermal condiition is changed, update attribute selections
        self.isothermalInput.currentTextChanged.connect(self.toggleIsothermal)

        self.ConductivityInput = QLineEdit()
        self.ConductivityInput.setPlaceholderText('13')
        self.ConductivityInput.setVisible(False)

        self.DensityInput = QLineEdit()
        self.DensityInput.setPlaceholderText('1000')
        self.DensityInput.setVisible(False)

        self.SpecificHeatCapacityInput = QLineEdit()
        self.SpecificHeatCapacityInput.setPlaceholderText('500')
        self.SpecificHeatCapacityInput.setVisible(False)
        #endregion NODE ATTRIBUTE SELECTIONS

        #region PATH ATTRIBUTE SELECTIONS
        self.currentPathSelection = QSpinBox()
        self.currentPathSelection.setRange(1, 20)

        self.heatTransferModeInput = QComboBox()
        self.heatTransferModeInput.addItems(["CONVECTION", "CONDUCTION"])
        self.heatTransferModeInput.setCurrentIndex(-1)
        self.heatTransferModeInput.setPlaceholderText("Select")
        #If heat transfer mode input is switched between conduction and convection, update available properties accordingly
        self.heatTransferModeInput.currentTextChanged.connect(self.toggleHeatTransferProperties)
        self.heatTransferCoefficientInput = QLineEdit()
        self.heatTransferCoefficientInput.setPlaceholderText("10")
        self.heatTransferCoefficientInput.setVisible(False)

        self.heatTransferAreaInput = QLineEdit()
        self.heatTransferAreaInput.setPlaceholderText("1e6")

        self.dxInput = QLineEdit()
        self.dxInput.setPlaceholderText(".01")
        self.dxInput.setVisible(False)
        #endregion PATH ATTRIBUTE SELECTIONS

        #region TIME INPUT 
        self.timeDurationInput = QLineEdit()
        self.timeDurationInput.setPlaceholderText("3600")
        #endregion TIME INPUT
        
        #region NODE TREE
        self.nodeTree = QTreeWidget()
        self.nodeTree.setColumnCount(3)
        self.nodeTree.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        self.nodeTree.setColumnWidth(0, 150)
        self.nodeTree.setHeaderLabels(["ATTRIBUTES", "VALUES", "UNITS"])
        self.nodeTreeHeader = self.nodeTree.header()
        self.nodeTreeHeader.setSectionsMovable(False)
        self.nodeLayout.addWidget(self.nodeTreeTitle,alignment=Qt.AlignmentFlag.AlignHCenter)
        self.nodeLayout.addWidget(self.nodeTree)
        self.nodeTree.itemClicked.connect(self.updateNodeEntries)
        #endregion NODE TREE

        #region PATH TREE
        self.pathTree = QTreeWidget()
        self.pathTree.setColumnCount(3)
        self.pathTree.setColumnWidth(0,150) 
        self.pathTree.setHeaderLabels(["ATTRIBUTES", "VALUES", "UNITS"])
        self.pathTreeHeader = self.pathTree.header()
        self.pathTreeHeader.setSectionsMovable(False)
        self.pathLayout.addWidget(self.pathTreeTitle,alignment=Qt.AlignmentFlag.AlignHCenter)
        self.pathLayout.addWidget(self.pathTree)
        self.pathTree.itemClicked.connect(self.updatePathEntries)

        #endregion PATH TREE

        #region NODE AND PATH SELECTIONS
        self.connectedNodesSelection1 = QComboBox()
        self.connectedNodesSelection2 = QComboBox()
        self.connectedNodesSelection1.setCurrentIndex(-1)
        self.connectedNodesSelection2.setCurrentIndex(-1) 
        #if a node item is changed, update the possible selections of the other box accordingly. The same node cannot be selected twice.
        self.connectedNodesSelection1.currentIndexChanged.connect(self.changeNodeSelectionItems)
        #endregion NODE AND PATH SELECTIONS

        #region SET NODE ATTRIBUTE INPUT LAYOUT

        self.attributeLayout.addWidget(self.numberOfNodeLabel)
        self.attributeLayout.addWidget(self.currentNodeSelection)

        self.attributeLayout.addWidget(self.isothermalLabel)
        self.attributeLayout.addWidget(self.isothermalInput)
        
        self.attributeLayout.addWidget(self.temperatureLabel)
        self.attributeLayout.addWidget(self.temperatureInput)

        self.attributeLayout.addWidget(self.mediumTypeLabel)
        self.attributeLayout.addWidget(self.mediumTypeSelection)
        self.attributeLayout.addWidget(self.mediumLabel)
        self.attributeLayout.addWidget(self.mediumSelection)
        
        self.attributeLayout.addWidget(self.DensityLabel)
        self.attributeLayout.addWidget(self.DensityInput)
        
        self.attributeLayout.addWidget(self.ConductivityLabel)
        self.attributeLayout.addWidget(self.ConductivityInput)

        self.attributeLayout.addWidget(self.SpecificHeatCapacityLabel)
        self.attributeLayout.addWidget(self.SpecificHeatCapacityInput)

        self.attributeLayout.addWidget(self.volumeLabel)
        self.attributeLayout.addWidget(self.volumeInput)

        self.attributeLayout.addWidget(self.pressureLabel)
        self.attributeLayout.addWidget(self.pressureInput)
        
        self.attributeLayout.addWidget(self.heatGeneratedLabel)
        self.attributeLayout.addWidget(self.heatGeneratedInput)
        
        self.attributeLayout.addWidget(self.emissivityLabel)
        self.attributeLayout.addWidget(self.emissivityInput)
        
        self.attributeLayout.addWidget(self.absorbivityLabel)
        self.attributeLayout.addWidget(self.absorbivityInput)
        #endregion SET NODE ATTRIBUTE INPUT LAYOUT
     
        #region SET PATH ATTRIBUTE INPUT LAYOUT
        self.pathAttributeLayout.addWidget(self.numberofPathsLabel)
        self.pathAttributeLayout.addWidget(self.currentPathSelection)

        self.pathAttributeLayout.addWidget(self.heatTransferModeLabel)
        self.pathAttributeLayout.addWidget(self.heatTransferModeInput)

        self.pathAttributeLayout.addWidget(self.heatTransferAreaLabel)
        self.pathAttributeLayout.addWidget(self.heatTransferAreaInput)

        self.pathAttributeLayout.addWidget(self.heatTransferCoefficientLabel) 
        self.pathAttributeLayout.addWidget(self.heatTransferCoefficientInput)

        self.pathAttributeLayout.addWidget(self.dxLabel)
        self.pathAttributeLayout.addWidget(self.dxInput)

        self.pathAttributeLayout.addWidget(self.connectedNodesLabel)     
        self.pathAttributeLayout.addWidget(self.nodeA)
        self.pathAttributeLayout.addWidget(self.connectedNodesSelection1)
        self.pathAttributeLayout.addWidget(self.nodeB)
        self.pathAttributeLayout.addWidget(self.connectedNodesSelection2)
        #endregion SET PATH ATTRIBUTE INPUT LAYOUT
        
        #region SET TIME INPUT LAYOUT
        
        self.timeEvalAndUnitLayout.addWidget(self.pressureUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.pressureUnits)
        self.timeEvalAndUnitLayout.addWidget(self.temperatureUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.temperatureUnits)
        self.timeEvalAndUnitLayout.addWidget(self.densityUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.densityUnits)
        self.timeEvalAndUnitLayout.addWidget(self.volumeUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.volumeUnits)
        self.timeEvalAndUnitLayout.addWidget(self.energyUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.energyUnits)
        self.timeEvalAndUnitLayout.addWidget(self.areaUnitsLabel) 
        self.timeEvalAndUnitLayout.addWidget(self.areaUnits)
        self.timeEvalAndUnitLayout.addWidget(self.distanceUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.distanceUnits)
        self.timeEvalAndUnitLayout.addWidget(self.timeUnitsLabel)
        self.timeEvalAndUnitLayout.addWidget(self.timeUnits)
        
        # self.timeEvalAndUnitLayout.addWidget(self.timeInitialLabel)
        # self.timeEvalAndUnitLayout.addWidget(self.timeInitialInput)
        self.timeEvalAndUnitLayout.addWidget(self.timeFinalLabel)
        self.timeEvalAndUnitLayout.addWidget(self.timeDurationInput)
        self.timeEvalAndUnitLayout.addWidget(self.outputText)
        #endregion SET TIME INPUT LAYOUT

        #region PLOT LAYOUT
        self.canvas = MplCanvas(self,width=5, height=2, dpi = 100)
        self.canvas.ax.set_title("Node Temperature vs Time")
        self.canvas.ax.grid(True)
        self.plotLayout.addWidget(self.canvas)
        
        #endregion PLOT LAYOUT
        
        #region BUTTONS
        #If a button is pressed, update the corresponing Node, solve, or clear the app data
        self.updateNodeButton = QPushButton("Update Node")

        self.updateNodeButton.pressed.connect(self.updateNode)
        self.updateNodeButton.pressed.connect(self.setNodeSelection)
        self.updateNodeLayout.addWidget(self.updateNodeButton)

        self.removeNodeButton = QPushButton("Remove Node")
        self.removeNodeButton.pressed.connect(self.removeNode)
        self.updateNodeLayout.addWidget(self.removeNodeButton)

        self.updatePathButton = QPushButton("Update Path")
        self.updatePathButton.pressed.connect(self.updatePath)

        self.removePathButton = QPushButton("Remove Path")  
        self.removePathButton.pressed.connect(self.removePath)
    
        self.updatePathLayout.addWidget(self.updatePathButton)
        self.updatePathLayout.addWidget(self.removePathButton)

        self.solveButton = QPushButton("SOLVE")
        self.timeEvalAndUnitLayout.addWidget(self.solveButton)
        self.solveButton.pressed.connect(self.solve)

        self.clearAllButton = QPushButton("CLEAR ALL")
        self.clearAllButton.pressed.connect(self.clearAll)
        self.plotLayout.addWidget(self.clearAllButton)

        #endregion BUTTONS

        #region SET OUTER LAYOUT
        self.outerLayout.addLayout(self.attributeLayout, 0,0)
        self.outerLayout.addLayout(self.nodeLayout,0,1,2,1)
        self.outerLayout.addLayout(self.updateNodeLayout,1,0)
        self.outerLayout.addLayout(self.pathLayout, 2, 1,2,1)
        self.outerLayout.addLayout(self.updatePathLayout,3,0)
        self.outerLayout.addLayout(self.pathAttributeLayout,2,0)
        self.outerLayout.addLayout(self.timeEvalAndUnitLayout, 0,2)
        self.outerLayout.addLayout(self.plotLayout,1,2,3,1)
        
        self.setLayout(self.outerLayout)
        #endregion SET OUTER LAYOUT


    #region METHODS
    '''Set Node Selection based on foregoing Node Selection for path (i.e sets selection for Node B)'''
    def setNodeSelection(self): 
        #Clear selected Nodes
        self.connectedNodesSelection1.clear()

        top_level_count = self.nodeTree.topLevelItemCount()
       
        self.connectedNodesSelection1.addItem(self.nodeTree.topLevelItem(0).text(0)) if self.nodeTree.topLevelItemCount() != 0 else ''
        
        for i in range(top_level_count): 
            node_name = self.nodeTree.topLevelItem(i).text(0)
            '''If the current iteration item is equal to a pre-existing node selection'''
            if self.connectedNodesSelection1.itemText(i) == node_name or top_level_count == 0:
                pass
            else:
                self.connectedNodesSelection1.addItem(node_name)

    '''Add or update node in node tree'''
    #region NODE AND PATH UPDATE METHODS
    def updateNode(self):
        try:
            if self.nodeTree.topLevelItemCount() == 15:
                self.outputText.setVisible(True)
                self.outputText.setText("Maximum number of nodes exceeded (15)")
                return 1
            items = []
            self.nodeTree.clear()
            #Sets attribute list depending on node conditions.
            if self.mediumTypeSelection.currentText() == 'SOLID' and self.isothermalInput.currentText() == 'True': 
                attributes = [
                    "T," + (self.temperatureInput.text()) +':'+self.temperatureUnits.currentText(), 
                    "MEDIUM,"+self.mediumSelection.currentText()+':', 
                    "EMISSIVITY," + (self.emissivityInput.text()) +':',
                    "ABSORPTIVITY,"+(self.emissivityInput.text()) +':',#Kirchoff's Law
                    "ISOTHERMAL," + (self.isothermalInput.currentText()) + ':',
                    "DENSITY," + (self.DensityInput.text()) + ':' + self.densityUnits.currentText() if self.mediumSelection.currentText() == 'CUSTOM' else '',
                    "THERMAL CONDUCTIVTIY," + (self.ConductivityInput.text()) + ':' + 'W/m-K' if self.mediumSelection.currentText() == 'CUSTOM' else '',
                    "SPECIFIC HEAT CAPACITY," + (self.SpecificHeatCapacityInput.text()) + ':' + 'J/kg-K' if self.mediumSelection.currentText() == 'CUSTOM' else '',
                ]
            elif self.mediumTypeSelection.currentText() == 'SOLID' and self.isothermalInput.currentText() == 'False':
                attributes = [
                    "T," + (self.temperatureInput.text()) +':'+self.temperatureUnits.currentText(), 
                    "MEDIUM,"+self.mediumSelection.currentText()+':', 
                    "EMISSIVITY," + (self.emissivityInput.text()) +':',
                    "ABSORPTIVITY,"+(self.absorbivityInput.text()) +':',
                    "ISOTHERMAL," + (self.isothermalInput.currentText()) + ':',
                    "DENSITY," + (self.DensityInput.text()) + ':' + self.densityUnits.currentText() if self.mediumSelection.currentText() == 'CUSTOM' else '',
                    "THERMAL CONDUCTIVTIY," + (self.ConductivityInput.text()) + ':' + 'W/m-K' if self.mediumSelection.currentText() == 'CUSTOM' else '',
                    "SPECIFIC HEAT CAPACITY," + (self.SpecificHeatCapacityInput.text()) + ':' + 'J/kg-K' if self.mediumSelection.currentText() == 'CUSTOM' else '',
                    "VOLUME," + (self.volumeInput.text()) +':'+ self.volumeUnits.currentText(), 
                    "HEAT GENERATED," + (self.heatGeneratedInput.text()) + ':'+self.energyUnits.currentText(), 
                ]
            elif self.mediumTypeSelection.currentText() == 'FLUID' and self.isothermalInput.currentText() == 'False': 
                attributes = [
                    "T," + (self.temperatureInput.text()) + ':' + self.temperatureUnits.currentText(), 
                    "MEDIUM," + self.mediumSelection.currentText() + ':', 
                    "VOLUME," + (self.volumeInput.text()) + ':' + self.volumeUnits.currentText(),
                    "HEAT GENERATED," + (self.heatGeneratedInput.text()) + ':' + self.energyUnits.currentText(),
                    "PRESSURE,"+ (self.pressureInput.text()) + ':'+self.pressureUnits.currentText(),
                    "ISOTHERMAL," + (self.isothermalInput.currentText()) + ':',
                ]    
            elif self.mediumTypeSelection.currentText() == 'FLUID' and self.isothermalInput.currentText() == 'True': 
                attributes = [
                    "T," + (self.temperatureInput.text()) + ':' + self.temperatureUnits.currentText(), 
                    "MEDIUM," + self.mediumSelection.currentText() + ':', 
                    "PRESSURE,"+ (self.pressureInput.text()) + ':'+self.pressureUnits.currentText(),
                    "ISOTHERMAL," + (self.isothermalInput.currentText()) + ':',
                ]

            '''Stores node in backend nodes and updates nodes using identifier attribute'''
            self.backendNodes = [node for node in self.backendNodes if node.identifier != self.currentNodeSelection.value()]

            #region Attributes
            T = unit_convert(float(self.temperatureInput.text()), self.temperatureUnits.currentText(),"K") 
            medium = self.mediumSelection.currentText()
            medium_type = self.mediumTypeSelection.currentText()
            Pressure = unit_convert(float(self.pressureInput.text()), self.pressureUnits.currentText(), "Pa") if medium_type == 'FLUID' else 0.0
            Eg = unit_convert(float(self.heatGeneratedInput.text()), self.energyUnits.currentText(), "W") if self.isothermalInput.currentText() == 'False' else 0.0
            V = unit_convert(float(self.volumeInput.text()), self.volumeUnits.currentText(), "m^3") if self.isothermalInput.currentText() == 'False' else 0.0
            e = float(self.emissivityInput.text()) if medium_type == 'SOLID' else 0.0
            a = float(self.absorbivityInput.text()) if medium_type == 'SOLID' and self.isothermalInput.currentText() == 'False' else 0.0
            isothermal= eval(self.isothermalInput.currentText()) 
            identifier=self.currentNodeSelection.value()
            density=unit_convert(float(self.DensityInput.text()), self.densityUnits.currentText(), 'kg/m^3') if medium == 'CUSTOM' else 0.0
            k = float(self.ConductivityInput.text()) if medium == 'CUSTOM' else 0.0
            c = float(self.SpecificHeatCapacityInput.text())if medium == 'CUSTOM' else 0.0

            if self.mediumTypeSelection.currentText() == 'SOLID': 
                self.backendNodes.append(t.Node(
                    T = T,
                    medium= medium,
                    medium_type=medium_type,
                    Eg = Eg,
                    V= V if self.isothermalInput.currentText() == "False" else 0.0, 
                    e = e,
                    a = a if self.isothermalInput.currentText() == 'False' else e,
                    isothermal= isothermal,
                    identifier=identifier,
                    density=density,
                    k = k,
                    c = c
                    ))
                
            elif self.mediumTypeSelection.currentText() == 'FLUID':
                self.backendNodes.append(t.Node(
                    T = T,
                    medium=medium,
                    medium_type=medium_type,
                    Eg = Eg,
                    Pressure= Pressure,
                    V= V if self.isothermalInput.currentText() == "False" else 0.0, 
                    e = e,
                    a = a,
                    isothermal= isothermal,
                    identifier=identifier
                    ))

            #Create Node Dictionary
            self.nodes['Node ' + str(self.currentNodeSelection.value())] = attributes
            self.nodes = dict(sorted(self.nodes.items()))
            print(self.nodes)
            print(self.backendNodes)
            for key,values in self.nodes.items():
                if key == '': 
                    pass
                else:
                    nodeAssignment = QTreeWidgetItem([key])
                for value in values:
                    if value == '' or value == 0.0:
                        pass
                    else:
                        label = value.split(",")[0]
                        val = value.split(':')[0].split(',')[-1]
                        units = value.split(':')[-1]
                        child = QTreeWidgetItem([label,val,units])
                        nodeAssignment.addChild(child)
                items.append(nodeAssignment)
        
            '''if node exists in an already determined path (i.e in path tree), then update path(s) with current node'''
            for node in self.backendNodes:
                if node.identifier == int(self.currentNodeSelection.text()): #grabs the node being updated
                    updatedNode = node
            for i in range(len(self.backendPaths)):
                node1 = self.backendPaths[i].nodeA
                node2 = self.backendPaths[i].nodeB
                if updatedNode != node1 and updatedNode.identifier == node1.identifier:
                    self.backendPaths[i].nodeA = updatedNode
                elif updatedNode != node2 and updatedNode.identifier == node2.identifier:
                    self.backendPaths[i].nodeB = updatedNode
            self.outputText.setVisible(True)
            self.outputText.setText(f"Node {self.currentNodeSelection.text()} has been updated.")
            self.currentNodeSelection.setMaximum(int(self.currentNodeSelection.maximum())+1)
            self.currentNodeSelection.setValue(self.currentNodeSelection.value() + 1)
            self.nodeTree.insertTopLevelItems(0, items)
            self.nodeTree.resizeColumnToContents(2)
           
        except Exception as e:
            self.outputText.setVisible(True)
            self.outputText.setText("Something went wrong with node update. Check node inputs." + str(e))

    def updatePath(self): 
        try:
            '''First checks if path already exists AND is not updating pre-existing path'''
            nume1 = self.connectedNodesSelection1.currentText().split(' ')[-1]
            denom1 = self.connectedNodesSelection2.currentText().split(' ')[-1]
            frac1 = nume1 + '/' + denom1
            frac1inverse = denom1 + '/' + nume1
            self.outputText.setVisible(True)
            
            print(self.pathTree.topLevelItemCount())
            for i in range(self.pathTree.topLevelItemCount()):
                nume2 = self.paths[self.pathTree.topLevelItem(i).text(0)][0].split(' ')[-1].split(':')[0]
                denom2 = self.paths[self.pathTree.topLevelItem(i).text(0)][1].split(' ')[-1].split(':')[0]   
                frac2 = nume2 + '/' + denom2
                if (self.pathTree.topLevelItem(i).text(0).split(' ')[-1] != self.currentPathSelection.text()) and (frac1 == frac2 or frac1inverse == frac2):  
                    self.outputText.setText("Path already exists.")
                    return 1
                
            self.pathTree.clear()
            attributes =[ 
                "Node A," + self.connectedNodesSelection1.currentText()+":",
                "Node B," + self.connectedNodesSelection2.currentText()+':',
                "Area," + self.heatTransferAreaInput.text()+':'+ self.areaUnits.currentText(),
                "dx," + self.dxInput.text()+':' +self.distanceUnits.currentText() if self.heatTransferModeInput.currentText() == "CONDUCTION" else '',
                "h," + self.heatTransferCoefficientInput.text() +':'+ 'W/m^2K' if self.heatTransferModeInput.currentText() == "CONVECTION" else '',
                f"{self.heatTransferModeInput.currentText()}," + ':'
            ]
            self.backendPaths = [path for path in self.backendPaths if path.identifier != self.currentPathSelection.value()]
            
            '''Look for connected nodes using identifier'''
            for i in range(len(self.backendNodes)):
                if self.backendNodes[i].identifier == int(self.connectedNodesSelection1.currentText().split(" ")[-1]):
                    node1 = self.backendNodes[i]
                elif self.backendNodes[i].identifier == int(self.connectedNodesSelection2.currentText().split(" ")[-1]):
                    node2 = self.backendNodes[i]
        
            self.backendPaths.append(t.Path(
                nodeA= node1,
                nodeB= node2,
                Area = unit_convert(
                    float(self.heatTransferAreaInput.text()),
                    self.areaUnits.currentText(),
                    "m^2",
                ) if self.heatTransferAreaInput.text() != '' else 0.01,
                h = float(self.heatTransferCoefficientInput.text()) if self.heatTransferCoefficientInput.text() != '' else 0.0, 
                dx = unit_convert(
                    float(self.dxInput.text()),
                    self.distanceUnits.currentText(),
                    'm'
                ) if self.dxInput.text() != '' else 1.0,
                identifier= self.currentPathSelection.value()
            ))
           
            self.paths['Path ' + str(self.currentPathSelection.value())] = attributes
            self.paths = dict(sorted(self.paths.items()))
            items = []
            for key,values in self.paths.items():
                    if key == '': 
                        pass
                    else:
                        pathAssignment = QTreeWidgetItem([key])
                    for value in values:
                        if value == ''or value == 0.0:
                            pass
                        else:
                            label = value.split(",")[0]
                            val = value.split(':')[0].split(',')[-1]
                            units = value.split(':')[-1]
                            child = QTreeWidgetItem([label,val,units])
                            pathAssignment.addChild(child)
                    items.append(pathAssignment)
            self.outputText.setVisible(True)
            self.outputText.setText(f"Path {self.currentPathSelection.text()} has been updated.")
            self.currentPathSelection.setValue(self.currentPathSelection.value() + 1)
            self.pathTree.insertTopLevelItems(0, items)
            print(self.paths)
            print(self.backendPaths)

        except Exception: 
            self.outputText.setText("Something went wrong with path inputs.")   

    #Sets Selection Medium based on medium type selection
    def changeMediumSelectionItems(self): 
        self.mediumSelection.clear()
        if self.mediumTypeSelection.currentText() == "SOLID": 
            self.mediumSelection.addItems(["SS316", "Al6061", "Al7075T6","CUSTOM"])
            self.mediumSelection.setCurrentIndex(-1)

        elif self.mediumTypeSelection.currentText() == "FLUID":
            self.mediumSelection.addItems(fluid_names)
            self.mediumSelection.setCurrentIndex(-1)

    #Change connected node selection items in 2nd connected node box
    def changeNodeSelectionItems(self): 
        self.connectedNodesSelection2.clear()
        for i in range(self.nodeTree.topLevelItemCount()):
            #If selected item in node A selection box is equal to current topLevelItem iteration or the node tree count is 0. ignore 
            if self.connectedNodesSelection1.currentText() == self.nodeTree.topLevelItem(i).text(0) or self.nodeTree.topLevelItemCount() ==0:
                pass
            else:
                self.connectedNodesSelection2.addItem(self.nodeTree.topLevelItem(i).text(0))

    #Adds/Removes Input Boxes depending on selected medium type
    def toggleSolidProperties(self):
        if self.mediumTypeSelection.currentText() == "SOLID": 
            self.pressureLabel.setVisible(False)
            self.pressureInput.setVisible(False)
            self.emissivityLabel.setVisible(True)
            self.emissivityInput.setVisible(True)
            self.absorbivityLabel.setVisible(True) if self.isothermalInput.currentText() == 'False' else self.absorbivityLabel.setVisible(False)
            self.absorbivityInput.setVisible(True) if self.isothermalInput.currentText() == 'False' else self.absorbivityInput.setVisible(False)
        elif self.mediumTypeSelection.currentText() == "FLUID":
            self.pressureLabel.setVisible(True)
            self.pressureInput.setVisible(True)
            self.emissivityLabel.setVisible(False)
            self.emissivityInput.setVisible(False)
            self.absorbivityLabel.setVisible(False)
            self.absorbivityInput.setVisible(False)
    #region isothermal
    def toggleIsothermal(self): 
        if self.isothermalInput.currentText() == "True":
            self.volumeLabel.setVisible(False)
            self.volumeInput.setVisible(False)
            self.heatGeneratedLabel.setVisible(False)
            self.heatGeneratedInput.setVisible(False)
            self.absorbivityLabel.setVisible(False)
            self.absorbivityInput.setVisible(False)
        else:
            self.volumeLabel.setVisible(True)
            self.volumeInput.setVisible(True)
            self.heatGeneratedLabel.setVisible(True)
            self.heatGeneratedInput.setVisible(True)
            if self.mediumTypeSelection.currentText() == "SOLID":
                self.absorbivityLabel.setVisible(True)
                self.absorbivityInput.setVisible(True)
    #endregion isothermal
    #region Solves Problem
    def solve(self): 
        try:
            #clear connected paths from last solve
            for node in self.backendNodes:
                node.connectedPaths = []

            self.canvas.ax.clear()
            if (self.backendPaths == [] or self.backendNodes == []) and self.nodeTree.topLevelItemCount() > 1:
                raise Exception
            elif self.backendNodes == []:
                raise Exception


            timeUnit = self.timeUnits.currentText()
            temperatureUnits = self.temperatureUnits.currentText()
            # timeInitial = float(self.timeInitialInput.text())
            timeInitial = 0
            timeFinal = float(self.timeDurationInput.text())

            if timeUnit == "min":
                timeInitial = timeInitial*60 #Converts min to s
                timeFinal = timeFinal*60
            elif timeUnit == 'hr':
                timeInitial = timeInitial*3600 #Converts hr to s
                timeFinal = timeFinal*3600
            timeScaleFactor = 1
            if timeUnit == 'min':
                timeScaleFactor = 60
            elif timeUnit == 'hr':
                timeScaleFactor = 3600
            tspan = [timeInitial, timeFinal]
            teval = np.linspace(tspan[0], tspan[1],10000)
            a = 0
            legend = []
            time = teval/timeScaleFactor
            #For single node case. Want to see how long it takes a mass to heat up
            if self.nodeTree.topLevelItemCount() == 1:           
                if node.isothermal == 'False':
                    node = self.backendNodes[0]
                    a = node.T + node.Eg/(node.density*node.V*node.c)*teval
                    self.canvas.ax.plot(time, unit_convert(a, "K", self.temperatureUnits.currentText()))
                    legend.append("Node 1")
                    self.canvas.draw()
                else: 
                    self.outputText.setVisible(True)
                    self.outputText.setText("There are easier ways to plot a flat line.")
                    self.canvas.ax.plot(time, [unit_convert((node.T), 'K', self.temperatureUnits.currentText())]*np.size(time))
                    self.canvas.ax.set_xlabel("Time, " + timeUnit)
                    self.canvas.ax.set_ylabel("Temperature, " + temperatureUnits)
                    self.canvas.ax.set_title("Node Temperature vs Time")
                    self.canvas.ax.grid(True)
                    self.canvas.draw()
            else: 
                self.outputText.setVisible(True)
                a = t.T_vs_t(tspan, teval, self.backendPaths, self.backendNodes)
                time = a.t/timeScaleFactor
                y =a.y 
                for i in range(len(y[:,0])):
                    for j in range(len(y[0,:])):
                        y[i,j] = unit_convert(y[i,j], "K", self.temperatureUnits.currentText())
                for i in range(len(y[:,0])):
                    self.canvas.ax.plot(time, y[i,:])
                    legend.append(f"Node {self.backendNodes[i].identifier}")
                self.canvas.ax.set_xlabel("Time, " + timeUnit)
                self.canvas.ax.set_ylabel("Temperature, " + temperatureUnits)
                self.canvas.ax.set_title("Node Temperature vs Time")
                self.canvas.ax.grid(True)
                self.canvas.ax.legend(legend)
                self.canvas.draw()
                self.outputText.setVisible(False)
        except Exception as ex:
            print(ex)
            self.outputText.setVisible(True)
            self.outputText.setText("Solve Inputs are incorrect/incomplete. Check nodes, paths, and time values")
   
    #Removes selected node referencing selectedNode box
    def removeNode(self):
        try: 
            for i in range(self.nodeTree.topLevelItemCount()):
                if self.currentNodeSelection.text() == self.nodeTree.topLevelItem(i).text(0).split(" ")[-1]:
                    
                    for j in range(len(self.backendNodes)):
                        if self.backendNodes[j].identifier == int(self.currentNodeSelection.text()): 
                            self.backendNodes.remove(self.backendNodes[j])
                            break
                    
                    item = self.nodeTree.takeTopLevelItem(i); del item
                    self.nodes.pop('Node ' + self.currentNodeSelection.text())
                    self.connectedNodesSelection1.removeItem(int(i) - 1)
                    self.currentNodeSelection.setMaximum(int(self.nodeTree.topLevelItem(self.nodeTree.topLevelItemCount()-1).text(0).split(' ')[-1])+1) if self.nodeTree.topLevelItemCount() != 0 else 1
                    self.currentNodeSelection.setValue(self.currentNodeSelection.value() - 1)
                    self.setNodeSelection()
                    self.changeNodeSelectionItems()
                    print(self.nodes)
                    print(self.backendNodes)
                    self.outputText.setText("Node removed from node tree.")
                    break
                else: 
                    self.outputText.setText("Node does not exist.")
        except Exception as e:
            self.outputText.setText(str(e))
        
    def removePath(self): 
        try:
            for i in range(self.pathTree.topLevelItemCount()):
                a = self.pathTree.topLevelItem(i).text(0).split(' ')[-1]
                if self.currentPathSelection.text() == a:
                    for j in range(len(self.backendPaths)):
                        if self.backendPaths[j].identifier == int(self.currentPathSelection.text()):
                            self.backendPaths.remove(self.backendPaths[j])
                            break
                        
                    item = self.pathTree.takeTopLevelItem(i); del item; 
                    self.paths.pop('Path ' + self.currentPathSelection.text())
                    self.currentPathSelection.setMaximum(self.currentPathSelection.maximum() - 1)
                    self.currentPathSelection.setValue(self.currentPathSelection.value() -1)
                    self.outputText.setText("Path removed from path tree.")
                    break
                else:
                    self.outputText.setText("Path does not exist.")
        
        except Exception as e:
            self.outputText.setText(str(e))

    #region update node entries
    def updateNodeEntries(self,item):
        try:
            itemClicked = item.text(0)
            nodeNumber = itemClicked.split(' ')[-1]
            self.currentNodeSelection.setValue(int(nodeNumber)) #Sets node selection to the correct node
            for i in range(self.nodeTree.topLevelItemCount()):
                if self.backendNodes[i].identifier == int(nodeNumber):
                    node = self.backendNodes[i]
            
            self.isothermalInput.setCurrentText(str(node.isothermal))
            self.temperatureInput.setText(str(round(unit_convert(node.T, "K", item.child(0).text(2)),2)))
            self.temperatureUnits.setCurrentText(item.child(0).text(2))
            self.mediumTypeSelection.setCurrentText(node.medium_type)
            self.mediumSelection.setCurrentText(node.medium)
            self.emissivityInput.setText(str(node.e))
            self.absorbivityInput.setText(str(node.a))
            self.outputText.setText(f"{itemClicked} selected")

            if node.isothermal == False:

                if node.medium_type == 'SOLID' and node.medium != 'CUSTOM': 
                    
                    self.volumeInput.setText(str(unit_convert(node.V, "m^3", item.child(5).text(2))))
                    self.volumeUnits.setCurrentText(item.child(5).text(2))
                    self.heatGeneratedInput.setText(str(unit_convert(node.Eg, 'W', item.child(6).text(2)))) 
                    self.energyUnits.setCurrentText(item.child(6).text(2))
                elif node.medium_type == 'SOLID' and node.medium == 'CUSTOM':
                    self.DensityInput.setText(str(unit_convert(node.density, 'kg/m^3', item.child(5).text(2))))
                    self.densityUnits.setCurrentText(item.child(5).text(2))
                    self.ConductivityInput.setText(str(node.k))
                    self.SpecificHeatCapacityInput.setText(str(node.c))
                    self.volumeInput.setText(str(unit_convert(node.V, "m^3", item.child(8).text(2))))
                    self.volumeUnits.setCurrentText(item.child(8).text(2))
                    self.heatGeneratedInput.setText(str(unit_convert(node.Eg, 'W', item.child(9).text(2)))) 
                    self.energyUnits.setCurrentText(item.child(9).text(2))
                
                elif node.medium_type == 'FLUID':   
                    self.volumeInput.setText(str(unit_convert(node.V, "m^3", item.child(2).text(2))))
                    self.volumeUnits.setCurrentText(item.child(2).text(2))
                    self.heatGeneratedInput.setText(str(unit_convert(node.Eg, 'W', item.child(3).text(2)))) 
                    self.energyUnits.setCurrentText(item.child(3).text(2))
                    self.pressureInput.setText(str(unit_convert(node.Pressure, 'Pa', item.child(4).text(2)))) 
                    self.pressureUnits.setCurrentText(item.child(4).text(2))
                    self.mediumSelection.setCurrentText(item.child(1).text(1))

            elif node.isothermal == True:
                if node.medium_type == 'FLUID':
                    self.pressureInput.setText(str(unit_convert(node.Pressure, 'Pa', item.child(2).text(2)))) 
                    self.pressureUnits.setCurrentText(item.child(2).text(2))
                    self.mediumSelection.setCurrentText(item.child(1).text(1))
                elif node.medium_type == 'SOLID' and node.medium != 'CUSTOM':
                    self.mediumSelection.setCurrentText(item.child(1).text(1))
                elif node.medium == 'CUSTOM':
                    self.DensityInput.setText(str(unit_convert(node.density, 'kg/m^3', item.child(5).text(2))))
                    self.densityUnits.setCurrentText(item.child(5).text(2))
                    self.ConductivityInput.setText(str(node.k))
                    self.SpecificHeatCapacityInput.setText(str(node.c))
           
        except Exception as e:
            print(e)
            self.outputText.setText("If attribute needs to be changed, click on parent node, not on attributes.")    
            
    #region UPDATE PATH ENTRIES
    def updatePathEntries(self, item): 
        try:
            itemClicked = item.text(0)
            pathNumber = itemClicked.split(' ')[-1]
            self.currentPathSelection.setValue(int(pathNumber)) #sets path selection to the correct path
            for i in range(self.pathTree.topLevelItemCount()):
                if self.backendPaths[i].identifier == int(pathNumber):
                    path = self.backendPaths[i]
            self.heatTransferModeInput.setCurrentText(item.child(4).text(0))
            self.heatTransferAreaInput.setText(str(unit_convert(path.Area, 'm^2', item.child(2).text(2))))
            self.areaUnits.setCurrentText(item.child(2).text(2))
            self.heatTransferCoefficientInput.setText(str(path.h))
            self.distanceUnits.setCurrentText(item.child(3).text(2))
            self.dxInput.setText(str(unit_convert(path.dx,'m', item.child(3).text(2)))) if self.heatTransferModeInput.currentText() == 'CONDUCTION' else ''
            self.connectedNodesSelection1.setCurrentText(str(item.child(0).text(1)))
            self.connectedNodesSelection2.setCurrentText(str(item.child(1).text(1)))
        except Exception as e:
            print(e)
            self.outputText.setText("If attribute needs to be changed, click on parent path, not on attributes.")

    def clearAll(self):
        for widget in self.findChildren(QLineEdit):
            widget.clear()
        for widget in self.findChildren(QTreeWidget):
            widget.clear()
        self.backendNodes = []
        self.backendPaths =[]
        self.nodes = {}
        self.paths = {}
        self.outputText.setVisible(False)
        self.canvas.ax.clear()
        self.canvas.ax.set_title("Node Temperature vs Time")
        self.canvas.ax.grid(True)
        self.currentNodeSelection.setRange(1,1)
        self.currentPathSelection.setValue(1)
        self.canvas.draw()

    #region UPDATE METHODS
    def updateTemperatureUnits(self):
        self.temperatureLabel.setText(
            "NODE TEMPERATURE, " + f'{self.temperatureUnits.currentText()}'
        )
    def updateVolumeUnits(self):
        self.volumeLabel.setText(
            "NODE VOLUME, " + f'{self.volumeUnits.currentText()}'
        )
    def updatePressureUnits(self):
        self.pressureLabel.setText(
            "NODE PRESSURE, " + f'{self.pressureUnits.currentText()}'
        )
    def updateEnergyUnits(self):
        self.heatGeneratedLabel.setText(
            "INTERNAL HEAT GENERATION, " + f'{self.energyUnits.currentText()}'
        )
    def updateAreaUnits(self):
        self.heatTransferAreaLabel.setText(
            "HEAT TRANSFER AREA, " + f'{self.areaUnits.currentText()}'
        )
    def updateDistanceUnits(self):
        self.dxLabel.setText(
            "LENGTH OF PATH, " + f'{self.distanceUnits.currentText()}'
        )
    def updateTimeUnits(self):
        self.timeInitialLabel.setText(
            "TIME INITIAL, " + f'{self.timeUnits.currentText()}'
        )
        self.timeFinalLabel.setText(
            "TIME DURATION, " + f'{self.timeUnits.currentText()}'
        )
    def updateDensityUnits(self):
        self.DensityLabel.setText(
            "NODE DENSITY, " + f'{self.densityUnits.currentText()}'
        )
    def toggleHeatTransferProperties(self):
        if self.heatTransferModeInput.currentText() == "CONDUCTION": 
            self.heatTransferCoefficientLabel.setVisible(False)
            self.heatTransferCoefficientInput.setVisible(False)
            self.dxLabel.setVisible(True)
            self.dxInput.setVisible(True)
        else: 
            self.heatTransferCoefficientLabel.setVisible(True)
            self.heatTransferCoefficientInput.setVisible(True)
            self.dxLabel.setVisible(False)
            self.dxInput.setVisible(False)
            
    def customMaterialEntry(self): 
        if self.mediumSelection.currentText() == 'CUSTOM':
            self.ConductivityLabel.setVisible(True)
            self.ConductivityInput.setVisible(True)
            self.DensityLabel.setVisible(True)
            self.DensityInput.setVisible(True)
            self.SpecificHeatCapacityLabel.setVisible(True)
            self.SpecificHeatCapacityInput.setVisible(True)
        else:
            self.ConductivityLabel.setVisible(False)
            self.ConductivityInput.setVisible(False)
            self.DensityLabel.setVisible(False)
            self.DensityInput.setVisible(False)
            self.SpecificHeatCapacityLabel.setVisible(False)
            self.SpecificHeatCapacityInput.setVisible(False) 

    #endregion UPDATE METHODS

def main():
    app = QApplication([])
    thermalSolve = MainWindow()
    thermalSolve.show()
    sys.exit(app.exec())

if __name__ == '__main__': 
    main()
