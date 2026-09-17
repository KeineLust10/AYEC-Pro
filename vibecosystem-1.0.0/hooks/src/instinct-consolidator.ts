/**
 * Instinct Consolidator - Stop hook
 *
 * Session sonunda:
 * 1. instincts.jsonl'i atomic rename ile claim et (race condition onleme)
 * 2. Pattern bazinda grupla (global + proje bazli)
 * 3. Tekrarlayan pattern'larin confidence'ini arttir
 * 4. Olgun instinct'leri (confidence >= 5) mature-instincts.json'a yaz
 * 5. Proje-ozel mature dosyalarini yaz (projects/{hash}/instincts/)
 * 6. Cross-project promotion: 2+ projede, 5+ toplam → global-instincts.json
 * 7. Cok olgun olanlari (confidence >= 10) otomatik rule dosyasina donustur
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync, appendFileSync, renameSync, unlinkSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { notify } from './shared/notify.js';

interface RawInstinct {
  ts: string;
  session: string;
  type: 'file_pattern' | 'edit_pattern' | 'error_fix';
  pattern: string;
  detail: string;
  confidence: number;
  project?: string;
  projectName?: string;
}

interface MatureInstinct {
  pattern: string;
  type: string;
  count: number;
  confidence: number;
  first_seen: string;
  last_seen: string;
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
  first_seen: string;
  last_seen: string;
  examples: string[];
  promotedAt: string;
}

interface ProjectInfo {
  hash: string;
  name: string;
  path: string;
  firstSeen: string;
  lastSeen: string;
  patternCount: number;
}

interface ProjectRegistry {
  projects: Record<string, ProjectInfo>;
  updatedAt: string;
}

const MATURE_THRESHOLD = 5;
const PROMOTE_THRESHOLD = 10;
const MAX_EXAMPLES = 3;
const CROSS_PROJECT_MIN_PROJECTS = 2;
const CROSS_PROJECT_MIN_TOTAL = 5;
const MAX_JSONL_SIZE = 5 * 1024 * 1024; // 5MB hard limit

function main() {
  try { readFileSync(0, 'utf-8'); } catch { /* ok */ }

  const claudeDir = join(homedir(), '.claude');
  const instinctsPath = join(claudeDir, 'instincts.jsonl');
  const maturePath = join(claudeDir, 'mature-instincts.json');

  if (!existsSync(instinctsPath)) {
    console.log('{}');
    return;
  }

  // Atomic rename: race condition onleme.
  // passive-learner yeni bir instincts.jsonl olusturur, biz processing'i isleriz.
  const processingPath = instinctsPath + '.processing';
  try {
    renameSync(instinctsPath, processingPath);
  } catch {
    // Rename basarisiz = baska consolidator calisiyor veya dosya yok
    console.log('{}');
    return;
  }

  let lines: string[];
  try {
    const raw = readFileSync(processingPath, 'utf-8');
    // Size safety: cok buyuk dosyada son 5000 satiri al
    if (raw.length > MAX_JSONL_SIZE) {
      const allLines = raw.split('\n');
      lines = allLines.slice(-5000).filter(l => l.trim());
    } else {
      lines = raw.split('\n').filter(l => l.trim());
    }
  } catch {
    // Okuma basarisiz - dosyayi geri koy
    try { renameSync(processingPath, instinctsPath); } catch { /* lost */ }
    console.log('{}');
    return;
  }

  if (lines.length === 0) {
    try { unlinkSync(processingPath); } catch { /* ok */ }
    console.log('{}');
    return;
  }

  const rawInstincts: RawInstinct[] = [];
  for (const line of lines) {
    if (line.length > 10_000) continue; // skip oversized lines
    try {
      rawInstincts.push(JSON.parse(line));
    } catch { /* skip malformed */ }
  }

  // --- Legacy global consolidation (backward compat) ---
  const matureMap = loadMatureMap(maturePath);
  consolidateInto(matureMap, rawInstincts);
  const matureList = [...matureMap.values()].sort((a, b) => b.confidence - a.confidence);
  atomicWriteJSON(maturePath, matureList);

  // --- Proje bazli consolidation ---
  const projectGroups = groupByProject(rawInstincts);
  const registry = loadRegistry(claudeDir);

  for (const [projectHash, instincts] of projectGroups) {
    if (projectHash === '__global__') continue;
    if (!isValidHash(projectHash)) continue;

    const projectDir = join(claudeDir, 'projects', projectHash, 'instincts');
    if (!existsSync(projectDir)) mkdirSync(projectDir, { recursive: true });

    const projectMaturePath = join(projectDir, 'mature-instincts.json');
    const projectMatureMap = loadMatureMap(projectMaturePath);
    consolidateInto(projectMatureMap, instincts);

    const projectMatureList = [...projectMatureMap.values()].sort((a, b) => b.confidence - a.confidence);
    atomicWriteJSON(projectMaturePath, projectMatureList);

    // Registry guncelle
    const firstInst = instincts[0];
    const existing = registry.projects[projectHash];
    registry.projects[projectHash] = {
      hash: projectHash,
      name: firstInst.projectName || existing?.name || projectHash,
      path: existing?.path || '',
      firstSeen: existing?.firstSeen || firstInst.ts,
      lastSeen: instincts[instincts.length - 1].ts,
      patternCount: projectMatureList.length,
    };
  }

  registry.updatedAt = new Date().toISOString();
  const registryPath = join(claudeDir, 'instinct-projects.json');
  atomicWriteJSON(registryPath, registry);

  // --- Cross-project promotion ---
  const promoted = crossProjectPromote(claudeDir, matureList, rawInstincts, registry);

  // --- Rule promotion ---
  const newlyPromoted: MatureInstinct[] = [];
  for (const m of matureList) {
    if (m.confidence >= PROMOTE_THRESHOLD && !m.promoted) {
      promoteToRule(m, claudeDir);
      m.promoted = true;
      newlyPromoted.push(m);
    }
  }

  if (newlyPromoted.length > 0) {
    atomicWriteJSON(maturePath, matureList);
    notify('Hizir: Instinct Promoted', `${newlyPromoted.length} pattern rule oldu: ${newlyPromoted.map(p => p.pattern).join(', ')}`, 'info');
  }

  if (promoted > 0) {
    notify('Hizir: Cross-Project', `${promoted} pattern global'e promote edildi`, 'info');
  }

  // Processing dosyasini temizle (basarili consolidation sonrasi)
  try { unlinkSync(processingPath); } catch { /* ok */ }

  const matureCount = matureList.filter(m => m.confidence >= MATURE_THRESHOLD).length;
  const parts = [`Instincts: ${rawInstincts.length} consolidated, ${matureCount} mature`];
  if (newlyPromoted.length > 0) parts.push(`${newlyPromoted.length} promoted to rules`);
  if (promoted > 0) parts.push(`${promoted} cross-project promoted`);

  console.log(JSON.stringify({ result: parts.join(', ') }));
}

