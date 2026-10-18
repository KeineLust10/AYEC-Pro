const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { spawn, spawnSync } = require("node:child_process");

const edgePath = process.env.EDGE_EXECUTABLE || "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const debugPort = Number(process.env.AYEC_CUSTOMER_CDP_PORT || 19500);
const baseUrl = process.env.AYEC_CUSTOMER_BASE_URL;
const sessionCookie = process.env.AYEC_CUSTOMER_SESSION_COOKIE;
const searchTerm = process.env.AYEC_CUSTOMER_SEARCH_TERM || "";
const expectedFilterCounts = JSON.parse(process.env.AYEC_CUSTOMER_FILTER_EXPECTATIONS || "{}");
const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "ayec-customer-directory-"));
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function run() {
  if (!baseUrl || !sessionCookie || !searchTerm) throw new Error("Authenticated customer directory inputs are required.");
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
    await send("Emulation.setDeviceMetricsOverride", { width: 1300, height: 850, deviceScaleFactor: 1, mobile: false });
    const cookie = await send("Network.setCookie", { name: "ayec_session", value: sessionCookie, url: baseUrl, httpOnly: true, sameSite: "Lax" });
    if (!cookie.success) throw new Error("Could not install the authenticated customer session.");
    await send("Page.navigate", { url: baseUrl });
    let authenticated = false;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      authenticated = await evaluate("typeof currentAuthUser !== 'undefined' && Boolean(currentAuthUser?.id && document.querySelector('#appShell'))");
      if (authenticated) break;
      await delay(100);
    }
    if (!authenticated) throw new Error("Authenticated AYEC web app did not initialize.");
    const result = await evaluate(`(async () => {
      document.querySelector("#authRoot")?.remove();
      document.body.classList.remove("auth-active");
      document.querySelector("#appShell")?.removeAttribute("inert");
      document.querySelector("#appShell")?.removeAttribute("aria-hidden");
      for(let attempt=0;attempt<400&&db.customers.length!==28;attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      navigate("customers");
      for(let attempt=0;attempt<160&&(!document.querySelector("#customerPageIndicator")||!document.querySelector("#customerSearch"));attempt++)await new Promise(resolve=>setTimeout(resolve,50));
      const table=document.querySelector(".customer-data-table"),tableWrap=table?.closest(".table-wrap");
      const initial={role:currentAuthUser?.role||"",isControlAdmin:currentAuthUser?.is_control_admin===true,total:db.customers.length,visibleRows:document.querySelectorAll(".customer-data-table tbody tr").length,page:document.querySelector("#customerPageIndicator")?.textContent||"",metrics:[...document.querySelectorAll(".customer-metrics .metric")].slice(0,4).map(node=>node.querySelector("strong")?.textContent.trim()||""),metricSecondary:[...document.querySelectorAll(".customer-metrics .metric")].slice(0,2).map(node=>node.querySelector(".customer-metric-secondary")?.textContent.trim()||""),firstNames:[...document.querySelectorAll(".customer-data-table tbody tr")].slice(0,5).map(row=>row.querySelector(".customer-name strong>span")?.textContent.trim()||""),tableGeometry:{containerWidth:tableWrap?.clientWidth||0,tableWidth:table?.getBoundingClientRect().width||0,tableScrollWidth:table?.scrollWidth||0,columns:[...(table?.querySelectorAll("thead th")||[])].map(node=>Math.round(node.getBoundingClientRect().width))}};
      const horizontalReachability=(()=>{const old=tableWrap.scrollLeft,scrollMax=tableWrap.scrollWidth-tableWrap.clientWidth,wrapBounds=tableWrap.getBoundingClientRect();tableWrap.scrollLeft=scrollMax;const actionCell=table.querySelector("tbody tr:first-child td:last-child")?.getBoundingClientRect();const result={scrollMax,lastActionVisible:Boolean(actionCell&&actionCell.left>=wrapBounds.left-1&&actionCell.right<=wrapBounds.right+1),documentWidth:document.documentElement.scrollWidth,viewportWidth:document.documentElement.clientWidth};tableWrap.scrollLeft=old;return result})();
      const search=document.querySelector("#customerSearch");
      if(!search)throw new Error("Customer search field did not render.");
      search.value=${JSON.stringify(searchTerm)};
      search.dispatchEvent(new Event("input",{bubbles:true}));
      const searchMatches=Number(document.querySelector("#customerFilteredCount")?.textContent||0);
      const searchedName=document.querySelector(".customer-data-table tbody tr")?.textContent||"";
      document.querySelector("#customerSearchClear")?.click();
      const restored={page:document.querySelector("#customerPageIndicator")?.textContent||"",total:Number(document.querySelector("#customerCount")?.textContent||0)};
      const filterAudit={};
      const typeFilter=document.querySelector("#customerTypeFilter");
      typeFilter.value="vip";typeFilter.dispatchEvent(new Event("change",{bubbles:true}));
      filterAudit.vip=Number(document.querySelector("#customerCount")?.textContent||0);
      typeFilter.value="";typeFilter.dispatchEvent(new Event("change",{bubbles:true}));
      const locationFilter=document.querySelector("#customerLocationFilter");
      locationFilter.value="Ankara";locationFilter.dispatchEvent(new Event("change",{bubbles:true}));
      filterAudit.locationAnkara=Number(document.querySelector("#customerCount")?.textContent||0);
      locationFilter.value="";locationFilter.dispatchEvent(new Event("change",{bubbles:true}));
      typeFilter.value="";typeFilter.dispatchEvent(new Event("change",{bubbles:true}));
      const balanceFilter=document.querySelector("#customerBalanceFilter");
      balanceFilter.value="debt";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
      filterAudit.debt=Number(document.querySelector("#customerCount")?.textContent||0);
      balanceFilter.value="";balanceFilter.dispatchEvent(new Event("change",{bubbles:true}));
      const nextPageButton=document.querySelector("#customerPageNext");
      const nextPageEnabled=Boolean(nextPageButton&&!nextPageButton.disabled);
      nextPageButton?.click();
      for(let attempt=0;attempt<40&&document.querySelector("#customerPageIndicator")?.textContent!=="2 / 3";attempt++)await new Promise(resolve=>setTimeout(resolve,25));
      const secondPage=document.querySelector("#customerPageIndicator")?.textContent||"";
      document.querySelector("#customerPagePrev")?.click();
      return{initial,horizontalReachability,secondPage,nextPageEnabled,searchMatches,searchedName,restored,filterAudit};
    })()`);
    if (process.env.AYEC_CUSTOMER_SCREENSHOT_PATH) {
      await delay(80);
      const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      fs.writeFileSync(process.env.AYEC_CUSTOMER_SCREENSHOT_PATH, Buffer.from(screenshot.data, "base64"));
    }
    result.customer360 = await evaluate(`(() => {
      const open = document.querySelector('[data-action="customer-open-360"]');
      const row = open?.closest("tr");
      const customer = db.customers.find(item => String(item.id) === String(open?.dataset.id));
      if (!open || !customer) throw new Error("Customer 360 entry point is unavailable.");
      open.click();
      const dialog = document.querySelector("#appDialog");
      if (!dialog?.open) throw new Error("Customer 360 dialog did not open.");
      const tabs = [...dialog.querySelectorAll("[data-c360-tab]")].map(tab => tab.dataset.c360Tab);
      const panelStates = [];
      for (const name of tabs) {
        dialog.querySelector('[data-c360-tab="' + name + '"]')?.click();
        panelStates.push({ name, active: dialog.querySelector('[data-c360-panel="' + name + '"]')?.classList.contains("active") === true });
      }
      const serviceRows = dialog.querySelectorAll('[data-c360-panel="service"] tbody tr').length;
      const ledgerRows = dialog.querySelectorAll('[data-c360-panel="ledger"] tbody tr').length;
      const title = document.querySelector("#dialogTitle")?.textContent.trim() || "";
      dialog.close("cancel");
      return { name: customer.name, title, serviceRows, expectedServices: (customer.services || []).length, ledgerRows, tabs, panelStates, closed: !dialog.open, rowName: row?.querySelector(".customer-name strong>span")?.textContent.trim() || "" };
    })()`);
    result.customerNote = await evaluate(`(async () => {
      const customer = db.customers.find(item => item.name === ${JSON.stringify(result.customer360.name)});
      if (!customer) throw new Error("Customer note target is unavailable.");
      customer360(customer);
      document.querySelector("#c360Notes")?.click();
      await new Promise(resolve => setTimeout(resolve, 60));
      const title = document.querySelector("#customerNoteTitle");
      const editor = document.querySelector("#customerNoteEditor");
      const dialog = document.querySelector("#appDialog");
      if (!dialog?.open || !title || !editor) throw new Error("Customer notes editor did not open.");
      const expectedTitle = "Authenticated browser note QA";
      const expectedContent = "Saved from the authenticated customer 360 workflow.";
      title.value = expectedTitle;
      editor.textContent = expectedContent;
      editor.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText", data: expectedContent }));
      document.querySelector("#dialogForm")?.requestSubmit();
      let record = null;
      for (let attempt = 0; attempt < 30 && !record; attempt += 1) {
        await new Promise(resolve => setTimeout(resolve, 100));
        const response = await fetch("/api/desktop/table/customer_notes?limit=1000", { credentials: "same-origin" });
        const payload = await response.json();
        record = (payload.rows || []).find(item => item.title === expectedTitle) || null;
      }
      dialog.close("cancel");
      return { title: record?.title || "", content: record?.content || "", id: record?.id || null, customerId: record?.customer_id || null, expectedCustomerId: customer.id, closed: !dialog.open };
    })()`);
    result.customerEdit = await evaluate(`(async () => {
      const customer = db.customers.find(item => item.name === ${JSON.stringify(result.initial.firstNames[0])});
      if (!customer) throw new Error("Customer edit target is unavailable.");
      const originalPhone2 = String(customer.phone2 || "");
      const editedPhone2 = originalPhone2 === "55500009999" ? "55500008888" : "55500009999";
      const openEditor = () => {
        const row = [...document.querySelectorAll('tr[data-kind="customer"]')].find(item => String(item.dataset.id) === String(customer.id));
        const actions = row?.querySelector('[data-action="customer-actions"]');
        if (!actions) throw new Error("Customer row actions are unavailable.");
        actions.click();
        const edit = document.querySelector('#dialogBody [data-modal-action="edit"]');
        if (!edit) throw new Error("Customer edit action is unavailable.");
        edit.click();
        const field = document.querySelector('#dialogBody [name="phone2"]');
        if (!field) throw new Error("Customer secondary phone field is unavailable.");
        return field;
      };
      const saveEditor = async fieldValue => {
        const dialog = document.querySelector("#appDialog");
        const field = openEditor();
        field.value = fieldValue;
        document.querySelector("#dialogForm")?.requestSubmit();
        for (let attempt = 0; attempt < 40 && dialog.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
        if (dialog.open) throw new Error("Customer edit save did not close the dialog.");
      };
      const readCustomer = async () => {
        const response = await fetch("/api/desktop/table/customers?limit=1000", { credentials: "same-origin" });
        const payload = await response.json();
        return (payload.rows || []).find(item => String(item.id) === String(customer.id)) || null;
      };
      await saveEditor(editedPhone2);
      let edited = null;
      for (let attempt = 0; attempt < 20 && !edited; attempt += 1) {
        edited = await readCustomer();
        if (edited?.phone2 !== editedPhone2) { edited = null; await new Promise(resolve => setTimeout(resolve, 50)); }
      }
      if (edited?.phone2 !== editedPhone2) throw new Error("Edited customer phone did not persist.");
      await saveEditor(originalPhone2);
      let restored = null;
      for (let attempt = 0; attempt < 20 && !restored; attempt += 1) {
        restored = await readCustomer();
        if (String(restored?.phone2 || "") !== originalPhone2) { restored = null; await new Promise(resolve => setTimeout(resolve, 50)); }
      }
      if (String(restored?.phone2 || "") !== originalPhone2) throw new Error("Customer phone was not restored after the roundtrip.");
      return { customerId: customer.id, originalPhone2, editedPhone2, observedEditedPhone2: edited.phone2, restoredPhone2: String(restored.phone2 || ""), restored: true };
    })()`);
    result.sortAudit = await evaluate(`(() => {
      const nameHeader = () => document.querySelector('.customer-data-table th[data-customer-sort="2"]');
      const names = () => [...document.querySelectorAll(".customer-data-table tbody tr .customer-name strong>span")].map(node => node.textContent.trim());
      const ids = () => [...document.querySelectorAll(".customer-data-table tbody tr .customer-id")].map(node => Number(node.textContent.replace(/\\D/g, "")));
      if (!nameHeader()) throw new Error("Customer name sort header is unavailable.");
      nameHeader().click();
      const descendingNames = names();
      nameHeader().click();
      const ascendingNames = names();
      const clickSort = column => document.querySelector('.customer-data-table th[data-customer-sort="' + column + '"]')?.click();
      clickSort(1);
      const ascendingIds = ids();
      const ordered = values => values.every((value, index) => index === 0 || values[index - 1].localeCompare(value, "tr-TR", { sensitivity: "base" }) <= 0);
      const numericOrdered = values => values.every((value, index) => index === 0 || values[index - 1] <= value);
      const sortedIdsMatch = (column, key, numeric = false) => {
        clickSort(column);
        const expected = [...db.customers].sort((left, right) => {
          const a = key(left), b = key(right);
          return numeric ? Number(a) - Number(b) : String(a).localeCompare(String(b), "tr-TR", { sensitivity: "base" });
        }).slice(0, 10).map(customer => Number(customer.id));
        return JSON.stringify(ids()) === JSON.stringify(expected);
      };
      const segmentMatches = sortedIdsMatch(3, customer => customer.type || "Bireysel");
      const phoneMatches = sortedIdsMatch(4, customer => {
        const phone = String(customer.phone || "\u2014"), digits = phone.replace(/\\D/g, "");
        return digits.length === 11 && digits.startsWith("0") ? digits.slice(0, 4) + " " + digits.slice(4, 7) + " " + digits.slice(7, 9) + " " + digits.slice(9) : phone;
      });
      const serviceMatches = sortedIdsMatch(5, customer => String(customer.service_counts?.open ?? customerServiceCounts(customer).open));
      const balanceMatches = sortedIdsMatch(6, customer => ["TRY", "USD", "EUR"].reduce((sum, currency) => sum + (Number(customer.balances?.[currency]) || 0), 0), true);
      const statusMatches = sortedIdsMatch(7, customer => customerReferenceStatus(customer));
      nameHeader().focus();
      nameHeader().dispatchEvent(new KeyboardEvent("keydown", { key: "Enter", bubbles: true }));
      const keyboardSort = nameHeader().getAttribute("aria-sort") === "ascending" && JSON.stringify(ids()) === JSON.stringify([...db.customers].sort((left, right) => String(left.name || "").localeCompare(String(right.name || ""), "tr-TR", { sensitivity: "base" })).slice(0, 10).map(customer => Number(customer.id)));
      return { descendingNames, ascendingNames, ascendingIds, namesDescending: ordered([...descendingNames].reverse()), namesAscending: ordered(ascendingNames), idsAscending: numericOrdered(ascendingIds), segmentMatches, phoneMatches, serviceMatches, balanceMatches, statusMatches, keyboardSort };
    })()`);
    if (Object.values(result.sortAudit).some(value => typeof value === "boolean" && !value)) throw new Error("Customer table sorting did not match the desktop header behavior.");
    result.selectionAudit = await evaluate(`(async () => {
      const selected = () => window.ayecSelectedCustomerIds?.size || 0;
      const header = () => document.querySelector("#customerSelectAll");
      header()?.click();
      const allRowsSelected = selected() === db.customers.length && document.querySelectorAll(".customer-row-select:checked").length === 10 && header()?.checked === true;
      document.querySelector("#customerPageNext")?.click();
      const secondPage = document.querySelector("#customerPageIndicator")?.textContent || "";
      const secondPageSelected = document.querySelectorAll(".customer-row-select:checked").length;
      header()?.click();
      const allRowsCleared = selected() === 0 && document.querySelectorAll(".customer-row-select:checked").length === 0;
      document.querySelector(".customer-row-select")?.click();
      const oneSelected = selected() === 1;
      document.querySelector("#customerPagePrev")?.click();
      const retainedOffPage = selected() === 1 && document.querySelectorAll(".customer-row-select:checked").length === 0;
      document.querySelector("#customerPageNext")?.click();
      const restoredOnPage = document.querySelectorAll(".customer-row-select:checked").length === 1;
      return { allRowsSelected, secondPage, secondPageSelected, allRowsCleared, oneSelected, retainedOffPage, restoredOnPage };
    })()`);
    if (Object.values(result.selectionAudit).some(value => typeof value === "boolean" && !value) || result.selectionAudit.secondPage !== "2 / 3" || result.selectionAudit.secondPageSelected !== 10) throw new Error("Customer multi-selection did not persist across the full dataset and pagination.");
    result.selectionExportAudit = await evaluate(`(async () => {
      const selectedIds = [...(window.ayecSelectedCustomerIds || [])];
      let exportedRows = null;
      const originalFetch = window.fetch;
      const originalAnchorClick = HTMLAnchorElement.prototype.click;
      const originalCreateObjectURL = URL.createObjectURL;
      window.fetch = async (input, options) => {
        if (String(input).includes("/api/desktop/customers/export/xlsx")) {
          exportedRows = JSON.parse(options.body).rows;
          return { ok: true, blob: async () => new Blob(["audit"]) };
        }
        return originalFetch.call(window, input, options);
      };
      URL.createObjectURL = () => "blob:customer-export-audit";
      HTMLAnchorElement.prototype.click = function () { if (this.download !== "musteriler-secili.xlsx") originalAnchorClick.call(this); };
      try {
        document.querySelector("#customerMultiSelect")?.click();
        const row = document.querySelector('.customer-data-table tbody tr[data-kind="customer"]');
        row?.dispatchEvent(new MouseEvent("contextmenu", { bubbles: true, cancelable: true, clientX: 800, clientY: 500 }));
        const action = document.querySelector('#contextMenu [data-customer-context-action="selected-excel"]');
        if (!action) throw new Error("Selected-customer export is unavailable in multi-select mode.");
        action.click();
        for (let attempt = 0; attempt < 30 && !exportedRows; attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
      } finally {
        window.fetch = originalFetch;
        URL.createObjectURL = originalCreateObjectURL;
        HTMLAnchorElement.prototype.click = originalAnchorClick;
      }
      const exportedIds = (exportedRows || []).map(values => String(values[0]));
      return { selectedIds, exportedIds, rowCount: exportedRows?.length || 0, matchesSelection: JSON.stringify(exportedIds) === JSON.stringify(selectedIds) };
    })()`);
    if (!result.selectionExportAudit.matchesSelection || result.selectionExportAudit.rowCount !== 1) throw new Error("Selected-customer export omitted an off-page selection.");
    result.jobReport = await evaluate(`(async () => {
      navigate("job-reports");
      for (let attempt = 0; attempt < 80 && (page !== "job-reports" || !document.querySelector("#jobReportHost")); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      for (let attempt = 0; attempt < 80 && !ayecJobLedgerRows.some(row => row.tracking_no === "QA-JOB-ROUNDTRIP"); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const target = ayecJobLedgerRows.find(row => row.tracking_no === "QA-JOB-ROUNDTRIP");
      if (!target) throw new Error("Authenticated job ledger fixture did not load.");
      let jobRow = null;
      for (let attempt = 0; attempt < 40 && !jobRow; attempt += 1) {
        jobRow = [...document.querySelectorAll(".job-report-table tbody tr[data-job-report-kind=job]")].find(row => row.dataset.jobReportId === target.id) || null;
        if (!jobRow) await new Promise(resolve => setTimeout(resolve, 50));
      }
      if (!jobRow) throw new Error("Authenticated job ledger row is not visible.");
      const metricCards = [...document.querySelectorAll(".job-report-metric")];
      const metricLabels = metricCards.map(card => card.querySelector(".job-report-metric-heading small")?.textContent.trim() || "");
      const metricValues = ["jobReportTotal", "jobReportOpen", "jobReportPaid", "jobReportServiceCount", "jobReportRevenue"].map(id => document.getElementById(id)?.textContent.trim() || "");
      const metricProgress = metricCards.map(card => Number(card.querySelector('[role="progressbar"]')?.getAttribute("aria-valuenow")));
      const totalMetricJobs = Number(metricValues[0]), openMetricJobs = Number(metricValues[1]), paidMetricJobs = Number(metricValues[2]), serviceMetricCount = Number(metricValues[3]);
      const expectedMetricProgress = [totalMetricJobs ? 100 : 0, totalMetricJobs ? Math.round(openMetricJobs * 100 / totalMetricJobs) : 0, totalMetricJobs ? Math.round(paidMetricJobs * 100 / totalMetricJobs) : 0, serviceMetricCount ? 100 : 0, 0];
      if (metricCards.length !== 5 || metricProgress.some((value, index) => value !== expectedMetricProgress[index])) throw new Error("Job report KPI values or progress do not match the desktop metric rules.");
      const metricAudit = { labels: metricLabels, values: metricValues, progress: metricProgress };
      const jobCells = [...jobRow.cells].map(cell => cell.innerText.trim());
      jobRow.querySelector("[data-job-report-view]")?.click();
      const dialog = document.querySelector("#appDialog");
      for (let attempt = 0; attempt < 30 && !dialog.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
      const historyRows = document.querySelectorAll("#dialogBody .field.full tbody tr").length;
      if (historyRows !== 2) throw new Error("Authenticated job detail did not show both ledger transactions.");
      dialog.close("cancel");
      document.querySelector('[data-job-report-tab="service"]')?.click();
      for (let attempt = 0; attempt < 40 && ![...document.querySelectorAll(".job-report-table tbody tr")].some(row => row.innerText.includes("QA-SERVICE-ROUNDTRIP")); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const serviceRow = [...document.querySelectorAll(".job-report-table tbody tr")].find(row => row.innerText.includes("QA-SERVICE-ROUNDTRIP"));
      if (!serviceRow) throw new Error("Authenticated service register row is not visible.");
      const detailValues = [...(document.querySelector("#dialogBody")?.querySelectorAll("input") || [])].map(input => input.value);
      document.querySelector("[data-job-report-monthly]")?.click();
      const monthlyDialog = document.querySelector("#appDialog");
      for (let attempt = 0; attempt < 30 && !monthlyDialog.open; attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
      const monthlyRows = document.querySelectorAll("#dialogBody .job-monthly-report-table tbody tr").length;
      monthlyDialog.close("cancel");
      document.querySelector('[data-job-report-tab="profit"]')?.click();
      for (let attempt = 0; attempt < 60 && !document.querySelector("#jobReportHost .job-report-table tbody tr"); attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      const profitabilityRows = document.querySelectorAll("#jobReportHost .job-report-table tbody tr").length;
      const profitabilityStatus = document.querySelector("#jobProfitabilityStatus")?.textContent.trim() || "";
      document.querySelector('[data-job-report-tab="jobs"]')?.click();
      for (let attempt = 0; attempt < 40 && !document.querySelector("[data-job-report-export]"); attempt += 1) await new Promise(resolve => setTimeout(resolve, 25));
      const originalCreateObjectUrl = URL.createObjectURL;
      const originalAnchorClick = HTMLAnchorElement.prototype.click;
      let exportedBlob = null;
      let exportFilename = "";
      URL.createObjectURL = blob => { exportedBlob = blob; return "blob:authenticated-job-report"; };
      HTMLAnchorElement.prototype.click = function() { exportFilename = this.download; };
      document.querySelector("[data-job-report-export]")?.click();
      for (let attempt = 0; attempt < 60 && !exportedBlob; attempt += 1) await new Promise(resolve => setTimeout(resolve, 50));
      URL.createObjectURL = originalCreateObjectUrl;
      HTMLAnchorElement.prototype.click = originalAnchorClick;
      if (!exportedBlob) throw new Error("Authenticated job report export did not create a workbook.");
      const workbookBytes = new Uint8Array(await exportedBlob.arrayBuffer());
      let workbookBinary = "";
      for (let offset = 0; offset < workbookBytes.length; offset += 8192) workbookBinary += String.fromCharCode(...workbookBytes.subarray(offset, Math.min(offset + 8192, workbookBytes.length)));
      const workbookBase64 = btoa(workbookBinary);
      return { page, jobCount: ayecJobLedgerRows.length, serviceCount: ayecJobServiceRows.length, metrics: metricAudit, targetJob: { customer: target.customer_name, tracking: target.tracking_no, debit: target.debit, credit: target.credit, remaining: target.remaining_amount, payment: target.payment_status }, jobCells, detailShowsTracking: detailValues.includes("QA-JOB-ROUNDTRIP"), detailShowsCustomer: detailValues.includes(target.customer_name), historyRows, serviceTracking: serviceRow.cells[0]?.innerText.trim() || "", serviceVisible: true, monthlyRows, profitabilityRows, profitabilityStatus, exportFilename, exportMime: exportedBlob.type, exportBytes: workbookBytes.length, workbookBase64 };
    })()`);
    if (process.env.AYEC_JOB_REPORT_SCREENSHOT_PATH) {
      const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
      fs.writeFileSync(process.env.AYEC_JOB_REPORT_SCREENSHOT_PATH, Buffer.from(screenshot.data, "base64"));
    }
    const valid = result.initial.role === "Admin"
      && !result.initial.isControlAdmin
      && result.initial.total === 28
      && result.initial.visibleRows === 10
      && result.initial.page === "1 / 3"
      && result.initial.tableGeometry.tableWidth === 1244
      && result.initial.tableGeometry.tableScrollWidth === 1244
      && JSON.stringify(result.initial.tableGeometry.columns) === JSON.stringify([36,106,215,143,149,191,146,111,147])
      && result.horizontalReachability?.scrollMax > 0
      && result.horizontalReachability?.lastActionVisible === true
      && result.horizontalReachability?.documentWidth === result.horizontalReachability?.viewportWidth
      && result.customer360.title === result.customer360.name
      && result.customer360.rowName === result.customer360.name
      && result.customer360.serviceRows === result.customer360.expectedServices
      && result.customer360.ledgerRows === 3
      && result.customer360.tabs.includes("cari")
      && result.customer360.tabs.includes("ledger")
      && result.customer360.tabs.includes("sales")
      && result.customer360.tabs.includes("offers")
      && result.customer360.panelStates.every(panel => panel.active)
      && result.customer360.closed
      && result.customerNote.title === "Authenticated browser note QA"
      && result.customerNote.content.includes("Saved from the authenticated customer 360 workflow.")
      && Number(result.customerNote.customerId) === Number(result.customerNote.expectedCustomerId)
      && Number(result.customerNote.id) > 0
      && result.customerNote.closed
      && result.customerEdit.observedEditedPhone2 === result.customerEdit.editedPhone2
      && result.customerEdit.restoredPhone2 === result.customerEdit.originalPhone2
      && result.customerEdit.restored
      && result.jobReport.page === "job-reports"
      && result.jobReport.targetJob.tracking === "QA-JOB-ROUNDTRIP"
      && result.jobReport.targetJob.debit === 2500
      && result.jobReport.targetJob.credit === 1000
      && result.jobReport.targetJob.remaining === 1500
      && result.jobReport.historyRows === 2
      && result.jobReport.detailShowsTracking
      && result.jobReport.detailShowsCustomer
      && result.jobReport.serviceVisible
      && result.jobReport.serviceTracking.includes("QA-SERVICE-ROUNDTRIP")
      && result.jobReport.monthlyRows === 12
      && result.jobReport.profitabilityRows === 1
      && result.jobReport.exportFilename.startsWith("is-servis-raporu-")
      && result.jobReport.exportMime.includes("spreadsheetml.sheet")
      && result.jobReport.exportBytes > 0
      && result.secondPage === "2 / 3"
      && result.searchMatches === 1
      && result.filterAudit.vip === expectedFilterCounts.vip
      && result.filterAudit.locationAnkara === expectedFilterCounts.locationAnkara
      && result.filterAudit.debt === expectedFilterCounts.debt
      && result.searchedName.includes(searchTerm)
      && result.restored.page === "1 / 3"
      && result.restored.total === 28
      && exceptions.length === 0;
    if (!valid) throw new Error(JSON.stringify({ result, exceptions }));
    process.stdout.write(JSON.stringify({ ...result, browserExceptions: exceptions.length }) + "\n");
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      try { await new Promise(resolve => { socket.addEventListener("close", resolve, { once: true }); socket.send(JSON.stringify({ id: 999999, method: "Browser.close" })); setTimeout(resolve, 200); }); } catch (_) { socket.close(); }
    }
    if (browser.pid) {
      const stopped = spawnSync("taskkill.exe", ["/PID", String(browser.pid), "/T", "/F"], { stdio: "ignore", windowsHide: true });
      if (stopped.error) browser.kill();
    }
    await delay(200);
    if (path.dirname(tempRoot) === path.resolve(os.tmpdir()) && path.basename(tempRoot).startsWith("ayec-customer-directory-")) {
      try { fs.rmSync(tempRoot, { recursive: true, force: true, maxRetries: 10, retryDelay: 200 }); } catch (_) {}
    }
  }
}

run().catch(error => { process.stderr.write(error.stack + "\n"); process.exitCode = 1; });
