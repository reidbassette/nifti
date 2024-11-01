import sys

import numpy as np
import CoolProp.CoolProp as CP
from CoolProp.CoolProp import PropsSI
from ctREFPROP.ctREFPROP import REFPROPFunctionLibrary
import math as m
import os


# Getters
def getR(fluid):
    ''' 
    Returns Specific Gas Constant for provided fluid in [J/(kg*K)]

    ''' 
    M = CP.PropsSI('M', fluid)
    R = 8.314/M
    return R


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

# CoolProp input dictionary
CoolProp_names = {
    "TCX": "CONDUCTIVITY",
    "CP": "CPMASS",
    "CV": "CVMASS",
    "D" :"D"
}

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
        if fluid == "CARBON DIOXIDE":
            fluid = "CARBONDIOXIDE"
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
        elif desired_property == "R":
            output = PropsSI(
                "GAS_CONSTANT",
                first_property,
                first_value,
                second_property,
                second_value,
                fluid
            ) / PropsSI(
                "M",
                first_property,
                first_value,
                second_property,
                second_value,
                fluid
            )
        else:
            if CoolProp_names[desired_property] is not None:
                output = PropsSI(
                    CoolProp_names[desired_property],
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


# Cv Conversions 
def Cv2Do(Cv):
    '''
    Returns equivalent ESEOD (Cd = 0.6) for a provided Cv
    Cv: Flow coefficient defined as GPM H2O given 1psid across component
    '''
    return 0.236*Cv**0.5

def Cv2F(Cv): 
    '''
    Returns flow factor for a provided Cv
    Cv: Flow coefficient defined as GPM H2O given 1psid across component at 60F
    ''' 
    return 0.556*Cv 

def Cv2CdA(Cv):
    '''
    Returns effective flow Area for a provided Cv.
    Assume Cd = 0.6
    Cv: Flow coefficient defined as GPM H2O given 1psid across component
    '''
    Do = Cv2Do(Cv)
    return 0.6*m.pi*Do**2/4

#Do conversions
def Do2Cv(Do):
    '''
    Returns CV for a provided ESEOD
    Do: equivalent sharp-edged orifice diameter (ESEOD)

    '''
    return (Do/.236)**2 


def Do2CdA(Do):
    '''
    Returns effective flow area for a provided Do
    Do: equivalent sharp-edged orifice diameter (ESEOD)
    '''
    Cv = Do2Cv(Do)
    return Cv2CdA(Cv)
    

def Do2F(Do):
    '''
    Returns Flow Factor for a provided ESOD (Cd = 0.6)
    
    '''
    return 10.01*Do**2
    


#Flow Factor Conversions
def F2Do(F): 
    '''
    Returns ESOD for a provided flow factor

    '''
    return 0.316*F**.5


def F2Cv(F): 
    '''
    Returns Cv for a provided flow Factor

    '''
    return 1.8*F


#Equivalent Orifice Diameter
def Do(Q, w, dP):
    '''
    Returns ESEOD for a provided flow rate Q, specific weight w, and Pressure drop dP
    '''
    return 1.445*Q**2*w**.25/dP**.25
    

# Flow Equations

def mdotIG(P1, P2, T1, CdA, fluid):
    '''
    Returns mass flow rate for an ideal gas for a provided pressure differential, Temperature, CdA, and Fluid

    '''
    g = 9.81 #m/s^2
    R = getR(fluid)
    cp = getfluidproperty(fluid, 'Cp0mass','P', P1,'T', T1) #Need to be able to distinguish between Coolprop and REFPROP
    gamma = cp/(cp - R)
    PcOverP1 = (2/(gamma+1))**(gamma/(gamma-1))

    if P2/P1 <= PcOverP1:
        '''CHOKED'''
        return CdA*P1*((g*gamma/(R*T1))*(2/(gamma+1))**((gamma+1)/(gamma-1)))**.5
    else:
        return CdA*(P2/P1)**(1/gamma)*(2*g*R*T1*(gamma/(gamma-1))*(1-(P2/P1)**((gamma-1)/gamma)))**.5

# Mass Conversions
def kg2lb(kg):
    '''
    kilogram to pound
    '''
    return 2.204*kg
    

def lb2kg(lb):
    '''
    Pound to Kilogram
    '''
    return lb/2.204
 
# Length Conversions
def m2ft(m):
    '''
    meter to foot
    '''
    return m/.3048
   

def ft2m(ft):
    '''
    Foot to Meter
    '''
    return ft*.3048
  

def inch2m(inch):
    '''
    Inch to Meter 
    '''
    return inch*.0254
    

def m2inch(m):
    ''' 
    Meter to Inch
    '''
    return m/.0254
    
# Area Conversions

def sm2sf(sm):  
    '''
    Meter squared to foot squared
    '''
    return sm*3.281**2

def sf2sm(sf): 
    '''
    Foot squared to meter squared
    '''
    return sf/(3.281**2)

def si2sm(si):
    '''
    inches squared to meters squared
    '''
    return si*.0254**2
    

def sm2si(sm): 
    '''
    Meters squared to inches squared 
    '''
    return sm/(.0254**2)
    

# Volume Conversions

def cintocm(cin): 
    '''
    cubic inch to cubic meter
    '''
    return cin/61023.7441
    

def cmtocin(cm):
    '''
    cubic meter to cubic inch
    '''
    return cm*61023.7441
   

# Density Conversions

def kgcmtolbcf(kgcm):
    '''
    
    kilogram per cubic meter to pound per cubic foot
    '''
    return kgcm/16.018


def lbcftokgcm(lbcf):
    '''
    pound per cubic foot to kilogram per cubic meter
    '''
    return lbcf*16.018
    

# Temperature Coversions
def F2K(F):
    '''
    Fahrenheit to Kelvin 
    '''
    return (F-32)/1.8+273.15

def K2F(K): 
    '''
    Kelvin to Fahrenheit
    '''
    return ((K-273.15)*1.8)+32


def C2F(C): 
    '''
    Celsius to Fahrenheit
    '''
    return C*1.8+32

def F2C(F):
    '''
    Fahrenheit to Celsius
    '''
    return (F-32)/1.8

# Pressure Conversions

def psi2pa(psi):
    '''
    Psi to Pascal
    '''
    return psi*6894.76

def pa2psi(pa): 
    '''
    Pascal to Psi
    '''
    return pa/6894.76

def cmm2cin(cmm):
    '''
    Cubic millimeters to Cubic inches
    '''
    return cmm/16387.064

