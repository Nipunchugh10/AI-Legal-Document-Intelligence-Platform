# 🔐 VIBE APP SECURITY AUDIT — BRUTAL PROMPT SET
> **Purpose:** A complete set of CLI-agent prompts for ruthlessly auditing any vibe-coded application across every known security domain.
> **Usage:** Feed each prompt individually to your CLI AI agent (Claude Code, Cursor Agent, Aider, etc.) with the full codebase in context.
> **Philosophy:** Assume everything is broken until proven otherwise. Trust nothing. Question every line.

---

## ⚠️ HOW TO USE THESE PROMPTS

1. Open your CLI agent (e.g., `claude`, `cursor`, `aider`) in the **root of your project**.
2. Paste each prompt **one at a time** and let the agent complete its full analysis before moving to the next.
3. Collect all findings in a `SECURITY_REPORT.md` file.
4. For each finding: **fix → re-run the same prompt → verify clean**.

---

## 🔴 PROMPT 1 — HARDCODED SECRETS & CREDENTIAL LEAKAGE

```
You are a brutal security auditor. Scan every single file in this codebase — including config files, environment files, test files, scripts, Dockerfiles, CI/CD YAML files, README files, comments, and any file not in .gitignore — for hardcoded secrets, credentials, API keys, tokens, passwords, database connection strings, private keys, OAuth secrets, JWT secrets, webhook URLs with tokens, and AWS/GCP/Azure credentials.

Do NOT rely on file extension alone. Search inside .js, .ts, .py, .env, .json, .yaml, .yml, .toml, .ini, .sh, .md, .txt, .sql, .config, .lock, and every other file type.

Look for:
- Strings matching patterns like sk-, pk-, AIza, AKIA, ghp_, xox, Bearer, password=, secret=, token=, api_key=, private_key
- Base64-encoded strings that may decode to credentials
- Hex strings that may be secrets
- Comments like "// TODO: remove this before prod" near sensitive values
- Default credentials (admin/admin, root/root, test/test)
- Any value that looks like a UUID being used as a static secret
- Credentials committed in git history (check via `git log -p | grep -i -E "password|secret|key|token"`)

For every finding: report the file path, line number, type of secret, severity (Critical/High/Medium), and recommended fix.
If nothing is found, explain exactly what you searched and how you confirmed it's clean.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
For each hardcoded secret found, immediately remove it from the file and replace with an environment-variable reference, then rotate the secret on its platform:
  # Remove secret from file and move to .env
  # e.g.  API_KEY=your_real_key  →  API_KEY=${API_KEY}
  git rm --cached <file>          # stop tracking if it was a .env file
  echo ".env" >> .gitignore
  # Rotate the key on its platform (GitHub, AWS, etc.) — the git history exposure is permanent.
  # To scrub history: npx -y git-filter-repo --path <file> --invert-paths
```

---

## 🔴 PROMPT 2 — INJECTION ATTACKS (SQL, NoSQL, LDAP, OS COMMAND, XPATH)

```
You are a penetration tester. Audit every data input point in this codebase for injection vulnerabilities.

SQL Injection: Find every database query. Check if user-controlled input is concatenated directly into SQL strings, even partially. Check for:
- String interpolation in queries (`SELECT * FROM users WHERE id = ${req.params.id}`)
- ORM raw query escape hatches (Sequelize.literal, Knex.raw, Django.extra, ActiveRecord.execute)
- Second-order SQL injection (data stored then used unsanitized in later queries)
- Stored procedures that re-concatenate input

NoSQL Injection: If MongoDB, Redis, Firebase, or similar is used — check for:
- Objects passed directly as query filters from user input (`db.find(req.body)`)
- Operator injection via `$where`, `$regex`, `$or`, `$gt` etc. passed from client
- Prototype pollution enabling query manipulation

OS Command Injection: Find every call to exec(), spawn(), system(), popen(), subprocess, child_process, os.system, shell=True, and similar. Check if any user-controlled data reaches these calls.

LDAP Injection: If LDAP is used, check all search filters for unsanitized input.

XPath Injection: Find all XML/XPath parsing and check for dynamic query construction.

For each finding: show the exact vulnerable code path, how an attacker could exploit it with a real payload example, and the exact fix (parameterized queries, allowlisting, input validation).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
Replace every raw query interpolation with a parameterized equivalent:
  # Node.js / Knex example:
  # BEFORE:  db.raw(`SELECT * FROM users WHERE id = ${req.params.id}`)
  # AFTER:   db.raw('SELECT * FROM users WHERE id = ?', [req.params.id])
  # Python / SQLAlchemy:
  # BEFORE:  session.execute(f"SELECT * FROM users WHERE id = {uid}")
  # AFTER:   session.execute(text("SELECT * FROM users WHERE id = :id"), {"id": uid})
  # OS command — replace exec/system with argument arrays (no shell=True):
  # BEFORE:  subprocess.run(f"convert {filename}", shell=True)
  # AFTER:   subprocess.run(["convert", filename])   # shell=False by default
```

---

## 🔴 PROMPT 3 — AUTHENTICATION & SESSION MANAGEMENT FLAWS

```
You are a security engineer. Perform a complete audit of all authentication and session management logic in this codebase.

Check for:
- Passwords stored in plaintext or with weak hashing (MD5, SHA1, unsalted SHA256)
- Missing bcrypt/argon2/scrypt with appropriate work factors
- JWT tokens: verify algorithm is not "none", HS256 secret is not weak/hardcoded, expiry is enforced, tokens are properly invalidated on logout
- Session tokens: check entropy (must be cryptographically random, ≥128 bits), check if they are regenerated after login (session fixation prevention), check secure+httpOnly+SameSite cookie flags
- Missing or bypassable authentication on protected routes — trace every route and middleware to confirm auth is actually enforced
- Authentication logic that can be bypassed with type juggling (== vs === in JS, loose comparisons in PHP)
- Race conditions in authentication flows
- Password reset flaws: predictable tokens, no expiry, token not invalidated after use, user enumeration via different error messages
- "Remember me" functionality: check token storage and expiry
- OAuth/SSO flows: check state parameter for CSRF protection, check redirect_uri validation
- Multi-factor authentication: check if it can be bypassed by directly accessing post-MFA endpoints
- Account lockout: is brute force protection in place? Is it bypassable?
- Timing attacks: are string comparisons constant-time for secrets?

Show the full auth flow per route, highlight every gap, and provide corrected code.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Replace weak password hashing (MD5/SHA1) with bcrypt:
  # Node.js:  npm install bcrypt  →  bcrypt.hash(password, 12)
  # Python:   pip install bcrypt  →  bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12))
  # Enforce httpOnly + Secure + SameSite on session cookies:
  # Express:  app.use(session({ cookie: { httpOnly: true, secure: true, sameSite: 'strict' } }))
  # Fix JWT alg:none vulnerability — pin the algorithm explicitly:
  # jwt.verify(token, secret, { algorithms: ['HS256'] })
  # Add session regeneration after login:
  # req.session.regenerate(() => { req.session.userId = user.id; res.redirect('/dashboard'); })
```

---

## 🔴 PROMPT 4 — AUTHORIZATION & BROKEN ACCESS CONTROL

```
You are a red team engineer. Audit this codebase for every possible broken access control vulnerability.

Check for:
- Insecure Direct Object Reference (IDOR): Find every endpoint that accepts an ID (user ID, order ID, file ID, document ID). Verify that ownership is checked server-side, not just client-side. A user with ID 5 must never be able to access /api/orders/6 unless they own it.
- Missing role checks: Find every admin-only, moderator-only, or privileged route. Verify the role check is on the SERVER, not just hidden from the UI.
- Privilege escalation: Can a regular user modify their own role field? Can they pass `role: "admin"` in a request body and have it accepted?
- Path traversal on file access: Any endpoint serving files — check if `../../etc/passwd` style input is possible.
- Horizontal privilege escalation: Can user A modify user B's data by changing an ID?
- Forced browsing: Are there routes that are not linked from the UI but are accessible if you know the URL?
- Function-level access control: Are destructive or sensitive functions (delete user, export all data, send emails) protected?
- JWT/token claims: Can a user modify their own token claims to gain elevated access? Is the signature properly validated?
- GraphQL: If used, check for introspection enabled in production, batching attacks, and missing field-level authorization.

Map every route → required role → where role is checked → whether it can be bypassed. Flag every gap.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add server-side ownership check to every ID-based endpoint:
  # BEFORE:  const order = await Order.findById(req.params.id)
  # AFTER:   const order = await Order.findOne({ _id: req.params.id, userId: req.user.id })
  # if (!order) return res.status(403).json({ error: 'Forbidden' })
  # Block mass-assignment of privileged fields — explicitly allowlist fields:
  # Express + Mongoose:  const allowed = ['name','email'];  const update = _.pick(req.body, allowed);
  # Strip role/isAdmin from user-submitted body before saving:
  # delete req.body.role; delete req.body.isAdmin;
```

---

## 🔴 PROMPT 5 — CROSS-SITE SCRIPTING (XSS)

```
You are an XSS specialist. Audit every place where user-controlled data is rendered in this codebase.

Check for:
- Reflected XSS: Every query parameter, form field, URL segment, or header value that gets rendered back in an HTML response without encoding.
- Stored XSS: Every piece of user-generated content stored in the database and then rendered (comments, usernames, bios, post content, file names, metadata).
- DOM-based XSS: Every place where JavaScript reads from location.hash, location.search, document.referrer, document.URL, postMessage, localStorage, cookies — and then writes to innerHTML, outerHTML, document.write, eval(), setTimeout(string), setInterval(string), insertAdjacentHTML.
- Template injection: In React — check for dangerouslySetInnerHTML. In Vue — check for v-html. In Angular — check for bypassSecurityTrustHtml. In server templates (Jinja2, EJS, Handlebars) — check for unescaped `{{{ }}}` or `| safe` filters.
- Attribute injection: User data placed in href, src, onerror, onload, or other event attributes.
- SVG/XHTML XSS: File uploads that accept SVG — SVG can contain inline scripts.
- Content-Type sniffing XSS: API endpoints returning user content — verify Content-Type is set correctly and X-Content-Type-Options: nosniff is present.
- CSP: Is a Content-Security-Policy header present? Is it strong enough? Does it use 'unsafe-inline' or 'unsafe-eval'?

For each finding: show the source (where input enters), the sink (where it's rendered), and the exact attack payload that would work. Then show the correct encoding/sanitization fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # React — replace dangerouslySetInnerHTML with safe rendering:
  # BEFORE:  <div dangerouslySetInnerHTML={{ __html: userContent }} />
  # AFTER:   import DOMPurify from 'dompurify';  <div dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(userContent) }} />
  # npm install dompurify
  # Add a strong Content-Security-Policy header (Node/Express):
  # npm install helmet
  # app.use(helmet.contentSecurityPolicy({ directives: { defaultSrc: ["'self'"], scriptSrc: ["'self'"] } }))
  # Fix DOM XSS — replace innerHTML with textContent:
  # BEFORE:  element.innerHTML = userInput
  # AFTER:   element.textContent = userInput
```

---

## 🔴 PROMPT 6 — CROSS-SITE REQUEST FORGERY (CSRF)

```
You are a security auditor. Audit this codebase for CSRF vulnerabilities across all state-changing operations.

Check for:
- Every POST, PUT, PATCH, DELETE endpoint: Is a CSRF token required? Is it validated server-side on every request?
- Cookie-based authentication without CSRF protection: If the app uses session cookies, every state-changing request MUST have a CSRF token or use SameSite=Strict/Lax cookies (and explain why Lax still has edge cases).
- SameSite cookie attribute: Is it set? Is it Strict or Lax? Is there a fallback for older browsers?
- CORS and CSRF interaction: A permissive CORS policy does NOT replace CSRF protection.
- GraphQL mutations: Are they protected against CSRF?
- JSON endpoints: Verify they reject Content-Type: application/x-www-form-urlencoded (attackers can CSRF JSON endpoints if Content-Type isn't enforced).
- Login CSRF: Can an attacker force a user to log in as the attacker's account?
- Logout CSRF: Can an attacker force a user to log out?

List every state-changing endpoint and its CSRF protection status. If no CSRF protection exists anywhere, flag this as Critical and provide an implementation plan.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add CSRF protection to Express app in minutes:
  # npm install csrf-csrf
  # const { doubleCsrfProtection } = require('csrf-csrf');
  # app.use(doubleCsrfProtection);   // apply to all state-changing routes
  # Set SameSite=Strict on all session cookies:
  # app.use(session({ cookie: { sameSite: 'strict', httpOnly: true, secure: true } }))
  # For Django — CSRF middleware is already included; ensure it is NOT disabled:
  # MIDDLEWARE must include: 'django.middleware.csrf.CsrfViewMiddleware'
```

---

## 🔴 PROMPT 7 — SENSITIVE DATA EXPOSURE & ENCRYPTION

