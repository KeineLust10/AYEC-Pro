/**
 * Agent Specialization Tuner
 * skill-matrix.json'dan agent performans analizi yaparak
 * tuning onerileri uretir.
 *
 * Calistirma: node dist/agent-tuner.mjs
 * CLI: node dist/canavar-cli.mjs tune
 */
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';
import { homedir } from 'os';

interface SkillStats {
  attempts: number;
  successes: number;
  rate: number;
}

interface AgentProfile {
  total_tasks: number;
  successes: number;
  failures: number;
  success_rate: number;
  skills: Record<string, SkillStats>;
  common_errors: string[];
  last_active: string;
}

interface SkillMatrix {
  agents: Record<string, AgentProfile>;
  updated_at: string;
}

interface TuningRecommendation {
  agent: string;
  action: 'retrain' | 'specialize' | 'reassign' | 'promote';
  reason: string;
  details: string;
  priority: 'high' | 'medium' | 'low';
}

interface TuningReport {
  ts: string;
  total_agents: number;
  recommendations: TuningRecommendation[];
  summary: {
    retrain: number;
    specialize: number;
    reassign: number;
    promote: number;
  };
}

function main() {
  const canavarDir = join(homedir(), '.claude', 'canavar');
  const matrixPath = join(canavarDir, 'skill-matrix.json');
  const cacheDir = join(homedir(), '.claude', 'cache');
  const outputPath = join(cacheDir, 'tuning-recommendations.json');

  if (!existsSync(matrixPath)) {
    console.log('skill-matrix.json bulunamadi. Once birkac session calistirin.');
    return;
  }

  const matrix: SkillMatrix = JSON.parse(readFileSync(matrixPath, 'utf-8'));
  const recommendations: TuningRecommendation[] = [];

  for (const [agentName, profile] of Object.entries(matrix.agents)) {
    // En az 2 gorev yapmis olmali
    if (profile.total_tasks < 2) continue;

    // RETRAIN: Dusuk basari orani
    if (profile.success_rate < 0.5) {
      recommendations.push({
        agent: agentName,
        action: 'retrain',
        reason: `Basari orani cok dusuk: %${(profile.success_rate * 100).toFixed(0)}`,
        details: `${profile.failures}/${profile.total_tasks} gorevde hata. Sik hatalar: ${profile.common_errors.join(', ') || 'yok'}`,
        priority: 'high',
      });
    }

    // SPECIALIZE: Belirli skill'de yuksek, diger skill'lerde dusuk
    const skills = Object.entries(profile.skills).filter(([, s]) => s.attempts >= 2);
    if (skills.length >= 2) {
      const highSkills = skills.filter(([, s]) => s.rate >= 0.8);
      const lowSkills = skills.filter(([, s]) => s.rate < 0.5);

      if (highSkills.length > 0 && lowSkills.length > 0) {
        recommendations.push({
          agent: agentName,
          action: 'specialize',
          reason: `Bazi skill'lerde iyi, bazilarinda zayif`,
          details: `Guclu: ${highSkills.map(([s, st]) => `${s}(%${(st.rate * 100).toFixed(0)})`).join(', ')}. Zayif: ${lowSkills.map(([s, st]) => `${s}(%${(st.rate * 100).toFixed(0)})`).join(', ')}`,
          priority: 'medium',
        });
      }
    }

    // PROMOTE: Yuksek basari orani (ve yeterli gorev)
    if (profile.success_rate >= 0.9 && profile.total_tasks >= 5) {
      recommendations.push({
        agent: agentName,
        action: 'promote',
        reason: `Mukemmel performans: %${(profile.success_rate * 100).toFixed(0)} basari`,
        details: `${profile.successes}/${profile.total_tasks} gorev basarili. Guclu skill'ler: ${Object.entries(profile.skills).filter(([, s]) => s.rate >= 0.8).map(([s]) => s).join(', ') || 'genel'}`,
        priority: 'low',
      });
    }
  }

  // REASSIGN: Hic kullanilmayan agent'lar (son 30 gun aktif degil)
  const thirtyDaysAgo = new Date();
  thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);

  for (const [agentName, profile] of Object.entries(matrix.agents)) {
    if (profile.last_active && new Date(profile.last_active) < thirtyDaysAgo) {
      recommendations.push({
        agent: agentName,
        action: 'reassign',
        reason: `30+ gundur aktif degil`,
        details: `Son aktif: ${profile.last_active}. Toplam gorev: ${profile.total_tasks}`,
        priority: 'low',
      });
    }
  }

  // Priority'ye gore sirala
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  recommendations.sort((a, b) => priorityOrder[a.priority] - priorityOrder[b.priority]);

  const report: TuningReport = {
    ts: new Date().toISOString(),
    total_agents: Object.keys(matrix.agents).length,
    recommendations,
    summary: {
      retrain: recommendations.filter(r => r.action === 'retrain').length,
      specialize: recommendations.filter(r => r.action === 'specialize').length,
      reassign: recommendations.filter(r => r.action === 'reassign').length,
      promote: recommendations.filter(r => r.action === 'promote').length,
    },
  };

  if (!existsSync(cacheDir)) mkdirSync(cacheDir, { recursive: true });
  writeFileSync(outputPath, JSON.stringify(report, null, 2));

  // Console output
  console.log(`=== AGENT TUNING RAPORU ===\n`);
  console.log(`Toplam agent: ${report.total_agents}`);
  console.log(`Oneri sayisi: ${recommendations.length}`);
  console.log(`  Retrain: ${report.summary.retrain} | Specialize: ${report.summary.specialize} | Reassign: ${report.summary.reassign} | Promote: ${report.summary.promote}\n`);

  if (recommendations.length === 0) {
    console.log('Hicbir oneri yok - tum agent\'lar iyi durumda.');
    return;
  }

  for (const rec of recommendations) {
    const icon = rec.action === 'retrain' ? '[!]' : rec.action === 'specialize' ? '[~]' : rec.action === 'reassign' ? '[-]' : '[+]';
    console.log(`${icon} ${rec.agent} → ${rec.action.toUpperCase()}`);
    console.log(`   ${rec.reason}`);
    console.log(`   ${rec.details}\n`);
  }
}

main();
