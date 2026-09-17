/**
 * Session Start Recall Hook - SessionStart
 *
 * Session başladığında OPC memory'den ilgili öğrenimleri çeker.
 * Continuity ledger veya handoff dosyalarından query oluşturur.
 */
import { spawnSync } from 'child_process';
import { readFileSync, existsSync, readdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

interface SessionStartInput {
  source: string;
  cwd: string;
}

function readStdin(): string {
  return readFileSync(0, 'utf-8');
}

function extractQueryFromContext(cwd: string): string {
  // Continuity ledger'dan query çıkar
  const ledgerDir = join(cwd, 'thoughts', 'ledgers');
  if (existsSync(ledgerDir)) {
    const files = readdirSync(ledgerDir);
    const ledger = files.find((f) => f.startsWith('CONTINUITY_CLAUDE-'));
    if (ledger) {
      const sessionName = ledger.replace('CONTINUITY_CLAUDE-', '').replace('.md', '');
      return sessionName.replace(/-/g, ' ');
    }
  }

  // Handoff dosyalarından query çıkar
  const handoffDir = join(cwd, 'thoughts', 'shared', 'handoffs');
  if (existsSync(handoffDir)) {
    const result = spawnSync('find', [handoffDir, '-name', '*.yaml', '-type', 'f'], {
      encoding: 'utf-8',
    });
    if (result.stdout) {
      const files = result.stdout.trim().split('\n').filter(Boolean);
      if (files.length > 0) {
        const latest = files[files.length - 1];
        const content = readFileSync(latest, 'utf-8');
        const goalMatch = content.match(/^goal:\s*(.+)$/m);
        if (goalMatch) {
          return goalMatch[1].slice(0, 100);
        }
      }
    }
  }

  return 'session patterns learnings';
}

async function main() {
  const input: SessionStartInput = JSON.parse(readStdin());

  if (!['startup', 'resume', 'clear'].includes(input.source)) {
    return;
  }

  const projectDir = process.env.CLAUDE_PROJECT_DIR || input.cwd;
  const claudeDir = join(homedir(), '.claude');
  const query = extractQueryFromContext(projectDir);

  const result = spawnSync('uv', [
    'run',
    'python',
    join(claudeDir, 'scripts', 'core', 'recall_learnings.py'),
    '--query',
    query,
    '--k',
    '3',
  ], {
    encoding: 'utf-8',
    cwd: claudeDir,
    env: { ...process.env, PYTHONPATH: join(claudeDir, 'scripts') },
    timeout: 20_000,
  });

  if (result.status === 0 && result.stdout) {
    const lines = result.stdout.split('\n');
    const learningLines = lines.filter(
      (l) => l.includes('[0.') || l.trim().startsWith('What ') || l.trim().startsWith('Decisions:'),
    );

    if (learningLines.length > 0) {
      console.log('');
      console.log('┌─────────────────────────────────────────────────────────────┐');
      console.log('│  📚 RECALLED LEARNINGS                                      │');
      console.log('├─────────────────────────────────────────────────────────────┤');
      for (const line of learningLines) {
        const trimmed = line.trim();
        const scoreMatch = trimmed.match(/\d+\.\s*\[(\d\.\d+)\]\s*Session:\s*(\S+)/);
        if (scoreMatch) {
          const score = scoreMatch[1];
          const session = scoreMatch[2].slice(0, 35);
          console.log(`│  ⭐ [${score}] ${session.padEnd(48)} │`);
          continue;
        }
        if (trimmed.startsWith('What worked:')) {
          const content = trimmed.slice(12).trim().slice(0, 50);
          console.log(`│     ✓ ${content.padEnd(52)} │`);
        } else if (trimmed.startsWith('What failed:')) {
          const content = trimmed.slice(12).trim().slice(0, 50);
          console.log(`│     ✗ ${content.padEnd(52)} │`);
        } else if (trimmed.startsWith('Decisions:')) {
          const content = trimmed.slice(10).trim().slice(0, 50);
          console.log(`│     → ${content.padEnd(52)} │`);
        }
      }
      console.log('└─────────────────────────────────────────────────────────────┘');
      console.log('');
    }
  }
}

main().catch(() => {});
