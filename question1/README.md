# Question 1 — Configuration Conflict Resolver

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Tests](https://img.shields.io/badge/tests-pytest-green)
![Docker](https://img.shields.io/badge/docker-supported-blue)
![Logging](https://img.shields.io/badge/logging-structured-orange)
![Status](https://img.shields.io/badge/status-production--style-success)

Production-oriented configuration conflict resolver designed for infrastructure and deployment environments.

The tool compares configuration states between environments, applies deterministic merge precedence rules, detects conflicts, generates diffs, and supports environment variable overrides.
The resolver continues execution even if one configuration source fails to load.
Failures are surfaced through structured logs and source status reporting.

The implementation focuses on:

* maintainability
* operational clarity
* deterministic behavior
* structured logging
* testability

---

# Features

* YAML configuration loading
* Recursive deep merge support
* Environment variable overrides
* Conflict detection
* Diff generation
* Sensitive value masking
* Structured JSON logging
* Dry-run support
* Unit tests with pytest
* Production-oriented project structure

---

# Project Structure

```text
question1/
├── configs/
│   ├── base.yml
│   ├── production.yml
│   └── broken.yml
│
├── lib/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── logging_utils.py
│   ├── models.py
│   └── utils.py
│
├── tests/
│   ├── __init__.py
│   └── test_config_resolver.py
│
├── __init__.py
├── config_resolver_main.py
├── DECISIONS.md
└── README.md
```

---

# Requirements

* Python 3.13
* pytest
* PyYAML

---

# Installation

Create virtual environment:

```bash
python -m venv .venv
```

Activate virtual environment:

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install pytest pyyaml
```

---

# Quick Start

```bash
pip install pytest pyyaml

python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --dry-run

```

# Running The Resolver

Example:

```bash
python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --dry-run
```
---

# Logs are written to:

```text
logs/info_YYYYMMDD.log
logs/error_YYYYMMDD.log
```

---

# CLI Demo Commands

## Basic Dry Run

Dry-run mode allows operators to safely inspect configuration differences without modifying runtime state.

```bash id="d0l8kg"
python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --dry-run
```

---

## With Environment Variable Overrides

Linux/macOS:

```bash id="k08f03"
export STAGING_SERVICE__PORT=9443
export STAGING_FEATURE_FLAGS__ENABLE_NEW_DASHBOARD=true
```

Run:

```bash id="9nn4mf"
python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --staging-env-prefix STAGING_ \
  --production-env-prefix PRODUCTION_ \
  --dry-run
```

---

## Using a Broken Configuration File

This demonstrates source failure handling and structured logging.

```bash id="vzpn71"
python -m question1.config_resolver_main \
  --staging-file question1/configs/broken.yml \
  --production-file question1/configs/production.yml \
  --dry-run
```

---

## Running Tests

Run all Question 1 tests:

```bash id="5cgqis"
pytest question1/tests -v
```

Run a single test file:

```bash id="g4k08s"
pytest question1/tests/test_config_resolver.py -v
```

---

## Running Inside Docker

Build image:

```bash id="1v95sn"
docker build -t sporty-config-resolver .
```

Run tests:

```bash id="u8bm70"
docker run --rm sporty-config-resolver
```

---

# Environment Variable Overrides

Environment variables override YAML configuration values.

Format:

```text
<PREFIX>SECTION__SUBSECTION__KEY=value
```

Example:

```bash
export PRODUCTION_SERVICE__PORT=9443
```

This overrides:

```yaml
service:
  port: 9443
```

Supported scalar conversions:

* integers
* floats
* booleans
* null values

Examples:

```bash
export STAGING_DEBUG=true
export STAGING_TIMEOUT=30
export STAGING_RATE=0.5
export STAGING_OPTION=null
```

---

# Merge Precedence

Configuration precedence order:

1. Environment variables
2. Environment-specific YAML
3. Base YAML configuration

Higher-priority sources override lower-priority values.

---

# Conflict Detection

A conflict is defined as:

> The same fully-qualified configuration path existing in both environments with different effective values.

Example conflict:

```yaml
service:
  port: 8080
```

vs

```yaml
service:
  port: 8443
```

---

# Sensitive Value Masking

Sensitive values are automatically masked in:

* effective config output
* conflicts
* diffs

Supported keywords:

* password
* secret
* token
* api_key
* private_key

Example output:

```json
{
  "database": {
    "password": "<masked>"
  }
}
```

---

# Running Tests

Run all tests:

```bash
pytest question1/tests -v
```

---

# Example Output

```json
{
  "dry_run": true,
  "summary": {
    "conflict_count": 2,
    "diff_count": 4
  },
  "conflicts": [
    {
      "path": "service.port",
      "staging_value": 8080,
      "production_value": 8443
    }
  ]
}
```

---

# Design Notes

The implementation intentionally prioritizes:

* readability
* explicit engineering tradeoffs
* deterministic behavior
* operational observability
* maintainability

rather than implementing every possible feature.

Additional architectural decisions and tradeoffs are documented in:

```text
DECISIONS.md
```

---

# Future Improvements

Potential future enhancements:

* schema validation
* remote configuration providers
* concurrent source loading
* rollback generation
* secret manager integration
* configuration versioning
* richer diff visualization

---

# Testing Focus

The tests currently validate:

* YAML loading
* recursive merging
* flattening logic
* conflict detection
* diff generation
* masking sensitive values
* failure handling
* resolver execution flow

---

# Notes

This implementation was designed to resemble a realistic internal infrastructure tool rather than a minimal algorithmic exercise.
