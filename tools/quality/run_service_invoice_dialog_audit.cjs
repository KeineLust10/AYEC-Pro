const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-service-invoice-audit-"));
const outputDir = path.join(root, "output", "playwright", `service-invoice-dialog-refresh-${new Date().toISOString().replace(/[:.]/g, "-")}`);
const webPort = 18300 + process.pid % 400;
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

    const auditOutput = path.join(tempRoot, "captures");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "service_invoice_dialog_offscreen_capture.cjs")], {
      cwd: tempRoot,
      encoding: "utf8",
      env: {
        ...process.env,
        AYEC_AUDIT_URL: baseUrl,
        AYEC_AUDIT_CDP_PORT: String(19500 + process.pid % 400),
        AYEC_AUDIT_OUTPUT: auditOutput,
      },
      timeout: 120000,
      windowsHide: true,
    });
    if (audit.stdout) process.stdout.write(audit.stdout);
    if (audit.stderr) process.stderr.write(audit.stderr);
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Service invoice dialog audit exited with status ${audit.status}.`);

    const result = JSON.parse(String(audit.stdout || "").trim().split(/\r?\n/).filter(Boolean).at(-1));
    fs.mkdirSync(outputDir, { recursive: true });
    for (const key of ["screenshot", "baselineScreenshot"]) {
      const source = path.resolve(auditOutput, result[key]);
      const destination = path.join(outputDir, path.basename(source));
      fs.copyFileSync(source, destination);
      result[key] = destination;
    }
    fs.writeFileSync(path.join(outputDir, "audit-result.json"), JSON.stringify(result, null, 2) + "\n", "utf8");
    process.stdout.write(JSON.stringify({ outputDir, result }) + "\n");
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
