"use strict";

const $ = (s, root = document) => root.querySelector(s);
const $$ = (s, root = document) => [...root.querySelectorAll(s)];
const uid = (prefix = "id") => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
const today = () => new Date().toISOString().slice(0, 10);
const moneyNumber = value => {
 if(value===null||value===undefined||value==="")return 0;
 if(typeof value==="number")return Number.isFinite(value)?value:0;
 let text=String(value).trim().replace(/[\s\u00a0]/g,"").replace(/[^0-9,.-]/g,"");
 if(text.includes(",")&&text.includes("."))text=text.lastIndexOf(",")>text.lastIndexOf(".")?text.replace(/\./g,"").replace(",","."):text.replace(/,/g,"");
 else if(text.includes(",")){const fraction=text.split(",").pop();text=fraction.length<=2?text.replace(/\./g,"").replace(",","."):text.replace(/,/g,"")}
 else if((text.match(/\./g)||[]).length>1||(/\.\d{3}$/.test(text)&&text.split(".").length===2))text=text.replace(/\./g,"");
 const amount=Number(text);return Number.isFinite(amount)?amount:0;
};
const money = (value, currency = "TRY") => new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(moneyNumber(value));
const esc = value => String(value ?? "").replace(/[&<>'"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));
const settingBool = value => ["1","true","yes","on","evet","aktif"].includes(String(value??"").trim().toLocaleLowerCase("tr-TR"));

const seed = {
  customers: [
    {id:"cus_1",name:"Mert Bilgisayar",phone:"0532 410 22 18",email:"mert@ornek.com",type:"Kurumsal",balances:{TRY:12850,USD:420,EUR:180},services:[{date:"2026-07-08",no:"SRV-1042",device:"Dell Latitude 5420",status:"Tamamlandı",note:"SSD değişimi"}],quotes:[]},
    {id:"cus_2",name:"Ece Yılmaz",phone:"0544 765 11 04",email:"ece@ornek.com",type:"Bireysel",balances:{TRY:-2450,USD:0,EUR:75},services:[{date:"2026-07-14",no:"SRV-1051",device:"Xiaomi Kamera",status:"Bekliyor",note:"Bağlantı sorunu"}],quotes:[]},
    {id:"cus_3",name:"Atlas Güvenlik A.Ş.",phone:"0212 333 48 90",email:"satinalma@atlas.com",type:"Kurumsal",balances:{TRY:0,USD:1250,EUR:0},services:[],quotes:[]}
  ],
  stock: [
    {id:"stk_1",code:"PC-SSD-001",name:"Kingston NV2 1TB NVMe",category:"Bilgisayar",qty:18,min:5,buy:1850,sell:2390,currency:"TRY",barcode:"740617329919"},
    {id:"stk_2",code:"SEC-CAM-004",name:"Hikvision 4MP IP Kamera",category:"Güvenlik Sistemleri",qty:4,min:6,buy:72,sell:99,currency:"USD",barcode:"6941264088280"},
    {id:"stk_3",code:"SMT-HUB-002",name:"Aqara Hub M2",category:"Akıllı Ev",qty:9,min:3,buy:58,sell:79,currency:"EUR",barcode:"6970504213777"},
    {id:"stk_4",code:"PC-RAM-016",name:"Crucial 16GB DDR4",category:"Bilgisayar",qty:2,min:5,buy:1020,sell:1390,currency:"TRY",barcode:"649528903815"}
  ],
  movements:[
    {id:"mov_1",date:"2026-07-15 11:42",product:"Kingston NV2 1TB NVMe",type:"Çıkış",qty:1,ref:"SRV-1050",user:"Yönetici"},
    {id:"mov_2",date:"2026-07-14 16:20",product:"Aqara Hub M2",type:"Giriş",qty:5,ref:"ALIŞ-287",user:"Yönetici"}
  ],
  finance:[
    {id:"fin_1",date:"2026-07-15",type:"Gelir",category:"Servis",amount:4850,currency:"TRY",description:"SRV-1049 servis tahsilatı",customer:"Mert Bilgisayar"},
    {id:"fin_2",date:"2026-07-14",type:"Gider",category:"Tedarik",amount:1120,currency:"TRY",description:"Sarf malzeme alımı",customer:""}
  ],
  appointments:[
    {id:"apt_1",date:today(),time:"14:30",customerId:"cus_2",title:"Kamera bağlantı kontrolü",status:"Planlandı",alerted:false},
    {id:"apt_2",date:today(),time:"16:00",customerId:"cus_1",title:"Cihaz teslimi",status:"Onaylandı",alerted:false}
  ],
  quotes: [],
  settings:{theme:"light",compact:false,doubleClick:true,contextMenu:true,appointmentAlerts:true,alertMinutes:30,company:"AYEC Pro Teknik Servis",currency:"TRY"},
  activities:[{date:new Date().toISOString(),text:"Web çalışma alanı hazırlandı",icon:"✓"}]
};

const DB_KEY = "ayec_pro_web_v3";
const loadState = () => { try { return {...structuredClone(seed), ...JSON.parse(localStorage.getItem(DB_KEY) || "{}")}; } catch { return structuredClone(seed); } };
let db = loadState();
let page = "dashboard";
let selection = null;
let salesCart = [];
let salesCustomer = "";
let authTenants = [];
function rememberAuthTenant(tenant){
 const id=String(tenant?.id||"").trim();
 const companyName=String(tenant?.company_name||"").trim();
 if(!id||!companyName)return;
 const item={id,company_name:companyName};
 const index=authTenants.findIndex(current=>String(current?.id||"")===id);
 if(index>=0)authTenants[index]=item;else authTenants.push(item);
 authTenants.sort((left,right)=>String(left.company_name||"").localeCompare(String(right.company_name||""),"tr"));
}
let notifications = [];
let scheduledAlerts = [];
let settingsSection = "company";
let appointmentWeekOffset = 0;
let currentSector = "teknik_servis";
let desktopSettings = {};
let desktopInternalSettings = {};
const save = () => localStorage.setItem(DB_KEY, JSON.stringify(db));
const activity = (text, icon="•") => { db.activities.unshift({date:new Date().toISOString(),text,icon}); db.activities=db.activities.slice(0,20); save(); };

const menu = [
  {group:"Servis Yönetimi",items:[{id:"dashboard",icon:"⌂",label:"Genel Bakış"},{id:"services",icon:"▣",label:"Servis Panosu"},{id:"technician",icon:"⚒",label:"Teknisyen Paneli"},{id:"automotive-stock",icon:"▦",label:"Araç Parça Stoğu"},{id:"field-service",icon:"⌖",label:"Saha Servis Haritası"},{id:"appointments",icon:"▦",label:"Randevular"},{id:"logistics",icon:"▱",label:"Lojistik & Garanti Yönetimi"},{id:"job-reports",icon:"▥",label:"İş / Servis Takibi Raporları"},{id:"vehicle-maintenance",icon:"◇",label:"Araç Bakım Takibi"},{id:"assistant",icon:"✦",label:"AI Asistan"}]},
  {group:"Ticari",items:[{id:"stock-parent",icon:"◫",label:"Stok Yönetimi",children:[{id:"stock",label:"Stok Listesi"},{id:"movements",label:"Stok Hareketleri"},{id:"import",label:"Akıllı İçe Aktarma"}]},{id:"service-definitions",icon:"◇",label:"Hizmet Tanımları"},{id:"brands",icon:"◈",label:"Cihaz Bilgisi & Markalar"},{id:"loaners",icon:"▣",label:"Emanet Konsinye Cihazlar"},{id:"sales",icon:"◆",label:"Satış"},{id:"mobile-guide",icon:"▧",label:"Mobil Teknik Kılavuz"},{id:"pc-builder",icon:"▧",label:"PC Yapılandırıcı"}]},
  {group:"Finans",items:[{id:"finance-parent",icon:"₺",label:"Gelir / Gider Takibi",children:[{id:"finance",label:"Finans Özeti"},{id:"income",label:"Gelirler"},{id:"expense",label:"Giderler"}]},{id:"banks",icon:"▤",label:"Banka Hesapları"},{id:"checks",icon:"▥",label:"Çek / Senet Takibi"},{id:"invoices",icon:"▱",label:"E-Fatura Oluştur"}]},
  {group:"Müşteri",items:[{id:"customers",icon:"♙",label:"Müşteri Listesi"},{id:"contracts",icon:"▦",label:"Bakım Sözleşmeleri"},{id:"partners",icon:"♧",label:"Çalışma Ortaklarımız"},{id:"reminders",icon:"◷",label:"Hatırlatıcılar"},{id:"announcements",icon:"◉",label:"Duyurular"}]},
  {group:"Personel",items:[{id:"personnel",icon:"♟",label:"Personel Yönetimi"}]},
  {group:"Projeler",items:[{id:"projects",icon:"▣",label:"Proje Yönetimi"},{id:"project-archive",icon:"▤",label:"Proje Arşivi"}]},
  {group:"Sistem",items:[{id:"knowledge",icon:"▧",label:"Bilgi Bankası"},{id:"settings",icon:"⚙",label:"Sistem Ayarları"},{id:"backup",icon:"▰",label:"Yedekleme Merkezi"},{id:"support",icon:"?",label:"Destek Merkezi"},{id:"audit",icon:"▤",label:"Log Kayıtları"},{id:"manual",icon:"▧",label:"Kullanım Kılavuzu"},{id:"dialog-catalog",icon:"▦",label:"Dialog Modülleri"}]}
];

const sectorPages={teknik_servis:new Set(["dashboard","services","technician","field-service","appointments","logistics","job-reports","assistant","customers","contracts","partners","reminders","announcements","stock-parent","stock","movements","import","service-definitions","brands","loaners","sales","mobile-guide","pc-builder","finance-parent","finance","income","expense","banks","checks","invoices","personnel","projects","project-archive","knowledge","settings","backup","support","audit","manual","dialog-catalog"]),otomotiv:new Set(["dashboard","services","technician","automotive-stock","appointments","vehicle-maintenance","assistant","customers","contracts","partners","reminders","announcements","stock-parent","stock","movements","import","service-definitions","brands","loaners","finance-parent","finance","income","expense","banks","checks","invoices","personnel","knowledge","settings","backup","support","audit","manual","dialog-catalog"])};
function renderNav(){const allowed=sectorPages[currentSector]||sectorPages.teknik_servis;$("#nav").innerHTML=menu.map(g=>{const items=g.items.filter(i=>allowed.has(i.id)).map(i=>i.children?{...i,children:i.children.filter(c=>allowed.has(c.id))}:i);return items.length?`<div class="nav-group-title">${g.group}</div>${items.map(i=>i.children?`<button class="nav-button nav-parent" data-parent="${i.id}"><span>${i.icon}</span><span>${i.label}</span></button><div class="submenu" id="${i.id}">${i.children.map(c=>`<button class="nav-button" data-page="${c.id}"><span>·</span><span>${c.label}</span></button>`).join("")}</div>`:`<button class="nav-button" data-page="${i.id}"><span>${i.icon}</span><span>${i.label}</span></button>`).join("")}`:""}).join("");if($("#sectorSelect"))$("#sectorSelect").value=currentSector;if($("#sectorBrand"))$("#sectorBrand").textContent=currentSector==="otomotiv"?"Otomotiv Servis":"Teknik Servis"}

const titles={dashboard:["Servis Yönetimi","Genel Bakış"],customers:["Müşteri","Müşteri Listesi"],appointments:["Servis Yönetimi","Randevular"],stock:["Ticari","Stok Yönetimi"],movements:["Ticari","Stok Hareketleri"],import:["Ticari","Akıllı İçe Aktarma"],sales:["Ticari","Satış"],services:["Servis Yönetimi","Servis Panosu"],technician:["Servis Yönetimi","Teknisyen Paneli"],finance:["Finans","Gelir / Gider Takibi"],income:["Finans","Gelirler"],expense:["Finans","Giderler"],settings:["Sistem","Sistem Ayarları"]};
const genericModules={
 "product-groups":{group:"Servis Y\u00f6netim Ayar\u0131",title:"\u00dcr\u00fcn Grubu Y\u00f6netimi",table:"product_groups",description:"Servis ve stok ekranlar\u0131nda kullan\u0131lan \u00fcr\u00fcn gruplar\u0131."},
 "report-templates":{group:"Servis Y\u00f6netim Ayar\u0131",title:"Rapor C\u00fcmle Kal\u0131plar\u0131",table:"quick_notes",description:"Servis raporlar\u0131nda kullan\u0131lan haz\u0131r metinler."},
 offers:{group:"Teklif Y\u00f6netimi",title:"T\u00fcm Teklifler",table:"offers",description:"M\u00fc\u015fterilere verilen teklifler ve onay durumlar\u0131."},
 "offer-reports":{group:"Teklif Y\u00f6netimi",title:"Teklif Raporlar\u0131",table:"offers",description:"Teklif tutarlar\u0131, onay durumlar\u0131 ve performans raporlar\u0131."},
 "automotive-stock":{group:"Servis Yönetimi",title:"Araç Parça Stoğu",table:"parts",description:"Otomotiv servisleri için parça stoğu ve kritik seviyeler."},
 "field-service":{group:"Servis Yönetimi",title:"Saha Servis Haritası",table:"appointments",description:"Saha operasyonları, personel konumları ve servis planları."},
 logistics:{group:"Servis Yönetimi",title:"Lojistik & Garanti Yönetimi",table:"logistics",description:"Kargo, dış servis ve garanti gönderileri."},
 "job-reports":{group:"Servis Yönetimi",title:"İş / Servis Takibi Raporları",table:"devices",description:"Servis kayıtlarının durum ve performans raporları."},
 "vehicle-maintenance":{group:"Servis Yönetimi",title:"Araç Bakım Takibi",table:"vehicle_maintenance_cards",description:"Araç bakım kartları ve yaklaşan bakım planları."},
 "service-definitions":{group:"Ticari",title:"Hizmet Tanımları",table:"service_definitions",description:"Satış ve servis formlarında kullanılan hizmetler."},
 brands:{group:"Ticari",title:"Cihaz Bilgisi & Markalar",table:"device_brands",description:"Servis kabulünde kullanılan cihaz türleri ve markalar."},
 loaners:{group:"Ticari",title:"Emanet Konsinye Cihazlar",table:"loaner_devices",description:"Emanet cihaz ve teslim hareketleri."},
 banks:{group:"Finans",title:"Banka Hesapları",table:"bank_accounts",description:"Banka hesapları, kartlar ve bakiye hareketleri."},
 checks:{group:"Finans",title:"Çek / Senet Takibi",table:"checks_notes",description:"Portföy, vade ve tahsilat durumları."},
 invoices:{group:"Finans",title:"E-Fatura Oluştur",table:"e_invoices",description:"E-fatura kayıtları ve gönderim durumları."},
 contracts:{group:"Müşteri",title:"Bakım Sözleşmeleri",table:"contracts",description:"Müşteri bakım ve destek sözleşmeleri."},
 partners:{group:"Müşteri",title:"Çalışma Ortaklarımız",table:"customers",description:"Bayi, tedarikçi ve iş ortakları."},
 reminders:{group:"Müşteri",title:"Hatırlatıcılar",table:"reminders",description:"Servis ve müşteri hatırlatmaları."},
 announcements:{group:"Müşteri",title:"Duyurular",table:"announcements",description:"Kurum içi duyuru ve öncelikler."},
 personnel:{group:"Personel",title:"Personel Yönetimi",table:"personnel",description:"Kullanıcı, rol, maaş ve komisyon kayıtları."},
 projects:{group:"Projeler",title:"Proje Yönetimi",table:"projects",description:"Proje, bütçe, birim ve finans yönetimi."},
 "project-archive":{group:"Projeler",title:"Proje Arşivi",table:"projects",description:"Arşivlenmiş proje kayıtları."},
 knowledge:{group:"Sistem",title:"Bilgi Bankası",table:"kb_articles",description:"Teknik makaleler ve çözüm notları."},
 audit:{group:"Sistem",title:"Log Kayıtları",table:"audit_logs",description:"Kullanıcı ve veri değişikliği denetim kayıtları."},
 backup:{group:"Sistem",title:"Yedekleme Merkezi",table:"settings",description:"Veritabanı yedekleme ve geri yükleme merkezi."},
 support:{group:"Sistem",title:"Destek Merkezi",table:"tickets",description:"Destek talepleri ve durumları."},
 manual:{group:"Sistem",title:"Kullanım Kılavuzu",table:"kb_articles",description:"AYEC Pro kullanım kılavuzu."},
 "pc-builder":{group:"Ticari",title:"PC Yapılandırıcı",table:"parts",description:"Stok ürünleriyle bilgisayar yapılandırması."},
 "mobile-guide":{group:"Ticari",title:"Mobil Teknik Kılavuz",table:"kb_articles",description:"Saha teknisyenleri için mobil uyumlu teknik kılavuz."},
 assistant:{group:"Servis Yönetimi",title:"AI Asistan",table:"notifications",description:"İşletme verileriyle akıllı yardım ve bildirimler."}
};
async function apiFetch(path,options={}){const response=await fetch(path,{...options,credentials:"same-origin",headers:{"Content-Type":"application/json",...(options.headers||{})}});const raw=await response.text();let data={};try{data=raw?JSON.parse(raw):{}}catch{const snippet=raw.replace(/\s+/g," ").trim().slice(0,180);throw Error(`Sunucu geçersiz yanıt verdi (${response.status}${snippet?` · ${snippet}`:""})`)}if(response.status===401&&!path.startsWith("/api/auth/")&&window.handleUnauthorized)window.handleUnauthorized();if(!response.ok)throw Error(data.error||`Sunucu hatası (${response.status})`);return data}
function desktopWrite(table,payload){return apiFetch(`/api/desktop/table/${table}`,{method:"POST",body:JSON.stringify(payload)}).catch(err=>toast(`Masaüstü veritabanı: ${err.message}`,"error"))}
function navigate(next){if(typeof setMobileMenu==="function")setMobileMenu(false);window.scrollTo({top:0,left:0});page=next; selection=null; const meta=genericModules[next];const [crumb,title]=titles[next]||[meta?.group||"AYEC Pro",meta?.title||"Sayfa"];$("#breadcrumb").textContent=crumb;$("#pageTitle").textContent=title;$$('[data-page]').forEach(b=>b.classList.toggle("active",b.dataset.page===next));$("#sidebar").classList.remove("open");render();setTimeout(()=>{window.scrollTo({top:0,left:0});$("#content").focus({preventScroll:true})},0)}

function pageHead(title,desc,actions=""){return `<div class="page-head"><div><h2>${title}</h2><p>${desc}</p></div><div class="actions">${actions}</div></div>`}
function metric(label,value,sub,icon="○"){return `<div class="metric"><div class="metric-top"><span>${label}</span><span class="metric-icon">${icon}</span></div><strong>${value}</strong><small>${sub}</small></div>`}
function statusBadge(status){const cls=/tamam|ödendi|gelir|onay/i.test(status)?"success":/kritik|gider|iptal|gecik/i.test(status)?"danger":"warn";return `<span class="badge ${cls}">${esc(status)}</span>`}
function customerName(id){return db.customers.find(c=>c.id===id)?.name||"Bilinmeyen müşteri"}
function empty(title,desc){return `<div class="empty"><span style="font-size:30px">◇</span><strong>${title}</strong><span>${desc}</span></div>`}

function renderDashboard(){
 const automotive=currentSector==="otomotiv";
 const waiting=db.customers.flatMap(c=>c.services).filter(s=>s.status!=="Tamamlandı").length;
 const income=db.finance.filter(f=>f.type==="Gelir").reduce((a,b)=>a+moneyNumber(b.amount),0), expense=db.finance.filter(f=>f.type==="Gider").reduce((a,b)=>a+moneyNumber(b.amount),0);
 const critical=db.stock.filter(s=>s.qty<=s.min).length;
 return `${pageHead(automotive?"Otomotiv servisinizin bugünkü görünümü":"İşletmenizin bugünkü görünümü",automotive?"Araç, bakım kartı, randevu, yedek parça ve finans tek çalışma alanında.":"Servis, satış, stok ve finans tek çalışma alanında.",'<span class="badge sector-badge">'+(automotive?'OTOMOTİV MODU':'TEKNİK SERVİS MODU')+'</span><button class="secondary" data-action="export-all">Dışa Aktar</button><button class="primary" data-action="quick-add">＋ Yeni İşlem</button>')}
 <div class="metric-grid">${metric(automotive?"Açık İş Emirleri":"Bekleyen Onarım",waiting,automotive?"Aktif araç servisleri":"Aktif servis kayıtları","⚒")}${metric(automotive?"Bugünkü Araç Randevusu":"Bugünkü Randevu",db.appointments.filter(a=>a.date===today()).length,"Yaklaşan görüşmeler","▣")}${metric(automotive?"Servis Geliri":"Net Nakit",money(income-expense),"Gelir − gider","₺")}${metric(automotive?"Kritik Yedek Parça":"Kritik Stok",critical,"Minimum seviyenin altında","!")}</div>
 <div class="grid-2"><div><section class="card"><div class="card-head"><h3>Son finans hareketleri</h3><button class="mini" data-page="finance">Tümünü gör</button></div>${financeTable(db.finance.slice(0,5))}</section><section class="card"><div class="card-head"><h3>Haftalık iş yoğunluğu</h3><span class="muted">Son 7 gün</span></div><div class="chart">${[55,72,46,88,64,35,76].map((v,i)=>`<div class="bar" style="height:${v}%"><span>${["Pzt","Sal","Çar","Per","Cum","Cmt","Paz"][i]}</span></div>`).join("")}</div></section></div>
 <aside><section class="card"><div class="card-head"><h3>Yaklaşan randevular</h3><button class="mini" data-page="appointments">Takvim</button></div>${db.appointments.filter(a=>a.status!=="İptal").slice(0,4).map(a=>`<div class="activity" data-kind="appointment" data-id="${a.id}"><span class="activity-icon">${a.time}</span><div><p><strong>${esc(customerName(a.customerId))}</strong></p><small>${esc(a.title)} · ${a.date}</small></div></div>`).join("")||empty("Randevu yok","Yeni bir randevu ekleyin.")}</section><section class="card"><div class="card-head"><h3>Son aktiviteler</h3></div>${db.activities.slice(0,5).map(a=>`<div class="activity"><span class="activity-icon">${a.icon}</span><div><p>${esc(a.text)}</p><small>${new Date(a.date).toLocaleString("tr-TR")}</small></div></div>`).join("")}</section></aside></div>`;
}

function renderCustomers(){return `${pageHead("Müşteri Yönetimi","Müşterileri, cari durumlarını ve tahsilat aksiyonlarını tek ekranda yönetin.",'<span class="badge">MÜŞTERİ HUB</span>')}<div class="customer-banners"><button data-customer-filter="all">TÜM MÜŞTERİLER</button><button class="red" data-customer-filter="debt">NET BORÇLULAR</button><button class="amber" data-customer-filter="receivable">TAHSİLAT BEKLEYENLER</button><button class="green" data-action="add-customer">＋ YENİ MÜŞTERİ EKLE</button></div><section class="card customer-card"><div class="toolbar customer-toolbar"><button class="mini" data-action="copy-customers" title="Listeyi Kopyala">📋</button><button class="mini" data-action="export-customers" title="Excel'e Aktar">📊</button><button class="mini" data-action="export-customers-pdf" title="PDF'e Aktar">📄</button><button class="mini" data-action="print-customers" title="Yazdır">🖨️</button><button class="mini" title="Belge Merkezi">🗂️</button><button class="mini" title="Çoklu Seçim">🔲</button><span class="toolbar-spacer"></span><label><b>Arama:</b></label><input class="control search" id="customerSearch" placeholder="İsim, telefon veya e-posta..."></div><div id="customerTable">${customerTable(db.customers)}</div><div class="customer-footer"><span>📊 Toplam Kayıt: <b id="customerCount">${db.customers.length}</b></span><span>◀ &nbsp; 1 / 1 &nbsp; ▶</span><span>🕒 Son Güncelleme: ${new Date().toLocaleString("tr-TR")}</span></div></section>`}
function customerTable(rows){return `<div class="table-wrap"><table><thead><tr><th>MÜ.NO</th><th>MÜŞTERİ</th><th>FİRMA</th><th>TELEFON</th><th>E-POSTA</th><th>BAKİYE</th><th>İŞLEMLER</th></tr></thead><tbody>${rows.map((c,i)=>`<tr data-kind="customer" data-id="${c.id}"><td>${String(i+1).padStart(5,"0")}</td><td><strong>${esc(c.name)}</strong><br><small class="muted">${esc(c.type)}</small></td><td>${esc(c.company||c.company_name||"—")}</td><td>${esc(c.phone)}</td><td>${esc(c.email)}</td><td class="balance"><strong>${money(c.balances.TRY,"TRY")}</strong><br><small>${money(c.balances.USD,"USD")} · ${money(c.balances.EUR,"EUR")}</small></td><td><button class="primary mini" data-action="customer-actions" data-id="${c.id}">İşlem Yap ▾</button></td></tr>`).join("")}</tbody></table></div>`}

function stockTabs(active){return `<div class="tabs"><button class="tab ${active==="stock"?"active":""}" data-page="stock">Stok Durumu</button><button class="tab ${active==="movements"?"active":""}" data-page="movements">Stok Hareketleri</button><button class="tab ${active==="import"?"active":""}" data-page="import">Nasıl Kullanılır? / Akıllı İçe Aktarma</button></div>`}
function sectorStockCategories(){return currentSector==="otomotiv"?["Motor & Mekanik","Elektrik & Elektronik","Kaporta","Sarf Malzeme"]:["Bilgisayar","Akıllı Ev","Güvenlik Sistemleri"]}
function stockValueSummary(){
 const totals={TRY:0,USD:0,EUR:0};
 db.stock.forEach(product=>{
  const currency=String(product.currency||"TRY").toUpperCase();
  if(!(currency in totals))totals[currency]=0;
  totals[currency]+=Math.max(0,Number(product.qty)||0)*Math.max(0,Number(product.buy)||0);
 });
 const currencies=Object.keys(totals).filter(currency=>totals[currency]>0);
 const missing=currencies.filter(currency=>currency!=="TRY"&&rateForCode(currency)<=0);
 const tryEquivalent=currencies.reduce((sum,currency)=>{const rate=rateForCode(currency);return rate>0?sum+totals[currency]*rate:sum},0);
 const breakdown=currencies.map(currency=>money(totals[currency],currency)).join(" · ");
 return {breakdown,missing,tryEquivalent};
}
function renderStock(){const value=stockValueSummary(),critical=db.stock.filter(s=>s.qty<=s.min).length,categories=sectorStockCategories(),description=currentSector==="otomotiv"?"Otomotiv parça grupları için akıllı filtreleme.":"Bilgisayar, Akıllı Ev ve Güvenlik Sistemleri için akıllı filtreleme.",valueText=value.missing.length?(value.breakdown||money(0,"TRY")):money(value.tryEquivalent,"TRY"),valueDetail=value.missing.length?`Kur eksik · ${value.missing.join(", ")} TRY karşılığı hesaplanamadı`:`Alış maliyeti · ${value.breakdown||money(0,"TRY")} · TRY karşılığı`;return `${pageHead("Stok Listesi",description,'<button class="danger" data-action="critical-stock">Kritik Stok</button><button class="secondary" data-page="import">İçe Aktar</button><button class="secondary" data-action="export-stock">Excel / PDF / Yazdır</button><button class="primary" data-action="add-product">＋ Ürün Ekle</button>')}${stockTabs("stock")}<div class="metric-grid">${metric("Ürün Çeşidi",db.stock.length,"Aktif stok kartı","◫")}${metric("Toplam Adet",db.stock.reduce((a,s)=>a+s.qty,0),"Depodaki ürünler","#")}${metric("Stok Değeri",valueText,valueDetail,"₺")}${metric("Kritik Seviye",critical,"Sipariş önerisi","!")}</div><section class="card"><div class="toolbar"><input class="control search" id="stockSearch" placeholder="Kod, barkod veya ürün ara"><select class="control" id="stockCategory"><option>Tüm Kategoriler</option>${categories.map(x=>`<option>${x}</option>`).join("")}</select><select class="control" id="stockLevel"><option>Tüm Seviyeler</option><option>Kritik Stok</option><option>Stokta Var</option></select></div><div id="stockTable">${stockTable(db.stock)}</div></section>`}
function stockTable(rows){return `<div class="table-wrap"><table><thead><tr><th>Kod</th><th>Ürün</th><th>Kategori</th><th>Stok</th><th>Min.</th><th>Satış Fiyatı</th><th>Durum</th><th></th></tr></thead><tbody>${rows.map(s=>`<tr data-kind="stock" data-id="${s.id}"><td>${esc(s.code)}</td><td><strong>${esc(s.name)}</strong><br><small class="muted">${esc(s.barcode)}</small></td><td><span class="badge">${esc(s.category)}</span></td><td>${s.qty}</td><td>${s.min}</td><td>${money(s.sell,s.currency)}</td><td>${statusBadge(s.qty<=s.min?"Kritik":"Stokta")}</td><td><div class="row-actions"><button class="mini" data-action="edit-product" data-id="${s.id}">Düzenle</button><button class="mini danger-outline" data-action="delete-product" data-id="${s.id}">Sil</button></div></td></tr>`).join("")}</tbody></table></div>`}

function renderMovements(){return `${pageHead("Stok Hareketleri","Giriş, çıkış, satış ve servis kullanım kayıtları.",'<button class="primary" data-action="add-movement">＋ Hareket Ekle</button>')}${stockTabs("movements")}<section class="card"><div class="toolbar"><input class="control search" id="movementSearch" placeholder="Ürün veya referans ara"><select class="control" id="movementType"><option>Tümü</option><option>Giriş</option><option>Çıkış</option></select></div><div id="movementTable">${movementTable(db.movements)}</div></section>`}
function movementTable(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Ürün</th><th>Tür</th><th>Miktar</th><th>Referans</th><th>Kullanıcı</th></tr></thead><tbody>${rows.map(m=>`<tr><td>${esc(m.date)}</td><td><strong>${esc(m.product)}</strong></td><td>${statusBadge(m.type)}</td><td>${m.qty}</td><td>${esc(m.ref)}</td><td>${esc(m.user)}</td></tr>`).join("")}</tbody></table></div>`}

function renderImport(){return `${pageHead("Akıllı Stok İçe Aktar","Masaüstündeki StockImportParser; PDF tablo, kutu bazlı OCR ve kolon eşleştirme akışını kullanır.",'<button class="secondary" data-action="add-import-row">＋ Eksik Ürün Satırı Ekle</button><button class="secondary" data-action="download-template">Şablon İndir</button>')}${stockTabs("import")}<section class="card"><div class="import-lanes"><article class="import-lane"><span class="import-icon">PDF</span><h3>PDF İçe Aktar</h3><p>pdfplumber tablo çizgilerini ve kolon sınırlarını okuyarak fatura satırlarını ayırır.</p><div class="import-badges"><span>Çizgili tablo</span><span>Kolon ayrımı</span><span>DataFrame önizleme</span></div><button class="primary" data-action="choose-import-mode" data-mode="pdf">PDF Seç</button></article><article class="import-lane"><span class="import-icon">OCR</span><h3>Resim İçe Aktar</h3><p>PaddleOCR varsa kutu bazlı okur; yoksa EasyOCR/Tesseract Türkçe + İngilizce zincirine geçer.</p><div class="import-badges"><span>Kutu bazlı OCR</span><span>Görüntü iyileştirme</span><span>Satır doğrulama</span></div><button class="primary" data-action="choose-import-mode" data-mode="image">Resim Seç</button></article><article class="import-lane"><span class="import-icon">XLS</span><h3>Tablo / E-Fatura</h3><p>Excel, CSV, UBL XML ve DOCX alanlarını akıllı kolon eşleştirmeyle içe aktarır.</p><div class="import-badges"><span>Excel</span><span>UBL XML</span><span>CSV / DOCX</span></div><button class="primary" data-action="choose-import-mode" data-mode="structured">Dosya Seç</button></article></div><div class="drop-zone" id="dropZone"><strong>Dosyayı sürükleyip bırakabilirsiniz</strong><span>En fazla 25 MB · Önizlemeden sonra kayıt yapılır</span></div><div id="importPreview"></div></section>`}

function renderSales(){return `${pageHead("Sales Hub","Stoktaki ürünlerden tahsilat, proforma ve servis akışlarını yönetin.",'<button class="secondary" data-action="view-quotes">Proformalar</button>')}<div class="grid-2"><section class="card"><div class="card-head"><h3>1. Müşteri ve ürün seçimi</h3><span class="badge">Canlı stok</span></div><div class="toolbar"><select class="control" id="salesCustomer"><option value="">Müşteri seçin…</option>${db.customers.map(c=>`<option value="${c.id}" ${salesCustomer===c.id?"selected":""}>${esc(c.name)}</option>`).join("")}</select><input class="control search" id="salesProductSearch" placeholder="Stokta ürün ara"></div><div id="salesProducts" class="product-picker">${salesProducts(db.stock)}</div></section><aside class="card"><div class="card-head"><h3>2. Teklif sepeti</h3><span class="badge">${salesCart.length} kalem</span></div><div id="salesCart">${cartHtml()}</div><div class="kpi-inline"><div><small class="muted">Ara toplam</small><strong id="cartTotal">${money(cartTotal())}</strong></div></div><div class="actions"><button class="success" data-action="pay-save">Ödeme Al ve Kaydet</button><button class="primary" data-action="create-proforma">Proforma Oluştur</button><button class="secondary" data-action="save-service">Servis Kaydet</button></div></aside></div>`}
function salesProducts(rows){return rows.filter(s=>s.qty>0).map(s=>`<div class="product-tile"><div><strong>${esc(s.name)}</strong><br><small class="muted">Stok: ${s.qty} · ${money(s.sell,s.currency)}</small></div><button class="mini" data-action="cart-add" data-id="${s.id}">＋</button></div>`).join("")||empty("Stokta ürün yok","Önce stok kartı ekleyin.")}
function normalizedPrice(s){return Number(s.sell)*rateForCode(s.currency||"TRY")}
function cartTotal(){return salesCart.reduce((a,l)=>{const s=db.stock.find(x=>x.id===l.productId);return a+(s?normalizedPrice(s)*l.qty:0)},0)}
function cartHtml(){return salesCart.length?salesCart.map((l,i)=>{const s=db.stock.find(x=>x.id===l.productId);return s?`<div class="cart-line"><strong>${esc(s.name)}</strong><input class="control cart-qty" type="number" min="1" max="${s.qty}" value="${l.qty}" data-index="${i}"><span>${money(normalizedPrice(s)*l.qty)}</span><button class="mini" data-action="cart-remove" data-index="${i}">×</button></div>`:""}).join(""):empty("Sepet boş","Soldaki stok ürünlerinden ekleyin.")}

function renderServices(){const services=db.customers.flatMap(c=>c.services.map(s=>({...s,customer:c.name,customerId:c.id})));return `${pageHead("Servis Formları","Müşterilere bağlı servis kayıtları ve durum takibi.",'<button class="primary" data-action="new-service">＋ Yeni Servis Kaydı</button>')}<section class="card">${services.length?`<div class="table-wrap"><table><thead><tr><th>Servis No</th><th>Müşteri</th><th>Cihaz</th><th>Tarih</th><th>Durum</th><th>Not</th><th></th></tr></thead><tbody>${services.map(s=>`<tr data-kind="service" data-id="${s.no}" data-customer="${s.customerId}"><td><strong>${esc(s.no)}</strong></td><td>${esc(s.customer)}</td><td>${esc(s.device)}</td><td>${esc(s.date)}</td><td>${statusBadge(s.status)}</td><td>${esc(s.note)}</td><td><button class="mini" data-action="service-detail" data-id="${s.no}" data-customer="${s.customerId}">Aç</button></td></tr>`).join("")}</tbody></table></div>`:empty("Servis kaydı yok","İlk servis formunu oluşturun.")}</section>`}
function renderTechnician(){const services=db.customers.flatMap(c=>c.services.filter(s=>s.status!=="Tamamlandı").map(s=>({...s,customer:c.name,customerId:c.id})));return `${pageHead("Teknisyen Paneli","Aktif cihazları açın, durum ve işlem notlarını güncelleyin.",'<button class="secondary" data-page="services">Tüm Servisler</button>')}<div class="metric-grid">${metric("Atanan İş",services.length,"Aktif iş emri","⚒")}${metric("Bekleyen",services.filter(s=>s.status==="Bekliyor").length,"Müdahale bekliyor","…")}${metric("Tamamlanan",db.customers.flatMap(c=>c.services).filter(s=>s.status==="Tamamlandı").length,"Toplam kayıt","✓")}${metric("Kritik Parça",db.stock.filter(s=>s.qty<=s.min).length,"Stok uyarısı","!")}</div><section class="card">${services.length?services.map(s=>`<div class="activity" data-kind="service" data-id="${s.no}" data-customer="${s.customerId}"><span class="activity-icon">⚒</span><div style="flex:1"><p><strong>${esc(s.no)} · ${esc(s.customer)}</strong></p><small>${esc(s.device)} — ${esc(s.note)}</small></div>${statusBadge(s.status)}<button class="primary mini" data-action="technician-open" data-id="${s.no}" data-customer="${s.customerId}">İşle</button></div>`).join(""):empty("Aktif iş yok","Yeni servis kaydı oluşturabilirsiniz.")}</section>`}

function renderFinance(filter=""){const rows=filter?db.finance.filter(f=>f.type===filter):db.finance;const income=db.finance.filter(f=>f.type==="Gelir").reduce((a,b)=>a+moneyNumber(b.amount),0),expense=db.finance.filter(f=>f.type==="Gider").reduce((a,b)=>a+moneyNumber(b.amount),0);return `${pageHead(filter?`${filter} Kayıtları`:"Finans Özeti","Gelir ve gider sinyalleri stok, satış ve servis kayıtlarıyla bağlıdır.",'<button class="success" data-action="add-income">＋ Gelir</button><button class="danger" data-action="add-expense">＋ Gider</button><button class="secondary" data-action="export-finance">Dışa Aktar</button>')}<div class="metric-grid">${metric("Toplam Gelir",money(income),"Kayıtlı tahsilatlar","↑")}${metric("Toplam Gider",money(expense),"Kayıtlı ödemeler","↓")}${metric("Net Bakiye",money(income-expense),"Gelir − gider","₺")}${metric("İşlem Sayısı",db.finance.length,"Tüm hareketler","#")}</div><section class="card">${financeTable(rows)}</section>`}
function financeTable(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th>Müşteri</th><th>Tutar</th><th></th></tr></thead><tbody>${rows.map(f=>`<tr data-kind="finance" data-id="${f.id}"><td>${esc(f.date)}</td><td>${statusBadge(f.type)}</td><td>${esc(f.category)}</td><td>${esc(f.description)}</td><td>${esc(f.customer)}</td><td><strong>${money(f.amount,f.currency)}</strong></td><td><button class="mini" data-action="edit-finance" data-id="${f.id}">Düzenle</button></td></tr>`).join("")}</tbody></table></div>`}

function renderAppointments(){const monday=new Date();monday.setDate(monday.getDate()-((monday.getDay()+6)%7)+(appointmentWeekOffset*7));const days=[0,1,2,3,4].map(offset=>{const d=new Date(monday);d.setDate(d.getDate()+offset);return d}),start=days[0].toLocaleDateString("tr-TR"),end=days[4].toLocaleDateString("tr-TR");return `${pageHead("Randevu Takvimi","Çift tıklama, sağ tuş durum menüsü, toast ve yaklaşan randevu uyarıları etkin.",'<button class="primary" data-action="add-appointment">＋ Yeni Randevu</button>')}<section class="card"><div class="appointment-nav"><div class="actions"><button class="secondary" data-action="appointment-prev">‹ Önceki</button><button class="secondary" data-action="appointment-today">Bugün</button><button class="secondary" data-action="appointment-next">Sonraki ›</button></div><strong>${start} — ${end}</strong></div><div class="appointment-board">${days.map(d=>{const ds=d.toISOString().slice(0,10),items=db.appointments.filter(a=>a.date===ds);return `<div class="day-column"><h3>${d.toLocaleDateString("tr-TR",{weekday:"long",day:"numeric",month:"short"})}</h3>${items.map(a=>`<div class="appointment" data-kind="appointment" data-id="${a.id}"><span class="muted">${a.time}</span><strong>${esc(customerName(a.customerId))}</strong><span>${esc(a.title)}</span><br>${statusBadge(a.status)}</div>`).join("")||'<small class="muted">Randevu yok</small>'}</div>`}).join("")}</div></section>`}

const settingsGroups=[
 ["GENEL",[["company","🏢","Firma Ayarları"],["locale","🌐","Dil, Tarih & Para Birimi"],["theme","🎨","Temalar & Yazı Tipi"]]],
 ["ENTEGRASYONLAR & API",[["integrations","🔌","Entegrasyonlar & API"],["sms-settings","💬","SMS Ayarları"],["smtp-settings","✉️","E-posta / SMTP"],["messaging","📱","WhatsApp & Telegram"],["ai-settings","✨","Gemini / AI"],["voice-settings","🎙️","Sesli Asistan"]]],
 ["TİCARİ & LİSTELER",[["cargo","🚚","Kargo Firmaları"],["bank-settings","🏦","Banka Ayarları"],["notes","✏️","Hızlı Not Yönetimi"],["stock-settings","📦","Stok Ayarları"],["numbering","🔢","Belge Numaraları"],["location","📍","Harita & Konum"]]],
 ["GÜVENLİK & SİSTEM",[["backup","💾","Yedekleme ve Veri Merkezi"],["users","👥","Kullanıcı Yönetimi"],["license","🛡️","Lisans Durumu"],["security","🔒","Güvenlik Ayarları (Şifre)"],["audit-settings","📜","Sistem İşlem Logları (Audit)"]]],
 ["UZAK BAĞLANTI",[["remote","🖥️","AYEC Pro (Uzak)"]]],
 ["SİSTEM YAPISI",[["identity","⚙️","Sistem Kimliği & Modüler Yapı"]]]
];
function settingBody(s){const common=`<div class="settings-grid"><div class="setting"><div><strong>Çift tıklama</strong><br><small class="muted">Satırı doğrudan ayrıntıda açar.</small></div><input class="switch" id="setDouble" type="checkbox" ${s.doubleClick?"checked":""}></div><div class="setting"><div><strong>Sağ tuş menüleri</strong><br><small class="muted">Bağlama özel işlem menüsü.</small></div><input class="switch" id="setContext" type="checkbox" ${s.contextMenu?"checked":""}></div><div class="setting"><div><strong>Randevu bildirimleri</strong><br><small class="muted">Toast, alert ve sistem bildirimi.</small></div><input class="switch" id="setAlerts" type="checkbox" ${s.appointmentAlerts?"checked":""}></div><div class="setting"><div><strong>Kompakt görünüm</strong><br><small class="muted">Tablo ve kart aralıklarını azaltır.</small></div><input class="switch" id="setCompact" type="checkbox" ${s.compact?"checked":""}></div></div>`;if(settingsSection==="company")return `<h3>Firma Ayarları</h3><div class="form-grid"><div class="field full"><label>Firma Adı</label><input id="setCompany" value="${esc(s.company)}"></div><div class="field"><label>Varsayılan Para Birimi</label><select id="setCurrency"><option ${s.currency==="TRY"?"selected":""}>TRY</option><option ${s.currency==="USD"?"selected":""}>USD</option><option ${s.currency==="EUR"?"selected":""}>EUR</option></select></div><div class="field"><label>Randevu uyarısı (dakika)</label><input id="setAlertMinutes" type="number" min="1" value="${s.alertMinutes}"></div></div><h3>Etkileşim ve Bildirim</h3>${common}`;if(settingsSection==="backup")return `<h3>Yedekleme ve Veri Merkezi</h3><p class="muted">Masaüstü uygulamasıyla aynı veritabanının tam yedeğini yönetin.</p><div class="actions"><button class="primary" data-action="export-all">Tam Yedek Al</button><button class="secondary" data-action="restore-backup">Yedeği Geri Yükle</button></div>`;if(settingsSection==="audit-settings")return `<h3>Sistem İşlem Logları</h3><p class="muted">Kullanıcı ve veri değişikliklerini denetleyin.</p><button class="primary" data-page="audit">Audit Kayıtlarını Aç</button>`;if(settingsSection==="stock-settings")return `<h3>Stok Ayarları</h3><div class="form-grid"><div class="field"><label>Varsayılan kritik stok</label><input name="default_min_stock" type="number" value="5"></div><div class="field"><label>Varsayılan kategori</label><select><option>Bilgisayar</option><option>Akıllı Ev</option><option>Güvenlik Sistemleri</option></select></div></div><button class="secondary" data-page="import">Akıllı İçe Aktarmayı Aç</button>`;if(settingsSection==="notes")return `<div class="card-head"><h3>Hızlı Not Yönetimi</h3><button class="primary" id="quickNoteAdd">＋ Hızlı Not Ekle</button></div><div id="quickNotesHost">${empty("Notlar yükleniyor","Masaüstü hızlı notları okunuyor.")}</div>`;if(settingsSection==="locale"||settingsSection==="theme")return `<h3>${settingsSection==="locale"?"Dil, Tarih & Para Birimi":"Temalar & Yazı Tipi"}</h3>${common}`;const title=settingsGroups.flatMap(g=>g[1]).find(x=>x[0]===settingsSection)?.[2]||"Ayarlar";return `<h3>${title}</h3><p class="muted">Bu modül masaüstü ayar anahtarlarını kullanır. Değişiklikler ortak veritabanına kaydedilir.</p><div class="form-grid"><div class="field full"><label>Yapılandırma</label><textarea id="setModuleValue" placeholder="${esc(title)} yapılandırması"></textarea></div></div>`}
const settingsDefinitions={
 company:{title:"Firma Ayarları",description:"Firma iletişim, sosyal medya, sözleşme, logo ve proforma bilgileri.",fields:[["company_name","Firma Adı","text","AYEC Pro"],["site_title","Uygulama Başlığı","text","Servis Yönetimi"],["company_email","E-posta","email",""],["company_phone","Telefon","tel",""],["company_gsm","GSM","tel",""],["company_fax","Faks","text",""],["company_website","Web Sitesi","url",""],["company_address","Adres","textarea",""],["social_facebook","Facebook","text",""],["social_instagram","Instagram","text",""],["social_youtube","YouTube","text",""],["cargo_company","Kargo Firması","text",""],["cargo_deal_no","Kargo Anlaşma No","text",""],["stock_prefix","Stok Öneki","text","TO"],["currency_precision","Kur Hassasiyeti","number","2"],["logo_path","Firma Logosu Yolu","text",""],["background_image","Masaüstü Arkaplanı","text",""],["proforma_template_path","Proforma Şablonu","text",""],["proforma_field_rects","Proforma Alan Yerleşimi (JSON)","textarea","{}"],["service_contract","Servis Sözleşmesi","textarea",""],["offer_contract","Teklif Sözleşmesi","textarea",""],["marquee_text","Kayan Yazı","textarea",""],["online_payment_active","Online ödeme aktif","checkbox","1"]]},
 locale:{title:"Dil, Tarih & Para Birimi",fields:[["app_lang","Uygulama Dili","select","Türkçe (TR)",["Türkçe (TR)","English (EN)"]],["date_format","Tarih Formatı","select","GG.AA.YYYY (31.12.2025)",["GG.AA.YYYY (31.12.2025)","YYYY-AA-GG (2025-12-31)"]],["default_currency","Aktif Para Birimi","select","TRY",["TRY","USD","EUR"]],["currency_format","Sayı Formatı","select","1.234,56 (TR Standart)",["1.234,56 (TR Standart)","1,234.56 (US)"]],["timezone","Saat Dilimi","select","(UTC+03:00) İstanbul",["(UTC+03:00) İstanbul","UTC"]]]},
 theme:{title:"Temalar & Yazı Tipi",fields:[["color_theme_full","Uygulama Teması","select","AYEC",["AYEC","Light","Dark","Classic"]],["appearance_mode","Görünüm Modu","select","modern",["modern","classic","compact"]],["nav_mode","Navigasyon Düzeni","select","sol_menu",["sol_menu","ust_menu"]],["display_profile","Ekran Profili","select","auto",["auto","laptop","large"]],["custom_accent_color","Özel Vurgu Rengi","color","#6558e8"],["custom_text_color","Özel Metin Rengi","color","#161927"],["combo_auto_popup","ComboBox otomatik açılsın","checkbox","0"],["show_feature_info","Özellikleri kayan yazıda göster","checkbox","1"],["enable_right_click","Genel sağ tık menüsü","checkbox","1"],["ticker_text","Duyuru Şeridi","textarea",""]]},
 integrations:{title:"Entegrasyonlar & API",description:"SMS, e-posta, WhatsApp, Telegram ve yapay zekâ bağlantıları.",fields:[["sms_username","SMS Kullanıcı Adı","text",""],["sms_password","SMS Şifresi","password",""],["sms_title","SMS Başlığı","text",""],["sms_active","SMS Aktif","checkbox","0"],["smtp_server","SMTP Sunucu","text","smtp.gmail.com"],["smtp_port","SMTP Port","number","587"],["smtp_email","SMTP E-posta","email",""],["smtp_password","SMTP Şifre","password",""],["whatsapp_number","WhatsApp Numarası","tel",""],["whatsapp_api_key","WhatsApp API Anahtarı","password",""],["whatsapp_active","WhatsApp Aktif","checkbox","0"],["telegram_bot_token","Telegram Bot Token","password",""],["gemini_api_key","Gemini API Anahtarı","password",""]]},
 cargo:{title:"Kargo Firma Ayarları",fields:[["cargo_default_company","Varsayılan Kargo","select","Yurtiçi",["Yurtiçi","Aras","MNG","Sürat","PTT"]],["cargo_branch_code","Şube Kodu","text",""],["cargo_sender_name","Gönderici Adı","text",""],["cargo_sender_phone","Gönderici Telefonu","tel",""],["cargo_delivery_days","Tahmini Teslim Günü","number","3"],["cargo_auto_track","Takip numarasını otomatik doğrula","checkbox","1"],["cargo_sms_notify","Kargo çıkışında SMS gönder","checkbox","0"],["cargo_require_receiver","Teslim alacak kişi zorunlu","checkbox","1"]]},
 "stock-settings":{title:"Stok Ayarları",fields:[["stock_min_level","Minimum Stok Seviyesi","number","5"],["stock_reorder_days","Sipariş Öneri Süresi","number","7"],["stock_default_profit_pct","Varsayılan Kâr Yüzdesi","number","20"],["stock_code_prefix","Stok Kod Öneki","text","STK"],["stock_auto_code","Otomatik stok kodu","checkbox","1"],["stock_warn_negative","Negatif stok uyarısı","checkbox","1"],["stock_sync_finance","Finansla senkronize et","checkbox","1"]]},
 backup:{title:"Yedekleme ve Veri Merkezi",fields:[["backup_server_ip","Yedek Sunucu","text","85.117.239.60:8000"],["backup_daily_enabled","Günlük otomatik yedek","checkbox","0"],["backup_daily_time","Yedek Saati","time","12:00"],["backup_auto_morning","Sabah otomatik yedeği","checkbox","0"],["backup_auto_evening","Akşam otomatik yedeği","checkbox","0"],["backup_on_exit","Çıkışta yedek al","checkbox","1"]]},
 license:{title:"Lisans Durumu",fields:[["license_key","Lisans Anahtar\u0131","text",""],["license_code","Lisans Kodu","text",""],["license_expires","Biti\u015f Tarihi","date",""]]},
 security:{title:"Güvenlik Ayarları",description:"Boş bırakılan şifre alanları mevcut şifreyi değiştirmez.",fields:[["app_password","Yeni Uygulama Şifresi","password",""],["tech_password","Yeni Teknisyen Şifresi","password",""],["admin_pass","Yeni Yönetici Şifresi","password",""],["security_question","Güvenlik Sorusu","text",""],["security_answer_new","Yeni Güvenlik Yanıtı","password",""],["app_lock_active","Uygulama kilidi","checkbox","0"],["tech_lock_active","Teknisyen kilidi","checkbox","0"],["auto_login","Otomatik giriş","checkbox","0"]]},
 remote:{title:"AYEC Pro Uzak Bağlantı",fields:[["remote_server_ip","Sunucu IP","text","85.117.239.60"],["remote_server_port","Sunucu Portu","number","5000"],["remote_enabled","Uzak bağlantı aktif","checkbox","1"],["remote_logging","Bağlantı logları","checkbox","1"]]},
 "sms-settings":{title:"SMS Ayarları",fields:[["sms_username","Kullanıcı Adı","text",""],["sms_password","Şifre","password",""],["sms_title","Gönderici Başlığı","text",""],["loop_repaired","Onarıldı tekrar sayısı","number","0"],["loop_approval","Onay tekrar sayısı","number","0"],["loop_parts","Parça bekliyor tekrar sayısı","number","0"],["loop_testing","Test tekrar sayısı","number","0"],["loop_done","Tamamlandı tekrar sayısı","number","0"],["sms_active","SMS servisi aktif","checkbox","0"]]},
 "smtp-settings":{title:"E-posta / SMTP",fields:[["smtp_server","SMTP Sunucu","text","smtp.gmail.com"],["smtp_port","Port","number","587"],["smtp_email","E-posta","email",""],["smtp_password","Uygulama Şifresi","password",""]]},
 messaging:{title:"WhatsApp & Telegram",fields:[["whatsapp_number","WhatsApp Numarası","tel",""],["whatsapp_mode","WhatsApp gönderim modu","select","disabled",["disabled","cloud_api","provider_api","desktop_manual"]],["whatsapp_cloud_phone_id","Meta Cloud phone ID","text",""],["whatsapp_cloud_token","Meta Cloud access token","password",""],["whatsapp_cloud_template","Cloud sablon adi","text","payment_reminder_tr"],["twilio_account_sid","Saglayici Account SID","text",""],["twilio_auth_token","Saglayici Auth Token","password",""],["twilio_whatsapp_from","Saglayici gonderici","text",""],["whatsapp_payment_reminder_enabled","Haftalik odeme hatirlatmasi","checkbox","0"],["whatsapp_payment_reminder_day","Hatirlatma gunu","number","4"],["whatsapp_payment_reminder_time","Hatirlatma saati","time","10:00"],["whatsapp_payment_min_debt_try","Asgari borc (TRY)","number","0"],["whatsapp_payment_template","Odeme sablonu","textarea","Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."],["whatsapp_api_key","WhatsApp API Anahtarı","password",""],["whatsapp_admin_phone","Yönetici WhatsApp","tel",""],["whatsapp_api_token","WhatsApp API Token","password",""],["telegram_bot_token","Telegram Bot Token","password",""],["whatsapp_active","WhatsApp aktif","checkbox","0"]]},
 "ai-settings":{title:"Gemini / AI Ayarları",fields:[["gemini_api_key","Gemini API Anahtarı","password",""],["gemini_model","Gemini Modeli","text","gemini-2.0-flash"],["gemini_available_models_cache","Model Önbelleği","textarea",""]]},
 "voice-settings":{title:"Sesli Asistan ve Zamanlanmış Uyarılar",fields:[["asistan_user_name","Kullanıcı Hitabı","text","Efendim"],["asistan_ozel_adi","Asistan Adı","text","AYEC"],["asistan_edge_voice","Ses","text","tr-TR-AhmetNeural"],["asistan_edge_pitch","Ton","text","-5Hz"],["asistan_edge_rate","Hız","text","+0%"],["asistan_tts_engine","TTS Motoru","select","auto",["auto","edge","system"]],["quiet_hours_start","Sessiz Saat Başlangıcı","time","19:00"],["quiet_hours_end","Sessiz Saat Bitişi","time","08:30"],["voice_assistant_active","Sesli asistan aktif","checkbox","1"],["jarvis_enabled","JARVIS modu aktif","checkbox","0"],["asistan_voice_enabled","Sesli yanıt aktif","checkbox","1"],["telsiz_efekti_aktif","Telsiz efekti","checkbox","0"],["asistan_hitap_aktif","Özel hitap","checkbox","0"],["critical_override_dnd","Kritik uyarı sessiz modu aşsın","checkbox","0"]]},
 "bank-settings":{title:"Banka Ayarları",fields:[["bank_default_name","Varsayılan Banka","text",""],["bank_default_iban","Varsayılan IBAN","text",""],["bank_default_currency","Para Birimi","select","TRY",["TRY","USD","EUR"]],["bank_fx_update_minutes","Kur Güncelleme Süresi","number","60"],["bank_auto_fx","Otomatik kur güncelle","checkbox","1"],["bank_sync_finance","Finansla eşleştir","checkbox","1"],["bank_warn_negative","Negatif bakiye uyarısı","checkbox","1"]]},
 numbering:{title:"Belge Numaraları",fields:[["service_number_prefix","Servis Öneki","text","SRV"],["service_number_next","Sonraki Servis No","number","1"],["job_number_prefix","İş Emri Öneki","text","IS"],["job_number_next","Sonraki İş Emri No","number","1"],["payment_number_prefix","Tahsilat Öneki","text","THS"],["payment_number_next","Sonraki Tahsilat No","number","1"],["project_number_prefix","Proje Öneki","text","PRJ"],["project_number_next","Sonraki Proje No","number","1"],["reference_number_prefix","Referans Öneki","text","REF"],["reference_number_next","Sonraki Referans No","number","1"]]},
 location:{title:"Harita & Konum",fields:[["map_default_lat","Varsayılan Enlem","number","39.6484"],["map_default_lng","Varsayılan Boylam","number","27.8826"]]},
 identity:{title:"Sistem Kimli\u011fi & Mod\u00fcler Yap\u0131",scope:"internal_settings",fields:[["module_operations_active","Operasyon Mod\u00fcl\u00fc","checkbox","1"],["module_finance_active","Finans Mod\u00fcl\u00fc","checkbox","1"],["module_stock_active","Stok Mod\u00fcl\u00fc","checkbox","1"],["module_projects_active","Projeler Mod\u00fcl\u00fc","checkbox","1"],["module_crm_active","CRM Mod\u00fcl\u00fc","checkbox","1"],["module_personnel_active","Personel Mod\u00fcl\u00fc","checkbox","1"],["feature_right_click_active","Sa\u011f T\u0131k \u00d6zelli\u011fi","checkbox","1"],["feature_double_click_active","\u00c7ift T\u0131klama \u00d6zelli\u011fi","checkbox","1"]]}
};
settingsDefinitions.integrations.fields.splice(7,0,["smtp_username","SMTP Kullanıcı Adı","text",""]);
settingsDefinitions["smtp-settings"].fields.splice(3,0,["smtp_username","SMTP Kullanıcı Adı","text",""]);
function exactSettingsField(field,scope){const [key,label,type,defaultValue,options]=field,source=scope==="internal_settings"?desktopInternalSettings:desktopSettings,value=type==="password"?"":source[key]??defaultValue,attrs=`data-setting-key="${key}" data-setting-scope="${scope}"`;if(type==="checkbox")return `<div class="setting"><div><strong>${label}</strong><br><small class="muted">Masaüstü ayarı: ${key}</small></div><input class="switch exact-setting" ${attrs} type="checkbox" ${String(value)==="1"||String(value)==="true"?"checked":""}></div>`;if(type==="textarea")return `<div class="field full"><label>${label}</label><textarea class="exact-setting" ${attrs}>${esc(value)}</textarea></div>`;if(type==="select")return `<div class="field"><label>${label}</label><select class="exact-setting" ${attrs}>${options.map(option=>`<option value="${esc(option)}" ${String(value)===String(option)?"selected":""}>${esc(option)}</option>`).join("")}</select></div>`;return `<div class="field"><label>${label}</label><input class="exact-setting" ${attrs} type="${type}" value="${esc(value)}" ${type==="password"?'autocomplete="new-password" placeholder="Boş bırakırsanız değişmez"':""}></div>`}
const baseSettingBody=settingBody;settingBody=function(s){if(settingsSection==="users")return `<div class="card-head"><div><h3>Kullanıcı Yönetimi</h3><p class="muted">Masaüstü kullanıcı, rol, aktiflik ve arayüz yetkileri.</p></div></div><div id="settingsUsersHost">${empty("Kullanıcılar yükleniyor","Ortak kullanıcı tablosu okunuyor.")}</div>`;const definition=settingsDefinitions[settingsSection];if(!definition)return baseSettingBody(s);const scope=definition.scope||"settings",regular=definition.fields.filter(f=>f[2]!=="checkbox"),toggles=definition.fields.filter(f=>f[2]==="checkbox");return `<h3>${definition.title}</h3>${definition.description?`<p class="muted">${definition.description}</p>`:""}<div class="form-grid">${regular.map(f=>exactSettingsField(f,scope)).join("")}</div>${toggles.length?`<div class="settings-grid" style="margin-top:18px">${toggles.map(f=>exactSettingsField(f,scope)).join("")}</div>`:""}${settingsSection==="backup"?'<div class="actions" style="margin-top:18px"><button class="secondary" data-action="export-all">Şimdi Yedekle</button><button class="secondary" data-action="restore-backup">Yedeği Geri Yükle</button></div>':""}`};
function renderSettings(){const s=db.settings,mobileSettings=settingsGroups.flatMap(([,items])=>items).map(([id,,label])=>`<option value="${id}" ${settingsSection===id?"selected":""}>${label}</option>`).join("");return `${pageHead("Ayarlar","Masaüstü uygulamasındaki ayar modülleri ve ortak veri merkezi.",'<button class="primary" data-action="save-settings">Ayarları Kaydet</button>')}<div class="settings-layout"><div class="settings-mobile-picker"><label for="settingsMobileSelect">Ayar bölümü</label><select id="settingsMobileSelect">${mobileSettings}</select></div><aside class="settings-sidebar"><input class="control" id="settingsSearch" placeholder="Ayarlarda ara…">${settingsGroups.map(([group,items])=>`<small>${group}</small>${items.map(([id,icon,label])=>`<button data-settings-section="${id}" class="${settingsSection===id?"active":""}">${icon} ${label}</button>`).join("")}`).join("")}</aside><section class="card settings-content">${settingBody(s)}</section></div><div hidden><input id="setCompany" value="${esc(s.company)}"><input id="setCurrency" value="${s.currency}"><input id="setAlertMinutes" value="${s.alertMinutes}"><input id="setDouble" type="checkbox" ${s.doubleClick?"checked":""}><input id="setContext" type="checkbox" ${s.contextMenu?"checked":""}><input id="setAlerts" type="checkbox" ${s.appointmentAlerts?"checked":""}><input id="setCompact" type="checkbox" ${s.compact?"checked":""}></div>`}

function genericShell(meta){return `${pageHead(meta.title,meta.description,'<button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-generic-add>＋ Yeni Kayıt</button>')}<section class="card"><div class="toolbar"><input class="control search" id="genericSearch" placeholder="Bu modülde ara…"><span class="muted" id="genericCount">Yükleniyor…</span></div><div id="genericHost">${empty("Veriler yükleniyor","Masaüstü veritabanı okunuyor.")}</div></section>`}
function columnLabel(name){return ({id:"NO",name:"AD",customer_name:"MÜŞTERİ",customer_id:"MÜŞTERİ NO",phone:"TELEFON",email:"E-POSTA",type:"TÜR",status:"DURUM",date:"TARİH",time:"SAAT",created_at:"OLUŞTURMA",description:"AÇIKLAMA",amount:"TUTAR",currency:"DÖVİZ",stock:"STOK",price:"FİYAT",category:"KATEGORİ",title:"BAŞLIK",role:"ROL"}[name]||name.replaceAll("_"," ").toLocaleUpperCase("tr-TR"))}
function genericValue(value,key){if(value===null||value===undefined||value==="")return '<span class="muted">—</span>';if(key==="status"||key==="type")return statusBadge(value);if(typeof value==="string"&&value.length>100)return esc(value.slice(0,100))+"…";return esc(value)}
function genericTable(meta,data){const preferred=["id","tracking_no","name","title","customer_name","phone","type","category","status","date","time","amount","currency","stock","price","description","created_at"];let columns=preferred.filter(c=>data.columns.includes(c)&&data.rows.some(r=>r[c]!==null&&r[c]!==""));for(const c of data.columns){if(columns.length>=9)break;if(!columns.includes(c)&&!c.includes("password")&&!c.includes("token")&&!c.includes("secret")&&!c.includes("photo"))columns.push(c)}return `<div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${columnLabel(c)}</th>`).join("")}<th>İŞLEMLER</th></tr></thead><tbody>${data.rows.map((row,index)=>`<tr tabindex="0" data-kind="generic" data-id="${index}" data-generic-row="${index}">${columns.map(c=>`<td>${genericValue(row[c],c)}</td>`).join("")}<td><button class="mini generic-edit" data-index="${index}">Düzenle</button> <button class="mini generic-delete" data-index="${index}">Sil</button></td></tr>`).join("")}</tbody></table></div>`}
async function loadGenericModule(meta,q=""){const host=$("#genericHost");if(!host)return;try{const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=500&q=${encodeURIComponent(q)}`);window.currentGenericData=data;window.currentGenericMeta=meta;host.innerHTML=data.rows.length?genericTable(meta,data):empty("Kayıt bulunamadı","Masaüstü veritabanında bu modüle ait kayıt yok.");$("#genericCount").textContent=`Toplam Kayıt: ${data.count}`;$$('.generic-edit').forEach(b=>b.onclick=()=>openGenericDialog(meta,data.rows[+b.dataset.index],data.columns));$$('.generic-delete').forEach(b=>b.onclick=()=>deleteGenericRow(meta,data.rows[+b.dataset.index]));$$('[data-generic-row]').forEach(tr=>{tr.ondblclick=()=>openGenericDialog(meta,data.rows[+tr.dataset.genericRow],data.columns);bindInteractiveRow(tr)})}catch(err){host.innerHTML=empty("Modül yüklenemedi",err.message)}}
async function loadQuickNotes(){const host=$("#quickNotesHost");if(!host)return;try{const data=await apiFetch("/api/desktop/table/quick_notes?limit=200");host.innerHTML=data.rows.length?`<div class="table-wrap"><table><thead><tr><th>Grup</th><th>Etiket</th><th>Kategori</th><th>Aktif</th><th></th></tr></thead><tbody>${data.rows.map((n,i)=>`<tr><td>${esc(n.group_name)}</td><td>${esc(n.label)}</td><td>${esc(n.category)}</td><td>${n.is_active?"Evet":"Hayır"}</td><td><button class="mini quick-note-edit" data-index="${i}">Düzenle</button> <button class="mini quick-note-delete" data-index="${i}">Sil</button></td></tr>`).join("")}</tbody></table></div>`:empty("Hızlı not yok","İlk hızlı notu ekleyin.");$$('.quick-note-edit').forEach(b=>b.onclick=()=>quickNoteDialog(data.rows[+b.dataset.index]));$$('.quick-note-delete').forEach(b=>b.onclick=async()=>{const row=data.rows[+b.dataset.index];await desktopWrite("quick_notes",{id:row.id,_action:"delete"});loadQuickNotes()})}catch(err){host.innerHTML=empty("Hızlı notlar yüklenemedi",err.message)}}
function quickNoteDialog(row={}){openDialog(row.id?"Hızlı Notu Düzenle":"Hızlı Not Ekle","AYARLAR",`<div class="form-grid"><div class="field"><label>Grup</label><input name="group_name" required value="${esc(row.group_name||"")}"></div><div class="field"><label>Kategori</label><input name="category" value="${esc(row.category||"")}"></div><div class="field full"><label>Etiket / Not</label><textarea name="label" required>${esc(row.label||"")}</textarea></div><div class="field"><label>Aktif</label><select name="is_active"><option value="1" ${row.is_active!==0?"selected":""}>Evet</option><option value="0" ${row.is_active===0?"selected":""}>Hayır</option></select></div></div>`,async fd=>{const payload=Object.fromEntries(fd);if(row.id){payload.id=row.id;payload._action="update"}await desktopWrite("quick_notes",payload);loadQuickNotes();toast("Hızlı not masaüstü veritabanına kaydedildi")},row.id?"Güncelle":"Kaydet")}
async function loadSettingsUsers(){const host=$("#settingsUsersHost");if(!host)return;try{const data=await apiFetch("/api/desktop/table/users?limit=200");host.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Kullanıcı</th><th>Ad Soyad</th><th>E-posta</th><th>Rol</th><th>Aktif</th><th>Son Giriş</th><th></th></tr></thead><tbody>${data.rows.map((u,i)=>`<tr><td><strong>${esc(u.username)}</strong></td><td>${esc(u.full_name||"")}</td><td>${esc(u.email||"")}</td><td>${esc(u.role||"")}</td><td>${u.active!==0?"Evet":"Hayır"}</td><td>${esc(u.last_login||"")}</td><td><button class="mini settings-user-edit" data-index="${i}">Yetkileri Düzenle</button></td></tr>`).join("")}</tbody></table></div>`;$$('.settings-user-edit').forEach(b=>b.onclick=()=>settingsUserDialog(data.rows[+b.dataset.index]))}catch(err){host.innerHTML=empty("Kullanıcılar yüklenemedi",err.message)}}
function settingsUserDialog(user){openDialog(`${user.username} — Yetkiler`,"KULLANICI YÖNETİMİ",`<div class="form-grid"><div class="field"><label>Ad Soyad</label><input name="full_name" value="${esc(user.full_name||"")}"></div><div class="field"><label>E-posta</label><input name="email" type="email" value="${esc(user.email||"")}"></div><div class="field"><label>Rol</label><select name="role">${["admin","manager","technician","user"].map(r=>`<option ${user.role===r?"selected":""}>${r}</option>`).join("")}</select></div><div class="field"><label>Aktif</label><select name="active"><option value="1" ${user.active!==0?"selected":""}>Evet</option><option value="0" ${user.active===0?"selected":""}>Hayır</option></select></div><div class="field full"><label>Yetkiler (JSON)</label><textarea name="permissions">${esc(user.permissions||"{}")}</textarea></div><div class="field"><label>Arayüz Düzenleme</label><select name="interface_edit_access"><option value="1" ${user.interface_edit_access?"selected":""}>Açık</option><option value="0" ${!user.interface_edit_access?"selected":""}>Kapalı</option></select></div></div>`,async fd=>{const payload=Object.fromEntries(fd);payload.id=user.id;payload._action="update";await desktopWrite("users",payload);loadSettingsUsers();toast("Kullanıcı yetkileri güncellendi")},"Yetkileri Kaydet")}
function genericFieldKind(column){if(/date/.test(column))return"date";if(/time/.test(column)&&!column.includes("date"))return"time";if(/amount|price|stock|salary|balance|quantity|qty|rate|year|km|limit/.test(column))return"number";if(/description|notes|content|address|details|summary/.test(column))return"textarea";if(/email/.test(column))return"email";return"text"}
function openGenericDialog(meta,row={},columns=[]){const hidden=/^(id|created_at|updated_at|deleted_at|is_deleted|password|remember_token|secret_answer)$/;const usable=columns.filter(c=>!hidden.test(c)).slice(0,24);const fields=usable.map(c=>{const kind=genericFieldKind(c),value=row[c]??"";return kind==="textarea"?`<div class="field full"><label>${columnLabel(c)}</label><textarea name="${c}">${esc(value)}</textarea></div>`:`<div class="field"><label>${columnLabel(c)}</label><input name="${c}" type="${kind}" value="${esc(value)}"></div>`}).join("");openDialog(row.id?`${meta.title} — Düzenle`:`${meta.title} — Yeni Kayıt`,meta.group,`<div class="form-grid">${fields}</div>`,async fd=>{const payload=Object.fromEntries(fd);if(row.id){payload.id=row.id;payload._action="update"}await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify(payload)});toast("Kayıt masaüstü veritabanına işlendi");loadGenericModule(meta,$("#genericSearch")?.value||"")},row.id?"Güncelle":"Kaydet")}
async function deleteGenericRow(meta,row){if(!confirm("Bu kayıt silinsin mi?"))return;await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify({id:row.id,_action:"delete"})});toast("Kayıt silindi","warning");loadGenericModule(meta,$("#genericSearch")?.value||"")}
function dialogCatalogShell(){return `${pageHead("Dialog Modülleri","Masaüstü kaynaklarından çıkarılan tüm alan, buton ve sinyal bağlantıları.",'<span class="badge" id="dialogSummary">Yükleniyor…</span>')}<section class="card"><div class="toolbar"><input class="control search" id="dialogCatalogSearch" placeholder="Dialog, sınıf veya dosya ara…"></div><div id="dialogCatalog" class="dialog-catalog"></div></section>`}
async function loadDialogCatalog(){const host=$("#dialogCatalog");if(!host)return;try{const data=await apiFetch('/api/desktop/dialogs');window.desktopDialogManifest=data;$("#dialogSummary").textContent=`${data.summary.dialog_count} dialog · ${data.summary.connection_count} sinyal`;const draw=q=>{const term=q.toLocaleLowerCase("tr-TR");const list=data.dialogs.filter(d=>[d.title,d.key,d.file,...(d.classes||[]).map(c=>c.name)].join(" ").toLocaleLowerCase("tr-TR").includes(term));host.innerHTML=list.map((d,i)=>`<button class="dialog-module" data-dialog-key="${esc(d.key)}"><strong>${esc(d.title||d.key)}</strong><small>${esc(d.file)}</small><span>${d.counts.buttons} buton · ${d.counts.fields} alan · ${d.counts.connections} sinyal</span></button>`).join("");$$('[data-dialog-key]').forEach(b=>b.onclick=()=>openManifestDialog(data.dialogs.find(d=>d.key===b.dataset.dialogKey)))};draw("");$("#dialogCatalogSearch").oninput=e=>draw(e.target.value)}catch(err){host.innerHTML=empty("Dialog manifesti yüklenemedi",err.message)}}
function manifestInput(field){const label=field.label||field.name,kind=field.kind;if(kind==="textarea")return `<div class="field full"><label>${esc(label)}</label><textarea name="${esc(field.name)}"></textarea></div>`;if(kind==="checkbox"||kind==="radio")return `<div class="field"><label><input name="${esc(field.name)}" type="checkbox"> ${esc(label)}</label></div>`;if(kind==="table"||kind==="list")return `<div class="field full"><label>${esc(label)}</label><div class="dialog-placeholder">${kind==="table"?"Tablo":"Liste"} yüzeyi</div></div>`;const type={number:"number",decimal:"number",date:"date",time:"time",datetime:"datetime-local"}[kind]||"text";return `<div class="field"><label>${esc(label)}</label><input name="${esc(field.name)}" type="${type}" value="${esc(field.default||"")}"></div>`}
function openManifestDialog(dialog){const key=dialog.key;const direct={add_customer_dialog:()=>openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle"),add_stock_dialog:()=>openDialog("Ürün Ekle","STOK KARTI",productForm(),fd=>saveProduct(fd),"Ürün Ekle"),payment_dialog:()=>customerSelect(paymentDialog,"Tahsilat için müşteri seçin"),tahsilat_dialog:()=>customerSelect(paymentDialog,"Tahsilat için müşteri seçin"),bulk_payment_dialog:()=>customerSelect(paymentDialog,"Toplu tahsilat için müşteri seçin"),new_service_dialog:()=>serviceDialog(),technical_service_new_service_dialog:()=>serviceDialog(),automotive_new_service_dialog:()=>serviceDialog(),add_device_dialog:()=>serviceDialog(),customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),technical_customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),automotive_customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),stock_smart_import_dialog:()=>navigate("import"),stock_import_preview_dialog:()=>navigate("import"),service_import_preview_dialog:()=>navigate("import"),quick_sale_dialog:()=>navigate("sales"),technician_panel:()=>navigate("technician"),technical_service_technician_panel:()=>navigate("technician"),automotive_technician_panel:()=>navigate("technician")};if(direct[key])return direct[key]();const fields=(dialog.fields||[]).slice(0,40).map(manifestInput).join("");const signals=(dialog.connections||[]).map(c=>`<tr><td>${esc(c.owner)}</td><td>${esc(c.signal)}</td><td>${esc(c.callback)}</td></tr>`).join("");openDialog(dialog.title||dialog.key,"MASAÜSTÜ DIALOG PORTU",`<div class="tabs"><button type="button" class="tab active">Form</button><button type="button" class="tab">Sinyaller (${dialog.counts.connections})</button></div><div class="form-grid">${fields||empty("Form alanı yok","Bu modül bileşik veya salt görüntüleme dialogudur.")}</div><details style="margin-top:18px"><summary>Sinyal bağlantıları</summary><div class="table-wrap"><table><thead><tr><th>Sahip</th><th>Sinyal</th><th>Callback</th></tr></thead><tbody>${signals}</tbody></table></div></details>`,()=>{toast(`${dialog.title} form sinyali yakalandı`)},"Kaydet / Uygula");$("#dialogFooter").insertAdjacentHTML("afterbegin",(dialog.buttons||[]).slice(0,8).map(b=>`<button type="button" class="secondary manifest-button" title="${esc(b.connections?.map(x=>x.callback).join(', ')||'')}">${esc(b.label)}</button>`).join(""));$$('.manifest-button').forEach(b=>b.onclick=()=>toast(`${b.textContent} sinyali çalıştırıldı`))}
function customerSelect(callback,title){openDialog(title,"MÜŞTERİ SEÇİMİ",`<div class="field"><label>Müşteri</label><select id="dialogCustomerSelect" required>${db.customers.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></div>`,()=>{const customer=db.customers.find(c=>String(c.id)===String($("#dialogCustomerSelect").value));setTimeout(()=>callback(customer),80)},"Devam")}
 function render(){const nav=$("#nav"),navScrollTop=nav?.scrollTop||0;document.body.dataset.page=page;const routes={dashboard:renderDashboard,customers:renderCustomers,appointments:renderAppointments,stock:renderStock,movements:renderMovements,import:renderImport,sales:renderSales,services:renderServices,technician:renderTechnician,finance:()=>renderFinance(""),income:()=>renderFinance("Gelir"),expense:()=>renderFinance("Gider"),settings:renderSettings,"dialog-catalog":dialogCatalogShell};const route=routes[page],meta=genericModules[page];$("#content").innerHTML=route?route():meta?genericShell(meta):renderDashboard();bindPage();if(meta){$("#genericSearch").oninput=e=>loadGenericModule(meta,e.target.value);$("[data-generic-refresh]").onclick=()=>loadGenericModule(meta,$("#genericSearch").value);$("[data-generic-add]").onclick=async()=>{const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=1`);openGenericDialog(meta,{},data.columns)};loadGenericModule(meta)}if(page==="dialog-catalog")loadDialogCatalog();if(nav)nav.scrollTop=navScrollTop}

function toast(message,type="success",duration=3500){const el=document.createElement("div");el.className=`toast ${type}`;el.innerHTML=`<span>${type==="success"?"✓":type==="warning"?"!":"×"}</span><div>${esc(message)}</div>`;$("#toastRoot").append(el);setTimeout(()=>el.remove(),duration)}
function openDialog(title,eyebrow,body,onSubmit,submitLabel="Kaydet"){const dialog=$("#appDialog");$("#dialogTitle").textContent=title;$("#dialogEyebrow").textContent=eyebrow;$("#dialogBody").innerHTML=body;$("#dialogFooter").innerHTML=`<button type="button" id="dialogCancel" class="secondary">Vazgeç</button><button type="submit" class="primary" id="dialogSubmit">${submitLabel}</button>`;$("#dialogClose").onclick=()=>dialog.close("cancel");$("#dialogCancel").onclick=()=>dialog.close("cancel");const form=$("#dialogForm");form.onsubmit=async e=>{e.preventDefault();const submit=$("#dialogSubmit");try{submit.disabled=true;submit.dataset.label=submit.textContent;submit.textContent="Kaydediliyor…";const ok=await onSubmit?.(new FormData(form));if(ok!==false&&dialog.open)dialog.close("ok")}catch(err){toast(err.message||"İşlem tamamlanamadı","error")}finally{if(dialog.open){submit.disabled=false;submit.textContent=submit.dataset.label||submitLabel}}};dialog.showModal();setTimeout(()=>$("input,select,textarea",$("#dialogBody"))?.focus(),30)}

function customerForm(c={}){return `<div class="form-grid"><div class="field full"><label>Müşteri / Firma Adı *</label><input name="name" required value="${esc(c.name||"")}"></div><div class="field"><label>Telefon</label><input name="phone" value="${esc(c.phone||"")}"></div><div class="field"><label>E-posta</label><input name="email" type="email" value="${esc(c.email||"")}"></div><div class="field"><label>Tür</label><select name="type"><option ${c.type==="Bireysel"?"selected":""}>Bireysel</option><option ${c.type==="Kurumsal"?"selected":""}>Kurumsal</option></select></div><div class="field"><label>TRY Bakiye</label><input name="TRY" type="number" step=".01" value="${c.balances?.TRY||0}"></div><div class="field"><label>USD Bakiye</label><input name="USD" type="number" step=".01" value="${c.balances?.USD||0}"></div><div class="field"><label>EUR Bakiye</label><input name="EUR" type="number" step=".01" value="${c.balances?.EUR||0}"></div></div>`}
function saveCustomer(fd,c){const data=Object.fromEntries(fd);const target=c||{id:uid("cus"),services:[],quotes:[]};Object.assign(target,{name:data.name,phone:data.phone,email:data.email,type:data.type,balances:{TRY:+data.TRY||0,USD:+data.USD||0,EUR:+data.EUR||0}});if(!c)db.customers.push(target);const payload={name:data.name,phone:data.phone,email:data.email,type:data.type};if(c&&Number.isInteger(+c.id)){payload.id=+c.id;payload._action="update"}desktopWrite("customers",payload).then(result=>{if(!c&&result?.id)target.desktopId=result.id});save();activity(`${target.name} müşteri kaydı ${c?"güncellendi":"oluşturuldu"}`,"♙");toast("Müşteri kaydedildi");render()}

function productForm(s={}){const categories=sectorStockCategories();if(s.category&&!categories.includes(s.category))categories.push(s.category);return `<div class="form-grid"><div class="field"><label>Stok Kodu *</label><input name="code" required value="${esc(s.code||"")}"></div><div class="field"><label>Barkod</label><input name="barcode" value="${esc(s.barcode||"")}"></div><div class="field full"><label>Ürün Adı *</label><input name="name" required value="${esc(s.name||"")}"></div><div class="field"><label>Kategori</label><select name="category">${categories.map(x=>`<option ${s.category===x?"selected":""}>${x}</option>`).join("")}</select></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(x=>`<option ${s.currency===x?"selected":""}>${x}</option>`).join("")}</select></div><div class="field"><label>Stok Adedi</label><input name="qty" type="number" min="0" value="${s.qty??0}"></div><div class="field"><label>Minimum Stok</label><input name="min" type="number" min="0" value="${s.min??0}"></div><div class="field"><label>Alış Fiyatı</label><input name="buy" type="number" min="0" step=".01" value="${s.buy??0}"></div><div class="field"><label>Satış Fiyatı</label><input name="sell" type="number" min="0" step=".01" value="${s.sell??0}"></div></div>`}
function saveProduct(fd,s){const d=Object.fromEntries(fd),target=s||{id:uid("stk")};const old=s?.qty||0;Object.assign(target,{code:d.code,name:d.name,barcode:d.barcode,category:d.category,currency:d.currency,qty:+d.qty||0,min:+d.min||0,buy:+d.buy||0,sell:+d.sell||0});if(!s)db.stock.push(target);const payload={name:d.name,code:d.code,barcode:d.barcode,category:d.category,currency:d.currency,stock:+d.qty||0,min_stock:+d.min||0,purchase_price:+d.buy||0,price:+d.sell||0};if(s&&Number.isInteger(+s.id)){payload.id=+s.id;payload._action="update"}desktopWrite("parts",payload);const diff=target.qty-old;if(diff){db.movements.unshift({id:uid("mov"),date:new Date().toLocaleString("tr-TR"),product:target.name,type:diff>0?"Giriş":"Çıkış",qty:Math.abs(diff),ref:s?"STOK-DÜZENLE":"ÜRÜN-EKLE",user:"Yönetici"});if(Number.isInteger(+target.id))desktopWrite("stock_movements",{part_id:+target.id,movement_type:diff>0?"Giriş":"Çıkış",amount:Math.abs(diff),new_stock:target.qty,description:s?"Stok düzenleme":"Ürün ekleme"})}save();activity(`${target.name} stok kartı kaydedildi`,"◫");toast("Ürün ve stok hareketi kaydedildi");render()}

async function deleteProduct(product){if(!product)return;if(!confirm(`“${product.name}” stok kartı silinsin mi? Bu işlem yanlış içe aktarılan ürünü de kaldırır.`))return;try{if(Number.isInteger(+product.id))await desktopWrite("parts",{id:+product.id,_action:"delete"});db.stock=db.stock.filter(item=>String(item.id)!==String(product.id));save();activity(`${product.name} stok kartı silindi`,"×");toast("Stok kartı silindi","success");render()}catch(error){toast(`Ürün silinemedi: ${error.message}`,"error")}}

function customerActions(id){const c=db.customers.find(x=>x.id===id);if(!c)return;openDialog(`${c.name} — İşlemler`,"MÜŞTERİ İŞLEM MERKEZİ",`<div class="product-picker"><button class="product-tile" type="button" data-modal-action="payment"><span><strong>Tahsilat Al</strong><br><small class="muted">3 dövizle cari hareket</small></span><span>₺</span></button><button class="product-tile" type="button" data-modal-action="360"><span><strong>Müşteri 360</strong><br><small class="muted">Servis ve proforma geçmişi</small></span><span>○</span></button><button class="product-tile" type="button" data-modal-action="service"><span><strong>Yeni Servis Kaydı</strong><br><small class="muted">Cihaz kabul formu</small></span><span>⚒</span></button><button class="product-tile" type="button" data-modal-action="print"><span><strong>Yazdır</strong><br><small class="muted">Cari hesap özeti</small></span><span>▤</span></button><button class="product-tile" type="button" data-modal-action="edit"><span><strong>Düzenle</strong><br><small class="muted">Müşteri bilgileri</small></span><span>✎</span></button></div>`,()=>true,"Kapat");$$('[data-modal-action]').forEach(b=>b.onclick=()=>{const a=b.dataset.modalAction;$("#appDialog").close();if(a==="payment")paymentDialog(c);if(a==="360")customer360(c);if(a==="service")serviceDialog(c.id);if(a==="print"){printCustomer(c)}if(a==="edit")openDialog("Müşteriyi Düzenle","CRM",customerForm(c),fd=>saveCustomer(fd,c),"Güncelle")})}
function paymentDialog(c){openDialog("Tahsilat Al","CARİ HAREKET",`<div class="form-grid"><div class="field full"><label>Müşteri</label><input disabled value="${esc(c.name)}"></div><div class="field"><label>Tutar *</label><input name="amount" type="number" min=".01" step=".01" required></div><div class="field"><label>Para Birimi</label><select name="currency"><option>TRY</option><option>USD</option><option>EUR</option></select></div><div class="field full"><label>Açıklama</label><textarea name="description">Müşteri tahsilatı</textarea></div></div>`,fd=>{const d=Object.fromEntries(fd),amount=+d.amount;c.balances[d.currency]=(c.balances[d.currency]||0)-amount;db.finance.unshift({id:uid("fin"),date:today(),type:"Gelir",category:"Tahsilat",amount,currency:d.currency,description:d.description,customer:c.name});desktopWrite("accounting",{type:"Gelir",category:"Tahsilat",amount,original_amount:amount,try_equivalent:amount,currency:d.currency,exchange_rate:1,description:d.description,date:today(),customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name,payment_method:"Web"});save();activity(`${c.name} müşterisinden ${money(amount,d.currency)} tahsil edildi`,"₺");toast("Tahsilat cari ve finans kayıtlarına işlendi");render()},"Tahsilatı Kaydet")}
function customer360(c){
 const services=c.services||[],offers=c.quotes||[],finance=db.finance.filter(f=>f.customer===c.name);
 const turnover=finance.filter(f=>f.type==="Gelir").reduce((a,f)=>a+moneyNumber(f.amount),0);
 const active=services.filter(s=>!["Tamamlandı","Teslim Edildi","İptal","Bitti"].includes(s.status)).length;
 const serviceTable=services.length?`<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Cihaz / Detay</th><th>Durum</th><th>Tutar</th><th>Ödeme</th></tr></thead><tbody>${services.map(s=>`<tr><td>${esc(s.date)}</td><td><strong>${esc(s.device)}</strong><br><small class="muted">${esc(s.no)} · ${esc(s.note)}</small></td><td>${statusBadge(s.status)}</td><td>${money(s.amount||0,s.currency||"TRY")}</td><td><button type="button" class="mini c360-pay">Ödeme Al</button></td></tr>`).join("")}</tbody></table></div>`:empty("Servis geçmişi yok","Bu müşteriye ait servis kaydı bulunmuyor.");
 const cari=finance.length?`<div class="table-wrap"><table><thead><tr><th>Tarih / Zaman</th><th>İşlem / Ürün Detayı</th><th>Döviz</th><th>Kur</th><th>Tutar</th><th>Durum</th><th>Ödeme</th></tr></thead><tbody>${finance.map(f=>`<tr><td>${esc(f.date)}</td><td>${esc(f.description)}</td><td>${esc(f.currency)}</td><td>1,0000</td><td>${money(f.amount,f.currency)}</td><td>${statusBadge(f.type)}</td><td>—</td></tr>`).join("")}</tbody></table></div>`:empty("Cari işlem geçmişi yok","Bu müşteriye ait finans hareketi bulunmuyor.");
 const ledger=["TRY","USD","EUR"].map(cur=>`<tr><td>${new Date().toLocaleDateString("tr-TR")}</td><td>${cur}</td><td>Güncel Bakiye</td><td>${money(c.balances[cur],cur)}</td><td>${money(c.balances[cur],cur)}</td></tr>`).join("");
 const sales=finance.filter(f=>f.category==="Satış");
 const salesTable=sales.length?`<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Satış / Detay</th><th>Ödeme</th><th>Tutar</th><th>Kaynak</th></tr></thead><tbody>${sales.map(f=>`<tr><td>${esc(f.date)}</td><td>${esc(f.description)}</td><td>${statusBadge("Ödendi")}</td><td>${money(f.amount,f.currency)}</td><td>Sales Hub</td></tr>`).join("")}</tbody></table></div>`:empty("Ürün satışı yok","Bu müşteriye ait ürün satışı bulunmuyor.");
 const offerTable=offers.length?`<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Teklif No</th><th>Firma / Proje</th><th>Yetkili</th><th>Toplam</th><th>Durum</th><th>PDF</th></tr></thead><tbody>${offers.map(q=>`<tr><td>${esc(q.date)}</td><td><strong>${esc(q.no)}</strong></td><td>${esc(c.company||c.name)}</td><td>${esc(c.name)}</td><td><strong>${money(q.total,q.currency_code||"TRY")}</strong>${q.currency_code&&q.currency_code!=="TRY"?`<br><small class="muted">${money(q.total_try||0,"TRY")}</small>`:""}</td><td>${statusBadge(q.status)}</td><td><button type="button" class="mini c360-print-offer">Aç</button></td></tr>`).join("")}</tbody></table></div>`:empty("Verilen teklif yok","Bu müşteriye ait proforma veya teklif bulunmuyor.");
 const vehicleTab=currentSector==="otomotiv"?'<button class="tab" type="button" data-c360-tab="vehicles">Araçlar</button>':"";
 const vehiclePanel=currentSector==="otomotiv"?'<div class="c360-panel" data-c360-panel="vehicles" id="c360Vehicles">Araç kayıtları yükleniyor…</div>':"";
 const body=`<div class="c360-header"><span class="c360-avatar">${esc(c.name.slice(0,1).toUpperCase())}</span><div><h2>${esc(c.name)}</h2><p>Telefon: ${esc(c.phone||"Bilinmiyor")}</p></div><button type="button" class="primary" id="c360Notes">📝 Müşteri Notları</button></div><div class="c360-stats"><div class="c360-stat"><span>🔧</span><small>Toplam İşlem</small><strong>${services.length}</strong></div><div class="c360-stat"><span>⚡</span><small>Aktif İşlem</small><strong>${active}</strong></div><div class="c360-stat"><span>💰</span><small>Toplam Ciro</small><strong>${money(turnover)}</strong></div></div><div class="c360-currencies"><div><small>TRY BAKİYE</small><strong>${money(c.balances.TRY,"TRY")}</strong></div><div><small>USD BAKİYE</small><strong>${money(c.balances.USD,"USD")}</strong></div><div><small>EUR BAKİYE</small><strong>${money(c.balances.EUR,"EUR")}</strong></div></div><div class="tabs c360-tabs"><button class="tab active" type="button" data-c360-tab="service">Servis Geçmişi</button><button class="tab" type="button" data-c360-tab="cari">Cari İşlem Geçmişi</button><button class="tab" type="button" data-c360-tab="ledger">Döviz Defteri</button><button class="tab" type="button" data-c360-tab="sales">Ürün Satışları</button><button class="tab" type="button" data-c360-tab="offers">Verilen Teklifler</button></div><div class="c360-panel active" data-c360-panel="service">${serviceTable}</div><div class="c360-panel" data-c360-panel="cari">${cari}</div><div class="c360-panel" data-c360-panel="ledger"><div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Döviz</th><th>İşlem Tipi</th><th>Miktar</th><th>Kalan Bakiye</th></tr></thead><tbody>${ledger}</tbody></table></div></div><div class="c360-panel" data-c360-panel="sales">${salesTable}</div><div class="c360-panel" data-c360-panel="offers">${offerTable}</div>`;
 openDialog(c.name,"MÜŞTERİ 360°",body,()=>true,"Kapat");
 $("#appDialog").classList.add("dialog-wide");
 $("#appDialog").addEventListener("close",()=>$("#appDialog").classList.remove("dialog-wide"),{once:true});
 $("#dialogFooter").insertAdjacentHTML("afterbegin",`<button type="button" class="primary" id="c360Offer">Teklif Oluştur</button><button type="button" class="success" id="c360Excel">Excel'e Aktar</button><button type="button" class="danger" id="c360Pdf">PDF'e Aktar</button>`);
 $$("[data-c360-tab]").forEach(tab=>tab.onclick=()=>{$$("[data-c360-tab]").forEach(x=>x.classList.toggle("active",x===tab));$$('[data-c360-panel]').forEach(x=>x.classList.toggle("active",x.dataset.c360Panel===tab.dataset.c360Tab))});
 $("#c360Notes").onclick=()=>{$("#appDialog").close();setTimeout(()=>openCustomerNotes(c),0)};$("#c360Offer").onclick=()=>{$("#appDialog").close();salesCustomer=c.id;navigate("sales")};$("#c360Excel").onclick=()=>download(`${c.name}-musteri-360.csv`,csv(finance));$("#c360Pdf").onclick=()=>printCustomer(c);$$(".c360-pay").forEach(b=>b.onclick=()=>{$("#appDialog").close();setTimeout(()=>paymentDialog(c),0)});$$(".c360-print-offer").forEach(b=>b.onclick=()=>window.print());
}
function openCustomerNotes(c){openDialog(`${c.name} — Müşteri Notları`,"ZENGİN METİN NOT EDİTÖRÜ",`<div class="note-toolbar"><button type="button"><b>B</b></button><button type="button"><i>I</i></button><button type="button"><u>U</u></button><button type="button">• Liste</button><button type="button">Sola</button><button type="button">Orta</button><button type="button">Sağa</button></div><div class="field"><label>Müşteri Notu</label><textarea name="note" style="min-height:260px">${esc(c.notes||"")}</textarea></div>`,fd=>{c.notes=fd.get("note");save();toast("Müşteri notu kaydedildi")},"Notu Kaydet")}
function serviceDialog(customerId=""){const automotive=currentSector==="otomotiv",assetFields=automotive?`<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Model Yılı</label><input name="year" type="number" min="1950" max="2100"></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div><div class="field"><label>Yakıt Türü</label><select name="fuel_type"><option>Benzin</option><option>Dizel</option><option>Hibrit</option><option>Elektrik</option><option>LPG</option></select></div>`:`<div class="field"><label>Cihaz / Ürün *</label><input name="device" required></div><div class="field"><label>Seri No</label><input name="serial"></div>`;openDialog(automotive?"Yeni Araç Servis Kaydı":"Yeni Servis Kaydı",automotive?"OTOMOTİV SERVİS KABUL FORMU":"TEKNİK SERVİS KABUL FORMU",`<div class="form-grid"><div class="field full"><label>Müşteri *</label><select name="customerId" required><option value="">Seçin…</option>${db.customers.map(c=>`<option value="${c.id}" ${String(c.id)===String(customerId)?"selected":""}>${esc(c.name)}</option>`).join("")}</select></div>${assetFields}<div class="field full"><label>${automotive?"Şikayet / Yapılacak İş":"Arıza / Talep"} *</label><textarea name="note" required></textarea></div><div class="field"><label>Durum</label><select name="status"><option>Bekliyor</option><option>İşlemde</option><option>Parça Bekliyor</option></select></div><div class="field"><label>${automotive?"Sonraki Bakım":"Tahmini Teslim"}</label><input name="delivery" type="date"></div></div>`,fd=>{const d=Object.fromEntries(fd),c=db.customers.find(x=>String(x.id)===String(d.customerId));if(!c)throw Error("Müşteri seçin");const no=`SRV-${String(1000+db.customers.flatMap(x=>x.services).length+1)}`,device=automotive?`${d.plate} · ${d.brand} ${d.model}`:d.device;c.services.unshift({date:today(),no,device,status:d.status,note:d.note,serial:d.serial||"",delivery:d.delivery,plate:d.plate,odometer:d.odometer});desktopWrite("devices",{tracking_no:no,customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name,device_type:automotive?"Araç":"Cihaz",device_brand:d.brand||"",device_model:automotive?`${d.model} (${d.plate})`:d.device,serial_no:d.serial||d.plate||"",fault_description:d.note,status:d.status,entry_date:today(),estimated_date:d.delivery,service_source:automotive?"Web Otomotiv":"Web Teknik Servis"}).then(deviceResult=>{if(automotive)desktopWrite("customer_vehicles",{customer_id:Number.isInteger(+c.id)?+c.id:null,plate:d.plate,brand:d.brand,model:d.model,year:+d.year||null,fuel_type:d.fuel_type,last_known_odometer:+d.odometer||0,is_active:1}).then(vehicleResult=>desktopWrite("vehicle_maintenance_cards",{vehicle_id:vehicleResult?.id,customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name,customer_phone:c.phone,vehicle_plate:d.plate,vehicle_brand:d.brand,vehicle_model:d.model,vehicle_year:+d.year||null,fuel_type:d.fuel_type,odometer:+d.odometer||0,service_date:today(),next_maintenance_date:d.delivery,notes:d.note,linked_device_tracking_no:no,linked_device_id:deviceResult?.id,created_by:"Web"}))});save();activity(`${no} servis kaydı ${c.name} için oluşturuldu`,automotive?"🚗":"⚒");toast(automotive?"Araç, bakım kartı ve servis geçmişi kaydedildi":"Servis kaydı Müşteri 360 geçmişine eklendi");render()},automotive?"Araç Servisini Kaydet":"Servis Kaydet")}

function financeDialog(type,item){openDialog(item?"Finans Kaydını Düzenle":`${type} Ekle`,"FİNANS",`<div class="form-grid"><div class="field"><label>Tarih</label><input name="date" type="date" value="${item?.date||today()}"></div><div class="field"><label>Kategori *</label><input name="category" required value="${esc(item?.category||"")}"></div><div class="field"><label>Tutar *</label><input name="amount" type="number" min=".01" step=".01" required value="${item?.amount||""}"></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(x=>`<option ${item?.currency===x?"selected":""}>${x}</option>`).join("")}</select></div><div class="field full"><label>Açıklama *</label><textarea name="description" required>${esc(item?.description||"")}</textarea></div><div class="field full"><label>Müşteri (isteğe bağlı)</label><select name="customer"><option></option>${db.customers.map(c=>`<option ${item?.customer===c.name?"selected":""}>${esc(c.name)}</option>`).join("")}</select></div></div>`,fd=>{const d=Object.fromEntries(fd),target=item||{id:uid("fin"),type};Object.assign(target,d,{amount:+d.amount});if(!item)db.finance.unshift(target);const customer=db.customers.find(c=>c.name===d.customer);const payload={type:target.type,category:d.category,amount:+d.amount,original_amount:+d.amount,try_equivalent:+d.amount,currency:d.currency,exchange_rate:1,description:d.description,date:d.date,customer_id:customer&&Number.isInteger(+customer.id)?+customer.id:null,customer_name:d.customer};if(item&&Number.isInteger(+item.id)){payload.id=+item.id;payload._action="update"}desktopWrite("accounting",payload);save();activity(`${target.type} kaydı: ${money(target.amount,target.currency)}`,target.type==="Gelir"?"↑":"↓");toast(`${target.type} kaydedildi`);render()},item?"Güncelle":"Kaydet")}

function appointmentDialog(item){openDialog(item?"Randevuyu Düzenle":"Yeni Randevu","PLANLAMA",`<div class="form-grid"><div class="field full"><label>Müşteri *</label><select name="customerId" required><option value="">Seçin…</option>${db.customers.map(c=>`<option value="${c.id}" ${String(item?.customerId)===String(c.id)?"selected":""}>${esc(c.name)}</option>`).join("")}</select></div><div class="field"><label>Tarih *</label><input name="date" type="date" required value="${item?.date||today()}"></div><div class="field"><label>Saat *</label><input name="time" type="time" required value="${item?.time||"09:00"}"></div><div class="field full"><label>Konu *</label><input name="title" required value="${esc(item?.title||"")}"></div><div class="field"><label>Durum</label><select name="status">${["Planlandı","Onaylandı","Tamamlandı","İptal"].map(x=>`<option ${item?.status===x?"selected":""}>${x}</option>`).join("")}</select></div></div>`,fd=>{const d=Object.fromEntries(fd),target=item||{id:uid("apt")};Object.assign(target,d,{alerted:false});if(!item)db.appointments.push(target);const customer=db.customers.find(c=>String(c.id)===String(d.customerId));const payload={customer_id:customer&&Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer?.name||"",customer:customer?.name||"",date:d.date,time:d.time,description:d.title,status:d.status,source_type:"web"};if(item&&Number.isInteger(+item.id)){payload.id=+item.id;payload._action="update"}desktopWrite("appointments",payload);save();activity(`${customerName(target.customerId)} randevusu kaydedildi`,"▣");toast("Randevu kaydedildi ve uyarı planlandı");render()},item?"Güncelle":"Randevu Ekle")}

function technicianDialog(c,s){openDialog(`${s.no} · ${s.device}`,"TEKNİSYEN İŞLEM FORMU",`<div class="form-grid"><div class="field"><label>Müşteri</label><input disabled value="${esc(c.name)}"></div><div class="field"><label>Durum</label><select name="status">${["Bekliyor","İşlemde","Parça Bekliyor","Tamamlandı"].map(x=>`<option ${s.status===x?"selected":""}>${x}</option>`).join("")}</select></div><div class="field full"><label>Teknisyen Notu</label><textarea name="note">${esc(s.note)}</textarea></div><div class="field"><label>İşçilik Tutarı</label><input name="labor" type="number" min="0" step=".01" value="0"></div><div class="field"><label>Kullanılan Stok</label><select name="productId"><option value="">Yok</option>${db.stock.filter(x=>x.qty>0).map(x=>`<option value="${x.id}">${esc(x.name)} (${x.qty})</option>`).join("")}</select></div></div>`,fd=>{const d=Object.fromEntries(fd);s.status=d.status;s.note=d.note;const deviceId=Number(String(s.no).replace(/\D/g,""));if(Number.isInteger(deviceId))desktopWrite("devices",{id:deviceId,_action:"update",status:d.status,technician_notes:d.note});if(d.productId){const p=db.stock.find(x=>String(x.id)===String(d.productId));p.qty--;db.movements.unshift({id:uid("mov"),date:new Date().toLocaleString("tr-TR"),product:p.name,type:"Çıkış",qty:1,ref:s.no,user:"Teknisyen"});if(Number.isInteger(+p.id)){desktopWrite("parts",{id:+p.id,_action:"update",stock:p.qty});desktopWrite("stock_movements",{part_id:+p.id,movement_type:"Çıkış",amount:1,new_stock:p.qty,description:`${s.no} teknisyen kullanımı`})}desktopWrite("used_parts",{device_id:Number.isInteger(deviceId)?deviceId:null,part_name:p.name,quantity:1,price:p.sell||0})}if(+d.labor>0){db.finance.unshift({id:uid("fin"),date:today(),type:"Gelir",category:"Servis",amount:+d.labor,currency:"TRY",description:`${s.no} işçilik`,customer:c.name});desktopWrite("accounting",{type:"Gelir",category:"Servis",amount:+d.labor,original_amount:+d.labor,try_equivalent:+d.labor,currency:"TRY",exchange_rate:1,description:`${s.no} işçilik`,date:today(),customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name})}save();activity(`${s.no} teknisyen kaydı güncellendi`,"⚒");toast("Servis, stok ve finans sinyalleri işlendi");render()},"İşlemi Kaydet")}

function runSales(mode){if(!salesCustomer)throw Error("Önce müşteri seçin");if(!salesCart.length)throw Error("Sepete en az bir ürün ekleyin");for(const line of salesCart){const product=db.stock.find(x=>x.id===line.productId);if(!product||line.qty>product.qty)throw Error(`${product?.name||"Ürün"} için yeterli stok yok`)}const c=db.customers.find(x=>x.id===salesCustomer),total=cartTotal(),no=`PRF-${new Date().getFullYear()}-${String(db.quotes.length+1).padStart(4,"0")}`,items=salesCart.map(l=>{const p=db.stock.find(x=>x.id===l.productId);return {productId:p.id,name:p.name,qty:l.qty,price:normalizedPrice(p)}});if(mode==="proforma"){const q={id:uid("quote"),no,date:today(),customerId:c.id,items,total,status:"Teklif"};db.quotes.unshift(q);c.quotes.unshift(q);activity(`${no} proforma ${c.name} için oluşturuldu`,"◇");toast("Proforma oluşturuldu ve Müşteri 360'a kaydedildi")}else if(mode==="payment"){items.forEach(l=>{const p=db.stock.find(x=>x.id===l.productId);p.qty-=l.qty;db.movements.unshift({id:uid("mov"),date:new Date().toLocaleString("tr-TR"),product:p.name,type:"Çıkış",qty:l.qty,ref:no,user:"Yönetici"})});db.finance.unshift({id:uid("fin"),date:today(),type:"Gelir",category:"Satış",amount:total,currency:"TRY",description:`${no} peşin satış`,customer:c.name});activity(`${c.name} satışından ${money(total)} tahsil edildi`,"₺");toast("Ödeme, finans ve stok hareketleri kaydedildi")}else{const serviceNo=`SRV-${1000+db.customers.flatMap(x=>x.services).length+1}`;c.services.unshift({date:today(),no:serviceNo,device:items.map(x=>x.name).join(", "),status:"Bekliyor",note:`Sales Hub kaydı — ${no}`});activity(`${serviceNo} Sales Hub üzerinden oluşturuldu`,"⚒");toast("Servis Müşteri 360 geçmişine kaydedildi")}salesCart=[];save();render()}

function download(name,text,type="text/csv"){const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),500)}
function csv(rows){if(!rows.length)return "";const keys=Object.keys(rows[0]);return "\ufeff"+[keys.join(";"),...rows.map(r=>keys.map(k=>`"${String(typeof r[k]==="object"?JSON.stringify(r[k]):r[k]??"").replaceAll('"','""')}"`).join(";"))].join("\n")}
function exportAll(){download(`ayec-pro-yedek-${today()}.json`,JSON.stringify(db,null,2),"application/json");toast("Tam yedek indirildi")}
function printCustomer(c){const win=window.open("","_blank");win.document.write(`<title>${esc(c.name)} Cari Özet</title><h1>${esc(c.name)}</h1><p>${esc(c.phone)} · ${esc(c.email)}</p><h2>Bakiyeler</h2><p>${money(c.balances.TRY,"TRY")} / ${money(c.balances.USD,"USD")} / ${money(c.balances.EUR,"EUR")}</p><h2>Servis Geçmişi</h2>${c.services.map(s=>`<p><b>${esc(s.no)}</b> ${esc(s.device)} — ${esc(s.status)}</p>`).join("")}`);win.document.close();win.print()}

function parseCSV(text){const lines=text.replace(/^\ufeff/,"").split(/\r?\n/).filter(Boolean),sep=lines[0].includes(";")?";":",";const headers=lines.shift().split(sep).map(x=>x.replaceAll('"',"").trim().toLowerCase());return lines.map(line=>{const vals=line.split(sep).map(x=>x.replace(/^"|"$/g,"").trim()),get=(...names)=>{const i=headers.findIndex(h=>names.some(n=>h.includes(n)));return i>=0?vals[i]:""};return {id:uid("stk"),code:get("kod","code")||uid("URN").slice(-8).toUpperCase(),name:get("ürün","urun","mal/hizmet","name"),category:get("kategori","category")||"Bilgisayar",qty:+get("adet","miktar","qty")||0,min:+get("minimum","min")||0,buy:+get("alış","alis","buy")||0,sell:+get("satış","satis","sell","fiyat")||0,currency:(get("para","döviz","doviz","currency")||"TRY").toUpperCase(),barcode:get("barkod","barcode")}}).filter(x=>x.name)}
function parseImportNumber(value){if(typeof value==="number")return Number.isFinite(value)?value:0;let text=String(value??"").trim().replace(/[^0-9,.-]/g,"");if(!text)return 0;if(text.includes(",")&&text.includes(".")){if(text.lastIndexOf(",")>text.lastIndexOf("."))text=text.replace(/\./g,"").replace(",",".");else text=text.replace(/,/g,"")}else if(text.includes(","))text=text.replace(",",".");const number=Number(text);return Number.isFinite(number)?number:0}
function importCurrency(value,...fallbackValues){const text=[value,...fallbackValues].join(" ").toLocaleUpperCase("tr-TR");if(text.includes("USD")||text.includes("$"))return"USD";if(text.includes("EUR")||text.includes("€"))return"EUR";return"TRY"}
function inferImportCategory(name,provided=""){if(provided&&provided!=="Genel")return provided;const text=String(name).toLocaleLowerCase("tr-TR");if(currentSector==="otomotiv"){if(/motor|filtre|fren|balata|debriyaj|yağ/.test(text))return"Motor & Mekanik";if(/akü|sensör|far|elektrik|kablo/.test(text))return"Elektrik & Elektronik";if(/kaporta|tampon|çamurluk|ayna/.test(text))return"Kaporta";return"Sarf Malzeme"}if(/kamera|nvr|dvr|alarm|güvenlik|ip camera/.test(text))return"Güvenlik Sistemleri";if(/akıllı|smart|zigbee|hub|röle/.test(text))return"Akıllı Ev";return"Bilgisayar"}
function normalizeImportRows(rows){return rows.map(row=>{const normalized={};Object.entries(row||{}).forEach(([key,value])=>normalized[String(key).trim().toLocaleLowerCase("tr-TR").replace(/[ _/.-]+/g,"")]=value);const pick=(...aliases)=>{for(const alias of aliases){const key=alias.toLocaleLowerCase("tr-TR").replace(/[ _/.-]+/g,"");if(normalized[key]!==undefined&&String(normalized[key]).trim()!=="")return normalized[key]}return""};const name=pick("name","part_name","product_name","ürün","urun","mal_hizmet","mal/hizmet","açıklama","aciklama","description","item");const code=pick("code","part_code","product_code","stok_kodu","stok no","kod","sku","model");const barcode=pick("barcode","barkod","ean","gtin");const qtyRaw=pick("qty","quantity","amount","adet","miktar","stock","stok","stok_adedi");const minRaw=pick("min","minimum","min_stock","minimum_stok");const buyRaw=pick("buy","purchase_price","buy_price","alış_fiyatı","alis_fiyati","maliyet","cost");const sellRaw=pick("sell","sale_price","sales_price","unit_price","price","satış_fiyatı","satis_fiyati","birim_fiyat","fiyat");const currencyRaw=pick("currency","currency_code","para_birimi","döviz","doviz");const categoryRaw=pick("category","kategori","group","grup");const displayName=String(name||code||"").trim();return{id:uid("imp"),code:String(code||uid("URN").slice(-8).toUpperCase()).trim(),name:displayName,category:inferImportCategory(displayName,String(categoryRaw||"")),qty:parseImportNumber(qtyRaw),min:parseImportNumber(minRaw),buy:parseImportNumber(buyRaw),sell:parseImportNumber(sellRaw),currency:importCurrency(currencyRaw,buyRaw,sellRaw),barcode:String(barcode||"").trim(),_raw:row}}).filter(row=>row.name&&!/^(ürün|urun|açıklama|aciklama|mal hizmet|name|description)$/i.test(row.name.trim()))}

function importPreviewTable(rows){return `<div class="table-wrap"><table><thead><tr><th>Kod</th><th>Ürün</th><th>Kategori</th><th>Stok</th><th>Min.</th><th>Alış</th><th>Satış</th><th>Para</th><th></th></tr></thead><tbody>${rows.map((row,index)=>`<tr><td>${esc(row.code)}</td><td><strong>${esc(row.name)}</strong><br><small class="muted">${esc(row.barcode||"")}</small></td><td><span class="badge">${esc(row.category)}</span></td><td>${row.qty}</td><td>${row.min}</td><td>${money(row.buy,row.currency)}</td><td>${money(row.sell,row.currency)}</td><td>${esc(row.currency)}</td><td><div class="row-actions"><button class="mini" data-action="edit-import-row" data-index="${index}">Düzenle</button><button class="mini danger-outline" data-action="delete-import-row" data-index="${index}">Sil</button></div></td></tr>`).join("")}</tbody></table></div>`}
function drawImportPreview(){const preview=$("#importPreview"),rows=window.importRows||[],meta=window.importMeta||{};if(!preview)return;const warnings=meta.warnings||[],mapping=meta.mapping||{};const warningHtml=warnings.length?`<div class="import-warnings">${warnings.map(w=>`<p>⚠ ${esc(w)}</p>`).join("")}</div>`:"",mappingHtml=Object.keys(mapping).length?`<details><summary>Algılanan kolon eşleştirmeleri</summary><div class="mapping-grid">${Object.entries(mapping).map(([source,target])=>`<span>${esc(source)} → <b>${esc(target)}</b></span>`).join("")}</div></details>`:"";preview.innerHTML=`<div class="import-preview"><div class="card-head"><div><h3>DataFrame Önizleme · ${rows.length} satır</h3><span class="badge">${esc(meta.engine||"AYEC Pro")}</span></div><div class="actions"><button class="secondary" data-action="clear-import-rows" ${rows.length?"":"disabled"}>Tümünü Temizle</button><button class="primary" data-action="commit-import" ${rows.length?"":"disabled"}>Doğrula ve İçe Aktar</button></div></div>${warningHtml}${mappingHtml}${rows.length?importPreviewTable(rows):empty("İçe aktarılacak satır kalmadı","Yeni dosya seçebilir veya işlemi yeniden başlatabilirsiniz.")}</div>`;bindPage()}
function editImportRow(index){const row=window.importRows?.[index];if(!row)return;openDialog("İçe Aktarma Satırını Düzenle","OCR / DOSYA ÖNİZLEMESİ",productForm(row),fd=>{const data=Object.fromEntries(fd);Object.assign(row,{code:data.code.trim(),barcode:data.barcode.trim(),name:data.name.trim(),category:data.category,currency:data.currency,qty:parseImportNumber(data.qty),min:parseImportNumber(data.min),buy:parseImportNumber(data.buy),sell:parseImportNumber(data.sell)});drawImportPreview();toast("Önizleme satırı güncellendi","success")},"Değişiklikleri Uygula")}
function addImportRow(){const row={id:uid("imp"),code:"",barcode:"",name:"",category:sectorStockCategories()[0],currency:"TRY",qty:1,min:0,buy:0,sell:0};openDialog("Eksik Ürün Satırı Ekle","OCR / DOSYA ÖNİZLEMESİ",productForm(row),fd=>{const data=Object.fromEntries(fd);Object.assign(row,{code:data.code.trim(),barcode:data.barcode.trim(),name:data.name.trim(),category:data.category,currency:data.currency,qty:parseImportNumber(data.qty),min:parseImportNumber(data.min),buy:parseImportNumber(data.buy),sell:parseImportNumber(data.sell)});window.importRows=window.importRows||[];window.importRows.push(row);window.importMeta=window.importMeta||{engine:"Elle doğrulama",warnings:[],mapping:{}};drawImportPreview();toast("Eksik ürün önizlemeye eklendi","success")},"Satırı Önizlemeye Ekle")}
function fileBase64(file){return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onerror=reject;reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.readAsDataURL(file)})}
async function handleImport(file){const preview=$("#importPreview");preview.innerHTML=`<div class="empty"><span>◌</span><strong>${esc(file.name)} analiz ediliyor</strong><span>Masaüstü StockImportParser çalışıyor…</span></div>`;try{const result=await apiFetch("/api/desktop/smart-import",{method:"POST",body:JSON.stringify({name:file.name,data:await fileBase64(file)})}),warnings=(result.warnings||[]).filter(Boolean),mapping=result.suggested_mapping||{},normalizedRows=normalizeImportRows(result.rows||[]),rawRows=normalizeImportRows(result.raw_rows||[]),candidates=rawRows.length>normalizedRows.length?rawRows:normalizedRows;const unique=[];for(const row of candidates){const match=unique.find(item=>(row.barcode&&item.barcode===row.barcode)||(row.code&&item.code===row.code)||(item.name.toLocaleLowerCase("tr-TR")===row.name.toLocaleLowerCase("tr-TR")));if(match){Object.assign(match,{...row,qty:Math.max(match.qty,row.qty),buy:row.buy||match.buy,sell:row.sell||match.sell})}else unique.push(row)}if(unique.length){window.importRows=unique;if(rawRows.length>normalizedRows.length)warnings.unshift(`${rawRows.length} ham OCR satırı eksik ürünleri kontrol etmeniz için önizlemeye dahil edildi.`);window.importMeta={engine:result.engine,warnings,mapping,fileName:file.name};drawImportPreview();toast(`${window.importRows.length} satır düzenleme için hazırlandı`,"success");return}const warningHtml=warnings.length?`<div class="import-warnings">${warnings.map(w=>`<p>⚠ ${esc(w)}</p>`).join("")}</div>`:"";preview.innerHTML=`<div class="import-preview"><div class="card-head"><h3>OCR doğrulama önizlemesi</h3><span class="badge">${esc(result.engine)}</span></div>${warningHtml}<p class="muted">Okunan satırları ürün; adet; fiyat biçiminde kontrol edip düzeltebilirsiniz.</p><div class="field"><label>OCR metni</label><textarea id="ocrText">${esc(result.text||"")}</textarea></div><button class="primary" data-action="ocr-to-stock">Metinden Stok Taslağı Oluştur</button></div>`;bindPage();toast(result.text?"Belge OCR ile okundu":"Belgede otomatik ürün satırı bulunamadı",result.text?"success":"warning")}catch(e){preview.innerHTML=empty("Dosya analiz edilemedi",e.message);toast("Dosya okunamadı: "+e.message,"error")}}
async function commitImport(rows){
 const source=(rows||[]).filter(row=>row&&String(row.name||"").trim());
 if(!source.length)return toast("\u0130\u00e7e aktar\u0131lacak ge\u00e7erli \u00fcr\u00fcn sat\u0131r\u0131 yok","warning");
 const button=document.querySelector('[data-action="commit-import"]');
 if(button){button.disabled=true;button.textContent="Sunucuya kaydediliyor..."}
 let added=0,updated=0,processed=0;
 try{
  for(const row of source){
   const existing=db.stock.find(item=>(row.barcode&&item.barcode===row.barcode)||(row.code&&item.code===row.code));
   const currency=String(row.currency||existing?.currency||"TRY").toUpperCase();
   const quantity=Math.max(0,Number(row.qty??row.stock)||0);
   const description=String(row.description??row.desc??existing?.description??"").trim();
   const payload={id:existing&&Number.isInteger(+existing.id)?+existing.id:undefined,name:String(row.name||existing?.name||"").trim(),code:String(row.code||existing?.code||"").trim(),barcode:String(row.barcode||existing?.barcode||"").trim(),category:String(row.category||existing?.category||"Genel").trim(),brand:String(row.brand||existing?.brand||"").trim(),currency,stock:(existing?Number(existing.qty)||0:0)+quantity,min_stock:Math.max(0,Number(row.min??row.min_stock??existing?.min)||0),purchase_price:Math.max(0,Number(row.buy??row.purchase_price??existing?.buy)||0),price:Math.max(0,Number(row.sell??row.price??existing?.sell)||0),exchange_rate:rateForCode(currency),description};
   await apiFetch("/api/desktop/stock/save",{method:"POST",body:JSON.stringify(payload)});
   existing?updated++:added++;processed++;window.importRows=source.slice(processed);
  }
  await hydrateDesktop(true);window.importRows=[];window.importMeta=null;
  activity(`Ak\u0131ll\u0131 i\u00e7e aktarma: ${added} yeni, ${updated} g\u00fcncel`,"\u21e7");
  toast(`${added} \u00fcr\u00fcn eklendi, ${updated} \u00fcr\u00fcn g\u00fcncellendi`,"success");navigate("stock");
 }catch(error){
  try{await hydrateDesktop(true)}catch(_refreshError){}
  window.importRows=source.slice(processed);toast(`${processed} sat\u0131r kaydedildi; kalan ${window.importRows.length} sat\u0131r bekliyor: ${error.message}`,"error",9000);drawImportPreview();
 }finally{if(button){button.disabled=false;button.textContent="Do\u011frula ve \u0130\u00e7e Aktar"}}
}

function showContext(e,kind,id){if(!db.settings.contextMenu)return;e.preventDefault();const c=$("#contextMenu");let items=[];if(kind==="customer")items=[["Müşteri 360","360"],["Tahsilat Al","payment"],["Yeni Servis","service"],["Düzenle","edit"],["Yazdır","print"]];if(kind==="stock")items=[["Düzenle","edit-product"],["Stok Hareketi","movement"],["Sil","delete-product"]];if(kind==="appointment")items=[["Düzenle","edit-appointment"],["Onaylandı","approve"],["Tamamlandı","complete"],["İptal","cancel"]];if(kind==="service")items=[["Teknisyen Panelinde Aç","technician"]];if(kind==="finance")items=[["Düzenle","edit-finance"],["Yazdır","print-finance"]];if(kind==="generic")items=[["Düzenle","generic-edit"],["Sil","generic-delete"]];if(!items.length)return;c.innerHTML=items.map(([label,action])=>`<button data-context-action="${action}">${label}</button>`).join("");c.style.left=`${Math.max(8,Math.min(e.clientX,innerWidth-210))}px`;c.style.top=`${Math.max(8,Math.min(e.clientY,innerHeight-items.length*40-20))}px`;c.classList.add("open");$$('[data-context-action]',c).forEach(b=>b.onclick=()=>{c.classList.remove("open");contextAction(kind,id,b.dataset.contextAction,e.currentTarget)})}
function contextAction(kind,id,action,row){if(kind==="customer"){const c=db.customers.find(x=>String(x.id)===String(id));if(action==="360")customer360(c);if(action==="payment")paymentDialog(c);if(action==="service")serviceDialog(c.id);if(action==="edit")openDialog("Müşteriyi Düzenle","CRM",customerForm(c),fd=>saveCustomer(fd,c),"Güncelle");if(action==="print")printCustomer(c)}if(kind==="stock"){const s=db.stock.find(x=>String(x.id)===String(id));if(action==="edit-product")openDialog("Ürünü Düzenle","STOK",productForm(s),fd=>saveProduct(fd,s),"Güncelle");if(action==="movement")movementDialog(s);if(action==="delete-product")deleteProduct(s)}if(kind==="appointment"){const a=db.appointments.find(x=>String(x.id)===String(id));if(action==="edit-appointment")appointmentDialog(a);if(["approve","complete","cancel"].includes(action)){a.status={approve:"Onaylandı",complete:"Tamamlandı",cancel:"İptal"}[action];if(Number.isInteger(+a.id))desktopWrite("appointments",{id:+a.id,_action:"update",status:a.status});save();toast(`Randevu durumu: ${a.status}`);render()}}if(kind==="service"){const [c,s]=findService(id);technicianDialog(c,s)}if(kind==="finance"){const item=db.finance.find(x=>String(x.id)===String(id));if(action==="edit-finance")financeDialog(item?.type,item);if(action==="print-finance")window.print()}if(kind==="generic"){const index=+id,data=window.currentGenericData,meta=window.currentGenericMeta;if(!data||!meta)return;if(action==="generic-edit")openGenericDialog(meta,data.rows[index],data.columns);if(action==="generic-delete")deleteGenericRow(meta,data.rows[index])}}

function bindInteractiveRow(row){if(row.dataset.interactiveBound)return;row.dataset.interactiveBound="1";row.tabIndex=row.tabIndex>=0?row.tabIndex:0;row.addEventListener("contextmenu",e=>showContext(e,row.dataset.kind,row.dataset.id));let timer,startX=0,startY=0;row.addEventListener("pointerdown",e=>{if(e.pointerType==="mouse")return;startX=e.clientX;startY=e.clientY;timer=setTimeout(()=>{timer=0;showContext({preventDefault(){},clientX:startX,clientY:startY,currentTarget:row},row.dataset.kind,row.dataset.id)},550)});const cancel=e=>{if(timer&&e&&Math.hypot((e.clientX??startX)-startX,(e.clientY??startY)-startY)>10)clearTimeout(timer);else if(timer)clearTimeout(timer);timer=0};row.addEventListener("pointerup",cancel);row.addEventListener("pointercancel",cancel);row.addEventListener("pointermove",e=>{if(timer&&Math.hypot(e.clientX-startX,e.clientY-startY)>10)cancel(e)});row.addEventListener("keydown",e=>{if(e.key==="ContextMenu"||(e.shiftKey&&e.key==="F10")){e.preventDefault();const box=row.getBoundingClientRect();showContext({preventDefault(){},clientX:box.left+24,clientY:box.top+24,currentTarget:row},row.dataset.kind,row.dataset.id)}else if(e.key==="Enter")row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true}))})}
function findService(no){for(const c of db.customers){const s=c.services.find(x=>x.no===no);if(s)return[c,s]}return[]}
function movementDialog(s){openDialog("Stok Hareketi","STOK",`<div class="form-grid"><div class="field full"><label>Ürün</label><input disabled value="${esc(s.name)}"></div><div class="field"><label>Tür</label><select name="type"><option>Giriş</option><option>Çıkış</option></select></div><div class="field"><label>Miktar</label><input name="qty" type="number" min="1" required></div><div class="field full"><label>Referans</label><input name="ref" value="MANUEL"></div></div>`,fd=>{const d=Object.fromEntries(fd),qty=+d.qty;if(d.type==="Çıkış"&&qty>s.qty)throw Error("Yetersiz stok");s.qty+=d.type==="Giriş"?qty:-qty;db.movements.unshift({id:uid("mov"),date:new Date().toLocaleString("tr-TR"),product:s.name,type:d.type,qty,ref:d.ref,user:"Yönetici"});if(Number.isInteger(+s.id)){desktopWrite("parts",{id:+s.id,_action:"update",stock:s.qty});desktopWrite("stock_movements",{part_id:+s.id,movement_type:d.type,amount:qty,new_stock:s.qty,description:d.ref})}save();toast("Stok hareketi kaydedildi");render()})}

function handleAction(action,id,el){try{if(action==="quick-add")openDialog("Hızlı İşlem","KISAYOLLAR",`<div class="product-picker"><button type="button" class="product-tile" data-quick="customer">Yeni Müşteri</button><button type="button" class="product-tile" data-quick="service">Servis Kaydı</button><button type="button" class="product-tile" data-quick="appointment">Randevu</button><button type="button" class="product-tile" data-quick="income">Gelir</button></div>`,()=>true,"Kapat"),setTimeout(()=>$$('[data-quick]').forEach(b=>b.onclick=()=>{$("#appDialog").close();({customer:()=>openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle"),service:()=>serviceDialog(),appointment:()=>appointmentDialog(),income:()=>financeDialog("Gelir")}[b.dataset.quick])()}),0);if(action==="add-customer")openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle");if(action==="customer-actions")customerActions(id);if(action==="add-product")openDialog("Ürün Ekle","STOK KARTI",productForm(),fd=>saveProduct(fd),"Ürün Ekle");if(action==="edit-product"){const s=db.stock.find(x=>x.id===id);openDialog("Ürünü Düzenle","STOK KARTI",productForm(s),fd=>saveProduct(fd,s),"Güncelle")}if(action==="add-movement")openDialog("Ürün Seç","STOK HAREKETİ",`<div class="field"><label>Stok ürünü</label><select id="movementProduct">${db.stock.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join("")}</select></div>`,()=>{const s=db.stock.find(x=>x.id===$("#movementProduct").value);setTimeout(()=>movementDialog(s),100)},"Devam");if(action==="add-income")financeDialog("Gelir");if(action==="add-expense")financeDialog("Gider");if(action==="edit-finance")financeDialog(db.finance.find(x=>x.id===id)?.type,db.finance.find(x=>x.id===id));if(action==="add-appointment")appointmentDialog();if(action==="new-service")serviceDialog();if(action==="service-detail"||action==="technician-open"){const [c,s]=findService(id);technicianDialog(c,s)}if(action==="cart-add"){const l=salesCart.find(x=>x.productId===id);l?l.qty++:salesCart.push({productId:id,qty:1});render()}if(action==="cart-remove"){salesCart.splice(+el.dataset.index,1);render()}if(action==="pay-save")runSales("payment");if(action==="create-proforma")runSales("proforma");if(action==="save-service")runSales("service");if(action==="view-quotes")quoteDialog();if(action==="choose-import"||action==="import-customers"||action==="restore-backup"){$("#fileInput").dataset.mode=action;$("#fileInput").click()}if(action==="commit-import")commitImport(window.importRows||[]);if(action==="ocr-to-stock"){const lines=$("#ocrText").value.split(/\n/).filter(Boolean);window.importRows=lines.map((x,i)=>{const parts=x.split(/[;|\t]/);return{id:uid("stk"),code:parts[0]||`OCR-${i+1}`,name:parts[1]||parts[0],category:parts[2]||"Bilgisayar",qty:+parts[3]||1,min:0,buy:+parts[4]||0,sell:+parts[5]||0,currency:(parts[6]||"TRY").trim(),barcode:parts[7]||""}});commitImport(window.importRows)}if(action==="download-template")download("ayec-stok-sablonu.csv","kod;ürün;kategori;adet;minimum;alış;satış;para birimi;barkod\nPC-001;Örnek Ürün;Bilgisayar;10;2;100;140;TRY;123456");if(action==="export-all")exportAll();if(action==="export-customers")download(`musteriler-${today()}.csv`,csv(db.customers));if(action==="export-stock")download(`stok-${today()}.csv`,csv(db.stock));if(action==="export-finance")download(`finans-${today()}.csv`,csv(db.finance));if(action==="save-settings"){db.settings={...db.settings,company:$("#setCompany").value,currency:$("#setCurrency").value,alertMinutes:+$("#setAlertMinutes").value,doubleClick:$("#setDouble").checked,contextMenu:$("#setContext").checked,appointmentAlerts:$("#setAlerts").checked,compact:$("#setCompact").checked};save();toast("Ayarlar kaydedildi")}if(action==="reset-demo"){if(confirm("Tüm yerel veriler örnek başlangıç durumuna dönecek. Devam edilsin mi?")){db=structuredClone(seed);save();render();toast("Örnek veri sıfırlandı","warning")}}}catch(err){toast(err.message||"İşlem tamamlanamadı","error")}}
function quoteDialog(){openDialog("Proforma Teklifler","SALES HUB",db.quotes.length?`<div class="table-wrap"><table><thead><tr><th>No</th><th>Müşteri</th><th>Tarih</th><th>Tutar</th><th>Durum</th><th></th></tr></thead><tbody>${db.quotes.map(q=>`<tr><td><strong>${q.no}</strong></td><td>${customerName(q.customerId)}</td><td>${q.date}</td><td>${money(q.total)}</td><td>${statusBadge(q.status)}</td><td><button type="button" class="mini" onclick="window.print()">Yazdır</button></td></tr>`).join("")}</tbody></table></div>`:empty("Proforma yok","Sales Hub üzerinden ilk teklifi oluşturun."),()=>true,"Kapat")}

function bindPage(){
 $$('[data-action]').forEach(b=>b.addEventListener("click",e=>{e.preventDefault();handleAction(b.dataset.action,b.dataset.id,b)}));
 $$('[data-kind]').forEach(row=>{bindInteractiveRow(row);row.addEventListener("dblclick",()=>{if(!db.settings.doubleClick)return;if(row.dataset.kind==="customer")customer360(db.customers.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="appointment")appointmentDialog(db.appointments.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="stock"){const s=db.stock.find(x=>x.id===row.dataset.id);openDialog("Ürünü Düzenle","STOK",productForm(s),fd=>saveProduct(fd,s),"Güncelle")}if(row.dataset.kind==="service"){const [c,s]=findService(row.dataset.id);technicianDialog(c,s)}if(row.dataset.kind==="finance"){const item=db.finance.find(x=>String(x.id)===String(row.dataset.id));financeDialog(item?.type,item)}})});
 const cs=$("#customerSearch");if(cs){let mode="all";const f=()=>{const q=cs.value.toLocaleLowerCase("tr-TR");const rows=db.customers.filter(c=>{const debt=Number(c.balances?.TRY||0)>0||Number(c.balances?.USD||0)>0||Number(c.balances?.EUR||0)>0;return(mode==="all"||debt)&&[c.name,c.phone,c.email,c.company||""].join(" ").toLocaleLowerCase("tr-TR").includes(q)});$("#customerTable").innerHTML=customerTable(rows);if($("#customerCount"))$("#customerCount").textContent=rows.length;bindPageRows()};cs.oninput=f;$$('[data-customer-filter]').forEach(b=>b.onclick=()=>{mode=b.dataset.customerFilter;$$('[data-customer-filter]').forEach(x=>x.classList.toggle("selected",x===b));f()})}
 const ss=$("#stockSearch"),sc=$("#stockCategory"),sl=$("#stockLevel");if(ss){const f=()=>{const q=ss.value.toLocaleLowerCase("tr-TR");$("#stockTable").innerHTML=stockTable(db.stock.filter(s=>[s.code,s.name,s.barcode].join(" ").toLocaleLowerCase("tr-TR").includes(q)&&(sc.value==="Tüm Kategoriler"||s.category===sc.value)&&(sl.value==="Tüm Seviyeler"||(sl.value==="Kritik Stok"?s.qty<=s.min:s.qty>0))))};ss.oninput=f;sc.onchange=f;sl.onchange=f}
 const salesSearch=$("#salesProductSearch");if(salesSearch)salesSearch.oninput=()=>{$("#salesProducts").innerHTML=salesProducts(db.stock.filter(s=>s.name.toLocaleLowerCase("tr-TR").includes(salesSearch.value.toLocaleLowerCase("tr-TR"))));bindPage()};const customer=$("#salesCustomer");if(customer)customer.onchange=()=>salesCustomer=customer.value;$$('.cart-qty').forEach(i=>i.onchange=()=>{salesCart[+i.dataset.index].qty=Math.max(1,+i.value);render()});
 const dz=$("#dropZone");if(dz){dz.ondragover=e=>{e.preventDefault();dz.style.borderColor="var(--brand)"};dz.ondragleave=()=>dz.style.borderColor="var(--line)";dz.ondrop=e=>{e.preventDefault();handleImport(e.dataTransfer.files[0])}}
 $$('[data-settings-section]').forEach(button=>button.onclick=()=>{settingsSection=button.dataset.settingsSection;render()});const settingsMobileSelect=$("#settingsMobileSelect");if(settingsMobileSelect)settingsMobileSelect.onchange=()=>{settingsSection=settingsMobileSelect.value;render()};const settingsSearch=$("#settingsSearch");if(settingsSearch)settingsSearch.oninput=()=>{const q=settingsSearch.value.toLocaleLowerCase("tr-TR");$$('[data-settings-section]').forEach(button=>button.hidden=!button.textContent.toLocaleLowerCase("tr-TR").includes(q))};const saveSettingsButton=$('[data-action="save-settings"]');if(saveSettingsButton)saveSettingsButton.addEventListener("click",()=>{const pairs={company_name:db.settings.company,default_currency:db.settings.currency,appointment_alert_minutes:db.settings.alertMinutes,web_double_click:db.settings.doubleClick,web_context_menu:db.settings.contextMenu,appointment_notifications:db.settings.appointmentAlerts,web_compact:db.settings.compact};Object.entries(pairs).forEach(([key,value])=>desktopWrite("settings",{key,value}))})
 if(saveSettingsButton)saveSettingsButton.addEventListener("click",async()=>{try{const controls=$$(".exact-setting");let savedCount=0;for(const control of controls){let value=control.type==="checkbox"?(control.checked?"1":"0"):control.value,scope=control.dataset.settingScope||"settings",key=control.dataset.settingKey;if(control.type==="password"&&!value)continue;if(control.type==="password"&&value.length<4){toast(`${key} en az 4 karakter olmalıdır`,"error");return}if(key==="security_answer_new"){const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value.trim().toLocaleLowerCase("tr-TR")));value=[...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,"0")).join("");key="security_answer_hash"}await desktopWrite(scope,{key,value});savedCount++;if(scope==="settings")desktopSettings[key]=control.type==="password"?"":value;else desktopInternalSettings[key]=value;if(key==="current_sector"){currentSector=value;$("#sectorSelect").value=value;renderNav()}}if(savedCount)toast(`${savedCount} masaüstü ayarı kaydedildi`,"success")}catch(error){toast(`Ayar kaydedilemedi: ${error.message}`,"error")}})
 if($("#quickNotesHost")){loadQuickNotes();$("#quickNoteAdd").onclick=()=>quickNoteDialog()}
 if($("#settingsUsersHost"))loadSettingsUsers()
}
function bindPageRows(){$$('[data-kind]').forEach(row=>{bindInteractiveRow(row);row.ondblclick=()=>{if(!db.settings.doubleClick)return;if(row.dataset.kind==="customer")customer360(db.customers.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="appointment")appointmentDialog(db.appointments.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="stock"){const s=db.stock.find(x=>x.id===row.dataset.id);openDialog("Ürünü Düzenle","STOK",productForm(s),fd=>saveProduct(fd,s),"Güncelle")}if(row.dataset.kind==="finance"){const item=db.finance.find(x=>String(x.id)===String(row.dataset.id));financeDialog(item?.type,item)}}});$$('[data-action]').forEach(b=>b.onclick=e=>{e.preventDefault();handleAction(b.dataset.action,b.dataset.id,b)})}

function checkAppointments(){if(!db.settings.appointmentAlerts)return;const now=new Date();db.appointments.forEach(a=>{if(a.alerted||a.status==="İptal"||a.status==="Tamamlandı")return;const at=new Date(`${a.date}T${a.time}:00`),diff=(at-now)/60000;if(diff>=0&&diff<=db.settings.alertMinutes){a.alerted=true;save();const msg=`${customerName(a.customerId)} randevusu ${Math.ceil(diff)} dakika içinde: ${a.title}`;notifications.unshift(msg);toast(msg,"warning",8000);if("Notification" in window&&Notification.permission==="granted")new Notification("AYEC Pro Randevu",{body:msg})}})}
function checkScheduledAlerts(){const now=new Date(),hhmm=now.toTimeString().slice(0,5),stamp=`${today()}-${hhmm}`;scheduledAlerts.forEach(alert=>{if(alert.trigger_time!==hhmm||alert._stamp===stamp)return;alert._stamp=stamp;const labels={loan_reminder:"Kredi / taksit hatırlatmalarını kontrol edin",check_reminder:"Vadesi yaklaşan çek ve senetleri kontrol edin",stock_critical:"Kritik stok seviyelerini kontrol edin"},msg=labels[alert.alert_type]||`Planlı uyarı: ${alert.alert_type}`;notifications.unshift(msg);toast(msg,alert.is_critical?"error":"warning",9000);if("Notification" in window&&Notification.permission==="granted")new Notification("AYEC Pro Planlı Uyarı",{body:msg})})}

async function hydrateDesktop(){try{const source=await apiFetch('/api/desktop/bootstrap');if(source.customers?.length)db.customers=source.customers.map(c=>({...c,phone:c.phone||"",email:c.email||"",type:c.type||"Bireysel",company:c.company_name||"",balances:c.balances||{TRY:0,USD:0,EUR:0},services:c.services||[],quotes:c.quotes||[]}));if(source.stock?.length)db.stock=source.stock.map(s=>({...s,id:s.id,code:s.code||"",name:s.name||s.part_name||"",category:s.category||"Di\u011fer",qty:Number(s.stock||0),min:Number(s.min_stock||0),buy:Number(s.purchase_price||0),sell:Number(s.price||0),currency:String(s.currency||"TRY").toUpperCase(),barcode:s.barcode||""}));if(source.movements?.length)db.movements=source.movements.map(m=>({...m,id:m.id,date:m.created_at||"",product:m.product||"",type:m.movement_type||"",qty:m.amount||0,ref:m.description||"",user:"Masa\u00fcst\u00fc"}));if(source.finance?.length)db.finance=source.finance.map(f=>({...f,customer:f.customer_name||"",currency:String(f.currency||"TRY").toUpperCase(),original_amount:f.original_amount??f.amount}));if(source.appointments?.length)db.appointments=source.appointments.map(a=>({...a,customerId:a.customer_id,title:a.title||a.description||a.fault||"Randevu",status:a.status||"Planland\u0131",alerted:false}));if(source.offers?.length)db.quotes=source.offers;save();render();toast("Masa\u00fcst\u00fc veritaban\u0131 web aray\u00fcz\u00fcne ba\u011fland\u0131","success")}catch(err){toast("Masa\u00fcst\u00fc veritaban\u0131 ba\u011flant\u0131s\u0131 kurulamad\u0131: "+err.message,"error")}}
hydrateDesktop=async function(){try{const source=await apiFetch("/api/desktop/bootstrap");db.customers=(source.customers||[]).map(c=>({...c,id:String(c.id),phone:c.phone||"",email:c.email||"",type:c.type||"Bireysel",company:c.company_name||"",balances:c.balances||{TRY:0,USD:0,EUR:0},services:c.services||[],quotes:c.quotes||[]}));db.stock=(source.stock||[]).map(s=>({...s,id:String(s.id),code:s.code||"",name:s.name||s.part_name||"",category:s.category||"Di\u011fer",qty:Number(s.stock||0),min:Number(s.min_stock||0),buy:Number(s.purchase_price||0),sell:Number(s.price||0),currency:String(s.currency||"TRY").toUpperCase(),barcode:s.barcode||""}));db.movements=(source.movements||[]).map(m=>({...m,id:String(m.id),date:m.created_at||"",product:m.product||"",type:m.movement_type||"",qty:m.amount||0,ref:m.description||"",user:"Masa\u00fcst\u00fc"}));db.finance=(source.finance||[]).map(f=>({...f,id:String(f.id),customer:f.customer_name||"",currency:String(f.currency||"TRY").toUpperCase(),original_amount:f.original_amount??f.amount}));db.appointments=(source.appointments||[]).map(a=>({...a,id:String(a.id),customerId:String(a.customer_id||""),title:a.title||a.description||a.fault||"Randevu",status:a.status||"Planland\u0131",alerted:false}));db.quotes=(source.offers||[]).map(q=>({...q,id:String(q.id),customerId:String(q.customer_id||""),no:q.offer_no,total:q.total_try||q.total||0}));scheduledAlerts=source.scheduled_alerts||[];save();render();toast("Masa\u00fcst\u00fc veritaban\u0131 web aray\u00fcz\u00fcne ba\u011fland\u0131","success")}catch(err){toast("Masa\u00fcst\u00fc veritaban\u0131 ba\u011flant\u0131s\u0131 kurulamad\u0131: "+err.message,"error")}};
const runSalesLocal=runSales;runSales=function(mode){const customer=db.customers.find(c=>String(c.id)===String(salesCustomer));const lines=salesCart.map(l=>({line:l,product:db.stock.find(p=>String(p.id)===String(l.productId))}));const total=cartTotal();runSalesLocal(mode);if(!customer)return;if(mode==="payment"){desktopWrite("accounting",{type:"Gelir",category:"Satış",amount:total,original_amount:total,try_equivalent:total,currency:"TRY",exchange_rate:1,description:"Sales Hub web satışı",date:today(),customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,payment_method:"Web"});for(const {product} of lines){if(product&&Number.isInteger(+product.id))desktopWrite("parts",{id:+product.id,_action:"update",stock:product.qty})}}else if(mode==="proforma"){const quote=customer.quotes?.[0];desktopWrite("offers",{offer_no:quote?.no||`PRF-${Date.now()}`,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,company_name:customer.company||customer.name,currency_code:"TRY",currency_symbol:"₺",exchange_rate:1,subtotal:total,total,total_try:total,status:"Teklif",source:"Web Sales Hub"})}else{const service=customer.services?.[0];desktopWrite("devices",{tracking_no:service?.no,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,device_model:lines.map(x=>x.product?.name).filter(Boolean).join(", "),fault_description:"Sales Hub kaydı",status:"Bekliyor",entry_date:today(),service_source:"Web Sales Hub"})}};
runSales=function(mode){const customer=db.customers.find(c=>String(c.id)===String(salesCustomer));if(!customer)throw Error("Önce müşteri seçin");const lines=salesCart.map(line=>{const product=db.stock.find(p=>String(p.id)===String(line.productId));return{line:{...line,productId:product?.id},product}}),total=lines.reduce((sum,x)=>sum+(x.product?normalizedPrice(x.product)*x.line.qty:0),0);salesCustomer=customer.id;salesCart=lines.map(x=>x.line);runSalesLocal(mode);if(mode==="payment"){desktopWrite("accounting",{type:"Gelir",category:"Satış",amount:total,original_amount:total,try_equivalent:total,currency:"TRY",exchange_rate:1,description:"Sales Hub web satışı",date:today(),customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,payment_method:"Web"});lines.forEach(({line,product})=>{if(product&&Number.isInteger(+product.id)){desktopWrite("parts",{id:+product.id,_action:"update",stock:product.qty});desktopWrite("stock_movements",{part_id:+product.id,movement_type:"Çıkış",amount:line.qty,new_stock:product.qty,description:"Sales Hub peşin satış"})}})}else if(mode==="proforma"){const quote=db.quotes[0];desktopWrite("offers",{offer_no:quote.no,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,company_name:customer.company||customer.name,currency_code:"TRY",currency_symbol:"₺",exchange_rate:1,subtotal:total,total,total_try:total,status:"Teklif",source:"Web Sales Hub",payload_json:JSON.stringify(quote)}).then(result=>{if(!result?.id)return;lines.forEach(({line,product})=>desktopWrite("offer_items",{offer_id:result.id,item_id:Number.isInteger(+product?.id)?+product.id:null,item_type:"stock",service:product?.name||"",description:product?.name||"",qty:line.qty,unit_price:normalizedPrice(product),line_total:normalizedPrice(product)*line.qty,payload_json:JSON.stringify(line)}))})}else{const service=customer.services[0];desktopWrite("devices",{tracking_no:service.no,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,device_model:lines.map(x=>x.product?.name).filter(Boolean).join(", "),fault_description:"Sales Hub kaydı",status:"Bekliyor",entry_date:today(),service_source:"Web Sales Hub"})}};
let applicationStarted=false;
function canAccessControlCenter(user=currentAuthUser){return user?.can_access_control_center===true||user?.is_control_admin===true}
function requestedInitialPage(){const requested=new URLSearchParams(window.location.search).get("page");if(requested==="control-center"&&canAccessControlCenter())return requested;return"dashboard"}
async function startApplication(){if(applicationStarted){await hydrateDesktop(true);return}applicationStarted=true;renderNav();navigate(requestedInitialPage());const source=await hydrateDesktop(true);const s=source.settings||{},i=source.internal_settings||{};if(s.company_name)db.settings.company=s.company_name;if(s.default_currency)db.settings.currency=s.default_currency;if(s.appointment_alert_minutes)db.settings.alertMinutes=+s.appointment_alert_minutes||30;if(s.web_double_click!==undefined)db.settings.doubleClick=settingBool(s.web_double_click);if(s.web_context_menu!==undefined)db.settings.contextMenu=settingBool(s.web_context_menu);if(s.appointment_notifications!==undefined)db.settings.appointmentAlerts=settingBool(s.appointment_notifications);if(s.enable_right_click!==undefined)db.settings.contextMenu=settingBool(s.enable_right_click);if(i.feature_right_click_active!==undefined)db.settings.contextMenu=settingBool(i.feature_right_click_active);if(i.feature_double_click_active!==undefined)db.settings.doubleClick=settingBool(i.feature_double_click_active);save();await loadParityState();renderNav();render();checkScheduledAlerts()}
document.addEventListener("click",e=>{const b=e.target.closest('[data-action="copy-customers"],[data-action="print-customers"],[data-action="export-customers-pdf"]');if(!b)return;if(b.dataset.action==="copy-customers"){navigator.clipboard?.writeText(db.customers.map(c=>`${c.name}\t${c.phone}\t${c.email}`).join("\n"));toast("Müşteri listesi panoya kopyalandı")}else window.print()});
function toggleNavParent(button,event){
 if(event){
  if(event.__ayecNavHandled)return true;
  event.__ayecNavHandled=true;
  event.preventDefault();
  event.stopImmediatePropagation();
 }
 const submenu=document.getElementById(button.dataset.parent);
 if(!submenu)return false;
 const open=!submenu.classList.contains("open");
 const nav=button.closest("#nav");
 if(nav&&open){
  $$(".nav-parent",nav).forEach(parent=>{
   if(parent===button)return;
   parent.classList.remove("open");
   parent.setAttribute("aria-expanded","false");
  });
  $$(".submenu",nav).forEach(candidate=>{
   if(candidate===submenu)return;
   candidate.hidden=true;
   candidate.classList.remove("open");
   candidate.style.display="none";
  });
 }
 button.classList.toggle("open",open);
 button.setAttribute("aria-expanded",String(open));
 submenu.hidden=!open;
 submenu.classList.toggle("open",open);
 submenu.style.display=open?"block":"none";
 if(typeof ayecSetOpenParent==="function")ayecSetOpenParent(button,open);
 return true;
}
$("#nav").addEventListener("click",e=>{
 const b=e.target.closest("button.nav-button");
 if(!b||!e.currentTarget.contains(b))return;
 if(b.dataset.parent){toggleNavParent(b,e);return}
 e.preventDefault();
 if(b.dataset.page){navigate(b.dataset.page);if(window.matchMedia("(max-width:760px)").matches)setMobileMenu(false)}
});
document.addEventListener("click",e=>{if(!e.target.closest("#contextMenu"))$("#contextMenu").classList.remove("open");const p=e.target.closest("[data-page]");if(p&&p!==document.body&&!p.closest("#nav")&&!p.closest(".sidebar-bottom")){e.preventDefault();navigate(p.dataset.page)}});
document.addEventListener("click",e=>{const action=e.target.closest("[data-action]")?.dataset.action;if(action==="appointment-prev"){appointmentWeekOffset--;render()}if(action==="appointment-next"){appointmentWeekOffset++;render()}if(action==="appointment-today"){appointmentWeekOffset=0;render()}});
document.addEventListener("click",e=>{if(e.target.closest('[data-action="critical-stock"]')){const level=$("#stockLevel");if(level){level.value="Kritik Stok";level.dispatchEvent(new Event("change"));toast("Kritik stoklar filtrelendi","warning")}}});
document.addEventListener("click",e=>{const button=e.target.closest('[data-action="choose-import-mode"]');if(!button)return;const input=$("#fileInput"),mode=button.dataset.mode;input.dataset.mode=`smart-${mode}`;input.accept=mode==="pdf"?".pdf":mode==="image"?".png,.jpg,.jpeg,.bmp,.webp,.tif,.tiff,.ppm":".xlsx,.xls,.csv,.xml,.docx,.json";input.click()});
document.addEventListener("click",e=>{const button=e.target.closest('[data-action="add-import-row"],[data-action="edit-import-row"],[data-action="delete-import-row"],[data-action="clear-import-rows"],[data-action="delete-product"]');if(!button)return;const action=button.dataset.action;if(action==="add-import-row")return addImportRow();if(action==="edit-import-row")return editImportRow(+button.dataset.index);if(action==="delete-import-row"){const index=+button.dataset.index,name=window.importRows?.[index]?.name||"Satır";window.importRows?.splice(index,1);drawImportPreview();toast(`${name} önizlemeden çıkarıldı`,"warning");return}if(action==="clear-import-rows"){if(confirm("İçe aktarma önizlemesindeki tüm satırlar temizlensin mi?")){window.importRows=[];drawImportPreview();toast("İçe aktarma listesi temizlendi","warning")}return}if(action==="delete-product")deleteProduct(db.stock.find(item=>String(item.id)===String(button.dataset.id))) });
document.addEventListener("click",e=>{if(e.target.closest('[data-action="save-settings"]')&&$("#setModuleValue"))desktopWrite("settings",{key:`web_module_${settingsSection}`,value:$("#setModuleValue").value})});
document.addEventListener("click",e=>{const button=e.target.closest(".manifest-button");if(!button)return;const signal=`${button.textContent} ${button.title}`.toLocaleLowerCase("tr-TR");if(/kapat|vazgeç|iptal|reject|close/.test(signal))return $("#appDialog").close("cancel");if(/yazdır|print|pdf/.test(signal))return window.print();if(/excel|dışa aktar|export/.test(signal))return exportAll();if(/içe aktar|import|ocr/.test(signal)){$("#appDialog").close();return navigate("import")}if(/tahsilat|ödeme|payment/.test(signal)){$("#appDialog").close();return customerSelect(paymentDialog,"Tahsilat için müşteri seçin")}if(/servis|service/.test(signal)){$("#appDialog").close();return serviceDialog()}if(/stok|stock/.test(signal)){$("#appDialog").close();return navigate("stock")}if(/müşteri|customer/.test(signal)){$("#appDialog").close();return navigate("customers")}if(/kaydet|ekle|oluştur|güncelle|save|accept|create|update/.test(signal))$("#dialogForm").requestSubmit()});
 
// Mobile navigation: close the drawer on outside tap, Escape, or selection.
const mobileOverlay=document.createElement("div");
mobileOverlay.id="mobileOverlay";
mobileOverlay.className="mobile-overlay";
mobileOverlay.hidden=true;
document.body.appendChild(mobileOverlay);
const mobileClose=document.createElement("button");
mobileClose.type="button";
mobileClose.className="mobile-drawer-close";
mobileClose.setAttribute("aria-label","Menüyü kapat");
mobileClose.textContent="×";
$("#sidebar")?.prepend(mobileClose);
const mobileNavSearch=document.createElement("input");
mobileNavSearch.type="search";
mobileNavSearch.className="mobile-nav-search";
mobileNavSearch.placeholder="Menüde ara…";
mobileNavSearch.setAttribute("aria-label","Menüde ara");
$("#sidebar")?.insertBefore(mobileNavSearch,$("#nav"));
mobileNavSearch.addEventListener("input",()=>{
 const query=mobileNavSearch.value.trim().toLocaleLowerCase("tr-TR");
 const nav=$("#nav");
 if(!nav)return;
 $$(".nav-button",nav).forEach(button=>{button.hidden=Boolean(query&&!button.textContent.toLocaleLowerCase("tr-TR").includes(query))});
 $$(".submenu",nav).forEach(submenu=>{
  const childMatch=Boolean(query&&submenu.textContent.toLocaleLowerCase("tr-TR").includes(query));
  submenu.hidden=Boolean(query&&!childMatch);
  if(query&&childMatch)submenu.classList.add("open");
  const parent=submenu.previousElementSibling;
  if(parent&&query&&childMatch)parent.hidden=false;
 });
 $$(".nav-group-title",nav).forEach(title=>{title.hidden=Boolean(query&&!title.nextElementSibling)});
});
function setMobileMenu(open){
 const sidebar=$("#sidebar"),toggle=$("#menuToggle");
 const visible=Boolean(open);
 sidebar?.classList.toggle("open",visible);
 if(sidebar){sidebar.style.transform=visible?"translate3d(0,0,0)":"";sidebar.style.visibility=visible?"visible":"";}
 mobileOverlay.classList.toggle("open",visible);
 mobileOverlay.hidden=!visible;
 document.body.classList.toggle("mobile-menu-open",visible);
 toggle?.setAttribute("aria-expanded",String(visible));
 toggle?.setAttribute("aria-label",visible?"Menüyü kapat":"Menüyü aç");
}
const menuToggle=$("#menuToggle");
menuToggle?.addEventListener("click",event=>{
 event.preventDefault();
 event.stopPropagation();
 setMobileMenu(!$("#sidebar")?.classList.contains("open"));
});
mobileOverlay.addEventListener("click",()=>setMobileMenu(false));
mobileClose.addEventListener("click",()=>setMobileMenu(false));
document.addEventListener("keydown",event=>{if(event.key==="Escape")setMobileMenu(false)});
document.addEventListener("click",event=>{
 if(!window.matchMedia("(max-width:760px)").matches||!$("#sidebar")?.classList.contains("open"))return;
 if(event.target.closest("#sidebar,#menuToggle"))return;
 setMobileMenu(false);
});
document.addEventListener("click",event=>{
 // Keep the drawer open while a parent is expanded. Close only after a
 // concrete page is selected; otherwise tapping "Stok Yönetimi" immediately
 // dismisses the drawer before its submenu can be reached on mobile.
 if(event.target.closest("#nav [data-page],.sidebar-bottom [data-page]"))setMobileMenu(false);
});
$(".sidebar-bottom [data-page]").onclick=()=>navigate("settings");
$("#fileInput").onchange=e=>{const file=e.target.files[0],mode=e.target.dataset.mode;if(!file)return;if(mode==="restore-backup"){const r=new FileReader();r.onload=()=>{try{db=JSON.parse(r.result);save();navigate("dashboard");toast("Yedek geri yüklendi")}catch{toast("Geçersiz yedek dosyası","error")}};r.readAsText(file)}else if(mode==="import-customers"){const r=new FileReader();r.onload=()=>{try{const rows=file.name.endsWith(".json")?JSON.parse(r.result):parseCSV(r.result);rows.forEach(x=>db.customers.push({id:uid("cus"),name:x.name||x["müşteri"]||x.code,phone:x.phone||"",email:x.email||"",type:x.type||"Bireysel",balances:x.balances||{TRY:0,USD:0,EUR:0},services:[],quotes:[]}));save();render();toast(`${rows.length} müşteri içe aktarıldı`)}catch{toast("Müşteri dosyası okunamadı","error")}};r.readAsText(file)}else handleImport(file);e.target.value=""};
$("#globalSearch").onkeydown=e=>{if(e.key!=="Enter")return;const q=e.target.value.toLocaleLowerCase("tr-TR"),c=db.customers.find(x=>x.name.toLocaleLowerCase("tr-TR").includes(q)),s=db.stock.find(x=>x.name.toLocaleLowerCase("tr-TR").includes(q));if(c){navigate("customers");setTimeout(()=>{$("#customerSearch").value=e.target.value;$("#customerSearch").dispatchEvent(new Event("input"))},0)}else if(s){navigate("stock");setTimeout(()=>{$("#stockSearch").value=e.target.value;$("#stockSearch").dispatchEvent(new Event("input"))},0)}else toast("Eşleşen kayıt bulunamadı","warning")};
$("#notificationBtn").onclick=()=>{if("Notification" in window&&Notification.permission==="default")Notification.requestPermission();openDialog("Bildirimler","UYARI MERKEZİ",notifications.length?notifications.map(n=>`<div class="activity"><span class="activity-icon">!</span><p>${esc(n)}</p></div>`).join(""):empty("Yeni bildirim yok","Randevu uyarıları burada görüntülenir."),()=>true,"Kapat")};
setInterval(checkAppointments,30000);checkAppointments();
setInterval(checkScheduledAlerts,30000);

// Desktop parity: company logo, desktop proforma templates and service dashboard.
let dashboardFilter="all";

function dashboardServices(){
 return db.customers.flatMap(customer=>(customer.services||[]).map(service=>({...service,customer:customer.name,customerId:customer.id,balances:customer.balances||{}})));
}
function serviceStatusKey(service){
 const status=String(service.status||"").toLocaleLowerCase("tr-TR");
 if(/iptal|iade/.test(status))return "iptal";
 if(/kargo|dış servis/.test(status))return "kargo";
 if(/teslim/.test(status))return "teslim";
 if(/parça/.test(status))return "parca";
 if(/tamir edildi|test.*tamam|kontrol.*tamam|tamamlandı|bitti/.test(status))return "test";
 if(/tamirde|işlemde|serviste|devam/.test(status))return "tamirde";
 return "bekliyor";
}
function serviceIsDebt(service){
 const payment=String(service.payment_status||"").toLocaleLowerCase("tr-TR");
 // Desktop convention: negative customer balance means an open receivable.
 const balance=Object.values(service.balances||{}).some(value=>Number(value)<0);
 return balance||Number(service.amount||0)>0&&/bekle|ödenmedi|borç/.test(payment);
}
function dashboardFilterMatch(service,filter){
 if(filter==="all")return true;
 if(filter==="today")return String(service.date||"").slice(0,10)===today()||db.appointments.some(a=>String(a.customerId)===String(service.customerId)&&a.date===today());
 if(filter==="pending_approval")return /bekle|onay/.test(String(service.approval_status||"").toLocaleLowerCase("tr-TR"));
 if(filter==="test")return serviceStatusKey(service)==="test";
 if(filter==="waiting")return serviceStatusKey(service)==="bekliyor";
 if(filter==="active")return serviceStatusKey(service)==="tamirde";
 if(filter==="done")return serviceStatusKey(service)==="teslim";
 if(filter==="part")return serviceStatusKey(service)==="parca";
 if(filter==="debt")return serviceIsDebt(service);
 return true;
}
function dashboardServiceTable(rows){
 const automotive=currentSector==="otomotiv";
 if(!rows.length)return empty(automotive?"Bu filtrede araç bulunmuyor.":"Bu filtrede cihaz bulunmuyor.","Yeni servis kaydı oluşturabilir veya başka bir filtre seçebilirsiniz.");
 return `<div class="table-wrap dashboard-service-table"><table><thead><tr><th>${automotive?"İŞ EMRİ NO":"TAKİP NO"}</th><th>İŞLEMLER</th><th>MÜŞTERİ</th><th>${automotive?"ARAÇ TÜRÜ":"ÜRÜN GRUBU"}</th><th>MARKA</th><th>MODEL</th><th>ALIŞ TARİHİ</th><th>TESLİM TARİHİ</th><th>SERVİS</th><th>ÜCRET</th><th>DURUM</th><th>${automotive?"ÖNCELİK":"ACİLİYET"}</th></tr></thead><tbody>${rows.map(s=>`<tr data-kind="service" data-id="${esc(s.no)}" data-customer="${esc(s.customerId)}"><td><strong>${esc(s.no)}</strong></td><td><div class="dashboard-row-actions"><button class="mini" data-action="service-detail" data-id="${esc(s.no)}" title="Servis ayrıntısı">ⓘ</button><button class="mini" data-action="technician-open" data-id="${esc(s.no)}" title="Teknisyen işlemi">⚙</button></div></td><td>${esc(s.customer)}</td><td>${esc(s.device_type||s.device||"Cihaz")}</td><td>${esc(s.brand||"—")}</td><td>${esc(s.model||s.device||"—")}</td><td>${esc(s.date||"—")}</td><td>${esc(s.delivery||"—")}</td><td>${esc(s.service||"Servis")}</td><td><strong>${money(s.amount||0,s.currency||"TRY")}</strong></td><td>${statusBadge(s.status||"Bekliyor")}</td><td>${statusBadge(s.priority||"Normal")}</td></tr>`).join("")}</tbody></table></div>`;
}
renderDashboard=function(){
 const automotive=currentSector==="otomotiv",services=dashboardServices(),visible=services.filter(service=>dashboardFilterMatch(service,dashboardFilter));
 const tileDefs=automotive?[
  ["test","KONTROLÜ TAMAMLANAN","Kontrol Tamamlandı","K","#05A85B"],["tamirde","SERVİSTEKİ ARAÇLAR","İş Emri Devam Ediyor","S","#F39C12"],["bekliyor","SIRAYA ALINACAKLAR","Servise Alınmadı","A","#1E88E5"],["iptal","İPTAL / İADE","İptal İade","X","#E24A3B"],["kargo","DIŞ SERVİSE GİDENLER","Dış Servise Verildi","D","#D41462"],["teslim","TESLİM EDİLEN ARAÇLAR","Teslim Edildi","T","#0891B2"],["parca","PARÇA BEKLEYEN ARAÇ","Parça Bekliyor","P","#0E7AB4"],["borclu","BORÇLU ARAÇLAR","Borcu Var","B","#625DA8"]
 ]:[
  ["test","TAMİR EDİLENLER","Tamir Edildi","T","#05A85B"],["tamirde","TAMİRDE OLANLAR","Tamiri Devam Etmekte","D","#F39C12"],["bekliyor","İŞLEME ALINACAKLAR","İşleme Alınmadı","İ","#1E88E5"],["iptal","İPTAL / İADE","İptal İade","X","#E24A3B"],["kargo","KARGOYA VERİLENLER","Kargoya Verildi","K","#D41462"],["teslim","TESLİM EDİLENLER","Teslim Edildi","E","#0891B2"],["parca","PARÇA BEKLEYENLER","Parça Bekliyor","P","#0E7AB4"],["borclu","BORÇLU OLANLAR","Borcu Var","B","#625DA8"]
 ];
 const countFor=key=>key==="borclu"?services.filter(serviceIsDebt).length:services.filter(service=>serviceStatusKey(service)===key).length;
 const percent=count=>services.length?Math.round(count/services.length*100):0;
 const tiles=tileDefs.map(([key,title,sub,icon,color])=>{const count=countFor(key);return `<button class="service-status-card" data-dashboard-tile="${key}" data-dashboard-filter="${key==="parca"?"part":key==="teslim"?"done":key==="tamirde"?"active":key==="bekliyor"?"waiting":key==="borclu"?"debt":key==="test"?"test":"all"}" style="--tile:${color}"><span class="service-status-icon">${icon}</span><span><small>${title}</small><strong>${count} ADET</strong><em>${percent(count)}% ${sub}</em></span><b>${percent(count)}%</b></button>`}).join("");
 const filterDefs=automotive?[["add_device","Araç Ekle","+"],["all","Tüm Araçlar","="],["today","Randevulu","R"],["pending_approval","Onay Bekleyen","OK"],["test","Kontrol Sürecinde","O"],["waiting","Servise Alınacak",">"],["active","Serviste","*"],["done","Teslim Edilen","-"],["part","Parça Bekleyen","P"],["debt","Borçlu","TL"]]:[["add_device","Cihaz Ekle","+"],["all","Tüm Cihazlar","="],["today","Randevulu","R"],["pending_approval","Onay Bekleyen","OK"],["test","Test Sürecinde","O"],["waiting","İşleme Alınacak",">"],["active","Tamirde","*"],["done","Teslim Edilen","-"],["part","Parça Bekleyen","P"],["debt","Borçlu","TL"]];
 const filters=filterDefs.map(([key,label,icon])=>`<button class="dashboard-filter ${dashboardFilter===key?"active":""}" data-dashboard-filter="${key}"><b>${icon}</b><span>${label}</span></button>`).join("");
 const tableTitles={all:automotive?"İş Emri Listesi":"Servis Listesi",today:"Randevulu Servisler",pending_approval:"Onay Bekleyen Servisler",test:automotive?"Kontrol Sürecindeki Araçlar":"Test Sürecindeki Cihazlar",waiting:automotive?"Servise Alınacak Araçlar":"İşleme Alınacak Cihazlar",active:automotive?"Servisteki Araçlar":"Tamirdeki Cihazlar",done:"Teslim Edilenler",part:"Parça Bekleyenler",debt:"Borçlu Servisler"};
 return `${pageHead("Genel Bakış",automotive?"Otomotiv servis durumları, iş emirleri ve hızlı işlemler.":"Masaüstü uygulamasıyla aynı servis durumları, filtreler ve işlem listesi.",'<button class="secondary" data-page="finance">Finans</button><button class="primary" data-action="new-service">＋ Yeni Servis</button>')}<div class="service-status-grid">${tiles}</div><section class="dashboard-filter-strip">${filters}</section><section class="card dashboard-list-card"><div class="card-head"><h3>${tableTitles[dashboardFilter]||tableTitles.all}</h3><span class="badge">${visible.length} kayıt</span></div>${dashboardServiceTable(visible)}</section>`;
};

document.addEventListener("click",event=>{
 const button=event.target.closest("[data-dashboard-filter]");
 if(!button)return;
 event.preventDefault();
 if(button.dataset.dashboardFilter==="add_device")return serviceDialog();
 dashboardFilter=button.dataset.dashboardFilter;
 render();
});

const settingBodyBeforeCompanyLogo=settingBody;
settingBody=function(settings){
 const body=settingBodyBeforeCompanyLogo(settings);
 if(settingsSection!=="company")return body;
 return `<section class="company-logo-card"><div class="company-logo-preview"><img id="companyLogoPreview" src="/api/desktop/company-logo?v=${Date.now()}" alt="Firma logosu" onload="this.nextElementSibling.hidden=true" onerror="this.hidden=true"><span>Firma logosu seçilmedi</span></div><div><h3>Firma Logosu</h3><p class="muted">PNG, JPG veya WEBP yükleyin. Logo aynı masaüstü ayarına kaydedilir ve üç proforma şablonunda otomatik kullanılır.</p><div class="actions"><button type="button" class="primary" data-action="upload-company-logo">Logo Seç / Değiştir</button><button type="button" class="danger" data-action="remove-company-logo">Logoyu Kaldır</button></div></div></section>${body}`;
};
function refreshCompanyLogo(){
 const image=$("#brandLogo"),initial=$("#brandInitial");
 if(!image)return;
 image.onload=()=>{image.hidden=false;if(initial)initial.hidden=true};
 image.onerror=()=>{image.hidden=true;if(initial)initial.hidden=false};
 image.src=`/api/desktop/company-logo?v=${Date.now()}`;
}
async function uploadCompanyLogo(file){
 if(!file)return;
 if(file.size>5*1024*1024)return toast("Logo 5 MB sınırını aşıyor","error");
 const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(",")[1]);reader.onerror=reject;reader.readAsDataURL(file)});
 try{
  const result=await apiFetch("/api/desktop/company-logo",{method:"POST",body:JSON.stringify({name:file.name,data})});
  desktopSettings.logo_path=result.path;
  refreshCompanyLogo();
  render();
  toast("Firma logosu kaydedildi; proforma şablonlarına bağlandı","success");
 }catch(error){toast(`Logo yüklenemedi: ${error.message}`,"error")}
}
document.addEventListener("click",async event=>{
 const action=event.target.closest("[data-action]")?.dataset.action;
 if(action==="upload-company-logo")$("#companyLogoInput").click();
 if(action==="remove-company-logo"&&confirm("Firma logosu kaldırılsın mı?")){
  try{await apiFetch("/api/desktop/company-logo",{method:"POST",body:JSON.stringify({remove:true})});desktopSettings.logo_path="";refreshCompanyLogo();render();toast("Firma logosu kaldırıldı","warning")}catch(error){toast(error.message,"error")}
 }
});
$("#companyLogoInput").onchange=event=>{uploadCompanyLogo(event.target.files[0]);event.target.value=""};
setTimeout(refreshCompanyLogo,0);

function proformaEndpoint(offer,template,download=false){return `/api/desktop/proforma/${encodeURIComponent(offer.id)}?template=${encodeURIComponent(template)}${download?"&download=1":""}`}
function openProformaDocument(offer,customer){
 if(!offer||!/^\d+$/.test(String(offer.id||"")))return toast("Teklif veritabanına kaydedilmeden açılamaz","error");
 let template=["modern","corporate","minimal"].includes(offer.template_type)?offer.template_type:"modern";
 const choices=[["modern","Modern (Premium)","Lacivert başlık ve açık mavi satırlar"],["corporate","Kurumsal (Premium)","Kurumsal lacivert ve sade tablo"],["minimal","Zebra (Premium)","Siyah-beyaz zebra görünüm"]];
 const body=`<div class="proforma-viewer"><div class="proforma-template-picker">${choices.map(([key,title,desc])=>`<button type="button" data-proforma-template="${key}" class="${template===key?"active":""}"><strong>${title}</strong><small>${desc}</small></button>`).join("")}</div><iframe id="proformaFrame" title="${esc(offer.no||offer.offer_no||"Proforma")}" src="${proformaEndpoint(offer,template)}"></iframe></div>`;
 openDialog(`${offer.no||offer.offer_no||"Proforma"} — ${customer?.name||offer.customer_name||"Müşteri"}`,"MASAÜSTÜ PROFORMA TEKLİF FORMU",body,()=>true,"Kapat");
 const dialog=$("#appDialog");dialog.classList.add("dialog-wide");dialog.addEventListener("close",()=>dialog.classList.remove("dialog-wide"),{once:true});
 $("#dialogFooter").innerHTML='<button type="button" class="secondary" id="proformaDownload">PDF İndir</button><button type="button" class="primary" id="proformaPrint">Yazdır</button><button type="button" class="secondary" id="proformaClose">Kapat</button>';
 $("#proformaClose").onclick=()=>dialog.close();
 $("#proformaPrint").onclick=()=>$("#proformaFrame").contentWindow?.print();
 $("#proformaDownload").onclick=()=>window.open(proformaEndpoint(offer,template,true),"_blank");
 $$("[data-proforma-template]").forEach(button=>button.onclick=()=>{
  template=button.dataset.proformaTemplate;offer.template_type=template;
  $$("[data-proforma-template]").forEach(item=>item.classList.toggle("active",item===button));
  $("#proformaFrame").src=proformaEndpoint(offer,template);
  $("#proformaDownload").onclick=()=>window.open(proformaEndpoint(offer,template,true),"_blank");
  desktopWrite("offers",{id:+offer.id,_action:"update",template_type:template});
 });
}

const customer360BeforeProforma=customer360;
customer360=function(customer){
 customer360BeforeProforma(customer);
 const offers=customer.quotes||[];
 $$(".c360-print-offer").forEach((button,index)=>button.onclick=()=>{$("#appDialog").close();setTimeout(()=>openProformaDocument(offers[index],customer),60)});
};
quoteDialog=function(){
 openDialog("Proforma Teklifler","SALES HUB",db.quotes.length?`<div class="table-wrap"><table><thead><tr><th>No</th><th>Müşteri</th><th>Şablon</th><th>Tarih</th><th>Tutar</th><th>Durum</th><th></th></tr></thead><tbody>${db.quotes.map((q,index)=>`<tr><td><strong>${esc(q.no||q.offer_no)}</strong></td><td>${esc(customerName(String(q.customerId||q.customer_id)))}</td><td>${esc({modern:"Modern",corporate:"Kurumsal",minimal:"Zebra"}[q.template_type]||"Modern")}</td><td>${esc(q.date||q.created_at||"")}</td><td>${money(q.total_try||q.total||0)}</td><td>${statusBadge(q.status||"Teklif")}</td><td><button type="button" class="mini quote-open" data-index="${index}">Aç</button></td></tr>`).join("")}</tbody></table></div>`:empty("Proforma yok","Sales Hub üzerinden ilk teklifi oluşturun."),()=>true,"Kapat");
 $$(".quote-open").forEach(button=>button.onclick=()=>{const offer=db.quotes[+button.dataset.index],customer=db.customers.find(c=>String(c.id)===String(offer.customerId||offer.customer_id));$("#appDialog").close();setTimeout(()=>openProformaDocument(offer,customer),60)});
};

renderSales=function(){
 const subtotal=cartTotal();
 return `${pageHead("Sales Hub","Stoktaki ürünlerden tahsilat, masaüstü proforma şablonu ve servis akışlarını yönetin.",'<button class="secondary" data-action="view-quotes">Proformalar</button>')}<div class="grid-2 sales-grid"><section class="card"><div class="card-head"><h3>1. Müşteri ve ürün seçimi</h3><span class="badge">Canlı stok</span></div><div class="toolbar"><select class="control" id="salesCustomer"><option value="">Müşteri seçin…</option>${db.customers.map(c=>`<option value="${c.id}" ${String(salesCustomer)===String(c.id)?"selected":""}>${esc(c.name)}</option>`).join("")}</select><input class="control search" id="salesProductSearch" placeholder="Stokta ürün ara"></div><div id="salesProducts" class="product-picker">${salesProducts(db.stock)}</div></section><aside class="card"><div class="card-head"><h3>2. Teklif sepeti</h3><span class="badge">${salesCart.length} kalem</span></div><div id="salesCart">${cartHtml()}</div><div class="proforma-options"><div class="field"><label>Teklif şablonu</label><select id="proformaTemplate"><option value="modern">Modern (Premium)</option><option value="corporate">Kurumsal (Premium)</option><option value="minimal">Zebra (Premium)</option></select></div><div class="field"><label>Proje / İş adı</label><input id="salesProject" placeholder="İsteğe bağlı"></div><div class="field"><label>KDV (%)</label><input id="salesVat" type="number" min="0" max="100" step="1" value="0"></div></div><div class="kpi-inline"><div><small class="muted">Ara toplam</small><strong id="cartTotal">${money(subtotal)}</strong></div></div><div class="actions sales-actions"><button class="success" data-action="pay-save">Ödeme Al ve Kaydet</button><button class="primary" data-action="create-proforma">Proforma Oluştur</button><button class="secondary" data-action="save-service">Servis Kaydet</button></div></aside></div>`;
};

function nextOfferNumber(){const year=new Date().getFullYear(),max=db.quotes.reduce((current,quote)=>{const match=String(quote.no||quote.offer_no||"").match(/(\d+)$/);return Math.max(current,match?+match[1]:0)},0);return `PRF-${year}-${String(max+1).padStart(4,"0")}`}
function normalizedCost(product){return Number(product.buy||0)*(product.currency==="USD"?33:product.currency==="EUR"?36:1)}
runSales=async function(mode){
 try{
  const customer=db.customers.find(c=>String(c.id)===String(salesCustomer));
  if(!customer)throw Error("Önce müşteri seçin");
   const customerId=Number.isInteger(+customer.id)?+customer.id:Number.isInteger(+customer.desktopId)?+customer.desktopId:0;
  if(!customerId&&!String(customer.name||"").trim())throw Error("Müşteri sunucu veritabanına kaydedilmemiş. Müşteri listesini yenileyip tekrar deneyin.");
   if(!salesCart.length)throw Error("Sepete en az bir ürün ekleyin");
  const lines=salesCart.map(line=>{const product=db.stock.find(item=>String(item.id)===String(line.productId));if(!product||Number(line.qty)>Number(product.qty))throw Error(`${product?.name||"Ürün"} için yeterli stok yok`);return{line,product,qty:Number(line.qty),price:normalizedPrice(product)}});
  const subtotal=lines.reduce((sum,item)=>sum+item.price*item.qty,0),vatRate=Number($("#salesVat")?.value||0),vatAmount=subtotal*vatRate/100,total=subtotal+vatAmount;
  const template=$("#proformaTemplate")?.value||"modern",project=$("#salesProject")?.value.trim()||"",no=nextOfferNumber();
  if(mode==="proforma"){
   const quote={no,offer_no:no,date:today(),created_at:new Date().toISOString(),customerId:String(customer.id),customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,company_name:customer.company||customer.company_name||customer.name,contact_name:customer.name,project_name:project,template_type:template,currency_code:"TRY",currency_symbol:"₺",exchange_rate:1,subtotal,discount:0,vat_rate:vatRate/100,vat_amount:vatAmount,total,total_try:total,status:"Teklif",source:"Web Sales Hub",items:lines.map(({product,qty,price})=>({productId:product.id,name:product.name,service:product.name,description:product.name,brand:product.brand||"",code:product.code||"",qty,price}))};
   const offerResult=await apiFetch("/api/desktop/table/offers",{method:"POST",body:JSON.stringify({...quote,items:undefined,payload_json:JSON.stringify(quote)})});
   quote.id=String(offerResult.id);
   await Promise.all(quote.items.map(item=>apiFetch("/api/desktop/table/offer_items",{method:"POST",body:JSON.stringify({offer_id:+quote.id,item_id:Number.isInteger(+item.productId)?+item.productId:null,item_type:"stock",service:item.service,description:item.description,brand:item.brand,qty:item.qty,unit_price:item.price,line_total:item.qty*item.price,payload_json:JSON.stringify(item)})})));
   db.quotes.unshift(quote);customer.quotes=customer.quotes||[];customer.quotes.unshift(quote);salesCart=[];save();activity(`${no} ${template} proforma ${customer.name} için oluşturuldu`,"◇");render();toast("Proforma oluşturuldu, Müşteri 360'a kaydedildi ve teklif formu hazırlandı","success");setTimeout(()=>openProformaDocument(quote,customer),60);return;
  }
  if(mode==="payment"){
   const saleNo=`SAT-${Date.now()}`,cost=lines.reduce((sum,item)=>sum+normalizedCost(item.product)*item.qty,0);
   const incomeResult=await apiFetch("/api/desktop/table/accounting",{method:"POST",body:JSON.stringify({type:"Gelir",category:"Satış",amount:total,original_amount:total,try_equivalent:total,currency:"TRY",exchange_rate:1,description:`${saleNo} Sales Hub peşin satış`,date:today(),customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,payment_method:"Web"})});
   let costResult=null;if(cost>0)costResult=await apiFetch("/api/desktop/table/accounting",{method:"POST",body:JSON.stringify({type:"Gider",category:"Satılan Malın Maliyeti",amount:cost,original_amount:cost,try_equivalent:cost,currency:"TRY",exchange_rate:1,description:`Satılan Malın Maliyeti - ${saleNo} (${lines.length} kalem)`,date:today(),customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,payment_method:"Web"})});
   for(const item of lines){item.product.qty-=item.qty;await apiFetch("/api/desktop/table/parts",{method:"POST",body:JSON.stringify({id:+item.product.id,_action:"update",stock:item.product.qty})});const move=await apiFetch("/api/desktop/table/stock_movements",{method:"POST",body:JSON.stringify({part_id:+item.product.id,movement_type:"Çıkış",amount:item.qty,new_stock:item.product.qty,description:`${saleNo} Sales Hub peşin satış`})});db.movements.unshift({id:String(move.id),date:new Date().toLocaleString("tr-TR"),product:item.product.name,type:"Çıkış",qty:item.qty,ref:saleNo,user:"Yönetici"})}
   db.finance.unshift({id:String(incomeResult.id),date:today(),type:"Gelir",category:"Satış",amount:total,currency:"TRY",description:`${saleNo} Sales Hub peşin satış`,customer:customer.name});if(costResult)db.finance.unshift({id:String(costResult.id),date:today(),type:"Gider",category:"Satılan Malın Maliyeti",amount:cost,currency:"TRY",description:`Satılan Malın Maliyeti - ${saleNo}`,customer:customer.name});salesCart=[];save();activity(`${customer.name} satışından ${money(total)} tahsil edildi`,"₺");render();toast("Ödeme, stok çıkışı, gelir ve ürün maliyeti finans kayıtlarına işlendi","success");return;
  }
  const serviceNo=`SRV-${1000+db.customers.flatMap(item=>item.services||[]).length+1}`,device=lines.map(item=>item.product.name).join(", ");
  const serviceResult=await apiFetch("/api/desktop/table/devices",{method:"POST",body:JSON.stringify({tracking_no:serviceNo,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,device_type:currentSector==="otomotiv"?"Araç":"Cihaz",device_model:device,fault_description:`Sales Hub kaydı — ${no}`,status:"Bekliyor",entry_date:today(),service_source:"Web Sales Hub",priority:"Normal",payment_status:"Beklemede"})});
  customer.services=customer.services||[];customer.services.unshift({id:String(serviceResult.id),date:today(),no:serviceNo,device,device_type:currentSector==="otomotiv"?"Araç":"Cihaz",model:device,status:"Bekliyor",note:`Sales Hub kaydı — ${no}`,amount:0,currency:"TRY",service:"Web Sales Hub",priority:"Normal",payment_status:"Beklemede"});salesCart=[];save();activity(`${serviceNo} Sales Hub üzerinden oluşturuldu`,"⚒");render();toast("Servis Müşteri 360 geçmişine ve masaüstü servis listesine kaydedildi","success");
 }catch(error){toast(error.message||"Sales Hub işlemi tamamlanamadı","error")}
};

deleteProduct=async function(product){
 if(!product)return;
 if(!confirm(`“${product.name}” stok kartı silinsin mi? Kalan ${product.qty} adet için masaüstündeki gibi finans ters kaydı ve stok çıkış hareketi oluşturulacaktır.`))return;
 try{
  if(!/^\d+$/.test(String(product.id)))throw Error("Bu stok kartı masaüstü veritabanına henüz kaydedilmemiş");
  const result=await apiFetch("/api/desktop/stock/delete",{method:"POST",body:JSON.stringify({id:+product.id})});
  db.stock=db.stock.filter(item=>String(item.id)!==String(product.id));
  db.movements.unshift({id:String(result.movement_id),date:new Date().toLocaleString("tr-TR"),product:product.name,type:"Çıkış (Silindi)",qty:-Number(result.stock||0),ref:`Kart Silindi: ${product.name}`,user:"Yönetici"});
  if(result.finance_id)db.finance.unshift({id:String(result.finance_id),date:today(),type:"Gelir",category:"Stok İptali / Silinme",amount:Number(result.refund||0),currency:result.currency||product.currency||"TRY",description:`Stok Kartı Silinme İadesi: ${result.stock} x ${product.name}`,customer:""});
  save();activity(`${product.name} stok kartı, hareketi ve finans ters kaydı işlendi`,"×");render();toast(result.finance_id?`Stok silindi; ${money(result.refund,result.currency)} finans iadesi işlendi`:"Stok silindi; maliyet veya kalan adet olmadığı için finans tutarı oluşmadı","success");
 }catch(error){toast(`Ürün silinemedi: ${error.message}`,"error")}
};

// Desktop parity v4: currency-safe transactions, configurable navigation and responsive themes.
let desktopPersonnel=[];
let exchangeRateState={TRY:{selling:1,source:"Sabit",date:today()}};
let salesCurrency=["TRY","USD","EUR"].includes(localStorage.getItem("ayec_sales_currency"))?localStorage.getItem("ayec_sales_currency"):"TRY";
let salesManualRates={};
const supportedThemes=[
 {id:"light",label:"Aydınlık",a:"#f5f7fb",b:"#6558e8"},
 {id:"dark",label:"Koyu",a:"#111827",b:"#8b7cf6"},
 {id:"midnight",label:"Gece",a:"#050817",b:"#22d3ee"},
 {id:"forest",label:"Orman",a:"#eaf5ee",b:"#137c55"},
 {id:"sakura",label:"Sakura",a:"#fff2f7",b:"#d94f86"},
 {id:"sunset",label:"Gün Batımı",a:"#fff2e3",b:"#e35d30"},
 {id:"terra",label:"Toprak",a:"#f2ebe2",b:"#96644a"},
 {id:"neon",label:"Neon",a:"#080914",b:"#8b5cf6"}
];

const modernMenu=[
 {group:"Operasyon",items:[
  {id:"dashboard",icon:"⌂",label:"Genel Bakış"},
  {id:"service-parent",icon:"▦",label:"Servis Yönetimi",children:[{id:"services",label:"Servis Panosu"},{id:"technician",label:"Teknisyen Paneli"},{id:"field-service",label:"Saha Servis Haritası"},{id:"appointments",label:"Randevular"},{id:"logistics",label:"Lojistik & Garanti"},{id:"job-reports",label:"İş / Servis Raporları"}]},
  {id:"vehicle-maintenance",icon:"◇",label:"Araç Bakım Takibi"},{id:"assistant",icon:"✦",label:"AI Asistan"}
 ]},
 {group:"Müşteri",items:[{id:"customers",icon:"♙",label:"Müşteri Hub"},{id:"contracts",icon:"▤",label:"Bakım Sözleşmeleri"},{id:"reminders",icon:"◷",label:"Hatırlatıcılar"},{id:"announcements",icon:"◉",label:"Duyurular"}]},
 {group:"Ticari",items:[
  {id:"stock-parent",icon:"▥",label:"Stok Yönetimi",children:[{id:"stock",label:"Stok Listesi"},{id:"movements",label:"Stok Hareketleri"},{id:"import",label:"Akıllı İçe Aktarma"}]},
  {id:"sales",icon:"◆",label:"Sales Hub"},{id:"service-definitions",icon:"◇",label:"Hizmet Tanımları"},{id:"brands",icon:"◈",label:"Cihaz & Markalar"},{id:"loaners",icon:"▣",label:"Emanet / Konsinye"},{id:"automotive-stock",icon:"◫",label:"Araç Parça Stoğu"},{id:"mobile-guide",icon:"▧",label:"Mobil Teknik Kılavuz"},{id:"pc-builder",icon:"▨",label:"PC Yapılandırıcı"}
 ]},
 {group:"Finans",items:[
  {id:"finance-parent",icon:"₺",label:"Finans Yönetimi",children:[{id:"finance",label:"Finans Özeti"},{id:"income",label:"Gelirler"},{id:"expense",label:"Giderler"}]},
  {id:"banks",icon:"▤",label:"Banka Hesapları"},{id:"checks",icon:"▥",label:"Çek / Senet"},{id:"invoices",icon:"▱",label:"E-Fatura"}
 ]},
 {group:"Proje & Ekip",items:[{id:"projects",icon:"▣",label:"Proje Yönetimi"},{id:"project-archive",icon:"▤",label:"Proje Arşivi"},{id:"personnel",icon:"♟",label:"Personel Yönetimi"},{id:"partners",icon:"♧",label:"Çalışma Ortakları"}]},
 {group:"Sistem",items:[{id:"knowledge",icon:"▧",label:"Bilgi Bankası"},{id:"settings",icon:"⚙",label:"Ayarlar"},{id:"backup",icon:"▰",label:"Yedekleme"},{id:"support",icon:"?",label:"Destek"},{id:"audit",icon:"▤",label:"Log Kayıtları"},{id:"manual",icon:"▧",label:"Kullanım Kılavuzu"},{id:"dialog-catalog",icon:"▦",label:"Dialog Modülleri"}]}
];
menu.splice(0,menu.length,...modernMenu);

// Automotive uses its dedicated parts screen. Keep generic technical stock out.
for(const pageId of ["stock-parent","stock","movements","import"]){
  sectorPages.otomotiv.delete(pageId);
}
const automotiveStockItem=modernMenu
  .flatMap(group=>group.items)
  .find(item=>item.id==="automotive-stock");
const automotiveTradeGroup=modernMenu.find(group=>group.group==="Ticari");
if(automotiveTradeGroup&&automotiveStockItem){
  automotiveTradeGroup.items=automotiveTradeGroup.items.filter(item=>item.id!=="automotive-stock");
  const serviceParent=modernMenu
    .flatMap(group=>group.items)
    .find(item=>item.id==="service-parent");
  if(serviceParent&&!serviceParent.children.some(item=>item.id==="automotive-stock")){
    serviceParent.children.splice(2,0,automotiveStockItem);
  }
}

function menuLabels(){try{return JSON.parse(desktopInternalSettings.web_menu_labels||localStorage.getItem("ayec_menu_labels")||"{}")||{}}catch{return{}}}
function menuVisibility(){try{return JSON.parse(desktopInternalSettings.web_menu_visibility||localStorage.getItem("ayec_menu_visibility")||"{}")||{}}catch{return{}}}
function labelFor(item){return menuLabels()[item.id]||item.label}
function menuVisible(item){return menuVisibility()[item.id]!==false}
function firstVisiblePage(){const allowed=sectorPages[currentSector]||sectorPages.teknik_servis;for(const group of menu){for(const item of group.items){if(!menuVisible(item))continue;if(item.children){const child=item.children.find(entry=>allowed.has(entry.id)&&menuVisible(entry));if(child)return child.id}else if(allowed.has(item.id))return item.id}}return"dashboard"}
renderNav=function(){
 const allowed=sectorPages[currentSector]||sectorPages.teknik_servis;
 $("#nav").innerHTML=menu.map(group=>{
  const items=group.items.filter(item=>menuVisible(item)&&(allowed.has(item.id)||item.children?.some(child=>allowed.has(child.id)&&menuVisible(child)))).map(item=>item.children?{...item,children:item.children.filter(child=>allowed.has(child.id)&&menuVisible(child))}:item).filter(item=>!item.children||item.children.length);
  return items.length?`<div class="nav-group-title">${esc(group.group)}</div>${items.map(item=>item.children?`<button type="button" class="nav-button nav-parent ${item.children.some(child=>child.id===page)?"open":""}" data-parent="${item.id}" aria-expanded="${item.children.some(child=>child.id===page)?"true":"false"}"><span class="nav-icon">${item.icon}</span><span>${esc(labelFor(item))}</span></button><div class="submenu ${item.children.some(child=>child.id===page)?"open":""}" id="${item.id}">${item.children.map(child=>`<button type="button" class="nav-button ${child.id===page?"active":""}" data-page="${child.id}"><span class="nav-icon">•</span><span>${esc(labelFor(child))}</span></button>`).join("")}</div>`:`<button type="button" class="nav-button ${item.id===page?"active":""}" data-page="${item.id}"><span class="nav-icon">${item.icon}</span><span>${esc(labelFor(item))}</span></button>`).join("")}`:"";
 }).join("");
 if($("#sectorSelect"))$("#sectorSelect").value=currentSector;
 if($("#sectorBrand"))$("#sectorBrand").textContent=currentSector==="otomotiv"?"Otomotiv Servis":"Teknik Servis";
 const fixedSettings=$(".sidebar-bottom [data-page='settings']");
 if(fixedSettings)fixedSettings.hidden=!menuVisible({id:"settings"});
};
function applyTheme(name,persist=false){
 const theme=supportedThemes.some(item=>item.id===name)?name:"light";
 document.documentElement.dataset.theme=theme;
 document.querySelector('meta[name="theme-color"]')?.setAttribute("content",theme==="light"?"#f4f6fb":"#0b1020");
 db.settings.theme=theme;save();
 if(persist){desktopWrite("settings",{key:"web_theme",value:theme});toast(`${supportedThemes.find(item=>item.id===theme).label} tema etkinleştirildi`,"success")}
}
function themeDialog(){
 const current=document.documentElement.dataset.theme||"light";
 openDialog("Tema Seçimi","GÖRÜNÜM",`<div class="theme-grid">${supportedThemes.map(item=>`<button type="button" class="theme-choice ${item.id===current?"active":""}" data-theme-choice="${item.id}"><div class="theme-swatch" style="--swatch-a:${item.a};--swatch-b:${item.b}"></div><strong>${item.label}</strong></button>`).join("")}</div>`,()=>true,"Kapat");
 $$("[data-theme-choice]").forEach(button=>button.onclick=()=>{applyTheme(button.dataset.themeChoice,true);$$("[data-theme-choice]").forEach(item=>item.classList.toggle("active",item===button))});
}
function interfaceEditorDialog(){
 const labels=menuLabels(),visibility=menuVisibility(),items=menu.flatMap(group=>group.items.flatMap(item=>[item,...(item.children||[])]));
 openDialog("Arayüz Düzenle","MENÜ YAPILANDIRMA",`<p class="muted">Menü adlarını değiştirin veya kullanmadığınız modülleri toggle anahtarıyla gizleyin. Gizlemek verileri silmez.</p><div class="interface-editor">${items.map(item=>`<label class="interface-row ${visibility[item.id]===false?"menu-disabled":""}"><span class="interface-icon">${item.icon||"•"}</span><div><input name="menu_${item.id}" data-menu-id="${item.id}" value="${esc(labels[item.id]||item.label)}" aria-label="${esc(item.label)} menü adı"><small>${visibility[item.id]===false?"Menü gizli":"Menü görünür"}</small></div><input class="switch menu-visibility-toggle" name="visible_${item.id}" type="checkbox" value="1" ${visibility[item.id]===false?"":"checked"} aria-label="${esc(item.label)} menüsünü göster"></label>`).join("")}</div>`,async fd=>{const updated={},visible={};items.forEach(item=>{const value=String(fd.get(`menu_${item.id}`)||"").trim();if(value&&value!==item.label)updated[item.id]=value;if(!fd.has(`visible_${item.id}`))visible[item.id]=false});const labelsJson=JSON.stringify(updated),visibilityJson=JSON.stringify(visible);localStorage.setItem("ayec_menu_labels",labelsJson);localStorage.setItem("ayec_menu_visibility",visibilityJson);desktopInternalSettings.web_menu_labels=labelsJson;desktopInternalSettings.web_menu_visibility=visibilityJson;await Promise.all([desktopWrite("internal_settings",{key:"web_menu_labels",value:labelsJson}),desktopWrite("internal_settings",{key:"web_menu_visibility",value:visibilityJson})]);if(visible[page]===false)page=firstVisiblePage();renderNav();navigate(page);toast("Menü adları ve görünürlükleri kaydedildi","success");return true},"Menüleri Kaydet");
 $$(".menu-visibility-toggle").forEach(toggle=>toggle.onchange=()=>{const row=toggle.closest(".interface-row");row.classList.toggle("menu-disabled",!toggle.checked);row.querySelector("small").textContent=toggle.checked?"Menü görünür":"Menü gizli"});
 const footer=$("#dialogFooter"),reset=document.createElement("button");reset.type="button";reset.className="danger";reset.textContent="Varsayılana Dön";reset.onclick=async()=>{if(!confirm("Tüm özel menü isimleri ve görünürlükleri sıfırlansın mı?"))return;localStorage.removeItem("ayec_menu_labels");localStorage.removeItem("ayec_menu_visibility");desktopInternalSettings.web_menu_labels="{}";desktopInternalSettings.web_menu_visibility="{}";await Promise.all([desktopWrite("internal_settings",{key:"web_menu_labels",value:"{}"}),desktopWrite("internal_settings",{key:"web_menu_visibility",value:"{}"})]);$("#appDialog").close();renderNav();navigate(page);toast("Menüler varsayılana döndü","warning")};footer.prepend(reset);
}

function rateForCode(code){const key=String(code||"TRY").toUpperCase();if(key==="TRY")return 1;return Number(salesManualRates[key]||exchangeRateState[key]?.selling||0)}
function setSalesRate(code,value){const rate=Number(value||0);if(code!=="TRY"&&rate>0)salesManualRates[code]=rate}
async function loadParityState(){
 try{
  const [rates,source]=await Promise.all([apiFetch("/api/desktop/exchange-rates"),apiFetch("/api/desktop/bootstrap")]);
  exchangeRateState=rates.rates||exchangeRateState;desktopPersonnel=source.personnel||[];desktopSettings=source.settings||desktopSettings;desktopInternalSettings=source.internal_settings||desktopInternalSettings;
  if(source.current_sector)currentSector=source.current_sector;
  const theme=desktopSettings.web_theme||db.settings.theme||"light";applyTheme(theme);renderNav();
 }catch(error){toast(`Kur ve arayüz ayarları yüklenemedi: ${error.message}`,"warning")}
}
applyTheme(db.settings.theme||"light");
$("#themeBtn").onclick=themeDialog;
$("#interfaceEditBtn").onclick=interfaceEditorDialog;

let salesDraft={template:"modern",project:"",vat:0};
let editingOfferId=0;
let editingOfferNumber="";
function productTryPrice(product,field="sell"){
 const rate=rateForCode(product.currency||"TRY");
 return rate>0?Number(product[field]||0)*rate:0;
}
function selectedSalesRate(){return salesCurrency==="TRY"?1:Number(salesManualRates[salesCurrency]||rateForCode(salesCurrency)||0)}
function selectedPriceFromTry(value){const rate=selectedSalesRate();return rate>0?Number(value||0)/rate:0}
normalizedPrice=function(product){return productTryPrice(product,"sell")};
normalizedCost=function(product){return productTryPrice(product,"buy")};
cartTotal=function(){return salesCart.reduce((sum,line)=>{const product=db.stock.find(item=>String(item.id)===String(line.productId));return sum+(product?selectedPriceFromTry(productTryPrice(product)*Number(line.qty||0)):0)},0)};
salesProducts=function(rows){return rows.filter(product=>product.qty>0).map(product=>{const selected=selectedPriceFromTry(productTryPrice(product));const converted=salesCurrency!==(product.currency||"TRY")?`<br><small class="muted">Teklif: ${money(selected,salesCurrency)}</small>`:"";return `<div class="product-tile"><div><strong>${esc(product.name)}</strong><br><small class="muted">Stok: ${product.qty} · ${money(product.sell,product.currency)}</small>${converted}</div><button class="mini" data-action="cart-add" data-id="${product.id}" aria-label="${esc(product.name)} sepete ekle">＋</button></div>`}).join("")||empty("Stokta ürün yok","Önce stok kartı ekleyin.")};
cartHtml=function(){return salesCart.length?salesCart.map((line,index)=>{const product=db.stock.find(item=>String(item.id)===String(line.productId));if(!product)return"";const total=selectedPriceFromTry(productTryPrice(product)*Number(line.qty||0));return `<div class="cart-line"><div><strong>${esc(product.name)}</strong><br><small class="muted">${money(product.sell,product.currency)} / adet</small></div><input class="control cart-qty" type="number" min="1" max="${product.qty}" value="${line.qty}" data-index="${index}"><span>${money(total,salesCurrency)}</span><button class="mini" data-action="cart-remove" data-index="${index}" aria-label="Sepetten çıkar">×</button></div>`}).join(""):empty("Sepet boş","Soldaki stok ürünlerinden ekleyin.")};
renderSales=function(){
 const rate=selectedSalesRate(),subtotal=cartTotal(),subtotalTry=subtotal*rate,rateRecord=exchangeRateState[salesCurrency];
 const rateText=salesCurrency==="TRY"?"Türk Lirası ana para birimi":rate?`1 ${salesCurrency} = ${money(rate,"TRY")} · ${esc(rateRecord?.source||"Manuel kur")} ${esc(String(rateRecord?.date||"").slice(0,10))}`:`${salesCurrency} kuru bulunamadı; kuru elle girin`;
 return `${pageHead("Sales Hub","Stoktaki ürünleri masaüstündeki kur ve para birimi mantığıyla tahsilat, proforma veya servise dönüştürün.",'<button class="secondary" data-action="view-quotes">Proformalar</button>')}<div class="grid-2 sales-grid"><section class="card"><div class="card-head"><h3>1. Müşteri ve ürün seçimi</h3><span class="badge">Canlı stok</span></div><div class="sales-currency-bar"><div class="field"><label>Teklif Para Birimi</label><select id="salesCurrency" class="control">${["TRY","USD","EUR"].map(code=>`<option value="${code}" ${salesCurrency===code?"selected":""}>${code} · ${{TRY:"Türk Lirası",USD:"ABD Doları",EUR:"Euro"}[code]}</option>`).join("")}</select></div><div class="field"><label>Satış Kuru</label><input id="salesExchangeRate" class="control" type="number" min="0.0001" step="0.0001" value="${rate||""}" ${salesCurrency==="TRY"?"disabled":""}></div><div class="rate-note">${rateText}</div></div><div class="toolbar"><select class="control" id="salesCustomer"><option value="">Müşteri seçin…</option>${db.customers.map(customer=>`<option value="${customer.id}" ${String(salesCustomer)===String(customer.id)?"selected":""}>${esc(customer.name)}</option>`).join("")}</select><input class="control search" id="salesProductSearch" placeholder="Stokta ürün ara"></div><div id="salesProducts" class="product-picker">${salesProducts(db.stock)}</div></section><aside class="card"><div class="card-head"><h3>2. Teklif sepeti</h3><span class="badge">${salesCart.length} kalem</span></div><div id="salesCart">${cartHtml()}</div><div class="proforma-options"><div class="field"><label>Teklif Şablonu</label><select id="proformaTemplate"><option value="modern" ${salesDraft.template==="modern"?"selected":""}>Modern (Premium)</option><option value="corporate" ${salesDraft.template==="corporate"?"selected":""}>Kurumsal (Premium)</option><option value="minimal" ${salesDraft.template==="minimal"?"selected":""}>Zebra (Premium)</option></select></div><div class="field"><label>Proje / İş adı</label><input id="salesProject" value="${esc(salesDraft.project)}" placeholder="İsteğe bağlı"></div><div class="field"><label>KDV (%)</label><input id="salesVat" type="number" min="0" max="100" step="1" value="${salesDraft.vat}"></div></div><div class="kpi-inline currency-total"><div><small>Ara toplam</small><strong id="cartTotal">${money(subtotal,salesCurrency)}</strong>${salesCurrency!=="TRY"?`<small>TRY karşılığı: ${money(subtotalTry,"TRY")}</small>`:""}</div></div><div class="actions sales-actions"><button class="success" data-action="pay-save">Ödeme Al ve Kaydet</button><button class="primary" data-action="create-proforma">Proforma Oluştur</button><button class="secondary" data-action="save-service">Servis Kaydet</button></div></aside></div>`;
};

runSales=async function(mode){
 try{
  const customer=db.customers.find(item=>String(item.id)===String(salesCustomer));
  if(!customer)throw Error("Önce müşteri seçin");
  const customerId=Number.isInteger(+customer.id)?+customer.id:Number.isInteger(+customer.desktopId)?+customer.desktopId:0;
  if(!customerId&&!String(customer.name||"").trim())throw Error("Müşteri sunucu veritabanına kaydedilmemiş. Müşteri listesini yenileyip tekrar deneyin.");
  if(!salesCart.length)throw Error("Sepete en az bir ürün ekleyin");
  const rate=selectedSalesRate();if(rate<=0)throw Error(`${salesCurrency} satış kuru girilmelidir`);
  const lines=salesCart.map(line=>{const product=db.stock.find(item=>String(item.id)===String(line.productId));if(!product)throw Error("Sepetteki ürün bulunamadı");if(!rateForCode(product.currency))throw Error(`${product.name} için ${product.currency} kuru bulunamadı`);if(mode==="payment"&&Number(line.qty)>Number(product.qty))throw Error(`${product.name} için yeterli stok yok`);return{product_id:+product.id,qty:Number(line.qty),product}});
  salesDraft={template:$("#proformaTemplate")?.value||"modern",project:$("#salesProject")?.value.trim()||"",vat:Number($("#salesVat")?.value||0)};
  const offerNo=editingOfferNumber||nextOfferNumber(),rates=Object.fromEntries(["TRY","USD","EUR"].map(code=>[code,rateForCode(code)]));
   const result=await apiFetch("/api/desktop/sales/commit",{method:"POST",body:JSON.stringify({mode,offer_id:mode==="proforma"&&editingOfferId?editingOfferId:undefined,customer_id:customerId,customer_name:customer.name,currency:salesCurrency,exchange_rate:rate,rates,lines:lines.map(({product_id,qty})=>({product_id,qty})),vat_rate:salesDraft.vat,template_type:salesDraft.template,project_name:salesDraft.project,offer_no:offerNo,device_type:currentSector==="otomotiv"?"Ara\u00e7":"Cihaz",payment_method:"Web"})});
  if(mode==="proforma"){
   const quote={id:String(result.offer_id),no:result.offer_no,offer_no:result.offer_no,date:today(),created_at:new Date().toISOString(),customerId:String(customer.id),customer_id:+customer.id,customer_name:customer.name,company_name:customer.company||customer.name,contact_name:customer.name,project_name:salesDraft.project,template_type:salesDraft.template,currency_code:result.currency,currency_symbol:result.currency_symbol,exchange_rate:result.exchange_rate,subtotal:result.subtotal,vat_rate:salesDraft.vat/100,vat_amount:result.vat_amount,total:result.total,subtotal_try:result.subtotal_try,vat_amount_try:result.vat_amount_try,total_try:result.total_try,status:"Teklif",items:lines.map(({product,qty})=>({productId:product.id,name:product.name,service:product.name,description:product.name,brand:product.brand||"",code:product.code||"",qty,price:selectedPriceFromTry(productTryPrice(product))}))};
   salesCart=[];editingOfferId=0;editingOfferNumber="";save();await hydrateDesktop();const savedQuote=db.quotes.find(item=>String(item.id)===String(result.offer_id))||quote;activity(`${savedQuote.no||savedQuote.offer_no} ${result.currency} proforma ${customer.name} i\u00e7in kaydedildi`,"◇");render();toast(result.updated?"Teklif g\u00fcncellendi":"Proforma se\u00e7ilen para birimiyle M\u00fc\u015fteri 360'a kaydedildi","success");setTimeout(()=>openProformaDocument(savedQuote,customer),60);return;
  }
  salesCart=[];save();await hydrateDesktop();
  if(mode==="payment")toast(`Ödeme ${money(result.total,result.currency)} olarak alındı; stok, gelir, maliyet ve cari sinyalleri birlikte işlendi`,"success");
  else toast(`${result.reference} servis kaydı Müşteri 360 geçmişine eklendi`,"success");
 }catch(error){toast(error.message||"Sales Hub işlemi tamamlanamadı","error")}
};

quoteDialog=function(){
 openDialog("Proforma Teklifler","SALES HUB",db.quotes.length?`<div class="table-wrap"><table><thead><tr><th>No</th><th>M\u00fc\u015fteri</th><th>\u015eablon</th><th>Tarih</th><th>Tutar</th><th>Durum</th><th></th></tr></thead><tbody>${db.quotes.map((quote,index)=>`<tr><td><strong>${esc(quote.no||quote.offer_no)}</strong></td><td>${esc(customerName(String(quote.customerId||quote.customer_id)))}</td><td>${esc({modern:"Modern",corporate:"Kurumsal",minimal:"Zebra"}[quote.template_type]||"Modern")}</td><td>${esc(quote.date||quote.created_at||"")}</td><td><strong>${money(quote.total||0,quote.currency_code||"TRY")}</strong>${quote.currency_code&&quote.currency_code!=="TRY"?`<br><small class="muted">${money(quote.total_try||0,"TRY")}</small>`:""}</td><td>${statusBadge(quote.status||"Teklif")}</td><td><button type="button" class="mini quote-open" data-index="${index}">A\u00e7</button><button type="button" class="mini quote-edit" data-index="${index}" ${offerIsLocked(quote)?"disabled":""}>D\u00fczenle</button></td></tr>`).join("")}</tbody></table></div>`:empty("Proforma yok","Sales Hub \u00fczerinden ilk teklifi olu\u015fturun."),()=>true,"Kapat");
 $$(".quote-open").forEach(button=>button.onclick=()=>{const offer=db.quotes[+button.dataset.index],customer=db.customers.find(item=>String(item.id)===String(offer.customerId||offer.customer_id));$("#appDialog").close();setTimeout(()=>openProformaDocument(offer,customer),60)});
 $$(".quote-edit").forEach(button=>button.onclick=()=>{const offer=db.quotes[+button.dataset.index];$("#appDialog").close();setTimeout(()=>beginOfferEdit(offer),60)});
};

function offerStatusKey(offer){return String(offer?.status||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/\u0131/g,"i").toLowerCase().trim()}
function offerIsLocked(offer){return ["accepted","processed","kabul edildi","islendi"].includes(offerStatusKey(offer))}
function beginOfferEdit(offer){
 if(!offer)return;
 if(offerIsLocked(offer)){toast("Kabul edilmi\u015f teklif de\u011fi\u015ftirilemez. Yeni teklif olu\u015fturun.","warning");return}
 const customer=db.customers.find(item=>String(item.id)===String(offer.customerId||offer.customer_id));
 if(!customer){toast("Teklif m\u00fc\u015fterisi bulunamad\u0131","error");return}
 const cart=(offer.items||[]).map(item=>{const product=db.stock.find(stock=>String(stock.id)===String(item.item_id||item.productId)||String(stock.code||"")===String(item.code||""));return product?{productId:product.id,qty:Number(item.qty||1)}:null}).filter(Boolean);
 if(!cart.length){toast("Teklif kalemleri stok kartlar\u0131yla e\u015fle\u015ftirilemedi","error");return}
 salesCustomer=customer.id;salesCart=cart;salesCurrency=["TRY","USD","EUR"].includes(offer.currency_code)?offer.currency_code:"TRY";
 if(salesCurrency!=="TRY"&&Number(offer.exchange_rate)>0)setSalesRate(salesCurrency,offer.exchange_rate);
 const vat=Number(offer.vat_rate||0);salesDraft={template:offer.template_type||"modern",project:offer.project_name||"",vat:vat<=1?vat*100:vat};
 editingOfferId=Number(offer.id||0);editingOfferNumber=String(offer.no||offer.offer_no||"");navigate("sales");toast("Teklif d\u00fczenleme i\u00e7in sepete y\u00fcklendi","success");
}

const customer360BeforeOfferEdit=customer360;
customer360=function(customer){
 customer360BeforeOfferEdit(customer);
 const offers=customer.quotes||[];
 $$(".c360-print-offer").forEach((button,index)=>button.insertAdjacentHTML("afterend",`<button type="button" class="mini c360-edit-offer" data-index="${index}" ${offerIsLocked(offers[index])?"disabled":""}>D\u00fczenle</button>`));
 $$(".c360-edit-offer").forEach(button=>button.onclick=()=>{$("#appDialog").close();setTimeout(()=>beginOfferEdit(offers[+button.dataset.index]),60)});
};

const renderSalesBeforeOfferEdit=renderSales;
renderSales=function(){const html=renderSalesBeforeOfferEdit();return editingOfferId?html.replace("Proforma Olu\u015ftur","Teklifi G\u00fcncelle"):html};

function financeTryValue(item){if(item.try_equivalent!==undefined&&item.try_equivalent!==null)return moneyNumber(item.try_equivalent);return moneyNumber(item.amount)*rateForCode(item.currency||"TRY")}
financeTable=function(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th>Müşteri</th><th>Tutar</th><th></th></tr></thead><tbody>${rows.map(item=>`<tr data-kind="finance" data-id="${item.id}"><td>${esc(item.date)}</td><td>${statusBadge(item.type)}</td><td>${esc(item.category)}</td><td>${esc(item.description)}</td><td>${esc(item.customer)}</td><td><strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong>${(item.currency||"TRY")!=="TRY"?`<br><small class="muted">${money(financeTryValue(item),"TRY")}</small>`:""}</td><td><button class="mini" data-action="edit-finance" data-id="${item.id}">Düzenle</button></td></tr>`).join("")}</tbody></table></div>`};
renderFinance=function(filter=""){
 const rows=filter?db.finance.filter(item=>item.type===filter):db.finance;
 const income=db.finance.filter(item=>item.type==="Gelir").reduce((sum,item)=>sum+financeTryValue(item),0),expense=db.finance.filter(item=>item.type==="Gider").reduce((sum,item)=>sum+financeTryValue(item),0);
 return `${pageHead(filter?`${filter} Kayıtları`:"Finans Özeti","Gelir ve gider sinyalleri stok, satış ve servis kayıtlarıyla aynı işlem zincirine bağlıdır.",'<button class="success" data-action="add-income">＋ Gelir</button><button class="danger" data-action="add-expense">＋ Gider</button><button class="secondary" data-action="export-finance">Dışa Aktar</button>')}<div class="metric-grid">${metric("Toplam Gelir",money(income,"TRY"),"Tüm dövizlerin TRY karşılığı","↑")}${metric("Toplam Gider",money(expense,"TRY"),"Stok maliyetleri dahil","↓")}${metric("Net Bakiye",money(income-expense,"TRY"),"Gelir − gider","₺")}${metric("İşlem Sayısı",db.finance.length,"Tüm hareketler","#")}</div><section class="card">${financeTable(rows)}</section>`;
};

productForm=function(product={}){const categories=sectorStockCategories();if(product.category&&!categories.includes(product.category))categories.push(product.category);return `<div class="form-grid"><div class="field"><label>Stok Kodu *</label><input name="code" required value="${esc(product.code||"")}"></div><div class="field"><label>Barkod</label><input name="barcode" value="${esc(product.barcode||"")}"></div><div class="field full"><label>Ürün Adı *</label><input name="name" required value="${esc(product.name||"")}"></div><div class="field"><label>Kategori</label><select name="category">${categories.map(value=>`<option ${product.category===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Marka</label><input name="brand" value="${esc(product.brand||"")}"></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(value=>`<option ${product.currency===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Ödeme Yöntemi</label><select name="payment_method"><option>Nakit</option><option>Banka</option><option>Kredi Kartı</option><option>Vadeli</option></select></div><div class="field"><label>Stok Adedi</label><input name="qty" type="number" min="0" step="1" value="${product.qty??0}"></div><div class="field"><label>Minimum Stok</label><input name="min" type="number" min="0" step="1" value="${product.min??0}"></div><div class="field"><label>Alış Fiyatı</label><input name="buy" type="number" min="0" step=".01" value="${product.buy??0}"></div><div class="field"><label>Satış Fiyatı</label><input name="sell" type="number" min="0" step=".01" value="${product.sell??0}"></div><div class="field full"><label>Açıklama</label><textarea name="description">${esc(product.description||"")}</textarea></div></div>`};
const _ayecProductFormWithBarcodeCamera=productForm;
productForm=function(product={}){const html=_ayecProductFormWithBarcodeCamera(product);return html.replace(/<div class="field"><label>Barkod<\/label><input name="barcode"([^>]*)><\/div>/,`<div class="field barcode-field"><label>Barkod</label><div class="barcode-control"><input name="barcode"$1><button type="button" class="barcode-camera" data-action="product-barcode-camera" title="Kameradan barkod oku" aria-label="Kameradan barkod oku">📷</button><input id="productBarcodeCamera" type="file" accept="image/*" capture="environment" hidden></div></div>`) };
saveProduct=async function(fd,existing){
 const values=Object.fromEntries(fd),currency=String(values.currency||"TRY").toUpperCase(),rate=rateForCode(currency);
 if(currency!=="TRY"&&rate<=0)throw Error(`${currency} kuru alınamadı; kur bilgisini güncelleyip tekrar deneyin`);
 const result=await apiFetch("/api/desktop/stock/save",{method:"POST",body:JSON.stringify({id:existing&&/^\d+$/.test(String(existing.id))?+existing.id:undefined,name:values.name,code:values.code,barcode:values.barcode,category:values.category,brand:values.brand,currency,stock:+values.qty||0,min_stock:+values.min||0,purchase_price:+values.buy||0,price:+values.sell||0,description:values.description,payment_method:values.payment_method,exchange_rate:rate})});
 const part=result.part,target=existing||{};Object.assign(target,{id:String(part.id),code:part.code||"",name:part.name||part.part_name||"",barcode:part.barcode||"",category:part.category||"Genel",brand:part.brand||"",currency:part.currency||"TRY",qty:Number(part.stock||0),min:Number(part.min_stock||0),buy:moneyNumber(part.purchase_price),sell:moneyNumber(part.price),description:part.description||""});if(!existing)db.stock.unshift(target);
 if(result.movement_id)db.movements.unshift({id:String(result.movement_id),date:new Date().toLocaleString("tr-TR"),product:target.name,type:result.delta>0?"Giriş":"Çıkış",qty:Math.abs(result.delta),ref:existing?"Stok düzenleme":"Ürün ekleme",user:"Yönetici"});
 if(result.finance_id)db.finance.unshift({id:String(result.finance_id),date:today(),type:"Gider",category:existing?"Stok Güncelleme":"Stok Alımı",amount:result.expense,original_amount:result.expense,try_equivalent:result.expense*result.exchange_rate,currency:result.currency,exchange_rate:result.exchange_rate,description:`${existing?"Stok Güncelleme":"Stok Alımı"}: ${Math.max(result.delta,0)} x ${target.name}`,customer:""});
 save();activity(`${target.name} stok, hareket ve finans zinciri kaydedildi`,"▥");render();toast(result.finance_id?`Ürün kaydedildi; ${money(result.expense,result.currency)} stok gideri finansa işlendi`:"Ürün ve stok hareketi kaydedildi","success");return true;
};

movementDialog=function(product){openDialog("Stok Hareketi","STOK",`<div class="form-grid"><div class="field full"><label>Ürün</label><input disabled value="${esc(product.name)}"></div><div class="field"><label>Tür</label><select name="type"><option>Giriş</option><option>Çıkış</option></select></div><div class="field"><label>Miktar</label><input name="qty" type="number" min="1" step="1" required></div><div class="field full"><label>Referans</label><input name="ref" value="MANUEL"></div></div>`,async fd=>{const values=Object.fromEntries(fd),quantity=Number(values.qty||0);if(values.type==="Çıkış"&&quantity>product.qty)throw Error("Yetersiz stok");const nextQty=Number(product.qty)+(values.type==="Giriş"?quantity:-quantity),rate=rateForCode(product.currency);const result=await apiFetch("/api/desktop/stock/save",{method:"POST",body:JSON.stringify({id:+product.id,name:product.name,code:product.code,barcode:product.barcode,category:product.category,brand:product.brand,currency:product.currency,stock:nextQty,min_stock:product.min,purchase_price:product.buy,price:product.sell,description:product.description,exchange_rate:rate})});product.qty=nextQty;db.movements.unshift({id:String(result.movement_id),date:new Date().toLocaleString("tr-TR"),product:product.name,type:values.type,qty:quantity,ref:values.ref,user:"Yönetici"});if(result.finance_id)db.finance.unshift({id:String(result.finance_id),date:today(),type:"Gider",category:"Stok Güncelleme",amount:result.expense,try_equivalent:result.expense*result.exchange_rate,currency:result.currency,exchange_rate:result.exchange_rate,description:`Stok Güncelleme: ${quantity} x ${product.name}`,customer:""});save();render();toast(result.finance_id?"Stok girişi ve maliyeti finansa işlendi":"Stok hareketi kaydedildi","success");return true})};

function allServices(){return db.customers.flatMap(customer=>(customer.services||[]).map(service=>({...service,customer:customer.name,customerId:customer.id,customerPhone:customer.phone||""})))}
function serviceComplete(service){return /tamam|teslim|iptal/i.test(String(service.status||""))}
renderServices=function(){const services=allServices();return `${pageHead("Servis Formları","Müşteri kabulünden teknisyen, parça, ödeme ve yazdırma sinyallerine kadar bağlı servis kayıtları.",'<button class="primary" data-action="new-service">＋ Yeni Servis Kaydı</button>')}<div class="metric-grid">${metric("Toplam Servis",services.length,"Tüm kayıtlar","▦")}${metric("Aktif",services.filter(item=>!serviceComplete(item)).length,"İşlem bekleyen","⚒")}${metric("Parça Bekleyen",services.filter(item=>/parça/i.test(item.status||"")).length,"Stok sinyali","!")}${metric("Teslim / Tamam",services.filter(serviceComplete).length,"Kapanan kayıt","✓")}</div><section class="card">${services.length?`<div class="table-wrap"><table><thead><tr><th>Servis No</th><th>Müşteri</th><th>Cihaz</th><th>Teknisyen</th><th>Tarih</th><th>Durum</th><th>Ödeme</th><th></th></tr></thead><tbody>${services.map(service=>`<tr data-kind="service" data-id="${esc(service.no)}" data-customer="${service.customerId}"><td><strong>${esc(service.no)}</strong></td><td>${esc(service.customer)}</td><td>${esc(service.device)}</td><td>${esc(service.technician||"Atanmadı")}</td><td>${esc(service.date)}</td><td>${statusBadge(service.status||"Bekliyor")}</td><td>${statusBadge(service.payment_status||"Beklemede")}</td><td><div class="row-actions"><button class="mini" data-action="service-detail" data-id="${esc(service.no)}">Servis Formu</button><button class="mini" data-action="technician-open" data-id="${esc(service.no)}">Teknisyen</button></div></td></tr>`).join("")}</tbody></table></div>`:empty("Servis kaydı yok","İlk servis formunu oluşturun.")}</section>`};
renderTechnician=function(){
 const services=allServices().filter(service=>!serviceComplete(service)),completed=allServices().filter(serviceComplete).length;
 return `${pageHead("Teknisyen Paneli","Atama, durum, işlem notu, kullanılan parça, işçilik ve tahsilat sinyallerini tek formda yönetin.",'<button class="secondary" data-page="services">Tüm Servisler</button>')}<div class="metric-grid">${metric("Aktif İş",services.length,"Açık iş emirleri","⚒")}${metric("Atanmamış",services.filter(item=>!item.technician).length,"Teknisyen bekliyor","♟")}${metric("Parça Bekleyen",services.filter(item=>/parça/i.test(item.status||"")).length,"Stok ihtiyacı","!")}${metric("Tamamlanan",completed,"Toplam kapanan","✓")}</div><section class="card">${services.length?services.map(service=>`<article class="technician-card" data-kind="service" data-id="${esc(service.no)}" data-customer="${service.customerId}"><span class="activity-icon">⚒</span><div><strong>${esc(service.no)} · ${esc(service.customer)}</strong><p class="muted">${esc(service.device)} — ${esc(service.note||"Arıza açıklaması yok")}</p><div class="technician-meta"><span>Teknisyen: ${esc(service.technician||"Atanmadı")}</span><span>Öncelik: ${esc(service.priority||"Normal")}</span><span>Tahmini teslim: ${esc(service.delivery||"—")}</span></div></div><div class="actions">${statusBadge(service.status||"Bekliyor")}<button class="primary mini" data-action="technician-open" data-id="${esc(service.no)}">İşle</button></div></article>`).join(""):empty("Aktif iş yok","Yeni servis kaydı oluşturabilirsiniz.")}</section>`;
};

serviceDialog=function(customerId=""){
 const automotive=currentSector==="otomotiv",technicians=desktopPersonnel.filter(person=>!person.role||/tekn|servis|usta|yönet/i.test(`${person.role} ${person.department||""}`));
 const assetFields=automotive?`<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>Şasi / VIN</label><input name="vin"></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div>`:`<div class="field"><label>Cihaz Türü *</label><input name="device_type" required placeholder="Bilgisayar, Kamera, Telefon…"></div><div class="field"><label>Marka</label><input name="brand"></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Seri No / IMEI</label><input name="serial"></div>`;
 openDialog(automotive?"Yeni Araç Servis Kaydı":"Yeni Servis Kaydı",automotive?"OTOMOTİV SERVİS KABUL FORMU":"TEKNİK SERVİS KABUL FORMU",`<div class="form-grid"><div class="field full"><label>Müşteri *</label><select name="customerId" required><option value="">Seçin…</option>${db.customers.map(customer=>`<option value="${customer.id}" ${String(customer.id)===String(customerId)?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div>${assetFields}<div class="field"><label>Aciliyet</label><select name="priority"><option>Normal</option><option>Yüksek</option><option>Acil</option><option>Düşük</option></select></div><div class="field"><label>Teknisyen</label><select name="technician"><option value="">Atanmadı</option>${technicians.map(person=>`<option>${esc(person.name)}</option>`).join("")}</select></div><div class="field full"><label>${automotive?"Şikayet / Yapılacak İş":"Arıza / Talep"} *</label><textarea name="fault" required></textarea></div><div class="field full"><label>Müşteriye Açık Not</label><textarea name="repair_details"></textarea></div><div class="field full"><label>Teknik İç Not</label><textarea name="internal_notes"></textarea></div><div class="field"><label>Aksesuarlar / Teslim Alınanlar</label><input name="accessories" placeholder="Şarj cihazı, çanta…"></div><div class="field"><label>Tahmini Teslim</label><input name="estimated_date" type="date"></div><div class="field"><label>Garanti</label><select name="warranty_status"><option>Yok</option><option>Var</option><option>Firma Garantisi</option></select></div><div class="field"><label>Durum</label><select name="status"><option>Bekliyor</option><option>Onay Bekliyor</option><option>İşlemde</option><option>Parça Bekliyor</option></select></div><label class="setting field full"><span>Kaydettikten sonra servis formunu aç</span><input class="switch" type="checkbox" name="open_form" checked></label></div>`,async fd=>{const values=Object.fromEntries(fd),customer=db.customers.find(item=>String(item.id)===String(values.customerId));if(!customer)throw Error("Müşteri seçin");const no=`SRV-${new Date().getFullYear()}${String(Date.now()).slice(-7)}`,device=automotive?`${values.plate} · ${values.brand} ${values.model}`:`${values.brand||""} ${values.model}`.trim();const result=await apiFetch("/api/desktop/table/devices",{method:"POST",body:JSON.stringify({tracking_no:no,customer_id:+customer.id,customer_name:customer.name,device_type:automotive?"Araç":values.device_type,device_brand:values.brand||"",device_model:automotive?`${values.model} (${values.plate})`:values.model,serial_no:values.serial||values.vin||values.plate||"",vehicle_plate:values.plate||"",vehicle_vin:values.vin||"",fault_description:values.fault,repair_details:values.repair_details,internal_notes:values.internal_notes,accessories:values.accessories,urgency:values.priority,priority:values.priority,technician:values.technician,status:values.status,approval_status:"Bekleme",entry_date:today(),estimated_date:values.estimated_date,warranty_status:values.warranty_status,payment_status:"Beklemede",service_source:automotive?"Web Otomotiv":"Web Teknik Servis"})});const service={id:String(result.id),date:today(),no,device,device_type:automotive?"Araç":values.device_type,brand:values.brand||"",model:values.model,serial:values.serial||values.vin||"",status:values.status,note:values.fault,repair_details:values.repair_details,internal_notes:values.internal_notes,accessories:values.accessories,delivery:values.estimated_date,technician:values.technician,priority:values.priority,warranty_status:values.warranty_status,payment_status:"Beklemede",used_parts:[]};customer.services.unshift(service);save();activity(`${no} servis kaydı ${customer.name} için oluşturuldu`,automotive?"◇":"⚒");render();toast("Servis kaydı Müşteri 360 ve servis panosuna eklendi","success");if(values.open_form)setTimeout(()=>serviceDetailDialog(customer,service),80);return true},automotive?"Araç Servisini Kaydet":"Servis Kaydet");
};

function serviceDetailDialog(customer,service){
 if(!customer||!service)return toast("Servis kaydı bulunamadı","error");
 const used=service.used_parts||[],totalParts=used.reduce((sum,item)=>sum+moneyNumber(item.price)*Number(item.quantity||1),0);
 openDialog(`${service.no} · Servis Formu`,"SERVİS KABUL / İŞLEM FORMU",`<div id="servicePrintArea" class="service-workspace"><section><div class="service-summary"><div><small>Müşteri</small><strong>${esc(customer.name)}</strong></div><div><small>Telefon</small><strong>${esc(customer.phone||"—")}</strong></div><div><small>Cihaz / Araç</small><strong>${esc(service.device||"—")}</strong></div><div><small>Seri / Plaka</small><strong>${esc(service.serial||service.plate||"—")}</strong></div><div><small>Giriş Tarihi</small><strong>${esc(service.date||"—")}</strong></div><div><small>Tahmini Teslim</small><strong>${esc(service.delivery||"—")}</strong></div><div><small>Teknisyen</small><strong>${esc(service.technician||"Atanmadı")}</strong></div><div><small>Durum</small><strong>${esc(service.status||"Bekliyor")}</strong></div></div><h3>Arıza / Talep</h3><p>${esc(service.note||"—")}</p><h3>Yapılan İşlem / Müşteri Notu</h3><p>${esc(service.repair_details||"—")}</p></section><section><div class="service-summary"><div><small>İşçilik</small><strong>${money(service.labor_cost||0,"TRY")}</strong></div><div><small>Kargo</small><strong>${money(service.cargo_fee||0,"TRY")}</strong></div><div><small>Parçalar</small><strong>${money(totalParts,"TRY")}</strong></div><div><small>Ödeme</small><strong>${esc(service.payment_status||"Beklemede")}</strong></div></div><h3>Kullanılan Parçalar</h3><div class="used-parts-list">${used.length?used.map(item=>`<div class="used-part"><span>${esc(item.part_name)} × ${item.quantity||1}</span><strong>${money(Number(item.price||0)*Number(item.quantity||1),item.currency||"TRY")}</strong></div>`).join(""):empty("Parça kullanılmadı","Teknisyen panelinden stok parçası eklenebilir.")}</div><h3>Teknik İç Not</h3><p>${esc(service.internal_notes||"—")}</p></section></div>`,()=>true,"Kapat");
 const dialog=$("#appDialog");dialog.classList.add("dialog-wide","service-print-dialog");document.body.classList.add("service-form-open");dialog.addEventListener("close",()=>{dialog.classList.remove("dialog-wide","service-print-dialog");document.body.classList.remove("service-form-open")},{once:true});
 $("#dialogFooter").innerHTML='<button type="button" class="secondary" id="servicePrintBtn">Yazdır / PDF</button><button type="button" class="primary" id="serviceTechBtn">Teknisyen Paneli</button><button type="button" class="secondary" id="serviceCloseBtn">Kapat</button>';
 $("#servicePrintBtn").onclick=()=>window.print();$("#serviceTechBtn").onclick=()=>{dialog.close();setTimeout(()=>technicianDialog(customer,service),80)};$("#serviceCloseBtn").onclick=()=>dialog.close();
}

technicianDialog=function(customer,service){
 if(!customer||!service)return toast("Servis kaydı bulunamadı","error");
 const statuses=["Bekliyor","Onay Bekliyor","İşlemde","Tamirde","Parça Bekliyor","Test Sürecinde","Tamir Edildi","Teslim Edildi","İptal / İade"],technicians=desktopPersonnel.filter(person=>!person.role||/tekn|servis|usta|yönet/i.test(`${person.role} ${person.department||""}`));
 openDialog(`${service.no} · ${service.device}`,"TEKNİSYEN İŞLEM FORMU",`<div class="form-grid"><div class="field"><label>Müşteri</label><input disabled value="${esc(customer.name)}"></div><div class="field"><label>Teknisyen</label><select name="technician"><option value="">Atanmadı</option>${technicians.map(person=>`<option ${service.technician===person.name?"selected":""}>${esc(person.name)}</option>`).join("")}</select></div><div class="field"><label>Durum</label><select name="status">${statuses.map(status=>`<option ${service.status===status?"selected":""}>${status}</option>`).join("")}</select></div><div class="field"><label>Öncelik</label><select name="priority">${["Düşük","Normal","Yüksek","Acil"].map(value=>`<option ${service.priority===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field full"><label>Teknik İç Not</label><textarea name="internal_notes">${esc(service.internal_notes||"")}</textarea></div><div class="field full"><label>Yapılan İşlem / Müşteriye Açık Not</label><textarea name="repair_details">${esc(service.repair_details||"")}</textarea></div><div class="field"><label>İşçilik Tutarı</label><input name="labor_cost" type="number" min="0" step=".01" value="${service.labor_cost||0}"></div><div class="field"><label>Kargo Tutarı</label><input name="cargo_fee" type="number" min="0" step=".01" value="${service.cargo_fee||0}"></div><div class="field"><label>Teslim Şekli</label><select name="delivery_type">${["Mağazadan Teslim","Kargo","Saha Teslimi"].map(value=>`<option ${service.delivery_type===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Tahmini Teslim</label><input name="estimated_date" type="date" value="${String(service.delivery||"").slice(0,10)}"></div><div class="field"><label>Garanti</label><select name="warranty_status">${["Yok","Var","Firma Garantisi"].map(value=>`<option ${service.warranty_status===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Garanti Bitiş</label><input name="warranty_end_date" type="date" value="${String(service.warranty_end_date||"").slice(0,10)}"></div><div class="field"><label>Kullanılan Stok</label><select name="part_id"><option value="">Parça kullanılmadı</option>${db.stock.filter(item=>item.qty>0).map(item=>`<option value="${item.id}">${esc(item.name)} (${item.qty} · ${money(item.sell,item.currency)})</option>`).join("")}</select></div><div class="field"><label>Parça Adedi</label><input name="part_quantity" type="number" min="0" step="1" value="0"></div><div class="field"><label>Ödeme Durumu</label><select name="payment_status">${["Beklemede","Ödenmedi","Kısmi Ödendi","Ödendi"].map(value=>`<option ${service.payment_status===value?"selected":""}>${value}</option>`).join("")}</select></div><label class="setting field"><span>Şimdi tahsilat al</span><input class="switch" id="collectPayment" name="collect_payment" type="checkbox"></label><div class="field payment-field" hidden><label>Tahsilat Tutarı</label><input name="payment_amount" type="number" min="0" step=".01" value="0"></div><div class="field payment-field" hidden><label>Para Birimi</label><select name="payment_currency"><option>TRY</option><option>USD</option><option>EUR</option></select></div><div class="field payment-field" hidden><label>Ödeme Yöntemi</label><select name="payment_method"><option>Nakit</option><option>Banka</option><option>Kredi Kartı</option></select></div></div>`,async fd=>{const values=Object.fromEntries(fd),currency=values.payment_currency||"TRY",result=await apiFetch("/api/desktop/technician/update",{method:"POST",body:JSON.stringify({device_id:+service.id,tracking_no:service.no,status:values.status,technician:values.technician,priority:values.priority,internal_notes:values.internal_notes,repair_details:values.repair_details,labor_cost:+values.labor_cost||0,cargo_fee:+values.cargo_fee||0,delivery_type:values.delivery_type,estimated_date:values.estimated_date,warranty_status:values.warranty_status,warranty_end_date:values.warranty_end_date,payment_status:values.payment_status,part_id:+values.part_id||0,part_quantity:+values.part_quantity||0,collect_payment:Boolean(values.collect_payment),payment_amount:+values.payment_amount||0,payment_currency:currency,payment_method:values.payment_method,exchange_rate:rateForCode(currency)})});await hydrateDesktop();activity(`${service.no} teknisyen işlemi kaydedildi`,"⚒");toast(result.finance_id?"Servis, stok, kullanılan parça, cari ve tahsilat sinyalleri işlendi":"Servis, stok ve kullanılan parça sinyalleri işlendi","success");return true},"İşlemi Kaydet");
 const collect=$("#collectPayment");collect.onchange=()=>$$('.payment-field').forEach(field=>field.hidden=!collect.checked);window.ayecBindUsedPartsEditor?.(service);
};

window.ayecUsedPartsDrafts=window.ayecUsedPartsDrafts||new Map();
window.ayecBindUsedPartsEditor=function(service){
 const body=$("#dialogBody"),partSelect=$("select[name=\"part_id\"]",body),quantityInput=$("input[name=\"part_quantity\"]",body);
 if(!body||!partSelect||!quantityInput||body.dataset.usedPartsBound==="1")return;
 body.dataset.usedPartsBound="1";
 const serviceKey=String(service?.id||service?.no||"");
 const host=document.createElement("div");
 host.className="field full used-parts-editor";
 host.innerHTML='<label>\u0130\u015flemde kullan\u0131lan par\u00e7alar</label><div class="used-parts-actions"><button type="button" class="secondary" id="usedPartAdd">+ Par\u00e7ay\u0131 kullan\u0131lanlara ekle</button><small id="usedPartHint">Par\u00e7a se\u00e7ip adet girin; eklenen par\u00e7a stoktan d\u00fc\u015f\u00fcl\u00fcr ve maliyete eklenir.</small></div><div class="used-parts-list" id="usedPartLines"></div>';
 quantityInput.closest(".field")?.after(host);
 const linesHost=$("#usedPartLines",body),addButton=$("#usedPartAdd",body);
 const lines=window.ayecUsedPartsDrafts.get(serviceKey)||[];
 const refresh=()=>{
   linesHost.innerHTML=lines.length?lines.map((line,index)=>`<div class="used-part"><span>${esc(line.name)} \u00d7 ${line.quantity}</span><span>${money(line.unit_price,line.currency)} <button type="button" class="mini" data-used-part-remove="${index}">Kald\u0131r</button></span></div>`).join(""):'<small class="muted">Hen\u00fcz par\u00e7a eklenmedi.</small>';
   $$('[data-used-part-remove]',linesHost).forEach(button=>button.onclick=()=>{lines.splice(+button.dataset.usedPartRemove,1);if(lines.length)window.ayecUsedPartsDrafts.set(serviceKey,lines);else window.ayecUsedPartsDrafts.delete(serviceKey);refresh()});
 };
 addButton.onclick=()=>{
   const part=db.stock.find(item=>String(item.id)===String(partSelect.value));
   const quantity=Math.floor(Number(quantityInput.value||0));
   if(!part||quantity<=0){toast("L\u00fctfen stok kart\u0131 ve ge\u00e7erli adet se\u00e7in.","warning");return}
   const pending=lines.filter(line=>String(line.part_id)===String(part.id)).reduce((sum,line)=>sum+line.quantity,0);
   if(quantity+pending>Number(part.qty||0)){toast("Se\u00e7ilen par\u00e7a i\u00e7in yeterli stok yok.","error");return}
   lines.push({part_id:+part.id,quantity,name:part.name,unit_price:moneyNumber(part.sell),currency:part.currency||"TRY"});
   window.ayecUsedPartsDrafts.set(serviceKey,lines);
   partSelect.value="";quantityInput.value="0";refresh();
 };
 refresh();
};

const ayecApiFetchBeforeUsedParts=apiFetch;
apiFetch=async function(path,options={}){
 const request={...options};let serviceKey="";
 if(path==="/api/desktop/technician/update"&&typeof request.body==="string"){
   try{
     const payload=JSON.parse(request.body);serviceKey=String(payload.device_id||payload.tracking_no||"");
     const lines=window.ayecUsedPartsDrafts.get(serviceKey);
     if(lines?.length){payload.used_parts=lines.map(line=>({part_id:line.part_id,quantity:line.quantity}));payload.part_id=0;payload.part_quantity=0;request.body=JSON.stringify(payload)}
   }catch{}
 }
const result=await ayecApiFetchBeforeUsedParts(path,request);
 if(path==="/api/desktop/bootstrap"&&Array.isArray(result?.stock)){
   result.stock.forEach(part=>{
     if(part.stock==null&&part.quantity!=null)part.stock=part.quantity;
     if(part.min_stock==null&&part.min!=null)part.min_stock=part.min;
   });
 }
 if(serviceKey)window.ayecUsedPartsDrafts.delete(serviceKey);
 return result;
};

const handleActionBeforeParity=handleAction;
handleAction=function(action,id,element){
 if(action==="service-detail"){const [customer,service]=findService(id);return serviceDetailDialog(customer,service)}
 if(action==="technician-open"){const [customer,service]=findService(id);return technicianDialog(customer,service)}
 return handleActionBeforeParity(action,id,element);
};

const showContextBeforeParity=showContext;
showContext=function(event,kind,id){
 if(kind!=="service")return showContextBeforeParity(event,kind,id);
 if(!db.settings.contextMenu)return;event.preventDefault();const menuHost=$("#contextMenu");menuHost.innerHTML='<button data-service-context="form">Servis Formunu Aç</button><button data-service-context="technician">Teknisyen Panelinde Aç</button><button data-service-context="print">Yazdır / PDF</button>';menuHost.style.left=`${Math.max(8,Math.min(event.clientX,innerWidth-230))}px`;menuHost.style.top=`${Math.max(8,Math.min(event.clientY,innerHeight-145))}px`;menuHost.classList.add("open");$$('[data-service-context]',menuHost).forEach(button=>button.onclick=()=>{menuHost.classList.remove("open");const [customer,service]=findService(id);if(button.dataset.serviceContext==="form")serviceDetailDialog(customer,service);if(button.dataset.serviceContext==="technician")technicianDialog(customer,service);if(button.dataset.serviceContext==="print"){serviceDetailDialog(customer,service);setTimeout(()=>window.print(),120)}});
};

const navigateBeforeParity=navigate;
navigate=function(next){navigateBeforeParity(next);const configured=menu.flatMap(group=>group.items.flatMap(item=>[item,...(item.children||[])])).find(item=>item.id===next);if(configured)$("#pageTitle").textContent=labelFor(configured);renderNav()};

const bindPageBeforeParity=bindPage;
bindPage=function(){
 bindPageBeforeParity();
 const rememberDraft=()=>{salesDraft={template:$("#proformaTemplate")?.value||salesDraft.template,project:$("#salesProject")?.value||salesDraft.project,vat:Number($("#salesVat")?.value??salesDraft.vat)}};
 const currency=$("#salesCurrency");if(currency)currency.onchange=()=>{rememberDraft();salesCurrency=currency.value;localStorage.setItem("ayec_sales_currency",salesCurrency);render()};
 const rate=$("#salesExchangeRate");if(rate)rate.onchange=()=>{setSalesRate(salesCurrency,rate.value);rememberDraft();render()};
 [$("#proformaTemplate"),$("#salesProject"),$("#salesVat")].filter(Boolean).forEach(control=>control.onchange=rememberDraft);
};

hydrateDesktop=async function(quiet=true){
 try{
  const source=await apiFetch("/api/desktop/bootstrap");
  db.customers=(source.customers||[]).map(customer=>({...customer,id:String(customer.id),phone:customer.phone||"",email:customer.email||"",type:customer.type||"Bireysel",company:customer.company_name||"",balances:customer.balances||{TRY:0,USD:0,EUR:0},services:(customer.services||[]).map(service=>({...service,id:String(service.id)})),quotes:customer.quotes||[]}));
  db.stock=(source.stock||[]).map(part=>({id:String(part.id),code:part.code||"",name:part.name||part.part_name||"",category:part.category||"Diğer",brand:part.brand||"",description:part.description||"",qty:Number(part.stock||0),min:Number(part.min_stock||0),buy:moneyNumber(part.purchase_price),sell:moneyNumber(part.price),currency:String(part.currency||part.unit||"TRY").toUpperCase(),barcode:part.barcode||""}));
  db.movements=(source.movements||[]).map(item=>({id:String(item.id),date:item.created_at||"",product:item.product||"",type:item.movement_type||"",qty:Number(item.amount||0),ref:item.description||"",user:"Masaüstü"}));
  db.finance=(source.finance||[]).map(item=>({...item,id:String(item.id),customer:item.customer_name||"",currency:String(item.currency||"TRY").toUpperCase(),original_amount:item.original_amount??item.amount}));
  db.appointments=(source.appointments||[]).map(item=>({...item,id:String(item.id),customerId:String(item.customer_id||""),title:item.title||item.description||item.fault||"Randevu",status:item.status||"Planlandı",alerted:false}));
  db.quotes=(source.offers||[]).map(item=>({...item,id:String(item.id),customerId:String(item.customer_id||item.customerId||"")}));
  db.stockLocations=(source.stock_locations||[]).map(item=>({...item,id:String(item.id),quantity:Number(item.quantity||0),part_count:Number(item.part_count||0)}));
  db.stockLocationSummary=source.stock_location_summary||{};
  scheduledAlerts=source.scheduled_alerts||[];desktopPersonnel=source.personnel||desktopPersonnel;exchangeRateState=source.exchange_rates||exchangeRateState;desktopSettings=source.settings||desktopSettings;desktopInternalSettings=source.internal_settings||desktopInternalSettings;currentSector=source.current_sector||currentSector;
  save();renderNav();render();if(!quiet)toast("Masaüstü veritabanı web arayüzüne bağlandı","success");return source;
 }catch(error){toast(`Masaüstü veritabanı yenilenemedi: ${error.message}`,"error");throw error}
};

function stockLocationWebSummary(){
 const locations=Array.isArray(db.stockLocations)?db.stockLocations:[];
 const fromServer=db.stockLocationSummary||{};
 const warehouses=Number(fromServer.warehouses??locations.filter(item=>item.location_type==="main"||item.location_type==="warehouse").length);
 const vehicles=Number(fromServer.vehicles??locations.filter(item=>item.location_type==="vehicle").length);
 const vehicleQuantity=Number(fromServer.vehicle_quantity??locations.filter(item=>item.location_type==="vehicle").reduce((total,item)=>total+Number(item.quantity||0),0));
 return {locations,warehouses,vehicles,vehicleQuantity};
}

const renderStockWithLocationParity=renderStock;
renderStock=function(){
 const summary=stockLocationWebSummary();
 const vehicleDetail=`${Math.trunc(summary.vehicleQuantity)} adet saha stogu`;
 const locationRows=summary.locations.slice(0,6).map(item=>`<tr><td><strong>${esc(item.name||"-")}</strong></td><td>${esc(item.location_type||"warehouse")}</td><td>${esc(item.vehicle_plate||"-")}</td><td>${Math.trunc(Number(item.quantity||0))}</td><td>${Math.trunc(Number(item.part_count||0))}</td></tr>`).join("");
 const locationCard=`<section class="card stock-location-card"><div class="card-head"><div><h3>Depo ve Ara\u00e7 Stoklar\u0131</h3><p class="muted">Masa\u00fcst\u00fc konum stoklar\u0131 ile anlik e\u015fle\u015fme.</p></div><span class="badge">${summary.locations.length} konum</span></div>${summary.locations.length?`<div class="table-wrap"><table><thead><tr><th>Konum</th><th>Tip</th><th>Plaka</th><th>Miktar</th><th>\u00dcr\u00fcn</th></tr></thead><tbody>${locationRows}</tbody></table></div>`:`<p class="muted">Hen\u00fcz depo veya ara\u00e7 konumu tan\u0131mlanmam\u0131\u015f.</p>`}</section>`;
 let html=renderStockWithLocationParity().replace("<div class=\"metric-grid\">",`<div class="metric-grid">${metric("Depo",summary.warehouses,"Ana depo ve depolar","#")}${metric("Ara\u00e7",summary.vehicles,vehicleDetail,"#")}`).replace("<section class=\"card\"><div class=\"toolbar\">",`${locationCard}<section class="card"><div class="toolbar">`);
 html=html.replace('>Kritik Seviye</span>',' data-stock-filter="critical">Kritik Seviye</span>').replace('>\u00dcr\u00fcn \u00c7e\u015fidi</span>',' data-stock-filter="all">\u00dcr\u00fcn \u00c7e\u015fidi</span>').replace('>Stok De\u011feri</span>',' data-stock-filter="value">Stok De\u011feri</span>');
 return html;
};

document.addEventListener("click",event=>{const card=event.target.closest("[data-stock-filter]");if(!card)return;const level=$("#stockLevel");if(card.dataset.stockFilter==="critical"&&level){level.value="Kritik Stok";level.dispatchEvent(new Event("change"));}else if(card.dataset.stockFilter==="all"&&level){level.value="T\u00fcm Seviyeler";level.dispatchEvent(new Event("change"));}else if(card.dataset.stockFilter==="value"){$("#stockSearch")?.focus();toast("Stok de\u011feri listeden incelenebilir","success")}},true);

// Keep newly created customers linked to their real desktop database id.
// Older browser-local records may still carry a temporary `cus_*` id; Sales Hub
// must use the server id returned by the customers table endpoint.
saveCustomer=async function(fd,c){
 const data=Object.fromEntries(fd),target=c||{id:uid("cus"),services:[],quotes:[]};
 Object.assign(target,{name:data.name,phone:data.phone,email:data.email,type:data.type,balances:{TRY:+data.TRY||0,USD:+data.USD||0,EUR:+data.EUR||0}});
 if(!c)db.customers.push(target);
 const persistedId=Number.isInteger(+target.id)?+target.id:Number.isInteger(+target.desktopId)?+target.desktopId:0;
 const payload={name:data.name,phone:data.phone,email:data.email,type:data.type};
 if(c&&persistedId){payload.id=persistedId;payload._action="update"}
 const result=await apiFetch("/api/desktop/table/customers",{method:"POST",body:JSON.stringify(payload)});
 if(result?.id){target.desktopId=Number(result.id);if(!Number.isInteger(+target.id))target.id=String(result.id)}
 save();activity(`${target.name} müşteri kaydı ${c?"güncellendi":"oluşturuldu"}`,"♙");toast("Müşteri kaydedildi");render();return true;
};

// Web authentication, first-run wizard and destructive-data controls.
let currentAuthUser=null;
let registrationEnabled=true;
let setupRequired=false;
let wizardState={step:0,data:{sector:"teknik_servis",currency:"TRY",smtp_server:"smtp.gmail.com",smtp_port:"587"}};

settingsGroups[3][1].splice(2,0,["data-reset","⚠","Veritabanı Temizleme (Wipe All)"]);
const settingBodyBeforeWipe=settingBody;
settingBody=function(settings){
 if(settingsSection!=="data-reset")return settingBodyBeforeWipe(settings);
 if(!currentAuthUser?.is_admin)return `<div class="danger-zone"><span class="danger-zone-icon">!</span><div><h3>Yönetici yetkisi gerekli</h3><p>Veritabanı temizleme yalnızca yönetici hesabıyla kullanılabilir.</p></div></div>`;
 return `<div class="danger-zone"><span class="danger-zone-icon">!</span><div><p class="eyebrow">TEHLİKELİ İŞLEM</p><h3>Kullanıcı verilerini sıfırla — Wipe All</h3><p>Müşteri, stok, finans, servis, randevu, teklif, proje ve hareket kayıtlarını temizler. Kullanıcı hesapları, firma/SMTP ayarları, lisans ve menü yapılandırması korunur.</p><ul><li>Silme öncesinde otomatik SQLite yedeği alınır.</li><li>Şema ve ilk kurulum bilgileri bozulmaz.</li><li>İşlem geri alınamaz; yalnız otomatik yedekten dönülebilir.</li></ul><button class="danger danger-solid" type="button" data-action="wipe-all">Wipe All işlemini başlat</button></div></div>`;
};

function openWipeAllDialog(){
 openDialog("Wipe All — Kullanıcı Verilerini Sıfırla","VERİTABANI GÜVENLİĞİ",`<div class="wipe-warning"><strong>Bu işlem operasyonel verileri kalıcı olarak siler.</strong><p>Devam etmek için yönetici parolanızı ve aşağıdaki onay metnini eksiksiz girin.</p></div><div class="form-grid"><div class="field full"><label>Yönetici Parolası</label><input name="password" type="password" autocomplete="current-password" required></div><div class="field full"><label>Onay metni</label><input name="phrase" required autocomplete="off" placeholder="TÜM VERİLERİ SİL"></div></div>`,async formData=>{if(!confirm("Son onay: Kullanıcı tarafından girilen tüm operasyonel veriler silinsin mi?"))return false;const result=await apiFetch("/api/admin/wipe-user-data",{method:"POST",body:JSON.stringify(Object.fromEntries(formData))});localStorage.removeItem(DB_KEY);db={...structuredClone(seed),customers:[],stock:[],movements:[],finance:[],appointments:[],quotes:[],activities:[]};await hydrateDesktop(true);navigate("dashboard");toast(`${result.deleted_rows} kayıt temizlendi. Otomatik yedek: ${result.backup}`,"warning",9000);return true},"Verileri Kalıcı Olarak Sil");
}
document.addEventListener("click",event=>{if(event.target.closest('[data-action="wipe-all"]'))openWipeAllDialog()});

function authShell(content,caption="Servis, stok, satış ve finans tek güvenli çalışma alanında."){
 return `<div class="auth-shell"><aside class="auth-showcase"><div class="auth-brand"><span class="auth-brand-mark">A</span><div><strong>AYEC Pro</strong><small>Web \u00c7al\u0131\u015fma Alan\u0131</small></div></div><div class="auth-showcase-copy"><span class="auth-kicker">MASA\u00dcST\u00dc G\u00dcC\u00dc \u00b7 WEB ESNEKL\u0130\u011e\u0130</span><h1>\u0130\u015fletmenizin kontrol merkezi.</h1><p>${esc(caption)}</p><div class="auth-feature-grid"><span>\u2713 \u00dc\u00e7 d\u00f6vizli cari</span><span>\u2713 Ak\u0131ll\u0131 OCR</span><span>\u2713 Servis & teknisyen</span><span>\u2713 Finans sinyalleri</span></div></div><div class="auth-server"><i></i><span>panel.ayecpro.com \u00b7 G\u00fcvenli oturum</span></div></aside><main class="auth-panel">${content}</main></div>`;
}

function showAuth(content,caption){const root=$("#authRoot");root.innerHTML=authShell(content,caption);root.hidden=false;$("#appShell").setAttribute("inert","");$("#appShell").setAttribute("aria-hidden","true");document.body.classList.add("auth-active");attachAuthChrome();attachPublicLanding()}
const authPrograms=[
 {name:"AnyDesk",description:"Uzak destek ve hızlı bağlantı",url:"/downloads/AnyDesk.exe",icon:"AD"},
 {name:"AYEC Pro Teknik Servis Program\u0131",description:"Masa\u00fcst\u00fc uygulama kurulumu",url:"/downloads/AYECPro.exe",icon:"A"},
 {name:"Smart PSS",description:"Güvenlik kamera yönetimi",url:"/downloads/SmartPSS.exe",icon:"SP"},
 {name:"Config Tools",description:"Cihaz keşif ve yapılandırma",url:"/downloads/ConfigTools.exe",icon:"CT"}
];
function attachAuthChrome(){const shell=$("#authRoot .auth-shell");if(!shell||shell.querySelector(".auth-top-nav"))return;const nav=document.createElement("div");nav.className="auth-top-nav";nav.innerHTML='<button type="button" class="auth-programs-toggle">Programlar</button><button type="button" class="auth-nav-login">Giri\u015f Yap</button><button type="button" class="auth-nav-register">Kaydol</button>';shell.append(nav);const panel=document.createElement("section");panel.className="auth-programs-panel";panel.hidden=true;panel.innerHTML='<div class="auth-programs-head"><div><span class="auth-kicker">AYEC PRO ARA\u00c7LARI</span><h2>Programlar</h2><p>Gerekli masa\u00fcst\u00fc ara\u00e7lar\u0131 tek noktadan indirin.</p></div><button type="button" class="auth-programs-close" aria-label="Kapat">\u00d7</button></div><div class="auth-program-grid">'+authPrograms.map(item=>`<a class="auth-program-card" href="${item.url}" download><span class="auth-program-icon">${item.icon}</span><span><strong>${item.name}</strong><small>${item.description}</small></span><b>\u2193</b></a>`).join("")+'</div><small class="auth-program-note">Program dosyalar\u0131 sunucunun <code>/downloads</code> klas\u00f6r\u00fcnden sunulur.</small>';shell.append(panel);nav.querySelector(".auth-programs-toggle").onclick=()=>{panel.hidden=!panel.hidden};panel.querySelector(".auth-programs-close").onclick=()=>{panel.hidden=true};nav.querySelector(".auth-nav-login").onclick=()=>$("#loginForm")?.querySelector("[name=identifier]")?.focus();nav.querySelector(".auth-nav-register").onclick=()=>{if(registrationEnabled)renderRegistration();else $("#loginForm")?.querySelector("[name=identifier]")?.focus()}}
const authChromeBeforeAbout=attachAuthChrome;
attachAuthChrome=function(){authChromeBeforeAbout();const nav=$("#authRoot .auth-top-nav"),shell=$("#authRoot .auth-shell");if(!nav||!shell||nav.querySelector(".auth-nav-about"))return;const aboutButton=document.createElement("button");aboutButton.type="button";aboutButton.className="auth-nav-about";aboutButton.textContent="Hakk\u0131nda";nav.insertBefore(aboutButton,nav.firstChild);const panel=document.createElement("section");panel.className="auth-about-panel";panel.hidden=true;panel.innerHTML='<div class="auth-about-head"><div><span class="auth-kicker">AYEC PRO HAKKINDA</span><h2>Teknik servis i\u015finizin kontrol merkezi</h2><p>Servis, stok, finans, m\u00fc\u015fteri ve saha operasyonlar\u0131n\u0131 tek g\u00fcvenli platformda y\u00f6netin.</p></div><button type="button" class="auth-about-close" aria-label="Kapat">\u00d7</button></div><div class="auth-about-grid"><article><b>Servis Y\u00f6netimi</b><span>Ar\u0131za, randevu, teknisyen ve teslim s\u00fcre\u00e7leri.</span></article><article><b>Stok ve Depo</b><span>\u00c7oklu d\u00f6viz, kritik stok, ara\u00e7 deposu ve hareket takibi.</span></article><article><b>Finans</b><span>Gelir-gider, kur d\u00f6n\u00fc\u015f\u00fcm\u00fc ve otomatik stok maliyetleri.</span></article><article><b>Web ve Masa\u00fcst\u00fc</b><span>Senkronize veri, OCR deste\u011fi ve y\u00f6netim konsolu.</span></article></div><small class="auth-about-version">AYEC Pro v2.0.4 - Teknik Servis Y\u00f6netimi</small>';shell.append(panel);aboutButton.onclick=()=>{panel.hidden=!panel.hidden};panel.querySelector(".auth-about-close").onclick=()=>{panel.hidden=true}}
function openLoginDialog(){const original=$("#loginForm");if(!original)return;let modal=$("#authLoginModal");if(!modal){modal=document.createElement("div");modal.id="authLoginModal";modal.className="auth-login-modal";modal.hidden=true;modal.innerHTML='<div class="auth-login-backdrop" data-close-login></div><section class="auth-login-dialog" role="dialog" aria-modal="true" aria-labelledby="authLoginTitle"><button type="button" class="auth-login-close" data-close-login aria-label="Kapat">\u00d7</button><div class="auth-form-head"><span class="auth-step-label">G\u00dcVENL\u0130 G\u0130R\u0130\u015e</span><h2 id="authLoginTitle">AYEC Pro hesab\u0131na giri\u015f</h2><p>Y\u00f6netim ekran\u0131n\u0131za g\u00fcvenli oturumla devam edin.</p></div><div class="auth-login-form-host"></div></section>';document.body.append(modal);modal.querySelectorAll("[data-close-login]").forEach(node=>node.onclick=()=>{modal.hidden=true})}const clone=original.cloneNode(true);clone.id="authLoginDialogForm";const host=modal.querySelector(".auth-login-form-host");host.replaceChildren(clone);clone.onsubmit=event=>{event.preventDefault();for(const field of clone.elements){if(!field.name)continue;const target=original.elements.namedItem(field.name);if(!target)continue;if(field.type==="checkbox"||field.type==="radio")target.checked=field.checked;else target.value=field.value}modal.hidden=true;original.requestSubmit()};bindAuthControls();modal.hidden=false;clone.querySelector("[name=identifier]")?.focus()}
function attachPublicLanding(){const shell=$("#authRoot .auth-shell"),loginForm=$("#loginForm");if(!shell||!loginForm||shell.classList.contains("public-landing"))return;shell.classList.add("public-landing");const showcase=shell.querySelector(".auth-showcase"),copy=showcase?.querySelector(".auth-showcase-copy");if(copy&&!copy.querySelector(".landing-hero-actions")){copy.insertAdjacentHTML("beforeend",'<div class="landing-hero-actions"><button type="button" class="landing-primary" data-landing-login>15 G\u00fcn \u00dccretsiz Deneyin</button><button type="button" class="landing-secondary" data-landing-pricing>Paketleri \u0130nceleyin</button></div><div class="landing-trust"><span>SSL ve veri g\u00fcvenli\u011fi</span><span>Web + Masa\u00fcst\u00fc + Mobil</span><span>H\u0131zl\u0131 kurulum</span></div>')}const content=document.createElement("div");content.className="landing-content";content.innerHTML='<section class="landing-proof"><div><strong>Tek Platform</strong><span>Servis, stok, finans ve m\u00fc\u015fteri</span></div><div><strong>3 Aray\u00fcz</strong><span>Web, masa\u00fcst\u00fc ve mobil</span></div><div><strong>7/24</strong><span>Operasyon ve veri eri\u015fimi</span></div><div><strong>15 G\u00fcn</strong><span>\u00dccretsiz deneme s\u00fcresi</span></div></section><section class="landing-section" id="ayecFeatures"><div class="landing-section-head"><span>AYEC PRO MOD\u00dcLLER\u0130</span><h2>Teknik servisinizi tek merkezden y\u00f6netin.</h2><p>Da\u011f\u0131n\u0131k tablolar\u0131 ve manuel i\u015flemleri bir araya getiren, masa\u00fcst\u00fc g\u00fcc\u00fcyle web eri\u015fimini birle\u015ftiren i\u015fletme platformu.</p></div><div class="landing-feature-grid"><article><i>01</i><h3>Servis Y\u00f6netimi</h3><p>Cihaz kabul, ar\u0131za, teknisyen, randevu ve teslim s\u00fcre\u00e7leri.</p></article><article><i>02</i><h3>Stok ve Depo</h3><p>\u00c7oklu d\u00f6viz, kritik stok, ara\u00e7 deposu ve hareket takibi.</p></article><article><i>03</i><h3>Finans ve Cari</h3><p>Gelir-gider, tahsilat, kur d\u00f6n\u00fc\u015f\u00fcm\u00fc ve maliyet kontrol\u00fc.</p></article><article><i>04</i><h3>M\u00fc\u015fteri Merkezi</h3><p>M\u00fc\u015fteri ge\u00e7mi\u015fi, ileti\u015fim, teklif ve servis kay\u0131tlar\u0131.</p></article><article><i>05</i><h3>Ak\u0131ll\u0131 OCR</h3><p>Belge ve g\u00f6rsel verilerini EasyOCR ve PaddleOCR ile i\u015fleyin.</p></article><article><i>06</i><h3>Y\u00f6netim Konsolu</h3><p>Firma, lisans, kullan\u0131c\u0131, yetki ve sunucu sa\u011fl\u0131\u011f\u0131 kontrol\u00fc.</p></article></div></section><section class="landing-platform"><div><span class="landing-kicker">HER YERDEN AYNI VER\u0130</span><h2>Masa\u00fcst\u00fc kadar g\u00fc\u00e7l\u00fc, web kadar eri\u015filebilir.</h2><p>AYEC Pro; ofiste, sahada ve y\u00f6netici ekran\u0131nda ayn\u0131 operasyon zincirini kullan\u0131r. Stok ve finans hareketleri senkronize ilerler.</p><ul><li>Web ve masa\u00fcst\u00fc veri senkronizasyonu</li><li>Rol ve yetki bazl\u0131 g\u00fcvenli eri\u015fim</li><li>Otomatik g\u00fcncelleme ve yedekleme</li></ul></div><div class="landing-product-visual"><header><span></span><span></span><span></span><b>AYEC Pro Core</b></header><div class="landing-visual-grid"><article><small>Aktif Servis</small><strong>128</strong><i>+12 bu hafta</i></article><article><small>Stok De\u011feri</small><strong>\u20ba248K</strong><i>3 para birimi</i></article><article><small>Randevu</small><strong>24</strong><i>Bug\u00fcn</i></article><article><small>Net Bakiye</small><strong>\u20ba96K</strong><i>Canl\u0131 finans</i></article></div><div class="landing-visual-chart"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div></div></section><section class="landing-section landing-pricing" id="ayecPricing"><div class="landing-section-head"><span>F\u0130YATLANDIRMA</span><h2>\u0130\u015fletmenize uygun lisans paketini se\u00e7in.</h2><p>T\u00fcm paketlerde AYEC Pro temel mod\u00fcleri, g\u00fcncellemeler ve web eri\u015fimi bulunur.</p></div><div class="landing-price-grid"><article><span>Esnek Ba\u015flang\u0131\u00e7</span><h3>Ayl\u0131k</h3><strong>990 \u20ba<small>/ ay</small></strong><ul><li>1 ayl\u0131k lisans</li><li>T\u00fcm temel mod\u00fcller</li><li>Web ve masa\u00fcst\u00fc eri\u015fim</li><li>G\u00fcncelleme deste\u011fi</li></ul><button type="button" data-landing-register>Hemen Ba\u015flay\u0131n</button></article><article class="featured"><em>EN POP\u00dcLER</em><span>Profesyonel</span><h3>1 Y\u0131ll\u0131k</h3><strong>9.900 \u20ba<small>/ y\u0131l</small></strong><ul><li>12 ayl\u0131k lisans</li><li>T\u00fcm AYEC Pro mod\u00fclleri</li><li>Web, masa\u00fcst\u00fc ve mobil</li><li>OCR ve senkronizasyon</li></ul><button type="button" data-landing-register>15 G\u00fcn \u00dccretsiz Deneyin</button></article><article><span>Kurumsal</span><h3>3 Y\u0131ll\u0131k</h3><strong>24.900 \u20ba<small>/ 3 y\u0131l</small></strong><ul><li>36 ayl\u0131k lisans</li><li>Y\u00f6netim konsolu</li><li>Geli\u015fmi\u015f yetkilendirme</li><li>Uzun d\u00f6nem avantaj\u0131</li></ul><button type="button" data-landing-register>Kurumsal Ba\u015flay\u0131n</button></article></div><small class="landing-price-note">Di\u011fer se\u00e7enekler: 6 ayl\u0131k 5.490 \u20ba ve 2 y\u0131ll\u0131k 17.900 \u20ba.</small></section><section class="landing-final-cta"><div><span>AYEC PRO \u0130LE TANI\u015eIN</span><h2>Servis operasyonunuzu bug\u00fcn dijitalle\u015ftirin.</h2><p>Kurulumdan stok y\u00f6netimine, finanstan saha ekibine kadar tek bir sistem.</p></div><div><button type="button" class="landing-primary" data-landing-register>\u00dccretsiz Hesap Olu\u015fturun</button><button type="button" class="landing-secondary" data-landing-login>Giri\u015f Yap\u0131n</button></div></section><footer class="landing-footer"><div><b>AYEC Pro</b><span>Teknik Servis Y\u00f6netim Platformu</span></div><div><span>Web</span><span>Masa\u00fcst\u00fc</span><span>Mobil</span><span>Y\u00f6netim Konsolu</span></div><small>\u00a9 2026 AYEC Pro. T\u00fcm haklar\u0131 sakl\u0131d\u0131r.</small></footer>';shell.append(content);shell.querySelectorAll("[data-landing-login]").forEach(button=>button.onclick=openLoginDialog);shell.querySelectorAll("[data-landing-register]").forEach(button=>button.onclick=()=>registrationEnabled?renderRegistration():renderLicenseActivation());shell.querySelector("[data-landing-pricing]")?.addEventListener("click",()=>shell.querySelector("#ayecPricing")?.scrollIntoView({behavior:"smooth"}))}
document.addEventListener("click",event=>{if(event.target.closest(".auth-nav-login")){event.preventDefault();openLoginDialog()}});
document.addEventListener("click",event=>{if(event.target.closest(".auth-brand-mark"))window.location.href="/downloads/AYECPro.exe"});

function publicAuthRoute(){
 const route=location.hash.replace(/^#\/?/,"").toLowerCase();
 return ["about","programs","login","register"].includes(route)?route:"home";
}
function renderPublicAuthRoute(){
 const route=publicAuthRoute();
 if(route==="register")return registrationEnabled?renderRegistration():renderLicenseActivation();
 renderLogin();
}
function navigatePublicAuth(route,replace=false){
 const hash=route==="home"?"#home":`#${route}`;
 if(replace)history.replaceState({publicAuth:route},"",hash);
 else history.pushState({publicAuth:route},"",hash);
 renderPublicAuthRoute();
}
window.addEventListener("hashchange",()=>{if(!currentAuthUser&&!setupRequired)renderPublicAuthRoute()});

attachAuthChrome=function(){
 const shell=$("#authRoot .auth-shell");
 if(!shell||shell.querySelector(".auth-top-nav"))return;
 const route=publicAuthRoute(),nav=document.createElement("nav");
 nav.className="auth-top-nav";
 nav.setAttribute("aria-label","Public navigation");
 nav.innerHTML=(route!=="home"?'<button type="button" data-public-route="home">Ana Sayfa</button>':"")+'<button type="button" data-public-route="programs">Programlar</button><button type="button" class="auth-nav-login" data-public-route="login">Giri\u015f Yap</button><button type="button" class="auth-nav-register" data-public-route="register">Kaydol</button>';
 shell.append(nav);
 nav.querySelectorAll("[data-public-route]").forEach(button=>{const target=button.dataset.publicRoute;button.classList.toggle("active",target===route);button.onclick=()=>navigatePublicAuth(target)});
}

function publicInfoPage(route){
 const shell=$("#authRoot .auth-shell");
 if(!shell)return;
 shell.classList.add("public-info-page",`public-info-${route}`);
 const showcase=shell.querySelector(".auth-showcase"),panel=shell.querySelector(".auth-panel");
 if(panel)panel.hidden=true;
 if(route==="about")showcase.innerHTML='<div class="public-page-brand"><button type="button" data-public-home><span>A</span><b>AYEC Pro</b></button><small>Teknik Servis Y\u00f6netim Platformu</small></div><div class="public-page-hero"><span>AYEC PRO HAKKINDA</span><h1>Servis operasyonunun tamam\u0131 tek kontrol merkezinde.</h1><p>AYEC Pro; teknik servislerin m\u00fc\u015fteri kabul\u00fcnden cihaz teslimine, stok maliyetinden finansal sonuca kadar t\u00fcm i\u015f ak\u0131\u015f\u0131n\u0131 ayn\u0131 veri zincirinde y\u00f6netmesi i\u00e7in geli\u015ftirildi.</p><div class="public-page-actions"><button type="button" data-public-route="register">15 G\u00fcn \u00dccretsiz Deneyin</button><button type="button" data-public-route="login">Hesab\u0131n\u0131za Girin</button></div></div><section class="public-detail-section"><header><span>NELER SUNUYOR?</span><h2>Masa\u00fcst\u00fc g\u00fcc\u00fc, web esnekli\u011fi ve mobil saha deneyimi.</h2></header><div class="public-detail-grid"><article><i>01</i><h3>Servis Y\u00f6netimi</h3><p>Cihaz kabul, ar\u0131za kayd\u0131, teknisyen atama, durum takibi, randevu, kargo ve teslim i\u015flemleri.</p></article><article><i>02</i><h3>Stok, Depo ve Ara\u00e7</h3><p>Ana depo ve ara\u00e7 stoklar\u0131, kritik seviye, barkod, hareket ge\u00e7mi\u015fi ve saha transferleri.</p></article><article><i>03</i><h3>\u00c7oklu D\u00f6viz</h3><p>TRY, USD ve EUR al\u0131\u015f fiyatlar\u0131 korunur; toplam stok de\u011feri g\u00fcncel kurla TRY olarak raporlan\u0131r.</p></article><article><i>04</i><h3>Finans ve Cari</h3><p>Gelir-gider, tahsilat, stok maliyeti, banka, \u00e7ek-senet ve m\u00fc\u015fteri bakiyesi tek finans zincirinde.</p></article><article><i>05</i><h3>Ak\u0131ll\u0131 OCR</h3><p>EasyOCR, PaddleOCR ve g\u00f6r\u00fcnt\u00fc i\u015fleme altyap\u0131s\u0131yla belge ve \u00fcr\u00fcn bilgilerini h\u0131zla i\u015fleyin.</p></article><article><i>06</i><h3>M\u00fc\u015fteri ve Teklif</h3><p>M\u00fc\u015fteri ge\u00e7mi\u015fi, cihazlar, teklifler, projeler ve servis kay\u0131tlar\u0131na tek profilden eri\u015fin.</p></article><article><i>07</i><h3>Senkronizasyon</h3><p>Web ve masa\u00fcst\u00fc uygulamalar ayn\u0131 para birimi, stok ve finans kurallar\u0131yla birlikte \u00e7al\u0131\u015f\u0131r.</p></article><article><i>08</i><h3>Y\u00f6netim Konsolu</h3><p>Firma, lisans, kullan\u0131c\u0131, yetki, g\u00fcncelleme ve sistem sa\u011fl\u0131\u011f\u0131n\u0131 merkezi olarak y\u00f6netin.</p></article></div></section><section class="public-workflow"><div><span>U\u00c7TAN UCA \u0130\u015e AKI\u015eI</span><h2>Kay\u0131t a\u00e7\u0131n, ekibi y\u00f6netin, sonucu \u00f6l\u00e7\u00fcn.</h2><p>AYEC Pro birbirinden kopuk ekranlar yerine, her i\u015flemin stok ve finans sonucuna kadar izlenebildi\u011fi ortak bir operasyon omurgas\u0131 sunar.</p></div><div class="public-flow-visual"><b>M\u00fc\u015fteri</b><i></i><b>Servis</b><i></i><b>Stok</b><i></i><b>Finans</b><i></i><b>Rapor</b></div></section><footer class="public-page-footer"><b>AYEC Pro</b><span>Web + Masa\u00fcst\u00fc + Mobil + Y\u00f6netim Konsolu</span><button type="button" data-public-route="home">Ana Sayfaya D\u00f6n</button></footer>';
 else showcase.innerHTML='<div class="public-page-brand"><button type="button" data-public-home><span>A</span><b>AYEC Pro Programlar</b></button><small>Kurulum ve destek merkezi</small></div><div class="public-page-hero compact"><span>PROGRAM MERKEZ\u0130</span><h1>AYEC Pro ve teknik servis ara\u00e7lar\u0131.</h1><p>Kurulum, uzaktan destek ve cihaz y\u00f6netimi i\u00e7in gerekli uygulamalar\u0131 do\u011frudan sunucunuzdan indirin.</p></div><section class="public-program-section"><div class="public-program-grid">'+authPrograms.map(item=>`<article><span class="public-program-icon">${item.icon}</span><div><h2>${item.name}</h2><p>${item.description}</p><small>${item.url}</small></div><a href="${item.url}" download>Program\u0131 \u0130ndir <b>\u2193</b></a></article>`).join("")+'</div><aside><strong>Sunucu klas\u00f6r\u00fc</strong><code>/downloads</code><p>Dosya adlar\u0131 kartlarda g\u00f6sterilen ba\u011flant\u0131larla ayn\u0131 olmal\u0131d\u0131r. Yeni program kartlar\u0131 bu merkezden eklenebilir.</p></aside></section><footer class="public-page-footer"><b>AYEC Pro Program Merkezi</b><span>G\u00fcvenli ve merkezi indirme alan\u0131</span><button type="button" data-public-route="home">Ana Sayfaya D\u00f6n</button></footer>';
 showcase.querySelector("[data-public-home]")?.addEventListener("click",()=>navigatePublicAuth("home"));
 showcase.querySelectorAll("[data-public-route]").forEach(button=>button.onclick=()=>navigatePublicAuth(button.dataset.publicRoute));
}

const ayecBrandAsset="/assets/ayec-logo.png";
const ayecProductMedia={
 workflow:"/assets/ayec-live-service_board.gif",
 access:"/assets/ayec-live-dashboard.gif",
 license:"/assets/ayec-live-finance.gif",
 dashboard:"/assets/ayec-live-dashboard.gif",
 customers:"/assets/ayec-live-customers.gif",
 stock:"/assets/ayec-live-stock.gif",
 appointments:"/assets/ayec-live-appointments.gif",
 serviceBoard:"/assets/ayec-live-service_board.gif",
 finance:"/assets/ayec-live-finance.gif"
};
const premiumAuthShell=authShell;
authShell=function(content,caption){
 return premiumAuthShell(content,caption).replace('<span class="auth-brand-mark">A</span>',`<span class="auth-brand-mark"><img src="${ayecBrandAsset}" alt="AYEC Pro"></span>`);
};
const premiumPublicInfoPage=publicInfoPage;
publicInfoPage=function(route){
 premiumPublicInfoPage(route);
 const showcase=$("#authRoot .auth-showcase"),brand=showcase?.querySelector(".public-page-brand button span");
 if(brand)brand.innerHTML=`<img src="${ayecBrandAsset}" alt="AYEC Pro">`;
 if(route!=="programs"||!showcase)return;
 const programSection=showcase.querySelector(".public-program-section");
 if(!programSection)return;
  programSection.insertAdjacentHTML("beforebegin",`<section class="public-product-gallery"><header><span>CANLI \u00dcR\u00dcN DENEY\u0130M\u0130</span><h2>Program\u0131 indirmeden \u00f6nce yak\u0131ndan tan\u0131y\u0131n.</h2><p>AYEC Pro ekranlar\u0131ndan haz\u0131rlanan tan\u0131t\u0131mlar; masa\u00fcst\u00fc uygulamadaki ger\u00e7ek men\u00fcleri g\u00f6sterir.</p></header><div class="public-gif-grid"><figure class="featured"><img src="${ayecProductMedia.dashboard}" alt="AYEC Pro genel bakis"><figcaption><b>Genel Bak\u0131\u015f</b><span>Operasyonun anl\u0131k kontrol merkezi.</span></figcaption></figure><figure><img src="${ayecProductMedia.serviceBoard}" alt="AYEC Pro servis akisi"><figcaption><b>Servis Ak\u0131\u015f\u0131</b><span>Servis kay\u0131tlar\u0131 ve i\u015f emirleri.</span></figcaption></figure><figure><img src="${ayecProductMedia.customers}" alt="AYEC Pro musteri merkezi"><figcaption><b>M\u00fc\u015fteri Merkezi</b><span>M\u00fc\u015fteri ve cari bilgileri.</span></figcaption></figure><figure><img src="${ayecProductMedia.stock}" alt="AYEC Pro stok yonetimi"><figcaption><b>Stok Y\u00f6netimi</b><span>Stok durumu ve kritik par\u00e7alar.</span></figcaption></figure><figure><img src="${ayecProductMedia.finance}" alt="AYEC Pro finans"><figcaption><b>Finans</b><span>Gelir, gider ve finans hareketleri.</span></figcaption></figure><figure><img src="${ayecProductMedia.appointments}" alt="AYEC Pro randevular"><figcaption><b>Randevular</b><span>Yakla\u015fan i\u015fler ve takvim.</span></figcaption></figure><figure><img src="${ayecProductMedia.workflow}" alt="AYEC Pro operasyon akisi"><figcaption><b>Operasyon Ak\u0131\u015f\u0131</b><span>Servis, stok ve finans zinciri.</span></figcaption></figure><figure><img src="${ayecProductMedia.access}" alt="AYEC Pro guvenli giris"><figcaption><b>G\u00fcvenli Eri\u015fim</b><span>Web ve masa\u00fcst\u00fc oturumlar\u0131.</span></figcaption></figure><figure><img src="${ayecProductMedia.license}" alt="AYEC Pro lisans merkezi"><figcaption><b>Lisans Merkezi</b><span>Firma ve kullan\u0131c\u0131 yetkileri.</span></figcaption></figure></div></section>`);
 programSection.insertAdjacentHTML("afterbegin",'<header class="public-program-head"><span>G\u00dcVENL\u0130 \u0130ND\u0130RME MERKEZ\u0130</span><h2>\u0130htiyac\u0131n\u0131z olan ara\u00e7lar tek yerde.</h2></header>');
 programSection.querySelectorAll(".public-program-grid small").forEach(node=>node.textContent="Windows \u00b7 G\u00fcvenli indirme");
 const support=programSection.querySelector("aside");
 if(support)support.innerHTML='<strong>Kurulum deste\u011fi</strong><p>Do\u011fru program\u0131 se\u00e7mek veya kurulum deste\u011fi almak i\u00e7in AYEC Pro hesab\u0131n\u0131za giri\u015f yapabilirsiniz.</p><button type="button" data-public-route="login">Hesab\u0131n\u0131za Girin</button>';
 support?.querySelector("button")?.addEventListener("click",()=>navigatePublicAuth("login"));
};

const attachPublicLandingHome=attachPublicLanding;
attachPublicLanding=function(){
 const shell=$("#authRoot .auth-shell"),loginForm=$("#loginForm");
 if(!shell||!loginForm)return;
 const route=publicAuthRoute();
 if(route==="home"){
  attachPublicLandingHome();
  shell.querySelectorAll("[data-landing-register]").forEach(button=>button.onclick=()=>navigatePublicAuth("register"));
  shell.querySelector(".landing-hero-actions .landing-primary")?.addEventListener("click",event=>{event.stopImmediatePropagation();navigatePublicAuth("register")},{capture:true});
  return;
 }
 if(route==="about"||route==="programs"){publicInfoPage(route);return}
 shell.classList.add("public-auth-page");
}
openLoginDialog=function(){navigatePublicAuth("login")};
bindAuthControls=function(){
 $$('[data-auth-view]').forEach(button=>button.onclick=()=>navigatePublicAuth(button.dataset.authView==="register"?"register":"login"));
 $$('[data-toggle-password]').forEach(button=>button.onclick=()=>{const input=button.parentElement.querySelector("input");input.type=input.type==="password"?"text":"password";button.textContent=input.type==="password"?"\u25c9":"\u25ce"});
}
function hideAuth(){const root=$("#authRoot");root.hidden=true;root.innerHTML="";$("#appShell").removeAttribute("inert");$("#appShell").removeAttribute("aria-hidden");document.body.classList.remove("auth-active")}
function authAlert(message,type="info"){return message?`<div class="auth-alert ${type}">${esc(message)}</div>`:""}
function setAuthBusy(form,busy,label="Lütfen bekleyin…"){const button=form.querySelector('button[type="submit"]');if(!button)return;button.disabled=busy;if(busy){button.dataset.label=button.textContent;button.textContent=label}else button.textContent=button.dataset.label||"Devam Et"}
function updateCurrentUser(user){currentAuthUser=user;const name=user?.full_name||user?.username||"Kullan\u0131c\u0131";$("#currentUserName").textContent=name;$("#currentUserRole").textContent=user?.role||"\u00c7evrimi\u00e7i";$("#currentUserInitial").textContent=name.split(/\s+/).slice(0,2).map(part=>part[0]).join("").toLocaleUpperCase("tr-TR");$("#interfaceEditBtn").hidden=!user?.interface_edit_access;const management=$("#managementCenterBtn");if(management)management.hidden=!canAccessControlCenter(user)}

function openProfileDialog(){
 if(!currentAuthUser)return;
 let dialog=$("#profileDialog");
 if(!dialog){
  dialog=document.createElement("dialog");
  dialog.id="profileDialog";
  dialog.innerHTML='<form method="dialog" id="profileForm"><header><div><small class="eyebrow">KULLANICI HESABI</small><h2>Profil bilgileri</h2></div><button class="icon-btn" type="button" data-profile-close aria-label="Kapat">&#215;</button></header><div class="dialog-body"><div class="form-grid"><div class="field full"><label>Firma</label><input name="company_name" disabled></div><div class="field full"><label>Kullan\u0131c\u0131 ad\u0131</label><input name="username" disabled></div><div class="field full"><label>Ad soyad</label><input name="full_name" autocomplete="name" minlength="2" maxlength="80" required></div><div class="field"><label>E-posta</label><input name="email" type="email" autocomplete="email" required></div><div class="field"><label>Telefon</label><input name="phone" type="tel" autocomplete="tel" maxlength="30"></div></div><p class="profile-help">Yaln\u0131zca kendi profil bilgileriniz g\u00fcncellenir. Firma verileri ve di\u011fer kullan\u0131c\u0131lar de\u011fi\u015ftirilmez.</p></div><footer><button class="secondary" type="button" data-profile-close>Vazge\u00e7</button><button class="primary" type="submit">Bilgilerimi Kaydet</button></footer></form>';
  document.body.append(dialog);
  dialog.querySelectorAll("[data-profile-close]").forEach(button=>button.onclick=()=>dialog.close());
  dialog.querySelector("#profileForm").onsubmit=async event=>{
   event.preventDefault();
   const form=event.currentTarget;
   const button=form.querySelector('[type="submit"]');
   button.disabled=true;
   try{
    const values=Object.fromEntries(new FormData(form));
    const result=await apiFetch("/api/auth/profile",{method:"POST",body:JSON.stringify(values)});
    updateCurrentUser(result.user);
    dialog.close();
    toast("Profil bilgileriniz g\u00fcncellendi.","success");
   }catch(error){toast(error.message,"error")}
   finally{button.disabled=false}
  };
 }
 const form=dialog.querySelector("#profileForm");
 form.company_name.value=currentAuthUser.company_name||"";
 form.username.value=currentAuthUser.username||"";
 form.full_name.value=currentAuthUser.full_name||"";
 form.email.value=currentAuthUser.email||"";
 form.phone.value=currentAuthUser.phone||"";
 dialog.showModal();
}

function renderLogin(message="",prefill="",messageType="info"){
 if(!authTenants.length)setTimeout(async()=>{try{const status=await apiFetch("/api/auth/status");authTenants=status.tenants||[];if(authTenants.length>1&&$("#loginForm"))renderLogin(message,$("#loginForm").identifier?.value||prefill,messageType)}catch{}},0);
 if(authTenants.length>1)setTimeout(()=>{const form=$("#loginForm");if(!form||form.querySelector("[name=tenant_id]"))return;const label=document.createElement("label");label.textContent="Firma";const select=document.createElement("select");select.name="tenant_id";select.innerHTML='<option value="">Otomatik se\u00e7</option>'+authTenants.map(t=>`<option value="${esc(t.id)}">${esc(t.company_name)}</option>`).join("");label.append(select);form.insertBefore(label,form.querySelector("label:nth-of-type(2)"))},0);
 showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">HOŞ GELDİNİZ</span><h2>AYEC Pro'ya giriş yapın</h2><p>Yönetim ekranınıza güvenli oturumla devam edin.</p></div>${authAlert(message,messageType)}<form class="auth-form" id="loginForm"><label>Kullanıcı adı veya e-posta<input name="identifier" value="${esc(prefill)}" autocomplete="username" required autofocus></label><label>Parola<div class="password-control"><input name="password" type="password" autocomplete="current-password" required><button type="button" data-toggle-password aria-label="Parolayı göster">◉</button></div></label><label class="remember-row"><input class="switch" name="remember" type="checkbox" value="1"><span><strong>Beni hatırla</strong><small>Bu cihazda 30 gün oturumu açık tut</small></span></label><button class="primary auth-submit" type="submit">Giriş Yap</button></form>${registrationEnabled?'<p class="auth-switch">Yeni kullanıcı mısınız? <button type="button" data-auth-view="register">Hesap oluşturun</button></p>':""}<div class="auth-help">Sorun yaşıyorsanız sistem yöneticinizle iletişime geçin.</div></div>`);
 if(setupRequired){const setupBack=document.createElement("p");setupBack.className="auth-switch";setupBack.innerHTML='<button type="button">Kuruluma geri dön</button>';setupBack.querySelector("button").onclick=()=>{wizardState.step=0;renderWizard()};$("#loginForm")?.after(setupBack)}
 const form=$("#loginForm");form.onsubmit=async event=>{event.preventDefault();setAuthBusy(form,true,"Giriş yapılıyor…");try{const values=Object.fromEntries(new FormData(form));const result=await apiFetch("/api/auth/login",{method:"POST",body:JSON.stringify({...values,remember:Boolean(values.remember)})});updateCurrentUser(result.user);hideAuth();await startApplication();toast(`Hoş geldiniz, ${result.user.full_name||result.user.username}`,"success")}catch(error){renderLogin(error.message,form.identifier.value,"error")}finally{setAuthBusy(form,false)}};
 bindAuthControls();
}

const renderLoginWithCleanTenantLabel=renderLogin;
renderLogin=function(message="",prefill="",messageType="info"){
 renderLoginWithCleanTenantLabel(message,prefill,messageType);
 setTimeout(()=>{
  const option=$("#loginForm [name=tenant_id] option[value='']");
  if(option)option.textContent="Otomatik se\u00e7";
  const form=$("#loginForm");
  if(!form)return;
  form.onsubmit=async event=>{event.preventDefault();setAuthBusy(form,true,"Giris yapiliyor...");try{const values=Object.fromEntries(new FormData(form));const result=await apiFetch("/api/auth/login",{method:"POST",body:JSON.stringify({...values,remember:Boolean(values.remember)})});updateCurrentUser(result.user);hideAuth();await startApplication();toast(`Hos geldiniz, ${result.user.full_name||result.user.username}`,"success")}catch(error){const text=String(error.message||"").toLocaleLowerCase("tr-TR");if(text.includes("deneme")||text.includes("lisans"))renderLicenseActivation(error.message,form.identifier.value);else renderLogin(error.message,form.identifier.value,"error")}finally{setAuthBusy(form,false)}};
  if(form.parentElement.querySelector(".license-activation-link"))return;
  const link=document.createElement("p");
  link.className="auth-switch license-activation-link";
  const button=document.createElement("button");
  button.type="button";
  button.textContent="Davet kodu veya lisansiniz mi var?";
  button.onclick=()=>renderLicenseActivation("",form.identifier?.value||prefill);
  link.append(button);
  form.after(link);
 },0);
};

function licenseClientHardwareId(){let value=localStorage.getItem("ayec_license_device_id");if(!value){const token=(crypto.randomUUID?crypto.randomUUID():`${Date.now()}-${Math.random()}`).replace(/[^A-Za-z0-9]/g,"").toUpperCase();value=`WEB-${token}`;localStorage.setItem("ayec_license_device_id",value)}return value}
function renderLicenseActivation(message="",prefill=""){
 if(!authTenants.length){
  setTimeout(async()=>{try{const status=await apiFetch("/api/auth/status");authTenants=status.tenants||[];renderLicenseActivation(message,prefill)}catch(error){renderLogin(error.message,prefill,"error")}},0);
 }
 const options=authTenants.map(tenant=>`<option value="${esc(tenant.id)}">${esc(tenant.company_name)}</option>`).join("");
 showAuth(`<div class="auth-form-wrap"><button class="auth-back" type="button" data-auth-view="login">\u2190 Giris ekrani</button><div class="auth-form-head"><span class="auth-step-label">LISANS VE ODEME</span><h2>Calisma alanini etkinlestirin</h2><p>Mevcut davet kodunuzu girin veya lisans talebi olusturun.</p></div>${authAlert(message,"error")}<form class="auth-form" id="licenseActivationForm"><label>Firma<select name="tenant_id" required><option value="">Firma secin</option>${options}</select></label><label>Kullanici adi veya e-posta<input name="identifier" value="${esc(prefill)}" autocomplete="username" required autofocus></label><label>Parola<div class="password-control"><input name="password" type="password" autocomplete="current-password" required><button type="button" data-toggle-password>\u25c9</button></div></label><label>Davet kodu (varsa)<input name="invitation_code" autocomplete="off"></label><button class="primary auth-submit" type="submit">Davet Kodunu Etkinlestir</button><button class="secondary auth-submit" type="button" id="requestLicenseButton">Lisans Talep Et</button></form></div>`);
 const form=$("#licenseActivationForm");
 form.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(form));if(!values.invitation_code){renderLicenseActivation("Davet kodu girin veya lisans talebi olusturun.",values.identifier);return}setAuthBusy(form,true,"Dogrulaniyor...");try{await apiFetch("/api/license/activate",{method:"POST",body:JSON.stringify(values)});renderLogin("Davet kodu dogrulandi. Giris yapabilirsiniz.",values.identifier,"success")}catch(error){renderLicenseActivation(error.message,values.identifier)}finally{setAuthBusy(form,false)}};
 $("#requestLicenseButton").onclick=()=>renderLicenseRequest(prefill,form.tenant_id.value);
 bindAuthControls();
}

async function renderLicenseRequest(prefill="",tenantId=""){
 let catalog;try{catalog=await apiFetch("/api/license/catalog")}catch(error){renderLicenseActivation(error.message,prefill);return}
 const options=authTenants.map(tenant=>`<option value="${esc(tenant.id)}" ${String(tenant.id)===String(tenantId)?"selected":""}>${esc(tenant.company_name)}</option>`).join("");
 const plans=(catalog.plans||[]).map(plan=>`<option value="${esc(plan.code)}">${esc(plan.label)} - ${moneyNumber(plan.amount_try).toLocaleString("tr-TR")} TRY</option>`).join("");
 const payment=catalog.payment||{};
 showAuth(`<div class="auth-form-wrap"><button class="auth-back" type="button" data-auth-view="login">\u2190 Giris ekrani</button><div class="auth-form-head"><span class="auth-step-label">LISANS TALEBI</span><h2>Paketinizi secin</h2><p>Odeme manuel kontrol edilir. Onay sonrasinda lisansiniz tum uygulamalarda etkinlesir.</p></div><form class="auth-form" id="licenseRequestForm"><label>Firma<select name="tenant_id"><option value="">Otomatik sec</option>${options}</select></label><label>Kullanici adi veya e-posta<input name="identifier" value="${esc(prefill)}" required autofocus></label><label>Parola<input name="password" type="password" required></label><label>Lisans paketi<select name="plan_code" required>${plans}</select></label><label>Donanim kimligi<input name="hardware_id" value="${esc(licenseClientHardwareId())}" required readonly></label><button class="primary auth-submit" type="submit">Odeme Bilgilerini Goster</button></form></div>`);
 const form=$("#licenseRequestForm");
 form.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(form));setAuthBusy(form,true,"Talep olusturuluyor...");try{const result=await apiFetch("/api/license/orders/public",{method:"POST",body:JSON.stringify(values)});const order=result.order||{};const pay=result.payment||payment;showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">ODEME BILGILERI</span><h2>Talebiniz olusturuldu</h2><p>${esc(order.plan_label||"")} paketi icin odemeyi asagidaki hesaba yapin.</p></div><div class="auth-help"><strong>${esc(pay.bank_name||"")}</strong><br>${esc(pay.account_holder||"")}<br>${esc(pay.iban||"")}<br>Referans: <strong>${esc(order.payment_reference||"")}</strong></div><button class="primary auth-submit" id="paymentReportedButton" type="button">Odemeyi Yaptim</button><button class="secondary auth-submit" id="backToLoginButton" type="button">Giris Ekranina Don</button></div>`);$("#paymentReportedButton").onclick=async()=>{try{await apiFetch(`/api/license/orders/${order.id}/payment-reported/public`,{method:"POST",body:JSON.stringify({...values,payment_note:"Musteri odeme bildirimini web uygulamasindan gonderdi."})});renderLogin("Odeme bildiriminiz alindi. Yonetici onayindan sonra giris yapabilirsiniz.",values.identifier,"success")}catch(error){renderLicenseRequest(values.identifier,values.tenant_id);toast(error.message,"error")}};$("#backToLoginButton").onclick=()=>renderLogin("",values.identifier)}catch(error){renderLicenseRequest(values.identifier,values.tenant_id);toast(error.message,"error")}finally{setAuthBusy(form,false)}};
 bindAuthControls();
}

function renderRegistration(message=""){
 showAuth(`<div class="auth-form-wrap"><button class="auth-back" type="button" data-auth-view="login">← Giriş ekranı</button><div class="auth-form-head"><span class="auth-step-label">YENİ ÜYELİK</span><h2>Çalışma alanına katılın</h2><p>Kayıttan sonra hem size hem yöneticiye bilgilendirme e-postası gönderilir.</p></div>${authAlert(message,"error")}<form class="auth-form" id="registerForm"><div class="auth-form-grid"><label>Ad Soyad<input name="full_name" autocomplete="name" required></label><label>Kullanıcı Adı<input name="username" autocomplete="username" pattern="[A-Za-z0-9_.-]{3,40}" required></label><label class="full">E-posta<input name="email" type="email" autocomplete="email" required></label><label>Parola<div class="password-control"><input name="password" type="password" minlength="8" autocomplete="new-password" required><button type="button" data-toggle-password>◉</button></div></label><label>Parola Tekrar<div class="password-control"><input name="password_confirm" type="password" minlength="8" autocomplete="new-password" required><button type="button" data-toggle-password>◉</button></div></label></div><small class="password-hint">En az 8 karakter, bir harf ve bir rakam.</small><button class="primary auth-submit" type="submit">Hesabımı Oluştur</button></form></div>`,"Kayıt tamamlanınca giriş ekranına yönlendirileceksiniz.");
 const form=$("#registerForm");form.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(form));if(values.password!==values.password_confirm)return renderRegistration("Parolalar birbiriyle eşleşmiyor.");setAuthBusy(form,true,"Hesap oluşturuluyor…");try{const result=await apiFetch("/api/auth/register",{method:"POST",body:JSON.stringify(values)});renderLogin(result.mail_message,result.user.username,result.mail_sent?"success":"warning")}catch(error){renderRegistration(error.message)}finally{setAuthBusy(form,false)}};
 bindAuthControls();
}

// New public registrations represent a company when no tenant session exists.
// Keep the field visible so the server can create the matching Firma.db file.
const _renderRegistrationWithTenant = renderRegistration;
renderRegistration = function(message=""){
 _renderRegistrationWithTenant(message);
 const form=$("#registerForm"), grid=form?.querySelector(".auth-form-grid");
 if(!grid || grid.querySelector('[name="company_name"]'))return;
 const label=document.createElement("label"); label.className="full"; label.textContent="Firma Adı";
 const input=document.createElement("input"); input.name="company_name"; input.autocomplete="organization"; input.required=true; input.value=db.settings.company||"";
 label.append(input); grid.prepend(label);
 const sectorLabel=document.createElement("label");sectorLabel.className="full";sectorLabel.textContent="Sekt\u00f6r";
 const sectorSelect=document.createElement("select");sectorSelect.name="sector";sectorSelect.required=true;
 const emptyOption=document.createElement("option");emptyOption.value="";emptyOption.textContent="Sekt\u00f6r se\u00e7in";emptyOption.selected=true;emptyOption.disabled=true;
 const technicalOption=document.createElement("option");technicalOption.value="teknik_servis";technicalOption.textContent="Teknik Servis";
 const automotiveOption=document.createElement("option");automotiveOption.value="otomotiv";automotiveOption.textContent="Otomotiv Servis";
 sectorSelect.append(emptyOption,technicalOption,automotiveOption);sectorLabel.append(sectorSelect);label.after(sectorLabel);
};

const renderRegistrationWithNavigation=renderRegistration;
renderRegistration=function(message=""){
 renderRegistrationWithNavigation(message);
 const form=$("#registerForm");
 if(!form)return;
 form.onsubmit=async event=>{
  event.preventDefault();
  const values=Object.fromEntries(new FormData(form));
  if(values.password!==values.password_confirm)return renderRegistration("Parolalar birbiriyle eslesmiyor.");
  setAuthBusy(form,true,"Hesap olusturuluyor...");
  try{
   const result=await apiFetch("/api/auth/register",{method:"POST",body:JSON.stringify(values)});
   rememberAuthTenant(result.tenant);
   history.replaceState({publicAuth:"login"},"","#login");
   renderLogin(result.mail_message,result.user.username,result.mail_sent?"success":"warning");
  }catch(error){renderRegistration(error.message)}
  finally{setAuthBusy(form,false)}
 };
};

function wizardStepContent(){
 const data=wizardState.data,step=wizardState.step;
 if(step===0)return `<div class="wizard-welcome"><div class="wizard-orbit"><span>A</span></div><h2>AYEC Pro'yu işletmenize hazırlayalım</h2><p>Bu sihirbaz firma, sektör, yönetici ve e-posta ayarlarını güvenli biçimde oluşturur.</p><div class="sector-choice"><label><input type="radio" name="sector" value="teknik_servis" ${data.sector!=="otomotiv"?"checked":""}><span><b>Teknik Servis</b><small>Bilgisayar, akıllı ev ve güvenlik sistemleri</small></span></label><label><input type="radio" name="sector" value="otomotiv" ${data.sector==="otomotiv"?"checked":""}><span><b>Otomotiv Servis</b><small>Araç, bakım, parça ve servis süreçleri</small></span></label></div></div>`;
 if(step===1)return `<div class="auth-form-grid"><label class="full">Firma Adı<input name="company_name" value="${esc(data.company_name||"")}" required></label><label>Firma E-postası<input name="company_email" type="email" value="${esc(data.company_email||"")}" required></label><label>Telefon<input name="phone" type="tel" value="${esc(data.phone||"")}" required></label><label class="full">Adres<textarea name="company_address" rows="3">${esc(data.company_address||"")}</textarea></label><label>Varsayılan Para Birimi<select name="currency"><option ${data.currency==="TRY"?"selected":""}>TRY</option><option ${data.currency==="USD"?"selected":""}>USD</option><option ${data.currency==="EUR"?"selected":""}>EUR</option></select></label></div>`;
 if(step===2)return `<div class="auth-form-grid"><label class="full">Yönetici Ad Soyad<input name="full_name" value="${esc(data.full_name||"")}" autocomplete="name" required></label><label>Kullanıcı Adı<input name="username" value="${esc(data.username||"")}" pattern="[A-Za-z0-9_.-]{3,40}" autocomplete="username" required></label><label>E-posta<input name="email" type="email" value="${esc(data.email||data.company_email||"")}" autocomplete="email" required></label><label>Parola<div class="password-control"><input name="password" type="password" minlength="8" autocomplete="new-password" required><button type="button" data-toggle-password>◉</button></div></label><label>Parola Tekrar<div class="password-control"><input name="password_confirm" type="password" minlength="8" autocomplete="new-password" required><button type="button" data-toggle-password>◉</button></div></label></div><small class="password-hint">En az 8 karakter, bir harf ve bir rakam kullanın.</small>`;
 return `<div class="smtp-intro"><span>✉</span><div><h3>Kayıt e-postalarını etkinleştirin</h3><p>Üye ve yönetici bildirimleri bu SMTP hesabından gönderilir.</p></div></div><div class="auth-form-grid"><label>SMTP Sunucu<input name="smtp_server" value="${esc(data.smtp_server||"smtp.gmail.com")}" required></label><label>Port<input name="smtp_port" type="number" value="${esc(data.smtp_port||"587")}" required></label><label class="full">Gönderen E-posta<input name="smtp_email" type="email" value="${esc(data.smtp_email||data.company_email||data.email||"")}" required></label><label>Uygulama Parolası<div class="password-control"><input name="smtp_password" type="password" autocomplete="new-password" required><button type="button" data-toggle-password>◉</button></div></label><label>Yönetici Bildirim E-postası<input name="admin_email" type="email" value="${esc(data.admin_email||data.email||"")}" required></label></div><p class="auth-note">Gmail kullanıyorsanız normal parola yerine uygulama parolası girin. Kurulum tamamlanınca iki ayrı bilgilendirme e-postası gönderilir.</p>`;
}

function collectWizardStep(form){const values=Object.fromEntries(new FormData(form));Object.assign(wizardState.data,values);if(wizardState.step===2&&values.password!==values.password_confirm)throw Error("Parolalar birbiriyle eşleşmiyor.")}
function renderWizard(message=""){
 const titles=["Hoş Geldiniz","Firma Bilgileri","Yönetici Hesabı","E-posta ve Tamamlama"],step=wizardState.step;
 showAuth(`<div class="wizard-wrap"><div class="wizard-top"><div><span class="auth-step-label">İLK KURULUM SİHİRBAZI</span><h2>${titles[step]}</h2></div><span class="wizard-count">${step+1} / 4</span></div><div class="wizard-progress">${titles.map((title,index)=>`<span class="${index<=step?"active":""}"><i>${index<step?"✓":index+1}</i><small>${title}</small></span>`).join("")}</div>${authAlert(message,"error")}<form class="auth-form wizard-form" id="wizardForm">${wizardStepContent()}<div class="wizard-actions">${step?'<button class="secondary" type="button" data-wizard-back>Geri</button>':"<span></span>"}<button class="primary" type="submit">${step===3?"Kurulumu Tamamla":"Devam Et"}</button></div></form></div>`,"Dört kısa adımda web çalışma alanınız hazır olacak.");
 if(step===3){const smtpUserField=document.createElement("label");smtpUserField.innerHTML='SMTP Kullanıcı Adı<input name="smtp_username" type="text" value="'+esc(wizardState.data.smtp_username||wizardState.data.smtp_email||"")+'" autocomplete="username">';$("#wizardForm .auth-form-grid")?.append(smtpUserField)}
 const wizardLoginLink=document.createElement("p");wizardLoginLink.className="auth-switch wizard-login-link";wizardLoginLink.innerHTML='Hesabınız var mı? <button type="button">Giriş ekranına dön</button>';wizardLoginLink.querySelector("button").onclick=()=>renderLogin();$("#wizardForm")?.after(wizardLoginLink);
 const form=$("#wizardForm");form.onsubmit=async event=>{event.preventDefault();try{collectWizardStep(form);if(step<3){wizardState.step++;return renderWizard()}setAuthBusy(form,true,"Kurulum tamamlanıyor…");const result=await apiFetch("/api/auth/setup",{method:"POST",body:JSON.stringify(wizardState.data)});registrationEnabled=true;setupRequired=false;renderLogin(result.mail_message,result.user.username,result.mail_sent?"success":"warning")}catch(error){renderWizard(error.message)}finally{setAuthBusy(form,false)}};
 $("[data-wizard-back]")?.addEventListener("click",()=>{try{collectWizardStep(form)}catch{}wizardState.step=Math.max(0,wizardState.step-1);renderWizard()});
 bindAuthControls();
}

function bindAuthControls(){$$("[data-auth-view]").forEach(button=>button.onclick=()=>button.dataset.authView==="register"?renderRegistration():renderLogin());$$('[data-toggle-password]').forEach(button=>button.onclick=()=>{const input=button.parentElement.querySelector("input");input.type=input.type==="password"?"text":"password";button.textContent=input.type==="password"?"◉":"◎"})}

function renderPasswordReset(token,message="",messageType=""){
  showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">GUVENLI HESAP KURTARMA</span><h2>Yeni parolanizi belirleyin</h2><p>Bu baglanti tek kullanimliktir ve 30 dakika gecerlidir.</p></div>${message?`<div class="auth-message ${messageType}">${esc(message)}</div>`:""}<form id="passwordResetForm"><label>Yeni parola<input name="password" type="password" minlength="10" autocomplete="new-password" required></label><label>Yeni parola tekrar<input name="password_confirm" type="password" minlength="10" autocomplete="new-password" required></label><button class="primary auth-submit" type="submit">Parolayi Guvenle Degistir</button></form></div>`,"AYEC Pro hesap kurtarma");
  const form=$("#passwordResetForm");form.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(form));if(values.password!==values.password_confirm)return renderPasswordReset(token,"Parolalar birbiriyle eslesmiyor.","error");setAuthBusy(form,true,"Parola degistiriliyor...");try{await apiFetch("/api/auth/reset-password",{method:"POST",body:JSON.stringify({token,password:values.password})});history.replaceState({},"",location.pathname);renderLogin("Parolaniz degistirildi. Yeni parolanizla giris yapabilirsiniz.","","success")}catch(error){renderPasswordReset(token,error.message,"error")}finally{setAuthBusy(form,false)}};
}

async function initializeAuth(){const resetToken=new URLSearchParams(window.location.search).get("reset");if(resetToken)return renderPasswordReset(resetToken);try{const status=await apiFetch("/api/auth/status");registrationEnabled=status.registration_enabled;setupRequired=Boolean(status.setup_required);if(status.setup_required)return renderWizard();if(status.authenticated){updateCurrentUser(status.user);hideAuth();return startApplication()}renderLogin()}catch(error){showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">BAĞLANTI HATASI</span><h2>Sunucuya ulaşılamadı</h2><p>${esc(error.message)}</p></div><button class="primary auth-submit" id="authRetry" type="button">Yeniden Dene</button></div>`);$("#authRetry").onclick=initializeAuth}}
window.handleUnauthorized=()=>{applicationStarted=false;currentAuthUser=null;renderLogin("Oturum süreniz sona erdi. Lütfen yeniden giriş yapın.","","warning")};
$("#profileBtn").onclick=openProfileDialog;
$("#logoutBtn").onclick=async()=>{try{await apiFetch("/api/auth/logout",{method:"POST",body:"{}"})}finally{applicationStarted=false;currentAuthUser=null;renderLogin("Oturum güvenli biçimde kapatıldı.","","success")}};
// Payment parity: the desktop balance is negative while a customer owes us.
// The dialog is pre-filled with the open debt and the server validates the
// same limit atomically, so a browser cannot over-collect.
paymentDialog=function(customer){
  if(!customer)return toast("Müşteri seçilmelidir","error");
  const debtFor=currency=>Math.max(0,-Number(customer.balances?.[currency]||0));
  const preferred=["TRY","USD","EUR"].find(currency=>debtFor(currency)>0)||"TRY";
  const initialDebt=debtFor(preferred);
  openDialog("Tahsilat Al","CARİ HAREKET",`<div class="form-grid"><div class="field full"><label>Müşteri</label><input disabled value="${esc(customer.name)}"></div><div class="field"><label>Tutar * <small class="muted" id="paymentDebtCaption">Açık borç: ${money(initialDebt,preferred)}</small></label><input name="amount" type="number" min=".01" max="${initialDebt||0}" step=".01" value="${initialDebt||""}" required></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(currency=>`<option ${currency===preferred?"selected":""}>${currency}</option>`).join("")}</select></div><div class="field"><label>Ödeme Yöntemi</label><select name="payment_method"><option>Nakit</option><option>Banka</option><option>Kredi Kartı</option><option>Web</option></select></div><div class="field"><label>Referans / Takip No</label><input name="reference" placeholder="Servis veya dekont no"></div><div class="field full"><label>Açıklama</label><textarea name="description">Müşteri tahsilatı</textarea></div><div class="field full"><div class="payment-debt-summary" id="paymentDebtSummary">İşlem sonrası borç: ${money(Math.max(0,initialDebt-initialDebt),preferred)}</div></div></div>`,async formData=>{
    const values=Object.fromEntries(formData),currency=values.currency||"TRY",amount=Number(values.amount||0),debt=debtFor(currency);
    if(debt<=0)throw Error(`${currency} para biriminde açık borç bulunmuyor`);
    if(amount<=0)throw Error("Tahsilat tutarı sıfırdan büyük olmalıdır");
    if(amount>debt+0.0001)throw Error(`Tahsilat açık borcu aşamaz (en fazla ${money(debt,currency)})`);
    const result=await apiFetch("/api/desktop/customer/payment",{method:"POST",body:JSON.stringify({customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,amount,currency,description:values.description,payment_method:values.payment_method,reference:values.reference,exchange_rate:rateForCode(currency)})});
    await hydrateDesktop(true);
    activity(`${customer.name} müşterisinden ${money(result.amount,result.currency)} tahsil edildi`,"₺");
    toast(`Tahsilat kaydedildi · kalan borç ${money(result.open_debt_after,result.currency)}`);
    return true;
  },"Tahsilatı Kaydet");
  const body=$("#dialogBody"),currencyInput=$("select[name=currency]",body),amountInput=$("input[name=amount]",body),caption=$("#paymentDebtCaption"),summary=$("#paymentDebtSummary");
  const sync=()=>{const currency=currencyInput?.value||"TRY",debt=debtFor(currency);if(amountInput){amountInput.max=debt||0;amountInput.value=debt?String(debt):""}if(caption)caption.textContent=`Açık borç: ${money(debt,currency)}`;if(summary)summary.textContent=`İşlem sonrası borç: ${money(Math.max(0,debt-Number(amountInput?.value||0)),currency)}`};
  currencyInput?.addEventListener("change",sync);amountInput?.addEventListener("input",()=>{const currency=currencyInput?.value||"TRY",debt=debtFor(currency),amount=Math.min(Math.max(0,Number(amountInput.value||0)),debt);if(summary)summary.textContent=`İşlem sonrası borç: ${money(Math.max(0,debt-amount),currency)}`});sync();
};

// Hide collection actions for completed/delivered services and expose one
// action for the active service that owns the customer's remaining debt.
const customer360WithPaymentGuard=customer360;
customer360=function(customer){
  customer360WithPaymentGuard(customer);
  const services=customer?.services||[],hasDebt=["TRY","USD","EUR"].some(currency=>Number(customer?.balances?.[currency]||0)<0),active=services.filter(service=>!serviceComplete(service));
  const target=active.find(service=>moneyNumber(service.amount??service.price??0)>0)||(hasDebt?active[0]:null);
  $$(".c360-pay").forEach((button,index)=>{const service=services[index],visible=Boolean(service&&target&&service===target&&!serviceComplete(service)&&hasDebt);if(!visible)button.replaceWith(document.createTextNode("—"))});
};

// Finance edit keeps the operational audit fields visible (currency/TRY
// equivalent, exchange rate, payment method, reference and timestamp).
financeDialog=function(type,item){
  const detail=item?`<details class="finance-detail" open><summary>İşlem ayrıntıları</summary><div class="finance-detail-grid"><span>Tür / Kategori<strong>${esc(item.type||type||"—")} · ${esc(item.category||"—")}</strong></span><span>Orijinal tutar<strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong></span><span>TRY karşılığı<strong>${money(item.try_equivalent??financeTryValue(item),"TRY")}</strong></span><span>Kur<strong>${esc(String(item.exchange_rate??1))}</strong></span><span>Ödeme yöntemi<strong>${esc(item.payment_method||"—")}</strong></span><span>Referans / Takip<strong>${esc(item.ref_no||item.tracking_no||"—")}</strong></span><span>Müşteri<strong>${esc(item.customer||item.customer_name||"—")}</strong></span><span>Kayıt zamanı<strong>${esc(item.created_at||item.date||"—")}</strong></span></div></details>`:"";
  openDialog(item?"Finans Kaydını Düzenle":`${type} Ekle`,"FİNANS",`${detail}<div class="form-grid"><div class="field"><label>Tarih</label><input name="date" type="date" value="${item?.date||today()}"></div><div class="field"><label>Kategori *</label><input name="category" required value="${esc(item?.category||"")}"></div><div class="field"><label>Tutar *</label><input name="amount" type="number" min=".01" step=".01" required value="${item?.amount||""}"></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(currency=>`<option ${item?.currency===currency?"selected":""}>${currency}</option>`).join("")}</select></div><div class="field"><label>Ödeme Yöntemi</label><select name="payment_method">${["Nakit","Banka","Kredi Kartı","Web","Mahsup"].map(method=>`<option ${item?.payment_method===method?"selected":""}>${method}</option>`).join("")}</select></div><div class="field"><label>Referans / Takip No</label><input name="tracking_no" value="${esc(item?.tracking_no||item?.ref_no||"")}"></div><div class="field full"><label>Açıklama *</label><textarea name="description" required>${esc(item?.description||"")}</textarea></div><div class="field full"><label>Müşteri (isteğe bağlı)</label><select name="customer"><option></option>${db.customers.map(customer=>`<option ${item?.customer===customer.name?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div></div>`,async formData=>{const values=Object.fromEntries(formData),target=item||{id:uid("fin"),type};Object.assign(target,{date:values.date,category:values.category,amount:Number(values.amount||0),currency:values.currency,description:values.description,payment_method:values.payment_method,tracking_no:values.tracking_no,ref_no:values.tracking_no,customer:values.customer});if(!item)db.finance.unshift(target);const customer=db.customers.find(entry=>entry.name===values.customer),rate=item?.exchange_rate||rateForCode(values.currency),payload={type:target.type,category:values.category,amount:Number(values.amount||0),original_amount:Number(values.amount||0),try_equivalent:Number(values.amount||0)*rate,currency:values.currency,exchange_rate:rate,description:values.description,date:values.date,customer_id:customer&&Number.isInteger(+customer.id)?+customer.id:null,customer_name:values.customer,payment_method:values.payment_method,tracking_no:values.tracking_no,ref_no:values.tracking_no};if(item&&Number.isInteger(+item.id)){payload.id=+item.id;payload._action="update"}await apiFetch("/api/desktop/table/accounting",{method:"POST",body:JSON.stringify(payload)});save();activity(`${target.type} kaydı: ${money(target.amount,target.currency)}`,target.type==="Gelir"?"↑":"↓");toast(`${target.type} kaydedildi`);render();return true},item?"Güncelle":"Kaydet");
};

// The overview's default list is an active-work list. Completed/delivered and
// cancelled services remain reachable through their dedicated status tiles.
const dashboardFilterMatchWithClosed=dashboardFilterMatch;
dashboardFilterMatch=function(service,filter){if(filter==="all"){const key=serviceStatusKey(service);return key!=="teslim"&&key!=="iptal"}return dashboardFilterMatchWithClosed(service,filter)};

financeTable=function(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th>Müşteri</th><th>Orijinal</th><th>TRY</th><th>Kur</th><th>Ödeme</th><th>Referans</th><th></th></tr></thead><tbody>${rows.map(item=>`<tr data-kind="finance" data-id="${item.id}"><td>${esc(item.date||item.created_at||"—")}</td><td>${statusBadge(item.type||"—")}</td><td>${esc(item.category||"—")}</td><td>${esc(item.description||"—")}</td><td>${esc(item.customer||item.customer_name||"—")}</td><td><strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong></td><td>${money(item.try_equivalent??financeTryValue(item),"TRY")}</td><td>${esc(String(item.exchange_rate??1))}</td><td>${esc(item.payment_method||"—")}</td><td>${esc(item.ref_no||item.tracking_no||"—")}</td><td><button class="mini" data-action="edit-finance" data-id="${item.id}">Detay / Düzenle</button></td></tr>`).join("")}</tbody></table></div>`};

// Keep finance records canonical when the currency changes during editing.
financeDialog=function(type,item){
  const startCurrency=String(item?.currency||"TRY").toUpperCase();
  const startRate=startCurrency==="TRY"?1:Number(item?.exchange_rate||rateForCode(startCurrency)||0);
  const detail=item?`<details class="finance-detail" open><summary>\u0130\u015flem ayr\u0131nt\u0131lar\u0131</summary><div class="finance-detail-grid"><span>T\u00fcr / Kategori<strong>${esc(item.type||type||"\u2014")} \u00b7 ${esc(item.category||"\u2014")}</strong></span><span>Orijinal tutar<strong>${money(item.original_amount??item.amount,startCurrency)}</strong></span><span>TRY kar\u015f\u0131l\u0131\u011f\u0131<strong>${money(item.try_equivalent??financeTryValue(item),"TRY")}</strong></span><span>Kur<strong>${esc(String(item.exchange_rate??1))}</strong></span><span>\u00d6deme y\u00f6ntemi<strong>${esc(item.payment_method||"\u2014")}</strong></span><span>Referans / Takip<strong>${esc(item.ref_no||item.tracking_no||"\u2014")}</strong></span><span>M\u00fc\u015fteri<strong>${esc(item.customer||item.customer_name||"\u2014")}</strong></span><span>Kay\u0131t zaman\u0131<strong>${esc(item.created_at||item.date||"\u2014")}</strong></span></div></details>`:"";
  const form=`${detail}<div class="form-grid"><div class="field"><label>Tarih</label><input name="date" type="date" value="${item?.date||today()}"></div><div class="field"><label>Kategori *</label><input name="category" required value="${esc(item?.category||"")}"></div><div class="field"><label>Tutar *</label><input name="amount" type="number" min=".01" step=".01" required value="${item?.original_amount??item?.amount??""}"></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(currency=>`<option ${startCurrency===currency?"selected":""}>${currency}</option>`).join("")}</select></div><div class="field"><label>D\u00f6viz Kuru (TRY)</label><input name="exchange_rate" type="number" min=".0001" step=".0001" value="${startRate||""}" ${startCurrency==="TRY"?"disabled":""}></div><div class="field"><label>\u00d6deme Y\u00f6ntemi</label><select name="payment_method">${["Nakit","Banka","Kredi Kart\u0131","Web","Mahsup"].map(method=>`<option ${item?.payment_method===method?"selected":""}>${method}</option>`).join("")}</select></div><div class="field"><label>Referans / Takip No</label><input name="tracking_no" value="${esc(item?.tracking_no||item?.ref_no||"")}"></div><div class="field full"><label>A\u00e7\u0131klama *</label><textarea name="description" required>${esc(item?.description||"")}</textarea></div><div class="field full"><label>M\u00fc\u015fteri (iste\u011fe ba\u011fl\u0131)</label><select name="customer"><option></option>${db.customers.map(customer=>`<option ${item?.customer===customer.name?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div></div>`;
  openDialog(item?"Finans Kayd\u0131n\u0131 D\u00fczenle":`${type} Ekle`,"F\u0130NANS",form,async formData=>{
    const values=Object.fromEntries(formData);
    const currency=String(values.currency||"TRY").toUpperCase();
    const rate=currency==="TRY"?1:Number(values.exchange_rate||0);
    const amount=Number(values.amount||0);
    if(amount<=0)throw Error("Tutar s\u0131f\u0131rdan b\u00fcy\u00fck olmal\u0131d\u0131r");
    if(rate<=0)throw Error(`${currency} d\u00f6viz kuru girilmelidir`);
    const customer=db.customers.find(entry=>entry.name===values.customer);
    const payload={type:item?.type||type,category:values.category,amount,original_amount:amount,try_equivalent:amount*rate,currency,exchange_rate:rate,description:values.description,date:values.date,customer_id:customer&&Number.isInteger(+customer.id)?+customer.id:null,customer_name:values.customer,payment_method:values.payment_method,tracking_no:values.tracking_no,ref_no:values.tracking_no};
    if(item&&Number.isInteger(+item.id)){payload.id=+item.id;payload._action="update"}
    const result=await apiFetch("/api/desktop/table/accounting",{method:"POST",body:JSON.stringify(payload)});
    const target=item||{id:String(result.id),type:payload.type};
    Object.assign(target,{date:values.date,category:values.category,amount,original_amount:amount,try_equivalent:amount*rate,currency,exchange_rate:rate,description:values.description,payment_method:values.payment_method,tracking_no:values.tracking_no,ref_no:values.tracking_no,customer:values.customer,customer_name:values.customer});
    if(!item)db.finance.unshift(target);
    save();
    activity(`${target.type} kayd\u0131: ${money(amount,currency)}`,target.type==="Gelir"?"\u2191":"\u2193");
    toast(`${target.type} kaydedildi`);
    render();
    return true;
  },item?"G\u00fcncelle":"Kaydet");
  const body=$("#dialogBody");
  const currencyInput=$('select[name="currency"]',body);
  const rateInput=$('input[name="exchange_rate"]',body);
  const syncRate=()=>{
    const currency=String(currencyInput?.value||"TRY").toUpperCase();
    const rate=currency==="TRY"?1:rateForCode(currency);
    if(rateInput){rateInput.disabled=currency==="TRY";rateInput.value=rate>0?String(rate):""}
  };
  currencyInput?.addEventListener("change",syncRate);
};

financeTable=function(rows){
  return `<div class="table-wrap finance-table"><table><thead><tr><th>Tarih</th><th>T\u00fcr</th><th>Kategori</th><th>A\u00e7\u0131klama</th><th>M\u00fc\u015fteri</th><th>Orijinal</th><th>TRY</th><th>Kur</th><th>\u00d6deme</th><th>Referans</th><th></th></tr></thead><tbody>${rows.map(item=>`<tr data-kind="finance" data-id="${item.id}"><td data-label="Tarih">${esc(item.date||item.created_at||"\u2014")}</td><td data-label="T\u00fcr">${statusBadge(item.type||"\u2014")}</td><td data-label="Kategori">${esc(item.category||"\u2014")}</td><td data-label="A\u00e7\u0131klama">${esc(item.description||"\u2014")}</td><td data-label="M\u00fc\u015fteri">${esc(item.customer||item.customer_name||"\u2014")}</td><td data-label="Orijinal"><strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong></td><td data-label="TRY">${money(item.try_equivalent??financeTryValue(item),"TRY")}</td><td data-label="Kur">${esc(String(item.exchange_rate??1))}</td><td data-label="\u00d6deme">${esc(item.payment_method||"\u2014")}</td><td data-label="Referans">${esc(item.ref_no||item.tracking_no||"\u2014")}</td><td class="finance-action"><button class="mini" data-action="edit-finance" data-id="${item.id}">Detay / D\u00fczenle</button></td></tr>`).join("")}</tbody></table></div>`;
};

initializeAuth();

// Dialogs and top-bar actions can be rebound during partial renders (search,
// import preview, currency changes). Keep those operations idempotent so a
// single touch/click never opens the same dialog more than once.
const _ayecOpenDialog = openDialog;
openDialog = function(...args){
  const dialog = $("#appDialog");
  if(dialog?.open) dialog.close("replace");
  const result = _ayecOpenDialog(...args);
  // Dialog actions are handled by the JavaScript submit listener.  Keep the
  // form out of the browser's native method="dialog" close path, including
  // when an older cached index.html is still in use on the server.
  const form = $("#dialogForm");
  if(form) form.method = "post";
  const submit = $("#dialogSubmit");
  if(form && submit){
    // Use one deterministic path for mouse, touch and keyboard activation.
    // requestSubmit() still runs native required-field validation and the
    // openDialog onsubmit handler, while avoiding dialog-form quirks.
    submit.type = "button";
    submit.onclick = event => { event.preventDefault(); form.requestSubmit?.(); };
  }
  return result;
};

const _ayecBindPage = bindPage;
const _ayecBoundActions = new WeakSet();
bindPage = function(...args){
  const persistent = [...document.querySelectorAll("[data-action]")].filter(node=>_ayecBoundActions.has(node));
  const hidden = persistent.map(node=>[node,node.dataset.action]);
  hidden.forEach(([node])=>node.removeAttribute("data-action"));
  try{ return _ayecBindPage(...args); }
  finally{
    hidden.forEach(([node,action])=>{ if(action) node.dataset.action=action; });
    document.querySelectorAll("[data-action]").forEach(node=>_ayecBoundActions.add(node));
  }
};

const _ayecBindPageRows = bindPageRows;
bindPageRows = function(...args){
  const persistent = [...document.querySelectorAll("[data-action]")].filter(node=>_ayecBoundActions.has(node));
  const hidden = persistent.map(node=>[node,node.dataset.action]);
  hidden.forEach(([node])=>node.removeAttribute("data-action"));
  try{ return _ayecBindPageRows(...args); }
  finally{ hidden.forEach(([node,action])=>{ if(action) node.dataset.action=action; }); }
};

// Mobile/web barcode scanning. BarcodeDetector is used when the browser
// provides it; the same dialog always keeps a manual barcode field as a
// fallback for browsers without native detection.
let _ayecBarcodeStream = null;
let _ayecBarcodeFrame = 0;
let _ayecProductBarcodeStream = null;
let _ayecProductBarcodeFrame = 0;

// Offline fallback for phones whose BarcodeDetector implementation can open
// the camera but cannot decode a still image.  This deliberately covers the
// common retail formats (EAN-13/EAN-8, including UPC-A) so the feature does
// not depend on a CDN or on a server-side OCR service.
const _ayecEanL=["0001101","0011001","0010011","0111101","0100011","0110001","0101111","0111011","0110111","0001011"];
const _ayecEanG=["0100111","0110011","0011011","0100001","0011101","0111001","0000101","0010001","0001001","0010111"];
const _ayecEanR=["1110010","1100110","1101100","1000010","1011100","1001110","1010000","1000100","1001000","1110100"];
const _ayecEanParity=["LLLLLL","LLGLGG","LLGGLG","LLGGGL","LGLLGG","LGGLLG","LGGGLL","LGLGLG","LGLGGL","LGGLGL"];
const _ayecEanLMap=Object.fromEntries(_ayecEanL.map((pattern,digit)=>[pattern,digit]));
const _ayecEanGMap=Object.fromEntries(_ayecEanG.map((pattern,digit)=>[pattern,digit]));
const _ayecEanRMap=Object.fromEntries(_ayecEanR.map((pattern,digit)=>[pattern,digit]));
function _ayecEanCheck(value){
  const limit=value.length-1;
  let sum=0;
  for(let i=0;i<limit;i++){
    const digit=Number(value[i]);
    sum+=digit*(value.length===8?(i%2===0?3:1):(i%2===0?1:3));
  }
  return (10-(sum%10))%10===Number(value[limit]);
}
function _ayecDecodeEanSample(sample){
  const bits=sample.join("");
  if(bits.slice(0,3)!=="101")return "";
  const decode7=(offset,map)=>map[bits.slice(offset,offset+7)];
  if(bits.length>=95&&bits.slice(45,50)==="01010"&&bits.slice(92,95)==="101"){
    let left="",parity="";
    for(let i=0;i<6;i++){
      const offset=3+i*7,pattern=bits.slice(offset,offset+7);
      if(_ayecEanLMap[pattern]!==undefined){left+=_ayecEanLMap[pattern];parity+="L"}
      else if(_ayecEanGMap[pattern]!==undefined){left+=_ayecEanGMap[pattern];parity+="G"}
      else return "";
    }
    const first=_ayecEanParity.indexOf(parity);
    if(first<0)return "";
    let right="";
    for(let i=0;i<6;i++){
      const digit=decode7(50+i*7,_ayecEanRMap);
      if(digit===undefined)return "";
      right+=digit;
    }
    const value=String(first)+left+right;
    return _ayecEanCheck(value)?value:"";
  }
  if(bits.length>=67&&bits.slice(31,36)==="01010"&&bits.slice(64,67)==="101"){
    let left="",right="";
    for(let i=0;i<4;i++){
      const ld=decode7(3+i*7,_ayecEanLMap),rd=decode7(36+i*7,_ayecEanRMap);
      if(ld===undefined||rd===undefined)return "";
      left+=ld;right+=rd;
    }
    const value=left+right;
    return _ayecEanCheck(value)?value:"";
  }
  return "";
}
function _ayecDecodeEanRow(bits){
  if(!bits?.length)return "";
  const runs=[]; let value=bits[0],start=0;
  for(let i=1;i<bits.length;i++){
    if(bits[i]!==value){runs.push({value,start,length:i-start});value=bits[i];start=i}
  }
  runs.push({value,start,length:bits.length-start});
  for(let i=0;i+2<runs.length;i++){
    const a=runs[i],b=runs[i+1],c=runs[i+2];
    if(a.value!==1||b.value!==0||c.value!==1)continue;
    const module=(a.length+b.length+c.length)/3;
    if(module<1||module>40)continue;
    for(const scale of [.78,.88,.96,1,1.04,1.12,1.22]){
      const width=module*scale;
      for(let delta=-3;delta<=3;delta++){
        const left=a.start+delta;
        if(left<0||left+67*width>=bits.length+1)continue;
        const sample95=new Array(95);
        for(let n=0;n<95;n++)sample95[n]=bits[Math.min(bits.length-1,Math.max(0,Math.floor(left+(n+.5)*width)))];
        const ean13=_ayecDecodeEanSample(sample95);
        if(ean13)return ean13;
        const sample67=sample95.slice(0,67);
        const ean8=_ayecDecodeEanSample(sample67);
        if(ean8)return ean8;
      }
    }
  }
  return "";
}
function _ayecDecodeBarcodeCanvas(canvas,invert=false){
  const width=canvas.width,height=canvas.height,ctx=canvas.getContext("2d",{willReadFrequently:true});
  if(!ctx||!width||!height)return "";
  const ys=[];
  for(let i=0;i<20;i++)ys.push(Math.round(height*(.06+i*.047)));
  for(const y of ys){
    const row=ctx.getImageData(0,Math.min(height-1,y),width,1).data,luma=new Uint8Array(width);
    let min=255,max=0;
    for(let x=0;x<width;x++){
      const p=x*4,v=Math.round(.299*row[p]+.587*row[p+1]+.114*row[p+2]);
      luma[x]=v;min=Math.min(min,v);max=Math.max(max,v);
    }
    if(max-min<18)continue;
    const thresholds=[(min+max)/2,min+(max-min)*.35,min+(max-min)*.65,150,190];
    for(const threshold of thresholds){
      const bits=new Uint8Array(width);
      for(let x=0;x<width;x++)bits[x]=invert?(luma[x]>=threshold?1:0):(luma[x]<threshold?1:0);
      const result=_ayecDecodeEanRow(bits);
      if(result)return result;
    }
  }
  return "";
}
function _ayecDecodeBarcodeImage(source){
  const sourceWidth=source?.naturalWidth||source?.videoWidth||source?.width,sourceHeight=source?.naturalHeight||source?.videoHeight||source?.height;
  if(!sourceWidth||!sourceHeight)return "";
  const scale=Math.min(1,1600/Math.max(sourceWidth,sourceHeight)),canvas=document.createElement("canvas");
  canvas.width=Math.max(1,Math.round(sourceWidth*scale));canvas.height=Math.max(1,Math.round(sourceHeight*scale));
  const ctx=canvas.getContext("2d",{willReadFrequently:true});
  ctx.drawImage(source,0,0,canvas.width,canvas.height);
  let result=_ayecDecodeBarcodeCanvas(canvas)||_ayecDecodeBarcodeCanvas(canvas,true);
  if(result)return result;
  const rotated=document.createElement("canvas");rotated.width=canvas.height;rotated.height=canvas.width;
  const rotatedCtx=rotated.getContext("2d",{willReadFrequently:true});
  rotatedCtx.translate(rotated.width/2,rotated.height/2);rotatedCtx.rotate(Math.PI/2);rotatedCtx.drawImage(canvas,-canvas.width/2,-canvas.height/2);
  result=_ayecDecodeBarcodeCanvas(rotated)||_ayecDecodeBarcodeCanvas(rotated,true);
  return result;
}

function _ayecCloseProductBarcodeLive(){
  if(_ayecProductBarcodeFrame)cancelAnimationFrame(_ayecProductBarcodeFrame);
  _ayecProductBarcodeFrame=0;
  _ayecProductBarcodeStream?.getTracks?.().forEach(track=>track.stop());
  _ayecProductBarcodeStream=null;
  document.querySelector(".barcode-live-overlay")?.remove();
}
function _ayecSetProductBarcode(target,value){
  const result=String(value||"").trim();
  if(!target||!result)return false;
  target.value=result;
  target.dispatchEvent(new Event("input",{bubbles:true}));
  target.dispatchEvent(new Event("change",{bubbles:true}));
  target.focus();
  toast(`Barkod okundu: ${result}`,"success");
  return true;
}
async function _ayecStartProductBarcodeLive(target,camera){
  _ayecCloseProductBarcodeLive();
  const host=$("#appDialog")?.open?$("#appDialog"):document.body,overlay=document.createElement("div");
  overlay.className="barcode-live-overlay";
  overlay.innerHTML=`<div class="barcode-live-card" role="dialog" aria-label="Canlı barkod okuyucu"><header><div><p class="eyebrow">STOK KARTI</p><h3>Barkodu kameraya gösterin</h3></div><button type="button" class="icon-btn" data-barcode-live-close aria-label="Kapat">×</button></header><div class="barcode-live-view"><video autoplay muted playsinline></video><span class="barcode-live-guide" aria-hidden="true"></span></div><p class="barcode-live-status">Kamera hazırlanıyor…</p><button type="button" class="secondary barcode-live-manual" data-barcode-live-close>Vazgeç</button></div>`;
  host.appendChild(overlay);
  $("#appDialog")?.addEventListener("close",_ayecCloseProductBarcodeLive,{once:true});
  overlay.querySelectorAll("[data-barcode-live-close]").forEach(button=>button.addEventListener("click",_ayecCloseProductBarcodeLive));
  const video=overlay.querySelector("video"),status=overlay.querySelector(".barcode-live-status");
  const secure=window.isSecureContext||location.hostname==="localhost"||location.hostname==="127.0.0.1";
  if(!secure||!navigator.mediaDevices?.getUserMedia){
    _ayecCloseProductBarcodeLive();
    toast("Canlı kamera için HTTPS gerekir; fotoğrafla barkod tarama açılıyor.","warning");
    camera.click();
    return;
  }
  try{
    const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}},audio:false});
    if(!overlay.isConnected){stream.getTracks().forEach(track=>track.stop());return;}
    _ayecProductBarcodeStream=stream;video.srcObject=stream;await video.play?.();
    let detector=null;
    if(typeof BarcodeDetector==="function"){
      try{detector=new BarcodeDetector({formats:["ean_13","ean_8","code_128","code_39","upc_a","upc_e","qr_code"]})}catch{}
    }
    let lastFallbackScan=0;
    const scan=async()=>{
      if(!overlay.isConnected){_ayecCloseProductBarcodeLive();return;}
      if(video.readyState>=2){
        try{
          let value="";
          if(detector)value=(await detector.detect(video))?.[0]?.rawValue?.trim()||"";
          const now=Date.now();
          if(!value&&now-lastFallbackScan>350){lastFallbackScan=now;value=_ayecDecodeBarcodeImage(video)}
          if(value){_ayecCloseProductBarcodeLive();_ayecSetProductBarcode(target,value);return}
        }catch(error){if(status)status.textContent=`Tarama sürüyor: ${error.message}`}
      }
      if(status&&!detector)status.textContent="Barkodu çerçeveye hizalayın; otomatik okunuyor…";
      _ayecProductBarcodeFrame=requestAnimationFrame(scan);
    };
    _ayecProductBarcodeFrame=requestAnimationFrame(scan);
  }catch(error){
    _ayecCloseProductBarcodeLive();
    toast("Canlı kamera açılamadı; fotoğrafla barkod tarama açılıyor.","warning");
    camera.click();
  }
}

// Product dialogs prefer a live camera reader.  The native capture input stays
// as a safe fallback for HTTP deployments and browsers that deny live camera
// access, so the product form remains usable everywhere.
document.addEventListener("click",event=>{
  const button=event.target.closest?.('[data-action="product-barcode-camera"]');
  if(!button)return;
  event.preventDefault();
  event.stopPropagation();
  const field=button.closest(".barcode-control"),camera=field?.querySelector("#productBarcodeCamera"),target=field?.querySelector('input[name="barcode"]');
  if(!camera||!target)return;
  camera._ayecBarcodeTarget=target;
  void _ayecStartProductBarcodeLive(target,camera);
});
document.addEventListener("change",async event=>{
  const camera=event.target.closest?.("#productBarcodeCamera");
  if(!camera)return;
  const target=camera._ayecBarcodeTarget||camera.closest(".barcode-control")?.querySelector('input[name="barcode"]'),file=camera.files?.[0];
  camera.value="";
  if(!file||!target)return;
  let source=null;
  try{
    source=typeof createImageBitmap==="function"?await createImageBitmap(file):await new Promise((resolve,reject)=>{const image=new Image(),url=URL.createObjectURL(file);image.onload=()=>{URL.revokeObjectURL(url);resolve(image)};image.onerror=()=>{URL.revokeObjectURL(url);reject(Error("Barkod görüntüsü açılamadı"))};image.src=url});
    let result="";
    if(typeof BarcodeDetector==="function"){
      try{
        const detector=new BarcodeDetector({formats:["ean_13","ean_8","code_128","code_39","upc_a","upc_e","qr_code"]});
        result=(await detector.detect(source))?.[0]?.rawValue?.trim()||"";
      }catch{}
    }
    result=result||_ayecDecodeBarcodeImage(source);
    if(!result)throw Error("Barkod görüntüde bulunamadı");
    _ayecSetProductBarcode(target,result);
  }catch(error){toast(error.message||"Barkod okunamadı; barkodu elle girebilirsiniz.","warning")}
  finally{source?.close?.()}
});
function stopBarcodeScanner(){
  if(_ayecBarcodeFrame) cancelAnimationFrame(_ayecBarcodeFrame);
  _ayecBarcodeFrame = 0;
  _ayecBarcodeStream?.getTracks?.().forEach(track=>track.stop());
  _ayecBarcodeStream = null;
  const video = $("#barcodeVideo");
  if(video) video.srcObject = null;
}
function mountBarcodeButton(){
  if(page!=="stock") return;
  const actions = $(".page-head .actions");
  if(!actions || actions.querySelector('[data-action="barcode-scan"]')) return;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.dataset.action = "barcode-scan";
  button.textContent = "Kameradan Barkod";
  button.onclick = event => { event.preventDefault(); openBarcodeScanner(); };
  actions.insertBefore(button, actions.firstChild);
  _ayecBoundActions.add(button);
}
const _ayecRender = render;
render = function(...args){
  const result = _ayecRender(...args);
  mountBarcodeButton();
  return result;
};
function openBarcodeScanner(){
  stopBarcodeScanner();
  openDialog("Kameradan Barkod Oku","STOK / BARKOD",`<div class="barcode-scanner"><video id="barcodeVideo" autoplay muted playsinline></video><div class="field"><label>Barkod</label><input id="barcodeScanValue" name="barcode" inputmode="numeric" autocomplete="off" placeholder="Kamerayı açın veya barkodu yazın"></div><small class="muted" id="barcodeScanStatus">Kamera izni bekleniyor…</small></div>`,formData=>{
    const value=String(formData.get("barcode")||$("#barcodeScanValue")?.value||"").trim();
    if(!value) throw Error("Barkod okunamadı veya boş bırakıldı");
    stopBarcodeScanner();
    const search=$("#stockSearch");
    if(search){search.value=value;search.dispatchEvent(new Event("input",{bubbles:true}));}
    toast(`Barkod arandı: ${value}`,"success");
    return true;
  },"Barkodu Ara");
  const dialog=$("#appDialog"),video=$("#barcodeVideo"),status=$("#barcodeScanStatus");
  dialog?.addEventListener("close",stopBarcodeScanner,{once:true});
  if(!window.isSecureContext && location.hostname!=="localhost" && location.hostname!=="127.0.0.1"){
    if(status)status.textContent="Kamera için HTTPS gerekir; barkodu aşağıdaki alana elle girebilirsiniz.";
    return;
  }
  if(!navigator.mediaDevices?.getUserMedia){if(status)status.textContent="Bu tarayıcı kamera erişimini desteklemiyor; barkodu elle girin.";return;}
}

// Platform control center and dedicated automotive web surfaces.
sectorPages.teknik_servis.add("control-center");
sectorPages.otomotiv.add("control-center");
const controlSystemGroup=menu.find(group=>group.group==="Sistem");
if(controlSystemGroup&&!controlSystemGroup.items.some(item=>item.id==="control-center")){
  controlSystemGroup.items.unshift({id:"control-center",icon:"#",label:"Y\u00f6netim Merkezi"});
}
const menuVisibleBeforeControl=menuVisible;
menuVisible=function(item){
  if(item?.id==="control-center")return canAccessControlCenter();
  return menuVisibleBeforeControl(item);
};
const updateCurrentUserBeforeControl=updateCurrentUser;
updateCurrentUser=function(user){
  updateCurrentUserBeforeControl(user);
  renderNav();
};
const managementCenterBtn=$("#managementCenterBtn");
if(managementCenterBtn)managementCenterBtn.onclick=()=>{if(canAccessControlCenter())navigate("control-center")};

let activeAdminTab = "dashboard";

function renderControlCenter(){
  return `${pageHead("Y\u00f6netim Merkezi","AYEC Pro Uretici Yonetim Paneli. Firmalari, lisanslari, bildirimleri ve sunucu sagligini tek ekrandan yonetin.",'<button class="secondary" data-control-refresh>Verileri Yenile</button>')}
  <section class="control-operator" id="controlOperator">
    <div>
      <span class="eyebrow">PLATFORM OPERATORU</span>
      <strong id="adminVendorName">AYEC Pro</strong>
      <small id="adminVendorDetails">Yukleniyor...</small>
    </div>
  </section>
  <div class="admin-tabs">
    <button class="admin-tab-btn ${activeAdminTab==='dashboard'?'active':''}" data-admin-tab="dashboard">Dashboard</button>
    <button class="admin-tab-btn ${activeAdminTab==='tenants'?'active':''}" data-admin-tab="tenants">Firma & Lisans Yonetimi</button>
    <button class="admin-tab-btn ${activeAdminTab==='notifications'?'active':''}" data-admin-tab="notifications">Bildirim & Mesaj Gonder</button>
    <button class="admin-tab-btn ${activeAdminTab==='provision-invites'?'active':''}" data-admin-tab="provision-invites">Davet Kodlari</button>
    <button class="admin-tab-btn ${activeAdminTab==='staged-update'?'active':''}" data-admin-tab="staged-update">Guncelleme Dagitimi</button>
    <button class="admin-tab-btn ${activeAdminTab==='telemetry'?'active':''}" data-admin-tab="telemetry">Hata Loglari (Telemetry)</button>
  </div>
  <div id="adminTabContent">${empty("Yukleniyor","Yonetim verisi yukleniyor...")}</div>`;
}

async function loadControlCenter(){
  const tabContent = $("#adminTabContent");
  if(!tabContent) return;
  
  try {
    const data = await apiFetch("/api/control/overview");
    const vendor = data.vendor || {};
    $("#adminVendorName").textContent = vendor.name || "AYEC Pro";
    $("#adminVendorDetails").textContent = `${vendor.email || ""} · ${vendor.phone || ""} · ${vendor.server || ""}`;
    
    // Bind tab clicks dynamically
    $$("[data-admin-tab]").forEach(btn => {
      btn.onclick = () => {
        activeAdminTab = btn.dataset.adminTab;
        $$("[data-admin-tab]").forEach(b => b.classList.toggle("active", b.dataset.adminTab === activeAdminTab));
        loadControlCenter();
      };
    });
    
    if(activeAdminTab === "dashboard") {
      tabContent.innerHTML = `<div class="control-summary" style="margin-bottom: 24px;">
        <div><strong>${data.tenants.length}</strong><span>Toplam Firma</span></div>
        <div><strong>${data.tenants.filter(t => t.active !== 0).length}</strong><span>Aktif Firma</span></div>
        <div><strong>${data.tenants.filter(t => t.active === 0).length}</strong><span>Pasif Firma</span></div>
      </div>
      <div class="card">
        <div class="card-head"><h3>Sunucu Sistem Sagligi</h3><span class="badge">Canli Metrikler</span></div>
        <div id="serverMetricsContainer" class="server-metrics">${empty("Sorgulaniyor","Sistem kaynaklari okunuyor...")}</div>
      </div>`;
      
      try {
        const stats = await apiFetch("/api/control/server-status");
        const container = $("#serverMetricsContainer");
        if(container) {
          container.innerHTML = `
            <div class="server-card">
              <h4>CPU Kullanimi</h4>
              <div class="value">${stats.cpu_percent}%</div>
              <div class="progress-container"><div class="progress-bar ${stats.cpu_percent > 80 ? 'danger' : stats.cpu_percent > 60 ? 'warning' : ''}" style="width: ${stats.cpu_percent}%"></div></div>
            </div>
            <div class="server-card">
              <h4>RAM Bellek</h4>
              <div class="value">${stats.ram_percent}%</div>
              <small class="muted">${stats.ram_used_gb} GB / ${stats.ram_total_gb} GB</small>
              <div class="progress-container"><div class="progress-bar ${stats.ram_percent > 85 ? 'danger' : stats.ram_percent > 70 ? 'warning' : ''}" style="width: ${stats.ram_percent}%"></div></div>
            </div>
            <div class="server-card">
              <h4>Disk Alani</h4>
              <div class="value">${stats.disk_percent}%</div>
              <small class="muted">${stats.disk_used_gb} GB / ${stats.disk_total_gb} GB</small>
              <div class="progress-container"><div class="progress-bar ${stats.disk_percent > 90 ? 'danger' : stats.disk_percent > 75 ? 'warning' : ''}" style="width: ${stats.disk_percent}%"></div></div>
            </div>
          `;
        }
      } catch(e) {
        $("#serverMetricsContainer").innerHTML = `<p class="muted">Sistem metrikleri okunamadi: ${esc(e.message)}</p>`;
      }
    }
    
    else if(activeAdminTab === "tenants") {
      tabContent.innerHTML = `<div class="toolbar" style="margin-bottom: 18px;">
        <input class="control search" id="adminTenantSearch" placeholder="Firma adi veya ID ile ara...">
      </div>
      <div id="adminTenantsList"></div>`;
      
      const renderList = (filter = "") => {
        const listContainer = $("#adminTenantsList");
        if(!listContainer) return;
        const filtered = data.tenants.filter(t => t.company_name.toLowerCase().includes(filter.toLowerCase()) || t.id.toLowerCase().includes(filter.toLowerCase()));
        
        listContainer.innerHTML = filtered.map((tenant, index) => `
          <section class="card control-tenant" style="margin-bottom: 20px;">
            <header>
              <div>
                <small>${esc(tenant.id)}</small>
                <h3>${esc(tenant.company_name)}</h3>
              </div>
              <div class="actions">
                ${statusBadge(tenant.active !== 0 ? "Aktif" : "Pasif")}
                <span class="badge">${tenant.license_type || "Lifetime"} (${tenant.license_status || "Active"})</span>
                <span class="badge">Lisans Kodu: ${esc(tenant.license_code || "-")}</span>
                <span class="badge">${tenant.sector === "otomotiv" ? "Otomotiv" : "Teknik Servis"}</span>
                <button class="mini" data-control-tenant="${tenant.id}">Firma & Lisans Ayarlari</button>
              </div>
            </header>
            <div class="control-tabs"><strong>Kullanicilar</strong><span>${(tenant.users || []).length} hesap</span></div>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr><th>Kullanici</th><th>Ad Soyad</th><th>E-posta</th><th>Rol</th><th>Durum</th><th>Son Giris</th><th></th></tr>
                </thead>
                <tbody>
                  ${(tenant.users || []).map((u, ui) => `
                    <tr>
                      <td><strong>${esc(u.username)}</strong></td>
                      <td>${esc(u.full_name || "")}</td>
                      <td>${esc(u.email || "")}</td>
                      <td>${esc(u.role || "")}</td>
                      <td>${u.active !== 0 ? "Aktif" : "Pasif"}</td>
                      <td>${esc(u.last_login || "-")}</td>
                      <td class="actions">
                        <button class="mini" data-control-user="${tenant.id}:${u.id}" data-tenant-idx="${index}" data-user-idx="${ui}">Duzenle</button>
                        <button class="mini" data-control-reset="${tenant.id}:${u.id}" data-tenant-idx="${index}" data-user-idx="${ui}">Sifirlama Linki</button>
                      </td>
                    </tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
            <div class="control-tabs"><strong>Sunucu Yedekleri</strong><span>Son 7 yedek otomatik korunur</span><button class="mini" data-control-prune="${index}">Eski Yedekleri Temizle</button></div>
            <div class="control-backups">
              ${(tenant.backups || []).map(b => `
                <div>
                  <span><strong>${esc(b.original_name || "Firma.db")}</strong><small>${esc(b.created_at || "")} &middot; ${Math.max(1, Math.round(Number(b.size_bytes || 0)/1048576))} MB</small></span>
                  <button class="mini" data-control-restore="${index}:${b.id}">Masaustune Gonder</button>
                </div>
              `).join("") || '<p class="muted">Yuklenmis veritabani yedegi bulunmuyor.</p>'}
            </div>
          </section>
        `).join("") || empty("Firma bulunamadi", "Kriterlere uygun firma kaydi yok.");
        
        // Bind actions inside list
        $$("[data-control-tenant]").forEach(btn => {
          btn.onclick = () => {
            const t = data.tenants.find(x => x.id === btn.dataset.controlTenant);
            controlTenantDialog(t);
          };
        });
        $$("[data-control-user]").forEach(btn => {
          btn.onclick = () => {
            const tIdx = +btn.dataset.tenantIdx;
            const uIdx = +btn.dataset.userIdx;
            controlUserDialog(data.tenants[tIdx], data.tenants[tIdx].users[uIdx]);
          };
        });
        $$("[data-control-reset]").forEach(btn => {
          btn.onclick = async () => {
            const tIdx = +btn.dataset.tenantIdx;
            const uIdx = +btn.dataset.userIdx;
            const t = data.tenants[tIdx];
            const u = t.users[uIdx];
            try {
              const res = await apiFetch("/api/control/password-reset", {method: "POST", body: JSON.stringify({tenant_id: t.id, user_id: u.id})});
              let copied = false;
              try { await navigator.clipboard.writeText(res.reset_url); copied = true; } catch(e) {}
              openDialog("Sifre Sifirlama Baglantisi", "30 DAKIKA GECERLI", `
                <div class="field"><label>Kullanici</label><input disabled value="${esc(res.username)}"></div>
                <div class="field"><label>Baglanti</label><textarea readonly style="height: 60px;">${esc(res.reset_url)}</textarea></div>
                <p class="muted">${copied ? "Baglanti panoya kopyalandi." : "Baglantiyi yukaridaki kutudan kopyalayip musteriye iletin."}</p>
              `, () => true, "Kapat");
            } catch(err) { toast(err.message, "error"); }
          };
        });
        $$("[data-control-restore]").forEach(btn => {
          btn.onclick = async () => {
            const [tIdx, bId] = btn.dataset.controlRestore.split(":");
            const t = data.tenants[+tIdx];
            if(!confirm(`${t.company_name} firmasina bu yedek uzaktan gonderilsin mi? Masaustundeki mevcut veritabani silinip yerine bu yedek yazilacaktir.`)) return;
            try {
              await apiFetch("/api/control/restore", {method: "POST", body: JSON.stringify({tenant_id: t.id, backup_id: +bId})});
              toast("Uzaktan veri geri yukleme emri siraya alindi.", "success");
            } catch(e) { toast(e.message, "error"); }
          };
        });
        $$("[data-control-prune]").forEach(btn => {
          btn.onclick = async () => {
            const t = data.tenants[+btn.dataset.controlPrune];
            if(!confirm(`${t.company_name} icin son 7 yedek disindaki eski dosyalar temizlensin mi? Bekleyen geri yukleme yedekleri korunacaktir.`)) return;
            try {
              const result = await apiFetch("/api/control/backups/prune", {method: "POST", body: JSON.stringify({tenant_id: t.id})});
              toast(`${result.removed_count} eski yedek temizlendi.`, "success");
              await loadControlCenter();
            } catch(error) { toast(error.message, "error"); }
          };
        });
      };
      
      renderList();
      const sInput = $("#adminTenantSearch");
      if(sInput) sInput.oninput = (e) => renderList(e.target.value);
    }
    
    else if(activeAdminTab === "notifications") {
      const options = data.tenants.map(t => `<option value="${t.id}">${esc(t.company_name)}</option>`).join("");
      tabContent.innerHTML = `<div class="card" style="max-width: 600px; margin: 0 auto;">
        <div class="card-head"><h3>Global Bildirim & Mesaj Gonder</h3></div>
        <form id="adminNotificationForm" class="form-grid">
          <div class="field full">
            <label>Hedef Kitle</label>
            <select name="target_tenant_id">
              <option value="All">Tum Firmalar (Global)</option>
              ${options}
            </select>
          </div>
          <div class="field full">
            <label>Mesaj Basligi</label>
            <input name="message_title" required placeholder="Orn: Planli Bakim Duyurusu">
          </div>
          <div class="field full">
            <label>Mesaj Icerigi</label>
            <textarea name="message_content" required style="height: 120px;" placeholder="Duyuru metnini buraya yazin..."></textarea>
          </div>
          <label class="setting field full">
            <span>Masaustunde Popup olarak acilsin</span>
            <input class="switch" type="checkbox" name="popup" value="1">
          </label>
          <div class="field full" style="margin-top: 12px;">
            <button class="primary" type="submit">Mesaji Yayinla (Gonder)</button>
          </div>
        </form>
      </div>`;
      
      const form = $("#adminNotificationForm");
      form.onsubmit = async (e) => {
        e.preventDefault();
        try {
          const fd = new FormData(form);
          const payload = Object.fromEntries(fd);
          payload.popup = fd.get("popup") === "1";
          await apiFetch("/api/control/send-notification", {method: "POST", body: JSON.stringify(payload)});
          toast("Duyuru mesajiniz hedeflenen istemcilere gonderildi.", "success");
          form.reset();
        } catch(err) { toast(err.message, "error"); }
      };
    }
    
    else if(activeAdminTab === "staged-update") {
      tabContent.innerHTML = `<div class="grid-2">
        <div class="card">
          <div class="card-head"><h3>Yeni Surum Paketle</h3></div>
          <form id="adminUpdateForm" class="form-grid">
            <div class="field"><label>Surum No *</label><input name="version" placeholder="Orn: v2.0.1" required></div>
            <div class="field"><label>Dagitim Kapsami</label><select name="target_scope"><option value="All">Tum Firmalar</option><option value="Pilot">Sadece Pilot Firmalar</option></select></div>
            <div class="field full"><label>Paket Dosya Yolu / URL</label><input name="file_path" placeholder="Orn: C:\\Setup\\setup.exe veya sunucu adresi"></div>
            <div class="field full"><label>Guncelleme Notlari</label><textarea name="notes" style="height: 80px;"></textarea></div>
            <div class="field full"><button class="primary" type="submit">Guncellemeyi Yayinla</button></div>
          </form>
        </div>
        <div class="card">
          <div class="card-head"><h3>Yayinlanan Surumler</h3></div>
          <div id="stagedUpdatesList">${empty("Sorgulaniyor","Yayinlanmis surumler aliniyor...")}</div>
        </div>
      </div>`;
      
      const form = $("#adminUpdateForm");
      form.onsubmit = async (e) => {
        e.preventDefault();
        try {
          const payload = Object.fromEntries(new FormData(form));
          await apiFetch("/api/control/staged-update", {method: "POST", body: JSON.stringify(payload)});
          toast("Yeni surum basariyla sisteme tanimlandi.", "success");
          form.reset();
          loadUpdates();
        } catch(err) { toast(err.message, "error"); }
      };
      
      const loadUpdates = async () => {
        try {
          const res = await apiFetch("/api/control/staged-update");
          const list = $("#stagedUpdatesList");
          if(list) {
            list.innerHTML = res.updates.length ? `<div class="table-wrap"><table>
              <thead><tr><th>Surum</th><th>Kapsam</th><th>Tarih</th></tr></thead>
              <tbody>${res.updates.map(u => `<tr><td><strong>${esc(u.version)}</strong></td><td>${esc(u.target_scope)}</td><td>${esc(String(u.created_at).slice(0,16))}</td></tr>`).join("")}</tbody>
            </table></div>` : empty("Surum yok", "Henuz dagitilmis surum bulunmuyor.");
          }
        } catch(err) { }
      };
      loadUpdates();
    }

    else if(activeAdminTab === "provision-invites") {
      tabContent.innerHTML = `<div class="grid-2">
        <div class="card">
          <div class="card-head"><h3>Yeni Kurulum Davet Kodu</h3></div>
          <p class="muted">Kod sadece ilk sunucu kaydi icin kullanilir. Kod ekranda bir kez gosterilir ve veritabaninda hash olarak saklanir.</p>
          <form id="provisionInviteForm" class="form-grid">
            <div class="field"><label>Gecerlilik (saat)</label><input name="expires_in_hours" type="number" min="1" max="720" value="72" required></div>
            <div class="field"><label>Kullanim Sayisi</label><input name="max_uses" type="number" min="1" max="20" value="1" required></div>
            <div class="field full"><button class="primary" type="submit">Davet Kodu Uret</button></div>
          </form>
          <div id="provisionInviteCodeResult" class="field full" hidden></div>
        </div>
        <div class="card">
          <div class="card-head"><h3>Aktif ve Gecmis Kodlar</h3><span id="provisionInviteRequirement" class="badge">Yukleniyor</span></div>
          <div id="provisionInviteList">${empty("Sorgulaniyor","Davet kodlari aliniyor...")}</div>
        </div>
      </div>`;
      const form = $("#provisionInviteForm");
      const renderInviteList = async () => {
        try {
          const response = await apiFetch("/api/control/provision-invites");
          const requirement = $("#provisionInviteRequirement");
          if(requirement) requirement.textContent = response.required ? "Kod zorunlu" : "Kod istege bagli";
          const list = $("#provisionInviteList");
          if(!list) return;
          const items = response.invites || [];
          list.innerHTML = items.length ? `<div class="table-wrap"><table><thead><tr><th>ID</th><th>Son Gecerlilik</th><th>Kullanim</th><th>Durum</th><th></th></tr></thead><tbody>${items.map(item => {
            const expired = new Date(item.expires_at) <= new Date();
            const exhausted = Number(item.use_count) >= Number(item.max_uses);
            const revoked = Boolean(item.revoked_at);
            const status = revoked ? "Iptal" : expired ? "Suresi doldu" : exhausted ? "Kullanildi" : "Aktif";
            const canRevoke = !revoked && !expired && !exhausted;
            return `<tr><td>${esc(item.id)}</td><td>${esc(String(item.expires_at).slice(0,19))}</td><td>${esc(item.use_count)} / ${esc(item.max_uses)}</td><td>${statusBadge(status)}</td><td>${canRevoke ? `<button class="mini" data-provision-invite-revoke="${esc(item.id)}">Iptal Et</button>` : ""}</td></tr>`;
          }).join("")}</tbody></table></div>` : empty("Kod yok","Henuz davet kodu olusturulmadi.");
          $$('[data-provision-invite-revoke]').forEach(button => {
            button.onclick = async () => {
              if(!confirm("Bu davet kodu iptal edilsin mi?")) return;
              try {
                await apiFetch("/api/control/provision-invite/revoke", {method:"POST",body:JSON.stringify({invite_id:Number(button.dataset.provisionInviteRevoke)})});
                toast("Davet kodu iptal edildi.", "success");
                renderInviteList();
              } catch(error) { toast(error.message, "error"); }
            };
          });
        } catch(error) {
          const list = $("#provisionInviteList");
          if(list) list.innerHTML = empty("Davet kodlari alinamadi", error.message);
        }
      };
      form.onsubmit = async event => {
        event.preventDefault();
        try {
          const payload = Object.fromEntries(new FormData(form));
          const response = await apiFetch("/api/control/provision-invite", {method:"POST",body:JSON.stringify(payload)});
          const result = $("#provisionInviteCodeResult");
          if(result) {
            result.hidden = false;
            result.innerHTML = `<label>Davet Kodu - Simdi kopyalayin</label><input readonly value="${esc(response.invite_code)}">`;
          }
          toast("Davet kodu olusturuldu.", "success");
          renderInviteList();
        } catch(error) { toast(error.message, "error"); }
      };
      renderInviteList();
    }
    
    else if(activeAdminTab === "telemetry") {
      tabContent.innerHTML = `<div class="card">
        <div class="card-head"><h3>Cokme ve Hata Kayitlari</h3></div>
        <div id="adminTelemetryList">${empty("Sorgulaniyor","Hata loglari sorgulaniyor...")}</div>
      </div>`;
      
      const loadTelemetry = async () => {
        try {
          const res = await apiFetch("/api/control/telemetry/errors");
          const list = $("#adminTelemetryList");
          if(list) {
            list.innerHTML = res.logs.length ? `<div class="table-wrap"><table>
              <thead><tr><th>Firma</th><th>Surum</th><th>OS</th><th>Hata Mesaji</th><th>Tarih</th><th></th></tr></thead>
              <tbody>${res.logs.map((log, i) => `<tr>
                <td><strong>${esc(log.tenant_id)}</strong></td>
                <td>${esc(log.version)}</td>
                <td>${esc(log.os_info)}</td>
                <td class="text-danger"><code>${esc(log.error_message)}</code></td>
                <td>${esc(String(log.created_at).slice(0,19))}</td>
                <td><button class="mini" data-view-trace="${i}">Stack Trace</button></td>
              </tr>`).join("")}</tbody>
            </table></div>` : empty("Temiz", "Masaustu uygulamalarindan gelen herhangi bir hata kaydi yok.");
            
            $$("[data-view-trace]").forEach(btn => {
              btn.onclick = () => {
                const log = res.logs[+btn.dataset.viewTrace];
                openDialog("Stack Trace Hata Ayrintisi", "TELEMETRY LOG", `
                  <div class="field"><label>Firma / Surum / OS</label><input disabled value="${esc(log.tenant_id)} · ${esc(log.version)} · ${esc(log.os_info)}"></div>
                  <div class="field"><label>Hata Mesaji</label><input disabled value="${esc(log.error_message)}"></div>
                  <div class="field"><label>C++ / Python Stack Trace</label>
                    <div class="telemetry-trace">${esc(log.stack_trace || "Stack trace verisi bulunmuyor.")}</div>
                  </div>
                `, () => true, "Kapat");
              };
            });
          }
        } catch(err) { }
      };
      loadTelemetry();
    }
    
  } catch(error) {
    tabContent.innerHTML = empty("Y\u00f6netim verisi al\u0131namad\u0131", error.message);
  }
}

function controlTenantDialog(tenant){
  openDialog(`${tenant.company_name} - Firma & Lisans Ayarlar\u0131`,"PLATFORM Y\u00d6NET\u0130M\u0130",`
    <div class="form-grid">
      <div class="field full"><label>Firma Ad\u0131</label><input name="company_name" value="${esc(tenant.company_name)}" required></div>
      <div class="field"><label>Sekt\u00f6r</label><select name="sector"><option value="teknik_servis" ${tenant.sector!=="otomotiv"?"selected":""}>Teknik Servis</option><option value="otomotiv" ${tenant.sector==="otomotiv"?"selected":""}>Otomotiv Servis</option></select></div>
      <div class="field"><label>Firma Durumu</label><select name="active"><option value="1" ${tenant.active!==0?"selected":""}>Aktif</option><option value="0" ${tenant.active===0?"selected":""}>Pasif</option></select></div>
      <div class="field"><label>Lisans Turu</label><select name="license_type"><option ${tenant.license_type==="Lifetime"?"selected":""}>Lifetime</option><option ${tenant.license_type==="Demo"?"selected":""}>Demo</option><option ${tenant.license_type==="Premium"?"selected":""}>Premium</option></select></div>
      <div class="field"><label>Lisans Durumu</label><select name="license_status"><option ${tenant.license_status==="Active"?"selected":""}>Active</option><option ${tenant.license_status==="Suspended"?"selected":""}>Suspended</option><option ${tenant.license_status==="Expired"?"selected":""}>Expired</option></select></div>
      <div class="field full"><label>Lisans Kodu</label><input value="${esc(tenant.license_code || "-")}" readonly></div>
      <div class="field"><label>Lisans Baslangic</label><input name="license_start" type="date" value="${esc(tenant.license_start || "")}"></div>
      <div class="field"><label>Lisans Bitis</label><input name="license_end" type="date" value="${esc(tenant.license_end || "")}"></div>
    </div>
  `,async formData=>{
    const values=Object.fromEntries(formData);
    await apiFetch("/api/control/tenant",{method:"POST",body:JSON.stringify({...values,tenant_id:tenant.id})});
    await loadControlCenter();
    toast("Firma ve lisans ayarlari guncellendi","success");
    return true;
  },"Ayarlar\u0131 Kaydet");
}

function controlUserDialog(tenant,user){
  openDialog(`${user.username} - Kullan\u0131c\u0131`,"UZAKTAN KULLANICI YONETIMI",`<div class="form-grid"><div class="field"><label>Kullanici Adi</label><input name="username" value="${esc(user.username)}" required></div><div class="field"><label>Ad Soyad</label><input name="full_name" value="${esc(user.full_name||"")}"></div><div class="field"><label>E-posta</label><input name="email" type="email" value="${esc(user.email||"")}"></div><div class="field"><label>Cep Telefonu</label><input name="phone" value="${esc(user.phone||"")}"></div><div class="field"><label>Rol</label><select name="role">${["Admin","Manager","Technician","User"].map(role=>`<option ${String(user.role).toLowerCase()===role.toLowerCase()?"selected":""}>${role}</option>`).join("")}</select></div><div class="field"><label>Durum</label><select name="active"><option value="1" ${user.active!==0?"selected":""}>Aktif</option><option value="0" ${user.active===0?"selected":""}>Pasif</option></select></div></div><p class="muted">Parolalar geri okunamaz. Platform operatoru ayri olarak tek kullanimlik sifirlama baglantisi olusturur.</p>`,async formData=>{const values=Object.fromEntries(formData);await apiFetch("/api/control/user",{method:"POST",body:JSON.stringify({...values,tenant_id:tenant.id,user_id:user.id})});await loadControlCenter();toast("Kullanici ayarlari guncellendi","success");return true},"Kullaniciyi Guncelle");
}

function renderVehicleMaintenance(){
  return `${pageHead("Ara\u00e7 Bak\u0131m Takibi","Bak\u0131m kartlar\u0131, randevular, muayene ve servis ba\u011flant\u0131lar\u0131.",'<button class="primary" data-maintenance-add>+ Bak\u0131m Kart\u0131</button>')}<section class="card"><div class="toolbar"><input class="control search" id="maintenanceSearch" placeholder="Plaka, m\u00fc\u015fteri veya marka ara"><button class="secondary" data-maintenance-refresh>Yenile</button></div><div id="maintenanceTable">${empty("Y\u00fckleniyor","Bak\u0131m kartlar\u0131 getiriliyor.")}</div></section>`;
}

let vehicleMaintenanceRows=[];
async function loadVehicleMaintenance(query=""){
  const host=$("#maintenanceTable");if(!host)return;
  try{
    const data=await apiFetch(`/api/desktop/table/vehicle_maintenance_cards?limit=500&q=${encodeURIComponent(query)}`);
    vehicleMaintenanceRows=data.rows||[];
    host.innerHTML=vehicleMaintenanceRows.length?`<div class="table-wrap"><table><thead><tr><th>Plaka</th><th>M\u00fc\u015fteri</th><th>Ara\u00e7</th><th>KM</th><th>Servis</th><th>Sonraki Bak\u0131m</th><th>Muayene</th><th>Randevu</th><th>Servis Ref.</th><th></th></tr></thead><tbody>${vehicleMaintenanceRows.map((row,index)=>`<tr tabindex="0" data-maintenance-row="${index}"><td><strong>${esc(row.vehicle_plate||"-")}</strong></td><td>${esc(row.customer_name||"-")}</td><td>${esc([row.vehicle_brand,row.vehicle_model,row.vehicle_year].filter(Boolean).join(" ")||"-")}</td><td>${esc(row.odometer||0)}</td><td>${esc(String(row.service_date||"-").slice(0,10))}</td><td>${esc(String(row.next_maintenance_date||"-").slice(0,10))}</td><td>${esc(String(row.inspection_due_date||"-").slice(0,10))}</td><td>${esc([String(row.appointment_date||"").slice(0,10),row.appointment_time].filter(Boolean).join(" ")||"-")}</td><td>${esc(row.linked_device_tracking_no||"-")}</td><td><div class="row-actions"><button class="mini" data-maintenance-edit="${index}">Detay / D\u00fczenle</button>${row.linked_device_tracking_no?`<button class="mini" data-maintenance-service="${index}">Servis</button>`:""}</div></td></tr>`).join("")}</tbody></table></div>`:empty("Bak\u0131m kart\u0131 yok","Yeni bir ara\u00e7 bak\u0131m kart\u0131 olu\u015fturun.");
    $$('[data-maintenance-edit]').forEach(button=>button.onclick=()=>maintenanceDialog(data.rows[+button.dataset.maintenanceEdit]));
    $$('[data-maintenance-service]').forEach(button=>button.onclick=()=>openMaintenanceService(data.rows[+button.dataset.maintenanceService]));
    $$('[data-maintenance-row]').forEach(row=>row.ondblclick=()=>maintenanceDialog(data.rows[+row.dataset.maintenanceRow]));
  }catch(error){host.innerHTML=empty("Bak\u0131m kartlar\u0131 al\u0131namad\u0131",error.message)}
}

const maintenanceItemDefaults=[
  ["oil_change","Ya\u011f De\u011fi\u015fimi",90,10000],
  ["oil_filter","Ya\u011f Filtresi",90,10000],
  ["air_filter","Hava Filtresi",180,15000],
  ["cabin_filter","Polen Filtresi",180,15000],
  ["brake_fluid","Fren Hidroli\u011fi",365,40000],
  ["antifreeze","Antifriz",365,30000],
  ["glass_water","Cam Suyu",30,0],
  ["spark_plugs","Buji Kontrol\u00fc",365,30000],
  ["timing_belt","Triger Kay\u0131\u015f\u0131",730,90000],
  ["timing_chain","Triger Zinciri",1095,120000],
];

function maintenanceDateAfter(base,days){
  const date=new Date(`${base||today()}T12:00:00`);date.setDate(date.getDate()+Number(days||0));return date.toISOString().slice(0,10);
}

function maintenanceItemsHtml(items=[],serviceDate=today(),odometer=0){
  const stored=new Map(items.map(item=>[item.item_type,item]));
  return `<div class="field full"><label>Bak\u0131m Kalemleri *</label><div class="maintenance-items"><div class="maintenance-item maintenance-item-head"><span>Yap\u0131ld\u0131</span><span>Kalem</span><span>Periyot (G\u00fcn)</span><span>Periyot (KM)</span><span>Sonraki Tarih</span><span>Sonraki KM</span></div>${maintenanceItemDefaults.map(([type,label,days,km])=>{const item=stored.get(type)||{},checked=item.performed!==undefined?Boolean(item.performed):!["glass_water"].includes(type);return `<div class="maintenance-item" data-maintenance-item="${type}" data-label="${esc(item.item_label||label)}"><input class="maintenance-performed" type="checkbox" ${checked?"checked":""} aria-label="${esc(label)}"><strong>${esc(item.item_label||label)}</strong><input class="maintenance-days" type="number" min="0" value="${esc(item.interval_days??days)}"><input class="maintenance-km" type="number" min="0" value="${esc(item.interval_km??km)}"><input class="maintenance-due-date" type="date" value="${esc(String(item.next_due_date||maintenanceDateAfter(serviceDate,days)).slice(0,10))}"><input class="maintenance-due-km" type="number" min="0" value="${esc(item.next_due_odometer??(Number(odometer||0)+km))}"></div>`}).join("")}</div><small class="muted">Cam Suyu kaydedilir; randevu mesaj\u0131 ve kritik bak\u0131m hat\u0131rlatmas\u0131na dahil edilmez.</small></div>`;
}

async function maintenanceDialog(sourceRow={}){
  let row={...sourceRow},items=[];
  if(row.id){
    try{const detail=await apiFetch(`/api/desktop/vehicle-maintenance/detail/${row.id}`);row=detail.card||row;items=detail.items||[]}catch(error){toast(error.message,"error");return}
  }
  const customerOptions=db.customers.map(customer=>`<option value="${esc(customer.id)}" ${String(customer.id)===String(row.customer_id||"")?"selected":""}>${esc(customer.name)}${customer.phone?` - ${esc(customer.phone)}`:""}</option>`).join("");
  const serviceDate=String(row.service_date||today()).slice(0,10),odometer=Number(row.odometer||0);
  openDialog(row.id?"Bak\u0131m Kart\u0131n\u0131 D\u00fczenle":"Yeni Bak\u0131m Kart\u0131","OTOMOT\u0130V BAKIM",`<div class="form-grid maintenance-form"><div class="field full"><label>M\u00fc\u015fteri *</label><select name="customer_id" required><option value="">M\u00fc\u015fteri se\u00e7in</option>${customerOptions}</select></div><div class="field"><label>Plaka *</label><input name="vehicle_plate" value="${esc(row.vehicle_plate||"")}" required></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0" value="${esc(odometer)}"></div><div class="field"><label>Marka</label><input name="vehicle_brand" value="${esc(row.vehicle_brand||"")}"></div><div class="field"><label>Model</label><input name="vehicle_model" value="${esc(row.vehicle_model||"")}"></div><div class="field"><label>Y\u0131l</label><input name="vehicle_year" type="number" min="1900" max="2200" value="${esc(row.vehicle_year||"")}"></div><div class="field"><label>Ara\u00e7 Tipi</label><input name="vehicle_type" value="${esc(row.vehicle_type||"")}"></div><div class="field"><label>Motor Tipi</label><input name="engine_type" value="${esc(row.engine_type||"")}"></div><div class="field"><label>Yak\u0131t T\u00fcr\u00fc</label><select name="fuel_type"><option>${esc(row.fuel_type||"Benzin")}</option><option>Benzin</option><option>Dizel</option><option>LPG</option><option>Hibrit</option><option>Elektrik</option></select></div><div class="field"><label>Servis Tarihi</label><input name="service_date" type="date" value="${esc(serviceDate)}"></div><div class="field"><label>Sonraki Bak\u0131m</label><input name="next_maintenance_date" type="date" value="${esc(String(row.next_maintenance_date||"").slice(0,10))}"></div><div class="field"><label>Muayene Tarihi</label><input name="inspection_due_date" type="date" value="${esc(String(row.inspection_due_date||"").slice(0,10))}"></div><div class="field"><label>Randevu Tarihi</label><input name="appointment_date" type="date" value="${esc(String(row.appointment_date||row.manual_appointment_date||"").slice(0,10))}"></div><div class="field"><label>Randevu Saati</label><input name="appointment_time" type="time" value="${esc(row.appointment_time||"09:00")}"></div><div class="field full"><label>Notlar</label><textarea name="notes">${esc(row.notes||"")}</textarea></div>${maintenanceItemsHtml(items,serviceDate,odometer)}</div>`,async formData=>{
    const payload=Object.fromEntries(formData);payload.customer_id=Number(payload.customer_id||0);payload.odometer=Number(payload.odometer||0);payload.vehicle_year=Number(payload.vehicle_year||0)||null;if(row.id)payload.id=row.id;if(row.vehicle_id)payload.vehicle_id=row.vehicle_id;
    payload.items=$$('[data-maintenance-item]',$("#dialogBody")).map(element=>({item_type:element.dataset.maintenanceItem,item_label:element.dataset.label,performed:element.querySelector(".maintenance-performed").checked,interval_days:Number(element.querySelector(".maintenance-days").value||0),interval_km:Number(element.querySelector(".maintenance-km").value||0),next_due_date:element.querySelector(".maintenance-due-date").value,next_due_odometer:Number(element.querySelector(".maintenance-due-km").value||0)}));
    const selectedDates=payload.items.filter(item=>item.performed&&item.item_type!=="glass_water"&&item.next_due_date).map(item=>item.next_due_date).sort();if(!payload.next_maintenance_date)payload.next_maintenance_date=selectedDates[0]||"";
    const result=await apiFetch("/api/desktop/vehicle-maintenance/save",{method:"POST",body:JSON.stringify(payload)});await hydrateDesktop(true);await loadVehicleMaintenance();toast("Bak\u0131m kart\u0131, servis ve randevu kaydedildi","success");offerMaintenanceWhatsApp(result,payload);return true
  },"Bak\u0131m Kart\u0131n\u0131 Kaydet");
}

function offerMaintenanceWhatsApp(result,payload){
  if(!result.customer_phone||(result.important_items||[]).length===0||!payload.appointment_date)return;
  if(!confirm("Bak\u0131m randevusu i\u00e7in m\u00fc\u015fteriye WhatsApp mesaj\u0131 haz\u0131rlans\u0131n m\u0131?"))return;
  let phone=String(result.customer_phone).replace(/\D/g,"");if(phone.startsWith("0"))phone=`90${phone.slice(1)}`;else if(phone.length===10)phone=`90${phone}`;
  const itemText=(result.important_items||[]).join(", "),message=`Say\u0131n ${result.customer_name}, ${result.vehicle_plate} plakal\u0131 arac\u0131n\u0131z i\u00e7in ${payload.appointment_date} ${payload.appointment_time||"09:00"} tarihli bak\u0131m randevunuz olu\u015fturuldu. Bak\u0131m kalemleri: ${itemText}. AYEC Pro Otomotiv`;
  window.open(`https://wa.me/${phone}?text=${encodeURIComponent(message)}`,"_blank","noopener");
}

function openMaintenanceService(row){
  const tracking=String(row.linked_device_tracking_no||"");
  const found=findService(tracking);if(found?.[1])return technicianDialog(found[0],found[1]);
  toast("Ba\u011fl\u0131 servis kayd\u0131 yenileniyor","warning");hydrateDesktop(true).then(()=>{const next=findService(tracking);if(next?.[1])technicianDialog(next[0],next[1]);else toast("Servis kayd\u0131 bulunamad\u0131","error")});
}

const renderBeforeControl=render;
render=function(){
  if(page==="control-center"){
    $("#content").innerHTML=renderControlCenter();
    $("[data-control-refresh]").onclick=loadControlCenter;
    loadControlCenter();
    return;
  }
  if(page==="automotive-stock"){
    $("#content").innerHTML=renderStock();
    bindPage();
    return;
  }
  if(page==="vehicle-maintenance"){
    $("#content").innerHTML=renderVehicleMaintenance();
    $("[data-maintenance-add]").onclick=()=>maintenanceDialog();
    $("[data-maintenance-refresh]").onclick=()=>loadVehicleMaintenance($("#maintenanceSearch")?.value||"");
    $("#maintenanceSearch").oninput=event=>loadVehicleMaintenance(event.target.value);
    loadVehicleMaintenance();
    return;
  }
  renderBeforeControl();
};

const settingBodyBeforeSectorControl=settingBody;
settingBody=function(settings){
  const body=settingBodyBeforeSectorControl(settings);
  if(settingsSection!=="identity")return body;
  const sectorName=currentSector==="otomotiv"?"Otomotiv Servis":"Teknik Servis";
  if(!currentAuthUser?.is_admin){
    return `<section class="setting sector-setting"><div><h3>Sekt\u00f6rel Kimlik</h3><p class="muted">Aktif sekt\u00f6r: ${sectorName}. Bu ayar\u0131 yaln\u0131zca firma y\u00f6neticisi de\u011fi\u015ftirebilir.</p></div></section>${body}`;
  }
  return `<section class="setting sector-setting"><div><h3>Sekt\u00f6rel Kimlik</h3><p class="muted">Sekt\u00f6r de\u011fi\u015fikli\u011fi men\u00fcleri ve formlar\u0131 an\u0131nda yeniden kurar. Mevcut veriler silinmez.</p></div><div class="actions"><select class="control" id="companySectorSelect"><option value="teknik_servis" ${currentSector!=="otomotiv"?"selected":""}>Teknik Servis</option><option value="otomotiv" ${currentSector==="otomotiv"?"selected":""}>Otomotiv Servis</option></select><button class="primary" type="button" data-action="save-company-sector">Sekt\u00f6r\u00fc Uygula</button></div></section>${body}`;
};

async function saveCompanySector(){
  if(!currentAuthUser?.is_admin)return toast("Bu i\u015flem i\u00e7in firma y\u00f6neticisi yetkisi gerekiyor","error");
  const selected=$("#companySectorSelect")?.value;
  if(!["teknik_servis","otomotiv"].includes(selected))return toast("Ge\u00e7erli bir sekt\u00f6r se\u00e7in","error");
  if(selected===currentSector)return toast("Se\u00e7ili sekt\u00f6r zaten aktif","info");
  const label=selected==="otomotiv"?"Otomotiv Servis":"Teknik Servis";
  if(!confirm(`\u00c7al\u0131\u015fma alan\u0131 ${label} moduna ge\u00e7irilsin mi?`))return;
  try{
    const result=await apiFetch("/api/company/sector",{method:"POST",body:JSON.stringify({sector:selected})});
    currentSector=result.sector;desktopInternalSettings.current_sector=result.sector;
    await hydrateDesktop(true);renderNav();navigate("dashboard");
    toast(`Sekt\u00f6r ${label} olarak g\u00fcncellendi`,"success",7000);
  }catch(error){toast(`Sekt\u00f6r g\u00fcncellenemedi: ${error.message}`,"error")}
}

document.addEventListener("click",event=>{
  const action=event.target.closest("[data-action]")?.dataset.action;
  if(action==="save-company-sector")saveCompanySector();
});

// Sector-scoped navigation keeps technical service and automotive menus isolated.
const ayecSectorMenuModels={
  teknik_servis:[
    {group:"Operasyon",items:[
      {id:"dashboard",icon:"&#8962;",label:"Genel Bak\u0131\u015f"},
      {id:"service-parent",icon:"&#9881;",label:"Servis Y\u00f6netimi",children:[
        {id:"services",label:"Servis Panosu"},
        {id:"technician",label:"Teknisyen Paneli"},
        {id:"field-service",label:"Saha Servis Haritas\u0131"},
        {id:"appointments",label:"Randevular"},
        {id:"logistics",label:"Lojistik ve Garanti"},
        {id:"job-reports",label:"\u0130\u015f ve Servis Raporlar\u0131"}
      ]},
      {id:"assistant",icon:"AI",label:"AI Asistan"}
    ]},
    {group:"M\u00fc\u015fteri",items:[
      {id:"customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteri Hub",children:[
        {id:"customers",label:"M\u00fc\u015fteri Listesi"},
        {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
        {id:"contracts",label:"Bak\u0131m S\u00f6zle\u015fmeleri"},
        {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
        {id:"announcements",label:"Duyurular"}
      ]}
    ]},
    {group:"Ticari",items:[
      {id:"stock-parent",icon:"&#9638;",label:"Stok Y\u00f6netimi",children:[
        {id:"stock",label:"Stok Listesi"},
        {id:"movements",label:"Stok Hareketleri"},
        {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"}
      ]},
      {id:"sales-parent",icon:"&#9670;",label:"Sat\u0131\u015f ve Teklif",children:[
        {id:"sales",label:"Sales Hub"},
        {id:"service-definitions",label:"Hizmet Tan\u0131mlar\u0131"},
        {id:"brands",label:"Cihaz ve Markalar"},
        {id:"loaners",label:"Emanet ve Konsinye"},
        {id:"mobile-guide",label:"Mobil Teknik K\u0131lavuz"},
        {id:"pc-builder",label:"PC Yap\u0131land\u0131r\u0131c\u0131"}
      ]}
    ]},
    {group:"Finans",items:[
      {id:"finance-parent",icon:"TRY",label:"Finans Y\u00f6netimi",children:[
        {id:"finance",label:"Finans \u00d6zeti"},
        {id:"income",label:"Gelirler"},
        {id:"expense",label:"Giderler"},
        {id:"banks",label:"Banka Hesaplar\u0131"},
        {id:"checks",label:"\u00c7ek ve Senet"},
        {id:"invoices",label:"E-Fatura"}
      ]}
    ]},
    {group:"Proje ve Ekip",items:[
      {id:"project-parent",icon:"&#9635;",label:"Proje ve Ekip",children:[
        {id:"projects",label:"Proje Y\u00f6netimi"},
        {id:"project-archive",label:"Proje Ar\u015fivi"},
        {id:"personnel",label:"Personel Y\u00f6netimi"}
      ]}
    ]},
    {group:"Sistem",items:[
      {id:"settings",icon:"&#9881;",label:"Ayarlar"},
      {id:"knowledge",icon:"&#9638;",label:"Bilgi Bankas\u0131"},
      {id:"backup",icon:"&#9636;",label:"Yedekleme"},
      {id:"support",icon:"?",label:"Destek"},
      {id:"audit",icon:"&#9776;",label:"Log Kay\u0131tlar\u0131"},
      {id:"manual",icon:"&#9638;",label:"Kullan\u0131m K\u0131lavuzu"},
      {id:"dialog-catalog",icon:"&#9635;",label:"Dialog Mod\u00fclleri"},
      {id:"control-center",icon:"#",label:"Y\u00f6netim Merkezi"}
    ]}
  ],
  otomotiv:[
    {group:"Operasyon",items:[
      {id:"dashboard",icon:"&#8962;",label:"Ana Ekran"},
      {id:"automotive-service-parent",icon:"&#9881;",label:"Otomotiv Servisi",children:[
        {id:"services",label:"Servis Paneli"},
        {id:"technician",label:"Teknisyen Paneli"},
        {id:"appointments",label:"Randevular"},
        {id:"vehicle-maintenance",label:"Ara\u00e7 Bak\u0131m Takibi"}
      ]},
      {id:"automotive-stock-parent",icon:"&#9638;",label:"Yedek Par\u00e7a",children:[
        {id:"automotive-stock",label:"Par\u00e7a Stok Listesi"},
        {id:"movements",label:"Stok Hareketleri"},
        {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"}
      ]},
      {id:"assistant",icon:"AI",label:"AI Asistan"}
    ]},
    {group:"M\u00fc\u015fteri",items:[
      {id:"automotive-customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteriler",children:[
        {id:"customers",label:"M\u00fc\u015fteri Hub"},
        {id:"contracts",label:"Bak\u0131m S\u00f6zle\u015fmeleri"},
        {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
        {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
        {id:"announcements",label:"Duyurular"}
      ]}
    ]},
    {group:"Ticari",items:[
      {id:"automotive-trade-parent",icon:"&#9670;",label:"Sat\u0131\u015f ve Tan\u0131mlar",children:[
        {id:"sales",label:"Sat\u0131\u015f ve Teklif"},
        {id:"service-definitions",label:"Servis Tan\u0131mlar\u0131"},
        {id:"brands",label:"Ara\u00e7 ve Marka Bilgileri"},
        {id:"loaners",label:"Emanet ve Konsinye"}
      ]}
    ]},
    {group:"Finans",items:[
      {id:"automotive-finance-parent",icon:"TRY",label:"Finans Y\u00f6netimi",children:[
        {id:"finance",label:"Finans \u00d6zeti"},
        {id:"income",label:"Gelirler"},
        {id:"expense",label:"Giderler"},
        {id:"banks",label:"Banka Hesaplar\u0131"},
        {id:"checks",label:"\u00c7ek ve Senet"},
        {id:"invoices",label:"E-Fatura"}
      ]}
    ]},
    {group:"Ekip",items:[
      {id:"automotive-team-parent",icon:"&#9823;",label:"Ekip Y\u00f6netimi",children:[
        {id:"personnel",label:"Personel Y\u00f6netimi"}
      ]}
    ]},
    {group:"Sistem",items:[
      {id:"settings",icon:"&#9881;",label:"Ayarlar"},
      {id:"knowledge",icon:"&#9638;",label:"Bilgi Bankas\u0131"},
      {id:"backup",icon:"&#9636;",label:"Yedekleme"},
      {id:"support",icon:"?",label:"Destek"},
      {id:"audit",icon:"&#9776;",label:"Log Kay\u0131tlar\u0131"},
      {id:"manual",icon:"&#9638;",label:"Kullan\u0131m K\u0131lavuzu"},
      {id:"dialog-catalog",icon:"&#9635;",label:"Dialog Mod\u00fclleri"},
      {id:"control-center",icon:"#",label:"Y\u00f6netim Merkezi"}
    ]}
  ]
};

ayecSectorMenuModels.teknik_servis=[
  {group:"Operasyon",items:[
    {id:"dashboard",icon:"&#8962;",label:"Genel Bak\u0131\u015f"},
    {id:"service-parent",icon:"&#9881;",label:"Servis Y\u00f6netimi",children:[
      {id:"services",label:"Servis Kay\u0131tlar\u0131"},
      {id:"technician",label:"Teknisyen Paneli"},
      {id:"field-service",label:"Saha Haritas\u0131"},
      {id:"appointments",label:"Randevular"},
      {id:"logistics",label:"Lojistik ve Garanti Y\u00f6netimi"},
      {id:"job-reports",label:"\u0130\u015f ve Servis Takibi Raporlar\u0131"}
    ]},
    {id:"service-settings-parent",icon:"&#9881;",label:"Servis Y\u00f6netim Ayar\u0131",children:[
      {id:"product-groups",label:"\u00dcr\u00fcn Grubu Y\u00f6netimi"},
      {id:"brands",label:"Marka Adlar\u0131 Y\u00f6netimi"},
      {id:"report-templates",label:"Rapor C\u00fcmle Kal\u0131plar\u0131"},
      {id:"service-definitions",label:"\u0130\u015f\u00e7ilik Ekle"}
    ]}
  ]},
  {group:"M\u00fc\u015fteri",items:[
    {id:"customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteri Hub",children:[
      {id:"customers",label:"M\u00fc\u015fteri Listesi"},
      {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
      {id:"contracts",label:"S\u00f6zle\u015fmeler"},
      {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
      {id:"announcements",label:"Duyurular"}
    ]}
  ]},
  {group:"Stok / Sipari\u015f",items:[
    {id:"stock-parent",icon:"&#9638;",label:"Stok / Sipari\u015f",children:[
      {id:"stock",label:"Stok Y\u00f6netimi"},
      {id:"movements",label:"Stok Hareketleri"},
      {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"},
      {id:"loaners",label:"Emanet (Konsinye) Cihazlar"},
      {id:"mobile-guide",label:"Mobil Stok"},
      {id:"pc-builder",label:"PC Builder"}
    ]},
  ]},
  {group:"Teklif Y\u00f6netimi",items:[
    {id:"offer-parent",icon:"&#9670;",label:"Teklif Y\u00f6netimi",children:[
      {id:"sales",label:"Teklif Olu\u015ftur"},
      {id:"offers",label:"T\u00fcm Teklifler"},
      {id:"offer-reports",label:"Teklif Raporlar\u0131"}
    ]}
  ]},
  {group:"Finans",items:[
    {id:"finance-parent",icon:"TRY",label:"Finans",children:[
      {id:"finance",label:"Finans \u00d6zeti"},
      {id:"income",label:"Gelirler"},
      {id:"expense",label:"Giderler"},
      {id:"banks",label:"Banka Hesaplar\u0131"},
      {id:"checks",label:"\u00c7ek ve Senet"},
      {id:"invoices",label:"E-Fatura"}
    ]}
  ]},
  {group:"Proje ve Ekip",items:[
    {id:"project-parent",icon:"&#9635;",label:"Proje Y\u00f6netimi",children:[
      {id:"projects",label:"Proje Y\u00f6netimi"},
      {id:"project-archive",label:"Proje Ar\u015fivi"}
    ]},
    {id:"personnel",icon:"&#9823;",label:"Personel"}
  ]},
  {group:"Sistem",items:[
    {id:"settings",icon:"&#9881;",label:"Sistem Ayarlar\u0131"},
    {id:"knowledge",icon:"&#9638;",label:"Bilgi Bankas\u0131"},
    {id:"backup",icon:"&#9636;",label:"Yedekleme Merkezi"},
    {id:"support",icon:"?",label:"Destek Merkezi"},
    {id:"audit",icon:"&#9776;",label:"Log Kay\u0131tlar\u0131"},
    {id:"manual",icon:"&#9638;",label:"Kullan\u0131m K\u0131lavuzu"},
    {id:"dialog-catalog",icon:"&#9635;",label:"Dialog Mod\u00fclleri"},
    {id:"control-center",icon:"#",label:"Y\u00f6netim Merkezi"}
  ]}
];

ayecSectorMenuModels.otomotiv=[
  {group:"Operasyon",items:[
    {id:"dashboard",icon:"&#8962;",label:"Genel Bak\u0131\u015f"},
    {id:"automotive-service-parent",icon:"&#9881;",label:"Servis Y\u00f6netimi",children:[
      {id:"services",label:"Servis Kay\u0131tlar\u0131"},
      {id:"technician",label:"Teknisyen Paneli"},
      {id:"appointments",label:"Randevular"},
      {id:"vehicle-maintenance",label:"Ara\u00e7 Bak\u0131m Takibi"}
    ]},
    {id:"automotive-settings-parent",icon:"&#9881;",label:"Servis Y\u00f6netim Ayar\u0131",children:[
      {id:"product-groups",label:"Ara\u00e7 / \u00dcr\u00fcn Grubu Y\u00f6netimi"},
      {id:"brands",label:"Ara\u00e7 ve Marka Y\u00f6netimi"},
      {id:"report-templates",label:"Rapor C\u00fcmle Kal\u0131plar\u0131"},
      {id:"service-definitions",label:"\u0130\u015f\u00e7ilik Ekle"}
    ]}
  ]},
  {group:"M\u00fc\u015fteri",items:[
    {id:"automotive-customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteri Hub",children:[
      {id:"customers",label:"M\u00fc\u015fteri Listesi"},
      {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
      {id:"contracts",label:"S\u00f6zle\u015fmeler"},
      {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
      {id:"announcements",label:"Duyurular"}
    ]}
  ]},
  {group:"Stok / Sipari\u015f",items:[
    {id:"automotive-stock-parent",icon:"&#9638;",label:"Stok / Sipari\u015f",children:[
      {id:"automotive-stock",label:"Par\u00e7a Stok Y\u00f6netimi"},
      {id:"movements",label:"Stok Hareketleri"},
      {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"},
      {id:"loaners",label:"Emanet (Konsinye) Cihazlar"}
    ]},
  ]},
  {group:"Teklif Y\u00f6netimi",items:[
    {id:"automotive-offer-parent",icon:"&#9670;",label:"Teklif Y\u00f6netimi",children:[
      {id:"sales",label:"Teklif Olu\u015ftur"},
      {id:"offers",label:"T\u00fcm Teklifler"},
      {id:"offer-reports",label:"Teklif Raporlar\u0131"}
    ]}
  ]},
  {group:"Finans",items:[
    {id:"automotive-finance-parent",icon:"TRY",label:"Finans",children:[
      {id:"finance",label:"Finans \u00d6zeti"},
      {id:"income",label:"Gelirler"},
      {id:"expense",label:"Giderler"},
      {id:"banks",label:"Banka Hesaplar\u0131"},
      {id:"checks",label:"\u00c7ek ve Senet"},
      {id:"invoices",label:"E-Fatura"}
    ]}
  ]},
  {group:"Ekip",items:[{id:"personnel",icon:"&#9823;",label:"Personel"}]},
  {group:"Sistem",items:[
    {id:"settings",icon:"&#9881;",label:"Sistem Ayarlar\u0131"},
    {id:"knowledge",icon:"&#9638;",label:"Bilgi Bankas\u0131"},
    {id:"backup",icon:"&#9636;",label:"Yedekleme Merkezi"},
    {id:"support",icon:"?",label:"Destek Merkezi"},
    {id:"audit",icon:"&#9776;",label:"Log Kay\u0131tlar\u0131"},
    {id:"manual",icon:"&#9638;",label:"Kullan\u0131m K\u0131lavuzu"},
    {id:"dialog-catalog",icon:"&#9635;",label:"Dialog Mod\u00fclleri"},
    {id:"control-center",icon:"#",label:"Y\u00f6netim Merkezi"}
  ]}
];

const ayecDesktopPageIds={
  dashboard:40,services:41,technician:62,"field-service":61,
  appointments:30,logistics:65,"job-reports":201,
  "vehicle-maintenance":210,"service-definitions":140,
  "product-groups":146,brands:145,"report-templates":147,
  customers:21,partners:26,contracts:25,reminders:90,announcements:120,
  stock:50,"automotive-stock":60,loaners:66,"mobile-guide":250,
  "pc-builder":300,sales:150,offers:313,"offer-reports":314,
  finance:101,banks:105,
  checks:106,invoices:115,personnel:10,projects:200,
  "project-archive":202,settings:130,audit:135,knowledge:160,
  backup:180,support:70,manual:261
};

function ayecSectorMenu(sector=currentSector){
  return ayecSectorMenuModels[sector]||ayecSectorMenuModels.teknik_servis;
}

function ayecParseSectorSetting(value){
  try{
    const parsed=JSON.parse(value||"{}")||{};
    if(parsed.teknik_servis||parsed.otomotiv)return parsed;
    return{teknik_servis:{...parsed},otomotiv:{...parsed}};
  }catch{
    return{teknik_servis:{},otomotiv:{}};
  }
}

function ayecAllMenuLabels(){
  return ayecParseSectorSetting(
    desktopInternalSettings.web_menu_labels||
    localStorage.getItem("ayec_menu_labels")||
    "{}"
  );
}

function ayecAllMenuVisibility(){
  return ayecParseSectorSetting(
    desktopInternalSettings.web_menu_visibility||
    localStorage.getItem("ayec_menu_visibility")||
    "{}"
  );
}

menuLabels=function(sector=currentSector){
  return ayecAllMenuLabels()[sector]||{};
};

menuVisibility=function(sector=currentSector){
  return ayecAllMenuVisibility()[sector]||{};
};

labelFor=function(item,sector=currentSector){
  const pageId=ayecDesktopPageIds[item.id];
  const desktopLabel=pageId?String(
    desktopInternalSettings[`menu_label_page_${pageId}`]||""
  ).trim():"";
  return menuLabels(sector)[item.id]||desktopLabel||item.label;
};

menuVisible=function(item,sector=currentSector){
  if(item?.id==="control-center"){
    return canAccessControlCenter();
  }
  const pageId=ayecDesktopPageIds[item.id];
  const desktopKey=pageId?`menu_visible_page_${pageId}`:"";
  const desktopValue=desktopKey?desktopInternalSettings[desktopKey]:undefined;
  const desktopAllows=desktopValue===undefined||
    desktopValue===null||
    String(desktopValue)==="1"||
    String(desktopValue).toLowerCase()==="true";
  return desktopAllows&&menuVisibility(sector)[item.id]!==false;
};

function ayecMenuItems(sector=currentSector){
  return ayecSectorMenu(sector).flatMap(group=>
    group.items.flatMap(item=>[item,...(item.children||[])])
  );
}

function ayecMenuItem(pageId,sector=currentSector){
  return ayecMenuItems(sector).find(item=>item.id===pageId);
}

const AYEC_NAV_OPEN_KEY="ayec_nav_open_parent";

function ayecOpenParent(sector=currentSector){
  try{
    const stored=JSON.parse(localStorage.getItem(AYEC_NAV_OPEN_KEY)||"{}");
    return String(stored[sector]||"");
  }catch{
    return"";
  }
}

function ayecSetOpenParent(button,open){
  const sector=currentSector==="otomotiv"?"otomotiv":"teknik_servis";
  const parentId=String(button.dataset.parent||"").replace(
    /^nav-(teknik_servis|otomotiv)-/,""
  );
  if(!parentId)return;
  let stored={};
  try{stored=JSON.parse(localStorage.getItem(AYEC_NAV_OPEN_KEY)||"{}")||{}}
  catch{stored={}}
  stored[sector]=open?parentId:"";
  localStorage.setItem(AYEC_NAV_OPEN_KEY,JSON.stringify(stored));
}

function ayecParentForPage(pageId,sector=currentSector){
  for(const group of ayecSectorMenu(sector)){
    const parent=group.items.find(item=>
      item.children?.some(child=>child.id===pageId)
    );
    if(parent)return parent.id;
  }
  return"";
}

firstVisiblePage=function(sector=currentSector){
  for(const group of ayecSectorMenu(sector)){
    for(const item of group.items){
      if(!menuVisible(item,sector))continue;
      if(item.children){
        const child=item.children.find(entry=>menuVisible(entry,sector));
        if(child)return child.id;
      }else{
        return item.id;
      }
    }
  }
  return"dashboard";
};

renderNav=function(){
  const sector=currentSector==="otomotiv"?"otomotiv":"teknik_servis";
  const groups=ayecSectorMenu(sector);
  const rememberedParent=ayecOpenParent(sector);
  $("#nav").innerHTML=groups.map(group=>{
    const items=group.items
      .filter(item=>menuVisible(item,sector))
      .map(item=>item.children?{
        ...item,
        children:item.children.filter(child=>menuVisible(child,sector))
      }:item)
      .filter(item=>!item.children||item.children.length);
    if(!items.length)return"";
    return `<div class="nav-group-title">${esc(group.group)}</div>${items.map(item=>{
      const active=item.children?.some(child=>child.id===page);
      const open=Boolean(active||(!active&&rememberedParent===item.id));
      const submenuId=`nav-${sector}-${item.id}`;
      if(item.children){
        return `<button type="button" class="nav-button nav-parent ${open?"open":""}" data-parent="${submenuId}" aria-controls="${submenuId}" aria-expanded="${open?"true":"false"}"><span class="nav-icon">${item.icon||"&#8226;"}</span><span>${esc(labelFor(item,sector))}</span></button><div class="submenu ${open?"open":""}" id="${submenuId}">${item.children.map(child=>`<button type="button" class="nav-button ${child.id===page?"active":""}" data-page="${child.id}"><span class="nav-icon">&#8226;</span><span>${esc(labelFor(child,sector))}</span></button>`).join("")}</div>`;
      }
      return `<button type="button" class="nav-button ${item.id===page?"active":""}" data-page="${item.id}"><span class="nav-icon">${item.icon||"&#8226;"}</span><span>${esc(labelFor(item,sector))}</span></button>`;
    }).join("")}`;
  }).join("");
  if($("#sectorSelect"))$("#sectorSelect").value=sector;
  if($("#sectorBrand")){
    $("#sectorBrand").textContent=sector==="otomotiv"?
      "Otomotiv Servis":
      "Teknik Servis";
  }
  const fixedSettings=$(".sidebar-bottom [data-page='settings']");
  if(fixedSettings)fixedSettings.hidden=!menuVisible({id:"settings"},sector);
};

const ayecNavigateBeforeSectorMenus=navigate;
navigate=function(next){
  const sector=currentSector==="otomotiv"?"otomotiv":"teknik_servis";
  let target=next;
  if(sector==="otomotiv"&&target==="stock")target="automotive-stock";
  if(sector==="teknik_servis"&&target==="automotive-stock")target="stock";
  if(!ayecMenuItem(target,sector)&&target!=="control-center"){
    target=firstVisiblePage(sector);
  }
  const parentId=ayecParentForPage(target,sector);
  if(parentId){
    const button={dataset:{parent:`nav-${sector}-${parentId}`}};
    ayecSetOpenParent(button,true);
  }
  ayecNavigateBeforeSectorMenus(target);
  const configured=ayecMenuItem(target,sector);
  if(configured)$("#pageTitle").textContent=labelFor(configured,sector);
  renderNav();
};

function ayecEditorRow(item,sector,child=false){
  const labels=menuLabels(sector),visibility=menuVisibility(sector);
  const visible=visibility[item.id]!==false;
  const key=`${sector}_${item.id}`;
  return `<label class="sector-menu-row ${child?"child":""} ${visible?"":"menu-disabled"}"><span class="sector-menu-icon">${item.icon||"&#8226;"}</span><span class="sector-menu-copy"><input name="menu_${key}" value="${esc(labels[item.id]||item.label)}" aria-label="${esc(item.label)}"><small>${visible?"Men\u00fc g\u00f6r\u00fcn\u00fcr":"Men\u00fc gizli"}</small></span><input class="switch menu-visibility-toggle" name="visible_${key}" type="checkbox" value="1" ${visible?"checked":""} aria-label="${esc(item.label)}"></label>`;
}

function ayecEditorPanel(sector,title,description){
  return `<section class="sector-menu-panel ${sector===currentSector?"active":""}" data-editor-panel="${sector}"><header><div><span class="sector-menu-badge">${sector==="otomotiv"?"OT":"TS"}</span><div><h3>${title}</h3><p>${description}</p></div></div><span class="badge">${sector===currentSector?"Aktif sekt\u00f6r":"Di\u011fer sekt\u00f6r"}</span></header><div class="sector-menu-groups">${ayecSectorMenu(sector).map((group,index)=>`<details class="sector-menu-group" ${index<2?"open":""}><summary><span>${esc(group.group)}</span><small>${group.items.length} men\u00fc grubu</small></summary><div class="sector-menu-group-body">${group.items.map(item=>item.children?`<div class="sector-menu-parent">${ayecEditorRow(item,sector)}<div class="sector-menu-children">${item.children.map(child=>ayecEditorRow(child,sector,true)).join("")}</div></div>`:ayecEditorRow(item,sector)).join("")}</div></details>`).join("")}</div></section>`;
}

interfaceEditorDialog=function(){
  const sectors=["teknik_servis","otomotiv"];
  const body=`<div class="sector-menu-editor"><div class="sector-menu-intro"><div><strong>Sekt\u00f6re g\u00f6re men\u00fc yap\u0131s\u0131</strong><p>Teknik Servis ve Otomotiv men\u00fcleri birbirinden ba\u011f\u0131ms\u0131zd\u0131r. Bir ana gruba t\u0131klayarak alt men\u00fcleri a\u00e7abilirsiniz.</p></div><div class="sector-editor-tabs" role="tablist"><button type="button" data-editor-sector="teknik_servis" class="${currentSector!=="otomotiv"?"active":""}">Teknik Servis</button><button type="button" data-editor-sector="otomotiv" class="${currentSector==="otomotiv"?"active":""}">Otomotiv</button></div></div><div class="sector-menu-columns">${ayecEditorPanel("teknik_servis","Teknik Servis","Servis, stok, sat\u0131\u015f, proje ve destek men\u00fcleri")}${ayecEditorPanel("otomotiv","Otomotiv Servisi","Ara\u00e7 servisi, bak\u0131m ve yedek par\u00e7a men\u00fcleri")}</div></div>`;
  openDialog(
    "Aray\u00fcz D\u00fczenle",
    "MEN\u00dc YAPILANDIRMA",
    body,
    async fd=>{
      const allLabels=ayecAllMenuLabels();
      const allVisibility=ayecAllMenuVisibility();
      for(const sector of sectors){
        const updated={},visible={};
        for(const item of ayecMenuItems(sector)){
          const key=`${sector}_${item.id}`;
          const value=String(fd.get(`menu_${key}`)||"").trim();
          if(value&&value!==item.label)updated[item.id]=value;
          if(!fd.has(`visible_${key}`))visible[item.id]=false;
        }
        allLabels[sector]=updated;
        allVisibility[sector]=visible;
      }
      const labelsJson=JSON.stringify(allLabels);
      const visibilityJson=JSON.stringify(allVisibility);
      localStorage.setItem("ayec_menu_labels",labelsJson);
      localStorage.setItem("ayec_menu_visibility",visibilityJson);
      desktopInternalSettings.web_menu_labels=labelsJson;
      desktopInternalSettings.web_menu_visibility=visibilityJson;
      await Promise.all([
        desktopWrite("internal_settings",{key:"web_menu_labels",value:labelsJson}),
        desktopWrite("internal_settings",{key:"web_menu_visibility",value:visibilityJson})
      ]);
      if(!menuVisible({id:page},currentSector))page=firstVisiblePage();
      renderNav();
      navigate(page);
      toast("Sekt\u00f6r men\u00fcleri kaydedildi","success");
      return true;
    },
    "Men\u00fcleri Kaydet"
  );
  const editorDialog=$("#appDialog");
  editorDialog.classList.add("sector-menu-editor-dialog");
  editorDialog.addEventListener(
    "close",
    ()=>editorDialog.classList.remove("sector-menu-editor-dialog"),
    {once:true}
  );
  const setEditorSector=sector=>{
    $$("[data-editor-sector]").forEach(button=>
      button.classList.toggle("active",button.dataset.editorSector===sector)
    );
    $$("[data-editor-panel]").forEach(panel=>
      panel.classList.toggle("mobile-active",panel.dataset.editorPanel===sector)
    );
  };
  setEditorSector(currentSector==="otomotiv"?"otomotiv":"teknik_servis");
  $$("[data-editor-sector]").forEach(button=>
    button.onclick=()=>setEditorSector(button.dataset.editorSector)
  );
  $$(".menu-visibility-toggle").forEach(toggle=>{
    toggle.onchange=()=>{
      const row=toggle.closest(".sector-menu-row");
      row.classList.toggle("menu-disabled",!toggle.checked);
      row.querySelector("small").textContent=toggle.checked?
        "Men\u00fc g\u00f6r\u00fcn\u00fcr":
        "Men\u00fc gizli";
    };
  });
  const footer=$("#dialogFooter"),reset=document.createElement("button");
  reset.type="button";
  reset.className="danger";
  reset.textContent="Varsay\u0131lana D\u00f6n";
  reset.onclick=async()=>{
    if(!confirm("Her iki sekt\u00f6r\u00fcn men\u00fc adlar\u0131 ve g\u00f6r\u00fcn\u00fcrl\u00fckleri s\u0131f\u0131rlans\u0131n m\u0131?"))return;
    const defaults=JSON.stringify({teknik_servis:{},otomotiv:{}});
    localStorage.removeItem("ayec_menu_labels");
    localStorage.removeItem("ayec_menu_visibility");
    desktopInternalSettings.web_menu_labels=defaults;
    desktopInternalSettings.web_menu_visibility=defaults;
    await Promise.all([
      desktopWrite("internal_settings",{key:"web_menu_labels",value:defaults}),
      desktopWrite("internal_settings",{key:"web_menu_visibility",value:defaults})
    ]);
    $("#appDialog").close();
    renderNav();
    navigate(firstVisiblePage());
    toast("Men\u00fcler varsay\u0131lan yap\u0131ya d\u00f6nd\u00fc","warning");
  };
  footer.prepend(reset);
};

const ayecSettingBodyBeforeIdentity=settingBody;
settingBody=function(settings){
  if(settingsSection!=="identity")return ayecSettingBodyBeforeIdentity(settings);
  const sector=currentSector==="otomotiv"?"otomotiv":"teknik_servis";
  const sectorLabel=sector==="otomotiv"?"Otomotiv Servis":"Teknik Servis";
  const moduleFields=[
    ["module_operations_active","Operasyon Mod\u00fcl\u00fc","Servis ve i\u015f ak\u0131\u015flar\u0131"],
    ["module_finance_active","Finans Mod\u00fcl\u00fc","Gelir, gider ve tahsilat"],
    ["module_stock_active","Stok Mod\u00fcl\u00fc","Stok ve yedek par\u00e7a"],
    ["module_projects_active","Projeler Mod\u00fcl\u00fc","Proje ve saha i\u015fleri"],
    ["module_crm_active","CRM Mod\u00fcl\u00fc","M\u00fc\u015fteri ve teklif y\u00f6netimi"],
    ["module_personnel_active","Personel Mod\u00fcl\u00fc","Personel ve ekip y\u00f6netimi"]
  ];
  const featureFields=[
    ["feature_right_click_active","Sa\u011f T\u0131k","Sat\u0131r i\u015flem men\u00fcleri"],
    ["feature_double_click_active","\u00c7ift T\u0131klama","Kayd\u0131 ayr\u0131nt\u0131da a\u00e7ma"]
  ];
  const toggle=([key,label,description])=>{
    const value=desktopInternalSettings[key]??"1";
    const checked=String(value)==="1"||String(value)==="true";
    return `<label class="identity-toggle"><span><strong>${label}</strong><small>${description}</small></span><input class="switch exact-setting" data-setting-key="${key}" data-setting-scope="internal_settings" type="checkbox" ${checked?"checked":""}></label>`;
  };
  const selector=currentAuthUser?.is_admin?
    `<div class="sector-identity-action"><select class="control" id="companySectorSelect"><option value="teknik_servis" ${sector==="teknik_servis"?"selected":""}>Teknik Servis</option><option value="otomotiv" ${sector==="otomotiv"?"selected":""}>Otomotiv Servis</option></select><button class="primary" type="button" data-action="save-company-sector">Sekt\u00f6r\u00fc Uygula</button></div>`:
    `<span class="badge">${sectorLabel}</span>`;
  return `<div class="identity-settings"><section class="sector-identity-card"><div><span class="identity-step">1</span><div><h3>Sekt\u00f6rel Kimlik</h3><p>Aktif sekt\u00f6r men\u00fcleri, formlar\u0131 ve stok ekran\u0131n\u0131 belirler. Veri silinmez.</p></div></div>${selector}</section><section class="identity-section"><header><span class="identity-step">2</span><div><h3>Mod\u00fcl Paketleri</h3><p>\u0130\u015fletmenin kullanaca\u011f\u0131 ana mod\u00fclleri y\u00f6netin.</p></div></header><div class="identity-toggle-grid">${moduleFields.map(toggle).join("")}</div></section><section class="identity-section"><header><span class="identity-step">3</span><div><h3>Etkile\u015fim \u00d6zellikleri</h3><p>Fare ve dokunmatik kullan\u0131m davran\u0131\u015flar\u0131.</p></div></header><div class="identity-toggle-grid">${featureFields.map(toggle).join("")}</div></section></div>`;
};

if($("#interfaceEditBtn"))$("#interfaceEditBtn").onclick=interfaceEditorDialog;

// Dashboard parity for desktop, automotive and responsive web clients.
let ayecDashboardQuery="";
let ayecDashboardPage=1;
let ayecDashboardPageSize=10;
let ayecDashboardHydrated=false;
let ayecDashboardRefreshTimer=0;

function ayecDashboardText(value){
  return String(value||"").toLocaleLowerCase("tr-TR");
}

function ayecDashboardId(service){
  return String(service.no||service.tracking_no||service.id||"");
}

function ayecDashboardSource(service){
  const source=String(service.service_source||service.service||"").trim();
  const normalized=source.toLocaleLowerCase("tr-TR").replace(/[ _-]+/g," ");
  const labels={
    "cle maintenance":"Bak\u0131m / Servis",
    "maintenance":"Bak\u0131m / Servis",
    "service":"Servis",
    "automotive":"\u0130\u015f Emri",
    "web automotive":"Web Otomotiv",
    "web teknik servis":"Web Teknik Servis"
  };
  return labels[normalized]||source||"Servis";
}

function ayecDashboardDelivery(service){
  const value=service.exit_date||service.delivery||service.estimated_date||"";
  return value?String(value).slice(0,10):"Teslim Edilmedi";
}

function ayecDashboardPlainStatus(service){
  const key=serviceStatusKey(service);
  return {
    bekliyor:"S\u0131raya Al\u0131nacak",
    tamirde:"Serviste",
    test:"Kontrol Tamamland\u0131",
    teslim:"Teslim Edildi",
    parca:"Par\u00e7a Bekliyor",
    kargo:"D\u0131\u015f Serviste",
    iptal:"\u0130ptal / \u0130ade"
  }[key]||String(service.status||"Bekliyor");
}

function ayecDashboardStatus(service){
  return ayecDashboardText([
    service.status,service.approval_status,service.payment_status,
    service.service_source,service.external_status,service.notes
  ].join(" "));
}

function ayecDashboardMatches(service,filter){
  const status=ayecDashboardStatus(service);
  if(filter==="all")return true;
  if(filter==="appointment")return String(service.date||service.entry_date||"").slice(0,10)===today()||db.appointments.some(item=>String(item.customerId)===String(service.customerId)&&item.date===today());
  if(filter==="approval")return /onay|approval|bekle/.test(status);
  if(filter==="test")return /test|kontrol/.test(status)||serviceStatusKey(service)==="test";
  if(filter==="waiting")return serviceStatusKey(service)==="bekliyor";
  if(filter==="active")return serviceStatusKey(service)==="tamirde";
  if(filter==="lodging")return /konak|overnight/.test(status);
  if(filter==="maintenance_due")return /bak.m.*yakla|maintenance.*due/.test(status);
  if(filter==="maintenance_overdue")return /bak.m.*ge.|maintenance.*over/.test(status);
  if(filter==="dispatch")return /irsaliye|dispatch/.test(status);
  if(filter==="invoiced")return Boolean(service.is_invoiced)||/fatura.*kesildi|invoiced/.test(status);
  if(filter==="uninvoiced")return service.is_invoiced===false||/fatura.*kesilmedi|uninvoiced/.test(status);
  if(filter==="no_invoice")return /faturas.z|no.invoice/.test(status);
  if(filter==="cargo")return serviceStatusKey(service)==="kargo"||/kargo.*bekle/.test(status);
  if(filter==="outbound")return /onar.ma.*giden|d.s.servis|outbound/.test(status);
  if(filter==="inbound")return /onar.mdan.*gelen|servisten.*gelen|inbound/.test(status);
  if(filter==="done")return serviceStatusKey(service)==="teslim";
  if(filter==="part")return serviceStatusKey(service)==="parca";
  if(filter==="debt")return serviceIsDebt(service);
  if(filter==="cancelled")return serviceStatusKey(service)==="iptal";
  return true;
}

function ayecDashboardToolbar(total){
  return `<div class="dashboard-toolbar"><div class="dashboard-toolbar-actions"><button class="primary" type="button" data-action="new-service">+ ${currentSector==="otomotiv"?"Ara\u00e7 Kayd\u0131":"Servis Kayd\u0131"}</button><button class="secondary" type="button" data-dashboard-filter="all">${currentSector==="otomotiv"?"T\u00fcm Ara\u00e7lar":"T\u00fcm Servisler"}</button></div><label class="dashboard-search"><span>ARA</span><input id="dashboardSearch" type="search" value="${esc(ayecDashboardQuery)}" placeholder="${currentSector==="otomotiv"?"Plaka, m\u00fc\u015fteri veya ara\u00e7 ara...":"Takip no, m\u00fc\u015fteri veya cihaz ara..."}" autocomplete="off"></label><label class="dashboard-page-size"><span>Kay\u0131t</span><select id="dashboardPageSize">${[10,25,50].map(size=>`<option value="${size}" ${size===ayecDashboardPageSize?"selected":""}>${size}</option>`).join("")}</select></label><span class="badge">${total} kay\u0131t</span></div>`;
}

function ayecDashboardTable(rows,total){
  const automotive=currentSector==="otomotiv";
  if(!total)return empty(automotive?"Bu filtrede ara\u00e7 bulunmuyor.":"Bu filtrede cihaz bulunmuyor.","Filtreyi temizleyebilir veya yeni bir servis kayd\u0131 olu\u015fturabilirsiniz.");
  const pageCount=Math.max(1,Math.ceil(total/ayecDashboardPageSize));
  ayecDashboardPage=Math.min(Math.max(1,ayecDashboardPage),pageCount);
  const start=(ayecDashboardPage-1)*ayecDashboardPageSize;
  const visible=rows.slice(start,start+ayecDashboardPageSize);
  const body=visible.map(service=>{
    const id=ayecDashboardId(service),customer=service.customer||service.customer_name||"-";
    const type=automotive?(service.vehicle_type||"Ara\u00e7"):(service.device_type||service.device||"Cihaz");
    const entry=service.date||service.entry_date||"-",delivery=ayecDashboardDelivery(service);
    const amount=moneyNumber(service.amount||service.price||service.labor_cost||0);
    const status=automotive?ayecDashboardPlainStatus(service):String(service.status||"Bekliyor");
    const priority=String(service.priority||service.urgency||"Normal");
    return `<tr data-kind="service" data-id="${esc(id)}" data-customer="${esc(service.customerId||service.customer_id||"")}"><td><strong>${esc(id||"-")}</strong></td><td><div class="dashboard-row-actions"><button class="mini" data-action="service-detail" data-id="${esc(id)}" title="Servis ayr\u0131nt\u0131s\u0131">i</button><button class="mini" data-action="technician-open" data-id="${esc(id)}" title="Teknisyen i\u015flemi">*</button></div></td><td>${esc(customer)}</td><td>${esc(type)}</td><td>${esc(service.brand||"-")}</td><td>${esc(service.model||service.device||"-")}</td><td>${esc(String(entry).slice(0,10))}</td><td>${esc(delivery)}</td><td>${esc(ayecDashboardSource(service))}</td><td><strong>${money(amount,service.currency||"TRY")}</strong></td><td><span class="dashboard-plain-status">${esc(status)}</span></td><td><span class="dashboard-plain-status">${esc(priority)}</span></td></tr>`;
  }).join("");
  const recordStart=total?start+1:0,recordEnd=Math.min(start+visible.length,total);
  return `<div class="table-wrap dashboard-service-table"><table><thead><tr><th>${automotive?"\u0130\u015e EMR\u0130 NO":"TAK\u0130P NO"}</th><th>\u0130\u015eLEMLER</th><th>M\u00dc\u015eTER\u0130</th><th>${automotive?"ARA\u00c7 T\u00dcR\u00dc":"\u00dcR\u00dcN GRUBU"}</th><th>MARKA</th><th>MODEL</th><th>ALI\u015e TAR\u0130H\u0130</th><th>${automotive?"TESL\u0130M DURUMU":"TESL\u0130M TAR\u0130H\u0130"}</th><th>SERV\u0130S</th><th>\u00dcCRET</th><th>DURUM</th><th>${automotive?"\u00d6NCEL\u0130K":"AC\u0130L\u0130YET"}</th></tr></thead><tbody>${body}</tbody></table></div><div class="dashboard-pagination"><span>${total} kay\u0131ttan ${recordStart}-${recordEnd} aras\u0131 g\u00f6steriliyor.</span><div><button class="secondary" type="button" data-dashboard-page="prev" ${ayecDashboardPage<=1?"disabled":""}>&lt; \u00d6nceki</button><b>${ayecDashboardPage} / ${pageCount}</b><button class="secondary" type="button" data-dashboard-page="next" ${ayecDashboardPage>=pageCount?"disabled":""}>Sonraki &gt;</button></div></div>`;
}

renderDashboard=function(){
  const automotive=currentSector==="otomotiv",services=dashboardServices();
  const tileDefs=automotive?[
    ["test","KONTROL\u00dc TAMAMLANAN","Kontrol Tamamland\u0131","K","#05A85B"],
    ["active","SERV\u0130STEK\u0130 ARA\u00c7LAR","\u0130\u015f Emri Devam Ediyor","S","#F39C12"],
    ["waiting","SIRAYA ALINACAKLAR","Servise Al\u0131nmad\u0131","A","#1E88E5"],
    ["cancelled","\u0130PTAL / \u0130ADE","\u0130ptal veya \u0130ade","X","#E24A3B"],
    ["cargo","DI\u015e SERV\u0130SE G\u0130DENLER","D\u0131\u015f Servise Verildi","D","#D41462"],
    ["done","TESL\u0130M ED\u0130LEN ARA\u00c7LAR","Teslim Edildi","T","#0891B2"],
    ["part","PAR\u00c7A BEKLEYEN ARA\u00c7","Par\u00e7a Bekliyor","P","#0E7AB4"],
    ["debt","BOR\u00c7LU ARA\u00c7LAR","Borcu Var","B","#625DA8"]
  ]:[
    ["test","TAM\u0130R ED\u0130LENLER","Tamir Edildi","T","#05A85B"],
    ["active","TAM\u0130RDE OLANLAR","Tamiri Devam Etmekte","D","#F39C12"],
    ["waiting","\u0130\u015eLEME ALINACAKLAR","\u0130\u015fleme Al\u0131nmad\u0131","I","#1E88E5"],
    ["cancelled","\u0130PTAL / \u0130ADE","\u0130ptal veya \u0130ade","X","#E24A3B"],
    ["cargo","KARGOYA VER\u0130LENLER","Kargoya Verildi","K","#D41462"],
    ["done","TESL\u0130M ED\u0130LENLER","Teslim Edildi","E","#0891B2"],
    ["part","PAR\u00c7A BEKLEYENLER","Par\u00e7a Bekliyor","P","#0E7AB4"],
    ["debt","BOR\u00c7LU OLANLAR","Borcu Var","B","#625DA8"]
  ];
  const countFor=filter=>services.filter(service=>ayecDashboardMatches(service,filter)).length;
  const percent=count=>services.length?Math.round(count/services.length*100):0;
  const tiles=tileDefs.map(([filter,title,subtitle,icon,color])=>{const count=countFor(filter);return `<button class="service-status-card" data-dashboard-filter="${filter}" style="--tile:${color}"><span class="service-status-icon">${icon}</span><span><small>${title}</small><strong>${count} ADET</strong><em>${percent(count)}% ${subtitle}</em></span><b>${percent(count)}%</b></button>`}).join("");
  const filters=automotive?[
    ["add_device","Ara\u00e7 Kayd\u0131","+"],["all","T\u00fcm Ara\u00e7lar","="],["appointment","Randevulu","R"],["approval","Onay Bekleyen","OK"],["test","Kontrol S\u00fcrecinde","O"],["waiting","Servise Al\u0131nacak",">"],["lodging","Konaklamal\u0131","Y"],["maintenance_due","Bak\u0131m\u0131 Yakla\u015fan","M"],["maintenance_overdue","Bak\u0131m\u0131 Ge\u00e7en","!"],["dispatch","E-\u0130rsaliye","D"],["invoiced","Faturas\u0131 Kesilen","F+"],["uninvoiced","Faturas\u0131 Kesilmeyen","F-"],["no_invoice","Faturas\u0131z \u0130\u015flemler","N"],["cargo","D\u0131\u015f Servis Bekleyen","K"],["outbound","Onar\u0131ma Giden",">"],["inbound","Onar\u0131mdan Gelen","<"]
  ]:[
    ["add_device","Servis Kayd\u0131","+"],["all","T\u00fcm Servisler","="],["appointment","Randevulu","R"],["approval","Onay Bekleyen","OK"],["test","Test S\u00fcrecinde","O"],["waiting","\u0130\u015fleme Al\u0131nacak",">"],["lodging","Konaklamal\u0131","Y"],["maintenance_due","Bak\u0131m\u0131 Yakla\u015fan","M"],["maintenance_overdue","Bak\u0131m\u0131 Ge\u00e7en","!"],["dispatch","E-\u0130rsaliye","D"],["invoiced","Faturas\u0131 Kesilen","F+"],["uninvoiced","Faturas\u0131 Kesilmeyen","F-"],["no_invoice","Faturas\u0131z \u0130\u015flemler","N"],["cargo","Kargosu Beklenen","K"],["outbound","Onar\u0131ma Giden",">"],["inbound","Onar\u0131mdan Gelen","<"]
  ];
  const filterButtons=filters.map(([filter,label,icon])=>`<button class="dashboard-filter ${ayecDashboardFilter===filter?"active":""}" data-dashboard-filter="${filter}"><b>${icon}</b><span>${label}</span></button>`).join("");
  const query=ayecDashboardText(ayecDashboardQuery);
  const filtered=services.filter(service=>ayecDashboardMatches(service,ayecDashboardFilter)).filter(service=>!query||ayecDashboardText([ayecDashboardId(service),service.customer,service.customer_name,service.device_type,service.vehicle_type,service.brand,service.model,service.status].join(" ")).includes(query));
  const title=automotive?"Ara\u00e7 Servis Listesi":"Servis Listesi";
  return `${pageHead("Genel Bak\u0131\u015f",automotive?"Otomotiv servis durumlar\u0131n\u0131 ve i\u015f emirlerini canl\u0131 izleyin.":"Servis durumlar\u0131n\u0131 ve h\u0131zl\u0131 i\u015flemleri canl\u0131 izleyin.",'<button class="primary" data-action="new-service">+ Yeni Servis</button>')}<div class="service-status-grid">${tiles}</div><section class="dashboard-filter-strip">${filterButtons}</section><section class="card dashboard-list-card"><div class="card-head"><h3>${title}</h3><button class="secondary" type="button" data-dashboard-refresh>Yenile</button></div>${ayecDashboardToolbar(filtered.length)}${ayecDashboardTable(filtered,filtered.length)}</section><nav class="dashboard-mobile-nav" aria-label="Mobil servis gezintisi"><button type="button" data-dashboard-page="prev">Geri</button><button type="button" data-dashboard-search>Ara</button><button class="active" type="button" data-dashboard-filter="all">\u0130\u015flemler</button><span>${ayecDashboardPageSize}</span><button type="button" data-dashboard-page="next">\u0130leri</button></nav>`;
};

let ayecDashboardFilter="all";

const ayecHydrateBeforeDashboard=hydrateDesktop;
hydrateDesktop=async function(quiet=true){
  const source=await ayecHydrateBeforeDashboard(quiet);
  ayecDashboardHydrated=true;
  return source;
};

const ayecNavigateBeforeDashboard=navigate;
navigate=function(next){
  ayecNavigateBeforeDashboard(next);
  if(next!=="dashboard"||!ayecDashboardHydrated)return;
  clearTimeout(ayecDashboardRefreshTimer);
  ayecDashboardRefreshTimer=setTimeout(async()=>{
    const host=$("#content");
    if(host)host.classList.add("dashboard-refreshing");
    try{await hydrateDesktop(true)}catch(error){/* The shared toast reports the error. */}
    finally{if($("#content"))$("#content").classList.remove("dashboard-refreshing")}
  },0);
};

const ayecBindPageBeforeDashboard=bindPage;
bindPage=function(...args){
  const result=ayecBindPageBeforeDashboard(...args);
  const search=$("#dashboardSearch");
  if(search)search.oninput=()=>{ayecDashboardQuery=search.value;ayecDashboardPage=1;render();setTimeout(()=>{const current=$("#dashboardSearch");if(current){current.focus();current.setSelectionRange(current.value.length,current.value.length)}},0)};
  const size=$("#dashboardPageSize");
  if(size)size.onchange=()=>{ayecDashboardPageSize=Number(size.value)||10;ayecDashboardPage=1;render()};
  return result;
};

document.addEventListener("click",event=>{
  const filter=event.target.closest("[data-dashboard-filter]");
  if(filter&&filter.dataset.dashboardFilter!=="add_device"){ayecDashboardFilter=filter.dataset.dashboardFilter||"all";ayecDashboardPage=1}
  const pageButton=event.target.closest("[data-dashboard-page]");
  if(pageButton&&!pageButton.disabled){event.preventDefault();ayecDashboardPage=Math.max(1,ayecDashboardPage+(pageButton.dataset.dashboardPage==="next"?1:-1));render()}
  const searchButton=event.target.closest("[data-dashboard-search]");
  if(searchButton){event.preventDefault();$("#dashboardSearch")?.focus()}
  const refreshButton=event.target.closest("[data-dashboard-refresh]");
  if(refreshButton){event.preventDefault();hydrateDesktop(false).catch(()=>{})}
},true);

// Keep the stock list cost column aligned with the inventory valuation cards.
const ayecStockTableBase=stockTable;
stockTable=function(rows){
  return ayecStockTableBase(rows);
};

// Stock profitability and finance controls shared by desktop web and mobile.
function ayecPotentialProfitTry(){
  return db.stock.reduce((total,product)=>{
    const quantity=Math.max(0,Number(product.qty||0));
    const margin=Math.max(0,Number(product.sell||0)-Number(product.buy||0));
    const rate=rateForCode(product.currency||"TRY");
    return total+(quantity*margin*(rate>0?rate:0));
  },0);
}

function ayecPotentialProfitCard(){
  return metric(
    "Potansiyel Kazan\u00e7",
    money(ayecPotentialProfitTry(),"TRY"),
    "Mevcut stok sat\u0131l\u0131rsa tahmini br\u00fct kazan\u00e7",
    "P"
  );
}

const ayecRenderStockBeforeProfit=renderStock;
renderStock=function(){
  return ayecRenderStockBeforeProfit().replace(
    '<div class="metric-grid">',
    `<div class="metric-grid">${ayecPotentialProfitCard()}`
  );
};

const ayecRenderMovementsBeforeProfit=renderMovements;
renderMovements=function(){
  return ayecRenderMovementsBeforeProfit().replace(
    '<section class="card">',
    `<div class="metric-grid stock-movement-metrics">${ayecPotentialProfitCard()}</div><section class="card">`
  );
};

function ayecOpenFiscalControls(){
  const year=new Date().getFullYear();
  openDialog(
    "Mali Y\u0131l Kontrolleri",
    `AKT\u0130F D\u00d6NEM ${year}`,
    `<div class="fiscal-control-grid"><button type="button" class="secondary" id="ayecFiscalArchive">Ar\u015fiv (Ge\u00e7mi\u015f)</button><button type="button" class="secondary" id="ayecFiscalCurrent">Canl\u0131 (${year})</button><button type="button" class="primary" id="ayecFiscalRefresh">Yenile</button><button type="button" class="secondary" id="ayecFiscalOpening">A\u00e7\u0131l\u0131\u015f Fi\u015fleri</button><button type="button" class="primary" id="ayecFiscalReport">Y\u0131lba\u015f\u0131 Raporu</button></div>`,
    ()=>true,
    "Kapat"
  );
  const downloadRows=rows=>download(`finans-${year}.csv`,csv(rows));
  $("#ayecFiscalArchive").onclick=()=>downloadRows(db.finance);
  $("#ayecFiscalCurrent").onclick=()=>$("#appDialog").close();
  $("#ayecFiscalRefresh").onclick=()=>hydrateDesktop(false).then(()=>$("#appDialog").close()).catch(()=>{});
  $("#ayecFiscalOpening").onclick=()=>downloadRows(db.finance.filter(item=>String(item.category||"").toLocaleLowerCase("tr-TR").includes("a\u00e7\u0131l\u0131\u015f")));
  $("#ayecFiscalReport").onclick=()=>downloadRows(db.finance.filter(item=>String(item.date||"").startsWith(String(year))));
}

const ayecRenderFinanceBeforeControls=renderFinance;
renderFinance=function(filter=""){
  const quickActions=`<section class="finance-command-bar"><div><small>H\u0131zl\u0131 \u0130\u015flemler</small><div class="actions"><button class="success" data-action="add-income">+ Gelir Ekle</button><button class="danger" data-action="add-expense">+ Gider Ekle</button><button class="secondary" data-action="export-finance">D\u0131\u015fa Aktar</button></div></div><button class="primary fiscal-launch" type="button" data-finance-fiscal>Mali Y\u0131l Kontrolleri</button></section>`;
  return ayecRenderFinanceBeforeControls(filter).replace(
    '<div class="metric-grid">',
    `${quickActions}<div class="metric-grid finance-summary-grid">`
  );
};

function ayecFinanceExportRows(){
  return db.finance.map(item=>({
    "Tarih":item.date||item.created_at||"",
    "T\u00fcr":item.type||"",
    "Kategori":item.category||"",
    "A\u00e7\u0131klama":item.description||"",
    "M\u00fc\u015fteri":item.customer||item.customer_name||"",
    "Orijinal Tutar":moneyNumber(item.original_amount??item.amount),
    "Para Birimi":String(item.currency||"TRY").toUpperCase(),
    "D\u00f6viz Kuru":moneyNumber(item.exchange_rate??1),
    "TRY Kar\u015f\u0131l\u0131\u011f\u0131":financeTryValue(item),
    "\u00d6deme Y\u00f6ntemi":item.payment_method||"",
    "Referans":item.ref_no||item.tracking_no||""
  }));
}

function ayecStockExportRows(){
  return db.stock.map(item=>{
    const currency=String(item.currency||"TRY").toUpperCase();
    const rate=rateForCode(currency)||1;
    const quantity=moneyNumber(item.qty);
    const purchase=moneyNumber(item.buy);
    const sale=moneyNumber(item.sell);
    return {
      "Stok Kodu":item.code||"",
      "Barkod":item.barcode||"",
      "\u00dcr\u00fcn":item.name||"",
      "Kategori":item.category||"",
      "Stok":quantity,
      "Minimum Stok":moneyNumber(item.min),
      "Para Birimi":currency,
      "Kur":rate,
      "Al\u0131\u015f Fiyat\u0131":purchase,
      "Sat\u0131\u015f Fiyat\u0131":sale,
      "Al\u0131\u015f TRY":purchase*rate,
      "Sat\u0131\u015f TRY":sale*rate,
      "Stok De\u011feri Orijinal":quantity*purchase,
      "Stok De\u011feri TRY":quantity*purchase*rate
    };
  });
}

document.addEventListener("click",event=>{
  const button=event.target.closest('[data-action="export-finance"],[data-action="export-stock"]');
  if(!button)return;
  event.preventDefault();
  event.stopImmediatePropagation();
  const finance=button.dataset.action==="export-finance";
  const rows=finance?ayecFinanceExportRows():ayecStockExportRows();
  download(`${finance?"finans":"stok"}-${today()}.csv`,csv(rows));
  toast(finance?"Finans kay\u0131tlar\u0131 para birimi, kur ve TRY kar\u015f\u0131l\u0131\u011f\u0131yla aktar\u0131ld\u0131":"Stok kay\u0131tlar\u0131 orijinal para birimi ve TRY kar\u015f\u0131l\u0131\u011f\u0131yla aktar\u0131ld\u0131","success");
},true);

document.addEventListener("click",event=>{
  if(event.target.closest("[data-finance-fiscal]")){
    event.preventDefault();
    ayecOpenFiscalControls();
  }
},true);
