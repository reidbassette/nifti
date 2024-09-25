"""
utilities.py
A library of tools for the purpose of fluid flow analysis
"""
import math as m
import numpy as np
from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
from CoolProp.CoolProp import PropsSI
import os
backend = "REFPROP"
try:
    RP = REFPROPFunctionLibrary(os.environ["RPPREFIX"])
    RP.SETPATHdll(os.environ["RPPREFIX"])
    MASS_BASE_SI = RP.GETENUMdll(0,"MASS BASE SI").iEnum
except:
    print("REFPROP not found, defaulting to CoolProp")
    backend = "CoolProp"
    MASS_BASE_SI = "NA"

#Fluid Properties
#start section

def getfluidproperty(
    fluid,
    desired_property,
    first_property,
    first_value,
    second_property,
    second_value,
    BASE= MASS_BASE_SI,
    backend = backend
    ):
    """
    Returns desired property in SI units
    All inputs in REFPROP syntax
    fluid: name of fluid, string
    desired_property: property tag, string
    first_property: first of 2 thermo properties, string
    first_value: value of first thermo property, SI units
    second_property: second of 2 thermo properties, string
    second_value: value of second thermo property, SI units
    BASE: default is MASS BASE, other option is MOLAR_BASE_SI
    backend: set by file, but options are "REFPROP" or "CoolProp"
    """
    if backend == "REFPROP":
        output = RP.REFPROPdll(
            fluid,
            first_property+second_property,
            desired_property,
            BASE,
            1,
            0,
            first_value,
            second_value,
            [1.0]
        ).Output[0]
    elif backend == "CoolProp":
        if desired_property == "CP/CV":
            output = PropsSI(
                "C",
                first_property,
                first_value,
                second_property,
                second_value,
                fluid
            ) / PropsSI(
                "O",
                first_property,
                first_value,
                second_property,
                second_value,
                fluid
            )
        else:
            output = PropsSI(
                desired_property,
                first_property,
                first_value,
                second_property,
                second_value,
                fluid
            )
    return output

# end section

# Lists of units supported
#start section
fluid_names = [
    "AIR",
    "AMMONIA",
    "ARGON",
    "CARBON DIOXIDE",
    "HELIUM",
    "HYDROGEN",
    "METHANE",
    "NITROGEN",
    "OXYGEN"
]

density_units = [
    "kg/m^3",
    "g/cm^3",
    "lbm/ft^3",
    "lbm/gal",
    "lbm/in^3"
]

volume_units = [
    "L",
    "m^3",
    "gal",
    "ft^3",
    "in^3"
]

pressure_units = [
    "psia",
    "psig",
    "Pa",
    "bar,a",
    "bar,g",
    "atm"
]

temperature_units = [
    "F",
    "Rank",
    "C",
    "K"
]

area_units = [
    "mm^2",
    "m^2",
    "in^2",
    "ft^2"
]

mass_flow_units = [
    "kg/s",
    "lbm/s",
    "Nm^3/hr",
    "SLPM",
    "SCFM"
]

flow_capacity_units = [
    "Cv",
    "Cd, Do",
    "CdA"
]

distance_units = [
    "m",
    "mm",
    "micron",
    "ft",
    "in"
]

#end section

# Unit conversions
# start section

def same_unit(value, *args):
    return value

# distance

def m2in(value):
    return value / 0.0254

def in2m(value):
    return value * 0.0254

def m2ft(value):
    return value / 0.3048

def ft2m(value):
    return value * 0.3048

def m2mm(value):
    return value * 1000

def mm2m(value):
    return value / 1000

def m2micron(value):
    return value * 1e6

def micron2m(value):
    return value / 1e6

from_m = {
    "m": same_unit,
    "mm": m2mm,
    "micron": m2micron,
    "ft": m2ft,
    "in": m2in
}

to_m = {
    "m":same_unit,
    "mm": mm2m,
    "micron": micron2m,
    "ft": ft2m,
    "in": in2m
}

# flow capacity

def CdA2Do(CdA, Cd):
    return m.sqrt(
        4 * CdA / (m.pi * Cd)
    )

def Do2CdA(Do, Cd):
    return Cd * m.pi / 4 * Do**2

def Cv2CdA(Cv, *args):
    return m.pi/120 * Cv

def CdA2Cv(CdA, *args):
    return 120 / m.pi * CdA

from_CdA = {
    "Cv": CdA2Cv,
    "Cd, Do": CdA2Do,
    "CdA": same_unit
}

to_CdA = {
    "Cv": Cv2CdA,
    "Cd, Do": Do2CdA,
    "CdA": same_unit
}

# Energy

def BTU2W(BTU):
    """
    Returns conversion to Watts from British Thermal Units
    BTU: number of BTUs
    """
    return BTU * 1055.0559

