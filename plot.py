
class Plot:
    def __init__(self, x_data, y_data, x_unit, y_unit):
        self.x_data = x_data
        self.y_data = y_data
        self.x_unit = x_unit
        self.y_unit = y_unit
        

    # def update_flow_plot(self, time_series, flow_series, time_units):
    #     self.canvas2.axes.cla()
    #     self.canvas2.axes.plot(time_series, flow_series)
    #     self.canvas2.axes.set_ylabel("Flow Rate, " + self.mass_flow_units.currentText())
    #     self.canvas2.axes.set_xlabel("Time, " + str(time_units))
    #     self.canvas2.axes.set_title("Flow Rate vs. Time")
    #     self.canvas2.axes.grid(True)
    #     if self.minor_grid_checkbox.isChecked():
    #         self.canvas2.axes.minorticks_on()
    #         self.canvas2.axes.grid(True, which='minor')
    #     self.canvas2.draw()

    def update_plot(self):
        """
        update plot
        """
        self.canvas.axes.cla()
        self.canvas.axes.plot(self.x_data, self.y_data) #self.canvas.axes.plot(time_series, pressure_series)
        self.canvas.axes.set_ylabel("y value update me, " + self.y_unit)
        self.canvas.axes.set_xlabel("x value update me, " + str(self.x_unit))
        self.canvas.axes.set_title("add a title")
        self.canvas.axes.grid(True)
        if self.minor_grid_checkbox.isChecked():
            self.canvas.axes.minorticks_on()
            self.canvas.axes.grid(True, which='minor')
        self.canvas.draw()

# if __name__ == "__main__":
    
#     Plot().update_pressure_plot(x_data, y_data, x_unit)