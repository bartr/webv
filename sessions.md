# WebV Implementation Sessions

> Source spec: [webv-prd.md](webv-prd.md)
> Methodology: [docs/METHODOLOGY.md](docs/METHODOLOGY.md)
> Session-log template: [docs/session-log.md](docs/session-log.md)

This document slices the WebV PRD into **release-able sessions** following the [context-first session model + RPI inner loop](docs/METHODOLOGY.md). Each session:

- Frames in 2 minutes, runs one Research → Plan → Implement → Review cycle, closes with green tests + FF-merge + dot-release tag.
- Targets **90–120 minutes** for a senior engineer comfortable with VS Code + GitHub Copilot.
- Ends with a working, demoable artifact behind a dot-release tag (`vX.Y.Z`) on `main` — never a half-built feature on a branch.
- Cuts scope at the fit check rather than running long.

Tag scheme follows the PRD's overlay scheme (`v0.1.0`, `v0.2.0`, …). The 1.0.0 cut is the integration session — the point where every PRD acceptance criterion is closed.

---

## Baseline Technical Decisions (apply to every session)

These are pinned up front so they are not re-litigated session-by-session. The PRD allows them; pinning here removes a recurring decision tax.

| Concern | Decision | Why |
| --- | --- | --- |
| Language | **Go 1.26** (latest stable) | Statically-linked single binary, distroless story, mature `prometheus/client_golang`, first-class signal/context handling, modest binary size — matches every PRD non-functional constraint without runtime framework. Pin via `go 1.26` in `go.mod` and `FROM golang:1.26-alpine AS builder` (digest-pinned) in the Dockerfile. |
| CLI / env binding | `github.com/urfave/cli/v2` | Single root command, clean `EnvVars` slice per flag, auto `--help` / `--version`, deterministic exit codes — matches the PRD CLI table directly. |
| YAML parser | `github.com/goccy/go-yaml` | Comment-tolerant, supports `yaml.UseJSONUnmarshaler()` and case-insensitive decoding via custom tag resolver. Falls back to `gopkg.in/yaml.v3` if a constraint blocks it. |
| HTTP client | `net/http` with `CheckRedirect: http.ErrUseLastResponse` and one `*http.Client` per parallel-server thread | PRD prohibits redirect following; per-thread clients keep parallelism honest (FR 2, NFR Performance). |
| Metrics | `github.com/prometheus/client_golang` | Standard, exposes process / Go runtime metrics for free. |
| Logging | `log/slog` for `Json` format; hand-rolled `bufio.Writer` for `Tsv` / `TsvMin` | `slog` gives us camelCase via `ReplaceAttr` cleanly; TSV is fixed-column and benefits from a tight writer. |
| Testing | `testing` + table-driven + `httptest.NewServer` | Stdlib only. Coverage gate **≥ 80%** per session, enforced in CI. |
| Static checks | `go vet`, `staticcheck`, `gosec`, `govulncheck` | Run in CI on every PR and locally via `./build --check`. |
| Container base | `gcr.io/distroless/static-debian12:nonroot` pinned by digest | Matches PRD §Container exactly. |
| CVE scan | `aquasec/trivy` pinned by digest, fail on HIGH/CRITICAL | Matches PRD FR 51. |
| Build tooling | POSIX `./build` shell script (`set -euo pipefail`, bash + zsh compatible) | Matches PRD FR 45 portability. |
| Repo layout | `cmd/webv/`, `internal/{cli,config,loader,httpx,validator,logsink,summary,runloop,metrics}`, `deploy/`, `tests/`, `docs/`, `.copilot-tracking/` | Internal packages keep the public surface small and let each session land code in a bounded directory. |
| CI | GitHub Actions: `build`, `test`, `lint`, `vuln`, `image-scan`, `e2e-k3d` jobs | Each job gates merge; image-scan + e2e land in later sessions. |

### Per-session conventions (enforced)

