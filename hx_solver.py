# hx_solver.py  — enhanced solver with bidirectional pressure solving,
# target-velocity sizing, inverse plate geometry, and formula-rich tooltips.

import math as m

from utilities import getfluidproperty, unit_convert, atm2Pa, LMTD  # uses your utilities.py
from mat_lib import Material, SS316
from thermal_solver import material_mapping


class HeatExchanger:
    """
    A Heat Exchanger model with dependency-driven solving.
    Adds: pressure in/out solving, target-velocity sizing, inverse geometry,
    math fixes (Cmin/Cmax, q blending), and LaTeX-style formulas in tooltips.
    """

    HR_SECS = 3600
    PI = 3.141592653589793

    # --------------------------------------------------------------------- #
    # Construction
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        Name=None,
        # Hot side
        H_Inlet_Temp=None,
        H_Inlet_ID=None,
        H_Outlet_Temp=None,
        H_Outlet_ID=None,
        H_Inlet_Pres=None,
        H_In_Mass_Flow=None,
        H_In_Vol_Flow_nm3=None,
        H_Fluid=None,
        # NEW: allow providing outlet pressure too
        H_Outlet_Pres=None,
        # Cold side
        C_Inlet_Temp=None,
        C_Inlet_ID=None,
        C_Outlet_Temp=None,
        C_Outlet_ID=None,
        C_Inlet_Pres=None,
        C_In_Mass_Flow=None,
        C_In_Vol_Flow_nm3=None,
        C_Fluid=None,
        # NEW: allow providing outlet pressure too
        C_Outlet_Pres=None,
        # HX type / direction
        HX_Type="plate",
        Counter_Flow=True,
        # Heat/UA/NTU/effectiveness
        q=None,
        q_max=None,
        effectiveness_U=None,
        effectiveness_epsilon=None,
        ntu=None,
        area=None,
        UA=None,
        F_sub_T=1.0,
        # Plate material/geometry
        Plate_Material=SS316,
        Plate_Thickness=0.6,  # [mm]
        Plate_Count=None,
        Plate_Distribution_Bias="hot",
        mean_channel_gap=None,  # [mm]
        enlargement_factor_phi=None,  # [-]
        Total_Hot_Channel_Volume=None,
        Total_Cold_Channel_Volume=None,
        Per_Channel_Volume=None,
        Hot_Passes=1,
        # NEW: target velocities (optional, used for ID or mdot sizing)
        H_Target_Velocity=None,  # [m/s]
        C_Target_Velocity=None,  # [m/s]
    ):
        # identity
        self._Name = Name

        # Hot side (Kelvin, mm, Pa, kg/s, Nm^3/hr, fluid)
        self._Thi = H_Inlet_Temp
        self._H_inlet_ID = H_Inlet_ID
        self._Tho = H_Outlet_Temp
        self._H_outlet_ID = H_Outlet_ID
        self._Pres_H_in = H_Inlet_Pres
        self._Pres_H_out = H_Outlet_Pres  # NEW
        self._mdot_h = H_In_Mass_Flow
        self._H_in_nm3_hr = H_In_Vol_Flow_nm3
        self._H_Fluid = H_Fluid

        # Cold side
        self._Tci = C_Inlet_Temp
        self._C_inlet_ID = C_Inlet_ID
        self._Tco = C_Outlet_Temp
        self._C_outlet_ID = C_Outlet_ID
        self._Pres_C_in = C_Inlet_Pres
        self._Pres_C_out = C_Outlet_Pres  # NEW
        self._mdot_c = C_In_Mass_Flow
        self._C_in_nm3_hr = C_In_Vol_Flow_nm3
        self._C_Fluid = C_Fluid

        # Type/flow
        self._Type = HX_Type
        self._Flow_Direction = Counter_Flow

        # Heat/UA/NTU/effectiveness
        self._q = q
        self._q_h = q
        self._q_c = q
        self._q_max = q_max
        self._U = effectiveness_U
        self._effectiveness_epsilon = effectiveness_epsilon
        self._NTU = ntu
        self._A = area
        self._UA = UA
        self._F_sub_T = F_sub_T

        # Plate specifics
        self._Plate_count = Plate_Count
        self._Plate_Distribution_Bias = Plate_Distribution_Bias
        self._mean_channel_gap = mean_channel_gap  # [mm]
        self._enlargement_phi = enlargement_factor_phi  # [-]
        self._Total_Hot_Ch_Vol = Total_Hot_Channel_Volume
        self._Total_Cold_Ch_Vol = Total_Cold_Channel_Volume
        self._Per_Ch_Vol = Per_Channel_Volume
        self._Hot_Passes = Hot_Passes
        self._plate_material = Plate_Material
        self._plate_material_name = None
        self._plate_thickness = Plate_Thickness  # [mm]

        # Target velocities (optional helper specs)
        self._H_target_velocity = H_Target_Velocity  # [m/s]
        self._C_target_velocity = C_Target_Velocity  # [m/s]

        # Cp buckets
        self._H_I_Cp = None
        self._H_O_Cp = None
        self._C_I_Cp = None
        self._C_O_Cp = None
        self._H_avg_Cp = None
        self._C_avg_Cp = None
        # Derived thermal
        self._lmtd = None
        self._Ch = None
        self._Cc = None
        self._Cmin = None
        self._Cmax = None
        self._Cr = None

        # Channeling
        self._channels_per_pass_hot = None
        self._channels_per_pass_cold = None
        self._mdot_h_channel = None
        self._mdot_c_channel = None

        # Velocities
        self._H_inlet_velocity = None
        self._H_outlet_velocity = None
        self._C_inlet_velocity = None
        self._C_outlet_velocity = None

        # Keep list of initial values
        self._initial_values = [key for key, value in vars(self).items() if value is not None]

        # HX-type gates
        self._HX_is_plate = True if (str(self._Type).lower() == "plate") else None
        self._HX_is_st = True if (str(self._Type).lower() == "shell & tube") else None
        self._HX_is_ache = True if (str(self._Type).lower() == "air-cooled") else None

        # ------------------------------------------------------------------ #
        # Dependency graph: [ [unit], [option1 deps], [option2 deps], ... ]
        # (NEW) adds pressure-out, inverse dP, velocity-target sizing, inverse
        #       plate geometry, and fixes Cmin/Cmax definitions.
        # ------------------------------------------------------------------ #
        self._dependencies = {
            "_Thi": [["K"], ["_mdot_h", "_H_O_Cp", "_Tho", "_q"]],
            "_H_inlet_ID": [["mm"], ["_H_inlet_ID"],  # pass-through
                            # NEW: ID from target v
                            ["_mdot_h", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"]],
            "_Tho": [["K"], ["_mdot_h", "_H_I_Cp", "_Thi", "_q"]],
            "_Tci": [["K"], ["_mdot_c", "_C_O_Cp", "_Tco", "_q"]],
            "_Tco": [["K"], ["_mdot_c", "_C_I_Cp", "_Tci", "_q"]],
            "_H_outlet_ID": [["mm"], ["_H_outlet_ID"],
                             # NEW: outlet ID from target v
                             ["_mdot_h", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]],
            "_Pres_H_in": [["Pa"], ["_Pres_H_in"],
                           # NEW: back-solve inlet from outlet & dP
                           ["_Pres_H_out", "_dP_h"]],
            "_Pres_H_out": [["Pa"],  # NEW
                            ["_Pres_H_in", "_dP_h"]],
            "_mdot_h": [["kg/s"],
                        ["_H_in_nm3_hr", "_H_Fluid"],
                        # NEW: mdot from ID and target velocity (inlet)
                        ["_H_inlet_ID", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"],
                        # NEW: mdot from ID and target velocity (outlet)
                        ["_H_outlet_ID", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]],
            "_mdot_c": [["kg/s"],
                        ["_C_in_nm3_hr", "_C_Fluid"],
                        # NEW: mdot from ID and target velocity (inlet)
                        ["_C_inlet_ID", "_C_target_velocity", "_Pres_C_in", "_Tci", "_C_Fluid"],
                        # NEW: mdot from ID and target velocity (outlet)
                        ["_C_outlet_ID", "_C_target_velocity", "_Pres_C_out", "_Tco", "_C_Fluid"]],
            "_H_in_nm3_hr": [["nm^3/hr"], ["_mdot_h", "_H_Fluid"]],
            "_C_in_nm3_hr": [["nm^3/hr"], ["_mdot_c", "_C_Fluid"]],
            "_q_h": [["J/s"], ["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"]],
            "_q_c": [["J/s"], ["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"]],
            "_H_avg_Cp": [["J/kg/K"], ["_H_I_Cp", "_H_O_Cp"], ["_H_I_Cp"]],
            "_C_avg_Cp": [["J/kg/K"], ["_C_I_Cp", "_C_O_Cp"], ["_C_I_Cp"]],
            "_lmtd": [["K"], ["_Thi", "_Tho", "_Tci", "_Tco"]],
            "_q": [["J/s"],
                   ["_q_h", "_q_c"],
                   ["_q_c"],
                   ["_q_h"],
                   ["_q_max", "_effectiveness_epsilon"]],
            "_q_max": [["J/s"], ["_Cmin", "_Thi", "_Tci"]],
            "_UA": [["W/K"], ["_q", "_lmtd"], ["_NTU", "_Cmin"]],
            "_Ch": [["W/K"], ["_mdot_h", "_H_avg_Cp"]],
            "_Cc": [["W/K"], ["_mdot_c", "_C_avg_Cp"]],
            # FIX: Cmin/Cmax are min/max, independent of flow direction
            "_Cmin": [["W/K"], ["_Cc", "_Ch"]],
            "_Cmax": [["W/K"], ["_Cc", "_Ch"]],
            "_effectiveness_epsilon": [["% as decimal"],
                                       ["_q", "_q_max"],
                                       ["_NTU", "_Cr", "_Flow_Direction", "_Type"]],
            "_NTU": [["(dimensionless)"], ["_Cmin", "_UA"]],
            "_Cr": [["% as decimal"], ["_Cmin", "_Cmax"]],
            "_channels_per_pass_hot": [["channels per pass"], ["_Plate_count", "_Plate_Distribution_Bias"]],
            "_channels_per_pass_cold": [["channels per pass"], ["_Plate_count", "_Plate_Distribution_Bias"]],
            "_mdot_h_channel": [["kg/s"], ["_mdot_h", "_channels_per_pass_hot"]],
            "_mdot_c_channel": [["kg/s"], ["_mdot_c", "_channels_per_pass_cold"]],
            "_H_inlet_velocity": [["m/s"], ["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"]],
            # prefer outlet pressure if available (declare a second option)
            "_H_outlet_velocity": [["m/s"],
                                   ["_mdot_h", "_H_outlet_ID", "_Pres_H_out", "_H_Fluid", "_Tho"],
                                   ["_mdot_h", "_H_outlet_ID", "_Pres_H_in", "_H_Fluid", "_Tho"]],
            "_C_inlet_velocity": [["m/s"], ["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"]],
            "_C_outlet_velocity": [["m/s"],
                                   ["_mdot_c", "_C_outlet_ID", "_Pres_C_out", "_C_Fluid", "_Tco"],
                                   ["_mdot_c", "_C_outlet_ID", "_Pres_C_in", "_C_Fluid", "_Tco"]],
            "_H_I_Cp": [["J/kg/K"], ["_Thi", "_H_Fluid"]],
            "_H_O_Cp": [["J/kg/K"], ["_Tho", "_H_Fluid"]],
            "_C_I_Cp": [["J/kg/K"], ["_Tci", "_C_Fluid"]],
            "_C_O_Cp": [["J/kg/K"], ["_Tco", "_C_Fluid"]],
            # NEW: target velocity "inputs" (units shown in UI tooltip)
            "_H_target_velocity": [["m/s"], ["_H_target_velocity"]],
            "_C_target_velocity": [["m/s"], ["_C_target_velocity"]],
        }

        # ---------------------- PLATE thermo–hydraulics ------------------- #
        # Geometry inputs [m unless noted]; fouling [m^2·K/W]
        self._Lv = None
        self._Lh = None
        self._Dp = None
        self._pitch = None
        self._t_m = None  # plate thickness [m]
        self._fouling_hot = 0.0
        self._fouling_cold = 0.0

        # Derived geometry
        self._Lp = None
        self._Lw = None
        self._Aproj = None
        self._Dh = None
        self._Aff_hot = None
        self._Aff_cold = None

        # Transport & non-dim
        self._mu_h = None
        self._mu_c = None
        self._k_h = None
        self._k_c = None
        self._Pr_h = None
        self._Pr_c = None
        self._G_h = None
        self._G_c = None
        self._Re_h = None
        self._Re_c = None

        # Films/overall U
        self._h_h = None
        self._h_c = None
        self._U_calc = None

        # Pressure drops
        self._dP_h = None
        self._dP_c = None
        self._dP_total = None

        # ε–NTU & entropy
        self._epsilon_NTU = None
        self._Tho_eps = None
        self._Tco_eps = None
        self._S_gen = None
        self._Ns = None

        self._dependencies.update({
            "_t_m": [["m"], ["_HX_is_plate", "_plate_thickness"]],
            "_Lp": [["m"], ["_HX_is_plate", "_Lv", "_Dp"]],
            "_Lw": [["m"], ["_HX_is_plate", "_Lh", "_Dp"]],
            "_Aproj": [["m^2"], ["_HX_is_plate", "_Lp", "_Lw"]],
            "_Dh": [["m"], ["_HX_is_plate", "_mean_channel_gap", "_enlargement_phi"]],
            "_Aff_hot": [["m^2"], ["_HX_is_plate", "_Lw", "_mean_channel_gap"]],
            "_Aff_cold": [["m^2"], ["_HX_is_plate", "_Lw", "_mean_channel_gap"]],
            "_mu_h": [["Pa·s"], ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]],
            "_mu_c": [["Pa·s"], ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]],
            "_k_h": [["W/m/K"], ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]],
            "_k_c": [["W/m/K"], ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]],
            "_Pr_h": [["(dimensionless)"], ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]],
            "_Pr_c": [["(dimensionless)"], ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]],
            "_G_h": [["kg/m^2/s"], ["_HX_is_plate", "_mdot_h_channel", "_Aff_hot"]],
            "_G_c": [["kg/m^2/s"], ["_HX_is_plate", "_mdot_c_channel", "_Aff_cold"]],
            "_Re_h": [["(dimensionless)"], ["_HX_is_plate", "_G_h", "_Dh", "_mu_h"]],
            "_Re_c": [["(dimensionless)"], ["_HX_is_plate", "_G_c", "_Dh", "_mu_c"]],
            "_h_h": [["W/m^2/K"], ["_HX_is_plate", "_Re_h", "_Pr_h", "_k_h", "_Dh"]],
            "_h_c": [["W/m^2/K"], ["_HX_is_plate", "_Re_c", "_Pr_c", "_k_c", "_Dh"]],
            "_U_calc": [["W/m^2/K"], ["_HX_is_plate", "_h_h", "_h_c", "_t_m", "_plate_material",
                                      "_fouling_hot", "_fouling_cold"]],
            "_dP_h": [["Pa"],
                      # legacy correlation branch
                      ["_HX_is_plate", "_Re_h", "_G_h", "_Dh", "_Lp", "_H_Fluid", "_Thi", "_Pres_H_in"],
                      # NEW: dP from two pressures
                      ["_Pres_H_in", "_Pres_H_out"]],
            "_dP_c": [["Pa"],
                      ["_HX_is_plate", "_Re_c", "_G_c", "_Dh", "_Lp", "_C_Fluid", "_Tci", "_Pres_C_in"],
                      # NEW: dP from two pressures
                      ["_Pres_C_in", "_Pres_C_out"]],
            "_dP_total": [["Pa"], ["_HX_is_plate", "_dP_h", "_dP_c"]],
            "_epsilon_NTU": [["(dimensionless)"], ["_NTU", "_Cr", "_Flow_Direction"]],
            "_Tho_eps": [["K"], ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch"]],
            "_Tco_eps": [["K"], ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Cc"]],
            "_S_gen": [["W/K"], ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci",
                                 "_Ch", "_Cc", "_dP_h", "_dP_c", "_H_Fluid", "_C_Fluid"]],
            "_Ns": [["(dimensionless)"], ["_HX_is_plate", "_S_gen", "_Cmax"]],
            # NEW: inverse plate geometry options
            "_mean_channel_gap": [["mm"], ["_HX_is_plate", "_Dh", "_enlargement_phi"]],
            "_enlargement_phi": [["(dimensionless)"], ["_HX_is_plate", "_Dh", "_mean_channel_gap"]],
        })

        # -------------------- SHELL & TUBE (unchanged logic) -------------- #
        self._ST_hot_in_tube = None  # 1 hot in tubes, 0 cold in tubes
        self._ST_N_tubes = None
        self._ST_N_tube_passes = None
        self._ST_N_shell_passes = None
        self._ST_Di = None  # [m]
        self._ST_Do = None  # [m]
        self._ST_L_pass = None  # [m]
        self._ST_k_wall = None  # [W/m/K]
        self._ST_Rf_i = 0.0  # [m^2 K/W]
        self._ST_Rf_o = 0.0  # [m^2 K/W]
        self._ST_h_o = None  # [W/m^2/K] (user or estimated)
        self._ST_L_total = None
        self._ST_N_tubes_per_pass = None
        self._ST_Ai = None
        self._ST_Ao = None
        self._ST_Re_tube = None
        self._ST_Nu_tube = None
        self._ST_h_i = None
        self._ST_U = None
        self._ST_UA = None
        self._dependencies.update({
            "_ST_L_total": [["m"], ["_HX_is_st", "_ST_L_pass", "_ST_N_tube_passes"]],
            "_ST_N_tubes_per_pass": [["(count)"], ["_HX_is_st", "_ST_N_tubes", "_ST_N_tube_passes"]],
            "_ST_Ai": [["m^2"], ["_HX_is_st", "_ST_Di", "_ST_L_total", "_ST_N_tubes"]],
            "_ST_Ao": [["m^2"], ["_HX_is_st", "_ST_Do", "_ST_L_total", "_ST_N_tubes"]],
            "_ST_Re_tube": [["(dimensionless)"],
                            ["_HX_is_st", "_ST_hot_in_tube", "_ST_Di", "_ST_N_tubes_per_pass",
                             "_mdot_h", "_mdot_c", "_H_Fluid", "_C_Fluid", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]],
            "_ST_Nu_tube": [["(dimensionless)"],
                            ["_HX_is_st", "_ST_Re_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube",
                             "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]],
            "_ST_h_i": [["W/m^2/K"],
                        ["_HX_is_st", "_ST_Nu_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube",
                         "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in", "_ST_Di"]],
            "_ST_U": [["W/m^2/K"],
                      ["_HX_is_st", "_ST_h_i", "_ST_h_o", "_ST_Rf_i", "_ST_Rf_o", "_ST_k_wall",
                       "_ST_Di", "_ST_Do", "_ST_Ai", "_ST_Ao", "_ST_L_total"]],
            "_ST_UA": [["W/K"], ["_HX_is_st", "_ST_U", "_ST_Ai"]],
        })

        # -------------------- AIR-COOLED / COMPACT (unchanged logic) ------ #
        self._ACH_A_fr = None
        self._ACH_V = None
        self._ACH_sigma = None
        self._ACH_Dh = None
        self._ACH_alpha = None
        self._ACH_Af_over_A = None
        self._ACH_eta_f = None
        self._ACH_eta_o_hot = None
        self._ACH_jH = None
        self._ACH_f_core = None
        self._ACH_A = None
        self._ACH_Aff = None
        self._ACH_G_hot = None
        self._ACH_h_hot = None
        self._ACH_eta_o_resolved = None
        self._ACH_U = None
        self._ACH_dp_core = None
        self._dependencies.update({
            "_ACH_Aff": [["m^2"], ["_HX_is_ache", "_ACH_A_fr", "_ACH_sigma"]],
            "_ACH_A": [["m^2"], ["_HX_is_ache", "_ACH_alpha", "_ACH_V"]],
            "_ACH_G_hot": [["kg/m^2/s"], ["_HX_is_ache", "_ACH_Aff", "_mdot_h"]],
            "_ACH_h_hot": [["W/m^2/K"], ["_HX_is_ache", "_ACH_jH", "_ACH_G_hot", "_H_Fluid", "_Thi", "_Pres_H_in"]],
            "_ACH_eta_o_resolved": [["(dimensionless)"], ["_HX_is_ache", "_ACH_eta_o_hot", "_ACH_Af_over_A", "_ACH_eta_f"]],
            "_ACH_U": [["W/m^2/K"],
                       ["_HX_is_ache", "_ACH_eta_o_resolved", "_ACH_h_hot", "_h_c", "_t_m", "_plate_material",
                        "_fouling_hot", "_fouling_cold"]],
            "_ACH_dp_core": [["Pa"],
                             ["_HX_is_ache", "_ACH_f_core", "_ACH_A", "_ACH_Aff", "_ACH_G_hot", "_H_Fluid",
                              "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]],
        })

        # ------------------------------------------------------------------ #
        # Fluid-property helpers (aligned with utilities.py)
        # ------------------------------------------------------------------ #
        def _get_mu(fluid, T, P):
            # utilities.py → CoolProp: "VISCOSITY"; REFPROP also supports "ETA"
            for sym in ("VISCOSITY", "ETA"):
                try:
                    return getfluidproperty(fluid, sym, "T", T, "P", P)
                except Exception:
                    pass
            return None

        def _get_k(fluid, T, P):
            try:
                return getfluidproperty(fluid, "TCX", "T", T, "P", P)
            except Exception:
                return None

        def _get_cp(fluid, T, P):
            return getfluidproperty(fluid, "CP", "T", T, "P", P)

        def _get_pr(fluid, T, P):
            try:
                return getfluidproperty(fluid, "PRANDTL", "T", T, "P", P)
            except Exception:
                try:
                    cp = _get_cp(fluid, T, P)
                    mu = _get_mu(fluid, T, P)
                    k = _get_k(fluid, T, P)
                    if cp and mu and k:
                        return (cp * mu) / k
                except Exception:
                    pass
            return None
        self._get_mu = _get_mu
        self._get_k = _get_k
        self._get_cp = _get_cp
        self._get_pr = _get_pr

        # ------------------------------------------------------------------ #
        # Formula text for tooltips (LaTeX-style strings)
        # ------------------------------------------------------------------ #
        self._formulae = {
            "_Thi": {
                tuple(["_mdot_h", "_H_O_Cp", "_Tho", "_q"]):
                    r"\(T_{hi} = \frac{q}{\dot m_h\,c_{p,h,o}} + T_{ho}\)",
            },
            "_Tho": {
                tuple(["_mdot_h", "_H_I_Cp", "_Thi", "_q"]):
                    r"\(T_{ho} = T_{hi} - \frac{q}{\dot m_h\,c_{p,h,i}}\)",
            },
            "_Tci": {
                tuple(["_mdot_c", "_C_O_Cp", "_Tco", "_q"]):
                    r"\(T_{ci} = T_{co} - \frac{q}{\dot m_c\,c_{p,c,o}}\)",
            },
            "_Tco": {
                tuple(["_mdot_c", "_C_I_Cp", "_Tci", "_q"]):
                    r"\(T_{co} = \frac{q}{\dot m_c\,c_{p,c,i}} + T_{ci}\)",
            },
            "_q_h": {
                tuple(["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"]):
                    r"\(q_h = \dot m_h\,c_{p,h,avg}\,(T_{hi}-T_{ho})\)",
            },
            "_q_c": {
                tuple(["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"]):
                    r"\(q_c = \dot m_c\,c_{p,c,avg}\,(T_{co}-T_{ci})\)",
            },
            "_q": {
                tuple(["_q_h", "_q_c"]):
                    r"\(q = \frac{q_h + q_c}{2}\)  (energy balance blending)",
                tuple(["_q_h"]):
                    r"\(q = q_h\)",
                tuple(["_q_c"]):
                    r"\(q = q_c\)",
                tuple(["_q_max", "_effectiveness_epsilon"]):
                    r"\(q = \varepsilon\,q_{\max}\)",
            },
            "_q_max": {
                tuple(["_Cmin", "_Thi", "_Tci"]):
                    r"\(q_{\max} = C_{\min}\,(T_{hi}-T_{ci})\)",
            },
            "_UA": {
                tuple(["_q", "_lmtd"]):
                    r"\(UA = \dfrac{q}{F\,\mathrm{LMTD}}\)",
                tuple(["_NTU", "_Cmin"]):
                    r"\(UA = \mathrm{NTU}\,C_{\min}\)",
            },
            "_lmtd": {
                tuple(["_Thi", "_Tho", "_Tci", "_Tco"]):
                    r"\(\Delta T_1, \Delta T_2 \;\rightarrow\; "
                    r"\mathrm{LMTD} = \dfrac{\Delta T_2-\Delta T_1}{\ln(\Delta T_2/\Delta T_1)}\)",
            },
            "_Ch": {
                tuple(["_mdot_h", "_H_avg_Cp"]):
                    r"\(C_h = \dot m_h\,c_{p,h,avg}\)",
            },
            "_Cc": {
                tuple(["_mdot_c", "_C_avg_Cp"]):
                    r"\(C_c = \dot m_c\,c_{p,c,avg}\)",
            },
            "_Cmin": {
                tuple(["_Cc", "_Ch"]):
                    r"\(C_{\min} = \min(C_h, C_c)\)",
            },
            "_Cmax": {
                tuple(["_Cc", "_Ch"]):
                    r"\(C_{\max} = \max(C_h, C_c)\)",
            },
            "_Cr": {
                tuple(["_Cmin", "_Cmax"]):
                    r"\(\mathit{Cr} = C_{\min}/C_{\max}\)",
            },
            "_effectiveness_epsilon": {
                tuple(["_q", "_q_max"]):
                    r"\(\varepsilon = q/q_{\max}\)",
                tuple(["_NTU", "_Cr", "_Flow_Direction", "_Type"]):
                    r"\(\varepsilon(\mathrm{NTU},\mathit{Cr})\) via standard ε–NTU relations "
                    r"(counterflow, parallel, or crossflow as selected)",
            },
            "_NTU": {
                tuple(["_Cmin", "_UA"]):
                    r"\(\mathrm{NTU} = UA/C_{\min}\)",
            },
            "_H_inlet_velocity": {
                tuple(["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"]):
                    r"\(v = \dot m/(\rho A),\; A=\pi (D/2)^2\)",
            },
            "_H_outlet_velocity": {
                tuple(["_mdot_h", "_H_outlet_ID", "_Pres_H_out", "_H_Fluid", "_Tho"]):
                    r"\(v = \dot m/(\rho A),\; \rho=\rho(T_{ho},P_{ho}),\; A=\pi (D/2)^2\)",
                tuple(["_mdot_h", "_H_outlet_ID", "_Pres_H_in", "_H_Fluid", "_Tho"]):
                    r"\(v = \dot m/(\rho A)\) (using inlet P if outlet P unknown)",
            },
            "_C_inlet_velocity": {
                tuple(["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"]):
                    r"\(v = \dot m/(\rho A)\)",
            },
            "_C_outlet_velocity": {
                tuple(["_mdot_c", "_C_outlet_ID", "_Pres_C_out", "_C_Fluid", "_Tco"]):
                    r"\(v = \dot m/(\rho A)\)",
                tuple(["_mdot_c", "_C_outlet_ID", "_Pres_C_in", "_C_Fluid", "_Tco"]):
                    r"\(v = \dot m/(\rho A)\) (using inlet P if outlet P unknown)",
            },
            "_Pres_H_out": {
                tuple(["_Pres_H_in", "_dP_h"]):
                    r"\(P_{ho} = P_{hi} - \Delta P_h\)",
            },
            "_Pres_H_in": {
                tuple(["_Pres_H_out", "_dP_h"]):
                    r"\(P_{hi} = P_{ho} + \Delta P_h\)",
            },
            "_Pres_C_out": {
                tuple(["_Pres_C_in", "_dP_c"]):
                    r"\(P_{co} = P_{ci} - \Delta P_c\)",
            },
            "_dP_h": {
                tuple(["_HX_is_plate", "_Re_h", "_G_h", "_Dh", "_Lp", "_H_Fluid", "_Thi", "_Pres_H_in"]):
                    r"\(\Delta P_{ch} = 4 f \frac{L_p}{D_h}\frac{\rho v^2}{2},\; f=1.441\,\mathrm{Re}^{-0.206}\)"
                    r";\; \Delta P_h \approx \Delta P_{ch} + \Delta P_{ports}\)",
                tuple(["_Pres_H_in", "_Pres_H_out"]):
                    r"\(\Delta P_h = P_{hi} - P_{ho}\)",
            },
            "_dP_c": {
                tuple(["_HX_is_plate", "_Re_c", "_G_c", "_Dh", "_Lp", "_C_Fluid", "_Tci", "_Pres_C_in"]):
                    r"\(\Delta P_{ch} = 4 f \frac{L_p}{D_h}\frac{\rho v^2}{2},\; f=1.441\,\mathrm{Re}^{-0.206}\)"
                    r";\; \Delta P_c \approx \Delta P_{ch} + \Delta P_{ports}\)",
                tuple(["_Pres_C_in", "_Pres_C_out"]):
                    r"\(\Delta P_c = P_{ci} - P_{co}\)",
            },
            "_U_calc": {
                tuple(["_HX_is_plate", "_h_h", "_h_c", "_t_m", "_plate_material", "_fouling_hot", "_fouling_cold"]):
                    r"\(\frac{1}{U}=\frac{1}{h_h}+ \frac{t}{k_\mathrm{wall}}+ \frac{1}{h_c}+R_{f,h}+R_{f,c}\)",
            },
            "_Dh": {
                tuple(["_HX_is_plate", "_mean_channel_gap", "_enlargement_phi"]):
                    r"\(D_h = 2\,b\,\phi\)  (with \(b\) in meters)",
            },
            "_mean_channel_gap": {
                tuple(["_HX_is_plate", "_Dh", "_enlargement_phi"]):
                    r"\(b = D_h/(2\phi)\)  (returned in mm)",
            },
            "_enlargement_phi": {
                tuple(["_HX_is_plate", "_Dh", "_mean_channel_gap"]):
                    r"\(\phi = D_h/(2b)\)",
            },
            "_H_inlet_ID": {
                tuple(["_mdot_h", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"]):
                    r"\(A = \dot m/(\rho v_\mathrm{tgt}),\; D = \sqrt{4A/\pi}\)  (returned in mm)",
            },
            "_H_outlet_ID": {
                tuple(["_mdot_h", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]):
                    r"\(A = \dot m/(\rho v_\mathrm{tgt}),\; D = \sqrt{4A/\pi}\)  (returned in mm)",
            },
            "_mdot_h": {
                tuple(["_H_inlet_ID", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"]):
                    r"\(\dot m_h = \rho\,A\,v_\mathrm{tgt}\)",
                tuple(["_H_outlet_ID", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]):
                    r"\(\dot m_h = \rho\,A\,v_\mathrm{tgt}\)",
            },
            "_mdot_c": {
                tuple(["_C_inlet_ID", "_C_target_velocity", "_Pres_C_in", "_Tci", "_C_Fluid"]):
                    r"\(\dot m_c = \rho\,A\,v_\mathrm{tgt}\)",
                tuple(["_C_outlet_ID", "_C_target_velocity", "_Pres_C_out", "_Tco", "_C_Fluid"]):
                    r"\(\dot m_c = \rho\,A\,v_\mathrm{tgt}\)",
            },
        }

    # ---------------------------------------------------------------------- #
    # Tooltip helpers (expanded: includes LaTeX-style formulas)
    # ---------------------------------------------------------------------- #
    def known_attributes(self):
        return [k for k, v in vars(self).items() if v is not None]

    def _dependency_options_for(self, attribute):
        try:
            entries = self._dependencies[attribute]
        except KeyError:
            return []
        return [opt for opt in entries[1:] if isinstance(opt, list)]

    def dependency_status(self, attribute, known_attributes=None):
        known = set(self.known_attributes() if known_attributes is None else known_attributes)
        status = []
        for opt in self._dependency_options_for(attribute):
            missing = [dep for dep in opt if dep not in known]
            status.append({"option": opt, "met": len(missing) == 0, "missing": missing})
        return status

    def _humanize_attr(self, attr, mapping=None):
        if mapping and attr in mapping:
            return str(mapping[attr])
        s = attr[1:] if isinstance(attr, str) and attr.startswith("_") else str(attr)
        return s.replace("_", " ").title()

    def _formula_for(self, attribute, option_list):
        """Return LaTeX-style formula for attribute/option if available."""
        try:
            by_attr = self._formulae.get(attribute, {})
            return by_attr.get(tuple(option_list), None)
        except Exception:
            return None

    def dependency_tooltip(self, attribute, known_attributes=None, ui_friendly_names=None):
        if attribute not in self._dependencies:
            return f"<b style='color:#ffffff'>No dependencies for <code>{attribute}</code></b>"
        unit = ""
        try:
            unit = self._dependencies[attribute][0][0] or ""
        except Exception:
            pass
        status_list = self.dependency_status(attribute, known_attributes=known_attributes)
        title_name = self._humanize_attr(attribute, ui_friendly_names)
        unit_str = f" <span style='color:#cccccc'>(unit: {unit})</span>" if unit else ""
        html = [f"<div style='color:#ffffff'><b>How to solve <code>{title_name}</code></b>{unit_str}"]
        html.append("<ul style='margin-left:0.9em; padding-left:1.0em; color:#ffffff;'>")
        if not status_list:
            html.append("<li>No dependency options listed</li>")
        else:
            for st in status_list:
                parts = []
                for dep in st["option"]:
                    met = dep not in st["missing"]
                    tag = "[met]" if met else "[unmet]"
                    parts.append(f"<code>{tag} {self._humanize_attr(dep, ui_friendly_names)}</code>")
                prefix = "met" if st["met"] else "unmet"
                # Add formula block when present
                formula = self._formula_for(attribute, st["option"])
                if formula:
                    # show as mono/inline LaTeX-ish string; UI can style later if needed
                    f_html = f"<div style='margin-top:2px; color:#B0E0E6'><code>{formula}</code></div>"
                else:
                    f_html = ""
                html.append(f"<li><span><b>{prefix}</b>: " + ", ".join(parts) + f"{f_html}</span></li>")
        html.append("</ul></div>")
        return "".join(html)

    # ---------------------------------------------------------------------- #
    # Solvers for each attribute (additions where noted)
    # ---------------------------------------------------------------------- #
    def solve_attribute(self, attribute, dependency_option):
        """All Equations for solving for unknown values"""

        # --------------------------- Scalars & heat ------------------------ #
        if attribute == "_Thi":
            if dependency_option == ["_mdot_h", "_H_O_Cp", "_Tho", "_q"]:
                self._Thi = self._q / (self._mdot_h * self._H_O_Cp) + self._Tho
            return self._Thi

        elif attribute == "_H_inlet_ID":
            if dependency_option == ["_H_inlet_ID"]:
                return self._H_inlet_ID
            # NEW: ID from target velocity
            if dependency_option == ["_mdot_h", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"]:
                rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                A = self._mdot_h / (rho * max(self._H_target_velocity, 1e-9))
                D_m = m.sqrt(4.0 * A / self.PI)
                self._H_inlet_ID = D_m * 1000.0  # in mm
            return self._H_inlet_ID

        elif attribute == "_Tho":
            if dependency_option == ["_mdot_h", "_H_I_Cp", "_Thi", "_q"]:
                self._Tho = self._Thi - self._q / (self._mdot_h * self._H_I_Cp)
            return self._Tho

        elif attribute == "_Tci":
            if dependency_option == ["_mdot_c", "_C_O_Cp", "_Tco", "_q"]:
                self._Tci = self._Tco - self._q / (self._mdot_c * self._C_O_Cp)
            return self._Tci

        elif attribute == "_Tco":
            if dependency_option == ["_mdot_c", "_C_I_Cp", "_Tci", "_q"]:
                self._Tco = self._q / (self._mdot_c * self._C_I_Cp) + self._Tci
            return self._Tco

        elif attribute == "_H_outlet_ID":
            if dependency_option == ["_H_outlet_ID"]:
                return self._H_outlet_ID
            # NEW: outlet ID from target velocity
            if dependency_option == ["_mdot_h", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]:
                P = self._Pres_H_out if self._Pres_H_out is not None else self._Pres_H_in
                rho = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
                A = self._mdot_h / (rho * max(self._H_target_velocity, 1e-9))
                D_m = m.sqrt(4.0 * A / self.PI)
                self._H_outlet_ID = D_m * 1000.0
            return self._H_outlet_ID

        elif attribute == "_Pres_H_in":
            if dependency_option == ["_Pres_H_in"]:
                return self._Pres_H_in
            # NEW: back-solve inlet pressure
            if dependency_option == ["_Pres_H_out", "_dP_h"]:
                if self._Pres_H_out is not None and self._dP_h is not None:
                    self._Pres_H_in = self._Pres_H_out + self._dP_h
            return self._Pres_H_in

        elif attribute == "_Pres_H_out":
            # NEW: outlet pressure from inlet and dP
            if dependency_option == ["_Pres_H_in", "_dP_h"]:
                if self._Pres_H_in is not None and self._dP_h is not None:
                    self._Pres_H_out = self._Pres_H_in - self._dP_h
            return self._Pres_H_out

        elif attribute == "_mdot_h":
            if dependency_option == ["_H_in_nm3_hr", "_H_Fluid"]:
                self._mdot_h = unit_convert(self._H_in_nm3_hr, "Nm^3/hr", "kg/s", self._H_Fluid)
            # NEW: mdot from inlet ID and target v
            elif dependency_option == ["_H_inlet_ID", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"]:
                rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                D_m = (self._H_inlet_ID or 0.0) / 1000.0
                A = self.PI * (D_m / 2.0) ** 2
                self._mdot_h = rho * A * self._H_target_velocity
            # NEW: mdot from outlet ID and target v
            elif dependency_option == ["_H_outlet_ID", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"]:
                P = self._Pres_H_out if self._Pres_H_out is not None else self._Pres_H_in
                rho = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
                D_m = (self._H_outlet_ID or 0.0) / 1000.0
                A = self.PI * (D_m / 2.0) ** 2
                self._mdot_h = rho * A * self._H_target_velocity
            return self._mdot_h

        elif attribute == "_mdot_c":
            if dependency_option == ["_C_in_nm3_hr", "_C_Fluid"]:
                self._mdot_c = unit_convert(self._C_in_nm3_hr, "Nm^3/hr", "kg/s", self._C_Fluid)
            # NEW: mdot from inlet ID and target v
            elif dependency_option == ["_C_inlet_ID", "_C_target_velocity", "_Pres_C_in", "_Tci", "_C_Fluid"]:
                rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
                D_m = (self._C_inlet_ID or 0.0) / 1000.0
                A = self.PI * (D_m / 2.0) ** 2
                self._mdot_c = rho * A * self._C_target_velocity
            # NEW: mdot from outlet ID and target v
            elif dependency_option == ["_C_outlet_ID", "_C_target_velocity", "_Pres_C_out", "_Tco", "_C_Fluid"]:
                P = self._Pres_C_out if self._Pres_C_out is not None else self._Pres_C_in
                rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tco, "P", P)
                D_m = (self._C_outlet_ID or 0.0) / 1000.0
                A = self.PI * (D_m / 2.0) ** 2
                self._mdot_c = rho * A * self._C_target_velocity
            return self._mdot_c

        elif attribute == "_H_in_nm3_hr":
            if dependency_option == ["_mdot_h", "_H_Fluid"]:
                self._H_in_nm3_hr = unit_convert(self._mdot_h, "kg/s", "Nm^3/hr", self._H_Fluid)
            return self._H_in_nm3_hr

        elif attribute == "_C_in_nm3_hr":
            if dependency_option == ["_mdot_c", "_C_Fluid"]:
                self._C_in_nm3_hr = unit_convert(self._mdot_c, "kg/s", "Nm^3/hr", self._C_Fluid)
            return self._C_in_nm3_hr

        elif attribute == "_q_h":
            if dependency_option == ["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"]:
                self._q_h = (self._mdot_h * self._H_avg_Cp * (self._Thi - self._Tho))
            return self._q_h

        elif attribute == "_q_c":
            if dependency_option == ["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"]:
                self._q_c = self._mdot_c * self._C_avg_Cp * (self._Tco - self._Tci)
            return self._q_c

        elif attribute == "_H_avg_Cp":
            if dependency_option == ["_H_I_Cp", "_H_O_Cp"]:
                self._H_avg_Cp = (self._H_O_Cp + self._H_I_Cp) / 2
            elif dependency_option == ["_H_I_Cp"]:
                self._H_avg_Cp = self._H_I_Cp
            return self._H_avg_Cp

        elif attribute == "_C_avg_Cp":
            if dependency_option == ["_C_I_Cp", "_C_O_Cp"]:
                self._C_avg_Cp = (self._C_O_Cp + self._C_I_Cp) / 2
            elif dependency_option == ["_C_I_Cp"]:
                self._C_avg_Cp = self._C_I_Cp
            return self._C_avg_Cp

        elif attribute == "_lmtd":
            if dependency_option == ["_Thi", "_Tho", "_Tci", "_Tco"]:
                self._lmtd = LMTD(Thi=self._Thi, Tho=self._Tho, Tci=self._Tci, Tco=self._Tco,
                                  counterflow=self._Flow_Direction)
            return self._lmtd

        elif attribute == "_q":
            if dependency_option == ["_q_h", "_q_c"]:
                # FIX: blend q_h & q_c rather than max()
                if self._q_h is not None and self._q_c is not None:
                    self._q = 0.5 * (self._q_h + self._q_c)
                else:
                    self._q = self._q_h if self._q_h is not None else self._q_c
            elif dependency_option == ["_q_c"]:
                self._q = self._q_c
            elif dependency_option == ["_q_h"]:
                self._q = self._q_h
            elif dependency_option == ["_q_max", "_effectiveness_epsilon"]:
                self._q = self._q_max * self._effectiveness_epsilon
            return self._q

        elif attribute == "_q_max":
            if dependency_option == ["_Cmin", "_Thi", "_Tci"]:
                self._q_max = self._Cmin * (self._Thi - self._Tci)
            return self._q_max

        elif attribute == "_UA":
            if dependency_option == ["_q", "_lmtd"]:
                self._UA = self._q / (self._lmtd * self._F_sub_T)
            elif dependency_option == ["_NTU", "_Cmin"]:
                self._UA = self._NTU * self._Cmin
            return self._UA

        elif attribute == "_Ch":
            if dependency_option == ["_mdot_h", "_H_avg_Cp"]:
                self._Ch = self._mdot_h * self._H_avg_Cp
            return self._Ch

        elif attribute == "_Cc":
            if dependency_option == ["_mdot_c", "_C_avg_Cp"]:
                self._Cc = self._mdot_c * self._C_avg_Cp
            return self._Cc

        elif attribute == "_Cmin":
            if dependency_option == ["_Cc", "_Ch"]:
                if self._Ch is not None and self._Cc is not None:
                    self._Cmin = min(self._Cc, self._Ch)
            return self._Cmin

        elif attribute == "_Cmax":
            if dependency_option == ["_Cc", "_Ch"]:
                if self._Ch is not None and self._Cc is not None:
                    self._Cmax = max(self._Cc, self._Ch)
            return self._Cmax

        elif attribute == "_effectiveness_epsilon":
            if dependency_option == ["_q", "_q_max"]:
                self._effectiveness_epsilon = self._q / self._q_max
            elif dependency_option == ["_NTU", "_Cr", "_Flow_Direction", "_Type"]:
                # counterflow/parallel correlations
                if self._Flow_Direction:  # counterflow
                    if self._Cr == 1:
                        self._effectiveness_epsilon = self._NTU / (1 + self._NTU)
                    elif self._Cr <= 1:
                        num = 1 - m.exp(-(self._NTU) * (1 - self._Cr))
                        den = 1 - (self._Cr * m.exp(-(self._NTU) * (1 - self._Cr)))
                        self._effectiveness_epsilon = num / den
                    else:
                        self._effectiveness_epsilon = (1 - m.exp(-(self._NTU) * (1 + self._Cr))) / (1 + self._Cr)
                else:  # parallel
                    self._effectiveness_epsilon = (1 - m.exp(-(self._NTU) * (1 + self._Cr))) / (1 + self._Cr)
            return self._effectiveness_epsilon

        elif attribute == "_NTU":
            if dependency_option == ["_Cmin", "_UA"]:
                self._NTU = self._UA / self._Cmin
            return self._NTU

        elif attribute == "_Cr":
            if dependency_option == ["_Cmin", "_Cmax"]:
                self._Cr = self._Cmin / self._Cmax
            return self._Cr

        # -------------------------- Channeling ----------------------------- #
        elif attribute == "_channels_per_pass_hot":
            if dependency_option == ["_Plate_count", "_Plate_Distribution_Bias"]:
                if self._Plate_count % 2 == 0:
                    if self._Plate_Distribution_Bias == "hot":
                        self._channels_per_pass_hot = (self._Plate_count - 1) / (2) + 0.5
                    else:
                        self._channels_per_pass_hot = (self._Plate_count - 1) / (2) - 0.5
                else:
                    self._channels_per_pass_hot = (self._Plate_count - 1) / (2)
            return self._channels_per_pass_hot

        elif attribute == "_channels_per_pass_cold":
            if dependency_option == ["_Plate_count", "_Plate_Distribution_Bias"]:
                if self._Plate_count % 2 == 0:
                    if self._Plate_Distribution_Bias == "hot":
                        self._channels_per_pass_cold = (self._Plate_count - 1) / (2) - 0.5
                    else:
                        self._channels_per_pass_cold = (self._Plate_count - 1) / (2) + 0.5
                else:
                    self._channels_per_pass_cold = (self._Plate_count - 1) / (2)
            return self._channels_per_pass_cold

        elif attribute == "_mdot_h_channel":
            if dependency_option == ["_mdot_h", "_channels_per_pass_hot"]:
                self._mdot_h_channel = self._mdot_h / self._channels_per_pass_hot
            return self._mdot_h_channel

        elif attribute == "_mdot_c_channel":
            if dependency_option == ["_mdot_c", "_channels_per_pass_cold"]:
                self._mdot_c_channel = self._mdot_c / self._channels_per_pass_cold
            return self._mdot_c_channel

        # ---------------------------- Velocities --------------------------- #
        elif attribute == "_H_inlet_velocity":
            if dependency_option == ["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"]:
                density = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                area = (self._H_inlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._H_inlet_velocity = self._mdot_h / (density * area)
            return self._H_inlet_velocity

        elif attribute == "_H_outlet_velocity":
            # prefer outlet pressure if we have it
            if dependency_option == ["_mdot_h", "_H_outlet_ID", "_Pres_H_out", "_H_Fluid", "_Tho"]:
                P = self._Pres_H_out
                density = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
                area = (self._H_outlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._H_outlet_velocity = self._mdot_h / (density * area)
            elif dependency_option == ["_mdot_h", "_H_outlet_ID", "_Pres_H_in", "_H_Fluid", "_Tho"]:
                P = self._Pres_H_in
                density = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
                area = (self._H_outlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._H_outlet_velocity = self._mdot_h / (density * area)
            return self._H_outlet_velocity

        elif attribute == "_C_inlet_velocity":
            if dependency_option == ["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"]:
                density = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
                area = (self._C_inlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._C_inlet_velocity = self._mdot_c / (density * area)
            return self._C_inlet_velocity

        elif attribute == "_C_outlet_velocity":
            if dependency_option == ["_mdot_c", "_C_outlet_ID", "_Pres_C_out", "_C_Fluid", "_Tco"]:
                P = self._Pres_C_out
                density = getfluidproperty(self._C_Fluid, "D", "T", self._Tco, "P", P)
                area = (self._C_outlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._C_outlet_velocity = self._mdot_c / (density * area)
            elif dependency_option == ["_mdot_c", "_C_outlet_ID", "_Pres_C_in", "_C_Fluid", "_Tco"]:
                density = getfluidproperty(self._C_Fluid, "D", "T", self._Tco, "P", self._Pres_C_in)
                area = (self._C_outlet_ID / 1000.0) ** 2 * self.PI / 4.0
                self._C_outlet_velocity = self._mdot_c / (density * area)
            return self._C_outlet_velocity

        elif attribute == "_H_I_Cp":
            if dependency_option == ["_Thi", "_H_Fluid"]:
                self._H_I_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1))
            elif dependency_option == ["_Tho", "_H_Fluid"]:
                # fallback to outlet temp if only that is known
                self._H_I_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1))
            return self._H_I_Cp

        elif attribute == "_H_O_Cp":
            if dependency_option == ["_Tho", "_H_Fluid"]:
                self._H_O_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1))
            elif dependency_option == ["_Thi", "_H_Fluid"]:
                self._H_O_Cp = getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1))
            return self._H_O_Cp

        elif attribute == "_C_I_Cp":
            if dependency_option == ["_Tci", "_C_Fluid"]:
                self._C_I_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1))
            elif dependency_option == ["_Tco", "_C_Fluid"]:
                self._C_I_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1))
            return self._C_I_Cp

        elif attribute == "_C_O_Cp":
            if dependency_option == ["_Tco", "_C_Fluid"]:
                self._C_O_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1))
            elif dependency_option == ["_Tci", "_C_Fluid"]:
                self._C_O_Cp = getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1))
            return self._C_O_Cp

        # ------------------------- Plate branches -------------------------- #
        elif attribute == "_t_m":
            if dependency_option == ["_HX_is_plate", "_plate_thickness"]:
                self._t_m = (self._plate_thickness or 0.0) / 1000.0
            return self._t_m

        elif attribute == "_Lp":
            if dependency_option == ["_HX_is_plate", "_Lv", "_Dp"]:
                self._Lp = (self._Lv - self._Dp)
            return self._Lp

        elif attribute == "_Lw":
            if dependency_option == ["_HX_is_plate", "_Lh", "_Dp"]:
                self._Lw = (self._Lh + self._Dp)
            return self._Lw

        elif attribute == "_Aproj":
            if dependency_option == ["_HX_is_plate", "_Lp", "_Lw"]:
                self._Aproj = self._Lp * self._Lw
            return self._Aproj

        elif attribute == "_Dh":
            if dependency_option == ["_HX_is_plate", "_mean_channel_gap", "_enlargement_phi"]:
                b_m = (self._mean_channel_gap or 0.0) / 1000.0
                phi = self._enlargement_phi or 1.0
                self._Dh = 2.0 * b_m * phi
            return self._Dh

        elif attribute == "_Aff_hot":
            if dependency_option == ["_HX_is_plate", "_Lw", "_mean_channel_gap"]:
                b_m = (self._mean_channel_gap or 0.0) / 1000.0
                self._Aff_hot = self._Lw * b_m
            return self._Aff_hot

        elif attribute == "_Aff_cold":
            if dependency_option == ["_HX_is_plate", "_Lw", "_mean_channel_gap"]:
                b_m = (self._mean_channel_gap or 0.0) / 1000.0
                self._Aff_cold = self._Lw * b_m
            return self._Aff_cold

        elif attribute == "_mu_h":
            if dependency_option == ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]:
                self._mu_h = self._get_mu(self._H_Fluid, self._Thi, self._Pres_H_in)
            return self._mu_h

        elif attribute == "_mu_c":
            if dependency_option == ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]:
                self._mu_c = self._get_mu(self._C_Fluid, self._Tci, self._Pres_C_in)
            return self._mu_c

        elif attribute == "_k_h":
            if dependency_option == ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]:
                self._k_h = self._get_k(self._H_Fluid, self._Thi, self._Pres_H_in)
            return self._k_h

        elif attribute == "_k_c":
            if dependency_option == ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]:
                self._k_c = self._get_k(self._C_Fluid, self._Tci, self._Pres_C_in)
            return self._k_c

        elif attribute == "_Pr_h":
            if dependency_option == ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"]:
                self._Pr_h = self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in)
            return self._Pr_h

        elif attribute == "_Pr_c":
            if dependency_option == ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"]:
                self._Pr_c = self._get_pr(self._C_Fluid, self._Tci, self._Pres_C_in)
            return self._Pr_c

        elif attribute == "_G_h":
            if dependency_option == ["_HX_is_plate", "_mdot_h_channel", "_Aff_hot"]:
                self._G_h = self._mdot_h_channel / self._Aff_hot
            return self._G_h

        elif attribute == "_G_c":
            if dependency_option == ["_HX_is_plate", "_mdot_c_channel", "_Aff_cold"]:
                self._G_c = self._mdot_c_channel / self._Aff_cold
            return self._G_c

        elif attribute == "_Re_h":
            if dependency_option == ["_HX_is_plate", "_G_h", "_Dh", "_mu_h"]:
                self._Re_h = (self._G_h * self._Dh) / self._mu_h
            return self._Re_h

        elif attribute == "_Re_c":
            if dependency_option == ["_HX_is_plate", "_G_c", "_Dh", "_mu_c"]:
                self._Re_c = (self._G_c * self._Dh) / self._mu_c
            return self._Re_c

        elif attribute == "_h_h":
            if dependency_option == ["_HX_is_plate", "_Re_h", "_Pr_h", "_k_h", "_Dh"]:
                C, n = 0.3, 0.663  # chevron-type correlation
                Nu = C * (self._Re_h ** n) * ((self._Pr_h or 0.7) ** (1.0 / 3.0))
                self._h_h = Nu * self._k_h / self._Dh
            return self._h_h

        elif attribute == "_h_c":
            if dependency_option == ["_HX_is_plate", "_Re_c", "_Pr_c", "_k_c", "_Dh"]:
                C, n = 0.3, 0.663
                Nu = C * (self._Re_c ** n) * ((self._Pr_c or 0.7) ** (1.0 / 3.0))
                self._h_c = Nu * self._k_c / self._Dh
            return self._h_c

        elif attribute == "_U_calc":
            if dependency_option == ["_HX_is_plate", "_h_h", "_h_c", "_t_m", "_plate_material", "_fouling_hot", "_fouling_cold"]:
                k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
                R_wall = (self._t_m or 0.0006) / float(k_wall)
                Rf_h = float(self._fouling_hot or 0.0)
                Rf_c = float(self._fouling_cold or 0.0)
                R_tot = (1.0 / self._h_h) + R_wall + (1.0 / self._h_c) + Rf_h + Rf_c
                self._U_calc = 1.0 / R_tot
            return self._U_calc

        elif attribute == "_dP_h":
            if dependency_option == ["_HX_is_plate", "_Re_h", "_G_h", "_Dh", "_Lp", "_H_Fluid", "_Thi", "_Pres_H_in"]:
                f = 1.441 * (self._Re_h ** (-0.206))
                rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                v = self._G_h / rho
                dP_ch = 4.0 * f * (self._Lp / self._Dh) * (rho * v * v / 2.0)
                # simple port loss estimate as before
                A_port = self.PI * (self._Dp / 2.0) ** 2 if self._Dp else None
                v_p = (self._mdot_h / A_port) / rho if (A_port and rho and A_port > 0) else 0.0
                dP_port = 1.4 * (self._Hot_Passes or 1) * (rho * v_p * v_p / 2.0)
                self._dP_h = dP_ch + dP_port
            elif dependency_option == ["_Pres_H_in", "_Pres_H_out"]:
                if self._Pres_H_in is not None and self._Pres_H_out is not None:
                    self._dP_h = self._Pres_H_in - self._Pres_H_out
            return self._dP_h

        elif attribute == "_dP_c":
            if dependency_option == ["_HX_is_plate", "_Re_c", "_G_c", "_Dh", "_Lp", "_C_Fluid", "_Tci", "_Pres_C_in"]:
                f = 1.441 * (self._Re_c ** (-0.206))
                rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
                v = self._G_c / rho
                dP_ch = 4.0 * f * (self._Lp / self._Dh) * (rho * v * v / 2.0)
                A_port = self.PI * (self._Dp / 2.0) ** 2 if self._Dp else None
                v_p = (self._mdot_c / A_port) / rho if (A_port and rho and A_port > 0) else 0.0
                dP_port = 1.4 * (self._Hot_Passes or 1) * (rho * v_p * v_p / 2.0)
                self._dP_c = dP_ch + dP_port
            elif dependency_option == ["_Pres_C_in", "_Pres_C_out"]:
                if self._Pres_C_in is not None and self._Pres_C_out is not None:
                    self._dP_c = self._Pres_C_in - self._Pres_C_out
            return self._dP_c

        elif attribute == "_dP_total":
            if dependency_option == ["_HX_is_plate", "_dP_h", "_dP_c"]:
                self._dP_total = (self._dP_h or 0.0) + (self._dP_c or 0.0)
            return self._dP_total

        elif attribute == "_epsilon_NTU":
            if dependency_option == ["_NTU", "_Cr", "_Flow_Direction"]:
                if self._Flow_Direction:  # counterflow
                    if self._Cr == 1:
                        self._epsilon_NTU = self._NTU / (1.0 + self._NTU)
                    else:
                        num = 1.0 - m.exp(-self._NTU * (1.0 - self._Cr))
                        den = 1.0 - self._Cr * m.exp(-self._NTU * (1.0 - self._Cr))
                        self._epsilon_NTU = num / den
                else:
                    self._epsilon_NTU = (1.0 - m.exp(-self._NTU * (1.0 + self._Cr))) / (1.0 + self._Cr)
            return self._epsilon_NTU

        elif attribute == "_Tho_eps":
            if dependency_option == ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch"]:
                self._Tho_eps = self._Thi - self._epsilon_NTU * self._Cmin * (self._Thi - self._Tci) / self._Ch
            return self._Tho_eps

        elif attribute == "_Tco_eps":
            if dependency_option == ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Cc"]:
                self._Tco_eps = self._Tci + self._epsilon_NTU * self._Cmin * (self._Thi - self._Tci) / self._Cc
            return self._Tco_eps

        elif attribute == "_S_gen":
            if dependency_option == ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch", "_Cc",
                                     "_dP_h", "_dP_c", "_H_Fluid", "_C_Fluid"]:
                Th2 = self._Tho or self._Tho_eps
                Tc2 = self._Tco or self._Tco_eps
                if Th2 is None or Tc2 is None:
                    self.solve_attribute("_Tho_eps", ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch"])
                    self.solve_attribute("_Tco_eps", ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Cc"])
                    Th2 = self._Tho_eps
                    Tc2 = self._Tco_eps
                Th1, Tc1 = self._Thi, self._Tci
                eps = 1e-12
                term_h = self._Ch * m.log(max(Th2, eps) / max(Th1, eps))
                term_c = self._Cc * m.log(max(Tc2, eps) / max(Tc1, eps))
                S_ht = term_h + term_c
                rho_h = getfluidproperty(self._H_Fluid, "D", "T", Th1, "P", self._Pres_H_in)
                rho_c = getfluidproperty(self._C_Fluid, "D", "T", Tc1, "P", self._Pres_C_in)
                S_dp = (self._mdot_h * (self._dP_h or 0.0) / (rho_h * Th1)) + (
                    self._mdot_c * (self._dP_c or 0.0) / (rho_c * Tc1)
                )
                self._S_gen = S_ht + S_dp
            return self._S_gen

        elif attribute == "_Ns":
            if dependency_option == ["_HX_is_plate", "_S_gen", "_Cmax"]:
                self._Ns = self._S_gen / self._Cmax
            return self._Ns

        # -------------------- Shell & Tube (your original) ---------------- #
        elif attribute == "_ST_L_total":
            if dependency_option == ["_HX_is_st", "_ST_L_pass", "_ST_N_tube_passes"]:
                self._ST_L_total = self._ST_L_pass * float(self._ST_N_tube_passes or 1)
            return self._ST_L_total

        elif attribute == "_ST_N_tubes_per_pass":
            if dependency_option == ["_HX_is_st", "_ST_N_tubes", "_ST_N_tube_passes"]:
                if (self._ST_N_tube_passes or 0) > 0:
                    self._ST_N_tubes_per_pass = float(self._ST_N_tubes or 0) / float(self._ST_N_tube_passes)
                else:
                    self._ST_N_tubes_per_pass = None
            return self._ST_N_tubes_per_pass

        elif attribute == "_ST_Ai":
            if dependency_option == ["_HX_is_st", "_ST_Di", "_ST_L_total", "_ST_N_tubes"]:
                self._ST_Ai = m.pi * self._ST_Di * self._ST_L_total * float(self._ST_N_tubes or 0)
            return self._ST_Ai

        elif attribute == "_ST_Ao":
            if dependency_option == ["_HX_is_st", "_ST_Do", "_ST_L_total", "_ST_N_tubes"]:
                self._ST_Ao = m.pi * self._ST_Do * self._ST_L_total * float(self._ST_N_tubes or 0)
            return self._ST_Ao

        elif attribute == "_ST_Re_tube":
            if dependency_option == ["_HX_is_st", "_ST_hot_in_tube", "_ST_Di", "_ST_N_tubes_per_pass",
                                     "_mdot_h", "_mdot_c", "_H_Fluid", "_C_Fluid", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]:
                hot_in = bool(int(self._ST_hot_in_tube or 1))
                if hot_in:
                    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                    mu = self._get_mu(self._H_Fluid, self._Thi, self._Pres_H_in)
                    mdot = (self._mdot_h or 0.0)
                else:
                    rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
                    mu = self._get_mu(self._C_Fluid, self._Tci, self._Pres_C_in)
                    mdot = (self._mdot_c or 0.0)
                Atube = m.pi * (self._ST_Di ** 2) / 4.0
                Npass = float(self._ST_N_tubes_per_pass or 1.0)
                Atotal = Atube * Npass
                u = (mdot / (rho * Atotal)) if (rho and Atotal) else 0.0
                self._ST_Re_tube = rho * u * self._ST_Di / (mu or 1e-9)
            return self._ST_Re_tube

        elif attribute == "_ST_Nu_tube":
            if dependency_option == ["_HX_is_st", "_ST_Re_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube",
                                     "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]:
                hot_in = bool(int(self._ST_hot_in_tube or 1))
                Pr = (self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in) if hot_in
                      else self._get_pr(self._C_Fluid, self._Tci, self._Pres_C_in)) or 0.7
                # Dittus–Boelter
                self._ST_Nu_tube = 0.023 * (self._ST_Re_tube ** 0.8) * (Pr ** 0.4)
            return self._ST_Nu_tube

        elif attribute == "_ST_h_i":
            if dependency_option == ["_HX_is_st", "_ST_Nu_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube",
                                     "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in", "_ST_Di"]:
                hot_in = bool(int(self._ST_hot_in_tube or 1))
                k = (self._get_k(self._H_Fluid, self._Thi, self._Pres_H_in) if hot_in
                     else self._get_k(self._C_Fluid, self._Tci, self._Pres_C_in))
                self._ST_h_i = (self._ST_Nu_tube * k / self._ST_Di) if (k and self._ST_Di) else None
            return self._ST_h_i

        elif attribute == "_ST_U":
            if dependency_option == ["_HX_is_st", "_ST_h_i", "_ST_h_o", "_ST_Rf_i", "_ST_Rf_o", "_ST_k_wall",
                                     "_ST_Di", "_ST_Do", "_ST_Ai", "_ST_Ao", "_ST_L_total"]:
                # 1/UA = 1/(h_i A_i) + Rf_i/A_i + ln(Do/Di)/(2πk L) + Rf_o/A_o + 1/(h_o A_o)
                term_i = (1.0 / (self._ST_h_i * (self._ST_Ai or 1e-9))) if (self._ST_h_i and self._ST_Ai) else 0.0
                term_ri = (self._ST_Rf_i or 0.0) / (self._ST_Ai or 1e-9)
                term_w = m.log(self._ST_Do / self._ST_Di) / (2.0 * m.pi * (self._ST_k_wall or 1e9) * self._ST_L_total) \
                    if (self._ST_Di and self._ST_Do and self._ST_k_wall and self._ST_L_total) else 0.0
                term_ro = (self._ST_Rf_o or 0.0) / (self._ST_Ao or 1e-9)
                term_o = (1.0 / ((self._ST_h_o or 1e-9) * (self._ST_Ao or 1e-9))) if (self._ST_Ao) else 0.0
                inv_UA = term_i + term_ri + term_w + term_ro + term_o
                UA = 1.0 / inv_UA if inv_UA > 0 else None
                self._ST_U = (UA / (self._ST_Ai or 1.0)) if UA else None
                self._ST_UA = UA
            return self._ST_U

        elif attribute == "_ST_UA":
            if dependency_option == ["_HX_is_st", "_ST_U", "_ST_Ai"]:
                self._ST_UA = (self._ST_U or 0.0) * (self._ST_Ai or 0.0)
            return self._ST_UA

        # -------------------- Air-Cooled / Compact ------------------------ #
        elif attribute == "_ACH_Aff":
            if dependency_option == ["_HX_is_ache", "_ACH_A_fr", "_ACH_sigma"]:
                self._ACH_Aff = (self._ACH_A_fr or 0.0) * (self._ACH_sigma or 0.0)
            return self._ACH_Aff

        elif attribute == "_ACH_A":
            if dependency_option == ["_HX_is_ache", "_ACH_alpha", "_ACH_V"]:
                self._ACH_A = (self._ACH_alpha or 0.0) * (self._ACH_V or 0.0)
            return self._ACH_A

        elif attribute == "_ACH_G_hot":
            if dependency_option == ["_HX_is_ache", "_ACH_Aff", "_mdot_h"]:
                if (self._ACH_Aff or 0.0) > 0.0:
                    self._ACH_G_hot = (self._mdot_h or 0.0) / self._ACH_Aff
                else:
                    self._ACH_G_hot = None
            return self._ACH_G_hot

        elif attribute == "_ACH_h_hot":
            if dependency_option == ["_HX_is_ache", "_ACH_jH", "_ACH_G_hot", "_H_Fluid", "_Thi", "_Pres_H_in"]:
                cp = self._get_cp(self._H_Fluid, self._Thi, self._Pres_H_in)
                Pr = self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in) or 0.7
                St = (self._ACH_jH or 0.0) / (Pr ** (2.0 / 3.0))
                self._ACH_h_hot = (St * (self._ACH_G_hot or 0.0) * (cp or 0.0))
            return self._ACH_h_hot

        elif attribute == "_ACH_eta_o_resolved":
            if dependency_option == ["_HX_is_ache", "_ACH_eta_o_hot", "_ACH_Af_over_A", "_ACH_eta_f"]:
                if self._ACH_eta_o_hot is not None:
                    self._ACH_eta_o_resolved = self._ACH_eta_o_hot
                else:
                    AfA = float(self._ACH_Af_over_A or 0.0)
                    eta_f = float(self._ACH_eta_f or 1.0)
                    self._ACH_eta_o_resolved = 1.0 - AfA * (1.0 - eta_f)
            return self._ACH_eta_o_resolved

        elif attribute == "_ACH_U":
            if dependency_option == ["_HX_is_ache", "_ACH_eta_o_resolved", "_ACH_h_hot", "_h_c", "_t_m", "_plate_material",
                                     "_fouling_hot", "_fouling_cold"]:
                k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
                R_wall = (self._t_m or 0.0006) / float(k_wall)
                R_hot = 1.0 / ((self._ACH_eta_o_resolved or 1.0) * (self._ACH_h_hot or 1e-9))
                R_cold = 1.0 / float(self._h_c or 1e-9)
                Rf_h = float(self._fouling_hot or 0.0)
                Rf_c = float(self._fouling_cold or 0.0)
                self._ACH_U = 1.0 / (R_hot + R_wall + R_cold + Rf_h + Rf_c)
            return self._ACH_U

        elif attribute == "_ACH_dp_core":
            if dependency_option == ["_HX_is_ache", "_ACH_f_core", "_ACH_A", "_ACH_Aff", "_ACH_G_hot", "_H_Fluid",
                                     "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"]:
                vi = 1.0 / getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
                To_guess = self._Tho or self._Tho_eps or (self._Thi - 10.0)
                vo = 1.0 / getfluidproperty(self._H_Fluid, "D", "T", max(To_guess, 1.0), "P", self._Pres_H_in)
                vm = 0.5 * (vi + vo)
                A_over_Aff = (self._ACH_A / (self._ACH_Aff or 1e-9)) if (self._ACH_A and self._ACH_Aff) else (
                    (self._ACH_V or 0.0) / (self._ACH_A_fr or 1e-9)
                )
                G2 = (self._ACH_G_hot or 0.0) ** 2
                term_accel = 0.5 * G2 * (vo - vi) / (vi * vo)
                term_fric = (self._ACH_f_core or 0.0) * A_over_Aff * (0.5 * G2 / vm)
                self._ACH_dp_core = term_accel + term_fric
            return self._ACH_dp_core

        # --------------------- Inverse plate geometry --------------------- #
        elif attribute == "_mean_channel_gap":
            if dependency_option == ["_HX_is_plate", "_Dh", "_enlargement_phi"]:
                # return in mm
                b_m = (self._Dh or 0.0) / (2.0 * (self._enlargement_phi or 1.0))
                self._mean_channel_gap = b_m * 1000.0
            return self._mean_channel_gap

        elif attribute == "_enlargement_phi":
            if dependency_option == ["_HX_is_plate", "_Dh", "_mean_channel_gap"]:
                b_m = (self._mean_channel_gap or 0.0) / 1000.0
                if b_m > 0:
                    self._enlargement_phi = (self._Dh or 0.0) / (2.0 * b_m)
            return self._enlargement_phi

        # else: leave unsolved
        return None

    # ---------------------------------------------------------------------- #
    # Pretty printer (unchanged except cosmetics)
    # ---------------------------------------------------------------------- #
    def pretty_print(self):
        spacing = 25
        digits = 6
        suppressed_values = ["_dependencies", "_initial_values", "_Name", "_plate_material",
                             "known_attributes", "unknown_attributes", "_formulae"]
        rule = "-" * 78
        print(rule)
        print("HX Instance:", self._Name)
        print(".... = Provided, ____ = Evaluated")
        print(rule)
        for k, v in self.__dict__.items():
            if k in self._initial_values:
                sym = "."
            else:
                sym = "_"
            if k not in suppressed_values:
                if v is None:
                    vv = "?"
                else:
                    vv = v
                try:
                    try:
                        unit = self._dependencies[k][0][0]
                    except KeyError:
                        unit = ""
                    print(f"{k.replace('_','',1):<{spacing}}{round(vv, digits)}".replace(" ", sym), unit)
                except TypeError:
                    print(f"{k.replace('_','',1):<{spacing}}{vv}".replace(" ", sym))

    # ---------------------------------------------------------------------- #
    # Main solve loop (unchanged flow control)
    # ---------------------------------------------------------------------- #
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
                for dependency_option in dependencies[1:]:
                    if set(dependency_option).issubset(set(known_attributes)):
                        if not quiet:
                            print("solving", attribute, "using", dependency_option)
                        self.solve_attribute(attribute, dependency_option)
                        # Only mark solved if it now has a value
                        if getattr(self, attribute, None) is not None:
                            unknown_attributes.remove(attribute)
                            known_attributes.append(attribute)
                            solved_attributes.append(attribute)
                            progressed = True
                            break
            if progressed:
                continue
            if not progressed:
                if not quiet:
                    print("Iteration complete; solved attributes:", solved_attributes)
                break
            iteration += 1
        self.known_attributes = known_attributes
        self.unknown_attributes = unknown_attributes
        return self.known_attributes, self.unknown_attributes