```
You are a data security auditor. Find every place in this codebase where sensitive data is handled, stored, transmitted, or logged.

Check for:
- PII in logs: Search all logging calls (console.log, logger.info, print, log.debug etc.) for email, password, SSN, credit card numbers, tokens, phone numbers, addresses, DOB.
- Sensitive data in error messages returned to clients: Stack traces, database errors, file paths, internal IP addresses, user data.
- Data in transit: Is HTTPS enforced everywhere? Are there any HTTP URLs hardcoded? Is HSTS configured?
- Encryption at rest: Are passwords hashed (not encrypted)? Is sensitive data in the database encrypted at the field level where required (PII, financial data)?
- Weak encryption: MD5, SHA1, DES, RC4, ECB mode — these are broken. Find every crypto call and verify algorithm strength.
- Insecure random: Math.random(), rand(), random.random() used for security-sensitive purposes (tokens, OTPs, session IDs). Must be crypto.randomBytes(), secrets.token_hex(), etc.
- Sensitive data in URLs: Tokens, passwords, user IDs passed as query parameters (logged in server logs, browser history, Referer headers).
- Sensitive data in localStorage/sessionStorage: These are accessible to any JavaScript on the page. Tokens stored here are XSS-vulnerable.
- Cache-Control headers: Are responses containing sensitive data marked no-store, no-cache?
- Database backups and exports: Any scripts that dump or export data — where do they write it? Is it accessible?

Report every finding with data classification (PII, financial, auth credential) and remediation steps.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Remove PII from logs — mask sensitive fields before logging:
  # const safeUser = { ...user, password: '[REDACTED]', token: '[REDACTED]' };
  # logger.info('User action', safeUser);
  # Force HTTPS and set HSTS (Express/Helmet):
  # app.use(helmet.hsts({ maxAge: 31536000, includeSubDomains: true }));
  # app.use((req, res, next) => { if (!req.secure) return res.redirect('https://' + req.headers.host + req.url); next(); });
  # Add no-store Cache-Control to sensitive API responses:
  # res.set('Cache-Control', 'no-store, no-cache, must-revalidate, private');
  # Replace Math.random() with cryptographic random:
  # Node.js:  require('crypto').randomBytes(32).toString('hex')
  # Python:   import secrets; secrets.token_hex(32)
```

---

## 🔴 PROMPT 8 — FILE UPLOAD VULNERABILITIES

```
You are an exploit developer. Audit every file upload feature in this codebase for vulnerabilities.

Check for:
- MIME type validation: Is it done server-side or only client-side? Client-side validation is bypassed trivially.
- File extension allowlisting: Is it allowlist (only .jpg, .png allowed) or blacklist (block .php, .exe)? Blacklists are always incomplete.
- Content validation: Is the actual file content inspected (magic bytes) or just the extension/MIME type?
- Malicious file execution: Can uploaded files be accessed via a URL? Can a PHP/Python/JS file be uploaded and then executed by the server?
- Path traversal in filenames: Is the filename sanitized? `../../evil.sh` as a filename could overwrite arbitrary files.
- Zip bombs and archive extraction: If the app extracts zip/tar files, is there a check for decompression bombs or path traversal within the archive (zip slip)?
- SVG uploads: SVGs can contain XSS payloads. Are they sanitized?
- XML uploads: Check for XXE (XML External Entity) attacks.
- File size limits: Are they enforced server-side? Can a user upload a 10GB file to exhaust disk space?
- Storage location: Are uploaded files stored inside the web root where they can be executed? They must be stored outside the web root or in a CDN/S3 bucket.
- Filename collision: Can an attacker overwrite existing files by crafting a specific filename?
- Virus/malware scanning: Is there any AV scanning on uploaded files?

For every upload endpoint: trace the full file handling path from receipt to storage to serving.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Enforce server-side MIME type + magic-byte validation (Node.js):
  # npm install file-type
  # const { fileTypeFromBuffer } = require('file-type');
  # const type = await fileTypeFromBuffer(req.file.buffer);
  # const ALLOWED = ['image/jpeg','image/png','image/webp'];
  # if (!type || !ALLOWED.includes(type.mime)) return res.status(400).json({ error: 'Invalid file type' });
  # Sanitize filename to prevent path traversal:
  # const safeName = path.basename(req.file.originalname).replace(/[^a-z0-9._-]/gi, '_');
  # Store uploads OUTSIDE the web root (or to S3 with private ACL — never public-read unless intended):
  # const uploadPath = path.join('/var/app/uploads', safeName);  // not inside /public or /static
  # Set a server-side file size limit:
  # upload = multer({ limits: { fileSize: 5 * 1024 * 1024 } })  // 5MB max
```

---

## 🔴 PROMPT 9 — API SECURITY & RATE LIMITING

```
You are an API security specialist. Audit every API endpoint in this codebase.

Check for:
- Missing authentication on any endpoint that should require it.
- API key security: Are API keys validated server-side? Can they be rotated? Are old keys invalidated?
- Rate limiting: Is there rate limiting on ALL endpoints, especially: login, password reset, OTP verification, registration, search, any AI/LLM endpoint, file upload, email sending? Rate limits must be per-IP AND per-user.
- Resource exhaustion: Can a single user trigger expensive operations (large database queries, file processing, external API calls) without limits?
- Mass assignment: Does the API accept arbitrary fields in request bodies and apply them to database models? (e.g., a user can set `isAdmin: true` in their profile update request)
- API versioning: Are old API versions still accessible? Do they have the same security controls as current versions?
- GraphQL specific: Introspection enabled in production? Query depth limiting? Query complexity limiting? Batching attack protection?
- HTTP verb tampering: Does the app use the correct HTTP methods? Can a GET request trigger a state change? Can OPTIONS/HEAD reveal sensitive info?
- Response filtering: Do API responses return only fields the user is authorized to see, or do they leak extra fields?
- Error messages: Do API errors reveal internal details (stack traces, DB schema, internal paths)?
- Pagination: Can a user request an enormous page size to dump all data?
- CORS: What origins are allowed? Is `Access-Control-Allow-Origin: *` combined with credentials? (This is a critical misconfiguration.)

List every endpoint with: method, path, auth required, rate limited (Y/N), findings.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add per-IP + per-user rate limiting to every sensitive endpoint (Express):
  # npm install express-rate-limit
  # const rateLimit = require('express-rate-limit');
  # const loginLimiter = rateLimit({ windowMs: 15*60*1000, max: 10, standardHeaders: true });
  # app.use('/api/auth/login', loginLimiter);
  # Block mass-assignment — strip unknown fields from request body:
  # const allowed = ['name', 'email'];  const safe = Object.fromEntries(Object.entries(req.body).filter(([k]) => allowed.includes(k)));
  # Fix CORS misconfiguration — never use wildcard with credentials:
  # app.use(cors({ origin: 'https://yourdomain.com', credentials: true }));
  # Disable GraphQL introspection in production:
  # ApolloServer({ introspection: process.env.NODE_ENV !== 'production' })
```

---

## 🔴 PROMPT 10 — DEPENDENCY & SUPPLY CHAIN VULNERABILITIES

```
You are a supply chain security analyst. Audit all third-party dependencies in this project.

Check for:
- Run `npm audit --audit-level=low` (or `pip-audit`, `bundle audit`, `cargo audit`, `composer audit`) and report EVERY vulnerability found, even low severity ones. Do not skip any.
- Outdated dependencies: List all packages more than 2 major versions behind their latest. For each: what security fixes have been released since the installed version?
- Unpinned dependency versions: `^`, `~`, `*` in package.json/requirements.txt allow automatic updates that could introduce malicious code. Every dependency should be pinned to an exact version.
- Abandoned packages: Check npm/PyPI for packages with no updates in 2+ years, transferred ownership, or no maintainers. These are supply chain attack targets.
- Typosquatting: Look for package names that are one letter off from popular packages.
- Lockfile integrity: Is package-lock.json / yarn.lock / poetry.lock committed? If not, builds are non-deterministic and vulnerable to dependency confusion.
- Dependency confusion attack surface: Are there any internal package names that could be registered on public registries?
- License compliance: Are there any GPL-licensed dependencies in a proprietary codebase? (Not security, but legal risk.)
- eval() in dependencies: Do any critical dependencies use eval() or Function() constructor?
- Minified code: Is any minified/obfuscated third-party code included inline? This is unauditable.

Produce a table: Package | Installed Version | Latest Version | Known CVEs | Severity | Action Required.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Scan and auto-fix known vulnerabilities:
  npm audit fix                         # Node.js — auto-patch non-breaking fixes
  npm audit fix --force                 # force-upgrade (review breaking changes first)
  pip-audit --fix                       # Python
  bundle update                         # Ruby
  # Pin all dependency versions (remove ^ and ~ from package.json):
  npx -y npm-pin-deps                   # converts ^1.2.3 → 1.2.3 in package.json
  # Ensure lockfile is committed:
  git add package-lock.json && git commit -m "chore: commit lockfile for deterministic builds"
  # Set up Dependabot for automatic PR-based updates:
  # Create .github/dependabot.yml with package-ecosystem: npm, directory: /, schedule: daily
```

---

## 🔴 PROMPT 11 — ENVIRONMENT & CONFIGURATION SECURITY

```
You are a DevSecOps engineer. Audit the entire configuration and deployment setup of this application.

Check for:
- .env files: Are they in .gitignore? Is there a .env.example with dummy values instead of real ones?
- Environment variable handling: Are secrets ever logged? Are they ever passed as command-line arguments (visible in `ps aux`)?
- Default configurations: Are any frameworks/libraries running with default configs (DEBUG=True in Django, default Express session secret, default database passwords)?
- Debug mode: Is debug mode disabled in production builds? Debug mode often exposes stack traces, environment variables, and internal routes.
- Error handling: Do unhandled errors expose stack traces to end users?
- Security headers: Check for presence and correctness of: Content-Security-Policy, X-Frame-Options (or frame-ancestors in CSP), X-Content-Type-Options: nosniff, Strict-Transport-Security, Referrer-Policy, Permissions-Policy.
- Dockerfile security: Is the app running as root inside the container? Is the base image updated? Are secrets baked into the image layers? Is the build stage separate from the runtime stage?
- CI/CD secrets: Are secrets exposed in build logs? Are GitHub Actions/GitLab CI secrets properly masked?
- Database configuration: Is the database accessible from the internet? Is it using the principle of least privilege (app user has only SELECT/INSERT/UPDATE, not DROP/CREATE)?
- Cloud misconfiguration: If AWS/GCP/Azure — are S3 buckets/Cloud Storage buckets publicly readable? Are security groups overly permissive? Is the metadata service protected from SSRF?
- Logging configuration: Are logs going somewhere persistent? Do they contain enough info to detect attacks? Too much info (PII/secrets)?

Produce a complete security baseline checklist with PASS/FAIL/UNKNOWN for each item.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add all critical security headers in one line (Express + Helmet):
  # npm install helmet
  # app.use(require('helmet')());   // sets CSP, HSTS, X-Frame-Options, nosniff, etc.
  # Disable debug mode — ensure environment variable is set correctly:
  # Node.js:  NODE_ENV=production node server.js
  # Django:   DEBUG = False  (in settings/production.py)
  # Ensure .env is gitignored and create a safe example:
  echo ".env" >> .gitignore
  cp .env .env.example && sed -i 's/=.*/=REPLACE_ME/g' .env.example
  git add .env.example && git commit -m "chore: add .env.example with placeholder values"
  # Run a quick header check against your live app:
  # npx -y security-headers --url https://yourdomain.com
```

---

## 🔴 PROMPT 12 — SERVER-SIDE REQUEST FORGERY (SSRF)

```
You are an SSRF specialist. Audit this codebase for every server-side request forgery vulnerability.

Check for:
- Every place the application makes an HTTP/HTTPS request to a URL that is influenced by user input: URL parameters, form fields, webhook URLs, image URL fetching, PDF generation from URLs, RSS feed readers, proxy endpoints, import from URL features.
- Allowlist validation: Is there an allowlist of permitted domains? IP address allowlisting? Or only a blacklist (which is always bypassable)?
- Internal network access: Can user-supplied URLs reach internal services at 169.254.169.254 (AWS metadata), 10.x.x.x, 172.16.x.x, 192.168.x.x, localhost, 127.0.0.1, [::1]?
- Protocol filtering: Can file://, gopher://, dict://, ftp:// be used instead of http://?
- DNS rebinding: Is there protection against DNS rebinding attacks where a hostname resolves to an external IP first, then to an internal IP?
- Redirect following: If the HTTP client follows redirects, can an attacker redirect from an allowed domain to an internal IP?
- Cloud metadata endpoints: On cloud providers, can an attacker use SSRF to steal IAM credentials from the metadata service?
- WebSocket SSRF: If WebSocket connections are proxied, same checks apply.

For each finding: show the exact code path, a working SSRF payload, what internal resources could be accessed, and the remediation (strict allowlisting + bind to outgoing IP + disable redirects to private ranges).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Validate every user-supplied URL against a strict allowlist before making a request:
  # npm install ssrf-req-filter
  # const { SsrfFilter } = require('ssrf-req-filter');
  # const filter = new SsrfFilter({ allowList: ['api.trustedpartner.com'] });
  # const res = await filter.fetch(userSuppliedUrl);   // throws on private IPs / blocked protocols
  # Python — use a DNS-based allowlist check:
  # pip install ssrf-protector
  # Block private IP ranges manually if no library available:
  # const url = new URL(userInput);
  # if (/^(10\.|172\.(1[6-9]|2\d|3[01])\.|192\.168\.|127\.|localhost|0\.0\.0\.0)/.test(url.hostname)) throw new Error('SSRF blocked');
  # Disable automatic redirect following:
  # axios.get(url, { maxRedirects: 0 })
```

---

## 🔴 PROMPT 13 — XML EXTERNAL ENTITY (XXE) & INSECURE DESERIALIZATION

```
You are an exploit researcher. Audit this codebase for XXE and insecure deserialization vulnerabilities.

XXE (XML External Entity):
- Find every place XML is parsed. Check the XML parser configuration — is external entity processing disabled?
- For Node.js: check libxmljs, xml2js, fast-xml-parser configurations.
- For Python: check lxml, xml.etree, defusedxml usage.
- For Java: check DocumentBuilder, SAXParser, XMLInputFactory — all must have external entity features disabled.
- Check SAML implementations specifically (XXE in SAML is a classic critical vulnerability).
- Check SVG parsing, Office document parsing (DOCX/XLSX are XML internally), any file import features.

Insecure Deserialization:
- Find every use of: pickle.loads() / pickle.load() in Python (CRITICAL — always RCE if user-controlled), unserialize() in PHP, Java ObjectInputStream.readObject(), YAML.load() (not safe_load) in Python/Ruby/JS, JSON.parse() with prototype pollution potential, eval() on JSON, Marshal.load in Ruby.
- Check if deserialized data comes from user input, cookies, API request bodies, or message queues that could be poisoned.
- Check for gadget chains in Java applications.
- Check for prototype pollution in JavaScript: `JSON.parse(userInput)` then `merge(obj, parsed)` can pollute Object.prototype.

For every finding: show exact vulnerable call, proof-of-concept exploit concept, and the safe alternative.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Python — replace unsafe deserializers:
  # BEFORE:  pickle.loads(user_data)         # RCE risk
  # AFTER:   json.loads(user_data)           # safe for structured data
  # Python YAML — always use safe_load:
  # BEFORE:  yaml.load(data)
  # AFTER:   yaml.safe_load(data)
  # Node.js — disable XML external entities in libxmljs / fast-xml-parser:
  # fast-xml-parser:  new XMLParser({ allowBooleanAttributes: true, processEntities: false })
  # Java — disable external entities on DocumentBuilder:
  # factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
  # PHP — replace unserialize() with json_decode() for untrusted data
  # Use defusedxml in Python instead of xml.etree for any external XML input:
  # pip install defusedxml  →  import defusedxml.ElementTree as ET
```

