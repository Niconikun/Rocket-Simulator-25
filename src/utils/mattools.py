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

class MatTools:
    """Clase de utilidades matemáticas para operaciones vectoriales y transformaciones."""
    
    # Constantes de clase
    deg2rad = pi/180
    rad2deg = 180/pi
    
    @staticmethod
    def hexa2dec(coord):
        """Convierte coordenadas [hora, minuto, segundo] a decimales"""
        return coord[0] + (coord[1]/60) + (coord[2]/3600)

    @staticmethod
    def skew3(vector):
        """Crea matriz antisimétrica 3x3 a partir de vector"""
        return np.array([[0, -vector[2], vector[1]],
                        [vector[2], 0, -vector[0]],
                        [-vector[1], vector[0], 0]])

    @staticmethod
    def skew4(vector):
        """Crea matriz antisimétrica 4x4 a partir de vector"""
        return np.array([[0, vector[2], -vector[1], vector[0]],
                        [-vector[2], 0, vector[0], vector[1]],
                        [vector[1], -vector[0], 0, vector[2]],
                        [-vector[0], -vector[1], -vector[2], 0]])

    @staticmethod
    def mat2quat(dcm):
        """Convierte matriz DCM a cuaternión"""
        q11, q12, q13 = dcm[0][0], dcm[0][1], dcm[0][2]
        q21, q22, q23 = dcm[1][0], dcm[1][1], dcm[1][2]
        q31, q32, q33 = dcm[2][0], dcm[2][1], dcm[2][2]

        q4 = 0.5 * (np.sqrt(1 + q11 + q22 + q33))
        q1 = (q23 - q32) / (4 * q4)
        q2 = (q31 - q13) / (4 * q4)
        q3 = (q12 - q21) / (4 * q4)

        return np.array([q1, q2, q3, q4])

    @staticmethod
    def quat2mat(quat):
        """Convierte cuaternión a matriz DCM"""
        q1, q2, q3, q4 = quat[0], quat[1], quat[2], quat[3]
        
        dcm11 = (q1**2) - (q2**2) - (q3**2) + (q4**2)
        dcm22 = -(q1**2) + (q2**2) - (q3**2) + (q4**2)
        dcm33 = -(q1**2) - (q2**2) + (q3**2) + (q4**2)
        dcm12 = 2*((q2*q1) + (q3*q4))
        dcm21 = 2*((q2*q1) - (q3*q4))
        dcm13 = 2*((q3*q1) - (q2*q4))
        dcm31 = 2*((q3*q1) + (q2*q4))
        dcm23 = 2*((q3*q2) + (q1*q4))
        dcm32 = 2*((q3*q2) - (q1*q4))
        
        return np.array([[dcm11, dcm12, dcm13],
                        [dcm21, dcm22, dcm23],
                        [dcm31, dcm32, dcm33]])

    @staticmethod
    def check(vector):
        """Convierte elementos menores a 1e-8 en 0"""
        return np.where(np.abs(vector) <= 1e-8, 0, vector)

    @staticmethod
    def normalise(vector):
        """Normaliza un vector"""
        norm = np.linalg.norm(vector)
        return np.zeros(3) if norm == 0 else vector/norm

    @staticmethod
    def vec2mat(vector):
        """Convierte vector 3D en matriz diagonal"""
        return np.diag(vector)

    @staticmethod
    def q_conjugate(q):
        """Calcula el conjugado de un cuaternión"""
        return np.array([-q[0], -q[1], -q[2], q[3]])

    @staticmethod
    def q_rot(v, q, invs):
        """Rota un vector usando un cuaternión"""
        q_v = np.array([v[0], v[1], v[2], 0])
        if invs == 0:
            q_conj = MatTools.q_conjugate(q)
            first = MatTools.hamilton(q_conj, q_v)
            new = MatTools.hamilton(first, q)
        else:
            q_conj = MatTools.q_conjugate(q)
            first = MatTools.hamilton(q, q_v)
            new = MatTools.hamilton(first, q_conj)
        return np.array([new[0], new[1], new[2]])

    @staticmethod
    def angle_vector_z(velocity):
        """Calcula ángulo entre vector y eje Z"""
        v = np.linalg.norm(velocity)
        if v == 0:
            return 0
        angle = np.arctan2(velocity[2], -velocity[0] if velocity[0] <= 0 else velocity[0])
        return angle * MatTools.rad2deg * -1

    @staticmethod
    def rot_z(vector, angle):
        """Rota vector alrededor del eje Z"""
        rot = angle * MatTools.deg2rad
        sin, cos = np.sin(rot), np.cos(rot)
        dcm = np.array([[cos, -sin, 0],
                       [sin, cos, 0],
                       [0, 0, 1]])
        return dcm.dot(vector)

    @staticmethod
    def hamilton(left_quat, right_quat):
        """Multiplicación de cuaterniones por método de Hamilton"""
        q1 = left_quat[3] * right_quat[0] - left_quat[2] * right_quat[1] + left_quat[1] * right_quat[2] + left_quat[0] * right_quat[3]
        q2 = left_quat[2] * right_quat[0] + left_quat[3] * right_quat[1] - left_quat[0] * right_quat[2] + left_quat[1] * right_quat[3]
        q3 = -left_quat[1] * right_quat[0] + left_quat[0] * right_quat[1] + left_quat[3] * right_quat[2] + left_quat[2] * right_quat[3]
        q4 = -left_quat[0] * right_quat[0] - left_quat[1] * right_quat[1] - left_quat[2] * right_quat[2] + left_quat[3] * right_quat[3]
        return np.array([q1, q2, q3, q4])