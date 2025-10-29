import math as m
from utilities import getfluidproperty, unit_convert, atm2Pa, LMTD
from mat_lib import Material, SS316
from thermal_solver import material_mapping

class HeatExchanger():
    """A Heat Exchanger"""
    HR_SECS = 3600
    PI = 3.14159265

    def __init__(self,
                 Name=None, 
                 H_Inlet_Temp=None,
                 H_Inlet_ID=None,
                 H_Outlet_Temp=None,
                 H_Outlet_ID=None, 
                 H_Inlet_Pres=None,
                 H_In_Mass_Flow=None,
                 H_In_Vol_Flow_nm3=None, 
                 H_Fluid=None,
                 C_Inlet_Temp=None,
                 C_Inlet_ID=None, 
                 C_Outlet_Temp=None,
                 C_Outlet_ID=None, 
                 C_Inlet_Pres=None,
                 C_In_Mass_Flow=None,
                 C_In_Vol_Flow_nm3=None,
                 C_Fluid=None,
                 HX_Type="plate",
                 Counter_Flow = True,
                 q = None,
                 q_max = None,
                 effectiveness_U = None,
                 effectiveness_epsilon = None,
                 ntu = None,
                 area = None,
                 UA = None,
                 F_sub_T = 1,
                 Plate_Material = SS316,
                 Plate_Thickness = 0.6,
                 Plate_Count=None,
                 Plate_Distribution_Bias = "hot",
                 mean_channel_gap = None,
                 enlargement_factor_phi = None,
                 Total_Hot_Channel_Volume = None,
                 Total_Cold_Channel_Volume = None,
                 Per_Channel_Volume = None,
                 Hot_Passes=1
                 ):
        """Create a new instance of a Heat Exchanger

        Attributes
        ----------
            Name : str
                The name of the heat exchanger, only used for clarical purposes in print statements.
            H_Inlet_Temp : float [Kelvin]
                The fluid Temperature entering the hot side. Called with self._Thi.
            H_Inlet_ID : float [mm]
                The inner diameter of the inlet of the hot side.
            H_Outlet_Temp : float [Kelvin]
                The fluid temperature exiting the hot side. Called with self._Tho
            H_Outlet_ID : float [mm]
                The inner diameter of the outlet of the hot side.
            H_Inlet_Pres : float [Pascals]
                The Pressure of the fluid entering the hot side
            H_In_Mass_Flow : float [kg/s]
                Hot side mass flow
            H_In_Vol_Flow_nm3 : float [Nm^3/hr]
                Hot side volumetric flow
            H_Fluid : str 
                The Fluid in the hot side, e.g("H2"). Must be a name recognized by CoolProp
            C_Inlet_Temp : float [Kelvin]
                The fluid Temperature entering the hot side. Called with self._Thi
            C_Inlet_ID : float [mm]
                The inner diameter of the inlet of the cold side,
            C_Outlet_Temp : float [kelvin]
                The fluid temperature exiting the hot side. Called with self._Tho
            C_Outlet_ID : float [mm]
                The inner diameter of the outlet of the cold side.
            C_Inlet_Pres : float [Pascals] 
                The Pressure of the fluid entering the cold side
            C_In_Mass_Flow : float [kg/s]
                cold side mass flow
            C_In_Vol_Flow_nm3 : float [Nm^3/hr]
                cold side volumetric flow 
            C_Fluid : str
                The Fluid in the cold side, e.g("H2"). Must be a name recognized by CoolProp
            HX_Type : str
                The type of heat exchanger. Available options: "plate"
            Counter_Flow : bool
                The relative direction of flow between the hot and cold fluids. False for parallel flow.
            q : float [J/s (i.e. W)]
                The total rate of heat transfer between the fluids
            q_max : float [J/s (i.e. W)]
                The max theoretical heat transfaer rate between the fluids.
            effectiveness_U : float [W/m^2/K]
                The effectiveness of the heat exchanger by area of heat transfer
            effectiveness_epsilon : float [dimensionless, 0 =< epsilon <= 1]
                q_max*epsilon=q (see eq 11.22 of [2])
            ntu : float [dimensionless]
                The number of transfer units of the heat exchanger.
            area : float [m^2]
                The surface area of the heat exchanging surfaces between the fluids
            UA : float [W/K]
                The overall heat transfer coefficient
            F_Sub_T : float [dimensionless] 0<Ft<1
                The correction factor for LMTD calculations, default of 1 is no correction factor
            Plate_Material : Material
                Applies only when 'HX_type' = plate. An instance of the Material class.
            Plate_Thickness : float [mm]
                Applies only when 'HX_type' = plate. Thickness of the plate at the exchange surface, i.e. of the material itself not including corrugations.
            Plate_Count : int [number of plates]
                The count of plates if HX_Type is "plate".
            Plate_Distribution_Bias : str ["hot" or "cold"]
                The side of the heat exchanger to be assigned the additional channel in the event the channel count (plate count -1) is odd.
                Default is "hot". For example, if plate count is 12, therefore there are 11 channels. If Bias is "hot", the hot side will be assigned 6 channels and cold 5.
            mean_channel_gap : float [mm]
                The mean gap between plates, equals pitch - thickness.
            enlargement_factor_phi : float
                The ratio of developed length and projected length.
                Calculated as Actual heat transfer area divided by rojected heat transfer area 
                where projected heat transfer area is L_p * L_w,
                where L_p = vertical port distance minus port diameter and L_w is horizontal port distance times port diameter.
                See 2.2.1 of reference [4].
            Total_Hot_Channel_Volume : int [mm^2]
                The total volume of the channels the hot gas will flow through.
                Applies only when 'HX_type' = plate
            Total_Cold_Channel_Volume : int [mm^2]
                The total volume of the channels the cold gas will flow through.
                Applies only when 'HX_type' = plate
            Per_Channel_Volume : int [mm^2]
                The volume of an individual channel.
                Applies only when 'HX_type' = plate.
                Assumes Channels are equally sized for hot and cold fluids.
            Hot_Passes : int [number of passes]
                The number of passes the hot fluid makes. Default is 1.

        """

        self._Name = Name
        """attribute HeatExchanger._Name : str [Name]
            The name of the heat exchanger. Used to identify the instance being evaluated in print statements"""    
        self._Thi = H_Inlet_Temp
        """attribute HeatExchanger._H_Inlet_Temp : float [Kelvin]
            The fluid Temperature entering the hot side. Provided as H_Inlet_Temp"""
        self._H_inlet_ID = H_Inlet_ID
        """attribute HeatExchanger._H_Inlet_ID : float [mm]
            The inner diameter of the inlet of the hot side. Provided as H_Inlet_ID"""
        self._Tho = H_Outlet_Temp
        """attribute HeatExchanger._H_Outlet_Temp : float [Kelvin]
            The fluid Temperature exiting the hot side. Provided as H_Outlet_Temp"""
        self._H_outlet_ID = H_Outlet_ID
        """attribute HeatExchanger._H_outlet_ID : float [mm]
            The inner diameter of the outlet of the hot side. Provided as H_Outlet_ID"""
        self._Pres_H_in = H_Inlet_Pres
        """attribute HeatExchanger._Pres_H_in : float [Pascals]
            The Pressure of the fluid entering the hot side. Provided as H_Inlet_Pres"""
        self._mdot_h = H_In_Mass_Flow
        """attribute HeatExchanger._mdot_h : float [kg/s]
            Hot side mass flow. Provided as H_In_Mass_Flow"""
        self._H_in_nm3_hr = H_In_Vol_Flow_nm3
        """attribute HeatExchanger._H_in_nm3_hr : float [Nm^3/hr]
            Hot side volumetric flow. Provided as H_In_Vol_Flow_nm3"""
        self._H_Fluid = H_Fluid
        """attribute self._H_Fluid : str
            The Fluid in the hot side, e.g("H2"). Must be a name recognized by CoolProp"""
        self._Tci = C_Inlet_Temp
        """attribute HeatExchanger._Tci : float [Kelvin]
            The fluid Temperature entering the cold side. Provided as C_Inlet_Temp"""
        self._C_inlet_ID = C_Inlet_ID
        """attribute HeatExchanger._C_inlet_ID : float [mm]
            The inner diameter of the inlet of the cold side. Provided as C_Inlet_ID"""
        self._Tco = C_Outlet_Temp
        """attribute HeatExchanger._Tco : float [Kelvin]
            The fluid Temperature exiting the cold side. Provided as C_Outlet_Temp"""
        self._C_outlet_ID = C_Outlet_ID
        """attribute HeatExchanger._C_Outlet_ID : float [mm]
            The inner diameter of the outlet of the cold side. Provided as C_Outlet_ID"""
        self._Pres_C_in = C_Inlet_Pres
        """attribute HeatExchanger._Pres_C_in : float [Pascals]
            The Pressure of the fluid entering the cold side. Provided as C_Inlet_Pres"""
        self._mdot_c = C_In_Mass_Flow
        """attribute HeatExchanger._mdot_c : float [kg/s]
            cold side mass flow. Provided as C_In_Mass_Flow"""
        self._C_in_nm3_hr = C_In_Vol_Flow_nm3
        """attribute HeatExchanger._C_in_nm3_hr : float [Nm^3/hr]
            Hot side volumetric flow. Provided as C_In_Vol_Flow_nm3"""
        self._C_Fluid = C_Fluid
        """attribute HeatExchanger._C_Fluid : str
            The Fluid in the cold side, e.g("H2"). Must be a name recognized by CoolProp"""
        self._Type = HX_Type
        """attribute HeatExchanger._Type : str
            The type of heat exchanger. Default is 'plate' """
        self._Flow_Direction = Counter_Flow
        """attribute HeatExchanger._Flow_Direction : bool
            True for counterflow, False for parrallel. Provided as Counter_Flow, default is True."""
        self._q = q
        """attribute HeatExchanger._q : float [J/s (i.e. W)]
            The total rate of heat transfer between the fluids. Provided as q.
            If not provided this value is set as the higher of HeatExchanger._q_h or HeatExchanger._q_c."""
        self._q_h = q
        """attribute HeatExchanger._q_h : float [J/s (i.e. W)]
            The total rate of heat transfer between the fluids as calculated using the fluid on the hot side."""
        self._q_c = q
        """attribute HeatExchanger._q_c : float [J/s (i.e. W)]
            The total rate of heat transfer between the fluids as calculated using the fluid on the cold side."""
        self._q_max = q_max
        """attribute HeatExchanger._q_max : float [J/s (i.e. W)]
            The theoretical max rate of heat transfer between the fluids.
            Calculated using HX._Cmin(HX._Thi-HX._Tci)"""
        self._U = effectiveness_U
        """attribute HeatExchanger._U : float [W/m^2 * K]
            The U portion of UA in the LMTD method (eq 11.14 of [2]). Not to be confused with HX._effectiveness_epsilon.
            Provided as effectiveness_U"""
        self._effectiveness_epsilon = effectiveness_epsilon
        """attribute HeatExchanger._effectiveness_epsilon : float [dimensionless, 0 =< epsilon =< 1]
            q_max*epsilon=q (see eq 11.22 of [2])"""
        self._NTU = ntu
        """attribute HeatExchanger._NTU : float [dimensionless]
            The number of transfer units of the heat exchanger.
            defined as HX._UA/HX._Cmin"""
        self._A = area
        """attribute HeatExchanger._A : float [m^2]
            The surface area of the heat exchanging surfaces between the fluids.
            provided as area"""
        self._UA = UA
        """attribute HeatExchanger._UA : float [W/K]
            The overall heat transfer coefficient. Provided as UA"""
        self._F_sub_T = F_sub_T
        """attribute HeatExchanger._F_Sub_T : float [0 =< Ft =< 1]
           correction factor in LMTD method. Default is 1 (ignored)"""
        self._Plate_count = Plate_Count
        """attribute HeatExchanger._Plate_Count : int [count of plates]
            The amount of plates. Requires HX._Type to be 'plate' """
        self._Plate_Distribution_Bias = Plate_Distribution_Bias
        """attribute HeatExchanger._Plate_Distribution_Bias : int ["hot" or "cold"]
            The side of the heat exchanger to be assigned the additional channel in the event the channel count (plate count -1) is odd.
            Default is "hot". 
            For example, if the plate count is 12 then there are 11 channels. If Bias is "hot", the hot side will be assigned 6 channels and cold 5."""
        self._mean_channel_gap = mean_channel_gap
        """attribute HeatExchanger._mean_channel_gap : float [mm]
            The mean gap between plates. defined as pitch minus thickness."""
        self._enlargement_phi = enlargement_factor_phi
        """attribute HeatExchanger._enlargement_phi : float [dimensionless]
            The ratio of developed length and projected length.
            Calculated as Actual heat transfer area divided by rojected heat transfer area 
            where projected heat transfer area is L_p * L_w,
            where L_p = vertical port distance minus port diameter and L_w is horizontal port distance times port diameter.
            See 2.2.1 of reference [4]."""
        self._Total_Hot_Ch_Vol = Total_Hot_Channel_Volume
        """attribute HeatExchanger._Total_Hot_Ch_Vol : int [mm^2]
            The total volume of the channels the hot gas will flow through.
            Applies only when 'HX_type' = plate"""
        self._Total_Cold_Ch_Vol = Total_Cold_Channel_Volume
        """attribute HeatExchanger._Total_Cold_Ch_Vol : int [mm^2]
            The total volume of the channels the cold gas will flow through.
            Applies only when 'HX_type' = plate"""
        self._Per_Ch_Vol = Per_Channel_Volume
        """attribute HeatExchanger._Per_Ch_Vol : int [mm^2]
            The volume of an individual channel.
            Applies only when 'HX_type' = plate"""
        self._Hot_Passes = Hot_Passes
        """attribute HeatExchanger._Hot_Passes : int [count of passes]
            The amount of passes the fluid makes on the hot side"""
        #self._H_nasa9 = db.set_compound(self._H_Fluid)
        """attribute HeatExchanger._H_nasa9 : A compound from the Nasa 9 Polynomials database.
            Fetched using HX._H_Fluid.
            Allows the use of methods from the thermopy library."""
        #self._C_nasa9 = db.set_compound(self._C_Fluid)
        """attribute HeatExchanger._C_nasa9 : A compound from the Nasa 9 Polynomials database.
            Fetched using HX._C_Fluid.
            Allows the use of methods from the thermopy library."""
        self._H_I_Cp = None
        """attribute HeatExchanger._H_I_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the Hot side fluid 
            at the inlet temperature and STP pressure."""
        self._H_O_Cp = None
        """attribute HeatExchanger._H_O_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the Hot side fluid 
            at the outlet temperature and STP pressure."""
        self._C_I_Cp = None
        """attribute HeatExchanger._C_I_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the cold side fluid 
            at the inlet temperature and STP pressure."""
        self._C_O_Cp = None
        """attribute HeatExchanger._C_O_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the cold side fluid 
            at the outlet temperature and STP pressure."""
        self._H_avg_Cp = None
        """attribute HeatExchanger._H_avg_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the Hot side fluid 
            as an unweighted average of the specific heat at the inlet and outlet temperatures."""
        self._C_avg_Cp = None
        """attribute HeatExchanger._C_avg_Cp : float [J/kg/K]
            Mass specific constant pressure specific heat of the cold side fluid 
            as an unweighted average of the specific heat at the inlet and outlet temperatures."""
        self._lmtd = None
        """attribute HeatExchanger._lmtd : float [K]
            The log mean temperature difference. See eq. 11.15 of [2]"""
        self._plate_material = Plate_Material
        """attribute HeatExchanger._plate_material : Metal
        see the 'Metal' class. """
        self._plate_material_name = None #self._plate_material._aliases[0]
        """attribute HeatExchanger._plate_material_name : Text
        First alias listed in Metal class object assigned to HeatExchanger._plate_material.
        see the 'Metal' class. """
        self._plate_thickness = Plate_Thickness
        """attribute HeatExchanger._plate_thickness : float [mm]
            The thickness of each plate. Requires HX._Type to be 'plate' """
        self._Ch = None
        """attribute HeatExchanger._Ch : float [W/K]
            The Heat capacity rate of the hot side fluid.
            defined as mass flow * specific heat (HX._mdot_h*HX._H_avg_Cp)"""
        self._Cc = None
        """attribute HeatExchanger._Cc : float [W/K]
            The Heat capacity rate of the cold side fluid.
            defined as mass flow * specific heat (HX._mdot_c*HX._C_avg_Cp)"""
        self._Cmin = None
        """attribute HeatExchanger._Cmin : float [W/K]
            The lesser of HX._Ch and HX._Cc"""
        self._Cmax = None
        """attribute HeatExchanger._Cmax : float [W/K]
            The greater of HX._Ch and HX._Cc"""
        self._Cr = None
        """attribute HeatExchanger._Cmax : float [dimensionless]
            The heat capacity ratio. Defined as HX._Cmin/HX._Cmax"""
        self._channels_per_pass_hot = None
        """attribute HeatExchanger._channels_per_pass : float [count]
            The number of channels for the fluid to travel through per pass. 
            Defined as (HX._Plate_count-1)/(HX._Hot_Passes*2)"""
        self._channels_per_pass_cold = None
        """attribute HeatExchanger._channels_per_pass : float [count]
            The number of channels for the fluid to travel through per pass. 
            Defined as (HX._Plate_count-1)/(HX._Hot_Passes*2)"""
        self._mdot_h_channel = None
        """attribute HeatExchanger._mdot_h_channel : float [kg/s]
            The mass flow of the hot fluid per channel.
            defined as HX._mdot_h/HX._channels_per_pass"""
        self._mdot_c_channel = None
        """attribute HeatExchanger._mdot_c_channel : float [kg/s]
            The mass flow of the cold fluid per channel.
            defined as HX._mdot_c/HX._channels_per_pass"""
        self._H_inlet_velocity = None
        """attribute HeatExchanger._H_inlet_velocity : float [m/s]
            The velocity of the hot side gas at the inlet."""
        self._H_outlet_velocity = None
        """attribute HeatExchanger._H_outlet_velocity : float [m/s]
            The velocity of the hot side gas at the outlet."""
        self._C_inlet_velocity = None
        """attribute HeatExchanger._C_inlet_velocity : float [m/s]
            The velocity of the cold side gas at the inlet."""
        self._C_outlet_velocity = None
        """attribute HeatExchanger._C_inlet_velocity : float [m/s]
            The velocity of the cold side gas at the outlet."""

        self._initial_values = [key for key, value in vars(self).items() if value is not None]
        """attribute HeatExchanger._initial_values : [list[str]]
            A list of the initally provided values at instantiation."""

        
        self._dependencies = {
            "_Thi" : [
                ["K"],
                ["_mdot_h", "_H_O_Cp", "_Tho", "_q"]
            ],
            "_H_inlet_ID": [
                ["mm"],
                ["_H_inlet_ID"]
            ],
            "_Tho" : [
                ["K"],
                ["_mdot_h", "_H_I_Cp", "_Thi", "_q"]
            ],
            "_Tci" : [
                ["K"],
                ["_mdot_c", "_C_O_Cp", "_Tco", "_q"]
            ],
            "_Tco" : [
                ["K"],
                ["_mdot_c", "_C_I_Cp", "_Tci", "_q"]
            ],
            "_H_outlet_ID" : [
                ["mm"],
                ["_H_outlet_ID"]
            ],
            "_Pres_H_in" : [
                ["Pa"],
                ["_Pres_H_in"]
            ],
            "_mdot_h" : [
                ["kg/s"],
                ["_H_in_nm3_hr", "_H_Fluid"]
            ],
            "_mdot_c" : [
                ["kg/s"],
                ["_C_in_nm3_hr", "_C_Fluid"]
            ],
            "_H_in_nm3_hr" : [
                ["nm^3/hr"],
                ["_mdot_h", "_H_Fluid"]
            ],
            "_C_in_nm3_hr" : [
                ["nm^3/hr"],
                ["_mdot_c", "_C_Fluid"]
            ],
            "_q_h" : [
                ["J/s"],
                ["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"]
            ],
            "_q_c" : [
                ["J/s"],
                ["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"]
            ],
            "_H_avg_Cp" : [
                ["J/kg/K"],
                ["_H_I_Cp", "_H_O_Cp"],
                ["_H_I_Cp"] # Fix this logic later
            ],
            "_C_avg_Cp" : [
                ["J/kg/K"],
                ["_C_I_Cp", "_C_O_Cp"],
                ["_C_I_Cp"] # Fix this logic later
            ],
            "_lmtd" : [
                ["K"],
                ["_Thi", "_Tho", "_Tci", "_Tco"]
            ],
            "_q" : [
                ["J/s"],
                ["_q_h", "_q_c"],
                ["_q_c"],
                ["_q_h"],
                ["_q_max", "_effectiveness_epsilon"]
            ],
            "_q_max" : [
                ["J/s"],
                ["_Cmin", "_Thi", "_Tci"]
            ],
            "_UA" : [
                ["W/K"],
                ["_q", "_lmtd"],
                ["_NTU", "_Cmin"]
            ],
            "_Ch" : [
                ["W/K"],
                ["_mdot_h", "_H_avg_Cp"]
            ],
            "_Cc" : [
                ["W/K"],
                ["_mdot_c", "_C_avg_Cp"]
            ],
            "_Cmin" : [
                ["W/K"],
                ["_Flow_Direction", "_Cc", "_Ch"]
            ],
            "_Cmax" : [
                ["W/K"],
                ["_Flow_Direction", "_Cc", "_Ch"]
            ],
            "_effectiveness_epsilon" : [
                ["% as decimal"],
                ["_q", "_q_max"],
                ["_NTU", "_Cr", "_Flow_Direction", "_Type"]
            ],
            "_NTU" : [
                ["(dimensionless)"],
                ["_Cmin", "_UA"]
            ],
            "_Cr" : [
                ["% as decimal"],
                ["_Cmin", "_Cmax"]
            ],
            "_channels_per_pass_hot" : [
                ["channels per pass"],
                ["_Plate_count", "_Plate_Distribution_Bias"]
            ],

            "_channels_per_pass_cold" : [
                ["channels per pass"],
                ["_Plate_count", "_Plate_Distribution_Bias"]
            ],

            "_mdot_h_channel" : [
                ["kg/s"],
                ["_mdot_h", "_channels_per_pass_hot"]
            ],
            "_mdot_c_channel" : [
                ["kg/s"],
                ["_mdot_c", "_channels_per_pass_cold"]
            ],
            "_H_inlet_velocity" : [
                ["m/s"],
                ["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"]
            ],
            "_H_outlet_velocity" : [
                ["m/s"],
                ["_mdot_h", "_H_outlet_ID", "_Pres_H_in", "_H_Fluid", "_Tho"]
            ],
            "_C_inlet_velocity" : [
                ["m/s"],
                ["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"]
            ],
            "_C_outlet_velocity" : [
                ["m/s"],
                ["_mdot_c", "_C_outlet_ID", "_Pres_C_in", "_C_Fluid", "_Tco"]
            ],
            "_H_I_Cp" : [
                ["J/kg/K"],
                ["_Thi", "_H_Fluid"]
            ],
            "_H_O_Cp" : [
                ["J/kg/K"],
                ["_Tho", "_H_Fluid"]
            ],
            "_C_I_Cp" : [
                ["J/kg/K"],
                ["_Tci", "_C_Fluid"]
            ],
            "_C_O_Cp" : [
                ["J/kg/K"],
                ["_Tco", "_C_Fluid"]
            ]
        }




    def solve_attribute(self, attribute, dependency_option):
        """All Equations for solving for unknown values"""

        if attribute == "_Thi":
            if dependency_option == ["_mdot_h", "_H_O_Cp", "_Tho", "_q"]:
                self._Thi = self._q/(self._mdot_h*self._H_O_Cp)+self._Tho
                return self._Thi

        elif attribute == "_H_inlet_ID":
            if dependency_option == ["_H_inlet_ID"]:
                return self._H_inlet_ID
        
        elif attribute == "_Tho":
            if dependency_option == ["_mdot_h", "_H_I_Cp", "_Thi", "_q"]:
                self._Tho = -1*(self._q/(self._mdot_h*self._H_I_Cp)-self._Thi)
                return self._Tho
            
        elif attribute == "_Tci":
            if dependency_option == ["_mdot_c", "_C_O_Cp", "_Tco", "_q"]:
                self._Tci = -1*(self._q/(self._mdot_c*self._C_O_Cp)-self._Tco)
                return self._Tci
        
        elif attribute == "_Tco":
            if dependency_option == ["_mdot_c", "_C_I_Cp", "_Tci", "_q"]:
                self._Tco = self._q/(self._mdot_c*self._C_I_Cp)+self._Tci
                return self._Tco

        elif attribute == "_mdot_h":
            if dependency_option == ["_H_in_nm3_hr", "_H_Fluid"]:
                self._mdot_h = unit_convert(self._H_in_nm3_hr, "Nm^3/hr", "kg/s", self._H_Fluid)
                return self._mdot_h
            
        elif attribute == "_mdot_c":
            if dependency_option == ["_C_in_nm3_hr", "_C_Fluid"]:
                self._mdot_c = unit_convert(self._C_in_nm3_hr, "Nm^3/hr", "kg/s", self._C_Fluid)
                return self._mdot_c
            
        elif attribute == "_H_in_nm3_hr":
            if dependency_option ==  ["_mdot_h", "_H_Fluid"]:
                self._H_in_nm3_hr = unit_convert(self._mdot_h, "kg/s", "Nm^3/hr", self._H_Fluid)
                return self._H_in_nm3_hr
        
        elif attribute == "_C_in_nm3_hr":
            if dependency_option ==  ["_mdot_c", "_C_Fluid"]:
                self._C_in_nm3_hr = unit_convert(self._mdot_c, "kg/s", "Nm^3/hr", self._C_Fluid)
                return self._C_in_nm3_hr                

        elif attribute == "_q_h":
            if dependency_option == ["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"]:
                self._q_h = (self._mdot_h*self._H_avg_Cp*(self._Thi-self._Tho))
                return self._q_h

        elif attribute == "_q_c":
            if dependency_option == ["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"]:
                self._q_c = self._mdot_c*self._C_avg_Cp*(self._Tco-self._Tci)
                return self._q_c
        
        elif attribute == "_H_avg_Cp":
            if dependency_option == ["_H_I_Cp", "_H_O_Cp"]:
                self._H_avg_Cp = (self._H_O_Cp+self._H_I_Cp)/2
            elif dependency_option == ["_H_I_Cp"]:
                self._H_avg_Cp = self._H_I_Cp
            return self._H_avg_Cp
        
        elif attribute == "_C_avg_Cp":
            if dependency_option == ["_C_I_Cp", "_C_O_Cp"]:
                self._C_avg_Cp = (self._C_O_Cp+self._C_I_Cp)/2
            elif dependency_option == ["_C_I_Cp"]:
                self._C_avg_Cp = self._C_I_Cp
            return self._C_avg_Cp
        
        elif attribute == "_lmtd":
            if dependency_option == ["_Thi", "_Tho", "_Tci", "_Tco"]:
                self._lmtd = LMTD(Tci = self._Tci, Tco = self._Tco, Thi = self._Thi, Tho = self._Tho, counterflow=self._Flow_Direction)
                return self._lmtd
            
        elif attribute == "_q":
            if dependency_option == ["_q_h", "_q_c"]:
                self._q = max(self._q_h, self._q_c)
            elif dependency_option == ["_q_c"]:
                self._q = self._q_c
            elif dependency_option == ["_q_h"]:
                self._q = self._q_h
            elif dependency_option == ["_q_max", "_effectiveness_epsilon"]:
                self._q = self._q_max*self._effectiveness_epsilon
            return self._q

        elif attribute == "_q_max":
            if dependency_option == ["_Cmin", "_Thi", "_Tci"]:
                self._q_max = self._Cmin*(self._Thi-self._Tci)
                return self._q_max

        elif attribute == "_UA":
            if dependency_option == ["_q", "_lmtd"]:
                self._UA = self._q/(self._lmtd * self._F_sub_T)    
            elif dependency_option == ["_NTU", "_Cmin"]:
                self._UA = self._NTU*self._Cmin
            return self._UA

        elif attribute == "_Ch":
            if dependency_option == ["_mdot_h", "_H_avg_Cp"]:
                self._Ch = self._mdot_h*self._H_avg_Cp
            return self._Ch

        elif attribute == "_Cc":
            if dependency_option == ["_mdot_c", "_C_avg_Cp"]:
                self._Cc = self._mdot_c*self._C_avg_Cp
            return self._Cc
            
        elif attribute == "_Cmin":
            if dependency_option == ["_Flow_Direction", "_Cc", "_Ch"]:
                if self._Flow_Direction:
                    self._Cmin = self._Cc
                else:
                    self._Cmin = self._Ch
            return self._Cmin

        elif attribute == "_Cmax":
            if dependency_option == ["_Flow_Direction", "_Cc", "_Ch"]:
                if self._Flow_Direction:
                    self._Cmax = self._Ch
                else:
                    self._Cmax = self._Cc
            return self._Cmax
            
        elif attribute == "_effectiveness_epsilon":
            if dependency_option == ["_q", "_q_max"]:
                self._effectiveness_epsilon = self._q/self._q_max    
            elif dependency_option == ["_NTU", "_Cr", "_Flow_Direction", "_Type"]: # Equation 11.32 in reference [2]. Need to add flow direction, hx type, etc. logic
                if self._Type == "crossflow":
                    self._effectiveness_epsilon = 1 - (m.exp( (1/self._Cr) * (pow(self._NTU, 0.22)) * (m.exp((-1*self._Cr) * pow(self._NTU,0.78)) -1) ))
                elif self._Type == "plate":
                    if self._Flow_Direction:
                        if self._Cr == 1:
                            self._effectiveness_epsilon = self._NTU/(1+self._NTU)
                        elif self._Cr <= 1:
                            self._effectiveness_epsilon = (1-m.exp((-self._NTU)*(1-self._Cr))) / (1-(self._Cr*m.exp((-self._NTU)*(1-self._Cr))))
                    else:
                        self._effectiveness_epsilon = (1-m.exp((-self._NTU)*(1+self._Cr))) / (1+self._Cr)
            return self._effectiveness_epsilon

        elif attribute == "_NTU":
            if dependency_option == ["_Cmin", "_UA"]:
                self._NTU = self._UA/self._Cmin
            return self._NTU
        
        elif attribute == "_Cr":
            if dependency_option == ["_Cmin", "_Cmax"]:
                self._Cr = self._Cmin/self._Cmax
            return self._Cr
        
        elif attribute == "_channels_per_pass_hot":
            if dependency_option == ["_Plate_count", "_Plate_Distribution_Bias"]:
                if self._Plate_count % 2 == 0:
                    if self._Plate_Distribution_Bias == "hot":
                        self._channels_per_pass_hot = (self._Plate_count-1)/(2) + 0.5
                else:
                    self._channels_per_pass_hot = (self._Plate_count-1)/(2) - 0.5
            return self._channels_per_pass_hot, self._channels_per_pass_cold
        
        elif attribute == "_channels_per_pass_cold":
            if dependency_option == ["_Plate_count", "_Plate_Distribution_Bias"]:
                if self._Plate_count % 2 == 0:
                    if self._Plate_Distribution_Bias == "hot":
                        self._channels_per_pass_cold = (self._Plate_count-1)/(2) - 0.5
                else:
                    self._channels_per_pass_cold = (self._Plate_count-1)/(2) + 0.5
            return self._channels_per_pass_cold
            
        elif attribute == "_mdot_h_channel":
            if dependency_option == ["_mdot_h", "_channels_per_pass_hot"]:
                self._mdot_h_channel = self._mdot_h/self._channels_per_pass_hot
            return self._mdot_h_channel

        elif attribute == "_mdot_c_channel":
            if dependency_option == ["_mdot_c", "_channels_per_pass_cold"]:
                self._mdot_c_channel = self._mdot_c/self._channels_per_pass_cold
            return self._mdot_c_channel
        
        elif attribute == "_H_inlet_velocity":
            if dependency_option == ["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"]:
                density = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                area = pow((self._H_inlet_ID/1000)/2,2)*self.PI #m^2
                self._H_inlet_velocity = self._mdot_h/(density*area)
            return self._H_inlet_velocity

        elif attribute == "_H_outlet_velocity":
            if dependency_option == ["_mdot_h", "_H_outlet_ID", "_Pres_H_in", "_H_Fluid", "_Tho"]:
                density = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", self._Pres_H_in)
                area = pow((self._H_outlet_ID/1000)/2,2)*self.PI #m^2
                self._H_outlet_velocity = self._mdot_h/(density*area)
            return self._H_outlet_velocity
        
        elif attribute == "_C_inlet_velocity":
            if dependency_option == ["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"]:
                density = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
                area = pow((self._C_inlet_ID/1000)/2,2)*self.PI #m^2
                self._C_inlet_velocity = self._mdot_c/(density*area)
                return self._C_inlet_velocity
            
        elif attribute == "_C_outlet_velocity":
            if dependency_option == ["_mdot_c", "_C_outlet_ID", "_Pres_C_in", "_C_Fluid", "_Tco"]:
                density = getfluidproperty(self._C_Fluid, "D", "T", self._Tco, "P", self._Pres_C_in)
                area = pow((self._C_outlet_ID/1000)/2,2)*self.PI #m^2
                self._C_outlet_velocity = self._mdot_c/(density*area)
            return self._C_outlet_velocity
        
        elif attribute == "_H_I_Cp":
            if dependency_option == ["_Thi", "_H_Fluid"]:
                self._H_I_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1))
            elif dependency_option == ["_Tho", "_H_Fluid"]:
                #Add Iterative logic here for solving H_I_Cp to get Thi then resolving
                self._H_I_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1))
            return(self._H_I_Cp) 
            
        elif attribute == "_H_O_Cp":
            if dependency_option == ["_Tho", "_H_Fluid"]:
                self._H_O_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1))  
            elif dependency_option == ["_Thi", "_H_Fluid"]:
                #Add Iterative logic here for solving H_O_Cp to get Tho then resolving
                self._H_O_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1))
            return(self._H_O_Cp)
            
        elif attribute == "_C_I_Cp":
            if dependency_option == ["_Tci", "_C_Fluid"]:
                self._C_I_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1))
            elif dependency_option == ["_Tco", "_C_Fluid"]:
                #Add Iterative logic here for solving C_I_Cp to get Tci then resolving
                self._C_I_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1))
            return(self._C_I_Cp)
            
        elif attribute == "_C_O_Cp":
            if dependency_option == ["_Tco", "_C_Fluid"]:
                self._C_O_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1))
            elif dependency_option == ["_Tci", "_C_Fluid"]:
                #Add Iterative logic here for solving C_I_Cp to get Tci then resolving
                self._C_O_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1))
            return(self._C_O_Cp)




    def pretty_print(self):
        spacing = 25
        digits = 6
        suppressed_values = ["_dependencies", "_initial_values", "_Name", "_plate_material", "known_attributes", "unknown_attributes"]

        festive_decorations = "--------------------------------------------"
        print(festive_decorations)
        print("HX Instance:",self._Name)
        print(".... = Provided, ____ = Evaluated")
        print(festive_decorations)
        for k, v in self.__dict__.items():
            if k in self._initial_values: 
                space_symbol = "."
            else: 
                space_symbol = "_"
            if k not in suppressed_values:
                if v != None:
                    pass
                else:
                    v = "?"
                try:
                    try:
                        unit = self._dependencies[k][0][0]
                    except KeyError:
                        unit = ""
                    print(f"{k.replace("_","",1):<{spacing}}{round(v,digits)}".replace(" ",space_symbol),unit)
                except TypeError:
                    print(f"{k.replace("_","",1):<{spacing}}{v}".replace(" ",space_symbol))



    def solve_hx(self, quiet=False):
        known_attributes = [k for k, v in vars(self).items() if v is not None]
        unknown_attributes = [k for k, v in vars(self).items() if v is None]
        solved_attributes = []
        iteration = 0

        while True:
            progressed = False
            for attribute in unknown_attributes[:]:  
                try:
                    dependencies = self._dependencies[attribute]
                except KeyError:
                    continue
                for dependency_option in dependencies:
                    if set(dependency_option).issubset(set(known_attributes)):
                        if not quiet:
                            print("solving", attribute, "using", dependency_option)
                        self.solve_attribute(attribute, dependency_option)
                        unknown_attributes.remove(attribute)
                        known_attributes.append(attribute)
                        solved_attributes.append(attribute)
                        progressed = True
                        break
            if not progressed:
                if not quiet:
                    print("Iteration complete; solved attributes:", solved_attributes)
                break
            iteration += 1

        self.known_attributes = known_attributes
        self.unknown_attributes = unknown_attributes
        return self.known_attributes, self.unknown_attributes
    
    
    # ───────────────── v in vars(self).items() if v is not None]

    def _dependency_options_for(self, attribute):
        """
        Return the list of dependency options (each a list of attribute names)
        for a given attribute, skipping the first entry which holds units.
        """
        try:
            entries = self._dependencies[attribute]
        except KeyError:
            return []
        # first sublist is units; subsequent sublists are options
        return [opt for opt in entries[1:] if isinstance(opt, list)]

    def dependency_status(self, attribute, known_attributes=None):
        """
        For a target attribute, return a list of dicts:
        [{ 'option': [...], 'met': bool, 'missing': [...] }, ...]
        """
        known = set(self.known_attributes() if known_attributes is None else known_attributes)
        status = []
        for opt in self._dependency_options_for(attribute):
            missing = [dep for dep in opt if dep not in known]
            status.append({
                "option": opt,
                "met": len(missing) == 0,
                "missing": missing
            })
        return status

    def _humanize_attr(self, attr, mapping=None):
        """Prettify an internal name, or map via UI label mapping if provided."""
        if mapping and attr in mapping:
            return str(mapping[attr])
        s = attr[1:] if isinstance(attr, str) and attr.startswith('_') else str(attr)
        return s.replace('_', ' ').title()

    def dependency_tooltip(self, attribute, known_attributes=None, ui_friendly_names=None):
        """
        Build an HTML tooltip listing dependency options for `attribute`.
        - Met options in black; unmet in red, with missing listed.
        - `ui_friendly_names`: optional dict mapping internal names to UI labels.
        """
        if attribute not in self._dependencies:
            return f"<b>No dependencies registered for <code>{attribute}</code></b>"

        unit = ""
        try:
            unit = self._dependencies[attribute][0][0] or ""
        except Exception:
            pass

        status_list = self.dependency_status(attribute, known_attributes=known_attributes)
        title_name = self._humanize_attr(attribute, ui_friendly_names)
        unit_str = f" &nbsp;<span style='color:#666'>(unit: {unit})</span>" if unit else ""

        html = [f"<b>How to solve <code>{title_name}</code></b>{unit_str}"]
        html.append("<ul style='margin-left:0.9em; padding-left:1.0em;'>")

        if not status_list:
            html.append("<li style='color:#cc0000;'>No dependency options listed</li>")
        else:
            for st in status_list:
                color = "#000000" if st["met"] else "#cc0000"
                deps = ", ".join(self._humanize_attr(x, ui_friendly_names) for x in st["option"])
                if st["met"]:
                    html.append(f"<li style='color:{color};'><code>{deps}</code></li>")
                else:
                    missing = ", ".join(self._humanize_attr(x, ui_friendly_names) for x in st["missing"])
                    html.append(
                        f"<li style='color:{color};'><code>{deps}</code> — missing: {missing}</li>"
                    )

        html.append("</ul>")
        return "".join(html)
    #────────────────────────────────────────────────────────────
    # Dependency introspection & tooltip helpers (for UI hover tooltips)
    # ─────────────────────────────────────────────────────────────────────────────
    def known_attributes(self):
        """Return attributes that are currently set (value is not None)."""
        return [k for k, v in vars(self).items() if v is not None]