---

## 🔴 PROMPT 14 — CRYPTOGRAPHY MISUSE

```
You are a cryptography auditor. Examine every cryptographic operation in this codebase with extreme scrutiny.

Check for:
- Weak algorithms: MD5, SHA1 (for security purposes), DES, 3DES, RC4, Blowfish, ECB mode for any symmetric cipher. These are all broken or deprecated.
- Symmetric encryption: Is AES used with GCM or CCM mode (authenticated encryption)? Is CBC mode used without authentication (vulnerable to padding oracle)? Is ECB mode used at all (NEVER acceptable)?
- Key management: Are encryption keys hardcoded? Are they derived from weak sources? Are they rotated?
- IV/Nonce reuse: Is the same IV/nonce used across multiple encryptions with the same key? (Catastrophic for GCM mode.)
- Password hashing: Must be bcrypt (cost ≥12), argon2id, or scrypt. Anything else is wrong.
- Random number generation: Any use of Math.random(), random.random(), rand(), srand() for security-sensitive purposes is a vulnerability.
- JWT: What algorithm is used? RS256 or HS256? Is the secret for HS256 cryptographically random and ≥256 bits? Is the `alg: none` attack possible?
- TLS configuration: Are deprecated TLS versions (1.0, 1.1) or cipher suites (RC4, DES, EXPORT ciphers, NULL cipher) enabled?
- Certificate validation: Is there any code that disables certificate verification (verify=False, rejectUnauthorized: false, ssl_verify=False)? This enables MITM attacks.
- Timing attacks: Are secret comparisons done with constant-time functions (hmac.compare_digest, crypto.timingSafeEqual) or with regular == / === (vulnerable to timing attacks)?

List every crypto operation in the codebase with its algorithm, mode, and verdict.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Replace MD5/SHA1 password hashing with bcrypt:
  # Node.js:   npm install bcrypt  →  await bcrypt.hash(password, 12)
  # Python:    pip install bcrypt  →  bcrypt.hashpw(pwd.encode(), bcrypt.gensalt(12))
  # Replace CBC-mode AES with AES-GCM (authenticated encryption):
  # Node.js:   const { createCipheriv } = require('crypto');
  #            const iv = crypto.randomBytes(12);  // 96-bit IV for GCM
  #            const cipher = createCipheriv('aes-256-gcm', key, iv);
  # Replace Math.random() with crypto.randomBytes for all tokens:
  # Node.js:   require('crypto').randomBytes(32).toString('hex')
  # Re-enable TLS certificate validation — remove all verify=False / rejectUnauthorized:false:
  # grep -r "rejectUnauthorized" .  →  set to true or remove entirely
  # grep -r "verify=False" .        →  remove or set verify=True
```

---

## 🔴 PROMPT 15 — INPUT VALIDATION & BUSINESS LOGIC FLAWS

```
You are a business logic security analyst. Audit this codebase for missing input validation and business logic vulnerabilities.

Input Validation:
- Find every form field, API parameter, URL segment, header, cookie, and file that accepts user input. For each: is there server-side validation of type, length, format, and range?
- Integer overflow: Are there calculations with user-supplied numbers? Can a user supply negative numbers, zero, extremely large numbers, or non-integer values to break business logic?
- String length: Is there a maximum length enforced on all string inputs? Can an attacker supply a 1MB string to cause DoS or buffer issues?
- Unicode attacks: Are there any string operations (length checks, pattern matching) that could be confused by Unicode normalization, emoji, or bidirectional text?
- Email/URL validation: Are these validated with a proper library or a home-rolled regex? Test with edge cases.
- Regular expression DoS (ReDoS): Find all regex patterns. Identify catastrophically backtracking patterns applied to user-supplied strings.

Business Logic:
- Price manipulation: Can a user set the price of an item in their order request?
- Quantity manipulation: Can a user order -1 items, 0 items, or 999999999 items?
- Coupon/discount abuse: Can coupons be applied multiple times? Can expired coupons be used?
- Workflow bypass: In multi-step processes (checkout, onboarding, password reset), can a user skip to a later step without completing earlier required steps?
- Race conditions: Find every operation that reads-then-writes (balance checks, rate limit checks, stock checks). Can two simultaneous requests exploit the window between read and write?
- Account balance manipulation: Can a user trigger double-spending, negative balances, or bypass payment verification?

Produce a vulnerability matrix for every user input point and every business operation.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add server-side input validation with a schema library:
  # Node.js:  npm install zod
  # const schema = z.object({ price: z.number().positive().max(99999), qty: z.number().int().min(1).max(100) });
  # const result = schema.safeParse(req.body);  if (!result.success) return res.status(400).json(result.error);
  # Python:   pip install pydantic
  # class Order(BaseModel):  price: float = Field(gt=0, le=99999);  qty: int = Field(ge=1, le=100)
  # Fix ReDoS — test all regex with safe-regex:
  # npm install safe-regex  →  safeRegex(/your-pattern/)  // returns false if catastrophic
  # Enforce max string length on all text inputs:
  # Express body-parser:  app.use(express.json({ limit: '100kb' }))
  # Add idempotency keys to prevent duplicate order submissions:
  # Store a unique request ID per operation and reject duplicates within a time window.
```

---

## 🔴 PROMPT 16 — LOGGING, MONITORING & FORENSIC READINESS

```
You are a security operations engineer. Audit the logging and monitoring configuration of this application.

Check for:
- Are failed authentication attempts logged (username, IP, timestamp, user agent)?
- Are successful logins logged?
- Are privilege escalation events logged?
- Are admin actions logged with who did what and when?
- Are all API calls logged with enough detail to reconstruct an attack?
- Are logs sent to a separate system (not just local files) so an attacker can't delete them after compromise?
- Are logs protected from injection? (Log4Shell was a log injection attack — user input in log messages that gets parsed)
- Are sensitive values in logs? (Passwords, full tokens, PII — these must be masked)
- Is there any log rotation that deletes old logs before incident response could use them?
- Is there alerting on anomalous behavior (multiple failed logins, unusual data export volume, access from new geolocation)?
- Are errors and exceptions always caught and logged, or are they silently swallowed?
- Is there a correlation ID / request ID that allows tracing a single request through all services?
- For production systems: is there intrusion detection (fail2ban, WAF, anomaly detection)?

Identify every security-relevant event that is NOT currently being logged. Rank by impact.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add structured security event logging to auth routes (Node.js example):
  # const logger = require('pino')();   // npm install pino
  # On failed login:   logger.warn({ event: 'auth.fail', ip: req.ip, user: req.body.email, ua: req.headers['user-agent'] });
  # On successful login:  logger.info({ event: 'auth.success', userId: user.id, ip: req.ip });
  # On privilege change:  logger.warn({ event: 'priv.change', actor: req.user.id, target: targetId, newRole });
  # Sanitize log messages to prevent log injection:
  # const clean = (s) => String(s).replace(/[\r\n]/g, ' ');  // strip newlines
  # Ship logs to a remote SIEM (never store only on local disk):
  # Minimal setup:  pipe to a remote syslog, Datadog, or Cloudwatch — add LOG_STREAM_URL to .env
  # Install fail2ban on server to auto-ban IPs with repeated failed auth:
  # sudo apt install fail2ban && sudo systemctl enable fail2ban
```

---

## 🔴 PROMPT 17 — CLIENT-SIDE SECURITY (FRONTEND SPECIFIC)

```
You are a frontend security specialist. Audit every piece of client-side code in this application.

Check for:
- Sensitive data in client-side code: API keys, internal URLs, business logic secrets, user data embedded in the initial HTML/JS bundle.
- localStorage/sessionStorage: What is stored here? Tokens stored in localStorage are stolen by any XSS. Are JWTs in localStorage? (They should be in httpOnly cookies.)
- postMessage vulnerabilities: Is the origin of postMessage events validated before acting on the data?
- Prototype pollution: Find all uses of object merging, deep clone libraries, query string parsers that could pollute Object.prototype. Test with `?__proto__[admin]=true`.
- React-specific: dangerouslySetInnerHTML usage. Component receiving unvalidated props rendered as HTML. React Router with dangerousURL patterns.
- clickjacking: Is X-Frame-Options or frame-ancestors CSP set to prevent the app from being embedded in an iframe on an attacker's page?
- Third-party scripts: Every `<script src="">` tag from a third party is a potential XSS vector. Are subresource integrity (SRI) hashes present on all third-party scripts?
- Source maps: Are .map files exposed in production? They reveal your full original source code.
- Console logs in production: Are there console.log() calls with sensitive data that run in production?
- Client-side authorization: Is any access control enforced only in the client? (Hide button in UI but API not protected = broken access control)
- Reverse tabnabbing: Are external links using `target="_blank"` without `rel="noopener noreferrer"`?

List every finding with exact file, line, and severity.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Remove all source maps from production build (Webpack/Vite):
  # webpack.config.js:  devtool: false   (production mode)
  # vite.config.js:     build: { sourcemap: false }
  # Move JWT from localStorage to httpOnly cookie:
  # Server-side set:  res.cookie('token', jwt, { httpOnly: true, secure: true, sameSite: 'strict' });
  # Client-side remove:  localStorage.removeItem('token');
  # Add SRI hashes to all third-party scripts:
  # Use https://www.srihash.org/ to generate integrity attribute, then:
  # <script src="https://cdn.example.com/lib.js" integrity="sha384-..." crossorigin="anonymous"></script>
  # Fix reverse tabnabbing — find all target="_blank" links and add rel attribute:
  # grep -r 'target="_blank"' src/  →  add rel="noopener noreferrer" to each
  # Strip all console.log in production (Babel/Vite plugin):
  # npm install vite-plugin-remove-console  →  add to vite.config.js plugins array
```

---

## 🔴 PROMPT 18 — DATABASE SECURITY

```
You are a database security auditor. Audit everything related to how this application interacts with its database.

Check for:
- Connection string security: Is the DB password hardcoded? Is it in environment variables? Is it rotated?
- Principle of least privilege: What permissions does the application's database user have? It should have only SELECT/INSERT/UPDATE/DELETE on the specific tables it needs. Never GRANT ALL. Never allow DROP, CREATE, ALTER, or access to other databases.
- Connection pooling: Are database connections properly closed after use? Can connection exhaustion cause DoS?
- ORM security: Find all uses of raw queries within the ORM. Find all uses of `evaluate` in MongoDB, `literal` in Sequelize, `extra` in Django ORM, `execute` in SQLAlchemy — these bypass ORM protections.
- Database error exposure: Are raw database errors (with schema info, table names, query details) exposed to users?
- Transaction handling: Are financial/critical operations wrapped in transactions? What happens on partial failure?
- Soft deletes: If soft deletes are used, are deleted records still accessible via direct ID queries?
- Backups: Are database backups encrypted? Are they stored securely? Are they tested?
- Schema exposure: Is there an admin interface (PHPMyAdmin, Adminer, Django admin, Prisma Studio) exposed to the internet?
- MongoDB: Is authentication enabled? Is it bound to localhost or 0.0.0.0? Is the admin user using a strong password?
- Redis: Is it password-protected? Is it bound to localhost? Is `CONFIG` command disabled?
- Time-of-check to time-of-use (TOCTOU): Find operations that check a condition then act on it in separate non-atomic operations.

Produce a full database security checklist with PASS/FAIL for each item.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Create a least-privilege DB user (PostgreSQL example):
  # CREATE USER appuser WITH PASSWORD 'strong_random_password';
  # GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO appuser;
  # REVOKE CREATE, DROP, ALTER ON SCHEMA public FROM appuser;
  # Disable Redis public binding — edit redis.conf:
  # bind 127.0.0.1  (and restart: sudo systemctl restart redis)
  # requirepass strong_random_password
  # Disable MongoDB public access:
  # mongod.conf:  net.bindIp: 127.0.0.1  →  restart mongod
  # Enable MongoDB auth:  mongod --auth
  # Wrap financial operations in a transaction:
  # Sequelize:  await sequelize.transaction(async (t) => { ... all queries pass { transaction: t } ... });
  # Add connection pool limits to prevent connection exhaustion:
  # Knex:  pool: { min: 2, max: 10 }
```

---

## 🔴 PROMPT 19 — DENIAL OF SERVICE (DoS) ATTACK SURFACES

