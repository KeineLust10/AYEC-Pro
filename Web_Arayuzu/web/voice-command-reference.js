const voiceCommandDefaults = [
  {name:"Asistan finans \u00f6zet", phrase:"\"\u00f6zet\"", detail:"Finans Konsolu & Ayl\u0131k Nakit Ak\u0131\u015f\u0131 Ekran\u0131", group:"Finans"},
  {name:"Asistan geli\u015fmi\u015f finansal \u00f6zet", phrase:"\"Geli\u015fmi\u015f\"", detail:"Bilan\u00e7o, Karl\u0131l\u0131k ve Tahsilat Grafikleri", group:"Finans"},
  {name:"Asistan kritik stoklar\u0131 listele", phrase:"\"Kritik Stok\"", detail:"Asgari Stok Alt\u0131 \u00dcr\u00fcnler ve Tedarik \u00d6nerileri", group:"Stok"},
  {name:"Asistan yeni servis kayd\u0131 a\u00e7", phrase:"\"Servis A\u00e7\"", detail:"H\u0131zl\u0131 Cihaz Kabul\u00fc ve M\u00fc\u015fteri Bildirimi", group:"Servis"},
  {name:"Asistan g\u00fcn sonu kasa raporu", phrase:"\"Kasa Raporu\"", detail:"G\u00fcnl\u00fck Ciro, Kasa Durumu & Tahsilat Sesi Dinleme", group:"Raporlar"},
  {name:"Asistan teknisyen durumlar\u0131", phrase:"\"Saha Ekibi\"", detail:"Saha Personeli G\u00f6rev Da\u011f\u0131l\u0131m\u0131 ve \u0130\u015f Emri Takibi", group:"Servis"}
];
const voiceScenarioDefaults = {
  "Finansal \u00d6zet": {
    "triggers": [
      "finans \u00f6zet",
      "mali durum \u00f6zeti",
      "kasa \u00f6zeti"
    ],
    "action": {
      "type": "builtin",
      "name": "accounting_summary"
    }
  },
  "Stoklara %10 Zam": {
    "triggers": [
      "stoklara y\u00fczde 10 zam yap",
      "stoklara %10 zam yap",
      "fiyatlara y\u00fczde 10 zam yap"
    ],
    "action": {
      "type": "builtin",
      "name": "apply_zam"
    }
  },
  "Kritik Stoklar": {
    "triggers": [
      "kritik stoklar\u0131 listele",
      "kritik stoklar",
      "eksik stoklar"
    ],
    "action": {
      "type": "builtin",
      "name": "list_critical_stock"
    }
  },
  "Teknisyen Paneli": {
    "triggers": [
      "teknisyen panelini a\u00e7",
      "teknisyen paneli",
      "panel a\u00e7"
    ],
    "action": {
      "type": "builtin",
      "name": "panel_ac"
    }
  },
  "Yeni Servis A\u00e7": {
    "triggers": [
      "yeni servis a\u00e7",
      "yeni servis kayd\u0131 a\u00e7",
      "servis kayd\u0131 olu\u015ftur",
      "servis formunu a\u00e7"
    ],
    "action": {
      "type": "builtin",
      "name": "servis_ac"
    }
  },
  "Bug\u00fcnk\u00fc Randevular": {
    "triggers": [
      "bug\u00fcnk\u00fc randevular",
      "randevular\u0131m\u0131 s\u00f6yle",
      "bug\u00fcn randevum var m\u0131"
    ],
    "action": {
      "type": "builtin",
      "name": "check_appointments"
    }
  },
  "Stok \u00d6zeti": {
    "triggers": [
      "stok \u00f6zeti",
      "envanter \u00f6zeti",
      "stok durum \u00f6zeti"
    ],
    "action": {
      "type": "builtin",
      "name": "stock_summary"
    }
  },
  "Y\u00f6netici \u00d6zeti": {
    "triggers": [
      "y\u00f6netici \u00f6zeti",
      "bug\u00fcn ne oldu",
      "g\u00fcnl\u00fck y\u00f6netici \u00f6zeti"
    ],
    "action": {
      "type": "builtin",
      "name": "managerial_summary"
    }
  },
  "Geli\u015fmi\u015f Finansal \u00d6zet": {
    "triggers": [
      "geli\u015fmi\u015f finansal \u00f6zet",
      "nakit ak\u0131\u015f \u00f6zeti",
      "vade \u00f6zetini s\u00f6yle"
    ],
    "action": {
      "type": "builtin",
      "name": "financial_summary"
    }
  },
  "M\u00fc\u015fteri 360": {
    "triggers": [
      "m\u00fc\u015fteri 360 a\u00e7",
      "m\u00fc\u015fteri cari hesap",
      "m\u00fc\u015fteri detaylar\u0131n\u0131 a\u00e7"
    ],
    "action": {
      "type": "builtin",
      "name": "customer_360"
    }
  },
  "Cihaz Durumu Sorgu": {
    "triggers": [
      "cihaz durumu sorgula",
      "cihaz durumu",
      "servis durumu sorgula"
    ],
    "action": {
      "type": "builtin",
      "name": "device_status_query"
    }
  },
  "\u0130ndirim Tavsiyesi": {
    "triggers": [
      "indirim tavsiyesi ver",
      "m\u00fc\u015fteri i\u00e7in indirim tavsiyesi",
      "indirim \u00f6nerisi"
    ],
    "action": {
      "type": "builtin",
      "name": "discount_advice"
    }
  },
  "Bor\u00e7 \u00d6zeti": {
    "triggers": [
      "bor\u00e7 \u00f6zeti",
      "kredi bor\u00e7 \u00f6zeti",
      "bor\u00e7 durumunu s\u00f6yle"
    ],
    "action": {
      "type": "builtin",
      "name": "loan_summary"
    }
  },
  "\u00c7ek Senet \u00d6zeti": {
    "triggers": [
      "\u00e7ek senet \u00f6zeti",
      "\u00e7ek senet portf\u00f6y\u00fc",
      "\u00e7ek senetleri a\u00e7"
    ],
    "action": {
      "type": "builtin",
      "name": "check_summary"
    }
  },
  "Stok Kar\u015f\u0131la\u015ft\u0131rma": {
    "triggers": [
      "stok kar\u015f\u0131la\u015ft\u0131rma yap",
      "stok kar\u015f\u0131la\u015ft\u0131rma",
      "hangi stok daha fazla"
    ],
    "action": {
      "type": "builtin",
      "name": "stock_comparison"
    }
  },
  "Sesli Not Ekle": {
    "triggers": [
      "not ekle",
      "not al",
      "notu al",
      "sesli not al",
      "h\u0131zl\u0131 not ekle"
    ],
    "action": {
      "type": "builtin",
      "name": "add_quick_note_voice"
    }
  },
  "Sesli Hat\u0131rlat\u0131c\u0131 Ekle": {
    "triggers": [
      "hat\u0131rlat\u0131c\u0131 ekle",
      "sesli hat\u0131rlat\u0131c\u0131 kur",
      "yar\u0131n i\u00e7in hat\u0131rlat\u0131c\u0131 ekle"
    ],
    "action": {
      "type": "builtin",
      "name": "add_reminder_voice"
    }
  },
  "G\u00fcn Kapan\u0131\u015f \u00d6zeti": {
    "triggers": [
      "g\u00fcn kapan\u0131\u015f \u00f6zeti",
      "g\u00fcn\u00fc kapat",
      "ak\u015fam \u00f6zetini ver"
    ],
    "action": {
      "type": "builtin",
      "name": "closing_routine"
    }
  },
  "Musteri Borc Durumu": {
    "triggers": [
      "borclu musterileri soyle",
      "musteri borc durumunu soyle",
      "kimlerin borcu var"
    ],
    "action": {
      "type": "builtin",
      "name": "customer_debt_summary"
    }
  },
  "Servis Is Yuku": {
    "triggers": [
      "servis is yukunu soyle",
      "kac cihaz bekliyor",
      "servis durum ozeti"
    ],
    "action": {
      "type": "builtin",
      "name": "service_workload_summary"
    }
  },
  "Simdi Senkronize Et": {
    "triggers": [
      "simdi senkronize et",
      "senkronizasyon yap",
      "verileri sunucuyla esitle"
    ],
    "action": {
      "type": "builtin",
      "name": "sync_now"
    }
  },
  "Asistan Yetenekleri": {
    "triggers": [
      "neler yapabilirsin",
      "hangi komutlari biliyorsun",
      "bana nasil yardim edebilirsin"
    ],
    "action": {
      "type": "builtin",
      "name": "assistant_help"
    }
  },
  "Sonraki Yetenekler": {
    "triggers": [
      "sonraki komutlar",
      "diger komutlari oku",
      "yetenege devam et"
    ],
    "action": {
      "type": "builtin",
      "name": "voice_help_next"
    }
  },
  "Genel Bak\u0131\u015f": {
    "triggers": [
      "genel bak\u0131\u015f a\u00e7",
      "genel dashboard a\u00e7",
      "ana ekran\u0131 a\u00e7"
    ],
    "action": {
      "type": "page",
      "index": 40
    }
  },
  "Stok Sayfas\u0131": {
    "triggers": [
      "stok sayfas\u0131n\u0131 a\u00e7",
      "stok ekran\u0131n\u0131 a\u00e7",
      "envanteri a\u00e7"
    ],
    "action": {
      "type": "page",
      "index": 50
    }
  },
  "M\u00fc\u015fteri Listesi": {
    "triggers": [
      "m\u00fc\u015fteri listesini a\u00e7",
      "m\u00fc\u015fterileri a\u00e7",
      "m\u00fc\u015fteri ekran\u0131n\u0131 a\u00e7"
    ],
    "action": {
      "type": "page",
      "index": 21
    }
  },
  "Sat\u0131\u015f Ekran\u0131": {
    "triggers": [
      "sat\u0131\u015f ekran\u0131n\u0131 a\u00e7",
      "sat\u0131\u015f i\u015flemini a\u00e7",
      "yeni sat\u0131\u015f a\u00e7"
    ],
    "action": {
      "type": "page",
      "index": 150
    }
  }
};
function voiceRepairScenarios(raw){
 const defaults=voiceScenarioDefaults,sanitized={},triggerOwners=new Map(),source=raw&&typeof raw==="object"&&!Array.isArray(raw)?raw:{};
 const keywordMap=[["finans",{type:"builtin",name:"accounting_summary"}],["mali",{type:"builtin",name:"accounting_summary"}],["zam",{type:"builtin",name:"apply_zam"}],["kritik stok",{type:"builtin",name:"list_critical_stock"}],["teknisyen",{type:"builtin",name:"panel_ac"}],["m\u00fc\u015fteri 360",{type:"builtin",name:"customer_360"}]];
 for(const [name,value] of Object.entries(source)){
  if(!name.trim())continue;
  const legacyList=Array.isArray(value)?value:null,record=value&&typeof value==="object"&&!Array.isArray(value)?value:null;
  if(!legacyList&&!record)continue;
  const triggerList=legacyList||(Array.isArray(record?.triggers)?record.triggers:Array.isArray(record?.kelimeler)?record.kelimeler:[]);
  const triggers=triggerList.map(item=>(item===null?"None":String(item)).trim().toLowerCase()).filter(Boolean),item={triggers};
  let action=record?.action&&typeof record.action==="object"&&!Array.isArray(record.action)?record.action:null;
  if(action?.type==="page_search")action={type:"page",index:action.index,auto_search:true};
  if(action)item.action=action;
  const haystack=[name.toLowerCase(),...triggers].join(" ");
  if(!item.action){const match=keywordMap.find(([keyword])=>haystack.includes(keyword));if(match)item.action={...match[1]}}
  if(!item.action&&defaults[name]?.action)item.action={...defaults[name].action};
  sanitized[name]=item;
 }
 for(const [name,scenario] of Object.entries(sanitized))for(const trigger of scenario.triggers)triggerOwners.set(trigger,name);
 for(const [name,scenario] of Object.entries(defaults)){
  const current=sanitized[name]||(sanitized[name]={triggers:[],action:{...scenario.action}});
  const currentAction=current.action||null,defaultAction=scenario.action||null;
  const sameAction=!!currentAction&&!!defaultAction&&Object.keys(currentAction).length===Object.keys(defaultAction).length&&Object.keys(defaultAction).every(key=>currentAction[key]===defaultAction[key]);
  if(!sameAction)continue;
  for(const trigger of scenario.triggers){const normalized=trigger.toLowerCase(),owner=triggerOwners.get(normalized);if(owner&&owner!==name)continue;if(!current.triggers.some(item=>item.toLowerCase()===normalized))current.triggers.push(trigger);triggerOwners.set(normalized,name)}
 }
 return sanitized;
}
const voiceCommandStateKey = "ayec.part9.voice-command-settings";
function voiceCommandState(){
 let saved=null;
 const sharedSetting=desktopSettings?.voice_command_settings;
 try{saved=typeof sharedSetting==="string"&&sharedSetting.trim()?JSON.parse(sharedSetting):sharedSetting&&typeof sharedSetting==="object"?sharedSetting:null}catch{}
 if(!saved){try{saved=JSON.parse(localStorage.getItem(voiceCommandStateKey)||"null")}catch{}}
 const state=saved&&typeof saved==="object"?{commands:Array.isArray(saved.commands)?saved.commands:voiceCommandDefaults.slice(),scenarios:saved.scenarios&&typeof saved.scenarios==="object"?saved.scenarios:{},alerts:Array.isArray(saved.alerts)?saved.alerts:[],start:saved.start||"19:00",end:saved.end||"08:30",critical:saved.critical!==false,volume:Number(saved.volume??85),speed:Number(saved.speed??1),active:saved.active||"AI Asistan Sayfasi",scenario_defaults_initialized:saved.scenario_defaults_initialized===true}:{commands:voiceCommandDefaults.slice(),scenarios:{},alerts:[],start:"19:00",end:"08:30",critical:true,volume:85,speed:1,active:"AI Asistan Sayfasi",scenario_defaults_initialized:false};
 if(!(state.scenario_defaults_initialized&&!Object.keys(state.scenarios).length))state.scenarios=voiceRepairScenarios(state.scenarios);
 if(Object.keys(state.scenarios).length&&!Object.hasOwn(state.scenarios,state.active))state.active=Object.keys(state.scenarios).sort()[0];
 if(sharedSetting&&saved) localStorage.setItem(voiceCommandStateKey,JSON.stringify(saved));
 return state;
}
function voiceCommandSaveState(state){state.scenario_defaults_initialized=true;const value=JSON.stringify(state);localStorage.setItem(voiceCommandStateKey,value);desktopSettings.voice_command_settings=value;desktopWrite("settings",{key:"voice_command_settings",value});}
async function openVoiceReminderLog(){
 const alerts=await loadAllDesktopTableRows("scheduled_alerts");
 const labels={loan_reminder:"Kredi taksitleri",check_reminder:"\u00c7ek ve senet",stock_critical:"Kritik stok",service_delivery:"Servis teslimat\u0131"};
 const rows=alerts.map(alert=>{
  const raw=String(alert.last_triggered||"");
  const date=raw?new Date(raw.replace(" ","T")):null;
  const last=date&&!Number.isNaN(date.getTime())?date.toLocaleString("tr-TR"):raw||"Hen\u00fcz \u00e7al\u0131\u015fmad\u0131";
  const label=labels[alert.alert_type]||String(alert.alert_type||"Uyar\u0131").replaceAll("_"," ");
  const status=Number(alert.is_enabled??1)===1?"Aktif":"Pasif";
  return `<tr><td>${esc(label)}</td><td>${esc(String(alert.trigger_time||"--:--").slice(0,5))}</td><td>${status}</td><td>${esc(last)}</td></tr>`;
 }).join("");
 const body=alerts.length?`<div class="table-wrap"><table><thead><tr><th>Uyar\u0131</th><th>Planlanan saat</th><th>Durum</th><th>Son \u00e7al\u0131\u015fma</th></tr></thead><tbody>${rows}</tbody></table></div>`:`<div class="empty-state">Kay\u0131tl\u0131 zamanlanm\u0131\u015f uyar\u0131 yok.</div>`;
 openDialog("Zamanlanm\u0131\u015f Uyar\u0131 Durumu","SESL\u0130 UYARILAR",body,()=>true,"Kapat");
}
function voiceScenarioActionCatalog(){
 const builtinNames=["panel_ac","servis_ac","accounting_summary","financial_summary","apply_zam","confirm_yes","confirm_no","check_appointments","list_critical_stock","stock_summary","add_reminder_voice","add_quick_note_voice","managerial_summary","device_status_query","greeting_routine","closing_routine","stock_comparison","customer_360","discount_advice","loan_summary","check_summary","customer_debt_summary","service_workload_summary","sync_now","assistant_help","voice_help_next"];
 const options=[{label:"Ba\u011flant\u0131 Yok (Sadece Komut)",action:null},...builtinNames.map(name=>({label:`\u00d6zel Fonksiyon: ${name}`,action:{type:"builtin",name}}))];
 const navItems=typeof ayecSectorMenu==="function"?ayecSectorMenu(currentSector):[];
 for(const [id,index] of Object.entries(ayecDesktopPageIds||{})){const item=navItems.find(entry=>entry.id===id),label=item?labelFor(item,currentSector):id;options.push({label:`Sayfa A\u00e7: ${label}`,action:{type:"page",index:Number(index)}})}
 return options;
}
function voiceScenarioMatch(state,transcript){
 const query=String(transcript||"").trim().toLocaleLowerCase("tr-TR"),matches=[];
 for(const [name,scenario] of Object.entries(state.scenarios||{}))for(const trigger of scenario?.triggers||[]){const phrase=String(trigger||"").replace(/^['\"]|['\"]$/g,"").trim().toLocaleLowerCase("tr-TR");if(phrase&&query.includes(phrase))matches.push({matched:true,name,phrase,action:scenario.action||null})}
 matches.sort((left,right)=>right.phrase.length-left.phrase.length);return matches[0]||{matched:false};
}
function voiceScenarioDispatch(state,transcript){
 const match=voiceScenarioMatch(state,transcript);if(!match.matched)return match;
 if(match.action?.type==="builtin"){
  if(typeof ayecExecuteVoiceAction==="function"){const result=ayecExecuteVoiceAction({type:"Aksiyon",action:match.action.name,voice_trigger:match.phrase},transcript);return{...match,action:"builtin",scenarioAction:match.action,route:"",executed:result!==false}}
  return{...match,action:"builtin",scenarioAction:match.action,route:"",executed:false};
 }
 if(match.action?.type==="page"){
  const route=Object.entries(ayecDesktopPageIds||{}).find(([,index])=>Number(index)===Number(match.action.index))?.[0];if(!route)return{...match,action:"page",scenarioAction:match.action,route:""};
  navigate(route);
  if(match.action.auto_search){const querySource=String(transcript||"").trim(),queryTrigger=String(match.phrase||"").trim(),queryLower=querySource.toLocaleLowerCase("tr-TR"),triggerOffset=queryTrigger?queryLower.indexOf(queryTrigger.toLocaleLowerCase("tr-TR")):-1,searchQuery=(triggerOffset>=0?(querySource.slice(0,triggerOffset)+" "+querySource.slice(triggerOffset+queryTrigger.length)).trim():querySource).replace(/^[\s,.:;-]+|[\s,.:;-]+$/g,"");const selector="#content #genericSearch,#content #groupSearch,#content input[type=search],#content [data-page-search]",applySearch=remaining=>{if(page!==route||remaining<=0)return;const input=document.querySelector(selector);if(!input){setTimeout(()=>applySearch(remaining-1),150);return}if(input.value!==searchQuery){input.value=searchQuery;input.dispatchEvent(new Event("input",{bubbles:true}));input.dispatchEvent(new Event("change",{bubbles:true}))}setTimeout(()=>{const current=document.querySelector(selector);if(page===route&&(!current||current.value!==searchQuery))applySearch(remaining-1)},150)};applySearch(20)}
  return{...match,action:"page",scenarioAction:match.action,route,autoSearch:!!match.action.auto_search};
 }
 return{...match,action:"none",scenarioAction:match.action,route:"",executed:true};
}
function ayecSpeakVoiceFeedback(message){const settings=typeof desktopSettings==="object"&&desktopSettings?desktopSettings:{},enabled=settingBool(settings.asistan_voice_enabled??settings.assistant_voice_enabled??"1");if(!enabled||typeof playScheduledAlertSpeech!=="function")return false;const text=String(message||""),limited=text.length>150?`${text.slice(0,147)}...`:text;void playScheduledAlertSpeech(limited);return true}
function ayecSelectDevicePickerByVoice(target){
 const search=document.querySelector("#devicePickerSearch"),host=document.querySelector("#devicePickerRows");if(!search||!host)return null;
 const normalize=value=>typeof ayecNormalizeVoicePhrase==="function"?ayecNormalizeVoicePhrase(value).trim().replace(/\s+/g," "):String(value||"").toLocaleLowerCase("tr-TR").trim().replace(/\s+/g," ");
 const query=normalize(target),words=query.split(" ").filter(Boolean),variants=[query];
 if(!query){toast("Hangi musteriyi veya cihazi secmemi istersiniz?","warning");return false}
 const last=words.at(-1);for(const suffix of ["yi","yu","ni","nu","i","u"]){if(last.endsWith(suffix)&&last.length-suffix.length>=3){variants.push([...words.slice(0,-1),last.slice(0,-suffix.length)].join(" "));break}}
 const rows=[...host.querySelectorAll("[data-device-picker]")],matches=rows.filter(row=>{const values=[...row.querySelectorAll("td")].map(cell=>normalize(cell.textContent));return variants.some(variant=>values.some(value=>value.includes(variant)))});
 if(!matches.length){search.value=String(target||"");search.dispatchEvent(new Event("input",{bubbles:true}));toast(`${target} icin acik servis cihazi bulamadim.`,"warning");return false}
 if(matches.length>1){search.value=String(target||"");search.dispatchEvent(new Event("input",{bubbles:true}));toast("Bu musteriye ait birden fazla cihaz var. Cihaz modelini veya takip numarasini soyleyin.","warning");return false}
 matches[0].click();document.querySelector("#dialogSubmit")?.click();toast("Cihazi sectim ve teknisyen panelini aciyorum.","info");return true;
}
const ayecExecuteVoiceActionBase=ayecExecuteVoiceAction;
const ayecRenderTechnicianBase=renderTechnician;
renderTechnician=function(){return ayecRenderTechnicianBase().replace('<button class="secondary" data-page="services">','<button type="button" class="secondary" data-action="device-selection">Cihaz Se\u00e7</button><button class="secondary" data-page="services">')};
document.addEventListener("click",event=>{if(event.target.closest('[data-action="device-selection"]')&&page==="technician")openDeviceSelectionManifestDialog()});
ayecExecuteVoiceAction=function(item,transcript=""){
 const action=String(item?.action?.name||item?.action||item?.page||"");
 if(action==="select_service_device"){
  const targetElement=document.querySelector("#devicePickerSearch");
  if(targetElement){const source=String(transcript||""),sourceLower=source.toLocaleLowerCase("tr-TR"),triggers=[item?.voice_trigger,...(Array.isArray(item?.phrases)?item.phrases:[])].map(value=>String(value||"").trim()).filter(Boolean).sort((left,right)=>right.length-left.length),trigger=triggers.find(value=>sourceLower.includes(value.toLocaleLowerCase("tr-TR")))||"",offset=trigger?sourceLower.indexOf(trigger.toLocaleLowerCase("tr-TR")):-1;const target=offset>=0?(source.slice(0,offset)+" "+source.slice(offset+trigger.length)).trim():source.trim();return ayecSelectDevicePickerByVoice(target)}
 }
 if(action==="accounting_summary"||action==="financial_summary"){
  navigate("finance");
  apiFetch("/api/desktop/voice/financial-summary").then(summary=>{
   const format=value=>new Intl.NumberFormat("tr-TR",{style:"currency",currency:"TRY"}).format(Number(value)||0);
   toast(`Bu ay toplam ${format(summary.gross_revenue)} gelir ve ${format(summary.expenses)} gideriniz var. Net durumunuz ${format(summary.net)}.`,"info");
  }).catch(error=>toast(`Finansal ozet hazirlanamadi: ${error.message}`,"error"));
  return;
 }
 if(action==="customer_360"){
  const normalize=value=>{const text=String(value||""),normalized=typeof ayecNormalizeVoicePhrase==="function"?ayecNormalizeVoicePhrase(text):text.normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[\u0131\u0130]/g,"i").toLowerCase();return normalized.replace(/[^a-z0-9]+/g," ").trim()},spoken=` ${normalize(transcript)} `,rows=typeof customerDirectoryRows==="function"?customerDirectoryRows():(Array.isArray(db?.customers)?db.customers:[]),customer=rows.filter(item=>String(item?.name||"").trim()).filter(item=>{const name=normalize(item.name);return name&&spoken.includes(` ${name} `)}).sort((left,right)=>String(right.name).length-String(left.name).length)[0];
  if(customer){customer360(customer);toast(`${customer.name} musterisi icin 360 derece gorunumu aciliyor.`,"info");return}
  navigate("customers");toast("Musteriyi bulamadim. Musteri listesini aciyorum.","warning");return;
 }
 if(action==="stok_sorgu"){
  const source=String(transcript||"").trim(),sourceLower=source.toLocaleLowerCase("tr-TR"),triggers=[item?.voice_trigger,...(Array.isArray(item?.phrases)?item.phrases:[])].map(value=>String(value||"").trim()).filter(Boolean).sort((left,right)=>right.length-left.length),trigger=triggers.find(value=>sourceLower.includes(value.toLocaleLowerCase("tr-TR")))||"",offset=trigger?sourceLower.indexOf(trigger.toLocaleLowerCase("tr-TR")):-1;
  const query=(offset>=0?(source.slice(0,offset)+" "+source.slice(offset+trigger.length)).trim():source).replace(/^(stok|stokta|stoklar|urun|urunler|parca|parcalar|ara|sorgula|bul)\b[\s:,-]*/i,"").trim();
  navigate("stock");setTimeout(()=>{const search=document.querySelector("#stockSearch");if(!search)return;search.value=query;search.dispatchEvent(new Event("input",{bubbles:true}));search.focus()},0);
  toast(query?`Stok aramas\u0131 haz\u0131r: ${query}`:"Stok ekran\u0131 a\u00e7\u0131ld\u0131.","info");return true;
 }
 if(action==="list_critical_stock"){
  const critical=(Array.isArray(db?.stock)?db.stock:[]).filter(part=>Number(part?.qty||0)<=Number(part?.min||0)).sort((left,right)=>Number(left?.qty||0)-Number(right?.qty||0)).slice(0,100);
  navigate("stock");const message=critical.length?`Kritik seviyede ${critical.length} stok kalemi var.`:"Kritik seviyede stok bulunmuyor.";toast(message,"info");ayecSpeakVoiceFeedback(critical.length?`${message} Kritik stok ekranini aciyorum.`:message);return;
 }
 if(action==="stock_summary"){
  const stock=Array.isArray(db?.stock)?db.stock:[],total=Math.trunc(stock.reduce((sum,part)=>sum+Number(part?.qty||0),0)),critical=stock.filter(part=>Number(part?.min||0)>0&&Number(part?.qty||0)<=Number(part?.min||0)).length;
  const message=`${stock.length} stok kartinda toplam ${total} urun var. Kritik seviyedeki kart sayisi ${critical}.`;navigate("stock");toast(message,"info");ayecSpeakVoiceFeedback(message);return;
 }
 const feedbackRoutes={check_appointments:["appointments","Randevularinizi kontrol ediyorum."],device_status_query:["job-reports","Cihaz ve servis durumunu aciyorum."],discount_advice:["customers","Indirim tavsiyesi icin musteri ekranini aciyorum."],loan_summary:["income","Borc ozetini aciyorum."],check_summary:["checks","Cek ve senet ekranini aciyorum."],stock_comparison:["stock","Stok karsilastirma ekranini aciyorum."],panel_ac:["technician","Teknisyen panelini aciyorum."],managerial_summary:["dashboard","Yonetici ozetini hazirliyorum."]};
 if(feedbackRoutes[action]){const [route,message]=feedbackRoutes[action];if(sectorPages[currentSector]?.has(route)){navigate(route);toast(message,"info");ayecSpeakVoiceFeedback(message);return}}
 return ayecExecuteVoiceActionBase(item,transcript);
};
async function runVoiceScenarioHealthcheck(state){
 const scenarios=state.scenarios||{},entries=Object.entries(scenarios),checks=[],knownBuiltins=new Set(voiceScenarioActionCatalog().map(item=>item.action?.type==="builtin"?item.action.name:null).filter(Boolean)),pageIds=new Set(Object.values(ayecDesktopPageIds||{}).map(Number));
 const addCheck=(name,ok,detail="")=>checks.push({name,ok:!!ok,detail});
 const activeOk=!!state.active&&Object.hasOwn(scenarios,state.active);addCheck("Aktif senaryo",activeOk);
 const triggers=entries.flatMap(([name,scenario])=>(Array.isArray(scenario?.triggers)?scenario.triggers:[]).map(trigger=>({name,trigger:String(trigger||"").trim()}))).filter(item=>item.trigger);
 const reachable=triggers.filter(item=>voiceScenarioMatch({scenarios},item.trigger)?.name===item.name).length;addCheck("Tetikleyici eslesmesi",triggers.length>0&&reachable===triggers.length,`${reachable}/${triggers.length}`);
 const invalidActions=entries.filter(([,scenario])=>{const action=scenario?.action;if(!action)return false;if(action.type==="builtin")return !knownBuiltins.has(action.name);if(action.type==="page")return !pageIds.has(Number(action.index));return true}).length;
 addCheck("Aksiyon hedefleri",invalidActions===0,invalidActions?String(invalidActions):"");
 const timePattern=/^(?:[01]\d|2[0-3]):[0-5]\d$/;const timesOk=timePattern.test(String(state.start||""))&&timePattern.test(String(state.end||""));addCheck("Zaman ayarlari",timesOk);
 let apiOk=false,apiDetail="";try{const response=await fetch("/api/desktop/health",{credentials:"same-origin",headers:ayecFiscalArchiveHeaders()}),health=await response.json();apiOk=response.ok&&health?.ok===true&&health?.schema_ready===true;if(!apiOk)apiDetail=(health?.missing_tables||[]).join(", ")||health?.error||`HTTP ${response.status}`}catch(error){apiDetail=String(error.message||error)}addCheck("Web API",apiOk,apiDetail);
 const passed=checks.filter(item=>item.ok).length,result=$("[data-voice-result]");
 result.textContent=`Saglik testi: ${passed}/${checks.length} kontrol gecti; ${entries.length} senaryo; ${triggers.length} tetikleyici. ${checks.map(item=>`${item.name}: ${item.ok?"OK":"HATA"}${item.detail?` (${item.detail})`:""}`).join(" | ")}`;
 toast(passed===checks.length?"Sesli senaryo saglik testi tamamlandi.":"Sesli senaryo saglik testinde sorun bulundu.",passed===checks.length?"success":"warning");
 return{ok:passed===checks.length,checks,scenarioCount:entries.length,triggerCount:triggers.length,reachableTriggerCount:reachable};
}
function openVoiceScenarioEditor(state){
 const scenarios=state.scenarios&&typeof state.scenarios==="object"?state.scenarios:{};
 const names=[...new Set([...Object.keys(scenarios),state.active].filter(Boolean))],scenarioOptions=names.map(name=>`<option value="${esc(name)}" ${name===state.active?"selected":""}>${esc(name)}</option>`).join("");
 const actions=voiceScenarioActionCatalog(),actionOptions=actions.map(option=>`<option value="${esc(option.action?JSON.stringify(option.action):"")}">${esc(option.label)}</option>`).join(""),selected=scenarios[state.active]||{},selectedAction=selected.action||null,selectedPayload=selectedAction?JSON.stringify(selectedAction.type==="page_search"?{type:"page",index:selectedAction.index}:selectedAction):"";
 const body=`<div class="form-grid"><div class="field full"><label for="voiceScenarioName">Senaryo</label><select id="voiceScenarioName" name="scenario">${scenarioOptions}</select></div><div class="field full"><label for="voiceScenarioTriggers">Tetikleyiciler (her sat\u0131ra bir ifade)</label><textarea id="voiceScenarioTriggers" name="triggers" rows="5" maxlength="1200">${esc(Array.isArray(selected.triggers)?selected.triggers.join("\n"):"")}</textarea></div><div class="field full"><label for="voiceScenarioAction">Ba\u011fl\u0131 i\u015flem</label><select id="voiceScenarioAction" name="action">${actionOptions}</select></div><label class="field full"><input type="checkbox" name="auto_search" ${selectedAction?.auto_search||selectedAction?.type==="page_search"?"checked":""}> Sayfa a\u00e7\u0131ld\u0131\u011f\u0131nda arama alan\u0131na tetikleyiciyi uygula</label></div>`;
 openDialog("Senaryo Tetikleyicileri ve \u0130\u015flem","SES KOMUTLARI",body,form=>{
  const name=String(form.get("scenario")||"").trim(),triggerList=[...new Set(String(form.get("triggers")||"").split(/\r?\n/).map(value=>value.trim()).filter(Boolean))];if(!name)throw Error("Bir senaryo se\u00e7in.");
  const actionValue=String(form.get("action")||"");let action=null;if(actionValue){try{action=JSON.parse(actionValue)}catch{throw Error("Ba\u011fl\u0131 i\u015flem ge\u00e7ersiz.")}}if(action?.type==="page")action.auto_search=!!form.get("auto_search");
  scenarios[name]={...(scenarios[name]||{}),triggers:triggerList,...(action?{action}:{})};if(!action)delete scenarios[name].action;state.scenarios=scenarios;state.active=name;
  const command=state.commands.find(item=>item.name===name);if(command&&triggerList.length)command.phrase=triggerList[0];voiceCommandSaveState(state);render();return true;
 },"Senaryoyu Kaydet");
 const activeSelect=document.querySelector("#voiceScenarioName"),triggerInput=document.querySelector("#voiceScenarioTriggers"),actionSelect=document.querySelector("#voiceScenarioAction"),autoSearch=document.querySelector('[name="auto_search"]');
 const syncScenario=()=>{const config=scenarios[activeSelect?.value]||{},action=config.action||null;triggerInput.value=Array.isArray(config.triggers)?config.triggers.join("\n"):"";const payload=action?JSON.stringify(action.type==="page_search"?{type:"page",index:action.index}:action):"";actionSelect.value=[...actionSelect.options].some(option=>option.value===payload)?payload:"";autoSearch.checked=!!(action?.auto_search||action?.type==="page_search")};activeSelect?.addEventListener("change",syncScenario);syncScenario();
 const removeButton=document.createElement("button");removeButton.type="button";removeButton.className="danger";removeButton.textContent="Senaryoyu Sil";removeButton.addEventListener("click",()=>{const name=activeSelect.value;delete scenarios[name];state.scenarios=scenarios;state.commands=state.commands.filter(item=>item.name!==name);state.active=Object.keys(scenarios)[0]||"";voiceCommandSaveState(state);document.querySelector("#appDialog")?.close();render()});document.querySelector("#dialogFooter")?.prepend(removeButton);
}
function voiceCommandCardMarkup(item,index){return `<article class="p9-voice-command" data-voice-command-row data-group="${esc(item.group||"")}"><div class="p9-voice-command-main"><strong>${esc(item.name||"")}</strong><span>${esc(item.detail||"")}</span></div><code>Tetikleyici: ${esc(item.phrase||"")}</code><button type="button" aria-label="Komutu kopyala" data-voice-copy="${index}">\u25a3</button><button type="button" aria-label="Komutu dinle" data-voice-speak="${index}">\u25b6</button></article>`}
function renderPart9VoiceCommandSettings(){
 const state=voiceCommandState();
  const alertDefinitions=[["loan_reminder","Kredi Taksit","G\u00fcnl\u00fck Hat\u0131rlatma","11:00"],["check_reminder","\u00c7ek / Senet","Vade Takibi","11:30"],["stock_critical","Kritik Stok","Depo E\u015fik Kontrol\u00fc","15:00"],["service_delivery","Servis Teslim Uyar\u0131s\u0131","Geciken \u0130\u015f Emirleri","17:30"]];
  const alerts=alertDefinitions.map(([type,name,detail,defaultTime],index)=>{const saved=state.alerts[index]||{},live=scheduledAlerts.find(item=>item.alert_type===type);return{type,id:live?.id,name,detail,time:live?.trigger_time||saved.time||defaultTime,enabled:live?String(live.is_enabled)!=="0":saved.enabled!==false}});
  const alertRows=alerts.map((item,index)=>`<label class="p9-voice-alert"><b>${String(index+1).padStart(2,"0")}</b><span><strong>${esc(item.name)}</strong><small>${esc(item.detail||"")}</small></span><input type="time" value="${esc(item.time)}" data-voice-alert-time="${item.type}" ${item.id?"":"disabled"}><input type="checkbox" ${item.enabled?"checked":""} data-voice-alert="${item.type}" data-voice-alert-enabled="${item.type}" ${item.id?"":"disabled"} aria-label="${esc(item.name)} etkin"></label>`).join("");
 return `<section class="p9-voice-page">
  <header class="p9-voice-brand"><div class="p9-voice-brand-mark">\u25c9</div><div><h2>AYEC Pro <span>| Sesli Senaryo &amp; AI Komut Merkezi</span> <small>v3.2 BETA</small></h2><p>Akilli Sesli Asistan, Tetikleyici Senaryolar ve Zamanlanmis Bildirim Yonetimi</p></div><div class="p9-voice-engine"><span>\u25cf Ses Motoru: Haz\u0131r</span><button type="button" data-voice-refresh>\u27f3 Yenile</button></div></header>
  <div class="p9-voice-stats"><article><small>HAZIR KOMUT SABLONLARI</small><strong>26 G\u00f6m\u00fcl\u00fc Senaryo</strong><span>Ontanimli kurumsal aksiyon havuzu hazir</span></article><article><small>TETIKLEME MANTIGI</small><strong>Uyanma Adi + En Uzun Eslesme</strong><span>Baglanti/MLP agirlikli tespit</span></article><article><small>DUZENLEME DAVRANISI</small><strong>Aninda Kaydet, Isterse Sil</strong><span>Canli veri senkronizasyonu devrede</span></article></div>
  <div class="p9-voice-main"><section class="p9-voice-panel p9-voice-commands"><header><div><h3>\u2726 \u00d6nerilen En G\u00fc\u00e7l\u00fc Komutlar</h3><p>Ses K\u00fct\u00fcphanesi &amp; Operasyonel H\u0131z Tetikleyiciler</p></div><span class="p9-voice-count">${state.commands.length} Komut Haz\u0131r</span></header><input class="p9-voice-search" type="search" placeholder="\u2315 Komut veya tetikleyici ara..." data-voice-search><div class="p9-voice-filters">${["T\u00fcm\u00fc","Finans","Stok","Servis","Raporlar"].map((label,index)=>`<button type="button" class="${index===0?"active":""}" data-voice-filter="${label}">${label}</button>`).join("")}</div><div class="p9-voice-command-list" data-voice-list>${state.commands.map(voiceCommandCardMarkup).join("")}</div><footer><button type="button" class="p9-voice-add" data-voice-add="command">\uff0b Yeni Sesli Komut Ekle</button><button type="button" data-voice-export>\u21e7 \u015eablonlar\u0131 D\u0131\u015fa Aktar</button><button type="button" data-voice-import-trigger>\u21e9 Masa\u00fcst\u00fcnden Senaryo Al</button><input type="file" accept="application/json,.json" data-voice-import-file hidden></footer></section>
  <div class="p9-voice-right"><section class="p9-voice-panel p9-voice-operation"><header><div><h3>\u{1f399} Sesli Senaryo Operasyon Masas\u0131</h3><p>Senaryolar\u0131, tetikleyicileri ve test i\u015flemlerini y\u00f6netin.</p></div><span class="p9-voice-active">\u25cf Aktif Senaryo: <b data-voice-active>${esc(state.active)}</b></span></header><div class="p9-voice-meta">\u2139 AI Asistan Sayfasi: 24 tetikleyici kural tanimli, islem hedefi: Sayfa 170. D\u00fczenleme i\u00e7in pencereyi a\u00e7abilirsiniz. <code>ID: #MOD-170-VOICE</code></div><div class="p9-voice-actions"><button class="primary" type="button" data-voice-manage>\u2723 Senaryolar\u0131 Y\u00f6net</button><button type="button" data-voice-add="scenario">\uff0b Senaryo Ekle</button><button type="button" data-voice-load>\u21e9 Haz\u0131r Senaryolar\u0131 Y\u00fckle</button><button type="button" data-voice-repair>\u270e Eski Senaryolar\u0131 D\u00fczelt</button><button type="button" data-voice-test>\u{1f399} Aktif Senaryoyu Test Et</button><button type="button" data-voice-health>\u2667 Sa\u011fl\u0131k Testi \u00c7al\u0131\u015ft\u0131r</button></div><p class="p9-voice-result" data-voice-result>Son test sonucu: Hen\u00fcz \u00e7al\u0131\u015ft\u0131r\u0131lmad\u0131</p></section>
   <section class="p9-voice-panel p9-voice-live"><header><h3>\u25c9 CANLI SES ALGILAMA &amp; AI TANIMA TEST PANELI</h3><span class="p9-voice-live-status" data-voice-mic-status>\u25cf Ses Motoru: Haz\u0131r</span></header><div><div><p>Mikrofon<br><b data-voice-mic>Haz\u0131r / Beklemede</b><br>Alg\u0131lama Gecikmesi: <b data-voice-latency>\u00d6l\u00e7\u00fclmedi</b><br>Son Test Durumu: <b data-voice-last-test>Bekleniyor</b></p><button type="button" data-voice-listen>\u{1f399} Komut Dinle</button></div><span class="p9-voice-spectrum" aria-label="Canl\u0131 spektrum">\u2582 \u2585 \u2583 \u2587 \u2584 \u2586 \u2582 \u2585<small>CANLI SPEKTRUM ANAL\u0130Z\u0130</small></span></div></section>
   <div class="p9-voice-bottom"><section class="p9-voice-panel p9-voice-alerts"><header><div><h3>\u25f7 Zamanlanm\u0131\u015f Uyar\u0131lar</h3><p>Uyar\u0131 saatlerini ve aktiflik durumlar\u0131n\u0131 y\u00f6netin.</p></div><a href="#" data-voice-log>Uyar\u0131 Durumunu G\u00f6r \u2192</a></header>${alertRows}<footer><span data-voice-alert-count>${alerts.filter(item=>item.enabled).length} zamanlanm\u0131\u015f g\u00f6rev aktif.</span></footer></section><section class="p9-voice-panel p9-voice-dnd"><header><div><h3>\u263e Sessiz Saatler &amp; Sentez</h3><p>Bildirim susturma ve konu\u015fma sesi ayarlar\u0131.</p></div></header><div class="p9-voice-time-fields"><label>Ba\u015flang\u0131\u00e7 Saati<input type="time" value="${esc(state.start)}" data-voice-start></label><label>Biti\u015f Saati<input type="time" value="${esc(state.end)}" data-voice-end></label></div><label class="p9-voice-critical"><input type="checkbox" ${state.critical?"checked":""} data-voice-critical><span><b>Kritik uyar\u0131larda sessiz modu yoksay</b><small>Acil finansal vadeler ve asgari g\u00fcvenlik seviyesi uyar\u0131lar\u0131 iletilir.</small></span></label><div class="p9-voice-synthesis"><label>\u25d6 Ses \u015eiddeti <input type="range" min="0" max="100" value="${state.volume}" data-voice-volume><b data-voice-volume-value>%${state.volume}</b></label><label>H\u0131z <select data-voice-speed><option value="0.8" ${state.speed===0.8?"selected":""}>0.8\u00d7</option><option value="1" ${state.speed===1?"selected":""}>1.0\u00d7</option><option value="1.2" ${state.speed===1.2?"selected":""}>1.2\u00d7</option></select></label><span>\u2713 Senkronize</span></div></section></div>
  </div></div>
 </section>`
}
settingsGroups[1][1].push(["voice-command-settings","[VOICE]","AYEC Pro Sesli Komut Ayarlari"]);
const voiceCommandSettingBodyBefore=settingBody;
settingBody=function(settings){return settingsSection==="voice-command-settings"?renderPart9VoiceCommandSettings():voiceCommandSettingBodyBefore(settings)};
const voiceCommandBindPageBefore=bindPage;
bindPage=function(){
 voiceCommandBindPageBefore();
 if(page!=="settings"||settingsSection!=="voice-command-settings")return;
 const state=voiceCommandState();
  const persist=()=>{state.start=$("[data-voice-start]").value;state.end=$("[data-voice-end]").value;state.critical=$("[data-voice-critical]").checked;state.volume=Number($("[data-voice-volume]").value);state.speed=Number($("[data-voice-speed]").value);voiceCommandSaveState(state)};
 const refreshList=(filter="T\u00fcm\u00fc",query="")=>{$$('[data-voice-command-row]').forEach(row=>{row.hidden=(filter!=="T\u00fcm\u00fc"&&row.dataset.group!==filter)||!row.textContent.toLocaleLowerCase("tr-TR").includes(query.toLocaleLowerCase("tr-TR"))})};
 let activeFilter="T\u00fcm\u00fc";
 $$("[data-voice-filter]").forEach(button=>button.onclick=()=>{activeFilter=button.dataset.voiceFilter;$$("[data-voice-filter]").forEach(item=>item.classList.toggle("active",item===button));refreshList(activeFilter,$("[data-voice-search]").value)});
 $("[data-voice-search]")?.addEventListener("input",event=>refreshList(activeFilter,event.target.value));
 $$('[data-voice-add]').forEach(button=>button.onclick=()=>{
  const scenario=button.dataset.voiceAdd==="scenario";
  const title=scenario?"Yeni Senaryo":"Yeni Sesli Komut";
  const body=`<div class="form-grid"><div class="field full"><label>Senaryo / komut ad\u0131<input name="name" required maxlength="120" placeholder="\u00d6rn: Asistan randevular\u0131 listele"></label></div><div class="field full"><label>Tetikleyici ifade<input name="phrase" required maxlength="160" placeholder="\u00d6rn: Randevular\u0131m"></label></div></div>`;
  openDialog(title,"SES KOMUTLARI",body,form=>{
   const name=String(form.get("name")||"").trim(),phrase=String(form.get("phrase")||"").trim();
   if(!name||!phrase)throw Error("Senaryo ad\u0131 ve tetikleyici ifade gereklidir.");
   if(state.commands.some(item=>String(item.name||"").toLocaleLowerCase("tr-TR")===name.toLocaleLowerCase("tr-TR")))throw Error("Bu senaryo ad\u0131 zaten kullan\u0131l\u0131yor.");
   state.commands.push({name,phrase:`"${phrase}"`,detail:"Yeni \u00f6zel senaryo",group:"Servis"});
   if(scenario){state.active=name;state.scenarios[name]={triggers:[`"${phrase}"`],action:null};}
   voiceCommandSaveState(state);render();return true;
  },scenario?"Senaryoyu Ekle":"Komutu Ekle");
 });
 $("[data-voice-manage]")?.addEventListener("click",()=>openVoiceScenarioEditor(state));
 $("[data-voice-load]")?.addEventListener("click",()=>{
  const added=Object.keys(voiceScenarioDefaults).filter(name=>!state.scenarios[name]).length;
  state.scenarios=voiceRepairScenarios(state.scenarios);
  if(!Object.hasOwn(state.scenarios,state.active))state.active=Object.keys(state.scenarios).sort()[0]||"";
  voiceCommandSaveState(state);render();toast(added?`${added} hazir senaryo eklendi.`:"Hazir senaryolar zaten yuklu.",added?"success":"warning")
 });
 $("[data-voice-repair]")?.addEventListener("click",()=>{
  state.scenarios=voiceRepairScenarios(state.scenarios);
  state.commands=state.commands.filter(item=>item&&item.name&&item.phrase);
  if(!Object.hasOwn(state.scenarios,state.active))state.active=Object.keys(state.scenarios).sort()[0]||"";
  voiceCommandSaveState(state);render();toast("Eski senaryo kay\u0131tlar\u0131 onar\u0131ld\u0131","success")
 });
 $("[data-voice-test]")?.addEventListener("click",()=>{
  const scenario=state.scenarios[state.active],example=scenario?.triggers?.[0]||"",body=`<div class="field"><label>Komutu tam ifade olarak girin<input name="sample" required maxlength="240" placeholder="${esc(example)}" value="${esc(example)}"></label></div>`;
  openDialog("Aktif Senaryoyu Test Et","SES KOMUTU TESTI",body,form=>{
   const sample=String(form.get("sample")||"").trim();if(!sample)throw Error("Test etmek icin bir komut girin.");
   const match=voiceScenarioMatch({scenarios:{[state.active]:scenario}},sample),action=match.action,actionLabel=action?.type==="builtin"?action.name:action?.type==="page"?`Sayfa ${action.index}`:"Baglanti Yok";
   const result=$("[data-voice-result]");if(match.matched){result.textContent=`${sample} | ${match.name} | ${match.phrase} | ${actionLabel}`;toast(`Tetiklendi: ${match.name} | ${actionLabel}`,"success")}else{result.textContent=`${sample} | Aksiyon: Tetiklenmedi | Parametre: -`;toast("Komut tetiklenmedi. Uyanma adi ve tetikleyicileri kontrol edin.","warning")}
   $("[data-voice-mic]").textContent=match.matched?"Test tamamlandi":"Komut tetiklenmedi";return true;
  },"Test Et");
 });
 $("[data-voice-health]")?.addEventListener("click",async()=>{try{await runVoiceScenarioHealthcheck(state)}catch(error){const result=$("[data-voice-result]");result.textContent=`Saglik testi tamamlanamadi: ${error.message||"beklenmeyen hata"}`;toast(result.textContent,"error")}});
 $("[data-voice-refresh]")?.addEventListener("click",()=>{$("[data-voice-mic-status]").textContent="\u25cf Ses Motoru: Haz\u0131r";$("[data-voice-mic]").textContent="Haz\u0131r / Beklemede"});
 $("[data-voice-import-trigger]")?.addEventListener("click",()=>$("[data-voice-import-file]")?.click());
 $("[data-voice-import-file]")?.addEventListener("change",async event=>{const file=event.target.files?.[0];if(!file)return;try{if(file.size>1048576)throw Error("Scenario file exceeds the 1 MB limit.");const parsed=JSON.parse(await file.text()),incoming=parsed?.scenarios&&typeof parsed.scenarios==="object"&&!Array.isArray(parsed.scenarios)?parsed.scenarios:parsed;if(!incoming||typeof incoming!=="object"||Array.isArray(incoming)||!Object.keys(incoming).length)throw Error("No scenarios were found in the file.");const scenarios=voiceRepairScenarios(incoming);if(!Object.keys(scenarios).length)throw Error("No valid scenarios were found in the file.");state.scenarios=scenarios;state.active=Object.hasOwn(scenarios,state.active)?state.active:Object.keys(scenarios).sort()[0];voiceCommandSaveState(state);render();toast("Desktop scenario file imported.","success")}catch(error){toast(error.message||"Could not read the scenario file.","error")}finally{event.target.value=""}});
 $("[data-voice-export]")?.addEventListener("click",()=>{const blob=new Blob([JSON.stringify(state.scenarios,null,2)],{type:"application/json;charset=utf-8"});const link=document.createElement("a");link.href=URL.createObjectURL(blob);link.download="sesli-komut-sablonlari.json";link.click();URL.revokeObjectURL(link.href)});
 $$('[data-voice-copy]').forEach(button=>button.onclick=()=>navigator.clipboard?.writeText(state.commands[Number(button.dataset.voiceCopy)]?.name||""));
 $$('[data-voice-speak]').forEach(button=>button.onclick=()=>{const text=state.commands[Number(button.dataset.voiceSpeak)]?.name||"";if("speechSynthesis" in window){const utterance=new SpeechSynthesisUtterance(text);utterance.volume=Math.max(0,Math.min(1,state.volume/100));utterance.rate=state.speed;speechSynthesis.speak(utterance)}});
 $("[data-voice-listen]")?.addEventListener("click",()=>{
   const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition,mic=$("[data-voice-mic]"),status=$("[data-voice-mic-status]"),button=$("[data-voice-listen]");
   const setStatus=value=>{if(status)status.textContent=`\u25cf ${value}`};
   if(!Recognition){if(mic)mic.textContent="Bu taray\u0131c\u0131da ses tan\u0131ma desteklenmiyor";setStatus("Ses tan\u0131ma desteklenmiyor");return}
   const recognition=new Recognition();recognition.lang="tr-TR";recognition.interimResults=false;recognition.maxAlternatives=1;const startedAt=performance.now();
   if(mic)mic.textContent="Dinleniyor...";if(button)button.disabled=true;setStatus("Dinleniyor...");
   recognition.onresult=event=>{const transcript=String(event.results?.[0]?.[0]?.transcript||""),match=voiceScenarioMatch(state,transcript),latency=$("[data-voice-latency]"),lastTest=$("[data-voice-last-test]");if(mic)mic.textContent=transcript;if(latency)latency.textContent=`${Math.max(0,Math.round(performance.now()-startedAt))} ms`;if(lastTest)lastTest.textContent=match.matched?"E\u015fle\u015fme bulundu":"E\u015fle\u015fme yok";setStatus("Komut alg\u0131land\u0131");$("[data-voice-result]").textContent=`Alg\u0131lanan komut: ${transcript}`;const dispatch=voiceScenarioDispatch(state,transcript);if(dispatch.matched&&dispatch.route)toast(`Senaryo ${dispatch.route} sayfas\u0131n\u0131 a\u00e7t\u0131`);else if(dispatch.matched&&dispatch.action==="builtin"&&!dispatch.executed)toast("Bu yerle\u015fik i\u015flem web surumunde henuz uygulanmiyor","warning")};
   recognition.onerror=()=>{const lastTest=$("[data-voice-last-test]");if(lastTest)lastTest.textContent="Ba\u015far\u0131s\u0131z";if(mic)mic.textContent="Mikrofon izni veya ba\u011flant\u0131s\u0131 gerekli";setStatus("Mikrofon eri\u015fimi gerekli")};
   recognition.onend=()=>{if(button)button.disabled=false;if(mic?.textContent==="Dinleniyor..."){mic.textContent="Haz\u0131r / Beklemede";const lastTest=$("[data-voice-last-test]");if(lastTest)lastTest.textContent="Sonu\u00e7 al\u0131namad\u0131";setStatus("Haz\u0131r")}};
   try{recognition.start()}catch{if(button)button.disabled=false;const lastTest=$("[data-voice-last-test]");if(lastTest)lastTest.textContent="Ba\u015far\u0131s\u0131z";if(mic)mic.textContent="Mikrofon kullan\u0131lam\u0131yor";setStatus("Mikrofon kullan\u0131lam\u0131yor")}
  });
 $("[data-voice-volume]")?.addEventListener("input",event=>$("[data-voice-volume-value]").textContent=`%${event.target.value}`);
  $(".p9-voice-page")?.addEventListener("change",event=>{
   const target=event.target,isTime=target.matches("[data-voice-alert-time]"),isEnabled=target.matches("[data-voice-alert-enabled]"),settingsChanged=target.matches("[data-voice-start],[data-voice-end],[data-voice-critical],[data-voice-volume],[data-voice-speed]");
   if(!isTime&&!isEnabled&&!settingsChanged)return;
   persist();if(isTime)saveVoiceReminderTime(target);if(isEnabled)saveVoiceReminder(target);
   const active=scheduledAlerts.filter(item=>String(item.is_enabled??1)==="1").length;$("[data-voice-alert-count]").textContent=`${active} zamanlanmis gorev aktif.`;
   desktopWrite("settings",{key:"quiet_hours_start",value:state.start});desktopWrite("settings",{key:"quiet_hours_end",value:state.end});desktopWrite("settings",{key:"critical_override_dnd",value:state.critical?"1":"0"});desktopWrite("settings",{key:"voice_volume",value:String(state.volume)});desktopWrite("settings",{key:"voice_speed",value:String(state.speed)})
  });
  $("[data-voice-log]")?.addEventListener("click",event=>{event.preventDefault();openVoiceReminderLog().catch(error=>toast(`Uyar\u0131 durumu y\u00fcklenemedi: ${error.message||"beklenmeyen hata"}`,"error"))});
}
