<!-- markdownlint-disable-file -->
<!-- markdown-table-prettify-ignore-start -->
# Web Validate (WebV) - Product Requirements Document (PRD)
Version 0.1.0 | Status Draft | Owner Product Manager (spec) | Team Development (implementation) | Target 0.1.0 in 2 weeks (weekly minor releases to 1.0.0) | Lifecycle Discovery

## Progress Tracker
| Phase | Done | Gaps | Updated |
|-------|------|------|---------|
| Context | Yes | — | 2026-06-21 |
| Problem & Users | Yes | Journeys optional | 2026-06-21 |
| Scope | Yes | — | 2026-06-21 |
| Requirements | Yes | Weekly release breakdown pre-kickoff | 2026-06-21 |
| Metrics & Risks | Yes | Quantitative baselines TBD until Movies API validation | 2026-06-21 |
| Operationalization | Yes | — | 2026-06-21 |
| Finalization | No | Pending review | 2026-06-21 |
Unresolved Critical Questions: 0 | TBDs: 2

## 1. Executive Summary
### Context
Teams operating web APIs need a single tool that validates correctness in CI/CD and continuously monitors latency, health, and availability in production. Existing approaches split functional testing and synthetic monitoring across separate tools, increasing operational overhead and creating gaps between what is tested pre-release and what is observed in production.

### Core Opportunity
Web Validate (WebV) is a web request validation tool that runs end-to-end functional tests and long-running performance/availability tests against JSON web APIs from a single YAML-driven definition. It serves both as a CI/CD test gate and as a geo-distributed, 24x7 production probe, exposing Prometheus metrics, health endpoints, and structured logs for observability.

### Goals
| Goal ID | Statement | Type | Baseline | Target | Timeframe | Priority |
|---------|-----------|------|----------|--------|-----------|----------|
| G-001 | Provide a single tool for both CI/CD functional testing and production synthetic monitoring | Outcome | TBD | One binary covering both modes | 0.1.0 (~2 weeks) | Must |
| G-002 | Enable authoring of deep JSON API validation tests in human-friendly YAML | Outcome | TBD | Full nested/array/object validation support | 0.1.0 (~2 weeks) | Must |
| G-003 | Gate CI/CD pipelines via reliable non-zero exit codes and JUnit reporting | Outcome | TBD | Deterministic exit semantics + JUnit XML | 0.1.0 (~2 weeks) | Must |
| G-004 | Deliver production-grade observability (metrics, health, structured logs) | Outcome | TBD | Prometheus + /healthz + /readyz + /version | 0.1.0 (~2 weeks) | Must |
| G-005 | Ship secure, reproducible, container- and Kubernetes-ready deployment artifacts | Outcome | TBD | Distroless image + Kustomize manifests | 0.1.0 (~2 weeks) | Must |

### Objectives (Optional)
| Objective | Key Result | Priority | Owner |
|-----------|------------|----------|-------|
| Unify test + monitor workflows | Single YAML test suite runs in both run-once and run-loop modes | Must | Development |
| Operate safely 24x7 | Graceful shutdown honored within bounded deadline across orchestrators | Must | Development |
| Validate via reference project | WebV fully tests the Movies API project at 0.1.0 | Must | Product Manager |

## 2. Problem Definition
### Current Situation
Functional API testing and production availability/performance monitoring are typically handled by different tools with different definition formats. Test definitions are not reused as production probes, and synthetic monitoring lacks the deep response validation available in functional test suites.

### Problem Statement
Teams lack a single, portable tool that can deeply validate JSON API responses, gate CI/CD pipelines, and run continuously as a geo-distributed production probe using one shared, human-friendly test definition.

### Root Causes
* Separation of functional test tooling from synthetic/availability monitoring tooling
* Test definition formats that are not reusable across CI and production contexts

### Impact of Inaction
* Duplicated test/monitor definitions and higher maintenance cost
* Production regressions in latency, availability, or response correctness detected late
* Inconsistent signal between pre-release validation and production observability

