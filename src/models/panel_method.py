# Author: Nicolas Sturm
#         Rocket Simulator - Panel Method Aerodynamics (Phase 1)

"""
Panel Method Aerodynamics Module

Alternative IAerodynamics implementation based on a surface panel method for
axisymmetric bodies of revolution, as an alternative to the Barrowman-based
Aerodynamics class in src/models/aerodynamics.py.

Method (axisymmetric panel/slender-body hybrid, robust for slender rockets):
    - The body (nosecone + fuselage + rear/boat-tail) is discretized into
      annular strips (panels) with control points on the surface; the
      freestream u is decomposed into an axial component and a crossflow
      component (angle of attack AND sideslip via the optional v_rel_body).
    - Axial flow: line of point sources on the body axis (classic source-line
      panel model for bodies of revolution), solved once at construction by
      enforcing no-penetration at the strip control points.
    - Crossflow: per-station 2D crossflow (doublet) field on each strip, which
      reproduces the 2D-cylinder pressure pattern Cp = 1 - 4 sin^2(theta)
      per section; the section normal force is the slender-body (Munk) term
      C_N = 2 sin(alpha) cos(alpha) S_base/S_ref with x_cp from the
      dS/dx distribution (exact for slender bodies: cone C_Nalpha = 2,
      x_cp = 2L/3). A full Hess-Smith surface-doublet solve is the accuracy
      upgrade path for blunt bodies (follow-up).
    - Cp(x, theta) on each panel from Bernoulli; used for the pressure map
      (GUI/thermodynamics) and, supersonically, for wave drag.
    - Regimes: subsonic M<0.8 Prandtl-Glauert scaling (Cp /= beta^2);
      transonic 0.8-1.2 incompressible solution + empirical drag rise (no
      panel method is valid there); supersonic M>1.2 linearized supersonic
      (Ackeret) Cp = -2 (u.n) / sqrt(M^2-1) on each panel, integrated for
      geometry-based wave drag and normal force.
    - Viscous drag (skin friction, Prandtl-Schlichting) and base drag remain
      empirical add-ons (potential flow does not capture them), reusing the
      same correlations as the Barrowman model. Fins use the Barrowman fin
      add-on with interference factor in this phase (flat fin panels are a
      follow-up).

The class is a drop-in IAerodynamics: same constructor shape and same
update(mach, angle_attack, height, density) contract as Aerodynamics, plus a
duck-typed optional v_rel_body keyword (full body-frame relative velocity, so
sideslip is not discarded) and extended duck-typed accessors
(get_force_moment_body, get_surface_pressure) used by RocketDynamics and the
GUI/thermodynamics when available.

References:
    [Hess-Smith] Hess & Smith, "Calculation of potential flow about arbitrary
                 bodies" - basis of panel methods.
    [Woodward]   Woodward, NASA CR-73106 / CR-2228 - supersonic panel method.
    [Barrowman]  Barrowman 1967 - slender finned vehicles (fin add-on).
    [Katz]       Katz & Plotkin, Low-Speed Aerodynamics - ring source/doublet.
"""

import logging
import math
from typing import Optional, Dict, Any, Tuple

import numpy as np

from src.models.interfaces import IAerodynamics
from src.models.aerodynamics import _calculate_dynamic_viscosity
from src.utils.simulation_constants import (
    AtmosphereConstants as AC,
    AerodynamicsConstants as ADC,
)
from src.utils.simulation_errors import InputValidationError

logger = logging.getLogger(__name__)

SEA_LEVEL_DENSITY = AC.SEA_LEVEL_DENSITY
SEA_LEVEL_TEMPERATURE = AC.SEA_LEVEL_TEMPERATURE
SPEED_OF_SOUND_SEA_LEVEL = ADC.SPEED_OF_SOUND_SEA_LEVEL
TURBULENT_SKIN_FRICTION_K = ADC.TURBULENT_SKIN_FRICTION_K