- **Branch** `session-NN-<slug>`. PR title `Session NN: <one-line goal>`.
- **RPI artifacts** in `.copilot-tracking/YYYY-MM-DD-<topic>-{research,plan,changes,review}.md`. New chat between each phase.
- **Frame / Start / End times** logged in [docs/session-log.md](docs/session-log.md) per the methodology.
- **Close ritual:** `go test -race ./...` + `staticcheck ./...` + `govulncheck ./...` green → squash-or-rebase merge → `git tag vX.Y.Z && git push origin vX.Y.Z` → repo-memory + retro updates → one-paragraph summary + next-session starter.
- **Definition of Done for every session:** all the session's listed PRD acceptance-criteria bullets are checked off in [webv-prd.md](webv-prd.md), and a manual smoke command (given per session) succeeds against a real binary.

---

## Session Map (overview)

| # | Tag | Theme | PRD acceptance bullets closed |
| --- | --- | --- | --- |
| 1 | `v0.1.0` | Project bootstrap, CLI skeleton, build script, CI | CLI: `--version`, `--help`; Build: `./build` produces `./bin/webv` |
| 2 | `v0.2.0` | YAML test-file loader + env-var substitution + model | CLI: `${VAR}` substitution, YAML case-insensitive + comments |
| 3 | `v0.3.0` | Run-once HTTP execution + basic TSV logging | CLI: `--dry-run`, exit codes for parse / unhandled / `--max-errors`; redirects not followed; flag-over-env precedence |
| 4 | `v0.4.0` | Validation engine (status / body / array / object) + `failOnValidationError` | Validation engine bullets (both) |
| 5 | `v0.5.0` | Log formats (`TsvMin`/`Tsv`/`Json`/`None`) + summary (`Tsv`/`Json`/`Xml`) + JUnit schema | Logging and summary bullets (all 7) |
| 6 | `v0.6.0` | Run-loop mode + HTTP endpoints `/healthz`, `/readyz`, `/version` + signal handling + parallel `--server` | Run-loop: `/version`, `/healthz`, `/readyz`, SIGTERM shutdown |
| 7 | `v0.7.0` | Prometheus `/metrics` + `WebVDuration` + `WebVSummary` + conditional `region`/`zone` | Run-loop: `/metrics`, conditional Prom labels |
| 8 | `v0.8.0` | Multi-stage Dockerfile + `./build --image` + trivy CVE gate | Container bullets (all 6) |
| 9 | `v0.9.0` | Kustomize `deploy/webv/` base + overlay `v0.1.0` + ServiceMonitor + Traefik IngressRoute + NetworkPolicy | Kubernetes bullets 1–10 |
| 10 | `v0.10.0` | Vendored observability: `deploy/servicemonitor-crd/`, `deploy/prometheus/`, `deploy/grafana/` + WebV dashboards | Remaining Kubernetes bullets (Helm-absence, basic-auth IngressRoutes, namespace PSA label) |
| 11 | `v1.0.0` | End-to-end on k3d, image digest pinning, GitOps-readiness verification, performance envelope check | GitOps-readiness bullet; final integration |

---

## Session 1 — `v0.1.0` · Project bootstrap, CLI skeleton, build script, CI

**Frame**

- **Goal:** `./build` produces `./bin/webv`; `./bin/webv --version` prints a semver and exits 0; `./bin/webv --help` prints every flag from the PRD CLI Parameter Reference; CI runs build + test + vet on every PR. No request execution yet.
- **Out of scope:** YAML loading, HTTP execution, run-loop, metrics, container, k8s.
- **Failure condition:** flags differ in name / short / env-var from the PRD; `./build` doesn't run cleanly under both bash and zsh; CI absent.

**RPI focus**

- **Research:** Pick `urfave/cli/v2` vs `cobra` (decision pinned above — confirm); confirm Go version; confirm semver embedding via `-ldflags "-X main.Version=..."`; confirm `staticcheck` / `govulncheck` install pattern in CI.
- **Plan:** module init → `cmd/webv/main.go` → flag definitions (every PRD flag, even no-op handlers) → `--version` reads embedded ldflags var → `./build` script (handles `--release`, `--image` as stubs) → `.github/workflows/ci.yml` (build, test, vet, staticcheck, govulncheck).

**Deliverables**

- `go.mod`, `cmd/webv/main.go`, `internal/cli/flags.go` (single source of truth for every flag — table-driven against the PRD), `internal/version/version.go`.
- `./build` script (bash, sets `set -euo pipefail`, validated under zsh).
- `.github/workflows/ci.yml`.
- `internal/cli/flags_test.go` covering: every PRD flag exists with correct short/env/default; mutually-exclusive `--log-format None` + `--verbose` parses to an error; `--port` range validator rejects 0 and 65536.