## 3. Users & Personas
| Persona | Goals | Pain Points | Impact |
|---------|-------|------------|--------|
| API/Platform Engineer | Author deep validation tests; run them in CI and production | Maintaining separate test and monitoring definitions | High |
| SRE / Reliability Engineer | Monitor latency, availability, error rates 24x7 across regions | Synthetic monitors lack deep response validation | High |
| DevOps / CI Engineer | Gate pipelines on functional correctness with clear pass/fail | Flaky or ambiguous exit semantics; weak CI reporting | High |
| Cluster Operator | Deploy and operate WebV securely on Kubernetes | Insecure defaults; non-GitOps-friendly manifests | Medium |

### Journeys (Optional)
TBD — confirm primary end-to-end journeys (CI gate run, continuous production probe, local development loop). Personas confirmed accurate.

## 4. Scope
### In Scope
* JSON web API validation with deep nested/array/object checks
* YAML-based test definitions with env-var substitution, custom bodies, and headers
* Run-once (CI) and run-loop (continuous) execution modes
* Structured logging, Prometheus metrics, health/readiness/version endpoints
* CI/CD exit-code gating and JUnit XML summaries
* Hardened Docker image and Kustomize-only Kubernetes deployment artifacts

### Out of Scope (justify if empty)
* Dedicated non-JSON API features — non-JSON APIs can be exercised with the current spec, but no additional non-JSON capabilities will be added
* Following HTTP redirects (explicitly not followed)
* Helm-based deployment (explicitly Kustomize-only)
* PII handling controls — not addressed in this release

### Assumptions
* Targets are JSON web APIs (non-JSON APIs can be exercised with the current spec without dedicated features)
* All string comparisons are case-sensitive
* Implementation language is unconstrained provided the CLI/log/metrics/endpoint contract is met
* The Movies API project is the initial validation target for the 0.1.0 release

### Constraints
* HTTP redirects are not followed
* YAML parsing must accept comments and treat property names case-insensitively
* Environment-variable substitution resolved at test-file load time
* Build must produce a self-contained binary at `./bin/webv`
* Kubernetes deployment is Kustomize-only (no Helm)

## 5. Product Overview
### Value Proposition
One YAML-defined test suite that validates JSON APIs deeply, gates CI/CD pipelines, and runs continuously as a geo-distributed production probe—wired for observability and secure deployment out of the box.

### Differentiators (Optional)
* Reuse of the same test definition for CI gating and 24x7 production monitoring
* Deep, recursive JSON validation (arrays, objects, nested graphs)
* Production-ready observability and hardened, reproducible deployment artifacts

### UX / UI (Conditional)
CLI-driven tool; no GUI. Human-friendly YAML test authoring is the primary authoring surface. UX Status: CLI-only confirmed.

