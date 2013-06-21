#!/usr/bin/python
import sys

from math import *
from pylab import *
import numpy as np
import copy
import itertools


import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from matplotlib import rc
import scipy.stats as stat
import scipy.optimize as optimize
import scipy.integrate as integrate

import nd_Fit2 as ndf

rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
## for Palatino and other serif fonts use:
#rc('font',**{'family':'serif','serif':['Palatino']})
rc('text', usetex=True)


# calculate the fermi level in graphene
def fermiLevel(T,carriersMeas=None): 

    k = 8.617e-5       #eV/K
    hbar = 6.582e-16   #eV*s
    vfermi = 1e8       #cm/s

    # Variable Constants
    eThermal = lambda T: k*T
    momentum = hbar*vfermi

    # Find carriers for various fermi levels
    carriers = []
    Ef = np.linspace(0.1,0.7,100)
    for i,E in enumerate(Ef):
        function = lambda r: r/(1+ np.exp(r-(E/eThermal(T))));
        n = (2/math.pi)*((eThermal(T)/momentum)**2)*integrate.quad(function,0,np.inf)[0]
        carriers.append(n)
  
    # Loop to find fermi level given carrier density
    if carriersMeas is not None:
        for i,n in enumerate(carriers):
            if carriersMeas < n: 
               return Ef[i]

# Calculate the carriers given a fermiLevel
def fermiCarriers(T, Ef):
    
    # Define Constants
    k = 8.617e-5       #eV/K
    hbar = 6.582e-16   #eV*s
    vfermi = 1e8       #cm/s

    # Variable Constants
    eThermal = lambda T:k*T
    momentum = hbar*vfermi

    # Integrate over wavevectors
    function = lambda r: r/(1+np.exp(r-(Ef/eThermal(T))))
    carriers = lambda T: (2/math.pi)*((eThermal(T)/momentum)**2)*integrate.quad(function,0,np.inf)[0]

    # Return Carrier Density
    return carriers(T)

# carriers is a constant fit phonon energy
def surfacePhononFit(carriers, temp, vsat, eFermi): 

    # Define Constants
    k = 8.617e-5       #eV/K
    hbar = 6.582e-16   #eV*s
    vfermi = 1e8       #cm/s
    momentum = hbar*vfermi
   
    # Functions for phonon calculation
    Noccup = lambda ePhonon,T: 1/(np.exp(ePhonon/eThermal(T))-1)
    const1 = lambda T: 2/(hbar*pi*sqrt(pi*_carriers(T))) 
    const2 = lambda T: 1/(4*pi*_carriers(T)*(momentum**2))
    
    # Get the carriers for a given Fermi energy
    eThermal = lambda T: k*T
    _carriers = lambda T: fermiCarriers(T,eFermi)

    # Calculate the Fermi Level
    eF_fit = eFermi

    ############################################
    # Fit a Phonon Energy to Velocity vs. Temp #
    ############################################
    _data = [temp,vsat] 

    fitfunc = lambda eP,d: const1(d[0])*eP[0]*sqrt(1-(eP[0]**2)*const2(d[0]))*(1/(Noccup(eP[0],d[0])+1))
    errfunc = lambda eP,d: fitfunc(eP,d) - d[1]
    fit_guess, fit_step, convergence, maxdepth = [0.100],[0.001],1e12,1000 
  
    # Run recursive fit
    fit = ndf.nd_Fit2(_data, fitfunc, errfunc, fit_guess, fit_step, convergence, maxdepth)
    fit.fit_run()
      
    # Print recursion informtiton 
    print ""
    print "--------- Phonon Fit ----------" 
    print "recursion depth:"+str(fit.depth) 
    print "convergence:"+str(fit.res_vec[-1])
    print "noise amplitude:"+str(fit.res_vec[-1]/len(temp)) 
    print "params:"+str(fit.p_found) 
 
    # Generate the nd_curve (the result)
    curve = fit.nd_curve_extended(2)

    # Get Best Fit value
    tempFit = curve[0]
    vsatFit = curve[1]
    
    result = {}   
    # Store Measured Data
    result['carriersMeas'] = carriers
    result['tempMeas'] = temp
    result['vsatMeas'] = vsat
    
    # Store Results of Fit
    result['tempFit'] = tempFit
    result['vsatFit'] = vsatFit
    result['ePhonon'] = fit.p_vec[-1]
    result['eFermi']  = eF_fit
    
    # Return Result
    return result
  
def velocityFieldFit(field, velocity, fit_guess, fit_step, convergence, maxdepth, temp=None): 

    # Store Data 
    field = [float(e) for e in field]
    velocity = [float(v) for v in velocity]
    _data = [field[2::2], velocity[2::2]] 

    # Fitting to Velocity Field Model
    fitfunc = lambda p, d: (p[0]*d[0])/np.power((1+np.power((p[0]*d[0]/p[1]),p[2])), 1/p[2])                    
    errfunc = lambda p, d: np.log10(fitfunc(p,d))-np.log10(d[1])                       
    
    # Run recursive fit
    fit = ndf.nd_Fit2(_data, fitfunc, errfunc, fit_guess, fit_step, convergence, maxdepth)
    fit.lattice_select("fco")
    fit.fit_throttling(1e-1, 3, 1e-3, 3)
    fit.fit_run()

    curve = fit.nd_curve_extended(4)


    # Print recursion informtiton 
    print "recursion depth:"+str(fit.depth) 
    print "convergence:"+str(fit.res_vec[-1])
    print "noise amplitude:"+str(fit.noise_vec[-1]) 
    print "params:"+str(fit.p_found) 
    
    result = {}
    # Store Measured Data
    result['fieldMeas'] = field
    result['velocityMeas'] = velocity
    
    # Store Results of Fit
    result['fieldFit'] = curve[0]
    result['velocityFit'] = curve[1]
    result['mu'] = fit.p_found[0]
    result['vsat'] = fit.p_found[1]
    result['alpha'] = fit.p_found[2]

    # Return Result
    return result

