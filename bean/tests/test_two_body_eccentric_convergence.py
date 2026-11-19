"""Independent eccentric-orbit convergence acceptance, not a learning benchmark.

Synthetic Earth-centered inertial state. Equal physical duration, fixed-step
velocity Verlet at three resolutions. Kepler energy and angular momentum are
independent analytic references; the finest numerical trajectory is a
convergence reference, not ground truth or an ephemeris.
"""
import math

from bean.engineering.two_body import propagate_two_body


def test_eccentric_orbit_refinement_and_analytic_invariants():
    mu = 398600.435507  # km^3/s^2, public JPL Earth-system GM
    rp = 7000.0  # km, periapsis, above physical mean Earth radius
    eccentricity = 0.3
    semimajor = rp / (1.0 - eccentricity)
    vp = math.sqrt(mu * (2.0 / rp - 1.0 / semimajor))
    specific_energy = -mu / (2.0 * semimajor)
    specific_h = rp * vp
    duration = 8000.0  # s, identical across resolutions

    def run(dt):
        return propagate_two_body(
            mu_km3_s2=mu, minimum_radius_km=6371.0084,
            position_km=[rp, 0.0, 0.0], velocity_km_s=[0.0, vp, 0.0],
            step_seconds=dt, steps=int(duration / dt),
        )

    coarse, medium, fine = (run(dt) for dt in (20.0, 10.0, 5.0))
    for result in (coarse, medium, fine):
        conic = result["initial_conic_reference"]
        assert conic["classification"] == "bound"
        assert math.isclose(conic["eccentricity"], eccentricity, abs_tol=1e-12)
        assert math.isclose(conic["semimajor_axis_km"], semimajor, rel_tol=1e-12)
        assert math.isclose(result["initial_specific_energy_km2_s2"],
                            specific_energy, rel_tol=1e-12)
        assert math.isclose(result["initial_specific_angular_momentum_km2_s"][2],
                            specific_h, rel_tol=1e-12)
        assert result["max_scaled_angular_momentum_vector_drift"] < 1e-10

    def separation(a, b):
        return math.dist(a["final_position_km"], b["final_position_km"])

    coarse_medium = separation(coarse, medium)
    medium_fine = separation(medium, fine)
    assert medium_fine > 0.0
    # Second-order global convergence: refinement by two approaches 4x.
    # Broad 3x threshold avoids treating floating-point details as physics.
    assert coarse_medium / medium_fine > 3.0
    assert fine["max_scaled_specific_energy_drift"] < coarse["max_scaled_specific_energy_drift"]
    assert fine["max_scaled_specific_energy_drift"] < 1e-4


def test_eccentric_orbit_direction_changes_state_not_energy():
    mu = 398600.435507
    rp = 7000.0
    vp = math.sqrt(mu * (2.0 / rp - 1.0 / 10000.0))
    args = dict(mu_km3_s2=mu, minimum_radius_km=6371.0084,
                position_km=[rp, 0.0, 0.0], step_seconds=10.0, steps=100)
    prograde = propagate_two_body(velocity_km_s=[0.0, vp, 0.0], **args)
    retrograde = propagate_two_body(velocity_km_s=[0.0, -vp, 0.0], **args)
    assert math.isclose(prograde["initial_specific_energy_km2_s2"],
                        retrograde["initial_specific_energy_km2_s2"], abs_tol=1e-12)
    assert prograde["final_position_km"][1] > 0.0
    assert retrograde["final_position_km"][1] < 0.0
    assert math.isclose(prograde["final_position_km"][0],
                        retrograde["final_position_km"][0], abs_tol=1e-9)
    assert prograde["initial_specific_angular_momentum_km2_s"][2] > 0
    assert retrograde["initial_specific_angular_momentum_km2_s"][2] < 0
