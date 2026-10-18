(function () {
  "use strict";

  var baseShowContext = showContext;
  var baseContextAction = contextAction;
  var baseHydrateDesktop = hydrateDesktop;
  var baseRenderAppointments = renderAppointments;

  function normalizeAppointmentRows() {
    if (!Array.isArray(db.appointments)) return;
    db.appointments = db.appointments.map(function (item) {
      return Object.assign({}, item, {
        appointment_type: item.appointment_type || (item.workflow === "teklif_montaj" ? "installation" : "service"),
        offerId: item.offerId || item.offer_id || ""
      });
    });
  }

  function appointmentFor(id) {
    return (db.appointments || []).find(function (item) {
      return String(item.id) === String(id);
    });
  }

  function isMontageAppointment(item) {
    return Boolean(item && (item.workflow === "teklif_montaj" || item.appointment_type === "installation"));
  }

  function locationLabel(location) {
    var label = String(location.name || "Location " + location.id);
    return location.vehicle_plate ? label + " (" + location.vehicle_plate + ")" : label;
  }

  function callMontageApi(payload) {
    return apiFetch("/api/desktop/appointments/montage-plan", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  }

  function appointmentMaterials(appointment) {
    return (appointment && appointment.plan_items || []).filter(function (plan) {
      return plan.item_role === "material" || plan.item_role === "manual_material";
    });
  }

  function availableAt(locationId, partId) {
    var row = (db.stockLocationBalances || []).find(function (balance) {
      return String(balance.location_id) === String(locationId)
        && String(balance.part_id) === String(partId);
    });
    return Number(row && row.quantity || 0);
  }

  function preparationRows(plans, sourceId) {
    return plans.map(function (plan) {
      var isMaterial = plan.item_role === "material" && plan.part_id;
      var manual = plan.item_role === "manual_material";
      var planned = Number(plan.planned_qty || 0);
      var loaded = Number(plan.loaded_qty || 0);
      var remaining = Math.max(0, planned - loaded);
      var available = isMaterial ? availableAt(sourceId, plan.part_id) : 0;
      var status = manual ? "Stok kart\u0131 gerekli" : isMaterial ? (remaining > 0 ? "Haz\u0131rlanacak" : "Y\u00fcklendi") : "Planland\u0131";
      var quantity = isMaterial
        ? '<input type="number" min="0" max="' + remaining + '" step="1" value="0" name="plan_' + esc(plan.id) + '" data-plan-id="' + esc(plan.id) + '" data-part-id="' + esc(plan.part_id) + '" aria-label="' + esc(plan.name) + ' y\u00fckleme miktar\u0131">'
        : '<span class="muted">-</span>';
      return '<tr><td><strong>' + esc(plan.name || "-") + '</strong></td><td>' + (isMaterial || manual ? "Malzeme" : "Hizmet") + '</td><td>' + Number(planned).toLocaleString("tr-TR") + ' ' + esc(plan.unit || "Adet") + '</td><td data-available-for="' + esc(plan.part_id || "") + '">' + (isMaterial ? available.toLocaleString("tr-TR") : "-") + '</td><td>' + quantity + '</td><td>' + status + '</td></tr>';
    }).join("");
  }

  async function openAppointmentMontagePreparation(id) {
    try {
      var prepared = await callMontageApi({ action: "prepare", appointment_id: Number(id) });
      await hydrateDesktop(true);
      var appointment = appointmentFor(id);
      var plans = prepared.plans || appointment && appointment.plan_items || [];
      var locations = db.stockLocations || prepared.locations || [];
      var sources = locations.filter(function (location) { return location.location_type !== "vehicle"; });
      var vehicles = locations.filter(function (location) { return location.location_type === "vehicle"; });
      var firstPlan = plans.find(function (plan) { return plan.source_location_id; });
      var sourceId = String(firstPlan && firstPlan.source_location_id || sources[0] && sources[0].id || "");
      var vehicleId = String(firstPlan && firstPlan.vehicle_location_id || vehicles[0] && vehicles[0].id || "");
      var sourceOptions = sources.map(function (location) {
        return '<option value="' + esc(location.id) + '"' + (String(location.id) === sourceId ? " selected" : "") + '>' + esc(locationLabel(location)) + '</option>';
      }).join("");
      var vehicleOptions = vehicles.map(function (location) {
        return '<option value="' + esc(location.id) + '"' + (String(location.id) === vehicleId ? " selected" : "") + '>' + esc(locationLabel(location)) + '</option>';
      }).join("");
      var body = '<section class="appointment-montage-hero"><strong>Araca Y\u00fckleme Kontrol\u00fc</strong><p>Teklif kalemlerini kontrol edin; malzemeleri sahaya \u00e7\u0131kmadan \u00f6nce servis arac\u0131na aktarabilirsiniz.</p></section>'
        + '<div class="form-grid appointment-montage-locations"><div class="field"><label>Kaynak Konum</label><select name="source_location_id" required>' + sourceOptions + '</select></div><div class="field"><label>Servis Arac\u0131</label><select name="vehicle_location_id" required>' + vehicleOptions + '</select></div></div>'
        + '<div class="table-wrap appointment-montage-table"><table><thead><tr><th>Kalem</th><th>T\u00fcr</th><th>Teklif</th><th>Depo</th><th>Y\u00fckle</th><th>Durum</th></tr></thead><tbody>'
        + (plans.length ? preparationRows(plans, sourceId) : '<tr><td colspan="6">Teklif kalemi bulunamad\u0131.</td></tr>')
        + '</tbody></table></div>';
      openDialog("Montaj Haz\u0131rl\u0131\u011f\u0131", "TEKL\u0130F VE MONTAJ", body, async function (formData) {
        var values = Object.fromEntries(formData);
        var lines = plans.filter(function (plan) { return plan.item_role === "material" && plan.part_id; }).map(function (plan) {
          return { plan_id: Number(plan.id), quantity: Number(values["plan_" + plan.id] || 0) };
        }).filter(function (line) { return line.quantity > 0; });
        var result = await callMontageApi({
          action: "load",
          appointment_id: Number(id),
          source_location_id: Number(values.source_location_id),
          vehicle_location_id: Number(values.vehicle_location_id),
          lines: lines
        });
        await hydrateDesktop(true);
        toast("Malzemeler araca y\u00fcklendi: " + (result.reference || ""));
        return true;
      }, "Araca Y\u00fckle");
      var sourceSelect = document.querySelector('#dialogBody [name="source_location_id"]');
      if (sourceSelect) sourceSelect.addEventListener("change", function () {
        document.querySelectorAll("#dialogBody [data-part-id]").forEach(function (input) {
          var cell = input.closest("tr").querySelector("[data-available-for]");
          if (cell) cell.textContent = availableAt(sourceSelect.value, input.dataset.partId).toLocaleString("tr-TR");
        });
      });
    } catch (error) {
      toast(error.message || "Montaj haz\u0131rl\u0131\u011f\u0131 a\u00e7\u0131lamad\u0131.", "error");
    }
  }

  async function openAppointmentMontageCompletion(id, cancellation, afterSave) {
    try {
      await callMontageApi({ action: "prepare", appointment_id: Number(id) });
      await hydrateDesktop(true);
      var appointment = appointmentFor(id);
      var plans = appointmentMaterials(appointment);
      var loadedPlans = plans.filter(function (plan) {
        return Number(plan.loaded_qty || 0) > 0 || plan.item_role === "manual_material";
      });
      var rows = loadedPlans.map(function (plan) {
        var loaded = Number(plan.loaded_qty || 0);
        return '<tr><td><strong>' + esc(plan.name || "-") + '</strong></td><td>' + loaded.toLocaleString("tr-TR") + ' ' + esc(plan.unit || "Adet") + '</td><td><input type="number" min="0" max="' + loaded + '" step="1" value="' + loaded + '" name="used_' + esc(plan.id) + '" data-used-qty data-loaded="' + loaded + '" data-returned="returned_' + esc(plan.id) + '"></td><td><output id="returned_' + esc(plan.id) + '">0</output></td><td>' + (loaded ? "Y\u00fcklendi" : "Y\u00fckleme yok") + '</td></tr>';
      }).join("");
      var message = cancellation
        ? "\u0130ptal edilen randevudaki kullan\u0131lan miktar\u0131 se\u00e7in. Kalan malzeme ana depoya iade edilir."
        : "Kullan\u0131lan miktarlari girin. Kullanilmayan malzemeler kaynak konuma iade edilir.";
      var body = '<p class="appointment-montage-notice">' + message + '</p><div class="table-wrap appointment-montage-table"><table><thead><tr><th>Kalem</th><th>Y\u00fcklenen</th><th>Kullan\u0131lan</th><th>\u0130ade</th><th>Durum</th></tr></thead><tbody>'
        + (rows || '<tr><td colspan="5">Bu montajda ara\u00e7 malzemesi bulunmuyor.</td></tr>') + '</tbody></table></div>';
      openDialog(cancellation ? "\u0130ptal ve Ara\u00e7 Malzeme Karar\u0131" : "Montaj Tamamlama", "TEKL\u0130F VE MONTAJ", body, async function (formData) {
        var values = Object.fromEntries(formData);
        var lines = plans.filter(function (plan) { return plan.item_role === "material"; }).map(function (plan) {
          return { plan_id: Number(plan.id), used_qty: Number(values["used_" + plan.id] || 0) };
        });
        await callMontageApi({ action: "complete", appointment_id: Number(id), lines: lines });
        await hydrateDesktop(true);
        if (afterSave) setTimeout(afterSave, 0);
        return true;
      }, cancellation ? "\u0130ptali ve Malzeme Karar\u0131n\u0131 Kaydet" : "Montaj\u0131 Tamamla");
      document.querySelectorAll("#dialogBody [data-used-qty]").forEach(function (input) {
        input.addEventListener("input", function () {
          var returned = document.getElementById(input.dataset.returned);
          if (returned) returned.value = Math.max(0, Number(input.dataset.loaded || 0) - Number(input.value || 0)).toLocaleString("tr-TR");
        });
      });
    } catch (error) {
      toast(error.message || "Montaj malzeme plan\u0131 y\u00fcklenemedi.", "error");
    }
  }

  function remainingVehicleStock(appointment) {
    return appointmentMaterials(appointment).some(function (plan) {
      return Number(plan.loaded_qty || 0) > Number(plan.used_qty || 0) + Number(plan.returned_qty || 0) + 0.000001;
    });
  }

  async function setAppointmentStatus(id, status) {
    var appointment = appointmentFor(id);
    if (!appointment) return;
    try {
      if (Number.isInteger(+appointment.id)) {
        await desktopWrite("appointments", { id: +appointment.id, _action: "update", status: status });
      }
      appointment.status = status;
      save();
      toast("Randevu durumu: " + status);
      render();
    } catch (error) {
      toast("Randevu durumu g\u00fcncellenemedi: " + (error.message || ""), "error");
    }
  }

  async function deleteAppointment(id) {
    var appointment = appointmentFor(id);
    if (!appointment) return;
    openDialog(
      "Randevuyu Sil",
      "SILME ONAYI",
      '<p>' + esc(appointment.appointment_no || appointment.no || id) + ' randevusunu silmek istediğinize emin misiniz?</p><p>Bu işlem geri alınamaz.</p>',
      async function () {
        try {
          if (Number.isInteger(+appointment.id)) {
            await apiFetch("/api/desktop/table/appointments", {
              method: "POST",
              body: JSON.stringify({ id: +appointment.id, _action: "delete" })
            });
          }
          db.appointments = (db.appointments || []).filter(function (item) {
            return String(item.id) !== String(id);
          });
          save();
          toast("Randevu silindi.", "success");
          render();
        } catch (error) {
          toast("Randevu silinemedi: " + (error.message || ""), "error");
          return false;
        }
      },
      "Evet, Sil"
    );
    var cancelButton = $("#dialogCancel");
    if (cancelButton) cancelButton.textContent = "Hayır";
    var submitButton = $("#dialogSubmit");
    if (submitButton) {
      submitButton.classList.remove("primary");
      submitButton.classList.add("danger");
    }
  }

  showContext = function (event, kind, id) {
    baseShowContext(event, kind, id);
    if (kind !== "appointment" || !ayecContextMenuEnabled()) return;
    var menu = document.querySelector("#contextMenu");
    if (!menu || !menu.classList.contains("open")) return;
    ["approve", "complete", "cancel"].forEach(function (action) {
      var baseButton = menu.querySelector('[data-context-action="' + action + '"]');
      if (baseButton) baseButton.remove();
    });

    var button = document.createElement("button");
    button.type = "button";
    button.textContent = "Montaj Haz\u0131rl\u0131\u011f\u0131";
    button.dataset.contextAction = "montage-prep";
    button.onclick = function () {
      menu.classList.remove("open");
      openAppointmentMontagePreparation(id);
    };
    menu.append(button);

    var statusTrigger = document.createElement("button");
    statusTrigger.type = "button";
    statusTrigger.textContent = "Durum De\u011fi\u015ftir  \u203a";
    statusTrigger.setAttribute("aria-haspopup", "menu");
    statusTrigger.setAttribute("aria-expanded", "false");
    menu.append(statusTrigger);

    var statusMenu = document.createElement("div");
    statusMenu.className = "appointment-status-submenu";
    statusMenu.setAttribute("role", "menu");
    Object.assign(statusMenu.style, {
      display: "none",
      position: "fixed",
      zIndex: "91",
      minWidth: "190px",
      padding: "6px",
      border: "1px solid var(--line)",
      borderRadius: "11px",
      background: "var(--surface)",
      boxShadow: "var(--shadow)"
    });
    [
      ["Bekliyor", "Bekliyor"],
      ["\u0130\u015flemde", "\u0130\u015flemde"],
      ["Tamamland\u0131", "complete"],
      ["\u0130ptal", "cancel"],
      ["Gidildi", "Gidildi"],
      ["Gidilmedi", "Gidilmedi"]
    ].forEach(function (entry) {
      var statusButton = document.createElement("button");
      statusButton.type = "button";
      statusButton.textContent = entry[0];
      statusButton.dataset.contextAction = "appointment-status";
      statusButton.onclick = function () {
        menu.classList.remove("open");
        statusMenu.style.display = "none";
        if (entry[1] === "complete" || entry[1] === "cancel") {
          contextAction("appointment", id, entry[1]);
        } else {
          setAppointmentStatus(id, entry[1]);
        }
      };
      statusMenu.append(statusButton);
    });
    menu.append(statusMenu);
    statusTrigger.onclick = function (event) {
      event.stopPropagation();
      var bounds = statusTrigger.getBoundingClientRect();
      var submenuWidth = 204;
      var left = bounds.right + 5;
      if (left + submenuWidth > window.innerWidth - 8) left = bounds.left - submenuWidth - 5;
      statusMenu.style.left = Math.max(8, left) + "px";
      if (statusMenu.style.display === "none") {
        statusMenu.style.display = "block";
        statusMenu.style.top = Math.max(8, Math.min(bounds.top, window.innerHeight - statusMenu.offsetHeight - 8)) + "px";
        statusTrigger.setAttribute("aria-expanded", "true");
      } else {
        statusMenu.style.display = "none";
        statusTrigger.setAttribute("aria-expanded", "false");
      }
    };

    var separator = document.createElement("hr");
    separator.className = "context-menu-separator";
    menu.append(separator);

    var deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.textContent = "Sil";
    deleteButton.dataset.contextAction = "appointment-delete";
    deleteButton.className = "danger";
    deleteButton.onclick = function () {
      menu.classList.remove("open");
      deleteAppointment(id);
    };
    menu.append(deleteButton);
    menu.style.top = Math.max(8, Math.min(event.clientY, window.innerHeight - menu.offsetHeight - 8)) + "px";
  };

  async function completeAppointmentStatus(id) {
    var appointment = appointmentFor(id);
    if (!appointment) return false;
    var now = new Date();
    var pad = function (value) { return String(value).padStart(2, "0"); };
    var completedAt = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate())
      + " " + pad(now.getHours()) + ":" + pad(now.getMinutes()) + ":" + pad(now.getSeconds());
    try {
      if (Number.isInteger(+appointment.id)) {
        await desktopWrite("appointments", { id: +appointment.id, _action: "update", status: "Tamamland\u0131", completed_at: completedAt });
      }
      appointment.status = "Tamamland\u0131";
      appointment.completed_at = completedAt;
      save();
      toast("Randevu durumu: " + appointment.status);
      render();
      return true;
    } catch (error) {
      toast("Randevu durumu g\u00fcncellenemedi: " + (error.message || ""), "error");
      return false;
    }
  }

  function openAppointmentPayment(id) {
    var appointment = appointmentFor(id);
    var customer = (db.customers || []).find(function (entry) {
      return String(entry.id) === String(appointment && (appointment.customerId || appointment.customer_id) || "")
        || String(entry.name) === String(appointment && (appointment.customer_name || appointment.customer) || "");
    });
    if (!customer) {
      toast("\u00d6deme i\u00e7in randevuya ba\u011fl\u0131 bir m\u00fc\u015fteri se\u00e7ilmelidir.", "warning");
      return;
    }
    var reference = "Montaj tamamland\u0131 | Teklif: " + (appointment.offer_no || "-");
    setTimeout(function () {
      paymentDialog(customer);
      var description = document.querySelector("#dialogBody [name='description']");
      if (description) description.value = reference;
    }, 0);
  }

  contextAction = function (kind, id, action, row) {
    var appointment = kind === "appointment" ? appointmentFor(id) : null;
    if (kind !== "appointment" || !["complete", "cancel"].includes(action)) {
      return baseContextAction(kind, id, action, row);
    }
    var montage = isMontageAppointment(appointment);
    var cancellation = action === "cancel";
    var needsMaterialDecision = montage && (cancellation
      ? remainingVehicleStock(appointment)
      : (appointment.plan_items || []).length > 0);
    if (cancellation && !needsMaterialDecision) return baseContextAction(kind, id, action, row);
    if (!needsMaterialDecision) {
      return completeAppointmentStatus(id).then(function (saved) {
        if (saved && montage) openAppointmentPayment(id);
        return saved;
      });
    }
    return openAppointmentMontageCompletion(id, cancellation, function () {
      if (cancellation) {
        baseContextAction(kind, id, action, row);
        return;
      }
      completeAppointmentStatus(id).then(function (saved) {
        if (saved) openAppointmentPayment(id);
      });
    });
  };

  hydrateDesktop = async function () {
    var result = await baseHydrateDesktop.apply(this, arguments);
    normalizeAppointmentRows();
    return result;
  };

  renderAppointments = function () {
    normalizeAppointmentRows();
    return baseRenderAppointments.apply(this, arguments);
  };

  window.openAppointmentMontagePreparation = openAppointmentMontagePreparation;
  window.openAppointmentMontageCompletion = openAppointmentMontageCompletion;
  window.setAppointmentStatus = setAppointmentStatus;
  normalizeAppointmentRows();
}());