MAX_ANGLE_OF_ATTACK = 20.0  # [deg]
CROSSFLOW_DRAG_COEFF = 1.2  # viscous crossflow drag of a cylinder (Allen)


# =============================================================================
# Geometry: axisymmetric body mesh
# =============================================================================

def _nose_profile_fraction(shape: str, xi: float) -> float:
    """Nosecone radius fraction r/R at xi = x/L in [0, 1]."""
    s = (shape or 'conical').lower().replace(' ', '_').replace('-', '_')
    xi = min(max(xi, 0.0), 1.0)
    if s in ('conical', 'cone'):
        return xi
    if s in ('parabolic',):
        return 2.0 * xi - xi * xi
    if s in ('ellipsoidal', 'ellipsoid', 'elliptical'):
        return math.sqrt(max(0.0, 2.0 * xi - xi * xi))
    if s in ('ogive', 'ogival', 'von_karman', 'vonkarman', 'haack', 'ld_haack'):
        theta = math.acos(1.0 - 2.0 * xi)
        return math.sqrt(max(0.0, (theta - math.sin(theta) * math.cos(theta)) / math.pi))
    if s == 'power':
        return xi ** 0.5
    return xi  # conical fallback


class BodyOfRevolutionMesh:
    """
    Axisymmetric mesh of the rocket body (nose tip at x=0, +x toward tail).

    Attributes:
        x_c: strip center axial positions [m] (N,)
        r_c: strip center radii [m] (N,)
        nx, nr: meridian-plane outward normal components (N,)
        area: strip areas [m^2] (N,)
        az: azimuth quadrature angles [rad] (M,)
        L: total body length [m]
        R: max radius [m]
    """

    def __init__(self, rocket_data: Dict[str, Any], n_axial: int = 48, n_theta: int = 16):
        nose = rocket_data.get('nosecone', {}) or {}
        fuselage = rocket_data.get('fuselage', {}) or {}
        rear = rocket_data.get('rear_section', {}) or {}
        geometry = rocket_data.get('geometry', {}) or {}

        self.L_nose = float(nose.get('length', 0.1))
        self.R_fus = 0.5 * float(fuselage.get('diameter', nose.get('diameter', 0.1)))
        self.R_nose = 0.5 * float(nose.get('diameter', fuselage.get('diameter', 0.1)))
        self.shape = nose.get('shape', nose.get('type', 'conical'))
        self.L_fus = float(fuselage.get('length', 0.5))
        self.L_rear = float(rear.get('length', 0.0) or 0.0)
        self.R_rear = 0.5 * float(rear.get('diameter', fuselage.get('diameter', 2 * self.R_fus)))
        self.L = float(geometry.get('total_length',
                                     geometry.get('total length',
                                                  self.L_nose + self.L_fus + self.L_rear)))
        if self.L <= 0:
            self.L = self.L_nose + self.L_fus + self.L_rear
        self.R = max(self.R_fus, self.R_nose, self.R_rear, 1e-6)

        n_axial = max(int(n_axial), 8)
        n_theta = max(int(n_theta), 8)
        self.n_axial = n_axial
        self.n_theta = n_theta
        self.az = np.linspace(0.0, 2.0 * math.pi, n_theta, endpoint=False)

        # Cosine-spaced stations, denser near nose and tail
        i = np.arange(n_axial + 1)
        xi = 0.5 * (1.0 - np.cos(math.pi * i / n_axial))
        x_st = self.L * xi
        r_st = np.array([self._radius(x) for x in x_st])

        # Strip centers
        self.x_c = 0.5 * (x_st[:-1] + x_st[1:])
        self.r_c = 0.5 * (r_st[:-1] + r_st[1:])
        dx = x_st[1:] - x_st[:-1]
        dr = r_st[1:] - r_st[:-1]
        slant = np.hypot(dx, dr)
        self.area = 2.0 * math.pi * np.maximum(self.r_c, 1e-9) * slant

        # Meridian normals from profile slope (central differences)
        drdx = np.gradient(r_st, x_st)
        drdx_c = 0.5 * (drdx[:-1] + drdx[1:])
        norm = np.hypot(drdx_c, 1.0)
        self.nx = -drdx_c / norm
        self.nr = 1.0 / norm

        # Axis singularity stations (source line at strip centers)
        self.s_axis = self.x_c.copy()

        # Cross-sectional area change per strip (slender-body/Munk lift)
        s_st = math.pi * r_st ** 2
        self.dS = np.diff(s_st)               # (N,) area growth per strip
        self.S_base = float(s_st[-1])         # base cross-section [m^2]

        # 3D control points: P[i, k], normals n[i, k]
        ca = np.cos(self.az)
        sa = np.sin(self.az)
        self.P = np.stack([
            np.repeat(self.x_c, n_theta),
            (self.r_c[:, None] * ca[None, :]).ravel(),
            (self.r_c[:, None] * sa[None, :]).ravel(),
        ], axis=1).reshape(n_axial, n_theta, 3)
        self.N = np.stack([
            np.repeat(self.nx, n_theta),
            (self.nr[:, None] * ca[None, :]).ravel(),
            (self.nr[:, None] * sa[None, :]).ravel(),
        ], axis=1).reshape(n_axial, n_theta, 3)
        self.cell_area = (self.area / n_theta)[:, None]  # (N, 1) broadcast over azimuth

    def _radius(self, x: float) -> float:
        """Body radius at axial position x (nose tip at x=0)."""
        if x <= 0.0:
            return 0.0
        if x <= self.L_nose:
            return self.R_nose * _nose_profile_fraction(self.shape, x / max(self.L_nose, 1e-12))
        if x <= self.L_nose + self.L_fus:
            return self.R_fus
        if self.L_rear > 1e-9 and x <= self.L_nose + self.L_fus + self.L_rear:
            t = (x - self.L_nose - self.L_fus) / self.L_rear
            return self.R_fus + (self.R_rear - self.R_fus) * t
        return self.R_rear if self.L_rear > 1e-9 else self.R_fus

    @property
    def wetted_area(self) -> float:
        return float(np.sum(self.area))