#area

def smm2sm(smm, *args):
    return smm * 1e-6

def sm2smm(sm, *args):
    return sm * 1e6

def sft2sm(sft, *args):
    return sft * 0.09290304

def sm2sft(sm, *args):
    return sm / 0.09290304

def sin2sm(sin, *args):
    return sin * 0.00064516

def sm2sin(sm, *args):
    return sm / 0.00064516

#volume

def cf2cm(cf, *args):
    return cf * 0.0283168466

def cm2cf(cm, *args):
    return cm / 0.0283168466 

def L2cm(value, *args):
    return value / 1e3

def cm2L(value, *args):
    return value * 1e3

def gal2cm(value, *args):
    return value * 0.00378541

def cm2gal(value, *args):
    return value / 0.00378541

def cin2cm(value, *args):
    return value / 61023.7441

def cm2cin(value, *args):
    return value * 61023.7441

to_cm = {
    "L": L2cm,
    "m^3": same_unit,
    "gal": gal2cm,
    "ft^3": cf2cm,
    "in^3": cin2cm
}

from_cm = {
    "L": cm2L,
    "m^3": same_unit,
    "gal": cm2gal,
    "ft^3": cm2cf,
    "in^3": cm2cin
}

#mass

def kg2lb(kg, *args):
    return (kg * 2.204622476038)

def lb2kg(lb, *args):
    return lb / 2.204622476038

def nm2kg(nm, fluid):
    # Normal Flow Conditions
    T_normal = 293.15
    P_normal = 101490.8
    D_normal = getfluidproperty(
        fluid,
        "D",
        "P",
        P_normal,
        "T",
        T_normal
    )
    return nm * D_normal

def kg2nm(kg, fluid):
    # Normal Flow Conditions
    T_normal = 293.15
    P_normal = 101490.8
    D_normal = getfluidproperty(
        fluid,
        "D",
        "P",
        P_normal,
        "T",
        T_normal
    )
    return kg / D_normal

def sl2kg(sl, fluid):
    #Return kg from standard liters
    #SAES Pure Gas Standard Conditions
    T_standard = 273.15
    P_standard = 101490.8
    D_standard = getfluidproperty(
        fluid,
        "D",
        "P",
        P_standard,
        "T",
        T_standard
    )
    return sl/1e3 * D_standard

def kg2sl(kg, fluid):
    #Return standard liters from kg
    #SAES Pure Gas Standard Conditions
    T_standard = 273.15
    P_standard = 101490.8
    D_standard = getfluidproperty(
        fluid,
        "D",
        "P",
        P_standard,
        "T",
        T_standard
    )
    return kg / D_standard * 1e3

def scf2kg(scf, fluid):
    """
    Return kilograms given standard cubic feet and fluid
    Standard Cubic Feet are evaluated at 14.696 psia, 61 °F
    scf: number of standard cubic feet, int or float
    fluid: name of fluid, all caps, REFPROP style
    """
    T_standard = F2K(61)
    P_standard = psia2Pa(14.696)
    D_standard = getfluidproperty(
        fluid,
        "D",
        "P",
        P_standard,
        "T",
        T_standard
    )
    return cf2cm(scf) * D_standard
    
def kg2scf(kg, fluid):
    """
    Return standard cubic feet given kilograms and fluid
    Standard Cubic Feet are evaluated at 14.696 psia, 61 °F
    scf: number of standard cubic feet, int or float
    fluid: name of fluid, all caps, REFPROP style
    """
    T_standard = F2K(61)
    P_standard = psia2Pa(14.696)
    D_standard = getfluidproperty(
        fluid,
        "D",
        "P",
        P_standard,
        "T",
        T_standard
    )
    return cm2cf(kg / D_standard)



#mass flow rate

def kgps2ncmphr(value, fluid):
    return kg2nm(value, fluid) * 3600

def ncmphr2kgps(value, fluid):
    return nm2kg(value, fluid) / 3600

def kgps2slpm(value, fluid):
    return kg2sl(value, fluid) * 60

def slpm2kgps(value, fluid):
    return sl2kg(value, fluid) /60

def kgps2scfm(value, fluid):
    return kg2scf(value, fluid) * 60

def scfm2kgps(value, fluid):
    return scf2kg(value, fluid) / 60

#density

def kgpcm2gpccm(value, *args):
    return value * 1e-3

def gpccm2kgpcm(value, *args):
    return value * 1e3

def kgpcm2lbpcf(value, *args):
    return value * 0.0624279606

def lbpcf2kgpcm(value, *args):
    return value / 0.0624279606

def kgpcm2lbpgal(value, *args):
    return value * 0.0083454045

def lbpgal2kgpcm(value, *args):
    return value / 0.0083454045

def kgpcm2lbpcin(value, *args):
    return value * 0.0000361273

