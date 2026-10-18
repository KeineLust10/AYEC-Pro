const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_PROFORMA_CDP_PORT || (19400 + process.pid % 500));
const baseUrl = process.env.AYEC_PROFORMA_BASE_URL;
const sessionCookie = process.env.AYEC_PROFORMA_SESSION_COOKIE;
const templateBase64 = process.env.AYEC_PROFORMA_TEMPLATE_BASE64;
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-proforma-roundtrip-"));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !sessionCookie || !templateBase64) throw new Error("Authenticated proforma test inputs are required.");
  const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(tempRoot, "profile")}`, "about:blank"], { stdio: "ignore", windowsHide: true });
  let socket;
  try {
    let target;
    for (let attempt = 0; attempt < 100; attempt += 1) {
      try {
        target = (await (await fetch(`http://127.0.0.1:${debugPort}/json`)).json()).find(item => item.type === "page");
        if (target?.webSocketDebuggerUrl) break;
      } catch (_) {}
      await delay(100);
    }
    if (!target?.webSocketDebuggerUrl) throw new Error("Hidden Edge did not expose a page target.");
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
      const request = pending.get(message.id);
      if (!request) return;
      pending.delete(message.id);
      if (message.error) request.reject(new Error(message.error.message)); else request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const response = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (response.exceptionDetails) throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
      return response.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    const cookie = await send("Network.setCookie", { name: "ayec_session", value: sessionCookie, url: baseUrl, httpOnly: true, sameSite: "Lax" });
    if (!cookie.success) throw new Error("Could not install the authenticated proforma session.");
    await send("Page.navigate", { url: baseUrl });
    let authenticated = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      authenticated = await evaluate("typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id && document.querySelector('#appShell'))");
      if (authenticated) break;
      await delay(100);
    }
    if (!authenticated) throw new Error("Authenticated AYEC web app did not initialize.");
    const openEditor = await evaluate(`(() => {document.querySelector('#authRoot')?.remove();document.body.classList.remove('auth-active');const shell=document.querySelector('#appShell');shell?.removeAttribute('inert');shell?.removeAttribute('aria-hidden');page='settings';settingsSection='proforma-template';render();return true})()`);
    if (!openEditor) throw new Error("Could not open the proforma settings section.");
    let editorReady = false;
    for (let attempt = 0; attempt < 300; attempt += 1) {
      editorReady = await evaluate("Boolean(document.querySelector('[data-proforma-pdf-file]') && document.querySelector('[data-proforma-pdf-picker]') && document.querySelector('#proformaTemplateHtml') && document.querySelector('[data-setting-key=\"proforma_use_custom_editor\"]') && document.querySelector('[data-action=\"save-settings\"]'))");
      if (editorReady) break;
      await delay(50);
    }
    if (!editorReady) throw new Error("Proforma PDF upload controls did not render.");
    const editor = await evaluate(`(async () => {
      let source,toggle,saveButton;
      for(let attempt=0;attempt<100;attempt++){
        source=document.querySelector("#proformaTemplateHtml");
        toggle=document.querySelector('[data-setting-key="proforma_use_custom_editor"]');
        saveButton=document.querySelector('[data-action="save-settings"]');
        if(source&&toggle&&saveButton)break;
        await new Promise(resolve=>setTimeout(resolve,50));
      }
      if(!source||!toggle||!saveButton)throw new Error(JSON.stringify({message:"Proforma editor save controls are missing.",readyState:document.readyState,page,settingsSection,href:location.href,source:Boolean(source),toggle:Boolean(toggle),saveButton:Boolean(saveButton),title:document.querySelector("#dialogTitle")?.textContent||"",body:document.body.innerText.slice(0,240)}));
      const legacyHtml='<p>Legacy template</p><img src="file:///private/secret.png" />';
      if(!source||!toggle||!saveButton)throw new Error("Proforma editor save controls are missing.");
      const editorHtml="<p><strong>Authenticated Editor QA</strong></p><p>{{musteri_adi}}</p>";
      source.value=editorHtml;
      source.dispatchEvent(new Event("input",{bubbles:true}));
      toggle.checked=true;
      const originalFetch=window.fetch.bind(window);
      window.__proformaPreview={status:0,type:""};
      window.fetch=async(input,init)=>{
        const response=await originalFetch(input,init);
        const url=String(typeof input==="string"?input:input?.url||"");
        if(url.includes("/api/desktop/pc-builder/proforma.pdf"))window.__proformaPreview={status:response.status,type:response.headers.get("content-type")||""};
        return response;
      };
      document.querySelectorAll("#toastRoot .toast").forEach(node=>node.remove());
      saveButton.click();
      for(let attempt=0;attempt<160&&!document.querySelector("#toastRoot .toast.success")?.textContent.includes("sablon ayarlari kaydedildi");attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      const activeSettings=await apiFetch("/api/desktop/bootstrap");
      const saved=activeSettings.settings.proforma_use_custom_editor==="1"&&String(activeSettings.settings.proforma_editor_html||"").includes("Authenticated Editor QA");
      const preview={...window.__proformaPreview};
      for(let attempt=0;attempt<80&&saveButton.disabled;attempt++)await new Promise(resolve=>setTimeout(resolve,25));
      const restoreSource=document.querySelector("#proformaTemplateHtml");
      const restoreToggle=document.querySelector('[data-setting-key="proforma_use_custom_editor"]');
      const restoreButton=document.querySelector('[data-action="save-settings"]');
      if(!restoreSource||!restoreToggle||!restoreButton)throw new Error("Proforma editor restore controls are missing.");
      restoreSource.value=legacyHtml;
      restoreSource.dispatchEvent(new Event("input",{bubbles:true}));
      restoreToggle.checked=false;
      document.querySelectorAll("#toastRoot .toast").forEach(node=>node.remove());
      restoreButton.click();
      for(let attempt=0;attempt<120&&!document.querySelector("#toastRoot .toast.error")?.textContent.includes("Eski masa\u00fcst\u00fc g\u00f6rsellerini");attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      const legacyWarning=document.querySelector("#toastRoot .toast.error")?.textContent||"";
      const legacyRestoreRejected=legacyWarning.includes("Eski masa\u00fcst\u00fc g\u00f6rsellerini");
      const rejectedSettings=await apiFetch("/api/desktop/bootstrap");
      const legacyRestorePreserved=rejectedSettings.settings.proforma_use_custom_editor==="1"&&String(rejectedSettings.settings.proforma_editor_html||"").includes("Authenticated Editor QA");
      return{saved,previewStatus:preview.status,previewContentType:preview.type,legacyRestoreRejected,legacyRestorePreserved,legacyGuardVerified:legacyRestoreRejected&&legacyRestorePreserved,restoreToast:legacyWarning};
    })()`);
    if (!editor.saved || editor.previewStatus !== 200 || !editor.previewContentType.includes("application/pdf") || !editor.legacyRestoreRejected || !editor.legacyRestorePreserved) throw new Error(JSON.stringify({ editor }));
    const encodedTemplate = JSON.stringify(templateBase64);
    const upload = await evaluate(`(async () => {
      const input=document.querySelector('[data-proforma-pdf-file]');
      const bytes=Uint8Array.from(atob(${JSON.stringify(templateBase64)}),char=>char.charCodeAt(0));
      const file=new File([bytes],"UI Custom Template.pdf",{type:"application/pdf"});
      const transfer=new DataTransfer();transfer.items.add(file);input.files=transfer.files;
      input.dispatchEvent(new Event("change",{bubbles:true}));
      for(let attempt=0;attempt<120&&!document.querySelector('[data-proforma-pdf-remove]');attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      const settings=await apiFetch("/api/desktop/bootstrap");
      if(settings.settings.proforma_template_uploaded==="1"){desktopSettings.proforma_template_uploaded="1";desktopSettings.proforma_template_filename=settings.settings.proforma_template_filename||"";render()}
      return{visible:Boolean(document.querySelector('[data-proforma-pdf-remove]')),filename:settings.settings.proforma_template_filename||"",uploaded:settings.settings.proforma_template_uploaded||"0",base64:settings.settings.proforma_template_pdf_base64||""};
    })()`);
    if (!upload.visible || upload.filename !== "UI Custom Template.pdf" || upload.uploaded !== "1" || upload.base64) throw new Error(`Proforma upload did not persist through the UI: ${JSON.stringify(upload)}`);
    await evaluate("document.querySelector('[data-proforma-pdf-remove]')?.click()");
    let removedFromUi = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      removedFromUi = await evaluate("!document.querySelector('[data-proforma-pdf-remove]') && Boolean(document.querySelector('[data-proforma-pdf-picker]'))");
      if (removedFromUi) break;
      await delay(50);
    }
    const removal = await evaluate(`(async () => {const settings=await apiFetch("/api/desktop/bootstrap");if(settings.settings.proforma_template_uploaded!=="1"){desktopSettings.proforma_template_uploaded="0";desktopSettings.proforma_template_filename="";render()}return{uploaded:settings.settings.proforma_template_uploaded||"0",filename:settings.settings.proforma_template_filename||"",removedFromUi:Boolean(document.querySelector("[data-proforma-pdf-picker]")&&!document.querySelector("[data-proforma-pdf-remove]"))}})()`);
    const validation = await evaluate(`(async () => {
      const input=document.querySelector("[data-proforma-pdf-file]"),dispatch=file=>{const transfer=new DataTransfer();transfer.items.add(file);input.files=transfer.files;input.dispatchEvent(new Event("change",{bubbles:true}))};
      document.querySelectorAll("#toastRoot .toast").forEach(node=>node.remove());
      dispatch(new File([new Uint8Array(8*1024*1024+1)],"Oversized Template.pdf",{type:"application/pdf"}));
      for(let attempt=0;attempt<40&&!document.querySelector("#toastRoot .toast.error");attempt++)await new Promise(resolve=>setTimeout(resolve,25));
      const oversizeToast=document.querySelector("#toastRoot .toast.error")?.textContent||"",oversizeRejected=oversizeToast.includes("8 MB"),inputClearedAfterOversize=input.value==="";
      document.querySelector("#toastRoot .toast.error")?.remove();
      dispatch(new File(["invalid-pdf"],"Invalid Template.pdf",{type:"application/pdf"}));
      for(let attempt=0;attempt<120&&!document.querySelector("#toastRoot .toast.error");attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      const invalidPdfToast=document.querySelector("#toastRoot .toast.error")?.textContent||"",invalidPdfRejected=invalidPdfToast.includes("Ozel PDF sablonu yuklenemedi");
      document.querySelector("#toastRoot .toast.error")?.remove();
      const settings=await apiFetch("/api/desktop/bootstrap");
      return{oversizeRejected,oversizeToast,inputClearedAfterOversize,invalidPdfRejected,invalidPdfToast,unchanged:settings.settings.proforma_template_uploaded==="0",filename:settings.settings.proforma_template_filename||""};
    })()`);
    if (!removal.removedFromUi || removal.uploaded !== "0" || removal.filename || !validation.oversizeRejected || !validation.inputClearedAfterOversize || !validation.invalidPdfRejected || !validation.unchanged || validation.filename || exceptions.length) throw new Error(JSON.stringify({ upload, removal, validation, exceptions }));
    process.stdout.write(JSON.stringify({ authenticated, editorSaved: editor.saved, editorPreviewStatus: editor.previewStatus, editorPreviewContentType: editor.previewContentType, legacyGuardVerified: editor.legacyGuardVerified, legacyRestoreRejected: editor.legacyRestoreRejected, legacyRestorePreserved: editor.legacyRestorePreserved, upload: { filename: upload.filename, uploaded: upload.uploaded, base64Exposed: Boolean(upload.base64) }, removal, oversizeRejected: validation.oversizeRejected, invalidPdfRejected: validation.invalidPdfRejected, validationUnchanged: validation.unchanged, browserExceptions: exceptions.length }) + "\n");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      try { socket.send(JSON.stringify({ id: 999999, method: "Browser.close" })); } catch (_) { socket.close(); }
    }
    if (browser.pid) {
      const stopped = spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      if (stopped.error) browser.kill();
    }
    await delay(150);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}

run().catch(error => { process.stderr.write(String(error.stack || error) + "\n"); process.exitCode = 1; });
