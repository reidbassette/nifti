# hx_solver.py
# A declarative, recipe-driven heat exchanger solver with wall/film coupling.
# --------------------------------------------------------------------------- #
# Highlights
# - @recipe decorator registers "how to solve X given Y" options in one place.
# - Dependency graph, units, and tooltip formulas are auto-built from recipes.
# - Maintains UI contract (HeatExchanger API, attribute names, tooltips).
# - Integrates steady + transient wall physics via hx_thermal_models.py.
# - Optional LaTeX→image math rendering for tooltips (fallback to plaintext).
# --------------------------------------------------------------------------- #

from __future__ import annotations
from functools import lru_cache
from typing import Any, Callable
import math as m
import base64
import io
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Tuple, Optional

# --- Optional LaTeX (mathtext) rendering for tooltips ---------------------- #
try:
    import matplotlib
    matplotlib.use("Agg")  # offscreen backend
    import matplotlib.pyplot as plt
    _HAS_MATPLOTLIB = True
except Exception:
    _HAS_MATPLOTLIB = False

# --- Project imports ------------------------------------------------------- #
from utilities import getfluidproperty, unit_convert, atm2Pa, LMTD
from mat_lib import Material, SS316
from hx_thermal_models import (
    FilmInputs, WallInputs,
    U_composite, UA_from_q_LMTD, t_required_for_U,
    wall_faces_from_qA, t_required_from_wall_face_gap,
    area_required_from_wall_limit, wall_time_constant, time_to_fraction
)

# =============================================================================
# Infrastructure: a lightweight recipe registry
# =============================================================================

# AFTER


@dataclass(frozen=True)

class Recipe:
    """A single recipe: how to compute an attribute from a set of dependencies."""
    attribute: str                 # e.g., "_UA"
    unit: str                      # e.g., "W/K"
    deps: Tuple[str, ...]          # e.g., ("_q", "_lmtd")
    formula: Optional[str] = None  # LaTeX-ish (mathtext) for display
    func: Callable[..., Any] = field(repr=False, default=None)  # callable(self)->value
    desc: Optional[str] = None     # human description for tooltips/docs

class RecipeRegistry:
    """Holds all recipes declared via @recipe."""
    def __init__(self):
        self._by_attr: Dict[str, List[Recipe]] = {}

    def register(self, r: Recipe):
        self._by_attr.setdefault(r.attribute, []).append(r)

    def for_attr(self, attr: str) -> List[Recipe]:
        return self._by_attr.get(attr, [])

    def all(self) -> Dict[str, List[Recipe]]:
        return self._by_attr
REGISTRY = RecipeRegistry()

# AFTER

def recipe(attribute: str, unit: str, deps: List[str],
           formula: Optional[str] = None, desc: Optional[str] = None):
    """
    Decorator to register a recipe method on HeatExchanger.
    Usage:
      @recipe("_UA", "W/K", ["_q","_lmtd"],
              r"UA=\frac{q}{F\,\mathrm{LMTD}}",
              desc="Overall conductance from duty and LMTD.")
      def _solve_UA_from_q_lmtd(self): ...
    """
    def decorator(func: Callable):
        REGISTRY.register(Recipe(attribute, unit, tuple(deps), formula, func, desc))
        return func
    return decorator



# =============================================================================
# HeatExchanger core
# =============================================================================

class HeatExchanger:
    """
    Heat Exchanger model (refactored to a recipe-driven engine).

    Public API (unchanged for UI):
      - constructor HeatExchanger(HX_Type="plate"|... , Counter_Flow=True|False, ...)
      - solve_hx(quiet: bool=False) -> (known_attrs, unknown_attrs)
      - dependency_tooltip(attribute, known_attributes=None, ui_friendly_names=None) -> HTML
      - pretty_print()
      - All same attribute names (e.g., _Thi, _UA, _H_inlet_velocity, ...)
    """

    HR_SECS = 3600
    PI = 3.141592653589793

    # ----------------------------- construction --------------------------- #
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
        Plate_Thickness=0.6,    # [mm]
        Plate_Count=None,
        Plate_Distribution_Bias="hot",
        mean_channel_gap=None,  # [mm]
        enlargement_factor_phi=None,  # [-]
        Total_Hot_Channel_Volume=None,
        Total_Cold_Channel_Volume=None,
        Per_Channel_Volume=None,
        Hot_Passes=1,
        # Target velocities
        H_Target_Velocity=None,
        C_Target_Velocity=None,
        # Wall constraints & transient
        T_wall_hot_max=None,    # [K]
        T_wall_cold_max=None,   # [K]
        Plate_rho=None,         # [kg/m^3]
        Plate_cp=None,          # [J/kg/K]
    ):
        # Identity
        self._Name = Name

        # --- Streams: Hot ---
        self._Thi = H_Inlet_Temp
        self._H_inlet_ID = H_Inlet_ID
        self._Tho = H_Outlet_Temp
        self._H_outlet_ID = H_Outlet_ID
        self._Pres_H_in = H_Inlet_Pres
        self._Pres_H_out = H_Outlet_Pres
        self._mdot_h = H_In_Mass_Flow
        self._H_in_nm3_hr = H_In_Vol_Flow_nm3
        self._H_Fluid = H_Fluid

        # --- Streams: Cold ---
        self._Tci = C_Inlet_Temp
        self._C_inlet_ID = C_Inlet_ID
        self._Tco = C_Outlet_Temp
        self._C_outlet_ID = C_Outlet_ID
        self._Pres_C_in = C_Inlet_Pres
        self._Pres_C_out = C_Outlet_Pres
        self._mdot_c = C_In_Mass_Flow
        self._C_in_nm3_hr = C_In_Vol_Flow_nm3
        self._C_Fluid = C_Fluid
        # Flow / type
        self._Type = HX_Type
        self._Flow_Direction = Counter_Flow
        self._HX_is_plate = True if str(self._Type).lower() == "plate" else None
        self._HX_is_st = True if str(self._Type).lower() == "shell & tube" else None
        self._HX_is_ache = True if str(self._Type).lower() == "air-cooled" else None

        # Heat/UA/NTU
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

        # Plate geometry/material
        self._Plate_count = Plate_Count
        self._Plate_Distribution_Bias = Plate_Distribution_Bias
        self._mean_channel_gap = mean_channel_gap
        self._enlargement_phi = enlargement_factor_phi
        self._Total_Hot_Ch_Vol = Total_Hot_Channel_Volume
        self._Total_Cold_Ch_Vol = Total_Cold_Channel_Volume
        self._Per_Ch_Vol = Per_Channel_Volume
        self._Hot_Passes = Hot_Passes
        self._plate_material = Plate_Material
        self._plate_material_name = None
        self._plate_thickness = Plate_Thickness  # [mm]

        # Target velocities
        self._H_target_velocity = H_Target_Velocity
        self._C_target_velocity = C_Target_Velocity

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

        # Plate thermo-hydraulics
        self._Lv = None
        self._Lh = None
        self._Dp = None
        self._pitch = None
        self._t_m = None
        self._fouling_hot = 0.0
        self._fouling_cold = 0.0
        self._Lp = None
        self._Lw = None
        self._Aproj = None
        self._Dh = None
        self._Aff_hot = None
        self._Aff_cold = None
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
        self._h_h = None
        self._h_c = None
        self._U_calc = None
        self._dP_h = None
        self._dP_c = None
        self._dP_total = None
        self._epsilon_NTU = None
        self._Tho_eps = None
        self._Tco_eps = None
        self._S_gen = None
        self._Ns = None

        # Shell & Tube
        self._ST_hot_in_tube = None
        self._ST_N_tubes = None
        self._ST_N_tube_passes = None
        self._ST_N_shell_passes = None
        self._ST_Di = None
        self._ST_Do = None
        self._ST_L_pass = None
        self._ST_k_wall = None
        self._ST_Rf_i = 0.0
        self._ST_Rf_o = 0.0
        self._ST_h_o = None
        self._ST_L_total = None
        self._ST_N_tubes_per_pass = None
        self._ST_Ai = None
        self._ST_Ao = None
        self._ST_Re_tube = None
        self._ST_Nu_tube = None
        self._ST_h_i = None
        self._ST_U = None
        self._ST_UA = None

        # Air-cooled / Compact
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

        # Wall coupling & constraints / transient
        self._U_from_material = None
        self._Tw_hot_avg = None
        self._Tw_cold_avg = None
        self._t_required_UA = None
        self._t_required_consistency = None
        self._A_required_wall_limit = None
        self._T_wall_hot_max = T_wall_hot_max
        self._T_wall_cold_max = T_wall_cold_max
        self._plate_rho = Plate_rho
        self._plate_cp = Plate_cp
        self._tau_wall = None
        self._t95_wall = None

        # track provided vs evaluated
        self._initial_values = [k for k, v in self.__dict__.items() if v is not None]

        # Build dependency index & formula map from recipes
        self._dependencies: Dict[str, List] = self._build_dependency_index_from_registry()
        self._formulae: Dict[str, Dict[Tuple[str, ...], str]] = self._build_formula_index_from_registry()


        # in __init__ (near where you build dependencies/formulae)
        self._reverse_deps = self._build_reverse_dependency_index_from_registry()

        # math rendering mode: "unicode" (default), "png", or "text"
        self._math_mode = "unicode"
        self._render_math_images = (self._math_mode == "png")

    # ---------------------------- fluid helpers --------------------------- #
    def _get_mu(self, fluid, T, P):
        for sym in ("VISCOSITY", "ETA"):
            try:
                return getfluidproperty(fluid, sym, "T", T, "P", P)
            except Exception:
                pass
        return None

    def _get_k(self, fluid, T, P):
        try:
            return getfluidproperty(fluid, "TCX", "T", T, "P", P)
        except Exception:
            return None
    def _get_cp(self, fluid, T, P):
        return getfluidproperty(fluid, "CP", "T", T, "P", P)

    def _get_pr(self, fluid, T, P):
        try:
            return getfluidproperty(fluid, "PRANDTL", "T", T, "P", P)
        except Exception:
            try:
                cp = self._get_cp(fluid, T, P)
                mu = self._get_mu(fluid, T, P)
                k = self._get_k(fluid, T, P)
                if cp and mu and k:
                    return (cp * mu) / k
            except Exception:
                pass
        return None

    # -------------------- registry → dependency index --------------------- #
    def _build_dependency_index_from_registry(self) -> Dict[str, List]:
        idx: Dict[str, List] = {}
        for attr, recipes in REGISTRY.all().items():
            unit = recipes[0].unit if recipes else ""
            idx[attr] = [[unit]] + [list(r.deps) for r in recipes]
        return idx

    def _build_formula_index_from_registry(self) -> Dict[str, Dict[Tuple[str, ...], str]]:
        fm = {}
        for attr, recipes in REGISTRY.all().items():
            for r in recipes:
                if r.formula:
                    fm.setdefault(attr, {})[tuple(r.deps)] = r.formula
        return fm

    # ---------------------------- tooltip API ----------------------------- #

    def _build_reverse_dependency_index_from_registry(self) -> Dict[str, List[str]]:
        """
        Map each attribute -> list of attributes that directly depend on it
        (first-order dependents).
        """
        rev: Dict[str, List[str]] = {}
        for attr, recipes in REGISTRY.all().items():
            for r in recipes:
                for dep in r.deps:
                    rev.setdefault(dep, [])
                    if attr not in rev[dep]:
                        rev[dep].append(attr)
        return rev
    def first_order_dependents(self, attribute: str) -> List[str]:
        """Return attributes that directly reference `attribute` in at least one recipe."""
        return sorted(self._reverse_deps.get(attribute, []))


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
    
    def _latex_to_unicode(self, s: str) -> str:
        """
        Convert a small, practical subset of LaTeX/mathtext to Unicode for tooltip display.
        This keeps tooltips readable without HTML images.
        """
        if not s:
            return s
        rep = {
            r"\cdot": "·",
            r"\times": "×",
            r"\pm": "±",
            r"\approx": "≈",
            r"\sim": "∼",
            r"\propto": "∝",
            r"\infty": "∞",
            r"\le": "≤",
            r"\ge": "≥",
            r"\neq": "≠",
            r"\equiv": "≡",
            r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
            r"\Delta": "Δ", r"\delta": "δ",
            r"\pi": "π", r"\mu": "μ", r"\rho": "ρ",
            r"\eta": "η", r"\lambda": "λ", r"\phi": "φ",
            r"\mathrm{LMTD}": "LMTD",
            r"\mathrm{NTU}": "NTU",
            r"\min": "min", r"\max": "max",
            r"\ln": "ln",
            r"\frac": "/",  # crude fallback
            r"\overline{T}_h": "T̄h", r"\overline{T}_c": "T̄c",
        }
        out = s
        for k, v in rep.items():
            out = out.replace(k, v)
        # Small superscripts/subscripts for simple cases like ^2, ^3
        out = out.replace("^2", "²").replace("^3", "³")
        # Remove common TeX braces that hurt readability
        out = out.replace("{", "").replace("}", "")
        # Compact: \, and \! spacing
        out = out.replace(r"\,", " ").replace(r"\!", "")
        return out