## 6. Functional Requirements
| FR ID | Title | Description | Goals | Personas | Priority | Acceptance | Notes |
|-------|-------|------------|-------|----------|----------|-----------|-------|
| FR-001 | YAML test definitions | Author requests and expected results in human-friendly YAML (comments, anchors, case-insensitive properties) | G-002 | API/Platform Engineer | Must | Valid YAML files parse; invalid files cause non-zero exit | |
| FR-002 | Per-request configuration | Support `path`, `verb`, `testName`, `tag`, and `validation` rules per request | G-002 | API/Platform Engineer | Must | Each field honored at runtime | |
| FR-003 | Custom request body | Send request `body` with configurable `contentMediaType` | G-002 | API/Platform Engineer | Should | Body and media type sent as configured | |
| FR-004 | Custom request headers | Attach arbitrary HTTP headers per request | G-002 | API/Platform Engineer | Should | Headers present on outbound request | |
| FR-005 | Env-var substitution | Inject `${VARIABLE_NAME}` values at load time (declared in `variables`) | G-002 | API/Platform Engineer | Must | Variables resolved at file load | |
| FR-006 | Status code validation | Validate HTTP status code (100–599; default 200) | G-002 | API/Platform Engineer | Must | Mismatch flagged as validation error | |
| FR-007 | Content type validation | Validate Content-Type/MIME (default application/json) | G-002 | API/Platform Engineer | Must | Mismatch flagged | |
| FR-008 | Content length validation | Exact `length` or `minLength`/`maxLength` bounds | G-002 | API/Platform Engineer | Should | Bounds enforced | |
| FR-009 | Response time validation | `maxMilliSeconds` max request duration | G-002,G-004 | SRE | Should | Exceeding duration flagged | |
| FR-010 | Exact match validation | Body exactly matches expected value | G-002 | API/Platform Engineer | Should | Exact comparison (case-sensitive) | |
| FR-011 | Contains / not contains | Case-sensitive presence and negated presence checks | G-002 | API/Platform Engineer | Should | Both checks supported | |
| FR-012 | JSON array validation | `count`/`minCount`/`maxCount`, `byIndex`, `forAny`, `forEach` | G-002 | API/Platform Engineer | Must | All array operators supported | |
| FR-013 | JSON object validation | Check fields exist, match values, recurse into nested objects | G-002 | API/Platform Engineer | Must | Deep recursion to arbitrary depth | |
| FR-014 | Fail-fast control | `failOnValidationError` per request triggers immediate failure | G-003 | DevOps/CI Engineer | Must | Immediate test failure on flagged request | |
| FR-015 | Default execution mode | Process input file(s) sequentially once, then exit | G-001 | DevOps/CI Engineer | Must | Single pass then exit | |
| FR-016 | Run-loop mode | `--run-loop` runs continuously until stopped or `--duration` | G-001,G-004 | SRE | Must | Loops until signal/duration | |
| FR-017 | Dry-run mode | `--dry-run` validates and displays params without executing | G-001 | DevOps/CI Engineer | Should | No requests executed | |
| FR-018 | Randomized requests | `--random` randomizes order in run-loop mode | G-001 | SRE | Could | Order randomized | |
| FR-019 | Delay & sleep controls | `--delay-start` defers start; `--sleep` throttles between requests | G-001 | SRE | Should | Timing honored | |
| FR-020 | Multi-threaded load | Repeat `--server` to run parallel threads in one instance | G-001 | SRE | Should | Parallel threads per repeated server | |
| FR-021 | Structured logging | stdout/stderr logs in `TsvMin`/`Tsv`/`Json`/`None`; per-request + summary fields | G-004 | SRE | Must | All formats emit specified fields | |
| FR-022 | Prometheus metrics | `/metrics` exposes `WebVDuration`/`WebVSummary` (+ runtime metrics) in run-loop | G-004 | SRE | Must | Metrics scrapeable in run-loop | |
| FR-023 | Health & version endpoints | `/healthz`, `/readyz`, `/version` exposed in run-loop | G-004 | Cluster Operator | Must | Endpoints serve in run-loop | |
| FR-024 | Test summaries | `--summary` outputs `Tsv`/`Json`/`Xml` (JUnit) | G-003 | DevOps/CI Engineer | Must | Summary emitted in chosen format | |
| FR-025 | CI/CD exit-code gating | Non-zero exit on parse error, unhandled exception, `--max-errors` exceeded, or flagged validation error | G-003 | DevOps/CI Engineer | Must | Deterministic exit codes | |
| FR-026 | Performance categorization | Categorize results (category/quartile) for trend analysis | G-004 | SRE | Should | Category/quartile present in logs | |
| FR-027 | Metadata labeling | `--tag`/`--region`/`--zone` distinguish instances/locations | G-004 | SRE | Should | Labels in logs/metrics | |
| FR-028 | CLI & env configuration | Configure via CLI options and env vars (CLI precedence); short flags; `--help`/`--version` | G-001 | API/Platform Engineer | Must | Both sources supported; CLI wins | |
| FR-029 | Graceful shutdown | Handle SIGINT/SIGTERM: drain loop, finish in-flight, serve final scrape, flush, bounded exit | G-001,G-004 | Cluster Operator | Must | Clean exit within deadline | |

