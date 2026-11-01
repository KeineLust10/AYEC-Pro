const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/service-list-date-filter"));
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-service-list-audit-"));
const serverRoot = path.join(root, "Web_Arayuzu");

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = net.createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const port = probe.address().port;
      probe.close(error => error ? reject(error) : resolve(port));
    });
  });
}

function stopProcess(child) {
  if (!child?.pid) return Promise.resolve();
  return new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
    killer.once("error", resolve);
  });
}

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const port = await freePort();
  const baseUrl = `http://127.0.0.1:${port}/`;
  const dbPath = path.join(tempRoot, "admin.db");
  const tenantPath = path.join(tempRoot, "tenants");
  const backend = spawn(process.env.PYTHON || "python", [path.join(serverRoot, "Main.py"), "--host", "127.0.0.1", "--port", String(port), "--db", dbPath, "--tenant-dir", tenantPath], { cwd: root, stdio: "ignore", windowsHide: true });
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try {
        const response = await fetch(baseUrl);
        ready = response.ok;
      } catch (_) {}
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "service_list_date_filter_offscreen.cjs")], {
      cwd: tempRoot,
      encoding: "utf8",
      env: { ...process.env, AYEC_AUDIT_URL: baseUrl },
      timeout: 180000,
      windowsHide: true,
    });
    fs.writeFileSync(path.join(outputDir, "service-list-date-audit.log"), `${audit.stdout || ""}${audit.stderr || ""}`, "utf8");
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Service-list/date audit exited with status ${audit.status}.`);
    const resultLine = String(audit.stdout || "").trim().split(/\r?\n/).at(-1);
    const result = JSON.parse(resultLine);
    fs.writeFileSync(path.join(outputDir, "service-list-date-audit.json"), JSON.stringify({ ok: true, ...result }, null, 2), "utf8");
  } catch (error) {
    fs.writeFileSync(path.join(outputDir, "service-list-date-audit.json"), JSON.stringify({ ok: false, error: String(error.stack || error) }, null, 2), "utf8");
    process.exitCode = 1;
  } finally {
    await stopProcess(backend);
    const tempPrefix = path.join(os.tmpdir(), "ayec-service-list-audit-");
    if (!path.resolve(tempRoot).startsWith(tempPrefix)) throw new Error("Temporary cleanup path escaped the audit directory.");
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
}

run().catch(error => {
  process.stderr.write(`${String(error.stack || error)}\n`);
  process.exitCode = 1;
});