**Smoke command:** `./build && ./bin/webv --version && ./bin/webv --help`

**Closes PRD bullets**
- `./bin/webv --version` prints a semver and exits 0.
- `./bin/webv --help` prints all CLI options.
- `./build` produces an executable at `./bin/webv` on Linux/WSL/macOS under bash and zsh.

---

## Session 2 — `v0.2.0` · YAML loader + env-var substitution + test-file model

**Frame**

- **Goal:** loader reads one or more YAML test files, builds typed `Request` / `Validation` / `InputJson` structs, substitutes `${VAR}` from env at load time, tolerates comments and case-insensitive property names. Pure data path — no HTTP yet.
- **Out of scope:** validation execution, HTTP, logging beyond loader errors, summary.
- **Failure condition:** YAML schema invented rather than derived directly from the PRD per-request fields (FR 9); silent default differs from the PRD (e.g., default `verb` ≠ `GET`, default `contentMediaType` ≠ `application/json`).

**RPI focus**

- **Research:** confirm `goccy/go-yaml` case-insensitivity option; pattern for substituting `${VAR}` against `os.LookupEnv`; how to report a missing variable as a parse error with file/line.
- **Plan:** types in `internal/loader/model.go` (mirror PRD field names exactly with `yaml` + `json` tags); `internal/loader/load.go` (read files, expand vars, decode, validate defaults); fixtures under `internal/loader/testdata/` covering: minimal GET, body + default content type, full validation block, missing var (must fail), comments, mixed-case keys.

**Deliverables**

- `internal/loader/{model,load,expand}.go` + tests.
- `internal/loader/testdata/*.yaml` fixtures.
- `--dry-run` wired to load and print resolved request structs.

**Smoke command:** `./bin/webv --dry-run --server http://example.com --files internal/loader/testdata/minimal.yaml`

**Closes PRD bullets**
- `${VAR}` placeholders in a test file are substituted from the environment; missing variables reported as a parse error.
- YAML parsing tolerates comments and case-insensitive property names (NFR Compatibility).
- Default `verb` is `GET`; default `contentMediaType` is `application/json` (FR 10, 11).

---

## Session 3 — `v0.3.0` · Run-once HTTP execution + basic TSV logging

**Frame**

- **Goal:** run-once mode sends real HTTP requests; per-request TSV record on stdout; `--timeout`, `--delay-start`, `--sleep`, `--url-prefix`, `--max-errors`, `--verbose`, `--verbose-errors`, `--dry-run` all functional. Exit codes for parse / unhandled / `--max-errors` correct. No validation engine yet (every response treated as pass).
- **Out of scope:** validation rules, log formats other than TSV (default + TsvMin), summary, run-loop, metrics.
- **Failure condition:** redirects followed; `http.Client` shared in a way that masks parallel-thread bugs; CLI flag override of env var not enforced.

**RPI focus**

- **Research:** `http.Client{CheckRedirect: func(...) error { return http.ErrUseLastResponse }}`; how to set `--timeout` on the client; ordering of `--delay-start` / first request / `--sleep`.
- **Plan:** `internal/httpx/client.go` (one client per server, redirect-disabled), `internal/runonce/run.go` (deterministic order, max-errors counter, exit-code wiring), `internal/logsink/tsv.go` (column order per PRD § Per-Request Log Fields), integration test using `httptest.NewServer`.

**Deliverables**

- `internal/httpx/`, `internal/runonce/`, `internal/logsink/tsv.go`.
- Integration test: spin up `httptest` server returning 200/301/500, assert exit codes and TSV output.

**Smoke command:** `./bin/webv --server https://httpbin.org --files tests/fixtures/smoke.yaml --verbose`

**Closes PRD bullets**
- Run-once exits non-zero on parse error, unhandled exception, `--max-errors` exceeded.
- `--dry-run` prints resolved parameters and sends no HTTP.
- HTTP redirects are not followed.
- CLI flag values override env-var values.

---

## Session 4 — `v0.4.0` · Validation engine

**Frame**