# --- at top of hx_solver.py (imports) ---


# ...



        


    def _render_formula_to_img_tag(self, formula_mathtext: str) -> Optional[str]:
        if not self._render_math_images or not _HAS_MATPLOTLIB:
            return None

        @lru_cache(maxsize=256)
        def _render_cached(formula: str) -> Optional[str]:
            fig = None
            try:
                fig = plt.figure(figsize=(0.01, 0.01), dpi=300)
                fig.patch.set_alpha(0.0)
                ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
                ax.text(0.0, 0.5, f"${formula}$", fontsize=8, ha="left", va="center")
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=300, transparent=True)
                data = base64.b64encode(buf.getvalue()).decode("ascii")
                # single-line exact string:
                return f'<img src="data;base64,{data}'
            except Exception:
                return None
            finally:
                try: plt.close(fig)
                except Exception: pass

        return _render_cached(formula_mathtext)


    def dependency_tooltip(self, attribute, known_attributes=None, ui_friendly_names=None):
        """
        Build an HTML tooltip with:
        - Title + unit
        - Description (from any recipe that has one)
        - 'Solved by' sections: each recipe option with [met]/[unmet] and an equation
        - 'Used by' first-order dependents
        """
        # Guard: attribute must exist in dependency index
        if attribute not in self._dependencies:
            return ("<html><body><div style='color:#ffffff'>"
                    f"<b>No dependencies for <code>{attribute}</code></b>"
                    "</div></body></html>")

        # Unit
        try:
            unit = self._dependencies[attribute][0][0] or ""
        except Exception:
            unit = ""

        # Gather description (take the first non-empty desc from any recipe)
        desc_text = ""
        for r in REGISTRY.for_attr(attribute):
            if r.desc:
                desc_text = r.desc
                break

        # Known/missing dependencies per option
        status_list = self.dependency_status(attribute, known_attributes=known_attributes)
        title_name = self._humanize_attr(attribute, ui_friendly_names)
        unit_str = f" <span style='color:#cccccc'>(unit: {unit})</span>" if unit else ""

        # Begin HTML (force rich text)
        html = [f"<html><body><div style='color:#ffffff; font-size: 11px;'>"
                f"<b>{title_name}</b>{unit_str}"]

        # Description
        if desc_text:
            html.append(f"<div style='margin-top:4px; color:#CDE6FF;'>{desc_text}</div>")

        # 'Solved by' section
        html.append("<div style='margin-top:6px;'><b>Solved by</b></div>")
        html.append("<ul style='margin-left:0.9em; padding-left:1.0em;'>")
        if not status_list:
            html.append("<li>No dependency options listed</li>")
        else:
            for st in status_list:
                # dependency chips
                chips = []
                for dep in st["option"]:
                    met = dep not in st["missing"]
                    tag = "<span style='color:#8FBC8F'>[met]</span>" if met else "<span style='color:#FFA07A'>[unmet]</span>"
                    chips.append(f"{tag} <code>{self._humanize_attr(dep, ui_friendly_names)}</code>")
                # equation (render according to mode)
                formula = self._formulae.get(attribute, {}).get(tuple(st["option"]), None)

                if self._math_mode == "png" and formula:
                    img = self._render_formula_to_img_tag(formula)
                    eq_html = f"<div style='margin-top:2px'>{img}</div>" if img else ""
                elif self._math_mode == "unicode" and formula:
                    eq = self._latex_to_unicode(formula)
                    eq_html = (f"<div style='margin-top:2px; color:#B0E0E6;'>"
                            f"<span style='white-space:pre; font-family:Segoe UI, DejaVu Sans, Arial Unicode MS, monospace;'>{eq}</span>"
                            f"</div>")
                elif self._math_mode == "text" and formula:
                    eq_html = (f"<div style='margin-top:2px; color:#B0E0E6;'>"
                            f"<span style='font-family:monospace; white-space:pre;'>{formula}</span>"
                            f"</div>")
                else:
                    eq_html = ""

                html.append(f"<li><div>{', '.join(chips)}</div>{eq_html}</li>")
        html.append("</ul>")

        # 'Used by' section (first-order dependents)
        used_by = self.first_order_dependents(attribute)
        html.append("<div style='margin-top:6px;'><b>Used by</b></div>")
        if not used_by:
            html.append("<div style='color:#cccccc'>No direct dependents.</div>")
        else:
            html.append("<ul style='margin-left:0.9em; padding-left:1.0em;'>")
            for dep in used_by:
                dep_unit = self._dependencies.get(dep, [[""]])[0][0] if dep in self._dependencies else ""
                dep_name = self._humanize_attr(dep, ui_friendly_names)
                dep_unit_str = f" <span style='color:#888'>(unit: {dep_unit})</span>" if dep_unit else ""
                html.append(f"<li><code>{dep_name}</code>{dep_unit_str}</li>")
            html.append("</ul>")

        html.append("</div></body></html>")
        return "".join(html)


    # --------------------------- solver engine ---------------------------- #
    def solve_hx(self, quiet: bool = False):
        """
        Iterate through attributes and solve when a recipe's dependencies are met.
        """
        known = {k for k, v in self.__dict__.items() if v is not None}
        unknown = [k for k, v in self.__dict__.items() if v is None and k.startswith("_")]
        solved_in_pass: List[str] = []
        step = 0
        while True:
            progressed = False
            for attr in list(unknown):
                # try all recipes for attr
                for r in REGISTRY.for_attr(attr):
                    if set(r.deps).issubset(known):
                        # call bound method
                        if not quiet:
                            print("solving", attr, "using", list(r.deps))
                        value = r.func(self)

                        if value is not None:
                            setattr(self, attr, value)
                            known.add(attr)
                            unknown.remove(attr)
                            solved_in_pass.append(attr)
                            progressed = True
                            break
                # end for recipes
            # end for attr
            if not progressed:
                if not quiet:
                    print("Iteration complete; solved attributes:", solved_in_pass)
                break
            step += 1

        self.known_attributes = sorted(list(known))
        self.unknown_attributes = sorted([k for k in unknown])
        return self.known_attributes, self.unknown_attributes

    def pretty_print(self):
        spacing = 26
        digits = 6
        skip = {"_dependencies", "_formulae", "_initial_values", "_Name",
                "known_attributes", "unknown_attributes", "_render_math_images"}
        rule = "-" * 78
        print(rule)
        print("HX Instance:", self._Name)
        print(".... = Provided, ____ = Evaluated")
        print(rule)
        for k, v in self.__dict__.items():
            if k in skip:
                continue
            sym = "." if k in self._initial_values else "_"
            vv = "?" if v is None else v
            try:
                unit = self._dependencies.get(k, [[""]])[0][0]
            except Exception:
                unit = ""
            try:
                print(f"{k.replace('_','',1):<{spacing}}{round(vv, digits)}".replace(" ", sym), unit)
            except Exception:
                print(f"{k.replace('_','',1):<{spacing}}{vv}".replace(" ", sym))


