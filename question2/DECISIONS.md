# Question 2: Task Executor - DECISIONS

## 1. What retry strategy did you implement and why? What alternatives did you consider?

I implemented configurable per-task retry logic using exponential backoff with jitter.

Each task has a `RetryConfig` with:

* `max_attempts`
* `base_delay_seconds`
* `max_delay_seconds`
* `jitter_seconds`

I chose per-task configuration because operational tasks often have different failure characteristics. For example, an HTTP health check may benefit from short retries, while a cleanup task or data synchronization task may require fewer retries or longer delays.

The implemented strategy is:

```text
delay = min(base_delay_seconds * 2^(attempt - 1), max_delay_seconds) + jitter
```

I chose exponential backoff because it reduces pressure on failing dependencies compared to immediate retries. I added jitter to reduce the chance of multiple tasks retrying at exactly the same time, which can create retry bursts.

Alternatives considered:

1. Fixed delay
   Simpler, but less adaptive when dependencies are degraded.

2. Immediate retry
   Fast, but risky because it can increase load on an already failing dependency.

3. Global retry configuration
   Simpler to configure, but less flexible for mixed operational workloads.

4. Full circuit breaker
   Useful in production, but too large for this framework extension and time limit.

---

## 2. How did you implement timeout handling? What are the tradeoffs of your approach?

Timeout handling is implemented by executing each task inside a `ThreadPoolExecutor` worker and calling:

```python
future.result(timeout=config.timeout_seconds)
```

If the timeout is exceeded, the executor raises a dedicated `TaskTimeoutError`, and the task result is marked with `TaskStatus.TIMEOUT`.

This makes timeout failures distinguishable from normal task failures.

Advantages:

* works with the existing synchronous task interface
* does not require rewriting tasks as async functions
* keeps the original framework pattern easy to understand
* allows timeout handling to be centralized in the executor

Tradeoffs:

* Python threads cannot always forcibly stop running code immediately
* `future.cancel()` only cancels work that has not started yet
* blocking system calls may continue in the background until they return
* this approach is safer for short operational tasks than for untrusted long-running workloads

In production, for stronger isolation, I would consider:

* subprocess-based execution
* async I/O for network tasks
* process pools for CPU-heavy work
* external job runners
* Kubernetes jobs with active deadline seconds

---

## 3. What additional task type did you add and why? How does it demonstrate the framework's extensibility?

I added two additional task types:

1. `file_exists`
2. `sleep`

The main useful operational task is `file_exists`.

It checks whether a local filesystem path exists and returns metadata such as:

* path
* exists
* is_file
* is_dir

This is a realistic operational task because many internal maintenance frameworks need to verify artifacts, generated reports, lock files, config files, or mounted paths.

The `sleep` task is intentionally a demo/testing task. It makes timeout behavior easy to reproduce in tests and local demos. I would not treat it as a real production task.

These tasks demonstrate extensibility because each task:

* inherits from `BaseTask`
* implements `validate()`
* implements `execute()`
* is registered through the `@register_task(...)` decorator
* does not require changes to `TaskExecutor`

This preserves the framework's existing registry pattern while making it easier to add new task types later.

---

## 4. Did you keep sequential execution or add concurrency? Why?

I kept sequential execution.

This was intentional.

The original framework executed tasks sequentially, and I wanted to preserve that behavior unless there was a strong reason to change it.

Sequential execution is easier to reason about because:

* logs are ordered
* retries are easier to understand
* operational side effects are easier to control
* shared resources are less likely to be overloaded
* failure behavior is simpler for operators

For a small operational task framework, predictable execution is more important than maximum throughput.

If the requirement changed to run hundreds of tasks efficiently, I would introduce concurrency as an explicit feature with:

* configurable worker count
* per-task timeout
* rate limiting
* bounded queues
* cancellation handling
* clear summary reporting
* protection against retry storms

---

## 5. What happens if a task fails all retry attempts? How is this surfaced to the operator?

If a task fails all retry attempts, the executor returns a `TaskResult` with:

* `status = TaskStatus.FAILED` for normal failures
* `status = TaskStatus.TIMEOUT` for timeout failures
* `attempts = max_attempts`
* `error_message` containing the final error
* `completed_at` timestamp

The failure is surfaced in three ways:

1. Structured JSON logs
   Each attempt is logged, including retries, failures, and timeouts.

2. Task result object
   The caller receives a structured `TaskResult`.

3. Summary output
   The executor summary includes:

   * status counts
   * success rate
   * total attempts
   * retried task count
   * registered task types

This gives operators both high-level visibility and per-task diagnostic detail.

---

## 6. What did you skip or simplify? What would break in production?

### Simplifications

I intentionally simplified several areas:

* no concurrent batch execution
* no external task configuration file
* no persistent task history
* no metrics exporter
* no circuit breaker
* no rate limiting
* no distributed locking
* no task dependency graph
* no hard process-level cancellation
* no external queue integration

The framework is intentionally small and readable.

---

### What Would Break In Production?

The biggest production limitation is timeout cancellation.

Using threads allows the executor to detect timeouts, but it does not guarantee immediate termination of already-running work. For tasks that perform long blocking operations, subprocesses or external job isolation would be safer.

Other production risks:

* retry storms if many tasks target the same failing dependency
* long-running tasks could consume worker resources
* no persistent audit trail after process exit
* no integration with monitoring systems
* no structured task configuration loading
* no concurrency controls for large batches
* no permissions/sandboxing for unsafe task types

---

### What I Would Improve With More Time

With more time, I would add:

1. Config-driven task loading
   Load task definitions from YAML or JSON.

2. Concurrency with safeguards
   Add configurable worker pools, bounded queues, and rate limits.

3. Stronger cancellation
   Use subprocesses for tasks that need hard timeout enforcement.

4. Metrics
   Export counts, durations, failures, retries, and timeouts.

5. Circuit breaker behavior
   Stop retrying dependencies that are clearly unavailable.

6. Persistent history
   Store task results for audit and troubleshooting.

7. Better retry classification
   Retry only transient failures and avoid retrying validation/configuration errors.

8. Duration tracking
   Add per-attempt and total task duration metrics.

---

## Notes On Structural Changes

The original starter code placed the framework, models, registry, logging, and task implementations in one file.

I split the code into small modules:

```text
question2/
├── executor.py
└── lib/
    ├── exceptions.py
    ├── logging_utils.py
    ├── models.py
    ├── registry.py
    └── tasks.py
```

I kept `executor.py` as the main entry point, as requested, but moved reusable framework components into `lib/`.

This preserves the original task registry pattern while improving:

* readability
* testability
* maintainability
* separation of responsibilities

I would keep this split for a small internal operational framework, but avoid splitting further unless the number of task types grows significantly.
