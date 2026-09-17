/**
 * Anti-Rationalization - Stop hook
 * Claude'un "scope disinda", "sonra yapariz" gibi kacis kaliplarini tespit eder
 * Tespit ederse uyari mesaji dondurur
 */
import { readFileSync } from 'fs';

interface StopInput {
  session_id: string;
  transcript?: string;
  stop_hook_active?: boolean;
}

const RATIONALIZATION_PATTERNS: Array<{ pattern: RegExp; label: string }> = [
  { pattern: /out of scope/i, label: 'scope bahane' },
  { pattern: /scope d[iı][sş][iı]nda/i, label: 'scope bahane' },
  { pattern: /beyond the scope/i, label: 'scope bahane' },
  { pattern: /pre-?existing\s+(issue|problem|bug)/i, label: 'sorunu başkasına atma' },
  { pattern: /follow[- ]?up\s+(task|issue|ticket)/i, label: 'erteleme' },
  { pattern: /separate\s+(pr|pull request|ticket|task)/i, label: 'erteleme' },
  { pattern: /future\s+(improvement|enhancement|work|iteration)/i, label: 'erteleme' },
  { pattern: /sonra\s+(yap|bak|halle|duzelt)/i, label: 'erteleme' },
  { pattern: /ilerde\s+(yap|bak|ekle)/i, label: 'erteleme' },
  { pattern: /simdilik\s+(yeterli|bu kadar|boyle kalsin)/i, label: 'tamamlanmamis is' },
  { pattern: /left as.{0,20}exercise/i, label: 'tamamlanmamis is' },
  { pattern: /TODO:?\s+implement/i, label: 'tamamlanmamis is' },
  { pattern: /placeholder\s+(for now|implementation)/i, label: 'tamamlanmamis is' },
  { pattern: /not\s+(possible|feasible)\s+(right now|at this time|currently)/i, label: 'kaçınma' },
  { pattern: /can'?t\s+be\s+done/i, label: 'kaçınma' },
  { pattern: /yapam[iı]yorum/i, label: 'kaçınma' },
];

function getLastAssistantMessage(transcript: string): string {
  // Transkriptten son assistant mesajini bul
  const parts = transcript.split(/\n(?=(?:Human|Assistant):)/i);
  const assistantParts = parts.filter(p => /^Assistant:/i.test(p.trim()));
  if (assistantParts.length === 0) return '';
  return assistantParts[assistantParts.length - 1] || '';
}

function main() {
  let raw = '';
  try { raw = readFileSync(0, 'utf-8'); } catch { return; }
  if (!raw) { console.log('{}'); return; }

  let input: StopInput;
  try { input = JSON.parse(raw); } catch { console.log('{}'); return; }

  const transcript = input.transcript || '';
  if (transcript.length < 50) {
    console.log('{}');
    return;
  }

  const lastMessage = getLastAssistantMessage(transcript);
  if (!lastMessage || lastMessage.length < 20) {
    console.log('{}');
    return;
  }

  const detected: string[] = [];
  for (const { pattern, label } of RATIONALIZATION_PATTERNS) {
    if (pattern.test(lastMessage)) {
      detected.push(label);
    }
  }

  // Deduplicate
  const unique = [...new Set(detected)];

  if (unique.length > 0) {
    console.log(JSON.stringify({
      result: `⚠️ ANTI-RATIONALIZATION: ${unique.length} kacis kalıbı tespit edildi: ${unique.join(', ')}. Is gercekten tamamlandi mi?`
    }));
  } else {
    console.log('{}');
  }
}

main();
