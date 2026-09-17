/**
 * Instinct Loader - SessionStart hook
 *
 * Session basinda:
 * 1. Proje-ozel olgun instinct'leri oku (projects/{hash}/instincts/)
 * 2. Global cross-project instinct'leri oku (global-instincts.json)
 * 3. Fallback: legacy mature-instincts.json
 * 4. Canavar takim hatalarini oku
 * 5. Hepsini context'e enjekte et
 */
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { getProjectIdentity } from './shared/project-identity.js';

interface MatureInstinct {
  pattern: string;
  type: string;
  count: number;
  confidence: number;
  examples: string[];
  promoted: boolean;
}

interface ProjectSource {
  hash: string;
  name: string;
  count: number;
  lastSeen: string;
}

interface GlobalInstinct {
  pattern: string;
  type: string;
  totalCount: number;
  projects: ProjectSource[];
  confidence: number;
  examples: string[];
  promotedAt: string;
}

const INJECT_THRESHOLD = 5;
const MAX_INJECT = 10;
const MAX_GLOBAL_INJECT = 5;
const TEAM_ERRORS_DAYS = 7;
const MAX_TEAM_ERRORS = 5;

interface ErrorEntry {
  ts: string;
  session: string;
  agent_id: string;
  agent_type: string;
  error_type: string;
  error_pattern: string;
  detail: string;
  file: string;
  lesson: string;
}

function main() {
  try { readFileSync(0, 'utf-8'); } catch { /* ok */ }

  const claudeDir = join(homedir(), '.claude');
  const identity = getProjectIdentity();
  const lines: string[] = [];

  // 1. Proje-ozel instinct'ler
  let projectMature: MatureInstinct[] = [];
  if (identity) {
    const projectMaturePath = join(claudeDir, 'projects', identity.hash, 'instincts', 'mature-instincts.json');
    if (existsSync(projectMaturePath)) {
      try {
        projectMature = JSON.parse(readFileSync(projectMaturePath, 'utf-8'));
      } catch { /* skip */ }
    }
  }

  const projectInjectable = projectMature
    .filter(i => i.confidence >= INJECT_THRESHOLD)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, MAX_INJECT);

  // 2. Global cross-project instinct'ler
  let globalInstincts: GlobalInstinct[] = [];
  const globalPath = join(claudeDir, 'global-instincts.json');
  if (existsSync(globalPath)) {
    try {
      globalInstincts = JSON.parse(readFileSync(globalPath, 'utf-8'));
    } catch { /* skip */ }
  }

  const globalInjectable = globalInstincts.slice(0, MAX_GLOBAL_INJECT);

  // 3. Fallback: legacy mature-instincts.json (proje-ozel yoksa)
  let legacyMature: MatureInstinct[] = [];
  if (projectInjectable.length === 0) {
    const legacyPath = join(claudeDir, 'mature-instincts.json');
    if (existsSync(legacyPath)) {
      try {
        legacyMature = JSON.parse(readFileSync(legacyPath, 'utf-8'));
      } catch { /* skip */ }
    }
  }

  const legacyInjectable = legacyMature
    .filter(i => i.confidence >= INJECT_THRESHOLD)
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, MAX_INJECT);

  // Hicbir sey yoksa cik
  if (projectInjectable.length === 0 && globalInjectable.length === 0 && legacyInjectable.length === 0) {
    // Yine de takim hatalarini kontrol et
    const teamErrorLines = loadTeamErrors();
    if (teamErrorLines.length > 0) {
      console.log(JSON.stringify({
        result: 'Loaded team errors',
        systemMessage: teamErrorLines.join('\n'),
      }));
    } else {
      console.log('{}');
    }
    return;
  }

  // Context mesaji olustur
  if (projectInjectable.length > 0) {
    const projectName = identity?.name || 'unknown';
    lines.push(`--- PROJECT PATTERNS: ${projectName} ---`);
    lines.push('');
    for (const inst of projectInjectable) {
      const promoted = inst.promoted ? ' [RULE]' : '';
      lines.push(`[${inst.type}] ${inst.pattern} (${inst.count}x)${promoted}`);
      if (inst.examples.length > 0) {
        lines.push(`  ornek: ${inst.examples[0]}`);
      }
    }
    lines.push('');
  }

  if (legacyInjectable.length > 0) {
    lines.push('--- LEARNED PATTERNS (Otomatik Ogrenilmis) ---');
    lines.push('');
    for (const inst of legacyInjectable) {
      const promoted = inst.promoted ? ' [RULE]' : '';
      lines.push(`[${inst.type}] ${inst.pattern} (${inst.count}x)${promoted}`);
      if (inst.examples.length > 0) {
        lines.push(`  ornek: ${inst.examples[0]}`);
      }
    }
    lines.push('');
  }

  if (globalInjectable.length > 0) {
    lines.push('--- GLOBAL PATTERNS (Cross-Project) ---');
    lines.push('');
    for (const gi of globalInjectable) {
      const projectNames = gi.projects.map(p => p.name).join(', ');
      lines.push(`[${gi.type}] ${gi.pattern} (${gi.totalCount}x across ${gi.projects.length} projects)`);
      lines.push(`  projeler: ${projectNames}`);
      if (gi.examples.length > 0) {
        lines.push(`  ornek: ${gi.examples[0]}`);
      }
    }
    lines.push('');
  }

  const totalProject = projectInjectable.length;
  const totalGlobal = globalInjectable.length;
  const totalLegacy = legacyInjectable.length;
  lines.push(`--- ${totalProject + totalGlobal + totalLegacy} pattern toplam (${totalProject} project, ${totalGlobal} global, ${totalLegacy} legacy) ---`);

  // Canavar takim hatalari
  const teamErrorLines = loadTeamErrors();
  if (teamErrorLines.length > 0) {
    lines.push('');
    lines.push(...teamErrorLines);
  }

  const parts: string[] = [];
  if (totalProject > 0) parts.push(`${totalProject} project`);
  if (totalGlobal > 0) parts.push(`${totalGlobal} global`);
  if (totalLegacy > 0) parts.push(`${totalLegacy} legacy`);
  if (teamErrorLines.length > 0) parts.push('team errors');
  const resultMsg = `Loaded ${parts.join(' + ')} patterns`;

  console.log(JSON.stringify({
    result: resultMsg,
    systemMessage: lines.join('\n'),
  }));
}

