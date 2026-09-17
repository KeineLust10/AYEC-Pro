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

  function tr(value){
    const replacements=[
      ["Yeni Arac Servis Kaydi","Yeni Ara\u00e7 Servis Kayd\u0131"],
      ["Model Yili","Model Y\u0131l\u0131"],
      ["Sikayet / Yapilacak Is","\u015eikayet / Yap\u0131lacak \u0130\u015f"],
      ["Musteriye Acik Not","M\u00fc\u015fteriye A\u00e7\u0131k Not"],
      ["Aksesuarlar / Teslim Alinanlar","Aksesuarlar / Teslim Al\u0131nanlar"],
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
      const text=[part.code,part.barcode,part.name,part.brand,part.category,part.oem_code,part.equivalent_code,part.compatible_models,part.shelf_number].join(" ").toLocaleLowerCase("tr-TR");
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

  productForm=function(product={}){
    const html=baseProductForm(product);
    if(!automotiveMode())return html;
    const fields=`<section class="automotive-fields"><h3>${tr("Otomotiv Parca Bilgileri")}</h3><div class="field"><label>OEM Kod</label><input name="oem_code" value="${esc(product.oem_code||"")}"></div><div class="field"><label>${tr("Muadil Kod")}</label><input name="equivalent_code" value="${esc(product.equivalent_code||"")}"></div><div class="field full"><label>${tr("Uyumlu Marka / Model / Yil")}</label><textarea name="compatible_models" placeholder="Ford Courier 2020-2026; Fiat Egea 2019-2025">${esc(product.compatible_models||"")}</textarea></div><div class="field"><label>${tr("Raf / Konum")}</label><input name="shelf_number" value="${esc(product.shelf_number||"")}"></div></section>`;
    return insertBeforeLastDiv(html,fields);
  };

  saveProduct=async function(formData,existing){
    const values=Object.fromEntries(formData),currency=String(values.currency||"TRY").toUpperCase(),rate=rateForCode(currency);
    if(currency!=="TRY"&&rate<=0)throw Error(`${currency} ${tr("kuru alinamadi")}`);
    const payload={
      id:existing&&/^\d+$/.test(String(existing.id))?+existing.id:undefined,
      name:values.name,code:values.code,barcode:values.barcode,category:values.category,
      brand:values.brand,currency,stock:+values.qty||0,min_stock:+values.min||0,
      purchase_price:+values.buy||0,price:+values.sell||0,description:values.description,
      payment_method:values.payment_method,exchange_rate:rate,oem_code:values.oem_code||"",
      equivalent_code:values.equivalent_code||"",compatible_models:values.compatible_models||"",
      shelf_number:values.shelf_number||""
    };
    const result=await apiFetch("/api/desktop/stock/save",{method:"POST",body:JSON.stringify(payload)});
    const part=result.part,target=existing||{};
    Object.assign(target,{id:String(part.id),code:part.code||"",name:part.name||part.part_name||"",barcode:part.barcode||"",category:part.category||"Genel",brand:part.brand||"",currency:part.currency||"TRY",qty:Number(part.stock||0),min:Number(part.min_stock||0),buy:moneyNumber(part.purchase_price),sell:moneyNumber(part.price),description:part.description||"",oem_code:part.oem_code||"",equivalent_code:part.equivalent_code||"",compatible_models:part.compatible_models||"",shelf_number:part.shelf_number||""});
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
      Object.assign(part,{brand:sourcePart.brand||part.brand||"",description:sourcePart.description||part.description||"",oem_code:sourcePart.oem_code||"",equivalent_code:sourcePart.equivalent_code||"",compatible_models:sourcePart.compatible_models||"",shelf_number:sourcePart.shelf_number||""});
    });
    save();
    if(page==="stock"||page==="automotive-stock")render();
    return source;
  };

  saveCustomer=async function(formData,existing){
    const values=Object.fromEntries(formData);
    const persistedId=existing&&Number.isInteger(+existing.id)?+existing.id:0;
    const payload={
      name:values.name,
      phone:values.phone,
      email:values.email,
      type:values.type,
      balances:{TRY:+values.TRY||0,USD:+values.USD||0,EUR:+values.EUR||0}
    };
    if(persistedId)Object.assign(payload,{id:persistedId,_action:"update"});
    const result=await apiFetch("/api/desktop/table/customers",{
      method:"POST",
      body:JSON.stringify(payload)
    });
    await hydrateDesktop(true);
    const customer=db.customers.find(item=>String(item.id)===String(result.id));
    activity(`${customer?.name||values.name} ${tr(existing?"musteri kaydi guncellendi":"musteri kaydi olusturuldu")}`,"#");
    toast(tr("Musteri kaydedildi"),"success");
    return true;
  };

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
    const assetFields=automotive
      ?`<div class="field"><label>Plaka *</label><input name="plate" required></div><div class="field"><label>${tr("Sasi / VIN")}</label><input name="vin"></div><div class="field"><label>Marka *</label><input name="brand" required></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>${tr("Model Yili")}</label><input name="year" type="number" min="1950" max="2200"></div><div class="field"><label>${tr("Arac Tipi")}</label><input name="vehicle_type" placeholder="Binek, SUV, Ticari"></div><div class="field"><label>${tr("Motor Tipi")}</label><input name="engine_type"></div><div class="field"><label>${tr("Yakit Turu")}</label><select name="fuel_type"><option>Benzin</option><option>Dizel</option><option>Hibrit</option><option>Elektrik</option><option>LPG</option></select></div><div class="field"><label>Kilometre</label><input name="odometer" type="number" min="0"></div>`
      :`<div class="field"><label>${tr("Cihaz Turu")} *</label><input name="device_type" required></div><div class="field"><label>Marka</label><input name="brand"></div><div class="field"><label>Model *</label><input name="model" required></div><div class="field"><label>Seri No / IMEI</label><input name="serial"></div>`;
    openDialog(
      automotive?tr("Yeni Arac Servis Kaydi"):tr("Yeni Servis Kaydi"),
      automotive?"OTOMOTIV SERVIS KABUL FORMU":"TEKNIK SERVIS KABUL FORMU",
      `<div class="form-grid"><div class="field full"><label>${tr("Musteri")} *</label><select name="customerId" required><option value="">${tr("Secin")}</option>${db.customers.map(customer=>`<option value="${customer.id}" ${String(customer.id)===String(customerId)?"selected":""}>${esc(customer.name)}</option>`).join("")}</select></div>${assetFields}<div class="field"><label>Aciliyet</label><select name="priority"><option>Normal</option><option>${tr("Yuksek")}</option><option>Acil</option><option>${tr("Dusuk")}</option></select></div><div class="field"><label>Teknisyen</label><select name="technician"><option value="">${tr("Atanmadi")}</option>${technicians.map(person=>`<option>${esc(person.name)}</option>`).join("")}</select></div><div class="field full"><label>${automotive?tr("Sikayet / Yapilacak Is"):tr("Ariza / Talep")} *</label><textarea name="fault" required></textarea></div><div class="field full"><label>${tr("Musteriye Acik Not")}</label><textarea name="repair_details"></textarea></div><div class="field full"><label>${tr("Teknik Ic Not")}</label><textarea name="internal_notes"></textarea></div><div class="field"><label>${tr("Aksesuarlar / Teslim Alinanlar")}</label><input name="accessories"></div><div class="field"><label>${tr("Tahmini Teslim")}</label><input name="estimated_date" type="date"></div><div class="field"><label>Garanti</label><select name="warranty_status"><option>Yok</option><option>Var</option><option>${tr("Firma Garantisi")}</option></select></div><div class="field"><label>Durum</label><select name="status"><option>Bekliyor</option><option>${tr("Onay Bekliyor")}</option><option>${tr("Islemde")}</option><option>${tr("Parca Bekliyor")}</option></select></div><label class="setting field full"><span>${tr("Kaydettikten sonra servis formunu ac")}</span><input class="switch" type="checkbox" name="open_form" checked></label></div>`,
      async formData=>{
        const values=Object.fromEntries(formData);
        const customer=db.customers.find(item=>String(item.id)===String(values.customerId));
        if(!customer)throw Error(tr("Musteri secin"));
        const no=`SRV-${new Date().getFullYear()}${String(Date.now()).slice(-7)}`;
        const payload={
          tracking_no:no,
          customer_id:+customer.id,
          customer_name:customer.name,
          customer_phone:customer.phone||"",
          device_type:automotive?tr("Arac"):values.device_type,
          device_brand:values.brand||"",
          device_model:values.model,
          vehicle_model_name:values.model,
          serial_no:values.serial||values.vin||values.plate||"",
          vehicle_plate:values.plate||"",
          vehicle_vin:values.vin||"",
          vehicle_year:+values.year||null,
          vehicle_type:values.vehicle_type||"",
          engine_type:values.engine_type||"",
          fuel_type:values.fuel_type||"",
          vehicle_odometer:+values.odometer||0,
          fault_description:values.fault,
          repair_details:values.repair_details,
          internal_notes:values.internal_notes,
          accessories:values.accessories,
          urgency:values.priority,
          priority:values.priority,
          technician:values.technician,
          status:values.status,
          approval_status:"Bekleme",
          entry_date:today(),
          estimated_date:values.estimated_date,
          warranty_status:values.warranty_status,
          payment_status:"Beklemede",
          service_source:automotive?"Web Otomotiv":"Web Teknik Servis"
        };
        const result=await apiFetch("/api/desktop/table/devices",{
          method:"POST",
          body:JSON.stringify(payload)
        });
        const source=await hydrateDesktop(true);
        const serviceOwner=db.customers.find(item=>String(item.id)===String(customer.id));
        const service=serviceOwner?.services?.find(item=>String(item.id)===String(result.id)||item.no===no);
        activity(`${no} ${tr("servis kaydi olusturuldu")}`,"#");
        toast(tr("Servis kaydi musteri ve servis panosuna eklendi"),"success");
        if(values.open_form&&service)setTimeout(()=>serviceDetailDialog(serviceOwner,service),80);
        return Boolean(source);
      },
      automotive?tr("Arac Servisini Kaydet"):tr("Servis Kaydet")
    );
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

  function vehicleEditor(customer,vehicle={}){
    openDialog(vehicle.id?tr("Araci Duzenle"):tr("Yeni Arac"),tr("OTOMOTIV ARAC KARTI"),`<div class="form-grid"><div class="field"><label>Plaka *</label><input name="plate" required value="${esc(vehicle.plate||"")}"></div><div class="field"><label>Marka *</label><input name="brand" required value="${esc(vehicle.brand||"")}"></div><div class="field"><label>Model *</label><input name="model" required value="${esc(vehicle.model||"")}"></div><div class="field"><label>${tr("Model Yili")}</label><input name="year" type="number" min="1900" max="2200" value="${esc(vehicle.year||"")}"></div><div class="field"><label>${tr("Arac Tipi")}</label><input name="vehicle_type" value="${esc(vehicle.vehicle_type||"")}"></div><div class="field"><label>${tr("Motor Tipi")}</label><input name="engine_type" value="${esc(vehicle.engine_type||"")}"></div><div class="field"><label>${tr("Yakit Turu")}</label><select name="fuel_type">${["Benzin","Dizel","LPG","Hibrit","Elektrik"].map(value=>`<option ${vehicle.fuel_type===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>${tr("Son Bilinen KM")}</label><input name="last_known_odometer" type="number" min="0" value="${esc(vehicle.last_known_odometer||0)}"></div><div class="field"><label>${tr("Muayene Tarihi")}</label><input name="inspection_due_date" type="date" value="${esc(String(vehicle.inspection_due_date||"").slice(0,10))}"></div><div class="field full"><label>Notlar</label><textarea name="notes">${esc(vehicle.notes||"")}</textarea></div></div>`,async data=>{
      const values=Object.fromEntries(data),payload={...values,customer_id:+customer.id,year:+values.year||null,last_known_odometer:+values.last_known_odometer||0,is_active:1};
      if(vehicle.id)Object.assign(payload,{id:+vehicle.id,_action:"update"});
      await apiFetch("/api/desktop/table/customer_vehicles",{method:"POST",body:JSON.stringify(payload)});
      toast(tr("Arac karti kaydedildi"),"success");
      setTimeout(()=>customer360(customer),120);
      return true;
    },tr("Araci Kaydet"));
  }

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
    const checks=parseJson(stored.checklist_json,{}),checkItems=[["brakes",tr("Fren sistemi")],["lights",tr("Aydinlatma")],["battery",tr("Aku ve sarj")],["tires",tr("Lastikler")],["steering",tr("Direksiyon ve suspansiyon")],["fluids",tr("Sivi seviyeleri")],["obd",tr("OBD ariza taramasi")],["road_test",tr("Test surusu")]];
    const statuses=[tr("Bekliyor"),tr("Onay Bekliyor"),tr("Islemde"),tr("Tamirde"),tr("Parca Bekliyor"),tr("Test Surecinde"),tr("Tamir Edildi"),tr("Teslim Edildi")];
    service.plate=service.vehicle_plate||service.plate||service.serial||"";
    stored.vehicle_vin=stored.vehicle_vin||service.vehicle_vin||"";
    stored.vehicle_id=stored.vehicle_id||service.vehicle_id||null;
    openDialog(`${service.no} - ${service.device}`,tr("OTOMOTIV TEKNISYEN FORMU"),`<div class="form-grid"><div class="field"><label>${tr("Musteri")}</label><input disabled value="${esc(customer.name)}"></div><div class="field"><label>Durum</label><select name="status">${statuses.map(value=>`<option ${service.status===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>Teknisyen</label><select name="technician"><option value="">${tr("Atanmadi")}</option>${desktopPersonnel.map(person=>`<option ${service.technician===person.name?"selected":""}>${esc(person.name)}</option>`).join("")}</select></div><div class="field"><label>${tr("Oncelik")}</label><select name="priority">${[tr("Dusuk"),"Normal",tr("Yuksek"),"Acil"].map(value=>`<option ${service.priority===value?"selected":""}>${value}</option>`).join("")}</select></div><section class="automotive-fields"><h3>${tr("Arac Kabul ve Kontrol")}</h3><div class="field"><label>Plaka</label><input name="vehicle_plate" value="${esc(stored.vehicle_plate||service.plate||service.serial||"")}"></div><div class="field"><label>VIN</label><input name="vehicle_vin" value="${esc(stored.vehicle_vin||"")}"></div><div class="field"><label>${tr("Motor Kodu")}</label><input name="engine_code" value="${esc(stored.engine_code||"")}"></div><div class="field"><label>${tr("Giris KM")}</label><input name="entry_odometer" type="number" min="0" value="${esc(stored.entry_odometer||service.odometer||0)}"></div><div class="field"><label>${tr("Cikis KM")}</label><input name="exit_odometer" type="number" min="0" value="${esc(stored.exit_odometer||0)}"></div><div class="field"><label>${tr("Giris Yakit")}</label><select name="fuel_level_entry">${["Bos","1/4","1/2","3/4","Dolu"].map(value=>`<option ${stored.fuel_level_entry===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field"><label>${tr("Cikis Yakit")}</label><select name="fuel_level_exit">${["Bos","1/4","1/2","3/4","Dolu"].map(value=>`<option ${stored.fuel_level_exit===value?"selected":""}>${value}</option>`).join("")}</select></div><div class="field full"><label>${tr("Kabul Notlari / Hasar Tespiti")}</label><textarea name="acceptance_notes">${esc(stored.acceptance_notes||"")}</textarea></div><div class="field full"><label>${tr("Arac Kontrol Listesi")}</label><div class="automotive-check-grid">${checkItems.map(([key,label])=>`<label class="setting"><span>${label}</span><input class="switch" type="checkbox" data-auto-check="${key}" ${checks[key]?"checked":""}></label>`).join("")}</div></div><label class="setting"><span>${tr("Musteri onayi alindi")}</span><input class="switch" type="checkbox" name="customer_approval" ${stored.customer_approval?"checked":""}></label><label class="setting"><span>${tr("KVKK onayi alindi")}</span><input class="switch" type="checkbox" name="kvkk_approval" ${stored.kvkk_approval?"checked":""}></label></section><div class="field full"><label>${tr("Teknik Ic Not")}</label><textarea name="internal_notes">${esc(service.internal_notes||"")}</textarea></div><div class="field full"><label>${tr("Yapilan Islem / Musteri Notu")}</label><textarea name="repair_details">${esc(service.repair_details||"")}</textarea></div><div class="field"><label>${tr("Iscilik Tutari")}</label><input name="labor_cost" type="number" min="0" step=".01" value="${service.labor_cost||0}"></div><div class="field"><label>${tr("Kargo Tutari")}</label><input name="cargo_fee" type="number" min="0" step=".01" value="${service.cargo_fee||0}"></div><div class="field"><label>${tr("Kullanilan Stok")}</label><select name="part_id"><option value="">${tr("Parca kullanilmadi")}</option>${db.stock.filter(part=>part.qty>0).map(part=>`<option value="${part.id}">${esc(part.name)} (${part.qty} - ${money(part.sell,part.currency)})</option>`).join("")}</select></div><div class="field"><label>${tr("Parca Adedi")}</label><input name="part_quantity" type="number" min="0" step="1" value="0"></div><label class="setting field"><span>${tr("Simdi tahsilat al")}</span><input class="switch" id="collectPayment" name="collect_payment" type="checkbox"></label><div class="field payment-field" hidden><label>${tr("Tahsilat Tutari")}</label><input name="payment_amount" type="number" min="0" step=".01" value="0"></div><div class="field payment-field" hidden><label>${tr("Para Birimi")}</label><select name="payment_currency"><option>TRY</option><option>USD</option><option>EUR</option></select></div><div class="field payment-field" hidden><label>${tr("Odeme Yontemi")}</label><select name="payment_method"><option>Nakit</option><option>Banka</option><option>${tr("Kredi Karti")}</option></select></div></div>`,async formData=>{
      const values=Object.fromEntries(formData),currency=values.payment_currency||"TRY",checklist={};
      $$('[data-auto-check]',$("#dialogBody")).forEach(control=>checklist[control.dataset.autoCheck]=control.checked);
      const payload={device_id:+service.id,tracking_no:service.no,status:values.status,technician:values.technician,priority:values.priority,internal_notes:values.internal_notes,repair_details:values.repair_details,labor_cost:+values.labor_cost||0,cargo_fee:+values.cargo_fee||0,part_id:+values.part_id||0,part_quantity:+values.part_quantity||0,collect_payment:Boolean(values.collect_payment),payment_amount:+values.payment_amount||0,payment_currency:currency,payment_method:values.payment_method,exchange_rate:rateForCode(currency),automotive_form:{vehicle_id:+stored.vehicle_id||null,vehicle_plate:values.vehicle_plate,vehicle_vin:values.vehicle_vin,engine_code:values.engine_code,entry_odometer:+values.entry_odometer||0,exit_odometer:+values.exit_odometer||0,fuel_level_entry:values.fuel_level_entry,fuel_level_exit:values.fuel_level_exit,acceptance_notes:values.acceptance_notes,checklist,damage_marks:[],customer_approval:Boolean(values.customer_approval),kvkk_approval:Boolean(values.kvkk_approval)}};
      const result=await apiFetch("/api/desktop/technician/update",{method:"POST",body:JSON.stringify(payload)});
      await hydrateDesktop(true);activity(`${service.no} ${tr("otomotiv teknisyen kaydi guncellendi")}`,"#");toast(result.finance_id?tr("Servis, stok, arac kontrolu ve tahsilat islendi"):tr("Servis, stok ve arac kontrolu kaydedildi"),"success");return true;
    },tr("Islemi Kaydet"));
    const collect=$("#collectPayment");
    if(collect)collect.onchange=()=>$$('.payment-field').forEach(field=>field.hidden=!collect.checked);
    if(window.ayecBindUsedPartsEditor)window.ayecBindUsedPartsEditor(service);
  };
  const ayecParityStockTable=stockTable;
  stockTable=function(rows){
    return ayecParityStockTable(rows);
  };
})();