- **Goal:** all PRD validation rules (FR 13–15) execute against real responses; `failOnValidationError: true` causes immediate non-zero exit. Coverage gate ≥ 90% on `internal/validator/`.
- **Out of scope:** new log formats, summary, run-loop, metrics.
- **Failure condition:** any rule lacks a negative test fixture; nested object validation only handles one level; `forAny` short-circuits incorrectly.

**RPI focus**

- **Research:** how to traverse arbitrary JSON without losing position context (use `map[string]any` + recursion or `json.Decoder` token stream — pick one and commit); how to surface validation error messages with a JSONPath-like locator for `--verbose-errors`.
- **Plan:** `internal/validator/{status,contenttype,length,duration,body,jsonarray,jsonobject}.go`, each with a `Validate(resp, rule) []string` signature; table-driven tests per rule with positive + negative fixtures.

**Deliverables**

- Full `internal/validator/` package.
- Updated `internal/runonce/run.go` to call the validator and honor `failOnValidationError`.

**Smoke command:** `./bin/webv --server https://api.github.com --files tests/fixtures/github.yaml --verbose-errors`

**Closes PRD bullets**
- All validation rules (FR 13–15) produce documented pass/fail on hand-crafted fixtures.
- `failOnValidationError: true` causes immediate non-zero exit.

---

## Session 5 — `v0.5.0` · Log formats + summary + JUnit XML

**Frame**

- **Goal:** every PRD log format (`TsvMin`, `Tsv`, `Json`, `None`) and every summary format (`Tsv`, `Json`, `Xml`) implemented; JSON fields are camelCase; `--log-format None` + `--verbose` is a parse error; JUnit XML validates against the JUnit schema.
- **Out of scope:** run-loop, metrics, container, k8s.
- **Failure condition:** JSON field names drift from the PRD table; TSV column order drift; JUnit output rejected by a schema validator.

**RPI focus**

- **Research:** `slog.HandlerOptions.ReplaceAttr` for camelCase; minimal JUnit XSD to validate against (vendor a `tests/schema/junit.xsd`); existing Go JUnit XSD validators or just shell out to `xmllint` in tests.
- **Plan:** `internal/logsink/{tsv,json,none}.go`, `internal/summary/{aggregate,tsv,json,xml}.go`, schema validation test using `xmllint` from CI.

**Deliverables**

- All log + summary writers behind an `internal/logsink.Sink` interface.
- `tests/schema/junit.xsd` vendored; `internal/summary/xml_schema_test.go` runs `xmllint --schema` if present and skips otherwise.

**Smoke command:** `./bin/webv --server https://httpbin.org --files tests/fixtures/smoke.yaml --log-format Json --summary Xml`

**Closes PRD bullets**
- Default log format is `Tsv` (run-once) / `Json` (run-loop).
- `--log-format Json` emits camelCase fields per the PRD table.
- `--log-format None` + `--verbose` is a parse error.
- TSV column order matches PRD; `TsvMin` omits trailing metadata.
- `--summary Xml` validates against the JUnit schema.
- `region` and `zone` present when set / absent (`-` for TSV) when unset.

---

## Session 6 — `v0.6.0` · Run-loop + endpoints + signal handling + parallel servers

**Frame**

- **Goal:** `--run-loop` runs continuously (or for `--duration`); `--random` shuffles per iteration; multiple `--server` values spawn parallel goroutines each with its own `*http.Client`; HTTP listener on `--port` serves `/healthz`, `/readyz`, `/version`; SIGINT/SIGTERM trigger the PRD-defined graceful shutdown sequence (FR 42) with the 30 s force-exit deadline (FR 43).
- **Out of scope:** `/metrics` (next session), container, k8s.
- **Failure condition:** listener torn down before in-flight request completes; `/readyz` returns 200 before first iteration; force-exit deadline missing; parallel servers serialized through a shared client.

**RPI focus**

- **Research:** `context.Context` cancellation patterns for goroutine fan-out + signal-triggered drain; `http.Server.Shutdown` interaction with the listener lifecycle; readiness gating pattern (atomic bool flipped after first iteration starts and again before drain).
- **Plan:** `internal/runloop/loop.go`, `internal/httpd/server.go` (mux for endpoints), `internal/lifecycle/shutdown.go` (drain → wait inflight (timeout-bounded) → flush → stop listener → exit), test using `httptest` + `SIGTERM` injection via a context.

**Deliverables**