# =============================================================================
# Recipes
# =============================================================================
# NOTE: To keep this file readable, related recipes are grouped by theme.
#       Each recipe is a small method that returns the computed value.
#       Units/dependencies/formulas are declared on the decorator.


# ----------------------------- Streams & Cp -------------------------------- #

@recipe("_H_I_Cp", "J/kg/K", ["_Thi", "_H_Fluid"], r"c_{p,h,i} = c_p(T_{hi})")
def _solve_H_I_Cp_from_Thi(self: HeatExchanger):
    return getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1)) if self._Thi and self._H_Fluid else None

@recipe("_H_I_Cp", "J/kg/K", ["_Tho", "_H_Fluid"], r"c_{p,h,i} \leftarrow c_p(T_{ho})\ (\mathrm{fallback})")
def _solve_H_I_Cp_from_Tho(self: HeatExchanger):
    return getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1)) if self._Tho and self._H_Fluid else None

@recipe("_H_O_Cp", "J/kg/K", ["_Tho", "_H_Fluid"], r"c_{p,h,o} = c_p(T_{ho})")
def _solve_H_O_Cp_from_Tho(self: HeatExchanger):
    return getfluidproperty(self._H_Fluid, "CP", "T", self._Tho, "P", atm2Pa(1)) if self._Tho and self._H_Fluid else None

@recipe("_H_O_Cp", "J/kg/K", ["_Thi", "_H_Fluid"], r"c_{p,h,o} \leftarrow c_p(T_{hi})\ (\mathrm{fallback})")
def _solve_H_O_Cp_from_Thi(self: HeatExchanger):
    return getfluidproperty(self._H_Fluid, "CP", "T", self._Thi, "P", atm2Pa(1)) if self._Thi and self._H_Fluid else None

@recipe("_C_I_Cp", "J/kg/K", ["_Tci", "_C_Fluid"], r"c_{p,c,i} = c_p(T_{ci})")
def _solve_C_I_Cp_from_Tci(self: HeatExchanger):
    return getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1)) if self._Tci and self._C_Fluid else None

@recipe("_C_I_Cp", "J/kg/K", ["_Tco", "_C_Fluid"], r"c_{p,c,i} \leftarrow c_p(T_{co})\ (\mathrm{fallback})")
def _solve_C_I_Cp_from_Tco(self: HeatExchanger):
    return getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1)) if self._Tco and self._C_Fluid else None

@recipe("_C_O_Cp", "J/kg/K", ["_Tco", "_C_Fluid"], r"c_{p,c,o} = c_p(T_{co})")
def _solve_C_O_Cp_from_Tco(self: HeatExchanger):
    return getfluidproperty(self._C_Fluid, "CP", "T", self._Tco, "P", atm2Pa(1)) if self._Tco and self._C_Fluid else None

@recipe("_C_O_Cp", "J/kg/K", ["_Tci", "_C_Fluid"], r"c_{p,c,o} \leftarrow c_p(T_{ci})\ (\mathrm{fallback})")
def _solve_C_O_Cp_from_Tci(self: HeatExchanger):
    return getfluidproperty(self._C_Fluid, "CP", "T", self._Tci, "P", atm2Pa(1)) if self._Tci and self._C_Fluid else None

@recipe("_H_avg_Cp", "J/kg/K", ["_H_I_Cp", "_H_O_Cp"], r"c_{p,h,avg} = (c_{p,h,i}+c_{p,h,o})/2")
def _solve_H_avg_Cp(self: HeatExchanger):
    return (self._H_I_Cp + self._H_O_Cp) / 2.0 if (self._H_I_Cp and self._H_O_Cp) else None

@recipe("_H_avg_Cp", "J/kg/K", ["_H_I_Cp"], r"c_{p,h,avg} \approx c_{p,h,i}")
def _solve_H_avg_Cp_fallback(self: HeatExchanger):
    return self._H_I_Cp

@recipe("_C_avg_Cp", "J/kg/K", ["_C_I_Cp", "_C_O_Cp"], r"c_{p,c,avg} = (c_{p,c,i}+c_{p,c,o})/2")
def _solve_C_avg_Cp(self: HeatExchanger):
    return (self._C_I_Cp + self._C_O_Cp) / 2.0 if (self._C_I_Cp and self._C_O_Cp) else None
@recipe("_C_avg_Cp", "J/kg/K", ["_C_I_Cp"], r"c_{p,c,avg} \approx c_{p,c,i}")
def _solve_C_avg_Cp_fallback(self: HeatExchanger):
    return self._C_I_Cp


# ----------------------------- Flow conversions --------------------------- #

@recipe("_mdot_h", "kg/s", ["_H_in_nm3_hr", "_H_Fluid"], r"\dot m_h \leftarrow \mathrm{Nm^3/hr} \to \mathrm{kg/s}")
def _solve_mdot_h_from_nm3(self: HeatExchanger):
    return unit_convert(self._H_in_nm3_hr, "Nm^3/hr", "kg/s", self._H_Fluid) if (self._H_in_nm3_hr and self._H_Fluid) else None

@recipe("_H_in_nm3_hr", "nm^3/hr", ["_mdot_h", "_H_Fluid"], r"\mathrm{Nm^3/hr} \leftarrow \dot m_h")
def _solve_nm3_from_mdot_h(self: HeatExchanger):
    return unit_convert(self._mdot_h, "kg/s", "Nm^3/hr", self._H_Fluid) if (self._mdot_h and self._H_Fluid) else None

@recipe("_mdot_c", "kg/s", ["_C_in_nm3_hr", "_C_Fluid"], r"\dot m_c \leftarrow \mathrm{Nm^3/hr} \to \mathrm{kg/s}")
def _solve_mdot_c_from_nm3(self: HeatExchanger):
    return unit_convert(self._C_in_nm3_hr, "Nm^3/hr", "kg/s", self._C_Fluid) if (self._C_in_nm3_hr and self._C_Fluid) else None

@recipe("_C_in_nm3_hr", "nm^3/hr", ["_mdot_c", "_C_Fluid"], r"\mathrm{Nm^3/hr} \leftarrow \dot m_c")
def _solve_nm3_from_mdot_c(self: HeatExchanger):
    return unit_convert(self._mdot_c, "kg/s", "Nm^3/hr", self._C_Fluid) if (self._mdot_c and self._C_Fluid) else None


# ----------------------------- Core thermal -------------------------------- #

@recipe("_q_h", "J/s", ["_H_avg_Cp", "_mdot_h", "_Thi", "_Tho"], r"q_h = \dot m_h c_{p,h,avg}(T_{hi}-T_{ho})")
def _solve_q_h(self: HeatExchanger):
    return self._mdot_h * self._H_avg_Cp * (self._Thi - self._Tho) if None not in (self._mdot_h, self._H_avg_Cp, self._Thi, self._Tho) else None

@recipe("_q_c", "J/s", ["_C_avg_Cp", "_mdot_c", "_Tci", "_Tco"], r"q_c = \dot m_c c_{p,c,avg}(T_{co}-T_{ci})")
def _solve_q_c(self: HeatExchanger):
    return self._mdot_c * self._C_avg_Cp * (self._Tco - self._Tci) if None not in (self._mdot_c, self._C_avg_Cp, self._Tci, self._Tco) else None

