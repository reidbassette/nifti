from __future__ import annotations

from dataclasses import dataclass
import math as m


@dataclass
class FilmInputs:
    """Film-side properties (bulk temps are cross-section averages)."""
    T_bulk: float             # [K] average bulk temp on a side
    h: float                  # [W/m^2/K] film coefficient
    Rf: float = 0.0           # [m^2 K/W] fouling (optional)


@dataclass
class WallInputs:
    """Solid wall properties."""
    k: float                  # [W/m/K] wall conductivity
    t: float                  # [m]      wall thickness
    rho: float | None = None  # [kg/m^3] (optional, for transient)
    cp: float | None = None   # [J/kg/K] (optional, for transient)


def U_composite(h_hot: float, h_cold: float, k_wall: float, t_wall: float,
                Rf_hot: float = 0.0, Rf_cold: float = 0.0) -> float:
    """
    U = 1 / (1/h_hot + Rf_hot + t/k + Rf_cold + 1/h_cold)
    """
    R_hot = 1.0 / max(h_hot, 1e-12) + float(Rf_hot or 0.0)
    R_cold = 1.0 / max(h_cold, 1e-12) + float(Rf_cold or 0.0)
    R_wall = float(t_wall) / max(k_wall, 1e-12)
    R_tot = R_hot + R_wall + R_cold
    return 1.0 / max(R_tot, 1e-18)


def UA_from_q_LMTD(q: float, LMTD: float, F_corr: float = 1.0) -> float:
    """UA needed to deliver heat rate q at given (corrected) LMTD."""
    return q / max(F_corr * max(LMTD, 1e-12), 1e-18)


def t_required_for_U(U_target: float, h_hot: float, h_cold: float, k_wall: float,
                     Rf_hot: float = 0.0, Rf_cold: float = 0.0) -> float:
    """
    Solve wall thickness needed to achieve U_target with known films:
      1/U = 1/h_hot + Rf_hot + t/k + Rf_cold + 1/h_cold  →  t = (1/U - 1/h_hot - Rf_hot - 1/h_cold - Rf_cold) * k
    Returns max(0, t).
    """
    invU = 1.0 / max(U_target, 1e-18)
    t = (invU - 1.0 / max(h_hot, 1e-18) - float(Rf_hot or 0.0)
         - 1.0 / max(h_cold, 1e-18) - float(Rf_cold or 0.0)) * float(k_wall)
    return max(0.0, t)


def wall_faces_from_qA(h_hot: float, h_cold: float, q: float, A: float,
                       T_bulk_hot: float, T_bulk_cold: float) -> tuple[float, float]:
    """
    Lumped (cross-averaged) wall face temperatures, using film balances:
      q/A = h_hot*(T_h,bulk - T_wall,hot) = h_cold*(T_wall,cold - T_c,bulk)
    → T_wall,hot  = T_h,bulk  - q/(A*h_hot)
      T_wall,cold = T_c,bulk  + q/(A*h_cold)
    """
    qA = q / max(A, 1e-18)
    Tw_hot = T_bulk_hot - qA / max(h_hot, 1e-12)
    Tw_cold = T_bulk_cold + qA / max(h_cold, 1e-12)
    return float(Tw_hot), float(Tw_cold)


def t_required_from_wall_face_gap(h_hot: float, h_cold: float, k_wall: float,
                                  q: float, A: float,
                                  T_bulk_hot: float, T_bulk_cold: float) -> float:
    """
    Using film-based wall faces and conduction consistency:
      Twh = Th - q/(A h_hot) ; Twc = Tc + q/(A h_cold)
      conduction requires Tw_hot - Tw_cold = (q/A) * (t/k)
    → t_required = k * (Tw_hot - Tw_cold) / (q/A)
    """
    Thw, Tcw = wall_faces_from_qA(h_hot, h_cold, q, A, T_bulk_hot, T_bulk_cold)
    qA = q / max(A, 1e-18)
    return float(k_wall) * (Thw - Tcw) / max(qA, 1e-18)


def area_required_from_wall_limit(h_hot: float, h_cold: float, q: float,
                                  T_bulk_hot: float, T_bulk_cold: float,
                                  Tw_hot_max: float | None = None,
                                  Tw_cold_max: float | None = None) -> float | None:
    """
    Solve minimum area A so that film-based wall faces respect limits:
      Twh = Th - q/(A h_hot)   (≤ Tw_hot_max)
      Twc = Tc + q/(A h_cold)  (≤ Tw_cold_max)
    Returns the governing A (None if no limit supplied).
    """
    A_req = 0.0
    if Tw_hot_max is not None:
        # Th - q/(A h) ≤ Tw_hot_max → A ≥ q/(h*(Th - Tw_hot_max)) if (Th > Tw_hot_max)
        denom = max(h_hot * max(T_bulk_hot - Tw_hot_max, 0.0), 0.0)
        if denom > 0.0:
            A_req = max(A_req, q / denom)
    if Tw_cold_max is not None:
        # Tc + q/(A h) ≤ Tw_cold_max → A ≥ q/(h*(Tw_cold_max - Tc)) if (Tw_cold_max > Tc)
        denom = max(h_cold * max(Tw_cold_max - T_bulk_cold, 0.0), 0.0)
        if denom > 0.0:
            A_req = max(A_req, q / denom)
    return A_req if A_req > 0.0 else None


def wall_time_constant(wall: WallInputs, A: float, h_hot: float, h_cold: float) -> float | None:
    """
    Lumped wall transient (ignoring through-thickness gradients):
      τ ≈ (ρ c V_wall) / (A (h_hot + h_cold))
      with V_wall = A * t
    """
    if wall.rho is None or wall.cp is None or A is None or wall.t is None:
        return None
    C = wall.rho * wall.cp * (A * wall.t)          # [J/K]
    G = A * (max(h_hot, 0.0) + max(h_cold, 0.0))   # [W/K]
    return C / max(G, 1e-18)


def time_to_fraction(tau: float, fraction: float = 0.95) -> float:
    """
    First-order step response: y(t) = 1 - exp(-t/τ)
    Solve t for y = fraction → t = -τ ln(1 - fraction)
    """
    frac = min(max(fraction, 1e-9), 0.999999999)
    return -tau * m.log(1.0 - frac)