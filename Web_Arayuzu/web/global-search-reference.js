(()=>{
  const input=document.getElementById("globalSearch");
  const searchLabel=input?.closest(".global-search");
  if(!input||!searchLabel)return;
  const wrapper=document.createElement("div");
  wrapper.className="global-search-wrap";
  const results=document.createElement("div");
  results.className="global-search-results";
  results.id="globalSearchResults";
  results.setAttribute("role","listbox");
  results.setAttribute("aria-label","Global search results");
  results.hidden=true;
  searchLabel.before(wrapper);
  const searchAnchor=document.createComment("Global search position");
  wrapper.before(searchAnchor);
  wrapper.append(searchLabel,results);
  const palette=document.createElement("dialog");
  palette.id="globalSearchDialog";
  palette.className="global-search-dialog";
  palette.innerHTML='<div class="global-search-dialog-head"><strong>Global Arama</strong><small>Sayfa, m\u00fc\u015fteri, stok veya servis ara</small></div><div class="global-search-dialog-body"></div><div class="global-search-dialog-foot">Secmek icin Enter, kapatmak icin Esc</div>';
  document.body.append(palette);
  input.setAttribute("role","combobox");
  input.setAttribute("aria-autocomplete","list");
  input.setAttribute("aria-controls",results.id);
  input.setAttribute("aria-expanded","false");
  const topbarPlaceholder=input.placeholder;

  const fallbackPageItems=[
    {label:"Ana Sayfa",route:"dashboard"},
    {label:"Servis Takip",route:"services"},
    {label:"M\u00fc\u015fteri Listesi",route:"customers"},
    {label:"Stok Listesi",route:"stock"},
    {label:"Gelir / Gider",route:"finance"},
    {label:"Ayarlar",route:"settings"},
    {label:"Duyurular",route:"announcements"},
    {label:"Saha Servisi",route:"field-service"}
  ];
  const pageItems=()=>{
    const visible=Array.from(document.querySelectorAll("#nav [data-page]"))
      .map(button=>({label:(button.querySelector(".nav-label")?.textContent||button.children[1]?.textContent||button.textContent).trim(),route:button.dataset.page}))
      .filter(item=>item.label&&item.route);
    return visible.length?visible:fallbackPageItems;
  };
  let matches=[];
  let activeIndex=-1;
  const fold=value=>String(value??"").toLocaleLowerCase("tr-TR").replace(/[\u00e7\u011f\u0131\u00f6\u015f\u00fc]/g,character=>({"\u00e7":"c","\u011f":"g","\u0131":"i","\u00f6":"o","\u015f":"s","\u00fc":"u"}[character]||character));
  const close=()=>{results.hidden=true;input.setAttribute("aria-expanded","false");input.removeAttribute("aria-activedescendant");activeIndex=-1};
  const closePalette=()=>{if(palette.open)palette.close();input.placeholder=topbarPlaceholder;searchAnchor.before(wrapper)};
  const openPalette=()=>{if(!palette.open){palette.querySelector(".global-search-dialog-body").append(wrapper);input.placeholder="Gitmek istedi\u011finiz yer, m\u00fc\u015fteri, stok veya servis...";palette.showModal()}input.focus();input.select();render()};
  window.ayecOpenGlobalSearch=openPalette;
  const activate=item=>{
    close();
    closePalette();
    if(item.kind==="page"){navigate(item.route);return}
    if(item.kind==="service"){
      window.ayecAdvancedServiceFilter={customer:"",tracking:item.query,serial:"",fault:"T\u00fcm\u00fc",status:"Hepsi",date_start:"",date_end:""};
      navigate("services");
      return;
    }
    navigate(item.kind==="customer"?"customers":"stock");
    setTimeout(()=>{
      const field=document.getElementById(item.kind==="customer"?"customerSearch":"stockSearch");
      if(!field)return;
      field.value=item.query;
      field.dispatchEvent(new Event("input",{bubbles:true}));
      field.focus({preventScroll:true});
    },0);
  };
  const markActive=index=>{
    activeIndex=matches.length?(index+matches.length)%matches.length:-1;
    results.querySelectorAll("[role=option]").forEach((button,i)=>{
      button.classList.toggle("active",i===activeIndex);
      button.setAttribute("aria-selected",i===activeIndex?"true":"false");
    });
    if(activeIndex>=0)input.setAttribute("aria-activedescendant",`globalSearchResult${activeIndex}`);
    else input.removeAttribute("aria-activedescendant");
  };
  const render=()=>{
    const query=input.value.trim();
    const folded=fold(query);
    matches=[];
    if(folded.length<2){close();return}
    pageItems().filter(item=>fold(item.label).includes(folded)).forEach(item=>matches.push({...item,kind:"page",subtitle:"Sayfaya Git"}));
    (Array.isArray(db?.customers)?db.customers:[]).filter(customer=>fold(customer.name).includes(folded)||fold(customer.phone).includes(folded)).slice(0,5).forEach(customer=>matches.push({kind:"customer",query:customer.name,label:customer.name,subtitle:`M\u00fc\u015fteri Detay\u0131na Git (${customer.phone||"-"})`}));
    (Array.isArray(db?.customers)?db.customers:[]).flatMap(customer=>(Array.isArray(customer.services)?customer.services:[]).map(service=>({...service,customerName:customer.name}))).filter(service=>[service.no,service.tracking_no,service.customerName,service.serial,service.serial_no,service.device,service.device_model,service.note,service.fault_description,service.status].some(value=>fold(value).includes(folded))).slice(0,5).forEach(service=>{const no=String(service.no||service.tracking_no||"");if(no)matches.push({kind:"service",query:no,label:no,subtitle:`Servis: ${service.customerName||"M\u00fcşteri"} | ${service.device||service.device_model||service.device_type||"Cihaz"} | ${service.status||""}`})});
    (Array.isArray(db?.stock)?db.stock:[]).filter(stock=>fold(stock.name).includes(folded)).slice(0,5).forEach(stock=>matches.push({kind:"stock",query:stock.name,label:stock.name,subtitle:`Stok: ${stock.quantity??stock.qty??0} Adet | ${money(stock.sell??stock.price_sell??0,stock.currency||"TRY")}`}));
    if(!matches.length){close();return}
    results.innerHTML=matches.map((item,index)=>`<button type="button" id="globalSearchResult${index}" data-search-kind="${esc(item.kind)}" data-search-route="${esc(item.route||"")}" role="option" aria-selected="false" class="global-search-result"><strong>${esc(item.label)}</strong><small>${esc(item.subtitle)}</small></button>`).join("");
    results.hidden=false;
    input.setAttribute("aria-expanded","true");
    activeIndex=-1;
    results.querySelectorAll("[role=option]").forEach((button,index)=>button.addEventListener("click",()=>activate(matches[index])));
  };
  input.addEventListener("input",render);
  input.addEventListener("keydown",event=>{
    if(event.key==="ArrowDown"&&matches.length){event.preventDefault();markActive(activeIndex+1)}
    else if(event.key==="ArrowUp"&&matches.length){event.preventDefault();markActive(activeIndex<0?matches.length-1:activeIndex-1)}
    else if(event.key==="Escape"){event.preventDefault();close();closePalette()}
    else if(event.key==="Enter"){
      if(!matches.length){if(input.value.trim().length>=2)toast("E\u015fle\u015fen kay\u0131t bulunamad\u0131","warning");return}
      event.preventDefault();activate(matches[activeIndex>=0?activeIndex:0]);
    }
  });
  document.addEventListener("keydown",event=>{
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
      event.preventDefault();
      const pageSearch=page==="contracts"?document.querySelector("#genericSearch"):page==="customers"?document.querySelector("#customerSearch"):null;
      if(pageSearch){pageSearch.focus();pageSearch.select();return}
      openPalette();
    }
  });
  palette.addEventListener("close",()=>{close();input.placeholder=topbarPlaceholder;searchAnchor.before(wrapper)});
  palette.addEventListener("click",event=>{if(event.target===palette)closePalette()});
  document.addEventListener("click",event=>{if(!wrapper.contains(event.target))close()});
})();
