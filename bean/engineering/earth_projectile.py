"""Exact terrestrial projectile reference for uniform gravity and linear drag.

All coordinates are locally flat (x horizontal, y vertical), with SI units.
Air resistance is -m*k*v; k is in 1/s. No wind, buoyancy, terrain,
rotation or density variation. This is a reference, not a field model.
"""
from __future__ import annotations

import math

SCHEMA = "bean.earth_projectile_reference.v1"
MAX_FLIGHT_SECONDS = 1.0e7


def _real(x, name, *, positive=False, nonnegative=False):
    if type(x) not in (int, float) or not math.isfinite(x):
        raise ValueError(f"{name} must be a finite real number")
    x = float(x)
    if positive and x <= 0 or nonnegative and x < 0:
        raise ValueError(f"{name} is outside the permitted range")
    return x


def _phi(z):
    """Stable (1-exp(-z))/z for nonnegative z."""
    if z < 1e-4:
        return 1 - z/2 + z*z/6 - z*z*z/24 + z**4/120
    return -math.expm1(-z)/z


def _psi(z):
    """Stable (1-phi(z))/z for nonnegative z."""
    if z < 1e-4:
        return 0.5 - z/6 + z*z/24 - z*z*z/120 + z**4/720
    return (1-_phi(z))/z


def solve_earth_projectile(*, launch_speed_m_s, angle_deg, initial_height_m,
                           gravity_m_s2, linear_drag_s_inv):
    speed = _real(launch_speed_m_s, "launch_speed_m_s", nonnegative=True)
    angle = _real(angle_deg, "angle_deg")
    height = _real(initial_height_m, "initial_height_m", nonnegative=True)
    g = _real(gravity_m_s2, "gravity_m_s2", positive=True)
    k = _real(linear_drag_s_inv, "linear_drag_s_inv", nonnegative=True)
    if not -90 <= angle <= 90:
        raise ValueError("angle_deg must be between -90 and 90")
    if height > 1e8 or speed > 1e6 or k > 1e6:
        raise ValueError("Inputs exceed bounded near-surface reference scope")
    rad = math.radians(angle)
    vx0, vy0 = speed * math.cos(rad), speed * math.sin(rad)

    def state(t):
        z = k*t
        phi = _phi(z)
        x = vx0 * t * phi
        y = height + vy0 * t * phi - g * t*t * _psi(z)
        decay = math.exp(-z)
        vx = vx0 * decay
        vy = vy0 * decay - g*t*phi
        if not all(math.isfinite(a) for a in (x, y, vx, vy)):
            raise ValueError("Computed trajectory is non-finite")
        return x, y, vx, vy

    if height == 0 and vy0 <= 0:
        flight = 0.0
    else:
        high = max(1.0, 2*max(vy0, 0)/g, math.sqrt(2*height/g))
        if high > MAX_FLIGHT_SECONDS:
            raise ValueError("Impact lies outside bounded simulation duration")
        while state(high)[1] > 0:
            high *= 2
            if high > MAX_FLIGHT_SECONDS:
                raise ValueError("Impact lies outside bounded simulation duration")
        low = 0.0
        for _ in range(90):
            mid = (low+high)/2
            if state(mid)[1] > 0:
                low = mid
            else:
                high = mid
        flight = (low+high)/2
    x, _, vx, vy = state(flight)
    apex_time = 0.0 if vy0 <= 0 else (math.log1p(k*vy0/g)/k if k else vy0/g)
    apex = state(apex_time)[1]
    initial_energy = speed**2/2 + g*height
    final_energy = (vx*vx+vy*vy)/2
    energy_loss = initial_energy-final_energy
    if not all(math.isfinite(a) for a in (flight, x, apex, energy_loss)):
        raise ValueError("Computed impact reference overflowed")
    return {
        "schema": SCHEMA,
        "method": "closed_form_uniform_gravity_linear_drag_bisected_impact",
        "units": {"distance":"m", "time":"s", "velocity":"m/s", "gravity":"m/s^2", "linear_drag":"1/s", "specific_energy":"m^2/s^2"},
        "flight_time_s":flight,
        "horizontal_range_m":x,
        "peak_height_m":apex,
        "peak_time_s":apex_time,
        "impact_velocity_m_s":[vx,vy],
        "specific_mechanical_energy_loss_m2_s2":energy_loss,
        "assumptions":["Locally flat ground and uniform downward gravity", "Linear isotropic drag -m*k*v", "Zero wind, no terrain, no Earth rotation and no varying air density"],
        "independently_validated":False,
        "physical_hardware_connected":False,
    }