def lbpcin2kgpcm(value, *args):
    return value / 0.0000361273

from_kgpcm = {
    "kg/m^3": same_unit,
    "g/cm^3": kgpcm2gpccm,
    "lbm/ft^3": kgpcm2lbpcf,
    "lbm/gal": kgpcm2lbpgal,
    "lbm/in^3": kgpcm2lbpcin
}

to_kgpcm = {
    "kg/m^3": same_unit,
    "g/cm^3": gpccm2kgpcm,
    "lbm/ft^3": lbpcf2kgpcm,
    "lbm/gal": lbpgal2kgpcm,
    "lbm/in^3": lbpcin2kgpcm
}

#pressure

def psia2Pa(psia, *args):
    return psia * 6894.75729

def Pa2psia(Pa, *args):
    return Pa / 6894.75729

def psig2Pa(value, *args):
    return psia2Pa(value + Pa2psia(101325))

def Pa2psig(value, *args):
    return Pa2psia(value) - Pa2psia(101325)

def bara2Pa(value, *args):
    return value*1e5

def Pa2bara(value, *args):
    return value/1e5

def barg2Pa(value, *args):
    return value*1e5 + 101325

def Pa2barg(value, *args):
    return value/1e5 - 1.01325

def Pa2atm(value, *args):
    return value / 101325

def atm2Pa(value, *args):
    return value * 101325

#Temperature
def Rank2K(Rank, *args):
    return Rank * 5 / 9

def K2Rank(K, *args):
    return K * 9 / 5

def Rank2F(Rank, *args):
    return Rank - 459.67

def F2Rank(F, *args):
    return F + 459.67

def K2C(K, *args):
    return K-273.15

def C2K(C, *args):
    return C+273.15

def F2K(F, *args):
    return Rank2K(F2Rank(F))

def K2F(K, *args):
    return Rank2F(K2Rank(K))


from_kgps = {
    "kg/s": same_unit,
    "lbm/s": kg2lb,
    "Nm^3/hr": kgps2ncmphr,
    "SLPM": kgps2slpm,
    "SCFM": kgps2scfm
}

to_kgps = {
    "kg/s": same_unit,
    "lbm/s": lb2kg,
    "Nm^3/hr": ncmphr2kgps,
    "SLPM": slpm2kgps,
    "SCFM": scfm2kgps
}

from_Pa = {
    "psia": Pa2psia,
    "psig": Pa2psig,
    "Pa": same_unit,
    "bar,a": Pa2bara,
    "bar,g": Pa2barg,
    "atm": Pa2atm
}

to_Pa = {
    "psia": psia2Pa,
    "psig": psig2Pa,
    "Pa": same_unit,
    "bar,a": bara2Pa,
    "bar,g": barg2Pa,
    "atm": atm2Pa
}

from_K = {
    "C": K2C,
    "K": same_unit,
    "F": K2F,
    "Rank": K2Rank
}

to_K = {
    "C": C2K,
    "K": same_unit,
    "F": F2K,
    "Rank": Rank2K
}

to_sm = {
    "mm^2": smm2sm,
    "m^2": same_unit,
    "in^2": sin2sm,
    "ft^2": sft2sm
}

from_sm = {
    "mm^2": sm2smm,
    "m^2": same_unit,
    "in^2": sm2sin,
    "ft^2": sm2sft
}

def unit_convert(value1, unit1, unit2, fluid="AIR", Cd=1.0):
    """
    Converts value1 from unit1 to unit2
    value1: int or float
    unit1: "from" unit name, string, use nomenclature from lists
    unit2: "to" unit name, string, use nomenclature from lists
    """

    if unit1 in mass_flow_units and unit2 in mass_flow_units:
        kgps = to_kgps[unit1](value1, fluid)
        value2 = from_kgps[unit2](kgps, fluid)
    elif unit1 in pressure_units and unit2 in pressure_units:
        Pa = to_Pa[unit1](value1)
        value2 = from_Pa[unit2](Pa)
    elif unit1 in temperature_units and unit2 in temperature_units:
        K = to_K[unit1](value1)
        value2 = from_K[unit2](K)
    elif unit1 in area_units and unit2 in area_units:
        sm = to_sm[unit1](value1)
        value2 = from_sm[unit2](sm)
    elif unit1 in volume_units and unit2 in volume_units:
        cm = to_cm[unit1](value1)
        value2 = from_cm[unit2](cm)
    elif unit1 in distance_units and unit2 in distance_units:
        m = to_m[unit1](value1)
        value2 = from_m[unit2](m)
    elif unit1 in flow_capacity_units and unit2 in flow_capacity_units:
        CdA = to_CdA[unit1](value1, Cd)
        value2 = from_CdA[unit2](CdA, Cd)
    elif unit1 in density_units and unit2 in density_units:
        kgpcm = to_kgpcm[unit1](value1)
        value2 = from_kgpcm[unit2](value1)
    else: 
        print("Not a valid combination")
        value2 = 1


    return value2

