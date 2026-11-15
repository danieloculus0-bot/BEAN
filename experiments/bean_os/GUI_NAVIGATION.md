# BEAN OS: Real desktop navigation, first vertical slice

**Target:** BEAN can drive a real graphical desktop, not merely classify
synthetic machine state.

This experiment boots an isolated X11 window-manager session on an actual
Linux host (GitHub Actions uses Xvfb + Openbox), displays real Tk windows,
and passes a host-authorized GUI task through **BEAN's existing `GoalCycle`**.

The registered local BEAN handler uses the new `X11Desktop` adapter to:

1. Discover and focus a real desktop window by title.
2. Move the mouse to a known control using observed window geometry, and click.
3. Open an editor window, type a filename and note with OS keyboard events.
4. Save via Ctrl+S and verify the document on the isolated filesystem.
5. Switch back to the desktop, click the file manager, select a file and
   open a separate document viewer using the keyboard.
6. Capture three **real screen screenshots** and persist the BEAN Core
   goal execution receipt.

The sandbox holds only synthetic test data. This is not connected to the
user's PC or Jetson, and it does not let ChatGPT control arbitrary hosts.

## Important capability boundary

BEAN **can operate** these real GUI windows now using a predeclared
screen-navigation procedure. It does **not yet** visually identify arbitrary
buttons, discover new navigation procedures, browse arbitrary sites, or plan
free-form GUI tasks. Two known control positions are fixture-specific; the
window position and dimensions are observed at runtime, not hardcoded screen
pixels. A native accessibility tree or screenshot understanding will be
required to expand this into unscripted desktop operation.

No external LLM is required. The task is provided by a trusted local host;
the existing BEAN Core runs it through its registered goal actions and writes
its durable run record. Status 'verified' means the test reached its narrow
observable file and window objectives, not general autonomy.

## Run on a graphical Linux/X11 environment

Requires Python 3 with Tk, PyAutoGUI, `xdotool` and `scrot` installed.

```bash
python -m pip install pyautogui Pillow
python -m experiments.bean_os.navigate_gui \
  --sandbox artifacts/bean-gui-nav \
  --output artifacts/bean-gui-navigation.json
```

For a headless Linux CI environment also install Xvfb, Xauth, Openbox and
launch the command inside `xvfb-run` with Openbox running.

Evidence: `.github/workflows/bean-os-native-gui.yml`. This workflow publishes
PNG images and a BEAN Core receipt. An action is not considered complete until
GitHub CI passes its actual GUI execution.

## Next real capability

Implement generic target discovery using native accessibility APIs with
screenshot fallback, then multi-window task planning and live Linux system
tools. Wayland backends and Jetson UI integration are subsequent targets.
