
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
     QAbstractScrollArea,
     QSizePolicy
     )

import thermal_solver as t
from PyQt6.QtCore import Qt
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import numpy as np


class MplCanvas(FigureCanvas):
    
    def __init__(self, parent=None, width=5, height=4, dpi=100):
            fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
            super(MplCanvas, self).__init__(fig) # Set the parent widget to make it behave like a QWidget

        
class MainWindow(QMainWindow): 

    def __init__(self): 

        super().__init__()
        self.title = 'Thermal Solver'
        self.setWindowTitle(self.title)
        # self.setGeometry(100,25,900,300)
        # self.setBaseSize(1200,1000)
        self.table_widget = thermalSolver()
        self.setCentralWidget(self.table_widget)

        self.show()
class thermalSolver(QWidget): 
    
    def __init__(self,parent):

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
        self.temperatureLabel = QLabel("NODE TEMPERATURE, K" )
        self.mediumTypeLabel = QLabel("MEDIUM TYPE")
        self.mediumLabel = QLabel("MEDIUM")
        self.pressureLabel= QLabel("NODE PRESSURE, Pa") #Specify if gage or not
        self.volumeLabel = QLabel("NODE VOLUME, m^3") 
        self.heatGeneratedLabel = QLabel("INTERNAL HEAT GENERATION, W")
        self.emissivityLabel= QLabel("EMISSIVITY")
        self.absorbivityLabel = QLabel("ABSORBTIVITY")
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
        self.heatTransferAreaLabel = QLabel("HEAT TRANSFER AREA, m^2")
        self.numberofPathsLabel =QLabel("CURRENT PATH")     
        self.timeInitialLabel = QLabel("TIME INITIAL,s")
        self.timeFinalLabel = QLabel("TIME FINAL, s")  
        self.dxLabel = QLabel("LENGTH OF PATH, m")
        self.energyUnitsLabel = QLabel("Energy Units")
        self.areaUnitsLabel = QLabel("Area Units")
        self.distanceUnitsLabel = QLabel("Distance Units")
        self.timeUnitsLabel = QLabel("Time Units")
        self.heatTransferModeLabel = QLabel("HEAT TRANSFER MODE")
        #endregion LABELS

        #region UNIT DROPDOWN MENUS
        self.pressureUnits = QComboBox()
        self.pressureUnits.addItems(["Pa","psig", "psia",  "bar,g","bar,a","atm"])
        self.pressureUnits.currentTextChanged.connect(self.updatePressureUnits)

        self.temperatureUnits = QComboBox()
        self.temperatureUnits.addItems(["K","C","F","Rank"])
        self.temperatureUnits.currentTextChanged.connect(self.updateTemperatureUnits)
        
        self.volumeUnits = QComboBox()
        self.volumeUnits.addItems(["m^3","mm^3","L","ft^3", "in^3", "gal"])
        self.volumeUnits.currentTextChanged.connect(self.updateVolumeUnits)

        self.energyUnits = QComboBox()
        self.energyUnits.addItems(["W", "BTU"])
        self.energyUnits.currentTextChanged.connect(self.updateEnergyUnits)

        self.areaUnits = QComboBox()
        self.areaUnits.addItems(["m^2", "mm^2", "ft^2","in^2"])
        self.areaUnits.currentTextChanged.connect(self.updateAreaUnits)

        self.distanceUnits = QComboBox()
        self.distanceUnits.addItems(["m", "mm", "ft","in"])
        self.distanceUnits.currentTextChanged.connect(self.updateDistanceUnits)

        self.timeUnits = QComboBox()
        self.timeUnits.addItems(["s", "min", "hr"])
        self.timeUnits.currentTextChanged.connect(self.updateTimeUnits)
        #endregion UNIT DROPDOWN MENUS
        
        #region OUTPUT TEXT PRINTING 
        self.outputText = QLabel()
        self.outputText.setVisible(False)
        #endregion OUTPUT TEXT PRINTING

        #region NODE ATTRIBUTE SELECTIONS
        self.currentNodeSelection = QSpinBox()
        self.currentNodeSelection.setRange(1,1)

        self.temperatureInput = QLineEdit()
        self.temperatureInput.setPlaceholderText("300 ")

        self.mediumTypeSelection = QComboBox()
        self.mediumTypeSelection.addItems(["FLUID","SOLID"])
        self.mediumTypeSelection.setCurrentIndex(-1)
        self.mediumTypeSelection.setPlaceholderText("Select")
        self.mediumTypeSelection.currentTextChanged.connect(self.changeMediumSelectionItems)
        self.mediumTypeSelection.currentTextChanged.connect(self.toggleSolidProperties)
        
        self.mediumSelection = QComboBox()
        self.mediumSelection.setPlaceholderText("Select")
        
        self.pressureInput = QLineEdit()
        self.pressureInput.setPlaceholderText("101325")

        self.volumeInput = QLineEdit()
        self.volumeInput.setPlaceholderText(".001")

        self.heatGeneratedInput = QLineEdit()
        self.heatGeneratedInput.setPlaceholderText("100")

        self.emissivityInput = QLineEdit()
        self.emissivityInput.setPlaceholderText("0.3")

        self.absorbivityInput = QLineEdit()
        self.absorbivityInput.setPlaceholderText("0.2")

        self.isothermalInput = QComboBox()
        self.isothermalInput.addItems(["True", "False"])
        self.isothermalInput.setCurrentIndex(1)
        self.isothermalInput.currentTextChanged.connect(self.toggleIsothermal)
        #endregion NODE ATTRIBUTE SELECTIONS

        #region PATH ATTRIBUTE SELECTIONS
        self.currentPathSelection = QSpinBox()
        self.currentPathSelection.setRange(1, 20)

        self.heatTransferModeInput = QComboBox()
        self.heatTransferModeInput.addItems(["CONVECTION", "CONDUCTION"])
        self.heatTransferModeInput.setCurrentIndex(-1)
        self.heatTransferModeInput.setPlaceholderText("Select")

        self.heatTransferModeInput.currentTextChanged.connect(self.toggleHeatTransferProperties)
        self.heatTransferCoefficientInput = QLineEdit()
        self.heatTransferCoefficientInput.setPlaceholderText("10")

        self.heatTransferAreaInput = QLineEdit()
        self.heatTransferAreaInput.setPlaceholderText("0.1")

        self.dxInput = QLineEdit()
        self.dxInput.setPlaceholderText(".01")
        #endregion PATH ATTRIBUTE SELECTIONS

        #region TIME INPUT 
        self.timeInitialInput = QLineEdit()
        self.timeInitialInput.setPlaceholderText("0")

        self.timeFinalInput = QLineEdit()
        self.timeFinalInput.setPlaceholderText("3600")
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
        
        self.timeEvalAndUnitLayout.addWidget(self.timeInitialLabel)
        self.timeEvalAndUnitLayout.addWidget(self.timeInitialInput)
        self.timeEvalAndUnitLayout.addWidget(self.timeFinalLabel)
        self.timeEvalAndUnitLayout.addWidget(self.timeFinalInput)
        self.timeEvalAndUnitLayout.addWidget(self.outputText)
        #endregion SET TIME INPUT LAYOUT

        #region PLOT LAYOUT
        self.canvas = MplCanvas(self,width=5, height=2, dpi = 100)
        self.canvas.ax.set_title("Node Temperature vs Time")
        self.canvas.ax.grid(True)
        self.plotLayout.addWidget(self.canvas)
        
        #endregion PLOT LAYOUT
        
        #region BUTTONS
        
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

    '''Set Node Selection based on foregoing Node Selection for path (i.e sets selsection for )'''
    def setNodeSelection(self): 
        #Clear selected Nodes
        self.connectedNodesSelection1.clear()

        top_level_count = self.nodeTree.topLevelItemCount()
        #if topLevelItemCount
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
            if self.nodeTree.topLevelItemCount() == 10:
                self.outputText.setVisible(True)
                self.outputText.setText("Maximum number of nodes exceeded(10)")
                return 1
            items = []
            self.nodeTree.clear()
            attributes = [
                "T," + (self.temperatureInput.text()) +':'+self.temperatureUnits.currentText(), 
                "MEDIUM,"+self.mediumSelection.currentText()+':', 
                "VOLUME," + (self.volumeInput.text()) +':'+ self.volumeUnits.currentText()if self.isothermalInput.currentText() == "False" else '', 
                "HEAT GENERATED," + (self.heatGeneratedInput.text()) + ':'+self.energyUnits.currentText() if self.heatGeneratedInput.text() != '' else '', 
                "PRESSURE,"+ (self.pressureInput.text()) + ':'+self.pressureUnits.currentText() if self.mediumTypeSelection.currentText() == "FLUID" else '' , 
                
                "EMISSIVITY," + (self.emissivityInput.text()) +':'if self.mediumTypeSelection.currentText() == "SOLID" else '', 
                "ABSORPTIVITY,"+(self.absorbivityInput.text()) +':'if self.mediumTypeSelection.currentText() == "SOLID" else '',
                "ISOTHERMAL," + (self.isothermalInput.currentText()) + ':'
            ]

            '''Stores node in backend nodes and updates nodes using identifier attribute'''
            self.backendNodes = [node for node in self.backendNodes if node.identifier != self.currentNodeSelection.value()]
            self.backendNodes.append(t.Node(
    
                T = unit_convert(
                    float(self.temperatureInput.text()), 
                    self.temperatureUnits.currentText(),
                    "K"
                ) if self.temperatureInput.text() != '' else '',

                medium= self.mediumSelection.currentText(),
                medium_type=self.mediumTypeSelection.currentText() if self.mediumTypeSelection.currentText() != '' else "SOLID",
                Pressure= unit_convert(
                    float(self.pressureInput.text()),
                    self.pressureUnits.currentText(), 
                    "Pa", 
                ) if self.mediumTypeSelection.currentText() == 'FLUID' else 0.0,
                Eg = unit_convert(
                    float(self.heatGeneratedInput.text()),
                    self.energyUnits.currentText(), 
                    "W",
                ) if self.heatGeneratedInput.text() != '' or self.isothermalInput == False else 0.0, 
                V= unit_convert(
                    float(self.volumeInput.text()),
                    self.volumeUnits.currentText(),
                    "m^3",
                ) if self.isothermalInput.currentText() == "False" else 0.0, 
                #remove emissivity input
                isothermal= eval(self.isothermalInput.currentText()) if self.isothermalInput.currentText() != '' else False,
                identifier=self.currentNodeSelection.value()
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
                if node.identifier == int(self.currentNodeSelection.text()):
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
            self.outputText.setText("Something went wrong with node update. Check node inputs.")

    def updatePath(self): 
        try:
            '''First checks if path already exists AND is not updating pre-existing path'''
            nume1 = int(self.connectedNodesSelection1.currentText().split(' ')[-1])
            denom1 = int(self.connectedNodesSelection2.currentText().split(' ')[-1])
            
            print(self.pathTree.topLevelItemCount())
            for i in range(self.pathTree.topLevelItemCount()):
                nume2 = int(self.paths[self.pathTree.topLevelItem(i).text(0)][0].split(' ')[-1].split(':')[0])
                denom2 = int(self.paths[self.pathTree.topLevelItem(i).text(0)][1].split(' ')[-1].split(':')[0])   
                prod = (nume1/denom1)*(nume2/denom2) 
                if (self.pathTree.topLevelItem(i).text(0).split(' ')[-1] != self.currentPathSelection.text()) and (prod == (nume2/denom2)**2 or prod == 1):  
                    self.outputText.setText("Path already exists")
                    return 1
                
            self.pathTree.clear()
            attributes =[ 
                "Node A," + self.connectedNodesSelection1.currentText()+":",
                "Node B," + self.connectedNodesSelection2.currentText()+':',
                "h," + self.heatTransferCoefficientInput.text() +':'+ 'W/m^2K' if self.heatTransferModeInput.currentText() == "CONVECTION" else '',
                "Area," + self.heatTransferAreaInput.text()+':'+ self.areaUnits.currentText(),
                "dx," + self.dxInput.text()+':' +self.distanceUnits.currentText() if self.heatTransferModeInput.currentText() == "CONDUCTION" else '',
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

        except Exception as e: 
            self.outputText.setText("Something went wrong with path inputs.")   

    #Sets Selection Medium based on medium type selection
    def changeMediumSelectionItems(self): 
        self.mediumSelection.clear()
        if self.mediumTypeSelection.currentText() == "SOLID": 
            self.mediumSelection.addItems(["SS316", "Al6061", "Al7075T6"])
            self.mediumSelection.setCurrentIndex(-1)

        elif self.mediumTypeSelection.currentText() == "FLUID":
            self.mediumSelection.addItems(["HYDROGEN", "ARGON", "NITROGEN","AIR"])
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
            self.absorbivityLabel.setVisible(True)
            self.absorbivityInput.setVisible(True)
        elif self.mediumTypeSelection.currentText() == "FLUID":
            self.pressureLabel.setVisible(True)
            self.pressureInput.setVisible(True)
            self.emissivityLabel.setVisible(False)
            self.emissivityInput.setVisible(False)
            self.absorbivityLabel.setVisible(False)
            self.absorbivityInput.setVisible(False)
    def toggleIsothermal(self): 
        if self.isothermalInput.currentText() == "True":
            self.volumeLabel.setVisible(False)
            self.volumeInput.setVisible(False)
            self.heatGeneratedLabel.setVisible(False)
            self.heatGeneratedInput.setVisible(False)
        else:
            self.volumeLabel.setVisible(True)
            self.volumeInput.setVisible(True)
            self.heatGeneratedLabel.setVisible(True)
            self.heatGeneratedInput.setVisible(True)

    #Solves Problem
    def solve(self): 
        try:
            #clear connected paths from last solve
            for node in self.backendNodes:
                node.connectedPaths = []
            self.canvas.ax.clear()

            timeUnit = self.timeUnits.currentText()
            temperatureUnits = self.temperatureUnits.currentText()
            timeInitial = float(self.timeInitialInput.text())
            timeFinal = float(self.timeFinalInput.text())

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
            #For single node case. Want to see how long it takes a mass to heat up
            if self.nodeTree.topLevelItemCount() == 1:
                node = self.backendNodes[0]
                a = node.T + node.Eg/(node.density*node.V*node.c)*teval
                time = teval/timeScaleFactor
                self.canvas.ax.plot(time, unit_convert(a, "K", self.temperatureUnits.currentText()))
                legend.append("Node 1")
            else: 
                
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

    #region node entries
    def updateNodeEntries(self,item):
        try:
            itemClicked = item.text(0)
            nodeNumber = itemClicked.split(' ')[-1]
            self.currentNodeSelection.setValue(int(nodeNumber))
            for i in range(self.nodeTree.topLevelItemCount()):
                if self.backendNodes[i].identifier == int(nodeNumber):
                    node = self.backendNodes[i]

            self.isothermalInput.setCurrentText(str(node.isothermal))
            self.temperatureInput.setText(str(unit_convert(node.T, "K", item.child(0).text(2))))
            self.temperatureUnits.setCurrentText(item.child(0).text(2))
            self.mediumSelection.setCurrentText(node.medium)
            self.mediumTypeSelection.setCurrentText(node.medium_type)
            self.volumeInput.setText(str(unit_convert(node.V, "m^3", item.child(2).text(2))))
            self.volumeUnits.setCurrentText(item.child(2).text(2))
            self.pressureInput.setText(str(unit_convert(node.Pressure, 'Pa', item.child(4).text(2)))) if node.medium_type == 'FLUID' else ''
            self.pressureUnits.setCurrentText(item.child(4).text(2))
            self.heatGeneratedInput.setText(str(unit_convert(node.Eg, 'W', item.child(3).text(2)))) if node.isothermal == False else ''
            self.energyUnits.setCurrentText(item.child(3).text(2))
            self.emissivityInput.setText(str(node.e))
            self.absorbivityInput.setText(str(node.a))
            self.outputText.setText(f"{itemClicked} selected")
        except:
            self.outputText.setText("if attribute needs to be changed, click on parent node not on attributes.")    
   
    def updatePathEntries(self, item): 
        try:
            itemClicked = item.text(0)
            pathNumber = itemClicked.split(' ')[-1]
            self.currentPathSelection.setValue(int(pathNumber))
            for i in range(self.pathTree.topLevelItemCount()):
                if self.backendPaths[i].identifier == int(pathNumber):
                    path = self.backendPaths[i]
            self.heatTransferModeInput.setCurrentText(item.child(4).text(0))
            self.heatTransferAreaInput.setText(str(unit_convert(path.Area, 'm^2', item.child(2).text(2))))
            self.areaUnits.setCurrentText(item.child(2).text(2))
            self.heatTransferCoefficientInput.setText(str(path.h))
            self.dxInput.setText(str(unit_convert(path.dx,'m', item.child(3).text(2)))) if self.heatTransferModeInput.currentText() == 'CONDUCTION' else ''
            self.connectedNodesSelection1.setCurrentText(str(item.child(0).text(1)))
            self.connectedNodesSelection2.setCurrentText(str(item.child(1).text(1)))
        except:
            self.outputText.setText("if attribute needs to be changed, click on parent path not on attributes.")

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
            "TIME FINAL, " + f'{self.timeUnits.currentText()}'
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
    #endregion UPDATE METHODS

if __name__ == '__main__': 
    app = QApplication([])
    thermalSolve = MainWindow()
    thermalSolve.show()
    sys.exit(app.exec())