@recipe("_q", "J/s", ["_q_h", "_q_c"], r"q = (q_h+q_c)/2")
def _solve_q_blend(self: HeatExchanger):
    if self._q_h is None and self._q_c is None:
        return None
    if self._q_h is None:
        return self._q_c
    if self._q_c is None:
        return self._q_h
    return 0.5 * (self._q_h + self._q_c)

@recipe("_q", "J/s", ["_q_c"], r"q \leftarrow q_c")
def _solve_q_from_qc(self: HeatExchanger):
    return self._q_c

@recipe("_q", "J/s", ["_q_h"], r"q \leftarrow q_h")
def _solve_q_from_qh(self: HeatExchanger):
    return self._q_h

@recipe("_lmtd", "K", ["_Thi", "_Tho", "_Tci", "_Tco"], r"\mathrm{LMTD}")
def _solve_lmtd(self: HeatExchanger):
    return LMTD(Thi=self._Thi, Tho=self._Tho, Tci=self._Tci, Tco=self._Tco, counterflow=self._Flow_Direction)

@recipe("_UA", "W/K", ["_q", "_lmtd"], r"UA = \frac{q}{F\,\mathrm{LMTD}}",
    desc= "Overall thermal conductance from duty and corrected LMTD.")
def _solve_UA_from_q_lmtd(self: HeatExchanger):
    return self._q / (self._lmtd * self._F_sub_T) if None not in (self._q, self._lmtd, self._F_sub_T) else None

@recipe("_UA", "W/K", ["_NTU", "_Cmin"], r"UA = \mathrm{NTU}\,C_{\min}")
def _solve_UA_from_NTU(self: HeatExchanger):
    return self._NTU * self._Cmin if None not in (self._NTU, self._Cmin) else None

@recipe("_Ch", "W/K", ["_mdot_h", "_H_avg_Cp"], r"C_h = \dot m_h c_{p,h,avg}")
def _solve_Ch(self: HeatExchanger):
    return self._mdot_h * self._H_avg_Cp if None not in (self._mdot_h, self._H_avg_Cp) else None

@recipe("_Cc", "W/K", ["_mdot_c", "_C_avg_Cp"], r"C_c = \dot m_c c_{p,c,avg}")
def _solve_Cc(self: HeatExchanger):
    return self._mdot_c * self._C_avg_Cp if None not in (self._mdot_c, self._C_avg_Cp) else None

@recipe("_Cmin", "W/K", ["_Cc", "_Ch"], r"C_{\min} = \min(C_h,C_c)")
def _solve_Cmin(self: HeatExchanger):
    return min(self._Ch, self._Cc) if None not in (self._Ch, self._Cc) else None

@recipe("_Cmax", "W/K", ["_Cc", "_Ch"], r"C_{\max} = \max(C_h,C_c)")
def _solve_Cmax(self: HeatExchanger):
    return max(self._Ch, self._Cc) if None not in (self._Ch, self._Cc) else None

@recipe("_Cr", "% as decimal", ["_Cmin", "_Cmax"], r"\mathrm{Cr} = C_{\min}/C_{\max}")
def _solve_Cr(self: HeatExchanger):
    return self._Cmin / self._Cmax if None not in (self._Cmin, self._Cmax) and self._Cmax else None

@recipe("_q_max", "J/s", ["_Cmin", "_Thi", "_Tci"], r"q_{\max} = C_{\min}(T_{hi}-T_{ci})")
def _solve_q_max(self: HeatExchanger):
    return self._Cmin * (self._Thi - self._Tci) if None not in (self._Cmin, self._Thi, self._Tci) else None

@recipe("_NTU", "(dimensionless)", ["_Cmin", "_UA"], r"\mathrm{NTU} = UA/C_{\min}")
def _solve_NTU(self: HeatExchanger):
    return self._UA / self._Cmin if None not in (self._UA, self._Cmin) and self._Cmin else None

@recipe("_effectiveness_epsilon", "% as decimal", ["_q", "_q_max"], r"\varepsilon = q/q_{\max}")
def _solve_epsilon_from_q(self: HeatExchanger):
    return self._q / self._q_max if None not in (self._q, self._q_max) and self._q_max else None
@recipe("_effectiveness_epsilon", "% as decimal", ["_NTU", "_Cr"], r"\varepsilon(\mathrm{NTU},\mathrm{Cr})")
def _solve_epsilon_from_NTU(self: HeatExchanger):
    if self._NTU is None or self._Cr is None:
        return None
    # counterflow vs parallel
    if self._Flow_Direction:  # counter
        if abs(self._Cr - 1.0) < 1e-9:
            return self._NTU / (1.0 + self._NTU)
        num = 1.0 - m.exp(-self._NTU * (1.0 - self._Cr))
        den = 1.0 - self._Cr * m.exp(-self._NTU * (1.0 - self._Cr))
        return num / den if abs(den) > 1e-12 else None
    # parallel
    return (1.0 - m.exp(-self._NTU * (1.0 + self._Cr))) / (1.0 + self._Cr)


# ----------------------------- Temperatures via q -------------------------- #

@recipe("_Thi", "K", ["_mdot_h", "_H_O_Cp", "_Tho", "_q"], r"T_{hi} = \frac{q}{\dot m_h c_{p,h,o}} + T_{ho}")
def _solve_Thi_from_q(self: HeatExchanger):
    return self._q / (self._mdot_h * self._H_O_Cp) + self._Tho if None not in (self._q, self._mdot_h, self._H_O_Cp, self._Tho) else None

@recipe("_Tho", "K", ["_mdot_h", "_H_I_Cp", "_Thi", "_q"], r"T_{ho} = T_{hi} - \frac{q}{\dot m_h c_{p,h,i}}")
def _solve_Tho_from_q(self: HeatExchanger):
    return self._Thi - self._q / (self._mdot_h * self._H_I_Cp) if None not in (self._Thi, self._q, self._mdot_h, self._H_I_Cp) else None
@recipe("_Tci", "K", ["_mdot_c", "_C_O_Cp", "_Tco", "_q"], r"T_{ci} = T_{co} - \frac{q}{\dot m_c c_{p,c,o}}")
def _solve_Tci_from_q(self: HeatExchanger):
    return self._Tco - self._q / (self._mdot_c * self._C_O_Cp) if None not in (self._Tco, self._q, self._mdot_c, self._C_O_Cp) else None

@recipe("_Tco", "K", ["_mdot_c", "_C_I_Cp", "_Tci", "_q"], r"T_{co} = \frac{q}{\dot m_c c_{p,c,i}} + T_{ci}")
def _solve_Tco_from_q(self: HeatExchanger):
    return self._q / (self._mdot_c * self._C_I_Cp) + self._Tci if None not in (self._q, self._mdot_c, self._C_I_Cp, self._Tci) else None


# ----------------------------- Pressure solving --------------------------- #

@recipe("_Pres_H_out", "Pa", ["_Pres_H_in", "_dP_h"], r"P_{ho} = P_{hi} - \Delta P_h")
def _solve_Pres_H_out(self: HeatExchanger):
    return self._Pres_H_in - self._dP_h if None not in (self._Pres_H_in, self._dP_h) else None
@recipe("_Pres_H_in", "Pa", ["_Pres_H_out", "_dP_h"], r"P_{hi} = P_{ho} + \Delta P_h")
def _solve_Pres_H_in(self: HeatExchanger):
    return self._Pres_H_out + self._dP_h if None not in (self._Pres_H_out, self._dP_h) else None

@recipe("_dP_h", "Pa", ["_Pres_H_in", "_Pres_H_out"], r"\Delta P_h = P_{hi}-P_{ho}")
def _solve_dP_h_from_pressures(self: HeatExchanger):
    return self._Pres_H_in - self._Pres_H_out if None not in (self._Pres_H_in, self._Pres_H_out) else None

@recipe("_Pres_C_out", "Pa", ["_Pres_C_in", "_dP_c"], r"P_{co} = P_{ci} - \Delta P_c")
def _solve_Pres_C_out(self: HeatExchanger):
    return self._Pres_C_in - self._dP_c if None not in (self._Pres_C_in, self._dP_c) else None

@recipe("_dP_c", "Pa", ["_Pres_C_in", "_Pres_C_out"], r"\Delta P_c = P_{ci}-P_{co}")
def _solve_dP_c_from_pressures(self: HeatExchanger):
    return self._Pres_C_in - self._Pres_C_out if None not in (self._Pres_C_in, self._Pres_C_out) else None


# ----------------------------- Target-velocity sizing --------------------- #

