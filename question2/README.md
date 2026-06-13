# Question 2 — Task Executor Framework

![Python](https://img.shields.io/badge/Python-3.13-blue)
![Pytest](https://img.shields.io/badge/Tested_with-pytest-green)
![Docker](https://img.shields.io/badge/Container-Docker-blue)
![Logging](https://img.shields.io/badge/Logging-Structured-orange)
![Retries](https://img.shields.io/badge/Retry-Exponential_Backoff-yellow)
![Status](https://img.shields.io/badge/Production_Style-Yes-success)

A production-style extensible task execution framework implemented in Python 3.13.

This project demonstrates:

* clean architecture
* extensible task registry
* retries with exponential backoff
* timeout handling
* structured logging
* strong validation
* production-oriented observability
* isolated task execution
* detailed test coverage

---

# Project Structure

```text
question2/
│
├── lib/
│   ├── __init__.py
│   ├── exceptions.py
│   ├── logging_utils.py
│   ├── models.py
│   ├── registry.py
│   └── tasks.py
│
├── tests/
│   ├── __init__.py
│   └── test_executor.py
│
├── __init__.py
├── executor_main.py
├── DECISIONS.md
└── README.md
```

---

# Main Concepts

The framework executes tasks using a common execution engine.

Each task:

* has validation
* supports retries
* supports timeout protection
* returns structured results
* logs every important step

The executor is intentionally extensible so new task types can be added without changing executor logic.

---

# Supported Tasks

## 1. FileExistsTask

Checks if a file exists on disk.

Example:

```python
TaskConfig(
    task_id="check-config",
    task_type="file_exists",
    target="/tmp/config.yml",
)
```

---

## 2. HttpCheckTask

Performs an HTTP request and validates response status.

Example:

```python
TaskConfig(
    task_id="health-check",
    task_type="http_check",
    target="https://www.python.org",
    params={
        "method": "GET",
        "expected_status": 200,
    },
)
```

---

## 3. SleepTask

Simulates long-running work.

Useful for timeout and retry testing.

Example:

```python
TaskConfig(
    task_id="slow-task",
    task_type="sleep",
    target="local",
    params={
        "duration_seconds": 5,
    },
)
```

---

# Installation

## 1. Create virtual environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\activate
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 2. Install dependencies

```bash
pip install -e .
```

Or:

```bash
pip install pytest requests
```

---

# Running the Executor

Run from repository root:

```bash
python -m question2.executor_main
```

The CLI demo executes multiple example tasks automatically.

---

# Example Execution Flow

The demo performs:

1. successful file check
2. failing file check
3. HTTP health check
4. sleep task
5. retry handling
6. timeout handling
7. execution summary

---

# Example Output

```text
INFO  Starting task execution
INFO  Executing task health-check
INFO  HTTP request completed successfully
INFO  Task completed successfully

ERROR File does not exist
WARNING Retrying task after failure

ERROR Task exceeded timeout

INFO  Execution summary:
INFO  Success: 2
INFO  Failed: 1
INFO  Timeout: 1
```

---

# Logging

The framework includes production-style structured logging.

Logs are separated by severity:

```text
logs/
├── debug_2026-06-13.log
├── error_2026-06-13.log
```

---

# Logged Events

The framework logs:

* task registration
* validation
* retry attempts
* timeout events
* HTTP requests
* task start/end
* summary statistics
* unexpected exceptions

This level of logging is useful during:

* production incidents
* night watch/on-call support
* debugging unstable systems
* infrastructure monitoring
* operational investigations

---

# Retry Strategy

Retries use exponential backoff:

```text
attempt 1 -> 1 second
attempt 2 -> 2 seconds
attempt 3 -> 4 seconds
```

Optional jitter prevents synchronized retry spikes.

---

# Timeout Protection

Tasks are protected against hanging forever.

If execution exceeds configured timeout:

```python
timeout_seconds=5
```

the task becomes:

```python
TaskStatus.TIMEOUT
```

instead of blocking the whole executor.

---

# Validation

The framework validates:

* empty task IDs
* invalid retry configuration
* unsupported HTTP methods
* invalid timeout values
* invalid task parameters
* unknown task types

Validation failures produce typed exceptions and structured logs.

---

# Running Tests

Run all tests:

```bash
pytest -v
```

Run specific tests:

```bash
pytest question2/tests/test_executor.py -v
```

Run with coverage:

```bash
pytest --cov=question2
```

---

# Test Coverage Includes

The tests validate:

* retry logic
* timeout handling
* task registration
* task validation
* HTTP validation
* execution summaries
* backoff calculation
* task isolation
* exception handling
* file checks
* logging behavior

---

# Extending the Framework

Adding a new task type requires only:

## 1. Create new task class

```python
@register_task("database_check")
class DatabaseCheckTask(BaseTask):
    ...
```

## 2. Implement execute()

```python
def execute(self) -> dict:
    ...
```

No executor changes are required.

---

# Design Goals

This solution prioritizes:

* maintainability
* extensibility
* observability
* production-readiness
* isolation of responsibilities
* clear logging
* defensive validation

instead of only solving the minimal assignment requirements.

---

# Why This Architecture

This structure resembles real production services where:

* tasks evolve over time
* new integrations are added
* debugging matters
* retries are critical
* logging is essential
* failures must be isolated

The goal was to implement something closer to an actual internal execution framework rather than a simple script.

---

# Operational Usage

This framework is suitable as a foundation for:

* internal schedulers
* health-check systems
* infrastructure automation
* ETL orchestration
* monitoring jobs
* operational tooling
* backend maintenance workflows

---

# Notes

* Python 3.13 compatible
* type-hinted
* production-style logging
* clean separation of concerns
* tested with pytest
* Docker-ready

---

# Quick Start

```bash
git clone <repo>
cd SportyGroupTask

python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate

pip install -e .

pytest -v

python -m question2.executor_main
```

---

# Author Notes

This implementation intentionally emphasizes:

* operational visibility
* debugging experience
* extensibility
* maintainability
* production engineering practices

rather than only the minimal happy-path solution.