```
You are a resilience engineer. Find every way an attacker could cause this application to become unavailable or severely degrade in performance.

Check for:
- CPU exhaustion: Find all expensive operations triggerable by a single request — cryptographic operations with user-controlled parameters, image/video/PDF processing, large data exports, complex database queries with no timeouts.
- Memory exhaustion: Large file uploads held in memory. Unbounded arrays/lists built from user input. JSON bodies with no size limit.
- Database DoS: Queries with no LIMIT clause on user-initiated searches. Cartesian product queries. Missing indexes on commonly queried fields.
- ReDoS: Find all regular expressions applied to user input. Test them with ReDoS-triggering inputs.
- Infinite loops: Are there any loops whose termination depends on user-controlled data?
- Algorithmic complexity: Any sorting, searching, or graph operations on user-supplied data sets with no size limits?
- Rate limiting gaps: Which endpoints have NO rate limiting at all? List every one of them.
- Connection exhaustion: Can an attacker open thousands of connections and leave them open?
- Third-party dependency DoS: Are external API calls made synchronously with no timeout? If the external service is slow, does it block all incoming requests?
- Zip bomb / decompression bomb: If files are extracted, are there checks for abnormal compression ratios?
- Queue exhaustion: If a job queue is used, can an attacker flood it with tasks to delay legitimate work?
- Email sending: Can an attacker trigger mass email sending (to themselves or others) from the app?
- Cascading failure: If one microservice/component fails, does it cascade and take down the rest of the system?

For every finding: rate by exploitability, impact, and complexity of fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add request body size limit to prevent memory exhaustion (Express):
  app.use(express.json({ limit: '100kb' }));  app.use(express.urlencoded({ limit: '100kb', extended: false }));
  # Add a server-side query timeout to prevent database DoS:
  # Knex:  knex.raw('SET statement_timeout = 5000')   // 5 seconds max per query
  # Mongoose:  mongoose.set('maxTimeMS', 5000);
  # Add rate limiting to ALL endpoints as a baseline (Express):
  # npm install express-rate-limit
  # app.use(rateLimit({ windowMs: 60000, max: 100 }));   // 100 req/min global default
  # Fix ReDoS — replace vulnerable regex:
  # npm install re2   →   const RE2 = require('re2');  new RE2(/your-pattern/)  // linear time
  # Cap file decompression output to prevent zip bombs:
  # npm install unzipper  →  entry.pipe(new LimitedTransform(maxBytes))
```

---

## 🔴 PROMPT 20 — WEBSOCKET & REAL-TIME COMMUNICATION SECURITY

```
You are a WebSocket security auditor. If this application uses WebSockets, Socket.io, SSE, or any real-time protocol, audit it completely.

Check for:
- Authentication: Is the WebSocket connection authenticated? Just because a user is authenticated for HTTP doesn't mean the WS connection is protected. Check if a token/session is validated when the WS connection is established.
- Authorization per message: Does every incoming WebSocket message have its authorization checked? A user authenticated on one channel must not be able to send/receive messages for another user's channel.
- CSRF via WebSocket: WebSocket connections honor cookies and are not protected by CSRF tokens by default. Is the Origin header checked server-side against an allowlist?
- Input validation: Is all data received over WebSocket validated the same way HTTP data is? WebSocket is just another input vector — all injection, XSS, and DoS rules apply.
- Message rate limiting: Can a single client send thousands of messages per second to exhaust server resources?
- Room/channel security: In Socket.io rooms — can a user join arbitrary rooms by guessing their ID?
- Reconnection logic: Does the reconnection logic expose authentication tokens in URLs?
- Message broadcasting: Can a user trigger messages to be broadcast to all users?
- Binary data: If binary data is handled, is there a size limit and content validation?
- SSE (Server-Sent Events): Is the SSE endpoint authenticated? Is it protected against connection exhaustion?

Map every WebSocket event handler and produce an auth+validation status for each.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Authenticate the WebSocket handshake (Socket.io example):
  # io.use((socket, next) => {
  #   const token = socket.handshake.auth.token;
  #   try { socket.user = jwt.verify(token, process.env.JWT_SECRET); next(); }
  #   catch { next(new Error('Unauthorized')); }
  # });
  # Check Origin header on every connection to prevent CSRF via WebSocket:
  # const ALLOWED_ORIGINS = ['https://yourdomain.com'];
  # if (!ALLOWED_ORIGINS.includes(socket.handshake.headers.origin)) return socket.disconnect(true);
  # Add per-socket message rate limiting:
  # npm install socket.io-rate-limiter
  # Apply input validation to every incoming event — treat WebSocket data like HTTP body data.
```

---

## 🔴 PROMPT 21 — INFRASTRUCTURE AS CODE (IaC) SECURITY

```
You are a cloud security architect. Audit all Infrastructure as Code files (Terraform, CloudFormation, Kubernetes YAML, Helm charts, Ansible, Pulumi, Docker Compose, CDK) in this repository.

Check for:
- Overly permissive IAM roles/policies: Any `"*"` in Action or Resource fields in AWS IAM. Any `roles/owner` or `roles/editor` in GCP. Any ClusterAdmin in Kubernetes.
- Public exposure: S3 buckets with public read/write. Security groups with 0.0.0.0/0 on ports other than 80/443. Kubernetes services of type LoadBalancer exposing internal services.
- Hardcoded secrets: Passwords, API keys, connection strings in Terraform variables, K8s ConfigMaps, or Helm values files.
- Kubernetes-specific: Pods running as root (runAsRoot: true or no securityContext). Privilege escalation allowed (allowPrivilegeEscalation: true). Hostpath volumes mounted. HostNetwork or HostPID enabled. No resource limits (CPU/memory) set on containers — this enables DoS.
- Docker security: Base images tagged as `latest` (non-deterministic). Running as root user. Capabilities not dropped (should drop ALL and add back only what's needed). No read-only filesystem where possible. Secrets in ENV instructions.
- Network policies: Is there a default-deny Kubernetes NetworkPolicy? Or can any pod communicate with any other pod?
- Logging and auditing: Is cloud audit logging enabled? Is K8s API server audit logging configured?
- Encryption: Are EBS volumes, RDS instances, and S3 buckets encrypted at rest?
- Backup and disaster recovery: Are automated backups configured? What is the RPO/RTO?

Produce a finding per resource with: resource name, finding, severity (Critical/High/Medium/Low), and Terraform/YAML fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Scan all IaC files for misconfigurations in one command:
  npx -y checkov -d .                   # checks Terraform, K8s YAML, Docker, CloudFormation
  # or:
  brew install tfsec && tfsec .         # Terraform-focused
  # Fix Kubernetes pod running as root — add securityContext:
  # spec.securityContext:  runAsNonRoot: true  runAsUser: 1000  readOnlyRootFilesystem: true
  # Drop all Linux capabilities in Kubernetes:
  # securityContext.capabilities:  drop: ["ALL"]
  # Block public S3 bucket (AWS CLI):
  aws s3api put-public-access-block --bucket BUCKET_NAME --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
  # Remove wildcard IAM permissions (Terraform):
  # BEFORE: actions = ["*"]  →  AFTER: actions = ["s3:GetObject", "s3:PutObject"]
```

---

## 🔴 PROMPT 22 — EMAIL & NOTIFICATION SECURITY

```
You are a security auditor. Audit all email, SMS, push notification, and webhook functionality in this codebase.

Check for:
- Email injection: If user-controlled data is included in email headers (To, From, CC, BCC, Subject), can an attacker inject newlines to add their own headers and hijack the email (email header injection)?
- HTML email XSS: If emails are sent as HTML with user-generated content, is the content sanitized?
- Email enumeration: Do "forgot password" and "account exists" flows reveal whether an email is registered in the system?
- Phishing via the app: Can an attacker craft a request to send emails to arbitrary addresses that appear to come from your domain? (e.g., invitation system that lets attackers send phishing emails through your servers)
- Unsubscribe security: Can an attacker unsubscribe another user from emails by guessing/manipulating their unsubscribe token?
- Webhook security: If outgoing webhooks are supported, are they validated against SSRF? Is there a signature verification on incoming webhooks (GitHub, Stripe, Twilio all provide this)?
- SMS/OTP security: Are OTPs single-use? Do they expire? Is there rate limiting on OTP verification attempts?
- Notification content: Do push notifications or SMS messages contain sensitive data that could be read from a locked screen?
- SPF/DKIM/DMARC: Are email authentication records configured? (Not code, but check if the app sends email and whether the domain has these DNS records.)

List every email/notification send point with its security status.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Sanitize all user data placed into email headers to prevent header injection:
  # BEFORE:  subject = `Hello ${req.body.name}`
  # AFTER:   subject = `Hello ${req.body.name.replace(/[\r\n]/g, '')}` // strip CRLF
  # Verify incoming webhook signatures (Stripe example):
  # const event = stripe.webhooks.constructEvent(req.rawBody, req.headers['stripe-signature'], process.env.STRIPE_WEBHOOK_SECRET);
  # GitHub webhook:  const sig = req.headers['x-hub-signature-256']; verify with HMAC-SHA256
  # Add rate limiting to OTP/email sending endpoints:
  # Allow max 3 OTP sends per email per 15 minutes.
  # Return a generic response for "forgot password" regardless of whether the email exists:
  # res.json({ message: 'If that email exists, you will receive a reset link.' });
  # Configure SPF/DKIM/DMARC DNS records for your sending domain (run this check):
  # npx -y mxtoolbox-check yourdomain.com  OR  visit https://mxtoolbox.com/spf.aspx
```

---

## 🔴 PROMPT 23 — MOBILE API & THIRD-PARTY INTEGRATION SECURITY

```
You are a security integrations specialist. Audit all third-party API integrations, OAuth flows, webhooks, and payment processing in this codebase.

Check for:
- Payment processing: Is raw card data ever touching your servers, or is Stripe.js / Braintree SDK used to tokenize on the client? PCI DSS compliance surface.
- Webhook signature verification: For every incoming webhook (Stripe, GitHub, Shopify, Twilio, etc.) — is the signature/HMAC verified before processing the payload? Without this, anyone can forge webhook events.
- OAuth implementation: Is the `state` parameter used and validated to prevent CSRF? Is `redirect_uri` validated against a strict allowlist? Are authorization codes single-use and short-lived?
- API keys for third parties: Are third-party API keys stored in environment variables? Are they scoped to minimum permissions? Are there separate keys for development and production?
- Third-party data handling: What data is being sent to third-party services (analytics, logging, CRM, error tracking)? Does it include PII? Is the user aware of this (privacy policy)?
- SDK versions: Are third-party SDKs up to date? Check for known vulnerabilities in the specific versions used.
- Callback/redirect validation: Any feature that takes a `returnUrl` or `callbackUrl` parameter — is it validated to prevent open redirect attacks?
- Open redirects: Find every redirect in the application. Can a user supply a `next=https://evil.com` parameter and be redirected off-site after login? This is used for phishing.
- Social login: If "Login with Google/GitHub/Facebook" is implemented, is the email returned from OAuth treated as verified? Is the account linking secure?

List every integration with its security controls and gaps.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Validate and restrict every redirect/callback URL parameter:
  # const ALLOWED_HOSTS = ['yourdomain.com'];
  # const redirectUrl = new URL(req.query.next, 'https://yourdomain.com');
  # if (!ALLOWED_HOSTS.includes(redirectUrl.hostname)) return res.status(400).send('Invalid redirect');
  # Verify all incoming webhook HMAC signatures before processing:
  # const sig = crypto.createHmac('sha256', process.env.WEBHOOK_SECRET).update(req.rawBody).digest('hex');
  # if (sig !== req.headers['x-signature']) return res.status(401).send('Invalid signature');
  # Validate OAuth state parameter on callback to prevent CSRF:
  # if (req.query.state !== req.session.oauthState) return res.status(403).send('CSRF detected');
  # Use Stripe.js / hosted payment fields — never log or store raw card data server-side.
```

---

## 🔴 PROMPT 24 — CODE QUALITY AS SECURITY (DEAD CODE, ERROR HANDLING, MEMORY)

```
You are a code security reviewer. Audit this codebase for code quality issues that create security vulnerabilities.

Check for:
- Unhandled promise rejections / unhandled exceptions: Find every async function, Promise, and try/catch. Are there places where errors are caught and silently swallowed? Silent failures can mask security events or leave systems in inconsistent state.
- Dead code / commented-out code: Find all commented-out code blocks. They often contain old passwords, deprecated insecure implementations, debug backdoors, and TODO security items that never got done.
- TODO/FIXME/HACK/SECURITY comments: Find every one of them. These are documented technical debts that may include known security issues the developer meant to fix.
- Type confusion vulnerabilities: In JavaScript — find comparisons using == instead of ===. In Python — find places where types are assumed without validation. Type confusion can bypass security checks.
- Null/undefined dereference: Find places where objects are accessed without null checking, especially after database queries or API calls. These cause crashes (DoS) and information disclosure.
- Error recovery leaving insecure state: If a transaction fails mid-way, does the application clean up properly or leave data in a partially-written, inconsistent, or insecure state?
- Code injection via eval: Find every eval(), Function(), exec(), compile(), and template literal with complex expressions. Is any user input anywhere in the call chain?
- Circular dependencies: In Node.js — circular requires can cause modules to load in unexpected order, potentially before security middleware is initialized.
- Prototype pollution sinks: Find all recursive merge, deep clone, and object assign operations. Are they safe against __proto__ and constructor.prototype pollution?
- Memory leaks that enable DoS: Find event listeners added but never removed, caches with no eviction, global arrays that grow unboundedly.

Report every finding with file, line, category, and fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Find and remove dead/commented-out code with secrets:
  grep -rn "//.*password\|//.*secret\|//.*key\|//.*token" src/
  # Fix all loose equality comparisons in JS (== → ===):
  npx -y eslint --fix --rule '{"eqeqeq": "error"}' src/
  # Find all swallowed errors (empty catch blocks):
  grep -rn "catch.*{}\|catch.*{\s*}" src/
  # Find all eval() / Function() calls:
  grep -rn "eval(\|new Function(" src/
  # Fix prototype pollution — replace lodash merge with a safe alternative:
  # npm install @fastify/deepmerge   // safe deep merge that rejects __proto__
  # Add global unhandled rejection handler (Node.js):
  # process.on('unhandledRejection', (reason) => { logger.error({ event: 'unhandled_rejection', reason }); });
```

---

## 🔴 PROMPT 25 — NETWORK & TRANSPORT LAYER SECURITY

```
You are a network security auditor. Audit all network-level configuration and communication in this application.