// --- Helper fonksiyonlar ---

/** Hash validation: sadece hex, tam 12 karakter */
function isValidHash(hash: string): boolean {
  return /^[a-f0-9]{12}$/.test(hash);
}

/** Atomic write: tmp dosyaya yaz, sonra rename. Crash-safe. */
function atomicWriteJSON(filePath: string, data: unknown): void {
  const tmpPath = filePath + '.tmp.' + process.pid;
  try {
    writeFileSync(tmpPath, JSON.stringify(data, null, 2), { mode: 0o600 });
    renameSync(tmpPath, filePath);
  } catch {
    try { unlinkSync(tmpPath); } catch { /* ignore */ }
  }
}

function loadMatureMap(path: string): Map<string, MatureInstinct> {
  const map = new Map<string, MatureInstinct>();
  if (existsSync(path)) {
    try {
      const existing: MatureInstinct[] = JSON.parse(readFileSync(path, 'utf-8'));
      for (const m of existing) {
        map.set(m.pattern, m);
      }
    } catch { /* fresh start */ }
  }
  return map;
}

function consolidateInto(map: Map<string, MatureInstinct>, instincts: RawInstinct[]): void {
  for (const inst of instincts) {
    const key = inst.pattern;
    const existing = map.get(key);

    if (existing) {
      existing.count++;
      existing.last_seen = inst.ts;
      existing.confidence = existing.count;
      if (existing.examples.length < MAX_EXAMPLES && !existing.examples.includes(inst.detail)) {
        existing.examples.push(inst.detail);
      }
    } else {
      map.set(key, {
        pattern: inst.pattern,
        type: inst.type,
        count: 1,
        confidence: 1,
        first_seen: inst.ts,
        last_seen: inst.ts,
        examples: [inst.detail],
        promoted: false,
      });
    }
  }
}

function groupByProject(instincts: RawInstinct[]): Map<string, RawInstinct[]> {
  const groups = new Map<string, RawInstinct[]>();
  for (const inst of instincts) {
    const key = inst.project || '__global__';
    const group = groups.get(key);
    if (group) {
      group.push(inst);
    } else {
      groups.set(key, [inst]);
    }
  }
  return groups;
}

function loadRegistry(claudeDir: string): ProjectRegistry {
  const registryPath = join(claudeDir, 'instinct-projects.json');
  if (existsSync(registryPath)) {
    try {
      return JSON.parse(readFileSync(registryPath, 'utf-8'));
    } catch { /* fresh */ }
  }
  return { projects: {}, updatedAt: '' };
}