- Run-loop end-to-end working with three of the four endpoints.
- Integration test: start loop, hit `/healthz` 200 + `/readyz` 200 after first iteration, send SIGTERM, assert listener stays up through the drain and exits 0 inside 30 s.

**Smoke command:** `./bin/webv --server https://httpbin.org --files tests/fixtures/smoke.yaml --run-loop --duration 30`

**Closes PRD bullets**
- `/version` returns the semver with no surrounding whitespace.
- `/healthz` returns 200 while running.
- `/readyz` returns 200 only after the first iteration has begun.
- SIGTERM shutdown completes inside 30 s with status 0.

---

## Session 7 — `v0.7.0` · Prometheus metrics

**Frame**

- **Goal:** `/metrics` endpoint live; `WebVDuration` (Histogram, 10 exponential buckets factor 2 from 1 ms) and `WebVSummary` (Summary, φ = 0.9/0.95/0.99/1.0, 5 min sliding window) emitted with labels `status`, `server`, `failed`, plus `region` / `zone` only when set; process / Go runtime metrics exported.
- **Out of scope:** container, k8s.
- **Failure condition:** `region`/`zone` labels always present (cardinality blow-up); bucket / quantile config drifts from the PRD; metric names differ from `WebVDuration` / `WebVSummary`.

**RPI focus**

- **Research:** `prometheus/client_golang` `HistogramOpts.Buckets` + `SummaryOpts.Objectives`; conditional label registration via a small helper that returns a `prometheus.Labels` map missing the keys when empty.
- **Plan:** `internal/metrics/metrics.go` (label-name list assembled at init time from config), `internal/metrics/handler.go` (mount on the existing `internal/httpd` mux), test that scrapes `/metrics` with `httptest` and asserts label sets.

**Deliverables**

- `internal/metrics/` package + tests.
- README snippet showing the resulting Prometheus exposition.

**Smoke command:** `./bin/webv --server https://httpbin.org --files tests/fixtures/smoke.yaml --run-loop --region tx --zone austin & curl -s localhost:8080/metrics | grep WebV`

**Closes PRD bullets**
- `/metrics` returns Prometheus text-format output including `WebVDuration` and `WebVSummary`.
- `region` and `zone` labels appear only when the corresponding flag/env-var is non-empty.

---

## Session 8 — `v0.8.0` · Container + reproducible build + CVE scan

**Frame**

- **Goal:** `./build --image vX.Y.Z` produces a hardened multi-stage image (`webv:X.Y.Z` + `webv:latest`); the runtime stage contains only the `webv` binary on `gcr.io/distroless/static-debian12:nonroot` (pinned by digest); image is scanned with `trivy` and the build fails on HIGH/CRITICAL CVEs; `docker stop` returns cleanly within 30 s.
- **Out of scope:** k8s manifests.
- **Failure condition:** runtime stage contains a shell; non-root not enforced (UID ≠ 65532); CVE scan omitted or non-blocking; tags missing the `latest` alias.

**RPI focus**

- **Research:** distroless `static-debian12:nonroot` digest as of build day; `CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -trimpath -buildvcs=true -ldflags "-s -w -X ..."`; `trivy image --severity HIGH,CRITICAL --exit-code 1`.
- **Plan:** `Dockerfile` (two stages), `./build --image` (pulls digest, tags both, runs trivy), GitHub Actions `image-scan` job, hardened `docker run` smoke included in the build script as `./build --smoke`.

**Deliverables**

- `Dockerfile` + updated `./build`.
- `.github/workflows/ci.yml` gets an `image-scan` job.
- README "Run with Docker" snippet matching the PRD hardened example.

**Smoke command:** `./build --image v0.8.0 && docker run --rm --read-only --cap-drop ALL --security-opt no-new-privileges --user 65532:65532 -v $PWD/tests:/tests:ro webv:0.8.0 --version`

**Closes PRD bullets**
- Multi-stage image; runtime stage contains only the binary on distroless/scratch.
- Runs as `65532:65532`, `ENTRYPOINT ["/webv"]`, no shell.
- Build fails on HIGH/CRITICAL CVEs.
- Hardened `docker run` command works and exposes all four endpoints.
- Swapping mounted `/tests` changes test files without rebuild.
- `docker stop webv` returns inside 30 s without force-kill.

---

