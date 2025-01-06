
class plot:
    def __init__(self, x_array, y_array, x_unit, y_unit):
        self.x_array = x_array
        self.y_array = y_array
        self.x_unit = x_unit
        self.y_unit = y_unit
        

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
        file_name):
        
        import matplotlib.pyplot as plt
        import numpy as np
        from matplotlib.image import imread
        from PIL import Image
        
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