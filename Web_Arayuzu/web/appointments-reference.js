"use strict";
let ayecAppointmentView = "week";
let ayecAppointmentTechnician = "all";
let ayecAppointmentLocation = "all";
let ayecAppointmentPersonnelRows = null;
let ayecAppointmentPersonnelPromise = null;
function apDate(d){return d.getFullYear()+"-"+String(d.getMonth()+1).padStart(2,"0")+"-"+String(d.getDate()).padStart(2,"0")}
function apAppointmentStatusKey(value){return String(value||"").trim().toLocaleLowerCase("tr-TR").replace(/\u0131/g,"i").normalize("NFD").replace(/[\u0300-\u036f]/g,"")}
function apAppointmentClosed(value){const status=apAppointmentStatusKey(value);return status.startsWith("tamam")||status.startsWith("iptal")||["completed","canceled","cancelled"].includes(status)}
function apDateKey(value){const text=String(value||"").slice(0,10);let match=text.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(match)return match[1]+"-"+match[2]+"-"+match[3];match=text.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})$/);return match?match[3]+"-"+match[2].padStart(2,"0")+"-"+match[1].padStart(2,"0"):""}
function apWeek(offset){const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()-((d.getDay()+6)%7)+offset*7);return Array.from({length:7},(_,i)=>{const x=new Date(d);x.setDate(x.getDate()+i);return x})}
function apMatch(a){const locations=(a.plan_items||[]).map(item=>String(item.source_location_id||""));return (ayecAppointmentTechnician==="all"||String(a.technician||a.technician_name||"")===ayecAppointmentTechnician)&&(ayecAppointmentLocation==="all"||locations.includes(ayecAppointmentLocation)||String(a.location||a.location_id||a.location_name||a.source_location_name||"")===ayecAppointmentLocation)}
function apLoadPersonnelDirectory(){if(ayecAppointmentPersonnelRows!==null||ayecAppointmentPersonnelPromise)return;ayecAppointmentPersonnelPromise=apiFetch("/api/desktop/table/personnel?limit=1000&include_deleted=1").then(function(result){ayecAppointmentPersonnelRows=result.rows||[];if(document.body.dataset.page==="appointments")render()}).catch(function(){ayecAppointmentPersonnelRows=Array.isArray(db.personnel)?db.personnel:[]}).finally(function(){ayecAppointmentPersonnelPromise=null})}
function apEvent(a){var technician=a.technician||a.technician_name||"";return '<article class="appointment-ref-event'+(technician?'':' unassigned')+'" data-kind="appointment" data-id="'+esc(a.id)+'" draggable="true"><header><b>'+esc(a.customer||customerName(a.customerId))+'</b><span>'+esc(a.status||"Planland\u0131")+'</span></header><strong>'+esc(a.title||a.description||"Randevu")+'</strong><small>'+esc(a.location||a.address||"")+'</small><footer><span>'+esc(technician||"Teknisyen atanmad\u0131")+'</span><time>'+esc(a.time||"09:00")+'</time></footer></article>'}
function apSideEvent(a){var event=apEvent(a),status=String(a.status||"").toLocaleLowerCase("tr-TR"),actions=[];if(!status.startsWith("tamam")&&!status.startsWith("iptal")){if(status==="bekliyor"){actions.push(["Yola \u00c7\u0131k\u0131ld\u0131","Gidildi"],["Gidilmedi","Gidilmedi"],["\u0130\u015flemde","\u0130\u015flemde"])}else if(status==="gidildi"){actions.push(["\u0130\u015flemde","\u0130\u015flemde"])}actions.push(["Tamamland\u0131","complete"],["\u0130ptal","cancel"],["Detay G\u00f6r","edit"])}var buttons=actions.map(function(item){return '<button type="button" data-appointment-outcome="'+esc(item[1])+'" data-id="'+esc(a.id)+'">'+item[0]+'</button>'}).join("");return event.replace('</article>',(buttons?'<div class="appointment-ref-side-actions">'+buttons+'</div>':"")+'</article>')}
apSideEvent=function(a){
 const status=String(a.status||"").toLocaleLowerCase("tr-TR");
 const statusLabels={planlandi:"Planland\u0131",bekliyor:"Bekliyor",gidildi:"Geldi",gidilmedi:"Gelmedi","i\u015flemde":"\u0130\u015flemde",tamamland\u0131:"Tamamland\u0131",iptal:"\u0130ptal"};
 const displayStatus=statusLabels[status]||String(a.status||"Bekliyor");
 const actions=[];
 if(!status.startsWith("tamam")&&!status.startsWith("iptal")){
  if(status==="bekliyor")actions.push([["Yola \u00c7\u0131k\u0131ld\u0131","Gidildi"],["Gidilmedi","Gidilmedi"],["\u0130\u015flemde","\u0130\u015flemde"]]);
  else if(status==="gidildi")actions.push([["\u0130\u015flemde","\u0130\u015flemde"]]);
  actions.push([["Tamamland\u0131","complete"],["\u0130ptal","cancel"],["Detay G\u00f6r","edit"]]);
 }
 const actionRows=actions.map(row=>'<div class="appointment-ref-side-action-row">'+row.map(([label,action])=>'<button type="button" data-appointment-outcome="'+esc(action)+'" data-id="'+esc(a.id)+'">'+label+'</button>').join("")+'</div>').join("");
 const time='<time>'+esc(a.time||"09:00")+'</time>';
 const badge='<span class="appointment-ref-side-status">'+esc(displayStatus)+'</span>';
 const customer='<strong>'+esc(a.customer||customerName(a.customerId)||"-")+'</strong>';
 const description=String(a.title||a.description||a.fault||"").split(" - ")[0];
 const detail=description?'<p>'+esc(description)+'</p>':"";
 const metadata=[];
 if(a.location||a.address)metadata.push("\u2302 "+String(a.location||a.address));
 if(a.technician||a.technician_name)metadata.push("\u2659 Teknisyen: "+String(a.technician||a.technician_name));
 const meta=metadata.length?'<small class="appointment-ref-side-meta">'+metadata.map(esc).join("<br>")+'</small>':"";
 return '<article class="appointment-ref-event appointment-ref-side-event" data-kind="appointment" data-id="'+esc(a.id)+'" tabindex="0"><header>'+time+badge+'</header>'+customer+detail+meta+'<div class="appointment-ref-side-actions">'+actionRows+'</div></article>';
};
function renderAppointments(){
 apLoadPersonnelDirectory();
 const weekDays=apWeek(appointmentWeekOffset),today=apDate(new Date()),days=ayecAppointmentView==="day"?[new Date()]:weekDays,personnelRows=ayecAppointmentPersonnelRows||db.personnel||[],namedPersonnel=personnelRows.filter(person=>String(person.name||"").trim()),activePersonnel=namedPersonnel.filter(person=>Number(person.active??1)!==0).sort((a,b)=>String(a.name||"").localeCompare(String(b.name||""),"tr-TR")),techs=[...new Set(activePersonnel.map(person=>String(person.name).trim()))],locations=db.stockLocations||[];
 const todayRows=db.appointments.filter(a=>apDateKey(a.date)===today&&apMatch(a)),weekRows=db.appointments.filter(a=>weekDays.some(d=>apDate(d)===apDateKey(a.date))&&apMatch(a));
 const hours=Array.from({length:11},(_,i)=>String(i+9).padStart(2,"0")+":00");
 const head='<div class="appointment-ref-grid-head"><b>Saat</b>'+days.map(d=>'<b class="'+(apDate(d)===today?"today":"")+'"><span>'+d.toLocaleDateString("tr-TR",{weekday:"short"})+'</span><small>'+d.toLocaleDateString("tr-TR",{day:"2-digit",month:"2-digit",year:"numeric"})+'</small></b>').join("")+'</div>';
 const rows=hours.map(hour=>'<div class="appointment-ref-hour">'+hour+'</div>'+days.map(d=>'<div class="appointment-ref-slot" data-date="'+apDate(d)+'" data-time="'+hour+'" title="Randevu eklemek icin \u00e7ift t\u0131klay\u0131n">'+db.appointments.filter(a=>apDateKey(a.date)===apDate(d)&&String(a.time||"09:00").slice(0,2)===hour.slice(0,2)&&apMatch(a)).map(apEvent).join("")+'</div>').join("")).join("");
 const monthStart=new Date(weekDays[0].getFullYear(),weekDays[0].getMonth(),1);monthStart.setDate(monthStart.getDate()-((monthStart.getDay()+6)%7));
 const monthCells=Array.from({length:42},(_,i)=>{const d=new Date(monthStart);d.setDate(monthStart.getDate()+i);const items=db.appointments.filter(a=>apDateKey(a.date)===apDate(d)&&apMatch(a));return '<div class="appointment-ref-month-day '+(d.getMonth()===weekDays[0].getMonth()?"":"outside")+(apDate(d)===today?" today":"")+'"><b>'+d.getDate()+'</b>'+items.slice(0,2).map(a=>'<button type="button" data-kind="appointment" data-id="'+esc(a.id)+'">'+esc(a.time||"")+' '+esc(a.title||customerName(a.customerId))+'</button>').join("")+(items.length>2?'<small>+'+(items.length-2)+' kayıt</small>':"")+'</div>';}).join("");
 const month='<div class="appointment-ref-month"><div class="appointment-ref-month-head">'+["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"].map(x=>'<b>'+x+'</b>').join("")+'</div><div class="appointment-ref-month-grid">'+monthCells+'</div></div>';
 const calendar=ayecAppointmentView==="month"?month:'<div class="appointment-ref-calendar'+(ayecAppointmentView==="week"?' week-view':'')+'" style="--appointment-days:'+days.length+'">'+head+rows+'</div>';
 const views=[["day","G\u00fcnl\u00fck"],["week","Haftal\u0131k"],["month","Ayl\u0131k"],["technician","Teknisyen"]].map(([id,label])=>'<button type="button" data-appointment-view="'+id+'" aria-selected="'+(ayecAppointmentView===id)+'">'+label+'</button>').join("");
 const list=todayRows.length?todayRows.sort((a,b)=>String(a.time||"").localeCompare(String(b.time||""))).map(apSideEvent).join(""):'<p class="muted">Bug\u00fcn i\u00e7in kay\u0131tl\u0131<br>randevu bulunamad\u0131.</p>';
 const techRows=activePersonnel.filter((person,index)=>activePersonnel.findIndex(item=>String(item.name||"").trim()===String(person.name||"").trim())===index).slice(0,3).map(person=>{const name=String(person.name||"").trim(),role=person.role||"Teknisyen",count=db.appointments.filter(a=>(a.technician||a.technician_name)===name&&apDateKey(a.date)>=today).length;return '<div class="appointment-ref-tech-row"><div><b>'+esc(name)+'</b><small>'+esc(role)+'</small></div><span>'+count+' G\u00f6rev</span><strong>Aktif</strong></div>'}).join("");
 const period=ayecAppointmentView==="day"?days[0].toLocaleDateString("tr-TR",{weekday:"long",day:"numeric",month:"long",year:"numeric"}):ayecAppointmentView==="month"?weekDays[0].toLocaleDateString("tr-TR",{month:"long",year:"numeric"}):weekDays[0].toLocaleDateString("tr-TR",{day:"2-digit",month:"2-digit",year:"numeric"})+" - "+weekDays[6].toLocaleDateString("tr-TR",{day:"2-digit",month:"2-digit",year:"numeric"});
 const techOptions=techs.map(name=>'<option value="'+esc(name)+'" '+(name===ayecAppointmentTechnician?"selected":"")+'>'+esc(name)+'</option>').join("");
 const locationOptions=locations.map(location=>{const name=location.name||location.location_name||("Location "+location.id),label=location.vehicle_plate?name+" ("+location.vehicle_plate+")":name;return '<option value="'+esc(String(location.id))+'" '+(String(location.id)===ayecAppointmentLocation?"selected":"")+'>'+esc(label)+'</option>'}).join("");
 const done=weekRows.filter(a=>String(a.status||"").toLocaleLowerCase("tr-TR").startsWith("tamam")).length;
 const metric='<div class="appointment-ref-metrics"><article><small>Bug\u00fcn Planlanan</small><b>'+todayRows.length+' Randevu</b></article><article><small>Saha Ekipleri</small><b>'+new Set(weekRows.map(a=>a.technician||a.technician_name).filter(Boolean)).size+' G\u00f6revli</b></article><article><small>Haftal\u0131k Tamamlanma</small><b>%'+(weekRows.length?Math.round(done/weekRows.length*100):0)+'</b></article><article><small>Acil SLA Bildirimi</small><b>'+weekRows.filter(a=>["acil","kritik"].includes(String(a.urgency||a.priority||"").toLocaleLowerCase("tr-TR"))).length+' Servis</b></article></div>';
 const techPanel=techRows||'<p>Aktif teknisyen kayd\u0131 bulunamad\u0131.</p>',activeTechnicianCount=activePersonnel.length,totalTechnicianCount=namedPersonnel.length;
 const main=ayecAppointmentView==="technician"?'<section class="appointment-ref-tech-list">'+techPanel+'</section>':calendar;
 return '<section class="appointment-ref-page">'+pageHead("Randevu Merkezi","Randevu planlamas\u0131n\u0131 ve saha ekiplerinin g\u00fcnl\u00fck i\u015f ak\u0131\u015f\u0131n\u0131 y\u00f6netin.",'<button class="primary" data-action="add-appointment">+ Yeni Randevu</button>')+'<div class="appointment-ref-toolbar"><div class="appointment-ref-period"><button data-appointment-shift="-1" aria-label="\u00d6nceki">&#8249;</button><button data-appointment-today>Bug\u00fcn</button><strong>'+period+'</strong><button data-appointment-shift="1" aria-label="Sonraki">&#8250;</button></div><div class="appointment-ref-views" role="tablist">'+views+'</div><label>Teknisyen<select id="appointmentTechnician"><option value="all">T\u00fcm Teknisyenler ('+techs.length+')</option>'+techOptions+'</select></label><label>Lokasyon<select id="appointmentLocation"><option value="all">T\u00fcm Lokasyonlar ('+locations.length+')</option>'+locationOptions+'</select></label><button class="secondary" data-appointment-planned>Planlanan Liste '+weekRows.length+'</button></div>'+metric+'<div class="appointment-ref-layout"><main>'+main+'<footer class="appointment-ref-legend"><span>Saha Randevusu</span><span>At\u00f6lye Kabul\u00fc</span><span>Kritik SLA / Acil</span><small>Saat dilimi: UTC+03:00 (\u0130stanbul)</small></footer></main><aside><section class="card"><header><h2>Bug\u00fcn\u00fcn \u0130\u015flemleri</h2><b>'+todayRows.length+' Randevu</b></header><div class="appointment-ref-side-list">'+list+'</div></section><section class="card"><div class="appointment-ref-tech-status"><header><h2>Teknisyen Durumu</h2><b>'+activeTechnicianCount+'/'+totalTechnicianCount+' Aktif</b></header><div class="appointment-ref-tech-list">'+techPanel+'</div><button data-page="field-service">Canl\u0131 Saha Haritas\u0131n\u0131 A\u00e7</button></div></section></aside></div></section>'
}
document.addEventListener("click",e=>{const v=e.target.closest("[data-appointment-view]");if(v){ayecAppointmentView=v.dataset.appointmentView;render();return}const s=e.target.closest("[data-appointment-shift]");if(s){appointmentWeekOffset+=Number(s.dataset.appointmentShift);render();return}if(e.target.closest("[data-appointment-today]")){appointmentWeekOffset=0;ayecAppointmentView="day";render();return}if(e.target.closest("[data-appointment-planned]")){const rows=db.appointments.filter(a=>weekDaysForPlanned(a.date,appointmentWeekOffset)&&!apAppointmentClosed(a.status)).sort((a,b)=>(apDateKey(a.date)+" "+(a.time||"")).localeCompare(apDateKey(b.date)+" "+(b.time||"")));openDialog("Planlanan Randevular","BU HAFTA",'<div class="planned-appointments">'+(rows.map(a=>'<article><strong>'+esc(apDateKey(a.date))+' '+esc(a.time||"--:--")+'</strong><span>'+esc(a.customer||customerName(a.customerId)||"-")+'</span><span>'+esc(a.title||a.description||"")+'</span><span>'+esc(a.status||"Planland\u0131")+'</span></article>').join("")||'<p class="muted">Bu hafta planlanan randevu bulunmuyor.</p>')+'</div>',function(){return true},"Kapat")}});
document.addEventListener("click",e=>{const button=e.target.closest("[data-appointment-outcome]");if(!button)return;const id=button.dataset.id,action=button.dataset.appointmentOutcome;if(action==="edit"){appointmentDialog(db.appointments.find(a=>String(a.id)===String(id)));return}if(action==="complete"||action==="cancel"){contextAction("appointment",id,action);return}if(window.setAppointmentStatus)window.setAppointmentStatus(id,action)});
document.addEventListener("change",e=>{if(e.target.id==="appointmentTechnician"){ayecAppointmentTechnician=e.target.value;render()}if(e.target.id==="appointmentLocation"){ayecAppointmentLocation=e.target.value;render()}});
document.addEventListener("dblclick",e=>{const sideCard=e.target.closest(".appointment-ref-side-event[data-kind='appointment']");if(sideCard){if(e.target.closest("button,a,input,select,textarea"))return;const item=db.appointments.find(a=>String(a.id)===String(sideCard.dataset.id));if(!item)return;e.preventDefault();e.stopPropagation();appointmentDialog(item);return}const slot=e.target.closest(".appointment-ref-slot");if(!slot||e.target.closest("[data-kind='appointment']"))return;appointmentDialog(null,{date:slot.dataset.date,time:slot.dataset.time})});
let ayecDraggedAppointmentId="";
document.addEventListener("dragstart",e=>{const card=e.target.closest(".appointment-ref-event");if(!card||!e.dataTransfer)return;ayecDraggedAppointmentId=card.dataset.id;e.dataTransfer.setData("text/plain",ayecDraggedAppointmentId);e.dataTransfer.effectAllowed="move";card.classList.add("dragging")});
document.addEventListener("dragend",e=>{e.target.closest(".appointment-ref-event")?.classList.remove("dragging");document.querySelectorAll(".appointment-ref-slot.drop-target").forEach(slot=>slot.classList.remove("drop-target"));ayecDraggedAppointmentId=""});
document.addEventListener("dragover",e=>{const slot=e.target.closest(".appointment-ref-slot");if(!slot)return;e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect="move";slot.classList.add("drop-target")});
document.addEventListener("dragleave",e=>{const slot=e.target.closest(".appointment-ref-slot");if(slot&&!slot.contains(e.relatedTarget))slot.classList.remove("drop-target")});
document.addEventListener("drop",async e=>{const slot=e.target.closest(".appointment-ref-slot");if(!slot)return;e.preventDefault();document.querySelectorAll(".appointment-ref-slot.drop-target").forEach(item=>item.classList.remove("drop-target"));const id=e.dataTransfer?.getData("text/plain")||ayecDraggedAppointmentId,item=db.appointments.find(row=>String(row.id)===String(id));if(!item)return;const previous={date:item.date,time:item.time};item.date=slot.dataset.date;item.time=slot.dataset.time;try{if(Number.isInteger(+item.id))await desktopWrite("appointments",{id:+item.id,_action:"update",date:item.date,time:item.time});save();render();activity("Randevu yeni saatine ta\u015f\u0131nd\u0131","\u25a3");toast("Randevu yeni saatine ta\u015f\u0131nd\u0131")}catch(error){item.date=previous.date;item.time=previous.time;render();toast(error.message||"Randevu ta\u015f\u0131namad\u0131","error")}});
const apRenderAppointmentsBeforeDesktopAlignment=renderAppointments;
renderAppointments=function(){
 const source=apRenderAppointmentsBeforeDesktopAlignment();
 const template=document.createElement("template");
 template.innerHTML=source;
 const root=template.content.querySelector(".appointment-ref-page");
 const toolbar=root?.querySelector(".appointment-ref-toolbar");
 if(!root||!toolbar)return source;
 const pageHeader=root.querySelector(".page-head");
 const addButton=pageHeader?.querySelector('[data-action="add-appointment"]');
 pageHeader?.remove();
 const period=toolbar.querySelector(".appointment-ref-period");
 const controls=Array.from(period?.querySelectorAll("button")||[]);
 const periodLabel=period?.querySelector("strong")?.textContent||"";
 const views=toolbar.querySelector(".appointment-ref-views");
 const labels=Array.from(toolbar.querySelectorAll("label"));
 const planned=toolbar.querySelector("[data-appointment-planned]");
 const navRow=document.createElement("div");
 navRow.className="appointment-ref-nav-row";
 const navigation=document.createElement("div");
 navigation.className="appointment-ref-period";
 controls.forEach(button=>navigation.append(button));
 const title=document.createElement("div");
 title.className="appointment-ref-title";
 const heading=document.createElement("b");
 heading.textContent="Randevu Merkezi & Takvim";
 const dateLabel=document.createElement("small");
 dateLabel.textContent=periodLabel;
 title.append(heading,dateLabel);
 const spacer=document.createElement("div");
 spacer.className="appointment-ref-nav-spacer";
 navRow.append(navigation,title);
 if(views)navRow.append(views);
 navRow.append(spacer);
 const filterRow=document.createElement("div");
 filterRow.className="appointment-ref-filter-row";
 labels.forEach(label=>{const textNode=Array.from(label.childNodes).find(node=>node.nodeType===Node.TEXT_NODE);const caption=document.createElement("span");caption.className="appointment-ref-filter-label";caption.textContent=(textNode?.textContent||"").trim();textNode?.remove();label.prepend(caption);filterRow.append(label);});
 if(addButton)filterRow.append(addButton);
 if(planned)filterRow.append(planned);
 const refresh=document.createElement("button");
 refresh.type="button";
 refresh.className="secondary";
 refresh.dataset.appointmentRefresh="";
 refresh.textContent="Listeyi Yenile";
 filterRow.append(refresh);
 toolbar.replaceChildren(navRow,filterRow);
 root.querySelectorAll(".appointment-ref-calendar .appointment-ref-event").forEach(oldCard=>{
  const item=db.appointments.find(row=>String(row.id)===String(oldCard.dataset.id));
  if(!item)return;
  const card=document.createElement("article");
  card.className="appointment-ref-event appointment-ref-calendar-event";
  card.dataset.kind="appointment";
  card.dataset.id=String(item.id);
  card.draggable=true;
  const rawColor=String(item.color||"#3b82f6");
  card.style.setProperty("--appointment-color",/^#[0-9a-fA-F]{6}$/.test(rawColor)?rawColor:"#3b82f6");
  const customer=document.createElement("b");
  customer.textContent=item.customer||customerName(item.customerId)||"-";
  const description=document.createElement("span");
  description.textContent=String(item.title||item.description||item.fault||"Randevu").split(" - ")[0];
  const time=document.createElement("time");
  time.textContent=String(item.time||"09:00");
  const detail=document.createElement("span");
  detail.className="appointment-ref-calendar-event-detail";
  detail.append(time,document.createTextNode("  "),description);
  card.append(customer,detail);
  const technician=item.technician||item.technician_name||"";
  if(technician){const assigned=document.createElement("small");assigned.textContent=technician;card.append(assigned)}
  oldCard.replaceWith(card);
 });
 return root.outerHTML;
};
document.addEventListener("click",async event=>{
 const button=event.target.closest("[data-appointment-refresh]");
 if(!button)return;
 button.disabled=true;
 try{
  const result=await apiFetch("/api/desktop/table/appointments?limit=1000");
  db.appointments=(result.rows||[]).map(row=>({...row,id:String(row.id),customerId:String(row.customer_id||""),customer:row.customer_name||"",technician:row.personnel_name||"",title:row.title||row.description||row.fault||"Randevu",status:row.status||"Bekliyor"}));
  save();render();toast("Randevu listesi yenilendi","success");
 }catch(error){toast(error.message||"Randevu listesi yenilenemedi","error");if(button.isConnected)button.disabled=false}
});
function weekDaysForPlanned(date,offset){return apWeek(offset).some(day=>apDate(day)===apDateKey(date))}
