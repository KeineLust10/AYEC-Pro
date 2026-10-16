const fs = require("node:fs");
const path = require("node:path");
const { spawn, execFileSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const baseUrl = process.env.AYEC_AUDIT_URL || "http://127.0.0.1:8851/";
const debugPort = Number(process.env.AYEC_AUDIT_CDP_PORT || (9300 + process.pid % 500));
const outputDir = path.resolve(process.env.AYEC_AUDIT_OUTPUT || "output/playwright");
const profile = path.join(outputDir, `project-unit-note-headless-profile-${process.pid}`);
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  fs.mkdirSync(outputDir, { recursive: true });
  const browser = spawn(edgePath, [
    "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
    `--remote-debugging-port=${debugPort}`, `--user-data-dir=${profile}`,
    "--window-size=1280,900", baseUrl
  ], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        const pages = await fetch(`http://127.0.0.1:${debugPort}/json`).then(response => response.json());
        target = pages.find(item => item.type === "page" && item.url.startsWith(baseUrl));
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose the audit page.");
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener("open", resolve, { once: true });
      socket.addEventListener("error", reject, { once: true });
    });
    let nextId = 0;
    const pending = new Map();
    const exceptions = [];
    socket.addEventListener("message", event => {
      const message = JSON.parse(event.data);
      if (message.method === "Runtime.exceptionThrown") exceptions.push(message.params.exceptionDetails.exception?.description || message.params.exceptionDetails.text);
      if (!message.id) return;
      const entry = pending.get(message.id);
      if (!entry) return;
      pending.delete(message.id);
      if (message.error) entry.reject(new Error(message.error.message));
      else entry.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      const timer = setTimeout(() => { pending.delete(id); reject(new Error(`CDP command timed out: ${method}`)); }, 15000);
      pending.set(id, {
        resolve(value) { clearTimeout(timer); resolve(value); },
        reject(error) { clearTimeout(timer); reject(error); }
      });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.text);
      return response.result.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Page.navigate", { url: baseUrl });
    let ready = false;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      ready = await evaluate("document.readyState === 'complete' && typeof p9EditUnitProductNote === 'function'");
      if (ready) break;
      await delay(100);
    }
    if (!ready) throw new Error("Project note editor code did not load.");
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      const originalApiFetch = apiFetch;
      const button = document.createElement("button");
      button.className = "p9-note-edit";
      button.dataset.id = "953";
      button.dataset.note = "Original note";
      button.textContent = "Original note";
      document.body.append(button);
      window.__projectNoteRequest = null;
      apiFetch = async (url, options = {}) => { window.__projectNoteRequest = { url, payload: JSON.parse(options.body) }; return { ok: true }; };
      p9EditUnitProductNote(button);
      const dialog = document.querySelector(".p9-unit-note-dialog");
      const textarea = dialog?.querySelector('textarea[name="notes"]');
      const initial = { open: dialog?.open === true, title: dialog?.querySelector("h2")?.textContent, note: textarea?.value };
      textarea.value = "Updated fixture note";
      dialog.querySelector('button[type="submit"]').click();
      await new Promise(resolve => setTimeout(resolve, 0));
      const state = { request: window.__projectNoteRequest, closed: !dialog.isConnected, open: dialog.open, updatedNote: button.dataset.note, buttonText: button.textContent };
      apiFetch = originalApiFetch;
      button.remove();
      return { initial, state };
    })()`);
    const expected = result.state.request?.url === "/api/desktop/table/project_unit_products"
      && result.state.request.payload.id === 953
      && result.state.request.payload.notes === "Updated fixture note"
      && result.state.request.payload._action === "update"
      && result.state.closed && !result.state.open
      && result.state.updatedNote === "Updated fixture note";
    if (!result.initial.open || result.initial.title !== "Teknik Not" || result.initial.note !== "Original note" || !expected || exceptions.length) {
      throw new Error(`Project note editor mismatch: ${JSON.stringify({ result, browserExceptions: exceptions })}`);
    }
    process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length, headless: true }) + "\n");
  } finally {
    try { socket?.close(); } catch (_) {}
    try {
      const query = `$needle='${profile.replace(/'/g, "''")}'; Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msedge.exe' -and $_.CommandLine -like ('*' + $needle + '*') } | Select-Object -ExpandProperty ProcessId`;
      const output = execFileSync("powershell.exe", ["-NoProfile", "-Command", query], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] });
      for (const pid of output.trim().split(/\s+/).filter(value => /^\d+$/.test(value))) {
        try { execFileSync("taskkill", ["/PID", pid, "/T", "/F"], { stdio: "ignore" }); } catch (_) {}
      }
    } catch (_) { try { browser.kill(); } catch (_) {} }
  }
}

run().catch(error => { process.stderr.write(`${error.stack || error}\n`); process.exitCode = 1; });