@recipe("_H_inlet_ID", "mm", ["_mdot_h", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"],
        r"D = \sqrt{\frac{4\dot m}{\pi\rho v_\mathrm{tgt}}}\ \ (\mathrm{mm})")
def _solve_H_inlet_ID_from_target_v(self: HeatExchanger):
    if None in (self._mdot_h, self._H_target_velocity, self._Pres_H_in, self._Thi, self._H_Fluid):
        return None
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    A = self._mdot_h / (rho * max(self._H_target_velocity, 1e-9))
    return m.sqrt(4.0 * A / self.PI) * 1000.0

@recipe("_H_outlet_ID", "mm", ["_mdot_h", "_H_target_velocity", "_Pres_H_out", "_Tho", "_H_Fluid"],
        r"D = \sqrt{\frac{4\dot m}{\pi\rho v_\mathrm{tgt}}}\ \ (\mathrm{mm})")
def _solve_H_outlet_ID_from_target_v(self: HeatExchanger):
    if None in (self._mdot_h, self._H_target_velocity, self._Tho, self._H_Fluid):
        return None
    P = self._Pres_H_out if self._Pres_H_out is not None else self._Pres_H_in
    if P is None:
        return None
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
    A = self._mdot_h / (rho * max(self._H_target_velocity, 1e-9))
    return m.sqrt(4.0 * A / self.PI) * 1000.0

@recipe("_mdot_h", "kg/s", ["_H_inlet_ID", "_H_target_velocity", "_Pres_H_in", "_Thi", "_H_Fluid"],
        r"\dot m_h = \rho A v_\mathrm{tgt}")
def _solve_mdot_h_from_ID_target_v(self: HeatExchanger):
    if None in (self._H_inlet_ID, self._H_target_velocity, self._Thi, self._Pres_H_in, self._H_Fluid):
        return None
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    D_m = self._H_inlet_ID / 1000.0
    A = self.PI * (D_m / 2.0) ** 2
    return rho * A * self._H_target_velocity

@recipe("_mdot_c", "kg/s", ["_C_inlet_ID", "_C_target_velocity", "_Pres_C_in", "_Tci", "_C_Fluid"],
        r"\dot m_c = \rho A v_\mathrm{tgt}")
def _solve_mdot_c_from_ID_target_v(self: HeatExchanger):
    if None in (self._C_inlet_ID, self._C_target_velocity, self._Tci, self._Pres_C_in, self._C_Fluid):
        return None
    rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
    D_m = self._C_inlet_ID / 1000.0
    A = self.PI * (D_m / 2.0) ** 2
    return rho * A * self._C_target_velocity


# ----------------------------- Velocities --------------------------------- #

@recipe("_H_inlet_velocity", "m/s", ["_mdot_h", "_H_inlet_ID", "_Pres_H_in", "_H_Fluid", "_Thi"], r"v=\dot m/(\rho A)")
def _solve_H_inlet_velocity(self: HeatExchanger):
    if None in (self._mdot_h, self._H_inlet_ID, self._Pres_H_in, self._H_Fluid, self._Thi):
        return None
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    A = self.PI * (self._H_inlet_ID/1000.0/2.0) ** 2
    return self._mdot_h / (rho * A)

@recipe("_H_outlet_velocity", "m/s", ["_mdot_h", "_H_outlet_ID", "_Pres_H_out", "_H_Fluid", "_Tho"], r"v=\dot m/(\rho A)")
def _solve_H_outlet_velocity(self: HeatExchanger):
    if None in (self._mdot_h, self._H_outlet_ID, self._H_Fluid, self._Tho):
        return None
    P = self._Pres_H_out if self._Pres_H_out is not None else self._Pres_H_in
    if P is None:
        return None
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Tho, "P", P)
    A = self.PI * (self._H_outlet_ID/1000.0/2.0) ** 2
    return self._mdot_h / (rho * A)

@recipe("_C_inlet_velocity", "m/s", ["_mdot_c", "_C_inlet_ID", "_Pres_C_in", "_C_Fluid", "_Tci"], r"v=\dot m/(\rho A)")
def _solve_C_inlet_velocity(self: HeatExchanger):
    if None in (self._mdot_c, self._C_inlet_ID, self._C_Fluid, self._Tci, self._Pres_C_in):
        return None
    rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
    A = self.PI * (self._C_inlet_ID/1000.0/2.0) ** 2
    return self._mdot_c / (rho * A)

@recipe("_C_outlet_velocity", "m/s", ["_mdot_c", "_C_outlet_ID", "_Pres_C_out", "_C_Fluid", "_Tco"], r"v=\dot m/(\rho A)")
def _solve_C_outlet_velocity(self: HeatExchanger):
    if None in (self._mdot_c, self._C_outlet_ID, self._C_Fluid, self._Tco):
        return None
    P = self._Pres_C_out if self._Pres_C_out is not None else self._Pres_C_in
    if P is None:
        return None
    rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tco, "P", P)
    A = self.PI * (self._C_outlet_ID/1000.0/2.0) ** 2
    return self._mdot_c / (rho * A)


# ----------------------------- Plate geometry & transport ----------------- #

@recipe("_t_m", "m", ["_HX_is_plate", "_plate_thickness"], r"t = t_\mathrm{mm}/1000")
def _solve_t_m(self: HeatExchanger):
    return (self._plate_thickness or 0.0) / 1000.0

@recipe("_Lp", "m", ["_HX_is_plate", "_Lv", "_Dp"], r"L_p = L_v - D_p")
def _solve_Lp(self: HeatExchanger):
    return (self._Lv - self._Dp) if None not in (self._Lv, self._Dp) else None

@recipe("_Lw", "m", ["_HX_is_plate", "_Lh", "_Dp"], r"L_w = L_h + D_p")
def _solve_Lw(self: HeatExchanger):
    return (self._Lh + self._Dp) if None not in (self._Lh, self._Dp) else None

@recipe("_Aproj", "m^2", ["_HX_is_plate", "_Lp", "_Lw"], r"A_\mathrm{proj} = L_p L_w")
def _solve_Aproj(self: HeatExchanger):
    return self._Lp * self._Lw if None not in (self._Lp, self._Lw) else None

@recipe("_Dh", "m", ["_HX_is_plate", "_mean_channel_gap", "_enlargement_phi"], r"D_h = 2 b \phi")
def _solve_Dh(self: HeatExchanger):
    b_m = (self._mean_channel_gap or 0.0) / 1000.0
    phi = self._enlargement_phi or 1.0
    return 2.0 * b_m * phi

@recipe("_Aff_hot", "m^2", ["_HX_is_plate", "_Lw", "_mean_channel_gap"], r"A_{ff} = L_w\,b")
def _solve_Aff_hot(self: HeatExchanger):
    if None in (self._Lw, self._mean_channel_gap):
        return None
    return self._Lw * (self._mean_channel_gap/1000.0)

@recipe("_Aff_cold", "m^2", ["_HX_is_plate", "_Lw", "_mean_channel_gap"], r"A_{ff} = L_w\,b")
def _solve_Aff_cold(self: HeatExchanger):
    if None in (self._Lw, self._mean_channel_gap):
        return None
    return self._Lw * (self._mean_channel_gap/1000.0)

