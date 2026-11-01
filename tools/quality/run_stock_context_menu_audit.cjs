const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-stock-context-audit-"));
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output", "playwright", "stock-context-current"));
let server;

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

async function stopProcess(child) {
  if (!child?.pid) return;
  await new Promise(resolve => {
    const killer = spawn("taskkill.exe", ["/PID", String(child.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
    killer.once("exit", resolve);
    killer.once("error", resolve);
  });
}

async function run() {
  try {
    const port = await freePort();
    const debugPort = await freePort();
    const baseUrl = `http://127.0.0.1:${port}/`;
    server = spawn(process.env.PYTHON || "python", [
      path.join(root, "Web_Arayuzu", "Main.py"), "--host", "127.0.0.1", "--port", String(port),
      "--db", path.join(tempRoot, "admin.db"), "--tenant-dir", path.join(tempRoot, "tenants"),
    ], { cwd: root, stdio: "ignore", windowsHide: true });
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await new Promise(resolve => setTimeout(resolve, 200));
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "stock_context_menu_offscreen.cjs")], {
      cwd: root,
      encoding: "utf8",
      env: { ...process.env, AYEC_AUDIT_URL: baseUrl, AYEC_AUDIT_CDP_PORT: String(debugPort), AYEC_AUDIT_OUTPUT: outputDir },
      timeout: 120000,
      windowsHide: true,
    });
    if (audit.stdout) process.stdout.write(audit.stdout);
    if (audit.stderr) process.stderr.write(audit.stderr);
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Stock context offscreen audit exited with status ${audit.status}.`);
  } finally {
    await stopProcess(server);
    await new Promise(resolve => setTimeout(resolve, 300));
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
