const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = process.env.AYEC_AUDIT_OUTPUT_DIR || path.join(root, "output", "playwright");
const port = Number(process.env.AYEC_AUDIT_PORT || 18853);
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || 19239);
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-pc-builder-audit-"));
const browserOutput = path.join(tempRoot, "captures");
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
    const audit = spawnSync(process.execPath, [path.join(__dirname, "pc_builder_offscreen_capture.cjs")], {
      cwd: root,
      encoding: "utf8",
      env: { ...process.env, AYEC_AUDIT_URL: `http://127.0.0.1:${port}/`, AYEC_PC_BUILDER_CDP_PORT: String(debugPort), AYEC_AUDIT_OUTPUT: browserOutput },
      timeout: 120000,
      windowsHide: true,
    });
    if (audit.stderr) process.stderr.write(audit.stderr);
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`PC Builder offscreen audit exited with status ${audit.status}.`);
    const auditLine = String(audit.stdout || "").trim().split(/\r?\n/).filter(Boolean).at(-1) || "{}";
    const auditResult = JSON.parse(auditLine);
    const screenshot = path.join(browserOutput, "pc-builder-current-headless.png");
    if (!fs.existsSync(screenshot)) throw new Error("PC Builder headless capture is missing.");
    fs.mkdirSync(outputDir, { recursive: true });
    const destination = path.join(outputDir, "pc-builder-viewport-matched-source-20261018.png");
    fs.copyFileSync(screenshot, destination);
    const viewportCapture = path.join(browserOutput, "pc-builder-native-viewport-current-headless.png");
    if (!fs.existsSync(viewportCapture)) throw new Error("PC Builder native viewport capture is missing.");
    fs.copyFileSync(viewportCapture, path.join(outputDir, "pc-builder-native-viewport-current-headless.png"));
    auditResult.screenshot = destination;
    const resultPath = path.join(outputDir, "pc-builder-visual-audit-result-20261018.json");
    fs.writeFileSync(resultPath, JSON.stringify(auditResult, null, 2) + "\n", "utf8");
    process.stdout.write(JSON.stringify({ auditResult: resultPath, pairedCapture: destination }) + "\n");
  } finally {
    await stopServer();
    await delay(300);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 300 });
  }
})().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
