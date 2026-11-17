"""Independent numerical crosscheck of the analytic terrestrial projectile solver.

RK4 integrates acceleration, never the solver's closed-form trajectory.
Synthetic inputs only. This is reference correctness, not learned physics.
"""
import math
import pytest
from bean.engineering.earth_projectile import solve_earth_projectile


def numerical_impact(speed, angle, height, gravity, drag, dt):
    theta = math.radians(angle)
    state = (0.0, height, speed * math.cos(theta), speed * math.sin(theta))

    def derivative(s):
        _, _, vx, vy = s
        return vx, vy, -drag * vx, -gravity - drag * vy

    def add(s, d, scale):
        return tuple(x + scale * y for x, y in zip(s, d))

    t = 0.0
    for _ in range(math.ceil(120.0 / dt)):
        a = derivative(state)
        b = derivative(add(state, a, dt / 2))
        c = derivative(add(state, b, dt / 2))
        d = derivative(add(state, c, dt))
        nxt = tuple(x + dt * (u + 2*v + 2*w + z) / 6
                    for x, u, v, w, z in zip(state, a, b, c, d))
        if nxt[1] <= 0:
            fraction = state[1] / (state[1] - nxt[1])
            impact = tuple(x + fraction * (y - x)
                           for x, y in zip(state, nxt))
            return t + fraction * dt, impact
        state, t = nxt, t + dt
    raise AssertionError("No ground impact in bounded integration")


@pytest.mark.parametrize("speed,angle,height,gravity,drag", [
    (35.0, 28.0, 5.0, 9.80665, 0.0),
    (42.0, 55.0, 10.0, 9.80665, 0.08),
    (18.0, -20.0, 30.0, 9.81, 0.25),
    (65.0, 72.0, 2.0, 3.71, 0.015),
])
def test_rk4_convergence(speed, angle, height, gravity, drag):
    exact = solve_earth_projectile(
        launch_speed_m_s=speed, angle_deg=angle, initial_height_m=height,
        gravity_m_s2=gravity, linear_drag_s_inv=drag)
    coarse_t, coarse = numerical_impact(speed, angle, height, gravity, drag, 0.08)
    fine_t, fine = numerical_impact(speed, angle, height, gravity, drag, 0.02)
    truth_t, truth_x = exact["flight_time_s"], exact["horizontal_range_m"]
    coarse_error = math.hypot(coarse_t - truth_t, coarse[0] - truth_x)
    fine_error = math.hypot(fine_t - truth_t, fine[0] - truth_x)
    assert fine_error < coarse_error * 0.35, (coarse_error, fine_error)
    assert fine_error < 0.001, fine_error
    vx, vy = exact["impact_velocity_m_s"]
    assert math.hypot(vx - fine[2], vy - fine[3]) < 0.005
    assert exact["specific_mechanical_energy_loss_m2_s2"] >= -1e-8


def test_conservation_and_invalid_inputs():
    out = solve_earth_projectile(
        launch_speed_m_s=30, angle_deg=45, initial_height_m=10,
        gravity_m_s2=9.81, linear_drag_s_inv=0)
    assert abs(out["specific_mechanical_energy_loss_m2_s2"]) < 1e-8
    for angle, drag in [(91, 0), (45, -0.1)]:
        with pytest.raises(ValueError):
            solve_earth_projectile(
                launch_speed_m_s=30, angle_deg=angle, initial_height_m=10,
                gravity_m_s2=9.81, linear_drag_s_inv=drag)
