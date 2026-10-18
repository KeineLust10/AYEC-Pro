(function(){
  let periodKey="month";
  let trendMonths=9;
  let shortcutOverlayOpen=true;
  const statusTiles=[
    ["test","Tamir Edilenler","#05a85b"],
    ["tamirde","Tamirde Olanlar","#f39c12"],
    ["bekliyor","\u0130\u015fleme Al\u0131nacaklar","#1e88e5"],
    ["iptal","\u0130ptal / \u0130ade","#e24a3b"],
    ["kargo","Kargoya Verilenler","#d41462"],
    ["teslim","Teslim Edilenler","#0891b2"],
    ["parca","Par\u00e7a Bekleyenler","#0e7ab4"],
    ["borclu","Bor\u00e7lu Olanlar","#625da8"]
  ];
  const chartPeriods=[["month","Bu Ay"],["today","Bug\u00fcn"],["week","Bu Hafta"],["all","T\u00fcm\u00fc"]];
  const localIsoDate=date=>{const value=new Date(date);if(Number.isNaN(value.getTime()))return"";return`${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,"0")}-${String(value.getDate()).padStart(2,"0")}`};
  const serviceRows=()=>typeof dashboardServices==="function"?dashboardServices():[];
  const serviceKey=service=>typeof serviceStatusKey==="function"?serviceStatusKey(service):"bekliyor";
  const periodMatches=(date,key)=>{
    const day=localIsoDate(date);
    if(!day)return false;
    const now=new Date(),todayKey=localIsoDate(now);
    if(key==="today")return day===todayKey;
    if(key==="month")return day.slice(0,7)===todayKey.slice(0,7);
    if(key==="week"){const first=new Date(now);first.setDate(now.getDate()-((now.getDay()+6)%7));return day>=localIsoDate(first)&&day<=todayKey}
    return true;
  };
  const serviceDate=service=>service.entry_date||service.date||service.created_at||"";
  const periodSelect=(id,value,options)=>`<label class="dashboard-period"><span class="sr-only">Grafik aral\u0131\u011f\u0131</span><select id="${id}" class="control">${options.map(([key,label])=>`<option value="${key}" ${String(key)===String(value)?"selected":""}>${label}</option>`).join("")}</select></label>`;
  const trendPoints=()=>{
    const now=new Date(),points=[];
    for(let offset=trendMonths-1;offset>=0;offset--){
      const date=new Date(now.getFullYear(),now.getMonth()-offset,1),key=localIsoDate(date).slice(0,7);
      const label=date.toLocaleDateString("tr-TR",{month:"short"});
      const amount=serviceRows().filter(row=>serviceDate(row).slice(0,7)===key).reduce((sum,row)=>sum+moneyNumber(row.amount||0)+moneyNumber(row.labor_cost||0),0);
      points.push({key,label,amount});
    }
    return points;
  };
  function renderDashboardParity(){
    const services=serviceRows(),appointments=db.appointments||[],finances=db.finance||[],stock=db.stock||[];
    const todayKey=localIsoDate(new Date()),monthKey=todayKey.slice(0,7),username=$("#currentUserName")?.textContent||"Kullan\u0131c\u0131";
    const countByStatus=Object.fromEntries(statusTiles.map(([key])=>[key,services.filter(row=>key==="borclu"?serviceIsDebt(row):serviceKey(row)===key).length]));
    const todayServices=services.filter(row=>serviceDate(row).slice(0,10)===todayKey).length;
    const openAppointments=appointments.filter(row=>!/(tamam|iptal|cancel|complete)/i.test(String(row.status||""))).length;
    const todayAppointments=appointments.filter(row=>String(row.date||"").slice(0,10)===todayKey).slice().sort((a,b)=>String(a.time||"").localeCompare(String(b.time||"")));
    const completedTodayAppointments=todayAppointments.filter(row=>/(tamam|complete)/i.test(String(row.status||""))).length;
    const todayAppointmentProgress=todayAppointments.length?`Randevular haz\u0131r: ${completedTodayAppointments}/${todayAppointments.length} tamamland\u0131`:'Bug\u00fcn i\u00e7in randevu bulunamad\u0131.';
    const appointmentStatusOptions=["Bekliyor","Geldi","\u0130\u015flemde","Tamamland\u0131","\u0130ptal"];
    const todayAppointmentRows=todayAppointments.length?todayAppointments.map(row=>{
      const id=row.id;
      const status=String(row.status||"Bekliyor");
      const customer=row.customer_name||row.customer||customerName(row.customer_id||row.customerId)||"";
      const details=row.description||"";
      return `<div class="dashboard-today-appointment" data-dashboard-appointment-row="${esc(id)}"><time>${esc(String(row.time||"").slice(0,5))}</time><strong title="${esc(customer)}">${esc(customer)}</strong><span title="${esc(details)}">${esc(details)}</span><div class="dashboard-appointment-status-wrap"><button type="button" class="dashboard-appointment-status" data-dashboard-appointment-status="${esc(id)}" aria-expanded="false">${esc(status.toLocaleUpperCase("tr-TR"))}<span aria-hidden="true">&#9662;</span></button><div class="dashboard-appointment-menu" data-dashboard-appointment-menu hidden>${appointmentStatusOptions.map(option=>`<button type="button" data-dashboard-appointment-set="${esc(id)}" data-status="${esc(option)}">${esc(option)}</button>`).join("")}</div></div></div>`;
    }).join(""):'<div class="dashboard-empty">Bug\u00fcn i\u00e7in randevu bulunamad\u0131.</div>';
    const pendingServices=countByStatus.bekliyor+countByStatus.parca;
    const serviceRevenue=services.filter(row=>serviceDate(row).slice(0,7)===monthKey).reduce((sum,row)=>sum+moneyNumber(row.amount||0)+moneyNumber(row.labor_cost||0),0);
    const fallbackRevenue=finances.filter(row=>row.type==="Gelir"&&String(row.date||"").slice(0,7)===monthKey).reduce((sum,row)=>sum+moneyNumber(row.amount),0);
    const monthlyRevenue=serviceRevenue||fallbackRevenue;
    const criticalStock=stock.filter(row=>Number(row.qty||0)<=Number(row.min||0)).length;
    const keyForDonut=periodKey;
    const visibleServices=services.filter(row=>periodMatches(serviceDate(row),keyForDonut));
    const donutCounts=Object.fromEntries(statusTiles.map(([key])=>[key,visibleServices.filter(row=>key==="borclu"?serviceIsDebt(row):serviceKey(row)===key).length]));
    const donutTotal=statusTiles.reduce((sum,[key])=>sum+donutCounts[key],0);
    let degrees=0;
    const donutSegments=statusTiles.map(([key,label,color])=>{const value=donutCounts[key],slice=donutTotal?value/donutTotal*360:0,start=degrees;degrees+=slice;return`${color} ${start}deg ${degrees}deg`}).join(", ");
    const points=trendPoints(),maxTrend=Math.max(1,...points.map(point=>point.amount));
    const recent=services.slice().sort((a,b)=>serviceDate(b).localeCompare(serviceDate(a))).slice(0,5);
    const activities=(db.activities||[]).slice(0,5);
    const periods=chartPeriods;
    const metrics=[
      ["Bug\u00fcnk\u00fc Servisler",todayServices,"Bug\u00fcn i\u015flem al\u0131nan","#1e88e5","\u25a6"],
      ["A\u00e7\u0131k Randevular",openAppointments,"Bekleyen randevu","#7c3aed","\u25a4"],
      ["Bekleyen \u0130\u015fler",pendingServices,"Onay / i\u015flem bekliyor","#f59e0b","\u231b"],
      ["Gelir",money(monthlyRevenue),"Bu ayki servis geliri","#16a34a","\u25ce"]
    ];
    const now=new Date(),dateText=now.toLocaleDateString("tr-TR",{weekday:"long",day:"numeric",month:"long",year:"numeric"});
    const tickerDefault=currentSector==="otomotiv"?"AYEC Pro Otomotiv Servis Y\u00f6netimi v2026.1 | H\u0131zl\u0131 Kay\u0131t: F5 | Ara\u00e7 Bul: Ctrl+F":"AYEC Pro Teknik Servis Y\u00f6netimi v2026.1 | H\u0131zl\u0131 Kay\u0131t: F5 | M\u00fc\u015fteri Ara: Ctrl+F";
    const tickerText=esc(db.settings?.ticker_text||tickerDefault);
    const topActions='<button class="secondary" data-dashboard-shortcuts-toggle>K\u0131sayollar</button><button class="secondary" data-page="finance">Finans</button><button class="secondary" data-page="appointments">Randevular</button><button class="secondary" data-action="export-all">D\u0131\u015fa Aktar</button><button class="primary" data-action="quick-add">&#65291; Yeni \u0130\u015flem</button>';
    const deviceTitle=currentSector==="otomotiv"?"Ara\u00e7 Kayd\u0131":"Cihaz Kayd\u0131";
    const deviceDetail=currentSector==="otomotiv"?"Yeni ara\u00e7 servis kayd\u0131":"Yeni cihaz servis kayd\u0131";
    const shortcutItems=[
      ["Yeni Servis Formu","Servis kayd\u0131 a\u00e7","new-service","#2563eb","service"],
      ["M\u00fc\u015fteri Ekle","Yeni m\u00fc\u015fteri kayd\u0131","new-customer","#059669","customer"],
      [deviceTitle,deviceDetail,currentSector==="otomotiv"?"vehicle-record":"new-service","#d97706","device"],
      ["Servis Listesi","A\u00e7\u0131k servisleri g\u00f6r","services","#0891b2","list"],
      ["Teknisyen Paneli","Par\u00e7a ve i\u015flem ekle","technician","#7c3aed","tools"],
      ["M\u00fc\u015fteriler","M\u00fc\u015fteri 360 ekran\u0131","customers","#db2777","customers"],
      ["Finans","Gelir ve giderleri g\u00f6r","finance","#16a34a","finance"],
      ["Stok Y\u00f6netimi","Par\u00e7a stoklar\u0131n\u0131 y\u00f6net","stock","#ea580c","stock"],
      ["Randevular","Bekleyen randevular\u0131 g\u00f6r","appointments","#9333ea","calendar"],
      ["Teklifler","Teklif olu\u015ftur ve takip et","offers","#0f766e","quote"],
      ["Gelir / Gider","Finans hareketlerini incele","finance","#65a30d","report"],
      ["Yedekleme","Verilerinizi g\u00fcvenle yedekleyin","backup","#475569","backup"]
    ];
    const shortcutIconPaths={service:'<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v5h5M8 13h8M8 17h5"/>',customer:'<circle cx="12" cy="8" r="3"/><path d="M5 21c.7-3.4 3.1-5 7-5s6.3 1.6 7 5"/>',device:'<rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8M12 17v4"/>',list:'<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M8 9h8M8 13h8M8 17h5"/>',tools:'<path d="M14 6a4 4 0 0 0-5 5l-6 6 3 3 6-6a4 4 0 0 0 5-5l-3 3-3-3z"/>',customers:'<circle cx="9" cy="8" r="3"/><circle cx="16" cy="10" r="2"/><path d="M3 21c.5-4 2.5-6 6-6s5.5 2 6 6M15 15c3 0 5 2 6 6"/>',finance:'<rect x="3" y="6" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h3"/>',stock:'<path d="M4 9h16v11H4zM7 9V5h10v4M8 13h8"/>',calendar:'<rect x="4" y="5" width="16" height="15" rx="2"/><path d="M8 3v4M16 3v4M4 10h16M8 14h3"/>',quote:'<path d="M6 3h9l3 3v15H6zM15 3v4h4M9 12h6M9 16h5"/>',report:'<path d="M5 20V10M12 20V4M19 20v-7"/>',backup:'<path d="M5 4h14v16H5zM8 4v5h8V4M9 16h6"/>'};
    const shortcutCardMarkup=([title,detail,target,color,icon])=>'<button type="button" class="dashboard-shortcut-card" data-dashboard-shortcut="'+target+'" style="--shortcut-accent:'+color+'"><svg viewBox="0 0 24 24" aria-hidden="true"><g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+shortcutIconPaths[icon]+'</g></svg><div><strong>'+title+'</strong><span>'+detail+'</span></div></button>';
    const shortcutOverlay=shortcutOverlayOpen?`<section class="dashboard-shortcut-overlay" role="dialog" aria-modal="true" aria-labelledby="dashboardShortcutTitle"><header><div><h2 id="dashboardShortcutTitle">AYEC Pro K\u0131sayollar</h2><p>Men\u00fclere ve formlara tek t\u0131klamayla eri\u015fin. Genel Bak\u0131\u015f ekran\u0131na d\u00f6nmek i\u00e7in kapat\u0131n.</p></div><button type="button" class="secondary" data-dashboard-shortcuts-close aria-label="K\u0131sayollar\u0131 kapat">Kapat</button></header><div class="dashboard-shortcut-grid">${shortcutItems.map(shortcutCardMarkup).join("")}</div></section>`:"";
    const statusMarkup=statusTiles.map(([key,label,color])=>`<button type="button" class="dashboard-status-tile" data-dashboard-parity-filter="${key}" style="--dashboard-accent:${color}" aria-label="${label}: ${countByStatus[key]}"><span class="dashboard-status-dot"></span><span class="dashboard-status-label">${label}</span><strong>${countByStatus[key]}</strong></button>`).join("");
    const metricMarkup=metrics.map(([label,value,description,color,icon])=>`<article class="dashboard-metric-card" style="--dashboard-accent:${color}"><span class="dashboard-metric-icon" aria-hidden="true">${icon}</span><div><small>${label}</small><strong>${value}</strong><span>${description}</span></div></article>`).join("");
    const donutMarkup=statusTiles.map(([key,label,color])=>`<button type="button" class="dashboard-legend-row" data-dashboard-parity-filter="${key}" style="--dashboard-accent:${color}"><span class="dashboard-legend-dot"></span><span>${label}</span><strong>${donutCounts[key]}</strong></button>`).join("");
    const trendMarkup=points.map(point=>`<div class="dashboard-trend-column" title="${point.label}: ${money(point.amount)}"><span style="--dashboard-bar-height:${Math.max(4,point.amount/maxTrend*100)}%"></span><small>${point.label}</small></div>`).join("");
    const recentRows=recent.length?recent.map(row=>`<button type="button" class="dashboard-recent-row" data-action="service-detail" data-id="${esc(row.no||row.id||"")}" data-customer="${esc(row.customerId||"")}"><span class="dashboard-recent-mark">${esc(String(row.status||"S").slice(0,1))}</span><span><strong>${esc(row.customer||customerName(row.customerId)||"\u0130simsiz kay\u0131t")}</strong><small>${esc(row.device_type||row.device||row.service||"Servis i\u015flemi")} &middot; ${esc(serviceDate(row)||"")}</small></span><b>${esc(row.status||"Bekliyor")}</b></button>`).join(""):activities.map(row=>`<div class="dashboard-recent-row"><span class="dashboard-recent-mark">${esc(row.icon||"\u2022")}</span><span><strong>${esc(row.text||"\u0130\u015flem kayd\u0131")}</strong><small>${esc(row.date||"")}</small></span></div>`).join("")||'<div class="dashboard-empty">Hen\u00fcz i\u015flem kayd\u0131 yok.</div>';
    return `
      <div class="dashboard-ticker" role="status"><div class="dashboard-ticker-track"><span>${tickerText}</span><span aria-hidden="true">${tickerText}</span></div></div>
      <section class="dashboard-welcome">
        <div class="dashboard-welcome-copy">
          <p class="dashboard-eyebrow">AYEC PRO &middot; MIDNIGHT ENTERPRISE</p>
          <h2>Ho\u015f Geldiniz, ${esc(username)}! <span aria-hidden="true">&#128075;</span></h2>
          <p>Servis s\u00fcre\u00e7lerinizin genel durumunu buradan takip edebilirsiniz.</p>
          <blockquote>\u201cDaha h\u0131zl\u0131 servis, daha mutlu m\u00fc\u015fteriler.\u201d <span>&mdash; AYEC Pro</span></blockquote>
        </div>
        <div class="dashboard-welcome-side">
          <time datetime="${todayKey}" class="dashboard-date">${dateText}<strong>${now.toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"})}</strong></time>
          <div class="dashboard-welcome-actions">${topActions}</div>
        </div>
      </section>
      <section class="dashboard-status-grid" aria-label="Servis durumlar\u0131">${statusMarkup}</section>
      <section class="dashboard-metric-grid" aria-label="\u00d6zet g\u00f6stergeler">${metricMarkup}</section>
      <section class="dashboard-chart-grid">
        <article class="dashboard-panel">
          <header><h3>Servis Durum Da\u011f\u0131l\u0131m\u0131</h3>${periodSelect("dashboardParityStatusPeriod",periodKey,periods)}</header>
          <div class="dashboard-donut-layout"><div class="dashboard-donut" style="--dashboard-donut:${donutSegments||"#1b2a42 0deg 360deg"}"><strong>${donutTotal}</strong><small>Kay\u0131t</small></div><div class="dashboard-legend">${donutMarkup}</div></div>
        </article>
        <article class="dashboard-panel">
          <header><h3>Ayl\u0131k Servis Trendi</h3>${periodSelect("dashboardParityTrendMonths",trendMonths,[[6,"Son 6 Ay"],[9,"Son 9 Ay"],[12,"Son 12 Ay"]])}</header>
          <div class="dashboard-trend">${trendMarkup}</div>
        </article>
        <article class="dashboard-panel dashboard-recent-panel">
          <header><h3>Son \u0130\u015flemler</h3><button type="button" class="mini" data-page="services">T\u00fcm\u00fcn\u00fc G\u00f6r &rsaquo;</button></header>
          <div class="dashboard-recent-list">${recentRows}</div>
        </article>
      </section>
      <section class="dashboard-panel dashboard-today-appointments-panel"><header><h3>Bug\u00fcn\u00fcn Randevular\u0131</h3><span class="dashboard-today-appointment-progress">${todayAppointmentProgress}</span></header><div class="dashboard-today-appointment-list">${todayAppointmentRows}</div></section>
      <section class="dashboard-footnote"><span>Bekleyen stok uyar\u0131s\u0131: <strong>${criticalStock}</strong></span><span>Yakla\u015fan randevu: <strong>${appointments.filter(row=>periodMatches(row.date,"week")).length}</strong></span></section>
      <footer class="dashboard-bottom-status"><strong>${now.toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}</strong><span>${dateText}</span></footer>${shortcutOverlay}`;
  }
  renderDashboard=renderDashboardParity;
  window.toggleDesktopDashboardShortcuts=()=>{
    shortcutOverlayOpen=!shortcutOverlayOpen;
    if(page==="dashboard")render();
    return shortcutOverlayOpen;
  };
  document.addEventListener("change",event=>{
    if(event.target.id==="dashboardParityStatusPeriod"){periodKey=event.target.value;render()}
    if(event.target.id==="dashboardParityTrendMonths"){trendMonths=Number(event.target.value)||9;render()}
  });
  document.addEventListener("click",event=>{
    if(event.target.closest("[data-dashboard-shortcuts-toggle]")){shortcutOverlayOpen=true;render();return;}
    if(event.target.closest("[data-dashboard-shortcuts-close]")){shortcutOverlayOpen=false;render();return;}
    const shortcut=event.target.closest("[data-dashboard-shortcut]");
    if(shortcut){
      const target=shortcut.dataset.dashboardShortcut;
      shortcutOverlayOpen=false;
      render();
      if(target==="new-service"){if(currentSector==="otomotiv"){navigate("vehicle-maintenance");window.setTimeout(()=>maintenanceDialog(),80)}else if(typeof serviceDialog==="function")serviceDialog();else document.querySelector('#content [data-action="quick-add"]')?.click();return;}
      if(target==="new-customer"){openDialog("Yeni M\u00fc\u015fteri","CRM",customerForm(),form=>saveCustomer(form),"M\u00fc\u015fteri Ekle");return;}
      if(target==="vehicle-record"){if(typeof window.openAutomotiveVehicleShortcut==="function")window.openAutomotiveVehicleShortcut();else toast("Arac kaydi akisi yuklenemedi.","error");return;}
      navigate(target);
      return;
    }
    const statusButton=event.target.closest("[data-dashboard-appointment-status]");
    if(statusButton){
      const menu=statusButton.parentElement.querySelector("[data-dashboard-appointment-menu]");
      const open=statusButton.getAttribute("aria-expanded")==="true";
      statusButton.setAttribute("aria-expanded",String(!open));
      if(menu)menu.hidden=open;
      return;
    }
    const statusOption=event.target.closest("[data-dashboard-appointment-set]");
    if(statusOption){updateDashboardAppointmentStatus(statusOption.dataset.dashboardAppointmentSet,statusOption.dataset.status);return;}
    const filter=event.target.closest("[data-dashboard-parity-filter]");
    if(filter){dashboardFilter=filter.dataset.dashboardParityFilter;navigate("service-status");return}
  });
  async function updateDashboardAppointmentStatus(id,status){
    if(!id||!status)return;
    try{
      await apiFetch("/api/desktop/table/appointments",{method:"POST",body:JSON.stringify({id:Number(id),_action:"update",status})});
      const appointment=(db.appointments||[]).find(row=>String(row.id)===String(id));
      if(appointment)appointment.status=status;
      render();
    }catch(error){toast("Randevu durumu g\u00fcncellenemedi: "+(error.message||""),"error");}
  }
  if(typeof render==="function")render();
})();
