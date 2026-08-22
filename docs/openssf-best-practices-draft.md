# OpenSSF Best Practices Badge — Self-Assessment Draft

> **How to use this document**
>
> 1. Go to <https://www.bestpractices.dev/en/projects/new> and sign in with your GitHub account.
> 2. Fill in the project URL (`https://github.com/tonyandrewmeyer/borescope`).
> 3. Work through each section below, copying the proposed answer and justification into the form.
> 4. Criteria marked **⚠ maintainer judgement required** need a human decision before submitting.
> 5. Submit — the badge ID will be returned and can be added to the README.
>
> **Badge submission still requires a human:** this draft was prepared for issue [#12](https://github.com/tonyandrewmeyer/borescope/issues/12)
> but the actual submission must be done at <https://bestpractices.coreinfrastructure.org/>.
>
> Criteria at the passing level only are covered here. Answers are one of:
> **Met** · **Unmet** · **N/A** · **?** (unsure / maintainer must decide).
>
> Criteria labelled *(MUST)* are required for the badge; those labelled *(SHOULD)* or *(SUGGESTED)*
> are recommended but not blocking.

---

## 1. Basics

### Basic project website content

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 1 | *(MUST)* `description_good` — the project website succinctly describes what the software does | **Met** | README.md lead paragraph: *"A natural shell for debugging Juju Kubernetes workload containers via Pebble."* Docs site at <https://tonyandrewmeyer.github.io/borescope/> provides further detail via tutorial and explanation pages. |
| 2 | *(MUST)* `interact` — the website explains how to obtain, give feedback on, and contribute to the software | **Met** | README.md has **Install** and **Usage** sections; `pyproject.toml` `[project.urls]` includes `Bug Tracker`; `CONTRIBUTING.md` documents the contribution workflow. |
| 3 | *(MUST)* `contribution` — contribution process is documented | **Met** | `CONTRIBUTING.md` at repo root covers development setup, running checks, spec-based tests, and design notes. |
| 4 | *(MUST)* `contribution_requirements` — acceptable contribution requirements are stated | **Met** | `CONTRIBUTING.md` explains the testing policy (POSIX spec citations required), states "By contributing, you agree your contributions are licensed under Apache-2.0," and describes divergence-labelling conventions. |

### FLOSS licence

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 5 | *(MUST)* `floss_license` — released under an OSI/FSF/Debian/Fedora-approved FLOSS licence | **Met** | Apache-2.0; declared in `LICENSE` file, `pyproject.toml` `license = "Apache-2.0"`, and PyPI classifiers. |
| 6 | *(SUGGESTED)* `floss_license_osi` — OSI-approved licence | **Met** | Apache-2.0 is OSI-approved. |
| 7 | *(MUST)* `license_location` — licence posted in a standard location | **Met** | `LICENSE` file at the repository root. |

### Documentation

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 8 | *(MUST)* `documentation_basics` — basic documentation covers installation, usage, and security | **Met** | README.md §Install + §Usage. Full docs site includes a tutorial (`docs/src/tutorial.md`), how-to guides (`docs/src/howto-*.md`), and a CLI reference. `SECURITY.md` documents the security policy. |
| 9 | *(MUST)* `documentation_interface` — reference documentation for external interfaces | **Met** | `docs/src/reference-cli.md` documents all CLI flags and options. `docs/src/reference-commands.md` documents every built-in shell command. |

### Other

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 10 | *(MUST)* `sites_https` — project sites support HTTPS | **Met** | <https://github.com/tonyandrewmeyer/borescope> and <https://tonyandrewmeyer.github.io/borescope/> both serve exclusively over HTTPS. |
| 11 | *(MUST)* `discussion` — project has a searchable discussion mechanism | **Met** | GitHub Issues (<https://github.com/tonyandrewmeyer/borescope/issues>) — publicly readable and searchable. |
| 12 | *(MUST)* `english` — documentation available in English | **Met** | All documentation and interface text is in English. |
| 13 | *(MUST)* `maintained` — project is actively maintained | **Met** | Active development (current version `0.1.0.dev1`). CI runs on every push and PR. Issues are responded to. |

---

## 2. Change Control

### Public version-controlled source repository

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 14 | *(MUST)* `repo_public` — publicly readable repository with a URL | **Met** | <https://github.com/tonyandrewmeyer/borescope> |
| 15 | *(MUST)* `repo_track` — repository tracks changes, authors, and timestamps | **Met** | Git — every commit records author, committer, and timestamp. |
| 16 | *(MUST)* `repo_interim` — interim versions between releases are in the repository | **Met** | All commits are public; the full history between any two releases is visible on GitHub. |
| 17 | *(SUGGESTED)* `repo_distributed` — uses distributed VCS | **Met** | Git. |

### Unique version numbering

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 18 | *(MUST)* `version_unique` — each release has a unique version identifier | **Met** | `pyproject.toml` `version` field; the publish workflow (`.github/workflows/publish.yaml`) triggers on `refs/tags/v*` tags, enforcing a unique identifier per release. |
| 19 | *(SUGGESTED)* `version_semver` — uses semantic or calendar versioning | **Met** | PEP 440 / SemVer convention (`major.minor.patch[.devN]`). |
| 20 | *(SUGGESTED)* `version_tags` — releases identified by VCS tags | **Met** | Publish workflow triggers on `v*` tags; each release is git-tagged. |

### Release notes

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 21 | *(MUST)* `release_notes` — human-readable release notes summarise changes per release | **?** ⚠ | No production releases exist yet (project is pre-v1.0, currently `0.1.0.dev1`). The publish workflow uses `gh release create --generate-notes`, which auto-generates notes from commit messages. **Maintainer action before first release:** ensure commit messages are descriptive enough to serve as release notes, or add a `CHANGELOG.md`. |
| 22 | *(MUST)* `release_notes_vulns` — release notes identify publicly known vulnerabilities fixed | **N/A** | No vulnerabilities have been publicly disclosed. Once any are fixed, the `SECURITY.md` process (CVE assignment, coordinated release) ensures they will appear in release notes. **Revisit when first security fix is released.** |

---

## 3. Reporting

### Bug-reporting process

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 23 | *(MUST)* `report_process` — bug reporting process is documented | **Met** | `pyproject.toml` `[project.urls]` `Bug Tracker` points to GitHub Issues. README §Documentation links to the project site which links back to the repository. |
| 24 | *(SUGGESTED)* `report_tracker` — uses an issue tracker | **Met** | GitHub Issues: <https://github.com/tonyandrewmeyer/borescope/issues> |
| 25 | *(MUST)* `report_responses` — majority of bug reports acknowledged within 2–12 months | **Met** ⚠ | Project is actively maintained. **Maintainer: confirm this is true based on historical response times.** |
| 26 | *(SHOULD)* `enhancement_responses` — responds to majority of enhancement requests | **Met** | GitHub Issues handles both bugs and enhancements. |
| 27 | *(MUST)* `report_archive` — publicly searchable archive of reports | **Met** | GitHub Issues are publicly searchable without an account. |

### Vulnerability report process

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 28 | *(MUST)* `vulnerability_report_process` — process for reporting vulnerabilities is published on the project site | **Met** | `SECURITY.md` at the repository root documents the process. |
| 29 | *(MUST)* `vulnerability_report_private` — if private reports are supported, a secure submission method is documented | **Met** | `SECURITY.md` directs reporters to [GitHub's private security advisory feature](https://github.com/tonyandrewmeyer/borescope/security/advisories/new). |
| 30 | *(MUST)* `vulnerability_report_response` — initial response to vulnerability reports within 14 days | **Met** | `SECURITY.md`: *"We aim to respond within 3 working days of your report."* |

---

## 4. Quality

### Working build system

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 31 | *(MUST)* `build` — working build system (if compilation needed) | **Met** | `uv build` (via hatchling) produces a wheel and sdist. The publish workflow (`.github/workflows/publish.yaml`) builds and publishes to PyPI automatically. |
| 32 | *(SUGGESTED)* `build_common_tools` — uses common, widely available build tools | **Met** | uv + hatchling — standard Python ecosystem tools. |
| 33 | *(MUST)* `build_floss_tools` — buildable using only FLOSS tools | **Met** | uv, hatchling, Python — all FLOSS. |

### Automated test suite

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 34 | *(MUST)* `test` — at least one automated test suite is released as FLOSS | **Met** | pytest (MIT licence) in `tests/`; spread tasks in `tests/spread/`. |
| 35 | *(SUGGESTED)* `test_invocation` — test suite is invocable in a standard way | **Met** | `uv run pytest` or `tox -e unit`; documented in `CONTRIBUTING.md`. |
| 36 | *(SUGGESTED)* `test_most` — tests cover most branches / functionality | **Met** | Unit tests with branch coverage (`--cov=borescope --cov-report=term-missing`), integration tests against a real Pebble binary, and POSIX-spec spread tasks in `tests/spread/` covering every built-in command. |
| 37 | *(SUGGESTED)* `test_continuous_integration` — CI implemented | **Met** | `.github/workflows/ci.yaml` runs lint, unit (across Python 3.11–3.14), integration, and docs checks on every push and PR. `.github/workflows/spread.yaml` runs the POSIX-conformance matrix. |

### New functionality testing

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 38 | *(MUST)* `test_policy` — policy requiring tests for major new functionality | **Met** | `CONTRIBUTING.md` §"Spec-based tests": *"Any change to a command, built-in, or shell-language feature MUST be accompanied by one or more spread tasks."* `CLAUDE.md` repeats the requirement. |
| 39 | *(MUST)* `tests_are_added` — evidence that the testing policy is followed | **Met** | Every built-in command has corresponding spread tasks in `tests/spread/` (cat, cd, cp, echo, env, exit, expand, find, grep, …). POSIX clause is cited in each task. |
| 40 | *(SUGGESTED)* `tests_documented_added` — testing policy is documented | **Met** | `CONTRIBUTING.md` §"Spec-based tests" and `CLAUDE.md` §"Spec-Based Tests" both document the policy. |

### Warning flags

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 41 | *(MUST)* `warnings` — compiler warnings or linting enabled | **Met** | ruff with an extensive ruleset (F, E, W, N, A, S, B, SIM, UP, D, RUF, PERF, FA, TC — see `pyproject.toml`), plus `ty` type checker; both run in CI. |
| 42 | *(MUST)* `warnings_fixed` — warnings are addressed | **Met** | CI (`tox -e lint`) fails on any ruff or ty finding. Per-file suppressions are documented with explanatory comments in `pyproject.toml`. |
| 43 | *(SUGGESTED)* `warnings_strict` — maximally strict with warnings | **Met** | ruff configured with `preview = true` and `explicit-preview-rules = true`; each suppression is justified in-file. |

---

## 5. Security

### Secure development knowledge

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 44 | *(MUST)* `know_secure_design` — at least one primary developer understands secure design principles (Saltzer–Schroeder) | **?** ⚠ | **Self-attestation required by the maintainer.** Supporting evidence: dependency-review workflow on every PR, OSV-Scanner and pip-audit weekly vulnerability scans, OIDC trusted publishing (no long-lived secrets), SHA-pinned GitHub Actions. |
| 45 | *(MUST)* `know_common_errors` — at least one primary developer knows common vulnerability types (e.g. OWASP Top 10) and mitigations | **?** ⚠ | **Self-attestation required by the maintainer.** Supporting evidence: ruff bandit rules (S*) enabled in CI to catch common Python security errors; dependency vulnerability scanning in place. |

### Basic cryptographic practices

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 46–54 | `crypto_*` (all crypto criteria) | **N/A** | borescope does not implement, negotiate, or store cryptographic material. It communicates via Unix domain sockets (Pebble API), relying on the OS and Juju security model. No passwords are stored. No cryptographic keys are generated. |

### Secured delivery

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 55 | *(MUST)* `delivery_mitm` — delivery mechanism counters MITM attacks | **Met** | Published to PyPI via HTTPS using OIDC trusted publishing (no long-lived token; `.github/workflows/publish.yaml`). Sigstore build-provenance attestations are generated for every release artefact. |
| 56 | *(MUST)* `delivery_unsigned` — cryptographic hashes not retrievable via unprotected HTTP | **Met** | All distribution channels (PyPI, GitHub Releases, Snap Store) use HTTPS. The publish workflow additionally produces a CycloneDX SBOM and attaches Sigstore attestations to each release. |

### Publicly known vulnerabilities fixed

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 57 | *(MUST)* `vulnerabilities_fixed_60_days` — no unpatched medium-or-higher vulnerabilities older than 60 days | **Met** | No known public vulnerabilities. OSV-Scanner (`.github/workflows/security.yaml`) and pip-audit scan the dependency tree weekly and on every PR; Dependabot raises security PRs automatically. |
| 58 | *(SUGGESTED)* `vulnerabilities_critical_fixed` — critical vulnerabilities fixed rapidly | **Met** | `SECURITY.md` commits to a 90-day resolution target; critical issues would be prioritised above that. |

### Other security

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 59 | *(MUST)* `no_leaked_credentials` — no valid private credentials in the public repository | **Met** | All secrets use GitHub Actions secrets or OIDC (`id-token: write`). `SNAPCRAFT_STORE_CREDENTIALS` is referenced only via `${{ secrets.SNAPCRAFT_STORE_CREDENTIALS }}`. No hardcoded tokens or passwords anywhere in the source. |

---

## 6. Analysis

### Static code analysis

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 60 | *(MUST)* `static_analysis` — at least one static analysis tool applied before each major release | **Met** | ruff (includes bandit-equivalent S rules), ty (type checker), and zizmor (GitHub Actions workflow security analysis) all run on every push and PR. |
| 61 | *(SUGGESTED)* `static_analysis_common_vulnerabilities` — tools detect common security vulnerabilities | **Met** | ruff S* rules (bandit) detect injection patterns, hardcoded secrets, subprocess misuse, insecure deserialization, etc. zizmor detects Actions-specific vulnerabilities (script injection, excessive permissions). |
| 62 | *(MUST)* `static_analysis_fixed` — medium-or-higher severity static-analysis findings are fixed in a timely manner | **Met** | CI blocks merge on any ruff, ty, or zizmor finding; the only suppressions are documented per-file with explanatory comments. |
| 63 | *(SUGGESTED)* `static_analysis_often` — static analysis on every commit or daily | **Met** | `ci.yaml` runs ruff + ty on every push and PR. `zizmor.yaml` runs zizmor on every push and PR. OpenSSF Scorecard (`scorecard.yaml`) and OSV-Scanner (`security.yaml`) run weekly. |

### Dynamic code analysis

| # | Criterion | Answer | Justification / evidence |
|---|-----------|--------|--------------------------|
| 64 | *(SUGGESTED)* `dynamic_analysis` — dynamic analysis applied before each major release | **Met** | Integration tests run against a real Pebble binary (`ci.yaml` integration job; `tox -e integration`). Spread tasks (`tests/spread/`) run every built-in command in a real Ubuntu VM with a real Pebble instance. |
| 65 | *(SUGGESTED)* `dynamic_analysis_unsafe` — memory-safety dynamic tools used where applicable | **N/A** | Python — no native C extensions; memory safety is managed by the CPython runtime. |
| 66 | *(SUGGESTED)* `dynamic_analysis_enable_assertions` — assertions enabled during dynamic analysis | **Met** | Python assertions are enabled by default (no `-O` flag). pytest does not suppress assertions. |
| 67 | *(SUGGESTED)* `dynamic_analysis_fixed` — medium-or-higher dynamic analysis findings are fixed in a timely manner | **Met** | No known dynamic-analysis findings. CI is blocking; any integration or spread failure blocks merge. |

---

## Summary for the maintainer

### Items requiring maintainer action before submitting

| # | Item | What to do |
|---|------|------------|
| A | `know_secure_design` (criterion 44) | Self-attest on the form that you are familiar with secure design principles (e.g. Saltzer–Schroeder, OWASP). |
| B | `know_common_errors` (criterion 45) | Self-attest on the form that you are familiar with common vulnerability types relevant to Python CLI tools (e.g. OWASP Top 10, CWE Top 25). |
| C | `release_notes` (criterion 21) | Before the first production release (v1.0), decide whether auto-generated GitHub Release notes are sufficient or whether a `CHANGELOG.md` is needed. Update this entry to **Met** once a release exists. |
| D | `report_responses` (criterion 25) | Confirm that the historical response rate to bug reports is consistent with "majority acknowledged within 2–12 months." |

### Criteria already clearly met (no action needed)

All other passing-level criteria are met by existing repository artefacts:
- Licence: `LICENSE` (Apache-2.0)
- Security policy: `SECURITY.md`
- Contributing guide: `CONTRIBUTING.md`
- Code of conduct: `CODE_OF_CONDUCT.md`
- CI/CD: `.github/workflows/ci.yaml`, `spread.yaml`, `security.yaml`, `scorecard.yaml`, `zizmor.yaml`
- Dependency updates: `.github/dependabot.yaml` (GitHub Actions monthly, Python security-only daily)
- Dependency vulnerability scanning: OSV-Scanner + pip-audit (weekly + every PR)
- Static analysis: ruff (bandit rules), ty, zizmor
- Build provenance: Sigstore attestations + CycloneDX SBOM on every release
- Trusted publishing: OIDC (no long-lived tokens)

### Suggested badge-ID placement

Once the badge is earned, add the following to `README.md` (replace `<ID>` with the project ID from bestpractices.dev):

```markdown
[![OpenSSF Best Practices](https://www.bestpractices.dev/projects/<ID>/badge)](https://www.bestpractices.dev/projects/<ID>)
```
