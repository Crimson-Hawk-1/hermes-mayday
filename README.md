# 🚨 hermes-mayday

<p align="center">
  <img src="images/terminal-alert-demo.jpg" alt="Mayday Mayday Mayday — Stop runaway AI agents" width="700">
</p>

**Stop runaway agents. Save your API tokens.**

🎵 [Listen to the official theme song](https://www.youtube.com/watch?v=DT61L8hbbJ4&list=RDDT61L8hbbJ4&start_radio=1)

A circuit breaker plugin for [Hermes Agent](https://github.com/NousResearch/hermes-agent) that detects infinite tool loops and halts execution before your agent burns through your API credits.

---

## The Problem

When autonomous agents get stuck, they don't crash gracefully — they **loop**. They retry the same failing API call 50 times in a row, burning tokens and time while you're not watching. By the time you notice, the damage is done.

**hermes-mayday** sits on the `pre_tool_call` hook and watches every tool invocation. When it detects the same action repeating, it pulls the emergency brake.

---

## Quick Start

### Install

```bash
pip install git+https://github.com/Crimson-Hawk-1/hermes-mayday.git
```

For pretty terminal output with colors and panels:

```bash
pip install "hermes-mayday[pretty] @ git+https://github.com/Crimson-Hawk-1/hermes-mayday.git"
```

### Enable

Add to your `.env` file (or Hermes `config.yaml`):

```bash
MAYDAY_ENABLED=true
```

That's it. Hermes will auto-discover the plugin via Python entry points.

### Verify

```bash
hermes plugins list
# Should show: hermes-mayday (v0.1.0) ✓
```

---

## How It Works

1. **Intercept** — Mayday registers on Hermes' `pre_tool_call` hook
2. **Hash** — Every tool call is hashed (with volatile keys like timestamps stripped out)
3. **Track** — Hashes are stored in a rolling window of the last N actions
4. **Detect** — If the same hash appears 3+ times in the window → **MAYDAY**
5. **Halt** — Execution is blocked and a forensic crash report is generated

```
Agent Loop                     hermes-mayday
    │                               │
    ├── LLM selects tool ──────────►│ Hash action
    │                               │ Check window
    │◄── Allow (None) ─────────────│ Not a loop ✓
    │                               │
    ├── LLM selects SAME tool ────►│ Hash action
    │                               │ Check window
    │◄── Allow (None) ─────────────│ 2/3 repeats ⚠️
    │                               │
    ├── LLM selects SAME tool ────►│ Hash action
    │                               │ Check window
    │◄── BLOCK 🚨 ─────────────────│ 3/3 = TRIPPED!
    │                               │ └── crash report saved
    └── Execution halted            │
```

---

## Configuration

All settings are configurable via environment variables or Hermes plugin config:

| Variable | Default | Description |
|---|---|---|
| `MAYDAY_ENABLED` | `true` | Master on/off switch |
| `MAYDAY_MAX_REPEATS` | `3` | Repeats before tripping |
| `MAYDAY_WINDOW_SIZE` | `10` | Rolling action history size |
| `MAYDAY_HALT_MODE` | `hard` | `hard` = block, `soft` = warn only |
| `MAYDAY_REPORT_DIR` | `./` | Where crash reports are saved |
| `MAYDAY_VOLATILE_KEYS` | `timestamp,request_id,...` | Keys stripped before hashing |

See [docs/configuration.md](docs/configuration.md) for the full reference.

---

## Crash Reports

When the circuit breaker trips, Mayday generates a forensic `mayday-crash-report-*.md` file containing:

- The exact tool and arguments that were looping
- The full action history from the rolling window
- Circuit breaker diagnostics (total calls, warnings, trips)
- Actionable next steps for debugging

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for diagrams showing how Mayday integrates with the Hermes execution loop.

---

## Development

### Setup

```bash
# Clone the repo
git clone https://github.com/your-username/hermes-mayday.git
cd hermes-mayday

# Create a virtual environment
python -m venv .venv

# Activate it
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
python -m pytest
```

### Project Structure

```
hermes-mayday/
├── src/
│   └── hermes_mayday/
│       ├── __init__.py          # Plugin entry point (register hook)
│       ├── circuit_breaker.py   # Core loop detection engine
│       ├── config.py            # Configuration loader
│       ├── crash_report.py      # Forensic report generator
│       └── display.py           # Terminal output (rich/fallback)
├── tests/
│   ├── conftest.py              # Shared fixtures
│   ├── test_circuit_breaker.py  # Loop detection tests
│   ├── test_config.py           # Config loading tests
│   └── test_crash_report.py     # Report generation tests
├── docs/
│   ├── architecture.md          # Architecture diagrams
│   └── configuration.md         # Config reference
├── plugin.yaml                  # Hermes plugin manifest
├── pyproject.toml               # Build config
├── LICENSE                      # MIT
└── README.md                    # This file
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, code style, and contribution guidelines.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Roadmap

- [ ] **v0.2** — Semantic drift detection (markdown state diffing)
- [ ] **v0.3** — Messaging gateway alerts (Telegram/Slack via Hermes)
- [ ] **v0.4** — Token budget tracking
- [ ] **v0.5** — Hermes WebUI dashboard integration
