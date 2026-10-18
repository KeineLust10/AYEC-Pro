const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-sidebar-audit-"));
const port = 18900 + process.pid % 300;
const baseUrl = `http://127.0.0.1:${port}/`;
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output", "playwright"));
const viewportWidth = process.env.AYEC_AUDIT_WIDTH || "1600";
const viewportHeight = process.env.AYEC_AUDIT_HEIGHT || "720";
const captureTop = process.env.AYEC_AUDIT_TOP || "70";
const captureHeight = process.env.AYEC_AUDIT_CAPTURE_HEIGHT || "650";
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
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    for (const sector of ["teknik_servis", "otomotiv"]) {
      const audit = spawnSync(process.execPath, [path.join(__dirname, "sidebar_parity_offscreen_capture.cjs")], {
        cwd: root,
        encoding: "utf8",
        env: { ...process.env, AYEC_AUDIT_URL: baseUrl, AYEC_AUDIT_OUTPUT: outputDir, AYEC_AUDIT_SECTOR: sector, AYEC_AUDIT_WIDTH: viewportWidth, AYEC_AUDIT_HEIGHT: viewportHeight, AYEC_AUDIT_TOP: captureTop, AYEC_AUDIT_CAPTURE_HEIGHT: captureHeight, AYEC_AUDIT_CAPTURE_ONLY: "1" },
        timeout: 120000,
        windowsHide: true,
      });
      if (audit.stdout) process.stdout.write(audit.stdout);
      if (audit.stderr) process.stderr.write(audit.stderr);
      if (audit.error) throw audit.error;
      if (audit.status !== 0) throw new Error(`Sidebar offscreen audit for ${sector} exited with status ${audit.status}.`);
    }
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