## Session 9 — `v0.9.0` · Kustomize WebV base + overlay `v0.1.0` + ServiceMonitor + Traefik IngressRoute + NetworkPolicy

**Frame**

- **Goal:** `kubectl apply -k deploy/webv/base` deploys a fully functional WebV pod (assuming Prometheus Operator CRDs + Traefik are present); `kubectl apply -k deploy/webv/overlays/v0.1.0` pins the image to `webv:0.1.0` with **only** a `newTag` override; all Pod Security `restricted` requirements (FR 63) satisfied; NetworkPolicy default-denies and allows only Traefik/Prometheus ingress + DNS/target egress.
- **Out of scope:** vendored Prometheus / Grafana / Operator CRDs (next session); 1.0 integration.
- **Failure condition:** any `kustomization.yaml` references a path outside its own component dir; any manifest hard-codes a cluster name; `restricted` admission rejects the pod; ServiceMonitor missing the `http` named port; IngressRoute missing rate-limit/IP-allowlist middleware on `/metrics`.

**RPI focus**

- **Research:** Pod Security `restricted` checklist (`runAsNonRoot`, `readOnlyRootFilesystem`, `cap drop ALL`, `seccompProfile: RuntimeDefault`, `automountServiceAccountToken: false`); Traefik `IngressRoute` + `Middleware` CRD shapes; `kubeconform --strict --schema-location default` for offline manifest validation.
- **Plan:** every file from the PRD layout: `namespace.yaml`, `serviceaccount.yaml`, `deployment.yaml`, `service.yaml`, `configmap-tests.yaml`, `servicemonitor.yaml`, `ingressroute.yaml` (+ middlewares), `networkpolicy.yaml`, `base/kustomization.yaml`, `overlays/v0.1.0/kustomization.yaml`. `kubeconform` job in CI.

**Deliverables**

- Entire `deploy/webv/` tree.
- `.github/workflows/ci.yml` gets a `kustomize-validate` job (`kustomize build` + `kubeconform`).

**Smoke command:** `kustomize build deploy/webv/base | kubeconform --strict && kustomize build deploy/webv/overlays/v0.1.0 | grep "image: webv:0.1.0"`

**Closes PRD bullets**
- `kubectl apply -k deploy/webv/base` produces a running pod (verified once Session 10 lands the dependencies).
- Overlay `v0.1.0` differs from base only in `newTag`.
- No `kustomization.yaml` references a path outside its component dir.
- No manifest hard-codes a cluster name.
- ServiceMonitor scrape via the `http` port at `/metrics`; no scrape annotations on Service/Pod.
- WebV IngressRoute exposes `/metrics`, `/healthz`, `/readyz`, `/version`; `/metrics` has rate-limit + IP-allowlist middleware.
- Deployment passes Pod Security `restricted` admission.
- NetworkPolicy default-deny + Traefik/Prometheus ingress + DNS/target egress.
- Production overlay can reference image by digest (pattern in place — actual digest pinned in Session 11).
- `webv` namespace labeled `pod-security.kubernetes.io/enforce: restricted`.

---

## Session 10 — `v0.10.0` · Vendored Prometheus, Grafana, Operator CRDs + dashboards + basic-auth IngressRoutes

**Frame**

- **Goal:** `deploy/servicemonitor-crd/`, `deploy/prometheus/`, `deploy/grafana/` are self-contained Kustomizations of vendored upstream YAML. Grafana and Prometheus each have a basic-auth-protected Traefik IngressRoute. WebV dashboards land as Grafana ConfigMaps consumed by the Grafana sidecar. Apply order documented in `deploy/README.md`.
- **Out of scope:** end-to-end k3d smoke (next session).
- **Failure condition:** any vendored content is a Helm template / Helm-rendered output; cross-component path references; basic-auth middleware missing.

**RPI focus**

- **Research:** latest pinned releases of `kube-prometheus` Operator CRDs (download a single bundle YAML and store it under `deploy/servicemonitor-crd/upstream/`); minimal Prometheus + Grafana deployment manifests (avoid kube-prometheus full stack to keep this fit-in-session); Traefik `Middleware` for basic-auth referencing a `Secret`.
- **Plan:** vendor source URLs + versions captured in each `kustomization.yaml`'s `# upstream:` comment header; per-component `README.md` documenting "to update: re-download from X at vY".

