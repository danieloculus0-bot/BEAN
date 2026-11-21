# BEAN 3D Studio

**Status:** Working dependency-free browser parametric geometry generator with STL/OBJ exports. Optional TripoSR adapter implemented for local image-to-3D. GPU inference is not CI-tested and is NOT available directly on GitHub Pages.

## Open the browser-only studio

Visit https://danieloculus0-bot.github.io/BEAN/bean-3d/ after merge and Pages deployment, or serve the HTML locally. Select **Woven coaster** or **Simple ring**, change dimensions, orbit the preview, and download a mesh for Bambu Studio. Every procedural operation is offline, local and free. STL coordinates are millimeters (binary STL itself does not formally declare units).

The coaster is a **single solid** with a raised continuous over-under weave approximation, not floating intersecting ropes. There is no multi-color AMS purge. The generated pattern is geometric, not an image heightmap. Physical print fidelity remains to be verified.

The "Design description" input only recognizes a few constrained preset words. It is **not** an LLM or general text-to-3D network.

## Enable real AI image-to-3D (optional, free local engine)

The backend calls the **actual upstream [TripoSR](https://github.com/VAST-AI-Research/TripoSR)** inference script, not a simulated mesh. TripoSR source and weights are MIT licensed. It is not copied into BEAN. Upstream reports about **6 GB GPU VRAM** for a single image; actual requirements depend on CUDA/PyTorch. GitHub Pages and standard CPU GitHub Actions runners cannot perform GPU inference.

Setup from a machine with compatible PyTorch/CUDA:

1. Clone BEAN and the upstream TripoSR separately.
2. Set up TripoSR using its own upstream README (install PyTorch appropriate to your GPU first, then its requirements.txt; original sources and weights remain upstream).
3. Point the BEAN bridge to your installed TripoSR and its Python interpreter.

Windows PowerShell example (paths reflect the actual installation, including the virtual environment):

    git clone https://github.com/VAST-AI-Research/TripoSR.git
    # Install PyTorch and TripoSR dependencies per the upstream README.
    $env:TRIPOSR_DIR = (Resolve-Path .\TripoSR).Path
    $env:TRIPOSR_PYTHON = (Resolve-Path .\TripoSR\.venv\Scripts\python.exe).Path
    # From the BEAN repository root:
    python -m bean.studio3d.server

If you installed TripoSR into the same Python environment as BEAN, omit TRIPOSR_PYTHON.

Navigate to **http://127.0.0.1:8768/**. The local server serves the same Studio interface. Use **Image to 3D** to upload a PNG/JPEG of an isolated object, specify the longest desired size in mm, and download STL. The model is loaded by TripoSR, not by the public webpage. Images are processed within a temporary directory and deleted when the request ends. The server binds **127.0.0.1 only**, does not require an API key, and does not upload images to third-party services itself. Upstream model downloads and setup may contact Hugging Face as documented by TripoSR.

### Technical interfaces

- GET /health reports service readiness and presence of TRIPOSR_DIR/run.py. It does **not** guarantee weights, CUDA, dependencies or successful inference.
- POST /api/image-to-3d accepts JSON with an image field containing a base64 PNG/JPEG data URL, and size_mm specifying a 10-500 mm longest dimension. Max input image 8 MB decoded.
- TripoSR run.py saves output/0/mesh.obj. The adapter converts this mesh to binary STL after scaling its longest axis to the desired dimension, centering XY and rebasing its minimum Z to zero. It is not calibrated physical reconstruction.
- docs/bean-3d/mesh.mjs generates offline meshes and exports STL/OBJ with a native WebGL preview.
- Run tests from the BEAN repo root: node --test docs/bean-3d/mesh.test.mjs ; python -m unittest discover -s tests -p test_studio3d.py -v

### Limitations

TripoSR performs **single-image inference**, not arbitrary text-to-mesh. True text-to-3D would require a separate text-to-image stage followed by TripoSR. Imported models may be open/non-manifold and need slicer mesh repair or printing orientation adjustment. The optional bridge returns untextured STL; PBR texture is not implemented. No paid generative API is required.

## Attribution

Model: [Tripo AI + Stability AI, TripoSR](https://github.com/VAST-AI-Research/TripoSR), MIT. BEAN owns the independent UI, deterministic geometry module, and local bridge. Upstream model weights are not redistributed here. **BEAN's repository does not currently declare a global open-source license.** The upstream MIT license does not license unrelated BEAN source code.
