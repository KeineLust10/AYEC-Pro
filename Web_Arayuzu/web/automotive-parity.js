"use strict";

// Responsive web and mobile parity additions for stock and automotive flows.
(function automotiveParity(){
  const baseRenderStock=renderStock;
  const baseStockTable=stockTable;
  const baseBindPage=bindPage;
  const baseProductForm=productForm;
  const baseSaveProduct=saveProduct;
  const baseHydrateDesktop=hydrateDesktop;
  const baseCustomer360=customer360;
  const baseServiceDetailDialog=serviceDetailDialog;
  const baseTechnicianDialog=technicianDialog;
  const baseContextAction=contextAction;
  let webVehicles=[];
  const automotiveDamageZones=[
    ["On",["On Tampon","Kaput","Sol On Camurluk","Sag On Camurluk"]],
    ["Arka",["Arka Tampon","Bagaj","Sol Arka Camurluk","Sag Arka Camurluk"]],
    ["Sol",["Sol On Kapi","Sol Arka Kapi","Sol Ayna","Sol Marspiyel"]],
    ["Sag",["Sag On Kapi","Sag Arka Kapi","Sag Ayna","Sag Marspiyel"]]
  ];
  const automotiveDamageStatuses=["Yok","Cizik","Gocuk","Boya Hasari","Kirildi"];
  const automotiveChecklistTemplates={
    servis_kabul:[{name:"Yakit Seviyesi"},{name:"Ikaz Lambalari"},{name:"Ruhsat Teslimi"},{name:"Yedek Anahtar"},{name:"Kaporta Gorunumu"},{name:"Dis Aydinlatma"}],
    bakim_oncesi:[{name:"Motor Yagi",required:true},{name:"Fren Balatalari"},{name:"Aku Durumu"},{name:"Sivi Seviyeleri",required:true},{name:"Lastik Durumu"},{name:"OBD Taramasi"}],
    bakim_sonrasi:[{name:"Yol Testi"},{name:"Ariza Lambasi Kontrolu",required:true},{name:"Servis Bakim Isigi Reset"},{name:"Teslim Oncesi Temizlik"},{name:"Musteri Bilgilendirme",required:true},{name:"Fatura Hazirligi"}]
  };
  const automotiveChecklistStatuses=["Tamam","Degismeli","Incelenmeli"];
  const maintenanceVehicleCatalog={
    Ford:["Courier","Connect","Focus","Fiesta","Transit"],
    Fiat:["Doblo","Egea","Fiorino","Linea"],
    Renault:["Clio","Fluence","Kangoo","Megane","Symbol"],
    Volkswagen:["Caddy","Golf","Jetta","Passat","Polo","Transporter"],
    Peugeot:["208","301","308","Partner","Rifter"],
    Toyota:["Corolla","Hilux","RAV4","Yaris"],
    Hyundai:["Accent","i10","i20","i30","Tucson"],
    Opel:["Astra","Combo","Corsa","Insignia"]
  };
  const maintenanceVehicleTypes=["Binek","Hafif Ticari","SUV","Minivan","Kamyonet","Motosiklet","Diger"];
  const maintenanceEngineTypes=["Benzinli","Dizel","Hibrit","Elektrikli","LPG","Turbo Dizel","Diger"];
  const maintenanceFuelTypes=["Benzin","Dizel","LPG","Elektrik","Hibrit","Diger"];

  function normalizeAutomotiveDamage(value){
    const parsed=typeof value==="string"?parseJson(value,{}):(value||{});
    return Array.isArray(parsed)?{items:parsed.filter(item=>item&&typeof item==="object"),general_note:""}:{items:Array.isArray(parsed.items)?parsed.items.filter(item=>item&&typeof item==="object"):[],general_note:String(parsed.general_note||"")};
  }

  function automotiveDamageCount(value){
    return normalizeAutomotiveDamage(value).items.filter(item=>item&&((item.status&&item.status!=="Yok")||String(item.note||"").trim())).length;
  }

  function openAutomotiveDamageDialog(value,onSave){
    const current=normalizeAutomotiveDamage(value);
    const entries=new Map(current.items.map(item=>[`${item.side}:${item.zone}`,item]));
    const dialog=document.createElement("dialog");
    dialog.className="automotive-damage-dialog";
    const sections=automotiveDamageZones.map(([side,zones])=>`<section class="automotive-damage-side"><h4>${side} Gorunus</h4>${zones.map(zone=>{
      const item=entries.get(`${side}:${zone}`)||{};
      return `<label class="automotive-damage-entry"><span>${zone}</span><select data-damage-status data-side="${side}" data-zone="${zone}">${automotiveDamageStatuses.map(status=>`<option value="${status}" ${String(item.status||"Yok")===status?"selected":""}>${status}</option>`).join("")}</select><input data-damage-note data-side="${side}" data-zone="${zone}" value="${esc(item.note||"")}" placeholder="Opsiyonel not"></label>`;
    }).join("")}</section>`).join("");
    const preview=automotiveDamageZones.map(([side,zones])=>`<section class="automotive-damage-preview-side"><h4>${side} Gorunus</h4><div>${zones.map(zone=>`<span data-damage-preview data-side="${side}" data-zone="${zone}">${zone}<b>Yok</b></span>`).join("")}</div></section>`).join("");
    dialog.innerHTML=`<form method="dialog" class="automotive-damage-panel"><header><div><h2>Hasar Tespit Formu</h2></div><button type="button" class="secondary" data-damage-cancel aria-label="Kapat">X</button></header><div class="automotive-damage-columns"><div class="automotive-damage-form"><p class="automotive-damage-intro">Aracin dort yonundeki bolgeleri isaretleyin. Hasar olmayan alanlari 'Yok' olarak birakin.</p>${sections}<label class="automotive-damage-general"><span>Genel Hasar Notu</span><textarea data-damage-general placeholder="Genel hasar notu">${esc(current.general_note)}</textarea></label></div><div class="automotive-damage-preview"><h3>Arac Uzeri Hasar Ozeti</h3><p>Secilen alanlar burada renkli olarak vurgulanir.</p>${preview}</div></div><footer><button type="button" class="secondary" data-damage-cancel>Iptal</button><button type="button" class="primary" data-damage-save>Hasar Formunu Kaydet</button></footer></form>`;
    document.body.appendChild(dialog);
    const refreshPreview=()=>dialog.querySelectorAll("[data-damage-preview]").forEach(badge=>{
      const side=badge.dataset.side,zone=badge.dataset.zone;
      const control=dialog.querySelector(`[data-damage-status][data-side="${side}"][data-zone="${zone}"]`);
      const status=control?.value||"Yok";
      const note=dialog.querySelector(`[data-damage-note][data-side="${side}"][data-zone="${zone}"]`)?.value||"";
      badge.querySelector("b").textContent=status;
      badge.dataset.status=status;
      badge.classList.toggle("has-note",Boolean(note.trim()));
    });
    dialog.addEventListener("change",event=>{if(event.target.matches("[data-damage-status]"))refreshPreview()});
    dialog.addEventListener("input",event=>{if(event.target.matches("[data-damage-note]"))refreshPreview()});
    dialog.querySelectorAll("[data-damage-cancel]").forEach(button=>button.addEventListener("click",()=>dialog.close("cancel")));
    dialog.querySelector("[data-damage-save]").addEventListener("click",()=>{
      const items=[];
      dialog.querySelectorAll("[data-damage-status]").forEach(control=>{
        const side=control.dataset.side,zone=control.dataset.zone;
        const note=dialog.querySelector(`[data-damage-note][data-side="${side}"][data-zone="${zone}"]`)?.value.trim()||"";
        if(control.value!=="Yok"||note)items.push({side,zone,status:control.value,note});
      });
      onSave({items,general_note:dialog.querySelector("[data-damage-general]").value.trim()});
      dialog.close("save");
    });
    dialog.addEventListener("close",()=>dialog.remove(),{once:true});
    refreshPreview();
    dialog.showModal();
  }

  function normalizeAutomotiveChecklist(value){
    const parsed=typeof value==="string"?parseJson(value,[]):(value||[]);
    let items=Array.isArray(parsed)?parsed:(Array.isArray(parsed.items)?parsed.items:[]);
    if(!Array.isArray(parsed)&&!Array.isArray(parsed.items)){
      const legacy={brakes:["bakim_oncesi","Fren Balatalari"],lights:["servis_kabul","Dis Aydinlatma"],battery:["bakim_oncesi","Aku Durumu"],tires:["bakim_oncesi","Lastik Durumu"],steering:["teknisyen_ek_kontrolleri","Direksiyon ve Suspansiyon"],fluids:["bakim_oncesi","Sivi Seviyeleri"],obd:["bakim_oncesi","OBD Taramasi"],road_test:["bakim_sonrasi","Yol Testi"]};
      items=Object.entries(legacy).filter(([key])=>typeof parsed[key]==="boolean").map(([key,[section,label]])=>({section,label,status:parsed[key]?"Tamam":"Incelenmeli",note:""}));
    }
    return {items:items.filter(item=>item&&typeof item==="object")};
  }

  function openAutomotiveChecklistDialog(value,onSave){
    const current=normalizeAutomotiveChecklist(value);
    const existing=new Map(current.items.map(item=>[`${item.section}:${item.label}`,item]));
    const dialog=document.createElement("dialog");
    dialog.className="automotive-checklist-dialog";
    const templates=Object.fromEntries(Object.entries(automotiveChecklistTemplates).map(([section,items])=>[section,[...items]]));
    current.items.forEach(item=>{if(item.label&&!templates[item.section]?.some(template=>template.name===item.label)){templates[item.section]=templates[item.section]||[];templates[item.section].push({name:item.label,required:false});}});
    const sections=Object.entries(templates).map(([section,items])=>`<section class="automotive-checklist-section"><h3>${section.replaceAll("_"," ")}</h3>${items.map(item=>{
      const key=`${section}:${item.name}`,saved=existing.get(key)||{};
      return `<label class="automotive-checklist-item"><span>${item.name}${item.required?'<b class="required-mark"> *</b>':""}</span><select data-checklist-status data-section="${section}" data-label="${item.name}">${automotiveChecklistStatuses.map(status=>`<option value="${status}" ${String(saved.status||"Tamam")===status?"selected":""}>${status}</option>`).join("")}</select><textarea data-checklist-note data-section="${section}" data-label="${item.name}" placeholder="Opsiyonel not">${esc(saved.note||"")}</textarea></label>`;
    }).join("")}</section>`).join("");
    dialog.innerHTML=`<form method="dialog" class="automotive-checklist-panel"><header><div><h2>Otomotiv Kontrol Formu</h2></div><button type="button" class="secondary" data-checklist-cancel aria-label="Kapat">X</button></header><div class="automotive-checklist-sections"><p class="automotive-checklist-intro">Kontrol kalemlerini Tamam, Degismeli veya Incelenmeli olarak isaretleyin ve gerekli notlari dusun.</p>${sections}</div><footer><button type="button" class="secondary" data-checklist-cancel>Iptal</button><button type="button" class="primary" data-checklist-save>Kontrol Formunu Kaydet</button></footer></form>`;
    document.body.appendChild(dialog);
    dialog.querySelectorAll("[data-checklist-cancel]").forEach(button=>button.addEventListener("click",()=>dialog.close("cancel")));
    dialog.querySelector("[data-checklist-save]").addEventListener("click",()=>{
      const items=[];
      dialog.querySelectorAll("[data-checklist-status]").forEach(control=>{
        const section=control.dataset.section,label=control.dataset.label;
        const note=dialog.querySelector(`[data-checklist-note][data-section="${section}"][data-label="${label}"]`)?.value.trim()||"";
        items.push({section,label,status:control.value,note});
      });
      onSave({items});
      dialog.close("save");
    });
    dialog.addEventListener("close",()=>dialog.remove(),{once:true});
    dialog.showModal();
  }

  function tr(value){
    const replacements=[
      ["Yeni Musteri Kaydi","Yeni M\u00fc\u015fteri Kayd\u0131"],
      ["Kayitli Musteri Sec","Kay\u0131tl\u0131 M\u00fc\u015fteri Se\u00e7"],
      ["Kayitli Musteri","Kay\u0131tl\u0131 M\u00fc\u015fteri"],
      ["Musteri Adi / Firma Unvani","M\u00fc\u015fteri Ad\u0131 / Firma \u00dcnvan\u0131"],
      ["Ad Soyad veya Kurumsal Firma Adi","Ad Soyad veya Kurumsal Firma Ad\u0131"],
      ["TCKN veya Vergi No","TCKN veya Vergi No"],
      ["Farkli ise teslim eden sahis","Farkl\u0131 ise teslim eden \u015fah\u0131s"],
      ["Irtibat GSM Numarasi","\u0130rtibat GSM Numaras\u0131"],["Envanter Eslesmesi","Envanter E\u015fle\u015fmesi"],["Teslim Alinan Aksesuar & Donanimlar","Teslim Al\u0131nan Aksesuar & Donan\u0131mlar"],["Ek Alanlari Gizle","Ek Alanlar\u0131 Gizle"],["Ek Servis Alanlari","Ek Servis Alanlar\u0131"],["Ek Servis Alanlarini Gizle","Ek Servis Alanlar\u0131n\u0131 Gizle"],
      ["Musteri Adi / Firma Unvani","M\u00fc\u015fteri Ad\u0131 / Firma \u00dcnvan\u0131"],
      ["Cihaz Turu","Cihaz T\u00fcr\u00fc"],
      ["Model Adi / Kodu","Model Ad\u0131 / Kodu"],
      ["Seri Numarasi veya IMEI girin","Seri Numaras\u0131 veya IMEI girin"],
      ["Tahmini Tutar (KDV Dahil)","Tahmini Tutar (KDV Dahil)"],
      ["Yeni Arac Servis Kaydi","Yeni Ara\u00e7 Servis Kayd\u0131"],
      ["Model Yili","Model Y\u0131l\u0131"],
      ["Sikayet / Yapilacak Is","\u015eikayet / Yap\u0131lacak \u0130\u015f"],
      ["Musteriye Acik Not","M\u00fc\u015fteriye A\u00e7\u0131k Not"],
      ["Aksesuarlar / Teslim Alinanlar","Aksesuarlar / Teslim Al\u0131nanlar"],
      ["Musteri Adi / Unvan","M\u00fc\u015fteri Ad\u0131 / Unvan"],
      ["Kimlik / Vergi No","Kimlik / Vergi No"],
      ["Iletisim Telefonu","\u0130leti\u015fim Telefonu"],
      ["Teslim Eden Kisi","Teslim Eden Ki\u015fi"],
      ["Teslim Eden Tel","Teslim Eden Tel"],
      ["Ariza Tanimi ve Musteri Sikayeti","Ar\u0131za Tan\u0131m\u0131 ve M\u00fc\u015fteri \u015eikayeti"],
      ["Musterinin bildirdigi arizalari ayrintili sekilde buraya yazin veya sesli dikte edin","M\u00fc\u015fterinin bildirdi\u011fi ar\u0131zalar\u0131 ayr\u0131nt\u0131l\u0131 \u015fekilde buraya yaz\u0131n veya sesli dikte edin"],
      ["Kaydi Tamamla ve Fis Olustur","Kayd\u0131 Tamamla ve Fi\u015f Olu\u015ftur"],
      ["Tahmini Tutar (KDV Dahil)","Tahmini Tutar (KDV Dahil)"],
      ["Kilit Deseni ve Guvenlik Sifresi","Kilit Deseni ve G\u00fcvenlik \u015eifresi"],
      ["Cihaz / Windows Acilis Sifresi","Cihaz / Windows A\u00e7\u0131l\u0131\u015f \u015eifresi"],
      ["BIOS / Supervisor Parolasi","BIOS / Supervisor Parolas\u0131"],
      ["Cihaz Gorseli ve Ekspertiz Fotograflari","Cihaz G\u00f6rseli ve Ekspertiz Foto\u011fraflar\u0131"],
      ["Fotograf yuklemek icin tiklayin veya surukleyin","Foto\u011fraf y\u00fcklemek i\u00e7in t\u0131klay\u0131n veya s\u00fcr\u00fckleyin"],
      ["En fazla 5 fotograf","En fazla 5 foto\u011fraf"],
      ["Deseni Sifirla","Deseni S\u0131f\u0131rla"],
      ["Orijinal Adapter","Orijinal Adapt\u00f6r"],
      ["Cihaz Cantasi","Cihaz \u00c7antas\u0131"],
      ["Kablo / Donusturucu","Kablo / D\u00f6n\u00fc\u015ft\u00fcr\u00fcc\u00fc"],
      ["Harici Disk / Flash","Harici Disk / Flash"],
      ["Goruntu Gelmiyor","G\u00f6r\u00fcnt\u00fc Gelmiyor"],
      ["Sivi Temasi","S\u0131v\u0131 Temas\u0131"],
      ["Asiri Isinma / Fan","A\u015f\u0131r\u0131 Is\u0131nma / Fan"],
      ["Format & Bakim","Format & Bak\u0131m"],
      ["Kaydettikten sonra servis formunu ac","Kaydettikten sonra servis formunu a\u00e7"],
      ["OTOMOTIV","OTOMOT\u0130V"],
      ["Secin","Se\u00e7in"],["Sasi","\u015easi"],["Acik","A\u00e7\u0131k"],
      ["Turu","T\u00fcr\u00fc"],["Alinanlar","Al\u0131nanlar"],
      ["TEKNISYEN","TEKN\u0130SYEN"],["Bos","Bo\u015f"],["Aku","Ak\u00fc"],
      ["sarj","\u015farj"],["ariza","ar\u0131za"],["alindi","al\u0131nd\u0131"],
      ["Yapilan","Yap\u0131lan"],["kullanilmadi","kullan\u0131lmad\u0131"],
      ["Yontemi","Y\u00f6ntemi"],["Karti","Kart\u0131"],["Notlari","Notlar\u0131"],
      ["Cikis","\u00c7\u0131k\u0131\u015f"],["cikis","\u00e7\u0131k\u0131\u015f"],
      ["Giris","Giri\u015f"],["giris","giri\u015f"],["Arac","Ara\u00e7"],["arac","ara\u00e7"],
      ["Musteri","M\u00fc\u015fteri"],["musteri","m\u00fc\u015fteri"],
      ["Duzenle","D\u00fczenle"],["duzenle","d\u00fczenle"],
      ["Kayit","Kay\u0131t"],["kayit","kay\u0131t"],["karti","kart\u0131"],["kaydi","kayd\u0131"],
      ["Yakit","Yak\u0131t"],["yakit","yak\u0131t"],["Yil","Y\u0131l"],["yil","y\u0131l"],
      ["Parca","Par\u00e7a"],["parca","par\u00e7a"],["Satis","Sat\u0131\u015f"],
      ["Urun","\u00dcr\u00fcn"],["urun","\u00fcr\u00fcn"],["Islem","\u0130\u015flem"],["islem","i\u015flem"],
      ["Iscilik","\u0130\u015f\u00e7ilik"],["Teknik Ic","Teknik \u0130\u00e7"],
      ["Odeme","\u00d6deme"],["Onay","Onay"],["Oncelik","\u00d6ncelik"],
      ["Dusuk","D\u00fc\u015f\u00fck"],["Yuksek","Y\u00fcksek"],["Simdi","\u015eimdi"],
      ["Sivi","S\u0131v\u0131"],["surusu","s\u00fcr\u00fc\u015f\u00fc"],["suspansiyon","s\u00fcspansiyon"],
      ["Alimi","Al\u0131m\u0131"],["Guncelleme","G\u00fcncelleme"],["guncellendi","g\u00fcncellendi"],
      ["Yonetici","Y\u00f6netici"],["onayi","onay\u0131"],["alinamadi","al\u0131namad\u0131"],
      ["okunamadi","okunamad\u0131"],["Atanmadi","Atanmad\u0131"],["Aydinlatma","Ayd\u0131nlatma"],
      ["Muadil","Muadil"],["Muayene","Muayene"],["Kullanilan","Kullan\u0131lan"],
      ["Tutari","Tutar\u0131"],["Bilinen","Bilinen"],["Tum","T\u00fcm"],["Raf","Raf"]
    ];
    return replacements.reduce((text,[plain,unicode])=>text.split(plain).join(unicode),String(value));
  }

  function automotiveMode(){
    return currentSector==="otomotiv";
  }

  function insertBeforeLastDiv(html,content){
    const index=html.lastIndexOf("</div>");
    return index<0?`${html}${content}`:`${html.slice(0,index)}${content}${html.slice(index)}`;
  }

  function stockSearchHtml(){
    return `<div class="stock-search-scan"><input class="control search" id="stockSearch" placeholder="${tr("Kod, barkod, OEM veya urun ara")}"><button class="secondary stock-search-camera" id="stockSearchCameraBtn" type="button" title="${tr("Kameradan barkod oku")}" aria-label="${tr("Kameradan barkod oku")}">&#128247;</button><input id="stockSearchCamera" type="file" accept="image/*" capture="environment" hidden></div>`;
  }

  renderStock=function(){
    const html=baseRenderStock();
    return html.replace(/<input class="control search" id="stockSearch"[^>]*>/,stockSearchHtml());
  };

  stockTable=function(rows){
    if(!automotiveMode())return baseStockTable(rows);
    return `<div class="table-wrap"><table><thead><tr><th>${tr("Kod / OEM")}</th><th>${tr("Parca")}</th><th>${tr("Marka / Kategori")}</th><th>${tr("Uyumlu Araclar")}</th><th>${tr("Raf")}</th><th>${tr("Stok")}</th><th>${tr("Satis")}</th><th>${tr("Durum")}</th><th></th></tr></thead><tbody>${rows.map(part=>`<tr data-kind="stock" data-id="${part.id}"><td><strong>${esc(part.code||"-")}</strong><br><small class="muted">OEM: ${esc(part.oem_code||"-")}</small><br><small class="muted">${esc(part.equivalent_code||"")}</small></td><td><strong>${esc(part.name)}</strong><br><small class="muted">${esc(part.barcode||"")}</small></td><td>${esc(part.brand||"-")}<br><span class="badge">${esc(part.category||"-")}</span></td><td>${esc(part.compatible_models||"-")}</td><td>${esc(part.shelf_number||"-")}</td><td>${part.qty}</td><td>${money(part.sell,part.currency)}</td><td>${statusBadge(part.qty<=part.min?tr("Kritik"):tr("Stokta"))}</td><td><div class="row-actions"><button class="mini" data-action="edit-product" data-id="${part.id}">${tr("Duzenle")}</button><button class="mini danger-outline" data-action="delete-product" data-id="${part.id}">${tr("Sil")}</button></div></td></tr>`).join("")}</tbody></table></div>`;
  };

  function filteredStockRows(){
    const query=String($("#stockSearch")?.value||"").trim().toLocaleLowerCase("tr-TR");
    const category=$("#stockCategory")?.value||tr("Tum Kategoriler");
    const level=$("#stockLevel")?.value||tr("Tum Seviyeler");
    return db.stock.filter(part=>{
      const text=[part.code,part.barcode,part.name,part.brand,part.category,part.oem_code,part.equivalent_code,part.compatible_models,part.vehicle_brand,part.vehicle_model,part.position,part.supplier,part.shelf_number].join(" ").toLocaleLowerCase("tr-TR");
      const categoryOk=/^T.m Kategoriler$/i.test(category)||part.category===category;
      const levelOk=/^T.m Seviyeler$/i.test(level)||(level.includes("Kritik")?part.qty<=part.min:part.qty>part.min);
      return (!query||text.includes(query))&&categoryOk&&levelOk;
    });
  }

  function refreshStockFilter(){
    const host=$("#stockTable");
    if(host)host.innerHTML=stockTable(filteredStockRows());
  }

  bindPage=function(){
    baseBindPage();
    const search=$("#stockSearch"),category=$("#stockCategory"),level=$("#stockLevel");
    if(search)search.oninput=refreshStockFilter;
    if(category)category.onchange=refreshStockFilter;
    if(level)level.onchange=refreshStockFilter;
    const camera=$("#stockSearchCameraBtn"),file=$("#stockSearchCamera");
    if(camera&&file)camera.onclick=event=>{
      event.preventDefault();
      const target=$("#stockSearch");
      file._ayecBarcodeTarget=target;
      void _ayecStartProductBarcodeLive(target,file);
    };
    if(file&&!file.dataset.parityBound){
      file.dataset.parityBound="1";
      file.onchange=async()=>{
        const source=file.files?.[0];
        if(!source)return;
        try{
          const value=await _ayecDecodeBarcodeImage(source);
          if(!value)throw Error(tr("Barkod okunamadi"));
          _ayecSetProductBarcode($("#stockSearch"),value);
          refreshStockFilter();
        }catch(error){toast(error.message,"error")}finally{file.value=""}
      };
    }
  };

  mountBarcodeButton=function(){
    document.querySelector('[data-action="barcode-scan"]')?.remove();
  };

  function automotiveDescriptionParts(value){
    const meta={supplier:"",vehicle_brand:"",vehicle_model:"",position:""},plain=[];
    const markerMap={OTO_SUPPLIER:"supplier",OTO_VEHICLE_BRAND:"vehicle_brand",OTO_VEHICLE_MODEL:"vehicle_model",OTO_POSITION:"position"};
    for(const line of String(value||"").split(/\r?\n/)){
      const match=line.trim().match(/^\[(OTO_SUPPLIER|OTO_VEHICLE_BRAND|OTO_VEHICLE_MODEL|OTO_POSITION)\]\s*(.*)$/);
      if(match)meta[markerMap[match[1]]]=match[2].trim();else plain.push(line);
    }
    return {description:plain.join("\n").trim(),...meta};
  }

  function composeAutomotiveDescription(description,meta){
    const values=automotiveDescriptionParts(description),fields={...values,...meta},lines=[];
    for(const [key,marker] of [["supplier","OTO_SUPPLIER"],["vehicle_brand","OTO_VEHICLE_BRAND"],["vehicle_model","OTO_VEHICLE_MODEL"],["position","OTO_POSITION"]]){
      const value=String(fields[key]||"").trim();if(value)lines.push(`[${marker}] ${value}`);
    }
    return [values.description,...lines].filter(Boolean).join("\n");
  }

  productForm=function(product={}){
    if(!automotiveMode())return baseProductForm(product);
    const metadata=automotiveDescriptionParts(product.description),normalized={...product,...metadata,description:metadata.description};
    const html=baseProductForm(normalized);
    const positions=["On Sol","On Sag","Arka Sol","Arka Sag","Sag","Sol","On","Arka","Motor","Sanziman","Ic Mekan","Dis Trim","Genel"];
    const fields=`<section class="automotive-fields"><h3>${tr("Otomotiv Parca Bilgileri")}</h3><div class="field"><label>OEM Kod</label><input name="oem_code" value="${esc(product.oem_code||"")}"></div><div class="field"><label>${tr("Muadil Kod")}</label><input name="equivalent_code" value="${esc(product.equivalent_code||"")}"></div><div class="field"><label>${tr("Arac Marka")}</label><input name="vehicle_brand" value="${esc(product.vehicle_brand||metadata.vehicle_brand)}"></div><div class="field"><label>${tr("Arac Model")}</label><input name="vehicle_model" value="${esc(product.vehicle_model||metadata.vehicle_model)}"></div><div class="field full"><label>${tr("Uyumlu Marka / Model / Yil")}</label><textarea name="compatible_models" placeholder="Ford Courier 2020-2026; Fiat Egea 2019-2025">${esc(product.compatible_models||"")}</textarea></div><div class="field"><label>${tr("Parca Konumu")}</label><input name="position" list="automotivePositionOptions" value="${esc(product.position||metadata.position)}"><datalist id="automotivePositionOptions">${positions.map(value=>`<option value="${value}">`).join("")}</datalist></div><div class="field"><label>${tr("Tedarikci")}</label><input name="supplier" value="${esc(product.supplier||metadata.supplier)}"></div><div class="field"><label>${tr("Raf / Konum")}</label><input name="shelf_number" value="${esc(product.shelf_number||"")}"></div></section>`;
    return insertBeforeLastDiv(html,fields);
  };

  saveProduct=async function(formData,existing){
    const values=Object.fromEntries(formData),currency=String(values.currency||"TRY").toUpperCase(),rate=rateForCode(currency);
    if(currency!=="TRY"&&rate<=0)throw Error(`${currency} ${tr("kuru alinamadi")}`);
    const description=automotiveMode()?composeAutomotiveDescription(values.description,{supplier:values.supplier,vehicle_brand:values.vehicle_brand,vehicle_model:values.vehicle_model,position:values.position}):values.description;
    const payload={
      id:existing&&/^\d+$/.test(String(existing.id))?+existing.id:undefined,
      name:values.name,code:values.code,barcode:values.barcode,category:values.category,
      brand:values.brand,currency,stock:+values.qty||0,min_stock:+values.min||0,
      purchase_price:+values.buy||0,price:+values.sell||0,description,unit:values.unit||"Adet",
      payment_method:values.payment_method,exchange_rate:rate,oem_code:values.oem_code||"",
      equivalent_code:values.equivalent_code||"",compatible_models:values.compatible_models||"",
      shelf_number:values.shelf_number||""
    };
    const result=await apiFetch("/api/desktop/stock/save",{method:"POST",body:JSON.stringify(payload)});
    const part=result.part,target=existing||{},savedDescription=part.description||description,metadata=automotiveDescriptionParts(savedDescription);
    Object.assign(target,{id:String(part.id),code:part.code||"",name:part.name||part.part_name||"",barcode:part.barcode||"",category:part.category||"Genel",brand:part.brand||"",currency:part.currency||"TRY",qty:Number(part.stock||0),min:Number(part.min_stock||0),buy:moneyNumber(part.purchase_price),sell:moneyNumber(part.price),description:savedDescription,unit:part.unit||"Adet",oem_code:part.oem_code||"",equivalent_code:part.equivalent_code||"",compatible_models:part.compatible_models||"",shelf_number:part.shelf_number||"",supplier:metadata.supplier,vehicle_brand:metadata.vehicle_brand,vehicle_model:metadata.vehicle_model,position:metadata.position});
    if(!existing)db.stock.unshift(target);
    if(result.movement_id)db.movements.unshift({id:String(result.movement_id),date:new Date().toLocaleString("tr-TR"),product:target.name,type:result.delta>0?tr("Giris"):tr("Cikis"),qty:Math.abs(result.delta),ref:existing?tr("Stok duzenleme"):tr("Urun ekleme"),user:tr("Yonetici")});
    if(result.finance_id)db.finance.unshift({id:String(result.finance_id),date:today(),type:"Gider",category:existing?tr("Stok Guncelleme"):tr("Stok Alimi"),amount:result.expense,original_amount:result.expense,try_equivalent:result.expense*result.exchange_rate,currency:result.currency,exchange_rate:result.exchange_rate,description:`${target.name} - ${Math.max(result.delta,0)}`,customer:""});
    save();activity(`${target.name} ${tr("stok karti kaydedildi")}`,"#");render();toast(tr("Urun, stok hareketi ve otomotiv bilgileri kaydedildi"),"success");return true;
  };

  hydrateDesktop=async function(quiet=true){
    const source=await baseHydrateDesktop(quiet);
    webVehicles=(source?.customer_vehicles||[]).map(vehicle=>({
      ...vehicle,
      id:String(vehicle.id),
      customerId:String(vehicle.customer_id||"")
    }));
    const sourceById=new Map((source?.stock||[]).map(part=>[String(part.id),part]));
    db.stock.forEach(part=>{
      const sourcePart=sourceById.get(String(part.id));
      if(!sourcePart)return;
      const description=sourcePart.description||part.description||"",metadata=automotiveDescriptionParts(description);
      Object.assign(part,{brand:sourcePart.brand||part.brand||"",description,oem_code:sourcePart.oem_code||"",equivalent_code:sourcePart.equivalent_code||"",compatible_models:sourcePart.compatible_models||"",shelf_number:sourcePart.shelf_number||"",supplier:metadata.supplier,vehicle_brand:metadata.vehicle_brand,vehicle_model:metadata.vehicle_model,position:metadata.position});
    });
    save();
    if(page==="stock"||page==="automotive-stock")render();
    return source;
  };

  saveCustomer=async function(formData,customer){return await persistCustomerProfile(formData,customer)};
  appointmentDialog=function(item){
    const automotive=automotiveMode();
    const selectedVehicleId=String(item?.source_ref_id||"");
    const vehicleField=automotive?`<div class="field full"><label>${tr("Arac")}</label><select name="vehicle_id" id="appointmentVehicle"><option value="">${tr("Arac secin")}</option></select></div>`:"";
    openDialog(
      item?tr("Randevuyu Duzenle"):tr("Yeni Randevu"),
      "PLANLAMA",
      `<div class="form-grid"><div class="field full"><label>${tr("Musteri")} *</label><select name="customerId" id="appointmentCustomer" required><option value="">${tr("Secin")}</option>${db.customers.map(customer=>`<option value="${customer.id}" ${String(item?.customerId)===String(customer.id)?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div>${vehicleField}<div class="field"><label>Tarih *</label><input name="date" type="date" required value="${item?.date||today()}"></div><div class="field"><label>Saat *</label><input name="time" type="time" required value="${item?.time||"09:00"}"></div><div class="field full"><label>Konu *</label><input name="title" required value="${esc(item?.title||"")}"></div><div class="field"><label>Durum</label><select name="status">${[tr("Planlandi"),tr("Onaylandi"),tr("Tamamlandi"),tr("Iptal")].map(value=>`<option ${item?.status===value?"selected":""}>${value}</option>`).join("")}</select></div></div>`,
      async formData=>{
        const values=Object.fromEntries(formData);
        const customer=db.customers.find(candidate=>String(candidate.id)===String(values.customerId));
        if(!customer)throw Error(tr("Musteri secin"));
        const vehicle=webVehicles.find(candidate=>String(candidate.id)===String(values.vehicle_id));
        const payload={
          customer_id:+customer.id,
          customer_name:customer.name,
          customer:customer.name,
          phone:customer.phone||"",
          date:values.date,
          time:values.time,
          description:values.title,
          status:values.status,
          source_type:automotive?"web_automotive":"web",
          source_ref_id:vehicle?+vehicle.id:null,
          device:vehicle?`${vehicle.brand||""} ${vehicle.model||""}`.trim():"",
          brand:vehicle?.brand||"",
          model:vehicle?.model||"",
          serial_no:vehicle?.plate||"",
          type:automotive?"vehicle_service":"service"
        };
        if(item&&Number.isInteger(+item.id))Object.assign(payload,{id:+item.id,_action:"update"});
        await apiFetch("/api/desktop/table/appointments",{
          method:"POST",
          body:JSON.stringify(payload)
        });
        await hydrateDesktop(true);
        activity(`${customer.name} ${tr("randevusu kaydedildi")}`,"#");
        toast(tr("Randevu kaydedildi ve uyari planlandi"),"success");
        return true;
      },
      item?tr("Guncelle"):tr("Randevu Ekle")
    );
    if(!automotive)return;
    const customerSelect=$("#appointmentCustomer"),vehicleSelect=$("#appointmentVehicle");
    const refreshVehicles=()=>{
      const customerId=String(customerSelect?.value||"");
      const choices=webVehicles.filter(vehicle=>vehicle.customerId===customerId);
      vehicleSelect.innerHTML=`<option value="">${tr("Arac secin")}</option>${choices.map(vehicle=>`<option value="${vehicle.id}" ${String(vehicle.id)===selectedVehicleId?"selected":""}>${esc(`${vehicle.plate||"-"} - ${vehicle.brand||""} ${vehicle.model||""}`.trim())}</option>`).join("")}`;
    };
    customerSelect.onchange=refreshVehicles;
    refreshVehicles();
  };

  serviceDialog=function(customerId=""){
    const automotive=automotiveMode();
    const technicians=desktopPersonnel.filter(person=>!person.role||/tekn|servis|usta|yonet/i.test(`${person.role} ${person.department||""}`));
    const selectedCustomer=db.customers.find(customer=>String(customer.id)===String(customerId));
    const intakeDamageMarks={items:[],general_note:""};
    const intakeChecklistData={items:[]};
    const warrantyOptions=automotive?["Yok","Var","Firma Garantisi"]:["Garantili","Garanti D\u0131\u015f\u0131","Bilinmiyor"];
    const warrantyField=`<div class="field"><label>${tr("Garanti")}</label><select name="warranty_status" ${automotive?"":"required"}>${warrantyOptions.map(value=>`<option>${esc(value)}</option>`).join("")}</select></div>`;
    const invoiceReadyField=automotive?`<label class="setting field full"><span>${tr("Fatura Hazir")}</span><input class="switch" type="checkbox" name="invoice_ready"></label>`:"";
    const assetFields=automotive
      ?`<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>${tr("Seri No")}</label><input name="serial"></div><div class="field"><label>${tr("Sasi / VIN")}</label><input name="vin"></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>${tr("Model Yili")}</label><input name="year" type="number" min="1950" max="2200"></div><div class="field"><label>${tr("Arac Tipi")}</label><input name="vehicle_type" placeholder="Binek, SUV, Ticari"></div><div class="field"><label>${tr("Motor Tipi")}</label><input name="engine_type"></div><div class="field"><label>${tr("Yakit Turu")}</label><select name="fuel_type"><option>Benzin</option><option>Dizel</option><option>Hibrit</option><option>Elektrik</option><option>LPG</option></select></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div><div class="field"><label>Servis Tipi *</label><select name="service_type" required><option>Periyodik Bak\u0131m</option><option>Motor Ar\u0131za</option><option>\u015eanz\u0131man</option><option>Fren Sistemi</option><option>Elektrik/Elektronik</option><option>Kaporta/Boya</option><option>Di\u011fer</option></select></div>`
      :`<div class="field"><label>${tr("Cihaz Turu")} *</label><select name="device_type" required><option value="Laptop / Notebook" selected>Laptop / Notebook</option><option value="Masa\u00fcst\u00fc Bilgisayar (PC)">Masa\u00fcst\u00fc Bilgisayar (PC)</option><option value="All-in-One PC">All-in-One PC</option><option value="Ak\u0131ll\u0131 Telefon / Tablet">Ak\u0131ll\u0131 Telefon / Tablet</option><option value="Sunucu / Server &amp; Storage">Sunucu / Server &amp; Storage</option><option value="Yaz\u0131c\u0131 / \u00c7evre Birimi">Yaz\u0131c\u0131 / \u00c7evre Birimi</option><option value="Di\u011fer">Di\u011fer</option></select></div><div class="field full" data-service-other-device hidden><label>${tr("Diger Cihaz Turu")} *</label><input name="other_device_type"></div><div class="field"><label>Marka *</label><input name="brand" list="serviceBrandOptions" value="Acer" required><datalist id="serviceBrandOptions"><option>Acer</option><option>Apple</option><option>Asus</option><option>Dell</option><option>HP</option><option>Lenovo</option><option>MSI</option><option>Monster</option><option>Di\u011fer / \u00d6zel Uretim</option></datalist></div><div class="field"><label>Model Adi / Kodu</label><input name="model" list="serviceModelOptions" placeholder="\u00d6rn: Aspire 7 A715-42G"><datalist id="serviceModelOptions"></datalist></div><div class="field"><label>Seri No / IMEI</label><input name="serial" placeholder="Seri Numaras\u0131 veya IMEI girin"></div>`;
    openDialog(
      automotive?tr("Yeni Arac Servis Kaydi"):tr("Yeni Servis Kayd\u0131 Olu\u015ftur"),
      automotive?"OTOMOTIV SERVIS KABUL FORMU":"M\u00fc\u015fteri kabul, cihaz donan\u0131m te\u015fhisi ve dijital servis kabul fi\u015fi olu\u015fturma sihirbaz\u0131",
      `<div class="service-accept-form">
        <div class="service-form-column service-form-left">
        <section class="service-form-card service-form-customer"><header class="service-form-card-head"><div><span class="service-form-icon">\u2659</span><div><h3>${tr("Musteri Bilgileri")}</h3><p class="service-form-state">${selectedCustomer?tr("Kayitli Musteri"):tr("Yeni Musteri Kaydi")}</p></div></div><input class="service-customer-picker service-customer-search" list="serviceCustomerOptions" aria-label="${tr("Kayitli Musteri Sec")}" placeholder="${tr("Ad Soyad veya Firma Unvani giriniz...")}" value="${esc(selectedCustomer?.name||"")}"><datalist id="serviceCustomerOptions">${db.customers.map(customer=>`<option value="${esc(customer.name)}"></option>`).join("")}</datalist><select name="customerId" aria-label="${tr("Kayitli Musteri Sec")}" hidden><option value="">${tr("Kayitli Musteri Sec")}</option>${db.customers.map(customer=>`<option value="${customer.id}" ${String(customer.id)===String(customerId)?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></header>
          <div class="field full"><label>${tr("Musteri Adi / Firma Unvani")} *</label><input name="customer_name" required value="${esc(selectedCustomer?.name||"")}" placeholder="${tr("Ad Soyad veya Kurumsal Firma Adi")}"></div>
          <div class="field"><label>${tr("Kimlik / Vergi No (TCKN / VKN)")}</label><input name="customer_identity" value="${esc(selectedCustomer?.tc_no||selectedCustomer?.tax_no||"")}" autocomplete="off" placeholder="${tr("TCKN veya Vergi No")}"></div><div class="field"><label>${tr("Iletisim Telefonu")} *</label><input name="customer_phone_input" value="${esc(selectedCustomer?.phone||"")}" inputmode="tel" placeholder="+90 (5XX) XXX XX XX" required></div>
          <div class="field"><label>${tr("Teslim Eden Kisi")}</label><input name="delivered_by_name" autocomplete="name" placeholder="${tr("Farkli ise teslim eden sahis")}"></div><div class="field"><label>${tr("Teslim Eden Tel")}</label><input name="delivered_by_phone" inputmode="tel" placeholder="${tr("Irtibat GSM Numarasi")}"></div>
        </section>
        <section class="service-form-card service-form-device"><header class="service-form-card-head"><div><span class="service-form-icon">\u25a3</span><h3>${tr("Cihaz Bilgileri")}</h3></div><div class="service-device-meta"><small>${tr("Envanter Eslesmesi: Otomatik")}</small></div></header><div class="form-grid service-device-fields">${assetFields}</div><div class="service-accessories"><span><span>${tr("Teslim Alinan Aksesuar & Donanimlar")}</span><button class="service-device-extra-toggle" type="button" aria-expanded="false" title="Teknisyen, tahmini teslim, garanti ve not alanlarini acar.">${tr("Ek Servis Alanlari")}</button></span><div class="service-accessory-options" data-service-accessory-options><label><input type="checkbox" name="accessory_option" value="Orijinal Adapter"><span>${tr("Orijinal Adapter")}</span></label><label><input type="checkbox" name="accessory_option" value="Cihaz Cantasi"><span>${tr("Cihaz Cantasi")}</span></label><label><input type="checkbox" name="accessory_option" value="Kablo / Donusturucu"><span>${tr("Kablo / Donusturucu")}</span></label><label><input type="checkbox" name="accessory_option" value="Harici Disk / Flash"><span>${tr("Harici Disk / Flash")}</span></label></div>
          <details class="service-extra-fields"><summary>${tr("Ek servis ve teslim bilgileri")}</summary><div class="service-extra-grid"><div class="field"><label>${tr("Teknisyen")}</label><select name="technician"><option value="">${tr("Atanmadi")}</option>${technicians.map(person=>`<option>${esc(person.name)}</option>`).join("")}</select></div><div class="field"><label>${tr("Tahmini Teslim")}</label><input name="estimated_date" type="date"></div><div class="field"><label>${tr("Aksesuarlar / Teslim Alinanlar")}</label><input name="accessories"></div>${warrantyField}<div class="field"><label>${tr("Durum")}</label><select name="status"><option>Bekliyor</option><option>${tr("Onay Bekliyor")}</option><option>${tr("Islemde")}</option><option>${tr("Parca Bekliyor")}</option></select></div><div class="field full"><label>${tr("Musteriye Acik Not")}</label><textarea name="repair_details"></textarea></div><div class="field full"><label>${tr("Teknik Ic Not")}</label><textarea name="internal_notes"></textarea></div><div class="field full"><label>${tr("Test / Kontrol Ozeti")}</label><textarea name="inspection_summary" placeholder="${tr("Teknik tespit ve kontrol ozeti")}"></textarea></div>${invoiceReadyField}<label class="setting field full service-open-form"><span>${tr("Kaydettikten sonra servis formunu ac")}</span><input class="switch" type="checkbox" name="open_form" checked></label></div></details>
        ${automotive?`<div class="service-form-damage"><strong>Arac Formlari</strong><button type="button" class="secondary" data-automotive-checklist-open>Kontrol Formu (0)</button><button type="button" class="secondary" data-automotive-damage-open>Hasar Tespiti (0)</button></div>`:""}
        </section>
        </div>
        <div class="service-form-column service-form-right">
        <section class="service-form-card service-form-fault"><header class="service-form-card-head"><div><span class="service-form-icon warning">\u26a0</span><h3>${tr("Ariza ve Servis Detaylari")}</h3></div><small class="service-ai-label">\u2728 ${tr("AI Destekli")}</small></header>
          <div class="field full"><div class="service-fault-label"><label>${automotive?tr("Sikayet / Yapilacak Is"):tr("Ariza Tanimi ve Musteri Sikayeti")} *</label><button type="button" class="service-speech-button">&#127908; ${tr("Sesle Yazdir")}</button></div><textarea name="fault" required placeholder="${tr("Musterinin bildirdigi arizalari ayrintili sekilde buraya yazin veya sesli dikte edin")}"></textarea></div>
          <div class="service-quick-issues field full">${["Goruntu Gelmiyor","Sivi Temasi","Asiri Isinma / Fan","Format & Bakim"].map(label=>`<button type="button" data-fault-shortcut="${tr(label)}">${tr(label)}</button>`).join("")}</div><div class="service-fault-note-toggles field full" data-service-fault-notes hidden><span class="muted" data-service-fault-selected></span><div data-service-fault-note-options></div></div>
          <div class="field"><label>${tr("Oncelik Derecesi")}</label><select name="priority"><option>Normal</option><option>${tr("Yuksek")}</option><option>Acil</option><option>${tr("Dusuk")}</option></select></div><div class="field"><div class="service-price-label"><label>${tr("Tahmini Tutar (KDV Dahil)")}</label><div class="service-currency-select" role="group" aria-label="${tr("Para Birimi")}"><button type="button" data-service-currency="TRY">&#8378;</button><button type="button" data-service-currency="USD">$</button><button type="button" data-service-currency="EUR">&euro;</button></div></div><div class="service-price-field"><input name="price" type="number" min="0" step="0.01" placeholder=""><select class="service-currency-native" name="currency" aria-label="${tr("Para Birimi")}"><option>TRY</option><option selected>USD</option><option>EUR</option></select></div></div>
        </section>
        <section class="service-form-card service-form-security">
          <div class="service-security-head"><h3>${tr("Kilit Deseni ve Guvenlik Sifresi")}</h3><span>${tr("Opsiyonel")}</span></div>
          <div class="service-pattern-box"><span>${tr("Desen Kilidi")}</span><div class="service-pattern-lock" role="group" aria-label="${tr("Desen Kilidi")}">${Array.from({length:9},(_,index)=>`<button type="button" class="service-pattern-dot" data-pattern-index="${index}" aria-label="${index+1}"></button>`).join("")}</div><button type="button" class="service-pattern-reset">${tr("Deseni Sifirla")}</button><input type="hidden" name="pattern_lock"></div>
          <div class="service-password-fields"><div class="field"><label>${tr("Cihaz / Windows Acilis Sifresi")}</label><input name="device_password" autocomplete="off"></div><div class="field"><label>BIOS / Supervisor ${tr("Parolasi")}</label><input name="bios_password" autocomplete="off"></div></div>
        </section>
        <section class="service-form-card service-form-photo"><header class="service-form-card-head"><div><span class="service-form-icon">\u25c6</span><h3>${tr("Cihaz Gorseli ve Ekspertiz Fotograflari")}</h3></div><small>${tr("En fazla 5 fotograf")}</small></header><label class="service-photo-drop"><span class="service-photo-upload-icon">\u2601</span><span>${tr("Fotograf yuklemek icin tiklayin veya surukleyin")}</span><small>${tr("Kasa cizigi, kirik mentese ve teslim ani durum tespitleri (PNG, JPG)")}</small><input name="device_photo" type="file" accept="image/png,image/jpeg" multiple></label><div class="service-photo-preview"><button type="button" aria-label="On Kasa">\u25a3<br>${tr("On Kasa")}</button><button type="button" aria-label="Fotograf Ekle">+</button><em>${tr("Teslim aninda cihazin fiziksel kusurlarini belgelemek musteri ihtilaflarini onler")}</em></div><div class="service-photo-selected-list" data-service-photo-selected></div></section>
       </div></div>`,
      async formData=>{
        const values=Object.fromEntries(formData);
        const invoiceReadyAt=automotive&&values.invoice_ready?new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,19).replace("T"," "):null;
        let customer=db.customers.find(item=>String(item.id)===String(values.customerId));
        if(!customer){
          const name=String(values.customer_name||"").trim();
          if(!name)throw Error(tr("Musteri adi girin"));
          const customerPayload={name,phone:values.customer_phone_input||"",email:"",type:values.customer_identity?"Kurumsal":"Bireysel",tc_no:values.customer_identity||"",tax_id:values.customer_identity||""};
          const savedCustomer=await apiFetch("/api/desktop/table/customers",{method:"POST",body:JSON.stringify(customerPayload)});
          if(!savedCustomer?.id)throw Error(tr("Musteri kaydi olusturulamadi"));
          customer={id:String(savedCustomer.id),desktopId:Number(savedCustomer.id),name,phone:customerPayload.phone,email:"",type:customerPayload.type,services:[],quotes:[],balances:{TRY:0,USD:0,EUR:0}};
          db.customers.push(customer);
        }
        const no=`SRV-${new Date().getFullYear()}${String(Date.now()).slice(-7)}`;
        const payload={
          tracking_no:no,
          customer_id:Number.isInteger(+customer.id)?+customer.id:null,
          customer_name:values.customer_name||customer.name,
          customer_phone:values.customer_phone_input||customer.phone||"",
          device_type:automotive?tr("Arac"):values.device_type==="Di\u011fer"?String(values.other_device_type||"").trim():values.device_type,
          device_brand:values.brand||"",
          device_model:values.model,
          vehicle_model_name:values.model,
          serial_no:values.serial||"",
          vehicle_plate:values.plate||"",
          vehicle_vin:values.vin||"",
          vehicle_year:+values.year||null,
          vehicle_type:values.vehicle_type||"",
          engine_type:values.engine_type||"",
          fuel_type:values.fuel_type||"",
          vehicle_odometer:+values.odometer||0,sector_extension:automotive?{vehicle_plate:values.plate||"",vehicle_vin:values.vin||"",current_km:values.odometer||"",service_type:values.service_type||""}:{device_type:values.device_type||"",serial_no:values.serial||"",warranty_status:values.warranty_status||""},
          fault_description:[...selectedFaultNotes,values.fault,values.repair_details&&values.repair_details.trim()?`[NOT]: ${values.repair_details}`:"",values.internal_notes&&values.internal_notes.trim()?`[TEKN\u0130K]: ${values.internal_notes}`:""].filter(Boolean).join("\n"),
          repair_details:values.repair_details,
          inspection_summary:values.inspection_summary||"",
          internal_notes:values.internal_notes,
          accessories:[...formData.getAll("accessory_option"),values.accessories].filter(Boolean).join(", "),
          device_password:values.device_password||"",
          bios_password:values.bios_password||"",
          pattern_lock:values.pattern_lock||"",
          delivered_by_name:values.delivered_by_name||"",
          delivered_by_phone:values.delivered_by_phone||"",
          price:+values.price||0,
          currency:values.currency||"USD",
          urgency:values.priority,
          priority:values.priority,
          technician:values.technician,
          status:values.status,
          approval_status:"Bekleme",
          entry_date:today(),
          estimated_date:values.estimated_date,
          invoice_ready_at:invoiceReadyAt,
          warranty_status:values.warranty_status,
          payment_status:"Beklemede",
          checklist:automotive?intakeChecklistData.items:undefined,
          damage_marks:automotive?intakeDamageMarks:undefined,
          service_source:automotive?"Web Otomotiv":"Web Teknik Servis"
        };
        const result=await apiFetch("/api/desktop/table/devices",{
          method:"POST",
          body:JSON.stringify(payload)
        });
        const photoFailures=[];
        for(const file of selectedServicePhotos){
          if(file.size>8*1024*1024){photoFailures.push(file.name);continue;}
          try{
            const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result||"").split(",",2)[1]||"");reader.onerror=()=>reject(Error("Photo could not be read"));reader.readAsDataURL(file);});
            await apiFetch("/api/desktop/external-tracking/photos",{method:"POST",body:JSON.stringify({tracking_no:no,label:file.name,data:encoded,stage:"Giri\u015f"})});
          }catch(error){photoFailures.push(file.name);}
        }
        const source=await hydrateDesktop(true);
        const serviceOwner=db.customers.find(item=>String(item.id)===String(customer.id));
        const service=serviceOwner?.services?.find(item=>String(item.id)===String(result.id)||item.no===no);
        activity(`${no} ${tr("servis kaydi olusturuldu")}`,"#");
        toast(photoFailures.length?tr("Servis kaydi eklendi; bazi fotograflar yuklenemedi"):tr("Servis kaydi musteri ve servis panosuna eklendi"),photoFailures.length?"warning":"success");
        if(values.open_form&&service)setTimeout(()=>serviceDetailDialog(serviceOwner,service),80);
        return Boolean(source);
      },
      automotive?tr("Arac Servisini Kaydet"):tr("Kaydi Tamamla ve Fis Olustur")
    );
    const serviceDialogElement=$("#appDialog");
    serviceDialogElement.classList.add("service-accept-dialog");
    if(!serviceDialogElement.querySelector("#serviceVersionBadge")){
      const versionBadge=document.createElement("span");
      versionBadge.id="serviceVersionBadge";
      versionBadge.textContent="v2.0.4 Enterprise";
      $("#dialogTitle",serviceDialogElement).after(versionBadge);
    }
    if(!serviceDialogElement.querySelector("#serviceEscHint")){
      const escHint=document.createElement("span");
      escHint.id="serviceEscHint";
      escHint.textContent="ESC ile kapat";
      $("#dialogClose",serviceDialogElement).before(escHint);
    }
    $("#dialogEyebrow",serviceDialogElement).textContent=tr("M\u00fc\u015fteri kabul, cihaz donan\u0131m te\u015fhisi ve dijital servis kabul fi\u015fi olu\u015fturma sihirbaz\u0131");
    const serviceForm=$("#dialogForm",serviceDialogElement);
    const selectedFaultNotes=new Set();
    const intakeDamageButton=$("[data-automotive-damage-open]",serviceForm);
    intakeDamageButton?.addEventListener("click",()=>openAutomotiveDamageDialog(intakeDamageMarks,value=>{Object.assign(intakeDamageMarks,value);intakeDamageButton.textContent=`Hasar Tespiti (${automotiveDamageCount(intakeDamageMarks)})`;}));
    const intakeChecklistButton=$("[data-automotive-checklist-open]",serviceForm);
    intakeChecklistButton?.addEventListener("click",()=>openAutomotiveChecklistDialog(intakeChecklistData,value=>{Object.assign(intakeChecklistData,value);intakeChecklistButton.textContent=`Kontrol Formu (${intakeChecklistData.items.length})`;}));
    const installServiceCombo=input=>{
      if(!input||input.tagName!=="INPUT"||input.dataset.serviceComboBound)return;
      const dataList=document.getElementById(input.getAttribute("list"));if(!dataList)return;
      const shell=document.createElement("div");shell.className="service-combo-shell";
      input.parentNode.insertBefore(shell,input);shell.appendChild(input);input.dataset.serviceComboBound="true";
      const toggle=document.createElement("button");toggle.type="button";toggle.className="service-combo-toggle";toggle.setAttribute("aria-label",tr("Se\u00e7enekleri a\u00e7"));toggle.tabIndex=-1;toggle.textContent="\u2304";
      const menu=document.createElement("div");menu.className="service-combo-options";menu.setAttribute("role","listbox");menu.hidden=true;
      const refresh=()=>{menu.replaceChildren();Array.from(dataList.options).forEach(source=>{const option=document.createElement("button");option.type="button";option.setAttribute("role","option");option.dataset.value=source.value||source.textContent;option.textContent=source.value||source.textContent;option.addEventListener("click",()=>{input.value=option.dataset.value;input.dispatchEvent(new Event("input",{bubbles:true}));input.dispatchEvent(new Event("change",{bubbles:true}));close();input.focus();});menu.appendChild(option);});};
      input.refreshServiceCombo=refresh;refresh();
      shell.append(toggle,menu);input.setAttribute("role","combobox");input.setAttribute("aria-autocomplete","list");input.setAttribute("aria-haspopup","listbox");input.setAttribute("aria-expanded","false");
      const close=()=>{menu.hidden=true;input.setAttribute("aria-expanded","false");};
      const open=()=>{menu.hidden=false;input.setAttribute("aria-expanded","true");};
      toggle.addEventListener("click",()=>{if(menu.hidden){open();input.focus();}else close();});
      input.addEventListener("keydown",event=>{if(event.key==="ArrowDown"){event.preventDefault();open();}else if(event.key==="Escape")close();});
      document.addEventListener("pointerdown",event=>{if(!shell.contains(event.target))close();});
    };
    if(!automotive){
      const deviceTypeInput=$("[name=\"device_type\"]",serviceForm),otherDeviceField=$("[data-service-other-device]",serviceForm),otherDeviceInput=$("[name=\"other_device_type\"]",serviceForm);
      const syncOtherDevice=()=>{const isOther=deviceTypeInput.value==="Di\u011fer";otherDeviceField.hidden=!isOther;otherDeviceInput.required=isOther;if(!isOther)otherDeviceInput.value=""};
      deviceTypeInput.addEventListener("change",syncOtherDevice);syncOtherDevice();
      const brandInput=$("[name=\"brand\"]",serviceForm),modelInput=$("[name=\"model\"]",serviceForm),brandList=$("#serviceBrandOptions",serviceForm),modelList=$("#serviceModelOptions",serviceForm);
      const normalized=value=>String(value||"").toLocaleLowerCase("tr-TR").replace(/\s+/g," ").replace(/ (pc|bilgisayar)$/g,"").trim();
      const history=(db.customers||[]).flatMap(customer=>customer.services||[]),defaultBrands=Array.from(brandList.options).map(option=>option.value);let catalogBrandRows=[];
      const otherTypeOption=Array.from(deviceTypeInput.options).find(option=>option.value==="Di\u011fer");
      for(const type of [...new Set(history.map(row=>String(row.device_type||"").trim()).filter(Boolean))]){
        if(type==="Di\u011fer"||Array.from(deviceTypeInput.options).some(option=>normalized(option.value)===normalized(type)))continue;
        const option=document.createElement("option");option.value=type;option.textContent=type;deviceTypeInput.insertBefore(option,otherTypeOption||null);
      }
      const setOptions=(list,values)=>{list.replaceChildren(...[...new Set(values.filter(Boolean))].sort((a,b)=>a.localeCompare(b,"tr")).map(value=>{const option=document.createElement("option");option.value=value;return option}));};
      const refreshDeviceCatalog=()=>{
        const type=deviceTypeInput.value==="Di\u011fer"?otherDeviceInput.value:deviceTypeInput.value,deviceKey=normalized(type);
        const matching=history.filter(row=>normalized(row.device_type)===deviceKey);
        const catalogBrands=catalogBrandRows.filter(row=>normalized(row.device_type)===deviceKey).map(row=>row.brand),knownBrands=[...catalogBrands,...matching.map(row=>row.brand||row.device_brand)];
        setOptions(brandList,knownBrands.length?knownBrands:defaultBrands);
        const brandKey=normalized(brandInput.value),models=matching.filter(row=>normalized(row.brand||row.device_brand)===brandKey).map(row=>row.model||row.device_model);
        setOptions(modelList,models);
        brandInput.refreshServiceCombo?.();modelInput.refreshServiceCombo?.();
      };
      installServiceCombo(brandInput);installServiceCombo(modelInput);
      deviceTypeInput.addEventListener("change",refreshDeviceCatalog);otherDeviceInput.addEventListener("input",refreshDeviceCatalog);brandInput.addEventListener("input",refreshDeviceCatalog);brandInput.addEventListener("change",refreshDeviceCatalog);refreshDeviceCatalog();
      apiFetch("/api/desktop/table/device_brands?limit=500").then(result=>{catalogBrandRows=result.rows||[];refreshDeviceCatalog()}).catch(()=>{});
    }
    const loadServiceNotes=async()=>{
      try{
        const result=await apiFetch("/api/desktop/table/fast_notes?limit=500"),rows=(result.rows||[]).filter(row=>Number(row.is_active)!==0),faultRows=rows.filter(row=>row.category==="Ar\u0131za H\u0131zl\u0131 Se\u00e7imi"&&String(row.label||"").trim()),accessoryRows=rows.filter(row=>row.category==="Aksesuar"&&String(row.label||"").trim());
        if(faultRows.length){const host=$("[data-service-fault-notes]",serviceForm),options=$("[data-service-fault-note-options]",serviceForm),summary=$("[data-service-fault-selected]",serviceForm);host.hidden=false;options.replaceChildren(...faultRows.map(row=>{const button=document.createElement("button");button.type="button";button.className="secondary";button.dataset.serviceFaultNote=row.label;button.setAttribute("aria-pressed","false");button.textContent=row.label;button.onclick=()=>{if(selectedFaultNotes.has(row.label)){selectedFaultNotes.delete(row.label);button.setAttribute("aria-pressed","false")}else{selectedFaultNotes.add(row.label);button.setAttribute("aria-pressed","true")}summary.textContent=[...selectedFaultNotes].join("  \u2022  ")};return button}));}
        if(accessoryRows.length){const host=$("[data-service-accessory-options]",serviceForm);host.replaceChildren(...accessoryRows.map(row=>{const label=document.createElement("label"),input=document.createElement("input"),text=document.createElement("span");input.type="checkbox";input.name="accessory_option";input.value=row.label;text.textContent=row.label;label.append(input,text);return label}));}
      }catch(error){toast(tr("Hizli servis notlari yuklenemedi"),"warning")}
    };
    void loadServiceNotes();
    const customerInput=$("[name='customerId']",serviceForm);
    const customerSearchInput=$(".service-customer-search",serviceForm);
    const nameInput=$("[name='customer_name']",serviceForm);
    const phoneInput=$("[name='customer_phone_input']",serviceForm);
    const identityInput=$("[name='customer_identity']",serviceForm);
    const customerState=$(".service-form-state",serviceForm);
    const syncCustomerFields=()=>{
      const customer=db.customers.find(item=>String(item.id)===String(customerInput.value));
      if(customer){nameInput.value=customer.name||"";phoneInput.value=customer.phone||"";identityInput.value=customer.tc_no||customer.tax_no||customer.tax_id||"";customerState.textContent=tr("Kayitli Musteri");}
      else{customerState.textContent=tr("Yeni Musteri Kaydi");}
    };
    customerInput.addEventListener("change",()=>{syncCustomerFields();const selected=db.customers.find(item=>String(item.id)===String(customerInput.value));if(selected)customerSearchInput.value=selected.name||"";});
    customerSearchInput.addEventListener("input",()=>{
      const query=String(customerSearchInput.value||"").trim().toLocaleLowerCase("tr-TR");
      const selected=db.customers.find(item=>String(item.name||"").trim().toLocaleLowerCase("tr-TR")===query);
      customerInput.value=selected?String(selected.id):"";
      if(selected){customerInput.dispatchEvent(new Event("change",{bubbles:true}));return;}
      syncCustomerFields();nameInput.value=customerSearchInput.value;phoneInput.value="";identityInput.value="";
    });
    if(customerId)syncCustomerFields();
    const patternInput=$("[name='pattern_lock']",serviceForm);
    const currencySelect=$("[name='currency']",serviceForm);
    const currencyButtons=$("[data-service-currency]",serviceForm) ? $$("[data-service-currency]",serviceForm) : [];
    const syncCurrencyButtons=()=>currencyButtons.forEach(button=>button.classList.toggle("active",button.dataset.serviceCurrency===currencySelect.value));
    currencyButtons.forEach(button=>button.onclick=()=>{currencySelect.value=button.dataset.serviceCurrency;currencySelect.dispatchEvent(new Event("change",{bubbles:true}));syncCurrencyButtons();});
    currencySelect.addEventListener("change",syncCurrencyButtons);syncCurrencyButtons();
    const extraDetails=$(".service-extra-fields",serviceForm);
    const extraToggle=$(".service-device-extra-toggle",serviceForm);
    extraToggle.onclick=()=>{extraDetails.open=!extraDetails.open;extraToggle.setAttribute("aria-expanded",String(extraDetails.open));extraToggle.textContent=extraDetails.open?tr("Ek Servis Alanlarini Gizle"):tr("Ek Servis Alanlari");};
    const photoInput=$("[name='device_photo']",serviceForm);
    const selectedServicePhotos=[];
    const photoList=$("[data-service-photo-selected]",serviceForm);
    const photoPreviewUrls=[];
    const renderServicePhotos=()=>{
      photoPreviewUrls.splice(0).forEach(url=>URL.revokeObjectURL(url));
      photoList.replaceChildren();
      selectedServicePhotos.forEach((file,index)=>{
        const item=document.createElement("div");item.className="service-photo-selected-item";
        const image=document.createElement("img");image.alt=file.name;image.src=URL.createObjectURL(file);photoPreviewUrls.push(image.src);
        const label=document.createElement("span");label.textContent=file.name;
        const remove=document.createElement("button");remove.type="button";remove.textContent="\u00d7";remove.setAttribute("aria-label",`${tr("Fotografi Kaldir")}: ${file.name}`);remove.onclick=()=>{selectedServicePhotos.splice(index,1);renderServicePhotos();};
        item.append(image,label,remove);photoList.append(item);
      });
    };
    photoInput.addEventListener("change",()=>{
      const allowed=Array.from(photoInput.files||[]).filter(file=>/\.(jpe?g|png)$/i.test(file.name)||["image/jpeg","image/png"].includes(file.type));
      let overflow=false;
      for(const file of allowed){if(selectedServicePhotos.some(item=>item.name===file.name&&item.size===file.size&&item.lastModified===file.lastModified))continue;if(selectedServicePhotos.length>=5){overflow=true;continue;}selectedServicePhotos.push(file);}
      if(overflow)toast(tr("En fazla 5 fotograf eklenebilir"),"warning");
      photoInput.value="";renderServicePhotos();
    });
    const photoDrop=$(".service-photo-drop",serviceForm);
    photoDrop.addEventListener("dragover",event=>{event.preventDefault();photoDrop.classList.add("dragging");});
    photoDrop.addEventListener("dragleave",()=>photoDrop.classList.remove("dragging"));
    photoDrop.addEventListener("drop",event=>{event.preventDefault();photoDrop.classList.remove("dragging");if(event.dataTransfer?.files){photoInput.files=event.dataTransfer.files;photoInput.dispatchEvent(new Event("change",{bubbles:true}));}});
    $$(".service-photo-preview button",serviceForm).forEach(button=>button.onclick=()=>photoInput.click());
    const pattern=[];
    serviceForm.addEventListener("service-form-reset",()=>{pattern.length=0;patternInput.value="";$$((".service-pattern-dot"),serviceForm).forEach(dot=>dot.classList.remove("selected"));});
    $$(".service-pattern-dot",serviceForm).forEach(dot=>dot.addEventListener("click",()=>{
      const point=dot.dataset.patternIndex;
      if(!pattern.includes(point))pattern.push(point);
      dot.classList.add("selected");
      patternInput.value=pattern.join("-");
    }));
    $(".service-pattern-reset",serviceForm).onclick=()=>{pattern.length=0;patternInput.value="";$$((".service-pattern-dot"),serviceForm).forEach(dot=>dot.classList.remove("selected"));};
    $$("[data-fault-shortcut]",serviceForm).forEach(button=>button.addEventListener("click",()=>{
      const faultInput=$("[name='fault']",serviceForm);
      const shortcut=button.dataset.faultShortcut;
      faultInput.value=faultInput.value?`${faultInput.value}, ${shortcut}`:shortcut;
      faultInput.dispatchEvent(new Event("input",{bubbles:true}));
      faultInput.focus();
    }));
    $(".service-speech-button",serviceForm).onclick=()=>{
      const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
      if(!SpeechRecognition){toast(tr("Tarayici sesle yazmayi desteklemiyor"),"warning");return;}
      const recognition=new SpeechRecognition();recognition.lang="tr-TR";recognition.interimResults=false;
      recognition.onresult=event=>{const transcript=event.results?.[0]?.[0]?.transcript||"";const faultInput=$("[name='fault']",serviceForm);faultInput.value=[faultInput.value,transcript].filter(Boolean).join(" ");};
      recognition.onerror=()=>toast(tr("Ses kaydi baslatilamadi"),"error");
      try{recognition.start();toast(tr("Dinleniyor"),"info");}catch(error){toast(tr("Ses kaydi baslatilamadi"),"error");}
    };
  };

  financeDialog=function(type,item){
    const operationType=item?.type||type;
    const startCurrency=String(item?.currency||"TRY").toUpperCase();
    const startRate=startCurrency==="TRY"?1:Number(item?.exchange_rate||rateForCode(startCurrency)||0);
    const detail=item?`<details class="finance-detail" open><summary>\u0130\u015flem ayr\u0131nt\u0131lar\u0131</summary><div class="finance-detail-grid"><span>T\u00fcr / Kategori<strong>${esc(operationType||"-")} / ${esc(item.category||"-")}</strong></span><span>Orijinal tutar<strong>${money(item.original_amount??item.amount,item.currency||"TRY")}</strong></span><span>TRY kar\u015f\u0131l\u0131\u011f\u0131<strong>${money(item.try_equivalent??financeTryValue(item),"TRY")}</strong></span><span>Kur<strong>${esc(String(item.exchange_rate??1))}</strong></span><span>\u00d6deme y\u00f6ntemi<strong>${esc(item.payment_method||"-")}</strong></span><span>Referans / Takip<strong>${esc(item.ref_no||item.tracking_no||"-")}</strong></span><span>M\u00fc\u015fteri<strong>${esc(item.customer||item.customer_name||"-")}</strong></span><span>Kay\u0131t zaman\u0131<strong>${esc(item.created_at||item.date||"-")}</strong></span></div></details>`:"";
    openDialog(
      item?"Finans Kayd\u0131n\u0131 D\u00fczenle":`${operationType} Ekle`,
      "F\u0130NANS",
      `${detail}<div class="form-grid"><div class="field"><label>Tarih</label><input name="date" type="date" value="${item?.date||today()}"></div><div class="field"><label>Kategori *</label><input name="category" required value="${esc(item?.category||"")}"></div><div class="field"><label>Tutar *</label><input name="amount" type="number" min=".01" step=".01" required value="${item?.original_amount??item?.amount??""}"></div><div class="field"><label>Para Birimi</label><select name="currency">${["TRY","USD","EUR"].map(currency=>`<option ${startCurrency===currency?"selected":""}>${currency}</option>`).join("")}</select></div><div class="field"><label>D\u00f6viz Kuru (TRY)</label><input name="exchange_rate" type="number" min=".0001" step=".0001" value="${startRate||""}" ${startCurrency==="TRY"?"disabled":""}></div><div class="field"><label>\u00d6deme Y\u00f6ntemi</label><select name="payment_method">${["Nakit","Banka","Kredi Kart\u0131","Web","Mahsup"].map(method=>`<option ${item?.payment_method===method?"selected":""}>${method}</option>`).join("")}</select></div><div class="field"><label>Referans / Takip No</label><input name="tracking_no" value="${esc(item?.tracking_no||item?.ref_no||"")}"></div><div class="field full"><label>A\u00e7\u0131klama *</label><textarea name="description" required>${esc(item?.description||"")}</textarea></div><div class="field full"><label>M\u00fc\u015fteri (iste\u011fe ba\u011fl\u0131)</label><select name="customer"><option></option>${db.customers.map(customer=>`<option ${item?.customer===customer.name||item?.customer_name===customer.name?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div></div>`,
      async formData=>{
        const values=Object.fromEntries(formData);
        const amount=Number(values.amount||0);
        const customer=db.customers.find(entry=>entry.name===values.customer);
        const rate=values.currency==="TRY"?1:Number(values.exchange_rate||0);
        if(amount<=0)throw Error("Tutar s\u0131f\u0131rdan b\u00fcy\u00fck olmal\u0131d\u0131r");
        if(values.currency!=="TRY"&&rate<=0)throw Error("D\u00f6viz kuru al\u0131namad\u0131");
        const payload={
          type:operationType,
          category:values.category,
          amount,
          original_amount:amount,
          try_equivalent:amount*rate,
          currency:values.currency,
          exchange_rate:rate,
          description:values.description,
          date:values.date,
          customer_id:customer&&Number.isInteger(+customer.id)?+customer.id:null,
          customer_name:values.customer,
          payment_method:values.payment_method,
          tracking_no:values.tracking_no,
          ref_no:values.tracking_no
        };
        if(item&&Number.isInteger(+item.id))Object.assign(payload,{id:+item.id,_action:"update"});
        await apiFetch("/api/desktop/table/accounting",{
          method:"POST",
          body:JSON.stringify(payload)
        });
        await hydrateDesktop(true);
        activity(`${operationType} kayd\u0131: ${money(amount,values.currency)}`,operationType==="Gelir"?"+":"-");
        toast(`${operationType} kaydedildi`,"success");
        return true;
      },
      item?"G\u00fcncelle":"Kaydet"
    );
    const body=$("#dialogBody");
    const currencyInput=$("select[name=\"currency\"]",body);
    const rateInput=$("input[name=\"exchange_rate\"]",body);
    const syncRate=()=>{
      const currency=String(currencyInput?.value||"TRY").toUpperCase();
      const rate=currency==="TRY"?1:rateForCode(currency);
      if(rateInput){rateInput.disabled=currency==="TRY";rateInput.value=rate>0?String(rate):""}
    };
    currencyInput?.addEventListener("change",syncRate);
  };

  contextAction=function(kind,id,action,row){
    if(kind!=="appointment"||!["approve","complete","cancel"].includes(action)){
      return baseContextAction(kind,id,action,row);
    }
    const appointment=db.appointments.find(item=>String(item.id)===String(id));
    const persistedId=Number(appointment?.id);
    if(!appointment||!Number.isInteger(persistedId)){
      toast("Randevu kayd\u0131 bulunamad\u0131","error");
      return;
    }
    const status={approve:"Onayland\u0131",complete:"Tamamland\u0131",cancel:"\u0130ptal"}[action];
    void (async()=>{
      await apiFetch("/api/desktop/table/appointments",{
        method:"POST",
        body:JSON.stringify({id:persistedId,_action:"update",status})
      });
      await hydrateDesktop(true);
      toast(`Randevu durumu: ${status}`,"success");
    })().catch(error=>toast(`Randevu g\u00fcncellenemedi: ${error.message}`,"error"));
  };

  function vehicleEditor(customer,vehicle={},options={}){
    openDialog(vehicle.id?tr("Araci Duzenle"):tr("Yeni Arac"),tr("OTOMOTIV ARAC KARTI"),`<div class="form-grid"><div class="field"><label>Plaka *</label><input name="plate" required value="${esc(vehicle.plate||"")}"></div><div class="field"><label>Marka *</label><input name="brand" required value="${esc(vehicle.brand||"")}"></div><div class="field"><label>Model *</label><input name="model" required value="${esc(vehicle.model||"")}"></div><div class="field"><label>${tr("Model Yili")}</label><input name="year" type="number" min="1900" max="2200" value="${esc(vehicle.year||"")}"></div><div class="field"><label>${tr("Arac Tipi")}</label><input name="vehicle_type" value="${esc(vehicle.vehicle_type||"")}"></div><div class="field"><label>${tr("Motor Tipi")}</label><input name="engine_type" value="${esc(vehicle.engine_type||"")}"></div><div class="field"><label>${tr("Yakit Turu")}</label><select name="fuel_type">${["Benzin","Dizel","LPG","Hibrit","Elektrik"].map(value=>`<option ${vehicle.fuel_type===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>${tr("Son Bilinen KM")}</label><input name="last_known_odometer" type="number" min="0" value="${esc(vehicle.last_known_odometer||0)}"></div><div class="field"><label>${tr("Muayene Tarihi")}</label><input name="inspection_due_date" type="date" value="${esc(String(vehicle.inspection_due_date||"").slice(0,10))}"></div><div class="field full"><label>Notlar</label><textarea name="notes">${esc(vehicle.notes||"")}</textarea></div></div>`,async data=>{
      const values=Object.fromEntries(data),payload={...values,customer_id:+customer.id,year:+values.year||null,last_known_odometer:+values.last_known_odometer||0,is_active:1};
      if(vehicle.id)Object.assign(payload,{id:+vehicle.id,_action:"update"});
      const result=await apiFetch("/api/desktop/table/customer_vehicles",{method:"POST",body:JSON.stringify(payload)});
      toast(tr("Arac karti kaydedildi"),"success");
      if(options.onSaved)options.onSaved(result,payload);
      if(options.refreshCustomer!==false)setTimeout(()=>customer360(customer),120);
      return true;
    },tr("Araci Kaydet"));
  }

  window.openAutomotiveVehicleShortcut=function(){
    const customers=(db.customers||[]).filter(customer=>customer&&customer.id!=null);
    if(!customers.length){toast(tr("Once bir musteri kaydi olusturun"),"warning");return;}
    openDialog(tr("Musteri Sec"),tr("YENI ARAC"),`<div class="field"><label>${tr("Musteri")}</label><select name="customerId" required><option value="">${tr("Secin")}</option>${customers.map(customer=>`<option value="${esc(customer.id)}">${esc(customer.name||"")}</option>`).join("")}</select></div>`,data=>{
      const customer=customers.find(item=>String(item.id)===String(data.get("customerId")));
      if(!customer)throw Error(tr("Musteri secin"));
      setTimeout(()=>vehicleEditor(customer),80);
      return true;
    },tr("Devam"));
  };

  const baseVehicleMaintenanceDialog=maintenanceDialog;
  maintenanceDialog=async function(sourceRow={}){
    await baseVehicleMaintenanceDialog(sourceRow);
    const maintenanceField=name=>document.querySelector(`#dialogBody [name="${name}"]`);
    const brandInput=maintenanceField("vehicle_brand"),modelInput=maintenanceField("vehicle_model");
    if(brandInput&&modelInput){
      const addDatalist=(input,id)=>{let list=document.getElementById(id);if(!list){list=document.createElement("datalist");list.id=id;document.querySelector("#dialogBody").append(list)}input.setAttribute("list",id);return list};
      const brandList=addDatalist(brandInput,"maintenanceBrandOptions"),modelList=addDatalist(modelInput,"maintenanceModelOptions");
      brandList.innerHTML=Object.keys(maintenanceVehicleCatalog).sort().map(value=>`<option value="${esc(value)}"></option>`).join("");
      const updateModels=()=>{const brand=Object.keys(maintenanceVehicleCatalog).find(value=>value.toLocaleLowerCase("en")===brandInput.value.trim().toLocaleLowerCase("en"));modelList.innerHTML=(maintenanceVehicleCatalog[brand]||[]).slice().sort().map(value=>`<option value="${esc(value)}"></option>`).join("")};
      brandInput.addEventListener("input",updateModels);brandInput.addEventListener("change",updateModels);updateModels();
    }
    const replaceWithChoices=(input,values,placeholder="")=>{
      if(!input)return null;
      const current=input.value,select=document.createElement("select");select.name=input.name;select.className=input.className;select.id=input.id;
      if(placeholder)select.add(new Option(placeholder,""));
      values.forEach(value=>select.add(new Option(value,value)));
      if(current&&!Array.from(select.options).some(option=>option.value===current))select.add(new Option(current,current));
      select.value=current||values[0]||"";input.replaceWith(select);return select;
    };
    replaceWithChoices(maintenanceField("vehicle_year"),Array.from({length:new Date().getFullYear()-1988},(_,index)=>String(new Date().getFullYear()+1-index)),"Yil secin");
    replaceWithChoices(maintenanceField("vehicle_type"),maintenanceVehicleTypes);
    replaceWithChoices(maintenanceField("engine_type"),maintenanceEngineTypes);
    replaceWithChoices(maintenanceField("fuel_type"),maintenanceFuelTypes);
    const customerSelect=document.querySelector('#dialogBody [name="customer_id"]');
    if(!customerSelect||customerSelect.dataset.vehicleLookupBound)return;
    customerSelect.dataset.vehicleLookupBound="true";
    const initialCustomer=(db.customers||[]).find(item=>String(item.id)===String(customerSelect.value)||String(item.desktopId)===String(customerSelect.value));
    for(const option of customerSelect.options){const customer=(db.customers||[]).find(item=>String(item.id)===String(option.value));if(customer)option.value=String(customer.desktopId||customer.id)}
    if(initialCustomer)customerSelect.value=String(initialCustomer.desktopId||initialCustomer.id);
    const customerField=customerSelect.closest(".field");
    customerField.insertAdjacentHTML("afterend",`<div class="field full maintenance-vehicle-select-field"><label>${tr("Kayitli Arac")}</label><select name="vehicle_id"><option value="">${tr("Musteriye ait arac secin")}</option></select></div>`);
    customerField.insertAdjacentHTML("beforeend",`<button type="button" class="secondary maintenance-add-customer" data-maintenance-add-customer>${tr("Yeni Musteri Ekle")}</button>`);
    const vehicleSelect=document.querySelector('#dialogBody [name="vehicle_id"]');
    vehicleSelect.insertAdjacentHTML("afterend",`<button type="button" class="secondary maintenance-add-vehicle" data-maintenance-add-vehicle>${tr("Yeni Arac Ekle")}</button>`);
    const vehicleRows=[];
    const field=name=>document.querySelector(`#dialogBody [name="${name}"]`);
    const readDraftItems=()=>{try{return JSON.parse(field("maintenance_items_json")?.value||"[]")}catch{return[]}};
    const applyVehicle=vehicle=>{
      const values={vehicle_plate:vehicle.plate,vehicle_brand:vehicle.brand,vehicle_model:vehicle.model,vehicle_year:vehicle.year,vehicle_type:vehicle.vehicle_type,engine_type:vehicle.engine_type,fuel_type:vehicle.fuel_type,odometer:vehicle.last_known_odometer,inspection_due_date:vehicle.inspection_due_date};
      Object.entries(values).forEach(([name,value])=>{const input=field(name);if(!input||value==null||value==="")return;if(input.tagName==="SELECT"&&!Array.from(input.options).some(option=>option.value===String(value)))input.add(new Option(String(value),String(value)));input.value=String(value)});
    };
    const loadCustomerVehicles=async(customerId,preferredId="")=>{
      vehicleRows.splice(0,vehicleRows.length);
      vehicleSelect.innerHTML=`<option value="">${tr("Musteriye ait arac secin")}</option>`;
      if(!customerId)return;
      const result=await apiFetch("/api/desktop/table/customer_vehicles?limit=500");
      const rows=(result.rows||[]).filter(vehicle=>String(vehicle.customer_id)===String(customerId));
      vehicleRows.push(...rows);
      vehicleSelect.innerHTML=`<option value="">${tr("Musteriye ait arac secin")}</option>`+rows.map(vehicle=>`<option value="${esc(vehicle.id)}">${esc(vehicle.plate||"")} | ${esc(`${vehicle.brand||""} ${vehicle.model||""}`.trim())}</option>`).join("");
      if(preferredId&&rows.some(vehicle=>String(vehicle.id)===String(preferredId))){vehicleSelect.value=String(preferredId);applyVehicle(rows.find(vehicle=>String(vehicle.id)===String(preferredId)))}
    };
    document.querySelector("[data-maintenance-add-customer]").addEventListener("click",()=>{
      const form=document.querySelector("#dialogForm"),draft=Object.fromEntries(new FormData(form));
      draft._draftItems=readDraftItems();
      const dialog=document.querySelector("#appDialog");dialog.close("cancel");let savedCustomer=null;
      const reopen=()=>{void maintenanceDialog({...draft,...(savedCustomer?{customer_id:savedCustomer.id}: {})})};
      setTimeout(()=>{
        openDialog(tr("Yeni Musteri"),"CRM",customerForm(),async data=>{await saveCustomer(data);savedCustomer=(db.customers||[]).at(-1);return true},tr("Musteri Ekle"));
        document.querySelector("#appDialog").addEventListener("close",reopen,{once:true});
      },80);
    });
    customerSelect.addEventListener("change",()=>{void loadCustomerVehicles(customerSelect.value).catch(error=>toast(error.message||"Araclar yuklenemedi","error"))});
    document.querySelector("[data-maintenance-add-vehicle]").addEventListener("click",()=>{
      if(!customerSelect.value){toast(tr("Once musteri secin"),"warning");return}
      const customer=(db.customers||[]).find(item=>String(item.desktopId||item.id)===String(customerSelect.value));
      if(!customer){toast(tr("Musteri bulunamadi"),"error");return}
      const form=document.querySelector("#dialogForm"),draft=Object.fromEntries(new FormData(form));
      draft._draftItems=readDraftItems();
      const dialog=document.querySelector("#appDialog");dialog.close("cancel");let saved=null;
      const reopen=()=>{void maintenanceDialog({...draft,...(saved?{vehicle_id:saved.id,vehicle_plate:saved.plate,vehicle_brand:saved.brand,vehicle_model:saved.model,vehicle_year:saved.year,vehicle_type:saved.vehicle_type,engine_type:saved.engine_type,fuel_type:saved.fuel_type,odometer:saved.last_known_odometer,inspection_due_date:saved.inspection_due_date}:{})})};
      setTimeout(()=>{vehicleEditor(customer,{}, {refreshCustomer:false,onSaved:(result,payload)=>{saved={...payload,...result,id:result.id||payload.id}}});document.querySelector("#appDialog").addEventListener("close",reopen,{once:true})},80);
    });
    vehicleSelect.addEventListener("change",()=>{const vehicle=vehicleRows.find(item=>String(item.id)===String(vehicleSelect.value));if(vehicle)applyVehicle(vehicle)});
    const plateInput=field("vehicle_plate");
    plateInput?.addEventListener("blur",async()=>{
      const plate=String(plateInput.value||"").trim().toLocaleUpperCase("tr-TR");
      if(!plate)return;
      plateInput.value=plate;
      try{
        const result=await apiFetch("/api/desktop/table/customer_vehicles?limit=500");
        const vehicle=(result.rows||[]).find(item=>String(item.plate||"").trim().toLocaleUpperCase("tr-TR")===plate);
        if(!vehicle)return;
        customerSelect.value=String(vehicle.customer_id);
        await loadCustomerVehicles(vehicle.customer_id,vehicle.id);
      }catch(error){toast(error.message||"Plaka sorgulanamadi","error")}
    });
    if(customerSelect.value)await loadCustomerVehicles(customerSelect.value,sourceRow.vehicle_id||"").catch(error=>toast(error.message||"Araclar yuklenemedi","error"));
  };

  async function loadCustomerVehicles(customer){
    const host=$("#c360Vehicles");
    if(!host)return;
    try{
      const response=await apiFetch("/api/desktop/table/customer_vehicles?limit=500");
      const rows=(response.rows||[]).filter(vehicle=>String(vehicle.customer_id)===String(customer.id));
      host.innerHTML=`<div class="vehicle-list-head"><div><strong>${tr("Kayitli Araclar")}</strong><p class="muted">${rows.length} ${tr("arac")}</p></div><button type="button" class="primary" id="c360VehicleAdd">+ ${tr("Yeni Arac")}</button></div>${rows.length?`<div class="table-wrap"><table><thead><tr><th>Plaka</th><th>${tr("Arac")}</th><th>${tr("Yil")}</th><th>${tr("Yakit")}</th><th>KM</th><th>${tr("Muayene")}</th><th></th></tr></thead><tbody>${rows.map((vehicle,index)=>`<tr tabindex="0" data-vehicle-index="${index}"><td><strong>${esc(vehicle.plate||"-")}</strong></td><td>${esc(`${vehicle.brand||""} ${vehicle.model||""}`.trim()||"-")}</td><td>${esc(vehicle.year||"-")}</td><td>${esc(vehicle.fuel_type||"-")}</td><td>${esc(vehicle.last_known_odometer||0)}</td><td>${esc(String(vehicle.inspection_due_date||"-").slice(0,10))}</td><td><button type="button" class="mini" data-vehicle-edit="${index}">${tr("Duzenle")}</button></td></tr>`).join("")}</tbody></table></div>`:empty(tr("Arac kaydi yok"),tr("Bu musteri icin ilk arac kartini olusturun."))}`;
      $("#c360VehicleAdd").onclick=()=>{$("#appDialog").close();setTimeout(()=>vehicleEditor(customer),80)};
      $$('[data-vehicle-edit]').forEach(button=>button.onclick=()=>{$("#appDialog").close();setTimeout(()=>vehicleEditor(customer,rows[+button.dataset.vehicleEdit]),80)});
      $$('[data-vehicle-index]').forEach(row=>row.ondblclick=()=>{$("#appDialog").close();setTimeout(()=>vehicleEditor(customer,rows[+row.dataset.vehicleIndex]),80)});
    }catch(error){host.innerHTML=empty(tr("Araclar alinamadi"),error.message)}
  }

  customer360=function(customer){
    baseCustomer360(customer);
    if(!automotiveMode())return;
    const tabs=$(".c360-tabs"),body=$("#dialogBody");
    if(!tabs||!body||tabs.querySelector('[data-c360-tab="vehicles"]'))return;
    const tab=document.createElement("button");
    tab.className="tab";tab.type="button";tab.dataset.c360Tab="vehicles";tab.textContent=tr("Araclar");tabs.appendChild(tab);
    const panel=document.createElement("div");
    panel.className="c360-panel";panel.dataset.c360Panel="vehicles";panel.id="c360Vehicles";panel.textContent=tr("Arac kayitlari yukleniyor...");body.appendChild(panel);
    tab.onclick=()=>{
      $$('[data-c360-tab]').forEach(item=>item.classList.toggle("active",item===tab));
      $$('[data-c360-panel]').forEach(item=>item.classList.toggle("active",item===panel));
      void loadCustomerVehicles(customer);
    };
  };

  function parseJson(value,fallback){
    try{return JSON.parse(value||"")||fallback}catch{return fallback}
  }

  serviceDetailDialog=function(customer,service){
    const result=baseServiceDetailDialog(customer,service);
    if(automotiveMode()||!service)return result;
    const totals=new Map();
    (service.used_parts||[]).forEach(item=>{
      const currency=String(item.currency||"TRY").toUpperCase();
      const total=moneyNumber(item.price)*Number(item.quantity||1);
      totals.set(currency,(totals.get(currency)||0)+total);
    });
    const summaries=$$(".service-summary",$("#servicePrintArea"));
    const totalField=summaries[1]?.children?.[2]?.querySelector("strong");
    if(totalField){
      totalField.textContent=totals.size
        ?[...totals].map(([currency,total])=>money(total,currency)).join(" / ")
        :money(0,"TRY");
    }
    return result;
  };

  technicianDialog=async function(customer,service){
    if(!automotiveMode()){
      const result=baseTechnicianDialog(customer,service);
      const paymentStatus=$("select[name=\"payment_status\"]",$("#dialogBody"));
      if(paymentStatus){
        paymentStatus.disabled=true;
        paymentStatus.title="Payment status is calculated from service debt and collections.";
      }
      return result;
    }
    if(!customer||!service)return toast(tr("Servis kaydi bulunamadi"),"error");
    let stored={};
    try{
      const response=await apiFetch(`/api/desktop/table/automotive_service_forms?limit=500&q=${encodeURIComponent(service.no||"")}`);
      stored=(response.rows||[]).find(row=>String(row.device_id)===String(service.id)||row.tracking_no===service.no)||{};
    }catch(error){toast(error.message,"warning")}
    const damageMarks=normalizeAutomotiveDamage(stored.damage_marks_json);
    let checklistData=normalizeAutomotiveChecklist(stored.checklist_json);
    const statuses=[tr("Bekliyor"),tr("Onay Bekliyor"),tr("Islemde"),tr("Tamirde"),tr("Parca Bekliyor"),tr("Test Surecinde"),tr("Tamir Edildi"),tr("Teslim Edildi")];
    service.plate=service.vehicle_plate||service.plate||service.serial||"";
    stored.vehicle_vin=stored.vehicle_vin||service.vehicle_vin||"";
    stored.vehicle_id=stored.vehicle_id||service.vehicle_id||null;
    openDialog(`${service.no} - ${service.device}`,tr("OTOMOTIV TEKNISYEN FORMU"),`<div class="form-grid"><div class="field"><label>${tr("Musteri")}</label><input disabled value="${esc(customer.name)}"></div><div class="field"><label>Durum</label><select name="status">${statuses.map(value=>`<option ${service.status===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Teknisyen</label><select name="technician"><option value="">${tr("Atanmadi")}</option>${desktopPersonnel.map(person=>`<option ${service.technician===person.name?"selected":""}>${esc(person.name)}</option>`).join("")}</select></div><div class="field"><label>${tr("Oncelik")}</label><select name="priority">${[tr("Dusuk"),"Normal",tr("Yuksek"),"Acil"].map(value=>`<option ${service.priority===value?"selected":""}>${value}</option>`).join("")}</select></div><section class="automotive-fields"><h3>${tr("Arac Kabul ve Kontrol")}</h3><div class="field"><label>Plaka</label><input name="vehicle_plate" value="${esc(stored.vehicle_plate||service.plate||service.serial||"")}"></div><div class="field"><label>VIN</label><input name="vehicle_vin" value="${esc(stored.vehicle_vin||"")}"></div><div class="field"><label>${tr("Motor Kodu")}</label><input name="engine_code" value="${esc(stored.engine_code||"")}"></div><div class="field"><label>${tr("Giris KM")}</label><input name="entry_odometer" type="number" min="0" value="${esc(stored.entry_odometer||service.odometer||0)}"></div><div class="field"><label>${tr("Cikis KM")}</label><input name="exit_odometer" type="number" min="0" value="${esc(stored.exit_odometer||0)}"></div><div class="field"><label>${tr("Giris Yakit")}</label><select name="fuel_level_entry">${["Bos","1/4","1/2","3/4","Dolu"].map(value=>`<option ${stored.fuel_level_entry===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>${tr("Cikis Yakit")}</label><select name="fuel_level_exit">${["Bos","1/4","1/2","3/4","Dolu"].map(value=>`<option ${stored.fuel_level_exit===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field full"><label>${tr("Kabul Notlari / Hasar Tespiti")}</label><textarea name="acceptance_notes">${esc(stored.acceptance_notes||"")}</textarea><button type="button" class="secondary" data-technician-damage-open>Hasar Tespiti (${automotiveDamageCount(damageMarks)})</button></div><div class="field full"><label>${tr("Arac Kontrol Listesi")}</label><button type="button" class="secondary" data-technician-checklist-open>Kontrol Formu (${checklistData.items.length})</button></div><div class="field full"><button type="button" class="secondary" data-technician-vehicle-history>QR / Ara\u00e7 Ge\u00e7mi\u015fi</button><div class="automotive-history-inline" id="technicianVehicleHistory" hidden></div></div><label class="setting"><span>${tr("Musteri onayi alindi")}</span><input class="switch" type="checkbox" name="customer_approval" ${stored.customer_approval?"checked":""}></label><label class="setting"><span>${tr("KVKK onayi alindi")}</span><input class="switch" type="checkbox" name="kvkk_approval" ${stored.kvkk_approval?"checked":""}></label></section><div class="field full"><label>${tr("Teknik Ic Not")}</label><textarea name="internal_notes">${esc(service.internal_notes||"")}</textarea></div><div class="field full"><label>${tr("Yapilan Islem / Musteri Notu")}</label><textarea name="repair_details">${esc(service.repair_details||"")}</textarea></div><div class="field"><label>${tr("Iscilik Tutari")}</label><input name="labor_cost" type="number" min="0" step=".01" value="${service.labor_cost||0}"></div><div class="field"><label>${tr("Kargo Tutari")}</label><input name="cargo_fee" type="number" min="0" step=".01" value="${service.cargo_fee||0}"></div><div class="field"><label>${tr("Kullanilan Stok")}</label><select name="part_id"><option value="">${tr("Parca kullanilmadi")}</option>${db.stock.filter(part=>part.qty>0).map(part=>`<option value="${part.id}">${esc(part.name)} (${part.qty} - ${money(part.sell,part.currency)})</option>`).join("")}</select></div><div class="field"><label>${tr("Parca Adedi")}</label><input name="part_quantity" type="number" min="0" step="1" value="0"></div><label class="setting field"><span>${tr("Simdi tahsilat al")}</span><input class="switch" id="collectPayment" name="collect_payment" type="checkbox"></label><div class="field payment-field" hidden><label>${tr("Tahsilat Tutari")}</label><input name="payment_amount" type="number" min="0" step=".01" value="0"></div><div class="field payment-field" hidden><label>${tr("Para Birimi")}</label><select name="payment_currency"><option>TRY</option><option>USD</option><option>EUR</option></select></div><div class="field payment-field" hidden><label>${tr("Odeme Yontemi")}</label><select name="payment_method"><option>Nakit</option><option>Banka</option><option>${tr("Kredi Karti")}</option></select></div></div>`,async formData=>{
      const values=Object.fromEntries(formData),currency=values.payment_currency||"TRY",checklist=checklistData.items;
      const payload={device_id:+service.id,tracking_no:service.no,status:values.status,technician:values.technician,priority:values.priority,internal_notes:values.internal_notes,repair_details:values.repair_details,labor_cost:+values.labor_cost||0,cargo_fee:+values.cargo_fee||0,part_id:+values.part_id||0,part_quantity:+values.part_quantity||0,collect_payment:Boolean(values.collect_payment),payment_amount:+values.payment_amount||0,payment_currency:currency,payment_method:values.payment_method,exchange_rate:rateForCode(currency),automotive_form:{vehicle_id:+stored.vehicle_id||null,vehicle_plate:values.vehicle_plate,vehicle_vin:values.vehicle_vin,engine_code:values.engine_code,entry_odometer:+values.entry_odometer||0,exit_odometer:+values.exit_odometer||0,fuel_level_entry:values.fuel_level_entry,fuel_level_exit:values.fuel_level_exit,acceptance_notes:values.acceptance_notes,checklist,damage_marks:damageMarks,customer_approval:Boolean(values.customer_approval),kvkk_approval:Boolean(values.kvkk_approval)}};
      const result=await apiFetch("/api/desktop/technician/update",{method:"POST",body:JSON.stringify(payload)});
      await hydrateDesktop(true);activity(`${service.no} ${tr("otomotiv teknisyen kaydi guncellendi")}`,"#");toast(result.finance_id?tr("Servis, stok, arac kontrolu ve tahsilat islendi"):tr("Servis, stok ve arac kontrolu kaydedildi"),"success");return true;
    },tr("Islemi Kaydet"));
    const checklistOpenButton=$("[data-technician-checklist-open]",$("#dialogBody"));
    checklistOpenButton?.addEventListener("click",()=>openAutomotiveChecklistDialog(checklistData,value=>{checklistData=value;checklistOpenButton.textContent=`Kontrol Formu (${checklistData.items.length})`;}));
    const historyButton=$("[data-technician-vehicle-history]",$("#dialogBody")),historyHost=$("#technicianVehicleHistory",$("#dialogBody"));
    let historyLoaded=false;
    historyButton?.addEventListener("click",async()=>{
      if(!historyHost)return;
      if(!historyHost.hidden){historyHost.hidden=true;return;}
      historyHost.hidden=false;
      if(historyLoaded)return;
      const plate=String($('[name="vehicle_plate"]',$("#dialogBody"))?.value||service.plate||"").trim();
      if(!plate){historyHost.innerHTML=`<p class="muted">Bu servis kaydina bagli plaka bulunamadi.</p>`;return;}
      historyHost.innerHTML=`<p class="muted">Arac gecmisi yukleniyor...</p>`;
      try{
        const result=await apiFetch(`/api/desktop/vehicle-maintenance/cards?q=${encodeURIComponent(plate)}`);
        const key=plate.replace(/\s+/g,"").toLocaleUpperCase("tr-TR");
        const card=(result.rows||[]).find(row=>String(row.vehicle_plate||"").replace(/\s+/g,"").toLocaleUpperCase("tr-TR")===key);
        if(!card)throw new Error("Arac bakim karti bulunamadi.");
        await maintenanceHistoryDialog(card,historyHost);historyLoaded=true;
      }catch(error){historyHost.innerHTML=`<p class="error">${esc(error.message||"Arac gecmisi alinamadi.")}</p>`;}
    });
    const damageOpenButton=$("[data-technician-damage-open]",$("#dialogBody"));
    damageOpenButton?.addEventListener("click",()=>openAutomotiveDamageDialog(damageMarks,value=>{Object.assign(damageMarks,value);damageOpenButton.textContent=`Hasar Tespiti (${automotiveDamageCount(damageMarks)})`;}));
    const collect=$("#collectPayment");
    if(collect)collect.onchange=()=>$$('.payment-field').forEach(field=>field.hidden=!collect.checked);
    if(window.ayecBindUsedPartsEditor)window.ayecBindUsedPartsEditor(service);
  };
  const ayecParityStockTable=stockTable;
  stockTable=function(rows){
    return ayecParityStockTable(rows);
  };
})();
