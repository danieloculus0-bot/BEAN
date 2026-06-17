# BEAN Memory Core 0.1 - Structured Package

This package is the Claude-provided BEAN memory core arranged into the folder layout its imports expect.

## Layout

- `bean/memory/` - SQLite store, identity, session, event logging
- `bean/reflection/` - grounded reflection pass
- `bean/runtime/` - runtime bootstrap and shutdown handling
- `bean/schemas/` - SQLite schema
- `bean/tests/` - pytest test suite

## Test

From this folder:

```bash
python -m pytest bean/tests/test_memory_core.py -v
```

Verified in sandbox: 29 tests passed.

## Notes

The original upload had the source files flat in the zip. The code itself expects a package layout like `bean/memory/store.py`, `bean/reflection/reflect.py`, etc.