@recipe("_mu_h", "Pa·s", ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"], r"\mu_h(T_{hi},P_{hi})")
def _solve_mu_h(self: HeatExchanger):
    return self._get_mu(self._H_Fluid, self._Thi, self._Pres_H_in)

@recipe("_mu_c", "Pa·s", ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"], r"\mu_c(T_{ci},P_{ci})")
def _solve_mu_c(self: HeatExchanger):
    return self._get_mu(self._C_Fluid, self._Tci, self._Pres_C_in)

@recipe("_k_h", "W/m/K", ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"], r"k_h(T_{hi},P_{hi})")
def _solve_k_h(self: HeatExchanger):
    return self._get_k(self._H_Fluid, self._Thi, self._Pres_H_in)

@recipe("_k_c", "W/m/K", ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"], r"k_c(T_{ci},P_{ci})")
def _solve_k_c(self: HeatExchanger):
    return self._get_k(self._C_Fluid, self._Tci, self._Pres_C_in)

@recipe("_Pr_h", "(dimensionless)", ["_HX_is_plate", "_H_Fluid", "_Thi", "_Pres_H_in"], r"\mathrm{Pr}_h")
def _solve_Pr_h(self: HeatExchanger):
    return self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in)

@recipe("_Pr_c", "(dimensionless)", ["_HX_is_plate", "_C_Fluid", "_Tci", "_Pres_C_in"], r"\mathrm{Pr}_c")
def _solve_Pr_c(self: HeatExchanger):
    return self._get_pr(self._C_Fluid, self._Tci, self._Pres_C_in)

@recipe("_channels_per_pass_hot", "channels per pass", ["_Plate_Count", "_Plate_Distribution_Bias"], r"\text{channels/pass (hot)}")
def _solve_cpp_hot_compat(self: HeatExchanger):
    # compatibility alias if UI uses Plate_Count (optional)
    return None

@recipe("_channels_per_pass_hot", "channels per pass", ["_Plate_count", "_Plate_Distribution_Bias"], r"\text{channels/pass (hot)}")
def _solve_cpp_hot(self: HeatExchanger):
    if self._Plate_count is None:
        return None
    if self._Plate_count % 2 == 0:
        return (self._Plate_count - 1)/2 + (0.5 if self._Plate_Distribution_Bias == "hot" else -0.5)
    return (self._Plate_count - 1)/2

@recipe("_channels_per_pass_cold", "channels per pass", ["_Plate_count", "_Plate_Distribution_Bias"], r"\text{channels/pass (cold)}")
def _solve_cpp_cold(self: HeatExchanger):
    if self._Plate_count is None:
        return None
    if self._Plate_count % 2 == 0:
        return (self._Plate_count - 1)/2 + (-0.5 if self._Plate_Distribution_Bias == "hot" else 0.5)
    return (self._Plate_count - 1)/2

@recipe("_mdot_h_channel", "kg/s", ["_mdot_h", "_channels_per_pass_hot"], r"\dot m_{h,ch} = \dot m_h/N_{ch,hot}")
def _solve_mdot_h_channel(self: HeatExchanger):
    return self._mdot_h / self._channels_per_pass_hot if None not in (self._mdot_h, self._channels_per_pass_hot) else None

@recipe("_mdot_c_channel", "kg/s", ["_mdot_c", "_channels_per_pass_cold"], r"\dot m_{c,ch} = \dot m_c/N_{ch,cold}")
def _solve_mdot_c_channel(self: HeatExchanger):
    return self._mdot_c / self._channels_per_pass_cold if None not in (self._mdot_c, self._channels_per_pass_cold) else None

@recipe("_G_h", "kg/m^2/s", ["_HX_is_plate", "_mdot_h_channel", "_Aff_hot"], r"G_h = \dot m_{h,ch}/A_{ff}")
def _solve_G_h(self: HeatExchanger):
    return self._mdot_h_channel / self._Aff_hot if None not in (self._mdot_h_channel, self._Aff_hot) else None

@recipe("_G_c", "kg/m^2/s", ["_HX_is_plate", "_mdot_c_channel", "_Aff_cold"], r"G_c = \dot m_{c,ch}/A_{ff}")
def _solve_G_c(self: HeatExchanger):
    return self._mdot_c_channel / self._Aff_cold if None not in (self._mdot_c_channel, self._Aff_cold) else None

@recipe("_Re_h", "(dimensionless)", ["_HX_is_plate", "_G_h", "_Dh", "_mu_h"], r"\mathrm{Re}_h = \frac{G_h D_h}{\mu_h}")
def _solve_Re_h(self: HeatExchanger):
    return (self._G_h * self._Dh) / self._mu_h if None not in (self._G_h, self._Dh, self._mu_h) and self._mu_h else None
@recipe("_Re_c", "(dimensionless)", ["_HX_is_plate", "_G_c", "_Dh", "_mu_c"], r"\mathrm{Re}_c = \frac{G_c D_h}{\mu_c}")
def _solve_Re_c(self: HeatExchanger):
    return (self._G_c * self._Dh) / self._mu_c if None not in (self._G_c, self._Dh, self._mu_c) and self._mu_c else None

@recipe("_h_h", "W/m^2/K", ["_HX_is_plate", "_Re_h", "_Pr_h", "_k_h", "_Dh"], r"h_h = \frac{\mathrm{Nu}_h k_h}{D_h}")
def _solve_h_h(self: HeatExchanger):
    if None in (self._Re_h, self._Pr_h, self._k_h, self._Dh):
        return None
    C, n = 0.3, 0.663
    Nu = C * (self._Re_h ** n) * ((self._Pr_h or 0.7) ** (1.0/3.0))
    return Nu * self._k_h / self._Dh

@recipe("_h_c", "W/m^2/K", ["_HX_is_plate", "_Re_c", "_Pr_c", "_k_c", "_Dh"], r"h_c = \frac{\mathrm{Nu}_c k_c}{D_h}")
def _solve_h_c(self: HeatExchanger):
    if None in (self._Re_c, self._Pr_c, self._k_c, self._Dh):
        return None
    C, n = 0.3, 0.663
    Nu = C * (self._Re_c ** n) * ((self._Pr_c or 0.7) ** (1.0/3.0))
    return Nu * self._k_c / self._Dh

@recipe("_U_calc", "W/m^2/K", ["_HX_is_plate", "_h_h", "_h_c", "_t_m", "_plate_material", "_fouling_hot", "_fouling_cold"],
        r"\left(\frac{1}{h_h}+R_{f,h}+\frac{t}{k} + R_{f,c}+\frac{1}{h_c}\right)^{-1}")
def _solve_U_calc(self: HeatExchanger):
    k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
    R_hot = 1.0 / max(self._h_h or 1e-12, 1e-12) + float(self._fouling_hot or 0.0)
    R_cold = 1.0 / max(self._h_c or 1e-12, 1e-12) + float(self._fouling_cold or 0.0)
    R_wall = (self._t_m or 0.0006) / float(k_wall)
    R_tot = R_hot + R_wall + R_cold
    return 1.0 / max(R_tot, 1e-18)

@recipe("_dP_h", "Pa", ["_HX_is_plate", "_Re_h", "_G_h", "_Dh", "_Lp", "_H_Fluid", "_Thi", "_Pres_H_in"],
        r"\Delta P \approx 4 f \frac{L_p}{D_h}\frac{\rho v^2}{2} + \Delta P_\mathrm{ports}")
def _solve_dP_h(self: HeatExchanger):
    if None in (self._Re_h, self._G_h, self._Dh, self._Lp, self._H_Fluid, self._Thi, self._Pres_H_in):
        return None
    f = 1.441 * (self._Re_h ** -0.206)
    rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    v = self._G_h / rho
    dP_ch = 4.0 * f * (self._Lp / self._Dh) * (rho * v * v / 2.0)
    A_port = self.PI * (self._Dp/2.0)**2 if self._Dp else None
    v_p = (self._mdot_h / A_port) / rho if (A_port and rho and A_port > 0) else 0.0
    dP_port = 1.4 * (self._Hot_Passes or 1) * (rho * v_p * v_p / 2.0)
    return dP_ch + dP_port

@recipe("_dP_c", "Pa", ["_HX_is_plate", "_Re_c", "_G_c", "_Dh", "_Lp", "_C_Fluid", "_Tci", "_Pres_C_in"],
        r"\Delta P \approx 4 f \frac{L_p}{D_h}\frac{\rho v^2}{2} + \Delta P_\mathrm{ports}")
def _solve_dP_c(self: HeatExchanger):
    if None in (self._Re_c, self._G_c, self._Dh, self._Lp, self._C_Fluid, self._Tci, self._Pres_C_in):
        return None
    f = 1.441 * (self._Re_c ** -0.206)
    rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
    v = self._G_c / rho
    dP_ch = 4.0 * f * (self._Lp / self._Dh) * (rho * v * v / 2.0)
    A_port = self.PI * (self._Dp/2.0)**2 if self._Dp else None
    v_p = (self._mdot_c / A_port) / rho if (A_port and rho and A_port > 0) else 0.0
    dP_port = 1.4 * (self._Hot_Passes or 1) * (rho * v_p * v_p / 2.0)
    return dP_ch + dP_port

@recipe("_dP_total", "Pa", ["_HX_is_plate", "_dP_h", "_dP_c"], r"\Delta P_\mathrm{tot} = \Delta P_h + \Delta P_c")
def _solve_dP_total(self: HeatExchanger):
    return (self._dP_h or 0.0) + (self._dP_c or 0.0)


# ----------------------------- ε–NTU + entropy ---------------------------- #

@recipe("_epsilon_NTU", "(dimensionless)", ["_NTU", "_Cr"], r"\varepsilon(\mathrm{NTU},\mathrm{Cr})")
def _solve_epsilon_NTU(self: HeatExchanger):
    return _solve_epsilon_from_NTU(self)

@recipe("_Tho_eps", "K", ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch"], r"T_{ho} = T_{hi} - \varepsilon\,\frac{C_{\min}}{C_h}(T_{hi}-T_{ci})")
def _solve_Tho_eps(self: HeatExchanger):
    return self._Thi - self._epsilon_NTU * self._Cmin * (self._Thi - self._Tci) / self._Ch if None not in (self._epsilon_NTU, self._Cmin, self._Thi, self._Tci, self._Ch) and self._Ch else None

@recipe("_Tco_eps", "K", ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Cc"], r"T_{co} = T_{ci} + \varepsilon\,\frac{C_{\min}}{C_c}(T_{hi}-T_{ci})")
def _solve_Tco_eps(self: HeatExchanger):
    return self._Tci + self._epsilon_NTU * self._Cmin * (self._Thi - self._Tci) / self._Cc if None not in (self._epsilon_NTU, self._Cmin, self._Thi, self._Tci, self._Cc) and self._Cc else None

@recipe("_S_gen", "W/K", ["_HX_is_plate", "_epsilon_NTU", "_Cmin", "_Thi", "_Tci", "_Ch", "_Cc", "_dP_h", "_dP_c", "_H_Fluid", "_C_Fluid"], r"S_\mathrm{gen}")
def _solve_S_gen(self: HeatExchanger):
    Th2 = self._Tho or self._Tho_eps
    Tc2 = self._Tco or self._Tco_eps
    if Th2 is None or Tc2 is None or None in (self._Thi, self._Tci, self._Ch, self._Cc, self._H_Fluid, self._C_Fluid, self._Pres_H_in, self._Pres_C_in):
        return None
    eps = 1e-12
    term_h = self._Ch * m.log(max(Th2, eps) / max(self._Thi, eps))
    term_c = self._Cc * m.log(max(Tc2, eps) / max(self._Tci, eps))
    S_ht = term_h + term_c
    rho_h = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    rho_c = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
    S_dp = (self._mdot_h * (self._dP_h or 0.0) / (rho_h * self._Thi)) + (self._mdot_c * (self._dP_c or 0.0) / (rho_c * self._Tci))
    return S_ht + S_dp

@recipe("_Ns", "(dimensionless)", ["_HX_is_plate", "_S_gen", "_Cmax"], r"N_s = S_\mathrm{gen}/C_{\max}")
def _solve_Ns(self: HeatExchanger):
    return self._S_gen / self._Cmax if None not in (self._S_gen, self._Cmax) and self._Cmax else None


# ----------------------------- Shell & Tube (core) ------------------------ #

@recipe("_ST_L_total", "m", ["_HX_is_st", "_ST_L_pass", "_ST_N_tube_passes"], r"L_\mathrm{tot} = L_\mathrm{pass}\,N_\mathrm{passes}")
def _solve_ST_L_total(self: HeatExchanger):
    return self._ST_L_pass * float(self._ST_N_tube_passes or 1) if self._ST_L_pass else None

@recipe("_ST_N_tubes_per_pass", "(count)", ["_HX_is_st", "_ST_N_tubes", "_ST_N_tube_passes"], r"N_\mathrm{tubes/pass} = N_\mathrm{tubes}/N_\mathrm{passes}")
def _solve_ST_N_tubes_per_pass(self: HeatExchanger):
    return (float(self._ST_N_tubes or 0) / float(self._ST_N_tube_passes)) if (self._ST_N_tube_passes or 0) > 0 else None
@recipe("_ST_Ai", "m^2", ["_HX_is_st", "_ST_Di", "_ST_L_total", "_ST_N_tubes"], r"A_i = \pi D_i L_\mathrm{tot} N")
def _solve_ST_Ai(self: HeatExchanger):
    return m.pi * self._ST_Di * self._ST_L_total * float(self._ST_N_tubes or 0) if None not in (self._ST_Di, self._ST_L_total, self._ST_N_tubes) else None

@recipe("_ST_Ao", "m^2", ["_HX_is_st", "_ST_Do", "_ST_L_total", "_ST_N_tubes"], r"A_o = \pi D_o L_\mathrm{tot} N")
def _solve_ST_Ao(self: HeatExchanger):
    return m.pi * self._ST_Do * self._ST_L_total * float(self._ST_N_tubes or 0) if None not in (self._ST_Do, self._ST_L_total, self._ST_N_tubes) else None

@recipe("_ST_Re_tube", "(dimensionless)", ["_HX_is_st", "_ST_hot_in_tube", "_ST_Di", "_ST_N_tubes_per_pass", "_mdot_h", "_mdot_c", "_H_Fluid", "_C_Fluid", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"], r"\mathrm{Re}_\mathrm{tube}")
def _solve_ST_Re_tube(self: HeatExchanger):
    if None in (self._ST_hot_in_tube, self._ST_Di, self._ST_N_tubes_per_pass):
        return None
    hot_in = bool(int(self._ST_hot_in_tube or 1))
    if hot_in:
        rho = getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
        mu = self._get_mu(self._H_Fluid, self._Thi, self._Pres_H_in)
        mdot = (self._mdot_h or 0.0)
    else:
        rho = getfluidproperty(self._C_Fluid, "D", "T", self._Tci, "P", self._Pres_C_in)
        mu = self._get_mu(self._C_Fluid, self._Tci, self._Pres_C_in)
        mdot = (self._mdot_c or 0.0)
    Atube = m.pi * (self._ST_Di**2) / 4.0
    Atotal = Atube * float(self._ST_N_tubes_per_pass or 1.0)
    u = (mdot / (rho * Atotal)) if (rho and Atotal) else 0.0
    return rho * u * self._ST_Di / (mu or 1e-9)

@recipe("_ST_Nu_tube", "(dimensionless)", ["_HX_is_st", "_ST_Re_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"], r"\mathrm{Nu}_\mathrm{tube} \approx 0.023\,\mathrm{Re}^{0.8}\mathrm{Pr}^{0.4}")
def _solve_ST_Nu_tube(self: HeatExchanger):
    if self._ST_Re_tube is None or self._ST_hot_in_tube is None:
        return None
    hot_in = bool(int(self._ST_hot_in_tube or 1))
    Pr = (self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in) if hot_in
          else self._get_pr(self._C_Fluid, self._Tci, self._Pres_C_in)) or 0.7
    return 0.023 * (self._ST_Re_tube ** 0.8) * (Pr ** 0.4)

@recipe("_ST_h_i", "W/m^2/K", ["_HX_is_st", "_ST_Nu_tube", "_H_Fluid", "_C_Fluid", "_ST_hot_in_tube", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in", "_ST_Di"], r"h_i = \mathrm{Nu}\,k/D_i")
def _solve_ST_h_i(self: HeatExchanger):
    if None in (self._ST_Nu_tube, self._ST_hot_in_tube, self._ST_Di):
        return None
    hot_in = bool(int(self._ST_hot_in_tube or 1))
    k = (self._get_k(self._H_Fluid, self._Thi, self._Pres_H_in) if hot_in
         else self._get_k(self._C_Fluid, self._Tci, self._Pres_C_in))
    return (self._ST_Nu_tube * k / self._ST_Di) if (k and self._ST_Di) else None

@recipe("_ST_U", "W/m^2/K", ["_HX_is_st", "_ST_h_i", "_ST_h_o", "_ST_Rf_i", "_ST_Rf_o", "_ST_k_wall", "_ST_Di", "_ST_Do", "_ST_Ai", "_ST_Ao", "_ST_L_total"], r"\left(\frac{1}{h_i A_i}+\frac{R_{f,i}}{A_i}+\frac{\ln(D_o/D_i)}{2\pi k L}+\frac{R_{f,o}}{A_o}+\frac{1}{h_o A_o}\right)^{-1}\! /A_i")
def _solve_ST_U(self: HeatExchanger):
    if None in (self._ST_h_i, self._ST_Ai, self._ST_Do, self._ST_Di, self._ST_k_wall, self._ST_L_total):
        return None
    term_i = (1.0/(self._ST_h_i * self._ST_Ai)) if (self._ST_h_i and self._ST_Ai) else 0.0
    term_ri = (self._ST_Rf_i or 0.0) / (self._ST_Ai or 1e-9)
    term_w = m.log(self._ST_Do/self._ST_Di)/(2.0*m.pi*(self._ST_k_wall or 1e9)*self._ST_L_total)
    term_ro = (self._ST_Rf_o or 0.0)/(self._ST_Ao or 1e-9) if self._ST_Ao else 0.0
    term_o = (1.0/((self._ST_h_o or 1e-9)*(self._ST_Ao or 1e-9))) if self._ST_Ao else 0.0
    inv_UA = term_i + term_ri + term_w + term_ro + term_o
    UA = 1.0/inv_UA if inv_UA > 0 else None
    self._ST_UA = UA
    return (UA / (self._ST_Ai or 1.0)) if UA else None

@recipe("_ST_UA", "W/K", ["_HX_is_st", "_ST_U", "_ST_Ai"], r"UA = U A_i")
def _solve_ST_UA(self: HeatExchanger):
    return (self._ST_U or 0.0) * (self._ST_Ai or 0.0) if None not in (self._ST_U, self._ST_Ai) else None
# ----------------------------- Air‑cooled / Compact ----------------------- #

@recipe("_ACH_Aff", "m^2", ["_HX_is_ache", "_ACH_A_fr", "_ACH_sigma"], r"A_{ff} = A_{fr}\,\sigma")
def _solve_ACH_Aff(self: HeatExchanger):
    return (self._ACH_A_fr or 0.0) * (self._ACH_sigma or 0.0) if None not in (self._ACH_A_fr, self._ACH_sigma) else None

@recipe("_ACH_A", "m^2", ["_HX_is_ache", "_ACH_alpha", "_ACH_V"], r"A = \alpha V")
def _solve_ACH_A(self: HeatExchanger):
    return (self._ACH_alpha or 0.0) * (self._ACH_V or 0.0) if None not in (self._ACH_alpha, self._ACH_V) else None

@recipe("_ACH_G_hot", "kg/m^2/s", ["_HX_is_ache", "_ACH_Aff", "_mdot_h"], r"G_h = \dot m_h/A_{ff}")
def _solve_ACH_G_hot(self: HeatExchanger):
    return (self._mdot_h or 0.0)/self._ACH_Aff if self._ACH_Aff else None

@recipe("_ACH_h_hot", "W/m^2/K", ["_HX_is_ache", "_ACH_jH", "_ACH_G_hot", "_H_Fluid", "_Thi", "_Pres_H_in"], r"h_h \approx \mathrm{St}\,G\,c_p")
def _solve_ACH_h_hot(self: HeatExchanger):
    if None in (self._ACH_jH, self._ACH_G_hot, self._H_Fluid, self._Thi, self._Pres_H_in):
        return None
    cp = self._get_cp(self._H_Fluid, self._Thi, self._Pres_H_in)
    Pr = self._get_pr(self._H_Fluid, self._Thi, self._Pres_H_in) or 0.7
    St = (self._ACH_jH or 0.0) / (Pr ** (2.0/3.0))
    return St * self._ACH_G_hot * (cp or 0.0)

@recipe("_ACH_eta_o_resolved", "(dimensionless)", ["_HX_is_ache", "_ACH_eta_o_hot", "_ACH_Af_over_A", "_ACH_eta_f"], r"\eta_o = 1 - \frac{A_f}{A}(1-\eta_f)")
def _solve_ACH_eta_o(self: HeatExchanger):
    if self._ACH_eta_o_hot is not None:
        return self._ACH_eta_o_hot
    AfA = float(self._ACH_Af_over_A or 0.0)
    eta_f = float(self._ACH_eta_f or 1.0)
    return 1.0 - AfA * (1.0 - eta_f)

@recipe("_ACH_U", "W/m^2/K", ["_HX_is_ache", "_ACH_eta_o_resolved", "_ACH_h_hot", "_h_c", "_t_m", "_plate_material", "_fouling_hot", "_fouling_cold"], r"\left(\frac{1}{\eta_o h_h}+ \frac{t}{k} + \frac{1}{h_c} + R_{f,h}+R_{f,c}\right)^{-1}")
def _solve_ACH_U(self: HeatExchanger):
    k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
    R_wall = (self._t_m or 0.0006) / float(k_wall)
    R_hot = 1.0 / ((self._ACH_eta_o_resolved or 1.0) * (self._ACH_h_hot or 1e-9))
    R_cold = 1.0 / float(self._h_c or 1e-9)
    Rf_h = float(self._fouling_hot or 0.0)
    Rf_c = float(self._fouling_cold or 0.0)
    return 1.0 / (R_hot + R_wall + R_cold + Rf_h + Rf_c)

@recipe("_ACH_dp_core", "Pa", ["_HX_is_ache", "_ACH_f_core", "_ACH_A", "_ACH_Aff", "_ACH_G_hot", "_H_Fluid", "_Thi", "_Tci", "_Pres_H_in", "_Pres_C_in"], r"\Delta p_\mathrm{core} \approx f\,\frac{A}{A_{ff}}\frac{G^2}{2\rho_\mathrm{mean}} + \mathrm{accel}")
def _solve_ACH_dp_core(self: HeatExchanger):
    if None in (self._ACH_f_core, self._ACH_G_hot, self._H_Fluid, self._Thi, self._Pres_H_in):
        return None
    vi = 1.0 / getfluidproperty(self._H_Fluid, "D", "T", self._Thi, "P", self._Pres_H_in)
    To_guess = self._Tho or self._Tho_eps or (self._Thi - 10.0)
    vo = 1.0 / getfluidproperty(self._H_Fluid, "D", "T", max(To_guess, 1.0), "P", self._Pres_H_in)
    vm = 0.5 * (vi + vo)
    A_over_Aff = (self._ACH_A / (self._ACH_Aff or 1e-9)) if (self._ACH_A and self._ACH_Aff) else ((self._ACH_V or 0.0)/(self._ACH_A_fr or 1e-9))
    G2 = (self._ACH_G_hot or 0.0) ** 2
    term_accel = 0.5 * G2 * (vo - vi) / (vi * vo)
    term_fric = (self._ACH_f_core or 0.0) * A_over_Aff * (0.5 * G2 / vm)
    return term_accel + term_fric


# ----------------------------- Wall coupling & transients ----------------- #

@recipe("_U_from_material", "W/m^2/K", ["_h_h", "_h_c", "_t_m", "_plate_material", "_fouling_hot", "_fouling_cold"],
        r"\left(\frac{1}{h_h}+R_{f,h}+\frac{t}{k}+R_{f,c}+\frac{1}{h_c}\right)^{-1}")
def _solve_U_from_material(self: HeatExchanger):
    k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
    return U_composite(self._h_h or 1e-12, self._h_c or 1e-12, k_wall, self._t_m or (self._plate_thickness or 0.0)/1000.0,
                       float(self._fouling_hot or 0.0), float(self._fouling_cold or 0.0))

@recipe("_Tw_hot_avg", "K", ["_q", "_A", "_h_h", "_Thi", "_Tho"], r"T_{w,h} \approx \overline{T}_h - \frac{q}{A h_h}")
def _solve_Tw_hot_avg(self: HeatExchanger):
    if None in (self._q, self._A, self._h_h, self._Thi, self._Tho):
        return None
    Th_avg = 0.5*(self._Thi + self._Tho)
    Thw, _ = wall_faces_from_qA(self._h_h, self._h_c or 1e-12, self._q, self._A, Th_avg, 0.0)
    return Thw

@recipe("_Tw_cold_avg", "K", ["_q", "_A", "_h_c", "_Tci", "_Tco"], r"T_{w,c} \approx \overline{T}_c + \frac{q}{A h_c}")
def _solve_Tw_cold_avg(self: HeatExchanger):
    if None in (self._q, self._A, self._h_c, self._Tci, self._Tco):
        return None
    Tc_avg = 0.5*(self._Tci + self._Tco)
    _, Tcw = wall_faces_from_qA(self._h_h or 1e-12, self._h_c, self._q, self._A, 0.0, Tc_avg)
    return Tcw

@recipe("_t_required_UA", "m", ["_q", "_lmtd", "_F_sub_T", "_h_h", "_h_c", "_plate_material", "_fouling_hot", "_fouling_cold"], r"t = k\!\left(\frac{1}{U}-\frac{1}{h_h}-R_{f,h}-\frac{1}{h_c}-R_{f,c}\right)")
def _solve_t_required_UA(self: HeatExchanger):
    if None in (self._q, self._lmtd, self._A, self._h_h, self._h_c, self._plate_material):
        return None
    UA_needed = UA_from_q_LMTD(self._q, self._lmtd, self._F_sub_T)
    U_needed = UA_needed / max(self._A, 1e-18)
    k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
    return t_required_for_U(U_needed, self._h_h, self._h_c, k_wall,
                            float(self._fouling_hot or 0.0), float(self._fouling_cold or 0.0))

@recipe("_t_required_consistency", "m", ["_q", "_A", "_h_h", "_h_c", "_Thi", "_Tho", "_Tci", "_Tco", "_plate_material"],
        r"t = k\,\dfrac{T_{w,h}-T_{w,c}}{q/A}")
def _solve_t_required_consistency(self: HeatExchanger):
    if None in (self._q, self._A, self._h_h, self._h_c, self._Thi, self._Tho, self._Tci, self._Tco, self._plate_material):
        return None
    Th_avg = 0.5*(self._Thi + self._Tho)
    Tc_avg = 0.5*(self._Tci + self._Tco)
    k_wall = getattr(self._plate_material, "k", None) or getattr(self._plate_material, "_k", None) or 15.0
    return t_required_from_wall_face_gap(self._h_h, self._h_c, k_wall, self._q, self._A, Th_avg, Tc_avg)

@recipe("_A_required_wall_limit", "m^2", ["_q", "_h_h", "_h_c", "_Thi", "_Tho", "_Tci", "_Tco", "_T_wall_hot_max", "_T_wall_cold_max"],
        r"A \ge \max\!\left(\frac{q}{h_h(\overline{T}_h - T_{w,h,\max})}, \frac{q}{h_c(T_{w,c,\max}-\overline{T}_c)}\right)")
def _solve_A_required_wall_limit(self: HeatExchanger):
    if None in (self._q, self._h_h, self._h_c, self._Thi, self._Tho, self._Tci, self._Tco):
        return None
    Th_avg = 0.5*(self._Thi + self._Tho)
    Tc_avg = 0.5*(self._Tci + self._Tco)
    return area_required_from_wall_limit(self._h_h, self._h_c, self._q, Th_avg, Tc_avg,
                                         self._T_wall_hot_max, self._T_wall_cold_max)

@recipe("_tau_wall", "s", ["_plate_rho", "_plate_cp", "_t_m", "_A", "_h_h", "_h_c"],
        r"\tau \approx \frac{\rho c\,t}{h_h+h_c}")
def _solve_tau_wall(self: HeatExchanger):
    if None in (self._plate_rho, self._plate_cp, self._t_m, self._A, self._h_h, self._h_c):
        return None
    wall = WallInputs(k=1.0, t=self._t_m, rho=self._plate_rho, cp=self._plate_cp)
    return wall_time_constant(wall, self._A, self._h_h, self._h_c)

@recipe("_t95_wall", "s", ["_tau_wall"], r"t_{95\%} = -\tau\ln(1-0.95)")
def _solve_t95_wall(self: HeatExchanger):
    return time_to_fraction(self._tau_wall, 0.95) if self._tau_wall else None