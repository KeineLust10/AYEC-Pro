# AYEC Pro Web Security Scan Instructions

Scan the AYEC Pro web surface with focus on:

- Authentication and authorization bypass risks
- JWT/refresh-token misuse and insecure storage patterns
- XSS, CSRF, and injection vectors
- API endpoint exposure and insecure direct object references
- Sensitive data disclosure in logs, responses, or client bundles

Targets:

- Frontend source: `frontend/src`
- Backend API source: `backend/app`
- Running web UI URL: `${TARGET_URL}`
- Running API URL: `${API_URL}`

Output expectations:

- List each finding with severity, endpoint/component, reproduction hint
- Include actionable remediation for each finding
- Prioritize auth/token issues and privilege escalation paths