def ivTanhFit(voltage,current,fit_guess,fit_step,convergence,maxdepth): 

    # Store Data
    _data = [voltage, current]

    # Hyperbolic model
    #fitfunc = lambda p,data: p[0] 
    fitfunc = lambda p,d: p[0]*(1 + p[1]*d[0])*np.tanh(p[2]*d[0]) 
    errfunc = lambda p,d: fitfunc(p,d)-d[1]
  
    # Run recursive fit with lattice throttling
    fit = ndf.nd_Fit2(_data, fitfunc, errfunc, fit_guess, fit_step, convergence, maxdepth)
    fit.lattice_select("fco")
    fit.fit_throttling(1e-3, 2, 1e-3, 2)
    fit.fit_run()

    # Generate the nd_curve (the result)
    curve = fit.nd_curve()

    # Calculate Resistance
    rfunc = lambda p,v: p[0]*p[1]*(1+p[1]*v)+p[0]*p[2]*(1 + p[1]*v)*(1-np.tanh(p[2]*v)**2)  
    resistance = [ rfunc(fit.p_found, v) for v in curve[0]]
    resistance = np.divide(1,resistance) 

    # Print recursion informtiton 
    print "recursion depth:"+str(fit.depth) 
    print "convergence:"+str(fit.res_vec[-1])
    print "noise amplitude:"+str(fit.res_vec[-1]/len(voltage)) 
    print "params:"+str(fit.p_found) 
    return curve[0], curve[1], resistance, fit.p_found
  

def main():
    print fermiCarriers(300, .250)
    print fermiCarriers(200, .250)
    print fermiCarriers(100, .250)

    print fermiCarriers(300, .520)
    print fermiCarriers(200, .520)
    print fermiCarriers(100, .520)

    pass

if __name__ == "__main__":
    main()





































































def nonlinearFit(x,y,fitfunc,errfunc,fit_guess,fit_step, convergence=1e-6): 

    # Walk around parameter space
    res_vec, p_vec = [],[]

    #First need to set inital (p) and step size (d)
    p = [val for val in fit_guess]
    d = [val for val in fit_step]


    # Calculate the initial residual
    res = 0
    for n,val in enumerate(y): 
        res+= errfunc(p,x[n],y[n])**2
    res_vec.append(res)
    p_vec.append(p)

    c = 1
    nsteps = 10000
    while c < nsteps: 
  
        # 2n sides for an n-dimensional box in parameter space
        tmp_res,tmp_p = [],[]
        for i in range(2*len(p)): 

            # Positive Direction Steps
            if i<len(p):
                
                ####### EDGES ############
                # Deep copy of p and index 
                pt = copy.deepcopy(p)
                pt[i]+=d[i]
                # Calculate residuals
                res = 0
                for n,val in enumerate(y):
                    res+= errfunc(pt,x[n],y[n])**2
                    
                # Save residual and p
                tmp_res.append(res)
                tmp_p.append(pt)
            
                ####### CORNERS###########
                # Deep copy of p and index 
                pt = copy.deepcopy(p)
                pt = [n+d[i] for n in pt]
                # Calculate residuals
                res = 0
                for n,val in enumerate(y):
                    res+= errfunc(pt,x[n],y[n])**2
                
                # Save residual and p
                tmp_res.append(res)
                tmp_p.append(pt)


            # Negative Direction Steps
            else:      
              
                ####### EDGES ############
                # Deep copy of p and index 
                pt = copy.deepcopy(p)
                pt[i-len(p)]-=d[i-len(p)]
                # Calculate residuals
                res = 0
                for n,val in enumerate(y): 
                    res+= errfunc(pt,x[n],y[n])**2
                
                # Save residual and p
                tmp_res.append(res)
                tmp_p.append(pt)
                
                ####### CORNERS###########
                # Deep copy of p and index 
                pt = copy.deepcopy(p)
                pt = [n-d[i-len(p)] for n in pt]
                # Calculate residuals
                res = 0
                for n,val in enumerate(y): 
                    res+= errfunc(pt,x[n],y[n])**2
                
                # Save residual and p
                tmp_res.append(res)
                tmp_p.append(pt)
                                   
        # Save minimum values
        res_vec.append(min(tmp_res))
        p_vec.append(tmp_p[tmp_res.index(min(tmp_res))])
             
        if (np.abs(res_vec[-1]) > np.abs(res_vec[-2])) and (min(res_vec)<convergence):
            p_found =  p_vec[-1]
            break

        else: 
            # Make the step
            p = p_vec[-1]
            c+=1

    if c == nsteps: 
        print "Warning: Probably not converged - try again with larger step"
        print "Returning final value" 
        p_found = p_vec[-1] 

    _x = np.linspace(min(x), max(x), 1000)
    _y = fitfunc(p_found,np.linspace(min(x), max(x), 1000))

    print p_found
    result = {}
    result["domain"] = _x
    result["range"] = _y 
    result["p_found"] = p_vec[-1]
    result["p_walk"] = p_vec
    result["residual"] = res_vec
    return result



