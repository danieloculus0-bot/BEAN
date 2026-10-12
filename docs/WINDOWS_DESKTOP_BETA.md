# BEAN Windows desktop technical beta

This page covers the **Windows installer**, not a general autonomous AI release. The installation offers two tested software surfaces: an offline Core contract check using disposable fictional data, and an optional chat interface using an already-installed **local** Ollama model. Neither surface authorizes trades, changes to external software, robot motion, or cloud access.

## What the installer actually proves

The GitHub Windows installer CI compiles a self-contained Python/Tk desktop bundle with PyInstaller, executes the frozen EXE **outside the source checkout**, compiles an Inno Setup EXE, silently installs to a path containing spaces, executes the installed EXE, checks all four Core contract proofs, uninstalls the app, and generates a SHA-256 digest of the setup file.

The four contract checks are: SQLite restart continuity; conflicting host-supplied reports remain unresolved; unsupported claims and motion proposals do not acquire execution permission; missing data stays N/A instead of being silently treated as zero. They use a **mock** reasoning provider and fictional input. A separate installer gate runs two distinct **installed EXE processes** against a temporary SQLite database. One records an explicit fictional note in BEAN's canonical event journal; the second recalls the same event with the original ID and its user-asserted/unverified provenance, and verifies the JSONL audit sidecar exists. A pass is **durable memory plumbing**, not a neural learning benchmark or proof of sustained real-world operation.

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
- **Remember note:** explicitly write text from the input field to BEAN Core's per-user SQLite event journal, at `%LOCALAPPDATA%\BEAN\desktop_memory.db`. BEAN marks each saved note as a **user submission, not verified evidence**. Notes are kept locally; no Ollama or cloud connection is needed for this control.
- **Recall notes:** enter search words and retrieve matching notes from the same persistent BEAN Core journal after future launches. A miss remains a miss; BEAN does not invent a note.
- **Include matching notes in local chat (opt-in):** when explicitly selected, matching notes are supplied to the local Ollama model as **untrusted user reference data**, never as a system instruction. The checkbox defaults off. Automatic capture of conversations is still disabled.
- **Important learning limitation:** model chat history is still short-lived and not automatically saved. Durable note retrieval does **not** update model weights, establish causal superiority to ordinary retrieval, or demonstrate autonomous research.

Uninstall from Windows Apps/Installed Apps or the generated uninstaller. **Uninstall does not delete user-saved BEAN notes:** the database and audit sidecar remain under `%LOCALAPPDATA%\BEAN\`. That data is not encrypted by this technical beta. To permanently clear the desktop notes, first close BEAN, preserve any backups you need, then remove the desktop memory database and its journal/sidecar files from that user-owned directory. The GUI has no individual-note deletion control. User-configured external Ollama installations are not bundled or deleted.

## Release decisions not yet cleared

Before calling the Windows software a supported production release, independently verify it on a fresh, ordinary non-CI Windows PC; capture first-launch and restart behavior with user-owned data boundaries; test an unsigned/untrusted-binary distribution and subsequent update/rollback flow; audit dependency and artifact provenance; assign explicit licensing terms; and qualify a matched-control test of whether this persistent-memory connection improves genuine unseen work over ordinary retrieval, rather than substituting a chat façade. A successful CI install/uninstall is one gate, not completion.

Related: [Core quickstart](GETTING_STARTED.md), [production-readiness audit](PRODUCTION_READINESS_AUDIT_2026-10-11.md), and [verified backup/restore gate](BEAN_BACKUP_RELEASE_GATE_2026-10-12.md).
