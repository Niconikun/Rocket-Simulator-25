# Author: Jorge Orozco
#         Universidad de Concepción, Facultad de Ingeniería
#         E-mail: joorozco@udec.cl

"""

*** MatTools.py ***

Contains:
Functions for mathematical operations.

External dependencies:
numpy       -Numpy Python extension. http://numpy.org/
             Version: Numpy 1.22.3

Internal dependencies:
cmath       -cMath Python extension. https://docs.python.org/3/library/cmath.html

Changelog:
Date          Name              Change
__ _          __ _              ____ _
15/08/2022    Jorge Orozco      Initial release

References:
Short     Author,Year     Title
___ _     _________ _     ___ _

"""
# Imports
import numpy as np
from cmath import pi

# Auxiliary funtions
deg2rad=pi/180
rad2deg=180/pi

def hexa2dec(coord):
    'coord=[hour, minute, second] to coord[deg]'
    
    dec=coord[0]+((coord[1])/60)+((coord[2])/3600)
    return dec

def skew3(vector):   
    'vector is a 3 elements array or list'

    skew_matrix=np.array([[0,-vector[2], vector[1]],
                          [vector[2],0,-vector[0]],
                          [-vector[1],vector[0],0]])
    return skew_matrix

def skew4(vector):
    'vector is a 3 elements array or list'

    skew_matrix=np.array([[0,vector[2],-vector[1],vector[0]],
                          [-vector[2],0, vector[0],vector[1]],
                          [vector[1],-vector[0],0, vector[2]],
                          [-vector[0],-vector[1],-vector[2],0]])
    return skew_matrix

def mat2quat(dcm):  
    'dcm= 3X3 Director Cosine Matrix... to its respective quaternion [q1,q2,q3,q4]'

    q11=dcm[0][0]; q12=dcm[0][1]; q13=dcm[0][2]
    q21=dcm[1][0]; q22=dcm[1][1]; q23=dcm[1][2]
    q31=dcm[2][0]; q32=dcm[2][1]; q33=dcm[2][2]

    q4=0.5*(np.sqrt(1+q11+q22+q33))
    q1=(q23-q32)/(4*q4)
    q2=(q31-q13)/(4*q4)
    q3=(q12-q21)/(4*q4)

    quaternion=np.array([q1,q2,q3,q4])
    return quaternion

def quat2mat(quat):
    'quat= quaternion [q1,q2,q3,q4]... into a 3x3 Director Cosine Matrix' 

    q1=quat[0] ; q2=quat[1] ; q3=quat[2] ; q4=quat[3]
    dcm11=(q1**2) - (q2**2 )- (q3**2) + (q4**2) 
    dcm22=-(q1**2) + (q2**2 )- (q3**2) + (q4**2) 
    dcm33=-(q1**2) - (q2**2 )+ (q3**2) + (q4**2)
    dcm12=2*((q2*q1)+(q3*q4)) ; dcm21=2*((q2*q1)-(q3*q4))
    dcm13=2*((q3*q1)-(q2*q4)) ;dcm31=2*((q3*q1)+(q2*q4))
    dcm23=2*((q3*q2)+(q1*q4)) ; dcm32=2*((q3*q2)-(q1*q4))
    dcm=np.array([[dcm11,dcm12,dcm13],[dcm21,dcm22,dcm23],[dcm31,dcm32,dcm33]])
    return dcm

def check(vector):
    'Receives any length vector.Converts all elements less than 1e-8 into 0'
    for i in range(len(vector)):
        if abs(vector[i])<=10**-8:
            vector[i]=0
        else:
            vector[i]=vector[i]
    return vector

def normalise(vector):
    'Normalizes a vector'

    norm=np.linalg.norm(vector)
    if norm==0:
        unit=np.zeros(3)
    else:
        unit=(1/norm)*vector
    return unit

def vec2mat(vector):
    'Converts a 3 elements vector into a 3x3 diagonal matrix'

    v1=vector[0]; v2=vector[1]; v3=vector[2]
    mat=np.array([[v1,0,0],[0,v2,0],[0,0,v3]])
    return mat

def q_conjugate(q):
    'Conjugates a [q1,q2,q3,q4] quaternion'

    q1=-q[0]
    q2=-q[1]
    q3=-q[2]
    q4=q[3]
    conj=np.array([q1,q2,q3,q4])
    return conj

def q_rot(v,q,invs):
    """
    Rotates a vector by given quaternion [q1,q2,q3,q4]
    If invs=1 rotates in opposite direction
    """
    if invs==0:
       q_conj=q_conjugate(q)
       q_v=np.array([v[0],v[1],v[2],0])
       first=hamilton(q_conj,q_v)
       new=hamilton(first,q)
    elif invs==1:
       q_conj=q_conjugate(q)
       q_v=np.array([v[0],v[1],v[2],0])
       first=hamilton(q,q_v)
       new=hamilton(first,q_conj)
    return np.array([new[0],new[1],new[2]])

def angle_vector_z(velocity):
    """
    MAINLY USED FOR ANGLE OF ATTACK. Obtains angle between two vectors. 
    """   
    v=np.linalg.norm(velocity)
    # Attempt to correct effect of negative X component of velocity on bodyframe:
    if v==0:
        angle=0
    else:
        if velocity[0]<=0:
            angle=np.arctan2(velocity[2],-velocity[0])
        else:
            angle=np.arctan2(velocity[2],velocity[0])

    return angle*rad2deg * -1  # Convention considers clockwise angle as positive for angle of attack

def rot_z(vector,angle):
    """
    Rotates any vector around its Z axis according to input angle in [deg]
    """
    rot=angle*deg2rad
    
    sin=np.sin(rot); cos=np.cos(rot)

    dcm=np.array([[cos,-sin,0],[sin,cos,0],[0,0,1]])

    rot_vector=dcm.dot(vector)

    return rot_vector

def hamilton(left_quat,right_quat):
    'Multiplies two quaternion by Hamiltons method...right quaternion is the first rotation'

    q_1 = left_quat[3] * right_quat[0] - left_quat[2] * right_quat[1] + left_quat[1] * right_quat[2] + left_quat[0] * right_quat[3] 
    q_2 = left_quat[2] * right_quat[0] + left_quat[3] * right_quat[1] - left_quat[0] * right_quat[2] + left_quat[1] * right_quat[3] 
    q_3 = -left_quat[1] * right_quat[0] + left_quat[0] * right_quat[1] + left_quat[3] * right_quat[2] + left_quat[2] * right_quat[3] 
    q_4 = -left_quat[0] * right_quat[0] - left_quat[1] * right_quat[1] - left_quat[2] * right_quat[2] + left_quat[3] * right_quat[3]

    return np.array([q_1,q_2,q_3,q_4])

# def hamilton(q1,q2):  ### Second method
#     'Multiplies two quaternion by Hamiltons method'

#     a1=q1[3]; b1=q1[0]; c1=q1[1]; d1=q1[2]
#     a2=q2[3]; b2=q2[0]; c2=q2[1]; d2=q2[2]
    
#     q_4=a1*a2 - b1*b2 - c1*c2 - d1*d2
#     q_1=a1*b2 + b1*a2 + c1*d2 - d1*c2
#     q_2=a1*c2 - b1*d2 + c1*a2 + d1*b2
#     q_3=a1*d2 + b1*c2 - c1*b2 + d1*a2

#     return np.array([q_1,q_2,q_3,q_4])