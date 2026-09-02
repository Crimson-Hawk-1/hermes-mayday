# hermes-mayday — Configuration Reference

## Overview

hermes-mayday can be configured through three layers (in order of precedence):

1. **Hermes Plugin Config** (`config.yaml` or dashboard settings)
2. **Environment Variables** (`.env` file or shell exports)
3. **Defaults** (built into the plugin)

---

## Configuration Options

### `MAYDAY_ENABLED`

| Property | Value |
|---|---|
| Type | `bool` |
| Default | `true` |
| Hermes Config Key | `enabled` |

Master on/off switch. Set to `false` to completely disable Mayday without uninstalling it.

```bash
MAYDAY_ENABLED=false
```

---

### `MAYDAY_MAX_REPEATS`

| Property | Value |
|---|---|
| Type | `int` |
| Default | `3` |
| Hermes Config Key | `max_repeats` |

Number of consecutive identical actions within the rolling window before the circuit breaker trips.

- **Lower values** (e.g., `2`) catch loops faster but may trigger false positives on flaky APIs.
- **Higher values** (e.g., `5`) are more conservative but allow more wasted tokens before tripping.

```bash
MAYDAY_MAX_REPEATS=5
```

---

### `MAYDAY_WINDOW_SIZE`

| Property | Value |
|---|---|
| Type | `int` |
| Default | `10` |
| Hermes Config Key | `window_size` |

Size of the rolling action history window. Only the last N actions are retained for loop detection.

- **Smaller windows** (e.g., `5`) only catch tight, rapid loops.
- **Larger windows** (e.g., `20`) catch slower, more spread-out repetition patterns.

```bash
MAYDAY_WINDOW_SIZE=20
```

---

### `MAYDAY_HALT_MODE`

| Property | Value |
|---|---|
| Type | `str` |
| Default | `"hard"` |
| Options | `"hard"`, `"soft"` |
| Hermes Config Key | `halt_mode` |

Controls what happens when the circuit breaker trips:

- **`hard`** — Returns a `{"action": "block"}` directive to Hermes, halting execution immediately. A crash report is generated.
- **`soft`** — Logs a loud warning and generates a crash report, but allows the agent to continue executing.

```bash
MAYDAY_HALT_MODE=soft
```

---

### `MAYDAY_REPORT_DIR`

| Property | Value |
|---|---|
| Type | `str` |
| Default | `"./"` |
| Hermes Config Key | `report_dir` |

Directory where `mayday-crash-report-*.md` files are saved. Relative paths are resolved from the current working directory. Falls back to `$HERMES_HOME` if set.

```bash
MAYDAY_REPORT_DIR=/home/user/mayday-reports
```

---

### `MAYDAY_VOLATILE_KEYS`

| Property | Value |
|---|---|
| Type | `str` (comma-separated) |
| Default | `"timestamp,request_id,trace_id,created_at,updated_at"` |
| Hermes Config Key | `volatile_keys` |

Argument keys to strip from tool call arguments before hashing. This prevents false negatives where two logically identical actions produce different hashes because of embedded metadata like timestamps or request IDs.

```bash
MAYDAY_VOLATILE_KEYS=timestamp,request_id,trace_id,nonce,session_id
```

---

## Example `.env` File

```bash
# hermes-mayday configuration
MAYDAY_ENABLED=true
MAYDAY_MAX_REPEATS=3
MAYDAY_WINDOW_SIZE=10
MAYDAY_HALT_MODE=hard
MAYDAY_REPORT_DIR=./
MAYDAY_VOLATILE_KEYS=timestamp,request_id,trace_id,created_at,updated_at
```

## Example Hermes `config.yaml` Plugin Settings

```yaml
plugins:
  entries:
    hermes-mayday:
      enabled: true
      settings:
        enabled: true
        max_repeats: 3
        window_size: 10
        halt_mode: hard
        report_dir: ./
        volatile_keys:
          - timestamp
          - request_id
          - trace_id
```