Check for:
- TLS everywhere: Are all endpoints (APIs, admin panels, webhooks, health checks, metrics endpoints) served over HTTPS? Is HTTP redirected to HTTPS with a 301?
- HSTS: Is Strict-Transport-Security set with a max-age of at least 1 year and includeSubDomains? Is it submitted to the HSTS preload list?
- Certificate pinning: For mobile apps or high-security APIs, is certificate pinning implemented?
- Internal service communication: Do microservices communicate over HTTP internally? Even internal traffic should use TLS if possible.
- DNS security: Is DNSSEC configured? Can an attacker perform DNS hijacking to redirect users?
- Firewall rules: What ports are exposed to the internet? Only 80 and 443 should be publicly accessible. Database ports (5432, 3306, 27017, 6379), admin ports (8080, 9200), SSH (22), and debug ports must NOT be public.
- SSH security: If SSH is used, is password authentication disabled (key-only)? Is root login disabled? Is fail2ban or similar configured?
- Exposed metrics/health endpoints: Are Prometheus metrics, /health, /status, or /debug endpoints exposing sensitive internal information publicly?
- Load balancer / proxy headers: If behind nginx/Cloudflare/ALB, is X-Forwarded-For trusted correctly? Can an attacker spoof their IP by setting this header to bypass IP-based rate limiting?
- gRPC security: If gRPC is used, are channels authenticated and encrypted?
- WebRTC: If used, is TURN server authentication secure? Can an attacker use your TURN server as an open proxy?

Produce a network security checklist with evidence for each pass/fail.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Redirect all HTTP to HTTPS and add HSTS (nginx config):
  # server { listen 80; return 301 https://$host$request_uri; }
  # server { listen 443 ssl; add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always; }
  # Check open ports on the server:
  nmap -sV --open YOUR_SERVER_IP
  # Close all non-essential ports via firewall (ufw example):
  sudo ufw default deny incoming
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw enable
  # Disable SSH password authentication:
  sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
  sudo systemctl restart sshd
  # Test TLS config for weak ciphers:
  # npx -y testssl --quiet YOUR_DOMAIN:443
```

---

## 🔴 PROMPT 26 — RACE CONDITIONS & CONCURRENCY VULNERABILITIES

```
You are a concurrency security specialist. Audit this codebase for race conditions and time-of-check to time-of-use (TOCTOU) vulnerabilities.

Check for:
- Balance/credit checks: Find every operation that: (1) reads a value (balance, stock, rate limit counter), (2) makes a decision based on it, (3) updates the value. If these three steps are not atomic, two simultaneous requests can both pass the check before either updates the value.
- Double-spending: Can a user withdraw the same funds twice by sending two simultaneous requests?
- Duplicate action: Can a user submit a form twice simultaneously to create two records when only one should exist?
- File operations: Find every create-then-write file operation. Is there a window where another process could access the file between creation and securing it?
- Database-level fixes: Are pessimistic locks (SELECT FOR UPDATE), optimistic locks (version columns), or atomic operations (UPDATE accounts SET balance = balance - 100 WHERE balance >= 100 AND id = ?) used where needed?
- Session race conditions: Can two simultaneous login requests cause session token duplication or state corruption?
- Token generation: If a unique token is generated and then inserted into the database, what happens if two requests generate the same token simultaneously?
- Caching race conditions: Find all cache read-compute-write patterns (cache stampede). Is there a mutex/lock around the compute step?
- Job queue deduplication: Can the same job be enqueued twice and processed twice?
- Node.js event loop: Even though Node.js is single-threaded, async/await creates interleaving points. Find critical sections that span await calls — these are NOT atomic.

For each finding: show the race window, a concrete exploit scenario, and the atomic/locked fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Fix balance/stock race condition with an atomic SQL update (no separate read step):
  # BEFORE:  if (user.balance >= amount) { user.balance -= amount; await user.save(); }
  # AFTER:   const rows = await db.raw('UPDATE accounts SET balance = balance - ? WHERE id = ? AND balance >= ? RETURNING balance', [amount, userId, amount]);
  #          if (rows.rowCount === 0) throw new Error('Insufficient funds');
  # Add database-level unique constraint to prevent duplicate submissions:
  # ALTER TABLE orders ADD CONSTRAINT unique_idempotency_key UNIQUE (idempotency_key);
  # Implement idempotency keys on the API:
  # const key = req.headers['idempotency-key'];  if (!key) return res.status(400).send('Idempotency-Key required');
  # const existing = await db.query('SELECT * FROM idempotency_cache WHERE key = ?', [key]);
  # if (existing) return res.json(existing.response);
  # Use SELECT FOR UPDATE for pessimistic locking:
  # await db.transaction(async (trx) => { const [row] = await trx.raw('SELECT * FROM accounts WHERE id = ? FOR UPDATE', [id]); ... });
```

---

## 🔴 PROMPT 27 — KUBERNETES & CONTAINER RUNTIME SECURITY

```
You are a container security specialist. Audit all Docker and Kubernetes configurations in this codebase.

Check for containers/pods:
- Is the container running as root? (UID 0) — check Dockerfile USER instruction and K8s securityContext.runAsUser.
- Is allowPrivilegeEscalation set to false?
- Are unnecessary Linux capabilities dropped? (drop: ["ALL"] then add back only what's needed)
- Is the root filesystem read-only where possible? (readOnlyRootFilesystem: true)
- Are there resource limits (CPU and memory) set on every container? Without limits, a single container can exhaust node resources.
- Are liveness and readiness probes configured? Without them, Kubernetes can't detect deadlocked containers.
- Are pod security standards (restricted, baseline) enforced via PodSecurityAdmission or OPA Gatekeeper?
- Are secrets mounted as environment variables (visible in pod spec) or as files (safer)?
- Are image digests pinned (sha256:...) rather than mutable tags?
- Is the Docker socket (/var/run/docker.sock) mounted into any container? (Gives full host access — critical vulnerability)
- Is there a NetworkPolicy that enforces default-deny and allows only necessary pod-to-pod traffic?
- Are Kubernetes RBAC roles scoped to minimum necessary permissions? No `verbs: ["*"]` on `resources: ["*"]`.
- Is the Kubernetes API server accessible from within pods unnecessarily? The default service account token should be automounted: false unless needed.
- Are namespace-level resource quotas set to prevent noisy neighbor DoS?

Produce a per-container and per-namespace security finding table.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add security context to Kubernetes deployment (patch in-place):
  # kubectl patch deployment YOUR_APP -p '{"spec":{"template":{"spec":{"securityContext":{"runAsNonRoot":true,"runAsUser":1000}}}}}'
  # Add resource limits to all containers:
  # kubectl set resources deployment YOUR_APP --limits=cpu=500m,memory=256Mi --requests=cpu=100m,memory=128Mi
  # Check which containers are running as root right now:
  kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[*].securityContext.runAsUser}{"\n"}{end}'
  # Scan running cluster for security issues:
  # kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml && kubectl logs -l app=kube-bench
  # Fix Dockerfile: add non-root user and drop to it:
  # RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
  # USER appuser
```

---

## 🔴 PROMPT 28 — AI/LLM-SPECIFIC VULNERABILITIES (IF APPLICABLE)

```
You are an AI security researcher. If this application integrates with any LLM (OpenAI, Anthropic, Gemini, local models via Ollama, LangChain, etc.), audit it for AI-specific vulnerabilities.

Check for:
- Prompt injection: Can a user inject instructions into the prompt that override the system prompt? Look for places where user input is concatenated directly into a prompt string without sanitization.
- Indirect prompt injection: Can an attacker place malicious instructions in content that the LLM reads (web pages it browses, documents it processes, emails it reads) to hijack its behavior?
- System prompt leakage: Can a user trick the LLM into revealing the system prompt? Test with "Repeat everything above" style attacks.
- Excessive agency: If the LLM has tools/function calling — what can it do? Can it send emails, delete files, make API calls, access databases? Are there human-in-the-loop checkpoints for destructive actions?
- Insecure output handling: Is the LLM's output treated as trusted? If the LLM can output HTML/Markdown/code that gets rendered or executed downstream, that's injection via the AI.
- API key exposure: Is the LLM API key exposed on the client side? All LLM API calls must be server-side.
- Cost exhaustion DoS: Can an attacker trigger unlimited expensive LLM calls? Is there rate limiting and cost capping per user?
- Data exfiltration: Can an attacker use the LLM to exfiltrate data from its context window to an external service via prompt injection?
- Training data poisoning: If fine-tuning is done on user-provided data, is the training data validated?
- Model inversion / data extraction: Can the LLM be prompted to reveal training data or PII from its context?
- Jailbreaking: Can the safety filters be bypassed to produce harmful content that then gets used in the application?

Map every LLM integration point and its attack surface.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Separate user input from system instructions — never concatenate them directly:
  # BEFORE:  const prompt = `${systemPrompt}\nUser: ${userMessage}`
  # AFTER:   use the messages array format with distinct role: 'system' and role: 'user' entries
  # { role: 'system', content: systemPrompt }, { role: 'user', content: userMessage }
  # Add a per-user LLM cost cap (OpenAI example):
  # Track token usage per userId in DB; reject requests if daily_tokens > MAX_DAILY_TOKENS.
  # Rate limit the LLM endpoint:
  # app.use('/api/ai', rateLimit({ windowMs: 60000, max: 10 }));  // 10 requests/min per IP
  # Move the LLM API key to server-side environment variable only:
  # grep -r 'OPENAI\|ANTHROPIC\|GEMINI' src/ public/  — any match in public/ = critical
  # Sanitize/validate LLM output before rendering as HTML:
  # import DOMPurify from 'dompurify'; const safe = DOMPurify.sanitize(llmOutput);
```

---

## 🔴 PROMPT 29 — SECURITY REGRESSION & CI/CD PIPELINE AUDIT

```
You are a DevSecOps engineer. Audit the CI/CD pipeline and deployment processes for security gaps that allow vulnerabilities to ship.

Check for:
- Is there a dependency vulnerability scan (npm audit, Snyk, Dependabot, Trivy) in the CI pipeline that BLOCKS deployment on critical/high vulnerabilities?
- Is there a SAST (Static Application Security Testing) tool (Semgrep, CodeQL, Bandit, ESLint security plugin) running on every pull request?
- Is there a secrets scanner (GitLeaks, truffleHog, detect-secrets) in the pre-commit hooks or CI pipeline?
- Is there a container image scanner (Trivy, Grype, Snyk Container) that checks the Docker image before deployment?
- Is there a DAST (Dynamic Application Security Testing) tool (OWASP ZAP, Burp Suite) running against a staging environment?
- Are deployments to production gated behind a security review for significant changes?
- Is there infrastructure scanning (checkov, tfsec, KICS) for IaC files?
- Are security findings from CI treated as blocking (build fails) or advisory (warnings only)?
- Can a developer deploy directly to production without going through CI/CD? (Manual deployments bypass all security gates)
- Are GitHub/GitLab branch protection rules requiring PR reviews enabled for main/production branches?
- Is there a Software Bill of Materials (SBOM) generated for each release?
- Are deployment artifacts signed and verified before deployment?
- Is there rollback capability if a security issue is discovered post-deployment?
- Are environment-specific configurations (prod vs dev) clearly separated and validated?

Produce a DevSecOps maturity assessment with current state and recommended next steps.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Install Gitleaks as a pre-commit hook to block secret commits:
  # brew install gitleaks  (or download binary)
  # gitleaks protect --staged -v   # run before every commit
  # Add to .git/hooks/pre-commit:  gitleaks protect --staged -v || exit 1
  # Add npm audit to CI pipeline (GitHub Actions example):
  # - name: Audit dependencies
  #   run: npm audit --audit-level=high
  # Install Semgrep SAST on every PR:
  # - uses: returntocorp/semgrep-action@v1
  #   with: { config: 'p/security-audit' }
  # Scan Docker image in CI with Trivy:
  # - name: Scan image
  #   run: docker run --rm aquasec/trivy image YOUR_IMAGE:latest --exit-code 1 --severity CRITICAL,HIGH
  # Enable GitHub branch protection: require 1 review, require status checks to pass.
```

---

## 🔴 PROMPT 30 — COMPLETE ATTACK SURFACE MAP & THREAT MODEL

```
You are a senior penetration tester doing a final comprehensive review. Produce a complete attack surface map of this entire application.

Step 1 — Asset Inventory:
List every: API endpoint (method + path + auth required), WebSocket event, background job/cron task, file processed, external service called, database table with sensitive data, user role, environment variable, open port.

Step 2 — Trust Boundary Analysis:
Identify every place where data crosses a trust boundary: internet → server, server → database, server → external API, user role A → user role B data, service A → service B. At each boundary, document: what validation exists, what could cross that shouldn't.

Step 3 — STRIDE Threat Model:
For the top 5 most critical components, apply STRIDE:
- Spoofing: Can an attacker impersonate a user or service?
- Tampering: Can an attacker modify data in transit or at rest?
- Repudiation: Can a user deny performing an action? Is there a non-repudiation mechanism?
- Information Disclosure: What sensitive data could be exposed and how?
- Denial of Service: What is the most effective DoS attack on this system?
- Elevation of Privilege: What is the most viable path from unauthenticated to admin?

Step 4 — Attack Chain Construction:
Construct 3 realistic end-to-end attack chains:
1. The most likely attack for an external unauthenticated attacker
2. The most damaging attack for an authenticated regular user
3. The most impactful insider threat scenario

Step 5 — Risk Matrix:
For every vulnerability found across ALL previous prompts, produce a single ranked table:
| Finding | Component | Likelihood (1-5) | Impact (1-5) | Risk Score | Effort to Fix | Priority |

Sort by Risk Score descending. This is your remediation roadmap.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # After completing the threat model, immediately act on Critical/High findings:
  # 1. Rotate any exposed credentials found.
  # 2. Deploy a WAF rule for the most easily exploitable finding while the code fix is in progress.
  #    (Cloudflare: Security → WAF → Custom Rules; AWS WAF: WebACL → Add Rule)
  # 3. Add the top-3 attack chains to your penetration testing scope for manual verification.
  # 4. File a security ticket for each finding with severity, owner, and SLA:
  #    Critical → fix same day, High → fix within 48h, Medium → fix within 1 sprint.
  # 5. Re-run Prompt 30 after all Critical/High findings are fixed to verify the attack surface is reduced.
