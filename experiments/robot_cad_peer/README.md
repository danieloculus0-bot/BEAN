# BEAN's first self-directed CAD choice

One small experiment. BEAN uses the existing verified free-model path to choose five numerical dimensions for a replaceable axle mount. A **trusted CadQuery adapter** turns BEAN's chosen dimensions into real STEP and STL. The independent [Shelbot CAD gate](https://github.com/danieloculus0-bot/BEAN-AI-Bridge-/pull/29) checks the exported physical geometry.

If the gate rejects the candidate, BEAN receives the rejection reason and gets **one more model-authored design round**. The tester and CAD template are not shown to the model, changed by the model, or run with its API credentials.

No code is installed on a robot, and no mainline mechanical design is changed. BEAN is choosing **parameters for a known part topology**, not inventing topology or full original CAD source. Mechanical constraints and material suitability still require real engineering verification.

In Core:

`python -m unittest bean.tests.test_bean_axle_cad_trial -v`

The workflow `.github/workflows/bean-autonomous-axle-cad.yml` records model-authored proposals, SHA-256 receipts, real STEP/STL artifacts, independent QA status and any revision attempt. All files remain CI artifacts, not automatically deployed hardware.
