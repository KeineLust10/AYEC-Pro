/**
 * Agent Observer - PreToolUse hook (tum tool'larda)
 * Her tool cagirisini ~/.claude/agent-events.jsonl'e loglar
 * Agent spawn, tool kullanimi, zamanlama bilgisi
 */
import { readFileSync, mkdirSync, existsSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';
import { appendWithRotation } from './shared/log-rotation.js';

interface ToolEvent {
  session_id: string;
  hook_event_name?: string;
  tool_name: string;
  tool_input: Record<string, unknown>;
}

interface EventLog {
  ts: string;
  session: string;
  event: string;
  tool: string;
  agent_id?: string;
  agent_type?: string;
  detail: string;
}

function main() {
  let raw = '';
  try { raw = readFileSync(0, 'utf-8'); } catch { return; }
  if (!raw) { console.log('{}'); return; }

  let input: ToolEvent;
  try { input = JSON.parse(raw); } catch { console.log('{}'); return; }

  const logDir = join(homedir(), '.claude');
  if (!existsSync(logDir)) mkdirSync(logDir, { recursive: true });

  const logPath = join(logDir, 'agent-events.jsonl');

  const entry: EventLog = {
    ts: new Date().toISOString(),
    session: input.session_id?.slice(0, 8) || 'unknown',
    event: input.hook_event_name || 'PreToolUse',
    tool: input.tool_name,
    detail: '',
  };

  // Agent spawn tespiti
  if (input.tool_name === 'Agent' || input.tool_name === 'Task') {
    const ti = input.tool_input as Record<string, string>;
    entry.agent_type = ti.subagent_type || ti.type || 'unknown';
    entry.detail = (ti.description || ti.prompt?.slice(0, 80) || '').trim();
  } else if (input.tool_name === 'Bash') {
    const cmd = (input.tool_input as Record<string, string>).command || '';
    entry.detail = cmd.slice(0, 120);
  } else if (input.tool_name === 'Read' || input.tool_name === 'Edit' || input.tool_name === 'Write') {
    entry.detail = ((input.tool_input as Record<string, string>).file_path || '').replace(/\\/g, '/');
  } else if (input.tool_name === 'Grep' || input.tool_name === 'Glob') {
    entry.detail = (input.tool_input as Record<string, string>).pattern || '';
  } else {
    entry.detail = JSON.stringify(input.tool_input).slice(0, 100);
  }

  // CLAUDE_AGENT_ID varsa sub-agent'tan geliyor
  if (process.env.CLAUDE_AGENT_ID) {
    entry.agent_id = process.env.CLAUDE_AGENT_ID;
  }

  appendWithRotation(logPath, JSON.stringify(entry) + '\n');
  console.log('{}');
}

main();