```

---

## 🔴 PROMPT 31 — ZERO-DAY THINKING: BUSINESS LOGIC EDGE CASES

```
You are an adversarial red teamer. Your job is to think like an attacker who has read the entire codebase and is looking for non-obvious, chained, or application-specific vulnerabilities that automated scanners would miss.

For every major feature in this application, ask:
- What is this feature SUPPOSED to do?
- What does this feature ACTUALLY do if given unexpected input?
- What happens if this feature is called out of expected order?
- What happens if this feature is called simultaneously by two users?
- What happens if an internal dependency of this feature fails silently?
- What happens if a user is in an edge state (account suspended, payment failed, email unverified) and uses this feature?
- What data does this feature read from external sources? Can that source be manipulated?
- What events/notifications does this feature trigger? Can they be used for abuse?
- Can this feature be used to infer information about other users?
- What does this feature do differently for the first use vs. subsequent uses? Is there a first-use vulnerability?
- Is there any import/export feature? Can it be used to exfiltrate data at scale?
- Are there any admin/debug features accessible in production that developers forgot to remove?
- Are there any time-dependent behaviors (trials, expirations, scheduled tasks) that can be manipulated by changing system time or sending requests at precise moments?
- Is there any functionality where the application trusts the client to report its own state?

Document every chained attack path you can construct, even if each individual step seems low-severity. Chains of low-severity vulnerabilities often produce critical outcomes.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # For every chained attack found, break the weakest link in the chain first:
  # e.g. Chain: open redirect → OAuth state bypass → account takeover
  #   Fix 1: validate redirect URIs as exact-match against allowlist.
  #   Fix 2: enforce state parameter on OAuth callback.
  # Remove all admin/debug routes in production:
  grep -rn "/debug\|/admin/test\|/dev/" src/routes/
  # Guard time-sensitive features with server-side time checks (never trust client time):
  # if (new Date() > offer.expiresAt) return res.status(410).json({ error: 'Expired' });
  # Add feature flags to easily disable any feature found to be abused:
  # if (!featureFlags.get('checkout_enabled')) return res.status(503).send('Feature unavailable');
```

---

## 🔴 PROMPT 32 — GDPR, COMPLIANCE & PRIVACY AUDIT

```
You are a privacy and compliance engineer. Audit this codebase for data privacy violations and compliance gaps.

Check for:
- Data minimization: Is the application collecting more data than necessary? Find every data field collected and question whether it's required for the core function.
- Data retention: Is there any automated deletion of user data after a retention period? Or does data live forever in the database?
- Right to erasure: Is there a "delete my account" feature? Does it actually delete (not just deactivate) all user data from the database, backups, logs, analytics, and third-party services?
- Data portability: Can users export their own data in a machine-readable format?
- Consent: Is there a record of when and what a user consented to? Is consent granular (separate consent for each use)?
- Third-party data sharing: What user data is sent to third parties (analytics, advertising, support, logging services)? Is the user informed?
- PII in logs: Audit all log outputs for email addresses, names, phone numbers, IP addresses, user IDs, and any other PII.
- Data encryption: Is PII encrypted at rest in the database? Who has access to the encryption keys?
- Cross-border data transfer: Where are servers and third-party services located? If EU users' data leaves the EU, is there a legal basis (Standard Contractual Clauses, etc.)?
- Cookie consent: Are tracking cookies set before consent is given?
- Children's data (COPPA/GDPR-K): If minors might use the app, are there additional protections?
- Breach notification readiness: If there is a data breach, does the organization have a process to notify users within 72 hours (GDPR requirement)?
- Privacy policy accuracy: Does the codebase match what the privacy policy says? Are there data flows in code not disclosed in the policy?

Produce a compliance gap analysis against GDPR (and CCPA where applicable).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add an automated data deletion job for expired user data (Node.js cron example):
  # npm install node-cron
  # cron.schedule('0 0 * * *', async () => { await db('users').where('deleted_at', '<', retentionCutoff).delete(); });
  # Implement a basic "delete my account" endpoint that cascades:
  # await Promise.all([db('users').where({id}).delete(), db('orders').where({userId: id}).delete(), /* etc */]);
  # Remove/mask PII from logs — search and replace in logging config:
  grep -rn 'email\|phone\|address\|ssn\|dob' src/logs/ src/middleware/
  # Set secure, consent-gated cookie flags:
  # Only set non-essential cookies AFTER user clicks "Accept" on the cookie banner.
  # document.cookie = "analytics_id=...; SameSite=Strict; Secure"  — only on consent.
  # Generate GDPR data export endpoint:
  # GET /api/me/export  → returns JSON of all user data, trigger async if large.
```

---

## 🔴 PROMPT 33 — FINAL SANITY CHECK: OWASP TOP 10 COMPLETE COVERAGE

```
You are a security auditor performing a final verification pass. Confirm that this codebase has been checked against every item in the OWASP Top 10 (2021) and OWASP API Security Top 10 (2023).

For each item below, state: AUDITED / FINDING EXISTS / CLEAN with a one-line summary of evidence:

OWASP Web Application Top 10 (2021):
1. A01 - Broken Access Control: [Status]
2. A02 - Cryptographic Failures: [Status]
3. A03 - Injection (SQL, NoSQL, OS, LDAP): [Status]
4. A04 - Insecure Design (threat model, business logic): [Status]
5. A05 - Security Misconfiguration: [Status]
6. A06 - Vulnerable & Outdated Components: [Status]
7. A07 - Identification & Authentication Failures: [Status]
8. A08 - Software & Data Integrity Failures (deserialization, CI/CD): [Status]
9. A09 - Security Logging & Monitoring Failures: [Status]
10. A10 - Server-Side Request Forgery: [Status]

OWASP API Security Top 10 (2023):
1. API1 - Broken Object Level Authorization (IDOR): [Status]
2. API2 - Broken Authentication: [Status]
3. API3 - Broken Object Property Level Authorization (mass assignment): [Status]
4. API4 - Unrestricted Resource Consumption (rate limiting, DoS): [Status]
5. API5 - Broken Function Level Authorization (admin functions): [Status]
6. API6 - Unrestricted Access to Sensitive Business Flows: [Status]
7. API7 - Server Side Request Forgery: [Status]
8. API8 - Security Misconfiguration: [Status]
9. API9 - Improper Inventory Management (shadow APIs, old versions): [Status]
10. API10 - Unsafe Consumption of APIs (third-party trust): [Status]

For any item without CLEAN status: link back to the specific prompt and finding number that covers it. This checklist is the final sign-off before any production deployment.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Run the complete OWASP ZAP baseline scan against your staging URL in one command:
  docker run -t owasp/zap2docker-stable zap-baseline.py -t https://staging.yourdomain.com -r zap_report.html
  # Run Semgrep against the full codebase for OWASP Top 10 patterns:
  npx -y semgrep --config=p/owasp-top-ten .
  # Run npm audit for A06 (Vulnerable Components):
  npm audit --audit-level=moderate
  # For any FINDING EXISTS item: do not ship to production until it is resolved and re-verified.
  # Mark each item CLEAN only after: fix committed, tests passing, re-audit shows no finding.
```

---


---

## 🔴 PROMPT 34 — GIT HISTORY FORENSICS & SECRET ARCHAEOLOGY

```
You are a forensic security investigator. Perform a deep archaeological audit of the entire git history of this repository. The current codebase being "clean" means nothing — secrets and vulnerabilities committed in the past are still exposed to anyone who clones this repo.

Step 1 — Secret Archaeology:
Run the following and analyze EVERY line of output:
  git log --all --full-history -p | grep -iE "(password|passwd|secret|api_key|apikey|token|credential|private_key|access_key|auth|bearer|sk-|pk-|AKIA|ghp_|xox|AIza|-----BEGIN)" | head -500

Also run: git log --all --oneline | grep -iE "(secret|key|password|remove|delete|revert|oops|fix cred|hotfix token)"

Step 2 — Branch & Tag Archaeology:
- List ALL branches including remote-tracking: `git branch -a`
- List ALL tags: `git tag -l`
- Check stashes: `git stash list`
- Check for orphaned commits: `git fsck --lost-found`
- Inspect any "temp", "dev", "debug", "test", "wip" branches — these often have secrets never cleaned up.

Step 3 — Large File & Binary Forensics:
- Find all large blobs ever committed: `git rev-list --all --objects | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sort -k3 -n -r | head -50`
- Check for .env files ever committed: `git log --all --full-history -- "**/.env" "**/.env.*" "*.pem" "*.p12" "*.key" "id_rsa"`
- Inspect every blob that matched an .env or key filename, even if deleted.

Step 4 — Commit Message Intelligence:
- Look for commit messages referencing: "fix security", "remove hardcoded", "delete key", "oops", "revert secret", "patch vulnerability"
- These are breadcrumbs to exactly where past secrets lived.

Step 5 — Contributor Analysis:
- List all committers: `git log --format='%ae' | sort -u`
- Flag any external email domains — were outside contributors ever given direct commit access?
- Check for force-pushed commits (history rewriting) that may have tried to scrub secrets but failed.

For every secret found in history: provide the commit hash, file, line, type of secret, and whether the secret is still active (i.e., was it rotated or is the same value still in use?). A secret in git history is a PERMANENT EXPOSURE even if deleted from HEAD — the entire history must be treated as compromised and the secret rotated immediately.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Immediately rotate any found secret on its platform (GitHub, AWS, Stripe, etc.) — first priority.
  # Then scrub the secret from git history using git-filter-repo (preferred over BFG):
  pip install git-filter-repo
  git filter-repo --path-glob '**/.env' --invert-paths   # removes .env from ALL history
  # or target a specific string:
  git filter-repo --replace-text <(echo "ACTUAL_SECRET_VALUE==>REDACTED")
  # Force-push to all remotes after scrubbing:
  git push --force --all
  git push --force --tags
  # Install Gitleaks to prevent future secret commits:
  # gitleaks protect --staged -v  (add to pre-commit hook)
  # Add secrets scanning to CI: GitHub Actions → Settings → Security → Secret scanning → Enable.
```

---

## 🔴 PROMPT 35 — HTTP REQUEST SMUGGLING & DESYNC ATTACKS

```
You are an HTTP protocol security specialist. Audit this application's entire HTTP layer for request smuggling and desync vulnerabilities — one of the most underestimated critical vulnerability classes, with CVEs in Apache (CVE-2022-26377), HAProxy, nginx, and major CDNs.

Background: HTTP request smuggling occurs when a front-end proxy (nginx, CDN, load balancer) and back-end server disagree on where one HTTP request ends and the next begins. This allows an attacker to prefix a malicious request to the next victim's request, bypass security controls, poison caches, and steal credentials.

Check for:

Architecture Analysis:
- Is there a reverse proxy / load balancer / CDN in front of the application? (nginx, HAProxy, Cloudflare, AWS ALB, Varnish, Squid)
- Does the proxy and app server use the same HTTP/1.1 parsing? Mismatches are the attack surface.
- Does the app support both HTTP/1.1 and HTTP/2? Downgrade paths are dangerous.

Transfer-Encoding / Content-Length Conflicts (CL.TE and TE.CL):
- Does the front-end use Content-Length and the back-end use Transfer-Encoding (CL.TE attack)?
- Does the front-end use Transfer-Encoding and the back-end use Content-Length (TE.CL attack)?
- Test: Send a request with BOTH `Content-Length` and `Transfer-Encoding: chunked` headers — how does each layer handle the conflict?
- Check for TE.TE obfuscation: `Transfer-Encoding: xchunked`, `Transfer-Encoding : chunked` (space before colon), `Transfer-Encoding: chunked, identity` — does the front-end honor the obfuscated header while the back-end ignores it?

HTTP/2 Downgrade Smuggling (H2.CL and H2.TE):
- If the front-end accepts HTTP/2 but the back-end uses HTTP/1.1: can an attacker inject Content-Length headers in HTTP/2 requests that get passed through to the back-end?
- Check for header smuggling via pseudo-headers: injecting `\r\n` into HTTP/2 header values.

Request Tunnel & Pause-Based Attacks:
- Does the server support long-lived connections where request boundaries could be ambiguous?
- Can an attacker send a partial chunked request body that causes the back-end to wait for more data, with the next victim's request completing it?

Security Control Bypass via Smuggling:
- Are there security rules in the WAF/proxy that apply to the first request but not the smuggled second request?
- Can request smuggling be used to bypass IP allowlists by making the smuggled request appear to come from 127.0.0.1?
- Can an attacker smuggle requests to internal-only paths (e.g., /admin, /internal) that the proxy blocks?

Configuration Audit:
- Is the proxy configured to normalize/validate Transfer-Encoding headers before forwarding?
- Are keep-alive connections limited in duration and request count?
- Is HTTP/1.0 disabled where not needed? (Simplifies parsing ambiguities)
- Does the app server reject requests with BOTH Content-Length and Transfer-Encoding?

For each finding: describe the specific CL/TE configuration that creates the vulnerability, the exact smuggled request payload, what an attacker can achieve (credential theft, cache poisoning, WAF bypass, session hijacking), and the proxy/app-level fix.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # nginx: reject requests with both Content-Length AND Transfer-Encoding:
  # Add to nginx.conf server block:
  # if ($http_transfer_encoding ~* "chunked" ) { return 400; }  # if app doesn't need chunked
  # Configure nginx to normalize TE headers before forwarding:
  # proxy_http_version 1.1;  proxy_set_header Connection '';  proxy_set_header Transfer-Encoding '';
  # Disable HTTP/1.0 keep-alive at the proxy layer:
  # keepalive_timeout 0;   (or set a low value like 5s)
  # Test your app for smuggling with PortSwigger's HTTP Request Smuggler (Burp extension)
  # or use the open-source tool: npm install -g http-request-smuggler
  # Upgrade nginx/HAProxy to latest version — many smuggling CVEs are version-specific:
  nginx -v && apt-get update && apt-get install --only-upgrade nginx
