from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Optional

from utilities import fluid_names, getfluidproperty, unit_convert


temperature_units = ["F", "Rank", "C", "K"]
line_pressure_units = ["psia", "psig", "Pa", "bar,a", "bar,g", "atm"]
absolute_pressure_units = ["psia", "Pa", "bar,a", "atm"]

REFERENCE_CONDITION_PRESETS = {
    "NIFTI Normal: 20 C, 14.72 psia": {
        "temperature_value": 20.0,
        "temperature_unit": "C",
        "pressure_value": 14.72,
        "pressure_unit": "psia",
    },
    "NIFTI Standard: 0 C, 14.72 psia": {
        "temperature_value": 0.0,
        "temperature_unit": "C",
        "pressure_value": 14.72,
        "pressure_unit": "psia",
    },
    "NIFTI Standard: 61 F, 14.696 psia": {
        "temperature_value": 61.0,
        "temperature_unit": "F",
        "pressure_value": 14.696,
        "pressure_unit": "psia",
    },
    "STP: 0 C, 1 atm": {
        "temperature_value": 0.0,
        "temperature_unit": "C",
        "pressure_value": 1.0,
        "pressure_unit": "atm",
    },
    "NTP: 20 C, 1 atm": {
        "temperature_value": 20.0,
        "temperature_unit": "C",
        "pressure_value": 1.0,
        "pressure_unit": "atm",
    },
    "NTP: 15 C, 1 atm": {
        "temperature_value": 15.0,
        "temperature_unit": "C",
        "pressure_value": 1.0,
        "pressure_unit": "atm",
    },
    "Custom": None,
}

TIME_UNIT_SECONDS = {
    "s": 1.0,
    "min": 60.0,
    "hr": 3600.0,
}

FLOW_UNIT_DEFINITIONS = {
    "kg/s": {"family": "mass", "quantity_unit": "kg", "time_unit": "s"},
    "kg/hr": {"family": "mass", "quantity_unit": "kg", "time_unit": "hr"},
    "lbm/s": {"family": "mass", "quantity_unit": "lbm", "time_unit": "s"},
    "lbm/hr": {"family": "mass", "quantity_unit": "lbm", "time_unit": "hr"},
    "m^3/s": {"family": "actual_volume", "quantity_unit": "m^3", "time_unit": "s"},
    "m^3/hr": {"family": "actual_volume", "quantity_unit": "m^3", "time_unit": "hr"},
    "LPS": {"family": "actual_volume", "quantity_unit": "L", "time_unit": "s"},
    "LPM": {"family": "actual_volume", "quantity_unit": "L", "time_unit": "min"},
    "ACFM": {"family": "actual_volume", "quantity_unit": "ft^3", "time_unit": "min"},
    "Nm^3/hr": {"family": "standard_volume", "quantity_unit": "m^3", "time_unit": "hr"},
    "NLPM": {"family": "standard_volume", "quantity_unit": "L", "time_unit": "min"},
    "SLPM": {"family": "standard_volume", "quantity_unit": "L", "time_unit": "min"},
    "SCFM": {"family": "standard_volume", "quantity_unit": "ft^3", "time_unit": "min"},
}

flow_units = list(FLOW_UNIT_DEFINITIONS.keys())

PROPERTY_CANDIDATES = {
    "D": ["D"],
    "VIS": ["VIS", "VISCOSITY", "V"],
}


@dataclass(frozen=True)
class StatePoint:
    temperature_k: float
    pressure_pa: float


@dataclass(frozen=True)
class ReferenceCondition:
    name: str
    temperature_value: float
    temperature_unit: str
    pressure_value: float
    pressure_unit: str

    @property
    def temperature_k(self) -> float:
        return unit_convert(self.temperature_value, self.temperature_unit, "K")

    @property
    def pressure_pa(self) -> float:
        return unit_convert(self.pressure_value, self.pressure_unit, "Pa")

    def as_state_point(self) -> StatePoint:
        return StatePoint(self.temperature_k, self.pressure_pa)

    @property
    def summary(self) -> str:
        return (
            f"{self.temperature_value:g} {self.temperature_unit}, "
            f"{self.pressure_value:g} {self.pressure_unit}"
        )


@dataclass(frozen=True)
class CMEResult:
    calibration_gas: str
    measured_gas: str
    input_value: float
    input_unit: str
    output_unit: str
    line_state: StatePoint
    input_reference: Optional[ReferenceCondition]
    output_reference: Optional[ReferenceCondition]
    output_value: float
    equivalent_mass_flow_kgps: float
    measured_mass_flow_kgps: float
    equivalent_actual_flow_m3ps: float
    measured_actual_flow_m3ps: float
    calibration_density_line_kgpm3: float
    measured_density_line_kgpm3: float
    calibration_viscosity_line_pas: float
    measured_viscosity_line_pas: float
    input_reference_density_kgpm3: Optional[float]
    output_reference_density_kgpm3: Optional[float]
    actual_flow_ratio: float
    mass_flow_ratio: Optional[float]
    display_factor: Optional[float]


