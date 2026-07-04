# BEAN OS Reformat and First-Boot Checklist

Purpose: get the Jetson back to a known-good BEAN brain state after a fresh OS install.

This checklist keeps memory outside the repo and verifies the brain stack before enabling the service.

## 1. Clone and enter repo

```bash
git clone https://github.com/danieloculus0-bot/BEAN.git /home/bean/BEAN
cd /home/bean/BEAN
```

## 2. Install BEAN brain files

```bash
bash install/jetson_brain_install.sh
```

The installer creates:

```text
/etc/bean/bean.env
/home/bean/bean_data
/home/bean/bean_data/inbox
/home/bean/bean_logs
/etc/systemd/system/bean.service
```

It does not enable real motion hardware.

## 3. Confirm environment

```bash
cat /etc/bean/bean.env
```

Expected paths:

```text
BEAN_HOME=/home/bean/BEAN
BEAN_DATA_DIR=/home/bean/bean_data
BEAN_LOG_DIR=/home/bean/bean_logs
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
```

## 4. Temp-DB boot check

This proves imports and schema initialization without touching the real memory DB.

```bash
bash scripts/bean_boot_ready.sh --temp
```

Required result:

```text
"success": true
"motion_enabled": false
```

## 5. Real-DB boot check

This initializes and validates the configured memory DB.

```bash
source /etc/bean/bean.env
bash scripts/bean_boot_ready.sh --db "$BEAN_DB_PATH"
```

Required result:

```text
"success": true
"motion_enabled": false
```

## 6. Smoke tests

```bash
bash scripts/run_brain_smoke_tests.sh
```

Fix failures before starting the service.

## 7. Start service

```bash
sudo systemctl enable bean.service
sudo systemctl start bean.service
sudo systemctl status bean.service
```

Follow logs:

```bash
journalctl -u bean.service -f
```

## 8. Runtime proof command

```bash
echo '{"command":"run_runtime_proof","from":"supervisor"}' > "$BEAN_INBOX_DIR/runtime_proof.json"
```

Then inspect logs or DB events.

## Safety posture

- Motion remains disabled.
- Real servo hardware is not enabled by install.
- The LLM is a reasoning tool, not BEAN identity.
- Speculation remains reviewable hypothesis records, not facts.
- Memory lives outside the repo.

## Reformat rule

Before wiping the Jetson again, copy or back up:

```text
/home/bean/bean_data/bean_memory.db
/home/bean/bean_data/inbox
/home/bean/bean_logs
/etc/bean/bean.env
```