```

---

## 🔴 PROMPT 36 — BROWSER EXTENSION SECURITY

```
You are a browser extension security auditor. If this application ships a browser extension (Chrome, Firefox, Safari, Edge) OR if users are expected to install one that interacts with this application, perform a complete security audit of the extension and its interaction with the host application.

Manifest & Permission Audit:
- Open manifest.json (V2 or V3). List every permission requested: `<all_urls>`, `tabs`, `cookies`, `webRequest`, `nativeMessaging`, `clipboardRead`, `history`, `bookmarks` etc.
- Apply the principle of least privilege: does the extension request more permissions than it actually uses? Every unnecessary permission is attack surface.
- Check `content_scripts.matches`: Is it scoped to only the necessary domains, or does it inject into `<all_urls>`?
- Check `externally_connectable`: which origins can send messages to this extension? A permissive allowlist enables web-to-extension attack chains.
- For MV2: is `unsafe-eval` in the CSP? (Huge red flag — enables XSS in extension context)
- For MV3: are there any remote code execution paths via remotely fetched scripts?

Content Script Security:
- Content scripts run in the context of web pages but have access to the extension's privileged background context. Find every `chrome.runtime.sendMessage()` / `browser.runtime.sendMessage()` call.
- Is the message schema validated in the background script before acting on it? Or does it trust arbitrary messages from content scripts?
- Can a malicious web page trick the content script into sending a privileged message? (Content script XSS → background script privilege escalation)
- Does the content script read from the page DOM and pass it to the background? DOM content is attacker-controlled on malicious pages.
- Are there any `eval()`, `innerHTML`, `document.write()`, or `insertAdjacentHTML()` calls in content scripts? These are XSS in extension context.

Background Script / Service Worker Security:
- Does the background script receive messages from content scripts, web pages, or native applications? Is every message source validated?
- Are there any fetch() or XHR calls in the background script to external URLs? Can a content script influence those URLs?
- Is the extension's storage (chrome.storage.local/sync) treated as trusted? Stored values could be poisoned by a compromised content script.
- Native messaging: if used, does the native application validate that the calling extension ID is expected?

Extension-to-Web-App Communication:
- Does the extension communicate with the host web application? How? (Shared storage, postMessage, direct DOM manipulation, injected tokens)
- If the extension injects authentication tokens into the page, can any script on that page steal them?
- Are CORS requests made from the extension using the extension's origin — which may bypass the app's CORS policy intended only for the web app?

Data Handling:
- Does the extension collect browsing history, keystrokes, form data, or page content? Where does this data go?
- Is sensitive data (auth tokens, passwords, PII) stored in chrome.storage.sync? (Synced across devices, accessible to Google servers)
- Is data sent to the developer's servers over HTTPS with proper certificate validation?

Update Security:
- Is the extension distributed through official stores only, or are there side-loading mechanisms?
- Are extension updates signed and verified by the browser?

For every finding: severity, attack scenario, and exact code location in the extension source.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Reduce manifest permissions to the minimum — remove unused permissions from manifest.json:
  # "permissions": ["storage"]   // only what you actually use
  # "host_permissions": ["https://yourdomain.com/*"]  // NOT <all_urls>
  # Validate message sender in background script before acting:
  # chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  #   if (sender.id !== chrome.runtime.id) return;  // reject external senders
  #   if (!['ACTION_A','ACTION_B'].includes(msg.type)) return; // allowlist actions
  # });
  # Replace innerHTML with textContent in all content scripts:
  # grep -rn 'innerHTML' extension/  →  replace each with textContent or DOMPurify.sanitize()
  # Store sensitive tokens in chrome.storage.local (not .sync) with a short TTL:
  # chrome.storage.local.set({ token, expiresAt: Date.now() + 3600000 });
```

---

## 🔴 PROMPT 37 — CACHE POISONING & WEB CACHE DECEPTION

```
You are a cache security specialist. Audit this application for web cache poisoning and web cache deception vulnerabilities — two distinct but equally critical attack classes affecting CDNs (Cloudflare, Akamai, Fastly, CloudFront), reverse proxies (nginx, Varnish, Squid), and application-level caches.

Part 1 — Web Cache Poisoning (Attacker controls what gets cached):

Cache Key Analysis:
- What headers are included in the cache key? By default, many caches key only on URL path. Headers like `Host`, `X-Forwarded-Host`, `X-Forwarded-Scheme`, `X-Original-URL`, and `X-Rewrite-URL` are often NOT in the cache key but DO affect the response.
- Unkeyed header injection: If the app uses `X-Forwarded-Host` to construct URLs in responses (for absolute redirects, canonical links, open graph tags) but the cache doesn't include this header in its key — an attacker can poison the cache by sending `X-Forwarded-Host: evil.com` in a request that gets cached for all users.
- Unkeyed parameter injection: Does the app accept parameters like `?cb=`, `?utm_source=`, `?_=` and reflect them in responses but the cache ignores them? Attackers can use these to inject malicious content into a cacheable response.
- Fat GET requests: Does the cache key include the request body? Can an attacker use a GET request with a body to smuggle unkeyed data?

Response Poisoning Vectors:
- Header reflection: Find every HTTP response header that is constructed using request headers. These are injection points.
- Import/script/link URL injection: If the app reflects a hostname from a request header into a `<script src="...">` or `<link rel="stylesheet" href="...">` tag, cache poisoning → stored XSS for all users.
- HTTP response splitting: If user-controlled data ends up in response headers, can `\r\n` injection create new headers or split the response?
- Cookie-based cache poisoning: Can setting a cookie in one request cause a poisoned response to be cached?

Cache Control Misconfiguration:
- Are responses containing sensitive data (user profiles, auth tokens, private pages) inadvertently cached? Check Cache-Control, Pragma, Expires headers on every private response.
- Is `Vary` header used correctly? If `Vary: Cookie` is missing, authenticated responses may be cached and served to unauthenticated users.
- Are API responses with PII marked `Cache-Control: no-store, private`?
- CDN configuration: Are any cache rules set at the CDN level that override application-level Cache-Control headers?