### Feature Hierarchy (Optional)
```plain
WebV
├─ Test Definition (YAML)
│  ├─ Requests (path/verb/body/headers)
│  └─ Validation (status/content/array/object)
├─ Execution (run-once / run-loop / dry-run)
├─ Observability (logs / metrics / health endpoints)
├─ CI/CD Integration (exit codes / JUnit)
└─ Deployment (binary / Docker / Kustomize)
```

## 7. Non-Functional Requirements
| NFR ID | Category | Requirement | Metric/Target | Priority | Validation | Notes |
|--------|----------|------------|--------------|----------|-----------|-------|
| NFR-001 | Reliability | Deterministic CI exit semantics | Correct exit code for every failure class | Must | CI test matrix | |
| NFR-002 | Reliability | Bounded graceful shutdown | Clean exit within 30s deadline (configurable) | Must | Signal tests | |
| NFR-003 | Performance | Request timeout control | Default 30s timeout; `--timeout` configurable | Must | Timeout tests | |
| NFR-004 | Observability | Metrics latency histogram | `WebVDuration` exp. buckets (1ms start, factor 2, 10 buckets) | Must | Scrape validation | |
| NFR-005 | Observability | Quantile summary window | `WebVSummary` φ=0.9/0.95/0.99/1.0, 5-min sliding window | Must | Scrape validation | |
| NFR-006 | Security | Container runs non-root | `USER 65532:65532`; no shell/package manager | Must | Image inspection | |
| NFR-007 | Security | Hardened runtime | read-only FS, drop ALL caps, no-new-privileges, seccomp RuntimeDefault | Must | Runtime audit | |
| NFR-008 | Security | Vulnerability gating | Build fails on HIGH/CRITICAL CVEs (trivy/grype) | Must | Build scan | |
| NFR-009 | Maintainability | Reproducible builds | Pinned digests; reproducible artifacts; semver tagging | Must | Build verification | |
| NFR-010 | Portability | Self-contained binary | `./bin/webv` static where supported; Linux/WSL/macOS, bash/zsh | Must | Build matrix | |
| NFR-011 | Observability | Log format defaults | `Tsv` (run-once), `Json` (run-loop); JSON camelCased | Must | Format tests | |
| NFR-012 | Scalability | Geo-distributed 24x7 operation | Multi-region run-loop with region/zone labeling | Should | Field deployment | |
| NFR-013 | Maintainability | GitOps-ready manifests | Kustomize-only, self-contained component dirs, relative paths | Must | Manifest review | |
| NFR-014 | Security | Network isolation | NetworkPolicy default-deny + scoped allows | Must | Cluster policy test | |
| NFR-015 | Compatibility | Contract stability | CLI surface, log formats, metrics, endpoints are the contract | Must | Contract tests | |
| NFR-016 | Observability | Error/latency metric segmentation | Errors and latency segmented by `/api/*` vs. static content; `404` tracked as a distinct, expected series | Must | Metric label review | |
| NFR-017 | Performance | Default latency targets | `/api/*` and static content respond <= 500 ms; 0 API errors (excl. 404) | Should | Probe metrics | Per-deployment tunable |

## 8. Data & Analytics (Conditional)
### Inputs
YAML test files (requests + expected results); CLI options; environment variables. Default test file location is the current directory; in containers, `/tests` mounted read-only.

### Outputs / Events
Per-request log records (one per executed request), end-of-run summary records, Prometheus metrics, and JUnit XML summaries.

### Instrumentation Plan
| Event | Trigger | Payload | Purpose | Owner |
|-------|---------|--------|---------|-------|
| request | Each executed request | Per-request log fields (type/date/server/verb/path/testName/statusCode/duration/contentLength/failed/validated/errorCount/errors/category/quartile/tag/region/zone) | Result + performance tracking | TBD |
| summary | End of run-once with `--summary` | totalRequests/validationErrorCount/failedRequests/successfulRequests/durationMs/startTime/endTime | CI reporting | TBD |
| WebVDuration | Run-loop scrape | Histogram labeled status/server/failed (+region/zone) | Latency distribution | TBD |
| WebVSummary | Run-loop scrape | Quantile summary labeled status/server/failed (+region/zone) | Latency quantiles | TBD |

