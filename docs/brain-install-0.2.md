# BEAN Brain 0.2 Install Candidate

This is the no-motion brain install target for BEAN.

It installs the runtime, memory database location, service wrapper, backup/status tools, and smoke test needed to run BEAN as a swaddled cognition process on the Jetson.

## Scope

Included:

- memory database outside the repo
- runtime loop
- self/world model
- cognition core
- possibility state core
- file inbox
- manual model update command
- manual consolidation command
- manual coherence command
- status command
- SQLite backup command
- systemd service file
- install smoke test

Not included:

- servo hardware enablement
- autonomous motion
- direct LLM-to-actuator path
- sentience claims
- fake emotion claims

## Install on Jetson

From the repo root:

```bash
bash install/jetson_brain_install.sh
```

Run smoke test:

```bash
python3 bean/tests/test_brain_install.py
```

Enable and start service:

```bash
sudo systemctl enable bean.service
sudo systemctl start bean.service
sudo systemctl status bean.service
```

View logs:

```bash
journalctl -u bean.service -n 100 --no-pager
journalctl -u bean.service -f
```

## Environment

The installer creates `/etc/bean/bean.env` if it does not already exist.

Default paths:

```text
BEAN_HOME=/home/bean/BEAN
BEAN_DATA_DIR=/home/bean/bean_data
BEAN_LOG_DIR=/home/bean/bean_logs
BEAN_DB_PATH=/home/bean/bean_data/bean_memory.db
BEAN_INBOX_DIR=/home/bean/bean_data/inbox
BEAN_TICK_HZ=1.0
```

The memory database is intentionally outside the repo. Code updates must not erase BEAN's lived records.

## Operator commands

Status:

```bash
bash scripts/beanctl.sh status
```

Backup memory:

```bash
bash scripts/beanctl.sh backup
```

Run smoke test:

```bash
bash scripts/beanctl.sh test
```

Service controls:

```bash
bash scripts/beanctl.sh start
bash scripts/beanctl.sh stop
bash scripts/beanctl.sh restart
bash scripts/beanctl.sh service
bash scripts/beanctl.sh logs
bash scripts/beanctl.sh follow
```

## Runtime inbox commands

Drop commands into `$BEAN_INBOX_DIR` while the service is running:

```bash
echo '{"command":"status","from":"supervisor"}' > $BEAN_INBOX_DIR/status.json

echo '{"command":"update_models","args":{"trigger":"manual_check"},"from":"supervisor"}' > $BEAN_INBOX_DIR/update.json

echo '{"command":"run_consolidation","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/consolidate.json

echo '{"command":"run_coherence","args":{"trigger":"manual"},"from":"supervisor"}' > $BEAN_INBOX_DIR/coherence.json

echo '{"command":"shutdown","args":{"reason":"supervisor_shutdown"},"from":"supervisor"}' > $BEAN_INBOX_DIR/stop.json
```

## Smoke test proves

`bean/tests/test_brain_install.py` proves:

- temporary DB initializes
- identity bootstraps
- session begins
- self/world model updater runs
- significance weights load
- possibility states seed
- coherence runs
- consolidation runs
- file inbox processes commands
- runtime loop ticks
- clean shutdown can be recorded

## Milestone meaning

Brain 0.2 does not make BEAN alive.

It makes BEAN installable as a safe, still, memory-bearing cognition process.

The next build can leave BEAN physically swaddled while the brain stack runs:

```text
eyes open
ears open
memory running
cognition running
uncertainty preserved
no motion required
```
