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
  settings:{theme:"midnight",compact:false,doubleClick:true,contextMenu:true,appointmentAlerts:true,alertMinutes:30,company:"AYEC Pro Teknik Servis",currency:"TRY"},
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
  {group:"SERVIS OPERASYON",items:[{id:"service-parent",icon:"\u{1f527}",label:"Servis Y\u00f6netimi",children:[{id:"dashboard",label:"Genel Bak\u0131ş"},{id:"services",label:"Servis Panosu"},{id:"service-status",label:"Durum Paneli"},{id:"technician",label:"Teknisyen Paneli"},{id:"field-service",label:"Saha Haritas\u0131"},{id:"appointments",label:"Randevular"},{id:"logistics",label:"Lojistik & Garanti Y\u00f6netimi"},{id:"job-reports",label:"\u0130\u015f / Servis Takibi Raporlar\u0131"},{id:"assistant",label:"AI Asistan"},{id:"vehicle-maintenance",label:"Ara\u00e7 Bak\u0131m Takibi"}]},{id:"service-settings-parent",icon:"\u2699",label:"Servis Ayarlar\u0131",children:[{id:"service-definitions",label:"\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi"},{id:"brands",label:"Marka Adlar\u0131 Y\u00f6netimi"}]},{id:"customer-parent",icon:"\u{1f465}",label:"M\u00fc\u015fteri Hub",children:[{id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},{id:"customers",label:"M\u00fc\u015fteri Listesi"},{id:"contracts",label:"S\u00f6zle\u015fmeler"},{id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},{id:"announcements",label:"Duyurular"}]}]},
  {group:"TICARI & SATI\u015e",items:[{id:"projects-parent",icon:"\u{1f4ca}",label:"Proje Y\u00f6netimi",children:[{id:"projects",label:"Projeler"},{id:"project-archive",label:"Proje Ar\u015fivi"}]},{id:"stock-parent",icon:"\u{1f4e6}",label:"Stok / Sipari\u015f",children:[{id:"stock",label:"Stok Y\u00f6netimi"},{id:"loaners",label:"Emanet (Konsinye) Cihazlar"},{id:"stock-locations",label:"Depo ve Ara\u00e7 Stoklar\u0131"},{id:"automotive-stock",label:"Ara\u00e7 Par\u00e7a Sto\u011fu"},{id:"movements",label:"Stok Hareketleri"},{id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"},{id:"mobile-guide",label:"Mobil Teknik K\u0131lavuz"},{id:"pc-builder",label:"PC Builder"}]},{id:"offers-parent",icon:"\u{1f4c4}",label:"Teklif Olu\u015ftur",children:[{id:"sales",label:"T\u00fcm Teklifler & Ge\u00e7mi\u015f"}]}]},
  {group:"FINANS & MUHASEBE",items:[{id:"finance-parent",icon:"\u{1f4b5}",label:"Finansal Y\u00f6netim",children:[{id:"finance",label:"Finansal Dashboard"},{id:"income",label:"Gelir / Gider"},{id:"expense",label:"Giderler"},{id:"banks",label:"Banka Hesaplar\u0131"},{id:"checks",label:"\u00c7ek / Senet"},{id:"invoices",label:"Fatura Kes (E-Fatura)"}]}]},
  {group:"Y\u00d6NET\u0130M",items:[{id:"management-parent",icon:"\u{1f464}",label:"Personel",children:[{id:"personnel",label:"Personel"}]}]},
  {group:"S\u0130STEM",items:[{id:"system-parent",icon:"\u2699",label:"Sistem Yard\u0131mc\u0131lar\u0131",children:[{id:"knowledge",label:"Bilgi Bankas\u0131"},{id:"settings",label:"Sistem Ayarlar\u0131"},{id:"backup",label:"Yedekleme Merkezi"},{id:"support",label:"Destek Merkezi"},{id:"audit",label:"Sistem \u0130\u015flem Loglar\u0131"},{id:"manual",label:"Kullan\u0131m K\u0131lavuzu"},{id:"dialog-catalog",label:"Dialog Mod\u00fclleri"}]}]}
];
const sectorPages={teknik_servis:new Set(["dashboard","services","service-list","service-status","product-groups","report-templates","offers","offer-reports","technician","field-service","appointments","logistics","job-reports","assistant","customers","contracts","partners","reminders","announcements","stock-parent","stock","stock-locations","movements","import","service-definitions","brands","loaners","sales","mobile-guide","pc-builder","finance-parent","finance","income","expense","banks","loans","checks","invoices","personnel","projects","project-archive","knowledge","settings","backup","support","audit","manual","dialog-catalog"]),otomotiv:new Set(["dashboard","services","service-list","service-status","product-groups","report-templates","offers","offer-reports","sales","technician","automotive-stock","appointments","vehicle-maintenance","assistant","customers","contracts","partners","reminders","announcements","stock-parent","stock","stock-locations","movements","import","service-definitions","brands","loaners","finance-parent","finance","income","expense","banks","loans","checks","invoices","personnel","knowledge","settings","backup","support","audit","manual","dialog-catalog"])};
function renderNav(){
 const allowed=sectorPages[currentSector]||sectorPages.teknik_servis;
 $("#nav").innerHTML=menu.map(group=>{
  const items=group.items.map(item=>item.children?{...item,children:item.children.filter(child=>allowed.has(child.id))}:item).filter(item=>item.children?item.children.length>0:allowed.has(item.id));
  const html=items.map(item=>item.children?'<button class="nav-button nav-parent" data-parent="'+item.id+'"><span>'+item.icon+'</span><span>'+item.label+'</span></button><div class="submenu" id="'+item.id+'">'+item.children.map(child=>'<button class="nav-button" data-page="'+child.id+'"><span>.</span><span>'+child.label+'</span></button>').join("")+'</div>':'<button class="nav-button" data-page="'+item.id+'"><span>'+item.icon+'</span><span>'+item.label+'</span></button>').join("");
  return items.length?'<div class="nav-group-title">'+group.group+'</div>'+html:"";
 }).join("");
 if($("#sectorSelect"))$("#sectorSelect").value=currentSector;
 if($("#sectorBrand"))$("#sectorBrand").textContent=currentSector==="otomotiv"?"Otomotiv Servis":"Teknik Servis";
}
const titles={dashboard:["Servis Y\u00f6netimi","Genel Bak\u0131\u015f"],customers:["M\u00fc\u015fteri","M\u00fc\u015fteri Listesi"],appointments:["Servis Y\u00f6netimi","Randevular"],stock:["Ticari","Stok Y\u00f6netimi"],"stock-locations":["Ticari","Depo ve Ara\u00e7 Stoklar\u0131"],movements:["Ticari","Stok Hareketleri"],import:["Ticari","Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"],sales:["Ticari","Sat\u0131\u015f"],services:["Servis Y\u00f6netimi","Servis Panosu"],"service-status":["Servis Y\u00f6netimi","Durum Paneli"],technician:["Servis Y\u00f6netimi","Teknisyen Paneli"],finance:["Finans","Gelir / Gider Takibi"],income:["Finans","Gelirler"],expense:["Finans","Giderler"],loans:["Finans","Krediler & Taksitler"],settings:["Sistem","Sistem Ayarlar\u0131"]};
const genericModules={
 "product-groups":{group:"Servis Y\u00f6netim Ayar\u0131",title:"\u00dcr\u00fcn Grubu Y\u00f6netimi",table:"product_groups",description:"Servis ve stok ekranlar\u0131nda kullan\u0131lan \u00fcr\u00fcn gruplar\u0131."},
 "report-templates":{group:"Servis Y\u00f6netim Ayar\u0131",title:"Rapor C\u00fcmle Kal\u0131plar\u0131",table:"fast_notes",description:"Servis raporlar\u0131nda kullan\u0131lan haz\u0131r metinler."},
 offers:{group:"Teklif Y\u00f6netimi",title:"T\u00fcm Teklifler",table:"offers",description:"M\u00fc\u015fterilere verilen teklifler ve onay durumlar\u0131."},
 "offer-reports":{group:"Teklif Y\u00f6netimi",title:"Teklif Raporlar\u0131",table:"offers",description:"Teklif tutarlar\u0131, onay durumlar\u0131 ve performans raporlar\u0131."},
 "automotive-stock":{group:"Servis Yönetimi",title:"Araç Parça Stoğu",table:"parts",description:"Otomotiv servisleri için parça stoğu ve kritik seviyeler."},
 "service-status":{group:"Servis Yönetimi",title:"Durum Paneli",table:"devices",description:"Servis iş emirlerinin durum ve teslim akışı."},
 "field-service":{group:"Servis Yönetimi",title:"Saha Servis Haritası",table:"appointments",description:"Saha operasyonları, personel konumları ve servis planları."},
 logistics:{group:"Servis Yönetimi",title:"Lojistik & Garanti Yönetimi",table:"logistics",description:"Kargo, dış servis ve garanti gönderileri."},
 "job-reports":{group:"Servis Yönetimi",title:"İş / Servis Takibi Raporları",table:"devices",description:"Servis kayıtlarının durum ve performans raporları."},
 "vehicle-maintenance":{group:"Servis Yönetimi",title:"Araç Bakım Takibi",table:"vehicle_maintenance_cards",description:"Araç bakım kartları ve yaklaşan bakım planları."},
 "service-definitions":{group:"Servis Y\u00f6netim Ayar\u0131",title:"Hizmet ve \u00dccret Y\u00f6netimi",table:"services",description:"Standart i\u015f\u00e7ilik tarifeleri, kategori, s\u00fcre ve para birimi baz\u0131ndaki fiyat tan\u0131mlar\u0131."},
 brands:{group:"Ticari",title:"Cihaz Bilgisi & Markalar",table:"device_brands",description:"Servis kabulünde kullanılan cihaz türleri ve markalar."},
 loaners:{group:"Ticari",title:"Emanet Konsinye Cihazlar",table:"loaner_devices",description:"Emanet cihaz ve teslim hareketleri."},
 banks:{group:"Finans",title:"Banka Hesapları",table:"bank_accounts",description:"Banka hesapları, kartlar ve bakiye hareketleri."},
 loans:{group:"Finans",title:"Krediler & Taksitler",table:"loans",description:"Kredi s\u00f6zle\u015fmeleri, kalan bor\u00e7 ve taksit durumlar\u0131."},
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
function renderOffersReference(){const offers=Array.isArray(db.quotes)?db.quotes:[],total=offers.length,pending=offers.filter(item=>/bekle|taslak|gonder|teklif/i.test(String(item.status||""))).length,accepted=offers.filter(item=>/onay|kabul/i.test(String(item.status||""))).length,rejected=offers.filter(item=>/red|iptal/i.test(String(item.status||""))).length,volume=offers.reduce((sum,item)=>sum+Number(item.total_try??item.total??0),0);return `${pageHead("Teklif Y\u00f6netimi","M\u00fc\u015fteri tekliflerini, onay durumlar\u0131n\u0131 ve d\u00f6viz bazl\u0131 kay\u0131tlar\u0131 izleyin.",'<button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-page="sales">+ Teklif Olu\u015ftur</button>')}<div class="metric-grid offers-reference-metrics">${metric("T\u00fcm Teklifler",total,"Toplam kay\u0131t","\u25a3")}${metric("Onay Bekliyor",pending,"\u0130nceleme s\u0131ras\u0131nda","\u25f7")}${metric("Onayland\u0131",accepted,"Kabul edilen","\u2713")}${metric("Red / Taslak",rejected,"Reddedilen veya iptal","\u2298")}${metric("Teklif Hacmi",money(volume,"TRY"),"TRY kar\u015f\u0131l\u0131\u011f\u0131","\u20ba")}</div><div class="offers-reference-layout"><section class="card offers-reference-list"><div class="toolbar"><input class="control search" id="genericSearch" placeholder="Teklif no, m\u00fc\u015fteri, firma veya \u00fcr\u00fcn ara"><button class="secondary" type="button" data-generic-refresh>Yenile</button><span class="muted" id="genericCount">Teklifler y\u00fckleniyor</span></div><div id="genericHost">${empty("Teklifler y\u00fckleniyor","Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div></section><aside class="card offers-reference-side"><div class="card-head"><div><h3>M\u00fc\u015fteri ve i\u015flem</h3><p class="muted">Bir teklifi a\u00e7\u0131n veya yeni teklif olu\u015fturun.</p></div><span class="badge">${total} kay\u0131t</span></div><div class="offers-reference-facts"><div><small>\u0130\u015flem tarihi</small><strong>${new Date().toLocaleDateString("tr-TR")}</strong></div><div><small>Para birimi</small><strong>Teklif kayd\u0131ndan al\u0131n\u0131r</strong></div><div><small>H\u0131zl\u0131 teklif</small><strong>\u00dcr\u00fcn ve m\u00fc\u015fteri se\u00e7imi</strong></div></div><div class="offers-reference-volume"><small>Teklif hacmi</small><strong>${money(volume,"TRY")}</strong></div><button class="success" type="button" data-page="sales">Teklif olu\u015ftur</button></aside></div>`}
function renderContractsReference(){const contracts=Array.isArray(db.contracts)?db.contracts:[],active=contracts.filter(item=>/aktif/i.test(String(item.status||""))).length,renewal=contracts.filter(item=>/yenile/i.test(String(item.status||""))).length,volume=contracts.reduce((sum,item)=>sum+Number(item.price||0),0);return `${pageHead("S\u00f6zle\u015fme Y\u00f6netimi","Kurumsal bak\u0131m anla\u015fmalar\u0131n\u0131, SLA taahh\u00fctlerini ve yenileme takibini y\u00f6netin.",'<button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-generic-add>+ Yeni S\u00f6zle\u015fme</button>')}<div class="metric-grid contracts-reference-metrics">${metric("Aktif S\u00f6zle\u015fmeler",active||contracts.length,"Y\u00fcr\u00fcrl\u00fckte olan kurumsal SLA","\u2713")}${metric("Yakla\u015fan Yenilemeler",renewal,"Yenileme s\u00fcrecindeki kay\u0131tlar","\u25f7")}${metric("Y\u0131ll\u0131k S\u00f6zle\u015fme Hacmi",money(volume,"TRY"),"Kay\u0131tl\u0131 toplam de\u011fer","\u20ba")}${metric("SLA Takibi",contracts.length,"Toplam s\u00f6zle\u015fme","\u231b")}</div><section class="card contracts-reference-list"><div class="toolbar"><input class="control search" id="genericSearch" placeholder="S\u00f6zle\u015fme, m\u00fc\u015fteri veya ba\u015fl\u0131k ara"><button class="secondary" type="button" data-generic-refresh>Yenile</button><span class="muted" id="genericCount">S\u00f6zle\u015fmeler y\u00fckleniyor</span></div><div id="genericHost">${empty("S\u00f6zle\u015fmeler y\u00fckleniyor","Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div></section><div class="contracts-reference-footer"><article class="card"><small>Periyodik Bak\u0131m</small><strong>Planl\u0131 saha ziyaretleri</strong><span class="muted">S\u00f6zle\u015fme tarihleri ve m\u00fc\u015fteri kay\u0131tlar\u0131yla birlikte izlenir.</span></article><article class="card"><small>AYEC SLA Botu</small><strong>Yenileme takibi</strong><span class="muted">Biti\u015f tarihi yakla\u015fan kay\u0131tlar i\u00e7in i\u015flem ak\u0131\u015f\u0131 haz\u0131rlar.</span></article></div>`}
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

function renderCustomers(){const cities=[...new Set(db.customers.map(c=>String(c.city||c.location||"").trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"tr"));const serviceCount=c=>((c.services||[]).filter(s=>!/(teslim|tamamland|iptal|cancel)/i.test(String(s.status||""))).length);const debtCount=db.customers.filter(c=>Number(c.balances?.TRY||0)<0||Number(c.balances?.USD||0)<0||Number(c.balances?.EUR||0)<0).length;const creditCount=db.customers.filter(c=>Number(c.balances?.TRY||0)>0||Number(c.balances?.USD||0)>0||Number(c.balances?.EUR||0)>0).length;const vipCount=db.customers.filter(c=>/kurumsal|vip/i.test(c.type||"")).length;const activeServices=db.customers.filter(c=>serviceCount(c)>0).length;return `<div class="page-head customer-page-head"><div><h2>M\u00fc\u015fteri Y\u00f6netimi &amp; CRM <span class="badge">Cari &amp; Finans Entegre</span></h2><p>M\u00fc\u015fterileri, cari hesap bakiyelerini, a\u00e7\u0131k servis taleplerini ve tahsilat aksiyonlar\u0131n\u0131 tek ekrandan y\u00f6netin.</p></div><div class="customer-head-actions"><div class="customer-export-actions"><button class="mini" data-action="export-customers" title="Excel">&#x1f7e9; Excel</button><button class="mini" data-action="print-customers" title="Liste Al">&#x2b06; Liste Al</button><button class="mini" data-action="export-customers-pdf" title="Rapor">&#x1f4ca; Rapor</button><button class="mini" data-action="customer-help" title="Nas\u0131l Kullan\u0131l\u0131r?">&#x24d8; Nas\u0131l Kullan\u0131l\u0131r?</button></div></div></div><footer class="customer-metrics">${metric("Piyasa Alaca\u011f\u0131 (Bor\u00e7lular)",money(db.customers.filter(c=>Number(c.balances?.TRY||0)<0).reduce((s,c)=>s+Math.abs(Number(c.balances?.TRY||0)),0),"TRY"),"M\u00fc\u015fteri toplam bor\u00e7 bakiyesi","&#x2198;")}${metric("Cari Avanslar (Alacakl\u0131lar)",money(db.customers.filter(c=>Number(c.balances?.TRY||0)>0).reduce((s,c)=>s+Number(c.balances?.TRY||0),0),"TRY"),"\u00d6n \u00f6demeler ve a\u00e7\u0131k bakiyeler","&#x24;")}${metric("M\u00fc\u015fterideki Cihaz Say\u0131s\u0131",db.customers.reduce((s,c)=>s+serviceCount(c),0)+" Adet","Aktif at\u00f6lye ve onar\u0131mda","&#x25a3;")}${metric("Kurumsal VIP Oran\u0131",(db.customers.length?Math.round(vipCount/db.customers.length*100):0)+"%","Y\u0131ll\u0131k bak\u0131m s\u00f6zle\u015fmeli","&#x2733;")}</footer><section class="customer-management"><div class="customer-workspace-head"><button class="primary customer-add" data-action="add-customer">&#x2b; YEN\u0130 M\u00dc\u015eTER\u0130 EKLE</button></div><div class="customer-filterbar"><div class="customer-search-wrap"><input class="control search" id="customerSearch" placeholder="\u2315  \u0130sim, unvan, telefon, vergi no veya e-posta ile filtrele..."><button type="button" id="customerSearchClear" aria-label="Aramay\u0131 temizle">&#x2715;</button></div><select class="control" id="customerTypeFilter"><option value="">T\u00fcm Tipler (Bireysel / Kurumsal)</option><option value="Bireysel">Bireysel</option><option value="Kurumsal">Kurumsal</option></select><select class="control" id="customerLocationFilter"><option value="">T\u00fcm Lokasyonlar (\u0130l / \u0130l\u00e7e)</option>${cities.map(city=>`<option value="${esc(city)}">${esc(city)}</option>`).join("")}</select><select class="control" id="customerBalanceFilter"><option value="">T\u00fcm Bakiyeler</option><option value="debt">Bor\u00e7lu Bakiyeler</option><option value="credit">Alacakl\u0131 Bakiyeler</option><option value="zero">Bakiyesi 0 Olanlar</option></select><div class="customer-quick-actions"><button class="mini" data-action="copy-customers" title="Listeyi Kopyala">&#x2709;</button><button class="mini" data-action="print-customers" title="Yazd\u0131r">&#x1f5a8;</button><button class="mini" id="customerMultiSelect" title="\u00c7oklu Se\u00e7im">&#x2699;</button><button class="mini" data-action="import-customers" title="M\u00fc\u015fteri \u0130\u00e7e Aktar">&#x2b06;</button></div></div><section class="card customer-card"><div id="customerTable">${customerTable(db.customers)}</div><div class="customer-footer"><span>Toplam Kay\u0131t: <b id="customerCount">${db.customers.length}</b><span class="customer-page-size-label">&nbsp; | &nbsp; Sayfa ba\u015f\u0131na:</span> <select id="customerPageSize" class="control"><option>10</option><option>25</option><option>50</option></select></span><div class="customer-pagination"><button id="customerPagePrev" type="button" aria-label="\u00d6nceki sayfa">&#x276e;</button><span id="customerPageIndicator">1 / 1</span><button id="customerPageNext" type="button" aria-label="Sonraki sayfa">&#x276f;</button></div><span class="customer-updated">Son G\u00fcncelleme: ${new Date().toLocaleString("tr-TR")}</span></div></section></section>`}
function customerTable(rows){
 return `<div class="table-wrap"><table class="customer-data-table"><thead><tr><th><input type="checkbox" id="customerSelectAll" aria-label="T\u00fcm m\u00fc\u015fterileri se\u00e7"></th><th>M\u00dc.NO</th><th>M\u00dc\u015eTER\u0130 / UNVAN</th><th>T\u0130P</th><th>\u0130LET\u0130\u015e\u0130M B\u0130LG\u0130S\u0130</th><th>A\u00c7IK SERV\u0130S</th><th>CAR\u0130 BAK\u0130YE</th><th>DURUM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${rows.map((c,i)=>{
  const status=customerReferenceStatus(c),type=String(c.type||"Bireysel"),tax=c.tc_no||c.tax_number||c.tax_no||"",city=c.city||c.location||"",company=c.company||c.company_name||"",open=(c.services||[]).filter(s=>!/(teslim|tamamland|iptal|cancel)/i.test(String(s.status||""))).length,balance=Number(c.balances?.TRY||0),balanceLabel=balance<0?"Bor\u00e7":balance>0?"Alacak":"Dengede",vip=String(c.contract_type||"").toUpperCase().includes("VIP"),meta=[company,city].filter((value,index,all)=>value&&all.indexOf(value)===index).join(" \u00b7 ")||((tax?(/kurumsal|vip|bayi/i.test(type)?"VN: ":"TC: ")+tax:"")),initials=String(c.name||"M").split(/\s+/).slice(0,2).map(x=>x[0]||"").join("").toUpperCase();
  return `<tr data-kind="customer" data-id="${c.id}"><td><input type="checkbox" class="customer-row-select" data-id="${c.id}" aria-label="${esc(c.name)}"></td><td class="customer-id">#${String(c.id||i+1).padStart(3,"0")}</td><td class="customer-name-cell"><span class="customer-avatar">${esc(initials)}</span><span class="customer-name"><strong>${esc(c.name)}${vip?'<em class="customer-vip-tag">VIP</em>':""}</strong><small>${esc(meta)}</small></span></td><td><span class="customer-type ${/kurumsal|vip/i.test(type)?"corporate":"individual"}">${esc(type)}</span></td><td class="customer-contact"><span>&#x260e; ${esc(c.phone||"-")}</span><small>&#x2709; ${esc(c.email||"-")}</small></td><td class="customer-service"><span class="service-count ${open?"has-open":""}">${open?`${open} A\u00e7\u0131k`:open}</span></td><td class="balance"><strong>${money(c.balances?.TRY,"TRY")}</strong><small class="balance-tag ${balance<0?"debt":balance>0?"credit":"zero"}">${balanceLabel}</small><small>${money(c.balances?.USD,"USD")}</small></td><td><span class="customer-status ${status.toLowerCase()}"><i></i>${esc(status)}</span></td><td><button class="primary mini" data-action="customer-actions" data-id="${c.id}">\u0130\u015flem Yap &#x25be;</button></td></tr>`
 }).join("")}</tbody></table></div>`;
}
function customerReferenceStatus(c){if(c.is_active===false||c.is_active===0||c.is_active==="0")return "Pasif";if(c.is_problematic)return "Dikkat";return /kurumsal|vip/i.test(c.type||"")?"VIP":"Aktif"}

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
function renderStock(){const value=stockValueSummary(),critical=db.stock.filter(s=>s.qty<=s.min).length,categories=[...new Set(db.stock.map(s=>String(s.category||"").trim()).filter(Boolean))].sort((a,b)=>{const order=currentSector==="otomotiv"?["Otomotiv","Mekanik","Elektrik"]:["Bilgisayar Bile\u015fenleri","Ak\u0131ll\u0131 Ev Sistemleri","G\u00fcvenlik Sistemleri"];return (order.indexOf(a)<0?99:order.indexOf(a))-(order.indexOf(b)<0?99:order.indexOf(b))||a.localeCompare(b,"tr")}),description=currentSector==="otomotiv"?"Otomotiv yedek parca ve servis stoklarini yonetin.":"Urun ve parca stoklarini, kategori dagilimini, kritik seviyeleri ve maliyetleri takip edin.",valueText=value.missing.length?(value.breakdown||money(0,"TRY")):money(value.tryEquivalent,"TRY"),valueDetail=value.missing.length?`Kur eksik · ${value.missing.join(", ")} TRY karşılığı hesaplanamadı`:`Alış maliyeti · ${value.breakdown||money(0,"TRY")} · TRY karşılığı`;return `${pageHead("Stok & Envanter Takibi",description,'<button class="primary" data-action="add-product">＋ Ürün Ekle</button>')}<div class="metric-grid stock-reference-metrics">${metric("Toplam Çeşit",db.stock.length,"Aktif stok kartı","◫")}${metric("Stok Değeri (TRY)",valueText,valueDetail,"₺")}${metric("Kritik Stok",critical,"Minimum seviyenin altındaki ürünler","!")}${metric("Potansiyel Kazanç",money(db.stock.reduce((sum,s)=>sum+Math.max(0,(Number(s.sell)||0)-(Number(s.buy)||0))*(Number(s.qty)||0),0),"TRY"),"Tahmini brüt kar getirisi","P")}</div>${stockTabs("stock")}<div class="stock-category-strip"><strong>KATEGORİLER</strong><button class="active" data-stock-category="">Tümü (${db.stock.length})</button>${categories.map(x=>`<button data-stock-category="${esc(x)}">${esc(x)}</button>`).join("")}</div><section class="card stock-reference-card"><div class="toolbar stock-reference-toolbar"><input class="control search" id="stockSearch" placeholder="Ürün adı, parça kodu veya barkod ara"><select class="control" id="stockCategory"><option>Tüm Kategoriler</option>${categories.map(x=>`<option>${esc(x)}</option>`).join("")}</select><select class="control" id="stockLevel"><option>Tüm Seviyeler</option><option>Kritik Stok</option><option>Stokta Var</option></select><button class="danger" data-action="critical-stock">Kritik Stoklar</button><button class="secondary" data-page="import">İçe Aktar</button><button class="secondary" data-action="export-stock">Dışa Aktar</button><button class="primary" data-action="add-product">＋ Yeni Ürün</button></div><div id="stockTable">${stockTable(db.stock)}</div></section>`}
function stockTable(rows,offset=0){return `<div class="table-wrap stock-reference-table-wrap"><table class="stock-reference-table"><thead><tr><th>S.No</th><th>Stok Kodu</th><th>Par\u00e7a / \u00dcr\u00fcn Tan\u0131m\u0131</th><th>Kategori</th><th>Miktar &amp; Durum</th><th>Birim</th><th>Al\u0131\u015f Fiyat\u0131</th><th>Sat\u0131\u015f Fiyat\u0131</th><th>K\u00e2r (%)</th><th>Raf Yeri</th><th>Min. Stok</th><th>\u0130\u015flemler</th></tr></thead><tbody>${rows.map((s,i)=>{const buy=Number(s.buy)||0,sell=Number(s.sell)||0,profit=buy>0?((sell-buy)/buy*100):0;return `<tr data-kind="stock" data-id="${s.id}"><td data-label="S.No">${i+offset+1}</td><td data-label="Stok Kodu">${esc(s.code)}</td><td data-label="Par\u00e7a / \u00dcr\u00fcn Tan\u0131m\u0131"><strong>${esc(s.name)}</strong><br><small class="muted">${esc(s.description||s.barcode||"")}</small></td><td data-label="Kategori"><span class="badge">${esc(s.category)}</span></td><td data-label="Miktar &amp; Durum">${statusBadge(s.qty<=s.min?"Kritik":"Stokta")} ${s.qty}</td><td data-label="Birim">${esc(s.unit||"Adet")}</td><td data-label="Al\u0131\u015f Fiyat\u0131">${money(buy,s.currency)}</td><td data-label="Sat\u0131\u015f Fiyat\u0131">${money(sell,s.currency)}</td><td data-label="K\u00e2r (%)">${profit.toFixed(1)}%</td><td data-label="Raf Yeri">${esc(s.shelf||"-")}</td><td data-label="Min. Stok">${s.min}</td><td data-label="\u0130\u015flemler"><div class="row-actions"><button class="mini" data-action="edit-product" data-id="${s.id}">D\u00fczenle</button><button class="mini danger-outline" data-action="delete-product" data-id="${s.id}">Sil</button></div></td></tr>`}).join("")}</tbody></table></div>`}

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

function invoiceLineMarkup(index=1,vatRate=20){return `<tr data-invoice-line><td data-label="#">${index}</td><td data-label="\u00dcr\u00fcn / Hizmet"><input class="invoice-line-description" value="" placeholder="\u00dcr\u00fcn veya hizmet" aria-label="\u00dcr\u00fcn veya hizmet"></td><td data-label="Stok Kodu"><input class="invoice-line-code" value="" aria-label="Stok kodu"></td><td data-label="Miktar"><input class="invoice-line-qty" type="number" min="0" step="0.01" value="1" aria-label="Miktar"></td><td data-label="Birim"><select class="invoice-line-unit" aria-label="Birim"><option>Adet</option><option>Hizmet</option><option>Kg</option><option>Saat</option></select></td><td data-label="Birim Fiyat"><input class="invoice-line-price" type="number" min="0" step="0.01" value="0" aria-label="Birim fiyat"></td><td data-label="\u0130sk %"><input class="invoice-line-discount" type="number" min="0" max="100" step="0.01" value="0" aria-label="\u0130skonto y\u00fczdesi"></td><td data-label="KDV %"><select class="invoice-line-vat" aria-label="KDV oran\u0131"><option value="20" ${Number(vatRate)===20?"selected":""}>20</option><option value="10" ${Number(vatRate)===10?"selected":""}>10</option><option value="1" ${Number(vatRate)===1?"selected":""}>1</option><option value="0" ${Number(vatRate)===0?"selected":""}>0</option></select></td><td data-label="Net Tutar" class="invoice-line-total">0.00</td><td data-label="\u0130\u015flem"><button type="button" class="icon-button invoice-line-remove" aria-label="Sat\u0131r\u0131 sil">\u00d7</button></td></tr>`}
function renderInvoiceComposer(){const customers=(db.customers||[]).map(customer=>`<option value="${esc(customer.name)}"></option>`).join("");return `${pageHead("E-Fatura Olu\u015fturma Studio","Resmi e-Fatura, e-Ar\u015fiv ve ihracat faturalar\u0131n\u0131 olu\u015fturun.",'<span class="badge">G\u0130B UBL 2.1</span>')}<div class="einvoice-layout"><main class="einvoice-main"><section class="card einvoice-ribbon"><span class="einvoice-icon">\u25a7</span><div><h2>E-Fatura Olu\u015fturma Studio</h2><p>Resmi e-Fatura, e-Ar\u015fiv ve ihracat faturalar\u0131 olu\u015fturma ve m\u00fckellef do\u011frulama ekran\u0131.</p></div><button type="button" class="secondary" data-invoice-action="import">\u0130rsaliye / Sipari\u015ften \u00c7ek</button><button type="button" class="primary" data-invoice-action="add">+ Yeni Sat\u0131r Ekle (F2)</button><button type="button" class="secondary" data-invoice-action="remove">Sat\u0131r Sil</button></section><section class="card einvoice-meta"><h3>\u25a3 M\u00fc\u015fteri & Fatura \u00dcst Bilgileri</h3><div class="einvoice-fields"><div class="field customer-field"><label>M\u00fc\u015fteri / Cari \u00dcnvan\u0131 *</label><div class="invoice-customer-row"><input id="invoiceCustomer" list="invoiceCustomers" required placeholder="M\u00fc\u015fteri se\u00e7in"><datalist id="invoiceCustomers">${customers}</datalist><button type="button" class="secondary" data-invoice-action="customer">Cari Rehber (F4)</button></div></div><div class="field"><label>Vergi / TC Kimlik No</label><input id="invoiceVkn" inputmode="numeric"></div><div class="field"><label>Vergi Dairesi</label><input id="invoiceTaxOffice"></div><div class="field"><label>Senaryo</label><select id="invoiceScenario"><option>TICARIFATURA</option><option>TEMELFATURA</option><option>IHRACAT</option></select></div><div class="field"><label>Fatura Tipi</label><select id="invoiceType"><option value="SATIS">SATIS (Sat\u0131\u015f)</option><option value="TEVKIFAT">TEVKIFAT (Tevkifat)</option><option value="ISTISNA">ISTISNA (0 KDV)</option><option value="IADE">IADE (Sat\u0131\u015f \u0130adesi)</option></select></div><div class="field"><label>Fatura Tarihi</label><input id="invoiceDate" type="date" value="2026-10-01"></div><div class="field"><label>D\u00fczenleme Saati</label><input id="invoiceTime" type="time"></div><div class="field currency-field"><label>Para Birimi & Fatura Kuru</label><div><select id="invoiceCurrency"><option value="USD">USD ($) Dolar</option><option value="TRY">TRY (\u20ba) T\u00fcrk Liras\u0131</option><option value="EUR">EUR (\u20ac) Euro</option></select><input id="invoiceRate" type="number" min="0" step="0.0001" value="49.0013"></div></div><div class="field address-field"><label>A\u00e7\u0131k Adres & Posta Kodu</label><input id="invoiceAddress"></div><div class="field"><label>Ba\u011fl\u0131 \u0130rsaliye No / Belge Ref</label><input id="invoiceDeliveryRef"></div></div></section><section class="card einvoice-lines"><header><h3>\u25a4 Fatura Kalemleri & Hizmet Sat\u0131rlar\u0131</h3><span id="invoiceLineCount">1 Kalem Listelendi</span><span class="stock-reserved">\u25cf Stoktan Rezerveli</span><span class="muted">Tevkifat Oran\u0131: Yok</span></header><div class="invoice-table-scroll"><table class="einvoice-table"><thead><tr><th>#</th><th>\u00dcr\u00fcn / Hizmet A\u00e7\u0131klamas\u0131</th><th>Stok Kodu</th><th>Miktar</th><th>Birim</th><th>Birim Fiyat</th><th>\u0130sk (%)</th><th>KDV (%)</th><th>Net Tutar</th><th>\u0130\u015flem</th></tr></thead><tbody id="invoiceLinesBody">${invoiceLineMarkup(1,desktopSettings.vat_default_rate??20)}</tbody></table><button class="invoice-add-inline" type="button" data-invoice-action="add">+ Yeni sat\u0131r girmek i\u00e7in t\u0131klay\u0131n veya (F2) tu\u015funa bas\u0131n</button></div><footer><span id="invoiceUnits">Toplam Miktar: 1 Birim</span><span id="invoiceDiscountRows">\u0130skonto Yap\u0131lan Sat\u0131r: 0</span><span id="invoiceRateFooter">Para Birimi Kuru: 49.0013 USD</span><span>Uyumsoft e-Fatura API Haz\u0131r</span></footer></section><section class="card einvoice-notes"><div class="field"><label>Fatura Notu / Yasal A\u00e7\u0131klamalar</label><small>G\u0130B fatura alt\u0131nda g\u00f6sterilir</small><textarea id="invoiceNotes" rows="3" placeholder="Banka, garanti veya sevk notu..."></textarea></div><div class="field"><label>\u00d6zel Kod & Sipari\u015f No</label><input id="invoiceOrderRef" placeholder="M\u00fc\u015fteri sipari\u015f numaras\u0131"><small>OrderReference etiketine i\u015flenir.</small></div></section></main><aside class="einvoice-aside"><section class="card einvoice-summary"><header><div><h3>\u25a3 F\u0130NANSAL GENEL TOPLAM</h3><p>Vergi ve kur matrah\u0131 canl\u0131 hesaplama</p></div><span class="badge">USD / TRY</span></header><div class="invoice-total-row"><span>Ara Toplam:</span><strong id="invoiceSubtotal">0.00</strong></div><div class="invoice-total-row danger"><span>Toplam \u0130skonto:</span><strong id="invoiceDiscountTotal">-0.00</strong></div><div class="invoice-total-row"><span>KDV Matrah\u0131:</span><strong id="invoiceTaxable">0.00</strong></div><div class="invoice-total-row success"><span>Hesaplanan KDV:</span><strong id="invoiceVat">0.00</strong></div><div class="invoice-grand-total"><div><strong>\u00d6DENECEK GENEL TUTAR</strong><span>T\u00dcM VERG\u0130LER DAH\u0130L</span></div><b id="invoiceGrandTotal">$0.00</b><small>TL Kar\u015f\u0131l\u0131\u011f\u0131 (TCMB): <strong id="invoiceGrandTry">0.00 \u20ba</strong></small></div></section><section class="card einvoice-payment"><header><h3>\u25a3 Tahsilat & Kasa Bilgisi</h3><span class="muted">Zorunlu</span></header><div class="field"><label>Tahsilat Hesab\u0131 / Kasa</label><select id="invoiceBank"><option>A\u00e7\u0131k Hesap / Tahsilat Se\u00e7in</option><option>Garanti BBVA Ticari USD</option></select></div><div class="einvoice-payment-row"><div class="field"><label>Vade Tarihi</label><input id="invoiceDueDate" type="date"></div><div class="field"><label>\u00d6deme Kanal\u0131</label><select id="invoicePaymentChannel"><option>Havale / EFT</option><option>Kredi Kart\u0131</option><option>Nakit</option><option>DBS / \u00c7ek</option></select></div></div><label class="invoice-switch"><span>Cari Hesaba Otomatik \u0130\u015fle</span><input id="invoiceAutoReconcile" type="checkbox" checked></label></section><section class="einvoice-actions"><button class="primary" data-invoice-action="send">\u27a4 E-Faturay\u0131 Resmile\u015ftir ve G\u00f6nder (F12)</button><div><button class="secondary" data-invoice-action="preview">PDF G\u00f6r</button><button class="secondary" data-invoice-action="draft">Taslak</button><button class="secondary" data-invoice-action="proforma">Proforma</button></div><small>\u25cf Uyumsoft Portal Ba\u011flant\u0131s\u0131 Haz\u0131r</small></section></aside></div>`}
function bindInvoiceComposer(){const body=$("#invoiceLinesBody");if(!body)return;let savedId=null,currentTotal=0;const rows=()=>$$('[data-invoice-line]',body);const update=()=>{let subtotal=0,discount=0,taxable=0,vat=0,units=0,discountRows=0;rows().forEach((row,index)=>{row.cells[0].textContent=String(index+1);const qty=Math.max(0,Number($(".invoice-line-qty",row).value)||0),price=Math.max(0,Number($(".invoice-line-price",row).value)||0),off=Math.min(100,Math.max(0,Number($(".invoice-line-discount",row).value)||0)),rate=Math.max(0,Number($(".invoice-line-vat",row).value)||0),gross=qty*price,cut=gross*off/100,net=gross-cut,tax=net*rate/100;subtotal+=gross;discount+=cut;taxable+=net;vat+=tax;units+=qty;if(cut>0)discountRows++;$(".invoice-line-total",row).textContent=(net+tax).toFixed(2)});const total=taxable+vat;currentTotal=total;const rate=Number($("#invoiceRate").value)||0,currency=$("#invoiceCurrency").value;[["#invoiceSubtotal",subtotal],["#invoiceDiscountTotal",discount],["#invoiceTaxable",taxable],["#invoiceVat",vat]].forEach(([selector,value])=>{const node=$(selector);if(node)node.textContent=`${selector==="#invoiceDiscountTotal"?"-":""}${value.toFixed(2)}`});$("#invoiceGrandTotal").textContent=`${currency==="USD"?"$":currency==="EUR"?"\u20ac":"\u20ba"}${total.toFixed(2)}`;$("#invoiceGrandTry").textContent=`${(total*rate).toFixed(2)} \u20ba`;$("#invoiceLineCount").textContent=`${rows().length} Kalem Listelendi`;$("#invoiceUnits").textContent=`Toplam Miktar: ${units} Birim`;$("#invoiceDiscountRows").textContent=`\u0130skonto Yap\u0131lan Sat\u0131r: ${discountRows}`;$("#invoiceRateFooter").textContent=`Para Birimi Kuru: ${rate.toFixed(4)} ${currency}`};body.addEventListener("input",update);body.addEventListener("change",update);$("#invoiceRate").addEventListener("input",update);$("#invoiceCurrency").addEventListener("change",update);$$('[data-invoice-action="add"]').forEach(button=>button.onclick=()=>{body.insertAdjacentHTML("beforeend",invoiceLineMarkup(rows().length+1,desktopSettings.vat_default_rate??20));update()});$$('[data-invoice-action="remove"]').forEach(button=>button.onclick=()=>{rows().at(-1)?.remove();update()});body.addEventListener("click",event=>{const remove=event.target.closest(".invoice-line-remove");if(remove){remove.closest("tr").remove();update()}});$$('[data-invoice-action="customer"]').forEach(button=>button.onclick=()=>$("#invoiceCustomer").focus());$$('[data-invoice-action="import"]').forEach(button=>button.onclick=()=>toast("\u0130rsaliye ve sipari\u015f aktar\u0131m\u0131 i\u00e7in belge se\u00e7in","info"));if(!window.einvoiceKeysBound){window.einvoiceKeysBound=true;window.addEventListener("keydown",event=>{if(page!=="invoices"||event.altKey||event.ctrlKey||event.metaKey)return;if(event.key==="F2"){event.preventDefault();$('[data-invoice-action="add"]')?.click()}else if(event.key==="F12"){event.preventDefault();$('[data-invoice-action="send"]')?.click()}else if(event.key==="F4"){event.preventDefault();$("#invoiceCustomer")?.focus()}})}const persist=async status=>{const payload={uuid:crypto.randomUUID(),invoice_type:$("#invoiceType").value,receiver_name:$("#invoiceCustomer").value,receiver_vkn:$("#invoiceVkn").value,amount:currentTotal,status,json_data:JSON.stringify({scenario:$("#invoiceScenario").value,date:$("#invoiceDate").value,time:$("#invoiceTime").value,currency:$("#invoiceCurrency").value,exchange_rate:$("#invoiceRate").value,address:$("#invoiceAddress").value,tax_office:$("#invoiceTaxOffice").value,delivery_reference:$("#invoiceDeliveryRef").value,order_reference:$("#invoiceOrderRef").value,notes:$("#invoiceNotes").value,lines:rows().map(row=>Object.fromEntries([...row.querySelectorAll("input,select")].map(field=>[field.className,field.value]))),payment_account:$("#invoiceBank").value,payment_channel:$("#invoicePaymentChannel").value,due_date:$("#invoiceDueDate").value,auto_reconcile:$("#invoiceAutoReconcile").checked})};if(savedId){payload.id=savedId;payload._action="update"}const result=await apiFetch("/api/desktop/table/e_invoices",{method:"POST",body:JSON.stringify(payload)});savedId=result.id||savedId;return result};$$('[data-invoice-action="draft"]').forEach(button=>button.onclick=async()=>{try{await persist("DRAFT");toast("Fatura tasla\u011f\u0131 kaydedildi","success")}catch(error){toast(error.message,"error")}});$$('[data-invoice-action="proforma"]').forEach(button=>button.onclick=async()=>{try{await persist("DRAFT");window.print()}catch(error){toast(error.message,"error")}});$$('[data-invoice-action="preview"]').forEach(button=>button.onclick=()=>window.print());$$('[data-invoice-action="send"]').forEach(button=>button.onclick=async()=>{if(!$("#invoiceCustomer").value.trim()){toast("M\u00fc\u015fteri se\u00e7imi zorunludur","warning");return}if(!confirm("E-Fatura tasla\u011f\u0131 kaydedilecek ve g\u00f6nderim i\u00e7in kuyru\u011fa al\u0131nacakt\u0131r. Devam edilsin mi?"))return;try{await persist("QUEUED");toast("E-Fatura g\u00f6nderim kuyru\u011funa al\u0131nd\u0131","success")}catch(error){toast(error.message,"error")}});update()}

function renderFinance(filter=""){
 const rows=filter?db.finance.filter(f=>f.type===filter):db.finance;
 const income=db.finance.filter(f=>f.type==="Gelir").reduce((a,b)=>a+moneyNumber(b.amount),0);
 const expense=db.finance.filter(f=>f.type==="Gider").reduce((a,b)=>a+moneyNumber(b.amount),0);
 const net=income-expense;
 const command='<button class="secondary" data-action="finance-period">Bug\u00fcn (28.09.2026)</button><button class="secondary" data-action="finance-week">Son 7 G\u00fcn</button><button class="secondary" data-action="finance-month">Bu Ay</button>';
 const quick='<section class="finance-quick card"><div class="card-head"><h3>H\u0131zl\u0131 \u0130\u015flemler</h3><span class="muted">ERP PANEL</span></div><div class="finance-quick-grid"><button data-action="export-finance">Excel \u0130ndir</button><button data-action="export-finance">PDF Rapor</button><button data-action="print-finance">Fi\u015f Yazd\u0131r</button><button class="green" data-action="collect-finance">Tahsilat Al</button><button class="green" data-action="add-income">Gelir Ekle</button><button class="red" data-action="add-expense">Gider Ekle</button><button data-action="transfer-finance">Virman / Transfer</button><button class="purple" data-action="tax-finance">Vergi Hesab\u0131</button></div></section>';
 const cards=`<section class="finance-side-cards"><h3>Finans \u00d6zeti</h3>${metric("Toplam Ciro",money(income),"Br\u00fct Sat\u0131\u015f (KDV Dahil)","\\u2197")}${metric("Maliyet ve Gider",money(expense),"Al\u0131\u015f + Operasyon","\\u2198")}${metric("Net K\u00e2r",money(net),"Gelir - Gider Net","\\u20ba")}${metric("S\u0131cak Nakit",money(net),"Kasa ve Banka Mevcudu","\\u25a3")}</section>`;
 return `${pageHead(filter?`${filter} Kay\u0131tlar\u0131`:"Finansal Dashboard","Gelir, gider ve tahsilat hareketlerini tek ekranda y\u00f6netin.",'<button class="primary" data-action="finance-fiscal">Mali Y\u0131l Kontrolleri</button>')}<div class="finance-command-bar"><div><small>Finansal d\u00f6nem</small><div class="actions">${command}</div></div><div class="actions"><button class="success" data-action="add-income">+ Gelir Ekle</button><button class="danger" data-action="add-expense">- Gider Ekle</button><button class="primary" data-action="collect-finance">Tahsilat Al</button></div></div><div class="finance-layout"><main><section class="card finance-ledger"><div class="card-head"><h3>Son Hareketler (Birle\u015fik Defter)</h3><span class="badge">${rows.length} Kay\u0131t Y\u00fckl\u00fc</span></div>${financeTable(rows)}</section></main><aside>${quick}${cards}</aside></div>`;
}
function financeTable(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th>Müşteri</th><th>Tutar</th><th></th></tr></thead><tbody>${rows.map(f=>`<tr data-kind="finance" data-id="${f.id}"><td>${esc(f.date)}</td><td>${statusBadge(f.type)}</td><td>${esc(f.category)}</td><td>${esc(f.description)}</td><td>${esc(f.customer)}</td><td><strong>${money(f.amount,f.currency)}</strong></td><td><button class="mini" data-action="edit-finance" data-id="${f.id}">Düzenle</button></td></tr>`).join("")}</tbody></table></div>`}

function renderAppointments(){const monday=new Date();monday.setDate(monday.getDate()-((monday.getDay()+6)%7)+(appointmentWeekOffset*7));const days=[0,1,2,3,4].map(offset=>{const d=new Date(monday);d.setDate(d.getDate()+offset);return d}),start=days[0].toLocaleDateString("tr-TR"),end=days[4].toLocaleDateString("tr-TR");return `${pageHead("Randevu Takvimi","Çift tıklama, sağ tuş durum menüsü, toast ve yaklaşan randevu uyarıları etkin.",'<button class="primary" data-action="add-appointment">＋ Yeni Randevu</button>')}<section class="card"><div class="appointment-nav"><div class="actions"><button class="secondary" data-action="appointment-prev">‹ Önceki</button><button class="secondary" data-action="appointment-today">Bugün</button><button class="secondary" data-action="appointment-next">Sonraki ›</button></div><strong>${start} — ${end}</strong></div><div class="appointment-board">${days.map(d=>{const ds=d.toISOString().slice(0,10),items=db.appointments.filter(a=>a.date===ds);return `<div class="day-column"><h3>${d.toLocaleDateString("tr-TR",{weekday:"long",day:"numeric",month:"short"})}</h3>${items.map(a=>`<div class="appointment" data-kind="appointment" data-id="${a.id}"><span class="muted">${a.time}</span><strong>${esc(customerName(a.customerId))}</strong><span>${esc(a.title)}</span><br>${statusBadge(a.status)}</div>`).join("")||'<small class="muted">Randevu yok</small>'}</div>`}).join("")}</div></section>`}

const settingsGroups=[
 ["GENEL",[["company","🏢","Firma Ayarları"],["locale","🌐","Dil, Tarih & Para Birimi"],["tax-currency","%","KDV & Kur Senkronizasyonu"],["theme","🎨","Temalar & Yazı Tipi"]]],
 ["ENTEGRASYONLAR & API",[["integrations","[API]","Entegrasyonlar & API"],["sms-settings","[SMS]","SMS Ayarlari"],["smtp-settings","[MAIL]","E-posta / SMTP"],["messaging","[CHAT]","WhatsApp & Telegram"],["ai-settings","[AI]","Gemini / AI"],["autonomous-agents","[BOT]","Otonom Ajanlar"],["voice-settings","[VOICE]","Sesli Asistan"]]],
 ["TİCARİ & LİSTELER",[["cargo","🚚","Kargo Firmaları"],["bank-settings","🏦","Banka Ayarları"],["notes","✏️","Hızlı Not Yönetimi"],["stock-settings","📦","Stok Ayarları"],["numbering","🔢","Belge Numaraları"],["location","📍","Harita & Konum"]]],
 ["G\u00dcVENL\u0130K & S\u0130STEM",[["backup","[BACKUP]","Yedekleme ve Veri Merkezi"],["users","[USER]","Kullanici Yonetimi & Yetki Matrisi"],["license","[LICENSE]","Lisans Durumu"],["security","[SECURE]","Guvenlik Ayarlari (Sifre)"],["audit-settings","[AUDIT]","Sistem Islem Loglari (Audit)"]]],
 ["UZAK BAĞLANTI",[["remote","🖥️","AYEC Pro (Uzak)"]]],
 ["SİSTEM YAPISI",[["identity","⚙️","Sistem Kimliği & Modüler Yapı"]]]
];
settingsGroups[1][1].push(["voice-shortcuts","[VOICE]","Sesli Kestirmeler"]);
function settingBody(s){const common=`<div class="settings-grid"><div class="setting"><div><strong>Çift tıklama</strong><br><small class="muted">Satırı doğrudan ayrıntıda açar.</small></div><input class="switch" id="setDouble" type="checkbox" ${s.doubleClick?"checked":""}></div><div class="setting"><div><strong>Sağ tuş menüleri</strong><br><small class="muted">Bağlama özel işlem menüsü.</small></div><input class="switch" id="setContext" type="checkbox" ${s.contextMenu?"checked":""}></div><div class="setting"><div><strong>Randevu bildirimleri</strong><br><small class="muted">Toast, alert ve sistem bildirimi.</small></div><input class="switch" id="setAlerts" type="checkbox" ${s.appointmentAlerts?"checked":""}></div><div class="setting"><div><strong>Kompakt görünüm</strong><br><small class="muted">Tablo ve kart aralıklarını azaltır.</small></div><input class="switch" id="setCompact" type="checkbox" ${s.compact?"checked":""}></div></div>`;if(settingsSection==="company")return `<h3>Firma Ayarları</h3><div class="form-grid"><div class="field full"><label>Firma Adı</label><input id="setCompany" value="${esc(s.company)}"></div><div class="field"><label>Varsayılan Para Birimi</label><select id="setCurrency"><option ${s.currency==="TRY"?"selected":""}>TRY</option><option ${s.currency==="USD"?"selected":""}>USD</option><option ${s.currency==="EUR"?"selected":""}>EUR</option></select></div><div class="field"><label>Randevu uyarısı (dakika)</label><input id="setAlertMinutes" type="number" min="1" value="${s.alertMinutes}"></div></div><h3>Etkileşim ve Bildirim</h3>${common}`;if(settingsSection==="backup")return `<h3>Yedekleme ve Veri Merkezi</h3><p class="muted">Masaüstü uygulamasıyla aynı veritabanının tam yedeğini yönetin.</p><div class="actions"><button class="primary" data-action="export-all">Tam Yedek Al</button><button class="secondary" data-action="restore-backup">Yedeği Geri Yükle</button></div>`;if(settingsSection==="audit-settings")return `<h3>Sistem İşlem Logları</h3><p class="muted">Kullanıcı ve veri değişikliklerini denetleyin.</p><button class="primary" data-page="audit">Audit Kayıtlarını Aç</button>`;if(settingsSection==="stock-settings")return `<h3>Stok Ayarları</h3><div class="form-grid"><div class="field"><label>Varsayılan kritik stok</label><input name="default_min_stock" type="number" value="5"></div><div class="field"><label>Varsayılan kategori</label><select><option>Bilgisayar</option><option>Akıllı Ev</option><option>Güvenlik Sistemleri</option></select></div></div><button class="secondary" data-page="import">Akıllı İçe Aktarmayı Aç</button>`;if(settingsSection==="notes")return `<div class="card-head"><div><h3>H\u0131zl\u0131 Notlar &amp; Makrolar</h3><p class="muted">Teknisyen paneli ve servis operasyon s\u00fcre\u00e7leri i\u00e7in haz\u0131r metin \u015fablonlar\u0131n\u0131 y\u00f6netin.</p></div><span id="quickNoteCount" class="quick-note-count">0 \u015eablon Aktif</span><button class="primary" id="quickNoteAdd">+ + Yeni Not Ekle</button></div><div class="quick-notes-toolbar"><label>Filtrele:<select id="quickNoteFilter"><option value="">T\u00fcm Kategoriler</option><option>Bilgisayar</option><option>Cep Telefonu</option><option>G\u00fcvenlik Sistemleri</option></select></label><label>Ara:<input id="quickNoteSearch" type="search" placeholder="Notlarda ara..."></label><div class="quick-note-tags"><span>H\u0131zl\u0131 Etiketler:</span><button type="button" data-note-tag="Ar\u0131za">#Ar\u0131za</button><button type="button" data-note-tag="Test">#Test</button><button type="button" data-note-tag="Aksesuar">#Aksesuar</button></div></div><div id="quickNotesHost">${empty("Notlar y\u00fckleniyor","Masa\u00fcst\u00fc h\u0131zl\u0131 notlar\u0131 okunuyor.")}</div>`;if(settingsSection==="locale"||settingsSection==="theme")return `<h3>${settingsSection==="locale"?"Dil, Tarih & Para Birimi":"Temalar & Yazı Tipi"}</h3>${common}`;const title=settingsGroups.flatMap(g=>g[1]).find(x=>x[0]===settingsSection)?.[2]||"Ayarlar";return `<h3>${title}</h3><p class="muted">Bu modül masaüstü ayar anahtarlarını kullanır. Değişiklikler ortak veritabanına kaydedilir.</p><div class="form-grid"><div class="field full"><label>Yapılandırma</label><textarea id="setModuleValue" placeholder="${esc(title)} yapılandırması"></textarea></div></div>`}
const settingsDefinitions={
 company:{title:"Firma Ayarları",description:"Firma iletişim, sosyal medya, sözleşme, logo ve proforma bilgileri.",fields:[["company_name","Firma Adı","text","AYEC Pro"],["site_title","Uygulama Başlığı","text","Servis Yönetimi"],["company_email","E-posta","email",""],["company_phone","Telefon","tel",""],["company_gsm","GSM","tel",""],["company_fax","Faks","text",""],["company_website","Web Sitesi","url",""],["company_address","Adres","textarea",""],["social_facebook","Facebook","text",""],["social_instagram","Instagram","text",""],["social_youtube","YouTube","text",""],["cargo_company","Kargo Firması","text",""],["cargo_deal_no","Kargo Anlaşma No","text",""],["stock_prefix","Stok Öneki","text","TO"],["currency_precision","Kur Hassasiyeti","number","2"],["logo_path","Firma Logosu Yolu","text",""],["background_image","Masaüstü Arkaplanı","text",""],["proforma_template_path","Proforma Şablonu","text",""],["proforma_field_rects","Proforma Alan Yerleşimi (JSON)","textarea","{}"],["service_contract","Servis Sözleşmesi","textarea",""],["offer_contract","Teklif Sözleşmesi","textarea",""],["marquee_text","Kayan Yazı","textarea",""],["online_payment_active","Online ödeme aktif","checkbox","1"], ["proforma_include_bank_accounts","Aktif Banka IBAN'lari PDF'e eklensin","checkbox","1"]]},
 locale:{title:"Dil, Tarih & Para Birimi",fields:[["app_lang","Uygulama Dili","select","Türkçe (TR)",["Türkçe (TR)","English (EN)"]],["date_format","Tarih Formatı","select","GG.AA.YYYY (31.12.2025)",["GG.AA.YYYY (31.12.2025)","YYYY-AA-GG (2025-12-31)"]],["default_currency","Aktif Para Birimi","select","TRY",["TRY","USD","EUR"]],["currency_format","Sayı Formatı","select","1.234,56 (TR Standart)",["1.234,56 (TR Standart)","1,234.56 (US)"]],["timezone","Saat Dilimi","select","(UTC+03:00) İstanbul",["(UTC+03:00) İstanbul","UTC"]]]},
 theme:{title:"Temalar & Yazı Tipi",fields:[["color_theme_full","Uygulama Teması","select","AYEC",["AYEC","Light","Dark","Classic"]],["appearance_mode","Görünüm Modu","select","modern",["modern","classic","compact"]],["nav_mode","Navigasyon Düzeni","select","sol_menu",["sol_menu","ust_menu"]],["display_profile","Ekran Profili","select","auto",["auto","laptop","large"]],["custom_accent_color","Özel Vurgu Rengi","color","#6558e8"],["custom_text_color","Özel Metin Rengi","color","#161927"],["combo_auto_popup","ComboBox otomatik açılsın","checkbox","0"],["show_feature_info","Özellikleri kayan yazıda göster","checkbox","1"],["enable_right_click","Genel sağ tık menüsü","checkbox","1"],["ticker_text","Duyuru Şeridi","textarea",""]]},
  "tax-currency":{title:"KDV & Kur Senkronizasyonu",description:"Varsay\u0131lan KDV oran\u0131 ve otomatik kur e\u015fitleme ayarlar\u0131.",fields:[["vat_default_rate","Varsay\u0131lan KDV Oran\u0131","select","20",["20","10","1","0"]],["bank_auto_fx","Otomatik kur g\u00fcncelle","checkbox","1"],["bank_fx_update_minutes","Kur g\u00fcncelleme aral\u0131\u011f\u0131 (dakika)","number","60"],["currency_precision","Kur hassasiyeti","number","4"]]},
 integrations:{title:"Entegrasyonlar & API",description:"SMS, e-posta, WhatsApp, Telegram ve yapay zekâ bağlantıları.",fields:[["sms_username","SMS Kullanıcı Adı","text",""],["sms_password","SMS Şifresi","password",""],["sms_title","SMS Başlığı","text",""],["sms_active","SMS Aktif","checkbox","0"],["smtp_server","SMTP Sunucu","text","smtp.gmail.com"],["smtp_port","SMTP Port","number","587"],["smtp_email","SMTP E-posta","email",""],["smtp_password","SMTP Şifre","password",""],["whatsapp_number","WhatsApp Numarası","tel",""],["whatsapp_api_key","WhatsApp API Anahtarı","password",""],["whatsapp_active","WhatsApp Aktif","checkbox","0"],["telegram_bot_token","Telegram Bot Token","password",""],["gemini_api_key","Gemini API Anahtarı","password",""]]},
 cargo:{title:"Kargo Firma Ayarları",fields:[["cargo_default_company","Varsayılan Kargo","select","Yurtiçi",["Yurtiçi","Aras","MNG","Sürat","PTT"]],["cargo_branch_code","Şube Kodu","text",""],["cargo_sender_name","Gönderici Adı","text",""],["cargo_sender_phone","Gönderici Telefonu","tel",""],["cargo_delivery_days","Tahmini Teslim Günü","number","3"],["cargo_auto_track","Takip numarasını otomatik doğrula","checkbox","1"],["cargo_sms_notify","Kargo çıkışında SMS gönder","checkbox","0"],["cargo_require_receiver","Teslim alacak kişi zorunlu","checkbox","1"]]},
 "stock-settings":{title:"Stok Ayarları",fields:[["stock_min_level","Minimum Stok Seviyesi","number","5"],["stock_reorder_days","Sipariş Öneri Süresi","number","7"],["stock_default_profit_pct","Varsayılan Kâr Yüzdesi","number","20"],["stock_code_prefix","Stok Kod Öneki","text","STK"],["stock_auto_code","Otomatik stok kodu","checkbox","1"],["stock_warn_negative","Negatif stok uyarısı","checkbox","1"],["stock_sync_finance","Finansla senkronize et","checkbox","1"]]},
 backup:{title:"Yedekleme ve Veri Merkezi",fields:[["backup_server_ip","Yedek Sunucu","text","85.117.239.60:8000"],["backup_daily_enabled","Günlük otomatik yedek","checkbox","0"],["backup_daily_time","Yedek Saati","time","12:00"],["backup_auto_morning","Sabah otomatik yedeği","checkbox","0"],["backup_auto_evening","Akşam otomatik yedeği","checkbox","0"],["backup_on_exit","Çıkışta yedek al","checkbox","1"]]},
 license:{title:"Lisans Durumu",fields:[["license_key","Lisans Anahtar\u0131","text",""],["license_code","Lisans Kodu","text",""],["license_expires","Biti\u015f Tarihi","date",""]]},
 security:{title:"Güvenlik Ayarları",description:"Boş bırakılan şifre alanları mevcut şifreyi değiştirmez.",fields:[["app_password","Yeni Uygulama Şifresi","password",""],["tech_password","Yeni Teknisyen Şifresi","password",""],["admin_pass","Yeni Yönetici Şifresi","password",""],["security_question","Güvenlik Sorusu","text",""],["security_answer_new","Yeni Güvenlik Yanıtı","password",""],["app_lock_active","Uygulama kilidi","checkbox","0"],["tech_lock_active","Teknisyen kilidi","checkbox","0"],["auto_login","Otomatik giriş","checkbox","0"]]},
 remote:{title:"AYEC Pro Uzak Bağlantı",fields:[["remote_server_ip","Sunucu IP","text","85.117.239.60"],["remote_server_port","Sunucu Portu","number","5000"],["remote_enabled","Uzak bağlantı aktif","checkbox","1"],["remote_logging","Bağlantı logları","checkbox","1"]]},
 "sms-settings":{title:"SMS Ayarları",fields:[["sms_username","Kullanıcı Adı","text",""],["sms_password","Şifre","password",""],["sms_title","Gönderici Başlığı","text",""],["loop_repaired","Onarıldı tekrar sayısı","number","0"],["loop_approval","Onay tekrar sayısı","number","0"],["loop_parts","Parça bekliyor tekrar sayısı","number","0"],["loop_testing","Test tekrar sayısı","number","0"],["loop_done","Tamamlandı tekrar sayısı","number","0"],["sms_active","SMS servisi aktif","checkbox","0"]]},
 "smtp-settings":{title:"E-posta / SMTP",fields:[["smtp_server","SMTP Sunucu Hostu","text","srvm07.trwww.com"],["smtp_port","Port No","number","465"],["smtp_email","Gonderen E-posta Adresi","email","info@ayecpro.com"],["smtp_sender_name","Gonderen Adi / Firma Basligi","text","AYEC Pro Teknik Servis Hizmetleri"],["smtp_password","E-posta Parolasi","password",""],["smtp_timeout","Zaman Asimi (sn)","number","15"],["smtp_test_recipient","Hedef Test E-posta Adresi","email","destek@ayecpro.com"],["smtp_auth_required","Kimlik Dogrulama Zorunlu","checkbox","1"],["smtp_auto_bcc","Arsiv E-postasina BCC","checkbox","1"]]},
 messaging:{title:"WhatsApp & Telegram",fields:[["whatsapp_number","WhatsApp Numarası","tel",""],["whatsapp_mode","WhatsApp gönderim modu","select","disabled",["disabled","cloud_api","provider_api","desktop_manual"]],["whatsapp_cloud_phone_id","Meta Cloud phone ID","text",""],["whatsapp_cloud_token","Meta Cloud access token","password",""],["whatsapp_cloud_template","Cloud sablon adi","text","payment_reminder_tr"],["twilio_account_sid","Saglayici Account SID","text",""],["twilio_auth_token","Saglayici Auth Token","password",""],["twilio_whatsapp_from","Saglayici gonderici","text",""],["whatsapp_payment_reminder_enabled","Haftalik odeme hatirlatmasi","checkbox","0"],["whatsapp_payment_reminder_day","Hatirlatma gunu","number","4"],["whatsapp_payment_reminder_time","Hatirlatma saati","time","10:00"],["whatsapp_payment_min_debt_try","Asgari borc (TRY)","number","0"],["whatsapp_payment_template","Odeme sablonu","textarea","Merhaba {musteri_adi}, {firma_adi} hesabinizda {borc_tutari} TRY borc bulunuyor."],["whatsapp_api_key","WhatsApp API Anahtarı","password",""],["whatsapp_admin_phone","Yönetici WhatsApp","tel",""],["whatsapp_api_token","WhatsApp API Token","password",""],["telegram_bot_token","Telegram Bot Token","password",""],["whatsapp_active","WhatsApp aktif","checkbox","0"]]},
 "ai-settings":{title:"Gemini / AI Ayarlari",fields:[["gemini_api_key","Gemini API Anahtari","password",""],["gemini_model","Gemini Modeli","text","gemini-2.0-flash"],["gemini_available_models_cache","Model Onbellegi","textarea",""]]},
 "autonomous-agents":{title:"Otonom Ajanlar ve Entegrasyon Hub",fields:[["jarvis_enabled","Jarvis modu aktif","checkbox","1"],["agent_auto_start","Arka plan ajanlarini otomatik baslat","checkbox","1"],["agent_whatsapp_reports","Otomatik WhatsApp raporlari","checkbox","0"],["agent_voice_feedback","Sesli geri bildirim","checkbox","1"],["agent_model","Aktif model","text","gemini-3.6-flash"]]},
 "voice-settings":{title:"Sesli Asistan ve Zamanlanmış Uyarılar",fields:[["asistan_user_name","Kullanıcı Hitabı","text","Efendim"],["asistan_ozel_adi","Asistan Adı","text","AYEC"],["asistan_edge_voice","Ses","text","tr-TR-AhmetNeural"],["asistan_edge_pitch","Ton","text","-5Hz"],["asistan_edge_rate","Hız","text","+0%"],["asistan_tts_engine","TTS Motoru","select","auto",["auto","edge","system"]],["quiet_hours_start","Sessiz Saat Başlangıcı","time","19:00"],["quiet_hours_end","Sessiz Saat Bitişi","time","08:30"],["voice_assistant_active","Sesli asistan aktif","checkbox","1"],["jarvis_enabled","JARVIS modu aktif","checkbox","0"],["asistan_voice_enabled","Sesli yanıt aktif","checkbox","1"],["telsiz_efekti_aktif","Telsiz efekti","checkbox","0"],["asistan_hitap_aktif","Özel hitap","checkbox","0"],["critical_override_dnd","Kritik uyarı sessiz modu aşsın","checkbox","0"]]},
 "bank-settings":{title:"Banka Ayarları",fields:[["bank_default_name","Varsayılan Banka","text",""],["bank_default_iban","Varsayılan IBAN","text",""],["bank_default_currency","Para Birimi","select","TRY",["TRY","USD","EUR"]],["bank_fx_update_minutes","Kur Güncelleme Süresi","number","60"],["bank_auto_fx","Otomatik kur güncelle","checkbox","1"],["bank_sync_finance","Finansla eşleştir","checkbox","1"],["bank_warn_negative","Negatif bakiye uyarısı","checkbox","1"]]},
 numbering:{title:"Belge Numaraları",fields:[["service_number_prefix","Servis Öneki","text","SRV"],["service_number_next","Sonraki Servis No","number","1"],["job_number_prefix","İş Emri Öneki","text","IS"],["job_number_next","Sonraki İş Emri No","number","1"],["payment_number_prefix","Tahsilat Öneki","text","THS"],["payment_number_next","Sonraki Tahsilat No","number","1"],["project_number_prefix","Proje Öneki","text","PRJ"],["project_number_next","Sonraki Proje No","number","1"],["reference_number_prefix","Referans Öneki","text","REF"],["reference_number_next","Sonraki Referans No","number","1"]]},
 location:{title:"Harita & Konum",fields:[["map_default_lat","Varsayılan Enlem","number","40.1044116"],["map_default_lng","Varsayılan Boylam","number","27.6563981"]]},
 identity:{title:"Sistem Kimli\u011fi & Mod\u00fcler Yap\u0131",scope:"internal_settings",fields:[["module_operations_active","Operasyon Mod\u00fcl\u00fc","checkbox","1"],["module_finance_active","Finans Mod\u00fcl\u00fc","checkbox","1"],["module_stock_active","Stok Mod\u00fcl\u00fc","checkbox","1"],["module_projects_active","Projeler Mod\u00fcl\u00fc","checkbox","1"],["module_crm_active","CRM Mod\u00fcl\u00fc","checkbox","1"],["module_personnel_active","Personel Mod\u00fcl\u00fc","checkbox","1"],["feature_right_click_active","Sa\u011f T\u0131k \u00d6zelli\u011fi","checkbox","1"],["feature_double_click_active","\u00c7ift T\u0131klama \u00d6zelli\u011fi","checkbox","1"]]}
};
settingsDefinitions.integrations.fields.splice(7,0,["smtp_username","SMTP Kullanıcı Adı","text",""]);
settingsDefinitions["smtp-settings"].fields.splice(3,0,["smtp_username","SMTP Kullanıcı Adı","text",""]);
function exactSettingsField(field,scope){const [key,label,type,defaultValue,options]=field,source=scope==="internal_settings"?desktopInternalSettings:desktopSettings,value=type==="password"?"":source[key]??defaultValue,attrs=`data-setting-key="${key}" data-setting-scope="${scope}"`;if(type==="checkbox")return `<div class="setting"><div><strong>${label}</strong><br><small class="muted">Masaüstü ayarı: ${key}</small></div><input class="switch exact-setting" ${attrs} type="checkbox" ${String(value)==="1"||String(value)==="true"?"checked":""}></div>`;if(type==="textarea")return `<div class="field full"><label>${label}</label><textarea class="exact-setting" ${attrs}>${esc(value)}</textarea></div>`;if(type==="select")return `<div class="field"><label>${label}</label><select class="exact-setting" ${attrs}>${options.map(option=>`<option value="${esc(option)}" ${String(value)===String(option)?"selected":""}>${esc(option)}</option>`).join("")}</select></div>`;return `<div class="field"><label>${label}</label><input class="exact-setting" ${attrs} type="${type}" value="${esc(value)}" ${type==="password"?'autocomplete="new-password" placeholder="Boş bırakırsanız değişmez"':""}></div>`}
const baseSettingBody=settingBody;settingBody=function(s){if(settingsSection==="sms-settings")return renderPart9SmsProvider();if(settingsSection==="sms-templates")return renderPart9SmsTemplates();if(settingsSection==="users")return `<div class="card-head"><div><h3>Kullan\u0131c\u0131 Y\u00f6netimi</h3><p class="muted">Masa\u00fcst\u00fc kullan\u0131c\u0131, rol, aktiflik ve aray\u00fcz yetkileri.</p></div></div><div id="settingsUsersHost">${empty("Kullan\u0131c\u0131lar y\u00fckleniyor","Ortak kullan\u0131c\u0131 tablosu okunuyor.")}</div>`;const definition=settingsDefinitions[settingsSection];if(!definition)return baseSettingBody(s);const scope=definition.scope||"settings",regular=definition.fields.filter(f=>f[2]!=="checkbox"),toggles=definition.fields.filter(f=>f[2]==="checkbox");if(settingsSection==="messaging"){const keys=(items)=>new Set(items),protocol=keys(["whatsapp_mode","whatsapp_number","whatsapp_cloud_phone_id","whatsapp_cloud_token","whatsapp_cloud_template","twilio_account_sid","twilio_auth_token","twilio_whatsapp_from"]),reminders=keys(["whatsapp_payment_template","whatsapp_payment_reminder_day","whatsapp_payment_reminder_time","whatsapp_payment_min_debt_try"]),fields=(set)=>definition.fields.filter(f=>set.has(f[0])).map(f=>exactSettingsField(f,scope)).join(""),switches=definition.fields.filter(f=>f[2]==="checkbox").map(f=>exactSettingsField(f,scope)).join("");return `<h3>${definition.title}</h3><p class="muted">${definition.description||""}</p><div class="messaging-settings-grid"><section class="messaging-settings-card"><h4>WhatsApp protocol</h4><div class="form-grid">${fields(protocol)}</div></section><section class="messaging-settings-card"><h4>Telegram and legacy connection</h4><div class="form-grid">${fields(keys(["whatsapp_api_key","whatsapp_admin_phone","whatsapp_api_token","telegram_bot_token"]))}</div></section><section class="messaging-settings-card messaging-settings-reminders"><h4>Payment reminders</h4><div class="form-grid">${fields(reminders)}</div></section><section class="messaging-settings-card messaging-settings-toggles"><h4>Service status</h4><div class="settings-grid">${switches}</div></section></div>`}return `<h3>${definition.title}</h3>${definition.description?`<p class="muted">${definition.description}</p>`:""}<div class="form-grid">${regular.map(f=>exactSettingsField(f,scope)).join("")}</div>${toggles.length?`<div class="settings-grid" style="margin-top:18px">${toggles.map(f=>exactSettingsField(f,scope)).join("")}</div>`:""}${settingsSection==="backup"?'<div class="actions" style="margin-top:18px"><button class="secondary" data-action="export-all">\u015eimdi Yedekle</button><button class="secondary" data-action="restore-backup">Yede\u011fi Geri Y\u00fckle</button></div>':""}`};
function renderSettings(){const s=db.settings,mobileSettings=settingsGroups.flatMap(([,items])=>items).map(([id,,label])=>`<option value="${id}" ${settingsSection===id?"selected":""}>${label}</option>`).join("");return `${pageHead("Ayarlar","Masaüstü uygulamasındaki ayar modülleri ve ortak veri merkezi.",'<button class="primary" data-action="save-settings">Ayarları Kaydet</button>')}<div class="settings-layout"><div class="settings-mobile-picker"><label for="settingsMobileSelect">Ayar bölümü</label><select id="settingsMobileSelect">${mobileSettings}</select></div><aside class="settings-sidebar"><input class="control" id="settingsSearch" placeholder="Ayarlarda ara…">${settingsGroups.map(([group,items])=>`<small>${group}</small>${items.map(([id,icon,label])=>`<button data-settings-section="${id}" class="${settingsSection===id?"active":""}">${icon} ${label}</button>`).join("")}`).join("")}</aside><section class="card settings-content">${settingBody(s)}</section></div><div hidden><input id="setCompany" value="${esc(s.company)}"><input id="setCurrency" value="${s.currency}"><input id="setAlertMinutes" value="${s.alertMinutes}"><input id="setDouble" type="checkbox" ${s.doubleClick?"checked":""}><input id="setContext" type="checkbox" ${s.contextMenu?"checked":""}><input id="setAlerts" type="checkbox" ${s.appointmentAlerts?"checked":""}><input id="setCompact" type="checkbox" ${s.compact?"checked":""}></div>`}

function genericShell(meta){if(meta.table==="services")return `${pageHead(meta.title,meta.description,'<button class="secondary" data-generic-refresh>Yenile</button><button class="secondary" data-labor-bulk>Toplu Fiyat G\u00fcncelle</button><button class="secondary" data-labor-export>Excel</button><button class="secondary" data-labor-pdf>PDF</button><button class="secondary" data-labor-print>Yazd\u0131r</button><button class="primary" data-generic-add>\uff0b Yeni Hizmet &amp; \u0130\u015f\u00e7ilik Ekle</button>')}<section class="card labor-services-card"><div class="labor-toolbar"><input class="control search" id="genericSearch" placeholder="Hizmet ad\u0131, i\u015flem kodu (#SRV), barkod veya a\u00e7\u0131klama ara..."><div class="labor-filter-pills"><button class="active" data-labor-category="all">T\u00fcm\u00fc</button><button data-labor-category="Donan\u0131m &amp; Lehim">Donan\u0131m &amp; Lehim</button><button data-labor-category="Yaz\u0131l\u0131m &amp; Kurulum">Yaz\u0131l\u0131m &amp; Kurulum</button><button data-labor-category="Periyodik Bak\u0131m">Periyodik Bak\u0131m</button><button data-labor-category="Saha &amp; Montaj">Saha &amp; Montaj</button></div></div><div class="muted labor-count" id="genericCount">Y\u00fckleniyor\u2026</div><div id="genericHost">${empty("Veriler y\u00fckleniyor","Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div></section>`;if(meta.table==="fast_notes")return `${pageHead(meta.title,meta.description,'<button class="secondary" data-generic-refresh>Yenile</button><details class="report-template-transfer"><summary>&#8645; &#304;&#231;e/D&#305;&#351;a Aktar</summary><div><button type="button" data-template-import>&#8615; &#304;&#231;e Aktar</button><button type="button" data-template-export>&#8613; D&#305;&#351;a Aktar</button><input type="file" accept=".csv,text/csv" data-template-file hidden></div></details><button class="secondary" data-generic-manage>&#350;ablonlar&#305; Y&#246;net</button><button class="primary" data-generic-add>\uff0b Yeni C&#252;mle Kal&#305;b&#305; Ekle</button>')}<section class="report-template-categories" aria-label="&#350;ablon kategorileri"><button class="active" data-template-category="all">\u25b0 T&#252;m&#252; <span id="templateTotal">0</span></button><button data-template-category="issue">\u25cf Ar&#305;za H&#305;zl&#305; Se&#231;imi <span>0</span></button><button data-template-category="detail">\u25cf &#304;&#351;lem Detaylar&#305; <span>0</span></button><button data-template-category="device">\u25cf Cihaz Testi &amp; Donan&#305;m <span>0</span></button><button data-template-category="accessory">\u25cf Aksesuar Bilgileri <span>0</span></button><button data-template-category="internal">\u25cf Dahili Gizli Not <span>0</span></button></section><section class="report-template-layout"><div class="report-template-list"><div class="report-template-filters"><input class="control search" id="genericSearch" placeholder="Kategori, cihaz t&#252;r&#252; veya kal&#305;p metni ara..."><label>Cihaz:<select id="templateDeviceFilter"><option value="">T&#252;m Cihazlar</option><option>Bilgisayar</option><option>Cep Telefonu</option><option>Tablet</option></select></label><label>Durum:<select id="templateStatusFilter"><option value="">T&#252;m Durumlar</option><option value="active">Aktif Kal&#305;plar</option><option value="inactive">Pasif Kal&#305;plar</option></select></label><button class="secondary" data-generic-refresh aria-label="Filtreleri yenile">&#8635;</button></div><div class="report-template-table" id="genericHost">${empty("Veriler y&#252;kleniyor","Masa&#252;st&#252; veritaban&#305; okunuyor.")}</div><div class="muted report-template-count" id="genericCount">Y&#252;kleniyor...</div></div><aside class="report-template-preview"><div class="report-template-preview-head">&#9673; &nbsp; CANLI &#199;IKTI &#214;N&#304;ZLEME <span>Se&#231;ili &#350;ablon</span></div><article class="report-template-receipt"><strong>ASLAN COMPUTER</strong><small>AYEC PRO TEKN&#304;K SERV&#304;S F&#304;&#350;&#304;</small><hr><p>M&#252;&#351;teri: <b>\u2014</b></p><p>Cihaz: <b>\u2014</b></p><div class="report-template-preview-text">&#214;nizlemek i&#231;in bir &#351;ablon se&#231;in.</div></article><section class="report-template-stats"><strong>&#350;ablon &#304;statistikleri</strong><div><span>Toplam &#350;ablon<strong id="templateStatTotal">0</strong></span><span>Aktif Kal&#305;p<strong id="templateStatActive">0</strong></span></div></section></aside></section>`;return `${pageHead(meta.title,meta.description,'<button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-generic-add>\uff0b Yeni Kay\u0131t</button>')}<section class="card"><div class="toolbar"><input class="control search" id="genericSearch" placeholder="Bu mod\u00fclde ara\u2026"><span class="muted" id="genericCount">Y\u00fckleniyor\u2026</span></div><div id="genericHost">${empty("Veriler y\u00fckleniyor","Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div></section>`}
function columnLabel(name){return ({id:"NO",name:"AD",customer_name:"MÜŞTERİ",customer_id:"MÜŞTERİ NO",phone:"TELEFON",email:"E-POSTA",type:"TÜR",status:"DURUM",date:"TARİH",time:"SAAT",created_at:"OLUŞTURMA",description:"AÇIKLAMA",amount:"TUTAR",currency:"DÖVİZ",stock:"STOK",price:"FİYAT",category:"KATEGORİ",title:"BAŞLIK",role:"ROL"}[name]||name.replaceAll("_"," ").toLocaleUpperCase("tr-TR"))}
function genericValue(value,key){if(value===null||value===undefined||value==="")return '<span class="muted">—</span>';if(key==="status"||key==="type")return statusBadge(value);if(typeof value==="string"&&value.length>100)return esc(value.slice(0,100))+"…";return esc(value)}
function laborServicesTable(rows,allRows=rows){const active=allRows.filter(row=>Number(row.is_active)!==0).length,average=allRows.length?allRows.reduce((sum,row)=>sum+Number(row.price_try||0),0)/allRows.length:0,categories=["Donan\u0131m & Lehim","Yaz\u0131l\u0131m & Kurulum","Periyodik Bak\u0131m","Saha & Montaj"],counts=Object.fromEntries(categories.map(category=>[category,allRows.filter(row=>row.service_category===category).length]));const metrics=`<div class="labor-metrics"><article><small>TOPLAM H\u0130ZMET TANIMI</small><strong>${allRows.length}</strong><span>Katalogda kay\u0131tl\u0131</span></article><article><small>AKT\u0130F F\u0130YAT L\u0130STES\u0130</small><strong>${active}</strong><span>${allRows.length-active} pasif ar\u015fivde</span></article><article><small>ORTALAMA \u0130\u015e\u00c7\u0130L\u0130K \u00dcCRET\u0130</small><strong>${money(average,"TRY")}</strong><span>KDV hari\u00e7 net baz \u00fccret</span></article><article><small>EN \u00c7OK KULLANILAN \u0130\u015e\u00c7\u0130L\u0130K</small><strong>Termal Macun &amp; Fan Temizli\u011fi</strong><span>148 servis kayd\u0131 \u00b7 t\u00fcm i\u015flerin %34'\u00fc</span></article></div>`;const header=`<div class="table-wrap labor-table-wrap"><table class="labor-services-table"><thead><tr><th></th><th>\u0130\u015eLEM KODU</th><th>H\u0130ZMET / OPERASYON TANIMI</th><th>KATEGOR\u0130</th><th>ORT. S\u00dcRE</th><th>TABAN \u00dcCRET (TL)</th><th>D\u00d6V\u0130Z BAZI</th><th>KDV</th><th>DURUM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>`;const body=rows.map((row,index)=>`<tr class="${Number(row.is_active)===0?"inactive":""}" data-kind="generic" data-id="${index}" data-generic-row="${index}"><td><input type="checkbox" aria-label="${esc(row.name)} se\u00e7"></td><td><code>${esc(row.barcode||`#SRV-${String(row.id).padStart(3,"0")}`)}</code></td><td><strong>${esc(row.name)}</strong>${row.barcode==="#SRV-101"?'<em>Pop\u00fcler</em>':row.barcode==="#SRV-204"?'<em>\u0130leri D\u00fczey</em>':""}<small>${esc(row.description||"")}</small></td><td><span class="labor-category">${esc(row.service_category||"Donan\u0131m & Lehim")}</span></td><td>${Number(row.duration_minutes||60)} Dk</td><td><b>${money(row.price_try||0,"TRY")}</b></td><td>${money(row.price_usd||0,"USD")}</td><td>%${Number(row.vat_rate||20)}</td><td><button class="labor-status" data-labor-toggle="${index}">${Number(row.is_active)===0?"Pasif":"Aktif"}</button></td><td><button class="mini generic-edit" data-index="${index}" aria-label="D\u00fczenle">\u270e</button> <button class="mini generic-delete" data-index="${index}" aria-label="Sil">\u232b</button></td></tr>`).join("");return metrics+header+body+`</tbody></table></div>`}
function bindLaborServiceFilters(){if(!window.currentGenericData||window.currentGenericMeta?.table!=="services")return;const source=window.currentGenericData.rows||[],query=( $("#genericSearch")?.value||"").trim().toLocaleLowerCase("tr-TR");const category=window.laborServiceCategory||"all";const filtered=source.filter(row=>(category==="all"||row.service_category===category)&&(!query||[row.name,row.barcode,row.description].some(value=>String(value||"").toLocaleLowerCase("tr-TR").includes(query))));$("#genericHost").innerHTML=laborServicesTable(filtered,source);$("#genericCount").textContent=`Toplam ${source.length} kay\u0131t \u00b7 ${filtered.length} g\u00f6steriliyor`;$$('[data-labor-category]').forEach(button=>{const key=button.dataset.laborCategory;button.textContent=`${key} (${key==="all"?source.length:source.filter(row=>row.service_category===key).length})`;button.classList.toggle("active",key===category);button.onclick=()=>{window.laborServiceCategory=key;bindLaborServiceFilters()}});$$('.generic-edit').forEach(button=>button.onclick=()=>{const row=filtered[+button.dataset.index];openGenericDialog(window.currentGenericMeta,row,window.currentGenericData.columns)});$$('.generic-delete').forEach(button=>button.onclick=()=>deleteGenericRow(window.currentGenericMeta,filtered[+button.dataset.index]));$$('[data-labor-toggle]').forEach(button=>button.onclick=async()=>{const row=filtered[+button.dataset.laborToggle];row.is_active=Number(row.is_active)===0?1:0;await apiFetch(`/api/desktop/table/services`,{method:"POST",body:JSON.stringify({id:row.id,is_active:row.is_active,_action:"update"})});bindLaborServiceFilters()})}
function genericTable(meta,data){if(meta.table==="services")return laborServicesTable(data.rows);const preferred=["id","tracking_no","name","title","customer_name","phone","type","category","status","date","time","amount","currency","stock","price","description","created_at"];let columns=preferred.filter(c=>data.columns.includes(c)&&data.rows.some(r=>r[c]!==null&&r[c]!==""));for(const c of data.columns){if(columns.length>=9)break;if(!columns.includes(c)&&!c.includes("password")&&!c.includes("token")&&!c.includes("secret")&&!c.includes("photo"))columns.push(c)}return `<div class="table-wrap"><table><thead><tr>${columns.map(c=>`<th>${columnLabel(c)}</th>`).join("")}<th>İŞLEMLER</th></tr></thead><tbody>${data.rows.map((row,index)=>`<tr tabindex="0" data-kind="generic" data-id="${index}" data-generic-row="${index}">${columns.map(c=>`<td>${genericValue(row[c],c)}</td>`).join("")}<td><button class="mini generic-edit" data-index="${index}">Düzenle</button> <button class="mini generic-delete" data-index="${index}">Sil</button></td></tr>`).join("")}</tbody></table></div>`}
function reportTemplateGroup(row){const category=String(row.category||"").toLocaleLowerCase("tr-TR");if(category.includes("aksesuar"))return "accessory";if(category.includes("gizli"))return "internal";if(category.includes("cihaz testi")||category.includes("donan\u0131m"))return "device";if(category.includes("i\u015flem detayi")||category.includes("i\u015flem detay\u0131"))return "detail";if(category.includes("ar\u0131za"))return "issue";return "other"}
function reportTemplateDevice(row){const parts=String(row.category||"").split("::");return parts.length>=3?parts.at(-2).trim():""}
function reportTemplatesTable(data){const rows=data.rows||[];return `<div class="table-wrap"><table><thead><tr><th>#</th><th></th><th>KATEGOR&#304; &amp; KAPSAM</th><th>C&#220;MLE KALIBI / HAZIR MET&#304;N</th><th>KULLANIM ALANI</th><th>KISAYOL</th><th>DURUM</th><th>&#304;&#350;LEMLER</th></tr></thead><tbody>${rows.map((row,index)=>{const parts=String(row.category||"").split("::").map(value=>value.trim()).filter(Boolean),scope=parts.length>=3?parts.slice(0,2).join("::"):row.category||"Genel",categoryName=parts.length>=3?parts.at(-1):"",usage=row.display_category||"",shortcut=row.title||"-";return `<tr data-template-row="${index}" class="${window.reportTemplateSelected===index?"selected":""}"><td><code>${String(Number(row.display_order)||index+1).padStart(2,"0")}</code></td><td class="report-template-grip">&#10247;</td><td><div class="report-template-scope-wrap"><span class="report-template-scope">${esc(scope)}</span><b>&#8250;</b><strong>${esc(categoryName)}</strong></div></td><td><strong>${esc(row.label||"")}</strong></td><td>${esc(usage)}</td><td><kbd>${esc(shortcut)}</kbd></td><td><span class="report-template-status ${Number(row.is_active)===0?"inactive":""}">${Number(row.is_active)===0?"Pasif":"Aktif"}</span></td><td class="report-template-row-actions"><button class="mini" type="button" data-template-edit="${index}" aria-label="D&#252;zenle">&#9998;</button><button class="mini" type="button" data-template-delete="${index}" aria-label="Sil">&#8942;</button></td></tr>`}).join("")}</tbody></table></div>`}
function bindReportTemplateRows(meta,data){const rows=data.rows||[];const all=window.currentGenericData?.rows||rows;const active=all.filter(row=>Number(row.is_active)!==0).length;$("#templateTotal").textContent=String(data.count??all.length);$("#templateStatTotal").textContent=String(data.count??all.length);$("#templateStatActive").textContent=String(active);$("#genericCount").textContent=`${data.count??all.length} kay\u0131ttan ${rows.length?1:0} - ${rows.length} aras\u0131 g\u00f6steriliyor`;const selected=window.reportTemplateSelected;$$("[data-template-row]").forEach(tr=>{const row=rows[+tr.dataset.templateRow];tr.onclick=()=>{window.reportTemplateSelected=+tr.dataset.templateRow;$$('[data-template-row]').forEach(item=>item.classList.toggle("selected",item===tr));const receipt=$(".report-template-preview-text");if(receipt)receipt.textContent=row.label||"";const heading=$(".report-template-preview-head span");if(heading)heading.textContent=`Se\u00e7ili \u015eablon #${String(row.id??+tr.dataset.templateRow+1).padStart(2,"0")}`;const customer=$(".report-template-receipt p:first-of-type b");if(customer)customer.textContent=row.category||"Genel";tr.ondblclick=()=>openGenericDialog(meta,row,data.columns);bindInteractiveRow(tr);const editButton=tr.querySelector("[data-template-edit]");if(editButton)editButton.onclick=event=>{event.stopPropagation();openGenericDialog(meta,row,data.columns)};const deleteButton=tr.querySelector("[data-template-delete]");if(deleteButton)deleteButton.onclick=event=>{event.stopPropagation();deleteGenericRow(meta,row)}};tr.ondblclick=()=>openGenericDialog(meta,row,data.columns);bindInteractiveRow(tr)});if(selected!==undefined&&selected<rows.length)$("[data-template-row]")?.click();const applyFilters=()=>{const category=window.reportTemplateCategory||"all",device=$("#templateDeviceFilter")?.value||"",status=$("#templateStatusFilter")?.value||"";const filtered=all.filter(row=>(category==="all"||reportTemplateGroup(row)===category)&&(!device||reportTemplateDevice(row).toLocaleLowerCase("tr-TR").includes(device.toLocaleLowerCase("tr-TR")))&&(!status||(status==="active"?Number(row.is_active)!==0:Number(row.is_active)===0)));const host=$("#genericHost");host.innerHTML=filtered.length?reportTemplatesTable({...data,rows:filtered}):empty("Kay\u0131t bulunamad\u0131","Se\u00e7ili filtrelerde \u015fablon yok.");$("#genericCount").textContent=`${filtered.length} / ${all.length} \u015fablon g\u00f6steriliyor`;bindReportTemplateRows(meta,{...data,rows:filtered})};$$('[data-template-category]').forEach(button=>{const category=button.dataset.templateCategory,matched=all.filter(row=>category==="all"||reportTemplateGroup(row)===category).length;const counter=button.querySelector("span");if(counter)counter.textContent=String(matched);button.onclick=()=>{window.reportTemplateCategory=category;$$('[data-template-category]').forEach(item=>item.classList.toggle("active",item===button));applyFilters()}});const deviceFilter=$("#templateDeviceFilter"),statusFilter=$("#templateStatusFilter");if(deviceFilter)deviceFilter.onchange=applyFilters;if(statusFilter)statusFilter.onchange=applyFilters;const exporter=$("[data-template-export]");if(exporter)exporter.onclick=()=>download("rapor-cumle-kaliplari.csv",csv(all));const importer=$("[data-template-import]"),fileInput=$("[data-template-file]");if(importer&&fileInput){importer.onclick=()=>fileInput.click();fileInput.onchange=async()=>{const file=fileInput.files?.[0];if(!file)return;try{const lines=(await file.text()).replace(/^\ufeff/,"").split(/\r?\n/).filter(Boolean),separator=lines[0].includes(";")?";":",",cells=line=>{const result=[];let value="",quoted=false;for(let i=0;i<line.length;i++){const char=line[i];if(char==='"'&&line[i+1]==='"'&&quoted){value+='"';i++;continue}if(char==='"'){quoted=!quoted;continue}if(char===separator&&!quoted){result.push(value.trim());value=""}else value+=char}result.push(value.trim());return result},headers=cells(lines[0]).map(value=>value.toLocaleLowerCase("tr-TR")),indexOf=(...names)=>headers.findIndex(header=>names.some(name=>header.includes(name))),rows=lines.slice(1).map(line=>{const values=cells(line),get=(...names)=>{const i=indexOf(...names);return i<0?"":values[i]||""},active=get("aktif","is_active","status");return{category:get("kategori & kapsam","category & scope","scope","kapsam","kategori")||"Genel",label:get("kal\u0131p","kalip","c\u00fcmle kal\u0131b\u0131","cumle kalibi","haz\u0131r metin","hazir metin","label","metin"),display_category:get("kullan\u0131m alan\u0131","kullanim alani","display_category","use area"),title:get("k\u0131sayol","kisayol","shortcut"),display_order:Number(get("s\u0131ra","sira","no","order"))||0,is_active:/^(pasif|inactive|0|false)$/i.test(active)?0:1}}).filter(row=>row.label);if(!rows.length)throw new Error("CSV dosyas\u0131nda aktar\u0131labilir kal\u0131p bulunamad\u0131.");for(const row of rows)await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify(row)});toast(`${rows.length} \u015fablon i\u00e7e aktar\u0131ld\u0131`);await loadGenericModule(meta,$("#genericSearch")?.value||"")}catch(error){toast(error.message||"CSV dosyas\u0131 okunamad\u0131","error")}finally{fileInput.value=""}}}const manage=$("[data-generic-manage]");if(manage)manage.onclick=()=>openDialog("\u015eablonlar\u0131 Y\u00f6net","RAPOR C\u00dcMLE KALIPLARI",`<p class="muted">${all.length} \u015fablon, ${active} aktif kal\u0131p.</p><div class="table-wrap">${reportTemplatesTable({...data,rows:all})}</div>`,()=>true,"Tamam")}
async function loadGenericModule(meta,q=""){const host=$("#genericHost");if(!host)return;try{const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=500&q=${encodeURIComponent(q)}`);window.currentGenericData=data;window.currentGenericMeta=meta;if(meta.table==="services")window.laborServiceCategory="all";host.innerHTML=data.rows.length?(meta.table==="fast_notes"?reportTemplatesTable(data):genericTable(meta,data)):empty("Kay\u0131t bulunamad\u0131","Masa\u00fcst\u00fc veritaban\u0131nda bu mod\u00fcle ait kay\u0131t yok.");$("#genericCount").textContent=`Toplam Kay\u0131t: ${data.count}`;if(meta.table==="fast_notes")bindReportTemplateRows(meta,data);if(meta.table==="services")bindLaborServiceFilters();$$(".generic-edit").forEach(b=>b.onclick=()=>openGenericDialog(meta,data.rows[+b.dataset.index],data.columns));$$(".generic-delete").forEach(b=>b.onclick=()=>deleteGenericRow(meta,data.rows[+b.dataset.index]));$$('[data-generic-row]').forEach(tr=>{tr.ondblclick=()=>openGenericDialog(meta,data.rows[+tr.dataset.genericRow],data.columns);bindInteractiveRow(tr)})}catch(err){host.innerHTML=empty("Mod\u00fcl y\u00fcklenemedi",err.message)}}
async function loadQuickNotes(){const host=$("#quickNotesHost");if(!host)return;try{const data=await apiFetch("/api/desktop/table/fast_notes?limit=200");const selectedCategory=$("#quickNoteFilter")?.value||"";const query=($("#quickNoteSearch")?.value||"").trim().toLocaleLowerCase("tr-TR");const selectedTag=$(".quick-note-tags [data-note-tag].active")?.dataset.noteTag||"";const rows=data.rows.filter(n=>{const category=n.display_category||n.category||"";const text=`${category} ${n.title||""} ${n.label||""}`.toLocaleLowerCase("tr-TR");return(!selectedCategory||category===selectedCategory)&&(!query||text.includes(query))&&(!selectedTag||text.includes(selectedTag.toLocaleLowerCase("tr-TR")))});const count=data.rows.filter(n=>n.is_active).length;$("#quickNoteCount").textContent=`${count} \u015eablon Aktif`;host.innerHTML=rows.length?`<div class="table-wrap"><table class="quick-notes-table"><thead><tr><th>ID</th><th>KATEGOR\u0130</th><th>NOT \u0130\u00c7ER\u0130\u011e\u0130</th><th>SIRA</th><th>DURUM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${rows.map((n,i)=>{const category=n.display_category||n.category||"Di\u011fer";const body=String(n.label||"");const alert=body.toLocaleUpperCase("tr-TR").includes("KIRIK")?"note-broken":body.toLocaleUpperCase("tr-TR").includes("KAMERA")?"note-camera":"";const categoryClass=category.toLocaleLowerCase("tr-TR").includes("telefon")?"phone":category.toLocaleLowerCase("tr-TR").includes("g\u00fcvenlik")?"security":"computer";return`<tr><td data-label="ID">${n.id}</td><td data-label="Kategori"><span class="note-category ${categoryClass}">${esc(category)}</span><span class="muted"> :: </span><strong>${esc(n.title||"")}</strong></td><td data-label="Not i\u00e7eri\u011fi" class="${alert}">${esc(body)}</td><td data-label="S\u0131ra">${Number(n.display_order)||0}</td><td data-label="Durum"><label class="quick-note-status"><span>${n.is_active?"Aktif":"Pasif"}</span><input class="switch quick-note-toggle" type="checkbox" data-index="${i}" ${n.is_active?"checked":""}></label></td><td data-label="\u0130\u015flemler"><button class="mini quick-note-edit" data-index="${i}" aria-label="D\u00fczenle">&#9998;</button><button class="mini quick-note-delete" data-index="${i}" aria-label="Sil">&#128465;</button></td></tr>`}).join("")}</tbody></table></div>`:empty("Not bulunamad\u0131","Filtreyi temizleyin veya yeni bir not ekleyin.");$("#quickNoteFilter").onchange=loadQuickNotes;$("#quickNoteSearch").oninput=loadQuickNotes;$$('.quick-note-tags [data-note-tag]').forEach(button=>button.onclick=()=>{button.classList.toggle("active");$$('.quick-note-tags [data-note-tag]').filter(other=>other!==button).forEach(other=>other.classList.remove("active"));loadQuickNotes()});$$('.quick-note-edit').forEach(button=>button.onclick=()=>quickNoteDialog(rows[+button.dataset.index]));$$('.quick-note-delete').forEach(button=>button.onclick=async()=>{const row=rows[+button.dataset.index];await desktopWrite("fast_notes",{id:row.id,_action:"delete"});loadQuickNotes()});$$('.quick-note-toggle').forEach(toggle=>toggle.onchange=async()=>{const row=rows[+toggle.dataset.index];await desktopWrite("fast_notes",{id:row.id,is_active:toggle.checked?1:0,_action:"update"});loadQuickNotes()})}catch(err){host.innerHTML=empty("H\u0131zl\u0131 notlar y\u00fcklenemedi",err.message)}}
function quickNoteDialog(row={}){const category=row.display_category||"Bilgisayar";openDialog(row.id?"Notu D\u00fczenle":"Yeni Not Ekle","HIZLI NOTLAR & MAKROLAR",`<div class="form-grid"><div class="field"><label>\u0130\u015f ak\u0131\u015f kategorisi</label><input name="category" required value="${esc(row.category||"Ar\u0131za Notu")}"></div><div class="field"><label>G\u00f6r\u00fcnen kategori</label><select name="display_category">${["Bilgisayar","Cep Telefonu","G\u00fcvenlik Sistemleri"].map(value=>`<option ${category===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field full"><label>Ba\u015fl\u0131k</label><input name="title" required value="${esc(row.title||"")}"></div><div class="field full"><label>Not i\u00e7eri\u011fi</label><textarea name="label" required>${esc(row.label||"")}</textarea></div><div class="field"><label>S\u0131ra</label><input name="display_order" type="number" min="0" value="${Number(row.display_order)||0}"></div><div class="field"><label>Durum</label><select name="is_active"><option value="1" ${row.is_active!==0?"selected":""}>Aktif</option><option value="0" ${row.is_active===0?"selected":""}>Pasif</option></select></div></div>`,async fd=>{const payload=Object.fromEntries(fd);payload.is_active=Number(payload.is_active);payload.display_order=Number(payload.display_order);if(row.id){payload.id=row.id;payload._action="update"}await desktopWrite("fast_notes",payload);loadQuickNotes();toast("H\u0131zl\u0131 not kaydedildi")},row.id?"G\u00fcncelle":"Kaydet")}
async function loadSettingsUsers(){const host=$("#settingsUsersHost");if(!host)return;try{const data=await apiFetch("/api/desktop/table/users?limit=200");host.innerHTML=`<div class="table-wrap"><table><thead><tr><th>Kullanıcı</th><th>Ad Soyad</th><th>E-posta</th><th>Rol</th><th>Aktif</th><th>Son Giriş</th><th></th></tr></thead><tbody>${data.rows.map((u,i)=>`<tr><td><strong>${esc(u.username)}</strong></td><td>${esc(u.full_name||"")}</td><td>${esc(u.email||"")}</td><td>${esc(u.role||"")}</td><td>${u.active!==0?"Evet":"Hayır"}</td><td>${esc(u.last_login||"")}</td><td><button class="mini settings-user-edit" data-index="${i}">Yetkileri Düzenle</button></td></tr>`).join("")}</tbody></table></div>`;$$('.settings-user-edit').forEach(b=>b.onclick=()=>settingsUserDialog(data.rows[+b.dataset.index]))}catch(err){host.innerHTML=empty("Kullanıcılar yüklenemedi",err.message)}}
const ayecUserPermissionSections=[["GENEL",[[40,"Genel Bak\u0131\u015f"]]],["SERV\u0130S OPERASYON",[[41,"Durum Paneli"],[62,"Teknisyen Paneli"],[61,"Saha Haritas\u0131"],[30,"Randevular"],[65,"Lojistik & Garanti Y\u00f6netimi"],[201,"\u0130\u015f/Servis Takibi Raporlar\u0131"],[170,"AI Asistan"]]],["M\u00dc\u015eTER\u0130",[[21,"M\u00fc\u015fteri Listesi"],[26,"\u00c7al\u0131\u015fma Ortaklar\u0131"],[25,"S\u00f6zle\u015fmeler"],[90,"Hat\u0131rlat\u0131c\u0131lar"],[120,"Duyurular"]]],["T\u0130CAR\u0130",[[200,"Proje Y\u00f6netimi"],[202,"Proje Ar\u015fivi"],[50,"Stok Y\u00f6netimi"],[60,"Ara\u00e7 Par\u00e7a Sto\u011fu"],[150,"Sales Hub"],[140,"Hizmet Tan\u0131mlar\u0131"],[146,"\u00dcr\u00fcn Grubu Y\u00f6netimi"],[147,"Rapor C\u00fcmle Kal\u0131plar\u0131"],[145,"Cihaz Bilgisi & Markalar"],[66,"Emanet (Konsinye) Cihazlar"],[250,"Mobil Stok"],[300,"PC Builder"]]],["F\u0130NANS",[[101,"Gelir / Gider"],[105,"Banka Hesaplar\u0131"],[106,"\u00c7ek / Senet"],[115,"E-Fatura"]]],["PERSONEL",[[10,"Personel"]]],["S\u0130STEM",[[160,"Bilgi Bankas\u0131"],[130,"Ayarlar"],[135,"Log Kay\u0131tlar\u0131"],[180,"Yedekleme"],[261,"Kullan\u0131m K\u0131lavuzu"],[70,"Destek"]]]];
function normalizeUserPermissions(value){let parsed=value;try{if(typeof value==="string")parsed=JSON.parse(value||"{}")}catch{parsed=null}return parsed&&typeof parsed==="object"&&!Array.isArray(parsed)?parsed:null}
function userRoleKey(role){return String(role||"").trim().toLowerCase().replace(/[\u00e7\u00f6\u00fc\u011f\u0131\u015f]/g,char=>({"\u00e7":"c","\u00f6":"o","\u00fc":"u","\u011f":"g","\u0131":"i","\u015f":"s"}[char])).normalize("NFKD").replace(/[^a-z0-9]+/g," ").trim()}
function userAdminRole(role){return new Set(["admin","administrator","superadmin","super admin","super administrator","master","master admin","platform admin","system admin","company admin","yonetici","sistem yoneticisi","firma yoneticisi","firma sahibi","owner","tenant owner","en yetkili","en yetkili kisi"]).has(userRoleKey(role))}
function defaultUserPermissionPages(role){const key=String(role||"").trim().toLowerCase();const all=ayecUserPermissionSections.flatMap(([,items])=>items.map(([id])=>id));if(userAdminRole(key))return new Set(all);if(["teknisyen","technician"].includes(key))return new Set([40,41,60,61,30,150,21,50,70]);if(["muhasebe","accounting"].includes(key))return new Set([40,21,101,135,130]);return new Set([40,41,21,50])}
function userPermissionPages(value,role){const known=new Set(ayecUserPermissionSections.flatMap(([,items])=>items.map(([id])=>id)));if(userAdminRole(role))return new Set(known);let decoded=value;try{if(typeof value==="string")decoded=JSON.parse(value)}catch{decoded=null}const saved=normalizeUserPermissions(decoded);if(saved?.mode==="all")return new Set(known);if(Array.isArray(saved?.pages))return new Set(saved.pages.map(Number).filter(id=>known.has(id)));if(Array.isArray(decoded))return new Set(decoded.map(Number).filter(id=>known.has(id)));if(saved){const legacy={dashboard:[40],customers:[21,25,90,120],services:[41,60,61,30],stock:[50,140,146,147],financial:[101],backup:[180],settings:[130],logs:[135]};const selected=Object.entries(legacy).filter(([key])=>saved[key]).flatMap(([,ids])=>ids);if(Object.keys(legacy).some(key=>Object.hasOwn(saved,key)))return new Set(selected)}return defaultUserPermissionPages(role)}
function renderUserPermissionMatrix(allowed,editable=false){return ayecUserPermissionSections.map(([section,items])=>`<section class="settings-user-permission-group"><header><strong>${esc(section)}</strong><small>${items.filter(([id])=>allowed.has(id)).length}/${items.length}</small></header>${items.map(([id,title])=>editable?`<label class="settings-user-edit-permission"><span>${esc(title)}</span><input type="checkbox" data-user-permission="${id}" ${allowed.has(id)?"checked":""}></label>`:`<div class="settings-user-permission"><span>${esc(title)}</span><b class="${allowed.has(id)?"allowed":"restricted"}">${allowed.has(id)?"A\u00e7\u0131k":"Kapal\u0131"}</b></div>`).join("")}</section>`).join("")}
function settingsUserDialog(user){const roleChoices=[...new Set(["admin","manager","technician","user",user.role].filter(Boolean))];let allowed=userPermissionPages(user.permissions,user.role);const permissionFields=renderUserPermissionMatrix(allowed,true);openDialog(`${user.username} — Yetkiler`,"KULLANICI YÖNETİMİ",`<div class="form-grid"><div class="field"><label>Ad Soyad</label><input name="full_name" value="${esc(user.full_name||"")}"></div><div class="field"><label>E-posta</label><input name="email" type="email" value="${esc(user.email||"")}"></div><div class="field"><label>Rol</label><select name="role">${roleChoices.map(r=>`<option value="${esc(r)}" ${user.role===r?"selected":""}>${esc(r)}</option>`).join("")}</select></div><div class="field"><label>Aktif</label><select name="active"><option value="1" ${user.active!==0?"selected":""}>Evet</option><option value="0" ${user.active===0?"selected":""}>Hayır</option></select></div><section class="field full settings-user-edit-matrix"><header><strong>İnce Ayarlı Yetki Matrisi</strong><small>${allowed.size} / ${ayecUserPermissionSections.reduce((sum,[,items])=>sum+items.length,0)} sayfa</small></header>${permissionFields}</section><div class="field"><label>Arayüz Düzenleme</label><select name="interface_edit_access"><option value="1" ${user.interface_edit_access?"selected":""}>Açık</option><option value="0" ${!user.interface_edit_access?"selected":""}>Kapalı</option></select></div></div>`,async fd=>{const payload=Object.fromEntries(fd),role=fd.get("role");if(userAdminRole(role))payload.permissions=JSON.stringify({mode:"all"});else{const selected=[...document.querySelectorAll("[data-user-permission]:checked")].map(input=>Number(input.dataset.userPermission));payload.permissions=JSON.stringify({pages:selected})}payload.id=user.id;payload._action="update";await desktopWrite("users",payload);loadSettingsUsers();toast("Kullanıcı yetkileri güncellendi")} ,"Yetkileri Kaydet");const roleField=$("#dialogBody [name=role]");roleField.onchange=()=>{allowed=defaultUserPermissionPages(roleField.value);document.querySelectorAll("[data-user-permission]").forEach(input=>{input.checked=allowed.has(Number(input.dataset.userPermission));input.disabled=userAdminRole(roleField.value)})};document.querySelectorAll("[data-user-permission]").forEach(input=>input.disabled=userAdminRole(user.role))}
function genericFieldKind(column){if(/date/.test(column))return"date";if(/time/.test(column)&&!column.includes("date"))return"time";if(/amount|price|stock|salary|balance|quantity|qty|rate|year|km|limit/.test(column))return"number";if(/description|notes|content|address|details|summary/.test(column))return"textarea";if(/email/.test(column))return"email";return"text"}
function openGenericDialog(meta,row={},columns=[]){const hidden=/^(id|created_at|updated_at|deleted_at|is_deleted|password|remember_token|secret_answer)$/;const usable=columns.filter(c=>!hidden.test(c)).slice(0,24);const fields=usable.map(c=>{const kind=genericFieldKind(c),value=row[c]??"";return kind==="textarea"?`<div class="field full"><label>${columnLabel(c)}</label><textarea name="${c}">${esc(value)}</textarea></div>`:`<div class="field"><label>${columnLabel(c)}</label><input name="${c}" type="${kind}" value="${esc(value)}"></div>`}).join("");openDialog(row.id?`${meta.title} — Düzenle`:`${meta.title} — Yeni Kayıt`,meta.group,`<div class="form-grid">${fields}</div>`,async fd=>{const payload=Object.fromEntries(fd);if(row.id){payload.id=row.id;payload._action="update"}await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify(payload)});toast("Kayıt masaüstü veritabanına işlendi");loadGenericModule(meta,$("#genericSearch")?.value||"")},row.id?"Güncelle":"Kaydet")}
async function deleteGenericRow(meta,row){if(!confirm("Bu kayıt silinsin mi?"))return;await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify({id:row.id,_action:"delete"})});toast("Kayıt silindi","warning");loadGenericModule(meta,$("#genericSearch")?.value||"")}
function dialogCatalogShell(){return `${pageHead("Dialog Modülleri","Masaüstü kaynaklarından çıkarılan tüm alan, buton ve sinyal bağlantıları.",'<span class="badge" id="dialogSummary">Yükleniyor…</span>')}<section class="card"><div class="toolbar"><input class="control search" id="dialogCatalogSearch" placeholder="Dialog, sınıf veya dosya ara…"></div><div id="dialogCatalog" class="dialog-catalog"></div></section>`}
async function loadDialogCatalog(){const host=$("#dialogCatalog");if(!host)return;try{const data=await apiFetch('/api/desktop/dialogs');window.desktopDialogManifest=data;$("#dialogSummary").textContent=`${data.summary.dialog_count} dialog · ${data.summary.connection_count} sinyal`;const draw=q=>{const term=q.toLocaleLowerCase("tr-TR");const list=data.dialogs.filter(d=>[d.title,d.key,d.file,...(d.classes||[]).map(c=>c.name)].join(" ").toLocaleLowerCase("tr-TR").includes(term));host.innerHTML=list.map((d,i)=>`<button class="dialog-module" data-dialog-key="${esc(d.key)}"><strong>${esc(d.title||d.key)}</strong><small>${esc(d.file)}</small><span>${d.counts.buttons} buton · ${d.counts.fields} alan · ${d.counts.connections} sinyal</span></button>`).join("");$$('[data-dialog-key]').forEach(b=>b.onclick=()=>openManifestDialog(data.dialogs.find(d=>d.key===b.dataset.dialogKey)))};draw("");$("#dialogCatalogSearch").oninput=e=>draw(e.target.value)}catch(err){host.innerHTML=empty("Dialog manifesti yüklenemedi",err.message)}}
function manifestInput(field){const label=field.label||field.name,kind=field.kind;if(kind==="textarea")return `<div class="field full"><label>${esc(label)}</label><textarea name="${esc(field.name)}"></textarea></div>`;if(kind==="checkbox"||kind==="radio")return `<div class="field"><label><input name="${esc(field.name)}" type="checkbox"> ${esc(label)}</label></div>`;if(kind==="table"||kind==="list")return `<div class="field full"><label>${esc(label)}</label><div class="dialog-placeholder">${kind==="table"?"Tablo":"Liste"} yüzeyi</div></div>`;const type={number:"number",decimal:"number",date:"date",time:"time",datetime:"datetime-local"}[kind]||"text";return `<div class="field"><label>${esc(label)}</label><input name="${esc(field.name)}" type="${type}" value="${esc(field.default||"")}"></div>`}
function openManifestDialog(dialog){const key=dialog.key;const direct={add_customer_dialog:()=>openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle"),add_stock_dialog:()=>openDialog("Ürün Ekle","STOK KARTI",productForm(),fd=>saveProduct(fd),"Ürün Ekle"),payment_dialog:()=>customerSelect(paymentDialog,"Tahsilat için müşteri seçin"),tahsilat_dialog:()=>customerSelect(paymentDialog,"Tahsilat için müşteri seçin"),bulk_payment_dialog:()=>customerSelect(paymentDialog,"Toplu tahsilat için müşteri seçin"),new_service_dialog:()=>serviceDialog(),technical_service_new_service_dialog:()=>serviceDialog(),automotive_new_service_dialog:()=>serviceDialog(),add_device_dialog:()=>serviceDialog(),customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),technical_customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),automotive_customer_360_dialog:()=>customerSelect(customer360,"Müşteri 360 için müşteri seçin"),stock_smart_import_dialog:()=>navigate("import"),stock_import_preview_dialog:()=>navigate("import"),service_import_preview_dialog:()=>navigate("import"),quick_sale_dialog:()=>navigate("sales"),technician_panel:()=>navigate("technician"),technical_service_technician_panel:()=>navigate("technician"),automotive_technician_panel:()=>navigate("technician")};if(direct[key])return direct[key]();const fields=(dialog.fields||[]).slice(0,40).map(manifestInput).join("");const signals=(dialog.connections||[]).map(c=>`<tr><td>${esc(c.owner)}</td><td>${esc(c.signal)}</td><td>${esc(c.callback)}</td></tr>`).join("");openDialog(dialog.title||dialog.key,"MASAÜSTÜ DIALOG PORTU",`<div class="tabs"><button type="button" class="tab active">Form</button><button type="button" class="tab">Sinyaller (${dialog.counts.connections})</button></div><div class="form-grid">${fields||empty("Form alanı yok","Bu modül bileşik veya salt görüntüleme dialogudur.")}</div><details style="margin-top:18px"><summary>Sinyal bağlantıları</summary><div class="table-wrap"><table><thead><tr><th>Sahip</th><th>Sinyal</th><th>Callback</th></tr></thead><tbody>${signals}</tbody></table></div></details>`,()=>{toast(`${dialog.title} form sinyali yakalandı`)},"Kaydet / Uygula");$("#dialogFooter").insertAdjacentHTML("afterbegin",(dialog.buttons||[]).slice(0,8).map(b=>`<button type="button" class="secondary manifest-button" title="${esc(b.connections?.map(x=>x.callback).join(', ')||'')}">${esc(b.label)}</button>`).join(""));$$('.manifest-button').forEach(b=>b.onclick=()=>toast(`${b.textContent} sinyali çalıştırıldı`))}
function customerSelect(callback,title){openDialog(title,"MÜŞTERİ SEÇİMİ",`<div class="field"><label>Müşteri</label><select id="dialogCustomerSelect" required>${db.customers.map(c=>`<option value="${c.id}">${esc(c.name)}</option>`).join("")}</select></div>`,()=>{const customer=db.customers.find(c=>String(c.id)===String($("#dialogCustomerSelect").value));setTimeout(()=>callback(customer),80)},"Devam")}
 function renderBackupPage(){settingsSection="backup";const definition=settingsDefinitions.backup,regular=definition.fields.filter(field=>field[2]!=="checkbox"),toggles=definition.fields.filter(field=>field[2]==="checkbox"),body=`<div class="form-grid">${regular.map(field=>exactSettingsField(field,definition.scope||"settings")).join("")}</div><div class="settings-grid">${toggles.map(field=>exactSettingsField(field,definition.scope||"settings")).join("")}</div>`;return `${pageHead("Yedekleme &amp; Veri G\u00fcvenli\u011fi Merkezi","Yerel yedekleri indirin, geri y\u00fckleyin ve masa\u00fcst\u00fc yedekleme tercihlerini y\u00f6netin.",'<div class="actions"><button class="secondary" data-action="restore-backup">Yede\u011fi Geri Y\u00fckle</button><button class="primary" data-action="export-all">\u015eimdi Yedekle</button></div>')}<section class="backup-ref-metrics"><article><small>SON YEREL YEDEK</small><strong>\u0130\u015flem se\u00e7ilmedi</strong><span>\u0130ndirme ge\u00e7mi\u015fi taray\u0131c\u0131 taraf\u0131ndan tutulur.</span></article><article><small>YEDEKLEME KAYNA\u011eI</small><strong>AYEC Pro Web</strong><span>JSON d\u0131\u015fa aktarma ve yerel geri y\u00fckleme.</span></article><article><small>VER\u0130 B\u00dcT\u00dcNL\u00dc\u011e\u00dc</small><strong>Kontrol edilmedi</strong><span>Sonu\u00e7 \u00fcretmeden \u00f6nce do\u011frulama gerekir.</span></article><article><small>KURTARMA DURUMU</small><strong>Haz\u0131r de\u011fil</strong><span>Sunucu yede\u011fi i\u00e7in Admin Konsolunu kullan\u0131n.</span></article></section><section class="backup-ref-layout"><article class="card backup-ref-archive"><header><div><h3>Yedek Ar\u015fivi</h3><p class="muted">Bu web oturumunda listelenebilir bir sunucu ar\u015fivi bulunmuyor.</p></div><button class="secondary" data-action="export-all">JSON Yede\u011fi \u0130ndir</button></header><div class="backup-ref-empty"><span aria-hidden="true">\u25a3</span><strong>Yerel yedek dosyan\u0131z yok</strong><p>Yede\u011fi indirin veya bilgisayar\u0131n\u0131zdaki bir JSON yede\u011fini geri y\u00fckleyin. Sunucu ar\u015fivi ve geri y\u00fckleme i\u015flemleri Admin Konsolu taraf\u0131ndan y\u00f6netilir.</p><div class="actions"><button class="primary" data-action="export-all">Yedek \u0130ndir</button><button class="secondary" data-action="restore-backup">JSON Yede\u011fi Se\u00e7</button></div></div></article><aside class="backup-ref-side"><section class="card"><header><h3>Yedekleme Kapsam\u0131</h3><span class="badge">Yerel JSON</span></header><ul><li>M\u00fc\u015fteri ve servis verileri</li><li>Stok, finans ve randevu verileri</li><li>Web ayarlar\u0131 ve i\u015flem kay\u0131tlar\u0131</li></ul><p class="muted">\u0130\u00e7erik mevcut uygulama veri modeline g\u00f6re d\u0131\u015fa aktar\u0131l\u0131r.</p></section><section class="card backup-ref-notice"><header><h3>Sunucu Yedekleme</h3><span class="badge">Admin Konsolu</span></header><p>Sunucu yedekleri, tenant ve \u00fcr\u00fcn kimli\u011fiyle merkez\u00ee yedekleme kayd\u0131nda saklan\u0131r. Web kullan\u0131c\u0131s\u0131 i\u00e7in ar\u015fiv listeleme u\u00e7 noktas\u0131 tan\u0131ml\u0131 de\u011fildir.</p><button class="secondary" data-page="support">Destek Merkezine Git</button></section></aside></section><section class="card backup-ref-settings"><header><div><h3>Otomatik Yedekleme Tercihleri</h3><p class="muted">Bu tercihler masa\u00fcst\u00fc ayar kayd\u0131na yaz\u0131l\u0131r; web zamanlay\u0131c\u0131s\u0131 \u00e7al\u0131\u015ft\u0131rmaz.</p></div><button class="primary" data-action="save-settings">Tercihleri Kaydet</button></header>${body}</section>`}
 function render(){const nav=$("#nav"),navScrollTop=nav?.scrollTop||0;document.body.dataset.page=page;const routes={dashboard:renderDashboard,customers:renderCustomers,appointments:renderAppointments,stock:renderStock,"stock-locations":renderStockLocations,movements:renderMovements,import:renderImport,sales:renderSales,services:renderServices,technician:renderTechnician,finance:()=>renderFinance(""),income:()=>renderFinance("Gelir"),expense:()=>renderFinance("Gider"),settings:renderSettings,backup:renderBackupPage,invoices:renderInvoiceComposer,"dialog-catalog":dialogCatalogShell};const route=routes[page],meta=page==="invoices"||page==="backup"?null:genericModules[page];$("#content").innerHTML=route?route():meta?genericShell(meta):renderDashboard();bindPage();if(meta){const genericSearch=$("#genericSearch"),genericRefresh=$("[data-generic-refresh]"),genericAdd=$("[data-generic-add]");if(genericSearch)genericSearch.oninput=e=>meta.table==="services"?bindLaborServiceFilters():loadGenericModule(meta,e.target.value);if(genericRefresh)genericRefresh.onclick=()=>loadGenericModule(meta,genericSearch?.value||"");if(genericAdd)genericAdd.onclick=async()=>{const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=1`);openGenericDialog(meta,{},data.columns)};if(meta.table==="services"){$("[data-labor-bulk]").onclick=async()=>{const raw=prompt("Fiyat değişimi (%)", "0");if(raw===null)return;const percent=Number(raw);if(!Number.isFinite(percent))return;for(const row of window.currentGenericData?.rows||[]){const price=Number(row.price_try||0)*(1+percent/100);await apiFetch("/api/desktop/table/services",{method:"POST",body:JSON.stringify({id:row.id,_action:"update",price,price_try:price})})}loadGenericModule(meta,$("#genericSearch").value)};$("[data-labor-export]").onclick=()=>download("hizmet-ucret.csv",csv(window.currentGenericData?.rows||[]));$("[data-labor-pdf]").onclick=()=>window.print();$("[data-labor-print]").onclick=()=>window.print()}loadGenericModule(meta)}if(page==="dialog-catalog")loadDialogCatalog();if(nav)nav.scrollTop=navScrollTop}

function toast(message,type="success",duration=3500){const el=document.createElement("div");el.className=`toast ${type}`;el.innerHTML=`<span>${type==="success"?"✓":type==="warning"?"!":"×"}</span><div>${esc(message)}</div>`;$("#toastRoot").append(el);setTimeout(()=>el.remove(),duration)}
function openDialog(title,eyebrow,body,onSubmit,submitLabel="Kaydet"){
 const dialog=$("#appDialog"),serviceAccept=body.includes('class="service-accept-form"'),companyEditor=body.includes('class="company-settings-editor"'),projectInstall=body.includes('class="p9-unit-products"');
 dialog.classList.remove("finance-detail-dialog","customer-editor-dialog","service-accept-dialog","company-settings-dialog","project-unit-install-dialog");
 if(projectInstall)dialog.classList.add("project-unit-install-dialog");
 if(serviceAccept)dialog.classList.add("service-accept-dialog");
 if(body.includes('class="customer-editor"'))dialog.classList.add("customer-editor-dialog");
 if(companyEditor)dialog.classList.add("company-settings-dialog");
  $("#dialogTitle").textContent=title;$("#dialogEyebrow").textContent=eyebrow;$("#dialogBody").innerHTML=body;
  if(projectInstall){const installHead=$("#dialogBody .p9-install-head"),badge=installHead?.querySelector(".p9-install-badge"),breadcrumb=installHead?.querySelector("p"),addRoom=installHead?.querySelector("[data-p9-add-room]"),header=dialog.querySelector("form>header"),titleElement=$("#dialogTitle");if(installHead&&header&&titleElement){const icon=document.createElement("span"),row=document.createElement("div"),titleHost=titleElement.parentElement;icon.className="p9-install-title-icon";row.className="p9-install-heading-row";titleElement.replaceWith(row);row.append(icon,titleElement);if(badge)row.append(badge);if(breadcrumb){breadcrumb.className="p9-install-breadcrumb";titleHost.append(breadcrumb)}$("#dialogEyebrow").hidden=true;if(addRoom)header.insertBefore(addRoom,$("#dialogClose"));installHead.remove()}}
 $("#dialogFooter").innerHTML=serviceAccept?`<span class="service-footer-status">ERP Core v2.0.4 Online \u00b7 USD Kuru: 49.20 TRY</span><button type="button" id="dialogCancel" class="secondary">\u0130ptal</button><button type="button" id="serviceResetButton" class="secondary">Temizle</button><button type="submit" class="primary" id="dialogSubmit">${submitLabel}</button>`:`<button type="button" id="dialogCancel" class="secondary">${companyEditor?"\u0130ptal":"Vazge\u00e7"}</button><button type="submit" class="primary" id="dialogSubmit">${submitLabel}</button>`;
 if(projectInstall){const allocation=$("#dialogBody .p9-install-allocation");if(allocation)$("#dialogFooter").prepend(allocation);}
 $("#dialogClose").onclick=()=>dialog.close("cancel");$("#dialogCancel").onclick=()=>dialog.close("cancel");
 const form=$("#dialogForm");if(serviceAccept)$("#serviceResetButton").onclick=()=>{form.reset();form.dispatchEvent(new Event("service-form-reset"))};
 form.onsubmit=async e=>{e.preventDefault();const submit=$("#dialogSubmit");try{submit.disabled=true;submit.dataset.label=submit.textContent;submit.textContent="Kaydediliyor\u2026";const ok=await onSubmit?.(new FormData(form));if(ok!==false&&dialog.open)dialog.close("ok")}catch(err){toast(err.message||"\u0130\u015flem tamamlanamad\u0131","error")}finally{if(dialog.open){submit.disabled=false;submit.textContent=submit.dataset.label||submitLabel}}};
 dialog.showModal();setTimeout(()=>$("input,select,textarea",$("#dialogBody"))?.focus(),30)
}

function customerForm(c={}){return `<div class="customer-editor"><section class="customer-editor-section"><h3>Temel Bilgiler</h3><div class="form-grid"><div class="field"><label>M\u00fc\u015fteri Ad\u0131 / Soyad\u0131 *</label><input name="name" required value="${esc(c.name||"")}"></div><div class="field"><label>Firma Ad\u0131 (Opsiyonel)</label><input name="company_name" value="${esc(c.company_name||"")}"></div><div class="field"><label>M\u00fc\u015fteri T\u00fcr\u00fc</label><select name="type"><option ${c.type==="Bireysel"?"selected":""}>Bireysel</option><option ${c.type==="Kurumsal"?"selected":""}>Kurumsal</option></select></div><div class="field"><label>TC Kimlik No</label><input name="tc_no" inputmode="numeric" value="${esc(c.tc_no||"")}"></div></div></section><section class="customer-editor-section"><h3>\u0130leti\u015fim Bilgileri</h3><div class="form-grid"><div class="field"><label>Telefon 1 *</label><input name="phone" type="tel" required value="${esc(c.phone||"")}"></div><div class="field"><label>Telefon 2</label><input name="phone2" type="tel" value="${esc(c.phone2||"")}"></div><div class="field full"><label>E-posta</label><input name="email" type="email" value="${esc(c.email||"")}"></div></div></section><section class="customer-editor-section"><h3>Finans &amp; Vergi</h3><div class="form-grid"><div class="field"><label>Vergi Numaras\u0131</label><input name="tax_number" inputmode="numeric" value="${esc(c.tax_number||c.tax_no||c.tax_id||"")}"></div><div class="field"><label>Vergi Dairesi</label><input name="tax_office" value="${esc(c.tax_office||"")}"></div><div class="field"><label>Vade (G\u00fcn)</label><input name="term_days" type="number" min="0" value="${Number(c.term_days||0)}"></div><div class="field"><label>Bor\u00e7 Limiti (USD)</label><input name="limit_amount" type="number" min="0" step=".01" value="${Number(c.limit_amount||0)}"></div><div class="field"><label>Komisyon (%)</label><input name="commission_rate" type="number" min="0" max="100" step=".1" value="${Number(c.commission_rate||0)}"></div><div class="field"><label>Hizmet T\u00fcr\u00fc</label><select name="service_type">${["Genel","Yaz\u0131l\u0131m &amp; Lisans","Donan\u0131m Bak\u0131m &amp; Onar\u0131m","A\u011f &amp; Altyap\u0131 Deste\u011fi"].map(value=>{const label=value.replaceAll("&amp;","&");return `<option value="${label}" ${c.service_type===label?"selected":""}>${value}</option>`}).join("")}</select></div></div><div class="customer-balance-grid"><label>TRY Bakiye<input name="TRY" type="number" step=".01" value="${c.balances?.TRY||0}"></label><label>USD Bakiye<input name="USD" type="number" step=".01" value="${c.balances?.USD||0}"></label><label>EUR Bakiye<input name="EUR" type="number" step=".01" value="${c.balances?.EUR||0}"></label></div></section><section class="customer-editor-section"><h3>Adres Bilgileri</h3><div class="form-grid"><div class="field"><label>\u0130l</label><input name="city" value="${esc(c.city||"")}"></div><div class="field"><label>\u0130l\u00e7e</label><input name="district" value="${esc(c.district||"")}"></div><div class="field"><label>Mahalle</label><input name="neighborhood" value="${esc(c.neighborhood||"")}"></div><div class="field"><label>Posta Kodu</label><input name="zip_code" value="${esc(c.zip_code||"")}"></div><div class="field full"><label>Cadde / Sokak</label><input name="street" value="${esc(c.street||"")}"></div><div class="field full"><label>A\u00e7\u0131k Adres</label><textarea name="address" rows="2">${esc(c.address||"")}</textarea></div><div class="field full"><label>\u00d6zel Notlar</label><textarea name="notes" rows="3">${esc(c.notes||"")}</textarea></div></div></section></div>`}
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
 const lastMovement=[...finance.map(item=>item.date),...services.map(item=>item.date)].filter(Boolean).sort().at(-1)||"-";
 const balanceTry=["TRY","USD","EUR"].reduce((sum,currency)=>sum+Number(c.balances?.[currency]||0)*(currency==="TRY"?1:(rateForCode(currency)||1)),0);
 const balanceTitle=balanceTry<0?"M\u00dc\u015eTER\u0130 BOR\u00c7 / FAZLA \u00d6DEME":"M\u00dc\u015eTER\u0130 ALACA\u011eI";
 const body=`<div class="c360-header"><span class="c360-avatar">${esc(c.name.slice(0,1).toUpperCase())}</span><div class="c360-profile"><div class="c360-title-row"><h2>${esc(c.name)}</h2><span class="c360-code">#M-${esc(String(c.id).padStart(4,"0"))}</span><span class="c360-profile-state">PROF\u0130L AKT\u0130F</span></div><p>Telefon: ${esc(c.phone||"Bilinmiyor")} <span>\u2022</span> Son Hareket: ${esc(lastMovement)}</p></div><button type="button" class="primary" id="c360Notes">&#128221; M\u00fc\u015fteri Notlar\u0131</button></div><div class="c360-stats"><div class="c360-stat"><span>&#128295;</span><small>TOPLAM \u0130\u015eLEM</small><strong>${services.length}</strong></div><div class="c360-stat"><span>&#9889;</span><small>AKT\u0130F \u0130\u015eLEM</small><strong>${active}</strong></div><div class="c360-stat"><span>&#128176;</span><small>TOPLAM C\u0130RO</small><strong>${money(turnover)}</strong></div><div class="c360-stat c360-debt"><span>&#128179;</span><small>${balanceTitle}</small><strong>${money(Math.abs(balanceTry),"TRY")}</strong></div></div><div class="tabs c360-tabs"><button class="tab" type="button" data-c360-tab="service">Servis Ge\u00e7mi\u015fi</button><button class="tab active" type="button" data-c360-tab="cari">Cari \u0130\u015flem Ge\u00e7mi\u015fi</button><button class="tab" type="button" data-c360-tab="ledger">D\u00f6viz Defteri</button><button class="tab" type="button" data-c360-tab="sales">\u00dcr\u00fcn Sat\u0131\u015flar\u0131</button><button class="tab" type="button" data-c360-tab="offers">Verilen Teklifler</button>${vehicleTab}</div><div class="c360-panel" data-c360-panel="service">${serviceTable}</div><div class="c360-panel active" data-c360-panel="cari">${cari}</div><div class="c360-panel" data-c360-panel="ledger"><div class="table-wrap"><table><thead><tr><th>Tarih</th><th>D\u00f6viz</th><th>\u0130\u015flem Tipi</th><th>Miktar</th><th>Kalan Bakiye</th></tr></thead><tbody>${ledger}</tbody></table></div></div><div class="c360-panel" data-c360-panel="sales">${salesTable}</div><div class="c360-panel" data-c360-panel="offers">${offerTable}</div>${vehiclePanel}`;
 openDialog(c.name,"MÜŞTERİ 360°",body,()=>true,"Kapat");
 $("#appDialog").classList.add("dialog-wide","c360-dialog");
 $("#appDialog").addEventListener("close",()=>$("#appDialog").classList.remove("dialog-wide","c360-dialog"),{once:true});
 $("#dialogFooter").insertAdjacentHTML("afterbegin",`<button type="button" class="primary" id="c360Offer">Teklif Oluştur</button><button type="button" class="success" id="c360Excel">Excel'e Aktar</button><button type="button" class="danger" id="c360Pdf">PDF'e Aktar</button>`);
 $$("[data-c360-tab]").forEach(tab=>tab.onclick=()=>{$$("[data-c360-tab]").forEach(x=>x.classList.toggle("active",x===tab));$$('[data-c360-panel]').forEach(x=>x.classList.toggle("active",x.dataset.c360Panel===tab.dataset.c360Tab))});
 $("#c360Notes").onclick=()=>{$("#appDialog").close();setTimeout(()=>openCustomerNotes(c),0)};$("#c360Offer").onclick=()=>{$("#appDialog").close();salesCustomer=c.id;navigate("sales")};$("#c360Excel").onclick=()=>download(`${c.name}-musteri-360.csv`,csv(finance));$("#c360Pdf").onclick=()=>printCustomer(c);$$(".c360-pay").forEach(b=>b.onclick=()=>{$("#appDialog").close();setTimeout(()=>paymentDialog(c),0)});$$(".c360-print-offer").forEach(b=>b.onclick=()=>window.print());
}
function openCustomerNotes(c){
 const filters=[["T\u00fcm\u00fc","T\u00fcm\u00fc"],["Genel Not","Genel Not"],["WhatsApp","WhatsApp Mesaj\u0131"],["SMS","SMS"],["Telefon","Telefon G\u00f6r\u00fc\u015fmesi"],["E-Posta","E-Posta"],["Teklif","PC Teklif"]];
 let notes=Array.isArray(c.note_history)?c.note_history.map(note=>({id:note.id,type:note.type||note.note_type||"Genel Not",title:note.title||"Not",content:note.content||"",date:note.created_at||note.date||""})):[];
 if(!notes.length&&c.notes)notes=[{id:null,type:"Genel Not",title:"Genel Not",content:String(c.notes),date:""}];
 let selected=null,activeFilter="T\u00fcm\u00fc";
 const formatLabel=note=>{const type=note.type||"Genel Not";return type==="WhatsApp Mesaj\u0131"?"WhatsApp":type==="Telefon G\u00f6r\u00fc\u015fmesi"?"Telefon":type};
 const filterHtml=filters.map(([label,value],index)=>`<button type="button" class="customer-note-filter${index===0?" active":""}" data-cnote-filter="${esc(value)}">${label}</button>`).join("");
 const body=`<div class="customer-notes-toolbar"><div class="customer-notes-filters">${filterHtml}</div><input id="customerNoteSearch" placeholder="Notlarda ara..." aria-label="Notlarda ara"></div><div class="customer-notes-layout"><aside class="customer-notes-history"><header><strong>Kay\u0131t Ge\u00e7mi\u015fi</strong><small id="customerNoteCount">0 Kay\u0131t Listelendi</small></header><div id="customerNoteList" class="customer-note-list"></div></aside><section class="customer-notes-editor"><div class="customer-note-heading"><label for="customerNoteTitle">Not Ba\u015fl\u0131\u011f\u0131 <i>*</i></label><small id="customerNoteDate">Yeni not - tarih kay\u0131tta otomatik olu\u015fturulacak</small></div><input id="customerNoteTitle" name="note_title" placeholder="Not ba\u015fl\u0131\u011f\u0131" required><div class="customer-note-formatbar"><button type="button" data-cnote-format="bold"><b>B</b></button><button type="button" data-cnote-format="italic"><i>I</i></button><button type="button" data-cnote-format="underline"><u>U</u></button><button type="button" data-cnote-format="insertUnorderedList">\u2261</button><button type="button" data-cnote-format="formatBlock" data-cnote-value="pre">&lt;/&gt;</button><button type="button" data-cnote-date>\u25a3</button><span id="customerNoteSaved">Otomatik Kaydedildi</span></div><div id="customerNoteEditor" class="customer-note-rich" contenteditable="true" role="textbox" aria-multiline="true" data-placeholder="Not metnini buraya yaz\u0131n..." ></div><textarea id="customerNoteValue" name="note" hidden></textarea><div class="customer-note-editor-foot"><span>\u2315 Dosya veya ekran g\u00f6r\u00fcnt\u00fcs\u00fc yap\u0131\u015ft\u0131rabilirsiniz (Ctrl+V)</span><small>UTF-8 Destekli</small></div></section></div>`;
 openDialog("M\u00fc\u015fteri Notlar\u0131",`${esc(c.name)}   ID: #C-${String(c.id||"").padStart(4,"0")}`,body,async formData=>{
  const title=String(formData.get("note_title")||"").trim(),content=String(formData.get("note")||"").trim(),type=String(formData.get("note_type")||"Genel Not");
  if(!title)throw Error("Not ba\u015fl\u0131\u011f\u0131 zorunludur");if(!content)throw Error("Not i\u00e7eri\u011fi bo\u015f b\u0131rak\u0131lamaz");
  const record={id:selected?.id||uid("note"),type,note_type:type,title,content,created_at:selected?.date||new Date().toISOString(),customer_id:Number.isInteger(+c.id)?+c.id:null};
  if(selected?.id)await desktopWrite("customer_notes",{...record,id:+selected.id,_action:"update"});else await desktopWrite("customer_notes",record);
  const index=notes.findIndex(note=>String(note.id)===String(record.id));if(index>=0)notes[index]=record;else notes.unshift(record);
  c.note_history=notes;c.notes=content.replace(/<[^>]*>/g," ").trim();save();selected=record;renderNotes();loadSelected(record);toast("M\u00fc\u015fteri notu kaydedildi","success");return false;
 },"Kaydet / G\u00fcncelle");
 const dialog=$("#appDialog"),bodyNode=$("#dialogBody"),editor=$("#customerNoteEditor",bodyNode),value=$("#customerNoteValue",bodyNode),titleInput=$("#customerNoteTitle",bodyNode),dateNode=$("#customerNoteDate",bodyNode),typeSelect=document.createElement("select");
 dialog.classList.add("dialog-wide","customer-notes-dialog");dialog.addEventListener("close",()=>dialog.classList.remove("dialog-wide","customer-notes-dialog"),{once:true});
 typeSelect.id="customerNoteType";typeSelect.name="note_type";typeSelect.setAttribute("aria-label","Kategori");["Genel Not","WhatsApp Mesaj\u0131","SMS","Telefon G\u00f6r\u00fc\u015fmesi","E-Posta","PC Teklif"].forEach(type=>typeSelect.add(new Option(type,type)));
 $("#dialogFooter").insertAdjacentHTML("afterbegin",`<label class="customer-note-category-label" for="customerNoteType">Kategori:</label><span id="customerNoteUpdated">Son G\u00fcncelleme: --:--</span><button type="button" class="secondary" id="customerNoteNew">+ Yeni Not</button>`);
 $("#dialogFooter").insertBefore(typeSelect,$("#dialogFooter").children[1]||null);
 $("#customerNoteNew").onclick=()=>{selected=null;titleInput.value="";editor.innerHTML="";value.value="";typeSelect.value="Genel Not";dateNode.textContent="Yeni not - tarih kay\u0131tta otomatik olu\u015fturulacak";editor.focus()};
 const loadSelected=note=>{selected=note;titleInput.value=note.title||"";editor.innerHTML=note.content||"";value.value=editor.innerHTML;typeSelect.value=note.type||note.note_type||"Genel Not";dateNode.textContent=note.date||note.created_at?`Kay\u0131t tarihi: ${note.date||note.created_at}`:"Yeni not - tarih kay\u0131tta otomatik olu\u015fturulacak";$("#customerNoteUpdated").textContent=`Son G\u00fcncelleme: ${(note.date||note.created_at||"--:--").slice(-5)}`};
 const renderNotes=()=>{const query=$("#customerNoteSearch",bodyNode).value.trim().toLocaleLowerCase("tr-TR"),shown=notes.filter(note=>(activeFilter==="T\u00fcm\u00fc"||note.type===activeFilter||(activeFilter==="PC Teklif"&&note.type==="Teklif"))&&(!query||`${note.title} ${note.content} ${note.type} ${note.date}`.toLocaleLowerCase("tr-TR").includes(query)));$("#customerNoteCount",bodyNode).textContent=`${shown.length} Kay\u0131t Listelendi`;const list=$("#customerNoteList",bodyNode);list.innerHTML=shown.length?shown.map((note,index)=>`<button type="button" class="customer-note-card${selected&&String(note.id)===String(selected.id)?" active":""}" data-cnote-index="${index}"><strong>${esc(note.title||"Not")}</strong><span>${esc(String(note.content||"").replace(/<[^>]*>/g," ").replace(/\s+/g," ").slice(0,84))}</span><small>${esc(note.date||note.created_at||"-")} <i>\u2022</i> ${esc(formatLabel(note))}</small></button>`).join(""):empty("Bu m\u00fc\u015fteriye ait not yok","Yeni Not ile ba\u015flay\u0131n.");$$("[data-cnote-index]",list).forEach(button=>button.onclick=()=>loadSelected(shown[+button.dataset.cnoteIndex]));};
 $$("[data-cnote-filter]",bodyNode).forEach(button=>button.onclick=()=>{activeFilter=button.dataset.cnoteFilter;$$('[data-cnote-filter]',bodyNode).forEach(item=>item.classList.toggle("active",item===button));renderNotes()});
 $("#customerNoteSearch",bodyNode).addEventListener("input",renderNotes);editor.addEventListener("input",()=>{value.value=editor.innerHTML;$("#customerNoteSaved").textContent="Kaydedilmedi"});
 $$('[data-cnote-format]',bodyNode).forEach(button=>button.onclick=()=>{editor.focus();const command=button.dataset.cnoteFormat;document.execCommand(command,false,command==="formatBlock"?button.dataset.cnoteValue:null);value.value=editor.innerHTML});
 $("[data-cnote-date]",bodyNode).onclick=()=>{editor.focus();document.execCommand("insertText",false,new Date().toISOString().slice(0,10));value.value=editor.innerHTML};
 renderNotes();if(notes.length)loadSelected(notes[0]);
 apiFetch("/api/desktop/table/customer_notes?limit=1000").then(result=>{const rows=(result.rows||[]).filter(note=>String(note.customer_id)===String(c.id)).map(note=>({id:note.id,type:note.type||note.note_type||"Genel Not",title:note.title||"Not",content:note.content||"",date:note.created_at||""}));if(rows.length){notes=rows;renderNotes();loadSelected(rows[0])}}).catch(()=>{});
}
function serviceDialog(customerId=""){const automotive=currentSector==="otomotiv",assetFields=automotive?`<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Model Yılı</label><input name="year" type="number" min="1950" max="2100"></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div><div class="field"><label>Yakıt Türü</label><select name="fuel_type"><option>Benzin</option><option>Dizel</option><option>Hibrit</option><option>Elektrik</option><option>LPG</option></select></div>`:`<div class="field"><label>Cihaz / Ürün *</label><input name="device" required></div><div class="field"><label>Seri No</label><input name="serial"></div>`;openDialog(automotive?"Yeni Araç Servis Kaydı":"Yeni Servis Kaydı",automotive?"OTOMOTİV SERVİS KABUL FORMU":"TEKNİK SERVİS KABUL FORMU",`<div class="form-grid"><div class="field full"><label>Müşteri *</label><select name="customerId" required><option value="">Seçin…</option>${db.customers.map(c=>`<option value="${c.id}" ${String(c.id)===String(customerId)?"selected":""}>${esc(c.name)}</option>`).join("")}</select></div>${assetFields}<div class="field full"><label>${automotive?"Şikayet / Yapılacak İş":"Arıza / Talep"} *</label><textarea name="note" required></textarea></div><div class="field"><label>Durum</label><select name="status"><option>Bekliyor</option><option>İşlemde</option><option>Parça Bekliyor</option></select></div><div class="field"><label>${automotive?"Sonraki Bakım":"Tahmini Teslim"}</label><input name="delivery" type="date"></div></div>`,fd=>{const d=Object.fromEntries(fd),c=db.customers.find(x=>String(x.id)===String(d.customerId));if(!c)throw Error("Müşteri seçin");const no=`SRV-${String(1000+db.customers.flatMap(x=>x.services).length+1)}`,device=automotive?`${d.plate} · ${d.brand} ${d.model}`:d.device;c.services.unshift({date:today(),no,device,status:d.status,note:d.note,serial:d.serial||"",delivery:d.delivery,plate:d.plate,odometer:d.odometer});desktopWrite("devices",{tracking_no:no,customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name,device_type:automotive?"Ara\u00e7":"Cihaz",device_brand:d.brand||"",device_model:automotive?`${d.model} (${d.plate})`:d.device,serial_no:d.serial||d.plate||"",fault_description:d.note,status:d.status,entry_date:today(),estimated_date:d.delivery,service_source:automotive?"Web Otomotiv":"Web Teknik Servis"}).then(deviceResult=>{if(automotive)desktopWrite("customer_vehicles",{customer_id:Number.isInteger(+c.id)?+c.id:null,plate:d.plate,brand:d.brand,model:d.model,year:+d.year||null,fuel_type:d.fuel_type,last_known_odometer:+d.odometer||0,is_active:1}).then(vehicleResult=>desktopWrite("vehicle_maintenance_cards",{vehicle_id:vehicleResult?.id,customer_id:Number.isInteger(+c.id)?+c.id:null,customer_name:c.name,customer_phone:c.phone,vehicle_plate:d.plate,vehicle_brand:d.brand,vehicle_model:d.model,vehicle_year:+d.year||null,fuel_type:d.fuel_type,odometer:+d.odometer||0,service_date:today(),next_maintenance_date:d.delivery,notes:d.note,linked_device_tracking_no:no,linked_device_id:deviceResult?.id,created_by:"Web"}))});save();activity(`${no} servis kaydı ${c.name} için oluşturuldu`,automotive?"🚗":"⚒");toast(automotive?"Araç, bakım kartı ve servis geçmişi kaydedildi":"Servis kaydı Müşteri 360 geçmişine eklendi");render()},automotive?"Araç Servisini Kaydet":"Servis Kaydet")}

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
function inferImportCategory(name,provided=""){if(provided&&provided!=="Genel")return provided;const text=String(name).toLocaleLowerCase("tr-TR");if(currentSector==="otomotiv"){if(/motor|filtre|fren|balata|debriyaj|yağ/.test(text))return"Motor & Mekanik";if(/akü|sensör|far|elektrik|kablo/.test(text))return"Elektrik & Elektronik";if(/kaporta|tampon|çamurluk|ayna/.test(text))return"Kaporta";return"Sarf Malzeme"}if(/kamera|nvr|dvr|alarm|g\u00fcvenlik|ip camera/.test(text))return"Güvenlik Sistemleri";if(/akıllı|smart|zigbee|hub|röle/.test(text))return"Akıllı Ev";return"Bilgisayar"}
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
function contextAction(kind,id,action,row){if(kind==="customer"){const c=db.customers.find(x=>String(x.id)===String(id));if(action==="360")customer360(c);if(action==="payment")paymentDialog(c);if(action==="service")serviceDialog(c.id);if(action==="edit")openDialog("Müşteriyi Düzenle","CRM",customerForm(c),fd=>saveCustomer(fd,c),"Güncelle");if(action==="print")printCustomer(c)}if(kind==="stock"){const s=db.stock.find(x=>String(x.id)===String(id));if(action==="edit-product")openDialog("Ürünü Düzenle","STOK",productForm(s),fd=>saveProduct(fd,s),"Güncelle");if(action==="movement")movementDialog(s);if(action==="delete-product")deleteProduct(s)}if(kind==="appointment"){const a=db.appointments.find(x=>String(x.id)===String(id));if(action==="edit-appointment")appointmentDialog(a);if(["approve","complete","cancel"].includes(action)){a.status={approve:"Onaylandı",complete:"Tamamlandı",cancel:"İptal"}[action];if(Number.isInteger(+a.id))desktopWrite("appointments",{id:+a.id,_action:"update",status:a.status});save();toast(`Randevu durumu: ${a.status}`);render()}}if(kind==="service"){const [c,s]=findService(id);technicianDialog(c,s)}if(kind==="finance"){const item=db.finance.find(x=>String(x.id)===String(id));if(action==="edit-finance")financeDialog(item?.type,item);if(action==="finance-detail")financeDetailDialog(item);if(action==="print-finance")window.print()}if(kind==="generic"){const index=+id,data=window.currentGenericData,meta=window.currentGenericMeta;if(!data||!meta)return;if(action==="generic-edit")openGenericDialog(meta,data.rows[index],data.columns);if(action==="generic-delete")deleteGenericRow(meta,data.rows[index])}}

function bindInteractiveRow(row){if(row.dataset.interactiveBound)return;row.dataset.interactiveBound="1";row.tabIndex=row.tabIndex>=0?row.tabIndex:0;row.addEventListener("contextmenu",e=>showContext(e,row.dataset.kind,row.dataset.id));let timer,startX=0,startY=0;row.addEventListener("pointerdown",e=>{if(e.pointerType==="mouse")return;startX=e.clientX;startY=e.clientY;timer=setTimeout(()=>{timer=0;showContext({preventDefault(){},clientX:startX,clientY:startY,currentTarget:row},row.dataset.kind,row.dataset.id)},550)});const cancel=e=>{if(timer&&e&&Math.hypot((e.clientX??startX)-startX,(e.clientY??startY)-startY)>10)clearTimeout(timer);else if(timer)clearTimeout(timer);timer=0};row.addEventListener("pointerup",cancel);row.addEventListener("pointercancel",cancel);row.addEventListener("pointermove",e=>{if(timer&&Math.hypot(e.clientX-startX,e.clientY-startY)>10)cancel(e)});row.addEventListener("keydown",e=>{if(e.key==="ContextMenu"||(e.shiftKey&&e.key==="F10")){e.preventDefault();const box=row.getBoundingClientRect();showContext({preventDefault(){},clientX:box.left+24,clientY:box.top+24,currentTarget:row},row.dataset.kind,row.dataset.id)}else if(e.key==="Enter")row.dispatchEvent(new MouseEvent("dblclick",{bubbles:true}))})}
function findService(no){for(const c of db.customers){const s=c.services.find(x=>x.no===no);if(s)return[c,s]}return[]}
function movementDialog(s){openDialog("Stok Hareketi","STOK",`<div class="form-grid"><div class="field full"><label>Ürün</label><input disabled value="${esc(s.name)}"></div><div class="field"><label>Tür</label><select name="type"><option>Giriş</option><option>Çıkış</option></select></div><div class="field"><label>Miktar</label><input name="qty" type="number" min="1" required></div><div class="field full"><label>Referans</label><input name="ref" value="MANUEL"></div></div>`,fd=>{const d=Object.fromEntries(fd),qty=+d.qty;if(d.type==="Çıkış"&&qty>s.qty)throw Error("Yetersiz stok");s.qty+=d.type==="Giriş"?qty:-qty;db.movements.unshift({id:uid("mov"),date:new Date().toLocaleString("tr-TR"),product:s.name,type:d.type,qty,ref:d.ref,user:"Yönetici"});if(Number.isInteger(+s.id)){desktopWrite("parts",{id:+s.id,_action:"update",stock:s.qty});desktopWrite("stock_movements",{part_id:+s.id,movement_type:d.type,amount:qty,new_stock:s.qty,description:d.ref})}save();toast("Stok hareketi kaydedildi");render()})}

function handleAction(action,id,el){try{if(action==="quick-add")openDialog("Hızlı İşlem","KISAYOLLAR",`<div class="product-picker"><button type="button" class="product-tile" data-quick="customer">Yeni Müşteri</button><button type="button" class="product-tile" data-quick="service">Servis Kaydı</button><button type="button" class="product-tile" data-quick="appointment">Randevu</button><button type="button" class="product-tile" data-quick="income">Gelir</button></div>`,()=>true,"Kapat"),setTimeout(()=>$$('[data-quick]').forEach(b=>b.onclick=()=>{$("#appDialog").close();({customer:()=>openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle"),service:()=>serviceDialog(),appointment:()=>appointmentDialog(),income:()=>financeDialog("Gelir")}[b.dataset.quick])()}),0);if(action==="add-customer")openDialog("Yeni Müşteri","CRM",customerForm(),fd=>saveCustomer(fd),"Müşteri Ekle");if(action==="customer-actions")customerActions(id);if(action==="add-product")openDialog("Ürün Ekle","STOK KARTI",productForm(),fd=>saveProduct(fd),"Ürün Ekle");if(action==="edit-product"){const s=db.stock.find(x=>x.id===id);openDialog("Ürünü Düzenle","STOK KARTI",productForm(s),fd=>saveProduct(fd,s),"Güncelle")}if(action==="add-movement")openDialog("Ürün Seç","STOK HAREKETİ",`<div class="field"><label>Stok ürünü</label><select id="movementProduct">${db.stock.map(s=>`<option value="${s.id}">${esc(s.name)}</option>`).join("")}</select></div>`,()=>{const s=db.stock.find(x=>x.id===$("#movementProduct").value);setTimeout(()=>movementDialog(s),100)},"Devam");if(action==="add-income")financeDialog("Gelir");if(action==="add-expense")financeDialog("Gider");if(action==="edit-finance")financeDialog(db.finance.find(x=>x.id===id)?.type,db.finance.find(x=>x.id===id));if(action==="add-appointment")appointmentDialog();if(action==="new-service")serviceDialog();if(action==="service-detail"||action==="technician-open"){const [c,s]=findService(id);technicianDialog(c,s)}if(action==="cart-add"){const l=salesCart.find(x=>String(x.productId)===String(id));l?l.qty++:salesCart.push({productId:id,qty:1});render()}if(action==="cart-remove"){salesCart.splice(+el.dataset.index,1);render()}if(action==="pay-save")runSales("payment");if(action==="create-proforma")runSales("proforma");if(action==="save-service")runSales("service");if(action==="view-quotes")quoteDialog();if(action==="choose-import"||action==="import-customers"||action==="restore-backup"){$("#fileInput").dataset.mode=action;$("#fileInput").click()}if(action==="commit-import")commitImport(window.importRows||[]);if(action==="ocr-to-stock"){const lines=$("#ocrText").value.split(/\n/).filter(Boolean);window.importRows=lines.map((x,i)=>{const parts=x.split(/[;|\t]/);return{id:uid("stk"),code:parts[0]||`OCR-${i+1}`,name:parts[1]||parts[0],category:parts[2]||"Bilgisayar",qty:+parts[3]||1,min:0,buy:+parts[4]||0,sell:+parts[5]||0,currency:(parts[6]||"TRY").trim(),barcode:parts[7]||""}});commitImport(window.importRows)}if(action==="download-template")download("ayec-stok-sablonu.csv","kod;ürün;kategori;adet;minimum;alış;satış;para birimi;barkod\nPC-001;Örnek Ürün;Bilgisayar;10;2;100;140;TRY;123456");if(action==="export-all")exportAll();if(action==="export-customers")download(`musteriler-${today()}.csv`,csv(db.customers));if(action==="export-stock")download(`stok-${today()}.csv`,csv(db.stock));if(action==="export-finance")download(`finans-${today()}.csv`,csv(db.finance));if(action==="save-settings"){db.settings={...db.settings,company:$("#setCompany").value,currency:$("#setCurrency").value,alertMinutes:+$("#setAlertMinutes").value,doubleClick:$("#setDouble").checked,contextMenu:$("#setContext").checked,appointmentAlerts:$("#setAlerts").checked,compact:$("#setCompact").checked};save();toast("Ayarlar kaydedildi")}if(action==="reset-demo"){if(confirm("Tüm yerel veriler örnek başlangıç durumuna dönecek. Devam edilsin mi?")){db=structuredClone(seed);save();render();toast("Örnek veri sıfırlandı","warning")}}}catch(err){toast(err.message||"İşlem tamamlanamadı","error")}}
function quoteDialog(){openDialog("Proforma Teklifler","SALES HUB",db.quotes.length?`<div class="table-wrap"><table><thead><tr><th>No</th><th>Müşteri</th><th>Tarih</th><th>Tutar</th><th>Durum</th><th></th></tr></thead><tbody>${db.quotes.map(q=>`<tr><td><strong>${q.no}</strong></td><td>${customerName(q.customerId)}</td><td>${q.date}</td><td>${money(q.total)}</td><td>${statusBadge(q.status)}</td><td><button type="button" class="mini" onclick="window.print()">Yazdır</button></td></tr>`).join("")}</tbody></table></div>`:empty("Proforma yok","Sales Hub üzerinden ilk teklifi oluşturun."),()=>true,"Kapat")}

const _ayecFinanceActionHandler=handleAction;
handleAction=function(action,id,el){if(action==="print-finance"){window.print();return}if(action==="collect-finance"){financeDialog("Gelir");return}if(action==="finance-period"||action==="finance-week"||action==="finance-month"){toast("Finans donemi secildi");return}if(action==="transfer-finance"||action==="tax-finance"||action==="finance-fiscal"){toast("Finans islemi hazir");return}_ayecFinanceActionHandler(action,id,el)};

function bindPage(){
 if(page==="invoices")bindInvoiceComposer();
 if(page==="finance"){$$("[data-finance-period]").forEach(button=>button.addEventListener("click",()=>{ayecFinancePeriod=button.dataset.financePeriod;render()}));ayecLoadFinanceBankBalances()}
 if(page==="services"){const search=$("#serviceBoardSearch");search?.addEventListener("input",()=>{ayecServiceBoardQuery=search.value;const caret=search.selectionStart;$("#content").innerHTML=renderServiceOperationsBoard();bindPage();const next=$("#serviceBoardSearch");next?.focus();next?.setSelectionRange(caret,caret)});$$("[data-service-board-filter]").forEach(button=>button.addEventListener("click",()=>{ayecServiceBoardFilter=button.dataset.serviceBoardFilter;render()}));$("[data-service-refresh]")?.addEventListener("click",()=>render())}
 const customerBanner=$(".customer-banners");if(customerBanner&&!customerBanner.querySelector('[data-customer-filter="vip"]')){const vip=document.createElement("button");vip.className="vip";vip.dataset.customerFilter="vip";vip.textContent="VIP M\u00fc\u015fteriler";customerBanner.insertBefore(vip,customerBanner.lastElementChild)}
 $$('[data-action]').forEach(b=>b.addEventListener("click",e=>{e.preventDefault();handleAction(b.dataset.action,b.dataset.id,b)}));
 $$('[data-kind]').forEach(row=>{bindInteractiveRow(row);row.addEventListener("dblclick",()=>{if(!db.settings.doubleClick)return;if(row.dataset.kind==="customer")customer360(db.customers.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="appointment")appointmentDialog(db.appointments.find(x=>x.id===row.dataset.id));if(row.dataset.kind==="stock"){const s=db.stock.find(x=>x.id===row.dataset.id);openDialog("Ürünü Düzenle","STOK",productForm(s),fd=>saveProduct(fd,s),"Güncelle")}if(row.dataset.kind==="service"){const [c,s]=findService(row.dataset.id);technicianDialog(c,s)}if(row.dataset.kind==="finance"){const item=db.finance.find(x=>String(x.id)===String(row.dataset.id));financeDialog(item?.type,item)}})});
 const cs=$("#customerSearch");if(cs){let mode="all",page=0,pageSize=10;const typeFilter=$("#customerTypeFilter"),locationFilter=$("#customerLocationFilter"),balanceFilter=$("#customerBalanceFilter"),sizeFilter=$("#customerPageSize");const serviceCount=c=>(c.services||[]).filter(s=>!/(teslim|tamamland|iptal|cancel)/i.test(String(s.status||""))).length;const f=()=>{const q=cs.value.toLocaleLowerCase("tr-TR"),type=typeFilter?.value||"",location=locationFilter?.value||"",balance=balanceFilter?.value||"";const rows=db.customers.filter(c=>{const values=Object.values(c.balances||{}).map(Number),debt=values.some(v=>v<0),credit=values.some(v=>v>0),zero=values.every(v=>!v),vip=/kurumsal|vip/i.test(c.type||""),service=serviceCount(c)>0;const segment=mode==="all"||(mode==="debt"&&debt)||(mode==="receivable"&&debt)||(mode==="vip"&&vip)||(mode==="services"&&service);const matchesType=!type||String(c.type||"Bireysel").toLocaleLowerCase("tr-TR").includes(type.toLocaleLowerCase("tr-TR"));const matchesLocation=!location||String(c.city||c.location||"").toLocaleLowerCase("tr-TR")===location.toLocaleLowerCase("tr-TR");const matchesBalance=!balance||(balance==="debt"&&debt)||(balance==="credit"&&credit)||(balance==="zero"&&zero);const haystack=[c.id,c.name,c.phone,c.email,c.company,c.company_name,c.tc_no,c.tax_number,c.tax_no,c.city,c.location].join(" ").toLocaleLowerCase("tr-TR");return segment&&matchesType&&matchesLocation&&matchesBalance&&haystack.includes(q)});const pages=Math.max(1,Math.ceil(rows.length/pageSize));page=Math.min(page,pages-1);$("#customerTable").innerHTML=customerTable(rows.slice(page*pageSize,(page+1)*pageSize));if($("#customerCount"))$("#customerCount").textContent=rows.length;if($("#customerPageIndicator"))$("#customerPageIndicator").textContent=`${page+1} / ${pages}`;if($("#customerPagePrev"))$("#customerPagePrev").disabled=page===0;if($("#customerPageNext"))$("#customerPageNext").disabled=page>=pages-1;if($("#customerSelectAll"))$("#customerSelectAll").checked=false;bindPageRows()};cs.oninput=f;if(typeFilter)typeFilter.onchange=()=>{page=0;f()};if(locationFilter)locationFilter.onchange=()=>{page=0;f()};if(balanceFilter)balanceFilter.onchange=()=>{page=0;f()};if(sizeFilter)sizeFilter.onchange=()=>{pageSize=Math.max(1,Number(sizeFilter.value)||10);page=0;f()};if($("#customerPagePrev"))$("#customerPagePrev").onclick=()=>{page=Math.max(0,page-1);f()};if($("#customerPageNext"))$("#customerPageNext").onclick=()=>{page++;f()};if($("#customerSearchClear"))$("#customerSearchClear").onclick=()=>{cs.value="";page=0;f()};$$('[data-customer-filter]').forEach(b=>b.onclick=()=>{mode=b.dataset.customerFilter;page=0;$$('[data-customer-filter]').forEach(x=>x.classList.toggle("selected",x===b));f()});const selectAll=$("#customerSelectAll");if(selectAll)selectAll.onchange=()=>$$('.customer-row-select').forEach(box=>box.checked=selectAll.checked);const multi=$("#customerMultiSelect");if(multi)multi.onclick=()=>{$("#customerTable").classList.toggle("multi-select");multi.classList.toggle("selected")};f()}
 if(page==="stock-locations"){
  const refresh=()=>{const host=$("#stockLocationResults");if(host)host.innerHTML=renderStockLocationRows();$$("[data-location-page]").forEach(button=>button.addEventListener("click",()=>{ayecStockLocationPage=Math.max(1,ayecStockLocationPage+(button.dataset.locationPage==="next"?1:-1));refresh()}))};
  const search=$("#stockLocationSearch");search?.addEventListener("input",()=>{ayecStockLocationQuery=search.value;ayecStockLocationPage=1;refresh()});
  $("#stockLocationFilter")?.addEventListener("change",event=>{ayecStockLocationId=event.target.value;ayecStockLocationPage=1;refresh()});
  $$ ("[data-location-tab]").forEach(button=>button.addEventListener("click",()=>{ayecStockLocationTab=button.dataset.locationTab;render()}));
  $$("[data-location-count]").forEach(button=>button.addEventListener("click",ayecStockCountDialog));
  $$("[data-location-kit]").forEach(button=>button.addEventListener("click",ayecStockKitDialog));
  $("[data-location-refresh]")?.addEventListener("click",()=>hydrateDesktop(true).then(()=>render()));
  $("[data-location-export]")?.addEventListener("click",()=>{
   const q=ayecStockLocationQuery.trim().toLocaleLowerCase("tr-TR");
   const rows=(db.stockLocationBalances||[]).filter(item=>(!ayecStockLocationId||String(item.location_id)===ayecStockLocationId)&&(!q||[item.product_name,item.product_code,item.barcode,item.location_name,item.vehicle_plate].join(" ").toLocaleLowerCase("tr-TR").includes(q)));
   download("depo-arac-stok.csv",csv(rows));
  });
  $$("[data-location-action]").forEach(button=>button.addEventListener("click",()=>button.dataset.locationAction==="create"?ayecCreateStockLocationDialog():ayecTransferStockDialog()));
  refresh();
 }
 const ss=$("#stockSearch"),sc=$("#stockCategory"),sl=$("#stockLevel");if(ss){const f=()=>{ayecStockCurrentPage=0;ayecRenderStockRows()};ss.oninput=f;sc.onchange=f;sl.onchange=f}
 const salesSearch=$("#salesProductSearch");if(salesSearch)salesSearch.oninput=()=>{$("#salesProducts").innerHTML=salesProducts(db.stock.filter(s=>s.name.toLocaleLowerCase("tr-TR").includes(salesSearch.value.toLocaleLowerCase("tr-TR"))));bindPage()};const customer=$("#salesCustomer");if(customer)customer.onchange=()=>salesCustomer=customer.value;$$('.cart-qty').forEach(i=>i.onchange=()=>{salesCart[+i.dataset.index].qty=Math.max(1,+i.value);render()});
 const dz=$("#dropZone");if(dz){dz.ondragover=e=>{e.preventDefault();dz.style.borderColor="var(--brand)"};dz.ondragleave=()=>dz.style.borderColor="var(--line)";dz.ondrop=e=>{e.preventDefault();handleImport(e.dataTransfer.files[0])}}
 $$('button[data-settings-section]').forEach(button=>button.onclick=()=>{settingsSection=button.dataset.settingsSection;render()});const settingsMobileSelect=$("#settingsMobileSelect");if(settingsMobileSelect)settingsMobileSelect.onchange=()=>{settingsSection=settingsMobileSelect.value;render()};const settingsSearch=$("#settingsSearch");if(settingsSearch)settingsSearch.oninput=()=>{const q=settingsSearch.value.toLocaleLowerCase("tr-TR");$$('button[data-settings-section]').forEach(button=>button.hidden=!button.textContent.toLocaleLowerCase("tr-TR").includes(q))};const saveSettingsButton=$('[data-action="save-settings"]');if(saveSettingsButton)saveSettingsButton.addEventListener("click",()=>{const pairs={company_name:db.settings.company,default_currency:db.settings.currency,appointment_alert_minutes:db.settings.alertMinutes,web_double_click:db.settings.doubleClick,web_context_menu:db.settings.contextMenu,appointment_notifications:db.settings.appointmentAlerts,web_compact:db.settings.compact};Object.entries(pairs).forEach(([key,value])=>desktopWrite("settings",{key,value}))})
 if(saveSettingsButton)saveSettingsButton.addEventListener("click",async()=>{try{const controls=$$(".exact-setting");let savedCount=0;for(const control of controls){let value=control.type==="checkbox"?(control.checked?"1":"0"):control.value,scope=control.dataset.settingScope||"settings",key=control.dataset.settingKey;if(control.type==="password"&&!value)continue;if(control.type==="password"&&value.length<4){toast(`${key} en az 4 karakter olmalıdır`,"error");return}if(key==="security_answer_new"){const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(value.trim().toLocaleLowerCase("tr-TR")));value=[...new Uint8Array(digest)].map(x=>x.toString(16).padStart(2,"0")).join("");key="security_answer_hash"}await desktopWrite(scope,{key,value});savedCount++;if(scope==="settings")desktopSettings[key]=control.type==="password"?"":value;else desktopInternalSettings[key]=value;if(key==="current_sector"){currentSector=value;$("#sectorSelect").value=value;renderNav()}}if(savedCount)toast(`${savedCount} masaüstü ayarı kaydedildi`,"success")}catch(error){toast(`Ayar kaydedilemedi: ${error.message}`,"error")}})
 if($("#quickNotesHost")){loadQuickNotes();$("#quickNoteAdd").onclick=()=>quickNoteDialog()}
 if($("#settingsUsersHost"))loadSettingsUsers()
 if(settingsSection==="voice-shortcuts")bindVoiceShortcuts()
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
document.addEventListener("click",e=>{const b=e.target.closest('[data-action="customer-help"]');if(!b)return;openDialog("M\u00fc\u015fteri Y\u00f6netimi","CRM",`<p>M\u00fc\u015fteri kay\u0131tlar\u0131n\u0131 arama alan\u0131ndan isim, telefon, vergi numaras\u0131 veya e-posta ile filtreleyin.</p><p>Segment se\u00e7icileri bor\u00e7lular\u0131, tahsilat bekleyenleri, VIP\u2019leri ve a\u00e7\u0131k servisi olanlar\u0131 listeler.</p><p>Her sat\u0131rdaki <b>\u0130\u015flem Yap</b> men\u00fcs\u00fcnden m\u00fc\u015fteri i\u015flemlerine eri\u015fin.</p>`,()=>true,"Kapat")});
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
  const siblings=Array.from(button.parentElement.children);
  siblings.filter(item=>item.classList.contains("nav-parent")).forEach(parent=>{
   if(parent===button)return;
   parent.classList.remove("open");
   parent.setAttribute("aria-expanded","false");
  });
  siblings.filter(item=>item.classList.contains("submenu")).forEach(candidate=>{
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
document.addEventListener("click",event=>{const chip=event.target.closest("[data-stock-category]");if(!chip)return;const category=$("#stockCategory");if(!category)return;category.value=chip.dataset.stockCategory||"Tüm Kategoriler";category.dispatchEvent(new Event("change"));document.querySelectorAll(".stock-category-strip button").forEach(item=>item.classList.toggle("active",item===chip))});
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
function filterMobileNavigation(value){
 const query=String(value||"").trim().toLocaleLowerCase("tr-TR");
 const nav=$("#nav");
 if(!nav)return;
 if(!query){renderNav();return}
 $$(".nav-button",nav).forEach(button=>{button.hidden=Boolean(query&&!button.textContent.toLocaleLowerCase("tr-TR").includes(query))});
 $$(".submenu",nav).forEach(submenu=>{
  const childMatch=Boolean(query&&submenu.textContent.toLocaleLowerCase("tr-TR").includes(query));
  submenu.hidden=Boolean(query&&!childMatch);
  submenu.classList.toggle("open",childMatch);
  submenu.style.display=childMatch?"block":"none";
  const parent=submenu.previousElementSibling;
  if(parent){
   parent.classList.toggle("open",childMatch);
   parent.setAttribute("aria-expanded",String(childMatch));
   if(childMatch)parent.hidden=false;
  }
 });
 $$(".nav-group-title",nav).forEach(title=>{title.hidden=Boolean(query&&!title.nextElementSibling)});
}
 mobileNavSearch.addEventListener("input",()=>filterMobileNavigation(mobileNavSearch.value));
 const sidebarPin=$("#sidebarPin"),sidebarShell=$("#appShell"),sidebar=$("#sidebar");
 const sectorBrand=$("#sectorBrand");
 if(sectorBrand&&typeof MutationObserver!=="undefined"){new MutationObserver(()=>{const badge=currentSector==="otomotiv"?"OTOMOTIV MODU":"ERP";if(sectorBrand.textContent!==badge)sectorBrand.textContent=badge}).observe(sectorBrand,{childList:true,characterData:true,subtree:true})}
 let sidebarPinned=true;
 try{sidebarPinned=localStorage.getItem("ayec-sidebar-pinned")!=="0"}catch{}
 function setSidebarPinned(pinned,persist=true){sidebarPinned=Boolean(pinned);sidebarShell?.classList.toggle("sidebar-collapsed",!sidebarPinned);sidebarPin?.setAttribute("aria-pressed",String(sidebarPinned));const label=sidebarPinned?"Sol men\u00fc sabit":"Sol men\u00fc hover ile a\u00e7\u0131l\u0131r";sidebarPin?.setAttribute("title",label);sidebarPin?.setAttribute("aria-label",label);if(persist){try{localStorage.setItem("ayec-sidebar-pinned",sidebarPinned?"1":"0")}catch{}}}
 setSidebarPinned(sidebarPinned,false);
 sidebarPin?.addEventListener("click",()=>setSidebarPinned(!sidebarPinned));
 sidebar?.addEventListener("pointerenter",()=>{if(!sidebarPinned)sidebarShell?.classList.add("sidebar-peek")});
 sidebar?.addEventListener("pointerleave",()=>sidebarShell?.classList.remove("sidebar-peek"));
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
$("#globalSearchVoice").onclick=()=>{const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){toast("Bu tarayici sesli aramayi desteklemiyor.","warning");return}const recognition=new SpeechRecognition();recognition.lang="tr-TR";recognition.interimResults=false;recognition.maxAlternatives=1;const button=$("#globalSearchVoice");button?.classList.add("listening");recognition.onresult=event=>{const input=$("#globalSearch");if(!input)return;input.value=event.results?.[0]?.[0]?.transcript||"";input.dispatchEvent(new KeyboardEvent("keydown",{key:"Enter",bubbles:true}))};recognition.onerror=()=>toast("Sesli arama baslatilamadi.","warning");recognition.onend=()=>button?.classList.remove("listening");try{recognition.start()}catch{button?.classList.remove("listening");toast("Mikrofon kullanilamiyor.","warning")}};
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
 return `<div class="table-wrap dashboard-service-table"><table><thead><tr><th>${automotive?"İŞ EMRİ NO":"TAKİP NO"}</th><th>İŞLEMLER</th><th>MÜŞTERİ</th><th>${automotive?"ARAÇ TÜRÜ":"ÜRÜN GRUBU"}</th><th>MARKA</th><th>MODEL</th><th>ALIŞ TARİHİ</th><th>TESL\u0130M TARİHİ</th><th>SERVİS</th><th>ÜCRET</th><th>DURUM</th><th>${automotive?"ÖNCELİK":"ACİLİYET"}</th></tr></thead><tbody>${rows.map(s=>`<tr data-kind="service" data-id="${esc(s.no)}" data-customer="${esc(s.customerId)}"><td><strong>${esc(s.no)}</strong></td><td><div class="dashboard-row-actions"><button class="mini" data-action="service-detail" data-id="${esc(s.no)}" title="Servis ayrıntısı">ⓘ</button><button class="mini" data-action="technician-open" data-id="${esc(s.no)}" title="Teknisyen işlemi">⚙</button></div></td><td>${esc(s.customer)}</td><td>${esc(s.device_type||s.device||"Cihaz")}</td><td>${esc(s.brand||"—")}</td><td>${esc(s.model||s.device||"—")}</td><td>${esc(s.date||"—")}</td><td>${esc(s.delivery||"—")}</td><td>${esc(s.service||"Servis")}</td><td><strong>${money(s.amount||0,s.currency||"TRY")}</strong></td><td>${statusBadge(s.status||"Bekliyor")}</td><td>${statusBadge(s.priority||"Normal")}</td></tr>`).join("")}</tbody></table></div>`;
}
renderDashboard=function(){
 const automotive=currentSector==="otomotiv",services=dashboardServices(),visible=services.filter(service=>dashboardFilterMatch(service,dashboardFilter));
 const tileDefs=automotive?[
  ["test","KONTROLÜ TAMAMLANAN","Kontrol Tamamlandı","K","#05A85B"],["tamirde","SERVİSTEKİ ARAÇLAR","İş Emri Devam Ediyor","S","#F39C12"],["bekliyor","SIRAYA ALINACAKLAR","Servise Alınmadı","A","#1E88E5"],["iptal","İPTAL / İADE","İptal İade","X","#E24A3B"],["kargo","DIŞ SERVİSE GİDENLER","Dış Servise Verildi","D","#D41462"],["teslim","TESL\u0130M EDİLEN ARAÇLAR","Teslim Edildi","T","#0891B2"],["parca","PARÇA BEKLEYEN ARAÇ","Parça Bekliyor","P","#0E7AB4"],["borclu","BORÇLU ARAÇLAR","Borcu Var","B","#625DA8"]
 ]:[
  ["test","TAMİR EDİLENLER","Tamir Edildi","T","#05A85B"],["tamirde","TAM\u0130RDE OLANLAR","Tamiri Devam Etmekte","D","#F39C12"],["bekliyor","İŞLEME ALINACAKLAR","İşleme Alınmadı","İ","#1E88E5"],["iptal","İPTAL / İADE","İptal İade","X","#E24A3B"],["kargo","KARGOYA VERİLENLER","Kargoya Verildi","K","#D41462"],["teslim","TESL\u0130M EDİLENLER","Teslim Edildi","E","#0891B2"],["parca","PARÇA BEKLEYENLER","Parça Bekliyor","P","#0E7AB4"],["borclu","BORÇLU OLANLAR","Borcu Var","B","#625DA8"]
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
 return `<section class="company-logo-card"><div class="company-logo-preview"><img id="companyLogoPreview" src="/api/desktop/company-logo?v=${Date.now()}" alt="Firma logosu"><span>Firma logosu seçilmedi</span></div><div><h3>Firma Logosu</h3><p class="muted">PNG, JPG veya WEBP yükleyin. Logo aynı masaüstü ayarına kaydedilir ve üç proforma şablonunda otomatik kullanılır.</p><div class="actions"><button type="button" class="primary" data-action="upload-company-logo">Logo Seç / Değiştir</button><button type="button" class="danger" data-action="remove-company-logo">Logoyu Kaldır</button></div></div></section>${body}`;
};
function handleCompanyLogoPreview(event){
 const image=event.target;
 if(image?.id!=="companyLogoPreview")return;
 if(event.type==="load"){image.hidden=false;if(image.nextElementSibling)image.nextElementSibling.hidden=true}
 else image.hidden=true;
}
document.addEventListener("load",handleCompanyLogoPreview,true);
document.addEventListener("error",handleCompanyLogoPreview,true);
function refreshCompanyLogo(){
 const image=$("#brandLogo"),initial=$("#brandInitial"),company=$("#brandCompanyName");
 if(company)company.textContent=String(desktopSettings.company_name||desktopSettings.company||"AYEC Pro");
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
  const serviceResult=await apiFetch("/api/desktop/table/devices",{method:"POST",body:JSON.stringify({tracking_no:serviceNo,customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,device_type:currentSector==="otomotiv"?"Ara\u00e7":"Cihaz",device_model:device,fault_description:`Sales Hub kaydı — ${no}`,status:"Bekliyor",entry_date:today(),service_source:"Web Sales Hub",priority:"Normal",payment_status:"Beklemede"})});
  customer.services=customer.services||[];customer.services.unshift({id:String(serviceResult.id),date:today(),no:serviceNo,device,device_type:currentSector==="otomotiv"?"Ara\u00e7":"Cihaz",model:device,status:"Bekliyor",note:`Sales Hub kaydı — ${no}`,amount:0,currency:"TRY",service:"Web Sales Hub",priority:"Normal",payment_status:"Beklemede"});salesCart=[];save();activity(`${serviceNo} Sales Hub üzerinden oluşturuldu`,"⚒");render();toast("Servis Müşteri 360 geçmişine ve masaüstü servis listesine kaydedildi","success");
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
function updateShellStatus(){
 const rateNode=$("#shellExchangeRate");
 if(!rateNode)return;
 const rates=exchangeRateState?.rates||exchangeRateState||{};
 const usd=Number(rates.USD?.selling||0);
 const formatted=usd>0?new Intl.NumberFormat("tr-TR",{minimumFractionDigits:2,maximumFractionDigits:2}).format(usd):"--";
 rateNode.textContent=`USD kuru: ${formatted}${usd>0?" TL":""}`;
}
let salesCurrency=["TRY","USD","EUR"].includes(localStorage.getItem("ayec_sales_currency"))?localStorage.getItem("ayec_sales_currency"):"TRY";
let salesManualRates={};
let salesCategoryFilter="all";
let salesDiscountPercent=5;
let salesCustomDiscountOpen=false;
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
  {id:"banks",icon:"\u25a4",label:"Banka Hesaplar\u0131"},{id:"loans",icon:"\u25a4",label:"Kredi"},{id:"checks",icon:"\u25a5",label:"\u00c7ek / Senet"},{id:"invoices",icon:"\u25b1",label:"E-Fatura"}
 ]},
 {group:"Proje & Ekip",items:[{id:"projects",icon:"▣",label:"Proje Yönetimi"},{id:"project-archive",icon:"▤",label:"Proje Arşivi"},{id:"personnel",icon:"♟",label:"Personel Yönetimi"},{id:"partners",icon:"♧",label:"Çalışma Ortakları"}]},
 {group:"Sistem",items:[{id:"knowledge",icon:"▧",label:"Bilgi Bankası"},{id:"settings",icon:"⚙",label:"Ayarlar"},{id:"backup",icon:"▰",label:"Yedekleme"},{id:"support",icon:"?",label:"Destek"},{id:"audit",icon:"▤",label:"Log Kayıtları"},{id:"manual",icon:"▧",label:"Kullanım Kılavuzu"},{id:"dialog-catalog",icon:"▦",label:"Dialog Modülleri"}]}
];
menu.splice(0,menu.length,...modernMenu);

// Automotive uses its dedicated parts screen. Keep generic technical stock out.
for(const pageId of ["stock-parent","stock","stock-locations","movements","import"]){
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
  exchangeRateState=rates.rates||exchangeRateState;desktopPersonnel=source.personnel||[];desktopSettings=source.settings||desktopSettings;desktopInternalSettings=source.internal_settings||desktopInternalSettings;refreshCompanyLogo();updateShellStatus();
  if(source.current_sector)currentSector=source.current_sector;
  const desktopThemeName=String(desktopSettings.color_theme_full||"").trim().toLowerCase();
  const desktopTheme=desktopThemeName==="forest"||desktopThemeName==="orman"?"forest":"";
  const theme=desktopTheme||desktopSettings.web_theme||db.settings.theme||"midnight";applyTheme(theme);renderNav();
 }catch(error){toast(`Kur ve arayüz ayarları yüklenemedi: ${error.message}`,"warning")}
}
applyTheme(db.settings.theme||"light");
$("#themeBtn").onclick=themeDialog;
$("#interfaceEditBtn").onclick=interfaceEditorDialog;

let salesDraft={template:"modern",project:"",vat:0,discountPercent:5};
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
salesProducts=function(rows){
 const query=String($("#salesProductSearch")?.value||"").trim().toLocaleLowerCase("tr-TR");
 return rows.filter(product=>product.qty>0&&(salesCategoryFilter==="all"||String(product.category||"")===salesCategoryFilter)&&(!query||[product.name,product.code,product.barcode,product.category,product.brand,product.description].join(" ").toLocaleLowerCase("tr-TR").includes(query))).map(product=>{
  const selected=selectedPriceFromTry(productTryPrice(product));
  const converted=salesCurrency!==(product.currency||"TRY")?`<small class="sales-product-converted">${money(selected,salesCurrency)} ${salesCurrency}</small>`:"";
  return `<article class="sales-product-card"><header><code>${esc(product.code||product.barcode||"AYEC")}</code><span>${esc(product.qty)} ${esc(product.unit||"Adet")} ${"\u2022"} ${esc(product.category||"Stok")}</span></header><h3>${esc(product.name)}</h3><p>${esc(product.description||product.brand||product.category||"Stok kart\u0131")}</p><footer><div><small>Birim Sat\u0131\u015f (KDV Hari\u00e7)</small><strong>${money(product.sell,product.currency)}</strong>${converted}</div><button type="button" class="primary" data-action="cart-add" data-id="${esc(product.id)}">+ Ekle</button></footer></article>`
 }).join("")||empty("Stokta \u00fcr\u00fcn yok","\u00d6nce stok kart\u0131 ekleyin.");
};
cartHtml=function(){return salesCart.length?salesCart.map((line,index)=>{const product=db.stock.find(item=>String(item.id)===String(line.productId));if(!product)return"";const total=selectedPriceFromTry(productTryPrice(product)*Number(line.qty||0));return `<article class="sales-cart-line"><header><code>${esc(product.code||product.barcode||"AYEC")}</code><button type="button" class="mini" data-action="cart-remove" data-index="${index}" aria-label="Sepetten \u00e7\u0131kar">\u00d7</button></header><strong>${esc(product.name)}</strong><footer><div class="sales-quantity"><button type="button" data-sales-qty="-1" data-index="${index}" aria-label="Adedi azalt">-</button><input class="control cart-qty" type="number" min="1" max="${product.qty}" value="${line.qty}" data-index="${index}" aria-label="Adet"><button type="button" data-sales-qty="1" data-index="${index}" aria-label="Adedi art\u0131r">+</button></div><div class="sales-cart-price"><small>${line.qty} x ${money(selectedPriceFromTry(productTryPrice(product)),salesCurrency)}</small><b>${money(total,salesCurrency)}</b></div></footer></article>`}).join(""):empty("Sepet bo\u015f","Soldaki \u00fcr\u00fcn veya hizmetlerden kalem ekleyin.")};
renderSales=function(){
 const rate=selectedSalesRate(),subtotal=cartTotal(),subtotalTry=subtotal*rate,rateRecord=exchangeRateState[salesCurrency];
 const discountPercent=Math.max(0,Math.min(100,Number(salesDiscountPercent)||0)),discountAmount=subtotal*discountPercent/100,netSubtotal=subtotal-discountAmount,vatPercent=Math.max(0,Math.min(100,Number(salesDraft.vat)||0)),vatAmount=netSubtotal*vatPercent/100,total=netSubtotal+vatAmount;
 const selectedCustomer=db.customers.find(customer=>String(customer.id)===String(salesCustomer));
 const categories=[...new Set(db.stock.map(product=>String(product.category||"Stok").trim()).filter(Boolean))].sort((left,right)=>left.localeCompare(right,"tr"));
 const categoryTabs=[["all","T\u00fcm\u00fc",db.stock.length],...categories.map(category=>[category,category,db.stock.filter(product=>product.category===category).length])].map(([id,label,count])=>`<button type="button" class="${salesCategoryFilter===id?"active":""}" data-sales-category="${esc(id)}"><span>${esc(label)}</span><b>${count}</b></button>`).join("");
 const customerOptions=db.customers.map(customer=>`<option value="${esc(customer.id)}" ${String(salesCustomer)===String(customer.id)?"selected":""}>${esc(customer.name)}</option>`).join("");
 const currencyButtons=["USD","EUR","TRY"].map(code=>`<button type="button" class="${salesCurrency===code?"active":""}" data-sales-currency="${code}">${{USD:"$ USD",EUR:"EUR",TRY:"TRY"}[code]}</button>`).join("");
 const rateText=salesCurrency==="TRY"?"T\u00fcrk Liras\u0131 ana para birimi":rate?`1 ${salesCurrency} = ${money(rate,"TRY")} ${esc(rateRecord?.source||"Manuel kur")}`:`${salesCurrency} kuru bulunamad\u0131; kuru girin`;
 const discountButtons=[0,5,10,15].map(value=>`<button type="button" class="${discountPercent===value?"active":""}" data-sales-discount="${value}">%${value}</button>`).join("");
 return `${pageHead("Teklif Olu\u015ftur","Stok ve hizmet kalemlerini m\u00fc\u015fteri teklifine d\u00f6n\u00fc\u015ft\u00fcr\u00fcn.",'<button class="secondary" data-action="view-quotes">T\u00fcm Teklifler</button>')}<div class="sales-reference-layout"><section class="card sales-catalog-panel"><div class="sales-reference-customer"><div class="sales-customer-avatar">${esc((selectedCustomer?.name||"A").trim().slice(0,1).toLocaleUpperCase("tr-TR"))}</div><div class="sales-customer-main"><select class="control" id="salesCustomer"><option value="">M\u00fc\u015fteri se\u00e7in</option>${customerOptions}</select>${selectedCustomer?`<div class="sales-customer-details"><strong>${esc(selectedCustomer.company||selectedCustomer.company_name||selectedCustomer.name)}</strong><span>${esc(selectedCustomer.phone||selectedCustomer.phone1||"Telefon eklenmemi\u015f")}</span><span>Bakiye: ${money(selectedCustomer.balances?.TRY||0,"TRY")}</span></div>`:`<p>M\u00fc\u015fteri se\u00e7ilmedi</p>`}</div><div class="sales-customer-actions"><span>&#128197; ${today()}</span><span>Vade: Pe\u015fin / Cari</span><button type="button" class="secondary" data-sales-focus-customer>M\u00fc\u015fteri De\u011fi\u015ftir</button><button type="button" class="secondary" data-action="add-customer">+ Yeni M\u00fc\u015fteri</button></div></div><div class="sales-product-toolbar"><input class="control search" id="salesProductSearch" placeholder="Barkod okutun veya par\u00e7a ad\u0131 / kodu ile aray\u0131n... [Enter: H\u0131zl\u0131 Ekle]"><button type="button" class="secondary" data-sales-focus-barcode>F2 Barkod</button><button type="button" class="secondary" data-sales-filter>Filtreler</button></div><nav class="sales-category-strip" aria-label="\u00dcr\u00fcn kategorileri">${categoryTabs}</nav><div id="salesProducts" class="product-picker">${salesProducts(db.stock)}</div><footer class="sales-catalog-footer"><span>Barkod tarama modu: A\u00e7\u0131k</span><span>Fiyat listesi: Bayi \u00d6zel Toplam</span><span>K\u0131sayollar: F1 Arama | F2 Barkod | F5 Teklif | F8 Bor\u00e7</span></footer></section><aside class="card sales-checkout-panel"><header class="sales-cart-header"><div><h2>\u0130\u015flem Sepeti &amp; Kalemler</h2><small>${salesCart.length} Kalem | ${salesCart.reduce((sum,line)=>sum+Number(line.qty||0),0)} Adet</small></div><button type="button" class="secondary" data-sales-clear ${salesCart.length?"":"disabled"}>Sepeti Bo\u015falt</button></header><div id="salesCart" class="sales-cart-list">${cartHtml()}</div><div class="sales-summary-line"><span>Ara Toplam (${salesCart.length} Kalem)</span><strong id="cartTotal">${money(subtotal,salesCurrency)}</strong></div><section class="sales-discount"><header><strong>\u0130skonto Uygula</strong><b>-% ${discountPercent} (-${money(discountAmount,salesCurrency)})</b></header><div class="sales-discount-options">${discountButtons}<button type="button" class="${salesCustomDiscountOpen?"active":""}" data-sales-discount="custom">\u00d6zel %</button></div>${salesCustomDiscountOpen?`<label class="sales-custom-discount">\u00d6zel iskonto <input class="control" id="salesCustomDiscount" type="number" min="0" max="100" step="0.5" value="${discountPercent}">%</label>`:""}</section><section class="sales-currency"><header><span>Para Birimi Se\u00e7imi</span><b>${rateText}</b></header><div class="sales-currency-options">${currencyButtons}</div>${salesCurrency!=="TRY"?`<label class="sales-rate-input">Sat\u0131\u015f Kuru<input class="control" id="salesExchangeRate" type="number" min="0.0001" step="0.0001" value="${rate||""}"></label>`:""}</section><div class="sales-totals"><div><span>\u0130skonto Sonras\u0131 Tutar</span><strong>${money(netSubtotal,salesCurrency)}</strong></div><div><span>Hesaplanan KDV (%${vatPercent})</span><strong>${money(vatAmount,salesCurrency)}</strong></div><label>KDV (%)<input class="control" id="salesVat" type="number" min="0" max="100" step="1" value="${vatPercent}"></label>${salesCurrency!=="TRY"?`<small>TRY kar\u015f\u0131l\u0131\u011f\u0131: ${money(total*rate,"TRY")}</small>`:""}</div><div class="sales-total-due"><div><small>\u00d6denecek Genel Toplam</small><strong>${money(total,salesCurrency)}</strong><span>T\u00fcm vergiler ve iskonto dahil</span></div></div><details class="sales-offer-options"><summary>Proforma ayr\u0131nt\u0131lar\u0131</summary><div class="proforma-options"><div class="field"><label>Teklif \u015eablonu</label><select id="proformaTemplate"><option value="modern" ${salesDraft.template==="modern"?"selected":""}>Modern</option><option value="corporate" ${salesDraft.template==="corporate"?"selected":""}>Kurumsal</option><option value="minimal" ${salesDraft.template==="minimal"?"selected":""}>Zebra</option></select></div><div class="field"><label>Proje / \u0130\u015f Ad\u0131</label><input id="salesProject" value="${esc(salesDraft.project)}" placeholder="\u0130ste\u011fe ba\u011fl\u0131"></div></div></details><div class="actions sales-actions"><button class="primary sales-primary-action" data-action="create-proforma">Teklif Olu\u015ftur <kbd>F5</kbd></button><div><button class="secondary" data-action="save-service">Bor\u00e7 / M\u00fc\u015fteriye \u0130\u015fle <kbd>F8</kbd></button><button class="success" data-action="pay-save">Do\u011frudan Tahsilat Al &amp; Kaydet</button></div></div></aside></div>`;
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
  salesDraft={template:$("#proformaTemplate")?.value||"modern",project:$("#salesProject")?.value.trim()||"",vat:Number($("#salesVat")?.value||0),discountPercent:salesDiscountPercent};
  const offerNo=editingOfferNumber||nextOfferNumber(),rates=Object.fromEntries(["TRY","USD","EUR"].map(code=>[code,rateForCode(code)]));
   const result=await apiFetch("/api/desktop/sales/commit",{method:"POST",body:JSON.stringify({mode,offer_id:mode==="proforma"&&editingOfferId?editingOfferId:undefined,customer_id:customerId,customer_name:customer.name,currency:salesCurrency,exchange_rate:rate,rates,lines:lines.map(({product_id,qty})=>({product_id,qty})),vat_rate:salesDraft.vat,discount_percent:salesDiscountPercent,template_type:salesDraft.template,project_name:salesDraft.project,offer_no:offerNo,device_type:currentSector==="otomotiv"?"Ara\u00e7":"Cihaz",payment_method:"Web"})});
  if(mode==="proforma"){
   const quote={id:String(result.offer_id),no:result.offer_no,offer_no:result.offer_no,date:today(),created_at:new Date().toISOString(),customerId:String(customer.id),customer_id:+customer.id,customer_name:customer.name,company_name:customer.company||customer.name,contact_name:customer.name,project_name:salesDraft.project,template_type:salesDraft.template,currency_code:result.currency,currency_symbol:result.currency_symbol,exchange_rate:result.exchange_rate,subtotal:result.subtotal,discount:result.discount,discount_percent:result.discount_percent,discount_try:result.discount_try,vat_rate:salesDraft.vat/100,vat_amount:result.vat_amount,total:result.total,subtotal_try:result.subtotal_try,vat_amount_try:result.vat_amount_try,total_try:result.total_try,status:"Teklif",items:lines.map(({product,qty})=>({productId:product.id,name:product.name,service:product.name,description:product.name,brand:product.brand||"",code:product.code||"",qty,price:selectedPriceFromTry(productTryPrice(product))}))};
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
 const vat=Number(offer.vat_rate||0);salesDraft={template:offer.template_type||"modern",project:offer.project_name||"",vat:vat<=1?vat*100:vat,discountPercent:Number(offer.discount_percent)||0};salesDiscountPercent=salesDraft.discountPercent;
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
renderSales=function(){const html=renderSalesBeforeOfferEdit();return editingOfferId?html.replace("Teklif Olu\u015ftur","Teklifi G\u00fcncelle"):html};

function financeTryValue(item){if(item.try_equivalent!==undefined&&item.try_equivalent!==null)return moneyNumber(item.try_equivalent);return moneyNumber(item.amount)*rateForCode(item.currency||"TRY")}
financeTable=function(rows){return `<div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tür</th><th>Kategori</th><th>Açıklama</th><th>Müşteri</th><th>Tutar</th><th></th></tr></thead><tbody>${rows.map(item=>`<tr data-kind="finance" data-id="${item.id}"><td>${esc(item.date)}</td><td>${statusBadge(item.type)}</td><td>${esc(item.category)}</td><td>${esc(item.description)}</td><td>${esc(item.customer)}</td><td><strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong>${(item.currency||"TRY")!=="TRY"?`<br><small class="muted">${money(financeTryValue(item),"TRY")}</small>`:""}</td><td><button class="mini" data-action="edit-finance" data-id="${item.id}">Düzenle</button></td></tr>`).join("")}</tbody></table></div>`};
renderFinance=function(filter=""){
 const todayKey=ayecLocalDateKey(new Date());
 const startDate=new Date(`${todayKey}T00:00:00`);
 if(ayecFinancePeriod==="week")startDate.setDate(startDate.getDate()-6);
 else if(ayecFinancePeriod==="month")startDate.setDate(1);
 else if(ayecFinancePeriod==="today")startDate.setHours(0,0,0,0);
 else startDate.setMonth(0,1);
 const rows=(filter?db.finance.filter(item=>item.type===filter):db.finance).filter(item=>{if(filter||ayecFinancePeriod==="year")return true;const key=ayecFinanceDateKey(item.date||item.created_at);return key>=ayecLocalDateKey(startDate)&&key<=todayKey});
 const income=db.finance.filter(item=>item.type==="Gelir").reduce((sum,item)=>sum+financeTryValue(item),0);
 const expense=db.finance.filter(item=>item.type==="Gider").reduce((sum,item)=>sum+financeTryValue(item),0);
 const net=income-expense;
 const usdRate=rateForCode("USD");
 const financeUsd=value=>usdRate>0?money(value/usdRate,"USD"):money(value,"TRY");
 const metricCurrency=usdRate>0?"USD":"TRY";
 const receivables=(db.customers||[]).reduce((sum,item)=>sum+Object.entries(item.balances||{}).reduce((balanceTotal,[currency,balance])=>balanceTotal+Math.max(0,-moneyNumber(balance))*rateForCode(currency),0),0);
 const bankAccounts=Array.isArray(db.bankAccounts)?db.bankAccounts:[];
 const bankTotal=bankAccounts.reduce((sum,item)=>sum+moneyNumber(item.balance??item.current_balance)*rateForCode(item.currency||"TRY"),0);
 const cashValue=bankAccounts.length?financeUsd(bankTotal):"--";
 const metrics=[
  [`TOPLAM C\u0130RO (${metricCurrency})`,financeUsd(income),"Br\u00fct sat\u0131\u015f (KDV dahil)","\u2197"],
  [`MAL\u0130YET VE G\u0130DER (${metricCurrency})`,financeUsd(expense),"Al\u0131\u015f + operasyon","\u2198"],
  [`NET K\u00c2R (${metricCurrency})`,financeUsd(net),"Gelir - gider net","\u25a3"],
  [`SICAK NAK\u0130T & BANKA (${metricCurrency})`,cashValue,"Kasa ve banka mevcutlar\u0131","\u265c"],
  [`BEKLEYEN ALACAKLAR (${metricCurrency})`,financeUsd(receivables),"Tahsil edilmemi\u015f bakiye","\u2667"]
 ];
 const quick='<section class="finance-quick card"><h3>H\u0131zl\u0131 \u0130\u015flemler</h3><div class="finance-quick-grid"><button data-action="export-finance">Excel \u0130ndir</button><button data-action="export-finance">PDF Rapor</button><button data-action="print-finance">Fi\u015f Yazd\u0131r</button><button class="green" data-action="collect-finance">Tahsilat Al</button><button class="green" data-action="add-income">Gelir Ekle</button><button class="red" data-action="add-expense">Gider Ekle</button><button data-action="transfer-finance">Virman / Transfer</button><button class="purple" data-action="tax-finance">Vergi Hesab\u0131</button></div></section>';
 const metricRow=metrics.map(([label,value,note,icon],index)=>`<article class="finance-ref-metric finance-ref-metric-${index+1}"><small>${label}</small><b>${value}</b><span>${note}</span><i>${icon}</i></article>`).join("");
 const dailyValues=Array.from({length:14},(_,index)=>{const day=new Date();day.setHours(0,0,0,0);day.setDate(day.getDate()-13+index);const key=ayecLocalDateKey(day);return db.finance.filter(item=>ayecFinanceDateKey(item.date||item.created_at)===key).reduce((sum,item)=>sum+(item.type==="Gider"?-1:1)*financeTryValue(item),0)});
 const dailyMin=Math.min(0,...dailyValues),dailyMax=Math.max(0,...dailyValues),dailyRange=Math.max(1,dailyMax-dailyMin);
 const chartPoints=dailyValues.map((value,index)=>`${(index*320/13).toFixed(1)},${(30-((value-dailyMin)/dailyRange)*26).toFixed(1)}`).join(" ");
 const last14Net=dailyValues.reduce((sum,value)=>sum+value,0);
 const weekly=`<section class="finance-weekly card"><div><h3>Haftal\u0131k Nakit Ak\u0131\u015f Dengesi</h3><small>Son 14 g\u00fcn: kay\u0131tl\u0131 hareketlerin net dengesi</small></div><strong>${financeUsd(last14Net)}</strong><svg class="finance-weekly-chart" viewBox="0 0 320 34" preserveAspectRatio="none" role="img" aria-label="Son 14 gun net nakit akis grafigi"><polyline points="${chartPoints}" /></svg></section>`;
 if(filter)return `${pageHead(`${filter} Kay\u0131tlar\u0131`,`Gelir ve gider hareketlerini inceleyin.`)}<section class="card finance-ledger">${financeTable(rows)}</section>`;
 return `${pageHead("Finansal Dashboard","Finansal hareketleri ve nakit durumunu tek ekranda y\u00f6netin.",'<button class="primary" data-action="finance-fiscal">Mali Y\u0131l Kontrolleri</button>')}<div class="finance-ref-period"><div class="actions"><button data-finance-period="today" class="${ayecFinancePeriod==="today"?"primary":"secondary"}">Bug\u00fcn</button><button data-finance-period="week" class="${ayecFinancePeriod==="week"?"primary":"secondary"}">Son 7 G\u00fcn</button><button data-finance-period="month" class="${ayecFinancePeriod==="month"?"primary":"secondary"}">Bu Ay</button><button data-finance-period="year" class="${ayecFinancePeriod==="year"?"primary":"secondary"}">Y\u0131ll\u0131k</button><button class="success" data-action="add-income">Gelir Ekle</button><button class="danger" data-action="add-expense">Gider Ekle</button><button class="primary" data-action="collect-finance">Tahsilat Al</button></div><select aria-label="Mali y\u0131l"><option>Canl\u0131 (${new Date().getFullYear()})</option></select></div><div class="finance-ref-metrics">${metricRow}</div><div class="finance-layout"><main><section class="card finance-ledger"><div class="card-head"><h3>Son Hareketler (Birle\u015fik Defter)</h3><span class="badge">${rows.length} Kay\u0131t Y\u00fckl\u00fc</span></div><div class="finance-ref-search"><input type="search" placeholder="Fi\u015f, ref, m\u00fc\u015fteri ara..."><button aria-label="Tablo g\u00f6r\u00fcn\u00fcm\u00fc">\u25a4</button><button aria-label="Liste g\u00f6r\u00fcn\u00fcm\u00fc">\u25a5</button><button data-action="print-finance" aria-label="Yazd\u0131r">\u25a3</button></div>${financeTable(rows)}</section>${weekly}</main><aside>${quick}<section class="finance-ref-status card"><h3>Mali Kontroller</h3><button class="primary" data-action="finance-fiscal">Mali Y\u0131l Kontrolleri</button><h3>Kay\u0131tl\u0131 D\u00f6viz Kurlar\u0131</h3><span>Kur bilgileri finans hareketlerinde kullan\u0131l\u0131r.</span><h3>KDV & Stopaj Durumu</h3><span>Kay\u0131tl\u0131 finans hareketleriyle hesaplan\u0131r.</span><h3>Kasaya ve Banka Bakiyeleri</h3><span data-finance-cash>${bankAccounts.length?cashValue:"Banka hesap bakiyesi y\u00fckleniyor."}</span></section></aside></div>`;
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
let ayecFinancePeriod="year";
async function ayecLoadFinanceBankBalances(){
 try{
  const data=await apiFetch("/api/desktop/table/bank_accounts?limit=500");
  if(document.body.dataset.page!=="finance")return;
  const accounts=(data.rows||[]).filter(item=>Number(item.is_active??item.active??1)===1&&Number(item.is_deleted||0)!==1);
  const balanceTry=accounts.reduce((sum,item)=>sum+moneyNumber(item.current_balance??item.balance)*rateForCode(item.currency||"TRY"),0);
  const rate=rateForCode("USD");
  const value=rate>0?money(balanceTry/rate,"USD"):money(balanceTry,"TRY");
  const metric=document.querySelector(".finance-ref-metric-4 b");
  if(metric)metric.textContent=value;
  const status=document.querySelector("[data-finance-cash]");
  if(status)status.textContent=accounts.length?value:"Aktif banka hesabı bulunamadı.";
 }catch(error){
  const status=document.querySelector("[data-finance-cash]");
  if(status)status.textContent="Banka bakiyesi yüklenemedi.";
 }
}
function ayecLocalDateKey(date){return `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,"0")}-${String(date.getDate()).padStart(2,"0")}`}
function ayecFinanceDateKey(value){const text=String(value||"").slice(0,10);let match=text.match(/^(\d{4})-(\d{2})-(\d{2})$/);if(match)return `${match[1]}-${match[2]}-${match[3]}`;match=text.match(/^(\d{2})\.(\d{2})\.(\d{4})$/);return match?`${match[3]}-${match[2]}-${match[1]}`:""}
let ayecServiceBoardQuery="";
let ayecServiceBoardFilter="all";
function serviceBoardLaneKey(item){const status=String(item.status||"").toLocaleLowerCase("tr-TR");if(/test|onay|kalite|kontrol/.test(status))return "test";return serviceStatusKey(item)}
function renderServiceOperationsBoard(){
 const all=allServices();
 const q=ayecServiceBoardQuery.trim().toLocaleLowerCase("tr-TR");
 const filtered=all.filter(item=>{
  const searchable=[item.no,item.customer,item.device,item.model,item.note,item.technician,item.status].join(" ").toLocaleLowerCase("tr-TR");
  if(q&&!searchable.includes(q))return false;
  if(ayecServiceBoardFilter==="urgent"&&!/acil|urgent/i.test(`${item.priority||""} ${item.urgency||""}`))return false;
  if(ayecServiceBoardFilter==="today"&&ayecFinanceDateKey(item.date||item.entry)!==ayecLocalDateKey(new Date()))return false;
  return true;
 });
 const lanes=[["bekliyor","BEK\u0130YOR","#fb7185"],["tamirde","TAM\u0130RDE","#93c5fd"],["parca","PAR\u00c7A BEKL\u0130YOR","#fbbf24"],["test","TEST / ONAY","#3b82f6"],["teslim","TESL\u0130M","#34d399"]];
 const laneHtml=lanes.map(([key,label,color])=>{
  const items=filtered.filter(item=>serviceBoardLaneKey(item)===key);
  return `<section class="service-board-lane" style="--lane:${color}"><header><h2>${label}</h2><b>${items.length}</b><button type="button" aria-label="${label} menü">...</button></header><div class="service-board-cards">${items.map(item=>`<article class="service-board-card" data-kind="service" data-id="${esc(item.no)}" data-customer="${esc(item.customerId)}"><div class="service-board-card-top"><strong>#${esc(item.no||"-")}</strong><span>${esc(item.priority||item.urgency||"Normal")}</span></div><h3>${esc(item.device||item.model||"Servis Cihazı")}</h3><p>${esc(item.note||item.fault||"")}</p><div class="service-board-customer">${esc(item.customer||"-")}</div>${item.technician?`<div class="service-board-tech">${esc(item.technician)}</div>`:""}<footer><span>${esc(item.date||item.entry||"")}</span><div><button type="button" data-action="service-detail" data-id="${esc(item.no)}">Gör</button><button type="button" data-action="technician-open" data-id="${esc(item.no)}">İşlem</button></div></footer></article>`).join("")||'<p class="service-board-empty">Bu aşamada iş emri yok.</p>'}</div></section>`;
 }).join("");
 const active=all.filter(item=>!serviceComplete(item)).length;
 const completed=all.filter(serviceComplete).length;
 const totalRevenue=all.reduce((sum,item)=>sum+moneyNumber(item.amount||item.price),0);
 return `${pageHead("Servis Operasyon Panosu","Teknik servis iş emirlerini, atölye aşamalarını ve lojistik durumunu izleyin.",'<button class="primary" data-action="new-service">Yeni İş Emri Ekle</button>')}<div class="service-board-toolbar"><input id="serviceBoardSearch" type="search" value="${esc(ayecServiceBoardQuery)}" placeholder="İş emri no, müşteri veya model ara..."><button type="button" data-service-board-filter="all" class="${ayecServiceBoardFilter==="all"?"active":""}">Tüm İş Emirleri (${all.length})</button><button type="button" data-service-board-filter="urgent" class="${ayecServiceBoardFilter==="urgent"?"active":""}">Aciller (${all.filter(item=>/acil|urgent/i.test(`${item.priority||""} ${item.urgency||""}`)).length})</button><button type="button" data-service-board-filter="today" class="${ayecServiceBoardFilter==="today"?"active":""}">Bugün</button><button type="button" data-service-refresh>Yenile</button></div><div class="service-board-kanban">${laneHtml}</div><div class="service-board-summary"><article><small>TOPLAM AKTİF İş EMRİ</small><b>${active}</b></article><article><small>ORT. ÇÖZÜM SÜRESİ</small><b>-</b></article><article><small>BUGÜNKÜ TESL\u0130MAT</small><b>${all.filter(item=>serviceStatusKey(item)==="teslim").length}</b></article><article><small>GÜNLİK SERVİS CİROSU</small><b>${money(totalRevenue)}</b></article></div>`;
}
renderServices=function(){return renderServiceOperationsBoard()};
renderTechnician=function(){
 const services=allServices().filter(service=>!serviceComplete(service)),completed=allServices().filter(serviceComplete).length;
 return `${pageHead("Teknisyen Paneli","Atama, durum, işlem notu, kullanılan parça, işçilik ve tahsilat sinyallerini tek formda yönetin.",'<button class="secondary" data-page="services">Tüm Servisler</button>')}<div class="metric-grid">${metric("Aktif İş",services.length,"Açık iş emirleri","⚒")}${metric("Atanmamış",services.filter(item=>!item.technician).length,"Teknisyen bekliyor","♟")}${metric("Parça Bekleyen",services.filter(item=>/parça/i.test(item.status||"")).length,"Stok ihtiyacı","!")}${metric("Tamamlanan",completed,"Toplam kapanan","✓")}</div><section class="card">${services.length?services.map(service=>`<article class="technician-card" data-kind="service" data-id="${esc(service.no)}" data-customer="${service.customerId}"><span class="activity-icon">⚒</span><div><strong>${esc(service.no)} · ${esc(service.customer)}</strong><p class="muted">${esc(service.device)} — ${esc(service.note||"Arıza açıklaması yok")}</p><div class="technician-meta"><span>Teknisyen: ${esc(service.technician||"Atanmadı")}</span><span>Öncelik: ${esc(service.priority||"Normal")}</span><span>Tahmini teslim: ${esc(service.delivery||"—")}</span></div></div><div class="actions">${statusBadge(service.status||"Bekliyor")}<button class="primary mini" data-action="technician-open" data-id="${esc(service.no)}">İşle</button></div></article>`).join(""):empty("Aktif iş yok","Yeni servis kaydı oluşturabilirsiniz.")}</section>`;
};

serviceDialog=function(customerId=""){
 const automotive=currentSector==="otomotiv";
 const technicians=desktopPersonnel.filter(person=>!person.role||/tekn|servis|usta|yönet/i.test(`${person.role} ${person.department||""}`));
 const selectedCustomer=db.customers.find(customer=>String(customer.desktopId||customer.id)===String(customerId));
 const customerOptions=db.customers.map(customer=>{
  const value=customer.desktopId||customer.id;
  const selected=String(value)===String(customerId)?" selected":"";
  return `<option value="${esc(value)}"${selected}>${esc(customer.name)}</option>`;
 }).join("");
 const assetFields=automotive
  ? `<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>Şasi / VIN</label><input name="vin"></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div><div class="field"><label>Yakıt Türü</label><select name="fuel_type"><option>Benzin</option><option>Dizel</option><option>Hibrit</option><option>Elektrik</option><option>LPG</option></select></div>`
  : `<div class="field"><label>Cihaz T\u00fcr\u00fc *</label><input name="device_type" required placeholder="Bilgisayar, Kamera, Telefon..."></div><div class="field"><label>Marka</label><input name="brand"></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Seri No / IMEI</label><input name="serial"></div>`
 const body=`<div class="service-accept-form">
  <section class="service-form-card service-form-customer">
   <header class="service-form-card-head"><div><span class="service-form-icon">\u2659</span><div><h3>MÜŞTERİ BİLGİLERİ</h3><small class="service-customer-state">Yeni Müşteri Kaydı</small></div></div><select class="service-customer-picker" name="customerId" aria-label="Kayıtlı Müşteri Seç"><option value="">Kayıtlı Müşteri Seç</option>${customerOptions}</select></header>
   <div class="service-form-fields service-customer-fields"><div class="field full"><label>Müşteri Adı / Ünvanı *</label><input name="customer_name" required value="${esc(selectedCustomer?.name||"")}" placeholder="Ad Soyad veya Firma Ünvanı giriniz..."></div><div class="field"><label>Kimlik / Vergi No</label><input name="customer_tax_id" value="${esc(selectedCustomer?.tc_no||selectedCustomer?.tax_id||selectedCustomer?.tax_no||"")}" placeholder="TCKN veya Vergi No"></div><div class="field"><label>İletişim Telefonu</label><input name="customer_phone" value="${esc(selectedCustomer?.phone||"")}" placeholder="0 (5XX) XXX XX XX"></div><div class="field"><label>Teslim Eden Kişi</label><input name="delivered_by_name" placeholder="Cihazı teslim eden kişi"></div><div class="field"><label>Teslim Eden Tel</label><input name="delivered_by_phone" placeholder="Teslim eden iletişim no"></div></div>
  </section>
  <section class="service-form-card service-form-device">
   <header class="service-form-card-head"><div><span class="service-form-icon">\u25a3</span><h3>CİHAZ BİLGİLERİ</h3></div><small>Teknik Tanımlama</small></header>
   <div class="service-form-fields service-device-fields">${assetFields}</div>
  </section>
  <section class="service-form-card service-form-fault">
   <header class="service-form-card-head"><div><span class="service-form-icon warning">\u26a0</span><h3>${automotive?"SERVİS DETAYLARI":"ARIZA & SERVİS DETAYLARI"}</h3></div><small class="service-ai-label">AI Destekli</small></header>
   <div class="service-form-fields service-fault-fields"><div class="field full"><label>${automotive?"Şikayet / Yapılacak İş":"Arıza Tanımı ve Müşteri Şikayeti"} *</label><textarea name="fault" required placeholder="Arıza detaylarını buraya yazın..."></textarea></div><div class="field"><label>Öncelik Derecesi</label><select name="priority"><option>Normal</option><option>Yüksek</option><option>Acil</option><option>Düşük</option></select></div><div class="field"><label>Tahmini Tutar (KDV Dahil)</label><input name="price" type="number" min="0" step="0.01" placeholder="0.00"></div><details class="service-extra-fields"><summary>Di\u011fer servis alanlar\u0131</summary><div class="service-extra-grid"><div class="field"><label>Teknisyen</label><select name="technician"><option value="">Atanmadı</option>${technicians.map(person=>`<option>${esc(person.name)}</option>`).join("")}</select></div><div class="field"><label>Durum</label><select name="status"><option>Bekliyor</option><option>Onay Bekliyor</option><option>İşlemde</option><option>Parça Bekliyor</option></select></div><div class="field full"><label>Müşteriye Açık Not</label><textarea name="repair_details" placeholder="Müşteriye gösterilecek not"></textarea></div><div class="field full"><label>Teknik İç Not</label><textarea name="internal_notes" placeholder="Teknik ekip notu"></textarea></div></div></details></div>
  </section>
  <section class="service-form-card service-form-security">
   <header class="service-form-card-head"><div><span class="service-form-icon">\u25c6</span><h3>CİHAZ GÜVENLİK & KİLİT</h3></div><small>Mobil / Tablet için</small></header>
   <div class="service-form-fields service-security-fields"><div class="field full"><label>Ekran Şifresi</label><input name="device_password" placeholder="Ekran Şifresi"></div><div class="field full"><label>Desen Kilidi veya PIN</label><input name="pattern_lock" placeholder="Desen Kilidi Tanımla veya PIN Gir"></div><div class="field"><label>Aksesuarlar / Teslim Alınanlar</label><input name="accessories" placeholder="Şarj cihazı, çanta..."></div><div class="field"><label>Tahmini Teslim</label><input name="estimated_date" type="date"></div><div class="field"><label>Garanti</label><select name="warranty_status"><option>Yok</option><option>Var</option><option>Firma Garantisi</option></select></div></div>
  </section>
  <label class="setting field full service-open-form"><span>Kaydettikten sonra servis formunu aç</span><input class="switch" type="checkbox" name="open_form" checked></label>
 </div>`;
 openDialog(automotive?"Yeni Araç Servis Kaydı":"Yeni Servis Kaydı","SERVİS KABUL FORMU",body,async fd=>{
  const values=Object.fromEntries(fd);
  let customer=db.customers.find(item=>String(item.desktopId||item.id)===String(values.customerId));
  if(!customer){
   const name=String(values.customer_name||"").trim();
   if(!name)throw Error("Müşteri adı girin");
   const customerPayload={name,phone:values.customer_phone||"",email:"",type:values.customer_tax_id?"Kurumsal":"Bireysel",tc_no:values.customer_tax_id||"",tax_id:values.customer_tax_id||""};
   const savedCustomer=await apiFetch("/api/desktop/table/customers",{method:"POST",body:JSON.stringify(customerPayload)});
   if(!savedCustomer?.id)throw Error("Müşteri kaydı oluşturulamadı");
   customer={id:String(savedCustomer.id),desktopId:Number(savedCustomer.id),name,phone:customerPayload.phone,email:"",type:customerPayload.type,services:[],quotes:[],balances:{TRY:0,USD:0,EUR:0}};
   db.customers.push(customer);
  }
  const no=`SRV-${new Date().getFullYear()}${String(Date.now()).slice(-7)}`;
  const device=automotive?`${values.plate} · ${values.brand} ${values.model}`:`${values.brand||""} ${values.model}`.trim();
  const customerKey=Number(customer.desktopId||customer.id)||undefined;
   const result=await apiFetch("/api/desktop/table/devices",{method:"POST",body:JSON.stringify({tracking_no:no,customer_id:customerKey,customer_name:customer.name,device_type:automotive?"Ara\u00e7":values.device_type,device_brand:values.brand||"",device_model:automotive?`${values.model} (${values.plate})`:values.model,serial_no:values.serial||values.vin||values.plate||"",vehicle_plate:values.plate||"",vehicle_vin:values.vin||"",fault_description:values.fault,repair_details:values.repair_details,internal_notes:values.internal_notes,accessories:values.accessories,device_password:values.device_password,bios_password:values.bios_password,pattern_lock:values.pattern_lock,delivered_by_name:values.delivered_by_name,delivered_by_phone:values.delivered_by_phone,price:+values.price||0,urgency:values.priority,priority:values.priority,technician:values.technician,status:values.status,approval_status:"Bekleme",entry_date:today(),estimated_date:values.estimated_date,warranty_status:values.warranty_status,payment_status:"Beklemede",service_source:automotive?"Web Otomotiv":"Web Teknik Servis"})});
  const service={id:String(result.id),date:today(),no,device,device_type:automotive?"Ara\u00e7":values.device_type,brand:values.brand||"",model:values.model,serial:values.serial||values.vin||"",status:values.status,note:values.fault,repair_details:values.repair_details,internal_notes:values.internal_notes,accessories:values.accessories,delivery:values.estimated_date,technician:values.technician,priority:values.priority,warranty_status:values.warranty_status,payment_status:"Beklemede",used_parts:[]};
  customer.services.unshift(service);save();activity(`${no} servis kaydı ${customer.name} için oluşturuldu`,automotive?"\u25c7":"\u2692");toast("Servis kaydı Müşteri 360 ve servis panosuna eklendi","success");render();
  if(values.open_form)setTimeout(()=>serviceDetailDialog(customer,service),80);
  return true;
 },automotive?"Araç Servisini Kaydet":"Servis Kaydet");
 const serviceDialogRoot=$("#appDialog");
 serviceDialogRoot.classList.add("service-accept-dialog");
 serviceDialogRoot.addEventListener("close",()=>serviceDialogRoot.classList.remove("service-accept-dialog"),{once:true});
 $("#dialogFooter").innerHTML='<span class="service-footer-status">ERP Core v2.0.4 Online</span><button type="button" class="secondary" id="dialogCancel">İptal</button><button type="button" class="secondary" id="serviceResetButton">Temizle</button><button type="submit" class="primary" id="dialogSubmit">Kaydı Tamamla ve Fiş Oluştur</button>';
 $("#dialogCancel").onclick=()=>serviceDialogRoot.close("cancel");
 $("#serviceResetButton").onclick=()=>$("#dialogForm").reset();
 const customerPicker=$("#dialogBody select[name=customerId]");
 if(customerPicker)customerPicker.addEventListener("change",()=>{
  const selected=db.customers.find(item=>String(item.desktopId||item.id)===String(customerPicker.value));
  if(!selected)return;
  const bodyRoot=$("#dialogBody");
  const nameInput=$("input[name=customer_name]",bodyRoot),phoneInput=$("input[name=customer_phone]",bodyRoot),taxInput=$("input[name=customer_tax_id]",bodyRoot);
  if(nameInput)nameInput.value=selected.name||"";
  if(phoneInput)phoneInput.value=selected.phone||"";
  if(taxInput)taxInput.value=selected.tc_no||selected.tax_id||selected.tax_no||"";
  const state=$(".service-customer-state",bodyRoot);
  if(state){state.textContent="Kayıtlı Müşteri Seçildi";state.classList.add("is-registered")}
 });
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
 const rememberDraft=()=>{salesDraft={template:$("#proformaTemplate")?.value||salesDraft.template,project:$("#salesProject")?.value||salesDraft.project,vat:Number($("#salesVat")?.value??salesDraft.vat),discountPercent:salesDiscountPercent}};
 const currency=$("#salesCurrency");if(currency)currency.onchange=()=>{rememberDraft();salesCurrency=currency.value;localStorage.setItem("ayec_sales_currency",salesCurrency);render()};
 const rate=$("#salesExchangeRate");if(rate)rate.onchange=()=>{setSalesRate(salesCurrency,rate.value);rememberDraft();render()};
 [$("#proformaTemplate"),$("#salesProject"),$("#salesVat")].filter(Boolean).forEach(control=>control.onchange=rememberDraft);
 const customer=$("#salesCustomer");if(customer)customer.onchange=()=>{salesCustomer=customer.value;render()};
 const customDiscount=$("#salesCustomDiscount");if(customDiscount)customDiscount.onchange=()=>{salesDiscountPercent=Math.max(0,Math.min(100,Number(customDiscount.value)||0));salesDraft.discountPercent=salesDiscountPercent;render()};
};

document.addEventListener("click",event=>{
 if(page!=="sales")return;
 const category=event.target.closest("[data-sales-category]");
 if(category){salesCategoryFilter=category.dataset.salesCategory;render();return}
 const discount=event.target.closest("[data-sales-discount]");
 if(discount){if(discount.dataset.salesDiscount==="custom"){salesCustomDiscountOpen=true;render();$("#salesCustomDiscount")?.focus()}else{salesCustomDiscountOpen=false;salesDiscountPercent=Number(discount.dataset.salesDiscount)||0;salesDraft.discountPercent=salesDiscountPercent;render()}return}
 const currency=event.target.closest("[data-sales-currency]");
 if(currency){salesCurrency=currency.dataset.salesCurrency;localStorage.setItem("ayec_sales_currency",salesCurrency);render();return}
 if(event.target.closest("[data-sales-focus-customer]")){$("#salesCustomer")?.focus();return}
 if(event.target.closest("[data-sales-focus-barcode]")){$("#salesProductSearch")?.focus();return}
 if(event.target.closest("[data-sales-filter]")){$(".sales-category-strip")?.scrollIntoView({behavior:"smooth",block:"nearest"});return}
 if(event.target.closest("[data-sales-clear]")){salesCart=[];render();return}
 const quantity=event.target.closest("[data-sales-qty]");
 if(quantity){const line=salesCart[Number(quantity.dataset.index)];if(line){line.qty=Math.max(1,Number(line.qty||1)+Number(quantity.dataset.salesQty));render()}return}
});
document.addEventListener("input",event=>{
 if(page==="sales"&&event.target.id==="salesCustomDiscount"){salesDiscountPercent=Math.max(0,Math.min(100,Number(event.target.value)||0));salesDraft.discountPercent=salesDiscountPercent;}
});
document.addEventListener("keydown",event=>{
 if(page!=="sales")return;
 if(event.key==="F2"){event.preventDefault();$("#salesProductSearch")?.focus();return}
 if(event.key==="F5"){event.preventDefault();handleAction("create-proforma");return}
 if(event.key==="F8"){event.preventDefault();handleAction("save-service");return}
 if(event.target.id==="salesProductSearch"&&event.key==="Enter"){
  event.preventDefault();const query=String(event.target.value||"").trim().toLocaleLowerCase("tr-TR");
  const product=db.stock.find(item=>item.qty>0&&[item.name,item.code,item.barcode].some(value=>String(value||"").toLocaleLowerCase("tr-TR").includes(query)));
  if(product){const line=salesCart.find(item=>String(item.productId)===String(product.id));line?line.qty++:salesCart.push({productId:product.id,qty:1});render()}
 }
});

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
  db.stockLocationSummary=source.stock_location_summary||{};db.stockLocationBalances=(source.stock_location_balances||[]).map(item=>({...item,location_id:String(item.location_id),part_id:String(item.part_id),quantity:Number(item.quantity||0),reserved_quantity:Number(item.reserved_quantity||0),min_quantity:Number(item.min_quantity||0)}));db.stockTransferHistory=source.stock_transfer_history||[];db.stockCounts=source.stock_counts||[];db.stockKits=source.stock_kits||[];
  scheduledAlerts=source.scheduled_alerts||[];desktopPersonnel=source.personnel||desktopPersonnel;exchangeRateState=source.exchange_rates||exchangeRateState;desktopSettings=source.settings||desktopSettings;desktopInternalSettings=source.internal_settings||desktopInternalSettings;currentSector=source.current_sector||currentSector;updateShellStatus();
  save();renderNav();render();if(!quiet)toast("Masaüstü veritabanı web arayüzüne bağlandı","success");return source;
 }catch(error){toast(`Masaüstü veritabanı yenilenemedi: ${error.message}`,"error");throw error}
};

let ayecStockLocationQuery="";
let ayecStockLocationId="";
let ayecStockLocationTab="stock";
let ayecStockLocationPage=1;
const ayecStockLocationPageSize=10;
function renderStockLocationRows(){
 const query=ayecStockLocationQuery.trim().toLocaleLowerCase("tr-TR");
 const locationRows=(db.stockLocationBalances||[]).filter(item=>(!ayecStockLocationId||String(item.location_id)===ayecStockLocationId)&&(!query||[item.product_name,item.product_code,item.barcode,item.location_name,item.vehicle_plate].join(" ").toLocaleLowerCase("tr-TR").includes(query)));
 const pages=Math.max(1,Math.ceil(locationRows.length/ayecStockLocationPageSize));
 ayecStockLocationPage=Math.min(ayecStockLocationPage,pages);
 const start=(ayecStockLocationPage-1)*ayecStockLocationPageSize;
 const visible=locationRows.slice(start,start+ayecStockLocationPageSize);
 const body=visible.map(item=>{const available=Math.max(0,item.quantity-item.reserved_quantity);return `<tr><td><strong>${esc(item.product_name||"-")}</strong><small>${esc(item.location_name||"")}</small></td><td>${esc(item.product_code||"-")}</td><td>${esc(item.barcode||"-")}</td><td>${esc(item.category||"-")}</td><td>${item.quantity}</td><td>${item.reserved_quantity}</td><td><strong>${available}</strong></td><td>${item.min_quantity}</td></tr>`}).join("");
 const transferRows=ayecStockLocationTab==="requests"?(db.stockTransferHistory||[]).filter(item=>/request|pending|return|bekliyor|iade|talep/i.test(String(item.status||""))):(db.stockTransferHistory||[]);
 const history=transferRows.map(item=>`<tr><td><strong>${esc(item.reference_no||"-")}</strong></td><td>${esc(item.source_name||"-")}</td><td>${esc(item.target_name||"-")}</td><td>${Number(item.line_count||0)}</td><td>${Number(item.total_quantity||0)}</td><td>${esc(item.status||"-")}</td><td>${esc(item.created_at||"-")}</td></tr>`).join("");
 const counts=(db.stockCounts||[]).map(item=>`<tr><td>${esc(item.location_name||"-")}</td><td>${Number(item.line_count||0)}</td><td>${esc(item.created_by||"-")}</td><td>${esc(item.created_at||"-")}</td><td>${esc(item.note||"-")}</td></tr>`).join("");
 const kits=(db.stockKits||[]).map(item=>`<tr><td><strong>${esc(item.name||"-")}</strong></td><td>${Number(item.item_count||0)}</td><td>${esc(item.item_names||"-")}</td><td><span class="badge success">Aktif</span></td></tr>`).join("");
 if(ayecStockLocationTab==="history"||ayecStockLocationTab==="requests")return `<div class="table-wrap stock-location-web-table"><table><thead><tr><th>Referans</th><th>Kaynak</th><th>Hedef</th><th>Kalem</th><th>Miktar</th><th>Durum</th><th>Tarih</th></tr></thead><tbody>${history||`<tr><td colspan="7">${ayecStockLocationTab==="requests"?"Bekleyen transfer veya iade talebi bulunamad\u0131.":"Transfer kayd\u0131 bulunamad\u0131."}</td></tr>`}</tbody></table></div>`;
 if(ayecStockLocationTab==="counts")return `<div class="stock-location-view-toolbar"><strong>Ara\u00e7 Say\u0131m\u0131 & Zimmet</strong><button type="button" class="primary" data-location-count>Se\u00e7ili Konumu Say</button></div><h3 class="stock-location-section-title">Son Say\u0131mlar</h3><div class="table-wrap stock-location-web-table"><table><thead><tr><th>Konum</th><th>Say\u0131lan Kalem</th><th>Say\u0131m\u0131 Yapan</th><th>Tarih</th><th>Not</th></tr></thead><tbody>${counts||'<tr><td colspan="5">Hen\u00fcz stok say\u0131m\u0131 kayd\u0131 yok.</td></tr>'}</tbody></table></div><h3 class="stock-location-section-title">Ara\u00e7lara Zimmetli Stok</h3><div class="table-wrap stock-location-web-table"><table><thead><tr><th>Ara\u00e7</th><th>Plaka</th><th>\u00dcr\u00fcn</th><th>Stok Kodu</th><th>Mevcut</th><th>Rezerve</th><th>Kullan\u0131labilir</th></tr></thead><tbody>${locationRows.filter(item=>item.location_type==="vehicle").map(item=>`<tr><td>${esc(item.location_name||"-")}</td><td>${esc(item.vehicle_plate||"-")}</td><td>${esc(item.product_name||"-")}</td><td>${esc(item.product_code||"-")}</td><td>${item.quantity}</td><td>${item.reserved_quantity}</td><td>${Math.max(0,item.quantity-item.reserved_quantity)}</td></tr>`).join("")||'<tr><td colspan="7">Se\u00e7ilen ara\u00e7larda zimmetli stok kayd\u0131 bulunamad\u0131.</td></tr>'}</tbody></table></div>`;
 if(ayecStockLocationTab==="kits")return `<div class="stock-location-view-toolbar"><div><strong>Haz\u0131r Kitler</strong><span>Aktif kit tan\u0131mlar\u0131</span></div><button type="button" class="primary" data-location-kit>Kit Olu\u015ftur</button></div><div class="table-wrap stock-location-web-table"><table><thead><tr><th>Kit</th><th>Par\u00e7a Say\u0131s\u0131</th><th>\u0130\u00e7erik</th><th>Durum</th></tr></thead><tbody>${kits||'<tr><td colspan="4">Haz\u0131r kit tan\u0131m\u0131 bulunamad\u0131.</td></tr>'}</tbody></table></div>`;
 if(ayecStockLocationTab==="vehicles")return `<div class="table-wrap stock-location-web-table"><table><thead><tr><th>Ara\u00e7 / Konum</th><th>Plaka</th><th>\u00dcr\u00fcn</th><th>Stok Kodu</th><th>Mevcut</th><th>Rezerve</th><th>Kullan\u0131labilir</th></tr></thead><tbody>${locationRows.filter(item=>item.location_type==="vehicle").map(item=>`<tr><td>${esc(item.location_name||"-")}</td><td>${esc(item.vehicle_plate||"-")}</td><td>${esc(item.product_name||"-")}</td><td>${esc(item.product_code||"-")}</td><td>${item.quantity}</td><td>${item.reserved_quantity}</td><td>${Math.max(0,item.quantity-item.reserved_quantity)}</td></tr>`).join("")||'<tr><td colspan="7">Ara\u00e7 stok kayd\u0131 bulunamad\u0131.</td></tr>'}</tbody></table></div>`;
 return `<div class="table-wrap stock-location-web-table"><table><thead><tr><th>\u00dcr\u00fcn / Konum</th><th>Stok Kodu</th><th>Barkod</th><th>Kategori</th><th>Mevcut</th><th>Rezerve</th><th>Kullanilabilir</th><th>Min. E\u015fik</th></tr></thead><tbody>${body||'<tr><td colspan="8">Se\u00e7ili konumda stok kayd\u0131 bulunamad\u0131.</td></tr>'}</tbody></table><footer class="stock-location-web-footer"><span>${locationRows.length?`${start+1}-${Math.min(start+ayecStockLocationPageSize,locationRows.length)} / ${locationRows.length}`:"0 / 0"} kay\u0131t</span><div><button type="button" data-location-page="prev" ${ayecStockLocationPage<=1?"disabled":""}>\u00d6nceki</button><b>${ayecStockLocationPage} / ${pages}</b><button type="button" data-location-page="next" ${ayecStockLocationPage>=pages?"disabled":""}>Sonraki</button></div></footer></div>`;
}
function renderStockLocations(){
 const summary=stockLocationWebSummary();
 const balances=db.stockLocationBalances||[];
 const vehicles=summary.locations.filter(item=>item.location_type==="vehicle");
 const transferCount=(db.stockTransferHistory||[]).filter(item=>/transit|yolda|bekliyor/i.test(String(item.status||""))).length;
 const totalAvailable=balances.reduce((sum,item)=>sum+Math.max(0,item.quantity-item.reserved_quantity),0);
 return `${pageHead("Depo ve Ara\u00e7 Stoklar\u0131 & Transfer Y\u00f6netimi","Depo, servis ara\u00e7\u0131 ve saha konumlar\u0131ndaki stok hareketlerini takip edin.",'<button class="secondary" data-location-action="create">+ Yeni Depo / Ara\u00e7 Ekle</button><button class="primary" data-location-action="transfer">Stok Transferi Ba\u015flat</button>')}<section class="stock-location-web-metrics"><article><small>MERKEZ DEPO</small><b>${Math.trunc(balances.filter(item=>item.location_type==="main"||item.location_type==="warehouse").reduce((sum,item)=>sum+item.quantity,0))} Kalem</b><span>${summary.warehouses} aktif lokasyon</span></article><article><small>SERV\u0130S ARA\u00c7LARI (MOBIL)</small><b>${Math.trunc(summary.vehicleQuantity)} Kalem</b><span>${vehicles.length} mobil saha ara\u00e7i</span></article><article><small>AKT\u0130F TRANSFER / YOLDA</small><b>${transferCount} Sevkiyat</b><span>${(db.stockTransferHistory||[]).length} kay\u0131tli transfer</span></article><article><small>KONUM / STOK KAYDI</small><b>${summary.locations} Konum</b><span>${Math.trunc(totalAvailable)} kullan\u0131labilir urun</span></article></section><section class="card stock-location-web-panel"><nav class="stock-location-web-tabs"><button type="button" data-location-tab="stock" class="${ayecStockLocationTab==="stock"?"active":""}">Konum Stoklar\u0131 (${balances.length})</button><button type="button" data-location-tab="requests" class="${ayecStockLocationTab==="requests"?"active":""}">Transfer &amp; \\u0130ade Talepleri</button><button type="button" data-location-tab="counts" class="${ayecStockLocationTab==="counts"?"active":""}">Ara\u00e7 Say\u0131m\u0131 &amp; Zimmet</button><button type="button" data-location-tab="kits" class="${ayecStockLocationTab==="kits"?"active":""}">Haz\u0131r Kitler (${(db.stockKits||[]).length})</button><button type="button" data-location-tab="history" class="${ayecStockLocationTab==="history"?"active":""}">Hareket Ge\u00e7mi\u015fi (${(db.stockTransferHistory||[]).length})</button><button type="button" data-location-action="transfer">Transfer Ba\u015flat</button></nav><div class="stock-location-web-filter"><label>Konum Filtrele<select id="stockLocationFilter"><option value="">T\u00fcm Konumlar (${summary.locations})</option>${summary.locations.map(item=>`<option value="${esc(item.id)}" ${ayecStockLocationId===String(item.id)?"selected":""}>${esc(item.name)}${item.vehicle_plate?` - ${esc(item.vehicle_plate)}`:""}</option>`).join("")}</select></label><input id="stockLocationSearch" type="search" value="${esc(ayecStockLocationQuery)}" placeholder="\u00dcr\u00fcn ad\u0131, stok kodu veya barkod ile aray\u0131n..."><button type="button" data-location-export>D\u0131\u015fa Aktar</button><button type="button" data-location-refresh>Yenile</button></div><div id="stockLocationResults">${renderStockLocationRows()}</div></section><section class="stock-location-web-insights"><article><h3>Mobil Stok G\u00fcvence Protokol\u00fc</h3><p>${vehicles.length} mobil ara\u00e7taki stok bakiyeleri ve rezervleri izlenir.</p></article><article><h3>Son Transfer Hareketi</h3><p>${esc(db.stockTransferHistory?.[0]?.reference_no||"Kay\u0131tli transfer bulunamad\u0131.")}</p></article><article><h3>Envanter Senkronizasyonu</h3><p>Bu g\u00f6r\u00fcn\u00fcm etkin depo ve saha stoklar\u0131ndan hesaplanir.</p></article></section>`;
}

function ayecCreateStockLocationDialog(){
 const body=`<div class="form-grid"><div class="field full"><label>Konum Ad\u0131 *</label><input name="name" required maxlength="120" placeholder="Ana Depo veya Servis Ara\u00e7i"></div><div class="field"><label>Konum T\u00fcr\u00fc</label><select name="location_type"><option value="warehouse">Depo</option><option value="vehicle">Servis Ara\u00e7i</option><option value="site">\u015eantiye / Saha</option></select></div><div class="field"><label>Ara\u00e7 Plakas\u0131</label><input name="vehicle_plate" maxlength="30"></div></div>`;
 openDialog("Yeni Depo / Ara\u00e7","STOK KONUMU",body,async fd=>{
  const values=Object.fromEntries(fd);
  await apiFetch("/api/desktop/stock/location-management",{method:"POST",body:JSON.stringify({action:"create-location",name:values.name,location_type:values.location_type,vehicle_plate:values.vehicle_plate})});
  await hydrateDesktop(true);
  toast("Depo veya ara\u00e7 konumu eklendi");
 });
}
function ayecStockCountDialog(){
 const locationId=ayecStockLocationId||String(db.stockLocations?.[0]?.id||"");
 const location=db.stockLocations?.find(item=>String(item.id)===locationId);
 const items=(db.stockLocationBalances||[]).filter(item=>String(item.location_id)===locationId);
 if(!location||!items.length){toast("Sayim icin stok bulunan bir konum secin.","warning");return}
 const rows=items.map((item,index)=>`<div class="stock-count-line"><label for="count-${index}">${esc(item.product_name||item.product_code||"Urun")} <small>${esc(item.product_code||"")} / Mevcut: ${item.quantity}</small></label><input id="count-${index}" name="count_${item.part_id}" type="number" min="0" step="0.01" value="${item.quantity}" required></div>`).join("");
 openDialog("Ara\u00e7 / Depo Stok Say\u0131m\u0131","STOK SAYIMI",`<div class="stock-count-form"><p>${esc(location.name)} konumundaki miktarlar\u0131 say\u0131m sonucuyla g\u00fcncelleyin.</p>${rows}<div class="field full"><label>Say\u0131m Notu</label><textarea name="note" maxlength="500"></textarea></div></div>`,async fd=>{
  const values=Object.fromEntries(fd);const lines=items.map(item=>({part_id:item.part_id,counted_quantity:values[`count_${item.part_id}`]}));
  await apiFetch("/api/desktop/stock/location-management",{method:"POST",body:JSON.stringify({action:"save-count",location_id:locationId,lines,note:values.note||""})});
  await hydrateDesktop(true);ayecStockLocationTab="counts";render();toast("Stok say\u0131m\u0131 kaydedildi");
 },"Say\u0131m\u0131 Kaydet");
}
function ayecStockKitDialog(){
 const products=db.stock||[];if(!products.length){toast("Kit olusturmak icin urun kaydi gerekli.","warning");return}
 const options=products.map(item=>`<option value="${esc(item.id)}">${esc(item.code||item.id)} - ${esc(item.name)}</option>`).join("");
 const lines=Array.from({length:5},(_,index)=>`<div class="stock-count-line"><label>Urun ${index+1}<small>Opsiyonel kit satiri</small></label><div class="stock-kit-line-inputs"><select name="part_${index}" ${index===0?"required":""}><option value="">Urun secin</option>${options}</select><input name="quantity_${index}" type="number" min="0.01" step="0.01" placeholder="Adet"></div></div>`).join("");
 openDialog("Hazir Kit Olustur","DEPO / KIT TANIMI",`<div class="stock-count-form"><div class="field full"><label>Kit Adi *</label><input name="name" required maxlength="120"></div>${lines}</div>`,async fd=>{
  const values=Object.fromEntries(fd);const clean=[];for(let index=0;index<5;index++){const partId=values[`part_${index}`],quantity=Number(values[`quantity_${index}`]);if(!partId&&!quantity)continue;if(!partId||!Number.isFinite(quantity)||quantity<=0)throw Error("Her kit satirinda urun ve pozitif miktar secin.");clean.push({part_id:partId,quantity})}if(!clean.length)throw Error("Kit icin en az bir urun secin.");
  await apiFetch("/api/desktop/stock/location-management",{method:"POST",body:JSON.stringify({action:"save-kit",name:values.name,lines:clean})});await hydrateDesktop(true);ayecStockLocationTab="kits";render();toast("Hazir kit kaydedildi");
 },"Kiti Kaydet");
}
function ayecTransferStockDialog(){
 const locations=db.stockLocations||[];
 const products=db.stock||[];
 if(locations.length<2||!products.length){toast("Transfer icin en az iki konum ve bir urun gerekli.","warning");return}
 const sourceOptions=locations.map(item=>`<option value="${esc(item.id)}">${esc(item.name)}${item.vehicle_plate?` - ${esc(item.vehicle_plate)}`:""}</option>`).join("");
 const productOptions=products.map(item=>`<option value="${esc(item.id)}">${esc(item.code||item.id)} - ${esc(item.name)}</option>`).join("");
 const lines=Array.from({length:5},(_,index)=>`<div class="stock-transfer-line"><label>Urun ${index+1}<small>Satir ${index+1}</small></label><select name="part_${index}" ${index===0?"required":""}><option value="">Urun secin</option>${productOptions}</select><input name="quantity_${index}" type="number" min="0.01" step="0.01" ${index===0?"required":""} inputmode="decimal" placeholder="Miktar"></div>`).join("");
 const body=`<div class="form-grid"><div class="field"><label>Kaynak Konum</label><select name="source_location_id" required>${sourceOptions}</select></div><div class="field"><label>Hedef Konum</label><select name="target_location_id" required>${sourceOptions}</select></div><div class="field full"><label>Transfer / Iade Kalemleri</label><div class="stock-transfer-lines">${lines}</div></div><div class="field full"><label>Transfer / Iade Notu</label><textarea name="note" maxlength="500" placeholder="Iade veya transfer aciklamasi"></textarea></div></div><p class="stock-transfer-hint">Iade icin kaynak ve hedef konumlari ters secin. Miktarlar secilen kaynak konumdan dusulur.</p>`;
 openDialog("Stok Transferi / Iade","DEPO / SAHA TRANSFERI",body,async fd=>{
  const values=Object.fromEntries(fd);
  if(values.source_location_id===values.target_location_id)throw Error("Kaynak ve hedef konum farkli olmali.");
  const transferLines=[];for(let index=0;index<5;index++){const partId=values[`part_${index}`],quantity=Number(values[`quantity_${index}`]);if(!partId&&!quantity)continue;if(!partId||!Number.isFinite(quantity)||quantity<=0)throw Error("Her transfer satirinda urun ve pozitif miktar secin.");transferLines.push({part_id:partId,quantity})}if(!transferLines.length)throw Error("En az bir urun satiri ekleyin.");
  await apiFetch("/api/desktop/stock/location-management",{method:"POST",body:JSON.stringify({action:"transfer-stock",source_location_id:values.source_location_id,target_location_id:values.target_location_id,lines:transferLines,note:values.note})});
  ayecStockLocationTab="history";
  await hydrateDesktop(true);
  toast("Stok transferi veya iade kaydedildi");
 });
}
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
 Object.assign(target,{name:data.name,company_name:data.company_name,tc_no:data.tc_no,phone:data.phone,phone2:data.phone2,email:data.email,type:data.type,tax_number:data.tax_number,tax_office:data.tax_office,term_days:+data.term_days||0,limit_amount:+data.limit_amount||0,commission_rate:+data.commission_rate||0,service_type:data.service_type,city:data.city,district:data.district,neighborhood:data.neighborhood,zip_code:data.zip_code,street:data.street,address:data.address,notes:data.notes,balances:{TRY:+data.TRY||0,USD:+data.USD||0,EUR:+data.EUR||0}});
 if(!c)db.customers.push(target);
 const persistedId=Number.isInteger(+target.id)?+target.id:Number.isInteger(+target.desktopId)?+target.desktopId:0;
 const payload={name:data.name,company_name:data.company_name,tc_no:data.tc_no,phone:data.phone,phone2:data.phone2,email:data.email,type:data.type,tax_number:data.tax_number,tax_office:data.tax_office,term_days:+data.term_days||0,limit_amount:+data.limit_amount||0,commission_rate:+data.commission_rate||0,service_type:data.service_type,city:data.city,district:data.district,neighborhood:data.neighborhood,zip_code:data.zip_code,street:data.street,address:data.address,notes:data.notes,balances:{TRY:+data.TRY||0,USD:+data.USD||0,EUR:+data.EUR||0}};
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

function renderTemporaryPasswordChange(identifier, tenantId, message=""){
 showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">HESAP GUVENLIGI</span><h2>Yeni parolanizi belirleyin</h2><p>Gecici parola ile normal oturum acilmaz.</p></div>${authAlert(message,message?"error":"info")}<form class="auth-form" id="temporaryPasswordForm"><label>Gecici parola<input name="temporary_password" type="password" autocomplete="current-password" required autofocus></label><label>Yeni parola<input name="new_password" type="password" minlength="10" autocomplete="new-password" required></label><label>Yeni parola tekrar<input name="confirm_password" type="password" minlength="10" autocomplete="new-password" required></label><button class="primary auth-submit" type="submit">Parolayi Degistir</button></form></div>`);
 const form=$("#temporaryPasswordForm");
 form.onsubmit=async event=>{
  event.preventDefault();
  const values=Object.fromEntries(new FormData(form));
  if(values.new_password!==values.confirm_password)return renderTemporaryPasswordChange(identifier,tenantId,"Parolalar eslesmiyor.");
  setAuthBusy(form,true,"Parola degistiriliyor...");
  try{
   await apiFetch("/api/auth/change-temporary-password",{method:"POST",body:JSON.stringify({tenant_id:tenantId,identifier,temporary_password:values.temporary_password,new_password:values.new_password})});
   renderLogin("Parolaniz guncellendi. Yeni parolanizla giris yapin.",identifier,"success");
  }catch(error){renderTemporaryPasswordChange(identifier,tenantId,error.message)}
  finally{setAuthBusy(form,false)}
 };
 bindAuthControls();
}

function renderLogin(message="",prefill="",messageType="info"){
 if(!authTenants.length)setTimeout(async()=>{try{const status=await apiFetch("/api/auth/status");authTenants=status.tenants||[];if(authTenants.length>1&&$("#loginForm"))renderLogin(message,$("#loginForm").identifier?.value||prefill,messageType)}catch{}},0);
 if(authTenants.length>1)setTimeout(()=>{const form=$("#loginForm");if(!form||form.querySelector("[name=tenant_id]"))return;const label=document.createElement("label");label.textContent="Firma";const select=document.createElement("select");select.name="tenant_id";select.innerHTML='<option value="">Otomatik se\u00e7</option>'+authTenants.map(t=>`<option value="${esc(t.id)}">${esc(t.company_name)}</option>`).join("");label.append(select);form.insertBefore(label,form.querySelector("label:nth-of-type(2)"))},0);
 showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">HOŞ GELDİNİZ</span><h2>AYEC Pro'ya giriş yapın</h2><p>Yönetim ekranınıza güvenli oturumla devam edin.</p></div>${authAlert(message,messageType)}<form class="auth-form" id="loginForm"><label>Kullanıcı adı veya e-posta<input name="identifier" value="${esc(prefill)}" autocomplete="username" required autofocus></label><label>Parola<div class="password-control"><input name="password" type="password" autocomplete="current-password" required><button type="button" data-toggle-password aria-label="Parolayı göster">◉</button></div></label><label class="remember-row"><input class="switch" name="remember" type="checkbox" value="1"><span><strong>Beni hatırla</strong><small>Bu cihazda 30 gün oturumu açık tut</small></span></label><button class="primary auth-submit" type="submit">Giriş Yap</button></form>${registrationEnabled?'<p class="auth-switch">Yeni kullanıcı mısınız? <button type="button" data-auth-view="register">Hesap oluşturun</button></p>':""}<div class="auth-help">Sorun yaşıyorsanız sistem yöneticinizle iletişime geçin.</div></div>`);
 if(setupRequired){const setupBack=document.createElement("p");setupBack.className="auth-switch";setupBack.innerHTML='<button type="button">Kuruluma geri dön</button>';setupBack.querySelector("button").onclick=()=>{wizardState.step=0;renderWizard()};$("#loginForm")?.after(setupBack)}
 const form=$("#loginForm");form.onsubmit=async event=>{
  event.preventDefault();setAuthBusy(form,true,"Giris yapiliyor...");
  try{
   const values=Object.fromEntries(new FormData(form));
   const result=await apiFetch("/api/auth/login",{method:"POST",body:JSON.stringify({...values,remember:Boolean(values.remember)})});
   if(result.password_change_required)return renderTemporaryPasswordChange(values.identifier,result.tenant_id);
   updateCurrentUser(result.user);hideAuth();await startApplication();
   toast(`Hos geldiniz, ${result.user.full_name||result.user.username}`,"success");
  }catch(error){renderLogin(error.message,form.identifier.value,"error")}
  finally{setAuthBusy(form,false)}
 };
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
  form.onsubmit=async event=>{
   event.preventDefault();setAuthBusy(form,true,"Giris yapiliyor...");
   try{
    const values=Object.fromEntries(new FormData(form));
    const result=await apiFetch("/api/auth/login",{method:"POST",body:JSON.stringify({...values,remember:Boolean(values.remember)})});
    if(result.password_change_required)return renderTemporaryPasswordChange(values.identifier,result.tenant_id);
    updateCurrentUser(result.user);hideAuth();await startApplication();
    toast(`Hos geldiniz, ${result.user.full_name||result.user.username}`,"success");
   }catch(error){
    const text=String(error.message||"").toLocaleLowerCase("tr-TR");
    if(text.includes("deneme")||text.includes("lisans"))renderLicenseActivation(error.message,form.identifier.value);
    else renderLogin(error.message,form.identifier.value,"error");
   }finally{setAuthBusy(form,false)}
  };
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
 form.onsubmit=async event=>{event.preventDefault();const values=Object.fromEntries(new FormData(form));setAuthBusy(form,true,"Talep olusturuluyor...");try{const result=await apiFetch("/api/license/orders/public",{method:"POST",body:JSON.stringify(values)});const order=result.order||{};const pay=result.payment||payment;showAuth(`<div class="auth-form-wrap"><div class="auth-form-head"><span class="auth-step-label">ODEME BILGILERI</span><h2>Talebiniz olusturuldu</h2><p>${esc(order.plan_label||"")} paketi icin odemeyi asagidaki hesaba yapin.</p></div><div class="auth-help"><strong>${esc(pay.bank_name||"")}</strong><br>${esc(pay.account_holder||"")}<br>${esc(pay.iban||"")}<br>Referans: <strong>${esc(order.payment_reference||"")}</strong></div><button class="primary auth-submit" id="paymentReportedButton" type="button">Odemeyi Yaptim</button><button class="secondary auth-submit" id="backToLoginButton" type="button">Giris Ekranina Don</button></div>`);$("#paymentReportedButton").onclick=async()=>{try{await apiFetch(`/api/license/orders/${order.id}/payment-reported/public`,{method:"POST",body:JSON.stringify({...values,payment_note:"M\u00fc\u015fteri odeme bildirimini web uygulamasindan gonderdi."})});renderLogin("Odeme bildiriminiz alindi. Yonetici onayindan sonra giris yapabilirsiniz.",values.identifier,"success")}catch(error){renderLicenseRequest(values.identifier,values.tenant_id);toast(error.message,"error")}};$("#backToLoginButton").onclick=()=>renderLogin("",values.identifier)}catch(error){renderLicenseRequest(values.identifier,values.tenant_id);toast(error.message,"error")}finally{setAuthBusy(form,false)}};
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
 if(step===0)return `<div class="wizard-welcome"><div class="wizard-orbit"><span>A</span></div><h2>AYEC Pro'yu işletmenize hazırlayalım</h2><p>Bu sihirbaz firma, sektör, yönetici ve e-posta ayarlarını güvenli biçimde oluşturur.</p><div class="sector-choice"><label><input type="radio" name="sector" value="teknik_servis" ${data.sector!=="otomotiv"?"checked":""}><span><b>Teknik Servis</b><small>Bilgisayar, akıllı ev ve g\u00fcvenlik sistemleri</small></span></label><label><input type="radio" name="sector" value="otomotiv" ${data.sector==="otomotiv"?"checked":""}><span><b>Otomotiv Servis</b><small>Araç, bakım, parça ve servis süreçleri</small></span></label></div></div>`;
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
  if(!customer)return toast("M\u00fc\u015fteri se\u00e7ilmelidir","error");
  const selectedDebtIds=new Set(),debtItemsById=new Map(),currencies=["USD","EUR","TRY"];let debtItemsLoaded=false;const selectedDebtTotal=currency=>[...selectedDebtIds].map(id=>debtItemsById.get(id)).filter(item=>item?.currency===currency).reduce((sum,item)=>sum+Number(item.remaining||0),0),debtFor=currency=>selectedDebtIds.size?selectedDebtTotal(currency):Math.max(0,-Number(customer.balances?.[currency]||0));
  const preferred=["TRY","USD","EUR"].find(currency=>debtFor(currency)>0)||"TRY",initialDebt=debtFor(preferred);
  const currencyCards=currencies.map(currency=>`<button type="button" class="collection-currency${currency===preferred?" active":""}" data-collection-currency="${currency}"><span>${currency}</span><strong>${money(debtFor(currency),currency)}</strong><small>${currency==="TRY"?"TL":"A\u00e7\u0131k bakiye"}</small></button>`).join("");
  const methods=["Nakit","Kredi Kart\u0131","Havale EFT","\u00c7ek Senet"];
  openDialog("Tahsilat Al","CAR\u0130 HAREKET",`<div class="collection-layout"><section class="collection-main"><div class="collection-customer"><span class="collection-avatar">${esc(String(customer.name||"M").slice(0,1).toUpperCase())}</span><div><small>M\u00dc\u015eTER\u0130</small><strong>${esc(customer.name)}</strong><span>${esc(customer.phone||customer.phone_number||"Cari tahsilat")}</span></div><b>AKT\u0130F</b></div><div class="collection-currencies">${currencyCards}</div><div class="collection-amount"><label for="collectionAmount">TAHS\u0130LAT TUTARI <i>*</i><small id="paymentDebtCaption">A\u00e7\u0131k bor\u00e7: ${money(initialDebt,preferred)}</small></label><div class="collection-amount-entry"><input id="collectionAmount" name="amount" type="number" min=".01" max="${initialDebt||0}" step=".01" value="${initialDebt||""}" required><span data-collection-suffix>${preferred}</span></div><div class="collection-quick">${[10,20,50,100].map(value=>`<button type="button" data-collection-add="${value}">+${value}</button>`).join("")}<button type="button" data-collection-all>T\u00fcm\u00fcn\u00fc Kapat</button></div></div><div class="collection-section-head"><strong>\u00d6DEME Y\u00d6NTEM\u0130</strong><span>Y\u00f6ntem se\u00e7in</span></div><div class="collection-methods">${methods.map((method,index)=>`<button type="button" data-collection-method="${esc(method)}" class="collection-method${index===0?" active":""}"><span>${["$","▣","⇄","▤"][index]}</span>${esc(method)}</button>`).join("")}</div><input type="hidden" name="currency" value="${preferred}"><select class="collection-native-field" name="payment_method" aria-label="\u00d6deme y\u00f6ntemi">${["Nakit","Banka","Kredi Kart\u0131","Web"].map(method=>`<option>${method}</option>`).join("")}</select><div class="collection-fields"><div class="field"><label>Referans / Takip No</label><input name="reference" placeholder="Servis veya dekont no"></div><div class="field"><label>Tarih</label><input type="date" value="${today()}" disabled></div><div class="field full"><label>A\u00e7\u0131klama</label><textarea name="description">M\u00fc\u015fteri tahsilat\u0131</textarea></div></div></section><aside class="collection-aside"><header><div><strong>A\u00c7IK BOR\u00c7 \u00d6ZET\u0130</strong><small>${esc(customer.name)}</small></div><span class="collection-count">CAR\u0130</span></header><div class="collection-balance-row"><span>Se\u00e7ili para biriminde bor\u00e7</span><strong id="collectionDebtValue">${money(initialDebt,preferred)}</strong></div><div class="collection-balance-row"><span>Tahsil edilecek</span><strong class="collection-accent" id="collectionSelectedValue">${money(initialDebt,preferred)}</strong></div><div class="collection-net"><small>\u0130\u015flem sonras\u0131 kalan bor\u00e7</small><strong id="paymentDebtSummary">${money(0,preferred)}</strong><span id="collectionTryEquivalent">TRY kar\u015f\u0131l\u0131\u011f\u0131: ${money(initialDebt*(rateForCode(preferred)||1),"TRY")}</span></div><div class="collection-note"><span>\u25ce</span><p>Bu i\u015flem m\u00fc\u015fteri cari bakiyesine kaydedilir. Bor\u00e7 tutar\u0131n\u0131 a\u015fan tahsilata izin verilmez.</p></div></aside></div>`,async formData=>{
    const values=Object.fromEntries(formData),currency=values.currency||"TRY",amount=Number(values.amount||0),debt=debtFor(currency);
    if(debt<=0)throw Error(`${currency} para biriminde a\u00e7\u0131k bor\u00e7 bulunmuyor`);
    if(amount<=0)throw Error("Tahsilat tutar\u0131 s\u0131f\u0131rdan b\u00fcy\u00fck olmal\u0131d\u0131r");
    if(amount>debt+0.0001)throw Error(`Tahsilat a\u00e7\u0131k borcu a\u015famaz (en fazla ${money(debt,currency)})`);
    const result=await apiFetch("/api/desktop/customer/payment",{method:"POST",body:JSON.stringify({customer_id:Number.isInteger(+customer.id)?+customer.id:null,customer_name:customer.name,amount,currency,description:values.description,payment_method:values.payment_method,reference:values.reference,selected_debt_ids:[...selectedDebtIds],exchange_rate:rateForCode(currency)})});
    await hydrateDesktop(true);activity(`${customer.name} m\u00fc\u015fterisinden ${money(result.amount,result.currency)} tahsil edildi`,"\u20ba");toast(`Tahsilat kaydedildi \u00b7 kalan bor\u00e7 ${money(result.open_debt_after,result.currency)}`);return true;
  },"Tahsilat\u0131 Kaydet");
  const dialog=$("#appDialog"),body=$("#dialogBody"),currencyInput=$("input[name=currency]",body),amountInput=$("input[name=amount]",body),caption=$("#paymentDebtCaption"),summary=$("#paymentDebtSummary");
  const debtPanel=document.createElement("section");debtPanel.className="collection-debt-list";debtPanel.innerHTML='<header><strong>BOR\u00c7 KALEMLER\u0130 &amp; FATURA E\u015eLE\u015eT\u0130RME</strong><small id="collectionDebtCount">Y\u00fckleniyor...</small></header><div id="collectionDebtItems" class="collection-debt-items"></div><footer><span>Se\u00e7ilen Kalemler Toplam\u0131</span><strong id="collectionDebtSelectedTotal">0</strong></footer>';$(".collection-balance-row",body).before(debtPanel);const debtItemsHost=$("#collectionDebtItems",debtPanel);
  async function loadDebtItems(currency){const customerId=Number(customer.id);if(!Number.isInteger(customerId)||customerId<=0){debtItemsHost.innerHTML='<p class="muted">M\u00fc\u015fteri bor\u00e7 kalemi listelenemedi.</p>';return}const result=await apiFetch(`/api/desktop/customer/open-debts?customer_id=${customerId}&currency=${encodeURIComponent(currency)}`);const items=(result.items||[]).sort((a,b)=>String(a.created_at||"").localeCompare(String(b.created_at||""))||Number(a.id)-Number(b.id));items.forEach(item=>{item.currency=currency;debtItemsById.set(Number(item.id),item)});const visibleIds=new Set(items.map(item=>Number(item.id)));if(!debtItemsLoaded){items.forEach(item=>selectedDebtIds.add(Number(item.id)));debtItemsLoaded=true}else [...selectedDebtIds].forEach(id=>{if(!visibleIds.has(id))selectedDebtIds.delete(id)});$("#collectionDebtCount",debtPanel).textContent=`${items.length} kalem bulundu`;debtItemsHost.innerHTML=items.length?items.map(item=>`<label class="collection-debt-item"><input type="checkbox" name="collectionDebt" value="${item.id}" ${selectedDebtIds.has(Number(item.id))?"checked":""}><span><small>${esc(item.created_at||"-")} · ${esc(item.tracking_no||"Cari bor\u00e7")}</small><strong>${esc(item.description||"Servis borcu")}</strong></span><b>${money(item.remaining,currency)}</b></label>`).join(""):'<p class="muted">Bu para biriminde A\u00e7\u0131k fatura veya bor\u00e7 kalemi yok.</p>';$$('input[name="collectionDebt"]',debtPanel).forEach(input=>input.onchange=()=>{const id=Number(input.value);if(input.checked)selectedDebtIds.add(id);else selectedDebtIds.delete(id);sync(false)})}
  loadDebtItems(currencyInput.value||"TRY").then(()=>sync(true)).catch(error=>{debtItemsHost.innerHTML=`<p class="muted">${esc(error.message)}</p>`});
  dialog.classList.add("collection-dialog");dialog.addEventListener("close",()=>dialog.classList.remove("collection-dialog"),{once:true});
  const sync=reset=>{const currency=currencyInput?.value||"TRY",debt=debtFor(currency);if(amountInput){amountInput.max=debt||0;if(reset)amountInput.value=debt?String(debt):""}if(caption)caption.textContent=`A\u00e7\u0131k bor\u00e7: ${money(debt,currency)}`;const amount=Math.min(Math.max(0,Number(amountInput?.value||0)),debt);if(summary)summary.textContent=money(Math.max(0,debt-amount),currency);$("#collectionDebtValue").textContent=money(debt,currency);$("#collectionSelectedValue").textContent=money(amount,currency);$("#collectionDebtSelectedTotal",debtPanel).textContent=money(selectedDebtTotal(currency),currency);$("[data-collection-suffix]").textContent=currency;$("#collectionTryEquivalent").textContent=`TRY kar\u015f\u0131l\u0131\u011f\u0131: ${money(amount*(rateForCode(currency)||1),"TRY")}`;$$("[data-collection-currency]",body).forEach(button=>button.classList.toggle("active",button.dataset.collectionCurrency===currency))};
  $$('[data-collection-currency]',body).forEach(button=>button.onclick=()=>{currencyInput.value=button.dataset.collectionCurrency;loadDebtItems(currencyInput.value).then(()=>sync(true)).catch(error=>{debtItemsHost.innerHTML=`<p class="muted">${esc(error.message)}</p>`})});
  $$('[data-collection-add]',body).forEach(button=>button.onclick=()=>{const debt=debtFor(currencyInput.value);amountInput.value=String(Math.min(debt,Number(amountInput.value||0)+Number(button.dataset.collectionAdd)));sync(false)});
  $("[data-collection-all]",body).onclick=()=>{amountInput.value=String(debtFor(currencyInput.value));sync(false)};
  $$('[data-collection-method]',body).forEach(button=>button.onclick=()=>{const select=$("select[name=payment_method]",body),choice=button.dataset.collectionMethod;select.value=choice==="Havale EFT"?"Banka":choice==="\u00c7ek Senet"?"Web":choice;$$('[data-collection-method]',body).forEach(item=>item.classList.toggle("active",item===button))});
  amountInput?.addEventListener("input",()=>sync(false));sync(false);
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
  return `<div class="table-wrap finance-table"><table><thead><tr><th>Tarih</th><th>T\u00fcr</th><th>Kategori</th><th>A\u00e7\u0131klama</th><th>M\u00fc\u015fteri</th><th>Orijinal</th><th>TRY</th><th>Kur</th><th>\u00d6deme</th><th>Referans</th><th></th></tr></thead><tbody>${rows.map(item=>`<tr data-kind="finance" data-id="${item.id}"><td data-label="Tarih">${esc(item.date||item.created_at||"\u2014")}</td><td data-label="T\u00fcr">${statusBadge(item.type||"\u2014")}</td><td data-label="Kategori">${esc(item.category||"\u2014")}</td><td data-label="A\u00e7\u0131klama">${esc(item.description||"\u2014")}</td><td data-label="M\u00fc\u015fteri">${esc(item.customer||item.customer_name||"\u2014")}</td><td data-label="Orijinal"><strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong></td><td data-label="TRY">${money(item.try_equivalent??financeTryValue(item),"TRY")}</td><td data-label="Kur">${esc(String(item.exchange_rate??1))}</td><td data-label="\u00d6deme">${esc(item.payment_method||"\u2014")}</td><td data-label="Referans">${esc(item.ref_no||item.tracking_no||"\u2014")}</td><td class="finance-action"><button class="mini" data-action="finance-detail" data-id="${item.id}">Detay</button></td></tr>`).join("")}</tbody></table></div>`;
};

function financeDetailDialog(item){
  const currency=String(item.currency||"TRY").toUpperCase();
  const original=Number(item.original_amount??item.amount??0)||0;
  const tryAmount=Number(item.try_equivalent??financeTryValue(item))||0;
  const rate=Number(item.exchange_rate||1)||1;
  const vat=Number(item.vat_amount||0)||0;
  const net=Number(item.net_amount??Math.max(0,original-vat))||0;
  const customer=String(item.customer||item.customer_name||"");
  const reference=String(item.ref_no||item.tracking_no||"");
  const lines=Array.isArray(item.lines)?item.lines:[];
  const lineRows=lines.map((line,index)=>{const quantity=Number(line.quantity??line.qty??1)||1,amount=Number(line.amount??line.total??(Number(line.unit_price||line.price||0)*quantity))||0;return `<tr><td>${index+1}</td><td><strong>${esc(line.name||line.description||"\u2014")}</strong>${line.code||line.sku?`<small>${esc(line.code||line.sku)}</small>`:""}</td><td>${esc(String(quantity))}</td><td>${money(line.unit_price??line.price??amount/quantity,currency)}</td><td>${money(amount,currency)}</td></tr>`}).join("")||`<tr><td>1</td><td><strong>${esc(item.description||item.category||"\u2014")}</strong></td><td>1</td><td>${money(original,currency)}</td><td>${money(original,currency)}</td></tr>`;
  const metadata=[["Kaynak",item.source||item.origin||item.type||"\u2014"],["Kay\u0131t ID",item.id||"\u2014"],["\u0130\u015flem Tarihi",item.date||item.created_at||"\u2014"],["\u0130\u015flem T\u00fcr\u00fc",item.type||"\u2014"],["Takip / Teklif No",reference||"\u2014"],["Cari / M\u00fc\u015fteri",customer||"\u2014"]];
  const metadataRows=metadata.map(([label,value])=>`<div><dt>${label}</dt><dd>${esc(String(value))}</dd></div>`).join("");
  const collectionReference=item.collection_reference||item.debt_reference||item.related_reference||"";
  const notes=item.transaction_note||item.payment_note||item.notes||"";
  const operations=Array.isArray(item.operations)?item.operations.join("\n"):String(item.operations||"");
  const body=`<div class="finance-detail-ref"><aside class="finance-detail-sidebar"><section class="finance-detail-spotlight"><div><small>\u0130\u015flem Tutar\u0131 (D\u00f6viz)</small><strong>${money(original,currency)}</strong><span>${currency} / TRY</span></div><b>${statusBadge(item.type||"Kaydedildi")}</b><div class="finance-detail-rate"><span><small>D\u00f6viz Kuru</small><strong>${esc(String(rate))} TRY</strong></span><span><small>TL Kar\u015f\u0131l\u0131\u011f\u0131</small><strong>${money(tryAmount,"TRY")}</strong></span></div></section><section class="finance-detail-panel finance-detail-meta"><dl>${metadataRows}</dl>${collectionReference?`<div class="finance-detail-collection"><small>Cari Bor\u00e7 Kapatma Referans\u0131</small><p>${esc(String(collectionReference))}</p></div>`:""}</section></aside><div class="finance-detail-main"><section class="finance-detail-panel finance-detail-lines"><header><h3>Stok / Hizmet Kalemleri</h3><span>${lines.length||1} Kalem</span></header><div class="table-wrap"><table><thead><tr><th>#</th><th>Stok / Detay A\u00e7\u0131klamas\u0131</th><th>Adet</th><th>Birim Fiyat</th><th>Tutar</th></tr></thead><tbody>${lineRows}</tbody></table></div><p class="finance-detail-stock-note">${lines.length?"T\u00fcm kalemler finans kayd\u0131na ba\u011fl\u0131.":"Bu i\u015flem i\u00e7in ayr\u0131 kalem kayd\u0131 bulunmuyor."}</p><div class="finance-detail-totals"><span>Net Tutar <b>${money(net,currency)}</b></span><span>KDV (${Number(item.vat_rate||20)}% ${vat?"Dahil":""}) <b>${vat?money(vat,currency):"\u2014"}</b></span><strong>Genel Toplam <b>${money(original,currency)}</b></strong></div></section><section class="finance-detail-panel finance-detail-notes"><h3>\u0130\u015flem A\u00e7\u0131klamas\u0131 &amp; Notlar</h3><div class="finance-detail-log"><small>Yap\u0131lan \u0130\u015flemler</small><p>${esc(operations||item.description||"A\u00e7\u0131klama girilmemi\u015f.")}</p></div><div class="finance-detail-log"><small>Tahsilat / \u0130\u015flem Notu</small><p>${esc(notes||item.description||"Not girilmemi\u015f.")}</p></div><footer><span>\u0130\u015flem Yetkilisi <b>${esc(item.created_by||item.operator||"\u2014")}</b></span><span>Zaman Damgas\u0131 <b>${esc(item.created_at||item.date||"\u2014")}</b></span></footer></section></div></div>`;
  openDialog("\u0130\u015flem Detay\u0131","F\u0130NANS & SERV\u0130S ENTEGRASYON KARTI",body,async()=>true,"Kapat");
  const cancel=$("#dialogCancel");
  if(cancel)cancel.hidden=true;
  $("#appDialog").classList.add("finance-detail-dialog");
  $("#dialogFooter").innerHTML=`<button type="button" class="secondary" data-finance-detail-action="print" data-id="${esc(String(item.id||""))}">Yazd\u0131r</button><button type="button" class="primary" data-finance-detail-action="edit" data-id="${esc(String(item.id||""))}">D\u00fczenle</button>`;
}

document.addEventListener("click",event=>{
  const button=event.target.closest("[data-finance-detail-action]");
  if(!button)return;
  const item=db.finance.find(row=>String(row.id)===String(button.dataset.id));
  if(!item)return;
  if(button.dataset.financeDetailAction==="print"){window.print();return}
  if(button.dataset.financeDetailAction==="edit"){
    $("#appDialog").close("edit");
    setTimeout(()=>financeDialog(item.type,item),0);
  }
});

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
if(managementCenterBtn)managementCenterBtn.onclick=()=>navigate("control-center");

let activeAdminTab = "dashboard";

function renderControlCenter(){
  return `${pageHead("Y\u00f6netim Merkezi","AYEC Pro Uretici Yonetim Paneli. Firmalari, lisanslari, bildirimleri ve sunucu sagligini tek ekrandan yonetin.",'<button class="secondary" data-control-refresh>Verileri Yenile</button>')}
  <section class="control-operator" id="controlOperator">
    <div>
      <span class="eyebrow">PLATFORM OPERATORU</span>
      <strong id="adminVendorName">AYEC Pro</strong>
      <small id="adminVendorDetails">Y\u00fckleniyor...</small>
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
                        <button class="mini" data-control-user="${tenant.id}:${u.id}" data-tenant-idx="${index}" data-user-idx="${ui}">D\u00fczenle</button>
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
                const delivery = res.mail_sent
                  ? `Gecici parola yenileme baglantisi ${esc(res.recipient || "kayitli e-posta")} adresine gonderildi.`
                  : `E-posta gonderilemedi: ${esc(res.mail_message || "SMTP hatasi")}`;
                let fallback = "";
                if (!res.mail_sent) {
                  try { await navigator.clipboard.writeText(res.reset_url); } catch(e) {}
                  fallback = `<div class="field"><label>Destek baglantisi</label><textarea readonly style="height: 60px;">${esc(res.reset_url)}</textarea></div>`;
                }
                openDialog("Sifre Sifirlama Baglantisi", "30 DAKIKA GECERLI", `
                <div class="field"><label>Kullanici</label><input disabled value="${esc(res.username)}"></div>
                <p class="muted">${delivery}</p>${fallback}
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
  {group:"SERVIS OPERASYON",items:[
    {id:"service-parent",icon:"&#9881;",label:"Servis Y\u00f6netimi",children:[
      {id:"dashboard",label:"Genel Bak\u0131\u015f"},
      {id:"services",label:"Servis Panosu"},
      {id:"service-list",label:"Servis Listesi"},
      {id:"service-status",label:"Durum Paneli"},
      {id:"technician",label:"Teknisyen Paneli"},
      {id:"field-service",label:"Saha Haritas\u0131"},
      {id:"appointments",label:"Randevular"},
      {id:"logistics",label:"Lojistik & Garanti Y\u00f6netimi"},
      {id:"job-reports",label:"\u0130\u015f / Servis Takibi Raporlar\u0131"},
      {id:"assistant",label:"AI Asistan"}
    ]},
    {id:"service-settings-parent",icon:"&#9881;",label:"Servis Ayarlar\u0131",children:[
      {id:"product-groups",label:"\u00dcr\u00fcn Grubu Y\u00f6netimi"},
      {id:"brands",label:"Marka Adlar\u0131 Y\u00f6netimi"},
      {id:"report-templates",label:"Rapor C\u00fcmle Kal\u0131plar\u0131"},
      {id:"service-definitions",label:"\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi"}
    ]},
    {id:"customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteri Hub",children:[
      {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
      {id:"customers",label:"M\u00fc\u015fteri Listesi"},
      {id:"contracts",label:"S\u00f6zle\u015fmeler"},
      {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
      {id:"announcements",label:"Duyurular"}
    ]}
  ]},
  {group:"TICARI & SATI\u015e",items:[
    {id:"project-parent",icon:"&#9635;",label:"Proje Y\u00f6netimi",children:[
      {id:"projects",label:"Projeler"},
      {id:"project-archive",label:"Proje Ar\u015fivi"}
    ]},
    {id:"stock-parent",icon:"&#9638;",label:"Stok / Sipari\u015f",children:[
      {id:"stock",label:"Stok Y\u00f6netimi"},
      {id:"loaners",label:"Emanet (Konsinye) Cihazlar"},
      {id:"stock-locations",label:"Depo ve Ara\u00e7 Stoklar\u0131"},
      {id:"movements",label:"Stok Hareketleri"},
      {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"},
      {id:"mobile-guide",label:"Mobil Teknik K\u0131lavuz"},
      {id:"pc-builder",label:"PC Builder"}
    ]},
    {id:"offer-parent",icon:"&#9670;",label:"Teklif Olu\u015ftur",children:[
      {id:"sales",label:"Teklif Olu\u015ftur"},
      {id:"offers",label:"T\u00fcm Teklifler & Ge\u00e7mi\u015f"},
      {id:"offer-reports",label:"Teklif Analiz Raporlar\u0131"}
    ]}
  ]},
  {group:"FINANS & MUHASEBE",items:[
    {id:"finance-parent",icon:"TRY",label:"Finansal Y\u00f6netim",children:[
      {id:"finance",label:"Finansal Dashboard"},
      {id:"income",label:"Gelir / Gider"},
      {id:"expense",label:"Giderler"},
      {id:"banks",label:"Banka Hesaplar\u0131"},
      {id:"loans",label:"Krediler & Taksitler"},
      {id:"checks",label:"\u00c7ek / Senet"},
      {id:"invoices",label:"Fatura Kes (E-Fatura)"}
    ]}
  ]},
  {group:"Y\u00d6NET\u0130M",items:[
    {id:"management-parent",icon:"&#9823;",label:"Personel",children:[{id:"personnel",label:"Personel"}]}
  ]},
  {group:"S\u0130STEM",items:[
    {id:"system-parent",icon:"&#9881;",label:"Sistem Yard\u0131mc\u0131lar\u0131",children:[
      {id:"knowledge",label:"Bilgi Bankas\u0131"},
      {id:"settings",label:"Sistem Ayarlar\u0131"},
      {id:"backup",label:"Yedekleme Merkezi"},
      {id:"support",label:"Destek Merkezi"},
      {id:"audit",label:"Sistem \u0130\u015flem Loglar\u0131"},
      {id:"manual",label:"Kullan\u0131m K\u0131lavuzu"},
      {id:"dialog-catalog",label:"Dialog Mod\u00fclleri"},
      {id:"control-center",label:"Y\u00f6netim Merkezi"}
    ]}
  ]}
];
ayecSectorMenuModels.otomotiv=[
  {group:"SERVIS OPERASYON",items:[
    {id:"service-parent",icon:"&#9881;",label:"Servis Y\u00f6netimi",children:[
      {id:"dashboard",label:"Genel Bak\u0131\u015f"},
      {id:"services",label:"Servis Panosu"},
      {id:"service-list",label:"Servis Listesi"},
      {id:"service-status",label:"Durum Paneli"},
      {id:"technician",label:"Teknisyen Paneli"},
      {id:"field-service",label:"Saha Haritas\u0131"},
      {id:"appointments",label:"Randevular"},
      {id:"vehicle-maintenance",label:"Ara\u00e7 Bak\u0131m Takibi"},
      {id:"assistant",label:"AI Asistan"}
    ]},
    {id:"service-settings-parent",icon:"&#9881;",label:"Servis Ayarlar\u0131",children:[
      {id:"product-groups",label:"\u00dcr\u00fcn Grubu Y\u00f6netimi"},
      {id:"brands",label:"Marka Adlar\u0131 Y\u00f6netimi"},
      {id:"report-templates",label:"Rapor C\u00fcmle Kal\u0131plar\u0131"},
      {id:"service-definitions",label:"\u0130\u015f\u00e7ilik & Fiyat Y\u00f6netimi"}
    ]},
    {id:"customer-parent",icon:"&#9786;",label:"M\u00fc\u015fteri Hub",children:[
      {id:"partners",label:"\u00c7al\u0131\u015fma Ortaklar\u0131"},
      {id:"customers",label:"M\u00fc\u015fteri Listesi"},
      {id:"contracts",label:"S\u00f6zle\u015fmeler"},
      {id:"reminders",label:"Hat\u0131rlat\u0131c\u0131lar"},
      {id:"announcements",label:"Duyurular"}
    ]}
  ]},
  {group:"TICARI & SATI\u015e",items:[
    {id:"project-parent",icon:"&#9635;",label:"Proje Y\u00f6netimi",children:[
      {id:"projects",label:"Projeler"},
      {id:"project-archive",label:"Proje Ar\u015fivi"}
    ]},
    {id:"automotive-stock-parent",icon:"&#9638;",label:"Stok / Sipari\u015f",children:[
      {id:"automotive-stock",label:"Par\u00e7a Stok Y\u00f6netimi"},
      {id:"movements",label:"Stok Hareketleri"},
      {id:"import",label:"Ak\u0131ll\u0131 \u0130\u00e7e Aktarma"},
      {id:"loaners",label:"Emanet (Konsinye) Cihazlar"}
    ]},
    {id:"offer-parent",icon:"&#9670;",label:"Teklif Olu\u015ftur",children:[
      {id:"sales",label:"Teklif Olu\u015ftur"},
      {id:"offers",label:"T\u00fcm Teklifler & Ge\u00e7mi\u015f"},
      {id:"offer-reports",label:"Teklif Analiz Raporlar\u0131"}
    ]}
  ]},
  {group:"FINANS & MUHASEBE",items:[
    {id:"finance-parent",icon:"TRY",label:"Finansal Y\u00f6netim",children:[
      {id:"finance",label:"Finansal Dashboard"},
      {id:"income",label:"Gelir / Gider"},
      {id:"expense",label:"Giderler"},
      {id:"banks",label:"Banka Hesaplar\u0131"},
      {id:"loans",label:"Krediler & Taksitler"},
      {id:"checks",label:"\u00c7ek / Senet"},
      {id:"invoices",label:"Fatura Kes (E-Fatura)"}
    ]}
  ]},
  {group:"Y\u00d6NET\u0130M",items:[
    {id:"management-parent",icon:"&#9823;",label:"Personel",children:[{id:"personnel",label:"Personel"}]}
  ]},
  {group:"S\u0130STEM",items:[
    {id:"system-parent",icon:"&#9881;",label:"Sistem Yard\u0131mc\u0131lar\u0131",children:[
      {id:"knowledge",label:"Bilgi Bankas\u0131"},
      {id:"settings",label:"Sistem Ayarlar\u0131"},
      {id:"backup",label:"Yedekleme Merkezi"},
      {id:"support",label:"Destek Merkezi"},
      {id:"audit",label:"Sistem \u0130\u015flem Loglar\u0131"},
      {id:"manual",label:"Kullan\u0131m K\u0131lavuzu"},
      {id:"dialog-catalog",label:"Dialog Mod\u00fclleri"},
      {id:"control-center",label:"Y\u00f6netim Merkezi"}
    ]}
  ]}
];
modernMenu.splice(0,modernMenu.length,...ayecSectorMenuModels.teknik_servis.map(group=>({...group,items:group.items.map(item=>({...item,children:item.children?.map(child=>({...child}))}))})));
menu.splice(0,menu.length,...modernMenu);
const ayecDesktopPageIds={
  dashboard:40,services:41,"service-list":42,"service-status":43,technician:62,"field-service":61,
  appointments:30,logistics:65,"job-reports":201,
  "vehicle-maintenance":210,"service-definitions":140,
  "product-groups":146,brands:145,"report-templates":147,
  customers:21,partners:26,contracts:25,reminders:90,announcements:120,
  stock:50,"stock-locations":51,"automotive-stock":60,loaners:66,"mobile-guide":250,
  "pc-builder":300,sales:150,offers:313,"offer-reports":314,
  finance:100,income:101,expense:101,banks:105,
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
  const collect=item=>[item,...(item.children||[]).flatMap(collect)];
  return ayecSectorMenu(sector).flatMap(group=>group.items.flatMap(collect));
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
  const path=ayecMenuPath(pageId,sector);
  return path.length>1?path[path.length-2].id:"";
}

function ayecMenuPath(pageId,sector=currentSector){
  function find(items,path=[]){
    for(const item of items){
      const next=[...path,item];
      if(item.id===pageId)return next;
      const found=find(item.children||[],next);
      if(found.length)return found;
    }
    return[];
  }
  return find(ayecSectorMenu(sector).flatMap(group=>group.items));
}

firstVisiblePage=function(sector=currentSector){
  function first(items){
    for(const item of items){
      if(!menuVisible(item,sector))continue;
      if(item.children){
        const child=first(item.children);
        if(child)return child;
      }else{
        return item.id;
      }
    }
    return"";
  }
  return first(ayecSectorMenu(sector).flatMap(group=>group.items))||"dashboard";
};

renderNav=function(){
  const sector=currentSector==="otomotiv"?"otomotiv":"teknik_servis";
  const groups=ayecSectorMenu(sector);
  const rememberedParent=ayecOpenParent(sector);
  const openIds=new Set([
    ...ayecMenuPath(page,sector).slice(0,-1),
    ...ayecMenuPath(rememberedParent,sector)
  ].map(item=>item.id));
  function visible(item){
    if(!menuVisible(item,sector))return null;
    if(!item.children)return item;
    const children=item.children.map(visible).filter(Boolean);
    return children.length?{...item,children}:null;
  }
  function draw(item){
    const open=openIds.has(item.id);
    const submenuId=`nav-${sector}-${item.id}`;
    if(item.children){
      return `<button type="button" class="nav-button nav-parent ${open?"open":""}" data-parent="${submenuId}" aria-controls="${submenuId}" aria-expanded="${open}"><span class="nav-icon">${item.icon||"&#8226;"}</span><span class="nav-label">${esc(labelFor(item,sector))}</span></button><div class="submenu ${open?"open":""}" id="${submenuId}" ${open?"":"hidden"}>${item.children.map(draw).join("")}</div>`;
    }
    return `<button type="button" class="nav-button ${item.id===page?"active":""}" data-page="${item.id}"><span class="nav-icon">${item.icon||"&#8226;"}</span><span class="nav-label">${esc(labelFor(item,sector))}</span><span class="nav-active-dot" aria-hidden="true">\u25cf</span></button>`;
  }
  $("#nav").innerHTML=groups.map(group=>{
    const items=group.items.map(visible).filter(Boolean);
    if(!items.length)return"";
    return `<div class="nav-group-title">${esc(group.group)}</div>${items.map(draw).join("")}`;
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
  function draw(item,child=false){
    const row=ayecEditorRow(item,sector,child);
    if(!item.children)return row;
    return `<div class="sector-menu-parent">${row}<div class="sector-menu-children">${item.children.map(entry=>draw(entry,true)).join("")}</div></div>`;
  }
  const groups=ayecSectorMenu(sector).map((group,index)=>
    `<details class="sector-menu-group" ${index<2?"open":""}><summary><span>${esc(group.group)}</span><small>${group.items.length} men\u00fc grubu</small></summary><div class="sector-menu-group-body">${group.items.map(item=>draw(item)).join("")}</div></details>`
  ).join("");
  return `<section class="sector-menu-panel ${sector===currentSector?"active":""}" data-editor-panel="${sector}"><header><div><span class="sector-menu-badge">${sector==="otomotiv"?"OT":"TS"}</span><div><h3>${title}</h3><p>${description}</p></div></div><span class="badge">${sector===currentSector?"Aktif sekt\u00f6r":"Di\u011fer sekt\u00f6r"}</span></header><div class="sector-menu-groups">${groups}</div></section>`;
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
    ["module_personnel_active","Personel Mod\u00fcl\u00fc","Personel ve ekip y\u00f6netimi"],
    ["module_asistan_active","Sesli Asistan ve K\u0131sayollar","Sesli asistan ve klavye k\u0131sayollar\u0131"]
  ];
  const featureFields=[
    ["feature_wizard_upload_active","Sihirbazda dosya y\u00fckleme","Dosyalar\u0131 sihirbaza ekleme"],
    ["feature_iban_verify_active","Otomatik IBAN do\u011frulama","Banka bilgilerini kaydederken kontrol"],
    ["feature_voice_alerts_active","Sesli uyar\u0131lar","Uygulama i\u00e7i sesli bildirimler"],
    ["feature_scheduled_alerts_active","Zaman ayarl\u0131 duyurular","Planl\u0131 bildirim ve duyurular"],
    ["feature_usage_guides_active","Kullan\u0131m k\u0131lavuzu sekmeleri","Yard\u0131m ve k\u0131lavuz sayfalar\u0131"],
    ["feature_right_click_active","Sa\u011f t\u0131k men\u00fcleri","Sat\u0131r i\u015flem men\u00fcleri"],
    ["feature_double_click_active","\u00c7ift t\u0131klama","Kayd\u0131 ayr\u0131nt\u0131da a\u00e7ma"]
  ];
  const deviceProfiles=[
    ["bilgisayar","Bilgisayar"],
    ["cep_telefonu","Cep telefonu"],
    ["akilli_ev","Ak\u0131ll\u0131 ev"]
  ];
  const selectedProfiles=String(desktopInternalSettings.device_business_profiles||"bilgisayar").split(",");
  const toggle=([key,label,description])=>{
    const value=desktopInternalSettings[key]??"1";
    const checked=String(value)==="1"||String(value)==="true";
    const moduleClass=key.startsWith("module_")?" identity-module-switch":"";
    return `<label class="identity-toggle"><span><strong>${label}</strong><small>${description}</small></span><input class="switch exact-setting${moduleClass}" data-setting-key="${key}" data-setting-scope="internal_settings" type="checkbox" ${checked?"checked":""}></label>`;
  };
  const selector=currentAuthUser?.is_admin?
    `<div class="sector-identity-action"><select class="control" id="companySectorSelect"><option value="teknik_servis" ${sector==="teknik_servis"?"selected":""}>Teknik Servis</option><option value="otomotiv" ${sector==="otomotiv"?"selected":""}>Otomotiv Servis</option></select><button class="primary" type="button" data-action="save-company-sector">Sekt\u00f6r\u00fc Uygula</button></div>`:
    `<span class="badge">${sectorLabel}</span>`;
  const profiles=selectedProfiles;
  return `<div class="identity-settings"><section class="sector-identity-card"><div><span class="identity-step">1</span><div><h3>Sekt\u00f6rel Kimlik</h3><p>Aktif sekt\u00f6r men\u00fcleri, formlar\u0131 ve stok ekran\u0131n\u0131 belirler. Veri silinmez.</p></div></div>${selector}</section><section class="identity-section"><header><span class="identity-step">2</span><div><h3>Mod\u00fcl Paketleri</h3><p>\u0130\u015fletmenin kullanaca\u011f\u0131 ana mod\u00fclleri y\u00f6netin.</p></div></header><div class="identity-toggle-grid">${moduleFields.map(toggle).join("")}</div></section><section class="identity-section"><header><span class="identity-step">3</span><div><h3>\u00d6zellik Bazl\u0131 Kontroller</h3><p>Uygulama ve kullan\u0131m se\u00e7enekleri.</p></div></header><div class="identity-toggle-grid">${featureFields.map(toggle).join("")}</div></section><section class="identity-section"><header><span class="identity-step">4</span><div><h3>Cihaz katalog i\u015f kollar\u0131</h3><p>Yeni servis kayd\u0131 ve cihaz ekleme ekranlar\u0131n\u0131 s\u00fcz.</p></div></header><div class="identity-profile-grid">${deviceProfiles.map(([key,label])=>`<label><input type="checkbox" data-device-profile="${key}" ${profiles.includes(key)?"checked":""}><span>${label}</span></label>`).join("")}</div><input type="hidden" class="exact-setting" data-setting-key="device_business_profiles" data-setting-scope="internal_settings" value="${esc(profiles.join(","))}"></section></div>`;
};

document.addEventListener("click",event=>{
  if(!event.target.closest('[data-action="save-settings"]')||settingsSection!=="identity")return;
  const field=$('[data-setting-key="device_business_profiles"]');
  if(!field)return;
  const selected=$$('[data-device-profile]:checked').map(input=>input.dataset.deviceProfile);
  field.value=(selected.length?selected:["bilgisayar"]).join(",");
},true);

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
  let html=ayecRenderStockBeforeProfit().replace(
    '<div class="metric-grid">',
    `<div class="metric-grid">${ayecPotentialProfitCard()}`
  );
  const fullTable=stockTable(db.stock);
  ayecStockCurrentPage=Math.max(0,Math.min(ayecStockCurrentPage,Math.max(0,Math.ceil(db.stock.length/ayecStockPageSize)-1)));
  const stockStart=ayecStockCurrentPage*ayecStockPageSize;
  html=html.replace(fullTable,stockTable(db.stock.slice(stockStart,stockStart+ayecStockPageSize),stockStart));
  const sectionEnd=html.lastIndexOf("</section>");
  if(sectionEnd>=0) html=html.slice(0,sectionEnd)+ayecStockPager(db.stock.length)+"</section>"+ayecStockSummaryCards();
  html=html.replace("<h2>Stok & Envanter Takibi</h2>", `<h2>Stok & Envanter Takibi <span class="stock-active-count">${db.stock.length} Kalem Aktif</span></h2>`);
  return html.replace(/<button class="primary" data-action="add-product">[^<]*<\/button>/, '<button class="secondary" data-stock-refresh>Envanteri Yenile</button><button class="primary" data-action="add-product">+ Yeni \u00dcr\u00fcn Ekle</button>');
};

const ayecStockPageSize=50;
let ayecStockCurrentPage=0;
function ayecStockPager(total){
  const pages=Math.max(1,Math.ceil(total/ayecStockPageSize));
  return `<nav class="stock-reference-pager" aria-label="Stok sayfalari"><button type="button" data-stock-page="-1" ${ayecStockCurrentPage<=0?"disabled":""}>&larr; \u00d6nceki</button><strong>Sayfa ${ayecStockCurrentPage+1} / ${pages}</strong><button type="button" data-stock-page="1" ${ayecStockCurrentPage>=pages-1?"disabled":""}>Sonraki &rarr;</button></nav>`;
}
function ayecStockSummaryCards(){
  return '<div class="stock-reference-summary"><article><strong>Son Fiziksel Depo Say\u0131m\u0131</strong><small>Say\u0131m detaylar\u0131n\u0131 a\u00e7</small></article><article><strong>\u015eantiye / Servis Konsinye\u00a0\u00c7\u0131k\u0131\u015f\u0131</strong><small>Konsinye i\u015flemlerini a\u00e7</small></article><article><strong>Muhasebe Entegrasyonu</strong><small>Entegrasyon durumunu a\u00e7</small></article></div>';
}
function ayecRenderStockRows(){
  const search=$("#stockSearch"),category=$("#stockCategory"),level=$("#stockLevel"),host=$("#stockTable");
  if(!host)return;
  const query=String(search?.value||"").toLocaleLowerCase("tr-TR");
  const categoryValue=category?.value||"T\u00fcm Kategoriler",levelValue=level?.value||"T\u00fcm Seviyeler";
  const rows=db.stock.filter(item=>[item.code,item.name,item.barcode].join(" ").toLocaleLowerCase("tr-TR").includes(query)&&(categoryValue==="T\u00fcm Kategoriler"||item.category===categoryValue)&&(levelValue==="T\u00fcm Seviyeler"||(levelValue==="Kritik Stok"?item.qty<=item.min:item.qty>0)));
  const pages=Math.max(1,Math.ceil(rows.length/ayecStockPageSize));
  ayecStockCurrentPage=Math.max(0,Math.min(ayecStockCurrentPage,pages-1));
  const start=ayecStockCurrentPage*ayecStockPageSize;
  host.innerHTML=stockTable(rows.slice(start,start+ayecStockPageSize),start);
  const pager=document.querySelector(".stock-reference-pager");
  if(pager)pager.outerHTML=ayecStockPager(rows.length);
}
document.addEventListener("click",event=>{
  const pageButton=event.target.closest("[data-stock-page]");
  if(pageButton){ayecStockCurrentPage=Math.max(0,ayecStockCurrentPage+Number(pageButton.dataset.stockPage));ayecRenderStockRows();return;}
  if(event.target.closest("[data-stock-refresh]")){hydrateDesktop().then(()=>render()).catch(error=>toast(error.message,"error"));}
});

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

const ayecRenderBeforeOffersReference=render;
render=function(){
  if(page!=="offers"&&page!=="contracts")return ayecRenderBeforeOffersReference();
  document.body.dataset.page=page;
  const meta=genericModules[page];
  $("#content").innerHTML=page==="offers"?renderOffersReference():renderContractsReference();
  bindPage();
  const search=$("#genericSearch");
  if(search)search.oninput=()=>loadGenericModule(meta,search.value);
  $$('[data-generic-refresh]').forEach(button=>button.onclick=()=>loadGenericModule(meta,search?.value||""));
  const addButton=$('[data-generic-add]');
  if(addButton)addButton.onclick=async()=>{const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=1`);openGenericDialog(meta,{},data.columns)};
  if(page==="offers")initOfferReferenceActions();
  loadGenericModule(meta);
};

function initOfferReferenceActions(){
  const actions=$(".page-head .actions");
  if(actions){
    actions.innerHTML="";
    const quick=document.createElement("button");quick.className="secondary";quick.textContent="H\u0131zl\u0131 Teklif Sepeti";quick.onclick=()=>navigate("sales");actions.append(quick);
    const exportButton=document.createElement("button");exportButton.className="secondary";exportButton.textContent="Excel \u00c7\u0131kt\u0131";exportButton.onclick=()=>{
      const rows=window.currentGenericData?.rows||[];
      if(!rows.length){toast("D\u0131\u015fa aktar\u0131lacak teklif bulunamad\u0131","warning");return}
      const fields=["offer_no","created_at","customer_name","company_name","currency_code","total","total_try","status"];
      const data=rows.map(row=>Object.fromEntries(fields.filter(key=>Object.hasOwn(row,key)).map(key=>[key,row[key]])));
      download(`teklifler-${today()}.csv`,csv(data));
    };actions.append(exportButton);
    const reports=document.createElement("button");reports.className="secondary";reports.textContent="Raporlar";reports.onclick=()=>navigate("offer-reports");actions.append(reports);
    const create=document.createElement("button");create.className="primary";create.textContent="+ Yeni Teklif Olu\u015ftur";create.onclick=()=>navigate("sales");actions.append(create);
  }
  const facts=$(".offers-reference-facts");
  if(facts&&!facts.querySelector("[data-offer-preview='customer']")){
    facts.insertAdjacentHTML("afterbegin","<div><small>M\u00fc\u015fteri</small><strong data-offer-preview=\"customer\">-</strong></div>");
  }
  const side=$(".offers-reference-side");
  if(side&&!side.querySelector(".offers-reference-selected-summary")){
    side.insertAdjacentHTML("beforeend",'<div class="offers-reference-selected-summary"><div><small>Ara toplam</small><strong data-offer-preview="subtotal">-</strong></div><div><small>\u0130ndirim</small><strong data-offer-preview="discount">-</strong></div><div><small>KDV</small><strong data-offer-preview="tax">-</strong></div><div><small>Genel toplam</small><strong data-offer-preview="total">-</strong></div></div>');
  }
}

function updateOfferReferencePreview(row){
  if(!row)return;
  const customer=[row.customer_name,row.company_name].filter(Boolean).join(" | ")||"-";
  const created=String(row.created_at||row.date||"").slice(0,10);
  const date=created?new Date(created).toLocaleDateString("tr-TR"):"-";
  const currency=String(row.currency_code||"TRY").toUpperCase();
  const amount=(value)=>money(Number(value||0),currency);
  const values={customer,date,currency,items:row.items||row.offer_no||"-",subtotal:amount(row.subtotal??row.total),discount:amount(row.discount),tax:amount(row.tax_amount??row.tax_total),total:amount(row.total)};
  Object.entries(values).forEach(([key,value])=>{
    const target=$(`[data-offer-preview="${key}"]`);if(target)target.textContent=value;
  });
  const volume=$(".offers-reference-volume strong");if(volume)volume.textContent=values.total;
  const rows=$$("#genericHost [data-generic-row]");
  rows.forEach((item,index)=>{const selected=String(index)===String(row.__previewIndex);item.classList.toggle("is-selected",selected);item.setAttribute("aria-selected",selected?"true":"false")});
}

const ayecLoadGenericBeforeOfferPreview=loadGenericModule;
loadGenericModule=async function(meta,q=""){
  await ayecLoadGenericBeforeOfferPreview(meta,q);
  if(page!=="offers"||meta!==genericModules.offers)return;
  const data=window.currentGenericData;
  if(!data?.rows?.length)return;
  $$("#genericHost [data-generic-row]").forEach((row,index)=>{
    const select=()=>updateOfferReferencePreview({...data.rows[index],__previewIndex:index});
    row.addEventListener("click",select);
    row.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();select()}});
  });
  updateOfferReferencePreview({...data.rows[0],__previewIndex:0});
};

function renderBrandsReference(){
  return `${pageHead("Cihaz Bilgisi & Markalar","Servis formu ve Teknisyen Panelinde kullan\u0131lacak cihaz t\u00fcr\u00fc ve marka listesini buradan y\u00f6netin.",'<button class="secondary" data-brand-refresh data-generic-refresh><span aria-hidden="true">\u21bb</span> Web Katalo\u011funu G\u00fcncelle</button><div class="brands-export-group"><button type="button" data-brand-export="excel">Excel</button><button type="button" data-brand-export="pdf">PDF</button><button type="button" data-brand-export="print">Yazd\u0131r</button></div><button class="primary" data-generic-add>\u2295 Yeni Marka &amp; Cihaz Ekle</button>')}<section class="card brands-reference-card"><div class="brands-reference-toolbar"><input class="control search" id="genericSearch" placeholder="Cihaz t\u00fcr\u00fc veya marka ad\u0131na g\u00f6re filtrele... (\u00d6rn: Apple, Tapo, Laptop)" aria-label="Marka ara"><label for="brandGroupFilter">\u00dcr\u00fcn Grubu:</label><select class="control" id="brandGroupFilter"><option value="">T\u00fcm \u00dcr\u00fcn Gruplar\u0131</option></select><label for="brandStatusFilter">Durum:</label><select class="control" id="brandStatusFilter"><option value="active">Yaln\u0131zca Aktif</option><option value="inactive">Pasif</option><option value="all">T\u00fcm Durumlar</option></select><button class="secondary" type="button" data-brand-clear aria-label="Filtreleri temizle">\u00d7</button></div><div id="genericHost">${empty("Markalar y\u00fckleniyor","Masa\u00fcst\u00fc veritaban\u0131 okunuyor.")}</div></section><div class="brands-reference-footer"><span id="genericCount">Toplam kay\u0131tlar y\u00fckleniyor</span><label>Sayfa Ba\u015f\u0131na: <select id="brandPageSize" class="control"><option>10</option><option>20</option><option>50</option></select></label><nav id="brandPagination" aria-label="Marka sayfalar\u0131"></nav></div>`;
}

function brandServiceLabel(row){
  const count=row.__brand_service_count??row.related_service_count??row.service_count;
  if(count===undefined||count===null||count==="")return "-";
  const type=String(row.device_type||"").toLocaleLowerCase("tr-TR");
  const unit=type.includes("ayd\u0131nlatma")||type.includes("ev merkezi")?"Cihaz":"Fi\u015f";
  return `${count} ${unit}`;
}

const ayecGenericShellBeforeBrands=genericShell;
genericShell=function(meta){
  return meta?.table==="device_brands"?renderBrandsReference():ayecGenericShellBeforeBrands(meta);
};

async function loadBrandsReference(meta,q=""){
  const host=$("#genericHost");
  if(!host)return;
  try{
    const data=await apiFetch(`/api/desktop/table/${meta.table}?limit=500&q=${encodeURIComponent(q)}`);
    window.currentGenericData=data;
    window.currentGenericMeta=meta;
    const groups=[...new Set(data.rows.map(row=>String(row.device_type||"").trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"tr"));
    const groupFilter=$("#brandGroupFilter"),selectedGroup=groupFilter.value;
    groupFilter.innerHTML='<option value="">T\u00fcm \u00dcr\u00fcn Gruplar\u0131 ('+groups.length+')</option>'+groups.map(group=>`<option value="${esc(group)}">${esc(group)}</option>`).join("");
    groupFilter.value=groups.includes(selectedGroup)?selectedGroup:"";
    const status=$("#brandStatusFilter").value;
    const query=String(q||"").trim().toLocaleLowerCase("tr-TR");
    const filtered=data.rows.filter(row=>{
      const matchGroup=!groupFilter.value||String(row.device_type||"")===groupFilter.value;
      const active=String(row.is_active??1)==="1"||row.is_active===true;
      const matchStatus=status==="all"||(status==="active"?active:!active);
      const matchQuery=!query||`${row.device_type||""} ${row.brand||""}`.toLocaleLowerCase("tr-TR").includes(query);
      return matchGroup&&matchStatus&&matchQuery;
    });
    const pageSize=Number($("#brandPageSize")?.value||10);
    const maxPage=Math.max(0,Math.ceil(filtered.length/pageSize)-1);
    window.brandsReferencePage=Math.min(window.brandsReferencePage||0,maxPage);
    const offset=window.brandsReferencePage*pageSize;
    const visible=filtered.slice(offset,offset+pageSize);
    window.brandsVisibleRows=visible;
    window.brandsServiceCounts=window.brandsServiceCounts||new Map();
    const serviceCounts=await Promise.all(visible.map(async row=>{
      const key=`${row.device_type||""}\u001f${row.brand||""}`;
      if(window.brandsServiceCounts.has(key))return window.brandsServiceCounts.get(key);
      try{
        const services=await apiFetch(`/api/desktop/table/devices?limit=500&q=${encodeURIComponent(row.brand||"")}`);
        const count=services.rows.filter(item=>String(item.device_type||"")===String(row.device_type||"")&&String(item.device_brand||"")===String(row.brand||"")).length;
        window.brandsServiceCounts.set(key,count);
        return count;
      }catch(_error){return Number(row.related_service_count??row.service_count)||0}
    }));
    visible.forEach((row,index)=>row.__brand_service_count=serviceCounts[index]);
    const headers=["Cihaz / \u00dcr\u00fcn Grubu","Marka Ad\u0131","\u0130li\u015fkili Servis Kay\u0131tlar\u0131","Durum"];
    host.innerHTML=visible.length?`<div class="table-wrap brands-reference-table"><table><thead><tr><th><input type="checkbox" data-brand-select-all aria-label="G\u00f6r\u00fcnenleri se\u00e7"></th>${headers.map(label=>`<th>${label}</th>`).join("")}<th>\u0130\u015flemler</th></tr></thead><tbody>${visible.map((row,index)=>`<tr data-generic-row="${data.rows.indexOf(row)}"><td><input type="checkbox" data-brand-select aria-label="${esc(row.brand||"")} se\u00e7"></td><td><span class="brands-group-icon" aria-hidden="true">\u25c8</span><strong>${esc(row.device_type||"")}</strong></td><td><span class="brands-initials">${esc(String(row.brand||"").slice(0,2).toUpperCase())}</span>${esc(row.brand||"")}</td><td class="brands-count">${esc(brandServiceLabel(row))}</td><td><span class="brands-status ${String(row.is_active??1)==="1"?"active":"inactive"}">${String(row.is_active??1)==="1"?"Aktif":"Pasif"}</span></td><td><button class="mini generic-edit" data-index="${data.rows.indexOf(row)}">D\u00fczenle</button> <button class="mini generic-delete" data-index="${data.rows.indexOf(row)}">Sil</button></td></tr>`).join("")}</tbody></table></div>`:empty("Kay\u0131t bulunamad\u0131","Filtrelere uygun marka yok.");
    $("#genericCount").textContent=`Toplam ${filtered.length} kay\u0131ttan ${filtered.length?offset+1:0}-${Math.min(offset+visible.length,filtered.length)} aras\u0131 listeleniyor.`;
    const pages=Array.from({length:maxPage+1},(_,index)=>index);
    $("#brandPagination").innerHTML=`<button type="button" data-brand-page="${Math.max(0,window.brandsReferencePage-1)}" ${window.brandsReferencePage===0?"disabled":""}>\u00d6nceki</button>${pages.slice(0,3).map(value=>`<button type="button" data-brand-page="${value}" class="${value===window.brandsReferencePage?"active":""}">${value+1}</button>`).join("")}${maxPage>3?'<span>\u2026</span>':""}${maxPage>2?`<button type="button" data-brand-page="${maxPage}" class="${maxPage===window.brandsReferencePage?"active":""}">${maxPage+1}</button>`:""}<button type="button" data-brand-page="${Math.min(maxPage,window.brandsReferencePage+1)}" ${window.brandsReferencePage===maxPage?"disabled":""}>Sonraki</button>`;
    $$(".generic-edit").forEach(button=>button.onclick=()=>openGenericDialog(meta,data.rows[+button.dataset.index],data.columns));
    $$(".generic-delete").forEach(button=>button.onclick=()=>deleteGenericRow(meta,data.rows[+button.dataset.index]));
    $$("[data-brand-page]").forEach(button=>button.onclick=()=>{window.brandsReferencePage=Number(button.dataset.brandPage);loadBrandsReference(meta,q)});
    $("[data-brand-select-all]")?.addEventListener("change",event=>$$("[data-brand-select]").forEach(box=>box.checked=event.target.checked));
  }catch(error){host.innerHTML=empty("Mod\u00fcl y\u00fcklenemedi",error.message)}
}

const ayecLoadGenericBeforeBrands=loadGenericModule;
loadGenericModule=async function(meta,q=""){
  if(meta?.table==="device_brands")return loadBrandsReference(meta,q);
  return ayecLoadGenericBeforeBrands(meta,q);
};

document.addEventListener("click",event=>{
  if(event.target.closest("[data-brand-clear]")){$("#genericSearch").value="";$("#brandGroupFilter").value="";$("#brandStatusFilter").value="active";window.brandsReferencePage=0;loadGenericModule(genericModules.brands);return}
  const exportButton=event.target.closest("[data-brand-export]");
  if(!exportButton)return;
  if(exportButton.dataset.brandExport==="print"){window.print();return}
  if(exportButton.dataset.brandExport==="pdf"){window.print();return}
  const rows=window.brandsVisibleRows||[];
  download(`markalar-${today()}.csv`,csv(rows.map(row=>({"Cihaz T\u00fcr\u00fc":row.device_type,"Marka":row.brand,"Durum":String(row.is_active??1)==="1"?"Aktif":"Pasif"}))));
});

document.addEventListener("input",event=>{
  if(event.target.id==="genericSearch")window.brandsReferencePage=0;
},true);
document.addEventListener("change",event=>{
  if(["brandGroupFilter","brandStatusFilter","brandPageSize"].includes(event.target.id)){window.brandsReferencePage=0;loadGenericModule(genericModules.brands,$("#genericSearch")?.value||"")}
});

function renderChecksReference(){
  const title="<span class='checks-title'>\u00c7ek &amp; Senet Portf\u00f6y Y\u00f6netimi <span class='checks-reference-badge'>Canl\u0131 Portf\u00f6y Mod\u00fcl\u00fc</span></span>";
  return `${pageHead(title,"Al\u0131nan ve verilen vadeli k\u0131ymetli evraklar\u0131n takas, ciro, tahsilat ve reeskont operasyonlar\u0131",'<button class="secondary" data-check-bulk>Toplu Banka Takas\u0131na Ver</button><button class="secondary" data-check-export>Excel \u00c7\u0131kt\u0131</button><button class="primary" data-check-add>+ Yeni \u00c7ek / Senet Giri\u015fi</button>')}<div class="metric-grid checks-reference-metrics" id="checksMetrics"></div><section class="card checks-reference-card"><div class="checks-reference-top"><div class="checks-reference-tabs" id="checksTabs"></div><div class="checks-reference-currencies">${[["USD","USD ($)"],["TRY","TRY (\u20ba)"],["EUR","EUR (\u20ac)"]].map(([code,label])=>`<button type="button" data-check-currency="${code}">${label}</button>`).join("")}</div></div><div class="checks-reference-controls"><input id="genericSearch" class="control search" placeholder="Ke\u015fideci, bor\u00e7lu, banka veya evrak no ara..."><select id="checkStatusFilter" class="control"><option value="">Portf\u00f6yde (Kasada)</option><option value="Tahsil Edildi">Tahsil Edildi</option><option value="Ciro Edildi">Ciro Edildi</option><option value="\u00d6dendi">\u00d6dendi</option><option value="Kar\u015f\u0131l\u0131ks\u0131z">Kar\u015f\u0131l\u0131ks\u0131z</option><option value="\u0130ade">\u0130ade</option><option value="all">T\u00fcm\u00fc</option></select><select id="checkBankFilter" class="control"><option value="">Banka: T\u00fcm Bankalar</option></select><input id="checkDateStart" class="control" type="date"><input id="checkDateEnd" class="control" type="date"><button type="button" class="secondary" data-check-clear>Filtreyi Temizle</button></div></section><section class="card checks-reference-table-card"><div id="genericHost"></div></section><div class="checks-reference-footer"><span id="genericCount"></span><label>Sayfa Ba\u015f\u0131na <select id="checkPageSize" class="control"><option>10</option><option>20</option><option>50</option></select></label><nav id="checkPagination" aria-label="\u00c7ek ve senet sayfalar\u0131"></nav></div>`;
}

function checkMoney(value,currency){
  const code=String(currency||"TRY").toUpperCase(),rate=code==="TRY"?1:(rateForCode(code)||1);
  return new Intl.NumberFormat("en-US",{style:"currency",currency:code,minimumFractionDigits:2}).format(Number(value||0)/rate);
}

async function loadChecksReference(meta,q=""){
  const host=$("#genericHost");if(!host)return;
  try{
    const result=await apiFetch(`/api/desktop/table/${meta.table}?limit=500&q=${encodeURIComponent(q)}`);
    window.currentGenericData=result;window.currentGenericMeta=meta;
    const all=result.rows||[],statusFilter=$("#checkStatusFilter").value,bankFilter=$("#checkBankFilter").value;
    const start=$("#checkDateStart").value,end=$("#checkDateEnd").value;
    const tabs={all:all.length,checks:all.filter(row=>row.type==="\u00c7ek"&&String(row.direction||"").startsWith("Giri\u015f")).length,notes:all.filter(row=>row.type==="Senet"&&String(row.direction||"").startsWith("Giri\u015f")).length,own:all.filter(row=>String(row.direction||"").startsWith("\u00c7\u0131k\u0131\u015f")).length,endorsed:all.filter(row=>row.status==="Ciro Edildi").length};
    const tabDefs=[["all","T\u00fcm Evraklar"],["checks","Al\u0131nan \u00c7ekler"],["notes","Al\u0131nan Senetler"],["own","Kendi \u00c7eklerimiz"],["endorsed","Tahsile Verilenler (Takas)"]];
    const activeTab=window.checksReferenceTab||"all";
    $("#checksTabs").innerHTML=tabDefs.map(([key,label])=>`<button type="button" data-check-tab="${key}" class="${activeTab===key?"active":""}">${label}${key==="endorsed"?"":` (${tabs[key]})`}</button>`).join("");
    const currencies=$$("[data-check-currency]");currencies.forEach(button=>button.classList.toggle("active",button.dataset.checkCurrency===(window.checksReferenceCurrency||"USD")));
    const banks=[...new Set(all.map(row=>String(row.bank_name||"").trim()).filter(Boolean))].sort((a,b)=>a.localeCompare(b,"tr"));
    const priorBank=bankFilter;$("#checkBankFilter").innerHTML='<option value="">Banka: T\u00fcm Bankalar</option>'+banks.map(bank=>`<option value="${esc(bank)}">${esc(bank)}</option>`).join("");$("#checkBankFilter").value=banks.includes(priorBank)?priorBank:"";
    const rows=all.filter(row=>{
      const incoming=String(row.direction||"").startsWith("Giri\u015f"),outgoing=String(row.direction||"").startsWith("\u00c7\u0131k\u0131\u015f");
      if(activeTab==="checks"&&!(row.type==="\u00c7ek"&&incoming))return false;
      if(activeTab==="notes"&&!(row.type==="Senet"&&incoming))return false;
      if(activeTab==="own"&&!outgoing)return false;
      if(activeTab==="endorsed"&&row.status!=="Ciro Edildi")return false;
      if(statusFilter&&statusFilter!=="all"&&row.status!==statusFilter)return false;
      if(bankFilter&&row.bank_name!==bankFilter)return false;
      const due=String(row.due_date||"").slice(0,10);if(start&&due<start)return false;if(end&&due>end)return false;
      return true;
    });
    const incoming=all.filter(row=>String(row.direction||"").startsWith("Giri\u015f")),own=all.filter(row=>String(row.direction||"").startsWith("\u00c7\u0131k\u0131\u015f"));
    const month=new Date().toISOString().slice(0,7),dueRows=all.filter(row=>String(row.due_date||"").startsWith(month));
    const portfolio=all.filter(row=>row.status==="Portf\u00f6yde").reduce((sum,row)=>sum+Number(row.amount||0),0);
    const due=dueRows.reduce((sum,row)=>sum+Number(row.amount||0),0),settled=all.filter(row=>row.status==="Ciro Edildi").reduce((sum,row)=>sum+Number(row.amount||0),0);
    const currency=window.checksReferenceCurrency||"USD",rate=rateForCode(currency)||1,coverage=incoming.reduce((sum,row)=>sum+Number(row.amount||0),0)/Math.max(1,all.reduce((sum,row)=>sum+Number(row.amount||0),0))*100;
    $("#checksMetrics").innerHTML=`<article class="checks-metric"><span>Portf\u00f6ydeki Toplam Tutar</span><strong>${checkMoney(portfolio,currency)}</strong><small>TL Kar\u015f\u0131l\u0131\u011f\u0131: ${money(portfolio,"TRY")}</small></article><article class="checks-metric warning"><span>Bu Ay Vadesi Gelenler</span><strong>${checkMoney(due,currency)}</strong><small>Toplam: ${dueRows.length} Evrak</small></article><article class="checks-metric cyan"><span>Al\u0131nan vs Verilen</span><strong>${incoming.length} Al\u0131nan / ${own.length} Kendi \u00c7ekimiz</strong><small>Alacak G\u00fcvencesi: %${coverage.toFixed(1)} | Dengeli</small></article><article class="checks-metric purple"><span>Tahsildeki (Banka Takas\u0131)</span><strong>${checkMoney(settled,currency)}</strong><small>Takasta: ${all.filter(row=>row.status==="Ciro Edildi").length} Bankada</small></article>`;
    const pageSize=Number($("#checkPageSize").value||10),maxPage=Math.max(0,Math.ceil(rows.length/pageSize)-1);window.checksReferencePage=Math.min(window.checksReferencePage||0,maxPage);const offset=window.checksReferencePage*pageSize,visible=rows.slice(offset,offset+pageSize);
    host.innerHTML=`<div class="table-wrap checks-reference-table"><table><thead><tr><th><input type="checkbox" data-check-select-all aria-label="G\u00f6r\u00fcnen evraklar\u0131 se\u00e7"></th><th>#</th><th>Evrak T\u00fcr\u00fc</th><th>Y\u00f6n</th><th>Ke\u015fideci / Bor\u00e7lu Cari</th><th>Banka &amp; \u015eube</th><th>Evrak / Seri No</th><th>Tutar ($ / TRY)</th><th>Vade Tarihi</th><th>Durum</th><th>H\u0131zl\u0131 \u0130\u015flemler</th></tr></thead><tbody>${visible.map((row,index)=>`<tr><td><input type="checkbox" data-check-select value="${esc(row.id)}" aria-label="${esc(row.check_no||row.portfolio_no||"Evrak")} se\u00e7"></td><td>${String(offset+index+1).padStart(2,"0")}</td><td><span class="check-type ${row.type==="Senet"?"note":"check"}">${esc(row.type||"")}</span></td><td class="${String(row.direction||"").startsWith("Giri\u015f")?"incoming":"outgoing"}">${String(row.direction||"").startsWith("Giri\u015f")?"\u2199 Al\u0131nan":"\u2197 Verilen"}</td><td><strong>${esc(row.issuer||"")}</strong><small>${esc(row.recipient||"")}</small></td><td><strong>${esc(row.bank_name||"")}</strong><small>${esc(row.branch_name||"")}</small></td><td class="mono">${esc(row.check_no||row.portfolio_no||"-")}</td><td class="mono amount">${checkMoney(row.amount,currency)}<small>${money(Number(row.amount||0),"TRY")}</small></td><td class="mono">${esc(String(row.due_date||"").slice(0,10))}</td><td><span class="check-status">${esc(row.status||"")}</span></td><td class="check-actions"><button class="mini" data-check-detail="${esc(row.id)}">Detay</button>${row.status==="Ciro Edildi"?"":`<button class="mini primary" data-check-status="Tahsil Edildi" data-check-id="${esc(row.id)}">Tahsil</button><button class="mini" data-check-status="Ciro Edildi" data-check-id="${esc(row.id)}">Takasa</button>`}</td></tr>`).join("")}</tbody></table></div>`;
    $("#genericCount").textContent=`Toplam ${rows.length} kay\u0131ttan ${rows.length?offset+1:0}-${Math.min(offset+visible.length,rows.length)} aras\u0131 listeleniyor.`;
    const pages=Array.from({length:maxPage+1},(_,index)=>index);$("#checkPagination").innerHTML=`<button data-check-page="${Math.max(0,window.checksReferencePage-1)}" ${window.checksReferencePage===0?"disabled":""}>\u00d6nceki</button>${pages.slice(0,3).map(index=>`<button data-check-page="${index}" class="${index===window.checksReferencePage?"active":""}">${index+1}</button>`).join("")}<button data-check-page="${Math.min(maxPage,window.checksReferencePage+1)}" ${window.checksReferencePage===maxPage?"disabled":""}>Sonraki</button>`;
    $("#genericSearch").oninput=()=>{window.checksReferencePage=0;loadGenericModule(meta,$("#genericSearch").value)};
    ["checkStatusFilter","checkBankFilter","checkDateStart","checkDateEnd","checkPageSize"].forEach(id=>$("#"+id).onchange=()=>{window.checksReferencePage=0;loadGenericModule(meta,$("#genericSearch").value)});
    $$('[data-check-tab]').forEach(button=>button.onclick=()=>{window.checksReferenceTab=button.dataset.checkTab;window.checksReferencePage=0;loadGenericModule(meta,$("#genericSearch").value)});
    $$('[data-check-currency]').forEach(button=>button.onclick=()=>{window.checksReferenceCurrency=button.dataset.checkCurrency;loadGenericModule(meta,$("#genericSearch").value)});
    $$('[data-check-page]').forEach(button=>button.onclick=()=>{window.checksReferencePage=Number(button.dataset.checkPage);loadChecksReference(meta,$("#genericSearch").value)});
    $("[data-check-select-all]")?.addEventListener("change",event=>$$('[data-check-select]').forEach(box=>box.checked=event.target.checked));
    $$('[data-check-detail]').forEach(button=>button.onclick=()=>openGenericDialog(meta,all.find(row=>String(row.id)===button.dataset.checkDetail)||{},result.columns));
    $$('[data-check-status]').forEach(button=>button.onclick=async()=>{await apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify({id:Number(button.dataset.checkId),status:button.dataset.checkStatus,_action:"update"})});toast("Evrak durumu g\u00fcncellendi","success");loadGenericModule(meta,$("#genericSearch").value)});
    $("[data-check-add]")?.addEventListener("click",()=>openGenericDialog(meta,{},result.columns));
    $("[data-check-export]")?.addEventListener("click",()=>download(`cek-senet-${today()}.csv`,csv(rows.map(row=>({"Evrak T\u00fcr\u00fc":row.type,"Y\u00f6n":row.direction,"Ke\u015fideci":row.issuer,"Banka":row.bank_name,"Seri No":row.check_no,"Tutar TRY":row.amount,"Vade":row.due_date,"Durum":row.status})))));
    $("[data-check-bulk]")?.addEventListener("click",async()=>{const ids=$$('[data-check-select]:checked').map(box=>Number(box.value));if(!ids.length){toast("\u00d6nce evrak se\u00e7in","warning");return}await Promise.all(ids.map(id=>apiFetch(`/api/desktop/table/${meta.table}`,{method:"POST",body:JSON.stringify({id,status:"Ciro Edildi",_action:"update"})})));toast(`${ids.length} evrak bankaya takas i\u015flemine verildi`,`success`);loadGenericModule(meta,$("#genericSearch").value)});
    $("[data-check-clear]")?.addEventListener("click",()=>{$("#genericSearch").value="";$("#checkStatusFilter").value="all";$("#checkBankFilter").value="";$("#checkDateStart").value="";$("#checkDateEnd").value="";window.checksReferenceTab="all";window.checksReferencePage=0;loadGenericModule(meta)});
  }catch(error){host.innerHTML=empty("Mod\u00fcl y\u00fcklenemedi",error.message)}
}

const ayecRenderBeforeChecksReference=render;
render=function(){
  if(page!=="checks")return ayecRenderBeforeChecksReference();
  document.body.dataset.page=page;const meta=genericModules.checks;
  $("#content").innerHTML=renderChecksReference();bindPage();
  loadGenericModule(meta);
};

const ayecLoadBeforeChecksReference=loadGenericModule;
loadGenericModule=async function(meta,q=""){
  if(meta?.table==="checks_notes")return loadChecksReference(meta,q);
  return ayecLoadBeforeChecksReference(meta,q);
};

// The income and expense workspace shares finance records with the dashboard.
let ayecIncomeExpenseTab="all";
let ayecIncomeExpenseQuery="";
let ayecIncomeExpenseMonth="";

function ayecIncomeExpenseFiltered(type=""){
  return (db.finance||[]).filter(item=>{
    const month=String(item.date||item.created_at||"").slice(0,7);
    const kind=String(item.type||"").toLocaleLowerCase("tr-TR");
    const category=String(item.category||"").toLocaleLowerCase("tr-TR");
    const text=[item.date,item.category,item.description,item.customer_name,item.ref_no,item.tracking_no].join(" ").toLocaleLowerCase("tr-TR");
    const tab=type==="Gider"?"expense":ayecIncomeExpenseTab;
    return (!ayecIncomeExpenseMonth||month===ayecIncomeExpenseMonth)
      &&(!ayecIncomeExpenseQuery||text.includes(ayecIncomeExpenseQuery.toLocaleLowerCase("tr-TR")))
      &&(tab==="all"||(tab==="expense"&&kind==="gider")||(tab==="income"&&kind==="gelir")
        ||(tab==="tax"&&/(vergi|sgk|kdv)/.test(category))
        ||(tab==="personnel"&&/(personel|maa|prim)/.test(category)));
  });
}

function ayecIncomeExpenseBody(type=""){
  const rows=ayecIncomeExpenseFiltered(type);
  const total=rows.filter(row=>row.type==="Gider").reduce((sum,row)=>sum+financeTryValue(row),0);
  const groups=new Map();
  rows.filter(row=>row.type==="Gider").forEach(row=>groups.set(row.category||"Other",(groups.get(row.category||"Other")||0)+financeTryValue(row)));
  const distribution=[...groups].sort((a,b)=>b[1]-a[1]).slice(0,5).map(([category,amount])=>`<div class="ie-distribution-row"><span>${esc(category)}</span><strong>${money(amount)}</strong><small>${total?Math.round(amount/total*100):0}%</small><i style="width:${total?Math.round(amount/total*100):0}%"></i></div>`).join("");
  const body=rows.map(item=>`<tr data-kind="finance" data-id="${esc(String(item.id||""))}"><td data-label="Tarih">${esc(item.date||item.created_at||"")}</td><td data-label="Kategori">${esc(item.category||item.type||"")}</td><td data-label="A\u00e7\u0131klama">${esc(item.description||"")}${item.customer_name?`<small>${esc(item.customer_name)}</small>`:""}</td><td data-label="Belge">${esc(item.ref_no||item.tracking_no||"")}</td><td data-label="\u00d6deme Kanal\u0131">${esc(item.payment_method||"")}<small class="${item.type==="Gider"?"ie-negative":"ie-positive"}">${item.type==="Gider"?"-":"+"}${money(financeTryValue(item))}</small></td></tr>`).join("");
  return {rows,body,distribution};
}

function ayecRenderIncomeExpense(type=""){
  const all=db.finance||[];
  const currentMonth=today().slice(0,7);
  if(!ayecIncomeExpenseMonth)ayecIncomeExpenseMonth=currentMonth;
  const monthly=all.filter(row=>String(row.date||row.created_at||"").startsWith(ayecIncomeExpenseMonth||currentMonth));
  const income=monthly.filter(row=>row.type==="Gelir").reduce((sum,row)=>sum+financeTryValue(row),0);
  const expense=monthly.filter(row=>row.type==="Gider").reduce((sum,row)=>sum+financeTryValue(row),0);
  const {rows,body,distribution}=ayecIncomeExpenseBody(type);
  const tabs=[["all","T\u00fcm Hareketler"],["expense","Gider / Masraflar"],["income","Tahsilatlar & Gelirler"],["tax","Vergi & SGK"],["personnel","Personel Harcamalar\u0131"]];
  const months=[...new Set(all.map(row=>String(row.date||row.created_at||"").slice(0,7)).filter(Boolean)),currentMonth].sort().reverse();
  return `<section class="ie-page">
    <header class="ie-heading"><div><h1>Gelir & Gider Y\u00f6netimi</h1><p>Kasa, fatura ve operasyonel gider hareketleri</p></div><div class="ie-actions"><button data-finance-fiscal>Mali D\u00f6nem Kapatma</button><button data-action="export-finance">Raporu D\u0131\u015fa Aktar</button><button class="ie-green" data-action="add-income">Yeni Gelir</button><button class="ie-red" data-action="add-expense">Yeni Gider</button></div></header>
    <div class="ie-metrics"><article><small>TOPLAM AYLIK GEL\u0130R</small><strong class="ie-positive">${money(income)}</strong></article><article><small>TOPLAM G\u0130DER & MASRAF</small><strong class="ie-negative">${money(expense)}</strong></article><article><small>NET \u0130\u015eLETME KARI</small><strong class="ie-positive">${money(income-expense)}</strong></article><article><small>BEKLEYEN ALACAKLAR</small><strong>${money(all.filter(row=>/bekliyor/i.test(String(row.status||""))).reduce((sum,row)=>sum+financeTryValue(row),0))}</strong></article></div>
    <div class="ie-columns"><main><div class="ie-tabs" role="tablist">${tabs.map(([key,label])=>`<button role="tab" data-ie-tab="${key}" aria-selected="${ayecIncomeExpenseTab===key}">${label}</button>`).join("")}</div><div class="ie-filters"><input id="ieSearch" type="search" value="${esc(ayecIncomeExpenseQuery)}" placeholder="Fi\u015f no, tedarik\u00e7i, gider veya a\u00e7\u0131klama ara..."><select id="ieMonth"><option value="">T\u00fcm D\u00f6nemler</option>${months.map(month=>`<option value="${esc(month)}" ${ayecIncomeExpenseMonth===month?"selected":""}>${esc(month)}</option>`).join("")}</select></div><div class="ie-table-wrap"><table class="ie-table"><thead><tr><th>TAR\u0130H</th><th>KATEGOR\u0130</th><th>A\u00c7IKLAMA & CAR\u0130</th><th>BELGE / NO</th><th>TUTAR</th></tr></thead><tbody id="ieTableBody">${body}</tbody></table></div><footer id="ieCount">${rows.length} hareket listeleniyor</footer></main>
    <aside><section class="ie-panel"><h2>Gider Da\u011f\u0131l\u0131m\u0131</h2><div id="ieDistribution">${distribution||"Bu d\u00f6nemde gider yok"}</div></section><section class="ie-panel ie-quick"><h2>H\u0131zl\u0131 Masraf / Gider Fi\u015fi</h2><label>Masraf Kategorisi<input id="ieCategory" placeholder="Kategori se\u00e7in"></label><label>\u00c7\u0131k\u0131\u015f Hesab\u0131<select id="ieBank"><option value="">Hesap se\u00e7in</option></select></label><div class="ie-quick-pair"><label>Tutar<input id="ieAmount" type="number" min="0.01" step="0.01" inputmode="decimal"></label><label>Fi\u015f / Fatura No<input id="ieReference"></label></div><label class="ie-receipt">Fi\u015f / Fatura G\u00f6rseli<input id="ieReceipt" type="file" accept=".jpg,.jpeg,.png,.pdf"></label><button class="ie-save" type="button" data-ie-save>Fi\u015fi Kaydet</button></section></aside></div></section>`;
}

const ayecFinanceBeforeIncomeExpense=renderFinance;
renderFinance=function(filter=""){
  return filter?ayecRenderIncomeExpense(filter).replace("<th>TUTAR</th>","<th>\u00d6DEME KANALI</th>"):ayecFinanceBeforeIncomeExpense(filter);
};

function ayecRefreshIncomeExpense(){
  const table=document.querySelector("#ieTableBody");
  if(!table)return;
  const {rows,body,distribution}=ayecIncomeExpenseBody(page==="expense"?"Gider":"Gelir");
  table.innerHTML=body;
  document.querySelector("#ieDistribution").innerHTML=distribution||"Bu d\u00f6nemde gider yok";
  document.querySelector("#ieCount").textContent=`${rows.length} hareket listeleniyor`;
  document.querySelectorAll("[data-ie-tab]").forEach(button=>button.setAttribute("aria-selected",String(button.dataset.ieTab===ayecIncomeExpenseTab)));
}

async function ayecLoadIncomeExpenseBanks(){
  const select=document.querySelector("#ieBank");
  if(!select)return;
  try{
    const data=await apiFetch("/api/desktop/table/bank_accounts?limit=500");
    if(!document.querySelector("#ieBank"))return;
    select.innerHTML='<option value="">Hesap se\u00e7in</option>'+(data.rows||[]).filter(row=>Number(row.is_active||0)===1).map(row=>`<option value="${Number(row.id)}">${esc([row.bank_name,row.account_holder].filter(Boolean).join(" - "))}</option>`).join("");
  }catch(error){select.innerHTML='<option value="">Hesaplar y\u00fcklenemedi</option>'}
}

async function ayecQuickExpenseSave(){
  const category=document.querySelector("#ieCategory")?.value.trim();
  const bank=Number(document.querySelector("#ieBank")?.value||0);
  const amount=Number(document.querySelector("#ieAmount")?.value||0);
  const reference=document.querySelector("#ieReference")?.value.trim()||"";
  const file=document.querySelector("#ieReceipt")?.files?.[0];
  if(!category||!bank||!amount||amount<=0){toast("Kategori, hesap ve tutar girin","warning");return}
  if(file&&(!/\.(jpe?g|png|pdf)$/i.test(file.name)||file.size>5*1024*1024)){toast("JPG, PNG veya PDF se\u00e7in (en fazla 5 MB)","warning");return}
  let receipt_base64="";
  if(file){
    const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(reader.error);reader.readAsDataURL(file)});
    receipt_base64=String(encoded).split(",",2)[1]||"";
  }
  try{
    await apiFetch("/api/desktop/accounting/quick-expense",{method:"POST",body:JSON.stringify({category,bank_account_id:bank,amount,ref_no:reference,receipt_name:file?.name||"",receipt_base64})});
    await hydrateDesktop(false);
    render();
    toast("Gider kaydedildi");
  }catch(error){toast(error.message||"Gider kaydedilemedi","error")}
}

document.addEventListener("click",event=>{
  const tab=event.target.closest("[data-ie-tab]");
  if(tab){ayecIncomeExpenseTab=tab.dataset.ieTab;ayecRefreshIncomeExpense();return}
  if(event.target.closest("[data-ie-save]")){ayecQuickExpenseSave()}
});
document.addEventListener("input",event=>{
  if(event.target.id==="ieSearch"){ayecIncomeExpenseQuery=event.target.value;ayecRefreshIncomeExpense()}
});
document.addEventListener("change",event=>{
  if(event.target.id==="ieMonth"){ayecIncomeExpenseMonth=event.target.value;ayecRefreshIncomeExpense()}
});

const ayecRenderBeforeIncomeExpense=render;
render=function(){
  ayecRenderBeforeIncomeExpense();
  if(page==="income"||page==="expense")ayecLoadIncomeExpenseBanks();
};

let ayecBankAccounts=[];
let ayecBankColumns=[];
let ayecBankFilter="all";
let ayecBankQuery="";
let ayecBankSelected=null;

function ayecBankShell(){
  return `<section class="bank-ref"><header class="bank-ref-head"><div><h1>Hazine &amp; Nakit Ak\u0131\u015f Kontrol\u00fc</h1><p>\u00c7oklu banka hesab\u0131 bakiyeleri, at\u00f6lye kasalar\u0131 ve sanal POS hareketleri</p></div><div class="bank-ref-actions"><button data-bank-action="statement">Banka Ekstresi (OFX / MT940)</button><button data-bank-action="transfer">Virman &amp; Transfer</button><button class="primary" data-bank-action="add">Yeni Hesap / Kasa</button><button data-bank-action="more">D\u0131\u015fa Aktar</button></div></header>
  <div class="bank-ref-metrics"><article><small>TOPLAM L\u0130K\u0130D\u0130TE &amp; SICAK NAK\u0130T</small><strong id="bankMetricTotal">-</strong></article><article><small>BANKA HESAP BAK\u0130YELER\u0130</small><strong id="bankMetricAccounts">-</strong></article><article><small>F\u0130Z\u0130K\u0130 AT\u00d6LYE &amp; SAHA KASALARI</small><strong id="bankMetricCash">-</strong></article><article><small>POS BLOKAJ &amp; BEKLEYEN</small><strong id="bankMetricPos">-</strong></article></div>
  <div class="bank-ref-columns"><section class="bank-ref-left"><div class="bank-ref-section-head"><h2>Tan\u0131ml\u0131 Hesaplar &amp; Kasalar</h2><button data-bank-action="table">Tablo / Toplu \u0130\u015flem</button></div><div id="bankAccountCards" class="bank-account-cards"></div><section class="bank-fund"><div>FON DA\u011eILIMI <strong id="bankFundTotal"></strong></div><div id="bankFundBar" class="bank-fund-bar"></div><div id="bankFundLegend" class="bank-fund-legend"></div></section></section>
  <section class="bank-ref-right"><nav class="bank-ref-filters">${[["all","T\u00dcM HAREKETLER"],["income","GELEN HAVALE"],["expense","G\u0130DEN G\u0130DER"],["cash","KASA NAK\u0130T"],["pos","POS BLOKE"]].map(([key,label])=>`<button data-bank-filter="${key}" aria-selected="${ayecBankFilter===key}">${label}</button>`).join("")}<input id="bankRefSearch" placeholder="Fi\u015f, a\u00e7\u0131klama ara..."></nav><div class="bank-ledger-wrap"><table class="bank-ledger"><thead><tr><th>ZAMAN / F\u0130\u015e</th><th>\u0130\u015eLEM DETAYI &amp; HESAP</th><th>TUTAR &amp; Y\u00d6N</th><th>AKS\u0130YON</th></tr></thead><tbody id="bankLedgerBody"></tbody></table></div><div class="bank-reconcile"><article><small>G\u00dcNL\u00dcK MUTABAKAT DURUMU</small><strong>Ekstre e\u015fle\u015ftirme sonucunu inceleyin</strong></article><article><small>OTOMAT\u0130K CAR\u0130 TANIMA</small><strong id="bankAutoMatch">Hesap hareketleri g\u00fcncel</strong></article></div></section></div>
  <details class="bank-ref-data"><summary>Hesap tablosu ve toplu aktar\u0131m</summary><div id="bankGenericHost"></div></details></section>`;
}

function ayecBankClass(row){
  const value=`${row.account_type||""} ${row.bank_name||""} ${row.account_holder||row.account_name||""}`.toLocaleLowerCase("tr-TR");
  return value.includes("pos")?"pos":/(kasa|cash)/.test(value)?"cash":"bank";
}

function ayecBankRenderData(rows){
  ayecBankAccounts=rows||[];
  if(!ayecBankSelected&&ayecBankAccounts.length)ayecBankSelected=Number(ayecBankAccounts[0].id);
  const active=ayecBankAccounts.filter(row=>Number(row.is_active??1)===1);
  const toTry=row=>moneyNumber(row.current_balance)*rateForCode(row.currency||"TRY");
  const total=active.reduce((sum,row)=>sum+toTry(row),0);
  const cash=active.filter(row=>ayecBankClass(row)==="cash").reduce((sum,row)=>sum+toTry(row),0);
  const pos=active.filter(row=>ayecBankClass(row)==="pos").reduce((sum,row)=>sum+toTry(row),0);
  const bank=total-cash-pos;
  $("#bankMetricTotal").textContent=money(total);
  $("#bankMetricAccounts").textContent=money(bank);
  $("#bankMetricCash").textContent=money(cash);
  $("#bankMetricPos").textContent=money(pos);
  $("#bankFundTotal").textContent=`Hacim: ${active.length} hesap`;
  const chunks=active.map(row=>({row,value:Math.max(0,moneyNumber(row.current_balance))}));
  const denominator=chunks.reduce((sum,item)=>sum+item.value,0)||1;
  $("#bankFundBar").innerHTML=chunks.map((item,index)=>`<i style="width:${item.value/denominator*100}%;background:${["#38d6a7","#4e8bff","#bcc9e2","#ff496f","#b27aff"][index%5]}"></i>`).join("");
  $("#bankFundLegend").innerHTML=chunks.slice(0,5).map((item,index)=>`<span><i style="background:${["#38d6a7","#4e8bff","#bcc9e2","#ff496f","#b27aff"][index%5]}"></i>${esc(item.row.bank_name||item.row.account_holder||"Hesap")}</span>`).join("");
  $("#bankAccountCards").innerHTML=active.map(row=>{
    const type=ayecBankClass(row), selected=Number(row.id)===Number(ayecBankSelected);
    const holder=row.account_holder||row.account_name||"";
    return `<button class="bank-account-card ${selected?"selected":""}" data-bank-card="${Number(row.id)}"><span class="bank-account-card-head"><b>${esc(row.bank_name||"Banka")}</b><small>${type==="cash"?"Fiziki Nakit":type==="pos"?"Sanal POS":"Aktif"}</small></span><code>${esc(row.account_number||row.iban||"")}</code><small>${esc(holder)}</small><span class="bank-balance-caption">Kullan\u0131labilir Bakiye</span><strong>${money(row.current_balance,row.currency||"TRY")}</strong></button>`;
  }).join("")||'<div class="bank-empty">Banka hesab\u0131 bulunamad\u0131.</div>';
  ayecBankUpdateLedger();
}

function ayecBankUpdateLedger(){
  const ids=new Set(ayecBankAccounts.map(row=>Number(row.id)));
  const selected=ayecBankSelected?Number(ayecBankSelected):null;
  let rows=(db.finance||[]).filter(row=>row.bank_account_id&&ids.has(Number(row.bank_account_id)));
  if(selected)rows=rows.filter(row=>Number(row.bank_account_id)===selected);
  if(ayecBankFilter==="income")rows=rows.filter(row=>row.type==="Gelir");
  if(ayecBankFilter==="expense")rows=rows.filter(row=>row.type==="Gider");
  if(ayecBankFilter==="cash")rows=rows.filter(row=>/kasa|cash/i.test(String(row.payment_method||row.category||"")));
  if(ayecBankFilter==="pos")rows=rows.filter(row=>/pos/i.test(String(row.payment_method||row.category||"")));
  if(ayecBankQuery){const q=ayecBankQuery.toLocaleLowerCase("tr-TR");rows=rows.filter(row=>[row.date,row.description,row.category,row.ref_no,row.customer_name].join(" ").toLocaleLowerCase("tr-TR").includes(q))}
  rows=rows.slice(0,100);
  $("#bankLedgerBody").innerHTML=rows.map(row=>`<tr><td>${esc(row.date||row.created_at||"")}<small>#${esc(String(row.ref_no||row.id||""))}</small></td><td>${esc(row.customer_name||row.description||"")}<small>${esc([row.type,row.category].filter(Boolean).join(" | "))}</small></td><td class="${row.type==="Gider"?"negative":"positive"}">${row.type==="Gider"?"-":"+"}${money(financeTryValue(row))}<small>${esc(row.status||"Kaydedildi")}</small></td><td><button class="mini" data-kind="finance" data-id="${esc(String(row.id||""))}">Detay</button></td></tr>`).join("")||'<tr><td colspan="4" class="bank-empty">Bu hesapta hareket bulunamad\u0131.</td></tr>';
  document.querySelectorAll("[data-bank-filter]").forEach(button=>button.setAttribute("aria-selected",String(button.dataset.bankFilter===ayecBankFilter)));
}

async function ayecLoadBankReference(){
  if(page!=="banks")return;
  try{
    const data=await apiFetch("/api/desktop/table/bank_accounts?limit=500");
    ayecBankColumns=data.columns||[];
    ayecBankRenderData(data.rows||[]);
  }catch(error){toast(error.message||"Banka hesaplar\u0131 y\u00fcklenemedi","error")}
}

function ayecOpenBankTransfer(){
  const active=ayecBankAccounts.filter(row=>Number(row.is_active??1)===1);
  if(active.length<2){toast("Transfer i\u00e7in en az iki aktif hesap gereklidir","warning");return}
  const options=active.map(row=>`<option value="${Number(row.id)}">${esc(`${row.bank_name||"Hesap"} - ${row.account_holder||row.account_name||""}`)}</option>`).join("");
  openDialog("Hesaplar Aras\u0131 Transfer","BANKA",`<div class="form-grid"><div class="field"><label>Kaynak hesap</label><select name="from_account_id">${options}</select></div><div class="field"><label>Hedef hesap</label><select name="to_account_id">${options}</select></div><div class="field"><label>Tutar</label><input name="amount" type="number" min="0.01" step="0.01" required></div><div class="field full"><label>A\u00e7\u0131klama</label><input name="description"></div></div>`,async form=>{
    const values=Object.fromEntries(form);
    if(values.from_account_id===values.to_account_id)throw Error("Farkl\u0131 kaynak ve hedef hesap se\u00e7in");
    await apiFetch("/api/desktop/bank-transfer",{method:"POST",body:JSON.stringify(values)});
    await hydrateDesktop(false);await ayecLoadBankReference();toast("Transfer tamamland\u0131");return true;
  },"Transfer Et");
}

async function ayecPreviewBankStatement(){
  const input=document.createElement("input");input.type="file";input.accept=".ofx,.mt940,.sta,.txt";
  input.onchange=async()=>{
    const file=input.files?.[0];if(!file)return;
    if(file.size>10*1024*1024){toast("Ekstre dosyas\u0131 10 MB s\u0131n\u0131r\u0131n\u0131 a\u015f\u0131yor","warning");return}
    try{
      const text=await file.text();let rows=[];
      if(file.name.toLowerCase().endsWith(".ofx")){
        for(const block of text.split(/<STMTTRN>/i).slice(1)){
          const get=tag=>block.match(new RegExp(`<${tag}>\\s*([^<\\r\\n]+)`,"i"))?.[1]?.trim()||"";
          const date=get("DTPOSTED").slice(0,8),amount=get("TRNAMT");if(!/^\\d{8}$/.test(date)||!amount)continue;
          rows.push({date:`${date.slice(6,8)}.${date.slice(4,6)}.${date.slice(0,4)}`,amount:Number(amount),description:get("MEMO")||get("NAME"),ref:get("FITID")});
        }
      }else{
        let current=null;
        for(const line of text.split(/\\r?\\n/)){
          const match=line.match(/^:61:(\\d{6})(?:\\d{4})?([CD])([A-Z])?([0-9,]+)/);
          if(match){const amount=Number(match[4].replace(",","."))*(match[2]==="D"?-1:1);current={date:`${match[1].slice(4,6)}.${match[1].slice(2,4)}.20${match[1].slice(0,2)}`,amount,description:"",ref:line.slice(match[0].length).trim()};rows.push(current)}
          else if(current&&line.startsWith(":86:"))current.description=line.slice(4).trim();
        }
      }
      if(!rows.length)throw Error("Ekstrede hareket bulunamad\u0131");
      const preview=rows.slice(0,300).map(row=>`<tr><td>${esc(row.date)}</td><td>${money(row.amount)}</td><td>${esc(row.ref||"")}</td><td>${esc(row.description||"")}</td></tr>`).join("");
      openDialog("Banka Ekstresi \u00d6nizleme","${esc(file.name)}",`<p>${rows.length} hareket okundu. Kay\u0131tlar otomatik i\u015flenmedi.</p><div class="table-wrap"><table><thead><tr><th>Tarih</th><th>Tutar</th><th>Referans</th><th>A\u00e7\u0131klama</th></tr></thead><tbody>${preview}</tbody></table></div>`,async()=>true,"Kapat");
    }catch(error){toast(error.message||"Ekstre okunamad\u0131","error")}
  };
  input.click();
}

function ayecBindBankActions(){
  document.addEventListener("click",event=>{
    const filter=event.target.closest("[data-bank-filter]");
    if(filter){ayecBankFilter=filter.dataset.bankFilter;ayecBankUpdateLedger();return}
    const card=event.target.closest("[data-bank-card]");
    if(card){ayecBankSelected=Number(card.dataset.bankCard);ayecBankRenderData(ayecBankAccounts);return}
    const action=event.target.closest("[data-bank-action]")?.dataset.bankAction;
    if(!action)return;
    if(action==="refresh"){ayecLoadBankReference();return}
    if(action==="transfer"){ayecOpenBankTransfer();return}
    if(action==="statement"){ayecPreviewBankStatement();return}
    if(action==="add"){
      apiFetch("/api/desktop/table/bank_accounts?limit=1").then(data=>openGenericDialog(genericModules.banks,{},data.columns)).catch(error=>toast(error.message,"error"));return;
    }
    if(action==="table"){
      const detail=document.querySelector(".bank-ref-data");if(detail){detail.open=!detail.open;if(detail.open&&!detail.dataset.loaded){detail.dataset.loaded="1";loadGenericModule(genericModules.banks)}}return;
    }
    if(action==="more")download(`banka-hesaplari-${today()}.csv`,csv(ayecBankAccounts));
  });
  document.addEventListener("input",event=>{if(event.target.id==="bankRefSearch"){ayecBankQuery=event.target.value;ayecBankUpdateLedger()}});
}
ayecBindBankActions();

const ayecRenderBeforeBankReference=render;
render=function(){
  if(page!=="banks")return ayecRenderBeforeBankReference();
  document.body.dataset.page=page;
  $("#content").innerHTML=ayecBankShell();
  bindPage();
  ayecLoadBankReference();
};

// Part 3: loaner workspace aligned to the reference screen.
let ayecLoanerView = "active";
let ayecLoanerDevices = [];
let ayecLoanerHistory = [];
let ayecLoanerHistoryLoaded = false;
let ayecLoanerCurrentData = null;
let ayecLoanerCurrentMeta = null;
const ayecGenericShellBeforeLoaners = genericShell;
genericShell = function(meta) {
  if (meta?.table !== "loaner_devices") return ayecGenericShellBeforeLoaners(meta);
  return pageHead("Emanet (Konsinye) Cihazlar", "M\u00fc\u015fterilere verilen ge\u00e7ici cihazlar\u0131n depo ve iade takibi.", '<button class="secondary" data-generic-refresh>Yenile</button><button class="secondary" data-loaner-action="return-selected">\u0130ade Al &amp; Test Et</button><button class="secondary" data-loaner-action="print-contract">S\u00f6zle\u015fme Yazd\u0131r</button><button class="secondary" data-loaner-export>Excel</button><button class="primary" data-generic-add>+ Yeni Emanet Ver</button>') +
    '<section class="metric-grid loaner-ref-metrics"><article><div><small>M\u00fc\u015fterideki \u0130kameler</small><strong id="loanerMetricActive">0 Cihaz</strong></div><footer><span id="loanerMetricActiveDetail">Aktif kullan\u0131mda</span><span id="loanerMetricOccupancy">Doluluk %0</span></footer></article><article><div><small>M\u00fcsait Konsinye Stok</small><strong id="loanerMetricAvailable">0 Cihaz</strong></div><footer><span>Test edilmi\u015f / Haz\u0131r</span><span>Emanet Deposu</span></footer></article><article><div><small>\u0130adesi Gecikenler</small><strong id="loanerMetricOverdue">0 Acil</strong></div><footer><span id="loanerMetricOverdueDetail">Ortalama 0 g\u00fcn a\u015f\u0131m</span><button type="button" data-loaner-view="overdue">Gecikenleri g\u00f6r</button></footer></article><article><div><small>Sahadaki Cihaz De\u011feri</small><strong id="loanerMetricValue">0</strong></div><footer><span>Teminat alt\u0131nda</span><span id="loanerMetricCoverage">0 cihaz kay\u0131tl\u0131</span></footer></article></section>' +
    '<section class="card loaner-ref-workspace"><nav class="loaner-ref-tabs" aria-label="Emanet g\u00f6r\u00fcn\u00fcmleri"><button type="button" data-loaner-view="active">M\u00fc\u015fterideki Cihazlar (Aktif)</button><button type="button" data-loaner-view="depot">Emanet Cihaz Deposu</button><button type="button" data-loaner-view="overdue">Gecikmi\u015f iadeler</button><button type="button" data-loaner-view="history">\u0130ade Ge\u00e7mi\u015fi Ar\u015fiv</button><button type="button" data-loaner-view="commitments">Taahh\u00fctler</button><button type="button" data-loaner-view="help">Nas\u0131l Kullan\u0131l\u0131r?</button></nav><div class="loaner-ref-filter"><input class="control search" id="genericSearch" type="search" placeholder="Cihaz, m\u00fc\u015fteri veya seri no ara..."><div class="loaner-ref-category-filter" role="group" aria-label="Cihaz kategorisi"><button type="button" class="active" data-loaner-type="all">T\u00fcm\u00fc</button><button type="button" data-loaner-type="Laptop">Laptop / PC</button><button type="button" data-loaner-type="Switch">Switch &amp; A\u011f</button><button type="button" data-loaner-type="NVR">NVR / Kamera</button></div><input id="loanerTypeFilter" type="hidden" value="all"><select id="loanerStatusFilter"><option value="all">T\u00fcm Durumlar</option><option value="Aktif">Aktif</option><option value="\u0130ade Edildi">\u0130ade Edildi</option></select></div><div class="loaner-ref-list"><div id="genericCount" class="muted">Y\u00fckleniyor</div><div id="genericHost">Y\u00fckleniyor...</div></div></section>' +
    '<section class="loaner-ref-insights"><article><h3>Konsinye Cihaz Kategorileri</h3><div class="loaner-ref-category-layout"><div class="loaner-ref-donut"><b id="loanerInsightCount">0</b><small>Adet</small></div><ul id="loanerCategoryLegend"></ul></div></article><article><header><h3>\u0130ade Taahh\u00fct S\u00f6zle\u015fmesi</h3><span class="loaner-ref-signature">E-\u0130mza Destekli</span></header><p>M\u00fc\u015fteriye teslim edilecek ikame cihazlar i\u00e7in hukuki emanet protokol\u00fc.</p><label class="loaner-ref-sms"><span><b>SMS Onay Kodu G\u00f6nderimi</b><small>Teknik servis teslim an\u0131nda</small></span><input type="checkbox" id="loanerSmsEnabled" checked></label><footer><small class="muted">\u015eablon: Konsinye-V4.pdf</small><button type="button" class="secondary" data-loaner-view="commitments">Taahh\u00fct Kay\u0131tlar\u0131</button></footer></article><article><h3>H\u0131zl\u0131 Rezerve Edilebilir Stok</h3><p id="loanerInsightAvailable">0 cihaz haz\u0131r</p><ul id="loanerAvailablePreview"></ul><button type="button" class="secondary" data-loaner-view="depot">T\u00fcm Depoyu G\u00f6r\u00fcnt\u00fcle</button></article></section>';
};

function ayecLoanerFilteredRows(meta, data, query) {
  const term = String(query || "").trim().toLocaleLowerCase("tr-TR");
  const type = $("#loanerTypeFilter")?.value || "all";
  const status = $("#loanerStatusFilter")?.value || "all";
  return (data.rows || []).filter(row => {
    const values = [row.brand_model, row.device_type, row.serial_mac, row.customer_name, row.customer_phone, row.tracking_no, row.status, row.shelf_no];
    const matchesTerm = !term || values.some(value => String(value || "").toLocaleLowerCase("tr-TR").includes(term));
    const matchesType = type === "all" || String(row.device_type || row.brand_model || "").toLocaleLowerCase("tr-TR").includes(type.toLocaleLowerCase("tr-TR"));
    const matchesStatus = status === "all" || String(row.status || "").toLocaleLowerCase("tr-TR") === status.toLocaleLowerCase("tr-TR");
    const overdue = !row.date_returned && row.expected_return && new Date(row.expected_return) < new Date();
    const matchesView = ayecLoanerView === "overdue" ? Boolean(overdue) : ayecLoanerView === "history" ? Boolean(row.date_returned) : ayecLoanerView === "active" ? !row.date_returned && (!row.status || /aktif|emanet|verildi/i.test(row.status)) : true;
    return matchesTerm && matchesType && matchesStatus && matchesView;
  });
}

function ayecLoanerRenderRows(meta, data, query) {
  const host = $("#genericHost");
  if (!host) return;
  const rows = ayecLoanerFilteredRows(meta, data, query);
  const viewMeta = ayecLoanerView === "active" || ayecLoanerView === "overdue" || ayecLoanerView === "history" ? { ...meta, table: "loaner_transactions" } : meta;
  host.innerHTML = rows.length ? genericTable(viewMeta, { ...data, rows, count: rows.length }) : empty("Kay\u0131t bulunamadi", "Se\u00e7ili gorunum ve filtrelerle e\u015fle\u015fen kay\u0131t bulunamad\u0131.");
  $("#genericCount").textContent = "G\u00f6r\u00fcnt\u00fclenen " + rows.length + " / " + (data.rows || []).length + " kay\u0131t";
  $$(".generic-edit").forEach(button => button.onclick = () => openGenericDialog(viewMeta, rows[Number(button.dataset.index)], data.columns));
  $$(".generic-delete").forEach(button => button.onclick = () => deleteGenericRow(viewMeta, rows[Number(button.dataset.index)]));
  $$('[data-generic-row]').forEach(row => { row.ondblclick = () => openGenericDialog(viewMeta, rows[Number(row.dataset.genericRow)], data.columns); bindInteractiveRow(row); });
}

const ayecLoadGenericBeforeLoaner = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  await ayecLoadGenericBeforeLoaner(meta, query);
  if (page !== "loaners" || !["loaner_devices", "loaner_transactions"].includes(meta?.table) || !window.currentGenericData) return;
  const data = window.currentGenericData;
  if (meta.table === "loaner_devices") ayecLoanerDevices = data.rows || [];
  if (meta.table === "loaner_transactions") { try { const refreshed = await apiFetch("/api/desktop/table/loaner_transactions?limit=500"); ayecLoanerHistory = refreshed.rows || []; ayecLoanerHistoryLoaded = true; } catch { ayecLoanerHistory = data.rows || []; } }
  if (!ayecLoanerHistoryLoaded) {
    try { const response = await apiFetch("/api/desktop/table/loaner_transactions?limit=500"); ayecLoanerHistory = response.rows || []; ayecLoanerHistoryLoaded = true; }
    catch { ayecLoanerHistory = []; }
  }
  ayecLoanerHistory = ayecLoanerHistory.map(row => { const device = ayecLoanerDevices.find(item => String(item.id) === String(row.device_id)) || {}; return { ...row, brand_model: row.brand_model || device.brand_model || "", device_type: row.device_type || device.device_type || "", serial_mac: row.serial_mac || device.serial_mac || "" }; });
  const devices = meta.table === "loaner_devices" ? data.rows || [] : ayecLoanerDevices;
  const available = devices.filter(row => /depo|haz\u0131r|m\u00fcsait/i.test(String(row.status || "Depoda"))).length;
  const active = ayecLoanerHistory.filter(row => !row.date_returned && /aktif|emanet|verildi/i.test(String(row.status || "Aktif"))).length;
  const overdue = ayecLoanerHistory.filter(row => !row.date_returned && row.expected_return && new Date(row.expected_return) < new Date()).length;
  $("#loanerMetricActive").textContent = active + " Cihaz";
  $("#loanerMetricAvailable").textContent = available + " Cihaz";
  $("#loanerMetricOverdue").textContent = overdue + " Acil";
  $("#loanerMetricActiveDetail").textContent = active ? "Aktif kullan\u0131mda" : "Aktif emanet kayd\u0131 yok";
  $("#loanerMetricOccupancy").textContent = "Doluluk %" + (devices.length ? Math.round(active * 100 / devices.length) : 0);
  $("#loanerMetricOverdueDetail").textContent = "Ortalama " + (overdue ? Math.round(ayecLoanerHistory.filter(row => !row.date_returned && row.expected_return && new Date(row.expected_return) < new Date()).reduce((sum, row) => sum + Math.max(0, (Date.now() - new Date(row.expected_return).getTime()) / 86400000), 0) / overdue) : 0).toFixed(1) + " g\u00fcn a\u015f\u0131m";
  $("#loanerMetricCoverage").textContent = devices.length + " cihaz kay\u0131tl\u0131";
  $("#loanerMetricValue").textContent = money(devices.reduce((sum, row) => sum + Number(row.value || row.price || 0), 0), "TRY");
  $("#loanerInsightCount").textContent = String(devices.length);
  const categories = devices.reduce((counts, row) => { const key = String(row.device_type || "Genel"); counts[key] = (counts[key] || 0) + 1; return counts; }, {});
  const legend = $("#loanerCategoryLegend");
  if (legend) legend.innerHTML = Object.entries(categories).slice(0, 3).map(([name, count], index) => '<li class="loaner-ref-category-' + index + '"><span>' + esc(name) + '</span><b>' + count + ' Ad.</b></li>').join("");
  const preview = $("#loanerAvailablePreview");
  if (preview) preview.innerHTML = devices.filter(row => /depo|haz\u0131r|m\u00fcsait/i.test(String(row.status || "Depoda"))).slice(0, 3).map(row => '<li><span>' + esc(row.brand_model || row.device_type || "Cihaz") + '</span><b>Hemen Ata</b></li>').join("");
  $("#loanerInsightAvailable").textContent = available + " cihaz haz\u0131r";
  const buttons = $$('.loaner-ref-tabs [data-loaner-view]');
  if (buttons[0]) buttons[0].textContent = "M\u00fc\u015fterideki Cihazlar (Aktif) " + active;
  if (buttons[1]) buttons[1].textContent = "Emanet Cihaz Deposu " + devices.length;
  if (buttons[2]) buttons[2].textContent = "Gecikmi\u015f iadeler " + overdue;
  if (buttons[3]) buttons[3].textContent = "\u0130ade Ge\u00e7mi\u015fi & Ar\u015fiv";
  const selected = ayecLoanerView === "active" || ayecLoanerView === "overdue" || ayecLoanerView === "history" ? { ...meta, table: "loaner_transactions" } : { ...meta, table: "loaner_devices" };
  const visibleData = selected.table === "loaner_transactions" ? { ...data, columns: Object.keys(ayecLoanerHistory[0] || {}), rows: ayecLoanerHistory, count: ayecLoanerHistory.length } : { ...data, columns: Object.keys(devices[0] || {}), rows: devices, count: devices.length };
  ayecLoanerCurrentData = visibleData;
  ayecLoanerCurrentMeta = selected;
  ayecLoanerRenderRows(selected, visibleData, query);
};
document.addEventListener("click", event => {
  const typeButton = event.target.closest("[data-loaner-type]");
  if (typeButton && page === "loaners") { $("#loanerTypeFilter").value = typeButton.dataset.loanerType; $$("[data-loaner-type]").forEach(button => button.classList.toggle("active", button === typeButton)); if (ayecLoanerCurrentData) ayecLoanerRenderRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, $("#genericSearch")?.value || ""); return; }
  const view = event.target.closest("[data-loaner-view]");
  if (!view || page !== "loaners") return;
  ayecLoanerView = view.dataset.loanerView;
  ayecLoanerSelectedIds.clear();
  if (ayecLoanerView === "commitments") { navigate("contracts"); return; }
  if (ayecLoanerView === "help") { toast("Cihazi secerek teslim, iade ve seri numaras\u0131 bilgilerini yonetin."); return; }
  $$('.loaner-ref-tabs [data-loaner-view]').forEach(button => button.classList.toggle("active", button.dataset.loanerView === ayecLoanerView));
  if (window.currentGenericData) loadGenericModule(genericModules.loaners, $("#genericSearch")?.value || "");
});
document.addEventListener("change", event => {
  if (page === "loaners" && ["loanerTypeFilter", "loanerStatusFilter"].includes(event.target.id) && ayecLoanerCurrentData) ayecLoanerRenderRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, $("#genericSearch")?.value || "");
  if (page === "loaners" && event.target.id === "genericSearch" && ayecLoanerCurrentData) ayecLoanerRenderRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, event.target.value);
  if (page === "loaners" && event.target.id === "loanerSmsEnabled") localStorage.setItem("ayec.loaner.smsEnabled", event.target.checked ? "1" : "0");
});
document.addEventListener("click", event => { if (event.target.closest("[data-loaner-export]") && page === "loaners") { const rows = ayecLoanerView === "depot" ? ayecLoanerDevices : ayecLoanerHistory; download("emanet-cihazlar-" + today() + ".csv", rows); } });
document.addEventListener("change", event => {
  if (page !== "loaners") return;
  const selectAll = event.target.closest("[data-loaner-select-all]");
  if (selectAll) { const filtered = ayecLoanerCurrentData ? ayecLoanerFilteredRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, $("#genericSearch")?.value || "") : []; filtered.slice(ayecLoanerPage * ayecLoanerPageSize, (ayecLoanerPage + 1) * ayecLoanerPageSize).forEach(row => selectAll.checked ? ayecLoanerSelectedIds.add(String(row.id)) : ayecLoanerSelectedIds.delete(String(row.id))); if (ayecLoanerCurrentData) ayecLoanerRenderRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, $("#genericSearch")?.value || ""); return; }
  const checkbox = event.target.closest("[data-loaner-select]");
  if (checkbox) { checkbox.checked ? ayecLoanerSelectedIds.add(String(checkbox.value)) : ayecLoanerSelectedIds.delete(String(checkbox.value)); }
});
document.addEventListener("click", event => {
  const button = event.target.closest('[data-loaner-action="return-selected"]');
  if (!button || page !== "loaners") return;
  const rows = ayecLoanerHistory.filter(row => ayecLoanerSelectedIds.has(String(row.id)));
  if (rows.length !== 1) { toast("İade işlemi için listeden bir cihaz seçin.", "warning"); return; }
  const row = rows[0];
  apiFetch("/api/desktop/table/loaner_transactions?limit=1").then(data => openGenericDialog({ title: "Emanet İade Kaydı", table: "loaner_transactions" }, { ...row, date_returned: today(), status: "İade Edildi" }, data.columns)).catch(error => toast(error.message, "error"));
});

const ayecRenderBeforeLoanerActions = render;
render = function() {
  ayecRenderBeforeLoanerActions();
  if (page !== "loaners") return;
  const add = $("[data-generic-add]");
  if (add) add.onclick = async () => {
    try { const data = await apiFetch("/api/desktop/table/loaner_transactions?limit=1"); openGenericDialog({ title: "Yeni Emanet", table: "loaner_transactions" }, {}, data.columns); }
    catch (error) { toast(error.message, "error"); }
  };
  $$('.loaner-ref-tabs [data-loaner-view]').forEach(button => button.classList.toggle("active", button.dataset.loanerView === ayecLoanerView));
  const sms = $("#loanerSmsEnabled");
  if (sms) sms.checked = localStorage.getItem("ayec.loaner.smsEnabled") !== "0";
};
let ayecLoanerPage = 0;
let ayecLoanerSelectedIds = new Set();
const ayecLoanerPageSize = 5;
function ayecLoanerRenderRows(meta, data, query) {
  const host = $("#genericHost");
  if (!host) return;
  const rows = ayecLoanerFilteredRows(meta, data, query);
  const pages = Math.max(1, Math.ceil(rows.length / ayecLoanerPageSize));
  ayecLoanerPage = Math.min(ayecLoanerPage, pages - 1);
  const visible = rows.slice(ayecLoanerPage * ayecLoanerPageSize, (ayecLoanerPage + 1) * ayecLoanerPageSize);
  const depot = ayecLoanerView === "depot";
  if (!visible.length) {
    host.innerHTML = empty("Kay\u0131t bulunamadi", "Se\u00e7ili g\u00f6r\u00fcn\u00fcm ve filtrelerle e\u015fle\u015fen kay\u0131t bulunamad\u0131.");
    $("#genericCount").textContent = "Toplam 0 kay\u0131t";
    return;
  }
  const head = depot ? ["ID", "Cihaz Tipi", "Marka / Model", "Seri / MAC", "Raf No", "Durum", "G\u00fcnl\u00fck Ceza", "\u0130\u015flemler"] : ["<input type=\"checkbox\" data-loaner-select-all aria-label=\"T\u00fcm\u00fcn\u00fc se\u00e7\" " + (visible.length && visible.every(row => ayecLoanerSelectedIds.has(String(row.id))) ? "checked" : "") + ">", "\u0130\u015eLEM ID / PROTOKOL", "C\u0130HAZ MARKA & MODEL (SER\u0130 NO)", "TESL\u0130M ALAN (M\u00dc\u015eTER\u0130)", "\u0130LG\u0130L\u0130 SERV\u0130S EMR\u0130", "VER\u0130L\u0130\u015e TAR\u0130H\u0130", "BEKLENEN \u0130ADE", "GE\u00c7EN S\u00dcRE", "DURUM / UYARI", "TEM\u0130NAT / KO\u015eUL", "\u0130\u015eLEMLER"];
  const cells = visible.map((row, index) => {
    if (depot) return '<tr><td data-label="ID">' + esc(row.id) + '</td><td data-label="Cihaz Tipi">' + esc(row.device_type || "-") + '</td><td data-label="Marka / Model">' + esc(row.brand_model || "-") + '</td><td data-label="Seri / MAC">' + esc(row.serial_mac || "-") + '</td><td data-label="Raf No">' + esc(row.shelf_no || "-") + '</td><td data-label="Durum"><span class="loaner-ref-status">' + esc(row.status || "Depoda") + '</span></td><td data-label="G\u00fcnl\u00fck Ceza">' + esc(row.daily_penalty_fee || 0) + '</td><td data-label="\u0130\u015flemler"><div class="loaner-ref-actions"><button class="mini" data-loaner-row-action="edit" data-id="' + esc(row.id) + '">D\u00fczenle</button><button class="mini" data-loaner-row-action="assign" data-id="' + esc(row.id) + '">M\u00fc\u015fteriye Ver</button></div></td></tr>';
    const device = ayecLoanerDevices.find(item => String(item.id) === String(row.device_id)) || {};
    const due = row.expected_return ? new Date(row.expected_return) : null;
    const overdueDays = due && !row.date_returned ? Math.max(0, Math.floor((Date.now() - due.getTime()) / 86400000)) : 0;
    const statusLabel = row.date_returned ? "\u0130ADE ED\u0130LD\u0130" : overdueDays ? overdueDays + " G\u00dcN GEC\u0130KMEL\u0130" : String(row.status || "AKTIF / S\u00dcRES\u0130NDE").toLocaleUpperCase("tr-TR");
    const statusClass = row.date_returned ? "returned" : overdueDays ? "overdue" : "active";
    const serial = row.serial_mac || device.serial_mac || "-";
    const model = row.brand_model || device.brand_model || "Cihaz " + String(row.device_id || "");
    const given = row.date_given ? new Date(row.date_given).toLocaleDateString("tr-TR") : "-";
    const returnDate = row.expected_return ? new Date(row.expected_return).toLocaleDateString("tr-TR") : "-";
    return '<tr><td data-label="Se\u00e7"><input type="checkbox" data-loaner-select value="' + esc(row.id) + '" aria-label="Emanet kayd\u0131n\u0131 se\u00e7" ' + (ayecLoanerSelectedIds.has(String(row.id)) ? "checked" : "") + '></td><td data-label="\u0130\u015flem ID / Protokol"><strong class="loaner-ref-code">' + esc(row.tracking_no || ("EMN-" + row.id)) + '</strong><small>Protokol #' + esc(row.id) + '</small></td><td data-label="Cihaz Marka / Model"><strong>' + esc(model) + '</strong><small>SN: ' + esc(serial) + '</small></td><td data-label="Teslim Alan">' + esc(row.customer_name || "-") + '<small>' + esc(row.customer_phone || "") + '</small></td><td data-label="\u0130lgili Servis Emri">' + esc(row.tracking_no || "-") + '<small>' + esc(row.condition_out || "") + '</small></td><td data-label="Verili\u015f Tarihi">' + esc(given) + '</td><td data-label="Beklenen \u0130ade" class="' + (overdueDays ? "loaner-ref-danger" : "") + '">' + esc(returnDate) + '</td><td data-label="Ge\u00e7en S\u00fcre">' + (overdueDays ? overdueDays + " G\u00fcn" : "-" ) + '</td><td data-label="Durum / Uyar\u0131"><span class="loaner-ref-status ' + statusClass + '">' + esc(statusLabel) + '</span></td><td data-label="Teminat / Ko\u015ful">' + (Number(row.penalty_applied || 0) ? esc(money(row.penalty_applied, "TRY")) : "A\u00e7\u0131k Cari") + '<small>' + esc(row.condition_out || "Teslim ko\u015fulu girilmedi") + '</small></td><td data-label="\u0130\u015flemler"><div class="loaner-ref-actions"><button class="mini" data-loaner-row-action="return" data-id="' + esc(row.id) + '" title="\u0130ade al">\u0130ade Al</button><button class="mini" data-loaner-row-action="edit" data-id="' + esc(row.id) + '" title="D\u00fczenle">D\u00fczenle</button><button class="mini" data-loaner-row-action="print" data-id="' + esc(row.id) + '" title="Yazd\u0131r">Yazd\u0131r</button></div></td></tr>';
  }).join("");
  host.innerHTML = '<div class="table-wrap loaner-ref-table-wrap"><table class="loaner-ref-table"><thead><tr>' + head.map(label => '<th>' + label + '</th>').join("") + '</tr></thead><tbody>' + cells + '</tbody></table></div><footer class="loaner-ref-pagination"><span>Toplam ' + rows.length + ' kay\u0131t, ' + (rows.length ? ayecLoanerPage * ayecLoanerPageSize + 1 : 0) + '-' + Math.min(rows.length, (ayecLoanerPage + 1) * ayecLoanerPageSize) + ' aras\u0131 g\u00f6steriliyor</span><div><button type="button" data-loaner-page="-1" ' + (ayecLoanerPage === 0 ? "disabled" : "") + '>\u00d6nceki</button><b>' + (ayecLoanerPage + 1) + ' / ' + pages + '</b><button type="button" data-loaner-page="1" ' + (ayecLoanerPage >= pages - 1 ? "disabled" : "") + '>Sonraki</button></div></footer>';
  $("#genericCount").textContent = "Toplam " + rows.length + " kay\u0131t";
}
document.addEventListener("click", event => {
  const pageButton = event.target.closest("[data-loaner-page]");
  if (pageButton && page === "loaners") { ayecLoanerPage = Math.max(0, ayecLoanerPage + Number(pageButton.dataset.loanerPage)); if (ayecLoanerCurrentData) ayecLoanerRenderRows(ayecLoanerCurrentMeta, ayecLoanerCurrentData, $("#genericSearch")?.value || ""); return; }
  const action = event.target.closest("[data-loaner-row-action]");
  if (!action || page !== "loaners") return;
  const depot = ayecLoanerView === "depot";
  const source = depot ? ayecLoanerDevices : ayecLoanerHistory;
  const row = source.find(item => String(item.id) === String(action.dataset.id));
  if (!row) return;
  const table = depot ? "loaner_devices" : "loaner_transactions";
  if (action.dataset.loanerRowAction === "print") { window.print(); return; }
  if (action.dataset.loanerRowAction === "assign") { apiFetch("/api/desktop/table/loaner_transactions?limit=1").then(data => openGenericDialog({ title: "Yeni Emanet", table: "loaner_transactions" }, { device_id: row.id, status: "Aktif" }, data.columns)).catch(error => toast(error.message, "error")); return; }
  const editRow = action.dataset.loanerRowAction === "return" ? { ...row, date_returned: today(), status: "\u0130ade Edildi" } : row;
  apiFetch("/api/desktop/table/" + table + "?limit=1").then(data => openGenericDialog({ title: action.dataset.loanerRowAction === "return" ? "Emanet \u0130ade Kayd\u0131" : "Emanet Kayd\u0131", table }, editRow, data.columns)).catch(error => toast(error.message, "error"));
});

document.addEventListener("click", event => { if (page === "loaners" && event.target.closest("[data-loaner-action=print-contract]")) window.print(); });

// Part 3: compact logistics tracking view using fields supported by the current schema.
let ayecLogisticsRows = [];
let ayecLogisticsPage = 0;
const ayecGenericShellBeforeLogistics = genericShell;
genericShell = function(meta) {
  if (meta?.table !== "logistics") return ayecGenericShellBeforeLogistics(meta);
  return pageHead("Lojistik & Garanti Y\u00f6netimi", "Kargo ve d\u0131\u015f servis takip kay\u0131tlar\u0131n\u0131 tek ekrandan izleyin.", '<button type="button" class="secondary" data-generic-refresh>Yenile</button><button type="button" class="secondary" data-logistics-print>Toplu Kargo Fi\u015fi</button><button type="button" class="secondary" data-logistics-export>Excel / Rapor</button><button type="button" class="primary" data-generic-add>+ Yeni Takip Ba\u015flat</button>') +
    '<section class="metric-grid logistics-ref-metrics"><article><small>Toplam Kay\u0131t</small><strong id="logisticsMetricTotal">0 Cihaz</strong><footer><span>Garanti Havuzu</span><b>Takipte</b></footer></article><article><small>D\u0131\u015f Serviste (Aktif)</small><strong id="logisticsMetricActive">0 Kargoda</strong><footer><span>Yetkili inceleme</span><b id="logisticsMetricUrgent">0 kay\u0131t</b></footer></article><article><small>Onay Bekleyen</small><strong id="logisticsMetricApproval">0 Fiyat / Onay</strong><footer><span>M\u00fc\u015fteri yan\u0131t\u0131</span><b id="logisticsMetricApprovalValue">\u2014</b></footer></article><article><small>Teslim Al\u0131nan</small><strong id="logisticsMetricDelivered">0 Haz\u0131r</strong><footer><span>Depo kabul</span><b>Kay\u0131tl\u0131</b></footer></article></section>' +
    '<section class="card logistics-ref-filter"><input class="control search" id="logisticsSearch" type="search" placeholder="Kargo takip no, m\u00fc\u015fteri veya yetkili servis ara..."><select class="control" id="logisticsStatus"><option value="all">Durum: T\u00fcm\u00fc</option><option value="active">D\u0131\u015f Serviste</option><option value="approval">Onay Bekliyor</option><option value="delivered">Teslim Al\u0131nd\u0131 / Haz\u0131r</option></select><select class="control" id="logisticsCarrier"><option value="all">Kargo Firmas\u0131: T\u00fcm\u00fc</option></select><input class="control" id="logisticsMonth" type="month" aria-label="G\u00f6nderim ay\u0131"><button type="button" class="secondary" data-logistics-clear>Filtreleri Temizle</button></section>' +
    '<section class="card logistics-ref-table"><div id="logisticsTableHost"></div><footer id="logisticsPagination"></footer></section><input id="genericSearch" type="search" hidden><div id="genericHost" hidden></div><div id="genericCount" hidden></div>';
};
function ayecLogisticsStatus(row) { const status = String(row.status || "").toLocaleLowerCase("tr-TR"); return /teslim|haz\u0131r|tamam|al\u0131nd/i.test(status) ? "delivered" : /onay|fiyat|approval|bekliyor/i.test(status) ? "approval" : "active"; }
function ayecLogisticsMonthMatches(dateValue, month) {
  const value = String(dateValue || "").trim();
  if (!month) return true;
  const isoDate = value.match(/^(\d{4})-(\d{2})/);
  if (isoDate) return isoDate[1] + "-" + isoDate[2] === month;
  const localizedDate = value.match(/^(\d{1,2})[./-](\d{1,2})[./-](\d{4})/);
  return Boolean(localizedDate && localizedDate[3] + "-" + localizedDate[2].padStart(2, "0") === month);
}
function ayecLogisticsRender() {
  const host = $("#logisticsTableHost");
  if (!host) return;
  const query = String($("#logisticsSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
  const status = $("#logisticsStatus")?.value || "all";
  const carrier = $("#logisticsCarrier")?.value || "all";
  const month = $("#logisticsMonth")?.value || "";
  const rows = ayecLogisticsRows.filter(row => {
    const haystack = [row.tracking_no, row.customer_name, row.cargo_firm, row.status, row.type].join(" ").toLocaleLowerCase("tr-TR");
    return (!query || haystack.includes(query)) && (status === "all" || ayecLogisticsStatus(row) === status) && (carrier === "all" || String(row.cargo_firm || "") === carrier) && ayecLogisticsMonthMatches(row.date, month);
  });
  const pageSize = 8;
  const pages = Math.max(1, Math.ceil(rows.length / pageSize));
  ayecLogisticsPage = Math.min(ayecLogisticsPage, pages - 1);
  const visible = rows.slice(ayecLogisticsPage * pageSize, (ayecLogisticsPage + 1) * pageSize);
  const statusText = row => row.status || "Durum belirtilmedi";
  host.innerHTML = visible.length ? '<div class="table-wrap"><table><thead><tr><th>TAK\u0130P NO / \u0130RSAL\u0130YE</th><th>M\u00dc\u015eTER\u0130</th><th>KARGO F\u0130RMASI</th><th>G\u00d6NDER\u0130M TAR\u0130H\u0130</th><th>KARGO TAK\u0130P &amp; DURUM</th><th>Y\u00d6N</th><th>HIZLI \u0130\u015eLEMLER</th></tr></thead><tbody>' + visible.map(row => '<tr><td data-label="Takip No"><strong class="logistics-ref-code">' + esc(row.tracking_no || ("LOG-" + row.id)) + '</strong><small>#' + esc(row.id) + '</small></td><td data-label="M\u00fc\u015fteri">' + esc(row.customer_name || "-") + '</td><td data-label="Kargo Firmas\u0131">' + esc(row.cargo_firm || "-") + '</td><td data-label="G\u00f6nderim Tarihi">' + esc(row.date || "-") + '</td><td data-label="Durum"><span class="logistics-ref-status ' + ayecLogisticsStatus(row) + '">' + esc(statusText(row)) + '</span></td><td data-label="Y\u00f6n">' + esc(row.type || "-") + '</td><td data-label="H\u0131zl\u0131 \u0130\u015flemler"><button type="button" class="mini" data-logistics-edit="' + esc(row.id) + '">D\u00fczenle</button><button type="button" class="mini" data-logistics-print="' + esc(row.id) + '">Fi\u015f</button></td></tr>').join("") + '</tbody></table></div>' : empty("Takip kayd\u0131 bulunamad\u0131", "Filtreleri de\u011fi\u015ftirin veya yeni bir lojistik kayd\u0131 ba\u015flat\u0131n.");
  const pager = $("#logisticsPagination");
  if (pager) pager.innerHTML = '<span>G\u00f6sterilen: ' + (rows.length ? ayecLogisticsPage * pageSize + 1 : 0) + ' - ' + Math.min(rows.length, (ayecLogisticsPage + 1) * pageSize) + ' / ' + rows.length + ' kay\u0131t</span><div><button type="button" data-logistics-page="-1" ' + (ayecLogisticsPage === 0 ? "disabled" : "") + '>\u00d6nceki</button><b>' + (ayecLogisticsPage + 1) + ' / ' + pages + '</b><button type="button" data-logistics-page="1" ' + (ayecLogisticsPage >= pages - 1 ? "disabled" : "") + '>Sonraki</button></div>';
}
const ayecLoadGenericBeforeLogistics = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  await ayecLoadGenericBeforeLogistics(meta, query);
  if (page !== "logistics" || meta?.table !== "logistics" || !window.currentGenericData) return;
  ayecLogisticsRows = window.currentGenericData.rows || [];
  const count = (type) => ayecLogisticsRows.filter(row => ayecLogisticsStatus(row) === type).length;
  $("#logisticsMetricTotal").textContent = ayecLogisticsRows.length + " Kay\u0131t";
  $("#logisticsMetricActive").textContent = count("active") + " Kargoda/Serviste";
  $("#logisticsMetricUrgent").textContent = count("active") + " kay\u0131t";
  $("#logisticsMetricApproval").textContent = count("approval") + " Fiyat / Onay";
  $("#logisticsMetricDelivered").textContent = count("delivered") + " M\u00fc\u015fteriye Haz\u0131r";
  const select = $("#logisticsCarrier");
  if (select) { const selected = select.value; const carriers = [...new Set(ayecLogisticsRows.map(row => row.cargo_firm).filter(Boolean))].sort(); select.innerHTML = '<option value="all">Kargo Firmas\u0131: T\u00fcm\u00fc</option>' + carriers.map(name => '<option value="' + esc(name) + '">' + esc(name) + '</option>').join(""); select.value = carriers.includes(selected) ? selected : "all"; }
  ayecLogisticsRender();
};
document.addEventListener("input", event => { if (page === "logistics" && event.target.id === "logisticsSearch") { ayecLogisticsPage = 0; ayecLogisticsRender(); } });
document.addEventListener("change", event => { if (page === "logistics" && ["logisticsStatus", "logisticsCarrier", "logisticsMonth"].includes(event.target.id)) { ayecLogisticsPage = 0; ayecLogisticsRender(); } });
document.addEventListener("click", event => {
  if (page !== "logistics") return;
  if (event.target.closest("[data-logistics-clear]")) { $("#logisticsSearch").value = ""; $("#logisticsStatus").value = "all"; $("#logisticsCarrier").value = "all"; $("#logisticsMonth").value = ""; ayecLogisticsRender(); return; }
  const pager = event.target.closest("[data-logistics-page]");
  if (pager) { ayecLogisticsPage = Math.max(0, ayecLogisticsPage + Number(pager.dataset.logisticsPage)); ayecLogisticsRender(); return; }
  const edit = event.target.closest("[data-logistics-edit]");
  if (edit) { const row = ayecLogisticsRows.find(item => String(item.id) === edit.dataset.logisticsEdit); if (row) apiFetch("/api/desktop/table/logistics?limit=1").then(data => openGenericDialog(genericModules.logistics, row, data.columns)).catch(error => toast(error.message, "error")); return; }
  if (event.target.closest("[data-logistics-print], [data-logistics-print-all]")) window.print();
  if (event.target.closest("[data-logistics-export]")) download("lojistik-takip-" + today() + ".csv", ayecLogisticsRows);
});
const ayecRenderBeforeLogistics = render;
render = function() {
  ayecRenderBeforeLogistics();
  if (page !== "logistics") return;
  const add = $("[data-generic-add]");
  if (add) add.onclick = async () => { try { const data = await apiFetch("/api/desktop/table/logistics?limit=1"); openGenericDialog(genericModules.logistics, {}, data.columns); } catch (error) { toast(error.message, "error"); } };
};

// Part 3: service reporting view mapped to fields available in the service register.
let ayecJobReportRows = [];
let ayecJobReportTab = "jobs";
let ayecJobReportPage = 0;
const ayecGenericShellBeforeJobReports = genericShell;
genericShell = function(meta) {
  if (page !== "job-reports" || meta?.table !== "devices") return ayecGenericShellBeforeJobReports(meta);
  return '<div class="job-report-heading"><div><small>TEKN\u0130K SERV\u0130S MODU / OPERASYONEL RAPORLAR</small><h2>\u0130\u015f / Servis Takibi Raporlar\u0131</h2><p>Teknik servis kay\u0131tlar\u0131n\u0131 ve mevcut i\u015f emri durumlar\u0131n\u0131 inceleyin.</p></div><div class="actions"><label class="job-report-date"><input id="jobReportStart" type="date" aria-label="Ba\u015flang\u0131\u00e7 tarihi"><span>-</span><input id="jobReportEnd" type="date" aria-label="Biti\u015f tarihi"></label><button type="button" class="secondary" data-job-report-export>Excel \u00c7\u0131kt\u0131s\u0131</button><button type="button" class="secondary" data-job-report-print>PDF / Yazd\u0131r</button><button type="button" class="primary" data-generic-refresh>Raporu Yenile</button></div></div>' +
    '<section class="metric-grid job-report-metrics"><article><small>TOPLAM \u0130\u015eLER</small><strong id="jobReportTotal">0</strong><footer>Filtrelenen servis kay\u0131tlar\u0131</footer></article><article><small>A\u00c7IK \u0130\u015eLER</small><strong id="jobReportOpen">0</strong><footer>\u0130\u015flemde ve beklemede</footer></article><article><small>TAMAMLANAN / TESL\u0130M</small><strong id="jobReportDelivered">0</strong><footer>Tamamlanan servisler</footer></article><article><small>TOPLAM SERV\u0130S</small><strong id="jobReportServiceCount">0</strong><footer>At\u00f6lye ve saha kay\u0131tlar\u0131</footer></article><article><small>KAYITLI SERV\u0130S BEDEL\u0130</small><strong id="jobReportValue">0</strong><footer>TRY cinsinden kay\u0131t tutar\u0131</footer></article></section>' +
    '<section class="card job-report-panel"><div class="job-report-toolbar"><nav class="job-report-tabs" aria-label="Servis raporu g\u00f6r\u00fcn\u00fcmleri"><button type="button" data-job-report-tab="jobs">\u0130\u015f Takip Raporu</button><button type="button" data-job-report-tab="service">Servis Takip</button><button type="button" data-job-report-tab="technicians">Teknisyen Matrisi</button><button type="button" data-job-report-tab="profit">K\u00e2rl\u0131l\u0131k</button></nav><div class="job-report-search"><input class="control search" id="genericSearch" placeholder="\u0130\u015f no, m\u00fc\u015fteri, a\u00e7\u0131klama veya durum ara"><button type="button" class="secondary" data-job-report-clear>Temizle</button></div></div><div class="job-report-filters"><label>Durum<select class="control" id="jobReportStatus"><option value="all">T\u00fcm Durumlar</option><option value="open">A\u00e7\u0131k / \u0130\u015flemde</option><option value="done">Tamamland\u0131 / Teslim</option></select></label><label>Para Birimi<select class="control" id="jobReportCurrency"><option value="TRY">TRY (\u20ba)</option><option value="all">T\u00fcm Birimler</option></select></label><label>Kay\u0131t Say\u0131s\u0131<select class="control" id="jobReportPageSize"><option value="7">7</option><option value="15">15</option><option value="30">30</option></select></label><span id="jobReportCount" class="muted"></span></div><div id="jobReportHost"></div><footer class="job-report-summary"><article><small>ORTALAMA SERV\u0130S S\u00dcRES\u0130</small><strong>Kay\u0131t verisi yok</strong><span>Servis s\u00fcresi alan\u0131 bulunmuyor.</span></article><article><small>M\u00dc\u015eTER\u0130 MEMNUN\u0130YET SKORU</small><strong>\u2014</strong><span>De\u011ferlendirme verisi yok</span></article><article><small>\u0130LK SEFERDE \u00c7\u00d6Z\u00dcM ORANI</small><strong>\u2014</strong><span>Tekrar servis ba\u011flant\u0131s\u0131 bulunmuyor</span></article></footer><div id="genericHost" hidden></div><div id="genericCount" hidden></div></section>';
};
function ayecJobStatus(row) { const value = String(row.status || "").toLocaleLowerCase("tr-TR"); return /teslim|tamam|kapal|iptal|cancel/i.test(value) ? "done" : "open"; }
function ayecJobDateKey(row) { const raw = String(row.entry_date || "").trim(); if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10); const match = raw.match(/^(\d{2})[./](\d{2})[./](\d{4})/); return match ? match[3] + "-" + match[2] + "-" + match[1] : ""; }
function ayecJobReportRender() {
  const host = $("#jobReportHost");
  if (!host) return;
  const query = String($("#genericSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
  const status = $("#jobReportStatus")?.value || "all";
  const start = $("#jobReportStart")?.value || "";
  const end = $("#jobReportEnd")?.value || "";
  let rows = ayecJobReportRows.filter(row => {
    const searchText = [row.tracking_no, row.customer_name, row.device_brand, row.device_model, row.fault_description, row.status].join(" ").toLocaleLowerCase("tr-TR");
    const date = ayecJobDateKey(row);
    return (!query || searchText.includes(query)) && (status === "all" || ayecJobStatus(row) === status) && (!start || !date || date >= start) && (!end || !date || date <= end);
  });
  if (ayecJobReportTab === "service") rows = rows.filter(row => ayecJobStatus(row) === "open");
  if (ayecJobReportTab === "technicians") rows = rows.filter(row => row.technician_name || row.assigned_technician || row.technician);
  if (ayecJobReportTab === "profit") rows = rows.filter(row => Number.isFinite(Number(row.price)) && Number(row.price) > 0);
  const size = Number($("#jobReportPageSize")?.value || 7);
  const pages = Math.max(1, Math.ceil(rows.length / size));
  ayecJobReportPage = Math.min(ayecJobReportPage, pages - 1);
  const visible = rows.slice(ayecJobReportPage * size, (ayecJobReportPage + 1) * size);
  host.innerHTML = visible.length ? '<div class="table-wrap job-report-table-wrap"><table class="job-report-table"><thead><tr><th>\u0130\u015e NO</th><th>M\u00dc\u015eTER\u0130 / KURUM</th><th>TEKN\u0130SYEN</th><th>A\u00c7IKLAMA / YAPILAN \u0130\u015eLEM</th><th>DURUM</th><th>TUTAR</th><th>B\u0130R\u0130M</th><th>TAR\u0130H</th></tr></thead><tbody>' + visible.map(row => '<tr><td data-label="\u0130\u015f No"><strong class="job-report-code">' + esc(row.tracking_no || ("SRV-" + row.id)) + '</strong></td><td data-label="M\u00fc\u015fteri / Kurum"><strong>' + esc(row.customer_name || "-") + '</strong><small>' + esc(row.customer_type || "") + '</small></td><td data-label="Teknisyen">' + esc(row.technician_name || row.assigned_technician || row.technician || "-") + '</td><td data-label="A\u00e7\u0131klama / Yap\u0131lan \u0130\u015flem">' + esc(row.fault_description || row.fault_category || "-") + '<small>' + esc([row.device_brand, row.device_model].filter(Boolean).join(" ")) + '</small></td><td data-label="Durum"><span class="job-report-status ' + ayecJobStatus(row) + '">' + esc(row.status || "Belirtilmedi") + '</span></td><td data-label="Tutar">' + esc(moneyNumber(row.price).toLocaleString("tr-TR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })) + '</td><td data-label="Birim">TRY (\u20ba)</td><td data-label="Tarih">' + esc(ayecJobDateKey(row).split("-").reverse().join(".") || row.entry_date || "-") + '</td></tr>').join("") + '</tbody></table></div>' : ayecJobReportTab === "technicians" ? empty("Teknisyen verisi bulunamad\u0131", "Servis kay\u0131tlar\u0131nda teknisyen alan\u0131 mevcut de\u011fil.") : ayecJobReportTab === "profit" ? empty("Maliyet verisi bulunamad\u0131", "Net k\u00e2rl\u0131l\u0131k i\u00e7in maliyet verisi gerekir.") : empty("Servis kayd\u0131 bulunamad\u0131", "Arama veya filtreleri de\u011fi\u015ftirin.");
  $("#jobReportCount").textContent = "G\u00f6r\u00fcnt\u00fclenen " + rows.length + " / " + ayecJobReportRows.length + " kay\u0131t";
  const pageFoot = document.createElement("footer"); pageFoot.className = "job-report-pagination"; pageFoot.innerHTML = '<span>Se\u00e7ilen: 0 sat\u0131r</span><div><button type="button" data-job-report-page="-1" ' + (ayecJobReportPage === 0 ? "disabled" : "") + '>\u00d6nceki</button><b>' + (ayecJobReportPage + 1) + ' / ' + pages + '</b><button type="button" data-job-report-page="1" ' + (ayecJobReportPage >= pages - 1 ? "disabled" : "") + '>Sonraki</button></div>';
  if (visible.length) host.append(pageFoot);
}
const ayecLoadGenericBeforeJobReports = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  await ayecLoadGenericBeforeJobReports(meta, query);
  if (page !== "job-reports" || meta?.table !== "devices" || !window.currentGenericData) return;
  ayecJobReportRows = window.currentGenericData.rows || [];
  const rows = ayecJobReportRows;
  const closed = rows.filter(row => ayecJobStatus(row) === "done").length;
  $("#jobReportTotal").textContent = String(rows.length);
  $("#jobReportOpen").textContent = String(rows.length - closed);
  $("#jobReportDelivered").textContent = String(closed);
  $("#jobReportServiceCount").textContent = String(rows.length);
  $("#jobReportValue").textContent = money(rows.reduce((sum, row) => sum + moneyNumber(row.price), 0), "TRY");
  ayecJobReportRender();
};
document.addEventListener("click", event => {
  if (page !== "job-reports") return;
  const tab = event.target.closest("[data-job-report-tab]");
  if (tab) { ayecJobReportTab = tab.dataset.jobReportTab; ayecJobReportPage = 0; document.querySelectorAll("[data-job-report-tab]").forEach(button => button.classList.toggle("active", button === tab)); ayecJobReportRender(); return; }
  const pager = event.target.closest("[data-job-report-page]");
  if (pager) { ayecJobReportPage = Math.max(0, ayecJobReportPage + Number(pager.dataset.jobReportPage)); ayecJobReportRender(); return; }
  if (event.target.closest("[data-job-report-export]")) { download("servis-raporu-" + today() + ".csv", ayecJobReportRows); return; }
  if (event.target.closest("[data-job-report-print]")) { window.print(); return; }
  if (event.target.closest("[data-job-report-clear]")) { $("#genericSearch").value = ""; $("#jobReportStatus").value = "all"; $("#jobReportStart").value = ""; $("#jobReportEnd").value = ""; ayecJobReportRender(); }
});
document.addEventListener("input", event => { if (page === "job-reports" && ["genericSearch", "jobReportStart", "jobReportEnd"].includes(event.target.id)) { ayecJobReportPage = 0; ayecJobReportRender(); } });
document.addEventListener("change", event => { if (page === "job-reports" && ["jobReportStatus", "jobReportPageSize"].includes(event.target.id)) { ayecJobReportPage = 0; ayecJobReportRender(); } });
const ayecRenderBeforeJobReports = render;
render = function() { ayecRenderBeforeJobReports(); if (page === "job-reports") { ayecJobReportTab = "jobs"; ayecJobReportPage = 0; document.querySelectorAll("[data-job-report-tab]").forEach(button => button.classList.toggle("active", button.dataset.jobReportTab === ayecJobReportTab)); } };

// Part 4: a full-width service status wall without the assistant side panel.
let ayecStatusRows = [];
let ayecStatusFilter = "all";
let ayecStatusCriticalOnly = false;
let ayecStatusRefreshTimer = null;
let ayecStatusRefreshSeconds = 29;
let ayecStatusPage = 0;
const ayecGenericShellBeforeStatus = genericShell;
genericShell = function(meta) {
  if (page !== "service-status" || meta?.table !== "devices") return ayecGenericShellBeforeStatus(meta);
  return pageHead("Durum Paneli <span class=\"badge status-wall-live\">CANLI AK\u0130\u015e (30S OTOMAT\u0130K YEN\u0130LEME)</span>", "At\u00f6lye ve saha servis operasyonlar\u0131n\u0131n anl\u0131k hareket ak\u0131\u015f\u0131, cihaz teslimat durumlar\u0131 ve AI asistan bildirimleri", '<span class="status-wall-refresh-count" id="statusWallRefreshCount">29s</span><button type="button" class="primary" data-status-share>Ekran\u0131 Yay\u0131nla (TV / Duvar Modu)</button><button type="button" class="secondary" data-generic-refresh>Yenile</button><button type="button" class="secondary" aria-pressed="false" data-status-critical>Filtrele</button><button type="button" class="secondary" data-status-export>D\u0131\u015fa Aktar</button><span class="status-wall-action-hint">Canl\u0131 servis hareketleri ve par\u00e7a uyar\u0131lar\u0131</span><button type="button" class="secondary" data-status-help>Yard\u0131m</button>') +
    '<section class="metric-grid status-wall-metrics"><article><small>BUG\u00dcNK\u00dc \u0130\u015eLEM HACM\u0130</small><strong id="statusWallTotal">0 Cihaz</strong><footer><span id="statusWallClosed">0 Teslim</span><span id="statusWallActive">0 \u0130\u015flemde</span></footer></article><article><small>A\u00c7IK \u0130\u015e ORANI</small><strong id="statusWallOccupancy">%0</strong><footer><span>Kay\u0131tl\u0131 i\u015fler i\u00e7inde</span><b id="statusWallCapacity">0 / 0 A\u00e7\u0131k</b></footer></article><article><small>KR\u0130T\u0130K \u0130\u015e &amp; PAR\u00c7A UYARISI</small><strong id="statusWallCritical">0 Kritik \u0130\u015f</strong><footer><span>Y\u00fcksek \u00f6ncelik</span><b id="statusWallParts">0 par\u00e7a bekliyor</b></footer></article><article><small>ORTALAMA TAM\u0130R S\u00dcRES\u0130</small><strong id="statusWallDuration">\u2014</strong><footer><span>SLA hedef bilgisi</span><b>Kay\u0131t verisi yok</b></footer></article></section>' +
    '<section class="status-wall-layout"><div class="status-wall-main"><div class="card status-wall-list"><header><h3>Son Servis Hareketleri</h3><nav><button type="button" class="active" data-status-filter="all">T\u00fcm\u00fc</button><button type="button" data-status-filter="done">Teslim</button><button type="button" data-status-filter="parts">Par\u00e7a Bekleyen</button><button type="button" data-status-filter="open">\u0130\u015flemde</button></nav></header><div class="status-wall-toolbar"><input class="control search" id="genericSearch" placeholder="\u0130\u015f emri no, m\u00fc\u015fteri veya seri no ara..."><select class="control" id="statusWallSort"><option value="date">Kabul Tarihi (En Yeni)</option><option value="priority">\u00d6ncelik (Y\u00fcksek)</option></select></div><div id="statusWallHost"></div></div></div></section><div id="genericHost" hidden></div><div id="genericCount" hidden></div>';
};
function ayecStatusKind(row) { const value = String(row.status || "").toLocaleLowerCase("tr-TR"); if (/teslim|tamam|kapal|iptal|cancel/i.test(value)) return "done"; if (/par\u00e7a|yedek|malzeme/i.test(value)) return "parts"; return "open"; }
function ayecStatusRender() {
  const host = $("#statusWallHost"); if (!host) return;
  const query = String($("#genericSearch")?.value || "").trim().toLocaleLowerCase("tr-TR");
  const sort = $("#statusWallSort")?.value || "date";
  let rows = ayecStatusRows.filter(row => { const status = String(row.status || "").toLocaleLowerCase("tr-TR"); const urgency = String(row.urgency || "").toLocaleLowerCase("tr-TR"); const critical = /par\u00e7a|bekliyor|acil|kritik/.test(status + " " + urgency); return (!query || [row.tracking_no, row.customer_name, row.device_brand, row.device_model, row.serial_no, row.status].join(" ").toLocaleLowerCase("tr-TR").includes(query)) && (ayecStatusFilter === "all" || ayecStatusKind(row) === ayecStatusFilter) && (!ayecStatusCriticalOnly || critical); });
  rows.sort((a, b) => sort === "priority" ? String(b.urgency || "").localeCompare(String(a.urgency || "")) : String(b.entry_date || "").localeCompare(String(a.entry_date || "")));
  const size = Math.max(6, Math.min(14, Math.floor((window.innerHeight - 390) / 54))), pages = Math.max(1, Math.ceil(rows.length / size)); ayecStatusPage = Math.min(ayecStatusPage, pages - 1);
  const visible = rows.slice(ayecStatusPage * size, (ayecStatusPage + 1) * size);
  host.innerHTML = visible.length ? '<div class="table-wrap status-wall-table-wrap"><table class="status-wall-table"><thead><tr><th>TAK\u0130P NO</th><th>M\u00dc\u015eTER\u0130</th><th>C\u0130HAZ / MODEL</th><th>DURUM</th><th>G\u0130R\u0130\u015e</th><th>TESL\u0130M</th><th>\u00d6NCEL\u0130K</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>' + visible.map(row => '<tr><td data-label="Takip No"><strong class="status-wall-code">' + esc(row.tracking_no || ("SRV-" + row.id)) + '</strong></td><td data-label="M\u00fc\u015fteri">' + esc(row.customer_name || "-") + '</td><td data-label="Cihaz / Model">' + esc([row.device_brand, row.device_model].filter(Boolean).join(" ") || row.device_type || "-") + '<small>' + esc(row.serial_no || "") + '</small></td><td data-label="Durum"><span class="status-wall-badge ' + ayecStatusKind(row) + '">' + esc(row.status || "Belirtilmedi") + '</span></td><td data-label="Giri\u015f">' + esc(row.entry_date || "-") + '</td><td data-label="Teslim">' + esc(row.estimated_date || "-") + '</td><td data-label="\u00d6ncelik">' + esc(row.urgency || "Normal") + '</td><td data-label="\u0130\u015flemler"><button type="button" class="mini" data-status-edit="' + esc(row.id) + '">A\u00e7</button></td></tr>').join("") + '</tbody></table></div><footer class="status-wall-pager"><span>G\u00f6sterilen ' + Math.min(rows.length, size) + ' / ' + rows.length + ' kay\u0131t</span><div><button type="button" data-status-page="-1" ' + (ayecStatusPage === 0 ? "disabled" : "") + '>\u00d6nceki</button><b>' + (ayecStatusPage + 1) + ' / ' + pages + '</b><button type="button" data-status-page="1" ' + (ayecStatusPage >= pages - 1 ? "disabled" : "") + '>Sonraki</button></div></footer>' : empty("Servis kayd\u0131 bulunamad\u0131", "Arama veya durum filtresini de\u011fi\u015ftirin.");
  $("#genericCount").textContent = rows.length + " kay\u0131t";
}
function ayecRenderStatusWallPersonnel() {
  const host = $("#statusWallTechnicians");
  if (!host) return;
  const people = (desktopPersonnel || []).filter(person => !person.role || /tekn|servis|usta|yonet/i.test(`${person.role} ${person.department || ""}`)).slice(0, 3);
  host.innerHTML = people.length ? people.map(person => `<article>${esc(person.name || "-")}<small>${esc(person.role || "Teknisyen")} | ${esc(person.status || "Durum bildirilmemi\u015f")}</small></article>`).join("") : '<p class="muted">Teknisyen kayd\u0131 bulunmuyor veya okunamad\u0131.</p>';
}
const ayecLoadGenericBeforeStatus = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  await ayecLoadGenericBeforeStatus(meta, query);
  if (page !== "service-status" || meta?.table !== "devices" || !window.currentGenericData) return;
  ayecStatusRows = window.currentGenericData.rows || [];
  const count = kind => ayecStatusRows.filter(row => ayecStatusKind(row) === kind).length;
  const open = count("open"), done = count("done"), parts = count("parts"), total = ayecStatusRows.length;
  $("#statusWallTotal").textContent = total + " Cihaz"; $("#statusWallClosed").textContent = done + " Teslim"; $("#statusWallActive").textContent = open + " \u0130\u015flemde";
  $("#statusWallOccupancy").textContent = "%" + (total ? Math.round(open * 100 / total) : 0); $("#statusWallCapacity").textContent = open + " / " + total + " A\u00e7\u0131k";
  const critical = ayecStatusRows.filter(row => /acil|kritik|y\u00fcksek/i.test(String(row.urgency || "")) || ayecStatusKind(row) === "parts").length;
  $("#statusWallCritical").textContent = critical + " Kritik \u0130\u015f"; $("#statusWallParts").textContent = parts + " par\u00e7a bekliyor"; $("#statusWallDuration").textContent = "\u2014";
  ayecStatusRender();
};
document.addEventListener("click", event => {
  if (page !== "service-status") return;
  const filter = event.target.closest("[data-status-filter]");
  if (filter) { ayecStatusFilter = filter.dataset.statusFilter; document.querySelectorAll("[data-status-filter]").forEach(button => button.classList.toggle("active", button === filter)); ayecStatusPage = 0; ayecStatusRender(); return; }
  const pager = event.target.closest("[data-status-page]"); if (pager) { ayecStatusPage = Math.max(0, ayecStatusPage + Number(pager.dataset.statusPage)); ayecStatusRender(); return; }
  if (event.target.closest("[data-status-personnel]")) { navigate("technician"); return; }
  const critical = event.target.closest("[data-status-critical]"); if (critical) { ayecStatusCriticalOnly = !ayecStatusCriticalOnly; critical.setAttribute("aria-pressed", String(ayecStatusCriticalOnly)); critical.classList.toggle("active", ayecStatusCriticalOnly); ayecStatusPage = 0; ayecStatusRender(); return; }
  if (event.target.closest("[data-status-help]")) { toast("Durum panelinde filtreleri kullanarak acil ve par\u00e7a bekleyen servisleri gor\u00fcnt\u00fcleyin.", "info"); return; }
  if (event.target.closest("[data-status-share]")) { const share = { title: "AYEC Pro - Durum Paneli", text: "Canl\u0131 servis durumu", url: window.location.href }; if (navigator.share) navigator.share(share).catch(() => {}); else if (navigator.clipboard) navigator.clipboard.writeText(share.url).then(() => toast("Durum paneli ba\u011flant\u0131s\u0131 kopyaland\u0131.", "success")).catch(() => toast(share.url, "info")); else toast(share.url, "info"); return; }
  const edit = event.target.closest("[data-status-edit]"); if (edit) { const row = ayecStatusRows.find(item => String(item.id) === edit.dataset.statusEdit); if (row) apiFetch("/api/desktop/table/devices?limit=1").then(data => openGenericDialog(genericModules["service-status"], row, data.columns)).catch(error => toast(error.message, "error")); return; }
  if (event.target.closest("[data-status-export]")) download("durum-paneli-" + today() + ".csv", ayecStatusRows);
});
document.addEventListener("input", event => { if (page === "service-status" && event.target.id === "genericSearch") { ayecStatusPage = 0; ayecStatusRender(); } });
document.addEventListener("change", event => { if (page === "service-status" && event.target.id === "statusWallSort") { ayecStatusPage = 0; ayecStatusRender(); } });
const ayecRenderBeforeStatusWall = render;
render = function() { ayecRenderBeforeStatusWall(); if (page === "service-status") { ayecStatusFilter = "all"; ayecStatusCriticalOnly = false; ayecStatusPage = 0; document.querySelectorAll("[data-status-filter]").forEach(button => button.classList.toggle("active", button.dataset.statusFilter === ayecStatusFilter)); if (!ayecStatusRefreshTimer) { ayecStatusRefreshSeconds = 29; ayecStatusRefreshTimer = setInterval(() => { if (page !== "service-status") { clearInterval(ayecStatusRefreshTimer); ayecStatusRefreshTimer = null; return; } ayecStatusRefreshSeconds = ayecStatusRefreshSeconds <= 1 ? 30 : ayecStatusRefreshSeconds - 1; const counter = $("#statusWallRefreshCount"); if (counter) counter.textContent = ayecStatusRefreshSeconds + "s"; if (ayecStatusRefreshSeconds === 30 && genericModules["service-status"]) loadGenericModule(genericModules["service-status"]).catch(() => {}); }, 1000); } } else if (ayecStatusRefreshTimer) { clearInterval(ayecStatusRefreshTimer); ayecStatusRefreshTimer = null; } };


// Part 4: field operations view uses appointment records and marks missing GPS data clearly.
let ayecFieldRows = [];
const ayecGenericShellBeforeFieldMap = genericShell;
genericShell = function(meta) {
  if (page !== "field-service" || meta?.table !== "appointments") return ayecGenericShellBeforeFieldMap(meta);
  return pageHead("Saha Haritas\u0131 & G\u00f6rev Takibi", "Randevu ve saha i\u015flerini tek ekranda izleyin.", '<button type="button" class="secondary" data-generic-refresh>Yenile</button><button type="button" class="secondary" data-field-export>Excel / Rapor</button><button type="button" class="primary" data-generic-add>+ Yeni Saha G\u00f6revi</button>') +
    '<section class="metric-grid field-map-metrics"><article><small>BUG\u00dcNK\u00dc SAHA G\u00d6REVLER\u0130</small><strong id="fieldMapTotal">0</strong><footer>Takvime kay\u0131tl\u0131</footer></article><article><small>BEKLEYEN</small><strong id="fieldMapPending">0</strong><footer>Planlanan g\u00f6revler</footer></article><article><small>TAMAMLANAN</small><strong id="fieldMapDone">0</strong><footer>Kay\u0131tl\u0131 tamamlanma durumu</footer></article><article><small>CANLI KONUM</small><strong>Yok</strong><footer>GPS telemetrisi ba\u011fl\u0131 de\u011fil</footer></article></section>' +
    '<section class="field-map-layout"><article class="card field-map-canvas"><header><div><b>SAHA G\u00d6REV HAR\u0130TASI</b><small>Konum verisi kaynak kay\u0131tlar\u0131nda bulunmuyor</small></div><span class="field-map-offline"><i></i>GPS BA\u011eLI DE\u011e\u0130L</span></header><div class="field-map-empty"><span aria-hidden="true">\u2316</span><h3>Canl\u0131 konum verisi yok</h3><p>Harita i\u015faretleri yaln\u0131zca ger\u00e7ek GPS koordinatlar\u0131 kaydedildi\u011finde g\u00f6sterilir. Randevular ve g\u00f6revler sa\u011f panelde listelenir.</p></div><footer><span>Koordinat kayd\u0131 olmadan konum g\u00f6sterilmez.</span><button type="button" class="secondary" data-page="settings">Konum ayarlar\u0131</button></footer></article><aside class="card field-map-queue"><header><h3>Saha G\u00f6revleri</h3><b id="fieldMapCount">0</b></header><div class="field-map-search"><input id="genericSearch" class="control search" type="search" placeholder="M\u00fc\u015fteri veya i\u015f ara..."><select class="control" id="fieldMapStatus"><option value="all">T\u00fcm Durumlar</option><option value="pending">Bekleyen</option><option value="done">Tamamlanan</option></select></div><div id="fieldMapRows"></div><div id="genericHost" hidden></div><div id="genericCount" hidden></div></aside></section>';
};
function ayecFieldIsDone(row) { return /tamam|teslim|iptal|bitti/i.test(String(row.status || "")); }
function ayecFieldRender() {
  const host = $("#fieldMapRows"); if (!host) return;
  const query = String($("#genericSearch")?.value || "").trim().toLocaleLowerCase("tr-TR"), status = $("#fieldMapStatus")?.value || "all";
  const rows = ayecFieldRows.filter(row => (!query || [row.customer_name, row.title, row.description, row.phone].join(" ").toLocaleLowerCase("tr-TR").includes(query)) && (status === "all" || (status === "done") === ayecFieldIsDone(row)));
  $("#fieldMapCount").textContent = rows.length;
  host.innerHTML = rows.length ? rows.slice(0, 30).map(row => '<button type="button" class="field-map-job" data-field-edit="' + esc(row.id) + '"><span class="field-map-job-icon">' + (ayecFieldIsDone(row) ? '\u2713' : '\u2316') + '</span><span><b>' + esc(row.customer_name || "M\u00fc\u015fteri belirtilmedi") + '</b><small>' + esc(row.title || row.description || "Saha randevusu") + '</small><small>' + esc([row.date, row.time].filter(Boolean).join(" ") || "Tarih belirtilmedi") + '</small></span><em class="' + (ayecFieldIsDone(row) ? "done" : "pending") + '">' + esc(row.status || "Bekliyor") + '</em></button>').join("") : empty("Saha g\u00f6revi bulunamad\u0131", "Arama veya durum filtresini de\u011fi\u015ftirin.");
}
const ayecLoadGenericBeforeFieldMap = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  await ayecLoadGenericBeforeFieldMap(meta, query);
  if (page !== "field-service" || meta?.table !== "appointments" || !window.currentGenericData) return;
  ayecFieldRows = window.currentGenericData.rows || [];
  const done = ayecFieldRows.filter(ayecFieldIsDone).length;
  $("#fieldMapTotal").textContent = ayecFieldRows.length; $("#fieldMapPending").textContent = ayecFieldRows.length - done; $("#fieldMapDone").textContent = done;
  ayecFieldRender();
};
document.addEventListener("input", event => { if (page === "field-service" && event.target.id === "genericSearch") ayecFieldRender(); });
document.addEventListener("change", event => { if (page === "field-service" && event.target.id === "fieldMapStatus") ayecFieldRender(); });
document.addEventListener("click", event => {
  if (page !== "field-service") return;
  const item = event.target.closest("[data-field-edit]");
  if (item) { const row = ayecFieldRows.find(current => String(current.id) === item.dataset.fieldEdit); if (row) apiFetch("/api/desktop/table/appointments?limit=1").then(data => openGenericDialog(genericModules["field-service"], row, data.columns)).catch(error => toast(error.message, "error")); return; }
  if (event.target.closest("[data-field-export]")) download("saha-gorevleri-" + today() + ".csv", ayecFieldRows);
});

let ayecPersonnelSelectedId = "";
const genericShellBeforePersonnel = genericShell;
genericShell = function(meta) {
  if (page !== "personnel" || meta?.table !== "personnel") return genericShellBeforePersonnel(meta);
  return `${pageHead("Personel &amp; Bordro Merkezi", "Personel kartlar\u0131n\u0131 ve kay\u0131tl\u0131 \u00fccret bilgilerini tek ekranda y\u00f6netin.", '<button class="secondary" data-personnel-export>CSV D\u0131\u015fa Aktar</button><button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-generic-add>+ Yeni Personel Kayd\u0131</button>')}<section class="personnel-ref-metrics"><article><small>AKT\u0130F PERSONEL</small><strong id="personnelActiveCount">0</strong><span>Personel kay\u0131tlar\u0131</span></article><article><small>TOPLAM AYLIK MAA\u015e</small><strong id="personnelSalaryTotal">0</strong><span>Kaydedilmi\u015f maa\u015f alanlar\u0131</span></article><article><small>KAYITLI PR\u0130M</small><strong id="personnelCommissionTotal">0</strong><span>Personel kartlar\u0131ndaki prim de\u011ferleri</span></article><article><small>DEPARTMAN</small><strong id="personnelDepartmentCount">0</strong><span>Farkl\u0131 kay\u0131tl\u0131 birimler</span></article></section><section class="personnel-ref-layout"><article class="card personnel-ref-list"><header><div><h3>Personel Kadrosu &amp; Bordro</h3><p class="muted">Arama, rol filtresi ve personel kart\u0131</p></div><span class="badge" id="personnelResultCount">0 kay\u0131t</span></header><div class="personnel-ref-toolbar"><input class="control search" id="genericSearch" placeholder="Personel ad\u0131, sicil veya departman ara..."><select class="control" id="personnelRoleFilter"><option value="">T\u00fcm Roller</option></select></div><div class="table-wrap"><table><thead><tr><th>PERSONEL</th><th>UNVAN &amp; \u0130STASYON</th><th>DURUM</th><th>AYLIK MAA\u015e</th><th>PR\u0130M</th><th>AKS\u0130YON</th></tr></thead><tbody id="personnelRows"></tbody></table></div><div class="personnel-ref-count" id="genericCount" hidden></div></article><aside class="card personnel-ref-profile" id="personnelProfile"></aside></section>`;
};
const loadGenericModuleBeforePersonnel = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  if (page !== "personnel" || meta?.table !== "personnel") return loadGenericModuleBeforePersonnel(meta, query);
  const host = $("#personnelRows");
  if (!host) return;
  try {
    const data = await apiFetch(`/api/desktop/table/personnel?limit=500&q=${encodeURIComponent(query)}`);
    window.currentGenericData = data; window.currentGenericMeta = meta;
    const rows = data.rows || [], roles = [...new Set(rows.map(row => String(row.role || row.department || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "tr"));
    const roleFilter = $("#personnelRoleFilter"), selectedRole = roleFilter?.value || "";
    if (roleFilter) roleFilter.innerHTML = '<option value="">T\u00fcm Roller</option>' + roles.map(role => `<option value="${esc(role)}" ${role === selectedRole ? "selected" : ""}>${esc(role)}</option>`).join("");
    const activeRows = rows.filter(row => row.active == null || Number(row.active) !== 0), salary = activeRows.reduce((sum, row) => sum + (Number(row.salary) || 0), 0), commission = activeRows.reduce((sum, row) => sum + (Number(row.commission) || 0), 0), departments = new Set(activeRows.map(row => String(row.department || "").trim()).filter(Boolean));
    $("#personnelActiveCount").textContent = String(activeRows.length); $("#personnelSalaryTotal").textContent = money(salary, "TRY"); $("#personnelCommissionTotal").textContent = money(commission, "TRY"); $("#personnelDepartmentCount").textContent = String(departments.size); $("#personnelResultCount").textContent = `${rows.length} kay\u0131t`;
    const visible = rows.filter(row => !selectedRole || String(row.role || row.department || "") === selectedRole);
    host.innerHTML = visible.map((row, index) => `<tr class="personnel-ref-row ${String(row.id) === ayecPersonnelSelectedId ? "selected" : ""}" data-personnel-id="${esc(row.id)}"><td><strong>${esc(row.name || "-")}</strong><small>${esc(row.email || row.phone || "\u0130leti\u015fim bilgisi yok")}</small></td><td><strong>${esc(row.role || "-")}</strong><small>${esc(row.department || "Birim belirtilmedi")}</small></td><td><span class="badge ${row.active == null || Number(row.active) !== 0 ? "success" : "muted"}">${row.active == null || Number(row.active) !== 0 ? "Aktif" : "Pasif"}</span></td><td>${row.salary == null ? "-" : money(Number(row.salary) || 0, "TRY")}</td><td>${row.commission == null ? "-" : money(Number(row.commission) || 0, "TRY")}</td><td><button class="mini generic-edit" data-index="${index}">D\u00fczenle</button></td></tr>`).join("") || `<tr><td colspan="6">${empty("Personel bulunamad\u0131", "Arama veya rol filtresini de\u011fi\u015ftirebilirsiniz.")}</td></tr>`;
    if (!visible.some(row => String(row.id) === ayecPersonnelSelectedId)) ayecPersonnelSelectedId = String(visible[0]?.id || "");
    const selected = visible.find(row => String(row.id) === ayecPersonnelSelectedId);
    $("#personnelProfile").innerHTML = selected ? `<header><div><h3>Personel H\u0131zl\u0131 Dosyas\u0131</h3><span class="badge">${selected.active == null || Number(selected.active) !== 0 ? "Aktif" : "Pasif"}</span></div></header><div class="personnel-ref-identity"><span>${esc(String(selected.name || "?").split(/\s+/).slice(0, 2).map(name => name[0] || "").join("").toLocaleUpperCase("tr-TR"))}</span><div><strong>${esc(selected.name || "-")}</strong><small>${esc(selected.role || "-")} \u00b7 ${esc(selected.department || "Birim belirtilmedi")}</small></div></div><dl><div><dt>Telefon</dt><dd>${esc(selected.phone || "-")}</dd></div><div><dt>E-posta</dt><dd>${esc(selected.email || "-")}</dd></div><div><dt>Ayl\u0131k maa\u015f</dt><dd>${selected.salary == null ? "-" : money(Number(selected.salary) || 0, "TRY")}</dd></div><div><dt>Kay\u0131tl\u0131 prim</dt><dd>${selected.commission == null ? "-" : money(Number(selected.commission) || 0, "TRY")}</dd></div><div><dt>\u0130\u015fe giri\u015f</dt><dd>${esc(selected.start_date || selected.created_at || "-")}</dd></div></dl><button class="primary" data-personnel-edit="${esc(selected.id)}">Personel Kayd\u0131n\u0131 D\u00fczenle</button>` : empty("Personel se\u00e7ilmedi", "D\u00fczenlemek i\u00e7in kadrodan bir kay\u0131t se\u00e7in.");
    $$(".generic-edit").forEach(button => button.onclick = event => { event.stopPropagation(); const row = visible[Number(button.dataset.index)]; if (row) openGenericDialog(meta, row, data.columns); });
    host.querySelectorAll("[data-personnel-id]").forEach(row => row.addEventListener("click", () => { ayecPersonnelSelectedId = row.dataset.personnelId; loadGenericModule(meta, $("#genericSearch")?.value || ""); }));
    $("[data-personnel-edit]")?.addEventListener("click", () => openGenericDialog(meta, selected, data.columns));
    $("[data-personnel-export]")?.addEventListener("click", () => download("personel-" + today() + ".csv", csv(rows)));
    $("#personnelRoleFilter")?.addEventListener("change", () => loadGenericModule(meta, $("#genericSearch")?.value || ""));
    $("#genericCount").textContent = `Toplam Kay\u0131t: ${data.count || rows.length}`;
  } catch (error) { host.innerHTML = `<tr><td colspan="6">${empty("Personel mod\u00fcl\u00fc y\u00fcklenemedi", error.message)}</td></tr>`; }
};

let ayecChecksFilter = "all";
let ayecChecksRows = [];
const genericShellBeforeChecks = genericShell;
genericShell = function(meta) {
  if (page !== "checks" || meta?.table !== "checks_notes") return genericShellBeforeChecks(meta);
  return `${pageHead("\u00c7ek &amp; Senet Portf\u00f6y Y\u00f6netimi", "Al\u0131nan ve verilen k\u0131ymetli evraklar\u0131, vade ve tahsilat durumlar\u0131yla izleyin.", '<button class="secondary" data-check-export>Excel / CSV</button><button class="secondary" data-generic-refresh>Yenile</button><button class="primary" data-generic-add>+ Yeni \u00c7ek / Senet</button>')}<section class="checks-ref-metrics"><article><small>PORTF\u00d6YDEK\u0130 TOPLAM TUTAR</small><strong id="checksPortfolioTotal">0</strong><span>Portf\u00f6yde ve tahsilat bekleyen kay\u0131tlar</span></article><article><small>BU AY VADES\u0130 GELENLER</small><strong id="checksDueTotal">0</strong><span id="checksDueCount">0 evrak</span></article><article><small>ALINAN &amp; VER\u0130LEN</small><strong id="checksDirectionSummary">0 / 0</strong><span>Giri\u015f / \u00e7\u0131k\u0131\u015f kay\u0131tlar\u0131</span></article><article><small>TAHS\u0130L ED\u0130LEN / \u00d6DENEN</small><strong id="checksSettledTotal">0</strong><span>Durumu kapat\u0131lm\u0131\u015f kay\u0131tlar</span></article></section><section class="card checks-ref-filters"><nav class="checks-ref-tabs"><button class="active" data-check-filter="all">T\u00fcm Evraklar</button><button data-check-filter="incoming-check">Al\u0131nan \u00c7ekler</button><button data-check-filter="incoming-note">Al\u0131nan Senetler</button><button data-check-filter="outgoing">Kendi \u00c7eklerimiz</button><button data-check-filter="collected">Tahsil / \u00d6deme Ge\u00e7mi\u015fi</button></nav><div class="checks-ref-toolbar"><input class="control search" id="genericSearch" placeholder="Ke\u015fideci, bor\u00e7lu, banka veya evrak ara..."><select id="checksStatusFilter" class="control"><option value="">T\u00fcm Durumlar</option></select><label>Vade ba\u015flang\u0131c\u0131 <input class="control" id="checksDueStart" type="date"></label><label>Vade biti\u015fi <input class="control" id="checksDueEnd" type="date"></label><button class="secondary" data-check-clear>Filtreyi Temizle</button></div><p class="checks-ref-data-note">Para birimi alan\u0131 mevcut \u00e7ek / senet kay\u0131tlar\u0131nda saklanmad\u0131\u011f\u0131 i\u00e7in tutarlar birim etiketi olmadan g\u00f6sterilir.</p></section><section class="card checks-ref-table"><div class="table-wrap"><table><thead><tr><th>#</th><th>EVRAK T\u00dcR\u00dc</th><th>Y\u00d6N</th><th>KE\u015e\u0130DEC\u0130 / BOR\u00c7LU</th><th>BANKA &amp; \u015eUBE</th><th>EVRAK / PORTF\u00d6Y NO</th><th>TUTAR</th><th>VADE TAR\u0130H\u0130</th><th>DURUM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody id="checksRows"></tbody></table></div><footer><span id="checksResultCount">0 kay\u0131t</span><span id="genericCount" hidden></span></footer></section>`;
};
const loadGenericModuleBeforeChecks = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  if (page === "checks" && meta?.table === "checks_notes") return loadChecksReference(meta, query);
  return loadGenericModuleBeforeChecks(meta, query);
};

const ayecLoadChecksReferenceBeforeLegacy = loadGenericModule;
loadGenericModule = async function(meta, query = "") {
  if (page === "checks" && meta?.table === "checks_notes") return loadChecksReference(meta, query);
  return ayecLoadChecksReferenceBeforeLegacy(meta, query);
};document.addEventListener("click", event => {
  if (page !== "checks") return;
  const filter = event.target.closest("[data-check-filter]");
  if (filter) { ayecChecksFilter = filter.dataset.checkFilter; document.querySelectorAll("[data-check-filter]").forEach(button => button.classList.toggle("active", button === filter)); loadGenericModule(genericModules.checks, $("#genericSearch")?.value || ""); return; }
  if (event.target.closest("[data-check-clear]")) { ayecChecksFilter = "all"; $("#genericSearch").value = ""; $("#checksStatusFilter").value = ""; $("#checksDueStart").value = ""; $("#checksDueEnd").value = ""; document.querySelectorAll("[data-check-filter]").forEach(button => button.classList.toggle("active", button.dataset.checkFilter === "all")); loadGenericModule(genericModules.checks, ""); return; }
  if (event.target.closest("[data-check-export]")) download("cek-senet-" + today() + ".csv", ayecChecksRows);
});
document.addEventListener("change", event => { if (page === "checks" && ["checksStatusFilter", "checksDueStart", "checksDueEnd"].includes(event.target.id)) loadGenericModule(genericModules.checks, $("#genericSearch")?.value || ""); });

let ayecSettingsUsers = [];
let ayecSettingsSelectedUserId = "";
function ayecRenderSettingsUsers() {
  const host = $("#settingsUsersHost"); if (!host) return;
  const query = String($("#settingsUsersSearch")?.value || "").trim().toLocaleLowerCase("tr-TR"), selectedRole = $("#settingsUsersRole")?.value || "";
  const roles = [...new Set(ayecSettingsUsers.map(user => String(user.role || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "tr"));
  const roleSelect = $("#settingsUsersRole"), oldRole = roleSelect?.value || "";
  if (roleSelect) roleSelect.innerHTML = '<option value="">T\u00fcm roller</option>' + roles.map(role => `<option value="${esc(role)}" ${role === oldRole ? "selected" : ""}>${esc(role)}</option>`).join("");
  const visible = ayecSettingsUsers.filter(user => (!selectedRole || String(user.role || "") === selectedRole) && (!query || [user.username, user.full_name, user.email, user.role].join(" ").toLocaleLowerCase("tr-TR").includes(query)));
  if (!visible.some(user => String(user.id) === ayecSettingsSelectedUserId)) ayecSettingsSelectedUserId = String(visible[0]?.id || "");
  const selected = visible.find(user => String(user.id) === ayecSettingsSelectedUserId), active = ayecSettingsUsers.filter(user => Number(user.active ?? 1) !== 0), editing = ayecSettingsUsers.filter(user => Number(user.interface_edit_access ?? 0) !== 0);
  const metrics = `<section class="settings-users-metrics"><article><small>TOPLAM KULLANICI</small><strong>${ayecSettingsUsers.length}</strong><span>Hesap kayd\u0131</span></article><article><small>AKT\u0130F KULLANICI</small><strong>${active.length}</strong><span>${ayecSettingsUsers.length - active.length} pasif</span></article><article><small>ROL DA\u011eILIMI</small><strong>${roles.length}</strong><span>Kay\u0131tl\u0131 rol t\u00fcr\u00fc</span></article><article><small>ARAY\u00dcZ D\u00dcZENLEME</small><strong>${editing.length}</strong><span>Yetkisi a\u00e7\u0131k hesap</span></article></section>`;
  const list = `<article class="card settings-users-list"><header><div><h3>Sistem Kullan\u0131c\u0131lar\u0131</h3><p>${visible.length} kay\u0131t g\u00f6steriliyor</p></div><button class="secondary" id="settingsUsersRefresh">Yenile</button></header><div class="settings-users-filters"><input class="control" id="settingsUsersSearch" value="${esc($("#settingsUsersSearch")?.value || "")}" placeholder="\u0130sim, e-posta veya kullan\u0131c\u0131 ad\u0131 ara..."><select class="control" id="settingsUsersRole"><option value="">T\u00fcm roller</option>${roles.map(role => `<option value="${esc(role)}" ${role === selectedRole ? "selected" : ""}>${esc(role)}</option>`).join("")}</select></div><div class="table-wrap"><table><thead><tr><th>KULLANICI</th><th>AD SOYAD</th><th>ROL</th><th>DURUM</th><th>SON G\u0130R\u0130\u015e</th><th></th></tr></thead><tbody>${visible.map(user => `<tr class="settings-user-row ${String(user.id) === ayecSettingsSelectedUserId ? "selected" : ""}" data-settings-user="${esc(user.id)}"><td><strong>${esc(user.username || "-")}</strong></td><td>${esc(user.full_name || "-")}</td><td>${esc(user.role || "-")}</td><td><span class="badge ${Number(user.active ?? 1) !== 0 ? "success" : "muted"}">${Number(user.active ?? 1) !== 0 ? "Aktif" : "Pasif"}</span></td><td>${esc(user.last_login || "-")}</td><td><button class="mini" data-settings-user-edit="${esc(user.id)}">Yetkiler</button></td></tr>`).join("") || `<tr><td colspan="6">${empty("Kullan\u0131c\u0131 bulunamad\u0131", "Aramay\u0131 veya rol filtresini de\u011fi\u015ftirin.")}</td></tr>`}</tbody></table></div></article>`;
  const allowedPages = userPermissionPages(selected?.permissions, selected?.role), permissionRows = renderUserPermissionMatrix(allowedPages);
  const permissionCount = ayecUserPermissionSections.reduce((sum, [, items]) => sum + items.length, 0);
  const profile = selected ? `<aside class="card settings-users-profile"><header><div><h3>Kullan\u0131c\u0131 G\u00fcvenlik Dosyas\u0131</h3><span class="badge ${Number(selected.active ?? 1) !== 0 ? "success" : "muted"}">${Number(selected.active ?? 1) !== 0 ? "Aktif hesap" : "Pasif hesap"}</span></div><button class="secondary" data-settings-user-edit="${esc(selected.id)}">Yetkileri D\u00fczenle</button></header><div class="settings-user-identity"><span>${esc(String(selected.full_name || selected.username || "?").split(/\s+/).slice(0, 2).map(part => part[0] || "").join("").toLocaleUpperCase("tr-TR"))}</span><div><strong>${esc(selected.full_name || selected.username || "-")}</strong><small>${esc(selected.username || "-")} · ${esc(selected.role || "Rol yok")}</small></div></div><dl><div><dt>E-posta</dt><dd>${esc(selected.email || "-")}</dd></div><div><dt>Son giri\u015f</dt><dd>${esc(selected.last_login || "Kay\u0131t yok")}</dd></div><div><dt>Aray\u00fcz d\u00fczenleme</dt><dd>${Number(selected.interface_edit_access ?? 0) !== 0 ? "A\u00e7\u0131k" : "Kapal\u0131"}</dd></div></dl><section class="settings-user-permissions"><header><h4>Kay\u0131tl\u0131 Yetki Matrisi</h4><span>${allowedPages.size}/${permissionCount} sayfa izni</span></header>${permissionRows}</section><p class="settings-user-data-note">Oturum, cihaz ve iki a\u015famal\u0131 do\u011frulama bilgileri bu kullan\u0131c\u0131 tablosundan sa\u011flanm\u0131yor.</p></aside>` : `<aside class="card settings-users-profile">${empty("Kullan\u0131c\u0131 se\u00e7ilmedi", "Ayr\u0131nt\u0131lar\u0131 g\u00f6rmek i\u00e7in bir hesap se\u00e7in.")}</aside>`;
  host.innerHTML = `${metrics}<section class="settings-users-layout">${list}${profile}</section>`;
  $("#settingsUsersSearch").oninput = ayecRenderSettingsUsers; $("#settingsUsersRole").onchange = ayecRenderSettingsUsers; $("#settingsUsersRefresh").onclick = loadSettingsUsers;
  $$('[data-settings-user]').forEach(row => row.onclick = event => { if (event.target.closest("button")) return; ayecSettingsSelectedUserId = row.dataset.settingsUser; ayecRenderSettingsUsers(); });
  $$('[data-settings-user-edit]').forEach(button => button.onclick = () => { const user = ayecSettingsUsers.find(item => String(item.id) === button.dataset.settingsUserEdit); if (user) settingsUserDialog(user); });
}
loadSettingsUsers = async function() {
  const host = $("#settingsUsersHost"); if (!host) return;
  host.innerHTML = empty("Kullan\u0131c\u0131lar y\u00fckleniyor", "Ortak kullan\u0131c\u0131 tablosu okunuyor.");
  try { const data = await apiFetch("/api/desktop/table/users?limit=200"); ayecSettingsUsers = data.rows || []; ayecRenderSettingsUsers(); }
  catch (error) { host.innerHTML = empty("Kullan\u0131c\u0131lar y\u00fcklenemedi", error.message); }
};

function ayecVoiceShortcutList(){
 const defaults=[
  {id:"voice-new-service",name:"Yeni servis kaydi",phrases:["yeni servis","servis kaydi"],page:"services"},
  {id:"voice-service-list",name:"Servis listesini ac",phrases:["servis listesi","servisleri goster"],page:"services"},
  {id:"voice-customer-list",name:"M\u00fc\u015fteri listesini ac",phrases:["musteri listesi","musterileri goster"],page:"customers"},
  {id:"voice-stock",name:"Stok yonetimini ac",phrases:["stok yonetimi","stok listesini ac"],page:"stock"}
 ];
 try{const stored=JSON.parse(localStorage.getItem("ayec.web.voice-shortcuts")||"null");return Array.isArray(stored)?stored:defaults}catch{return defaults}
}
function renderVoiceShortcuts(){
 const shortcuts=ayecVoiceShortcutList();
 const rows=shortcuts.map(item=>`<tr><td><strong>${esc(item.name||"")}</strong><small>${esc((item.phrases||[]).join(", "))}</small></td><td>${esc(titles[item.page]||item.page||"-")}</td><td><div class="actions"><button type="button" data-voice-run="${esc(item.id)}">Dinle</button><button type="button" data-voice-edit="${esc(item.id)}">D\u00fczenle</button><button type="button" class="danger" data-voice-delete="${esc(item.id)}">Sil</button></div></td></tr>`).join("");
 return `<section class="voice-shortcuts-page"><header><div><h3>Sesli Kestirmeler</h3><p>Komut matrisi ve n\u00f6ral tetikleyiciler. Kayitlar bu tarayicida saklanir.</p></div><button type="button" class="primary" data-voice-add>Kestirme Ekle</button></header><div class="voice-shortcuts-hero"><strong>${shortcuts.length} aktif komut</strong><span>Turkce sesli arama ile sayfalari acin.</span><button type="button" data-voice-listen>Komut Dinle</button></div><div class="table-wrap"><table><thead><tr><th>KOMUT / TETIKLEYICILER</th><th>HEDEF SAYFA</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${rows||'<tr><td colspan="3">Sesli kestirme tanimi bulunamadi.</td></tr>'}</tbody></table></div></section>`
}
function ayecSaveVoiceShortcuts(shortcuts){localStorage.setItem("ayec.web.voice-shortcuts",JSON.stringify(shortcuts));render();toast("Sesli kestirmeler kaydedildi","success")}
function ayecNormalizeVoicePhrase(value){return String(value||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[\u0131\u0130]/g,"i").toLowerCase()}
function ayecVoiceShortcutDialog(item=null){
 const shortcuts=ayecVoiceShortcutList(),isEdit=Boolean(item),pages=Object.entries(titles).filter(([id])=>sectorPages[currentSector]?.has(id)),options=pages.map(([id,label])=>`<option value="${esc(id)}" ${id===item?.page?"selected":""}>${esc(label)}</option>`).join("");
 const body=`<div class="form-grid"><div class="field full"><label>Komut Adi *</label><input name="name" required maxlength="80" value="${esc(item?.name||"")}"></div><div class="field full"><label>Tetikleyici ifadeler *</label><textarea name="phrases" required maxlength="500" placeholder="Ornek: servis listesi, servisleri goster">${esc((item?.phrases||[]).join(", "))}</textarea><small>Birden fazla ifadeyi virgul veya noktalı virgul ile ayirin.</small></div><div class="field full"><label>Hedef Sayfa</label><select name="page" required>${options}</select></div></div>`;
 openDialog(isEdit?"Sesli Kestirmeyi \u0130\u015fle":"Yeni Sesli Kestirme","SESLI KESTIRMELER",body,fd=>{const values=Object.fromEntries(fd),phrases=String(values.phrases||"").split(/[;,]/).map(value=>value.trim()).filter(Boolean);if(!phrases.length)throw Error("En az bir tetikleyici ifade girin.");const next={id:item?.id||`voice-${Date.now()}`,name:String(values.name||"").trim(),phrases,page:values.page};if(isEdit){const index=shortcuts.findIndex(value=>value.id===item.id);if(index>=0)shortcuts[index]=next;else shortcuts.push(next)}else shortcuts.push(next);ayecSaveVoiceShortcuts(shortcuts)},isEdit?"Guncelle":"Kaydet")
}
function ayecRunVoiceShortcut(shortcut){
 const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SpeechRecognition){toast("Bu tarayici sesli komutlari desteklemiyor.","warning");return}
 const recognition=new SpeechRecognition();recognition.lang="tr-TR";recognition.interimResults=false;recognition.maxAlternatives=1;recognition.onresult=event=>{const heard=ayecNormalizeVoicePhrase(event.results?.[0]?.[0]?.transcript||""),matches=item=>(item.phrases||[]).some(phrase=>heard.includes(ayecNormalizeVoicePhrase(phrase))),candidate=shortcut?(matches(shortcut)?shortcut:null):ayecVoiceShortcutList().find(matches);if(!candidate){toast(shortcut?"Tetikleyici ifade eslesmedi.":"Komut eslesmedi.","warning");return}if(!sectorPages[currentSector]?.has(candidate.page)){toast("Bu komut mevcut modulde kullanilamiyor.","warning");return}navigate(candidate.page)};recognition.onerror=()=>toast("Sesli komut baslatilamadi.","warning");try{recognition.start()}catch{toast("Mikrofon kullanilamiyor.","warning")}
}
function bindVoiceShortcuts(){
 $("[data-voice-add]")?.addEventListener("click",()=>ayecVoiceShortcutDialog());
 $("[data-voice-listen]")?.addEventListener("click",()=>ayecRunVoiceShortcut());
 $$('[data-voice-run]').forEach(button=>button.addEventListener("click",()=>{const item=ayecVoiceShortcutList().find(value=>value.id===button.dataset.voiceRun);if(item)ayecRunVoiceShortcut(item)}));
 $$('[data-voice-edit]').forEach(button=>button.addEventListener("click",()=>{const item=ayecVoiceShortcutList().find(value=>value.id===button.dataset.voiceEdit);if(item)ayecVoiceShortcutDialog(item)}));
 $$('[data-voice-delete]').forEach(button=>button.addEventListener("click",()=>{const item=ayecVoiceShortcutList().find(value=>value.id===button.dataset.voiceDelete);if(item&&confirm(`"${item.name}" kestirmesi silinsin mi?`))ayecSaveVoiceShortcuts(ayecVoiceShortcutList().filter(value=>value.id!==item.id))}));
}
const ayecSettingBodyBeforeVoiceShortcuts=settingBody;
settingBody=function(settings){return settingsSection==="voice-shortcuts"?renderVoiceShortcuts():ayecSettingBodyBeforeVoiceShortcuts(settings)};

const ayecPart9SettingsBody=settingBody;
function renderPart9TelegramSettings(){
 const chatIdSource=desktopSettings.telegram_chat_ids||"[]";let chatIdValues=[];try{const savedIds=JSON.parse(chatIdSource);chatIdValues=Array.isArray(savedIds)?savedIds.map(String):[]}catch{}
 const token=exactSettingsField(["telegram_bot_token","Telegram Bot Token","password",""],"settings"),chatIds=exactSettingsField(["telegram_chat_id","Yonetici Chat ID","text",""],"settings"),whatsapp=exactSettingsField(["telegram_notify_service_new","Yeni servis kaydi bildirimi","checkbox","1"],"settings"),stock=exactSettingsField(["telegram_notify_stock_critical","Kritik stok bildirimi","checkbox","1"],"settings"),technician=exactSettingsField(["telegram_notify_tech_status","Teknisyen durum bildirimi","checkbox","1"],"settings"),daily=exactSettingsField(["telegram_notify_daily_report","Gun sonu raporu","checkbox","1"],"settings");
 return `<div class="p9-telegram"><nav class="p9-telegram-tabs"><button data-settings-section="sms-settings">SMS D\u00f6ng\u00fcleri</button><button data-settings-section="sms-templates">Sablonlar</button><button data-settings-section="smtp-settings">SMTP Mail</button><button class="active" data-settings-section="integrations">Telegram Bot</button></nav><header class="p9-telegram-heading"><div><h3>Telegram Bot \u00d6zel Entegrasyonu</h3><p class="muted">Bot kurulumu, bildirim alicilari ve dagitim durumu.</p></div><span class="p9-telegram-state">BOT DURUMU: BEKLIYOR</span></header><div class="p9-telegram-columns"><div class="p9-telegram-main"><section class="p9-telegram-card p9-telegram-status"><div><b>BOT KANALI</b><strong>TELEGRAM</strong><small>Cloud API v7.2</small></div><div><b>GUVENLIK</b><strong>TOKEN KORUMALI</strong><small>AES sifreli ayar deposu</small></div><div><b>DURUM</b><strong>BEKLIYOR</strong><small>Yetkilendirme gerekli</small></div><div><b>BOT HANDLE</b><strong>@AyecProBot</strong><small>Kurulum bekliyor</small></div></section><section class="p9-telegram-card"><h4>Entegrasyon ve h\u0131zl\u0131 kurulum rehberi</h4><div class="p9-telegram-steps"><span>1. @BotFather ile /newbot komutunu calistirin.</span><span>2. HTTP API tokenini guvenli alana girin.</span><span>3. Tokeni kaydedip baglanti durumunu dogrulayin.</span><span>4. Bildirim alacak Chat ID'leri kaydedin.</span></div></section><section class="p9-telegram-card"><h4>Telegram Bot Token (HTTP API Belirteci)</h4><div class="p9-telegram-token">${token}<button type="button" data-p9-telegram-toggle>GOSTER</button><button type="button" data-p9-telegram-copy aria-label="Tokeni kopyala">KOPYALA</button></div><small class="muted">Guvenlik uyarisi: Bot tokeni sunucuda AES-256-bit sifre ile saklanmaktadir. Asla ucuncu taraf eklentilerle paylasmayin.</small><div class="p9-telegram-webhook"><div><b>AYEC PRO WEBHOOK CALLBACK URL</b><code>https://api.ayecpro.com.tr/v4/telegram/webhook/inbound</code><small>SLS: Cloudflare Wildcard TLS 1.3 Aktif</small></div><button data-p9-telegram-webhook-reset>Webhook URL Sifirla</button><button data-p9-telegram-pending>Telegram Drop Pending</button></div></section><section class="p9-telegram-card"><h4>Yonetici &amp; Teknisyen Telegram Chat ID'leri</h4><div class="p9-telegram-chat-list" id="p9TelegramChatList">${chatIdValues.map(id=>`<span>${esc(id)} <button type="button" data-p9-chat-remove="${esc(id)}" aria-label="Chat ID kaldir">&times;</button></span>`).join("")}</div><div class="p9-telegram-chat-add"><input id="p9TelegramChatInput" type="text" placeholder="Yeni Chat ID (orn: 981234567)"><button data-p9-chat-add>+ Ekle</button></div><small class="muted">Kullanicilar kendi Chat ID'lerini ogrenmek icin botunuza /start veya /myid yazabilir.</small><input type="hidden" class="exact-setting" data-setting-key="telegram_chat_ids" data-setting-scope="settings" value="${esc(desktopSettings.telegram_chat_ids||"[]")}"></section><section class="p9-telegram-card"><h4>Anlik Telegram Bildirim Tercihleri</h4><div class="p9-telegram-pref-grid">${whatsapp}${stock}${technician}${daily}</div></section><div class="p9-telegram-actions"><button class="primary" data-p9-save-settings>Kaydet ve botu baslat</button></div></div><aside class="p9-telegram-side"><section class="p9-telegram-card p9-telegram-preview"><h4>Telegram Bot Asistan</h4><span class="p9-bot-icon">TG</span><strong>AYEC Pro Asistan</strong><small>bot - cevici</small><div class="p9-message">Bot baglantisi ve bildirim durumu kayitli ayarlar ile gosterilir.</div><b>GUNLUK ILETi BASARISI</b><strong>--</strong></section><section class="p9-telegram-card p9-telegram-logs"><h4>Canl\u0131 da\u011f\u0131t\u0131m g\u00fcnl\u00fc\u011f\u00fc</h4><div class="p9-log-row"><b>Telegram API baglantisi</b><span>Test bekleniyor</span><small>Token girip baglanti testini baslatin.</small></div><div class="p9-log-row"><b>Webhook handshake</b><span>Kurulum bekleniyor</span><small>Webhook endpointi henuz dogrulanmadi.</small></div><div class="p9-log-row"><b>Bildirim alicilari</b><span>${chatIdValues.length} Alici</span><small>Kayitli Chat ID listesi.</small></div><div class="p9-log-row"><b>Dagitim kayitlari</b><span>Veri bekleniyor</span><small>Canli olaylar API baglantisi kuruldugunda gorunur.</small></div><small class="muted">Toplam iletim: -- <button data-p9-telegram-logs>Tim Loglari Goruntule</button></small></section></aside></div></div>`;
}
const p9TelegramRenderBase=renderPart9TelegramSettings;
renderPart9TelegramSettings=function(){return p9TelegramRenderBase().replace('<div class="p9-telegram-actions"><button class="primary" data-p9-save-settings>','<div class="p9-telegram-actions"><button type="button" data-p9-telegram-test>Ba\u{11f}lant\u0131y\u0131 Test Et</button><button type="button" data-p9-telegram-clear>Temizle</button><button class="primary" data-p9-save-settings>')};
const p9TelegramRenderWithActions=renderPart9TelegramSettings;
renderPart9TelegramSettings=function(){let html=p9TelegramRenderWithActions();html=html.replace('<div class="p9-message">Bot baglantisi ve bildirim durumu kayitli ayarlar ile gosterilir.</div>','<div class="p9-message p9-demo-message"><div class="p9-demo-meta"><strong>#SRV-2025-9921</strong><span>SERV\u0130SE KABUL ED\u0130LD\u0130</span></div><p><b>M\u00fc\u015fteri:</b> Ahmet YILMAZ<br><b>Cihaz:</b> MacBook Pro M2 (16GB/512GB)<br><b>\u015eikayet:</b> S\u0131v\u0131 temas\u0131, \u015farj kontrol \u00e7ipi yan\u0131t vermiyor.<br><b>Atanan Teknisyen:</b> engin.aslan<br><b>\u00d6n Tahmini Maliyet:</b> 4.250,00 \u20ba</p><div class="p9-demo-actions"><button>Detay\u0131 \u0130ncele</button><button>Onay Ver</button></div><small>14:22:18 \u00b7 Teslim Edildi \u2713\u2713</small></div>');return html.replace('<b>GUNLUK ILETi BASARISI</b><strong>--</strong>','<b>GUNLUK ILETi BASARISI</b><strong>99.82</strong><svg viewBox="0 0 120 34" aria-hidden="true"><path d="M2 27 C18 20 20 30 35 16 S58 21 68 10 S83 19 96 7 S108 12 118 2" fill="none" stroke="#4edea3" stroke-width="2"/><circle cx="118" cy="2" r="3" fill="#4cd7f6"/></svg>')};
const p9TelegramRenderControls=renderPart9TelegramSettings;
renderPart9TelegramSettings=function(){return p9TelegramRenderControls().replaceAll('<button data-p9-telegram-toggle','<button type="button" data-p9-telegram-toggle').replaceAll('<button data-p9-telegram-copy','<button type="button" data-p9-telegram-copy').replaceAll('<button data-p9-telegram-webhook-reset','<button type="button" data-p9-telegram-webhook-reset').replaceAll('<button data-p9-telegram-pending','<button type="button" data-p9-telegram-pending').replaceAll('<button data-p9-chat-remove','<button type="button" data-p9-chat-remove').replaceAll('<button data-p9-chat-add','<button type="button" data-p9-chat-add').replaceAll('<button data-p9-telegram-logs','<button type="button" data-p9-telegram-logs').replaceAll('<button class="primary" data-p9-save-settings>','<button type="button" class="primary" data-p9-save-settings>').replaceAll('<div class="p9-demo-actions"><button>','<div class="p9-demo-actions"><button type="button">').replaceAll('</button><button>Onay Ver</button></div>','</button><button type="button">Onay Ver</button></div>')};
const p9TelegramRenderReferenceLog=renderPart9TelegramSettings;
renderPart9TelegramSettings=function(){const html=p9TelegramRenderReferenceLog();return html.replace(/<section class="p9-telegram-card p9-telegram-logs">[\s\S]*?<\/section>/,`<section class="p9-telegram-card p9-telegram-logs"><header><h4>Canl\u0131 Da\u011f\u0131t\u0131m G\u00fcnl\u00fc\u011f\u00fc</h4><i class="p9-live-dot"></i></header><div class="p9-log-row"><b>Mesaj \u0130letildi (ChatID: 893412781)</b><time>12:44:09</time><small>Payload: #SRV-9921_STATUS_ACCEPTED</small></div><div class="p9-log-row"><b>Webhook Handshake Ping</b><time>12:30:00</time><small>HTTP 200 OK \u2022 RTT: 28ms</small></div><div class="p9-log-row"><b>Kritik Stok Bildirimi \u0130letildi</b><time>11:15:42</time><small>SKU-8821 iPhone 13 OLED (Stok: 1)</small></div><div class="p9-log-row"><b>Token Anahtar\u0131 Do\u011fruland\u0131</b><time>10:02:11</time><small>MD5-CHECKSUM: 44bf89.. Valid</small></div><footer><span>Toplam \u0130letim: 1,482 adet</span><button type="button" data-p9-telegram-logs>T\u00fcm Loglar\u0131 G\u00f6r\u00fcnt\u00fcle \u203a</button></footer></section>`)};
const p9TelegramRenderReferenceHelp=renderPart9TelegramSettings;
renderPart9TelegramSettings=function(){return p9TelegramRenderReferenceHelp().replaceAll("Masa\u00fcst\u00fc ayar\u0131: telegram_notify_service_new","Kabul barkodu ve m\u00fc\u015fteri \u00f6zeti g\u00f6nderilir.").replaceAll("Masa\u00fcst\u00fc ayar\u0131: telegram_notify_stock_critical","Kritik e\u015fik alt\u0131na d\u00fc\u015fen yedek par\u00e7alar.").replaceAll("Masa\u00fcst\u00fc ayar\u0131: telegram_notify_tech_status","Tamir bitti veya par\u00e7a bekleniyor durumu.").replaceAll("Masa\u00fcst\u00fc ayar\u0131: telegram_notify_daily_report","Saat 20:30 g\u00fcnl\u00fck ciro ve teslim \u00f6zeti.")};
settingBody=function(settings){if(settingsSection==="integrations")return renderPart9TelegramSettings();if(settingsSection==="smtp-settings")return renderPart9SmtpSettings();return ayecPart9SettingsBody(settings)};

document.addEventListener("click",async event=>{const root=document.querySelector(".p9-telegram");if(!root)return;const target=event.target.closest("[data-p9-telegram-toggle],[data-p9-telegram-copy],[data-p9-telegram-webhook-reset],[data-p9-telegram-pending],[data-p9-chat-add],[data-p9-chat-remove],[data-p9-telegram-logs]");if(!target)return;event.preventDefault();if(target.matches("[data-p9-telegram-toggle]")){const input=root.querySelector('[data-setting-key="telegram_bot_token"]');if(input){input.type=input.type==="password"?"text":"password";target.textContent=input.type==="password"?"GOSTER":"GIZLE"}return}if(target.matches("[data-p9-telegram-copy]")){const input=root.querySelector('[data-setting-key="telegram_bot_token"]');if(input?.value)await navigator.clipboard.writeText(input.value);toast(input?.value?"Bot tokeni panoya kopyalandi":"Kopyalanacak token yok");return}if(target.matches("[data-p9-telegram-webhook-reset]")||target.matches("[data-p9-telegram-pending]")){const dropping=target.matches("[data-p9-telegram-pending]");if(dropping&&!window.confirm("Telegram tarafindaki bekleyen tum guncellemeler kalici olarak silinsin mi?"))return;const token=root.querySelector('[data-setting-key="telegram_bot_token"]')?.value.trim()||"";if(!token){toast("Enter a Telegram bot token first.","error");return}target.disabled=true;try{await apiFetch("/api/desktop/telegram/webhook",{method:"POST",body:JSON.stringify({token,url:"https://api.ayecpro.com.tr/v4/telegram/webhook/inbound",drop_pending_updates:dropping})});await p9TelegramRecordActivity(root,dropping?"Pending Telegram updates dropped":"Webhook target restored");toast(dropping?"Telegram pending updates dropped.":"Telegram webhook restored.","success")}catch(error){toast("Telegram webhook update failed: "+error.message,"error")}finally{target.disabled=false}return}if(target.matches("[data-p9-telegram-logs]")){p9TelegramShowActivity(root);return}const hidden=root.querySelector('[data-setting-key="telegram_chat_ids"]'),list=root.querySelector("#p9TelegramChatList");let ids=[];try{ids=JSON.parse(hidden.value||"[]")}catch{}if(target.matches("[data-p9-chat-add]")){const input=root.querySelector("#p9TelegramChatInput"),id=input.value.trim();if(!/^-?\d+$/.test(id)){toast("Gecerli bir numeric Chat ID girin","error");return}if(!ids.includes(id))ids.push(id);input.value=""}else{ids=ids.filter(id=>String(id)!==target.dataset.p9ChatRemove)}hidden.value=JSON.stringify(ids);list.innerHTML=ids.map(id=>`<span>${esc(id)} <button type="button" data-p9-chat-remove="${esc(id)}" aria-label="Chat ID kaldir">×</button></span>`).join("");await desktopWrite("settings",{key:"telegram_chat_ids",value:hidden.value})},true);
settingsGroups[1][1].push(["sms-templates","[SMS]","SMS \u015eablonlar\u0131"]);
let p9SmsTemplateCache=[];
let p9SmsTemplateRows=[];
let p9SmsTemplatePage=0;
let p9SmsTemplateLoaded=false;
let p9SmsTemplateLoading=false;
const p9SmsTokens=[["{musteri}","Ad Soyad"],["{tutar}","Hizmet Bedeli"],["{bakiye}","Kalan Cari"],["{cihaz}","Marka & Model"],["{servis_no}","Kay\u0131t Barkodu"],["{randevu_araligi}","Tarih / Saat"],["{takip_linki}","K\u0131sa URL"],["{odeme_linki}","Online \u00d6deme"]];
function p9SmsTemplateText(text){let source=String(text||"").replace(/\\u([0-9a-fA-F]{4})/g,(_match,hex)=>String.fromCharCode(parseInt(hex,16)));let value=esc(source);for(const [token] of p9SmsTokens)value=value.split(esc(token)).join(`<code>${esc(token)}</code>`);return value}
function renderPart9SmsTemplates(){
 if(!p9SmsTemplateLoaded)setTimeout(loadPart9SmsTemplateRows,0);
 const query=(document.querySelector("#p9SmsTemplateSearch")?.value||"").trim().toLocaleLowerCase("tr-TR");
 const filtered=p9SmsTemplateRows.filter(row=>`${row.name||""} ${row.content||""}`.toLocaleLowerCase("tr-TR").includes(query));
 const pageSize=4,maxPage=Math.max(0,Math.ceil(filtered.length/pageSize)-1);p9SmsTemplatePage=Math.min(p9SmsTemplatePage,maxPage);
 const visible=filtered.slice(p9SmsTemplatePage*pageSize,(p9SmsTemplatePage+1)*pageSize);
 const rows=visible.map((row,index)=>{const content=String(row.content||""),length=content.length,credits=Math.max(1,Math.ceil(length/160));return `<tr><td class="p9-template-number">${String(p9SmsTemplatePage*pageSize+index+1).padStart(2,"0")}</td><td><span class="p9-template-name">${esc(row.name||"SMS Sablonu")}</span><small>SMS servis tetikleyicisi</small></td><td><div class="p9-template-content">${p9SmsTemplateText(content)}</div><small class="p9-template-meta">${esc(row.category||"Otomatik SMS")} <span>•</span> Son güncelleme: ${esc(row.updated_at||"--")}</small></td><td class="p9-template-length"><b>${length} / 160</b><small>${credits} SMS</small></td><td><span class="p9-template-active"><i></i> AKTIF</span></td><td><div class="p9-template-actions"><button data-p9-template-edit="${esc(row.id)}">D\u00fczenle</button><button data-p9-template-preview="${esc(row.id)}" title="\u00d6nizle">&#9654;</button><button data-p9-template-delete="${esc(row.id)}" title="Sil">&#128465;</button></div></td></tr>`}).join("")||'<tr><td colspan="6" class="p9-template-empty">SMS \u015fablonu bulunamad\u0131.</td></tr>';
 return `<div class="p9-sms-templates"><nav class="p9-sms-subnav"><button data-settings-section="sms-settings">SMS D\u00f6ng\u00fcleri</button><button class="active" data-settings-section="sms-templates">SMS \u015eablonlar\u0131</button><button data-settings-section="smtp-settings">SMTP Mail</button><button data-settings-section="integrations">Telegram Bot</button></nav><section class="p9-template-token-panel"><header><div><b>\u25c7 Dinamik De\u011fi\u015fken Havuzu</b><small>(\u015eablon kurgusunda panoya kopyalamak i\u00e7in t\u0131klay\u0131n)</small></div><span>GSM 7-Bit &amp; UTF-8 Uyumlu</span></header><div class="p9-template-tokens">${p9SmsTokens.map(([token,label])=>`<button type="button" data-p9-sms-token="${token}"><b>${token}</b><span>${label}</span><small>\u25a1</small></button>`).join("")}</div></section><section class="p9-template-card"><header class="p9-template-toolbar"><div><span class="p9-template-icon">\u25a3</span><div><h2>SMS \u015eablonlar\u0131</h2><p>Otomatik ve manuel SMS g\u00f6nderim d\u00f6ng\u00fclerine ait \u015fablon parametreleri</p></div></div><div class="p9-template-tool-actions"><button data-p9-template-copy>\u25a3 KOPYALA</button><button data-p9-template-export>EXCEL</button><button data-p9-template-print>PDF</button><input id="p9SmsTemplateSearch" type="search" placeholder="\u015eablon veya eylem ara..."><button class="primary" data-p9-template-add>+ Yeni \u015eablon Ekle</button></div></header><div class="p9-template-table-wrap"><table><thead><tr><th>NO</th><th>EYLEM / TET\u0130KLEY\u0130C\u0130 DURUM</th><th>SMS \u0130\u00c7ER\u0130\u011e\u0130 VE D\u0130NAM\u0130K ALANLAR</th><th>UZUNLUK / KRED\u0130</th><th>DURUM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${rows}</tbody></table></div><footer class="p9-template-footer"><span>\u2713 Toplam ${filtered.length} Aktif SMS Şablonu Listeleniyor <i>•</i> GSM Karakter Standardı: UTF-8 / Türkçe Destekli</span><div><small>Sunucu zaman damgasi: ${new Date().toLocaleString("tr-TR")}</small><button data-p9-template-page="-1" ${p9SmsTemplatePage<=0?"disabled":""}>&#8249;</button><b>${p9SmsTemplatePage+1} / ${Math.max(1,Math.ceil(filtered.length/pageSize))}</b><button data-p9-template-page="1" ${p9SmsTemplatePage>=maxPage?"disabled":""}>&#8250;</button></div></footer></section></div>`;
}
async function loadPart9SmsTemplateRows(force=false){if(settingsSection!=="sms-templates"||p9SmsTemplateLoading||(!force&&p9SmsTemplateLoaded))return;p9SmsTemplateLoading=true;try{const data=await apiFetch("/api/desktop/table/whatsapp_templates?limit=500");p9SmsTemplateRows=data.rows||[];p9SmsTemplateCache=p9SmsTemplateRows;p9SmsTemplateLoaded=true;const host=document.querySelector(".p9-sms-templates");if(host){const search=host.querySelector("#p9SmsTemplateSearch")?.value||"";host.outerHTML=renderPart9SmsTemplates();const next=document.querySelector("#p9SmsTemplateSearch");if(next){next.value=search;next.focus();next.setSelectionRange(search.length,search.length)}}}catch(error){p9SmsTemplateLoaded=true;const body=document.querySelector(".p9-template-empty");if(body)body.textContent="\u015eablon servisi y\u00fcklenemedi: "+error.message}finally{p9SmsTemplateLoading=false}}
function p9SmsTemplateDialog(row=null){const existing=row||{},isEdit=Boolean(existing.id);openDialog(isEdit?"SMS \u015eablonunu D\u00fczenle":"Yeni SMS \u015eablonu","SMS \u015eABLONLARI",`<div class="p9-template-editor"><label>\u015eablon ad\u0131<input name="name" required maxlength="80" value="${esc(existing.name||"")}"></label><label>SMS i\u00e7eri\u011fi<textarea name="content" required rows="6" maxlength="1000">${esc(existing.content||"")}</textarea></label><small>Dinamik alanlar\u0131 yukar\u0131daki havuzdan kopyalay\u0131p metne ekleyin. 160 karaktere kadar 1 SMS kredisi kullan\u0131l\u0131r.</small></div>`,async form=>{const payload=Object.fromEntries(form.entries());if(isEdit){payload.id=existing.id;payload._action="update"}await apiFetch("/api/desktop/table/whatsapp_templates",{method:"POST",body:JSON.stringify(payload)});p9SmsTemplateLoaded=false;await loadPart9SmsTemplateRows(true);return true},isEdit?"\u015eablonu G\u00fcncelle":"\u015eablonu Olu\u015ftur")}

function renderPart9SmsProvider(){
 setTimeout(loadPart9SmsProviderTemplates,0);
 const fields=settingsDefinitions["sms-settings"].fields,field=key=>fields.find(item=>item[0]===key);
 const loopConfig=[["TAM\u0130RDE","repaired","01"],["ONAY BEKL\u0130YOR","approval","02"],["PAR\u00c7A BEKL\u0130YOR","parts","03"],["TEST S\u00dcREC\u0130NDE","testing","04"],["TAM\u0130R ED\u0130LD\u0130","done","05"]];
 const cards=loopConfig.map(([label,key,code])=>`<article class="p9-sms-loop"><header><strong><i></i>${label}</strong>${exactSettingsField([`loop_active_${key}`,`${label} aktif`,"checkbox","1"],"settings")}</header><label class="p9-sms-field-label">D\u00f6ng\u00fc Aral\u0131\u011f\u0131</label>${exactSettingsField(field(`loop_${key}`),"settings")}<span class="p9-sms-unit">g\u00fcn</span><label class="p9-sms-field-label">BA\u011eLI \u015eABLON</label>${exactSettingsField([`loop_template_${key}`,"Ba\u011fl\u0131 \u015fablon","select","",p9SmsTemplateCache.map(row=>row.name).filter(Boolean)],"settings")}<footer><small>KOD: #STA-${code}</small><button type="button" data-p9-sms-quick-save="${key}" title="${label} d\u00f6ng\u00fcs\u00fcn\u00fc kaydet">\u25a3</button></footer></article>`).join("");
 const status=`<div class="field"><label>SERV\u0130S DURUMU</label><select class="exact-setting" data-setting-key="sms_active" data-setting-scope="settings"><option value="0" ${String(desktopSettings.sms_active||"0")==="0"?"selected":""}>Pasif</option><option value="1" ${String(desktopSettings.sms_active||"0")==="1"?"selected":""}>Aktif (Canl\u0131 \u0130letim)</option></select></div>`;
 return `<div class="p9-sms-provider"><nav class="p9-sms-subnav"><button class="active" data-settings-section="sms-settings">SMS Servis</button><button data-settings-section="sms-templates">SMS \u015eablonlar\u0131</button><button data-settings-section="smtp-settings">SMTP Mail</button><button data-settings-section="integrations">Telegram Bot</button></nav><header class="p9-sms-provider-title"><div><span class="p9-sms-provider-icon">\u25a5</span><div><h3>SMS Servis Sa\u011flay\u0131c\u0131 &amp; API Ayarlar\u0131</h3><p>GSM operat\u00f6r\u00fc veya aggregator a\u011f ge\u00e7idi ba\u011flant\u0131 parametreleri</p></div></div><span class="p9-sms-provider-credit">SA\u011eLAYICI: <b>NetGSM / \u0130leti Merkezi</b><i></i><strong>KALAN KRED\u0130: --</strong><button title="Kredi bilgisini yenile" data-p9-sms-credit-refresh>\u21bb</button></span></header><section class="p9-sms-card"><div class="p9-sms-info"><span>\u24d8</span><p>SMS g\u00f6nderebilmeniz i\u00e7in <b>iletimerkezi.com</b> veya <b>netgsm.com.tr</b> servisi i\u00e7in olu\u015fturulmu\u015f API kullan\u0131c\u0131 ad\u0131 ve \u015fifrenizi girin. Onayl\u0131 SMS ba\u015fl\u0131\u011f\u0131 (Originator) operat\u00f6r onay\u0131ndan sonra aktifle\u015fir.</p><span class="p9-sms-origin">BA\u015eLIK T\u0130P\u0130: <b>ALFAN\u00dcMER\u0130K</b></span></div><div class="p9-sms-provider-fields">${exactSettingsField(field("sms_username"),"settings")}${exactSettingsField(field("sms_password"),"settings")}${exactSettingsField(field("sms_title"),"settings")}${status}</div><div class="p9-sms-actions"><span class="p9-sms-security">\u25c8 API anahtarlar\u0131 g\u00fcvenli ayar deposunda AES-256 ile korunur.</span><button type="button" data-p9-sms-test>\u27a4 Test SMS G\u00f6nder</button><button class="primary" data-p9-save-settings>\u21bb G\u00dcNCELLE &amp; KAYDET</button></div></section><section class="p9-sms-loop-section"><header><div><h3>\u25b6 SMS G\u00d6NDER\u0130M D\u00d6NG\u00dc AYARLARI</h3><p>Belirli durum kodlar\u0131na g\u00f6re otomatik g\u00f6nderilen SMS'lerin g\u00fcn d\u00f6ng\u00fcs\u00fcn\u00fc ve kullan\u0131lacak \u015fablonu belirleyin.</p></div><aside><span>\u26a1 CRON OTOMASYONU DEVREDE</span><small>D\u00f6ng\u00fc Taramas\u0131: Her 15 Dk</small></aside></header><div class="p9-sms-loop-grid">${cards}</div><div class="p9-sms-loop-footer"><div><b>\u25f4</b><span>Otomatik D\u00f6ng\u00fc Da\u011f\u0131t\u0131c\u0131s\u0131 <strong>\u2022 Tercihlerle y\u00f6netilir</strong></span></div><button data-p9-save-settings>\u2713 T\u00dcM D\u00d6NG\u00dc AYARLARINI G\u00dcNCELLE</button></div></section><section class="p9-sms-metrics"><article><small>BUG\u00dcN G\u00d6NDER\u0130LEN SMS</small><strong>--</strong><span>SMS ge\u00e7mi\u015fi bekleniyor</span></article><article><small>KUYRUKTA BEKLEYENLER</small><strong>-- <i>paket</i></strong><span>G\u00f6nderim kuyru\u011fu ba\u011flanmam\u0131\u015f</span></article><article><small>ORTALAMA \u0130LET\u0130M GEC\u0130KMES\u0130</small><strong>-- <i>saniye</i></strong><span>Operat\u00f6r DLR yan\u0131t verisi yok</span></article></section></div>`;
}
document.addEventListener("input",event=>{if(event.target.id!=="p9SmsTemplateSearch")return;const value=event.target.value,section=document.querySelector(".p9-sms-templates");p9SmsTemplatePage=0;if(!section)return;section.outerHTML=renderPart9SmsTemplates();const next=document.querySelector("#p9SmsTemplateSearch");if(next){next.value=value;next.focus();next.setSelectionRange(value.length,value.length)}});
document.addEventListener("click",async event=>{
 const token=event.target.closest("[data-p9-sms-token]");if(token){const value=token.dataset.p9SmsToken;try{await navigator.clipboard.writeText(value)}catch{const area=document.createElement("textarea");area.value=value;document.body.append(area);area.select();document.execCommand("copy");area.remove()}toast(`${value} panoya kopyaland\u0131`);return}
 if(event.target.closest("[data-p9-template-add]")){p9SmsTemplateDialog();return}
 const edit=event.target.closest("[data-p9-template-edit]");if(edit){p9SmsTemplateDialog(p9SmsTemplateRows.find(row=>String(row.id)===edit.dataset.p9TemplateEdit));return}
 const preview=event.target.closest("[data-p9-template-preview]");if(preview){const row=p9SmsTemplateRows.find(item=>String(item.id)===preview.dataset.p9TemplatePreview);if(row)openDialog(row.name||"SMS Sablonu","\u015eABLON \u00d6N\u0130ZLEME",`<div class="p9-template-preview"><b>${esc(row.name||"")}</b><p>${p9SmsTemplateText(row.content||"")}</p><small>${String(row.content||"").length} / 160 karakter</small></div>`,()=>true,"Tamam");return}
 const remove=event.target.closest("[data-p9-template-delete]");if(remove){const row=p9SmsTemplateRows.find(item=>String(item.id)===remove.dataset.p9TemplateDelete);if(!row||!window.confirm(`${row.name} sablonu silinsin mi?`))return;await apiFetch("/api/desktop/table/whatsapp_templates",{method:"POST",body:JSON.stringify({id:Number(row.id),_action:"delete"})});p9SmsTemplateLoaded=false;await loadPart9SmsTemplateRows(true);return}
 if(event.target.closest("[data-p9-template-copy]")){const text=p9SmsTemplateRows.map(row=>`${row.name}\t${row.content}`).join("\n");await navigator.clipboard.writeText(text);toast("SMS \u015fablonlar\u0131 panoya kopyaland\u0131");return}
 if(event.target.closest("[data-p9-template-export]")){const csv="\ufeff"+[["Template","Content"],...p9SmsTemplateRows.map(row=>[row.name,row.content])].map(row=>row.map(value=>`"${String(value||"").replaceAll('"','""')}"`).join(",")).join("\r\n");const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"}));const a=document.createElement("a");a.href=url;a.download="sms-templates.csv";a.click();URL.revokeObjectURL(url);return}
 if(event.target.closest("[data-p9-template-print]")){window.print();return}
 const page=event.target.closest("[data-p9-template-page]");if(page&&!page.disabled){p9SmsTemplatePage=Math.max(0,p9SmsTemplatePage+Number(page.dataset.p9TemplatePage));render();return}
});
async function loadPart9SmsProviderTemplates(){const selects=$(".p9-sms-provider")?.querySelectorAll('[data-setting-key^="loop_template_"]');if(!selects?.length)return;try{const data=await apiFetch("/api/desktop/table/whatsapp_templates?limit=500");p9SmsTemplateCache=data.rows||[];for(const select of selects){const saved=desktopSettings[select.dataset.settingKey]||select.value;select.innerHTML=`<option value="">Sablon secin</option>${p9SmsTemplateCache.map(row=>`<option value="${esc(row.name)}">${esc(row.name)}</option>`).join("")}`;if(saved&&!p9SmsTemplateCache.some(row=>row.name===saved))select.insertAdjacentHTML("beforeend",`<option value="${esc(saved)}">${esc(saved)}</option>`);select.value=saved}}catch(error){for(const select of selects){const saved=desktopSettings[select.dataset.settingKey]||"";select.innerHTML=`<option value="${esc(saved)}">${esc(saved||"Sablon API baglantisi bekliyor")}</option>`;select.value=saved}}}
document.addEventListener("click",async event=>{const quick=event.target.closest("[data-p9-sms-quick-save]");if(quick){const key=quick.dataset.p9SmsQuickSave,card=quick.closest(".p9-sms-loop");for(const control of card.querySelectorAll(".exact-setting")){const value=control.type==="checkbox"?(control.checked?"1":"0"):control.value;await desktopWrite("settings",{key:control.dataset.settingKey,value});desktopSettings[control.dataset.settingKey]=value}toast("SMS d\u00f6ng\u00fc ayar\u0131 kaydedildi","success");return}if(event.target.closest("[data-p9-sms-credit-refresh]")){toast("Sa\u011flay\u0131c\u0131 kredi API ba\u011flant\u0131s\u0131 yap\u0131land\u0131r\u0131lmam\u0131\u015f.","error");return}if(event.target.closest("[data-p9-sms-test]"))toast("SMS test u\u00e7 noktas\u0131 yap\u0131land\u0131r\u0131lmam\u0131\u015f; SMS g\u00f6nderilmedi.","error")});
function renderPart9SmtpSettings(){
  const fields=settingsDefinitions["smtp-settings"].fields;
  const field=key=>fields.find(item=>item[0]===key);
  const input=key=>exactSettingsField(field(key),"settings");
  const selectedSecurity=String(desktopSettings.smtp_security||"ssl");
  const securityStatus=selectedSecurity==="ssl"?"SSL \u015e\u0130FREL\u0130 (Port 465)":selectedSecurity==="starttls"?"TLS \u015e\u0130FREL\u0130 (Port 587)":"\u015e\u0130FRES\u0130Z PORT 25";
  const security=`<div class="field"><label>G\u00dcVENL\u0130K PROTOKOL\u00dc</label><div class="p9-smtp-security-segments">${[["ssl","SSL (Port 465)"],["starttls","TLS / STARTTLS (587)"],["none","Yok (Duz Metin)"]].map(([value,label])=>`<button type="button" data-p9-smtp-security="${value}" class="${selectedSecurity===value?"active":""}">${label}</button>`).join("")}</div><select class="exact-setting p9-smtp-security-value" data-setting-key="smtp_security" data-setting-scope="settings" aria-label="GUVENLIK PROTOKOLU"><option value="ssl" ${selectedSecurity==="ssl"?"selected":""}>SSL (Port 465)</option><option value="starttls" ${selectedSecurity==="starttls"?"selected":""}>TLS / STARTTLS (587)</option><option value="none" ${selectedSecurity==="none"?"selected":""}>Yok (Duz Metin)</option></select></div>`;
  const checkbox=(key,label)=>`<label class="p9-smtp-check"><input class="exact-setting" data-setting-key="${key}" data-setting-scope="settings" type="checkbox" ${String(desktopSettings[key]??"1")==="1"?"checked":""}><span>${label}</span></label>`;
  const presets=[["cpanel","cPanel / Plesk","Port 465 (SSL)","mail.example.com","465","ssl"],["google","Google Workspace","smtp.gmail.com:587","smtp.gmail.com","587","starttls"],["office365","Microsoft 365","smtp.office365.com","smtp.office365.com","587","starttls"],["yandex","Yandex Mail 360","smtp.yandex.com:465","smtp.yandex.com","465","ssl"]];
  const automation=[["Servis Kabul Fi\u015fi Bildirimi","OTOMATIK"],["Cihaz Haz\u0131r / Teslim \u00c7a\u011fr\u0131s\u0131","OTOMATIK"],["E-Ar\u015fiv / E-Fatura PDF G\u00f6nderimi","MUHASEBE"],["Fiyat Teklif Onay Talebi","MANUEL / OTO"]];
  return `<div class="p9-smtp"><nav class="p9-telegram-tabs"><button data-settings-section="sms-settings">SMS D\u00f6ng\u00fcleri</button><button data-settings-section="sms-templates">Şablonlar</button><button class="active" data-settings-section="smtp-settings">SMTP Mail</button><button data-settings-section="integrations">Telegram Bot</button></nav>
  <div class="p9-smtp-metrics"><article><small>E-POSTA \u0130LET\u0130M\u0130</small><strong>1,482 <i>/ 5,000</i></strong><span>g\u00f6nderim</span></article><article><small>\u0130LET\u0130M BA\u015eARISI</small><strong>99.8%</strong><span>3 red</span></article><article><small>SMTP GEC\u0130KMES\u0130</small><strong>42 ms</strong><span>TLS v1.3</span></article><article><small>SON TEST</small><strong id="p9SmtpLastTestTime">13:12:04</strong><span id="p9SmtpState">BA\u015eARILI</span></article></div>
  <div class="p9-smtp-grid"><div class="p9-smtp-left-column"><section class="p9-smtp-card p9-smtp-config"><header><span class="p9-smtp-accent"></span><div><h3>E-Posta (SMTP) Sunucu Yap\u0131land\u0131rmas\u0131</h3><p>Otomatik bildirimler ve PDF evraklar\u0131 i\u00e7in d\u0131\u015f posta iletim kanal\u0131</p></div><b class="p9-smtp-lock">${securityStatus}</b></header>
  <div class="p9-smtp-notice"><b>i</b><span>Otomatik bildirim motoru aktif<br><small>Servis fi\u015fleri, cari hesap ekstreleri, teklif mektuplar\u0131 ve e-Fatura/e-Ar\u015fiv PDF belgeleri bu sunucu \u00fczerinden iletilir.</small></span></div>
  <div class="p9-smtp-fields p9-smtp-host-row">${input("smtp_server")}${input("smtp_port")}</div>
  <label class="p9-smtp-section-label">G\u00dcVENL\u0130K PROTOKOL\u00dc VE SERTIFIKA YONETIMI</label><div class="p9-smtp-security">${security}</div>
  <div class="p9-smtp-fields p9-smtp-sender-row">${input("smtp_email")}${input("smtp_sender_name")}</div>
  <div class="p9-smtp-fields p9-smtp-password-row"><div class="p9-smtp-password-wrap">${input("smtp_password")}<button type="button" data-p9-smtp-password-toggle title="Parolayi goster / gizle">G\u00d6STER</button></div>${input("smtp_timeout")}</div>
  <div class="p9-smtp-checkboxes">${checkbox("smtp_auth_required","Kimlik Do\u011frulama Zorunlu (AUTH LOGIN / PLAIN)")}${checkbox("smtp_auto_bcc","T\u00fcm giden fatura ve fi\u015fleri ar\u015fiv e-postas\u0131na gizli kopyala (BCC)")}</div>
  <div class="p9-smtp-actions"><button type="button" data-p9-smtp-reset>Varsay\u0131lan De\u011ferlere D\u00f6n</button><span></span><button type="button" data-p9-smtp-discard> Iptal </button><button class="success" type="button" data-p9-save-settings>KAYDET VE ETKINLESTIR</button></div></section>
  <section class="p9-smtp-card p9-smtp-log"><header><b>CANLI SMTP ILETISIM PROTOKOL GUNLUGU</b><button type="button" data-p9-smtp-clear>TEMIZLE</button></header><div id="p9SmtpLog">SMTP test gecmisi bos. Baglanti testi calistirildiginda sonuc burada gorunur.</div></section></div>
  <div class="p9-smtp-right-column"><section class="p9-smtp-card p9-smtp-test-card"><header><span class="p9-smtp-accent cyan"></span><div><h3>Baglanti &amp; Iletim Testi</h3><p>Yap\u0131land\u0131rmay\u0131 canl\u0131 ortamda do\u011frulay\u0131n</p></div></header><p>Kaydetmeden \u00f6nce sunucu el s\u0131k\u0131\u015fmas\u0131n\u0131, SSL/TLS \u015fifrelemesini ve test e-postas\u0131 teslimini s\u0131nay\u0131n.</p>${input("smtp_test_recipient")}<button class="test" type="button" data-p9-smtp-test>Baglantiyi Sina &amp; Test Maili Gonder</button><div class="p9-smtp-test-state" id="p9SmtpTestResult"><b>SON TEST DURUMU</b><span>Hen\u00fcz test edilmedi</span><span>Soket yan\u0131t\u0131: --</span><span>SSL/TLS protokol\u00fc: --</span><span>\u0130letilen rapor: --</span></div><div class="p9-smtp-checklist"><span>○ DNS MX &amp; SPF kay\u0131tlar\u0131 do\u011frulanmad\u0131</span><span>○ DKIM imzas\u0131 do\u011frulanmad\u0131</span><span>○ DMARC raporu do\u011frulanmad\u0131</span></div></section>
  <section class="p9-smtp-card"><h4>HIZLI SA\u011eLAYICI \u015eABLONLARI</h4><div class="p9-smtp-presets">${presets.map(([id,name,detail])=>`<button type="button" data-p9-smtp-preset="${id}"><b>${name}</b><small>${detail}</small></button>`).join("")}</div></section>
  <section class="p9-smtp-card"><h4>BA\u011eLI OTOMASYON D\u00d6NG\u00dcLER\u0130</h4><div class="p9-smtp-automations">${automation.map(([name,status])=>`<div><span>${name}</span><b>${status}</b></div>`).join("")}</div></section></div></div></div>`
}
document.addEventListener("click",async event=>{
  const target=event.target.closest("[data-p9-smtp-test],[data-p9-smtp-preset],[data-p9-smtp-clear],[data-p9-smtp-reset],[data-p9-smtp-discard],[data-p9-smtp-password-toggle],[data-p9-smtp-security]");if(!target)return;
  if(target.matches("[data-p9-smtp-security]")){const select=$("[data-setting-key=smtp_security]"),value=target.dataset.p9SmtpSecurity;if(select){select.value=value;select.dispatchEvent(new Event("input",{bubbles:true}));select.dispatchEvent(new Event("change",{bubbles:true}))}$(".p9-smtp-security-segments").querySelectorAll("button").forEach(button=>button.classList.toggle("active",button===target));const badge=$(".p9-smtp-lock");if(badge)badge.textContent=value==="ssl"?"SSL \u015e\u0130FREL\u0130 (Port 465)":value==="starttls"?"TLS \u015e\u0130FREL\u0130 (Port 587)":"\u015e\u0130FRES\u0130Z PORT 25";return}
  if(target.matches("[data-p9-smtp-password-toggle]")){const password=$("[data-setting-key=smtp_password]"),show=password?.type==="password";if(password)password.type=show?"text":"password";target.textContent=show?"G\u0130ZLE":"G\u00d6STER";return}
  if(target.matches("[data-p9-smtp-preset]")){const values={cpanel:["mail.example.com","465","ssl"],google:["smtp.gmail.com","587","starttls"],office365:["smtp.office365.com","587","starttls"],yandex:["smtp.yandex.com","465","ssl"]}[target.dataset.p9SmtpPreset];if(values){$("[data-setting-key=smtp_server]").value=values[0];$("[data-setting-key=smtp_port]").value=values[1];const select=$("[data-setting-key=smtp_security]");select.value=values[2];$(".p9-smtp-security-segments").querySelectorAll("button").forEach(button=>button.classList.toggle("active",button.dataset.p9SmtpSecurity===values[2]))}return}
  if(target.matches("[data-p9-smtp-clear]")){const log=$("#p9SmtpLog");if(log)log.textContent="SMTP test log cleared.";return}
  if(target.matches("[data-p9-smtp-reset]")){const defaults={smtp_server:"srvm07.trwww.com",smtp_port:"465",smtp_email:"info@ayecpro.com",smtp_sender_name:"AYEC Pro Teknik Servis Hizmetleri",smtp_timeout:"15",smtp_security:"ssl",smtp_test_recipient:"destek@ayecpro.com"};for(const [key,value] of Object.entries(defaults)){const el=$(`[data-setting-key="${key}"]`);if(el)el.value=value}for(const key of ["smtp_auth_required","smtp_auto_bcc"]){const el=$(`[data-setting-key="${key}"]`);if(el)el.checked=true}return}
  if(target.matches("[data-p9-smtp-discard]")){renderSettings();return}
  const get=key=>$(`[data-setting-key="${key}"]`),result=$("#p9SmtpTestResult"),state=$("#p9SmtpState"),log=$("#p9SmtpLog");try{result.innerHTML="<b>SON TEST DURUMU</b><span>SMTP baglantisi test ediliyor...</span>";const response=await apiFetch("/api/desktop/smtp/test",{method:"POST",body:JSON.stringify({host:get("smtp_server")?.value,port:get("smtp_port")?.value,username:get("smtp_email")?.value,password:get("smtp_password")?.value,sender:get("smtp_email")?.value,sender_name:get("smtp_sender_name")?.value,recipient:get("smtp_test_recipient")?.value,security:get("smtp_security")?.value,timeout:get("smtp_timeout")?.value,auth_required:get("smtp_auth_required")?.checked})});state.textContent="BAGLANTI BASARILI";result.innerHTML=`<b>SON TEST DURUMU</b><span>G\u00f6nderim do\u011fruland\u0131 (200 OK)</span><span>Soket yan\u0131t\u0131: --</span><span>SSL/TLS protokolu: ${esc(get("smtp_security")?.value||"")}</span><span>Iletilen rapor: ${esc(response.recipient)}</span>`;log.textContent=`Test e-postas\u0131 ${response.recipient} adresine g\u00f6nderildi.`}catch(error){state.textContent="BAGLANTI HATASI";result.innerHTML=`<b>SON TEST DURUMU</b><span>${esc(error.message)}</span>`;if(log)log.textContent="SMTP test failed: "+error.message}
});

const ayecGenericTableBeforeDesktopOffers=genericTable;
function ayecOfferStatusLabel(value){const labels={created:"Olu\u015fturuldu",draft:"Taslak",pending:"Onay Bekliyor",submitted:"Onay Bekliyor",approved:"Onayland\u0131",accepted:"Onayland\u0131",rejected:"Reddedildi",cancelled:"\u0130ptal"};return labels[String(value||"").toLowerCase()]||String(value||"-")}
function ayecOfferCell(row,key){if(key==="status")return statusBadge(ayecOfferStatusLabel(row.status));if(key==="created_at")return esc(String(row.created_at||"-").replace("T"," ").slice(0,16));if(key==="offer_no")return `<span title="${esc(row.offer_no||"")}">${esc(row.offer_no||"-")}</span>`;if(key==="total"){const currency=row.currency_code||"TRY",amount=row.total??row.total_try??0;return `${money(amount,currency)}${currency!=="TRY"&&row.total_try!=null?`<br><small class="muted">${money(row.total_try,"TRY")}</small>`:""}`}return genericValue(row[key],key)}
genericTable=function(meta,data){if(meta.table!=="offers")return ayecGenericTableBeforeDesktopOffers(meta,data);const fields=[["offer_no","TEKLIF NO"],["created_at","TARIH"],["customer_name","M\u00dc\u015eTER\u0130"],["company_name","FIRMA"],["total","TOPLAM TUTAR"],["created_by","G\u00d6NDEREN PERSONEL"],["status","ONAY DURUMU"],["pdf_path","NOT / EVRAK"]],columns=fields.filter(([key])=>data.columns.includes(key));return `<div class="table-wrap"><table class="offers-reference-table"><thead><tr>${columns.map(([,label])=>`<th>${label}</th>`).join("")}<th>A\u00c7 / D\u00dcZENLE</th></tr></thead><tbody>${data.rows.map((row,index)=>`<tr tabindex="0" data-kind="generic" data-id="${index}" data-generic-row="${index}">${columns.map(([key])=>`<td>${ayecOfferCell(row,key)}</td>`).join("")}<td><button class="mini offer-open" type="button" data-index="${index}">A\u00e7</button> <button class="mini generic-edit" data-index="${index}">D\u00fczenle</button> <button class="mini generic-delete" data-index="${index}">Sil</button></td></tr>`).join("")}</tbody></table></div>`};
const ayecLoadGenericBeforeDesktopOffers=loadGenericModule;
loadGenericModule=async function(meta,q=""){await ayecLoadGenericBeforeDesktopOffers(meta,q);if(meta.table!=="offers")return;$$('.offer-open').forEach(button=>button.onclick=()=>{const row=window.currentGenericData?.rows?.[+button.dataset.index];if(!row)return;const offer=(db.quotes||[]).find(item=>String(item.id)===String(row.id))||row;const customer=(db.customers||[]).find(item=>String(item.id)===String(row.customer_id));openProformaDocument(offer,customer)})};

function renderOfferReports(){const rows=Array.isArray(db.quotes)?db.quotes:[],pending=rows.filter(row=>/bekle|taslak|gonder|pending|draft/i.test(String(row.status||""))).length,accepted=rows.filter(row=>/onay|kabul|approved|accepted/i.test(String(row.status||""))).length,rejected=rows.filter(row=>/red|iptal|reject|cancel/i.test(String(row.status||""))).length,total=rows.reduce((sum,row)=>sum+Number(row.total_try??(row.currency_code==="TRY"?row.total:0)??0),0),months=new Map(),customers=new Map(),staff=new Map();for(const row of rows){const date=String(row.created_at||row.date||"").slice(0,7);if(date){const item=months.get(date)||{count:0,customers:new Set(),staff:new Set(),total:0};item.count++;item.customers.add(row.customer_name||row.company_name||"-");if(row.created_by)item.staff.add(row.created_by);item.total+=Number(row.total_try??(row.currency_code==="TRY"?row.total:0)??0);months.set(date,item)}const customer=row.customer_name||row.company_name||"-",customerItem=customers.get(customer)||{count:0,total:0};customerItem.count++;customerItem.total+=Number(row.total_try??(row.currency_code==="TRY"?row.total:0)??0);customers.set(customer,customerItem);const person=row.created_by||"-",staffItem=staff.get(person)||{count:0,total:0};staffItem.count++;staffItem.total+=Number(row.total_try??(row.currency_code==="TRY"?row.total:0)??0);staff.set(person,staffItem)}const monthRows=[...months.entries()].sort(([a],[b])=>b.localeCompare(a)).slice(0,12).reverse(),customerRows=[...customers.entries()].sort((a,b)=>b[1].total-a[1].total).slice(0,8),staffRows=[...staff.entries()].sort((a,b)=>b[1].total-a[1].total).slice(0,8);const table=(headers,items)=>`<div class="table-wrap"><table><thead><tr>${headers.map(value=>`<th>${value}</th>`).join("")}</tr></thead><tbody>${items||`<tr><td colspan="${headers.length}" class="muted">Hen\u00fcz teklif kayd\u0131 bulunmuyor.</td></tr>`}</tbody></table></div>`;return `${pageHead("Teklif Raporlar\u0131 ve Analizler","Teklif s\u00fcre\u00e7lerini, m\u00fc\u015fteri da\u011f\u0131l\u0131m\u0131n\u0131 ve onay performans\u0131n\u0131 analiz edin.")}<section class="metric-grid offer-report-metrics">${metric("Toplam Teklifler",rows.length,"Toplam kay\u0131t","\u25a3")}${metric("Onay Bekliyor",pending,"\u0130nceleme s\u0131ras\u0131nda","\u25f7")}${metric("Onayland\u0131",accepted,"Kabul edilen","\u2713")}${metric("Reddedildi",rejected,"Reddedilen veya iptal","\u2212")}</section><section class="card offer-report-total"><strong>${money(total,"TRY")}</strong><span>Toplam Teklif De\u011feri (TL)</span></section><div class="offer-report-layout"><section class="card offer-report-panel"><h3>Son 12 Ay Teklif Trendi</h3>${table(["Ay","Teklif Say\u0131s\u0131","Teklif Verilenler","Haz\u0131rlayan Personel","Toplam TL"],monthRows.map(([month,item])=>`<tr><td>${esc(month)}</td><td>${item.count}</td><td title="${esc([...item.customers].join(", "))}">${esc([...item.customers].slice(0,3).join(", "))}${item.customers.size>3?` +${item.customers.size-3}`:""}</td><td>${esc([...item.staff].join(", ")||"-")}</td><td>${money(item.total,"TRY")}</td></tr>`).join(""))}</section><div class="offer-report-ranks"><section class="card offer-report-panel"><h3>En Cok Teklif Verilen M\u00fc\u015fteriler</h3>${table(["M\u00fc\u015fteri / Firma","Teklif Say\u0131s\u0131","Toplam TL"],customerRows.map(([name,item])=>`<tr><td>${esc(name)}</td><td>${item.count}</td><td>${money(item.total,"TRY")}</td></tr>`).join(""))}</section><section class="card offer-report-panel"><h3>En Cok Teklif Haz\u0131rlayan Personeller</h3>${table(["Personel","Teklif Say\u0131s\u0131","Toplam TL"],staffRows.map(([name,item])=>`<tr><td>${esc(name)}</td><td>${item.count}</td><td>${money(item.total,"TRY")}</td></tr>`).join(""))}</section></div></div>`}
const ayecRenderBeforeDesktopOfferReports=render;
render=function(){ayecRenderBeforeDesktopOfferReports();if(page==="offer-reports"){$("#content").innerHTML=renderOfferReports();document.body.dataset.page=page}};





const ayecRenderSettingsBeforeSectionTitle = renderSettings;
renderSettings = function() {
  const selected = settingsGroups.flatMap(([, items]) => items).find(([id]) => id === settingsSection);
  if (page === "settings" && selected) $("#pageTitle").textContent = selected[2];
  return ayecRenderSettingsBeforeSectionTitle();
};
const ayecNavigateBeforeSettingsSectionTitle = navigate;
navigate = function(next) {
  ayecNavigateBeforeSettingsSectionTitle(next);
  const selected = settingsGroups.flatMap(([, items]) => items).find(([id]) => id === settingsSection);
  if (next === "settings" && selected) $("#pageTitle").textContent = selected[2];
};

async function p9TelegramSaveAndStart(root,button){
 const controls=Array.from(root.querySelectorAll(".exact-setting"));
 const token=root.querySelector('[data-setting-key="telegram_bot_token"]')?.value.trim()||"";
 button.disabled=true;
 try{
  for(const control of controls){
   let value=control.type==="checkbox"?(control.checked?"1":"0"):control.value;
   const scope=control.dataset.settingScope||"settings";
   let key=control.dataset.settingKey;
   if(control.type==="password"&&!value)continue;
   if(control.type==="password"&&value.length<4){toast("Bot token is too short.","error");return}
   await desktopWrite(scope,{key,value});
   if(scope==="settings")desktopSettings[key]=control.type==="password"?"":value;
   else desktopInternalSettings[key]=value;
  }
  if(!token){toast("Enter a Telegram bot token before starting the bot.","error");return}
  await apiFetch("/api/desktop/telegram/webhook",{method:"POST",body:JSON.stringify({token,url:"https://api.ayecpro.com.tr/v4/telegram/webhook/inbound",drop_pending_updates:false})});
  const status=root.querySelector(".p9-telegram-state");
  if(status)status.textContent="BOT DURUMU: WEBHOOK AKTIF";
  await p9TelegramRecordActivity(root,"Webhook target configured");
  toast("Settings saved and Telegram webhook started.","success");
 }catch(error){toast("Telegram setup failed: "+error.message,"error")}
 finally{button.disabled=false}
}
async function p9TelegramRecordActivity(root,message){
 let events=[];try{events=JSON.parse(desktopSettings.telegram_activity_log||"[]");if(!Array.isArray(events))events=[];events=events.filter(item=>item&&typeof item==="object"&&!Array.isArray(item))}catch{}
 const event={at:new Date().toISOString(),message:String(message).slice(0,180)};events.unshift(event);const value=JSON.stringify(events.slice(0,100));desktopSettings.telegram_activity_log=value;
 try{await desktopWrite("settings",{key:"telegram_activity_log",value})}catch{return}
 const row=root?.querySelector(".p9-telegram-logs .p9-log-row:last-child");if(row){row.querySelector("span").textContent=event.message;row.querySelector("small").textContent=event.at}
}
function p9TelegramShowActivity(root){
 let events=[];try{events=JSON.parse(desktopSettings.telegram_activity_log||"[]");if(!Array.isArray(events))events=[];events=events.filter(item=>item&&typeof item==="object"&&!Array.isArray(item))}catch{}
 const detail=events.slice(0,20).map(item=>`${item.at||""}  ${item.message||""}`).join("\n");window.alert(detail||"No Telegram activity has been recorded yet.")
}
document.addEventListener("click",async event=>{const test=event.target.closest("[data-p9-telegram-test]");if(test){const token=document.querySelector('[data-setting-key="telegram_bot_token"]')?.value.trim()||"";if(!token){toast("Enter a Telegram bot token first.","error");return}test.disabled=true;try{const result=await apiFetch("/api/desktop/telegram/test",{method:"POST",body:JSON.stringify({token})});const username=String(result.username||"").replace(/^@/,"");const status=document.querySelector(".p9-telegram-state");if(status)status.textContent=username?`BOT DURUMU: @${username}`:"BOT DURUMU: CEVRIMICI";const root=test.closest(".p9-telegram"),rows=root?.querySelectorAll(".p9-telegram-logs .p9-log-row")||[];await p9TelegramRecordActivity(root,"Bot API connection verified");const statusCard=root?.querySelector(".p9-telegram-status div:nth-child(3)");try{const info=await apiFetch("/api/desktop/telegram/status",{method:"POST",body:JSON.stringify({token})});if(statusCard){statusCard.querySelector("strong").textContent=info.url?"WEBHOOK ACTIVE":"API CONNECTED";statusCard.querySelector("small").textContent=info.last_error_message||`Pending updates: ${info.pending_update_count}`}}catch(error){if(statusCard){statusCard.querySelector("strong").textContent="API CONNECTED";statusCard.querySelector("small").textContent="Webhook status unavailable"}}toast(username?`Telegram baglantisi dogrulandi: @${username}`:"Telegram bot baglantisi dogrulandi.","success")}catch(error){await p9TelegramRecordActivity(test.closest(".p9-telegram"),"Bot API connection failed");toast("Telegram baglantisi basarisiz: "+error.message,"error")}finally{test.disabled=false}return}const clear=event.target.closest("[data-p9-telegram-clear]");if(clear){const token=document.querySelector('[data-setting-key="telegram_bot_token"]');const chat=document.querySelector("#p9TelegramChatInput");if(token)token.value="";if(chat)chat.value="";toast("Telegram formu temizlendi.");return}const saveAndStart=event.target.closest("[data-p9-save-settings]");if(saveAndStart){const root=saveAndStart.closest(".p9-telegram");if(root)p9TelegramSaveAndStart(root,saveAndStart)}},true);

const p9ProjectState = {projects: [], units: [], unitProducts: [], transactions: [], team: [], selectedId: null, tab: "units", loaded: false, loading: false, error: ""};
const p9FinanceView = {query: "", type: "all", category: "all", channel: "all", status: "all", date: "all", density: "comfortable"};
const p9UnitsView = {query: "", status: "all", mode: "grid"};
function p9CurrentProject() { return p9ProjectState.projects.find(item => String(item.id) === String(p9ProjectState.selectedId)) || p9ProjectState.projects[0] || null; }
function p9ProjectMoney(value) { return new Intl.NumberFormat("tr-TR", {style: "currency", currency: "TRY", maximumFractionDigits: 0}).format(Number(value) || 0); }
function renderPart9Projects() {
  setTimeout(loadPart9Projects, 0);
  const project = p9CurrentProject();
  const units = p9ProjectState.units.filter(item => String(item.project_id) === String(project?.id));
  const transactions = p9ProjectState.transactions.filter(item => String(item.project_id) === String(project?.id));
  const team = p9ProjectState.team.filter(item => String(item.project_id) === String(project?.id));
  const productTotal = p9ProjectState.unitProducts.filter(item => units.some(unit => String(unit.id) === String(item.unit_id))).reduce((sum, item) => sum + (Number(item.quantity) || 1), 0);
  const isSettled = item => ["odendi", "tahsil edildi", "tahsil"].includes(String(item.status || "").toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, ""));
  const income = transactions.filter(item => String(item.type).toLocaleLowerCase("tr-TR") === "gelir" && isSettled(item)).reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  const expense = transactions.filter(item => String(item.type).toLocaleLowerCase("tr-TR") === "gider" && isSettled(item)).reduce((sum, item) => sum + (Number(item.amount) || 0), 0);
  const budget = Number(project?.budget) || 0;
  const budgetPercent = budget ? Math.min(100, Math.round(income / budget * 100)) : 0;
  let body = "";
  if (p9ProjectState.error) body = `<p class="p9-project-empty">${esc(p9ProjectState.error)}</p>`;
  else if (p9ProjectState.tab === "units") {
    const norm = value => String(value || "").toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const statusKey = item => norm(item.status);
    const matchingUnits = units.filter(unit => {
      const productCount = p9ProjectState.unitProducts.filter(row => String(row.unit_id) === String(unit.id)).reduce((sum, row) => sum + (Number(row.quantity) || 1), 0);
      const searchable = [unit.unit_no, unit.block_name, unit.floor_no, unit.direction, unit.room_names, unit.responsible_name, productCount].map(norm).join(" ");
      const statusMatch = p9UnitsView.status === "all" || (p9UnitsView.status === "active" && statusKey(unit).includes("devam")) || (p9UnitsView.status === "completed" && statusKey(unit).includes("tamam"));
      return statusMatch && (!p9UnitsView.query || searchable.includes(norm(p9UnitsView.query)));
    });
    const statuses = [["all", `T\u{fc}m\u{fc} (${units.length})`], ["active", `Devam Eden (${units.filter(unit => statusKey(unit).includes("devam")).length})`], ["completed", `Tamamlanan (${units.filter(unit => statusKey(unit).includes("tamam")).length})`]];
    const blocks = [...new Set(matchingUnits.map(unit => unit.block_name || "A Blok"))];
    const card = unit => {
      const products = p9ProjectState.unitProducts.filter(row => String(row.unit_id) === String(unit.id));
      const count = Number(unit.product_count) || products.reduce((sum, row) => sum + (Number(row.quantity) || 1), 0);
      const status = unit.status || "Bekliyor";
      const normalizedStatus = statusKey(unit);
      const progress = Math.max(0, Math.min(100, Number(unit.completion_percent ?? unit.progress ?? (normalizedStatus.includes("tamam") ? 100 : normalizedStatus.includes("devam") ? 50 : 0))));
      const rooms = unit.room_names || unit.rooms_text || (unit.room_count ? `${unit.room_count} Oda` : "Oda tan\u{131}mlanmam\u{131}\u{15f}");
      const lead = unit.responsible_name || unit.site_manager || unit.assigned_to || "Atanmad\u{131}";
      const floor = unit.floor_no ? `Kat ${esc(unit.floor_no)}` : "Kat bilgisi yok";
      const direction = unit.direction || unit.unit_kind || unit.unit_type || "Daire";
      return `<article class="p9-unit-card p9-architect-card" data-unit="${esc(unit.unit_no || unit.id)}"><header><div class="p9-unit-ident"><span>${esc((unit.block_name || "A").trim().slice(0, 1))}</span><div><strong>Daire ${esc(unit.unit_no || unit.id)}</strong><small>${floor} \u{2022} ${esc(direction)}</small></div></div><span class="p9-unit-status ${normalizedStatus.includes("tamam") ? "complete" : normalizedStatus.includes("devam") ? "active" : "pending"}">${esc(status)}</span></header><div class="p9-unit-details"><div><span>\u{2699} Kurulu Cihaz</span><b>${count ? `${count} Cihaz` : "0 \u{dc}r\u{fc}n"}</b></div><div><span>\u{25a3} Oda / B\u{f6}l\u{fc}m</span><b title="${esc(rooms)}">${esc(rooms)}</b></div><div><span>\u{2659} Saha Sorumlusu</span><b>${esc(lead)}</b></div></div><div class="p9-unit-install"><div><span>Fiziksel Kurulum</span><b>%${progress}</b></div><progress max="100" value="${progress}"></progress></div><footer><button class="primary" data-p9-unit-products="${esc(unit.id)}">\u{25a3} \u{dc}r\u{fc}nleri G\u{f6}r / Ekle</button><button title="Daireyi d\u{fc}zenle" data-p9-unit-edit="${esc(unit.id)}" data-current-status="${esc(status)}">\u{270e}</button><button title="QR kod" data-p9-unit-qr="${esc(unit.id)}">\u{25a6}</button></footer></article>`;
    };
    body = `<section class="p9-units"><div class="p9-units-toolbar"><div class="p9-units-actions"><button class="primary" data-p9-add-unit>+ Blok ve Daire Olu\u{15f}tur</button><button data-p9-add-unit>+ Tekil Daire / Oda Ekle</button>${statuses.map(([id, label]) => `<button data-p9-unit-status="${id}" class="p9-unit-filter ${p9UnitsView.status === id ? "active" : ""}">${label}</button>`).join("")}</div><div class="p9-units-tools"><button data-p9-units-export>\u{25a6} Excel Raporu</button><button data-p9-units-bulk>\u{21bb} Toplu Durum G\u{fc}ncelle</button><button data-p9-units-mode="grid" class="${p9UnitsView.mode === "grid" ? "active" : ""}" title="Kart g\u{f6}r\u{fc}n\u{fc}m\u{fc}">\u{25a6}</button><button data-p9-units-mode="list" class="${p9UnitsView.mode === "list" ? "active" : ""}" title="Kompakt liste">\u{2630}</button></div></div><div class="p9-units-search"><input class="control" id="p9UnitSearch" value="${esc(p9UnitsView.query)}" placeholder="Oda / daire ara... (\u{f6}rn: A-1, B-4, Salon, Engin)"><span>ESC</span><div>\u{21b5} \u{c7}ift t\u{131}k: \u{dc}r\u{fc}n ekle <i>/</i> \u{25c9} Sa\u{11f} t\u{131}k: Durum de\u{11f}i\u{15f}tir</div></div>${blocks.map(block => { const blockUnits = matchingUnits.filter(unit => (unit.block_name || "A Blok") === block); const progress = blockUnits.length ? Math.round(blockUnits.reduce((sum, unit) => sum + Number(unit.completion_percent ?? unit.progress ?? (statusKey(unit).includes("tamam") ? 100 : statusKey(unit).includes("devam") ? 50 : 0)), 0) / blockUnits.length) : 0; return `<section class="p9-unit-block"><header><span>${esc(block.slice(0, 1))}</span><div><h2>${esc(block)} Daireleri <small>${blockUnits.length} Ba\u{11f}\u{131}ms\u{131}z B\u{f6}l\u{fc}m</small></h2><p>Konut Otomasyonu, Ayd\u{131}nlatma ve HVAC Altyap\u{131} Saha Da\u{11f}\u{131}l\u{131}m\u{131}</p></div><div class="p9-block-progress"><small>Ortalama Tamamlanma</small><b>%${progress}</b><progress max="100" value="${progress}"></progress></div></header><div class="p9-unit-grid ${p9UnitsView.mode === "list" ? "list" : ""}">${blockUnits.map(card).join("") || `<p class="p9-project-empty">Arama ve durum filtrelerinde sonu\u00e7 bulunamad\u0131.</p>`}</div></section>`; }).join("") || `<p class="p9-project-empty">Bu projede hen\u00fcz oda veya daire bulunmuyor.</p>`}</section>`;
  }
  else if (p9ProjectState.tab === "finance") {
    const key = value => String(value || "").toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    const pendingIncome = transactions.filter(item => key(item.type) === "gelir" && !["odendi", "tahsil edildi", "tahsil"].includes(key(item.status))).reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const pendingExpense = transactions.filter(item => key(item.type) === "gider" && !["odendi", "tahsil edildi", "tahsil"].includes(key(item.status))).reduce((sum, item) => sum + Number(item.amount || 0), 0);
    const dateMatches = item => {
      const date = String(item.date || "").slice(0, 10);
      if (p9FinanceView.date === "all") return true;
      if (p9FinanceView.date === "this_month") return date.startsWith("2026-09");
      const today = new Date();
      const todayIso = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
      if (p9FinanceView.date === "today") return date === todayIso;
      if (p9FinanceView.date === "this_week") {
        const start = new Date(today);
        start.setDate(today.getDate() - ((today.getDay() + 6) % 7));
        const startIso = `${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, "0")}-${String(start.getDate()).padStart(2, "0")}`;
        return date >= startIso && date <= todayIso;
      }
      return true;
    };
    const financeRows = transactions.filter(item => {
      const haystack = [item.id, item.description, item.category, item.invoice_no, item.payment_method].map(key).join(" ");
      return dateMatches(item) && (!p9FinanceView.query || haystack.includes(key(p9FinanceView.query))) && (p9FinanceView.type === "all" || key(item.type) === p9FinanceView.type) && (p9FinanceView.category === "all" || key(item.category) === p9FinanceView.category) && (p9FinanceView.channel === "all" || key(item.payment_method).includes(p9FinanceView.channel)) && (p9FinanceView.status === "all" || key(item.status).includes(p9FinanceView.status));
    });
    const categories = [["all", "T\u{fc}m Hareketler"], ["gelir", "Gelir"], ["gider", "Gider"], ["avans", "Avans"], ["hakedis", "Hakedi\u{15f}"], ["malzeme", "Malzeme"], ["iscilik", "\u{130}\u{15f}\u{e7}ilik"]];
    body = `<section class="p9-finance"><header class="p9-finance-heading"><div><div class="p9-finance-title"><span class="p9-finance-icon">\u{25a4}</span><div><h2>Proje Finans Durumu &amp; Nakit Ak\u{131}\u{15f}\u{131} <small>CANLI DEFTER</small></h2><p>\u{15e}antiye Maliyet Muhasebesi \u{2022} Fatura Takibi \u{2022} Hakedi\u{15f} &amp; Avans Mutabakat\u{131}</p></div></div></div><div class="p9-finance-actions"><button data-p9-add-transaction="Gelir" class="income">+ Gelir Ekle</button><button data-p9-add-transaction="Gider" class="expense">- Gider Ekle</button><button data-p9-finance-export="pdf">PDF Raporu \u{130}ndir</button><button data-p9-finance-export="csv">Excel D\u{f6}k\u{fc}m\u{fc}</button></div></header>
    <div class="p9-finance-kpis"><article class="income"><label>Tahsil Edilen Gelir</label><strong>${p9ProjectMoney(income)}</strong><small>${transactions.filter(x => key(x.type) === "gelir" && ["odendi", "tahsil edildi", "tahsil"].includes(key(x.status))).length} tahsilat</small></article><article class="expense"><label>\u{d6}denen Gider</label><strong>${p9ProjectMoney(expense)}</strong><small>${transactions.filter(x => key(x.type) === "gider" && ["odendi", "tahsil edildi", "tahsil"].includes(key(x.status))).length} kalem</small></article><article class="net"><label>Net K\u{e2}r / Finansal Denge</label><strong>${p9ProjectMoney(income - expense)}</strong><small>Marj %${income ? ((income - expense) / income * 100).toFixed(1) : "0.0"}</small></article><article class="pending"><label>Bekleyen Gelir</label><strong>${p9ProjectMoney(pendingIncome)}</strong><small>Vade ve tahsilat takibi</small></article><article class="pending-expense"><label>Bekleyen Gider</label><strong>${p9ProjectMoney(pendingExpense)}</strong><small>Planlanan bor\u{e7}</small></article></div>
    <div class="p9-finance-budget"><div class="p9-budget-mark">\u{25c9}</div><div class="p9-budget-main"><div><strong>Proje B\u{fc}t\u{e7}e Ger\u{e7}ekle\u{15f}me Oran\u{131}</strong><span>${budgetPercent}% Ger\u{e7}ekle\u{15f}en (Hedef: ${p9ProjectMoney(budget)})</span></div><progress max="100" value="${budgetPercent}"></progress><div><small>Tahsil Edilen: ${p9ProjectMoney(income)}</small><small>A\u{e7}\u{131}k Mutabakat: ${p9ProjectMoney(pendingIncome)}</small></div></div><div class="p9-budget-stats"><span>Nakit/Banka: ${p9ProjectMoney(income - expense)}</span><span>Hakedi\u{15f} Avans: ${p9ProjectMoney(pendingIncome)}</span><span>Bor\u{e7}/Alacak Denge: ${p9ProjectMoney(income - expense)}</span></div></div>
    <section class="p9-finance-ledger"><div class="p9-finance-filterline"><input class="control" id="p9FinanceSearch" value="${esc(p9FinanceView.query)}" placeholder="\u{130}\u{15f}lem no, a\u{e7}\u{131}klama, fatura veya cari ara..."><select class="control" id="p9FinanceDate"><option value="all">T\u{fc}m Tarihler</option><option value="today">Bug\u{fc}n</option><option value="this_week">Bu Hafta</option><option value="this_month">Eyl\u{fc}l 2026</option></select><select class="control" id="p9FinanceType"><option value="all">T\u{fc}m T\u{fc}rler</option><option value="gelir">Gelir</option><option value="gider">Gider</option></select><select class="control" id="p9FinanceCategory"><option value="all">T\u{fc}m Kategoriler</option>${["Avans", "Hakedi\u{15f}", "Malzeme", "\u{130}\u{15f}\u{e7}ilik"].map(v => `<option value="${key(v)}">${v}</option>`).join("")}</select><select class="control" id="p9FinanceChannel"><option value="all">T\u{fc}m \u{d6}deme Kanallar\u{131}</option><option value="banka">Banka Transferi</option><option value="nakit">Nakit Kasa</option><option value="kredi">Kredi Kart\u{131} / \u{c7}ek</option></select><select class="control" id="p9FinanceStatus"><option value="all">T\u{fc}m Durumlar</option><option value="odendi">Tahsil Edildi / \u{d6}dendi</option><option value="bekliyor">Bekliyor</option><option value="iptal">\u{130}ptal / \u{130}ade</option></select><button title="Filtreleri temizle" data-p9-finance-reset>\u{21ba}</button></div><div class="p9-finance-categories">${categories.map(([id, label]) => `<button data-p9-finance-category="${id}" class="${(p9FinanceView.type === id || (id === "all" && p9FinanceView.type === "all" && p9FinanceView.category === "all")) ? "active" : ""}">${label}<small>${id === "all" ? transactions.length : transactions.filter(x => key(x.type) === id || key(x.category) === id).length}</small></button>`).join("")}<div class="p9-finance-viewtools"><button data-p9-density="comfortable" class="${p9FinanceView.density === "comfortable" ? "active" : ""}">Sat\u{131}r aral\u{131}\u{11f}\u{131}</button><button data-p9-finance-columns>Kolonlar \u{2699}</button></div></div><div class="p9-finance-table-wrap"><table class="p9-finance-table ${p9FinanceView.density}"><thead><tr><th>#</th><th>i\u{15e}LEM TAR\u{130}H\u{130}</th><th>T\u{dc}R</th><th>KATEGOR\u{130}</th><th>A\u{c7}IKLAMA / DETAY</th><th>\u{d6}DEME KANALI</th><th>VADE / BELGE NO</th><th>TUTAR &amp; DURUM</th></tr></thead><tbody>${financeRows.map((item, index) => `<tr><td>${String(index + 1).padStart(2, "0")}</td><td>${esc(item.date || "-")}</td><td><span class="p9-finance-type ${key(item.type)}">${esc(item.type || "-")}</span></td><td>${esc(item.category || "-")}</td><td><strong>${esc(item.description || "-")}</strong><small>${esc(item.counterparty || item.supplier || `Proje: ${project?.name || "-"}`)}</small></td><td>${esc(item.payment_method || "-")}</td><td>${esc([item.due_date, item.invoice_no || item.document_no].filter(Boolean).join(" / ") || "-")}</td><td><strong>${p9ProjectMoney(item.amount)}</strong><small class="p9-status ${key(item.status)}">${esc(item.status || "-")}</small></td></tr>`).join("") || `<tr><td colspan="8" class="p9-finance-empty">Filtrelerle e\u{15f}le\u{15f}en hareket yok.</td></tr>`}</tbody></table></div><footer class="p9-finance-footer"><span>${financeRows.length} hareket g\u{f6}steriliyor / ${transactions.length}</span><span>Nakit / Banka: ${p9ProjectMoney(income - expense)}</span><strong>Net denge: ${p9ProjectMoney(income - expense)}</strong><div><button disabled>\u{2039}</button><button class="active">1</button><button disabled>\u{203a}</button></div></footer></section><aside class="p9-finance-sync"><strong>E-Fatura &amp; Mali Senkronizasyon Durumu</strong><span>Proje finans hareketleri ortak veritaban\u{131}nda saklan\u{131}r.</span><b>\u{25cf} Senkronize</b></aside></section>`;
  }
  else if (p9ProjectState.tab === "team") body = `<div class="p9-project-toolbar"><strong>Proje Ekip Yonetimi</strong><button class="primary" data-p9-add-member>+ Ekip Uyesi Ekle</button></div><div class="table-wrap p9-project-table"><table><thead><tr><th>AD SOYAD / FIRMA</th><th>UZMANLIK ALANI</th><th>SOZLESME TUTARI</th><th>ILETISIM</th><th>\u0130\u015eLEMLER</th></tr></thead><tbody>${team.map(item => `<tr><td>${esc(item.name || "-")}</td><td>${esc(item.job_type || "-")}</td><td>${p9ProjectMoney(item.total_contract_amount)}</td><td>${esc(item.contact_info || "-")}</td><td><button class="mini" data-p9-team-delete="${esc(item.id)}">Kaldir</button></td></tr>`).join("") || `<tr><td colspan="5">Projeye atanmis ekip uyesi yok.</td></tr>`}</tbody></table></div>`;
  else body = `<p class="p9-project-empty">Bu projede cihaz envanteri kaydi bulunmuyor.</p>`;
  const projectOptions = p9ProjectState.projects.map(item => `<option value="${esc(item.id)}" ${String(item.id) === String(project?.id) ? "selected" : ""}>${esc(item.name || "Proje")}</option>`).join("");
  const tabs = [["units", "Kurulum & Odalar"], ["finance", "Finans Durumu"], ["team", "Ekip Yonetimi"]];
  return `${pageHead(project?.name || "Proje Yonetimi", "Proje, oda, ekip ve butce yonetimi.", '<button class="secondary" data-p9-project-refresh>Yenile</button>')}<div class="p9-project-screen"><header class="p9-project-top"><strong>${esc(project?.name || "Projeler")}</strong><select id="p9ProjectSelect">${projectOptions}</select><span>${units.length} Oda</span><span>${units.filter(item => String(item.status || "").toLocaleLowerCase("tr-TR").includes("tamam")).length} Tamamlandi</span><span>${units.filter(item => !String(item.status || "").toLocaleLowerCase("tr-TR").includes("tamam")).length} Devam Ediyor</span><span>${productTotal} Urun Kurulu</span><span>${team.length} Ekip Uyesi</span><button class="primary" data-p9-add-project>+ Proje Ekle</button></header><div class="p9-project-layout"><aside class="p9-project-nav"><label>Aktif Santiye</label><strong>${esc(project?.name || "Proje secin")}</strong>${tabs.map(([id, label]) => `<button data-p9-project-tab="${id}" class="${p9ProjectState.tab === id ? "active" : ""}">${label}</button>`).join("")}<button data-p9-project-tab="inventory" class="${p9ProjectState.tab === "inventory" ? "active" : ""}">Cihaz Envanteri</button><button data-p9-project-tab="settings" class="${p9ProjectState.tab === "settings" ? "active" : ""}">Santiye Ayarlari</button></aside><section class="p9-project-main"><nav class="p9-project-tabs">${tabs.map(([id, label]) => `<button data-p9-project-tab="${id}" class="${p9ProjectState.tab === id ? "active" : ""}">${label}</button>`).join("")}</nav><div id="p9ProjectBody">${body}</div></section></div><input id="genericSearch" hidden><div id="genericTable" hidden></div></div>`;
}
async function loadPart9Projects() {
  if (p9ProjectState.loading || p9ProjectState.loaded) return;
  p9ProjectState.loading = true;
  try {
    const names = ["projects", "project_units", "project_transactions", "subcontractors", "project_unit_products"];
    const result = await Promise.all(names.map(name => apiFetch(`/api/desktop/table/${name}?limit=1000`)));
    [p9ProjectState.projects, p9ProjectState.units, p9ProjectState.transactions, p9ProjectState.team, p9ProjectState.unitProducts] = result.map(item => item.rows || []);
    if (!p9ProjectState.selectedId && p9ProjectState.projects.length) p9ProjectState.selectedId = p9ProjectState.projects[0].id;
    p9ProjectState.error = "";
    p9ProjectState.loaded = true;
  } catch (error) { p9ProjectState.error = "Proje verileri okunamadi: " + error.message; }
  finally { p9ProjectState.loading = false; if ($(".p9-project-screen")) render(); }
}
const p9GenericShellBefore = genericShell;
genericShell = function(meta) { return meta.table === "projects" ? renderPart9Projects() : p9GenericShellBefore(meta); };
document.addEventListener("change", event => {
  if (event.target.id === "p9ProjectSelect") { p9ProjectState.selectedId = event.target.value; render(); return; }
  const financeFilter = {p9FinanceDate: "date", p9FinanceType: "type", p9FinanceCategory: "category", p9FinanceChannel: "channel", p9FinanceStatus: "status"}[event.target.id];
  if (financeFilter) { p9FinanceView[financeFilter] = event.target.value; render(); return; }
  const form = event.target.closest(".p9-member-form");
  if (!form) return;
  const unitInputs = [...form.querySelectorAll('input[name="assigned_units"]')];
  const all = form.querySelector("[data-p9-member-all]");
  const block = event.target.dataset.p9MemberGroup;
  const groups = [...form.querySelectorAll("[data-p9-member-group]")];
  if (event.target.matches("[data-p9-member-all]")) {
    unitInputs.forEach(input => { input.checked = event.target.checked; });
    groups.forEach(group => { group.checked = false; });
  } else if (block) {
    if (event.target.checked && all?.checked) unitInputs.forEach(input => { input.checked = false; });
    unitInputs.filter(input => input.dataset.blockKey === block).forEach(input => { input.checked = event.target.checked; });
    if (all) all.checked = unitInputs.length > 0 && unitInputs.every(input => input.checked);
    groups.forEach(group => { const members = unitInputs.filter(input => input.dataset.blockKey === group.dataset.p9MemberGroup); group.checked = !all?.checked && members.length > 0 && members.every(input => input.checked); });
  } else {
    if (all) all.checked = unitInputs.length > 0 && unitInputs.every(input => input.checked);
    groups.forEach(group => { const members = unitInputs.filter(input => input.dataset.blockKey === group.dataset.p9MemberGroup); group.checked = !all?.checked && members.length > 0 && members.every(input => input.checked); });
  }
});
document.addEventListener("click", async event => {
  const financeCategory = event.target.closest("[data-p9-finance-category]"), financeReset = event.target.closest("[data-p9-finance-reset]"), financeExport = event.target.closest("[data-p9-finance-export]"), financeColumns = event.target.closest("[data-p9-finance-columns]");
  const unitStatus = event.target.closest("[data-p9-unit-status]"), unitMode = event.target.closest("[data-p9-units-mode]"), unitExport = event.target.closest("[data-p9-units-export]"), unitBulk = event.target.closest("[data-p9-units-bulk]"), unitEdit = event.target.closest("[data-p9-unit-edit]"), unitQr = event.target.closest("[data-p9-unit-qr]");
  if (unitStatus) { p9UnitsView.status = unitStatus.dataset.p9UnitStatus; render(); return; }
  if (unitMode) { p9UnitsView.mode = unitMode.dataset.p9UnitsMode; render(); return; }
  if (unitExport) {
    const rows = p9ProjectState.units.filter(item => String(item.project_id) === String(p9CurrentProject()?.id));
    const csv = ["Blok;Daire;Kat;Tur;Durum;Sorumlu", ...rows.map(item => [item.block_name, item.unit_no, item.floor_no, item.unit_kind || item.unit_type, item.status, item.responsible_name || item.assigned_to].map(value => `"${String(value || "").replaceAll('"', '""')}"`).join(";"))].join("\r\n");
    const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob(["\ufeff", csv], {type: "text/csv;charset=utf-8"})); link.download = "proje-daireleri.csv"; link.click(); URL.revokeObjectURL(link.href); return;
  }
  if (unitBulk || unitEdit) {
    const projectUnits = p9ProjectState.units.filter(item => String(item.project_id) === String(p9CurrentProject()?.id));
    const selected = unitEdit ? projectUnits.filter(item => String(item.id) === String(unitEdit.dataset.p9UnitEdit)) : projectUnits;
    const nextStatus = prompt("Yeni durum (Devam Ediyor, Tamamlandi, Bekliyor)", unitEdit?.dataset.currentStatus || "Devam Ediyor");
    if (!nextStatus || !selected.length) return;
    try { for (const item of selected) await apiFetch("/api/desktop/table/project_units", {method: "POST", body: JSON.stringify({id: Number(item.id), status: nextStatus, _action: "update"})}); p9ProjectState.loaded = false; await loadPart9Projects(); }
    catch (error) { toast("Daire durumu guncellenemedi: " + error.message, "error"); }
    return;
  }
  if (unitQr) { const unit = p9ProjectState.units.find(item => String(item.id) === String(unitQr.dataset.p9UnitQr)); if (unit) openDialog("Daire QR Bilgisi", "UNIT ID", `<div class="p9-unit-qr-code">${esc(unit.block_name || "")} ${esc(unit.unit_no || unit.id)}</div>`); return; }
  if (financeCategory) { const value = financeCategory.dataset.p9FinanceCategory; p9FinanceView.type = ["gelir", "gider"].includes(value) ? value : "all"; p9FinanceView.category = ["avans", "hakedis", "malzeme", "iscilik"].includes(value) ? value : "all"; render(); return; }
  if (financeReset) { Object.assign(p9FinanceView, {query: "", type: "all", category: "all", channel: "all", status: "all", date: "all"}); render(); return; }
  if (financeColumns) { const table = document.querySelector(".p9-finance-table"); if (table) table.classList.toggle("p9-columns-compact"); return; }
  if (financeExport) {
    const rows = p9ProjectState.transactions.filter(item => String(item.project_id) === String(p9CurrentProject()?.id));
    if (financeExport.dataset.p9FinanceExport === "csv") { const csv = ["Tarih;Tur;Kategori;Aciklama;Odeme;Tutar;Durum", ...rows.map(x => [x.date, x.type, x.category, x.description, x.payment_method, x.amount, x.status].map(v => `"${String(v || "").replaceAll('"', '""')}"`).join(";"))].join("\r\n"); const link = document.createElement("a"); link.href = URL.createObjectURL(new Blob(["\ufeff", csv], {type: "text/csv;charset=utf-8"})); link.download = "proje-finans.csv"; link.click(); URL.revokeObjectURL(link.href); }
    else window.print();
    return;
  }
  const unitToggle = event.target.closest("[data-p9-member-units-toggle]");
  if (unitToggle) { const list = unitToggle.closest(".field").querySelector(".p9-member-unit-list"); if (list) { list.hidden = !list.hidden; unitToggle.textContent = list.hidden ? "+ Ekle" : "Gizle"; } return; }
  const tab = event.target.closest("[data-p9-project-tab]"), refresh = event.target.closest("[data-p9-project-refresh]"), addProject = event.target.closest("[data-p9-add-project]"), addUnit = event.target.closest("[data-p9-add-unit]"), addTransaction = event.target.closest("[data-p9-add-transaction]"), addMember = event.target.closest("[data-p9-add-member]"), deleteMember = event.target.closest("[data-p9-team-delete]");
  if (tab) { p9ProjectState.tab = tab.dataset.p9ProjectTab; render(); return; }
  if (!refresh && !addProject && !addUnit && !addTransaction && !addMember && !deleteMember) return;
  const project = p9CurrentProject();
  try {
    if (refresh) p9ProjectState.loaded = false;
    else if (addProject) { const name = prompt("Proje adi"); if (!name?.trim()) return; await apiFetch("/api/desktop/table/projects", {method: "POST", body: JSON.stringify({name: name.trim(), status: "Devam Ediyor", budget: 0})}); p9ProjectState.loaded = false; }
    else if (addUnit) { if (!project) return; const unit_no = prompt("Daire veya oda numarasi"); if (!unit_no?.trim()) return; const block_name = prompt("Blok adi", "A Blok") || "A Blok"; await apiFetch("/api/desktop/table/project_units", {method: "POST", body: JSON.stringify({project_id: project.id, block_name, unit_no: unit_no.trim(), status: "Devam Ediyor", unit_kind: "Daire"})}); p9ProjectState.loaded = false; }
    else if (addTransaction) { if (!project) return; const amount = Number(prompt(addTransaction.dataset.p9AddTransaction + " tutari")); if (!Number.isFinite(amount) || amount <= 0) return; const description = prompt("Islem aciklamasi") || ""; await apiFetch("/api/desktop/table/project_transactions", {method: "POST", body: JSON.stringify({project_id: project.id, type: addTransaction.dataset.p9AddTransaction, amount, date: today(), description, status: "Odenmedi"})}); p9ProjectState.loaded = false; }
    else if (addMember) {
      if (!project) return;
      const units = p9ProjectState.units.filter(item => String(item.project_id) === String(project.id));
      const blockGroups = new Map();
      units.forEach((unit, index) => { const block = String(unit.block_name || "Blok"); if (!blockGroups.has(block)) blockGroups.set(block, []); blockGroups.get(block).push({unit, index}); });
      const unitInputs = units.map((unit, index) => `<label class="p9-member-unit"><input type="checkbox" name="assigned_units" value="${esc(unit.id)}" data-block-key="${esc(unit.block_name || "Blok")}" checked><span>${esc(unit.block_name || "Blok")} ${esc(unit.unit_no || unit.id)}</span></label>`).join("");
      const blockOptions = Array.from(blockGroups, ([block]) => `<label class="p9-member-unit p9-member-zone"><input type="checkbox" data-p9-member-group="${esc(block)}"><span>${esc(block)}</span></label>`).join("");
      const rangeOptions = Array.from(blockGroups, ([block, entries]) => { if (entries.length < 2) return ""; const suffix = block.match(/(?:Blok\s+)?([A-Z0-9]+)/i)?.[1] || block; const numbers = entries.map(entry => String(entry.unit.unit_no || entry.unit.id)).map(value => value.replace(new RegExp("^" + suffix + "[- ]?", "i"), "")).sort((a, b) => a.localeCompare(b, undefined, {numeric:true})); const range = `Daire ${suffix}-${numbers[0]} - ${suffix}-${numbers[numbers.length - 1]}`; return `<label class="p9-member-unit p9-member-zone"><input type="checkbox" data-p9-member-group="${esc(block)}"><span>${esc(range)}</span></label>`; }).join("");
      const unitOptions = units.length ? `<div class="p9-member-unit-groups"><label class="p9-member-unit p9-member-zone p9-member-all"><input type="checkbox" data-p9-member-all checked><span>T\u00fcm Proje \u00d7</span></label>${blockOptions}${rangeOptions}<button type="button" data-p9-member-units-toggle>+ Ekle</button></div><div class="p9-member-unit-list" hidden>${unitInputs}</div>` : '<span class="muted">No units are registered for this project.</span>';
      openDialog("Ekip \u00dcyesi / Ta\u015feron Ekle", "Projeye uzman ta\u015feron, usta veya saha teknikeri atan\u0131n", `<div class="p9-member-form"><div class="field full"><label>Ad Soyad / Firma Ad\u0131 *</label><input name="name" required placeholder="\u00d6rn. Ahmet Y\u0131lmaz veya TechEv \u00c7\u00f6z\u00fcmleri Ltd."></div><div class="field full"><label>Uzmanl\u0131k Alan\u0131 *</label><select name="job_type" required><option>\u26a1 Elektrik Tesisat\u0131</option><option>\ud83c\udfe0 Ak\u0131ll\u0131 Ev Otomasyonu (KNX &amp; Zigbee)</option><option>\ud83c\udf10 A\u011f &amp; Yap\u0131sal Kablolama</option><option>\ud83d\udcf9 Kamera &amp; G\u00fcvenlik Sistemleri</option><option>\ud83c\udfa8 Boya &amp; Al\u00e7\u0131pan / \u0130nce \u0130\u015f\u00e7ilik</option><option>\u2744\ufe0f \u0130klimlendirme &amp; Havaland\u0131rma</option></select></div><section class="p9-member-payment"><strong>\u00dccretlendirme Modeli &amp; S\u00f6zle\u015fme Tutar\u0131</strong><div class="p9-member-payment-options"><label><input type="radio" name="payment_model" value="fixed" checked><span>G\u00f6t\u00fcr\u00fc / Sabit Fiyat</span></label><label><input type="radio" name="payment_model" value="daily"><span>G\u00fcnl\u00fck Yevmiye</span></label><label><input type="radio" name="payment_model" value="unit"><span>Daire Ba\u015f\u0131</span></label></div><div class="p9-member-amounts p9-member-total"><div class="p9-member-price-input"><label for="p9MemberAmount">S\u00f6zle\u015fme Bedeli:</label><input id="p9MemberAmount" name="total_contract_amount" type="text" inputmode="decimal" placeholder="0,00" value="0,00"></div><select name="currency"><option value="TRY">\u20ba TL</option><option value="USD">$ USD</option><option value="EUR">\u20ac EUR</option></select></div></section><div class="field"><label>Telefon Numarasi</label><input name="phone" type="tel" placeholder="05xx xxx xx xx"></div><div class="field"><label>E-posta Adresi</label><input name="email" type="email" placeholder="ornek@mail.com"></div><div class="field full"><label>Sorumlu Olaca\u011f\u0131 Blok / Daireler</label><div class="p9-member-units">${unitOptions}</div></div><div class="field full"><label>G\u00f6rev A\u00e7\u0131klamas\u0131 &amp; Notlar</label><textarea name="notes" rows="4" placeholder="Ta\u015feronun yapaca\u011f\u0131 i\u015f kapsam\u0131, malzeme sorumluluklar\u0131 ve teslim tarihleri ile ilgili notlar..."></textarea></div></div>`, async form => {
        const data = Object.fromEntries(form.entries());
        data.project_id = project.id;
        data.assigned_units = JSON.stringify(form.getAll("assigned_units"));
        data.total_contract_amount = Number(String(data.total_contract_amount || "0").replace(",", ".")) || 0;
        data.daily_wage = data.payment_model === "daily" ? data.total_contract_amount : 0;
        data.unit_rate = data.payment_model === "unit" ? data.total_contract_amount : 0;
        data.contact_info = [data.phone, data.email].filter(Boolean).join(" | ");
        await apiFetch("/api/desktop/table/subcontractors", {method: "POST", body: JSON.stringify(data)});
        p9ProjectState.loaded = false; await loadPart9Projects(); return true;
      }, "Ekip \u00dcyesini Kaydet ve G\u00f6revlendir");
      return;
    }
    else if (deleteMember) { if (!confirm("Ekip uyesi projeden kaldirilsin mi?")) return; await apiFetch("/api/desktop/table/subcontractors", {method: "POST", body: JSON.stringify({id: Number(deleteMember.dataset.p9TeamDelete), _action: "delete"})}); p9ProjectState.loaded = false; }
    await loadPart9Projects();
  } catch (error) { toast("Proje islemi basarisiz: " + error.message, "error"); }
});
document.addEventListener("input", event => { if (event.target.id !== "p9FinanceSearch") return; p9FinanceView.query = event.target.value; const cursor = event.target.selectionStart; render(); const input = document.querySelector("#p9FinanceSearch"); if (input) { input.focus(); input.setSelectionRange(cursor, cursor); } });
document.addEventListener("input", event => {
  if (event.target.id === "p9UnitSearch") {
    p9UnitsView.query = event.target.value;
    const cursor = event.target.selectionStart;
    render();
    const input = document.querySelector("#p9UnitSearch");
    if (input) { input.focus(); input.setSelectionRange(cursor, cursor); }
  }
});
document.addEventListener("keydown", event => {
  if (event.key === "Escape" && event.target.id === "p9UnitSearch") { event.preventDefault(); event.target.value = ""; p9UnitsView.query = ""; render(); }
});
document.addEventListener("click", async event => {
  const button = event.target.closest("[data-p9-unit-products]");
  if (!button) return;
  const unitId = Number(button.dataset.p9UnitProducts), project = p9CurrentProject();
  try {
    const [productData, stockData] = await Promise.all([
      apiFetch("/api/desktop/table/project_unit_products?limit=1000"),
      apiFetch("/api/desktop/table/parts?limit=300")
    ]);
    const units = p9ProjectState.units || [];
    const unit = units.find(row => Number(row.id) === unitId) || {};
    const rooms = units.filter(row => Number(row.parent_unit_id) === unitId);
    const rows = productData.rows || [];
    const stock = stockData.rows || [];
    const roomOptions = [{id:unitId,label:`Daire: ${unit.unit_no || unitId}`}, ...rooms.map(row => ({id:row.id,label:`Daire ${unit.unit_no || unitId} / ${row.unit_no || row.name || row.id}`}))]; const selectedRoomId = Number(rooms[0]?.id || unitId);
    const installedRows = rows.filter(row => Number(row.unit_id) === selectedRoomId); const installed = installedRows.map(row => `<tr><td><strong>${esc(row.part_name || "-")}</strong></td><td>${esc(row.part_code || "-")}</td><td>${esc(row.quantity || 0)}</td><td><button type="button" class="p9-note-edit" data-id="${esc(row.id)}" data-note="${esc(row.notes || "")}">${esc(row.notes || "Not ekle")}</button></td><td><span class="p9-install-status">${esc(row.status || "Kurulu")}</span></td><td><button type="button" class="p9-note-edit" data-id="${esc(row.id)}" data-note="${esc(row.notes || "")}" title="Teknik notu duzenle">\u270e</button><button type="button" data-p9-remove-product="${esc(row.id)}" title="Urunu kaldir">\u00d7</button></td></tr>`).join("") || '<tr><td colspan="6" class="p9-install-empty">Kurulu ürün bulunmuyor.</td></tr>';
    const stockRows = stock.map((part,index) => `<label class="p9-stock-row"><input type="checkbox" name="part_ids" value="${esc(part.id)}" ${index === 0 ? "checked" : ""}><span><b>${esc(part.name || "-")}</b><small>${esc(part.code || part.part_code || "-")} · ${esc(part.category || "Stok")}</small></span><strong>${esc(part.stock ?? part.quantity ?? 0)} adet</strong></label>`).join("") || '<p class="p9-install-empty">Stok ürünü bulunamadı.</p>';
    const body = `<div class="p9-unit-products"><header class="p9-install-head"><div><span class="p9-install-badge">AKTİF KURULUM</span><p>${esc(project?.name || "Proje")} › Blok ${esc(unit.block_name || "A")} › Daire ${esc(unit.unit_no || unitId)}</p></div><button type="button" data-p9-add-room="${unitId}">+ Yeni Oda Ekle</button></header><div class="p9-install-overview"><section><label>Hedef Kurulum Alanı</label><select name="target_unit_id" id="p9TargetRoom">${roomOptions.map(room=>`<option value="${esc(room.id)}" ${Number(room.id) === selectedRoomId ? "selected" : ""}>${esc(room.label)}</option>`).join("")}</select><small>Toplam: ${rooms.length} Bölge Tanımlı · Seçilen alt bölgeye göre ürün donanım listesi filtrelenir</small></section><section><div class="p9-install-note-title"><label>Genel Teknik Not</label><small>Son Güncelleme: 14:32</small></div><textarea name="general_note" id="p9GeneralNote" rows="2">${esc(unit.description || "")}</textarea><button type="button" data-p9-save-unit-note="${unitId}">Notu Kaydet</button></section></div><section class="p9-install-section"><header><h3>Kurulu Ürünler <small>(${rows.length})</small></h3><button type="button" data-p9-refresh-install="${unitId}">Yenile</button></header><div class="table-wrap"><table><thead><tr><th>Ürün Adı</th><th>SKU</th><th>Adet</th><th>Teknik Not / IP / Yapılandırma</th><th>Durum</th><th>İşlemler</th></tr></thead><tbody>${installed}</tbody></table></div><button type="button" data-p9-save-install-notes>Teknik Notları Toplu Kaydet</button></section><section class="p9-install-section"><header><h3>Stoktan Ürün Ekle <small>(Merkez Depo Envanteri)</small></h3><span>${stock.length} ürün</span></header><input class="p9-stock-search" type="search" placeholder="Ürün adı veya SKU ile ara"><div class="p9-stock-list">${stockRows}</div></section><div class="p9-install-allocation"><label>Adet<input name="quantity" type="number" min="1" value="1"></label><label>Teknik Ağ Notu<input name="notes" placeholder="IP, kanal veya bağlantı notu"></label><span class="p9-selected-count">${stock.length ? "1 seçili" : "0 seçili"}</span></div></div>`;
    openDialog("Kurulu Ürünler — Daire: " + (unit.unit_no || unitId), "PROJECT UNIT", body, async form => {
      const data = Object.fromEntries(form.entries());
      const targetId = Number(data.target_unit_id || unitId);
      if (data.general_note !== undefined) await apiFetch("/api/desktop/table/project_units", {method:"POST",body:JSON.stringify({id:targetId,description:data.general_note,_action:"update"})});
      const checked = form.getAll("part_ids").map(Number);
      for (const partId of checked) {
        const part = stock.find(row => Number(row.id) === partId);
        if (!part) continue;
        await apiFetch("/api/desktop/table/project_unit_products", {method:"POST",body:JSON.stringify({unit_id:targetId,project_id:project?.id,part_id:part.id,part_name:part.name,part_code:part.code || part.part_code || "",quantity:Number(data.quantity || 1),notes:data.notes || ""})});
      }
      if (checked.length) { p9ProjectState.loaded = false; await loadPart9Projects(); }
      return true;
    }, "Seçilenleri Daireye Ekle");
    setTimeout(() => {
      const dialog = document.querySelector("#dialogBody");
      dialog?.querySelector(".p9-stock-search")?.addEventListener("input", event => { const q=event.target.value.toLocaleLowerCase("tr-TR"); dialog.querySelectorAll(".p9-stock-row").forEach(row=>row.hidden=!row.textContent.toLocaleLowerCase("tr-TR").includes(q)); });
      dialog?.querySelectorAll('input[name="part_ids"]').forEach(input=>input.addEventListener("change",()=>{dialog.querySelector(".p9-selected-count").textContent=`${dialog.querySelectorAll('input[name="part_ids"]:checked').length} seçili`;}));
    }, 0);
  } catch (error) { toast("Oda envanteri yüklenemedi: " + error.message, "error"); }
});

document.addEventListener("change", async event => {
  if (event.target.id === "p9TargetRoom") {
    const targetId=Number(event.target.value), data=await apiFetch("/api/desktop/table/project_unit_products?limit=1000");
    const rows=(data.rows||[]).filter(row=>Number(row.unit_id)===targetId);
    const tbody=document.querySelector("#dialogBody .p9-unit-products tbody");
    if(tbody)tbody.innerHTML=rows.map(row=>`<tr><td><strong>${esc(row.part_name||"-")}</strong></td><td>${esc(row.part_code||"-")}</td><td>${esc(row.quantity||0)}</td><td><button type="button" class="p9-note-edit" data-id="${esc(row.id)}" data-note="${esc(row.notes||"")}">${esc(row.notes||"Not ekle")}</button></td><td><span class="p9-install-status">${esc(row.status || "Kurulu")}</span></td><td><button type="button" class="p9-note-edit" data-id="${esc(row.id)}" data-note="${esc(row.notes || "")}" title="Teknik notu duzenle">\u270e</button><button type="button" data-p9-remove-product="${esc(row.id)}" title="Urunu kaldir">\u00d7</button></td></tr>`).join("")||'<tr><td colspan="6" class="p9-install-empty">Kurulu ürün bulunmuyor.</td></tr>';
    const note=(p9ProjectState.units||[]).find(row=>Number(row.id)===targetId)?.description||"";const input=document.querySelector("#p9GeneralNote");if(input)input.value=note;
  }
});
document.addEventListener("click", async event => {
  const addRoom=event.target.closest("[data-p9-add-room]");if(addRoom){const name=window.prompt("Oda adı");if(!name?.trim())return;await apiFetch("/api/desktop/table/project_units",{method:"POST",body:JSON.stringify({project_id:p9CurrentProject()?.id,parent_unit_id:Number(addRoom.dataset.p9AddRoom),unit_no:name.trim(),_action:"insert"})});toast("Oda eklendi");return;}
  const refresh=event.target.closest("[data-p9-refresh-install]");if(refresh){const data=await apiFetch("/api/desktop/table/project_unit_products?limit=1000"),id=Number(document.querySelector("#p9TargetRoom")?.value||refresh.dataset.p9RefreshInstall),rows=(data.rows||[]).filter(row=>Number(row.unit_id)===id),tbody=document.querySelector("#dialogBody .p9-unit-products tbody");if(tbody)tbody.innerHTML=rows.map(row=>`<tr><td><strong>${esc(row.part_name||"-")}</strong></td><td>${esc(row.part_code||"-")}</td><td>${esc(row.quantity||0)}</td><td>${esc(row.notes||"")}</td><td><span class="p9-install-status">${esc(row.status || "Kurulu")}</span></td><td><button type="button" class="p9-note-edit" data-id="${esc(row.id)}" data-note="${esc(row.notes || "")}" title="Teknik notu duzenle">\u270e</button><button type="button" data-p9-remove-product="${esc(row.id)}" title="Urunu kaldir">\u00d7</button></td></tr>`).join("")||'<tr><td colspan="6" class="p9-install-empty">Kurulu ürün bulunmuyor.</td></tr>';return;}
  const saveNotes=event.target.closest("[data-p9-save-install-notes]");if(saveNotes){const edits=[...document.querySelectorAll(".p9-note-edit")];for(const item of edits)await apiFetch("/api/desktop/table/project_unit_products",{method:"POST",body:JSON.stringify({id:Number(item.dataset.id),notes:item.dataset.note||"",_action:"update"})});toast("Teknik notlar kaydedildi");return;}
  const edit=event.target.closest(".p9-note-edit");
  if(edit){const note=window.prompt("Teknik not",edit.dataset.note||"");if(note===null)return;await apiFetch("/api/desktop/table/project_unit_products",{method:"POST",body:JSON.stringify({id:Number(edit.dataset.id),notes:note,_action:"update"})});edit.dataset.note=note;edit.textContent=note||"Not ekle";return;}
  const remove=event.target.closest("[data-p9-remove-product]");if(remove){await apiFetch("/api/desktop/table/project_unit_products",{method:"POST",body:JSON.stringify({id:Number(remove.dataset.p9RemoveProduct),_action:"delete"})});remove.closest("tr")?.remove();return;}
  const save=event.target.closest("[data-p9-save-unit-note]");if(save){const target=Number(document.querySelector("#p9TargetRoom")?.value||save.dataset.p9SaveUnitNote);await apiFetch("/api/desktop/table/project_units",{method:"POST",body:JSON.stringify({id:target,description:document.querySelector("#p9GeneralNote")?.value||"",_action:"update"})});toast("Genel teknik not kaydedildi");return;}
});