# =============================================================================
# Singularity influence functions (unit freestream)
# =============================================================================

def _source_influence(P: np.ndarray, S: np.ndarray) -> np.ndarray:
    """Velocity induced at P by a unit point source at S: (P-S)/(4 pi |P-S|^3)."""
    r = P - S
    d = np.linalg.norm(r, axis=-1, keepdims=True)
    d = np.maximum(d, 1e-12)
    return r / (4.0 * math.pi * d ** 3)


# =============================================================================
# Panel method aerodynamics
# =============================================================================

class PanelMethodAerodynamics(IAerodynamics):
    """
    IAerodynamics implementation using a surface panel method (axisymmetric
    source/doublet line for the body + Barrowman fin add-on).

    Drop-in alternative to Aerodynamics: same update(mach, angle_attack,
    height, density) contract, plus optional duck-typed v_rel_body keyword with
    the full body-frame relative velocity (preserves sideslip) and extended
    accessors get_force_moment_body / get_surface_pressure.

    Attributes:
        accepts_v_rel_body: True - update() accepts v_rel_body keyword.
    """

    accepts_v_rel_body = True

    def __init__(
        self,
        mach: Optional[float] = None,
        angle_attack: Optional[float] = None,
        height: Optional[float] = None,
        atmosphere: Optional[Any] = None,
        rocket_data: Optional[Dict[str, Any]] = None,
        mass_props: Optional[Dict[str, Any]] = None,
        # Simple-mode coefficients (kept for interface compatibility)
        cd: Optional[float] = None,
        cl: Optional[float] = None,
        center_of_pressure_x: Optional[float] = None,
        stability_margin: Optional[float] = None,
        reference_area: Optional[float] = None,
        # Panel options
        n_axial: int = 48,
        n_theta: int = 16,
        include_fins: bool = True,
        viscous_crossflow: bool = True,
    ) -> None:
        if not rocket_data:
            raise InputValidationError(
                "PanelMethodAerodynamics requires rocket_data with geometry "
                "(nosecone, fuselage, rear_section, fins, reference_area)."
            )
        self.atmosphere = atmosphere
        self.rocket_data = rocket_data
        self.mass_props = mass_props or {}
        self.ref_area = float(rocket_data.get('reference_area', reference_area or 0.01))
        fuselage = rocket_data.get('fuselage', {}) or {}
        self.ref_diameter = float(fuselage.get('diameter', 0.1))
        self.include_fins = bool(include_fins)
        self.viscous_crossflow = bool(viscous_crossflow)

        # Build mesh and solve the two unit problems once
        self.mesh = BodyOfRevolutionMesh(rocket_data, n_axial=n_axial, n_theta=n_theta)
        self._solve_unit_problems()

        # State
        self.mach = float(mach or 0.0)
        self.alpha = float(angle_attack or 0.0)
        self.height = float(height or 0.0)
        if atmosphere is not None:
            self.rho = float(atmosphere.give_dens(self.height))
            self.temp = float(atmosphere.give_temp(self.height))
            self.speed_of_sound = float(atmosphere.give_v_sonic(self.height))
        else:
            self.rho = SEA_LEVEL_DENSITY
            self.temp = SEA_LEVEL_TEMPERATURE
            self.speed_of_sound = SPEED_OF_SOUND_SEA_LEVEL
        self.velocity = self.mach * self.speed_of_sound

        self._cache: Dict[tuple, Dict[str, Any]] = {}
        self._last: Optional[Dict[str, Any]] = None
        self._compute(self.mach, self.alpha)

    # ------------------------------------------------------------------
    # Unit solves (done once per geometry)
    # ------------------------------------------------------------------

    def _solve_unit_problems(self) -> None:
        """Solve the unit axial problem (source line on the body axis).

        The crossflow is treated analytically per strip (2D doublet field),
        which is exact for slender bodies of revolution; see module docstring.
        """
        m = self.mesh
        n = m.n_axial
        S = np.stack([m.s_axis, np.zeros(n), np.zeros(n)], axis=1)  # (N, 3)

        # Control points in the meridian plane phi=0: P=(x, r, 0), n=(nx, nr, 0)
        P0 = np.stack([m.x_c, m.r_c, np.zeros(n)], axis=1)
        N0 = np.stack([m.nx, m.nr, np.zeros(n)], axis=1)

        # No-penetration: sum_j q_j * v_source(P_i, S_j).n_i = -n_x
        A = np.empty((n, n))
        for j in range(n):
            A[:, j] = np.sum(_source_influence(P0, S[j]) * N0, axis=1)
        b = -N0[:, 0]
        self._q_source, *_ = np.linalg.lstsq(A, b, rcond=None)

        # Induced axial velocity field at all 3D control points (unit freestream)
        P = m.P.reshape(-1, 3)  # (N*M, 3)
        v_ax = np.zeros_like(P)
        for j in range(n):
            v_ax += self._q_source[j] * _source_influence(P, S[j])
        self._v_ax = v_ax.reshape(n, m.n_theta, 3)

    def _crossflow_velocity(self, u: np.ndarray) -> np.ndarray:
        """
        Induced crossflow velocity at all control points (unit freestream).

        Per-station 2D doublet (cylinder) field on the surface:
        v_ind = -(w.e_r) e_r + (w.e_phi) e_phi, with w = u_cf at azimuth phi_w,
        giving the surface pattern Cp = 1 - 4 sin^2(phi - phi_w) * u_cf^2.
        Returns array (N, M, 3).
        """
        m = self.mesh
        u_cf = math.hypot(u[1], u[2])
        if u_cf < 1e-12:
            return np.zeros((m.n_axial, m.n_theta, 3))
        phi_w = math.atan2(u[2], u[1])  # azimuth of crossflow direction
        az = m.az[None, :]              # (1, M)
        er = np.stack([np.zeros_like(az), np.cos(az), np.sin(az)], axis=-1)     # (1, M, 3)
        ephi = np.stack([np.zeros_like(az), -np.sin(az), np.cos(az)], axis=-1)  # (1, M, 3)
        wr = u_cf * np.cos(az - phi_w)    # w . e_r
        wp = -u_cf * np.sin(az - phi_w)   # w . e_phi
        v = -wr[:, :, None] * er + wp[:, :, None] * ephi  # (1, M, 3)
        return np.broadcast_to(v, (m.n_axial, m.n_theta, 3)).copy()

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _freestream_unit(self, alpha_deg: float, v_rel_body: Optional[np.ndarray]) -> np.ndarray:
        """Unit freestream direction in the body frame (x = rocket axis)."""
        if v_rel_body is not None:
            v = np.asarray(v_rel_body, dtype=float)
            n = np.linalg.norm(v)
            if n > 1e-12:
                return v / n
        a = math.radians(alpha_deg)
        return np.array([math.cos(a), 0.0, math.sin(a)])

    def _compute(self, mach: float, alpha_deg: float,
                 v_rel_body: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Compute coefficients for the given flight state (with caching)."""
        u = self._freestream_unit(alpha_deg, v_rel_body)
        key = (round(float(mach), 3),
               round(float(u[0]), 4), round(float(u[1]), 4), round(float(u[2]), 4))
        if key in self._cache:
            self._last = self._cache[key]
            return self._last

        m = self.mesh
        mach = float(mach)
        u_cf = math.hypot(u[1], u[2])           # sin of total incidence
        alpha_rad = math.asin(min(1.0, u_cf))

        # Pressure coefficient on each panel
        if mach > 1.2:
            beta_s = math.sqrt(mach * mach - 1.0)
            un = np.sum(m.N * u[None, None, :], axis=-1)  # (N, M)
            Cp = -2.0 * un / beta_s  # Ackeret (linearized supersonic)
        else:
            # Total velocity = freestream + induced axial (source line)
            # + induced crossflow (per-station 2D doublet field)
            V = u + u[0] * self._v_ax + self._crossflow_velocity(u)
            Cp = 1.0 - np.sum(V * V, axis=-1)
            if mach < 0.8:
                beta = math.sqrt(max(1e-6, 1.0 - mach * mach))
                Cp = Cp / (beta * beta)  # Prandtl-Glauert

        self._cp = Cp

        # Pressure force per unit dynamic pressure (mesh frame, x aft-positive)
        dA = m.cell_area  # (N, 1)
        F = -np.sum(Cp[:, :, None] * m.N * dA[:, :, None], axis=(0, 1)) / self.ref_area
        C_A = float(F[0])  # axial pressure (drag direction, +x aft)

        if mach > 1.2:
            # Supersonic: forces and CP from the Ackeret pressure integration
            C_Cy, C_Cz = float(F[1]), float(F[2])
            r_cross_n = np.cross(m.P, Cp[:, :, None] * m.N * dA[:, :, None])
            Mo = -np.sum(r_cross_n, axis=(0, 1)) / self.ref_area
            C_N_body = math.hypot(C_Cy, C_Cz)
            x_cp_body = float(-Mo[1] / C_Cz) if abs(C_Cz) > 1e-9 else 0.0
        else:
            # Subsonic/transonic: slender-body (Munk) body normal force,
            # C_N = 2 sin(alpha) cos(alpha) S_base/S_ref along the crossflow dir,
            # Prandtl-Glauert corrected for subsonic compressibility
            C_N_body = 2.0 * u_cf * abs(u[0]) * (m.S_base / self.ref_area)
            if mach < 0.8:
                beta = math.sqrt(max(1e-6, 1.0 - mach * mach))
                C_N_body /= beta
            if u_cf > 1e-12:
                C_Cy = C_N_body * u[1] / u_cf
                C_Cz = C_N_body * u[2] / u_cf
            else:
                C_Cy = C_Cz = 0.0
            # CP from the dS/dx (cross-section growth) distribution
            if m.S_base > 1e-12:
                x_cp_body = float(np.sum(m.x_c * m.dS) / m.S_base)
            else:
                x_cp_body = 0.5 * m.L

        # Fin add-on (Barrowman) and viscous crossflow (Allen); the viscous
        # crossflow follows the same dS/dx axial distribution as the body lift
        C_N_fins, x_cp_fins, cd_fins = self._fin_contribution(mach, alpha_rad)
        C_N_visc = 0.0
        if self.viscous_crossflow and mach < 1.2:
            s_plan = self.ref_diameter * m.L
            C_N_visc = CROSSFLOW_DRAG_COEFF * (s_plan / self.ref_area) * math.sin(alpha_rad) ** 2
            if u_cf > 1e-12:
                C_Cy += C_N_visc * u[1] / u_cf
                C_Cz += C_N_visc * u[2] / u_cf
        C_N_body_tot = C_N_body + C_N_visc
        C_N_tot = C_N_body_tot + C_N_fins
        if abs(C_N_tot) > 1e-9:
            x_cp = (C_N_body_tot * x_cp_body + C_N_fins * x_cp_fins) / C_N_tot
        else:
            x_cp = x_cp_body

        # Drag: pressure (panels) + skin friction + base + fins
        cd_pressure = C_A
        cd_friction = self._skin_friction_cd(mach)
        cd_base = self._base_drag_cd(mach)
        cd = cd_pressure + cd_friction + cd_base + cd_fins
        if 0.8 <= mach <= 1.2:
            cd *= 1.0 + 0.5 * ((mach - 0.8) / 0.4) ** 2  # transonic drag rise

        # Scalar-interface semantics: cl = C_N * cos(alpha), drag magnitude cd
        cl = C_N_tot * u[0] if abs(u[0]) > 0 else 0.0

        result = {
            'cd': float(cd),
            'cl': float(cl),
            'c_ax': C_A,
            'c_cy': C_Cy,
            'c_cz': C_Cz,
            'c_n': C_N_tot,
            'x_cp': float(x_cp),
            'u': u,
            'mach': mach,
            'alpha': alpha_deg,
        }
        self._cache[key] = result
        self._last = result
        return result

    def _fin_contribution(self, mach: float, alpha_rad: float) -> Tuple[float, float, float]:
        """Barrowman fin normal force, CP and form/interference drag."""
        if not self.include_fins:
            return 0.0, 0.0, 0.0
        g = self.rocket_data
        fins = g.get('fins', {}) or {}
        s = float(fins.get('span', 0.0))
        d = self.ref_diameter
        cr = float(fins.get('chord_root', 0.0))
        ct = float(fins.get('chord_tip', 0.0))
        n = float(fins.get('N_fins', 0))
        if s <= 0 or d <= 0 or cr + ct <= 0 or n <= 0:
            return 0.0, 0.0, 0.0
        K_fin = 1.0 + d / (2.0 * s)
        AR = (2.0 * s) / (cr + ct)
        Cn_alpha_fins = (K_fin * 4.0 * n * (s / d) ** 2) / (1.0 + math.sqrt(1.0 + (2.0 * AR) ** 2))
        C_N_fins = Cn_alpha_fins * alpha_rad
        if mach < 0.8:
            C_N_fins /= max(0.3, math.sqrt(1.0 - mach * mach))
        elif mach > 1.2:
            C_N_fins /= math.sqrt(mach * mach - 1.0)

        nose_length = float((g.get('nosecone', {}) or {}).get('length', 0.1))
        fin_position = float((g.get('geometry', {}) or {}).get(
            'length_nosecone_fins', nose_length + 0.1))
        mid_chord = float(fins.get('mid_chord', 0.5 * (cr + ct)))
        if mid_chord > 0 and (cr + ct) > 0:
            x_fin_cp = (mid_chord / 3.0) * ((cr + 2.0 * ct) / (cr + ct))
        else:
            x_fin_cp = 0.6 * cr
        x_cp_fins = fin_position + x_fin_cp

        # Fin form + interference drag (same correlations as Barrowman model)
        thickness = 0.003
        chord_avg = 0.5 * (cr + ct)
        planform = 0.5 * (cr + ct) * s * n
        cd_form = 2.0 * (thickness / max(chord_avg, 1e-6)) * (planform / self.ref_area)
        cd_int = 0.1 * 0.05 * (planform / self.ref_area) * n
        return C_N_fins, x_cp_fins, cd_form + cd_int

    def _skin_friction_cd(self, mach: float) -> float:
        """Turbulent skin friction drag (Prandtl-Schlichting), as in Barrowman model."""
        m = self.mesh
        mu = _calculate_dynamic_viscosity(self.temp)
        V = mach * self.speed_of_sound
        Re_L = (self.rho * V * m.L) / mu if V > 0 else 0.0
        Cf = TURBULENT_SKIN_FRICTION_K / (Re_L ** 0.2) if Re_L > 0 else 0.0
        A_wet = m.wetted_area
        if self.include_fins:
            fins = self.rocket_data.get('fins', {}) or {}
            s = float(fins.get('span', 0.0))
            cr = float(fins.get('chord_root', 0.0))
            ct = float(fins.get('chord_tip', 0.0))
            n = float(fins.get('N_fins', 0))
            A_wet += 2.0 * 0.5 * (cr + ct) * s * n
        roughness = 1.1
        compressibility = 1.0 / (1.0 + 0.12 * mach ** 2) if mach > 0.6 else 1.0
        return Cf * roughness * compressibility * (A_wet / self.ref_area)

    def _base_drag_cd(self, mach: float) -> float:
        """Base drag, same correlation as the Barrowman model."""
        rear = self.rocket_data.get('rear_section', {}) or {}
        base_diameter = float(rear.get('diameter', self.ref_diameter))
        base_area = math.pi * (base_diameter / 2.0) ** 2
        if mach < 0.8:
            cd_base = 0.12 + 0.13 * mach ** 2
        else:
            cd_base = 0.25 / (1.0 + 0.5 * (mach - 0.8))
        return cd_base * (base_area / self.ref_area)

    # ------------------------------------------------------------------
    # IAerodynamics interface
    # ------------------------------------------------------------------

    def update(self, mach: float, angle_attack: float, height: float,
               density: float, v_rel_body: Optional[np.ndarray] = None) -> None:
        """Update coefficients for the current flight state.

        v_rel_body (optional, duck-typed): full air-relative velocity in the
        body frame; when given it defines both angle of attack and sideslip.
        """
        self.mach = float(mach)
        self.alpha = float(angle_attack)
        self.height = float(height)
        self.rho = float(density)
        if getattr(self, 'atmosphere', None) is not None:
            self.temp = float(self.atmosphere.give_temp(height))
            self.speed_of_sound = float(self.atmosphere.give_v_sonic(height))
        self.velocity = self.mach * self.speed_of_sound
        self._compute(self.mach, self.alpha, v_rel_body=v_rel_body)

    def get_coefficients(self) -> Tuple[float, float]:
        r = self._last or self._compute(self.mach, self.alpha)
        return float(r['cd']), float(r['cl'])

    def get_center_of_pressure(self) -> np.ndarray:
        r = self._last or self._compute(self.mach, self.alpha)
        return np.array([r['x_cp'], 0.0, 0.0])

    def get_stability_margin(self) -> float:
        r = self._last or self._compute(self.mach, self.alpha)
        com_before = self.mass_props.get('CoM_before_burn', {}) or {}
        com_after = self.mass_props.get('CoM_after_burn', {}) or {}
        x_cg = 0.5 * (float(com_before.get('x', 0.0)) + float(com_after.get('x', 0.0)))
        if self.ref_diameter > 0:
            return float((r['x_cp'] - x_cg) / self.ref_diameter)
        return 0.0

    def get_aerodynamic_forces(self, dynamic_pressure: float,
                               reference_area: Optional[float] = None) -> dict:
        r = self._last or self._compute(self.mach, self.alpha)
        S = reference_area if reference_area is not None else self.ref_area
        return {
            'drag': float(r['cd'] * dynamic_pressure * S),
            'lift': float(r['cl'] * dynamic_pressure * S),
            'cd': float(r['cd']),
            'cl': float(r['cl']),
            'cp_position': self.get_center_of_pressure(),
            'stability_margin': self.get_stability_margin(),
        }

    # ------------------------------------------------------------------
    # Extended (duck-typed) API used by RocketDynamics / GUI / thermodynamics
    # ------------------------------------------------------------------

    def get_force_moment_body(self, dynamic_pressure: float,
                              reference_area: float,
                              cm_b: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Full aerodynamic force [N] and moment [N.m] about cm_b in body frame.

        Force semantics match the scalar path used by RocketDynamics: axial
        (drag) along -X body, normal force in the crossflow (Y-Z) plane.
        """
        r = self._last or self._compute(self.mach, self.alpha)
        S = reference_area
        qS = dynamic_pressure * S
        F_b = np.array([-r['c_ax'] * qS, r['c_cy'] * qS, r['c_cz'] * qS])
        # Friction + base act axially (drag direction)
        cd_visc = r['cd'] - r['c_ax']
        F_b[0] -= cd_visc * qS
        cp_b = np.array([r['x_cp'], 0.0, 0.0])
        M_b = np.cross(np.asarray(cm_b, dtype=float) - cp_b, F_b)
        return F_b, M_b

    def get_surface_pressure(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Current panel pressure coefficients: (x_strips, azimuth, Cp[N, M])."""
        if not hasattr(self, '_cp'):
            self._compute(self.mach, self.alpha)
        return self.mesh.x_c.copy(), self.mesh.az.copy(), self._cp.copy()

    def get_method_name(self) -> str:
        return 'panel'

    # ------------------------------------------------------------------
    # Backward-compatibility properties (mirror Aerodynamics)
    # ------------------------------------------------------------------

    @property
    def cd(self) -> float:
        return self.get_coefficients()[0]

    @property
    def cl(self) -> float:
        return self.get_coefficients()[1]

    @property
    def xcp(self) -> np.ndarray:
        return self.get_center_of_pressure()

    def set_coefficients(self, cd: float, cl: float) -> None:
        """Override coefficients (simple mode); clears cache entry effect."""
        self._last = dict(self._last or self._compute(self.mach, self.alpha))
        self._last['cd'] = float(cd)
        self._last['cl'] = float(cl)

    def set_stability_margin(self, stability_margin: float) -> None:
        self._stability_margin_override = float(stability_margin)

    def set_reference_area(self, reference_area: float) -> None:
        self.ref_area = float(reference_area)

    def set_center_of_pressure(self, x: float, y: float = 0.0, z: float = 0.0) -> None:
        if self._last is not None:
            self._last['x_cp'] = float(x)


__all__ = [
    'PanelMethodAerodynamics',
    'BodyOfRevolutionMesh',
    'CROSSFLOW_DRAG_COEFF',
]
