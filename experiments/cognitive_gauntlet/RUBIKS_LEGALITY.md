# BEAN cube physical-state integrity

The 54 facelets must describe a reachable, fixed-center 3x3 cube. Merely
checking nine stickers of each color is insufficient: a single flipped edge,
a single twisted corner, or a swap of two edge cubies is impossible.

`rubiks3_legality.validate_legal_cube` checks the fixed centers, all eight
distinct corner identities, all twelve distinct edge identities, corner twist
sum modulo 3, edge flip sum modulo 2, and matching corner/edge permutation
parity. It uses facelet geometry only, not scramble traces or any solver.
Both BEAN-native SpongeTD inference paths reject impossible inputs before
selecting moves. The conventional reference solver and public browser
challenge remain unchanged.

The independent unit suite includes 40 legal 40-turn scrambles in all 24
whole-cube orientations (960 legal cases), plus physically impossible
states and direct policy-entry rejection tests. These checks measure **task
integrity**, not learning or new Rubik-solving success. Existing held-out
policy outcomes are unchanged; in particular the last verified full-length
20-turn result remains 0/30. Keep all failed policy cases in the existing
Gauntlet receipts. This is isolated experimental functionality.
