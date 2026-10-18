const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const port = Number(process.env.AYEC_AUDIT_PORT || 18852);
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 19238);
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-external-tracking-audit-"));
const persistentOutput = process.env.AYEC_AUDIT_OUTPUT_DIR ? path.resolve(process.env.AYEC_AUDIT_OUTPUT_DIR) : null;
const output = persistentOutput || path.join(tempRoot, "captures");
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function waitForServer() {
  for (let attempt = 0; attempt < 150; attempt += 1) {
    try { if ((await fetch(`http://127.0.0.1:${port}/`)).ok) return; } catch (_) {}
    await delay(200);
  }
  throw new Error("Temporary AYEC web server did not start.");
}

async function stopServer() {
  if (!server.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill", ["/PID", String(server.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
}

(async () => {
  try {
    await waitForServer();
    const audit = spawnSync(process.execPath, [path.join(__dirname, "external_tracking_double_click_offscreen.cjs")], {
      cwd: root,
      encoding: "utf8",
      env: { ...process.env, AYEC_AUDIT_URL: `http://127.0.0.1:${port}/`, AYEC_AUDIT_CDP_PORT: String(debugPort), AYEC_AUDIT_OUTPUT: output },
      timeout: 120000,
      windowsHide: true,
    });
    if (persistentOutput) {
      fs.mkdirSync(persistentOutput, { recursive: true });
      fs.writeFileSync(path.join(persistentOutput, "external-tracking-audit-result.json"), audit.stdout || "", "utf8");
    }
    if (audit.stdout) process.stdout.write(audit.stdout);
    if (audit.stderr) process.stderr.write(audit.stderr);
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Offscreen browser audit exited with status ${audit.status}.`);
  } finally {
    await stopServer();
    await delay(300);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
})().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