function crossProjectPromote(
  claudeDir: string,
  matureList: MatureInstinct[],
  _rawInstincts: RawInstinct[],
  registry: ProjectRegistry,
): number {
  const globalPath = join(claudeDir, 'global-instincts.json');

  let globalMap = new Map<string, GlobalInstinct>();
  if (existsSync(globalPath)) {
    try {
      const existing: GlobalInstinct[] = JSON.parse(readFileSync(globalPath, 'utf-8'));
      for (const g of existing) {
        globalMap.set(g.pattern, g);
      }
    } catch { /* fresh */ }
  }

  // Her proje dizinindeki mature instinct'leri tara
  const patternProjects = new Map<string, Map<string, { count: number; lastSeen: string; firstSeen: string }>>();

  for (const [hash] of Object.entries(registry.projects)) {
    if (!isValidHash(hash)) continue;
    const projectMaturePath = join(claudeDir, 'projects', hash, 'instincts', 'mature-instincts.json');
    if (!existsSync(projectMaturePath)) continue;

    try {
      const projectMature: MatureInstinct[] = JSON.parse(readFileSync(projectMaturePath, 'utf-8'));
      for (const m of projectMature) {
        let projectMap = patternProjects.get(m.pattern);
        if (!projectMap) {
          projectMap = new Map();
          patternProjects.set(m.pattern, projectMap);
        }
        projectMap.set(hash, { count: m.count, lastSeen: m.last_seen, firstSeen: m.first_seen });
      }
    } catch { /* skip */ }
  }

  // Promotion kontrol
  let promotedCount = 0;
  const now = new Date().toISOString();

  for (const [pattern, projectMap] of patternProjects) {
    if (projectMap.size < CROSS_PROJECT_MIN_PROJECTS) continue;

    let totalCount = 0;
    const sources: ProjectSource[] = [];
    let firstSeen = '';
    let lastSeen = '';

    for (const [hash, data] of projectMap) {
      totalCount += data.count;
      const info = registry.projects[hash];
      sources.push({
        hash,
        name: info?.name || hash,
        count: data.count,
        lastSeen: data.lastSeen,
      });
      if (!firstSeen || data.firstSeen < firstSeen) firstSeen = data.firstSeen;
      if (!lastSeen || data.lastSeen > lastSeen) lastSeen = data.lastSeen;
    }

    if (totalCount < CROSS_PROJECT_MIN_TOTAL) continue;

    const existing = globalMap.get(pattern);
    if (existing) {
      existing.totalCount = totalCount;
      existing.projects = sources;
      existing.last_seen = lastSeen;
      existing.confidence = totalCount;
    } else {
      const mature = matureList.find(m => m.pattern === pattern);
      globalMap.set(pattern, {
        pattern,
        type: mature?.type || 'unknown',
        totalCount,
        projects: sources,
        confidence: totalCount,
        first_seen: firstSeen,
        last_seen: lastSeen,
        examples: mature?.examples || [],
        promotedAt: now,
      });
      promotedCount++;
    }
  }

  const globalList = [...globalMap.values()].sort((a, b) => b.totalCount - a.totalCount);
  if (globalList.length > 0) {
    atomicWriteJSON(globalPath, globalList);
  }

  return promotedCount;
}

function sanitizeFilename(name: string): string {
  return name
    .replace(/[^a-zA-Z0-9_-]/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 100);
}

function promoteToRule(instinct: MatureInstinct, claudeDir: string): void {
  const rulesDir = join(claudeDir, 'rules', 'archive');
  if (!existsSync(rulesDir)) mkdirSync(rulesDir, { recursive: true });

  const safeName = sanitizeFilename(instinct.pattern);
  const fileName = `learned-${safeName}.md`;
  const filePath = join(rulesDir, fileName);

  if (!filePath.startsWith(rulesDir)) return;
  if (existsSync(filePath)) return;

  const content = `# Learned: ${instinct.pattern}

> Bu kural otomatik olusturuldu (${instinct.count} tekrar, ${instinct.type} tipi).

## Pattern
${instinct.pattern}

## Ornekler
${instinct.examples.map(e => `- ${e}`).join('\n')}

## Ilk gorulme
${instinct.first_seen}

## Son gorulme
${instinct.last_seen}
`;

  writeFileSync(filePath, content, { mode: 0o600 });

  const logPath = join(claudeDir, 'learning-log.txt');
  const logLine = `[${new Date().toISOString()}] PROMOTED: ${instinct.pattern} (${instinct.count} occurrences) → ${fileName}\n`;
  appendFileSync(logPath, logLine);
}

main();