### Metrics & Success Criteria
Success metrics are TBD pending the initial validation milestone: WebV must fully test the Movies API project at the 0.1.0 release. Quantitative baselines/targets will be defined from that exercise.

Default metric segmentation: errors and latency are reported separately for `/api/*` paths versus other (static) content. `404` responses are tracked as a distinct series because they are an expected "not found" status, not a failure.

| Metric | Type | Baseline | Target | Window | Source |
|--------|------|----------|--------|--------|--------|
| Movies API full coverage | Outcome | TBD | WebV fully tests Movies API at 0.1.0 | 2 weeks | Movies API project |
| API errors (`/api/*`, excl. 404) | Reliability | TBD | 0 errors | 5-min | WebVDuration/logs |
| API response time (`/api/*`) | Performance | TBD | <= 500 ms | 5-min | WebVSummary |
| Static content response time (non-`/api/*`) | Performance | TBD | < 500 ms | 5-min | WebVSummary |
| 404 responses (tracked separately) | Informational | TBD | Tracked, not alerted (expected not-found) | 5-min | logs/metrics |
| Adoption (CI + monitoring) | Outcome | TBD | TBD | TBD | TBD |
| Production probe uptime | Reliability | TBD | TBD | TBD | Metrics |

## 9. Dependencies
| Dependency | Type | Criticality | Owner | Risk | Mitigation |
|-----------|------|------------|-------|------|-----------|
| Prometheus / Prometheus Operator | Observability | High | TBD | Scrape misconfig | ServiceMonitor + vendored manifests |
| Grafana | Observability | Medium | TBD | Dashboard drift | Example dashboards as ConfigMaps |
| Traefik (k3s/k3d) ingress | Platform | Medium | TBD | Ingress changes | IngressRoute CRD + middlewares |
| Fluent Bit / log infra | Observability | Medium | TBD | Forwarding gaps | Structured log formats |
| Container base (distroless/scratch) | Build | High | TBD | Base image CVEs | Pinned digests + scan gate |

## 10. Risks & Mitigations
| Risk ID | Description | Severity | Likelihood | Mitigation | Owner | Status |
|---------|-------------|---------|-----------|-----------|-------|--------|
| R-001 | Graceful shutdown exceeds deadline in orchestrators | High | Medium | Bounded deadline force-exit; final scrape window | TBD | Open |
| R-002 | Unauthenticated metrics scraping from outside cluster | High | Medium | Rate-limit + IP-allowlist middleware on `/metrics` | TBD | Open |
| R-003 | Flaky CI gating from ambiguous exit semantics | Medium | Low | Deterministic exit-code matrix + tests | TBD | Open |
| R-004 | Base image / dependency CVEs | High | Medium | Pinned digests + trivy/grype build gate | TBD | Open |
| R-005 | Mixing environments in one GitOps repo collapses security context | High | Low | Separate repos per environment | TBD | Open |

## 11. Privacy, Security & Compliance
### Data Classification
Test definitions and request/response metadata; classification TBD (may include endpoint URLs and headers). Avoid embedding secrets—use env-var substitution.

### PII Handling
Not addressed in this release. PII handling controls are explicitly out of scope for 0.1.0; revisit in a future release.

### Threat Considerations
Hardened container (non-root, read-only FS, dropped caps, seccomp), network default-deny with scoped allows, rate-limited/IP-allowlisted metrics, images referenced by digest in production overlays.

### Regulatory / Compliance (Conditional)
| Regulation | Applicability | Action | Owner | Status |
|-----------|--------------|--------|-------|--------|
| None identified for 0.1.0 | N/A | PII handling deferred to a future release | Product Manager | Deferred |

