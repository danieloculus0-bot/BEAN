# Jetson Orin Nano Super ISO installation gate (BEAN research handoff)

**Status: pre-hardware readiness work, NOT booted or validated on a Jetson.**
This guide is for the model recorded in [BEAN hardware inventory](hardware-inventory.md):
**NVIDIA Jetson Orin Nano Super Developer Kit**. It does not apply to the
original Jetson Nano.

## 0. Never flash the venvWin amd64 ISO onto Jetson

The current [venvWin Portable build](https://github.com/danieloculus0-bot/venvWin/blob/main/venvwin-portable/build-iso.sh)
uses `--architectures amd64` and Debian's x86_64 kernel. It is a separate PC
test product, not a Jetson boot image. BEAN's first Jetson deployment will use
NVIDIA's Jetson Linux BSP as the base OS. Do not represent Core tests or
desktop QEMU results as a successful Jetson boot.

## 1. OEM Jetson ISO handoff, before installing BEAN

Source of truth: NVIDIA's [Orin Nano Quick Start](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/quick_start.html),
[firmware update path](https://docs.nvidia.com/jetson/orin-nano-devkit/user-guide/latest/update_firmware.html)
and [JetPack releases](https://developer.nvidia.com/embedded/jetpack/downloads).

- Verify board identity and NVIDIA UEFI/QSPI firmware first. Older factory
  firmware needs the NVIDIA JetPack 6.x update path **before** using the 7.2.1 ISO.
- The JetPack 7.2.1 / L4T r39.2.1 **Jetson ISO** is written to a USB
  installer stick (16 GB or larger); it is not a desktop live USB and is
  **not** written directly onto the target microSD card.
- Provide separate target storage: microSD (64 GB UHS-1 or larger recommended)
  or NVMe SSD, and the supported 19V power supply.
- Use the manufacturer's installer to select target storage. Installing
  Jetson Linux erases the selected destination. Record the chosen device.
- Finish Ubuntu's first-boot setup, including user, networking, and storage.
  Collect the Jetson version, device-tree model, UEFI version, target disk,
  USB install boot result and power/reboot evidence in a private test report.

No repo command in this document flashes a card, alters firmware, starts
motors, or manufactures NVIDIA's proprietary install media.

## 2. Existing BEAN installer prerequisites

The current [Jetson installer](../install/jetson_brain_install.sh) and
[service template](../install/bean.service) expect an existing `bean` user,
repository checkout at `/home/bean/BEAN`, systemd, Python 3.10+, a functioning
`python3 -m venv`, and pip. The installer **does not create the service user**
and its static service file **does not support overridden BEAN_HOME/BEAN_USER
values**. The experimental installer now rejects those overrides up front
instead of silently leaving a mismatched service, and provisions venv and data
as the service account. A pre-existing account and checkout are still required.

Install packages appropriate to the confirmed JetPack release first. On a
fresh developer kit, provision the expected dedicated user/checkout (do not
run the BEAN runtime as root):

```bash
sudo useradd --create-home --user-group --shell /bin/bash bean
sudo -u bean -H git clone https://github.com/danieloculus0-bot/BEAN.git /home/bean/BEAN
```

Use these commands only if the account/checkout do not already exist, and
confirm group ownership and repository contents. The operator executing the
installer must have sudo rights; the `bean` runtime user does not need sudo.
Run the read-only gate **before** the installer:

```bash
cd /home/bean/BEAN
python3 install/jetson_deployment_gate.py --report /tmp/bean-jetson-gate.json
```

`status=READY_FOR_BEAN_INSTALL` means only that observed post-install
prerequisites and static path contracts match. On a fresh image with no
`bean` account, `service_user_exists` fails explicitly. Repair the account
and checkout arrangement rather than overriding the gate. This check may
return `BLOCKED` legitimately until the system is provisioned.

**Interpretation:** this gate does not prove USB boot, UEFI compatibility,
an ISO's checksum, live hardware functionality, motor safety, or persistent
BEAN learning. Its false/unknown fields stay false until verified elsewhere.

For Python older than 3.10, obtain a supported interpreter before running
BEAN; do not claim compatibility from an installer error or a syntax error.

## 3. Functional smoke tests, after platform gate

Use the existing Core tests and tools without reimplementing the brain:

```bash
python3 -m pip install psutil pytest
python3 -m bean.runtime.boot_readiness --temp
python3 -m examples.restart_continuity
python3 -m pytest bean/tests/test_brain_install.py -q
```

Only after the platform gate, temporary boot tests and service prerequisites
succeed, use the current installer from the repository root and verify the
actual installed service:

```bash
bash install/jetson_brain_install.sh
sudo systemctl status bean.service --no-pager
sudo systemctl cat bean.service
sudo journalctl -u bean.service -n 100 --no-pager
```

Record reboot recovery with the **same** persistent database, check that
the source event is retrieved unchanged, and exercise the provided backup
and restore verification. Verify disk writes, idle RAM/CPU, thermal behavior,
network independence, logs and restart behavior on actual hardware. A
single successful boot is not an endurance test.

## 4. Go/no-go definitions

- **Software-only preflight:** synthetic tests for model/architecture/paths
  pass; no hardware acceptance is implied.
- **Jetson BSP boot:** real device boots NVIDIA's ISO installer, installs
  Jetson Linux and cold boots from target storage. Capture exact firmware,
  board, storage and OS versions.
- **BEAN boot:** service starts and restarts on the Jetson; source events,
  SQLite identity and backup remain intact; mock reasoning doesn't produce
  motor commands; original failures remain in the ledger.
- **Hardware interface test:** identify and test camera, microphone,
  motor-controller transport and feedback independently with measured
  receipts. This is **not** part of the first brain-only installation.
- **Release:** blocked until real Orin Nano evidence, power cycle/restart
  continuity, service-account/path remediation, version reproducibility and
  rollback/restore checks exist.

Research/learning branches, hosted @BEAN notes, venvWin amd64 builds and
Core `main` all remain separate until their exact integration is tested.
