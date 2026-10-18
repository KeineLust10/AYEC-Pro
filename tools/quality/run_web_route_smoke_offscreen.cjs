const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/web-route-smoke-20261017"));
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-web-route-smoke-"));
const port = Number(process.env.AYEC_AUDIT_PORT || 19000 + process.pid % 400);
const baseUrl = `http://127.0.0.1:${port}/`;
const server = spawn(process.env.PYTHON || "python", [path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants")], { cwd: root, stdio: "ignore", windowsHide: true });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
}

(async () => {
  fs.mkdirSync(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "runner-result.json");
  const logPath = path.join(outputDir, "runner-process.log");
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "web_route_smoke_offscreen.cjs")], { cwd: root, encoding: "utf8", env: { ...process.env, AYEC_AUDIT_URL: baseUrl, AYEC_AUDIT_OUTPUT: outputDir }, timeout: 180000, windowsHide: true });
    fs.writeFileSync(logPath, `${audit.stdout || ""}${audit.stderr || ""}`, "utf8");
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Web route smoke exited with status ${audit.status}.`);
    const resultFile = path.join(outputDir, "route-smoke-result.json");
    if (!fs.existsSync(resultFile)) throw new Error("Web route smoke result file is missing.");
    fs.writeFileSync(resultPath, JSON.stringify({ ok: true, ...JSON.parse(fs.readFileSync(resultFile, "utf8")) }, null, 2), "utf8");
  } catch (error) {
    fs.writeFileSync(resultPath, JSON.stringify({ ok: false, error: String(error.stack || error) }, null, 2), "utf8");
    process.exitCode = 1;
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(() => { process.exitCode = 1; });
