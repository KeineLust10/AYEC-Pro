# AYEC Pro Agent Prompt Templates

Bu belge, kullanıcının kısa bir istek, hata metni veya görsel açıklaması vermesi durumunda bunun standart bir ajan promptuna nasıl dönüştürüleceğini tanımlar.

## Kullanım Kuralı
- Kullanıcı sadece sorunu yazsa bile uygun ajan promptu otomatik üretilir.
- Kullanıcı ekran görüntüsü atarsa prompt içine `Evidence` veya `Observed Symptoms` bölümü eklenir.
- Eksik ama düşük riskli alanlar repo bağlamından doldurulur.
- Her prompt şu cümleler ile biter:

`Work step by step and verify each step before proceeding.`
`If the solution does not work, debug and retry until it works. Do not stop at first attempt.`

## Global Güçlendirme
- Her promptta başarı kriteri açıkça yazılmalıdır.
- Başarı kriteri doğrulanmadan görev tamamlanmış sayılmaz.
- Başarılı çözüm varsa çözüm örüntüsü olarak kaydedilmeye uygun özet çıkarılır.

## 1. Full Setup Agent

```text
Create a full-stack web application from scratch.

Requirements:
- Backend: [backend stack]
- Frontend: [frontend stack]
- Database: [database]
- Authentication: [auth method]

Tasks:
1. Initialize project structure
2. Set up backend API
3. Create database schema
4. Implement authentication
5. Build the basic frontend pages
6. Connect frontend to backend
7. Add validation and error handling
8. Make sure everything runs locally with clear instructions

Success Criteria:
- Project installs locally
- Backend starts successfully
- Frontend starts successfully
- Database schema works
- Authentication flow works end-to-end

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 2. Repository Analysis Agent

```text
Analyze this repository and explain its structure.

Tasks:
1. Identify the main technologies used
2. Explain the folder structure
3. Describe how the app runs
4. Find potential issues or improvements
5. Suggest refactoring ideas

Be concise but technical.
Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 3. Bug Fix Agent

```text
Fix the following issue in the codebase.

Problem:
[issue description]

Observed Symptoms:
- [symptom 1]
- [symptom 2]

Evidence:
- [error message, screenshot summary, failing behavior]

Tasks:
1. Locate the source of the issue
2. Explain why it happens
3. Implement a fix
4. Ensure there are no side effects
5. Add short comments only where the fix is not self-evident

Success Criteria:
- The original issue no longer occurs
- Relevant logs no longer show the same failure
- Related behavior still works
- If tests exist, relevant tests pass

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 4. Test Writer Agent

```text
Write unit tests for the existing codebase.

Requirements:
- Test framework: [framework]
- Cover critical functions
- Include edge cases

Tasks:
1. Identify testable units
2. Write meaningful test cases
3. Ensure tests pass
4. Improve code if needed for testability

Success Criteria:
- Tests cover critical behavior
- Edge cases are included
- Test suite passes

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 5. Refactor Agent

```text
Refactor the codebase for better readability and performance.

Tasks:
1. Remove duplicate code
2. Improve naming conventions
3. Optimize slow parts
4. Apply best practices
5. Keep functionality unchanged

Success Criteria:
- Behavior remains unchanged
- Readability improves
- Duplicate code is reduced
- Performance-sensitive paths are improved where relevant

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 6. Security Agent

```text
Audit the project for security vulnerabilities.

Tasks:
1. Check the authentication flow
2. Identify common vulnerabilities such as XSS, SQL injection, insecure secrets, auth bypass, and unsafe file handling
3. Suggest fixes
4. Apply fixes where possible

Success Criteria:
- Key risks are identified
- Fixes are proposed clearly
- Applied fixes do not break existing behavior

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 7. Deployment Agent

```text
Prepare this project for production deployment.

Tasks:
1. Create Docker setup
2. Add environment configuration
3. Optimize the build
4. Provide deployment steps for the target platform

Success Criteria:
- Project is buildable for production
- Environment configuration is documented
- Deployment steps are clear and reproducible

Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 8. Code Analysis

```text
Analyze the following codebase.

Tasks:
- Detect bugs
- Detect bad practices
- Identify risky areas
- Suggest fixes

Output Format:
[FILE]
path/to/file.py

[ISSUE]
Short issue title

[LINE]
42

[FIX]
Concrete fix suggestion

Return structured output.
Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 9. Auto Fix Agent

```text
Analyze this codebase and fix all critical issues safely.

Tasks:
1. Detect critical bugs
2. Explain the issue briefly
3. Produce fixed code only for the affected file
4. Avoid destructive or unrelated changes

Return structured output with file path and fixed code.
Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## 10. Chained Multi-Agent Flow

```text
Run this work as a chained delivery flow:
1. Setup Agent
2. Test Writer Agent
3. Security Agent
4. Deployment Agent

Each stage must validate the previous one before continuing.
Work step by step and verify each step before proceeding.
If the solution does not work, debug and retry until it works. Do not stop at first attempt.
```

## Kullanıcı Girdisi -> Prompt Eşleme
- Yeni proje istiyorsa: `Full Setup Agent`
- Repo anlattırmak istiyorsa: `Repository Analysis Agent`
- Hata, ekran görüntüsü, crash, bozuk davranış gönderirse: `Bug Fix Agent`
- Test kapsamı istiyorsa: `Test Writer Agent`
- Kod temizliği, performans, okunabilirlik istiyorsa: `Refactor Agent`
- Güvenlik taraması istiyorsa: `Security Agent`
- Docker, env, build, production hazırlığı istiyorsa: `Deployment Agent`
- Kodu inceleyip bulgu raporu istiyorsa: `Code Analysis`
- Güvenli otomatik düzeltme ve PR istiyorsa: `Auto Fix Agent`