def requires_reference_condition(flow_unit: str) -> bool:
    return FLOW_UNIT_DEFINITIONS[flow_unit]["family"] == "standard_volume"


def flow_family(flow_unit: str) -> str:
    return FLOW_UNIT_DEFINITIONS[flow_unit]["family"]


def preset_reference_condition(preset_name: str) -> ReferenceCondition:
    preset = REFERENCE_CONDITION_PRESETS[preset_name]
    if preset is None:
        raise ValueError("Custom does not map to a fixed reference condition.")
    return ReferenceCondition(
        name=preset_name,
        temperature_value=preset["temperature_value"],
        temperature_unit=preset["temperature_unit"],
        pressure_value=preset["pressure_value"],
        pressure_unit=preset["pressure_unit"],
    )


def build_reference_condition(
    name: str,
    temperature_value: float,
    temperature_unit: str,
    pressure_value: float,
    pressure_unit: str,
) -> ReferenceCondition:
    return ReferenceCondition(
        name=name,
        temperature_value=temperature_value,
        temperature_unit=temperature_unit,
        pressure_value=pressure_value,
        pressure_unit=pressure_unit,
    )


def build_state_point(
    temperature_value: float,
    temperature_unit: str,
    pressure_value: float,
    pressure_unit: str,
) -> StatePoint:
    temperature_k = unit_convert(temperature_value, temperature_unit, "K")
    pressure_pa = unit_convert(pressure_value, pressure_unit, "Pa")

    if temperature_k <= 0:
        raise ValueError("Temperature must convert to an absolute temperature above 0 K.")
    if pressure_pa <= 0:
        raise ValueError("Pressure must convert to an absolute pressure above 0 Pa.")

    return StatePoint(temperature_k=temperature_k, pressure_pa=pressure_pa)


def _property_at_state(fluid: str, desired_property: str, state: StatePoint) -> float:
    candidates = PROPERTY_CANDIDATES.get(desired_property, [desired_property])
    last_error = None

    for property_name in candidates:
        try:
            value = getfluidproperty(
                fluid,
                property_name,
                "P",
                state.pressure_pa,
                "T",
                state.temperature_k,
            )
        except Exception as exc:
            last_error = exc
            continue

        if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
            return float(value)

    raise ValueError(
        f"Unable to evaluate {desired_property} for {fluid} at the selected state."
    ) from last_error


def density_at_state(fluid: str, state: StatePoint) -> float:
    return _property_at_state(fluid, "D", state)


def viscosity_at_state(fluid: str, state: StatePoint) -> float:
    return _property_at_state(fluid, "VIS", state)


def _volume_rate_to_m3ps(value: float, flow_unit: str) -> float:
    metadata = FLOW_UNIT_DEFINITIONS[flow_unit]
    quantity_m3 = unit_convert(value, metadata["quantity_unit"], "m^3")
    return quantity_m3 / TIME_UNIT_SECONDS[metadata["time_unit"]]


def _mass_rate_to_kgps(value: float, flow_unit: str) -> float:
    metadata = FLOW_UNIT_DEFINITIONS[flow_unit]
    quantity_kg = unit_convert(value, metadata["quantity_unit"], "kg")
    return quantity_kg / TIME_UNIT_SECONDS[metadata["time_unit"]]


def _m3ps_to_output_value(value_m3ps: float, flow_unit: str) -> float:
    metadata = FLOW_UNIT_DEFINITIONS[flow_unit]
    quantity_in_unit = unit_convert(
        value_m3ps * TIME_UNIT_SECONDS[metadata["time_unit"]],
        "m^3",
        metadata["quantity_unit"],
    )
    return quantity_in_unit


def _kgps_to_output_value(value_kgps: float, flow_unit: str) -> float:
    metadata = FLOW_UNIT_DEFINITIONS[flow_unit]
    quantity_in_unit = unit_convert(
        value_kgps * TIME_UNIT_SECONDS[metadata["time_unit"]],
        "kg",
        metadata["quantity_unit"],
    )
    return quantity_in_unit


def _value_to_mass_flow(
    value: float,
    flow_unit: str,
    fluid: str,
    line_state: StatePoint,
    reference_condition: Optional[ReferenceCondition],
) -> float:
    family = flow_family(flow_unit)

    if family == "mass":
        return _mass_rate_to_kgps(value, flow_unit)

    if family == "actual_volume":
        return _volume_rate_to_m3ps(value, flow_unit) * density_at_state(fluid, line_state)

    if reference_condition is None:
        raise ValueError(f"{flow_unit} requires a reference condition.")

    return _volume_rate_to_m3ps(value, flow_unit) * density_at_state(
        fluid,
        reference_condition.as_state_point(),
    )