function loadTeamErrors(): string[] {
  const ledgerPath = join(homedir(), '.claude', 'canavar', 'error-ledger.jsonl');
  if (!existsSync(ledgerPath)) return [];

  const cutoff = new Date();
  cutoff.setDate(cutoff.getDate() - TEAM_ERRORS_DAYS);

  const lines = readFileSync(ledgerPath, 'utf-8').split('\n').filter(l => l.trim());
  const recent: ErrorEntry[] = [];

  for (const line of lines) {
    try {
      const entry: ErrorEntry = JSON.parse(line);
      if (new Date(entry.ts) >= cutoff) {
        recent.push(entry);
      }
    } catch { /* skip */ }
  }

  if (recent.length === 0) return [];

  const grouped = new Map<string, { count: number; agent: string; lesson: string }>();
  for (const e of recent) {
    const key = `${e.agent_type}:${e.error_pattern}`;
    const existing = grouped.get(key);
    if (existing) {
      existing.count++;
    } else {
      grouped.set(key, { count: 1, agent: e.agent_type, lesson: e.lesson });
    }
  }

  const sorted = [...grouped.values()]
    .sort((a, b) => b.count - a.count)
    .slice(0, MAX_TEAM_ERRORS);

  const result: string[] = [
    `--- TAKIM HATALARI (Son ${TEAM_ERRORS_DAYS} Gun) ---`,
  ];

  for (const entry of sorted) {
    result.push(`[${entry.count}x] ${entry.agent}: ${entry.lesson}`);
  }

  return result;
}

main();
