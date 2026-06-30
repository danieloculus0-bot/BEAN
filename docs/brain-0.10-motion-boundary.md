# Brain 0.10 - Motion Boundary

Brain 0.10 is intentionally treated as a boundary in this recovery branch.

The repo already contains body registry, motion command vocabulary, simulator-oriented safety checks, and teaching-related motion structures from earlier work. This branch does not add physical hardware motion execution.

## Recovery-branch decision

Physical motion, Pi servo daemon work, GPIO, RPi, pigpio, serial drivers, and actuator execution are out of scope for this branch.

## Safe rule

Reasoning and speculation may produce proposed records only. They must not execute motion.

## Required future work before real motion

- Separate Pi-side or microcontroller-side motion daemon.
- Hardware E-stop.
- Deadman timeout.
- Physical current and limit protection.
- Supervisor-reviewed motion enablement.
- Test fixture before body installation.

## Current invariant

Runtime proof must continue to report:

- `motion_enabled=False`
- no hardware motion driver invoked
- no direct LLM-to-actuator path