def _mass_flow_to_value(
    mass_flow_kgps: float,
    flow_unit: str,
    fluid: str,
    line_state: StatePoint,
    reference_condition: Optional[ReferenceCondition],
) -> float:
    family = flow_family(flow_unit)

    if family == "mass":
        return _kgps_to_output_value(mass_flow_kgps, flow_unit)

    if family == "actual_volume":
        density = density_at_state(fluid, line_state)
        return _m3ps_to_output_value(mass_flow_kgps / density, flow_unit)

    if reference_condition is None:
        raise ValueError(f"{flow_unit} requires a reference condition.")

    density = density_at_state(fluid, reference_condition.as_state_point())
    return _m3ps_to_output_value(mass_flow_kgps / density, flow_unit)


def solve_cme_flow(
    calibration_gas: str,
    measured_gas: str,
    input_value: float,
    input_unit: str,
    line_temperature_value: float,
    line_temperature_unit: str,
    line_pressure_value: float,
    line_pressure_unit: str,
    output_unit: str,
    input_reference: Optional[ReferenceCondition] = None,
    output_reference: Optional[ReferenceCondition] = None,
) -> CMEResult:
    if input_unit not in FLOW_UNIT_DEFINITIONS:
        raise ValueError(f"Unsupported input unit: {input_unit}")
    if output_unit not in FLOW_UNIT_DEFINITIONS:
        raise ValueError(f"Unsupported output unit: {output_unit}")
    if input_value < 0:
        raise ValueError("Input flow must be zero or positive.")

    line_state = build_state_point(
        temperature_value=line_temperature_value,
        temperature_unit=line_temperature_unit,
        pressure_value=line_pressure_value,
        pressure_unit=line_pressure_unit,
    )

    equivalent_mass_flow_kgps = _value_to_mass_flow(
        value=input_value,
        flow_unit=input_unit,
        fluid=calibration_gas,
        line_state=line_state,
        reference_condition=input_reference,
    )

    calibration_density_line_kgpm3 = density_at_state(calibration_gas, line_state)
    measured_density_line_kgpm3 = density_at_state(measured_gas, line_state)
    calibration_viscosity_line_pas = viscosity_at_state(calibration_gas, line_state)
    measured_viscosity_line_pas = viscosity_at_state(measured_gas, line_state)

    equivalent_actual_flow_m3ps = (
        equivalent_mass_flow_kgps / calibration_density_line_kgpm3
    )
    actual_flow_ratio = (
        calibration_viscosity_line_pas / measured_viscosity_line_pas
    )
    measured_actual_flow_m3ps = equivalent_actual_flow_m3ps * actual_flow_ratio
    measured_mass_flow_kgps = measured_actual_flow_m3ps * measured_density_line_kgpm3

    output_value = _mass_flow_to_value(
        mass_flow_kgps=measured_mass_flow_kgps,
        flow_unit=output_unit,
        fluid=measured_gas,
        line_state=line_state,
        reference_condition=output_reference,
    )

    input_reference_density_kgpm3 = None
    if input_reference is not None:
        input_reference_density_kgpm3 = density_at_state(
            calibration_gas,
            input_reference.as_state_point(),
        )

    output_reference_density_kgpm3 = None
    if output_reference is not None:
        output_reference_density_kgpm3 = density_at_state(
            measured_gas,
            output_reference.as_state_point(),
        )

    display_factor = None
    if input_value != 0:
        display_factor = output_value / input_value

    mass_flow_ratio = None
    if equivalent_mass_flow_kgps != 0:
        mass_flow_ratio = measured_mass_flow_kgps / equivalent_mass_flow_kgps

    return CMEResult(
        calibration_gas=calibration_gas,
        measured_gas=measured_gas,
        input_value=input_value,
        input_unit=input_unit,
        output_unit=output_unit,
        line_state=line_state,
        input_reference=input_reference,
        output_reference=output_reference,
        output_value=output_value,
        equivalent_mass_flow_kgps=equivalent_mass_flow_kgps,
        measured_mass_flow_kgps=measured_mass_flow_kgps,
        equivalent_actual_flow_m3ps=equivalent_actual_flow_m3ps,
        measured_actual_flow_m3ps=measured_actual_flow_m3ps,
        calibration_density_line_kgpm3=calibration_density_line_kgpm3,
        measured_density_line_kgpm3=measured_density_line_kgpm3,
        calibration_viscosity_line_pas=calibration_viscosity_line_pas,
        measured_viscosity_line_pas=measured_viscosity_line_pas,
        input_reference_density_kgpm3=input_reference_density_kgpm3,
        output_reference_density_kgpm3=output_reference_density_kgpm3,
        actual_flow_ratio=actual_flow_ratio,
        mass_flow_ratio=mass_flow_ratio,
        display_factor=display_factor,
    )