Part 2 — Web Cache Deception (Attacker tricks cache into storing victim's private data):

Cache Deception Attack Pattern:
- Does the application serve user-specific private content at URLs like `/account`, `/profile`, `/orders`?
- Does the cache (CDN/proxy) cache responses based on file extension? If an attacker navigates to `/account/profile.css` and the app serves the profile page (ignoring the .css suffix), but the cache caches it as a CSS file — the victim's private data gets cached publicly.
- Test: Can `.css`, `.js`, `.ico`, `.jpg`, `.png`, `.woff` be appended to private page paths and still receive private content from the application?
- Path confusion: Do `/account` and `/account/` and `/account/;x` all return the same content? CDNs and apps may disagree on path normalization.

API Response Caching:
- Are `GET /api/me`, `GET /api/user/{id}`, `GET /api/profile` responses cached? Even with proper authentication, if the cache key doesn't include the auth token/session, the first authenticated response may be cached and served to unauthenticated requests.

For every finding: show the exact unkeyed input, what the poisoned response contains, who gets served the poisoned content, and the cache configuration fix (correct cache key, Vary headers, Cache-Control on private routes).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Add Cache-Control: no-store to ALL private/authenticated API responses:
  # Express middleware:  res.set('Cache-Control', 'no-store, no-cache, private');
  # nginx:  add_header Cache-Control "no-store, no-cache, private" always;   (in location /api/)
  # Add Vary: Cookie header so caches key on session:
  # res.set('Vary', 'Cookie, Authorization');
  # Prevent X-Forwarded-Host from being used to construct response URLs:
  # Remove any use of req.headers['x-forwarded-host'] in URL construction;
  # Instead, use a hardcoded APP_BASE_URL environment variable.
  # Block path-based cache deception: configure CDN to cache only explicit paths:
  # Cloudflare: Page Rule → Cache Level: Bypass for /*profile*, /*account*, /*orders*
  # Test for cache poisoning with param-miner Burp extension or manually:
  # curl -H 'X-Forwarded-Host: evil.com' https://yourdomain.com/  | grep evil.com
```

---

## 🔴 PROMPT 38 — SUBDOMAIN TAKEOVER & DNS HIJACKING

```
You are a DNS and subdomain security specialist. Audit this application for subdomain takeover vulnerabilities — a vulnerability class responsible for numerous real-world breaches where attackers hijack legitimate subdomains to serve malicious content under the victim's domain, steal cookies, and bypass same-origin policies.

Step 1 — Enumerate All Subdomains:
Extract every subdomain from:
- DNS records (CNAME, A, MX, TXT, NS): `dig ANY yourdomain.com` and subdomain enumeration
- Codebase: grep for hardcoded subdomains, API endpoints, webhook URLs, CDN URLs, redirect targets
- Configuration files: nginx/Apache vhosts, Kubernetes ingress rules, Cloudflare/Route53 configs
- Third-party services in use: check which SaaS platforms (GitHub Pages, Heroku, Netlify, Vercel, S3, Azure, Shopify, Zendesk, Intercom, SendGrid, etc.) have CNAME records pointing to them

Step 2 — Dangling DNS Records (The Core Vulnerability):
For each subdomain, check if the DNS record points to a service that is no longer provisioned:
- CNAME → GitHub Pages (check if the gh-pages branch still exists and the repo is still configured for that domain)
- CNAME → Heroku app (check if `*.herokuapp.com` target is still an active app)
- CNAME → Netlify/Vercel/Render (check if the project is still deployed and has that custom domain configured)
- CNAME → S3 bucket (check if the bucket still exists in the correct region — `NoSuchBucket` error means takeover is possible)
- CNAME → Azure/GCP services (check if the resource still exists)
- CNAME → Shopify/Zendesk/Intercom (check if the store/portal is still configured for that domain)
- NS records pointing to nameservers no longer owned by the organization (NS takeover — highest impact)
A dangling CNAME is one where the target does NOT exist — anyone can register that target and take over the subdomain.

Step 3 — Cookie & Session Scope Analysis:
- Are session cookies set with `Domain=.yourdomain.com`? If so, a subdomain takeover means the attacker's page on the taken-over subdomain receives your session cookies.
- Are CORS policies in the main application that trust `*.yourdomain.com`? A subdomain takeover = origin trust = full CORS bypass.
- Is `document.domain` set anywhere? (Effectively enables cross-subdomain communication)

Step 4 — CNAME Chain Analysis:
- Are there CNAME chains (A → B → C) where an intermediate record points to a claimable service?
- Do any CNAME records point to third-party CDN or infrastructure hostnames that could be registered?

Step 5 — Remediation Verification:
- For every subdomain no longer in use: is the DNS record removed?
- Is there a process for removing DNS records when decommissioning services?
- Is subdomain enumeration and dangling record monitoring part of the security operations process?

For each vulnerable subdomain: record the CNAME target, the service that no longer exists, the takeover difficulty (easy/medium/hard), the impact (cookie theft / phishing / CORS bypass / full origin control), and the fix (delete DNS record or re-provision the service).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Delete the dangling DNS record immediately (this is the only safe fix):
  # AWS Route53:  aws route53 change-resource-record-sets --hosted-zone-id ZONE_ID --change-batch '{"Changes":[{"Action":"DELETE","ResourceRecordSet":{...}}]}'
  # Cloudflare:   Dashboard → DNS → find the CNAME → Delete
  # Scan for dangling CNAMEs using open-source tools:
  npx -y subjack -w subdomains.txt -t 100 -o results.txt -ssl
  # or: pip install dnstwist && dnstwist --registered yourdomain.com
  # Verify the subdomain is no longer claimable after DNS delete:
  dig CNAME sub.yourdomain.com   # should return NXDOMAIN
  # Change session cookie scope from Domain=.yourdomain.com to specific hostname:
  # res.cookie('session', token, { domain: 'app.yourdomain.com' })  // NOT .yourdomain.com
  # Restrict CORS to exact origins, never wildcard subdomains:
  # origin: /^https:\/\/app\.yourdomain\.com$/  // NOT *.yourdomain.com
```

---

## 🔴 PROMPT 39 — SECOND-ORDER & STORED VULNERABILITY CHAINS

```
You are an advanced penetration tester specializing in second-order vulnerabilities — attacks where malicious input is stored harmlessly at one point and then executed or processed dangerously at a completely different point in the application, often by a different user or an automated process. These are among the hardest vulnerabilities to find with automated scanners because the injection and the trigger are separated in time, user context, and code path.

Second-Order SQL Injection:
- Find every location where user input is stored in the database. Now trace EVERY place that stored data is later retrieved and used in database queries. Example: A username stored with a SQL-special character gets stored safely via parameterized query, but when it's later inserted into a dynamic query (to generate a report, build an audit log query, or send to a stored procedure), the parameterization is missing.
- Check: admin panels that query using stored usernames, audit log queries, reporting features, batch processing jobs, export functions that construct queries from stored filter settings.
- Test: Register with username `' OR '1'='1` and check if any admin functionality or reporting feature that uses that username becomes injectable.

Second-Order XSS:
- User input is HTML-escaped on input but later:
  - Re-encoded and lost its escaping
  - Inserted into a context where HTML encoding is not enough (e.g., inside a JavaScript string, inside a JSON blob embedded in HTML, inside an attribute value)
  - Used by a different template engine with different escaping rules
  - Exported to a PDF, email, or report that renders HTML
  - Mirrored to an admin panel with different (or no) sanitization
- Check every admin interface — it's common for customer-facing input to be sanitized but the admin view of the same data to lack sanitization.

Second-Order Command Injection:
- User-supplied filenames, usernames, or metadata stored in the database and later used in shell commands (file processing scripts, cron jobs, backup scripts).
- Configuration values stored by users and later used in server-side operations.
- Image metadata (EXIF) stored and later processed by command-line tools like ImageMagick or ffmpeg.

Second-Order SSRF:
- URLs or hostnames stored by users (webhook URLs, callback URLs, avatar URLs, feed URLs) that are later fetched by background jobs or admin tools without the same SSRF protections applied at the time of storage.
- Import features that store a URL and process it asynchronously — the async fetcher may not have URL allowlisting.

Template Injection (SSTI) via Stored Data:
- If user-provided strings are ever used as template strings (even partially) in server-side templating, stored input can become template injection. Find every `render(template_string, data)` or `eval(f"f'{user_string}'")` pattern where the template comes from the database.

Second-Order Deserialization:
- Data serialized and stored in one format (e.g., a JWT, a pickled object, a PHP-serialized string) is stored in the database or a cache. Later, a different code path deserializes it without the same integrity checks applied at storage time.

Audit Process:
1. List every user-controlled input that is stored (database, file, cache, queue message).
2. For each stored value, trace ALL read paths — where is it retrieved and what operations are performed on it?
3. At each read path: are the same security controls applied as at the write path?
4. Map every cross-context use: data written by user A read by user B (admin), data written via API read by cron job, data written at registration read at login.

For each finding: show the write path (where stored), the read path (where triggered), the user/role context difference, a proof-of-concept payload, and the fix (sanitize at read time, not just write time — or better, store data in a canonical safe form).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Re-apply parameterized queries at EVERY read path, not just at input time:
  # Any place that reads stored user data and puts it into a query MUST use parameterization.
  # Re-apply HTML encoding at EVERY render path, especially in admin panels:
  # Admin template:  {{ user.name | escape }}  // always escape, even "trusted" DB data
  # Sanitize EXIF metadata before using it in shell commands:
  # npm install exifr   // read EXIF safely without shell commands
  # exifr.parse(buffer)  // returns parsed object — never pass raw EXIF to exec()
  # Add server-side sanitization when serving stored content to the admin UI:
  # const safeContent = DOMPurify.sanitize(storedContent, { ALLOWED_TAGS: [] });  // strip all HTML from admin view
  # Test for second-order SQLi by registering with: username = admin'--
  # then trigger every admin/reporting function that references that username.
```

---

## 🔴 PROMPT 40 — GRAPHQL SECURITY DEEP DIVE

```
You are a GraphQL security specialist. Perform a complete, adversarial audit of every GraphQL endpoint in this codebase. GraphQL's flexibility is exactly what makes it dangerous — a single misconfigured GraphQL API exposes more attack surface than dozens of REST endpoints.

Introspection & Schema Exposure:
- Is GraphQL introspection enabled in production? Run: `{"query": "{__schema{types{name,fields{name}}}}"}` — if this returns schema data, introspection is on.
- Even if introspection is disabled, check for field suggestion (does the API return "Did you mean: adminUsers?" errors on typos?). This leaks schema information without introspection.
- Is the GraphQL playground/GraphiQL IDE exposed in production? It should be disabled.

Authorization Failures (The Most Critical Class):
- Object-level authorization: For every query that returns a type (User, Order, Document, Invoice), is the resolver verifying that the requesting user is authorized to see that specific object? Or does it just check "is the user logged in"?
- Field-level authorization: Can a regular user query fields that should be admin-only? Example: `{ user(id: 1) { id, email, role, internalNotes, creditCardLast4, isAdmin } }` — are sensitive fields protected at the field level?
- Mutation authorization: For every mutation (createPost, deleteUser, updatePayment, assignRole), is the authorization check present in the resolver, not just the route middleware?
- Cross-object authorization: In nested queries `{ user(id: 1) { orders { items { price } } } }` — does accessing orders via a parent user object bypass the authorization check that would apply to a direct order query?

Batching & Complexity Attacks:
- Query batching: Does the API accept arrays of queries `[{"query": "..."}, {"query": "..."}]`? An attacker can send 1000 login mutation attempts in a single HTTP request, bypassing rate limiting that counts by HTTP request.
- Alias batching: Can an attacker use aliases to send many operations in one query? `{ a1: login(user:"a", pass:"1") a2: login(user:"a", pass:"2") ... a1000: login(...) }` — bypasses rate limiting.
- Query depth: Is there a maximum query depth enforced? Deeply nested queries `{ user { friends { friends { friends { friends { ... } } } } } }` can cause exponential database queries.
- Query complexity: Is there a complexity limit? A single query selecting every field on every object could return megabytes of data and execute hundreds of database queries.
- Field count limits: Can a query request thousands of fields?

Injection via GraphQL:
- Are GraphQL variables sanitized before use in database queries? GraphQL variables are still injection-vulnerable if passed to raw queries.
- NoSQL injection: If the backend is MongoDB, can GraphQL variables contain MongoDB operators?
- SSRF via GraphQL: If any mutation accepts URLs (avatar upload, webhook, import), does it enforce SSRF protections?

Information Disclosure:
- Do error messages in GraphQL responses reveal stack traces, database query details, or internal type information?
- Do failed authorization checks on field queries return null vs. return an error? (Returning null silently may reveal the field exists but the user can't see it)

Subscription Security:
- If GraphQL subscriptions (WebSocket-based) are used, is authentication enforced on the subscription connection?
- Can a user subscribe to events for resources they don't own?
- Is there rate limiting on subscription connections?

Denial of Service:
- Is there a query timeout enforced server-side?
- Is query complexity calculated BEFORE execution (rejecting expensive queries without running them)?
- Can circular fragment definitions cause infinite loops in the server's query analysis? (`fragment F on T { f { ...F } }`)

N+1 Query Problems (Security-Adjacent):
- DataLoader pattern: Without it, each item in a list triggers a separate database query. An attacker requesting a list of 10,000 items could trigger 10,000 database queries.

For every finding: show the exact GraphQL query/mutation that triggers it, the authorization bypass or data leak achieved, and the resolver-level fix (field-level auth middleware, complexity limits, depth limits, batching restrictions).

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Disable GraphQL introspection in production (Apollo Server):
  # new ApolloServer({ introspection: process.env.NODE_ENV !== 'production' });
  # Add query depth limit:
  # npm install graphql-depth-limit
  # const depthLimit = require('graphql-depth-limit');
  # new ApolloServer({ validationRules: [depthLimit(5)] });
  # Add query complexity limit:
  # npm install graphql-query-complexity
  # Block alias-based batching rate-limit bypass:
  # npm install graphql-rate-limit  →  add directive @rateLimit(max: 10, window: "1m") to mutations
  # Add field-level authorization with graphql-shield:
  # npm install graphql-shield
  # const permissions = shield({ Query: { adminUsers: isAdmin }, Mutation: { deleteUser: isAdmin } });
  # Disable query suggestions (field hints) in production:
  # new ApolloServer({ fieldResolver: undefined, debug: false });
```

---

## 🔴 PROMPT 41 — ADVANCED PROTOCOL & EMERGING ATTACK SURFACES

```
You are a security researcher specializing in protocol-level and emerging attack vectors. Audit this application for vulnerabilities that don't fit neatly into traditional web security categories but have real CVEs and real-world exploitation history.

OAuth 2.0 & OpenID Connect Deep Dive (Beyond Basic Checks):
- PKCE enforcement: For public clients (SPAs, mobile apps), is PKCE (Proof Key for Code Exchange) enforced? Without it, authorization code interception attacks are possible.
- Token leakage via Referer: If the access token is ever in a URL (implicit flow fragment, query parameter), it leaks to any third-party resource loaded on the same page via the Referer header.
- JWT algorithm confusion: If the server uses RS256, can an attacker change the algorithm to HS256 and sign with the public key (which is known)? Is `alg` validated strictly?
- OAuth token substitution: Can a token issued for one client be used with a different client?
- Redirect URI manipulation: Is the redirect_uri validated as an EXACT match or just a prefix match? Prefix matching allows `https://legit.com.evil.com/` or `https://legit.com/../../attacker`.
- Silent authentication: In SPA flows with `prompt=none`, is the resulting token properly validated?
- Token binding: Are tokens bound to the specific client/IP to prevent theft and replay?

SAML Security:
- XML signature wrapping (XSW): Is the SAML library vulnerable to XSW attacks where the attacker wraps a malicious assertion around the signed legitimate assertion?
- XXE in SAML: Is the XML parser used for SAML configured to disable external entities?
- SAML replay: Are SAML assertions validated for their `NotOnOrAfter` timestamp and `InResponseTo` field to prevent replay?
- Signature validation: Does the app verify the SAML assertion signature, or just the response signature? These are different elements.

WebAuthn / Passkey Security:
- Origin validation: Is the `rpId` (relying party ID) strictly validated? Can an attacker register credentials for a subdomain and use them on the main domain?
- Challenge freshness: Are WebAuthn challenges single-use and short-lived?
- User verification: Is `userVerification: required` enforced for high-security operations?

Prototype Pollution to RCE:
- In Node.js, prototype pollution vulnerabilities can escalate beyond XSS to server-side code execution via gadget chains in popular libraries (lodash merge, jquery extend, express render options).
- Find every deep merge, extend, clone operation on untrusted data.
- Check for known gadget chains: if `ejs` is used as a template engine and `Object.prototype.outputFunctionName` can be set, this is RCE.
- Test: `?__proto__[admin]=true`, `?constructor[prototype][admin]=true` — do any API endpoints accept query parameters that are parsed into nested objects?

Path Traversal in Modern Frameworks:
- Framework-specific bypasses: `%2e%2e%2f` (URL-encoded), `....//` (double-dot slash), `..%c0%af` (overlong UTF-8 encoding), null byte `%00` termination.
- If using Next.js, check for CVE-2025-29927 (middleware bypass via x-middleware-subrequest header) and similar framework-level CVEs.
- ZIP/tar path traversal (Zip Slip): Already covered in uploads, but also check import features that accept archives.

HTTP Parameter Pollution:
- What happens when the same parameter is supplied twice? `?user=admin&user=attacker` — does the app use the first, last, or both values? This behavior difference between languages (PHP uses last, Django uses first, Express uses both in array) can bypass security checks.
- Does the app parse parameters from multiple sources (URL + body) and do they conflict in exploitable ways?

Server-Side Template Injection (SSTI):
- Find every template rendering call. Does any template content come from user input, database values, or configuration?
- Test endpoints that reflect user input for template syntax: `{{7*7}}`, `${7*7}`, `<%= 7*7 %>`, `#{7*7}` — if the response contains `49`, SSTI is confirmed.
- SSTI severity: In Jinja2, Twig, FreeMarker, Velocity — SSTI is Remote Code Execution. In Handlebars, Mustache — it's typically limited to data access.
- Check email templates, PDF generation, notification templates — these commonly accept dynamic user data.

Mass Assignment Beyond API (Framework-Specific):
- Rails: `params.permit()` — is strong parameters used everywhere, or are there any `params.permit!` (allows all) calls?
- Django: `ModelForm` without explicit `fields` or with `exclude` — can fields be set that shouldn't be?
- Mongoose: Schemas without `strict: true` — can arbitrary fields be added to documents?

Type Juggling & Logic Bypass:
- PHP `==` comparison: `"0e123" == "0e456"` is TRUE (both are zero in scientific notation). Does any security check use loose comparison with user-supplied values?
- Python: `"0" == 0` is False, but check for implicit type coercions in numeric comparisons.
- JavaScript: `[] == false`, `null == undefined`, `"" == 0` — find security checks using `==`.
- JWT none algorithm: Is the JWT library configured to reject the `none` algorithm? Some libraries accept unsigned JWTs if `alg: none` is set by the attacker.

For every finding: provide the CVE reference if applicable, the exact attack vector for this codebase, and the remediation. Prioritize any finding where exploitation leads to authentication bypass, privilege escalation, or remote code execution.

⛔ NO FINDINGS = NO FIX: If the check above reveals no real issue in this codebase, explicitly write "✅ CLEAN — nothing found" for that category and stop. Do NOT invent vulnerabilities, make speculative changes, or apply the commands below "just in case." Only proceed with the fix if you have identified a concrete, evidence-backed finding in actual code above.

🔧 QUICK FIX COMMAND (run only if a real finding was confirmed above):
  # Enforce PKCE on OAuth public clients (MSAL / Auth0 / custom):
  # Auth0: enforce_pkce: true in Application settings.
  # Custom: generate code_verifier = crypto.randomBytes(32).toString('base64url'); code_challenge = sha256(code_verifier)
  # Fix JWT algorithm confusion — pin algorithm explicitly in verify call:
  # jwt.verify(token, publicKey, { algorithms: ['RS256'] })
  # Fix prototype pollution — replace lodash.merge with a safe alternative:
  # npm remove lodash; npm install @fastify/deepmerge
  # Test for SSTI by sending {{7*7}} in every text input field — if the response shows 49, it's confirmed.
  # Fix SSTI — never use user input as a template string:
  # BEFORE:  ejs.render(userTemplate, data)
  # AFTER:   ejs.render(FIXED_TEMPLATE, { userValue: sanitizedInput })
  # Replace PHP loose comparisons with strict (=== instead of ==):
  grep -rn ' == ' src/ | grep -v '===' | grep -v '!=='  # find all remaining loose comparisons
```

---

## 📋 MASTER FINDINGS TEMPLATE

After running all prompts, consolidate findings into this table:

```markdown
| # | Prompt | Finding | File:Line | Severity | CVSS Score | Status | Fix Made |
|---|--------|---------|-----------|----------|------------|--------|----------|
| 1 | P01    |         |           | Critical |            | Open   |          |
| 2 | ...    |         |           |          |            |        |          |
```

**Severity Definitions:**
- 🔴 **Critical** — Immediate exploitation possible, full system compromise or data breach risk. Fix before deployment.
- 🟠 **High** — Significant security risk, likely exploitation path. Fix within 24 hours of discovery.
- 🟡 **Medium** — Requires specific conditions to exploit. Fix within 1 sprint.
- 🟢 **Low** — Defense-in-depth improvements. Fix in backlog.
- ℹ️ **Info** — Best practice improvements, no direct security risk.

*Generated for comprehensive vibe-coded application security auditing. Run in sequence. Fix and re-run. No finding is too small to document.*
