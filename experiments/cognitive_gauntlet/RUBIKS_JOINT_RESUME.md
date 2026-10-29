# Frozen BEAN joint-cube checkpoint continuation

Earlier joint-rescue experiments paused many attempts after one compute slice.
A pause is not a definitive failure. This isolated experiment verifies the
original SHA-256 receipt, rebuilds identical full-state and 96-pair SpongeTD
Q tables, checks exact digests and TD update counts, then resumes only paused
cases with the existing BEAN-native controller. No solver, inverse scramble
or search fallback supplies answers. Learned weights remain frozen.

Each continuation records the original scramble and route, every additional
legal move sequence, status, failure or pause, checkpoint and independent
replay. The source receipt remains untouched. Slices bound compute per run,
not the total permitted number of solution moves.

Run:
    python -m unittest bean.tests.test_cognitive_rubiks_joint_resume -v
    python -m experiments.cognitive_gauntlet.rubiks3_joint_rescue --rescue-backup --test-seed-start 31000 --test-count 3 --work-budget 16 --output cognitive-gauntlet-results/joint-original-31000.json
    python -m experiments.cognitive_gauntlet.rubiks3_joint_resume --source cognitive-gauntlet-results/joint-original-31000.json --output cognitive-gauntlet-results/joint-resume-31000.json --slices 2 --work-budget 32
    python -m experiments.cognitive_gauntlet.rubiks3_joint_resume --verify --source cognitive-gauntlet-results/joint-original-31000.json --output cognitive-gauntlet-results/joint-resume-31000.json

Independent cohorts 31000-31002 and 32000-32002, scramble lengths 3, 4, 5,
6, 20, retain all rotation-class exclusions. This is a frozen learned-policy
continuation, not weight learning, universal cube solving or shortest HTM proof.
Only verified unseen full 20-turn success warrants the requested notification.
