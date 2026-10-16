(() => {
  let fieldPersonnel = [];
  let fieldMapCenter = { lat: 40.10441, lng: 27.65640 };
  let fieldMap = null;
  let fieldMapElement = null;
  let officeMarker = null;
  let personnelMarkers = new Map();
  let routeLine = null;
  let fieldLocationMarker = null;
  let trafficLayer = null;
  let trafficActive = false;
  let trafficErrorReported = false;
  let vectorMapFrame = null;
  let vectorMapReady = false;
  let canShareLocation = false;
  let locationWatchId = null;
  let locationLastSentAt = 0;
  let locationUploadPending = false;
  let locationShareConfirmed = false;
  let leafletPromise = null;
  let fieldPanelMode = "customer";
  let fieldRadarCategory = "all";
  let routeDrawing = false;
  let routePoints = [];

  function ensureFieldLocationTools(actionHost, mapHeader) {
    if (!actionHost || !mapHeader || mapHeader.parentElement.querySelector(".field-location-tools")) return;
    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "secondary field-location-tools-toggle";
    toggle.textContent = "Konum Islemleri +";
    toggle.setAttribute("aria-expanded", "false");
    const tools = document.createElement("section");
    tools.className = "field-location-tools";
    tools.hidden = true;
    tools.setAttribute("aria-label", "Konum islemleri");
    const actions = [
      ["draw-route", "Yeni Rota Ciz"], ["manual-location", "Manuel Koordinat Gir"],
      ["home", "Eve Don (Merkez)"], ["whatsapp-paste", "WhatsApp Konumu Yapistir"],
      ["share-location", "Konum Baglantisini Paylas"], ["assign-location", "Secili Konumu Personele Ata"]
    ];
    actions.forEach(([action, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary";
      button.dataset.fieldMapAction = action;
      button.textContent = label;
      button.addEventListener("click", () => runFieldMapAction(action));
      tools.append(button);
    });
    const finish = document.createElement("button");
    finish.type = "button";
    finish.className = "primary";
    finish.dataset.fieldRouteFinish = "";
    finish.textContent = "Rotayi Bitir";
    finish.hidden = true;
    finish.addEventListener("click", finishFieldRouteDrawing);
    tools.append(finish);
    const shareRoute = document.createElement("button");
    shareRoute.type = "button";
    shareRoute.className = "secondary";
    shareRoute.dataset.fieldRouteShare = "";
    shareRoute.textContent = "Rotayi WhatsApp ile Paylas";
    shareRoute.hidden = true;
    shareRoute.addEventListener("click", shareFieldRoute);
    tools.append(shareRoute);
    toggle.addEventListener("click", () => {
      tools.hidden = !tools.hidden;
      toggle.setAttribute("aria-expanded", String(!tools.hidden));
      toggle.textContent = tools.hidden ? "Konum Islemleri +" : "Konum Islemleri -";
    });
    actionHost.append(toggle);
    mapHeader.after(tools);
  }

  function currentFieldCoordinates() {
    const selected = fieldLocationMarker?.getLatLng?.();
    return selected ? { lat: selected.lat, lng: selected.lng } : fieldMapCenter;
  }

  async function runFieldMapAction(action) {
    if (action === "manual-location") return openManualFieldLocation();
    if (action === "home") {
      await ensureFieldMap();
      fieldMap?.flyTo([fieldMapCenter.lat, fieldMapCenter.lng], 13);
      if (vectorMapReady) vectorMapFrame.contentWindow.ayecTomTomMap.flyTo(fieldMapCenter.lat, fieldMapCenter.lng, 13);
      return;
    }
    if (action === "whatsapp-paste") return openWhatsAppLocationPaste();
    if (action === "share-location") return shareFieldLocation();
    if (action === "assign-location") return openFieldLocationAssignment();
    if (action === "draw-route") {
      await ensureFieldMap();
      if (!fieldMap) return toast("Harita yuklenemedi.", "warning");
      routeDrawing = true;
      routePoints = [];
      if (routeLine) fieldMap.removeLayer(routeLine);
      routeLine = null;
      fieldMap.getContainer().style.cursor = "crosshair";
      const finish = document.querySelector("[data-field-route-finish]");
      if (finish) finish.hidden = false;
      const share = document.querySelector("[data-field-route-share]");
      if (share) share.hidden = true;
      const footer = document.querySelector(".field-map-canvas>footer span");
      if (footer) footer.textContent = "Durak eklemek icin haritaya tiklayin; en az iki durak secin.";
    }
  }

  async function openManualFieldLocation() {
    openDialog("Konuma Git", "SAHA SERVISI", '<div class="field-manual-location"><p>Gitmek istediginiz nokta icin koordinat giriniz.</p><label>Enlem (Lat)<input id="fieldManualLat" type="number" min="-90" max="90" step="any" required placeholder="39.6484"></label><label>Boylam (Lng)<input id="fieldManualLng" type="number" min="-180" max="180" step="any" required placeholder="27.8826"></label></div>', async () => {
      const lat = Number(document.querySelector("#fieldManualLat")?.value);
      const lng = Number(document.querySelector("#fieldManualLng")?.value);
      if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) {
        toast("Koordinatlar gecersiz.", "warning");
        return false;
      }
      await ensureFieldMap();
      focusFieldLocation({ lat, lon: lng, display_name: "Manuel Konum" });
      return true;
    }, "Konuma Git");
  }

  function openWhatsAppLocationPaste() {
    openDialog("WhatsApp Konumu Yapistir", "SAHA SERVISI", '<div class="field-whatsapp-paste"><p>WhatsApp veya harita baglantisini yapistirin.</p><textarea id="fieldWhatsAppLocationText" rows="4" required></textarea><button type="button" class="secondary" data-field-clipboard-read>Panodan Oku</button></div>', async () => {
      const text = String(document.querySelector("#fieldWhatsAppLocationText")?.value || "").trim();
      if (!text) return false;
      const match = text.match(/(?:[?&]q=|@|:|^|\s)([-+]?\d+(?:\.\d+)?)[,\s]+([-+]?\d+(?:\.\d+)?)/);
      if (match) {
        const lat = Number(match[1]), lng = Number(match[2]);
        if (Math.abs(lat) <= 90 && Math.abs(lng) <= 180) {
          await ensureFieldMap();
          focusFieldLocation({ lat, lon: lng, display_name: "WhatsApp Konumu" });
          return true;
        }
      }
      const input = document.querySelector("#fieldLocationSearch");
      if (input) input.value = text;
      await searchFieldLocation();
      return true;
    }, "Konumu Bul");
    document.querySelector("[data-field-clipboard-read]")?.addEventListener("click", async () => {
      try {
        document.querySelector("#fieldWhatsAppLocationText").value = await navigator.clipboard.readText();
      } catch (_error) {
        toast("Pano izni yok. Baglantiyi metin alanina yapistirin.", "warning");
      }
    });
  }

  async function shareWhatsAppText(text) {
    const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
    if (navigator.share) {
      try {
        await navigator.share({ text });
        return;
      } catch (error) {
        if (error.name === "AbortError") return;
      }
    }
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function shareFieldLocation() {
    const { lat, lng } = currentFieldCoordinates();
    const mapsUrl = `https://www.google.com/maps?q=${lat.toFixed(6)},${lng.toFixed(6)}`;
    await shareWhatsAppText(`\uD83D\uDCCD Konumum: ${mapsUrl}`);
  }

  async function openFieldLocationAssignment() {
    const { lat, lng } = currentFieldCoordinates();
    const options = fieldPersonnel.map(person => `<option value="${esc(person.id)}">${esc(person.name || "Personel")} (${esc(person.job || person.role || "Personel")})</option>`).join("");
    if (!options) return toast("Sistemde saha personeli bulunamadi.", "warning");
    openDialog("Konumu Personele Ata", "SAHA SERVISI", `<p>Secilen Konum: ${lat.toFixed(5)}, ${lng.toFixed(5)}</p><label>Personel<select id="fieldLocationPersonnel" required>${options}</select></label>`, async () => {
      const id = Number(document.querySelector("#fieldLocationPersonnel")?.value);
      await apiFetch("/api/desktop/field-service/assign", {
        method: "POST", body: JSON.stringify({ id, lat, lng })
      });
      await loadFieldPersonnel();
      toast("Personel konumu guncellendi.", "success");
      return true;
    }, "Konumu Ata");
  }

  async function finishFieldRouteDrawing() {
    if (routePoints.length < 2) return toast("Guzergah icin haritada en az iki durak secin.", "warning");
    routeDrawing = false;
    fieldMap?.getContainer().style && (fieldMap.getContainer().style.cursor = "");
    if (routeLine) fieldMap.removeLayer(routeLine);
    routeLine = window.L.polyline(routePoints.map(point => [point.lat, point.lng]), {
      color: "#4edea3", weight: 4, opacity: 0.9, dashArray: "8 6"
    }).addTo(fieldMap);
    fieldMap.fitBounds(routeLine.getBounds(), { padding: [32, 32], maxZoom: 14 });
    const finish = document.querySelector("[data-field-route-finish]");
    if (finish) finish.hidden = true;
    const share = document.querySelector("[data-field-route-share]");
    if (share) share.hidden = false;
    const footer = document.querySelector(".field-map-canvas>footer span");
    if (footer) footer.textContent = `${routePoints.length} durakli taslak rota`;
    syncVectorMap();
    try {
      const result = await apiFetch("/api/desktop/field-service/route", {
        method: "POST", body: JSON.stringify({ points: routePoints })
      });
      if (result.ok && Array.isArray(result.geometry)) {
        routeLine.setLatLngs(result.geometry);
        routeLine.setStyle({ dashArray: null, opacity: 1 });
        if (footer) footer.textContent = `TomTom yol rotasi | ${(Number(result.distance_meters || 0) / 1000).toFixed(1)} km`;
      }
    } catch (error) {
      if (footer) footer.textContent = error.message || "Taslak rota haritada gosteriliyor.";
    }
    syncVectorMap();
  }

  function shareFieldRoute() {
    if (routePoints.length < 2) return;
    const first = routePoints[0];
    const last = routePoints[routePoints.length - 1];
    const waypoints = routePoints.slice(1, -1).map(point => `${point.lat},${point.lng}`).join("|");
    const params = new URLSearchParams({ api: "1", origin: `${first.lat},${first.lng}`, destination: `${last.lat},${last.lng}`, travelmode: "driving" });
    if (waypoints) params.set("waypoints", waypoints);
    void shareWhatsAppText(`Saha rotasi: https://www.google.com/maps/dir/?${params}`);
  }

  function setFieldPanelMode(mode) {
    fieldPanelMode = ["customer", "teams", "jobs"].includes(mode) ? mode : "customer";
    document.querySelectorAll("[data-field-panel-mode]").forEach(button => {
      const selected = button.dataset.fieldPanelMode === fieldPanelMode;
      button.classList.toggle("active", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    const jobs = fieldPanelMode === "jobs";
    const personnelQueue = document.querySelector(".field-personnel-queue");
    const jobRows = document.querySelector("#fieldMapRows");
    if (personnelQueue) personnelQueue.hidden = jobs;
    if (jobRows) jobRows.hidden = !jobs;
    const status = document.querySelector("#fieldMapStatus");
    if (status) status.hidden = !jobs;
    const search = document.querySelector("#genericSearch");
    if (search) search.placeholder = jobs ? "M\u00fc\u015fteri veya i\u015f ara..." : "Teknisyen veya i\u015f emri ara...";
    const filters = document.querySelector(".field-radar-filters");
    if (filters) filters.hidden = fieldPanelMode !== "teams";
    if (jobs) window.ayecFieldRender?.();
    else renderFieldPersonnel();
  }

  function ensureFieldPanelControls() {
    const queue = document.querySelector(".field-map-queue");
    if (!queue || queue.querySelector(".field-mode-tabs")) return;
    const tabs = document.createElement("nav");
    tabs.className = "field-mode-tabs";
    tabs.setAttribute("aria-label", "Saha paneli g\u00f6r\u00fcn\u00fcmleri");
    [["customer", "M\u00fc\u015fteri & WhatsApp"], ["teams", "Ekipler"], ["jobs", "\u0130\u015f Emirleri"]].forEach(([mode, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.fieldPanelMode = mode;
      button.textContent = label;
      button.addEventListener("click", () => setFieldPanelMode(mode));
      tabs.append(button);
    });
    const header = queue.querySelector(":scope > header");
    header?.after(tabs);
    const filters = document.createElement("div");
    filters.className = "field-radar-filters";
    filters.setAttribute("role", "group");
    filters.setAttribute("aria-label", "Ekip filtresi");
    [["all", "Ekipler"], ["idle", "Bekleyen"], ["warnings", "Uyar\u0131lar"]].forEach(([category, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.dataset.fieldRadarCategory = category;
      button.textContent = label;
      button.classList.toggle("active", category === fieldRadarCategory);
      button.addEventListener("click", () => {
        fieldRadarCategory = category;
        filters.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button));
        renderFieldPersonnel();
      });
      filters.append(button);
    });
    const people = queue.querySelector(".field-personnel-queue");
    people?.querySelector("header")?.after(filters);
    const search = document.querySelector("#genericSearch");
    search?.addEventListener("input", () => {
      if (fieldPanelMode !== "jobs") renderFieldPersonnel();
    });
    setFieldPanelMode(fieldPanelMode);
  }

  function coordinate(person) {
    const lat = Number(person?.lat), lng = Number(person?.lng);
    if (!Number.isFinite(lat) || !Number.isFinite(lng) || Math.abs(lat) > 90 || Math.abs(lng) > 180) return null;
    return { lat, lng };
  }

  const genericShellBeforeFieldPersonnel = genericShell;
  genericShell = function(meta) {
    let html = genericShellBeforeFieldPersonnel(meta);
    if (page !== "field-service" || meta?.table !== "appointments") return html;
    html = html.replace(
      "Saha Haritas\u0131 & Canl\u0131 Teknisyen Takibi",
      "Saha Haritas\u0131 & Teknisyen Takibi"
    ).replace(
      "Saha ekiplerinin anl\u0131k konumlar\u0131, devam eden servis rotalar\u0131, m\u00fc\u015fteri lokasyonlar\u0131 ve acil ar\u0131za \u00e7a\u011fr\u0131lar\u0131.",
      "Saha ekiplerinin kay\u0131tl\u0131 koordinatlar\u0131, servis randevular\u0131 ve g\u00f6rev durumlar\u0131."
    ).replace("CANLI KONUM", "GPS KOORD\u0130NATLARI");
    html = html.replace(
      /<div class="field-map-empty">[\s\S]*?<\/div>/,
      '<div class="field-personnel-map-wrap"><div id="fieldPersonnelMap" role="application" aria-label="Saha personel haritas\u0131"></div></div>'
    );
    html = html.replace(
      '<div id="fieldMapRows"></div>',
      '<div id="fieldMapRows"></div><section class="field-personnel-queue"><header><h3>Saha Personeli</h3><b id="fieldPersonnelCount">0</b></header><div id="fieldPersonnelRows"></div></section>'
    );
    return html;
  };

  function loadLeaflet() {
    if (window.L) return Promise.resolve(window.L);
    if (leafletPromise) return leafletPromise;
    leafletPromise = new Promise((resolve, reject) => {
      if (!document.querySelector("#fieldLeafletCss")) {
        const style = document.createElement("link");
        style.id = "fieldLeafletCss";
        style.rel = "stylesheet";
        style.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
        document.head.append(style);
      }
      const script = document.createElement("script");
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.onload = () => window.L ? resolve(window.L) : reject(new Error("Map library did not initialize"));
      script.onerror = () => reject(new Error("Map library could not be loaded"));
      document.head.append(script);
    });
    return leafletPromise;
  }

  function updateTrafficControl() {
    const button = document.querySelector("[data-field-traffic-toggle]");
    if (!button) return;
    button.textContent = trafficActive ? "Trafik Katmanini Kapat" : "Canli Trafik";
    button.setAttribute("aria-pressed", String(trafficActive));
  }

  function addTrafficLayer() {
    if (!fieldMap || !window.L || !trafficActive || trafficLayer) return;
    trafficErrorReported = false;
    trafficLayer = window.L.tileLayer(
      "/api/desktop/field-service/traffic/{z}/{x}/{y}",
      { maxZoom: 19, opacity: 0.82, attribution: "Traffic &copy; TomTom" }
    );
    trafficLayer.on("tileerror", () => {
      if (trafficErrorReported || !trafficActive) return;
      trafficErrorReported = true;
      trafficActive = false;
      if (fieldMap && trafficLayer) fieldMap.removeLayer(trafficLayer);
      trafficLayer = null;
      updateTrafficControl();
      const status = document.querySelector(".field-map-canvas>footer span");
      if (status) status.textContent = "Trafik katmani acilamadi; TomTom Traffic Flow erisimini kontrol edin.";
      toast("Trafik verisi alinamadi. TomTom Traffic Flow anahtarini ve yetkisini kontrol edin.", "warning");
    });
    trafficLayer.addTo(fieldMap);
  }

  function setTrafficActive(active) {
    trafficActive = Boolean(active);
    if (!trafficActive && fieldMap && trafficLayer) fieldMap.removeLayer(trafficLayer);
    if (!trafficActive) trafficLayer = null;
    updateTrafficControl();
    if (trafficActive) addTrafficLayer();
    syncVectorMap();
  }

  function syncVectorMap() {
    if (!vectorMapReady || !vectorMapFrame?.contentWindow?.ayecTomTomMap) return;
    const map = vectorMapFrame.contentWindow.ayecTomTomMap;
    map.setPersonnel(fieldPersonnel);
    map.setTraffic(trafficActive);
    map.setPitch(52);
    const routePoints = routeLine?.getLatLngs?.();
    if (Array.isArray(routePoints) && routePoints.length > 1) {
      map.setRoute(routePoints.map(point => [point.lat, point.lng]));
    } else {
      map.clearRoute();
    }
    const selected = fieldLocationMarker?.getLatLng?.();
    if (selected) map.select(selected.lat, selected.lng);
  }

  function toggleFieldVectorMap() {
    const root = document.querySelector("#fieldPersonnelMap");
    const button = document.querySelector("[data-field-vector-toggle]");
    if (!root || !button) return;
    if (vectorMapFrame) {
      vectorMapReady = false;
      vectorMapFrame.remove();
      vectorMapFrame = null;
      root.classList.remove("field-vector-map-active");
      button.setAttribute("aria-pressed", "false");
      button.textContent = "3D Vektor";
      fieldMap?.invalidateSize();
      return;
    }
    const frame = document.createElement("iframe");
    frame.className = "field-vector-map-frame";
    frame.title = "3D TomTom saha haritasi";
    frame.src = "/field-vector-map-dist/index.html";
    vectorMapFrame = frame;
    vectorMapReady = false;
    root.classList.add("field-vector-map-active");
    root.append(frame);
    button.setAttribute("aria-pressed", "true");
    button.textContent = "2D Haritaya Don";
    frame.addEventListener("load", () => {
      if (vectorMapFrame !== frame) return;
      const mapWindow = frame.contentWindow;
      mapWindow?.addEventListener("ayec-map-ready", () => {
        if (vectorMapFrame !== frame) return;
        vectorMapReady = true;
        syncVectorMap();
        mapWindow.ayecTomTomMap.flyTo(fieldMapCenter.lat, fieldMapCenter.lng, 14);
      }, { once: true });
      mapWindow?.addEventListener("ayec-map-error", event => {
        if (vectorMapFrame !== frame) return;
        const footer = document.querySelector(".field-map-canvas>footer span");
        if (footer) footer.textContent = "3D harita kullanilamadi; 2D haritaya donuluyor.";
        if (event.detail) console.warn("TomTom vector map failed", event.detail);
        toggleFieldVectorMap();
      }, { once: true });
      if (typeof mapWindow?.initAyecTomTomMap !== "function") {
        frame.title = "3D harita yuklenemedi. Tekrar deneyin veya 2D haritaya donun.";
        return;
      }
      const started = mapWindow.initAyecTomTomMap("ayec-server-proxy", fieldMapCenter.lat, fieldMapCenter.lng);
      if (!started && vectorMapFrame === frame) toggleFieldVectorMap();
      window.setTimeout(() => {
        if (vectorMapFrame === frame && !vectorMapReady) toggleFieldVectorMap();
      }, 10000);
    }, { once: true });
  }

  async function ensureFieldMap() {
    const root = document.querySelector("#fieldPersonnelMap");
    if (!root) return null;
    if (fieldMap && fieldMapElement === root) return fieldMap;
    if (fieldMap) fieldMap.remove();
    trafficLayer = null;
    fieldMap = null;
    officeMarker = null;
    personnelMarkers.clear();
    const L = await loadLeaflet();
    if (!root.isConnected) return null;
    fieldMap = L.map(root, { zoomControl: false }).setView([fieldMapCenter.lat, fieldMapCenter.lng], 13);
    fieldMapElement = root;
    fieldMap.on("click", event => {
      const point = { lat: event.latlng.lat, lng: event.latlng.lng };
      if (routeDrawing) {
        routePoints.push(point);
        if (routeLine) fieldMap.removeLayer(routeLine);
        routeLine = L.polyline(routePoints.map(item => [item.lat, item.lng]), {
          color: "#4edea3", weight: 4, opacity: 0.9, dashArray: "8 6"
        }).addTo(fieldMap);
        const footer = document.querySelector(".field-map-canvas>footer span");
        if (footer) footer.textContent = `${routePoints.length} durak secildi`;
        return;
      }
      focusFieldLocation({ lat: point.lat, lon: point.lng, display_name: "Secilen Konum" });
    });
    L.control.zoom({ position: "bottomright" }).addTo(fieldMap);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap contributors"
    }).addTo(fieldMap);
    officeMarker = L.circleMarker([fieldMapCenter.lat, fieldMapCenter.lng], {
      radius: 7, color: "#ffffff", weight: 2, fillColor: "#ef4444", fillOpacity: 1
    }).addTo(fieldMap).bindPopup("Merkez Ofis");
    addTrafficLayer();
    setTimeout(() => fieldMap?.invalidateSize(), 100);
    return fieldMap;
  }

  function drawPersonnelMarkers(L) {
    if (!fieldMap) return;
    personnelMarkers.forEach(marker => fieldMap.removeLayer(marker));
    personnelMarkers.clear();
    const located = fieldPersonnel.map(person => ({ person, point: coordinate(person) })).filter(item => item.point);
    located.forEach(({ person, point }) => {
      const icon = L.divIcon({
        className: "field-personnel-marker",
        html: '<span aria-hidden="true"></span>',
        iconSize: [22, 22],
        iconAnchor: [11, 11]
      });
      const marker = L.marker([point.lat, point.lng], { icon }).addTo(fieldMap);
      const details = [person.job || person.role || "Personel", person.status || "", person.last_seen || ""]
        .filter(Boolean).map(value => esc(value)).join("<br>");
      marker.bindPopup(`<strong>${esc(person.name || "Personel")}</strong><br>${details}`);
      marker.on("click", () => selectPersonnelCard(person.id));
      personnelMarkers.set(String(person.id), marker);
    });
    if (located.length > 1) {
      const bounds = L.latLngBounds(located.map(item => [item.point.lat, item.point.lng]));
      fieldMap.fitBounds(bounds, { padding: [32, 32], maxZoom: 14 });
    } else if (located.length === 1) {
      const point = located[0].point;
      fieldMap.setView([point.lat, point.lng], 14);
    } else {
      fieldMap.setView([fieldMapCenter.lat, fieldMapCenter.lng], 13);
    }
    if (officeMarker) officeMarker.setLatLng([fieldMapCenter.lat, fieldMapCenter.lng]);
    setTimeout(() => fieldMap?.invalidateSize(), 100);
  }

  function distanceKm(first, second) {
    const radians = value => value * Math.PI / 180;
    const dLat = radians(second.lat - first.lat);
    const dLng = radians(second.lng - first.lng);
    const lat1 = radians(first.lat), lat2 = radians(second.lat);
    const value = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
    return 6371 * 2 * Math.atan2(Math.sqrt(value), Math.sqrt(Math.max(0, 1 - value)));
  }

  async function optimizeFieldRoute() {
    const stops = fieldPersonnel.map(person => ({ person, point: coordinate(person) }))
      .filter(item => item.point);
    if (!stops.length || !fieldMap || !window.L) {
      toast("Rota i\u00e7in konum kayd\u0131 olan saha personeli bulunamad\u0131.", "warning");
      return;
    }
    let current = fieldMapCenter;
    const ordered = [];
    const pending = stops.slice();
    while (pending.length) {
      let nearestIndex = 0;
      for (let index = 1; index < pending.length; index += 1) {
        if (distanceKm(current, pending[index].point) < distanceKm(current, pending[nearestIndex].point)) {
          nearestIndex = index;
        }
      }
      const next = pending.splice(nearestIndex, 1)[0];
      ordered.push(next);
      current = next.point;
    }
    if (routeLine) fieldMap.removeLayer(routeLine);
    const points = [fieldMapCenter, ...ordered.map(item => item.point)];
    routeLine = window.L.polyline(points.map(point => [point.lat, point.lng]), {
      color: "#4edea3", weight: 4, opacity: 0.9, dashArray: "8 6"
    }).addTo(fieldMap);
    syncVectorMap();
    fieldMap.fitBounds(routeLine.getBounds(), { padding: [32, 32], maxZoom: 14 });
    const names = ordered.map(item => item.person.name || "Personel").join(" \u2192 ");
    const footerStatus = document.querySelector(".field-map-canvas>footer span");
    if (footerStatus) footerStatus.textContent = `${ordered.length} durakli taslak rota: ${names}`;
    try {
      const result = await apiFetch("/api/desktop/field-service/route", {
        method: "POST",
        body: JSON.stringify({ points: points.map(point => ({ lat: point.lat, lng: point.lng })) })
      });
      if (result.ok && Array.isArray(result.geometry)) {
        routeLine.setLatLngs(result.geometry);
        routeLine.setStyle({ color: "#4edea3", dashArray: null, opacity: 1 });
        fieldMap.fitBounds(routeLine.getBounds(), { padding: [32, 32], maxZoom: 14 });
        const distance = (Number(result.distance_meters || 0) / 1000).toFixed(1);
        const minutes = Math.max(1, Math.round(Number(result.duration_seconds || 0) / 60));
        if (footerStatus) footerStatus.textContent = `TomTom yol rotasi | ${ordered.length} durak | ${distance} km | ${minutes} dk (canli trafik)`;
        syncVectorMap();
        toast(`Yol rotasi olusturuldu: ${distance} km, ${minutes} dk. ${names}`, "success");
        return;
      }
      if (footerStatus) footerStatus.textContent = "TomTom yol rotasi kullanilamiyor; kesik cizgi taslak rotayi gosteriyor.";
      syncVectorMap();
      toast("Yol rotasi icin TomTom Routing yetkisi gerekli; taslak rota haritada kaldi.", "warning");
    } catch (error) {
      if (footerStatus) footerStatus.textContent = "Yol servisine ulasilamadi; kesik cizgi taslak rotayi gosteriyor.";
      syncVectorMap();
      toast(error.message || "Yol rotasi hesaplanamadi; taslak rota haritada kaldi.", "warning");
    }
  }

  function focusFieldLocation(result) {
    const point = coordinate({ lat: result.lat, lng: result.lon });
    if (!point || !fieldMap || !window.L) return;
    if (fieldLocationMarker) fieldMap.removeLayer(fieldLocationMarker);
    fieldLocationMarker = window.L.marker([point.lat, point.lng]).addTo(fieldMap)
      .bindPopup(esc(result.display_name || "Konum"));
    fieldMap.flyTo([point.lat, point.lng], 15);
    fieldLocationMarker.openPopup();
    if (vectorMapReady) {
      vectorMapFrame.contentWindow.ayecTomTomMap.select(point.lat, point.lng);
      vectorMapFrame.contentWindow.ayecTomTomMap.flyTo(point.lat, point.lng, 15);
    }
    const results = document.querySelector("#fieldLocationResults");
    if (results) results.replaceChildren();
  }

  async function searchFieldLocation() {
    const input = document.querySelector("#fieldLocationSearch");
    const resultsHost = document.querySelector("#fieldLocationResults");
    const query = String(input?.value || "").trim();
    if (!query) return;
    const coords = query.match(/([-+]?\d+(?:\.\d+)?),\s*([-+]?\d+(?:\.\d+)?)/);
    if (coords) {
      const result = { lat: Number(coords[1]), lon: Number(coords[2]), display_name: query };
      if (coordinate({ lat: result.lat, lng: result.lon })) {
        await ensureFieldMap();
        focusFieldLocation(result);
        return;
      }
    }
    const button = document.querySelector("[data-field-location-search]");
    if (button) button.disabled = true;
    if (resultsHost) {
      resultsHost.replaceChildren();
      resultsHost.textContent = "Adres aran\u0131yor...";
    }
    try {
      const data = await apiFetch("/api/desktop/field-service/geocode", {
        method: "POST", body: JSON.stringify({ query })
      });
      const matches = Array.isArray(data.results) ? data.results : [];
      if (!matches.length) {
        if (resultsHost) resultsHost.textContent = "Konum bulunamad\u0131.";
        return;
      }
      await ensureFieldMap();
      if (matches.length === 1) {
        focusFieldLocation(matches[0]);
        return;
      }
      if (resultsHost) {
        resultsHost.replaceChildren(...matches.map((match, index) => {
          const option = document.createElement("button");
          option.type = "button";
          option.className = "field-location-result";
          option.setAttribute("role", "option");
          option.textContent = match.display_name || `Konum ${index + 1}`;
          option.addEventListener("click", () => focusFieldLocation(match));
          return option;
        }));
      }
    } catch (error) {
      if (resultsHost) resultsHost.textContent = error.message || "Adres aramas\u0131 tamamlanamad\u0131.";
    } finally {
      if (button) button.disabled = false;
    }
  }

  function selectPersonnelCard(id) {
    document.querySelectorAll(".field-personnel-card").forEach(card => {
      card.classList.toggle("selected", String(card.dataset.id) === String(id));
    });
  }

  function focusPerson(person) {
    const point = coordinate(person);
    const marker = personnelMarkers.get(String(person?.id));
    selectPersonnelCard(person?.id);
    if (point && fieldMap) {
      fieldMap.flyTo([point.lat, point.lng], 16);
      if (marker) marker.openPopup();
    }
  }

  function updateLocationShareControl() {
    const button = document.querySelector("[data-field-location-share]");
    if (!button) return;
    button.textContent = locationWatchId === null ? "Canli GPS Paylas" : "GPS Paylasimini Durdur";
    button.setAttribute("aria-pressed", String(locationWatchId !== null));
  }

  function stopFieldLocationShare(notify = false) {
    if (locationWatchId !== null && navigator.geolocation) {
      navigator.geolocation.clearWatch(locationWatchId);
    }
    locationWatchId = null;
    locationUploadPending = false;
    updateLocationShareControl();
    if (notify) toast("Canli GPS paylasimi durduruldu.", "info");
  }

  async function uploadFieldLocation(position) {
    if (locationUploadPending || Date.now() - locationLastSentAt < 30000) return;
    locationUploadPending = true;
    try {
      const result = await apiFetch("/api/desktop/field-service/location", {
        method: "POST",
        body: JSON.stringify({ lat: position.coords.latitude, lng: position.coords.longitude })
      });
      locationLastSentAt = Date.now();
      const person = fieldPersonnel.find(item => String(item.id) === String(result.personnel_id));
      if (person) {
        person.lat = Number(result.lat);
        person.lng = Number(result.lng);
        person.last_seen = result.last_seen;
        renderFieldPersonnel();
      }
      const status = document.querySelector(".field-map-canvas>footer span");
      if (status) status.textContent = `GPS konumu guncellendi: ${Number(result.lat).toFixed(5)}, ${Number(result.lng).toFixed(5)}`;
      if (!locationShareConfirmed) {
        toast("GPS konumunuz saha haritasiyla paylasiliyor.", "success");
        locationShareConfirmed = true;
      }
    } catch (error) {
      stopFieldLocationShare();
      toast(error.message || "GPS konumu guncellenemedi.", "error");
    } finally {
      locationUploadPending = false;
    }
  }

  function toggleFieldLocationShare() {
    if (locationWatchId !== null) {
      stopFieldLocationShare(true);
      return;
    }
    if (!canShareLocation || !navigator.geolocation) {
      toast("Bu oturumda saha GPS paylasimi kullanilamiyor.", "warning");
      return;
    }
    locationLastSentAt = 0;
    locationShareConfirmed = false;
    locationWatchId = navigator.geolocation.watchPosition(
      uploadFieldLocation,
      error => {
        stopFieldLocationShare();
        const message = error.code === 1
          ? "Konum izni verilmedi. Tarayici ayarlarindan konum iznini acin."
          : "Cihaz konumu alinamadi. GPS baglantisini kontrol edin.";
        toast(message, "warning");
      },
      { enableHighAccuracy: true, maximumAge: 15000, timeout: 20000 }
    );
    updateLocationShareControl();
  }

  function renderFieldPersonnel() {
    ensureFieldPanelControls();
    const host = document.querySelector("#fieldPersonnelRows");
    if (!host) return;
    const count = document.querySelector("#fieldPersonnelCount");
    if (count) count.textContent = String(fieldPersonnel.length);
    const mapHint = document.querySelector(".field-map-canvas header small");
    if (mapHint) mapHint.textContent = fieldPersonnel.some(coordinate)
      ? "Kay\u0131tl\u0131 personel koordinatlar\u0131"
      : "Varsay\u0131lan i\u015fletme konumu";
    const gpsCount = fieldPersonnel.filter(coordinate).length;
    const gpsMetric = document.querySelector(".field-map-metrics article:nth-child(4) strong");
    const gpsNote = document.querySelector(".field-map-metrics article:nth-child(4) footer");
    if (gpsMetric) gpsMetric.textContent = `${gpsCount} / ${fieldPersonnel.length}`;
    if (gpsNote) gpsNote.textContent = `${gpsCount} personel i\u00e7in konum kayd\u0131`;
    const connected = document.querySelector(".field-map-offline");
    if (connected) {
      connected.innerHTML = `<i></i>${gpsCount} GPS / ${fieldPersonnel.length} PERSONEL`;
      connected.classList.toggle("field-map-online", fieldPersonnel.some(coordinate));
    }
    const query = String(document.querySelector("#genericSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
    const visiblePersonnel = fieldPersonnel.filter(person => {
      const matchesQuery = !query || [person.name, person.job, person.role, person.status].join(" ").toLocaleLowerCase("tr-TR").includes(query);
      const point = coordinate(person);
      const matchesCategory = fieldRadarCategory === "all"
        || (fieldRadarCategory === "idle" && String(person.status || "").toLocaleLowerCase("tr-TR").includes("bo\u015fta"))
        || (fieldRadarCategory === "warnings" && !point);
      return matchesQuery && matchesCategory;
    });
    const teamTab = document.querySelector('[data-field-panel-mode="teams"]');
    const jobTab = document.querySelector('[data-field-panel-mode="jobs"]');
    if (teamTab) teamTab.textContent = `Ekipler (${fieldPersonnel.length})`;
    if (jobTab) jobTab.textContent = `\u0130\u015f Emirleri (${document.querySelectorAll("#fieldMapRows .field-map-job").length})`;
    const idleCount = fieldPersonnel.filter(person => String(person.status || "").toLocaleLowerCase("tr-TR").includes("bo\u015fta")).length;
    const warningCount = fieldPersonnel.filter(person => !coordinate(person)).length;
    const allFilter = document.querySelector('[data-field-radar-category="all"]');
    const idleFilter = document.querySelector('[data-field-radar-category="idle"]');
    const warningFilter = document.querySelector('[data-field-radar-category="warnings"]');
    if (allFilter) allFilter.textContent = `Ekipler (${fieldPersonnel.length})`;
    if (idleFilter) idleFilter.textContent = `Bekleyen (${idleCount})`;
    if (warningFilter) warningFilter.textContent = `Uyar\u0131lar (${warningCount})`;
    host.innerHTML = visiblePersonnel.length ? visiblePersonnel.map(person => {
      const point = coordinate(person);
      const coords = point ? `GPS: ${point.lat.toFixed(5)}, ${point.lng.toFixed(5)}` : "GPS: Konum tan\u0131ml\u0131 de\u011fil";
      return `<article class="field-personnel-card" tabindex="0" data-kind="field-personnel" data-id="${esc(person.id)}"><button type="button" class="field-personnel-focus"><strong>${esc(person.name || "Personel")}</strong><span>${esc(person.job || person.role || "Personel")}</span><span class="badge">${esc(person.status || "Durum bildirilmemi\u015f")}</span><small>${esc(coords)}</small>${person.last_seen ? `<small>Son konum: ${esc(person.last_seen)}</small>` : ""}</button><button type="button" class="mini field-personnel-finish" data-field-personnel-finish="${esc(person.id)}">G\u00f6revi Tamamla</button></article>`;
    }).join("") : empty("Aktif saha personeli bulunamad\u0131", "GPS konumu olan personel bu listede g\u00f6sterilir.");
    host.querySelectorAll('[data-kind="field-personnel"]').forEach(card => {
      bindInteractiveRow(card);
      card.querySelector(".field-personnel-focus")?.addEventListener("click", () => focusPerson(fieldPersonnel.find(person => String(person.id) === card.dataset.id)));
    });
    host.querySelectorAll("[data-field-personnel-finish]").forEach(button => {
      button.addEventListener("click", event => {
        event.stopPropagation();
        finishDuty(button.dataset.fieldPersonnelFinish);
      });
    });
    const mapHeader = document.querySelector(".field-map-canvas>header");
    if (mapHeader && !mapHeader.querySelector(".field-map-actions")) {
      const actions = document.createElement("div");
      actions.className = "field-map-actions";
      const status = mapHeader.querySelector(".field-map-offline");
      mapHeader.insertBefore(actions, status || null);
    }
    const actionHost = mapHeader?.querySelector(".field-map-actions") || mapHeader;
    if (canShareLocation && mapHeader && !mapHeader.querySelector("[data-field-location-share]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary field-location-share";
      button.dataset.fieldLocationShare = "";
      button.addEventListener("click", toggleFieldLocationShare);
      actionHost.append(button);
      updateLocationShareControl();
    } else if (!canShareLocation) {
      mapHeader?.querySelector("[data-field-location-share]")?.remove();
    }
    if (mapHeader && !mapHeader.querySelector("[data-field-route-optimize]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary field-route-optimize";
      button.dataset.fieldRouteOptimize = "";
      button.textContent = "Rotay\u0131 Optimize Et";
      button.addEventListener("click", optimizeFieldRoute);
      actionHost.append(button);
    }
    if (mapHeader && !mapHeader.querySelector("[data-field-traffic-toggle]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary field-traffic-toggle";
      button.dataset.fieldTrafficToggle = "";
      button.addEventListener("click", () => setTrafficActive(!trafficActive));
      actionHost.append(button);
      updateTrafficControl();
    }
    if (mapHeader && !mapHeader.querySelector("[data-field-vector-toggle]")) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "secondary field-vector-toggle";
      button.dataset.fieldVectorToggle = "";
      button.textContent = vectorMapFrame ? "2D Haritaya Don" : "3D Vektor";
      button.setAttribute("aria-pressed", String(Boolean(vectorMapFrame)));
      button.addEventListener("click", toggleFieldVectorMap);
      actionHost.append(button);
    }
    if (mapHeader && !mapHeader.querySelector(".field-location-search")) {
      const search = document.createElement("div");
      search.className = "field-location-search";
      search.innerHTML = '<input id="fieldLocationSearch" class="control" type="search" maxlength="250" placeholder="Adres veya koordinat ara"><button type="button" class="secondary" data-field-location-search>Ara</button><div id="fieldLocationResults" role="listbox"></div>';
      actionHost.append(search);
      search.querySelector("[data-field-location-search]").addEventListener("click", searchFieldLocation);
      search.querySelector("input").addEventListener("keydown", event => {
        if (event.key === "Enter") searchFieldLocation();
      });
    }
    ensureFieldLocationTools(actionHost, mapHeader);
    ensureFieldMap().then(map => { if (map && window.L) drawPersonnelMarkers(window.L); syncVectorMap(); })
      .catch(error => {
        leafletPromise = null;
        const mapHint = document.querySelector(".field-map-canvas header small");
        if (mapHint) mapHint.textContent = error.message || "Harita yuklenemedi";
      });
  }

  async function loadFieldPersonnel() {
    const data = await apiFetch("/api/desktop/field-service/personnel");
    fieldPersonnel = data.personnel || [];
    canShareLocation = data.can_share_location === true;
    if (data.center && Number.isFinite(Number(data.center.lat)) && Number.isFinite(Number(data.center.lng))) {
      fieldMapCenter = { lat: Number(data.center.lat), lng: Number(data.center.lng) };
    }
    renderFieldPersonnel();
  }

  async function finishDuty(id) {
    const person = fieldPersonnel.find(item => String(item.id) === String(id));
    if (!person) return;
    openDialog("G\u00f6revi Tamamla", "SAHA SERV\u0130S\u0130", `<p><strong>${esc(person.name || "Personel")}</strong> i\u00e7in g\u00f6rev tamamlan\u0131p durumu Bo\u015fta yap\u0131lacak. Devam edilsin mi?</p>`, async () => {
      try {
        await apiFetch("/api/desktop/field-service/finish", {
          method: "POST", body: JSON.stringify({ id: Number(id) })
        });
        person.status = "Bo\u015fta";
        renderFieldPersonnel();
        toast(`${person.name} durumu Bo\u015fta olarak g\u00fcncellendi.`, "success");
        return true;
      } catch (error) {
        toast(error.message || "Personel durumu g\u00fcncellenemedi.", "error");
        return false;
      }
    }, "Evet, Tamamla");
    document.querySelector("#dialogCancel").textContent = "Hay\u0131r";
  }

  const genericLoadBeforeFieldPersonnel = loadGenericModule;
  loadGenericModule = async function(meta, query = "") {
    await genericLoadBeforeFieldPersonnel(meta, query);
    if (page !== "field-service") {
      stopFieldLocationShare();
      vectorMapFrame?.remove();
      vectorMapFrame = null;
      vectorMapReady = false;
    }
    if (page === "field-service" && meta?.table === "appointments") await loadFieldPersonnel();
  };

  const showContextBeforeFieldPersonnel = showContext;
  showContext = function(event, kind, id) {
    if (kind !== "field-personnel") return showContextBeforeFieldPersonnel(event, kind, id);
    if (!ayecContextMenuEnabled()) return;
    event.preventDefault();
    const menu = document.querySelector("#contextMenu");
    menu.innerHTML = '<button type="button" role="menuitem" data-context-action="field-personnel-finish">G\u00f6revi Tamamla / Bo\u015fa \u00c7\u0131kar</button>';
    menu.style.left = Math.max(8, Math.min(event.clientX, innerWidth - 220)) + "px";
    menu.style.top = Math.max(8, Math.min(event.clientY, innerHeight - 64)) + "px";
    menu.classList.add("open");
    menu.querySelectorAll("[data-context-action]").forEach(button => {
      button.onclick = () => {
        menu.classList.remove("open");
        contextAction(kind, id, button.dataset.contextAction, event.currentTarget);
      };
    });
  };

  const contextActionBeforeFieldPersonnel = contextAction;
  contextAction = function(kind, id, action, row) {
    if (kind === "field-personnel" && action === "field-personnel-finish") return finishDuty(id);
    return contextActionBeforeFieldPersonnel(kind, id, action, row);
  };

})();
