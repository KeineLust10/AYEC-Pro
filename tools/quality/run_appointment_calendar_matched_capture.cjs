const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const root = path.resolve(__dirname, "../..");
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || path.join(root, "output/playwright/appointment-calendar-matched-20261017"));
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-calendar-match-"));
const port = 19400 + process.pid % 400;
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
  const resultPath = path.join(outputDir, "audit-result.json");
  const logPath = path.join(outputDir, "audit-process.log");
  try {
    let ready = false;
    for (let attempt = 0; attempt < 150; attempt += 1) {
      try { ready = (await fetch(baseUrl)).ok; } catch (_) {}
      if (ready) break;
      await delay(200);
    }
    if (!ready) throw new Error("Temporary AYEC web server did not start.");
    const audit = spawnSync(process.execPath, [path.join(__dirname, "appointment_calendar_offscreen_capture.cjs")], {
      cwd: root,
      encoding: "utf8",
      env: {
        ...process.env,
        AYEC_AUDIT_URL: baseUrl,
        AYEC_AUDIT_OUTPUT: outputDir,
        AYEC_CALENDAR_MATCHED_VIEWPORT: process.env.AYEC_CALENDAR_MATCHED_VIEWPORT || "1",
        AYEC_VIEWPORT_WIDTH: process.env.AYEC_VIEWPORT_WIDTH || "1280",
        AYEC_VIEWPORT_HEIGHT: process.env.AYEC_VIEWPORT_HEIGHT || "1024",
        AYEC_CALENDAR_CONTENT_WIDTH: process.env.AYEC_CALENDAR_CONTENT_WIDTH || "1040",
      },
      timeout: 180000,
      windowsHide: true,
    });
    fs.writeFileSync(logPath, `${audit.stdout || ""}${audit.stderr || ""}`, "utf8");
    if (audit.error) throw audit.error;
    if (audit.status !== 0) throw new Error(`Matched calendar capture exited with status ${audit.status}.`);
    const finalLine = String(audit.stdout || "").trim().split(/\r?\n/).filter(Boolean).at(-1) || "{}";
    fs.writeFileSync(resultPath, JSON.stringify(JSON.parse(finalLine), null, 2), "utf8");
  } catch (error) {
    fs.writeFileSync(resultPath, JSON.stringify({ error: String(error.stack || error) }, null, 2), "utf8");
    process.exitCode = 1;
  } finally {
    await stopProcess(server);
    try { fs.rmSync(tempRoot, { recursive: true, force: true }); } catch (_) {}
  }
})().catch(() => { process.exitCode = 1; });
