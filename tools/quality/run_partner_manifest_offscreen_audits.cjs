const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-partner-audit-"));
const outputDir = path.join(root, "output", "playwright", `partner-manifest-refresh-${new Date().toISOString().replace(/[:.]/g, "-")}`);
const webPort = 18800 + process.pid % 300;
const baseUrl = `http://127.0.0.1:${webPort}/`;
const server = spawn(process.env.PYTHON || "python", [
  path.join(root, "Web_Arayuzu", "Main.py"),
  "--host", "127.0.0.1",
  "--port", String(webPort),
  "--db", path.join(tempRoot, "admin.db"),
  "--tenant-dir", path.join(tempRoot, "tenants"),
], { cwd: root, stdio: "ignore", windowsHide: true });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
  });
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

    const audits = [];
    for (const [index, script] of ["partner_finance_manifest_offscreen.cjs", "partner_shipment_manifest_offscreen.cjs"].entries()) {
      const audit = spawnSync(process.execPath, [path.join(__dirname, script)], {
        cwd: tempRoot,
        encoding: "utf8",
        env: { ...process.env, AYEC_AUDIT_URL: baseUrl, AYEC_AUDIT_CDP_PORT: String(19000 + process.pid % 500 + index) },
        timeout: 120000,
        windowsHide: true,
      });
      if (audit.stdout) process.stdout.write(audit.stdout);
      if (audit.stderr) process.stderr.write(audit.stderr);
      if (audit.error) throw audit.error;
      if (audit.status !== 0) throw new Error(`${script} exited with status ${audit.status}.`);
      const result = JSON.parse(audit.stdout.trim().split(/\r?\n/).at(-1));
      audits.push({ script, result });
    }

    fs.mkdirSync(outputDir, { recursive: true });
    for (const { result } of audits) {
      const source = path.resolve(tempRoot, result.screenshot);
      fs.copyFileSync(source, path.join(outputDir, path.basename(result.screenshot)));
    }
    fs.writeFileSync(path.join(outputDir, "audit-result.json"), JSON.stringify(audits, null, 2) + "\n", "utf8");
    process.stdout.write(JSON.stringify({ outputDir, audits: audits.map(({ script, result }) => ({ script, exceptions: result.exceptions, screenshot: path.basename(result.screenshot) })) }) + "\n");
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
