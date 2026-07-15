# Claude Code — Comprehensive Code & Architecture Review Prompt

> **How to use:** Copy the prompt block below and run it in Claude Code from the root of the
> third-party application repository. All output files will be written relative to `./review/`.

---

## Prompt (paste this into Claude Code)

```
You are acting as a senior review team composed of three specialists:
  1. **Solution Architect** — evaluates architecture, design patterns, scalability, and technical debt.
  2. **Security Engineer** — evaluates application security (OWASP Top 10 + beyond), secrets, auth, and data exposure.
  3. **Engineering Lead** — evaluates code quality, maintainability, test coverage, dependency health, and production readiness.

Your mission is to perform a full, evidence-based review of the codebase in the current working directory and produce a structured set of findings that will be used to decide:
  → **Option A: Move to production as-is (with mitigations)**
  → **Option B: Refactor before production**

---

## PHASE 1 — Discovery & Inventory

Start by understanding what you are reviewing. Execute the following steps in order:

1. List the root directory tree (max 3 levels deep).
2. Detect the tech stack: languages, frameworks, runtimes, build tools, package managers.
3. Read every configuration file: `.env*`, `docker-compose*`, `Dockerfile*`, `*.config.*`, `*.yaml`, `*.yml`, `*.toml`, `*.ini`, CI/CD pipelines.
4. Read `package.json` / `requirements.txt` / `pom.xml` / `go.mod` (whichever apply) and list all direct dependencies with their versions.
5. Identify entry points: `main.*`, `index.*`, `app.*`, `server.*`, `lambda_handler`, etc.
6. Map the high-level module/package structure and how they interconnect.
7. Identify the data persistence layer(s): databases, caches, file storage, third-party APIs.
8. Look for existing documentation: `README*`, `ARCHITECTURE*`, `docs/`, `ADR/`, `wiki/`.

Write a concise **Project Inventory** into `./review/00_project_inventory.md` using the template provided in that file.

---

## PHASE 2 — Solution Architecture Review

Evaluate the following dimensions. For each finding, note the file(s) and line number(s) that evidence it.

### 2a. Architecture Style & Patterns
- What architectural pattern is used (monolith, microservices, serverless, MVC, hexagonal, event-driven, etc.)?
- Is it appropriate for the stated purpose? Are anti-patterns present?
- Is the separation of concerns clear (presentation / business logic / data access)?
- Is there a defined domain model or is logic scattered?

### 2b. Scalability & Performance
- Are there obvious bottlenecks (N+1 queries, missing indexes, synchronous blocking I/O)?
- Is horizontal scaling possible without code changes?
- Is caching used appropriately?
- Are async/queue patterns used where needed?

### 2c. Resilience & Reliability
- Are there retry strategies, circuit breakers, timeouts?
- How are external service failures handled?
- Is there graceful degradation?
- Are health-check endpoints present?

### 2d. Observability
- Is structured logging implemented? Are log levels appropriate?
- Is distributed tracing present?
- Are metrics / APM hooks present?
- Is there alerting configuration?

### 2e. Data Architecture
- Is the data model normalized correctly?
- Are there missing constraints, indexes, or foreign keys?
- Is data migration strategy defined?
- Is PII/sensitive data handled with appropriate controls (encryption at rest, masking in logs)?

### 2f. Technical Debt & Maintainability
- Are there TODO / FIXME / HACK comments that indicate known issues?
- Is the code DRY or does significant duplication exist?
- Are modules cohesive and loosely coupled?
- Is the codebase reasonably navigable for a new engineer?

Write findings into `./review/01_architecture_review.md`.

---

## PHASE 3 — Security Review

### 3a. Secrets & Credentials
- Scan for hardcoded secrets, API keys, passwords, tokens in source code, configs, and committed `.env` files.
- Check if `.env` files are in `.gitignore`.
- Verify secrets are loaded from environment variables or a vault, not from code.

### 3b. Authentication & Authorization
- Is authentication implemented? Which mechanism (JWT, sessions, OAuth2, API keys)?
- Are JWT secrets strong and stored securely? Is algorithm `none` rejected?
- Is authorization enforced at every protected endpoint (not just in the frontend)?
- Is there privilege escalation risk (IDOR, missing ownership checks)?
- Are admin/internal routes protected?

### 3c. OWASP Top 10 (2021)
Check for evidence of each:
- **A01 Broken Access Control** — missing authz, IDOR, CORS misconfiguration.
- **A02 Cryptographic Failures** — weak algorithms (MD5/SHA1 for passwords), no TLS enforcement, plaintext sensitive data.
- **A03 Injection** — SQL injection, NoSQL injection, command injection, LDAP injection, template injection.
- **A04 Insecure Design** — missing rate limiting, no account lockout, insecure password reset flows.
- **A05 Security Misconfiguration** — default creds, verbose error messages leaking stack traces, debug mode in production configs, open cloud storage buckets.
- **A06 Vulnerable & Outdated Components** — flag dependencies with known CVEs (check versions against known vulnerability data in your training).
- **A07 Identification & Authentication Failures** — weak passwords allowed, no MFA support, session fixation.
- **A08 Software & Data Integrity Failures** — deserialization of untrusted data, unsigned packages.
- **A09 Security Logging & Monitoring Failures** — failed logins not logged, no audit trail for sensitive actions.
- **A10 Server-Side Request Forgery (SSRF)** — user-controlled URLs fetched server-side.

### 3d. Application-Specific Risks
- Input validation: are all inputs validated and sanitized server-side?
- Output encoding: is data escaped before rendering (XSS)?
- File uploads: are MIME types and file sizes validated? Are uploads stored outside the web root?
- Mass assignment: can users set fields they should not?
- Rate limiting & DoS: are expensive endpoints protected?
- Dependency integrity: are lock files present and committed?

### 3e. Infrastructure & Deployment Security
- Are Dockerfiles running as non-root?
- Are ports minimally exposed?
- Are there open debug ports or admin interfaces?
- Is HTTPS enforced? Are security headers present (CSP, HSTS, X-Frame-Options)?

Write findings into `./review/02_security_review.md`, using severity levels: **CRITICAL / HIGH / MEDIUM / LOW / INFO**.

---

## PHASE 4 — Code Quality Review

### 4a. Code Standards
- Is there a linter/formatter configuration? Is it enforced (pre-commit hooks, CI gate)?
- Is naming consistent and meaningful?
- Are functions/methods small and single-purpose?
- Is complexity reasonable (cyclomatic complexity)?

### 4b. Error Handling
- Are errors handled explicitly or silently swallowed?
- Are user-facing error messages safe (no stack traces, no internal paths)?
- Is there a global error handler for unhandled exceptions/promises?

### 4c. Test Coverage
- Are there unit tests? Integration tests? E2E tests?
- What is the approximate coverage (if measurable)?
- Are critical paths (auth, payments, data mutations) tested?
- Are tests meaningful or just coverage padding?

### 4d. Dependency Health
- Are dependencies pinned to specific versions?
- Are there unnecessary or duplicate dependencies?
- Are any dependencies abandoned (no recent commits, no maintainer)?
- Are dev dependencies leaking into production builds?

### 4e. Build & Deployment Pipeline
- Is there a CI/CD pipeline? Does it run tests and security scans?
- Are environment-specific configs separated from code?
- Is the production build reproducible?

Write findings into `./review/03_code_quality_review.md`.

---

## PHASE 5 — Risk Register

For every finding across all phases, create a risk register entry with:
- **ID** (e.g., RISK-001)
- **Category** (Architecture / Security / Code Quality / Dependency / Operational)
- **Title** (one line)
- **Description** (what the issue is and why it matters)
- **Evidence** (file:line or config key)
- **Severity** (CRITICAL / HIGH / MEDIUM / LOW)
- **Likelihood** (HIGH / MEDIUM / LOW)
- **Risk Score** = Severity × Likelihood (use: CRITICAL×HIGH=10, HIGH×HIGH=8, HIGH×MEDIUM=6, MEDIUM×HIGH=5, MEDIUM×MEDIUM=3, LOW×any=1–2)
- **Recommendation** (concrete remediation action)
- **Effort to fix** (Hours / Days / Weeks)
- **Blocks production?** (YES / NO / CONDITIONAL)

Write the full register into `./review/04_risk_register.md` sorted by Risk Score descending.

---

## PHASE 6 — Executive Summary & Go/No-Go Recommendation

Write `./review/05_executive_summary.md` with:

1. **Application Overview** — what it does, tech stack, size (files/LOC estimate).
2. **Review Scope** — what was examined, what was out of scope.
3. **Key Findings Summary** — top 5 most impactful findings.
4. **Risk Dashboard** — counts by severity and category (a simple table).
5. **Production Readiness Score** — rate each dimension 1–5:
   - Architecture & Design
   - Security Posture
   - Code Quality
   - Test Coverage
   - Operational Readiness
   - Overall (weighted average)
6. **Go / No-Go Recommendation** with explicit rationale:
   - If GO: list mandatory pre-launch mitigations and monitoring requirements.
   - If NO-GO: list the blocking issues, estimated refactor effort, and a recommended remediation roadmap (P0/P1/P2 priorities).
7. **Immediate Action Items** — the 3–5 things that must happen before any next step.

---

## OUTPUT RULES

- Always write findings to the markdown files, not just to the chat.
- Every finding must reference at least one specific file or configuration key.
- Do not hallucinate vulnerabilities — only report what is evidenced in the code.
- Do not report theoretical risks as CRITICAL unless there is a clear exploit path.
- If a file or directory cannot be read, note it in the inventory and skip gracefully.
- Use the exact markdown templates provided in each output file (they will be pre-created).
- After all phases complete, print a single summary table to chat listing each output file and its finding counts.
```

---

## Files this prompt will create

| File | Contents |
|---|---|
| `./review/00_project_inventory.md` | Tech stack, modules, dependencies, entry points |
| `./review/01_architecture_review.md` | Architecture, scalability, resilience, data, debt |
| `./review/02_security_review.md` | OWASP Top 10 + secrets + infra security |
| `./review/03_code_quality_review.md` | Standards, errors, tests, dependencies, CI/CD |
| `./review/04_risk_register.md` | All risks ranked by score |
| `./review/05_executive_summary.md` | Go/No-Go recommendation + action plan |

---

## Tips for running in Claude Code

- Run from the **root of the repository**: `cd /path/to/app && claude`
- If the repo is large (+50k LOC), add this line to the prompt: *"Prioritize reading entry points, auth modules, database layers, and API route handlers first."*
- If you have a specific concern (e.g., payment processing, PII handling), append it: *"Pay special attention to the payment flow in `src/payments/`."*
- Grant Claude Code file-write permission so it can create the `./review/` folder and all output files.
