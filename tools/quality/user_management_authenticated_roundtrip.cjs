const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_USER_CDP_PORT || 19312);
const baseUrl = process.env.AYEC_USER_BASE_URL;
const sessionCookie = process.env.AYEC_USER_SESSION_COOKIE;
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-user-roundtrip-"));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !sessionCookie) throw new Error("Authenticated test URL and session cookie are required.");
    const browser = spawn(edgePath, ["--headless=new", "--disable-gpu", "--disable-background-timer-throttling", "--disable-renderer-backgrounding", "--no-first-run", "--no-default-browser-check", `--remote-debugging-port=${debugPort}`, `--user-data-dir=${path.join(tempRoot, "profile")}`, "about:blank"], { stdio: "ignore", windowsHide: true });
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
    if (!target?.webSocketDebuggerUrl) throw new Error("Headless Edge did not expose a page target.");
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
      message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result);
    });
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++nextId;
      pending.set(id, { resolve, reject });
      socket.send(JSON.stringify({ id, method, params }));
    });
    const evaluate = async expression => {
      const result = await send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result?.value;
    };
    await send("Page.enable");
    await send("Runtime.enable");
    await send("Network.enable");
    const cookie = await send("Network.setCookie", { name: "ayec_session", value: sessionCookie, url: baseUrl, httpOnly: true, sameSite: "Lax" });
    if (!cookie.success) throw new Error("Could not install authenticated test session.");
    await send("Page.navigate", { url: baseUrl });
    let authenticated = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      authenticated = await evaluate("typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id && document.querySelector('#appShell'))");
      if (authenticated) break;
      await delay(100);
    }
    if (!authenticated) throw new Error("Authenticated web app did not initialize.");
    const result = await evaluate(`(async () => {
      document.querySelector('#authRoot')?.remove();
      document.body.classList.remove('auth-active');
      document.querySelector('#appShell')?.removeAttribute('inert');
      document.querySelector('#appShell')?.removeAttribute('aria-hidden');
      page = 'settings';
      settingsSection = 'users';
      render();
      for (let attempt = 0; attempt < 120 && !document.querySelector('[data-managed-user-create]'); attempt += 1) {
        if (page !== 'settings' || settingsSection !== 'users' || !document.querySelector('#settingsUsersHost')) {
          page = 'settings';
          settingsSection = 'users';
          render();
        }
        await new Promise(resolve => setTimeout(resolve, 50));
      }
      const createButton = document.querySelector('[data-managed-user-create]');
      if (!createButton) throw new Error('Admin create action is not rendered: '+JSON.stringify({page,settingsSection,role:currentAuthUser?.role,adminRole:userAdminRole(currentAuthUser?.role),helper:typeof window.ayecAttachUserCreateAction,host:Boolean(document.querySelector('#settingsUsersHost')),header:Boolean(document.querySelector('#settingsUsersHost')?.previousElementSibling),userCount:window.ayecSettingsUsers?.length}));
      createButton.click();
      const fill = (name, value) => { const input = document.querySelector('#dialogForm [name="'+name+'"]'); if (!input) throw new Error('Missing form field: '+name); input.value = value; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); };
      const unwrappedApiFetch = apiFetch;
      let createPostCount = 0, transientCreateFailureCalls = 0, permissionFailureCalls = 0;
      apiFetch = async (url, options = {}) => {
        if (url === '/api/desktop/users' && String(options.method || 'GET').toUpperCase() === 'POST') {
          createPostCount += 1;
          const payload = JSON.parse(options.body || '{}');
          if (payload.username === 'browser.retry' && transientCreateFailureCalls === 0) {
            transientCreateFailureCalls += 1;
            throw new Error('Temporary user service failure');
          }
          if (payload.username === 'browser.denied' && permissionFailureCalls === 0) {
            permissionFailureCalls += 1;
            throw new Error('User creation is not authorized');
          }
        }
        return unwrappedApiFetch(url, options);
      };
      fill('full_name', 'Browser Created User');
      fill('username', 'vendor-operator');
      fill('password', 'BrowserStrong123');
      fill('email', 'not-an-email');
      fill('role', 'Teknisyen');
      fill('department', 'Teknik Servis');
      fill('active', '1');
      document.querySelectorAll('#newUserPermissions [data-user-permission]').forEach(input => { input.checked = ['40', '41', '50'].includes(input.dataset.userPermission); input.dispatchEvent(new Event('change', { bubbles: true })); });
      document.querySelector('#dialogForm').requestSubmit();
      const emailInput = document.querySelector('#dialogForm [name="email"]');
      const invalidEmailBlocked = emailInput?.validity.typeMismatch === true && createPostCount === 0 && Boolean(document.querySelector('#appDialog')?.open);
      fill('email', 'browser.created@example.test');
      fill('username', 'browser.retry');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const transientCreateFailureHandled = document.querySelector('#toastRoot .toast.error')?.textContent.includes('Temporary user service failure') === true && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('username', 'vendor-operator');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const duplicateRejected = Boolean(document.querySelector('#toastRoot .toast.error')) && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('username', 'browser.weak');
      fill('password', 'weak');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const weakPasswordRejected = Boolean(document.querySelector('#toastRoot .toast.error')) && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('username', 'browser.denied');
      fill('password', 'BrowserStrong123');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const permissionFailureHandled = document.querySelector('#toastRoot .toast.error')?.textContent.includes('User creation is not authorized') === true && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('username', 'browser.server-validation');
      fill('phone', '123456789');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const serverValidationHandled = document.querySelector('#toastRoot .toast.error')?.textContent.includes('Phone number must use the desktop +90 format') === true && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('phone', '');
      fill('username', 'browser.server-conflict');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 80 && !document.querySelector('#toastRoot .toast.error'); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const serverConflictHandled = document.querySelector('#toastRoot .toast.error')?.textContent.includes('Username or email is already in use.') === true && Boolean(document.querySelector('#appDialog')?.open);
      document.querySelector('#toastRoot .toast.error')?.remove();
      fill('username', 'browser.created');
      fill('password', 'BrowserStrong123');
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 120 && document.querySelector('#appDialog')?.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const created = (ayecSettingsUsers || []).find(user => user.username === 'browser.created');
      if (!created) return { created: false, invalidEmailBlocked, transientCreateFailureHandled, duplicateRejected, weakPasswordRejected, dialogClosed: !document.querySelector('#appDialog')?.open };
      await settingsUserDialog(created);
      const editFill = (name, value) => { const input = document.querySelector('#dialogForm [name="'+name+'"]'); if (!input) throw new Error('Missing edit field: '+name); input.value = value; input.dispatchEvent(new Event('input', { bubbles: true })); input.dispatchEvent(new Event('change', { bubbles: true })); };
      editFill('full_name', 'Browser Edited User');
      editFill('role', 'Muhasebe');
      document.querySelectorAll('#managedUserPermissions [data-user-permission]').forEach(input => { input.checked = ['40', '41'].includes(input.dataset.userPermission); input.dispatchEvent(new Event('change', { bubbles: true })); });
      document.querySelector('#dialogForm').requestSubmit();
      for (let attempt = 0; attempt < 120 && document.querySelector('#appDialog')?.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const edited = (ayecSettingsUsers || []).find(user => user.username === 'browser.created');
      const editPersisted = edited?.full_name === 'Browser Edited User' && edited?.role === 'Muhasebe';
      ayecBulkPasswordsDialog();
      const bulkSelect = document.querySelector('[data-bulk-password-select]');
      const bulkDialogTitle = document.querySelector('#dialogTitle')?.textContent || '';
      bulkSelect?.click();
      const bulkPassword = document.querySelector('[data-bulk-password-field="'+CSS.escape(String(edited.id))+'"]');
      if (!bulkPassword) throw new Error('Edited user was not eligible for bulk password update.');
      document.querySelectorAll('[data-bulk-password-user]:checked').forEach(input => { if (input.dataset.bulkPasswordUser !== String(edited.id)) input.click(); });
      const bulkSelectedBeforeSubmit = [...document.querySelectorAll('[data-bulk-password-user]')].filter(input => input.checked).length;
      bulkPassword.value = 'BulkChangedPass789';
      bulkPassword.dispatchEvent(new Event('input', { bubbles: true }));
      document.querySelector('#dialogSubmit').click();
      for (let attempt = 0; attempt < 80 && (!document.querySelector('[data-bulk-password-confirm]') || document.querySelector('#dialogSubmit')?.disabled); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const bulkConfirmShown = Boolean(document.querySelector('[data-bulk-password-confirm]'));
      if (!bulkConfirmShown) return { created: Boolean(created), userId: created?.id || null, duplicateRejected, editPersisted, bulkDialogTitle, bulkSelectedBeforeSubmit, bulkSubmitDisabled: document.querySelector('#dialogSubmit')?.disabled, bulkToastText: document.querySelector('#toastRoot')?.textContent || '', bulkBodyText: document.querySelector('#dialogBody')?.textContent || '' };
      const bulkConfirm = document.querySelector('[data-bulk-password-confirm]');
      if (bulkConfirm) bulkConfirm.click();
      document.querySelector('#dialogSubmit').click();
      for (let attempt = 0; attempt < 120 && document.querySelector('#appDialog')?.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const bulkDialogClosed = !document.querySelector('#appDialog')?.open;
      if (!bulkDialogClosed) return { created: Boolean(created), userId: created?.id || null, duplicateRejected, editPersisted, bulkSelectedBeforeSubmit, bulkConfirmShown, bulkDialogClosed, bulkToastText: document.querySelector('#toastRoot')?.textContent || '', bulkBodyText: document.querySelector('#dialogBody')?.textContent || '' };
      ayecDeleteManagedUser(edited.id);
      document.querySelector('#dialogSubmit').click();
      for (let attempt = 0; attempt < 120 && document.querySelector('#appDialog')?.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const deletedRow = [...document.querySelectorAll('#settingsUsersHost tbody tr')].find(row => row.textContent.includes('browser.created'));
      const deletedInactive = Boolean(deletedRow && deletedRow.textContent.includes('Pasif'));
      return { authRole: currentAuthUser?.role || '', isControlAdmin: currentAuthUser?.is_control_admin === true, created: Boolean(created), userId: created?.id || null, invalidEmailBlocked, transientCreateFailureHandled, duplicateRejected, weakPasswordRejected, permissionFailureHandled, serverValidationHandled, serverConflictHandled, dialogClosed: !document.querySelector('#appDialog')?.open, editPersisted, bulkSelectedBeforeSubmit, bulkConfirmShown, bulkDialogClosed, deletedInactive };
    })()`);
    if (result.authRole !== "Admin" || result.isControlAdmin || !result.created || !result.userId || !result.invalidEmailBlocked || !result.transientCreateFailureHandled || !result.duplicateRejected || !result.weakPasswordRejected || !result.permissionFailureHandled || !result.serverValidationHandled || !result.serverConflictHandled || !result.dialogClosed || !result.editPersisted || result.bulkSelectedBeforeSubmit !== 1 || !result.bulkConfirmShown || !result.bulkDialogClosed || !result.deletedInactive || exceptions.length) throw new Error(JSON.stringify({ result, exceptions }));
    process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length }) + "\n");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      try { await new Promise(resolve => { socket.addEventListener("close", resolve, { once: true }); socket.send(JSON.stringify({ id: 999999, method: "Browser.close" })); setTimeout(resolve, 200); }); } catch (_) { socket.close(); }
    }
    browser.kill();
    await delay(200);
    fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 });
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
