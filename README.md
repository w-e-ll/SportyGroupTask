# Sporty Group — Senior Python Engineer Take-Home Assessment

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Tests](https://img.shields.io/badge/pytest-tested-green)
![Docker](https://img.shields.io/badge/Docker-supported-2496ED)

This repository contains solutions for both take-home assessment questions.

The implementation focuses on:

* production-oriented engineering decisions
* maintainability
* operational clarity
* structured logging
* explicit tradeoff documentation
* testability

Structured logs are written into the `logs/` directory and split by severity level.

---

# Production Notes

The implementations intentionally emphasize:

- deterministic behavior
- operational observability
- explicit error handling
- structured logging
- maintainable project structure
- realistic backend engineering tradeoffs

over algorithmic minimalism.

---

# Quick Start

Run all tests:

```bash
pytest -v
```

Run Question 1:

```bash
python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --dry-run
```

Run Question 2:

```bash
python -m question2.executor_main
```

---

# Repository Structure

```text
.
├── question1/
│   ├── configs/
│   ├── lib/
│   ├── tests/
│   ├── config_resolver_main.py
│   ├── DECISIONS.md
│   └── README.md
│
├── question2/
│   ├── lib/
│   ├── tests/
│   ├── executor_main.py
│   ├── DECISIONS.md
│   └── README.md
│
├── Dockerfile
├── CHANGELOG.md
├── VERSION.txt
├── pyproject.toml
└── README.md
```

---

# Python Version

The solutions were implemented and tested using:

```text
Python 3.13
```

---

# Setup

## 1. Create Virtual Environment

```bash
python -m venv .venv
```

Activate:

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows:

```powershell
.venv\Scripts\activate
```

---

## 2. Install Dependencies

Using pip:

```bash
pip install -U pip
pip install pytest pyyaml
```

Or using pyproject.toml:

```bash
pip install .
```

---

# Running Tests

Run all tests:

```bash
pytest -v
```

Run Question 1 tests only:

```bash
pytest question1/tests -v
```

Run Question 2 tests only:

```bash
pytest question2/tests -v
```

---

# Question 1 — Configuration Conflict Resolver

Detailed documentation:

```text
question1/README.md
```

Run example:

```bash
python -m question1.config_resolver_main \
  --staging-file question1/configs/base.yml \
  --production-file question1/configs/production.yml \
  --dry-run
```

Example environment override:

Linux/macOS:

```bash
export PRODUCTION_SERVICE__PORT=9443
```

Windows PowerShell:

```powershell
$env:PRODUCTION_SERVICE__PORT=9443
```

---

# Question 2 — Task Executor

Detailed documentation:

```text
question2/README.md
```

Run example:

```bash
python -m question2.executor_main
```

---

# Design Documentation

Each question includes:

* implementation
* tests
* README
* DECISIONS.md

The DECISIONS.md files explicitly document:

* engineering tradeoffs
* operational considerations
* limitations
* future improvements
* alternatives considered

---

# Docker Support

Optional Docker support is included.

Build:

```bash
docker build -t sporty-group-task .
```

Run:

```bash
docker run --rm sporty-group-task
```

---

# Notes

The implementations intentionally prioritize:

* deterministic behavior
* operational safety
* maintainability
* observability
* realistic production tradeoffs

rather than maximum feature completeness.

The goal was to implement solutions similar to internal infrastructure tooling and operational backend systems rather than purely academic exercises.
