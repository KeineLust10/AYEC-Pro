(function(){
  sectorPages.teknik_servis.add("loans");
  sectorPages.otomotiv.add("loans");
  let loanRows=[], installmentRows=[], loanPage=1, loanCurrency="USD", loanFilter="active", loanQuery="", selectedLoanId=null;
  const loanPageSize=11;
  const loanText=(value)=>String(value??"");
  const loanDate=(value)=>{if(!value)return "\u2014";const date=new Date(`${value}T00:00:00`);return Number.isNaN(date.getTime())?loanText(value):new Intl.DateTimeFormat("tr-TR").format(date)};
  const loanMoney=(value,currency=loanCurrency)=>{const code=currency||"TRY",raw=Number(value||0),rate=code==="TRY"?1:Number(exchangeRateState?.[code]?.selling||0),precisionValue=Number.parseInt(desktopSettings.currency_precision||"2",10),precision=Number.isFinite(precisionValue)?Math.max(0,Math.min(3,precisionValue)):2,displayCode=code!=="TRY"&&rate<=0?"TRY":code,amount=displayCode==="TRY"?raw:raw/rate,symbol={TRY:"\u20ba",USD:"$",EUR:"\u20ac"}[displayCode]||displayCode;return `${new Intl.NumberFormat("en-US",{minimumFractionDigits:precision,maximumFractionDigits:precision}).format(amount)} ${symbol}`};
  function loansView(){return `${pageHead("Krediler & Taksitler","Kredi s\u00f6zle\u015fmelerini ve \u00f6deme planlar\u0131n\u0131 izleyin.",'<button class="secondary" id="loansRefresh">Yenile</button><button class="primary" id="loanCreate">+ Yeni Kredi Ekle</button>')}<section class="loan-metrics" id="loanMetrics"></section><section class="card loan-contract" id="loanContract"></section><section class="loan-toolbar"><div class="loan-filters"><button type="button" data-loan-filter="active" class="active">Aktif</button><button type="button" data-loan-filter="all">T\u00fcm S\u00f6zle\u015fmeler</button></div><input class="control search" id="loanSearch" placeholder="Banka ad\u0131, kredi no veya kullan\u0131m yeri ara..." aria-label="Kredi ara"><select class="control" id="loanSelect" aria-label="Kredi s\u00f6zle\u015fmesi"></select><div class="loan-currencies">${["USD","TRY","EUR"].map(code=>`<button type="button" data-loan-currency="${code}" class="${code===loanCurrency?"active":""}">${code}</button>`).join("")}</div><div class="loan-export-actions"><button type="button" class="secondary" id="loanExport">Excel / CSV</button><button type="button" class="secondary" id="loanPrint">Yazd\u0131r</button></div></section><section class="card loan-installments"><div class="loan-table-head"><div><h3>\u00d6deme Plan\u0131</h3><p id="loanTableSummary"></p></div></div><div class="table-wrap"><table><thead><tr><th>#</th><th>Vade Tarihi</th><th>Tutar</th><th>Durum</th><th>\u00d6deme Tarihi</th><th>\u0130\u015flem</th></tr></thead><tbody id="loanTableBody"></tbody></table></div><footer class="loan-pagination"><span id="loanPageSummary"></span><div><button type="button" class="secondary" id="loanPrev">Geri</button><button type="button" class="secondary" id="loanNext">\u0130leri</button></div></footer></section>`}
  function installmentIsPaid(item){const status=String(item?.status||"").toLocaleLowerCase("tr-TR").normalize("NFD").replace(/[\u0300-\u036f]/g,"");return ["odendi","paid","dendi"].includes(status)}
  function filteredLoans(){return loanRows.filter(row=>{const active=loanFilter==="all"||String(row.status||"").toLocaleLowerCase("tr-TR")==="aktif",searchable=[row.bank_name,row.description,row.loan_title,row.id].map(value=>String(value??"")).join(" ").toLocaleLowerCase("tr-TR");return active&&searchable.includes(loanQuery.toLocaleLowerCase("tr-TR"))})}
  function printLoanSchedule(){
    const rows=filteredLoans().flatMap(loan=>installmentRows.filter(item=>String(item.loan_id)===String(loan.id)).sort((left,right)=>Number(left.installment_no)-Number(right.installment_no)).map(item=>({bank:loan.bank_name||"",installment:item.installment_no,due:item.due_date||"",amount:loanMoney(item.amount??item.total_amount),status:item.status||"",paid:item.paid_date||""})));
    const root=document.createElement("main");root.id="loanPrintDocument";
    root.innerHTML=`<h2>Kredi ve Taksit Plan\u0131</h2><table><thead><tr><th>Banka</th><th>Taksit</th><th>Vade</th><th>Tutar</th><th>Durum</th><th>\u00d6deme tarihi</th></tr></thead><tbody>${rows.map(item=>`<tr><td>${esc(item.bank)}</td><td>${esc(item.installment)}</td><td>${esc(item.due)}</td><td>${esc(item.amount)}</td><td>${esc(item.status)}</td><td>${esc(item.paid)}</td></tr>`).join("")}</tbody></table>`;
    document.body.append(root);document.body.classList.add("loan-print-mode");let cleaned=false;
    const cleanup=()=>{if(cleaned)return;cleaned=true;root.remove();document.body.classList.remove("loan-print-mode")};
    window.addEventListener("afterprint",cleanup,{once:true});
    try{window.print()}finally{window.setTimeout(cleanup,1000)}
  }
  function drawLoans(){const host=document.getElementById("loanTableBody");if(!host)return;const choices=filteredLoans();if(!choices.some(row=>String(row.id)===String(selectedLoanId)))selectedLoanId=choices[0]?.id??null;const loan=choices.find(row=>String(row.id)===String(selectedLoanId))||choices[0],selector=document.getElementById("loanSelect");if(selector){selector.innerHTML=choices.map(row=>`<option value="${esc(row.id)}">${esc(row.bank_name||"Banka")} \u00b7 ${esc(row.loan_type||"Kredi")}</option>`).join("");selector.value=String(selectedLoanId??"")}const items=loan?installmentRows.filter(row=>String(row.loan_id)===String(loan.id)).sort((a,b)=>Number(a.installment_no)-Number(b.installment_no)):[];const paid=items.filter(installmentIsPaid).length,remaining=items.filter(row=>!installmentIsPaid(row)).reduce((sum,row)=>sum+Number(row.total_amount||0),0),next=items.find(row=>!installmentIsPaid(row));document.getElementById("loanMetrics").innerHTML=`<article><span>Toplam Kredi</span><strong>${loanMoney(loan?.amount??loan?.principal_amount??0)}</strong><small>${loanRows.length} sozlesme</small></article><article><span>Kalan Borc</span><strong>${loanMoney(remaining)}</strong><small>${items.length-paid} taksit kaldi</small></article><article><span>Aylik Taksit</span><strong>${loanMoney(next?.total_amount||0)}</strong><small>Planlanan odeme</small></article><article><span>Sonraki Vade</span><strong>${loanDate(next?.due_date)||"\u2014"}</strong><small>${next?`Taksit ${next.installment_no}`:"\u00d6deme bulunmuyor"}</small></article>`;document.getElementById("loanContract").innerHTML=loan?`<div data-loan-context-row="${esc(loan.id)}"><small>KREDI SOZLESMESI</small><h3>${esc(loan.bank_name||"Banka")}</h3><span>${esc(loan.loan_type||"Banka Kredisi")}</span></div><div><small>TOPLAM KREDI</small><strong>${loanMoney(loan.amount??loan.principal_amount)}</strong></div><div><small>FAIZ ORANI</small><strong>%${esc(loan.interest_rate||0)}</strong></div><div><small>KALAN TAKS\u0130T</small><strong>${items.length-paid} / ${items.length}</strong></div><div><small>B\u0130T\u0130\u015e TAR\u0130H\u0130</small><strong>${loanDate(items.at(-1)?.due_date)}</strong></div><button type="button" id="loanDetails" class="secondary">S\u00f6zle\u015fme Detay\u0131</button>`:empty("Kredi kaydi bulunamadi","Masaustu veritabaninda kredi kaydi yok.");document.getElementById("loanTableSummary").textContent=`${items.length} taksit \u00b7 ${paid} \u00f6dendi`;const pages=Math.max(1,Math.ceil(items.length/loanPageSize));loanPage=Math.min(loanPage,pages);const shown=items.slice((loanPage-1)*loanPageSize,loanPage*loanPageSize);host.innerHTML=shown.map(item=>`<tr tabindex="0" data-installment-row="${esc(item.id)}" data-loan-id="${esc(item.loan_id)}"><td>${esc(item.installment_no)}</td><td>${loanDate(item.due_date)}</td><td>${loanMoney(item.total_amount)}</td><td><span class="loan-status ${installmentIsPaid(item)?"paid":"pending"}">${esc(item.status||"Bekliyor")}</span></td><td>${loanDate(item.paid_date)}</td><td><button type="button" class="loan-row-action" data-loan-action="${installmentIsPaid(item)?"details":"pay"}" data-installment="${esc(item.id)}">${installmentIsPaid(item)?"\u00d6deme Detaylar\u0131":"\u015eimdi \u00d6de"}</button></td></tr>`).join("")||`<tr><td colspan="6">${empty("\u00d6deme plan\u0131 yok","Bu sozlesme icin taksit kayd\u0131 bulunamadi.")}</td></tr>`;document.getElementById("loanPageSummary").textContent=`Sayfa ${loanPage} / ${pages}`;document.getElementById("loanPrev").disabled=loanPage<=1;document.getElementById("loanNext").disabled=loanPage>=pages;document.querySelectorAll("[data-loan-action]").forEach(button=>button.onclick=()=>{const item=installmentRows.find(row=>String(row.id)===button.dataset.installment);if(!item)return;if(button.dataset.loanAction==="details"){openDialog("\u00d6deme Detaylar\u0131","KREDI TAKSITI",`<div class="form-grid"><div class="field"><label>Taksit</label><strong>${esc(item.installment_no)}</strong></div><div class="field"><label>Tutar</label><strong>${loanMoney(item.total_amount)}</strong></div><div class="field"><label>Vade</label><strong>${loanDate(item.due_date)}</strong></div><div class="field"><label>\u00d6deme Tarihi</label><strong>${loanDate(item.paid_date)}</strong></div></div>`,()=>true,"Kapat");document.getElementById("dialogFooter").insertAdjacentHTML("afterbegin",'<button type="button" class="secondary" id="loanMarkPending">\u00d6demeyi Geri Al</button>');document.getElementById("loanMarkPending").onclick=()=>apiFetch(`/api/desktop/loan-installments/${item.id}/status`,{method:"POST",body:JSON.stringify({status:"Bekliyor"})}).then(()=>{document.getElementById("appDialog").close();loadLoansData()}).catch(error=>toast(error.message,"error"));return}confirmLoanAction("Taksiti \u00d6dendi Olarak \u0130\u015faretle","<p>Bu taksiti \u00f6dendi olarak i\u015faretlemek istiyor musunuz?</p>","Evet, \u00d6dendi \u0130\u015faretle",async()=>{await apiFetch(`/api/desktop/loan-installments/${item.id}/status`,{method:"POST",body:JSON.stringify({status:"\u00d6dendi"})});await loadLoansData()})});document.getElementById("loanDetails")?.addEventListener("click",()=>{openDialog("Kredi S\u00f6zle\u015fmesi","KRED\u0130 DETAYI",`<div class="form-grid"><div class="field"><label>Banka</label><strong>${esc(loan.bank_name||"")}</strong></div><div class="field"><label>Kredi Tutari</label><strong>${loanMoney(loan.amount??loan.principal_amount)}</strong></div><div class="field"><label>Faiz Orani</label><strong>%${esc(loan.interest_rate||0)}</strong></div><div class="field"><label>Kalan Borc</label><strong>${loanMoney(remaining)}</strong></div></div>`,()=>true,"Kapat")})}
  async function loadAllLoanTableRows(table){const limit=1000,first=await apiFetch(`/api/desktop/table/${table}?limit=${limit}&offset=0`),offsets=[];for(let offset=limit;offset<Number(first.count||0);offset+=limit)offsets.push(offset);const rest=await Promise.all(offsets.map(offset=>apiFetch(`/api/desktop/table/${table}?limit=${limit}&offset=${offset}`)));return[...(first.rows||[]),...rest.flatMap(result=>result.rows||[])]}
  async function loadLoansData(){const [loans,installments]=await Promise.all([loadAllLoanTableRows("loans"),loadAllLoanTableRows("loan_installments")]);loanRows=loans;installmentRows=installments;drawLoans()}
  function openBulkLoanPayment(loan){
    const unpaid=installmentRows.filter(item=>String(item.loan_id)===String(loan.id)&&!installmentIsPaid(item));
    const rows=unpaid.map(item=>`<tr><td><input type="checkbox" name="installment_ids" value="${esc(item.id)}"></td><td>${esc(item.installment_no)}</td><td>${loanMoney(item.total_amount??item.amount)}</td><td>${loanDate(item.due_date)}</td><td>${esc(item.status||"Bekliyor")}</td></tr>`).join("");
    const body=`<p class="muted">${esc(loan.bank_name||"Banka")} - \u00d6demek istedi\u011Finiz taksitleri se\u00e7in.</p><div class="table-wrap"><table><thead><tr><th>Se\u00e7</th><th>Taksit No</th><th>Tutar</th><th>Vade Tarihi</th><th>Durum</th></tr></thead><tbody>${rows||'<tr><td colspan="5">T\u00fcm taksitler \u00f6denmi\u015f</td></tr>'}</tbody></table></div><p class="muted" id="loanPaymentSummary"></p><div class="loan-bulk-actions"><button type="button" class="secondary" id="loanSelectAll" ${unpaid.length?"":"disabled"}>T\u00fcm\u00fcn\u00fc Se\u00e7</button><button type="button" class="secondary" id="loanEarlyClose">Erken Kapat</button><button type="button" class="secondary" id="loanPayAll" ${unpaid.length?"":"disabled"}>T\u00fcm\u00fcn\u00fc \u00d6de</button></div>`;
    openDialog("Toplu \u00d6deme", "KRED\u0130 TAKS\u0130TLER\u0130", body, async form=>{
      const ids=form.getAll("installment_ids");
      if(!ids.length){toast("L\u00fctfen en az bir taksit se\u00e7in.","warning");return false;}
      let paidCount=0;
      for(const id of ids){try{await apiFetch(`/api/desktop/loan-installments/${encodeURIComponent(id)}/status`,{method:"POST",body:JSON.stringify({status:"\u00d6dendi"})});paidCount++}catch(error){toast(error.message||"\u00d6deme i\u015flemi ba\u015far\u0131s\u0131z oldu.","error")}}
      await loadLoansData();
      if(!paidCount)return false;
      toast(`${paidCount} taksit \u00f6dendi olarak i\u015faretlendi.`);
      return true;
    },"Se\u00e7ilenleri \u00d6de");
    const checkboxes=[...document.querySelectorAll('#dialogBody [name="installment_ids"]')];
    const summary=document.getElementById("loanPaymentSummary");
    const updateSummary=()=>{const selected=checkboxes.filter(input=>input.checked),amount=items=>items.reduce((sum,item)=>sum+Number(item.total_amount??item.amount??0),0);if(summary)summary.textContent=selected.length?`Se\u00e7ili: ${selected.length} Taksit - ${loanMoney(amount(selected.map(input=>unpaid.find(item=>String(item.id)===input.value)).filter(Boolean)))}`:`Toplam \u00f6denmemi\u015f: ${unpaid.length} Taksit - ${loanMoney(amount(unpaid))}`};
    checkboxes.forEach(input=>input.addEventListener("change",updateSummary));
    const selectAll=document.getElementById("loanSelectAll");
    if(selectAll)selectAll.onclick=()=>{checkboxes.forEach(input=>input.checked=true);updateSummary()};
    const payAll=document.getElementById("loanPayAll");
    if(payAll)payAll.onclick=()=>{checkboxes.forEach(input=>input.checked=true);document.getElementById("dialogForm").requestSubmit()};
    document.getElementById("loanEarlyClose")?.addEventListener("click",()=>{if(!unpaid.length){toast("T\u00fcm taksitler zaten \u00f6denmi\u015f.","warning");return}openEarlyLoanClosure(loan,unpaid)});
    updateSummary();
  }
  function openEarlyLoanClosure(loan,unpaid){
    const fields=unpaid.map(item=>({principal:Number(item.principal_part)||0,interest:Number(item.interest_part)||0,kkdf:Number(item.kkdf_amount)||0,bsmv:Number(item.bsmv_amount)||0,amount:Number(item.total_amount??item.amount)||0}));
    let principal=fields.reduce((sum,item)=>sum+item.principal,0),interest=fields.reduce((sum,item)=>sum+item.interest,0),kkdf=fields.reduce((sum,item)=>sum+item.kkdf,0),bsmv=fields.reduce((sum,item)=>sum+item.bsmv,0);
    if(!principal){const total=fields.reduce((sum,item)=>sum+item.amount,0);principal=total*.65;interest=total*.28;kkdf=interest*.15;bsmv=interest*.10}
    const body=`<section class="loan-early-closure"><div class="early-loan-summary"><strong>Erken Kredi Kapatma Hesaplamas\u0131</strong><span>${esc(loan.bank_name||"Kredi")}</span></div><div class="field"><label for="loanEarlyPenalty">Erken Kapatma Tazminat Oran\u0131</label><div class="loan-penalty-input"><input id="loanEarlyPenalty" type="number" min="0" max="5" step="1" value="0"><span>%</span></div></div><div class="table-wrap"><table><thead><tr><th>Kalem</th><th>Tutar</th></tr></thead><tbody id="loanEarlyBreakdown"></tbody></table></div><p class="loan-early-comparison" id="loanEarlyComparison"></p><p class="loan-early-note">Not: Erken kapatmada kalan ana para esas al\u0131n\u0131r; faiz ve vergilerden tasarruf hesaplan\u0131r.</p></section>`;
    openDialog("Kredi Erken Kapatma","KRED\u0130 ERKEN KAPATMA",body,async()=>{
      if(!unpaid.length)return false;
      try{await apiFetch(`/api/desktop/loans/${encodeURIComponent(loan.id)}/early-close`,{method:"POST",body:"{}"})}catch(error){toast(error.message||"Kredi erken kapat\u0131lamad\u0131.","error");await loadLoansData();return false}
      await loadLoansData();toast("Kredi erken kapat\u0131ld\u0131. Taksit ge\u00e7mi\u015fi korundu.");return true;
    },"Evet, Kapat");
    const renderBreakdown=()=>{
      const penalty=principal*(Math.max(0,Math.min(5,Number(document.getElementById("loanEarlyPenalty")?.value)||0))/100),tax=kkdf+bsmv,savings=interest+tax-penalty;
      const rows=[["Kapatmak \u0130\u00e7in Gereken (Ana Para)",principal,""],["",0,""],["\u00d6demekten Kurtuldu\u011Funuz Faiz",interest,"saving"],["\u00d6demekten Kurtuldu\u011Funuz Vergi (KKDF+BSMV)",tax,"saving"],...(penalty>0?[["Erken Kapatma Tazminat\u0131",penalty,"penalty"]]:[]),["",0,""],["TOPLAM KAZANCINIZ",savings,"total"]];
      document.getElementById("loanEarlyBreakdown").innerHTML=rows.map(([label,value,kind])=>`<tr class="${kind}"><td>${label}</td><td>${label?loanMoney(value):""}</td></tr>`).join("");
      const comparison=savings>500000?`Bu tasarrufla tam ${Math.floor(savings/500000)} adet sifir arac pesinati odeyebilirdiniz!`:savings>95000?`Tam ${Math.floor(savings/95000)} adet son model akilli telefon bedavaya geldi!`:savings>45000?`Teknik servisiniz icin ${Math.floor(savings/45000)} adet yuksek performansli laptop alabilirdiniz!`:"Onemli bir faiz yukunden kurtuldunuz!";
      const comparisonNode=document.getElementById("loanEarlyComparison");if(comparisonNode)comparisonNode.textContent=`AYEC Pro Finansal Zekasi: ${comparison}`;
    };
    document.getElementById("loanEarlyPenalty")?.addEventListener("input",renderBreakdown);renderBreakdown();
  }
  function confirmLoanAction(title, message, submitLabel, action, destructive=false){
    openDialog(title,"KRED\u0130 VE TAKS\u0130TLER",message,async()=>{
      try{await action();return true}
      catch(error){toast(error.message||"\u0130\u015flem tamamlanamad\u0131.","error");return false}
    },submitLabel);
    document.querySelector("#dialogCancel").textContent="Hay\u0131r";
    if(destructive){document.querySelector("#dialogSubmit").classList.remove("primary");document.querySelector("#dialogSubmit").classList.add("danger")}
  }
  document.addEventListener("contextmenu",event=>{
    if(page!=="loans")return;
    if(!ayecContextMenuEnabled()){document.getElementById("contextMenu")?.classList.remove("open");return}
    const loanNode=event.target.closest("[data-loan-context-row]");
    const installmentNode=event.target.closest("[data-installment-row]");
    if(!loanNode&&!installmentNode)return;
    event.preventDefault();
    const menu=document.getElementById("contextMenu");if(!menu)return;
    if(loanNode){
      menu.dataset.loanContextType="loan";menu.dataset.loanContextId=loanNode.dataset.loanContextRow;
      menu.innerHTML='<button type="button" data-loan-context-action="edit">Krediyi D\u00fczenle</button><button type="button" data-loan-context-action="bulk">Toplu \u00d6deme Yap</button><button type="button" data-loan-context-action="details">Detaylar</button><button type="button" data-loan-context-action="add-installment">Taksit Ekle</button><hr><button type="button" data-loan-context-action="cancel">Krediyi \u0130ptal Et</button><button type="button" data-loan-context-action="delete">Krediyi Sil</button>';
    }else{
      const installment=installmentRows.find(item=>String(item.id)===String(installmentNode.dataset.installmentRow));if(!installment)return;
      menu.dataset.loanContextType="installment";menu.dataset.loanContextId=String(installment.id);menu.dataset.loanContextLoanId=String(installment.loan_id);
      const paid=installmentIsPaid(installment);
      menu.innerHTML=(paid?'<button type="button" data-loan-context-action="unpay">\u00d6deme Durumunu Geri Al</button>':'<button type="button" data-loan-context-action="pay">Taksiti \u00d6dendi Olarak \u0130\u015faretle</button>')+'<button type="button" data-loan-context-action="details">Kredi Detaylar\u0131</button>';
    }
    menu.style.left=Math.max(8,Math.min(event.clientX,innerWidth-230))+"px";
    menu.style.top=Math.max(8,Math.min(event.clientY,innerHeight-menu.querySelectorAll("button").length*40-20))+"px";
    menu.classList.add("open");
  });
  document.addEventListener("click",async event=>{
    const button=event.target.closest("[data-loan-context-action]");if(!button||page!=="loans")return;
    event.preventDefault();const menu=document.getElementById("contextMenu"),action=button.dataset.loanContextAction,type=menu.dataset.loanContextType,id=menu.dataset.loanContextId;menu.classList.remove("open");
    if(type==="loan"){
      const loan=loanRows.find(item=>String(item.id)===String(id));if(!loan)return;
      if(action==="edit"){const data=await apiFetch("/api/desktop/table/loans?limit=1");openGenericDialog({title:"Kredi",table:"loans"},loan,data.columns);return;}
      if(action==="bulk"){openBulkLoanPayment(loan);return;}
      if(action==="details"){selectedLoanId=loan.id;drawLoans();document.getElementById("loanDetails")?.click();return;}
      if(action==="add-installment"){toast("Taksit ekleme \u00e7ok yak\u0131nda.","warning");return;}
      if(action==="cancel"){
        if(String(loan.status||"").trim()==="\u0130ptal")return toast("Bu kredi zaten iptal edilmi\u015f.","warning");
        confirmLoanAction("Krediyi \u0130ptal Et",`<p><strong>${esc(loan.bank_name||"Kredi")}</strong> kredisini iptal etmek istiyor musunuz?</p><p>Taksit kay\u0131tlar\u0131 silinmeyecektir.</p>`,"Evet, \u0130ptal Et",async()=>{
          await apiFetch("/api/desktop/table/loans",{method:"POST",body:JSON.stringify({id:loan.id,_action:"update",status:"\u0130ptal"})});
          toast("Kredi iptal edildi. Taksit ge\u00e7mi\u015fi korundu.");
          await loadLoansData();
        },true);
        return;
      }
      if(action==="delete"){
        confirmLoanAction("Krediyi Sil",`<p><strong>${esc(loan.bank_name||"Kredi")}</strong> kredisini ve t\u00fcm taksitlerini silmek istiyor musunuz?</p><p>Bu i\u015flem geri al\u0131namaz.</p>`,"Evet, Sil",async()=>{
          await apiFetch("/api/desktop/table/loans",{method:"POST",body:JSON.stringify({id:loan.id,_action:"delete"})});
          toast("Kredi silindi.");
          await loadLoansData();
        },true);
        return;
      }
    }
    const installment=installmentRows.find(item=>String(item.id)===String(id));if(!installment)return;
    if(action==="pay"){
      confirmLoanAction("Taksiti \u00d6dendi Olarak \u0130\u015faretle","<p>Bu taksiti \u00f6dendi olarak i\u015faretlemek istiyor musunuz?</p>","Evet, \u00d6dendi \u0130\u015faretle",async()=>{
        await apiFetch(`/api/desktop/loan-installments/${encodeURIComponent(id)}/status`,{method:"POST",body:JSON.stringify({status:"\u00d6dendi"})});
        await loadLoansData();
      });
      return;
    }
    if(action==="unpay"){
      await apiFetch(`/api/desktop/loan-installments/${encodeURIComponent(id)}/status`,{method:"POST",body:JSON.stringify({status:"Bekliyor"})});await loadLoansData();return;
    }
    if(action==="details"){
      selectedLoanId=installment.loan_id;drawLoans();document.getElementById("loanDetails")?.click();
    }
  });
  const previousRender=render;render=function(){if(page!=="loans")return previousRender();const nav=document.getElementById("nav"),scroll=nav?.scrollTop||0;document.body.dataset.page=page;document.getElementById("content").innerHTML=loansView();bindPage();document.getElementById("loanSearch").oninput=event=>{loanQuery=event.target.value;selectedLoanId=null;loanPage=1;drawLoans()};document.getElementById("loanSelect").onchange=event=>{selectedLoanId=event.target.value;loanPage=1;drawLoans()};document.querySelectorAll("[data-loan-filter]").forEach(button=>button.onclick=()=>{loanFilter=button.dataset.loanFilter;selectedLoanId=null;loanPage=1;document.querySelectorAll("[data-loan-filter]").forEach(item=>item.classList.toggle("active",item===button));drawLoans()});document.querySelectorAll("[data-loan-currency]").forEach(button=>button.onclick=()=>{loanCurrency=button.dataset.loanCurrency;document.querySelectorAll("[data-loan-currency]").forEach(item=>item.classList.toggle("active",item===button));drawLoans()});document.getElementById("loanPrev").onclick=()=>{loanPage--;drawLoans()};document.getElementById("loanNext").onclick=()=>{loanPage++;drawLoans()};document.getElementById("loansRefresh").onclick=loadLoansData;document.getElementById("loanCreate").onclick=openAdvancedLoanWizardManifestDialog;document.getElementById("loanExport").onclick=()=>{const rows=filteredLoans().flatMap(loan=>installmentRows.filter(item=>String(item.loan_id)===String(loan.id)).map(item=>({bank:loan.bank_name,loan_id:loan.id,installment:item.installment_no,due_date:item.due_date,amount:loanMoney(item.amount??item.total_amount),status:item.status,paid_date:item.paid_date||"",receipt:item.receipt_number||""})));download("kredi-taksit-plani.csv",csv(rows))};document.getElementById("loanPrint").onclick=printLoanSchedule;if(nav)nav.scrollTop=scroll;loadLoansData().catch(error=>toast(error.message,"error"))};
})();
