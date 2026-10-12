# BEAN Windows desktop technical beta

This page covers the **Windows installer**, not a general autonomous AI release. The installation offers two tested software surfaces: an offline Core contract check using disposable fictional data, and an optional chat interface using an already-installed **local** Ollama model. Neither surface authorizes trades, changes to external software, robot motion, or cloud access.

## What the installer actually proves

The GitHub Windows installer CI compiles a self-contained Python/Tk desktop bundle with PyInstaller, executes the frozen EXE **outside the source checkout**, compiles an Inno Setup EXE, silently installs to a path containing spaces, executes the installed EXE, checks all four Core contract proofs, uninstalls the app, and generates a SHA-256 digest of the setup file.

The four contract checks are: SQLite restart continuity; conflicting host-supplied reports remain unresolved; unsupported claims and motion proposals do not acquire execution permission; missing data stays N/A instead of being silently treated as zero. They use a **mock** reasoning provider and fictional input. A pass is not a neural learning benchmark or proof of sustained real-world operation.

## Get the candidate installer

Open the [Windows installer Actions runs](https://github.com/danieloculus0-bot/BEAN/actions/workflows/windows-installer.yml). Select a **successful run for the intended commit**, then download the `BEAN-Windows-Installer` artifact. It contains `BEAN-Setup.exe` and `BEAN-Setup.exe.sha256`. The workflow's own file hashes are not independently signed provenance.

To verify the two files after extraction, run in PowerShell:

```powershell
(Get-FileHash .\BEAN-Setup.exe -Algorithm SHA256).Hash.ToLower()
Get-Content .\BEAN-Setup.exe.sha256
```

Compare the two hashes. Do not run an installer if they differ. The current binary is **not code-signed**, so Windows publisher identity has not been cryptographically established. Windows may show an unsigned-app warning. The GitHub build itself is a technical-beta candidate, not a general public production certification.

## First launch

Double-click the installer. It is configured as a per-user installation and offers a BEAN desktop shortcut. The program does not require a Python installation on the target computer.

- **Verify BEAN Core:** runs the offline proof against disposable data. It does not use the user's business records, model API credentials, wallets, or existing BEAN deployment.
- **Connect local Ollama:** connects only to an Ollama instance already running at `127.0.0.1:11434` and uses a locally installed model. This interface makes no attempt to configure or download Ollama and provides no trading or hardware controls.
- **Important chat limitation:** chat history is short-lived, in-process context and is **not automatically written to BEAN Core's SQLite memory**. Installing the desktop beta does not provide AI learning transfer, persistent conversation memory, or autonomous research.

Uninstall from Windows Apps/Installed Apps or the generated uninstaller. User-configured external Ollama installations are not bundled or deleted.

## Release decisions not yet cleared

Before calling the Windows software a supported production release, independently verify it on a fresh, ordinary non-CI Windows PC; capture first-launch and restart behavior with user-owned data boundaries; test an unsigned/untrusted-binary distribution and subsequent update/rollback flow; audit dependency and artifact provenance; assign explicit licensing terms; and qualify a real persistent-memory connection rather than substituting a chat façade. A successful CI install/uninstall is one gate, not completion.

Related: [Core quickstart](GETTING_STARTED.md), [production-readiness audit](PRODUCTION_READINESS_AUDIT_2026-10-11.md), and [verified backup/restore gate](BEAN_BACKUP_RELEASE_GATE_2026-10-12.md).