# Equation functions

def mdotidealgas(
    upstream_pressure,
    upstream_density,
    downstream_pressure,
    CdA,
    fluid
):
    gamma = getfluidproperty(
        fluid,
        "CP/CV",
        "P",
        upstream_pressure,
        "D",
        upstream_density
    )
    crit_pressure = (
        upstream_pressure * (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    )
    if crit_pressure > downstream_pressure:
        P2 = crit_pressure
    else:
        P2 = downstream_pressure
    return (
        CdA * m.sqrt(
            upstream_pressure * upstream_density * 2 * gamma / (gamma - 1)
            * (P2 / upstream_pressure)**(2/gamma)
            * (1 - (P2/upstream_pressure)**((gamma-1)/gamma))
        )
    ) if upstream_pressure > downstream_pressure else 0

def mdot2CdA(
    upstream_pressure,
    upstream_density,
    downstream_pressure,
    mdot,
    fluid
):
    gamma = getfluidproperty(
        fluid,
        "CP/CV",
        "P",
        upstream_pressure,
        "D",
        upstream_density
    )
    crit_pressure = (
        upstream_pressure * (2 / (gamma + 1)) ** (gamma / (gamma - 1))
    )
    if crit_pressure > downstream_pressure:
        P2 = crit_pressure
    else:
        P2 = downstream_pressure
    return (
        mdot / m.sqrt(
            upstream_pressure * upstream_density * 2 * gamma / (gamma - 1)
            * (P2 / upstream_pressure)**(2/gamma)
            * (1 - (P2/upstream_pressure)**((gamma-1)/gamma))
        )
    ) if upstream_pressure > downstream_pressure else 0


def moody_tau(
    P1,
    P2,
    T1,
    CdA,
    Volume,
    fluid
):
    gamma = getfluidproperty(
        fluid,
        "CP/CV",
        "P",
        P1,
        "T",
        T1
    )
    D1 = getfluidproperty(
        fluid,
        "D",
        "P",
        P1,
        "T",
        T1
    )
    numerator = (P2 / P1) ** ((1-gamma)/(2*gamma)) - 1
    denomenator = CdA / Volume * (gamma - 1) / 2 * (2 / (gamma + 1))**((gamma + 1)/(2 * (gamma - 1))) * m.sqrt(gamma * P1 / D1)
    return numerator / denomenator

def Nusseldt2h(
    Nusseldt,
    characteristic_length,
    fluid,
    first_property, 
    first_value, 
    second_property, 
    second_value):
    thermal_conductivity = getfluidproperty(
        fluid,
        "TCX",
        first_property,
        first_value,
        second_property,
        second_value
    )
    return Nusseldt * thermal_conductivity / characteristic_length

def churchill_bernstein(
    Reynolds,
    Prandtl):
    Nusseldt = 0.3 + 0.62 * Reynolds**0.5 * Prandtl**(1/3) / (
        1 + (0.4/Prandtl)**(2/3)
    )**0.25 * (
        1 + (
            Reynolds / 282000
        )**0.625
    )**0.8
    return Nusseldt

def reynolds(
    flow_velocity,
    characteristic_length,
    fluid,
    first_property, 
    first_value, 
    second_property, 
    second_value):
    kinematic_viscosity = getfluidproperty(
        fluid,
        "KV",
        first_property, 
        first_value, 
        second_property, 
        second_value
    )
    return flow_velocity * characteristic_length / kinematic_viscosity

def critical_pressure(gamma, P1):
    return P1 * (2/(gamma + 1))**(gamma / (gamma - 1))


def churchill_chu(Rayleigh, Prandtl):
    Nusseldt = (
        0.60 + 0.387 * Rayleigh**(1/6) / (
            1 + (
                0.559/Prandtl
            )**(9/16)
        )**(8/27)
    )**2
    return Nusseldt

def Grashof(fluid,
    first_property, 
    first_value, 
    second_property, 
    second_value, 
    surface_temp,
    fluid_temp,
    characteristic_length):
    g = 9.81 #m/s2
    volume_expansivity = getfluidproperty(
        fluid,
        "BETA",
        first_property,
        first_value,
        second_property,
        second_value
    )
    kinematic_viscosity = getfluidproperty(
        fluid,
        "KV",
        first_property,
        first_value,
        second_property,
        second_value
    )
    return (
        g * volume_expansivity * (surface_temp - fluid_temp) *
        characteristic_length**3 / kinematic_viscosity
    )

def Rayleigh(Grashof, Prandtl):
    return Grashof * Prandtl