**Deliverables**

- Three new `deploy/<component>/` trees, each with `kustomization.yaml` + vendored manifests + per-component README.
- `deploy/README.md` documenting apply order.
- Updated `kustomize-validate` CI job to cover the new directories.

**Smoke command:** `kustomize build deploy/servicemonitor-crd | kubeconform --strict --skip ServiceMonitor && kustomize build deploy/prometheus | kubeconform --strict && kustomize build deploy/grafana | kubeconform --strict`

**Closes PRD bullets**
- No Helm chart / `helm install` / `helm template` anywhere under `deploy/` (verified by a CI grep gate).
- Grafana + Prometheus IngressRoutes require basic-auth middleware.
- `deploy/` apply order works for a fresh cluster (verified in Session 11).

---

## Session 11 — `v1.0.0` · End-to-end on k3d, image-digest pinning, GitOps-readiness verification, performance envelope

**Frame**

- **Goal:** fresh `k3d` cluster goes from zero to scraping WebV via Prometheus in one scripted run; production overlay references WebV image by digest (`webv@sha256:...`); a verification script proves the GitOps-readiness invariants (no cross-component paths, no cluster names, no Helm); a performance smoke confirms the 256 MiB / 0.5 CPU envelope holds under nominal load. Tag `v1.0.0`.
- **Out of scope:** new features. Only what's needed to close every remaining PRD acceptance bullet.
- **Failure condition:** any PRD acceptance bullet remains unchecked when the session ends; e2e script not idempotent.

**RPI focus**

- **Research:** `k3d cluster create webv -p "80:80@loadbalancer" -p "443:443@loadbalancer"`; reading the image digest after `./build --image` and rewriting the production overlay's `images:` `digest:` field; `kubectl top pod` or container `cgroup` reads for envelope evidence.
- **Plan:** `tests/e2e/up.sh` (cluster create → import image → apply order from `deploy/README.md` → wait for ready → curl `/metrics` from inside cluster → assert `WebVDuration` is non-empty); `tests/e2e/gitops-invariants.sh` (greps for forbidden patterns and asserts each component's `kustomize build` succeeds in isolation); `tests/e2e/envelope.sh` (run for 5 min, assert pod RSS ≤ 256 MiB and CPU ≤ 0.5).

**Deliverables**

- `tests/e2e/` scripts + a GitHub Actions `e2e-k3d` job that runs `up.sh` and `gitops-invariants.sh`.
- Production overlay `deploy/webv/overlays/v0.1.0/` updated to pin image by digest.
- Final PRD walk-through: every acceptance box checked.

**Smoke command:** `./tests/e2e/up.sh && ./tests/e2e/gitops-invariants.sh && ./tests/e2e/envelope.sh`

**Closes PRD bullets**
- Inserting an arbitrary `deploy/cluster-<name>/` wrapper reconciles without modifying component directories (verified by `gitops-invariants.sh` simulating the insertion).
- Production overlays reference image by digest.
- All previously deferred bullets confirmed by the end-to-end script.

---

## Parking Lot (not in any session — capture for later)

These are explicitly out of scope per the PRD or fall outside the 1.0.0 cut. Keep here so they don't drift into a session frame.

- OAuth/OIDC token helpers for tests.
- gRPC / WebSocket support.
- Browser-driven (Selenium/Playwright) tests.
- Alertmanager integration / alerting rules shipped in `deploy/`.
- Multi-arch image builds (arm64 + amd64) — additive, can land in a v1.1 session.
- `deploy/cluster-<name>/` real-world wiring (org-wide GitOps repo lives elsewhere).
- Test-authoring UI / linter for YAML test files.

---

## How to use this document

1. Before starting a session, copy the corresponding section into the next Session block in [docs/session-log.md](docs/session-log.md) as the **frame**.
2. Run the RPI cycle producing the three `.copilot-tracking/` artifacts.
3. Do the **fit check** honestly — every session above was sized for 90–120 min for a senior engineer with Copilot. If a session is bigger on your machine, cut from the "Deliverables" list, not from the "Closes PRD bullets" list. Re-frame and re-tag (`v0.N.1`) if needed.
4. Close with the ritual; check off the PRD bullets in [webv-prd.md](webv-prd.md) as you go. The PRD is the spec; this document is just a sequencing plan.
