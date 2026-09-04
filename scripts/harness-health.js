#!/usr/bin/env node
/**
 * harness-health.js — 健康检查 CLI
 *
 * 收集各子系统指标并输出 JSON。参考 gstack 的环形缓冲区 + ECC v2 的 Rust control plane。
 *
 * 用法：node scripts/harness-health.js [--json] [--check=<name>]
 */

const fs = require('fs');
const path = require('path');

const FOUNDRY_DIR = path.resolve(__dirname, '..');
const RUNTIME_DIR = path.join(FOUNDRY_DIR, '..', '.ai-runtime-artifacts');

// === Health Check Functions ===

function checkConfigValidity() {
  const files = [
    'core/orchestration/domain-config.yaml',
    'core/orchestration/config.defaults.yaml'
  ];
  // 2026-09 phase-2: hooks/guardrails/guardrail-config.json 已删除，
  // guardrail 配置 fallback 到 skills/agent-shield/SKILL.md

  const results = files.map(f => {
    const fullPath = path.join(FOUNDRY_DIR, f);
    const exists = fs.existsSync(fullPath);
    let valid = exists;
    if (exists && f.endsWith('.json')) {
      try { JSON.parse(fs.readFileSync(fullPath, 'utf8')); }
      catch { valid = false; }
    }
    return { file: f, exists, valid };
  });

  const allValid = results.every(r => r.valid);
  return {
    status: allValid ? 'pass' : 'fail',
    message: allValid ? 'All config files valid' : `${results.filter(r => !r.valid).length} config files invalid`,
    details: results.filter(r => !r.valid)
  };
}

function checkReferenceIntegrity() {
  const checks = [
    { name: 'NEVER.md', path: 'core/NEVER.md' },
    { name: 'intent-routing.md', path: 'core/intent-routing.md' },
    { name: 'dispatcher-workflow.md', path: 'core/orchestration/dispatcher-workflow.md' },
    { name: 'domain-config.yaml', path: 'core/orchestration/domain-config.yaml' },
    // 2026-09 phase-2: guardrail-config.json 已删，参考 skills/agent-shield/SKILL.md
    { name: 'execution-context model', path: 'core/orchestration/execution-context/model.yaml' },
    { name: 'execution-context protocol', path: 'core/orchestration/execution-context/provider-protocol.md' }
  ];

  const missing = checks.filter(c => !fs.existsSync(path.join(FOUNDRY_DIR, c.path)));
  return {
    status: missing.length === 0 ? 'pass' : 'warn',
    message: missing.length === 0 ? 'All core files present' : `${missing.length} core files missing`,
    missing: missing.map(m => m.path)
  };
}

function checkInstinctQuality() {
  const instinctDir = path.join(FOUNDRY_DIR, 'references', 'instincts');
  let totalCount = 0;
  let avgConfidence = 0;
  let belowThreshold = 0;

  // Count instinct files in project and global dirs
  function countInstincts(dir) {
    if (!fs.existsSync(dir)) return;
    const files = fs.readdirSync(dir);
    files.forEach(f => {
      if (f.endsWith('.yaml') || f.endsWith('.yml')) {
        totalCount++;
        try {
          const content = fs.readFileSync(path.join(dir, f), 'utf8');
          const confMatch = content.match(/confidence:\s*([\d.]+)/);
          if (confMatch) {
            const conf = parseFloat(confMatch[1]);
            avgConfidence += conf;
            if (conf < 0.3) belowThreshold++;
          }
        } catch {}
      }
    });
  }

  const projectDir = path.join(instinctDir, 'project');
  const globalDir = path.join(instinctDir, 'global', 'instincts');

  if (fs.existsSync(projectDir)) {
    fs.readdirSync(projectDir).forEach(sub => {
      const instinctsPath = path.join(projectDir, sub, 'instincts');
      if (fs.existsSync(instinctsPath)) countInstincts(instinctsPath);
    });
  }
  if (fs.existsSync(globalDir)) countInstincts(globalDir);

  if (totalCount > 0) avgConfidence = Math.round((avgConfidence / totalCount) * 100) / 100;

  return {
    status: totalCount > 0 ? (avgConfidence >= 0.7 ? 'pass' : 'warn') : 'info',
    total_count: totalCount,
    avg_confidence: avgConfidence,
    below_threshold_count: belowThreshold,
    message: totalCount === 0
      ? 'No instincts recorded yet'
      : `${totalCount} instincts, avg confidence ${avgConfidence}`
  };
}

function checkSkillCoverage() {
  const skillsDir = path.join(FOUNDRY_DIR, 'skills');
  if (!fs.existsSync(skillsDir)) {
    return { status: 'fail', message: 'Skills directory missing' };
  }

  const entries = fs.readdirSync(skillsDir, { withFileTypes: true });
  const dirs = entries.filter(e => e.isDirectory());

  let withMeta = 0;
  let withPurpose = 0;

  dirs.forEach(d => {
    const skillMd = path.join(skillsDir, d.name, 'SKILL.md');
    if (fs.existsSync(skillMd)) {
      withMeta++;
      try {
        const content = fs.readFileSync(skillMd, 'utf8');
        if (content.includes('description:') && content.includes('---')) {
          withPurpose++;
        }
      } catch {}
    }
  });

  return {
    status: 'pass',
    total_skills: dirs.length,
    with_meta: withMeta,
    with_purpose: withPurpose,
    coverage_pct: dirs.length > 0 ? Math.round((withMeta / dirs.length) * 100) : 0
  };
}

