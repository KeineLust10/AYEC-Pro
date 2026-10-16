(()=>{
  const fold=value=>String(value??"").toLocaleLowerCase("tr-TR").replace(/[\u00e7\u011f\u0131\u00f6\u015f\u00fc]/g,character=>({"\u00e7":"c","\u011f":"g","\u0131":"i","\u00f6":"o","\u015f":"s","\u00fc":"u"}[character]||character));
  const lineItem=line=>line?.type==="service"?{id:line.serviceId,name:line.name,description:line.description||"",sell:Number(line.unitPriceTry??line.priceTry)||0,buy:0,currency:"TRY",qty:999,isService:true}:db.stock.find(item=>String(item.id)===String(line?.productId));
  cartTotal=function(){return salesCart.reduce((sum,line)=>{const item=lineItem(line);return sum+(item?(line.type==="service"?Number(line.unitPriceTry??line.priceTry)||0:normalizedPrice(item))*Number(line.qty||0):0)},0)};
  cartHtml=function(){
    if(!salesCart.length)return empty("Sepet bo\u015f","Soldaki stok ve hizmet listesinden se\u00e7im yap\u0131n.");
    return salesCart.map((line,index)=>{
      const item=lineItem(line);if(!item)return "";
      const service=line.type==="service",price=service?Number(line.unitPriceTry??line.priceTry)||0:normalizedPrice(item),maximum=service?999:Number(item.qty||0);
      return `<div class="cart-line" data-kind="sales-cart" data-id="${index}" tabindex="0"><strong>${esc(service?line.name:item.name)}${service?'<small class="muted">Hizmet</small>':""}</strong><input class="control cart-qty" type="number" min="1" max="${maximum}" value="${esc(line.qty)}" data-index="${index}"><span>${money(price*Number(line.qty||0),"TRY")}</span><button class="mini" data-action="cart-remove" data-index="${index}">\u00d7</button></div>`;
    }).join("");
  };
  const previousContextAction=contextAction;
  contextAction=function(kind,id,action,row){
    if(kind!=="sales-cart")return previousContextAction(kind,id,action,row);
    const index=Number(id),line=salesCart[index],item=lineItem(line);if(!line||!item)return;
    if(action==="sales-cart-remove"){salesCart.splice(index,1);render();return}
    if(action==="sales-cart-copy"){salesCart.splice(index+1,0,{...line});render();return}
    if(action==="sales-cart-quantity"){
      const maximum=line.type==="service"?999:Number(item.qty||0);
      openDialog("Miktar\u0131 De\u011fi\u015ftir","SATI\u015e SEPET\u0130",`<div class="field"><label>Yeni miktar</label><input name="quantity" type="number" min="1" max="${maximum}" step="1" value="${esc(line.qty)}" required></div>`,form=>{const quantity=Number(form.get("quantity"));if(!Number.isInteger(quantity)||quantity<1||quantity>maximum){toast("Miktar ge\u00e7erli aral\u0131kta olmal\u0131.","error");return false}line.qty=quantity;render();return true},"Miktar\u0131 Kaydet");return;
    }
    if(action==="sales-cart-price"){
      const priceTry=Number(line.unitPriceTry??line.priceTry??normalizedPrice(item));
      openDialog("Fiyat\u0131 G\u00fcncelle","SATI\u015e SEPET\u0130",`<div class="field"><label>Yeni birim fiyat (TRY)</label><input name="unit_price" type="number" min="0" max="1000000000" step="0.01" value="${priceTry}" required></div>`,form=>{const value=Number(form.get("unit_price"));if(!Number.isFinite(value)||value<0||value>1000000000)return false;if(line.type==="service")line.unitPriceTry=value;else line.unitPriceTry=value;render();return true},"Fiyat\u0131 Kaydet");return;
    }
    if(action==="sales-cart-description"){
      openDialog("A\u00e7\u0131klama Ekle","SATI\u015e SEPET\u0130",`<div class="field"><label>Kalem a\u00e7\u0131klamas\u0131</label><textarea name="description">${esc(line.description||item.description||"")}</textarea></div>`,form=>{line.description=String(form.get("description")||"");render();return true},"A\u00e7\u0131klamay\u0131 Kaydet");return;
    }
    previousContextAction(kind,id,action,row);
  };
  let serviceRows=[];
  async function openBulkSalesSelection(){
    let response;
    try{response=await apiFetch("/api/desktop/table/services?limit=1000")}catch(error){toast("Hizmet listesi y\u00fcklenemedi: "+error.message,"error");return}
    serviceRows=(response.rows||[]).filter(item=>item&&item.name).map(item=>({...item,_selectionType:"service",_priceTry:moneyNumber(item.price||0)}));
    const parts=db.stock.filter(item=>Number(item.qty||0)>0).map(item=>({...item,_selectionType:"part",_priceTry:normalizedPrice(item),stock:Number(item.qty||0)}));
    const all=[...parts,...serviceRows];
    const state={mode:"part",system:"all",status:"available",sort:"price_asc",query:"",selected:new Map()};
    const key=item=>`${item._selectionType}:${item.id??item.name}`;
    const body=`<section class="bulk-sales-select"><p class="muted">Hizmet veya stok \u00fcr\u00fcnlerini filtreleyin, adet belirleyin ve tek t\u0131kla sepete ekleyin.</p><nav class="bulk-sales-modes"><button type="button" class="active" data-bulk-mode="part">Stok &amp; Par\u00e7a</button><button type="button" data-bulk-mode="service">Hizmet &amp; \u0130\u015f\u00e7ilik</button></nav><nav class="bulk-sales-systems">${[["all","T\u00fcm\u00fc"],["computer","Bilgisayar Bile\u015fenleri"],["security","G\u00fcvenlik Sistemleri"],["smart_home","Ak\u0131ll\u0131 Ev Sistemleri"]].map(([value,label])=>`<button type="button" data-bulk-system="${value}" class="${value==="all"?"active":""}">${label}</button>`).join("")}</nav><div class="bulk-sales-filters"><input type="search" id="bulkSalesSearch" class="control search" placeholder="\u00dcr\u00fcn, kod, barkod veya a\u00e7\u0131klama ara"><select id="bulkSalesStatus" class="control"><option value="available">Durum: Yaln\u0131zca Stokta Olanlar</option><option value="all">Durum: T\u00fcm\u00fcn\u00fc G\u00f6ster (Kritik Dahil)</option><option value="critical">Durum: Yaln\u0131zca Kritik Stok (&lt;10)</option></select><select id="bulkSalesSort" class="control"><option value="price_asc">S\u0131ralama: Fiyata G\u00f6re Artan</option><option value="price_desc">S\u0131ralama: Fiyata G\u00f6re Azalan</option><option value="best_selling">S\u0131ralama: En \u00c7ok Satanlar</option><option value="stock">S\u0131ralama: Stok Miktar\u0131na G\u00f6re</option></select><label><input id="bulkSalesVisible" type="checkbox">G\u00f6r\u00fcnenleri Se\u00e7</label></div><div class="bulk-sales-count" id="bulkSalesCount"></div><div class="table-wrap bulk-sales-table-wrap"><table><thead><tr><th>Se\u00e7</th><th>\u00dcr\u00fcn / Hizmet</th><th>Kod</th><th>Stok</th><th>Fiyat (TRY)</th><th>Adet</th></tr></thead><tbody id="bulkSalesRows"></tbody></table></div><p class="bulk-sales-selected" id="bulkSalesSelected">0 se\u00e7ili</p></section>`;
    openDialog("Toplu \u00dcr\u00fcn &amp; Hizmet Se\u00e7im Havuzu","SATI\u015e SEPET\u0130",body,()=>{
      const chosen=[...state.selected.entries()].filter(([,value])=>value.checked);
      if(!chosen.length){toast("L\u00fctfen en az bir hizmet veya stok \u00fcr\u00fcn\u00fc se\u00e7in.","warning");return false}
      for(const [itemKey,value] of chosen){
        const item=all.find(candidate=>key(candidate)===itemKey);if(!item)continue;
        const quantity=Number(value.qty);if(!Number.isInteger(quantity)||quantity<1){toast("Adet en az 1 olmal\u0131.","warning");return false}
        if(item._selectionType==="part"){
          const line=salesCart.find(entry=>entry.type!=="service"&&String(entry.productId)===String(item.id));
          if(quantity+Number(line?.qty||0)>Number(item.stock)){toast(`${item.name} i\u00e7in yeterli stok yok.`,"warning");return false}
          if(line)line.qty+=quantity;else salesCart.push({productId:item.id,qty:quantity});
        }else{
          const line=salesCart.find(entry=>entry.type==="service"&&String(entry.serviceId)===String(item.id));
          if(line)line.qty+=quantity;else salesCart.push({type:"service",serviceId:item.id,name:item.name,description:item.description||"",priceTry:Number(item._priceTry)||0,qty:quantity});
        }
      }
      render();toast("Se\u00e7ilen hizmet ve stok kalemleri sepete eklendi.","success");return true;
    },"Se\u00e7ilenleri Sepete Ekle");
    const rowsHost=document.getElementById("bulkSalesRows"),search=document.getElementById("bulkSalesSearch"),status=document.getElementById("bulkSalesStatus"),sort=document.getElementById("bulkSalesSort"),selectVisible=document.getElementById("bulkSalesVisible");
    const systemKey=item=>{const text=fold([item.name,item.category,item.description,item.code,item.brand].join(" "));if(/guvenlik|kamera|alarm|sensor|nvr|dvr|yangin|interkom|kayit|siren|dedektor|ups|pir/.test(text))return "security";if(/akilli|smart|hub|priz|role|aydinlatma|ev sarj|sarj|ses asistan|klima kontrol|enerji yonet|kilit|homepod|echo|zigbee|aqara/.test(text))return "smart_home";if(/anakart|islemci|ram|ssd|hdd|ekran kart|gpu|psu|kasa|monitor|klavye|mouse|yazilim|cpu|thermal|kablo|printer|modem|sunucu|bilgisayar|computer|pc|laptop|nvme/.test(text))return "computer";return "computer"};
    const visibleItems=()=>{
      const q=fold(state.query),items=all.filter(item=>item._selectionType===state.mode);
      return items.filter(item=>{
        const searchText=fold([item.name,item.code,item.sku,item.barcode,item.description,item.category,item.brand].join(" "));
        const systemMatch=state.system==="all"||systemKey(item)===state.system;
        const stock=Number(item.stock||0),statusMatch=item._selectionType==="service"||state.status==="all"||(state.status==="available"&&stock>0)||(state.status==="critical"&&stock>0&&stock<10);
        return (!q||searchText.includes(q))&&systemMatch&&statusMatch;
      }).sort((a,b)=>{const name=String(a.name||"").localeCompare(String(b.name||""),"tr");if(state.sort==="price_desc")return b._priceTry-a._priceTry||name;if(state.sort==="stock")return Number(b.stock||0)-Number(a.stock||0)||name;if(state.sort==="best_selling")return Number(b.sales_count||b.sold_count||0)-Number(a.sales_count||a.sold_count||0)||name;return a._priceTry-b._priceTry||name});
    };
    const updateSelected=()=>{const n=[...state.selected.values()].filter(value=>value.checked).length;document.getElementById("bulkSalesSelected").textContent=`${n} se\u00e7ili`;selectVisible.checked=visibleItems().length>0&&visibleItems().every(item=>state.selected.get(key(item))?.checked)};
    const renderRows=()=>{
      const visible=visibleItems();document.getElementById("bulkSalesCount").textContent=`${visible.length} kay\u0131t listeleniyor`;
      rowsHost.innerHTML=visible.map(item=>{const id=esc(key(item)),saved=state.selected.get(key(item))||{checked:false,qty:1},stock=Number(item.stock||0);return `<tr><td><input type="checkbox" data-bulk-select-check="${id}" ${saved.checked?"checked":""} aria-label="Se\u00e7: ${esc(item.name)}"></td><td><strong>${esc(item.name)}</strong><small>${esc(item.category||item.description||"")}</small></td><td>${esc(item.code||item.sku||item.barcode||"-")}</td><td>${item._selectionType==="service"?"Hizmet":stock}</td><td>${money(Number(item._priceTry)||0,"TRY")}</td><td><input type="number" min="1" max="${item._selectionType==="service"?999:Math.max(1,stock)}" value="${esc(saved.qty)}" data-bulk-select-qty="${id}" aria-label="Adet: ${esc(item.name)}"></td></tr>`}).join("")||`<tr><td colspan="6">${state.mode==="service"?"Hizmet bulunamad\u0131.":"Se\u00e7ilen filtrelerde stok bulunamad\u0131."}</td></tr>`;
      rowsHost.querySelectorAll("[data-bulk-select-check]").forEach(input=>input.addEventListener("change",()=>{const itemKey=input.dataset.bulkSelectCheck,saved=state.selected.get(itemKey)||{qty:1};saved.checked=input.checked;state.selected.set(itemKey,saved);updateSelected()}));
      rowsHost.querySelectorAll("[data-bulk-select-qty]").forEach(input=>input.addEventListener("input",()=>{const itemKey=input.dataset.bulkSelectQty,saved=state.selected.get(itemKey)||{checked:false};saved.qty=Number(input.value)||1;state.selected.set(itemKey,saved)}));updateSelected();
    };
    document.querySelectorAll("[data-bulk-mode]").forEach(button=>button.onclick=()=>{state.mode=button.dataset.bulkMode;document.querySelectorAll("[data-bulk-mode]").forEach(item=>item.classList.toggle("active",item===button));renderRows()});
    document.querySelectorAll("[data-bulk-system]").forEach(button=>button.onclick=()=>{state.system=button.dataset.bulkSystem;document.querySelectorAll("[data-bulk-system]").forEach(item=>item.classList.toggle("active",item===button));renderRows()});
    search.oninput=()=>{state.query=search.value;renderRows()};status.onchange=()=>{state.status=status.value;renderRows()};sort.onchange=()=>{state.sort=sort.value;renderRows()};
    selectVisible.onchange=()=>{visibleItems().forEach(item=>{const itemKey=key(item),saved=state.selected.get(itemKey)||{qty:1};saved.checked=selectVisible.checked;state.selected.set(itemKey,saved)});renderRows()};renderRows();
  }
  const addSalesBulkButton=()=>{const search=document.getElementById("salesProductSearch");if(!search||document.querySelector("[data-sales-bulk-select]"))return;const button=document.createElement("button");button.type="button";button.className="secondary";button.dataset.salesBulkSelect="";button.textContent="Toplu Se\u00e7im";button.title="Stok ve hizmetleri toplu se\u00e7";search.insertAdjacentElement("afterend",button)};
  new MutationObserver(addSalesBulkButton).observe(document.body,{childList:true,subtree:true});addSalesBulkButton();
  document.addEventListener("click",event=>{if(event.target.closest("[data-sales-bulk-select]")){openBulkSalesSelection().catch(error=>toast(error.message||"Se\u00e7im havuzu a\u00e7\u0131lamad\u0131.","error"));}});
  document.addEventListener("keydown",event=>{if(event.ctrlKey&&event.key.toLowerCase()==="f"&&document.getElementById("appDialog")?.open){event.preventDefault();document.getElementById("bulkSalesSearch")?.focus()}});
})();
