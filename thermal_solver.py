
'''
Assumptions: 
ignore radiation 

'''
import numpy as np
from scipy.integrate import solve_ivp
import mat_lib as p
import utilities as u

material_mapping = {
    "SS316": "p.SS316",
    "Al6061": "p.Al6061",
    "Al7075T6" : "p.Al7075T6"
}

class Node:
    '''
    Creates Temperature node with HT attributes
    '''
    def __init__(
        self, 
        T, 
        
        medium_type, 
        medium = 'CUSTOM', 
        V = 0.0, 
        Eg = 0.0, 
        Pressure = 0.0,
        isothermal = False,
        connectedPaths = None,
        e = 0.0,
        a = 0.0,
        density = 0.0,
        k = 0.0, 
        c = 0.0,
        identifier = 0
        ): 
        '''
        T = type::float; initial temperature, K
        
        medium_type = "FLUID" or "SOLID"
        
        '''
        self.medium = medium
        self.medium_type = medium_type
        if medium_type == "FLUID":
            self.density = u.getfluidproperty(
                self.medium,
                'D',
                'T',
                T,
                'P',
                Pressure
            ) #kg/m3 
            self.k = u.getfluidproperty(
                self.medium,
                'TCX',
                'T',
                T,
                "P",
                Pressure
            ) #W/m-K
            self.c = u.getfluidproperty(
                self.medium,
                'CP',
                'T',
                T,
                'P',
                Pressure
            ) #J/kgK
        elif medium_type == "SOLID": 
            if medium == 'CUSTOM':
                self.density = density
                self.c = c
                self.k = k
            else:
                self.material = eval(material_mapping.get(self.medium)) # type: ignore
                self.density = p.getMatProp(self.material, "density") #kg/m3 
                self.k= p.getMatProp(self.material, "k") #W/m-K
                self.c = p.getMatProp(self.material, "specificHeatCapacity") #J/kgK

        self.isothermal = isothermal #isothermal condition is true if isothermal == 1 
        if isothermal == False and V == 0.0:
            raise Exception("non-Isothermal node must have a volume")
        else:
            self.V = V #m3
        self.Pressure = Pressure
        self.T = T #K 
        self.Eg = Eg #W, heat generated
        self.e = e
        self.a = a 
        self.identifier = identifier
        if self.e == 0.0 and medium_type == "SOLID":
            self.e = 0 #emissivity
        if isothermal == True:
            self.a = e # Kirchoff's Law
        if connectedPaths is None:
            self.connectedPaths = [] #specifies which paths are connected to node
    
class Path:
    '''
    Creates Conduction, Convection, or Radiation Pathway between Nodes
    Assumptions: Path is of Constant Area
    '''
    def __init__(
        self, 
        nodeA, 
        nodeB, 
        Area=0.0, 
        dx=1.0, 
        h=0.0,
        F=1.0,
        identifier = 0
    ):
        self.Area = Area #Heat Transfer Area [m^2]
        self.dx = dx #length [m]
        self.h = h # Overall heat transfer coefficient [W/m2K]

        self.nodeA = nodeA 
        self.nodeB = nodeB
        self.F = F #View Factor between paths
        self.k = (nodeA.k+nodeB.k)/2  #conduction coefficient [W/mK]

        self.identifier = identifier

    