function checkAgentFormatConsistency() {
  const agentsDir = path.join(FOUNDRY_DIR, 'agents');
  if (!fs.existsSync(agentsDir)) {
    return { status: 'fail', message: 'Agents directory missing' };
  }

  const files = fs.readdirSync(agentsDir).filter(f => f.endsWith('.md') && f !== 'README.md');
  let yamlFm = 0;
  let plainMd = 0;

  files.forEach(f => {
    const firstLine = fs.readFileSync(path.join(agentsDir, f), 'utf8').split('\n')[0] || '';
    if (firstLine.startsWith('---')) yamlFm++;
    else plainMd++;
  });

  return {
    status: yamlFm > 0 ? (yamlFm > plainMd ? 'pass' : 'warn') : 'warn',
    total_agents: files.length,
    yaml_frontmatter: yamlFm,
    plain_markdown: plainMd,
    consistency_pct: Math.round((yamlFm / files.length) * 100)
  };
}

function checkGuardrailConfig() {
  const guardrailPath = path.join(FOUNDRY_DIR, 'hooks', 'guardrails', 'guardrail-config.json');
  if (!fs.existsSync(guardrailPath)) {
    return { status: 'fail', message: 'Guardrail config missing (P0-2)' };
  }

  try {
    const config = JSON.parse(fs.readFileSync(guardrailPath, 'utf8'));
    const inputRules = config.guardrails?.input?.rules?.length || 0;
    const outputRules = config.guardrails?.output?.rules?.length || 0;
    const enabledInput = config.guardrails?.input?.rules?.filter(r => r.enabled !== false).length || 0;
    const enabledOutput = config.guardrails?.output?.rules?.filter(r => r.enabled !== false).length || 0;

    return {
      status: (enabledInput > 0 && enabledOutput > 0) ? 'pass' : 'warn',
      input_rules: inputRules,
      input_enabled: enabledInput,
      output_rules: outputRules,
      output_enabled: enabledOutput
    };
  } catch {
    return { status: 'fail', message: 'Guardrail config invalid JSON' };
  }
}

function checkExecutionContext() {
  const modelPath = path.join(FOUNDRY_DIR, 'core', 'orchestration', 'execution-context', 'model.yaml');
  const protocolPath = path.join(FOUNDRY_DIR, 'core', 'orchestration', 'execution-context', 'provider-protocol.md');
  const providersDir = path.join(FOUNDRY_DIR, 'core', 'orchestration', 'execution-context', 'providers');

  const providers = fs.existsSync(providersDir)
    ? fs.readdirSync(providersDir).filter(f => f.endsWith('.md'))
    : [];

  return {
    status: (fs.existsSync(modelPath) && fs.existsSync(protocolPath)) ? 'pass' : 'fail',
    model_exists: fs.existsSync(modelPath),
    protocol_exists: fs.existsSync(protocolPath),
    providers: providers.map(p => p.replace('.md', ''))
  };
}

// === Main ===

function runAllChecks() {
  return {
    timestamp: new Date().toISOString(),
    system_health: {
      status: null, // computed below
      checks: {
        config_validity: checkConfigValidity(),
        reference_integrity: checkReferenceIntegrity(),
        execution_context: checkExecutionContext(),
        guardrail_config: checkGuardrailConfig(),
        instinct_quality: checkInstinctQuality(),
        skill_coverage: checkSkillCoverage(),
        agent_format_consistency: checkAgentFormatConsistency()
      }
    },
    token_estimates: {
      core_rules_total_lines: countLinesRecursive(path.join(FOUNDRY_DIR, 'core')),
      entry_overhead_lines: countFile(path.join(FOUNDRY_DIR, 'core', 'intent-routing.md'))
    }
  };
}

function countLinesRecursive(dir) {
  if (!fs.existsSync(dir)) return 0;
  let lines = 0;
  function walk(d) {
    fs.readdirSync(d, { withFileTypes: true }).forEach(e => {
      const full = path.join(d, e.name);
      if (e.isDirectory()) walk(full);
      else if (e.name.endsWith('.md') || e.name.endsWith('.yaml') || e.name.endsWith('.json')) {
        lines += fs.readFileSync(full, 'utf8').split('\n').length;
      }
    });
  }
  walk(dir);
  return lines;
}

function countFile(filepath) {
  if (!fs.existsSync(filepath)) return 0;
  return fs.readFileSync(filepath, 'utf8').split('\n').length;
}

// Execute
const report = runAllChecks();

// Compute overall status
const checks = Object.values(report.system_health.checks);
const failures = checks.filter(c => c.status === 'fail');
const warnings = checks.filter(c => c.status === 'warn');
if (failures.length > 0) {
  report.system_health.status = 'unhealthy';
} else if (warnings.length > 0) {
  report.system_health.status = 'degraded';
} else {
  report.system_health.status = 'healthy';
}

// Output
const args = process.argv.slice(2);
const jsonMode = args.includes('--json');

if (jsonMode) {
  console.log(JSON.stringify(report, null, 2));
} else {
  console.log('=== Harness Foundry Health Report ===');
  console.log(`Status: ${report.system_health.status.toUpperCase()}`);
  console.log('');

  for (const [name, check] of Object.entries(report.system_health.checks)) {
    const icon = check.status === 'pass' ? '✅' : check.status === 'warn' ? '⚠️' : '❌';
    console.log(`${icon} ${name}: ${check.message || check.status}`);
  }

  console.log('');
  console.log(`Token Estimates:`);
  console.log(`  Core rules total lines: ${report.token_estimates.core_rules_total_lines}`);
  console.log(`  Entry overhead lines: ${report.token_estimates.entry_overhead_lines}`);
}
