/**
 * Instinct CLI - Cross-project learning raporlari
 * Kullanim: node instinct-cli.mjs <komut>
 * Komutlar: portfolio, global, project <isim>, stats
 */
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

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

const claudeDir = join(homedir(), '.claude');

function loadRegistry(): ProjectRegistry {
  const path = join(claudeDir, 'instinct-projects.json');
  if (!existsSync(path)) return { projects: {}, updatedAt: '' };
  try { return JSON.parse(readFileSync(path, 'utf-8')); } catch { return { projects: {}, updatedAt: '' }; }
}

function loadGlobal(): GlobalInstinct[] {
  const path = join(claudeDir, 'global-instincts.json');
  if (!existsSync(path)) return [];
  try { return JSON.parse(readFileSync(path, 'utf-8')); } catch { return []; }
}

function loadProjectMature(hash: string): MatureInstinct[] {
  if (!/^[a-f0-9]{12}$/.test(hash)) return [];
  const path = join(claudeDir, 'projects', hash, 'instincts', 'mature-instincts.json');
  if (!existsSync(path)) return [];
  try { return JSON.parse(readFileSync(path, 'utf-8')); } catch { return []; }
}

function loadLegacyMature(): MatureInstinct[] {
  const path = join(claudeDir, 'mature-instincts.json');
  if (!existsSync(path)) return [];
  try { return JSON.parse(readFileSync(path, 'utf-8')); } catch { return []; }
}

function cmdPortfolio() {
  const registry = loadRegistry();
  const projects = Object.values(registry.projects);

  if (projects.length === 0) {
    console.log('Henuz proje kaydedilmemis. Farkli projelerde session baslatin.');
    return;
  }

  console.log('=== PROJE PORTFOYU ===\n');
  console.log(`Toplam proje: ${projects.length}`);
  console.log(`Son guncelleme: ${registry.updatedAt}\n`);

  console.log('  Proje               Hash         Pattern  Ilk Gorulme');
  console.log('  -----               ----         -------  -----------');

  const sorted = projects.sort((a, b) => b.patternCount - a.patternCount);
  for (const p of sorted) {
    const name = p.name.padEnd(20).slice(0, 20);
    const hash = p.hash.padEnd(12);
    const count = String(p.patternCount).padEnd(8);
    const first = p.firstSeen.slice(0, 10);
    console.log(`  ${name} ${hash} ${count} ${first}`);
  }

  const global = loadGlobal();
  if (global.length > 0) {
    console.log(`\nGlobal promote edilmis: ${global.length} pattern`);
  }
}

function cmdGlobal() {
  const global = loadGlobal();

  if (global.length === 0) {
    console.log('Henuz global promote edilmis pattern yok.');
    console.log('Kosullar: 2+ projede gorulen, toplam 5+ tekrarlayan pattern\'ler.');
    return;
  }

  console.log(`=== GLOBAL PATTERNS (${global.length} toplam) ===\n`);

  for (const g of global) {
    const projectNames = g.projects.map(p => `${p.name}(${p.count}x)`).join(', ');
    console.log(`[${g.type}] ${g.pattern}`);
    console.log(`  Toplam: ${g.totalCount}x | Projeler: ${g.projects.length}`);
    console.log(`  Kaynak: ${projectNames}`);
    if (g.examples.length > 0) {
      console.log(`  Ornek: ${g.examples[0]}`);
    }
    console.log(`  Promote: ${g.promotedAt.slice(0, 10)}`);
    console.log('');
  }
}

function cmdProject(nameOrHash: string) {
  if (!nameOrHash) {
    console.log('Kullanim: instinct-cli project <proje-ismi-veya-hash>');
    return;
  }

  const registry = loadRegistry();
  const projects = Object.values(registry.projects);

  // Isim veya hash ile bul
  const project = projects.find(
    p => p.name.toLowerCase() === nameOrHash.toLowerCase() || p.hash === nameOrHash,
  );

  if (!project) {
    console.log(`Proje '${nameOrHash}' bulunamadi.`);
    console.log(`Mevcut projeler: ${projects.map(p => p.name).join(', ') || 'yok'}`);
    return;
  }

  const mature = loadProjectMature(project.hash);

  console.log(`=== ${project.name.toUpperCase()} ===\n`);
  console.log(`Hash: ${project.hash}`);
  console.log(`Ilk gorulme: ${project.firstSeen.slice(0, 10)}`);
  console.log(`Son gorulme: ${project.lastSeen.slice(0, 10)}`);
  console.log(`Toplam pattern: ${mature.length}`);
  console.log(`Olgun (5+): ${mature.filter(m => m.confidence >= 5).length}`);
  console.log(`Rule'a donusen (10+): ${mature.filter(m => m.promoted).length}`);

  if (mature.length > 0) {
    console.log('\n--- Pattern\'ler ---');
    const sorted = mature.sort((a, b) => b.confidence - a.confidence);
    for (const m of sorted.slice(0, 15)) {
      const badge = m.promoted ? ' [RULE]' : m.confidence >= 5 ? ' [MATURE]' : '';
      console.log(`  ${m.pattern} (${m.count}x)${badge}`);
    }
    if (mature.length > 15) {
      console.log(`  ... ve ${mature.length - 15} daha`);
    }
  }
}

function cmdStats() {
  const registry = loadRegistry();
  const projects = Object.values(registry.projects);
  const global = loadGlobal();
  const legacy = loadLegacyMature();

  console.log('=== INSTINCT ISTATISTIKLERI ===\n');

  // Genel
  console.log(`Projeler: ${projects.length}`);
  console.log(`Global pattern: ${global.length}`);
  console.log(`Legacy pattern: ${legacy.length}`);
  console.log(`Legacy olgun (5+): ${legacy.filter(m => m.confidence >= 5).length}`);
  console.log(`Legacy rule (10+): ${legacy.filter(m => m.promoted).length}`);

  // Proje bazli
  if (projects.length > 0) {
    let totalPatterns = 0;
    let totalMature = 0;
    for (const p of projects) {
      const mature = loadProjectMature(p.hash);
      totalPatterns += mature.length;
      totalMature += mature.filter(m => m.confidence >= 5).length;
    }
    console.log(`\nProje pattern toplam: ${totalPatterns}`);
    console.log(`Proje olgun toplam: ${totalMature}`);
  }

  // Type dagilimi
  if (legacy.length > 0) {
    const types = new Map<string, number>();
    for (const m of legacy) {
      types.set(m.type, (types.get(m.type) || 0) + 1);
    }
    console.log('\n--- Tip Dagilimi ---');
    for (const [type, count] of [...types.entries()].sort((a, b) => b[1] - a[1])) {
      console.log(`  ${type}: ${count}`);
    }
  }

  // Global promotion detay
  if (global.length > 0) {
    console.log('\n--- Global Promote ---');
    for (const g of global) {
      console.log(`  ${g.pattern}: ${g.totalCount}x, ${g.projects.length} proje`);
    }
  }
}

// Main
const args = process.argv.slice(2);
const cmd = args[0] || 'stats';

switch (cmd) {
  case 'portfolio': cmdPortfolio(); break;
  case 'global': cmdGlobal(); break;
  case 'project': cmdProject(args[1] || ''); break;
  case 'stats': cmdStats(); break;
  default:
    console.log('Instinct CLI - Cross-Project Learning System');
    console.log('Komutlar:');
    console.log('  portfolio      - Tum projeler ve pattern sayilari');
    console.log('  global         - Global promote edilmis pattern\'ler');
    console.log('  project <isim> - Belirli projenin pattern\'leri');
    console.log('  stats          - Genel istatistikler');
}