## 12. Operational Considerations
| Aspect | Requirement | Notes |
|--------|------------|-------|
| Deployment | Self-contained binary, hardened Docker image, Kustomize manifests | `./bin/webv`; `webv:<semver>` + `latest` |
| Rollback | Pin prior semver via overlay `newTag` | Overlays only override tag/patches |
| Monitoring | Prometheus scrape via ServiceMonitor (30s/10s) | Honors region/zone labels |
| Alerting | Alert rules vary by observed API and are defined per deployment; Prometheus metrics for errors and latency are segmented by `/api/*` vs. static content. Default targets: 0 API errors and <= 500 ms for `/api/*`; < 500 ms for static content; `404` tracked separately as an expected not-found status (not alerted). | Per-API thresholds tuned at deployment |
| Support | Public GitHub repository with Discussions and Issues | Community-driven support model |
| Capacity Planning | Resource requests/limits set (e.g., 256m mem, 0.5 cpu) | Tune per deployment |

## 13. Rollout & Launch Plan
### Phases / Milestones
| Phase | Date | Gate Criteria | Owner |
|-------|------|--------------|-------|
| v0.1.0 | 2026-07-05 (~2 weeks) | Core validation, run modes, observability, image, base manifests; fully tests Movies API | Development |
| Weekly minors (v0.2.0+) | Weekly | Incremental improvements each week | Development |
| v1.0.0 | TBD | Feature-complete, stable contract | Development |

### Feature Flags (Conditional)
| Flag | Purpose | Default | Sunset Criteria |
|------|---------|--------|----------------|
| TBD | TBD | TBD | TBD |

### Communication Plan (Optional)
TBD

## 14. Open Questions
| Q ID | Question | Owner | Deadline | Status |
|------|----------|-------|---------|--------|
| Q-001 | Who is the document owner, owning team, and target release? | Product Manager | 2026-06-21 | Resolved |
| Q-002 | What are the measurable success metrics and baselines? | Product Manager | 0.1.0 | Open (TBD until Movies API validation) |
| Q-003 | Are non-JSON APIs in or out of scope? | Product Manager | 2026-06-21 | Resolved |
| Q-004 | Do request bodies/headers/logs ever contain PII? | Product Manager | 2026-06-21 | Resolved (deferred) |
| Q-005 | What is the support and alerting model post-launch? | Product Manager | 2026-06-21 | Resolved |

## 15. Changelog
| Version | Date | Author | Summary | Type |
|---------|------|-------|---------|------|
| 0.1.0 | 2026-06-21 | PRD Builder | Initial PRD generated from webv.md feature spec | Created |
| 0.1.1 | 2026-06-21 | PRD Builder | Added ownership, timeline, Movies API validation, scope/PII/support decisions | Updated |
| 0.1.2 | 2026-06-21 | PRD Builder | Added metric segmentation (`/api/*` vs static), latency/error targets, 404 tracking, alerting guidance | Updated |

## 16. References & Provenance
| Ref ID | Type | Source | Summary | Conflict Resolution |
|--------|------|--------|---------|--------------------|
| REF-001 | Spec | webv.md | WebV feature specification (capabilities, CLI, logs, metrics, deployment) | Source of truth for this PRD |

### Citation Usage
All functional and non-functional requirements derive from REF-001 (webv.md). TBD markers indicate fields not specified in the source that require stakeholder input.

## 17. Appendices (Optional)
### Glossary
| Term | Definition |
|------|-----------|
| Run-loop | Continuous execution mode (`--run-loop`) for long-running monitoring |
| Run-once | Default mode: process input files once then exit |
| ServiceMonitor | Prometheus Operator CRD selecting the WebV service for scraping |

### Additional Notes
Implementation language is unconstrained; the CLI surface, log formats, metrics, and endpoints constitute the binding contract.

Generated 2026-06-21 by PRD Builder (mode: full)
<!-- markdown-table-prettify-ignore-end -->
