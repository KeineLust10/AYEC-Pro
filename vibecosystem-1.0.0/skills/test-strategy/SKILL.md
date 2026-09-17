---
name: test-strategy
description: Test pyramid decision matrix, coverage targets, when to write which test type, mock vs real dependency decisions, and test ROI analysis.
---

# Test Strategy

## Test Pyramid Ratio Guidance

```
        /\
       /e2e\         ~10% — critical user flows only
      /------\
     /  integ  \     ~20% — API contracts, DB interactions
    /------------\
   /    unit      \  ~70% — pure logic, transformations, edge cases
  /--------------\
```

Keep the pyramid right-side-up. Inverting it (too many e2e) leads to slow, flaky CI.

## Decision Matrix: Task Type → Test Type

| Task Type | Test Type | Tool |
|-----------|-----------|------|
| Pure function / utility | Unit | Jest / Vitest |
| API endpoint | Integration | Supertest / httpx |
| Critical user flow | E2E | Playwright |
| Data transformation | Property-based | fast-check / Hypothesis |
| React/Vue component | Component | Testing Library |
| CLI command | Integration | execa + assertions |
| Database query | Integration (real DB) | jest + pg / pytest |
| Cron job / scheduler | Unit (mocked time) | Jest fakeTimers |

## Mock vs Real Dependency Decision Tree

```
Is it an external API (Stripe, Sendgrid, etc.)?
  → YES: Always mock. Use recorded fixtures or MSW.

Is it a database?
  → Unit test context: mock (in-memory store or jest.fn())
  → Integration test context: real DB (test container or local)

Is it the file system?
  → Mock with memfs or tmp dir, then clean up.

Is it time / Date.now()?
  → Always mock. Use Jest fakeTimers or freezegun (Python).

Is it a third-party SDK wrapper you wrote?
  → Skip testing the wrapper itself, test your code's behavior.
```

## Coverage Targets by Project Type

| Project Type | Branch Coverage | Notes |
|-------------|----------------|-------|
| Published library | 90%+ | Every exported function needs tests |
| Production app | 80%+ | Focus on critical paths |
| Internal tool | 70%+ | Happy path + main error cases |
| Prototype / spike | Skip | Throw it away anyway |
| Generated code | Skip | Don't test codegen output |

## Test Naming Conventions

### Jest / Vitest (describe + it)
```typescript
describe('calculateDiscount', () => {
  it('returns 10% for gold members', () => { ... })
  it('returns 0% when cart is empty', () => { ... })
  it('throws when discount rate exceeds 100', () => { ... })
})
```

### Given-When-Then (BDD style)
```typescript
describe('OrderService', () => {
  describe('given a confirmed order', () => {
    describe('when the user cancels', () => {
      it('then it transitions to CANCELLED state', () => { ... })
      it('then it sends a cancellation email', () => { ... })
    })
  })
})
```

## When NOT to Test

- Generated code (Prisma client, GraphQL types, protobuf outputs)
- Third-party SDK wrappers with zero custom logic
- Trivial getters/setters (`getEmail() { return this.email }`)
- Config files
- Framework boilerplate (Next.js `_app.tsx`, Express server bootstrap)

## Test Isolation Strategies

### Transaction rollback (PostgreSQL)
```typescript
beforeEach(async () => {
  await db.query('BEGIN')
})

afterEach(async () => {
  await db.query('ROLLBACK')
})
```

### Cleanup hooks
```typescript
afterEach(() => {
  jest.clearAllMocks()        // clear call counts
  jest.resetAllMocks()        // reset return values
  jest.restoreAllMocks()      // restore spied originals
})
```

### Test containers (real DB, isolated)
```typescript
import { PostgreSqlContainer } from '@testcontainers/postgresql'

let container: StartedPostgreSqlContainer

beforeAll(async () => {
  container = await new PostgreSqlContainer().start()
  process.env.DATABASE_URL = container.getConnectionUri()
})

afterAll(async () => {
  await container.stop()
})
```

## Flaky Test Triage

When a test is flaky (passes/fails non-deterministically):

1. Check for shared mutable state (global variables, singleton caches)
2. Check for missing `await` on async calls
3. Check for time-dependent assertions (`setTimeout`, `Date.now()`)
4. Check for ordering dependencies (tests relying on previous test state)
5. Add `--runInBand` to isolate and confirm

## Mutation Testing (Stryker)

Mutation testing verifies that your tests actually catch bugs:

```bash
npx stryker run
```

```json
// stryker.config.json
{
  "mutator": { "excludedMutations": ["StringLiteral"] },
  "thresholds": { "high": 80, "low": 60, "break": 50 },
  "reporters": ["html", "progress"]
}
```

Mutation score < 60% means tests pass without catching real logic errors. Focus on the surviving mutants — each one is an untested code path.

## Test ROI Analysis

High ROI (write these first):
- Business logic with branching conditions
- Error handling paths
- Data validation functions
- State machine transitions

Low ROI (write last or skip):
- Simple CRUD with no custom logic
- Pass-through adapters
- Logging statements
- UI cosmetic details
