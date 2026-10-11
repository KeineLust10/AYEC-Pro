(function(){
  let periodKey="month";
  let trendMonths=9;
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
    const topActions='<button class="secondary" data-page="finance">Finans</button><button class="secondary" data-page="appointments">Randevular</button><button class="secondary" data-action="export-all">D\u0131\u015fa Aktar</button><button class="primary" data-action="quick-add">&#65291; Yeni \u0130\u015flem</button>';
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
      <section class="dashboard-footnote"><span>Bekleyen stok uyar\u0131s\u0131: <strong>${criticalStock}</strong></span><span>Yakla\u015fan randevu: <strong>${appointments.filter(row=>periodMatches(row.date,"week")).length}</strong></span></section>
      <footer class="dashboard-bottom-status"><strong>${now.toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit",second:"2-digit"})}</strong><span>${dateText}</span></footer>`;
  }
  renderDashboard=renderDashboardParity;
  document.addEventListener("change",event=>{
    if(event.target.id==="dashboardParityStatusPeriod"){periodKey=event.target.value;render()}
    if(event.target.id==="dashboardParityTrendMonths"){trendMonths=Number(event.target.value)||9;render()}
  });
  document.addEventListener("click",event=>{
    const filter=event.target.closest("[data-dashboard-parity-filter]");
    if(filter){dashboardFilter=filter.dataset.dashboardParityFilter;navigate("service-status");return}
  });
  if(typeof render==="function")render();
})();
