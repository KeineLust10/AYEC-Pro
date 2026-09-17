/**
 * Intent Classifier - UserPromptSubmit hook
 * Kullanici prompt'unu analiz ederek intent tipini belirler.
 * Sonuc: ~/.claude/cache/current-intent.json
 *
 * Diger hook'lar (adaptive loader, smart compact) bu dosyayi okuyarak
 * kendilerini optimize eder.
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { detectTask } from './shared/task-detector.js';

interface UserPromptSubmitInput {
  session_id: string;
  prompt: string;
}

interface ClassifiedIntent {
  ts: string;
  session_id: string;
  task_type: 'implementation' | 'research' | 'debug' | 'planning' | 'conversational';
  confidence: number;
  domain: string[];
  skills_needed: string[];
  agent_hint: string | null;
}

// Domain pattern'leri
const DOMAIN_PATTERNS: Array<{ regex: RegExp; domain: string }> = [
  { regex: /\b(typescript|\.ts|\.tsx|react|next\.?js|node)\b/i, domain: 'typescript' },
  { regex: /\b(python|\.py|django|flask|fastapi)\b/i, domain: 'python' },
  { regex: /\b(go|golang|\.go)\b/i, domain: 'go' },
  { regex: /\b(rust|\.rs|cargo)\b/i, domain: 'rust' },
  { regex: /\b(sql|database|postgres|mysql|sqlite|prisma|migration)\b/i, domain: 'database' },
  { regex: /\b(docker|kubernetes|k8s|ci\/cd|deploy|infra)\b/i, domain: 'devops' },
  { regex: /\b(css|tailwind|styled|scss|styling|ui|component)\b/i, domain: 'frontend' },
  { regex: /\b(api|endpoint|rest|graphql|grpc)\b/i, domain: 'api' },
  { regex: /\b(test|spec|jest|vitest|playwright|e2e)\b/i, domain: 'testing' },
  { regex: /\b(auth|security|token|jwt|oauth|permission)\b/i, domain: 'security' },
  { regex: /\b(ai|llm|model|prompt|embedding|vector)\b/i, domain: 'ai' },
];

// Agent hint pattern'leri
const AGENT_HINTS: Array<{ regex: RegExp; agent: string }> = [
  { regex: /\b(fix|debug|bug|broken|not working|hata|calismıyor)\b/i, agent: 'sleuth' },
  { regex: /\b(refactor|clean|dead code|tech debt)\b/i, agent: 'refactor-cleaner' },
  { regex: /\b(test|tdd|coverage)\b/i, agent: 'tdd-guide' },
  { regex: /\b(deploy|release|ci|cd)\b/i, agent: 'devops' },
  { regex: /\b(security|audit|vulnerability)\b/i, agent: 'security-reviewer' },
  { regex: /\b(plan|architect|design system)\b/i, agent: 'architect' },
  { regex: /\b(review|code review)\b/i, agent: 'code-reviewer' },
  { regex: /\b(performance|slow|optimize|profil)\b/i, agent: 'profiler' },
];

// Skill pattern'leri
const SKILL_PATTERNS: Array<{ regex: RegExp; skill: string }> = [
  { regex: /\b(react|component|hook|useState|useEffect)\b/i, skill: 'frontend-patterns' },
  { regex: /\b(api|endpoint|route|middleware)\b/i, skill: 'backend-patterns' },
  { regex: /\b(test|spec|mock|fixture)\b/i, skill: 'testing-patterns' },
  { regex: /\b(sql|query|schema|migration)\b/i, skill: 'database-patterns' },
  { regex: /\b(docker|k8s|pipeline)\b/i, skill: 'devops-patterns' },
];

function classifyIntent(input: UserPromptSubmitInput): ClassifiedIntent {
  const prompt = input.prompt || '';
  const detection = detectTask(prompt);

  // Task type belirleme
  let taskType: ClassifiedIntent['task_type'] = 'conversational';
  if (detection.isTask && detection.taskType && detection.taskType !== 'unknown') {
    taskType = detection.taskType as ClassifiedIntent['task_type'];
  }

  // Domain tespiti
  const domains: string[] = [];
  for (const dp of DOMAIN_PATTERNS) {
    if (dp.regex.test(prompt)) {
      domains.push(dp.domain);
    }
  }

  // Agent hint
  let agentHint: string | null = null;
  for (const ah of AGENT_HINTS) {
    if (ah.regex.test(prompt)) {
      agentHint = ah.agent;
      break;
    }
  }

  // Skill tespiti
  const skillsNeeded: string[] = [];
  for (const sp of SKILL_PATTERNS) {
    if (sp.regex.test(prompt)) {
      skillsNeeded.push(sp.skill);
    }
  }

  return {
    ts: new Date().toISOString(),
    session_id: input.session_id?.slice(0, 8) || 'unknown',
    task_type: taskType,
    confidence: detection.confidence,
    domain: domains,
    skills_needed: skillsNeeded,
    agent_hint: agentHint,
  };
}

function main() {
  let raw = '';
  try { raw = readFileSync(0, 'utf-8'); } catch { return; }
  if (!raw) { console.log('{}'); return; }

  let input: UserPromptSubmitInput;
  try { input = JSON.parse(raw); } catch { console.log('{}'); return; }

  const intent = classifyIntent(input);

  // Cache'e yaz (session-specific dosya + current symlink)
  const cacheDir = join(homedir(), '.claude', 'cache');
  if (!existsSync(cacheDir)) mkdirSync(cacheDir, { recursive: true });
  const intentPath = join(cacheDir, 'current-intent.json');

  try {
    // Session ID'yi dosyaya dahil et, staleness kontrolu icin ts zaten var
    writeFileSync(intentPath, JSON.stringify(intent, null, 2));
  } catch { /* skip */ }

  // Hook output - sadece task ise bilgilendir
  if (intent.task_type !== 'conversational') {
    console.log(JSON.stringify({
      result: 'continue',
    }));
  } else {
    console.log('{}');
  }
}

main();
