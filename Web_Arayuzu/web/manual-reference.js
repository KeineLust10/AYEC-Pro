(function () {
  let selectedManual = "usage";
  let requestId = 0;
  const names = { usage: "Kullan\u0131m K\u0131lavuzu", setup: "Kurulum Rehberi" };

  function escapeHtml(value) {
    return String(value).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/\"/g, "&quot;").replace(/'/g, "&#39;");
  }

  function inlineMarkdown(value) {
    let html = escapeHtml(value);
    html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
    html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    html = html.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+|mailto:[^\s)]+|#[A-Za-z0-9_-]+)\)/gi, (match, label, href) => href.startsWith("#") ? `<a href="${href}">${label}</a>` : `<a href="${href}" target="_blank" rel="noopener">${label}</a>`);
    return html;
  }

  function tableCells(line) {
    return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map(cell => cell.trim());
  }

  function isTableSeparator(line) {
    const cells = tableCells(line);
    return cells.length > 1 && cells.every(cell => /^:?-{3,}:?$/.test(cell));
  }

  function renderMarkdown(source) {
    const lines = String(source || "").replace(/\r/g, "").split("\n");
    const output = [];
    let paragraph = [], list = "", code = false, codeLines = [];
    const flushParagraph = () => {
      if (paragraph.length) output.push(`<p>${inlineMarkdown(paragraph.join(" "))}</p>`);
      paragraph = [];
    };
    const closeList = () => {
      if (list) output.push(`</${list}>`);
      list = "";
    };
    for (let index = 0; index < lines.length; index++) {
      const line = lines[index];
      if (line.trim().startsWith("```")) {
        flushParagraph();
        closeList();
        if (code) {
          output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
          codeLines = [];
          code = false;
        } else code = true;
        continue;
      }
      if (code) { codeLines.push(line); continue; }
      if (line.includes("|") && index + 1 < lines.length && isTableSeparator(lines[index + 1])) {
        flushParagraph(); closeList();
        const headers = tableCells(line);
        const alignments = tableCells(lines[index + 1]).map(cell => cell.startsWith(":") ? (cell.endsWith(":") ? "center" : "left") : (cell.endsWith(":") ? "right" : ""));
        const cellHtml = (cells, tag) => `<tr>${headers.map((_, cellIndex) => {
          const alignment = alignments[cellIndex] ? ` style="text-align:${alignments[cellIndex]}"` : "";
          return `<${tag}${alignment}>${inlineMarkdown(cells[cellIndex] || "")}</${tag}>`;
        }).join("")}</tr>`;
        output.push(`<div class="manual-table-wrap"><table><thead>${cellHtml(headers, "th")}</thead><tbody>`);
        index += 2;
        while (index < lines.length && lines[index].includes("|")) {
          output.push(cellHtml(tableCells(lines[index]), "td"));
          index++;
        }
        output.push("</tbody></table></div>");
        index--;
        continue;
      }
      if (!line.trim()) { flushParagraph(); closeList(); continue; }
      const heading = line.match(/^(#{1,6})\s+(.+)$/);
      if (heading) {
        flushParagraph(); closeList();
        const level = heading[1].length;
        const slug = heading[2].toLocaleLowerCase("tr-TR").replace(/[^\p{L}\p{N}\s-]/gu, "").trim().replace(/\s+/g, "-");
        output.push(`<h${level} id="${escapeHtml(slug)}">${inlineMarkdown(heading[2])}</h${level}>`);
        continue;
      }
      if (/^\s*[-*_]{3,}\s*$/.test(line)) { flushParagraph(); closeList(); output.push("<hr>"); continue; }
      const quote = line.match(/^\s*&gt;\s?(.*)$/) || line.match(/^\s*>\s?(.*)$/);
      if (quote) { flushParagraph(); closeList(); output.push(`<blockquote>${inlineMarkdown(quote[1])}</blockquote>`); continue; }
      const item = line.match(/^\s*(?:[-*+]\s+|\d+[.)]\s+)(.*)$/);
      if (item) {
        flushParagraph();
        const wanted = /^\s*\d/.test(line) ? "ol" : "ul";
        if (list && list !== wanted) closeList();
        if (!list) { list = wanted; output.push(`<${list}>`); }
        output.push(`<li>${inlineMarkdown(item[1])}</li>`);
        continue;
      }
      closeList();
      paragraph.push(line.trim());
    }
    flushParagraph();
    closeList();
    if (code) output.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    return output.join("");
  }

  function manualShell() {
    return `<section class="manual-reference"><header class="manual-reference-head"><div><h2><span class="manual-heading-icon" aria-hidden="true">&#128218;</span> Yard\u0131m ve K\u0131lavuzlar</h2></div><button type="button" class="secondary" data-manual-refresh>Yenile</button></header><nav class="manual-tabs" role="tablist" aria-label="K\u0131lavuzlar">${Object.entries(names).map(([key, label]) => `<button type="button" role="tab" aria-selected="${selectedManual === key}" data-manual-tab="${key}">${label}</button>`).join("")}</nav><article class="manual-document" id="manualDocument" aria-live="polite"><p class="manual-loading">K\u0131lavuz y\u00fckleniyor...</p></article></section>`;
  }

  async function loadManual() {
    const id = ++requestId;
    const documentNode = $("#manualDocument");
    if (!documentNode) return;
    documentNode.innerHTML = '<p class="manual-loading">K\u0131lavuz y\u00fckleniyor...</p>';
    try {
      const result = await apiFetch(`/api/desktop/manual/content?document=${selectedManual}`);
      if (id !== requestId || !$("#manualDocument")) return;
      $("#manualDocument").innerHTML = renderMarkdown(result.content);
      $(".manual-tabs [data-manual-tab='usage']")?.setAttribute("aria-label", names.usage);
    } catch (error) {
      if (id === requestId && $("#manualDocument")) $("#manualDocument").innerHTML = `<p class="manual-error">${escapeHtml(error.message)}</p>`;
    }
  }

  const baseRender = render;
  render = function () {
    if (page !== "manual") return baseRender();
    document.body.dataset.page = page;
    $("#content").innerHTML = manualShell();
    $("[data-manual-refresh]").onclick = loadManual;
    document.querySelectorAll("[data-manual-tab]").forEach(button => button.onclick = () => {
      selectedManual = button.dataset.manualTab;
      document.querySelectorAll("[data-manual-tab]").forEach(tab => tab.setAttribute("aria-selected", String(tab === button)));
      loadManual();
    });
    loadManual();
  };
})();
