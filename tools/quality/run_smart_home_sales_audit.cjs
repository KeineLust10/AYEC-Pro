const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-smart-home-audit-"));
const port = 18500 + process.pid % 500;
const cdpPort = 19500 + process.pid % 500;
const baseUrl = `http://127.0.0.1:${port}/`;
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => { const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true }); killer.once("exit", resolve); });
}

(async () => {
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "smart_home_sales_offscreen.cjs")], { cwd: root, encoding: "utf8", env: { ...process.env, AYEC_AUDIT_URL: baseUrl, AYEC_AUDIT_CDP_PORT: String(cdpPort) }, timeout: 120000, windowsHide: true });
    if (audit.stdout) process.stdout.write(audit.stdout);
    if (audit.stderr) process.stderr.write(audit.stderr);
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Smart Home Sales offscreen audit exited with status ${audit.status}.`);
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