def T_vs_t(t, t_eval, path, nodes):
    """
    t: timespan, list [t_start, t_end]
    t_eval: array of evaluation times
    path: list of paths
    nodes: list of nodes
    """
    n = len(nodes)
    T = []
    for node in nodes: 
        T.append(node.T)
    if n > 2:
        for i in range(n):
            for j in range(len(path)):  
                if path[j].nodeA == nodes[i] or path[j].nodeB == nodes[i]: #if either of path j's nodes are equal to current node, append path to connected attribute path
                    nodes[i].connectedPaths.append(j)
    
    def func(t,T):
        try:
            dTdt = np.zeros(n, dtype=float)
            if n == 2: #Only two nodes
                '''index addded to work with t_solve.py'''
                a = path[0]
                k = a.k 
                h = a.h
                dx = a.dx

                Area = a.Area

                e0 = a.nodeA.e
                a0 = a.nodeA.a 

                e1 = a.nodeB.e
                a1 = a.nodeB.a

                Eg0 = a.nodeA.Eg
                Eg1 = a.nodeB.Eg

                sig = 5.678e-8
                dT = (T[0] - T[1]) 
                dT4= (T[0]**4 -T[1]**4)
                if T[0] >= T[1]: #T0 is emmitting
                    dTdt[0] = (Eg0  - k * Area*dT / dx - h * Area *dT  - (sig * Area * e0*dT4))/(a.nodeA.density*a.nodeA.V*a.nodeA.c)if nodes[0].isothermal == False else 0
                elif T[0] <= T[1]: #T0 is absorbing
                    dTdt[0] = (Eg0 - k * Area*dT  / dx - h * Area *dT  - (sig * Area * a0*
                    dT4))/(a.nodeA.density*a.nodeA.V*a.nodeA.c)if nodes[0].isothermal == False else 0
                if T[1] >= T[0]: #T1 is emitting
                    dTdt[1] =  (Eg1 - k * Area*dT *(-1) / dx - h * Area *-dT - (sig * Area * e1*dT4*-1))/(a.nodeB.density*a.nodeB.V*a.nodeB.c)if nodes[1].isothermal == False else 0
                elif T[1] <= T[0]: #T1 is absorbing
                    dTdt[1] =  (Eg1 - k * Area*-dT / dx - h * Area *-dT - (sig * Area * a1*dT4*-1))/(a.nodeB.density*a.nodeB.V*a.nodeB.c)if nodes[1].isothermal == False else 0
                return dTdt
            else:
                for i in range(n):
                    # for node i get connectedPaths
                    P = nodes[i].connectedPaths
                    for j in range(len(P)):
                        #Iterate thru each connected to node i
                        '''Conduction Terms'''
                        k = path[P[j]].k
                        dx = path[P[j]].dx
                        Area = path[P[j]].Area
                        '''Convection Terms'''
                        h = path[P[j]].h
                        '''Radiation Terms'''
                        e_A = path[P[j]].nodeA.e
                        a_A = path[P[j]].nodeA.a
                        e_B = path[P[j]].nodeB.e
                        a_B = path[P[j]].nodeB.a
                        
                        sig = 5.678e-8 
                        Eg_A = path[P[j]].nodeA.Eg
                        Eg_B = path[P[j]].nodeB.Eg
                        
                        #get temperature associated with path[p[j]] order must be maintained. 
                        T1 = T[nodes.index(path[P[j]].nodeA)]
                        T2 = T[nodes.index(path[P[j]].nodeB)]
                        
                        if nodes.index(path[P[j]].nodeA) == i: #If T being accessed is from iteration node; use this equation
                            if T1 > T2:
                                dTdt[i] = (
                                    dTdt[i] - (-Eg_A+k*Area*(T1-T2) / dx + h * Area * (T1 - T2) 
                                    + (e_A)*sig*Area*(T1**4 - T2**4))/(path[P[j]].nodeA.density 
                                    * path[P[j]].nodeA.V * path[P[j]].nodeA.c) if nodes[i].isothermal == False else 0
                                )
                            elif T1 < T2: 
                                dTdt[i] = (
                                    dTdt[i] - (-Eg_A+ k*Area*(T1-T2) / dx + h * Area * (T1 - T2) 
                                    + (a_A)*sig*Area*(T1**4 - T2**4))/(path[P[j]].nodeA.density 
                                    * path[P[j]].nodeA.V * path[P[j]].nodeA.c) if nodes[i].isothermal == False else 0
                                )
                        elif nodes.index(path[P[j]].nodeA) != i: #If T being accessed is not from iteration node; use this equation
                            if T1 > T2:    
                                dTdt[i] =  (
                                    dTdt[i] - (-Eg_B+k*Area*(T2-T1) / dx + h * Area * (T2 - T1)
                                    + (a_B)*sig*Area*(T2**4 - T1**4))/(path[P[j]].nodeB.density 
                                    * path[P[j]].nodeB.V * path[P[j]].nodeB.c) if nodes[i].isothermal == False else 0
                                )
                            elif T1 < T2: 
                                dTdt[i] =  (
                                    dTdt[i] - (-Eg_B+k*Area*(T2-T1) / dx + h * Area * (T2 - T1)
                                    + (e_B)*sig*Area*(T2**4 - T1**4))/(path[P[j]].nodeB.density 
                                    * path[P[j]].nodeB.V * path[P[j]].nodeB.c) if nodes[i].isothermal == False else 0
                                )
            return dTdt 

        except Exception as e:
            print(e)
        
    return solve_ivp(func, t_span=t, t_eval=t_eval, y0=T, rtol = 1e-3)
