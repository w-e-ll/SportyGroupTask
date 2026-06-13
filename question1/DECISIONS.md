# Question 1: Configuration Conflict Resolver - DECISIONS

## 1. Which configuration sources did you support and why? What did you exclude?

I implemented support for two configuration source types:

1. YAML configuration files
2. Environment variable overrides

I chose YAML because it is commonly used in infrastructure and deployment workflows due to its readability and support for nested configuration structures. It also aligns well with operational environments such as Kubernetes, CI/CD systems, and internal service configuration management.

I chose environment variables because they are widely used for runtime overrides, containerized deployments, and secret injection.

The effective configuration is produced by merging:

* base YAML configuration
* environment-specific YAML configuration
* environment variable overrides

I intentionally excluded:

* remote API configuration sources
* distributed configuration services
* database-backed configuration storage

These would require additional concerns such as:

* authentication
* retries
* caching
* network failure handling
* consistency guarantees

Given the time constraints of the assessment, I preferred a smaller but production-oriented implementation rather than partially implementing more complex systems.

---

## 2. What are your precedence rules and why? What alternatives did you consider?

The precedence order is:

1. Environment variables
2. Environment-specific YAML
3. Base YAML configuration

This mirrors common operational practices where:

* base configuration defines defaults
* environment configuration customizes deployment-specific values
* environment variables provide final runtime overrides

Example:

```yaml
# base.yml
service:
  port: 8080
```

```yaml
# production.yml
service:
  port: 8443
```

```bash
PRODUCTION_SERVICE__PORT=9443
```

Final effective value:

```yaml
service.port = 9443
```

I considered:

* explicit source ordering via CLI arguments
* "last source wins" dynamic precedence
* strict conflict rejection during merges

However, fixed precedence rules are simpler, more deterministic, and easier to reason about operationally.

---

## 3. How do you define "conflict"? Give one example that is a conflict and one that is not.

I define a conflict as:

> The same fully-qualified configuration path existing in both environments with different effective values.

Example conflict:

```yaml
staging:
  service:
    port: 8080

production:
  service:
    port: 8443
```

This is a conflict because:

* both contain `service.port`
* the values differ

Example that is NOT considered a conflict:

```yaml
staging:
  feature_flags:
    experimental_ui: true

production:
  service:
    port: 8443
```

These are different configuration paths.
This still appears in the diff output, but not as a direct environment conflict.

I intentionally separated:

* "conflicts"
* "differences"

because operationally they represent different concepts.

---

## 4. How do you handle source failures? Fail entirely or proceed partially? Why?

The resolver proceeds partially if a source fails to load.

For example:

* missing YAML file
* invalid YAML syntax
* malformed environment override

The failure is:

* logged using structured logs
* surfaced in the source status
* isolated to the failing source

The resolver then continues using available sources.

I chose this approach because:

* operational tooling should remain observable during partial outages
* diagnostics are often more valuable than strict failure
* operators can still inspect partial effective configuration

In production, I would likely support:

* strict mode (fail-fast)
* permissive mode (best-effort)

depending on whether the resolver is used for:

* deployment enforcement
* diagnostics
* dry-run validation
* runtime debugging

---

## 5. What did you skip or simplify? What would you improve with 10 more hours?

### Simplifications

I intentionally simplified several areas:

* YAML only (no TOML/JSON support)
* no remote configuration APIs
* no schema validation
* no rollback generation
* no configuration versioning
* no concurrent source loading
* no secret manager integration
* no write/apply mode

The implementation currently focuses on:

* correctness
* maintainability
* observability
* operational clarity

rather than maximum feature completeness.

---

---

## 6. Observability and Logging

The implementation includes structured operational logging across all critical execution paths.

Logging was intentionally designed to support:

* debugging
* incident analysis
* production observability
* operational auditing

The resolver logs:

* source loading attempts
* merge operations
* environment parsing
* conflict detection
* diff generation
* validation failures
* source parsing failures

Separate rotating log streams are used for:

* informational/debug events
* warnings/errors

This separation improves signal quality during operational troubleshooting.

Example log outputs include:

* configuration source load failures
* malformed environment overrides
* invalid nested path structures
* merge conflicts
* unsupported file formats

I intentionally treated logging as a production feature rather than a debugging afterthought.
Structured logs simplify future integration with centralized logging systems such as ELK/Splunk/Grafana Loki.

---

## 7. Security Considerations

The implementation masks sensitive configuration values in:

* conflict reports
* diff output
* serialized responses

Sensitive keys are detected using common operational naming conventions such as:

* password
* secret
* token
* api_key
* private_key

This prevents accidental exposure of secrets during:

* dry-run output
* CI/CD logs
* operational debugging
* incident analysis

Example:

```json
{
  "database.password": "<masked>"
}
```

I intentionally preferred over-masking rather than risking credential exposure.

---

## 8. Testing Strategy

The test suite focuses on both correctness and operational edge cases.

Covered scenarios include:

* successful YAML loading
* broken YAML parsing
* missing configuration sources
* deep merge behavior
* conflict detection
* diff generation
* added/removed/changed values
* sensitive value masking
* nested environment overrides
* invalid nested path structures
* unsupported file extensions
* log file creation
* partial source failure handling

The tests intentionally validate both:

* functional correctness
* production-oriented failure behavior

This mirrors real-world infrastructure tooling requirements where operational resilience is as important as happy-path correctness.
Tests were designed to validate both happy-path and failure-path behavior.”

---

## 9. Scalability Considerations

The current implementation is intentionally optimized for clarity and maintainability rather than maximum scale.

However, the architecture allows future improvements such as:

* concurrent source loading
* streaming large configuration trees
* remote provider caching
* incremental diff calculation
* plugin-based source providers

The internal structure separates:

* parsing
* merging
* diffing
* conflict detection
* serialization
* CLI execution

which reduces coupling and simplifies future extension.

I intentionally prioritized clean separation of concerns to support long-term maintainability.

---

### Improvements With Additional Time

With more time, I would add:

#### 1. Schema Validation

Using:

* Pydantic
* JSON Schema

to validate:

* required fields
* type safety
* invalid nested structures

---

#### 2. Rollback Planning

Generate:

* rollback patches
* reversible diffs
* deployment safety previews

---

#### 3. Remote Source Support

Add:

* HTTP/REST configuration providers
* timeout handling
* retries
* authentication
* caching
* circuit-breaker protection

---

#### 4. Better Diff Engine

Improve output to distinguish:

* added values
* removed values
* modified values
* masked secrets
* type changes

---

#### 5. Concurrency

Load multiple configuration sources concurrently to reduce latency in large-scale environments.

---

#### 6. Secret Management Integration

Integrate with:

* Vault
* AWS Secrets Manager
* Kubernetes Secrets

instead of relying purely on environment variables.

---

## Additional Notes

The implementation intentionally emphasizes:

* operational safety
* readability
* explicit tradeoffs
* maintainability
* deterministic behavior

over implementing every possible feature.

I optimized for the kind of engineering decisions commonly required in production backend and infrastructure systems.
