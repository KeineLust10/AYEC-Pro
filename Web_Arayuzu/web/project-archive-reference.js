(() => {
  const archiveModule = genericModules["project-archive"];
  const baseShell = genericShell;
  const baseLoader = loadGenericModule;
  const state = { page: 0, query: "", rows: [], count: 0, pageSize: 30 };

  function archiveShell() {
    return `${pageHead("\uD83D\uDCE6 Proje Ar\u015fivi", "Ar\u015fivlenmi\u015f projeleri geri y\u00fckleyin veya kal\u0131c\u0131 olarak silin.", '<button class="secondary" data-generic-refresh>Yenile</button>')}<section class="card project-archive-reference"><div class="toolbar"><input class="control search" id="genericSearch" type="search" placeholder="Ar\u015fivde ara..."><span class="muted" id="genericCount">Y\u00fckleniyor...</span></div><div id="genericHost">${empty("Projeler y\u00fckleniyor", "Ar\u015fiv kay\u0131tlar\u0131 okunuyor.")}</div><nav class="project-archive-pager" aria-label="Proje ar\u015fivi sayfalar\u0131"><button type="button" class="secondary" data-project-archive-page="previous">&lt; \u00d6nceki</button><output id="projectArchivePageLabel">Sayfa 1 / 1</output><button type="button" class="secondary" data-project-archive-page="next">Sonraki &gt;</button></nav></section>`;
  }

  function archiveCard(project) {
    const reference = project.ref_no ? `[${esc(project.ref_no)}] ` : "";
    const customer = project.customer_name || project.client_name || project.customer || "";
    return `<article class="project-archive-card"><h3>${reference}${esc(project.name || "-")}</h3>${customer ? `<p>${esc(customer)}</p>` : ""}<p class="project-archive-status">Durum: ${esc(project.status || "Ar\u015fivde")}</p><div class="project-archive-actions"><button type="button" data-project-archive-action="restore" data-project-id="${esc(project.id)}">\u21a9 Geri Al</button><button type="button" data-project-archive-action="delete" data-project-id="${esc(project.id)}" aria-label="Kal\u0131c\u0131 sil" title="Kal\u0131c\u0131 Sil">\uD83D\uDDD1</button></div></article>`;
  }

  async function loadArchive(query = "") {
    const host = $("#genericHost");
    if (!host || page !== "project-archive") return;
    if (query !== state.query) {
      state.query = query;
      state.page = 0;
    }
    try {
      const params = `limit=${state.pageSize}&offset=${state.page * state.pageSize}&q=${encodeURIComponent(state.query)}&archived_only=1`;
      const data = await apiFetch(`/api/desktop/table/projects?${params}`);
      state.rows = data.rows || [];
      state.count = Number(data.count || 0);
      const pageCount = Math.max(1, Math.ceil(state.count / state.pageSize));
      if (state.page >= pageCount) {
        state.page = pageCount - 1;
        if (Number(data.offset || 0) !== state.page * state.pageSize) return loadArchive(state.query);
      }
      host.innerHTML = state.rows.length ? `<div class="project-archive-grid">${state.rows.map(archiveCard).join("")}</div>` : empty("Ar\u015fivde proje bulunmuyor.", state.query ? "Arama ko\u015fullar\u0131n\u0131 de\u011fi\u015ftirin." : "Ar\u015fivlenmi\u015f proje bulunamad\u0131.");
      $("#genericCount").textContent = `Toplam Ar\u015fiv: ${state.count}`;
      $("#projectArchivePageLabel").textContent = `Sayfa ${state.page + 1} / ${pageCount}`;
      const previous = $('[data-project-archive-page="previous"]');
      const next = $('[data-project-archive-page="next"]');
      if (previous) previous.disabled = state.page <= 0;
      if (next) next.disabled = state.page + 1 >= pageCount;
    } catch (error) {
      host.innerHTML = empty("Ar\u015fiv y\u00fcklenemedi", error.message || "Proje ar\u015fivi okunamad\u0131.");
    }
  }

  function openPermanentDelete(project) {
    openDialog("Projeyi Kal\u0131c\u0131 Sil", "PROJE AR\u015e\u0130V\u0130", `<p>${esc(project.name || "Bu proje")} projesini kal\u0131c\u0131 olarak silmek istedi\u011finizden emin misiniz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`, async () => {
      await apiFetch("/api/desktop/projects/lifecycle", { method: "POST", body: JSON.stringify({ project_id: Number(project.id), action: "delete" }) });
      toast("Proje kal\u0131c\u0131 olarak silindi.", "warning");
      await loadArchive(state.query);
      return true;
    }, "Kal\u0131c\u0131 Sil");
    const submit = $("#dialogSubmit");
    if (submit) {
      submit.classList.remove("primary");
      submit.classList.add("danger");
    }
  }

  genericShell = function(meta) {
    return meta === archiveModule ? archiveShell() : baseShell(meta);
  };

  loadGenericModule = function(meta, query = "") {
    return meta === archiveModule ? loadArchive(query) : baseLoader(meta, query);
  };

  if (!document.body.dataset.projectArchiveActionsDelegated) {
    document.body.dataset.projectArchiveActionsDelegated = "1";
    document.addEventListener("click", event => {
      const target = event.target instanceof Element ? event.target : null;
      if (page !== "project-archive" || !target) return;
      const pager = target.closest("[data-project-archive-page]");
      if (pager) {
        state.page = Math.max(0, state.page + (pager.dataset.projectArchivePage === "next" ? 1 : -1));
        void loadArchive(state.query);
        return;
      }
      const action = target.closest("[data-project-archive-action]");
      if (!action) return;
      const project = state.rows.find(row => String(row.id) === String(action.dataset.projectId));
      if (!project) return;
      if (action.dataset.projectArchiveAction === "restore") {
        void apiFetch("/api/desktop/projects/lifecycle", { method: "POST", body: JSON.stringify({ project_id: Number(project.id), action: "restore" }) })
          .then(() => { toast("Proje ar\u015fivden \u00e7\u0131kar\u0131ld\u0131.", "success"); return loadArchive(state.query); })
          .catch(error => toast(error.message || "Proje geri al\u0131namad\u0131.", "error"));
      } else if (action.dataset.projectArchiveAction === "delete") {
        openPermanentDelete(project);
      }
    });
  }
})();
