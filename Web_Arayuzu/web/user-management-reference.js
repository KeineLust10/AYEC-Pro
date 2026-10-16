function ayecNewManagedUserDialog(){
  let allowed=defaultUserPermissionPages("Teknisyen");
  const roles=[["Teknisyen","Teknisyen"],["Muhasebe","Muhasebe"],["Sat\u0131\u015f","Sat\u0131\u015f"],["Y\u00f6netici","Y\u00f6netici"],["Admin","Admin"],["Di\u011fer","Di\u011fer"]];
  const departments=["IT","\u0130nsan Kaynaklar\u0131","Finans","Pazarlama","Teknik Servis","Genel"];
  const form=`<div class="form-grid"><div class="field full"><label>Ad Soyad *</label><input name="full_name" maxlength="60" required></div><div class="field"><label>Kullan\u0131c\u0131 Ad\u0131 *</label><input name="username" maxlength="40" minlength="3" autocomplete="off" required></div><div class="field"><label>Ba\u015flang\u0131\u00e7 \u015eifresi *</label><input name="password" type="password" minlength="10" autocomplete="new-password" required><small class="muted">En az 10 karakter; b\u00fcy\u00fck/k\u00fc\u00e7\u00fck harf ve rakam gerekir.</small></div><div class="field"><label>E-posta</label><input name="email" type="email" maxlength="254"></div><div class="field"><label>Telefon</label><input name="phone" type="tel" placeholder="+90 5XX XXX XX XX"></div><div class="field"><label>Rol / G\u00f6rev *</label><select name="role">${roles.map(([value,label])=>`<option value="${esc(value)}">${esc(label)}</option>`).join("")}</select></div><div class="field"><label>Departman</label><select name="department">${departments.map(value=>`<option>${esc(value)}</option>`).join("")}</select></div><div class="field"><label>Hesap Durumu</label><select name="active"><option value="1">Aktif</option><option value="0">Pasif</option></select></div><section class="field full settings-user-edit-matrix"><header><strong>Varsay\u0131lan Yetki Matrisi</strong><small id="newUserPermissionCount"></small></header><div id="newUserPermissions">${renderUserPermissionMatrix(allowed,true)}</div></section></div>`;
  openDialog("Yeni Kullan\u0131c\u0131 Ekle","KULLANICI Y\u00d6NET\u0130M\u0130",form,async fd=>{
    const role=String(fd.get("role")||"Teknisyen"),pages=[...document.querySelectorAll("#newUserPermissions [data-user-permission]:checked")].map(input=>Number(input.dataset.userPermission));
    const payload=Object.fromEntries(fd);payload.permissions=JSON.stringify(userAdminRole(role)?{mode:"all"}:{pages});
    await apiFetch("/api/desktop/users",{method:"POST",body:JSON.stringify(payload)});
    toast("Kullan\u0131c\u0131 ve personel kayd\u0131 olu\u015fturuldu.","success");await loadSettingsUsers();
  },"Kullan\u0131c\u0131y\u0131 Ekle");
  const roleField=document.querySelector("#dialogBody [name=role]");
  const updatePermissions=()=>{const role=roleField.value;allowed=defaultUserPermissionPages(role);document.querySelectorAll("#newUserPermissions [data-user-permission]").forEach(input=>{input.checked=allowed.has(Number(input.dataset.userPermission));input.disabled=userAdminRole(role)});const count=document.getElementById("newUserPermissionCount");if(count)count.textContent=`${allowed.size} / ${ayecUserPermissionSections.reduce((sum,[,items])=>sum+items.length,0)} sayfa`;};
  roleField.onchange=updatePermissions;document.querySelectorAll("#newUserPermissions [data-user-permission]").forEach(input=>input.onchange=()=>{allowed=new Set([...document.querySelectorAll("#newUserPermissions [data-user-permission]:checked")].map(item=>Number(item.dataset.userPermission)));const count=document.getElementById("newUserPermissionCount");if(count)count.textContent=`${allowed.size} / ${ayecUserPermissionSections.reduce((sum,[,items])=>sum+items.length,0)} sayfa`;});updatePermissions();
}
settingsUserDialog=async function(user){
  let personnel=[];
  try{personnel=(await apiFetch("/api/desktop/table/personnel?limit=1000")).rows||[]}catch(error){toast("Personel listesi y\u00fcklenemedi: "+error.message,"warning")}
  const roleChoices=[...new Set(["Master","Admin","Teknisyen","Muhasebe","Personel","Sat\u0131\u015f","Di\u011fer",user.role].filter(Boolean))];
  let allowed=userPermissionPages(user.permissions,user.role);
  const roles=roleChoices.map(role=>`<option value="${esc(role)}" ${String(user.role||"")===role?"selected":""}>${esc(role)}</option>`).join("");
  const personnelOptions=`<option value="">Atanmad\u0131</option>${personnel.map(item=>`<option value="${esc(item.id)}" ${String(item.id)===String(user.personnel_id||"")?"selected":""}>${esc(item.name||item.full_name||item.id)}</option>`).join("")}`;
  const body=`<div class="form-grid settings-user-desktop-edit"><div class="field"><label>Kullan\u0131c\u0131 Ad\u0131 *</label><input name="username" maxlength="40" minlength="3" required autocomplete="username" value="${esc(user.username||"")}"></div><div class="field"><label>Ad Soyad</label><input name="full_name" maxlength="60" value="${esc(user.full_name||user.username||"")}"></div><div class="field"><label>E-posta</label><input name="email" type="email" maxlength="254" value="${esc(user.email||"")}"></div><div class="field"><label>Telefon</label><input name="phone" type="tel" value="${esc(user.phone||"")}" placeholder="+90 5XX XXX XX XX"></div><div class="field"><label>Rol</label><select name="role">${roles}</select></div><div class="field"><label>Personel</label><select name="personnel_id">${personnelOptions}</select></div><div class="field"><label>Hesap durumu</label><select name="active"><option value="1" ${Number(user.active??1)!==0?"selected":""}>Aktif</option><option value="0" ${Number(user.active??1)===0?"selected":""}>Pasif</option></select></div><label class="settings-user-auto-login"><input name="auto_login" type="checkbox" ${Number(user.auto_login??0)!==0?"checked":""}>Otomatik Giri\u015f \u0130zni</label><div class="field full"><label>Yeni Parola</label><input name="password" type="password" minlength="10" autocomplete="new-password" placeholder="Bo\u015f b\u0131rak\u0131rsan\u0131z de\u011fi\u015fmez"><small class="muted">Masa\u00fcst\u00fc parola g\u00fcvenlik kurallar\u0131 uygulan\u0131r.</small></div><div class="field"><label>Yeni Gizli Soru</label><input name="secret_question" maxlength="250" placeholder="De\u011fi\u015ftirmek istemiyorsan\u0131z bo\u015f b\u0131rak\u0131n"></div><div class="field"><label>Yeni Gizli Yan\u0131t</label><input name="secret_answer" type="password" maxlength="250" autocomplete="off" placeholder="Gizli yan\u0131t g\u00f6sterilmez"></div><div class="field"><label>Aray\u00fcz D\u00fczenleme</label><select name="interface_edit_access"><option value="1" ${user.interface_edit_access?"selected":""}>A\u00e7\u0131k</option><option value="0" ${!user.interface_edit_access?"selected":""}>Kapal\u0131</option></select></div><section class="field full settings-user-edit-matrix"><header><strong>\u0130nce Ayarl\u0131 Yetki Matrisi</strong><small id="managedUserPermissionCount"></small></header><div id="managedUserPermissions">${renderUserPermissionMatrix(allowed,true)}</div></section></div>`;
  openDialog(`${esc(user.username||"Kullan\u0131c\u0131")} \u2014 Yetkiler`,"KULLANICI Y\u00d6NET\u0130M\u0130",body,async fd=>{
    const payload=Object.fromEntries(fd),role=String(fd.get("role")||user.role||"Teknisyen");
    payload.user_id=user.id;payload.permissions=JSON.stringify(userAdminRole(role)?{mode:"all"}:{pages:[...document.querySelectorAll("#managedUserPermissions [data-user-permission]:checked")].map(input=>Number(input.dataset.userPermission))});
    payload.auto_login=fd.has("auto_login")?1:0;payload.personnel_id=payload.personnel_id||null;
    if(!payload.password)delete payload.password;
    await apiFetch("/api/desktop/users/update",{method:"POST",body:JSON.stringify(payload)});
    toast("Kullan\u0131c\u0131 hesab\u0131 g\u00fcncellendi.","success");await loadSettingsUsers();return true;
  },"De\u011fi\u015fiklikleri Kaydet");
  const roleField=document.querySelector("#dialogBody [name=role]"),permissionCount=document.getElementById("managedUserPermissionCount");
  const updatePermissionCount=()=>{const count=document.querySelectorAll("#managedUserPermissions [data-user-permission]:checked").length;if(permissionCount)permissionCount.textContent=`${count} / ${ayecUserPermissionSections.reduce((sum,[,items])=>sum+items.length,0)} sayfa`;};
  roleField.onchange=()=>{allowed=defaultUserPermissionPages(roleField.value);document.querySelectorAll("#managedUserPermissions [data-user-permission]").forEach(input=>{input.checked=allowed.has(Number(input.dataset.userPermission));input.disabled=userAdminRole(roleField.value)});updatePermissionCount()};
  document.querySelectorAll("#managedUserPermissions [data-user-permission]").forEach(input=>{input.disabled=userAdminRole(user.role);input.onchange=updatePermissionCount});updatePermissionCount();
};
function ayecAttachUserCreateAction(){
  const host=document.getElementById("settingsUsersHost"),header=host?.previousElementSibling;
  if(!host||!header||settingsSection!=="users"||!userAdminRole(currentAuthUser?.role)||header.querySelector("[data-managed-user-create]"))return;
  const button=document.createElement("button");button.type="button";button.className="primary";button.dataset.managedUserCreate="1";button.textContent="+ Yeni Kullan\u0131c\u0131 Ekle";button.onclick=ayecNewManagedUserDialog;header.append(button);
}
function ayecBulkPasswordsDialog(){
  const eligible=ayecSettingsUsers.filter(user=>String(user.id)!==String(currentAuthUser?.id)&&!userAdminRole(user.role));
  const body=`<p class="muted">Her se\u00e7ili hesap i\u00e7in farkl\u0131 ve g\u00fc\u00e7l\u00fc bir parola girin. Eski parolalar ve hat\u0131rlanan giri\u015f belirte\u00e7leri ge\u00e7ersiz olur; a\u00e7\u0131k oturumlar kapanmaz. Y\u00f6netici ve Master hesaplar\u0131 bu toplu i\u015flemin d\u0131\u015f\u0131ndad\u0131r.</p><button type="button" class="secondary" data-bulk-password-select>Uygun Hesaplar\u0131 Se\u00e7</button><div class="table-wrap"><table class="data-table"><thead><tr><th>Se\u00e7</th><th>Kullan\u0131c\u0131</th><th>Personel</th><th>Rol</th><th>Hesap</th><th>Yeni Parola</th></tr></thead><tbody>${ayecSettingsUsers.map(user=>{const locked=String(user.id)===String(currentAuthUser?.id)||userAdminRole(user.role);const id=esc(user.id);return `<tr><td><input type="checkbox" name="bulk_user_${id}" data-bulk-password-user="${id}" ${locked?"disabled":""} aria-label="Hesab\u0131 se\u00e7: ${esc(user.username)}"></td><td>${esc(user.username||"-")}</td><td>${esc(user.full_name||user.name||"-")}</td><td>${esc(user.role||"-")}</td><td>${Number(user.active??1)?"Aktif":"Pasif"}</td><td><input type="password" name="bulk_password_${id}" data-bulk-password-field="${id}" autocomplete="new-password" minlength="10" placeholder="En az 10 karakter" ${locked?"disabled":""} aria-label="Yeni parola: ${esc(user.username)}"></td></tr>`}).join("")||`<tr><td colspan="6">Kullan\u0131c\u0131 kayd\u0131 bulunamad\u0131.</td></tr>`}</tbody></table></div><p class="muted" id="bulkPasswordSelectionCount">0 hesap se\u00e7ildi</p>`;
  openDialog("Toplu Parola De\u011fi\u015ftirme","KULLANICI G\u00dcVENL\u0130\u011e\u0130",body,async()=>{
    const changes=eligible.filter(user=>document.querySelector(`[data-bulk-password-user="${CSS.escape(String(user.id))}"]`)?.checked).map(user=>({user_id:user.id,password:document.querySelector(`[data-bulk-password-field="${CSS.escape(String(user.id))}"]`)?.value||""}));
    if(!changes.length)throw Error("En az bir uygun hesap se\u00e7in.");
    if(changes.some(item=>!item.password))throw Error("Se\u00e7ili her hesap i\u00e7in yeni parola girin.");
    if(new Set(changes.map(item=>item.password)).size!==changes.length)throw Error("Her hesap i\u00e7in farkl\u0131 bir parola girin.");
    let confirmation=document.querySelector("[data-bulk-password-confirm]");
    if(!confirmation){
      const prompt=document.createElement("div");
      prompt.className="field full";
      prompt.innerHTML=`<label><input type="checkbox" data-bulk-password-confirm> ${changes.length} hesab\u0131n parolas\u0131 de\u011fi\u015fecek. Kay\u0131tl\u0131 giri\u015f belirte\u00e7leri iptal edilecek; a\u00e7\u0131k oturumlar kapanmayacak. Onayl\u0131yorum.</label>`;
      const dialogBody=document.querySelector("#dialogBody");
      dialogBody.append(prompt);
      confirmation=prompt.querySelector("[data-bulk-password-confirm]");
      const resetConfirmation=event=>{if(event.target.matches("[data-bulk-password-user], [data-bulk-password-field]"))confirmation.checked=false};
      dialogBody.addEventListener("input",resetConfirmation);
      dialogBody.addEventListener("change",resetConfirmation);
      document.querySelector("#dialogSubmit").dataset.label="Evet, De\u011fi\u015ftir";
      return false;
    }
    if(!confirmation.checked)throw Error("Parola de\u011fi\u015fikli\u011fini onaylay\u0131n.");
    const result=await apiFetch("/api/desktop/users/bulk-passwords",{method:"POST",body:JSON.stringify({changes})});toast(`${result.changed} yerel hesap parolas\u0131 g\u00fcncellendi.`,"success");await loadSettingsUsers();return true;
  },"Se\u00e7ili Parolalar\u0131 De\u011fi\u015ftir");
  const select=document.querySelector("[data-bulk-password-select]"),checkboxes=[...document.querySelectorAll("[data-bulk-password-user]:not(:disabled)")],count=document.getElementById("bulkPasswordSelectionCount");
  select.onclick=()=>checkboxes.forEach(input=>{input.checked=true;input.dispatchEvent(new Event("change",{bubbles:true}))});
  const update=()=>{const selected=checkboxes.filter(input=>input.checked).length;if(count)count.textContent=`${selected} hesap se\u00e7ildi`;checkboxes.forEach(input=>{const password=document.querySelector(`[data-bulk-password-field="${CSS.escape(input.dataset.bulkPasswordUser)}"]`);if(password)password.disabled=!input.checked})};
  checkboxes.forEach(input=>input.addEventListener("change",update));update();
}
function ayecAttachBulkPasswordAction(){
  const host=document.getElementById("settingsUsersHost"),header=host?.previousElementSibling;
  if(!host||!header||settingsSection!=="users"||!userAdminRole(currentAuthUser?.role)||header.querySelector("[data-managed-user-bulk-password]"))return;
  const button=document.createElement("button");button.type="button";button.className="secondary";button.dataset.managedUserBulkPassword="1";button.textContent="Toplu Parola S\u0131f\u0131rla";button.onclick=ayecBulkPasswordsDialog;header.append(button);
}
function ayecOpenUserSecurityReport(){
  if(!userAdminRole(currentAuthUser?.role))return;
  auditReferenceState.offset=0;auditReferenceState.paused=false;
  const dialog=document.getElementById("appDialog");dialog.classList.add("audit-report-dialog");
  dialog.addEventListener("close",()=>dialog.classList.remove("audit-report-dialog"),{once:true});
  openDialog("G\u00fcvenlik Raporu / Audit Log","KULLANICI G\u00dcVENL\u0130\u011e\u0130",renderAuditReference(),()=>true,"Kapat");
  bindAuditReference();loadAuditReference();
}
function ayecAttachUserSecurityReportAction(){
  const host=document.getElementById("settingsUsersHost"),header=host?.previousElementSibling;
  if(!host||!header||settingsSection!=="users"||!userAdminRole(currentAuthUser?.role)||header.querySelector("[data-managed-user-security-report]"))return;
  const button=document.createElement("button");button.type="button";button.className="secondary";button.dataset.managedUserSecurityReport="1";button.textContent="G\u00fcvenlik Raporu";button.onclick=ayecOpenUserSecurityReport;header.append(button);
}
const ayecRenderSettingsBeforeUserSection=renderSettings;
renderSettings=function(){document.body.dataset.settingsSection=settingsSection;return ayecRenderSettingsBeforeUserSection()};
async function ayecDeleteManagedUser(userId){
  const target=ayecSettingsUsers.find(user=>String(user.id)===String(userId));
  if(!target||!userAdminRole(currentAuthUser?.role)||String(target.id)===String(currentAuthUser?.id))return;
  openDialog("Kullan\u0131c\u0131y\u0131 Sil","KULLANICI Y\u00d6NET\u0130M\u0130",`<p><strong>${esc(target.username||"")}</strong> hesab\u0131 silinecek veya devre d\u0131\u015f\u0131 b\u0131rak\u0131lacak. Devam edilsin mi?</p>`,async()=>{
    try{await apiFetch("/api/desktop/users/delete",{method:"POST",body:JSON.stringify({user_id:target.id})});toast("Kullan\u0131c\u0131 kayd\u0131 silindi.","success");await loadSettingsUsers();return true}
    catch(error){toast("Kullan\u0131c\u0131 silinemedi: "+error.message,"error");return false}
  },"Evet, Sil");
  document.querySelector("#dialogCancel").textContent="Hay\u0131r";
  document.querySelector("#dialogSubmit").classList.remove("primary");
  document.querySelector("#dialogSubmit").classList.add("danger");
}
function ayecAttachUserDeleteAction(){
  const profile=document.querySelector(".settings-users-profile"),header=profile?.querySelector("header"),edit=profile?.querySelector("[data-settings-user-edit]");
  if(!profile||!header||!edit||settingsSection!=="users"||!userAdminRole(currentAuthUser?.role)||header.querySelector("[data-managed-user-delete]"))return;
  if(String(edit.dataset.settingsUserEdit)===String(currentAuthUser?.id))return;
  const button=document.createElement("button");button.type="button";button.className="danger";button.dataset.managedUserDelete=edit.dataset.settingsUserEdit;button.textContent="Kullan\u0131c\u0131y\u0131 Sil";button.onclick=()=>ayecDeleteManagedUser(button.dataset.managedUserDelete);header.append(button);
}
const ayecShowContextBeforeManagedUser=showContext;
showContext=function(event,kind,id){
  if(kind!=="settings-user")return ayecShowContextBeforeManagedUser(event,kind,id);
  if(!ayecContextMenuEnabled())return;
  const user=ayecSettingsUsers.find(item=>String(item.id)===String(id));if(!user)return;
  event.preventDefault();const menu=document.querySelector("#contextMenu");
  const items=[["\u270f\ufe0f D\u00fczenle","managed-user-edit"],["\u{1f5d1}\ufe0f Sil","managed-user-delete"]];
  menu.innerHTML=items.map(([label,action])=>`<button type="button" role="menuitem" data-context-action="${action}">${label}</button>`).join("");
  menu.style.left=Math.max(8,Math.min(event.clientX,innerWidth-220))+"px";
  menu.style.top=Math.max(8,Math.min(event.clientY,innerHeight-items.length*40-20))+"px";
  menu.classList.add("open");menu.querySelectorAll("[data-context-action]").forEach(button=>{
    button.onclick=()=>{menu.classList.remove("open");contextAction(kind,id,button.dataset.contextAction,event.currentTarget)};
  });
};
const ayecContextActionBeforeManagedUser=contextAction;
contextAction=function(kind,id,action,row){
  if(kind!=="settings-user")return ayecContextActionBeforeManagedUser(kind,id,action,row);
  const user=ayecSettingsUsers.find(item=>String(item.id)===String(id));if(!user)return;
  if(action==="managed-user-edit")settingsUserDialog(user);
  if(action==="managed-user-delete")ayecDeleteManagedUser(user.id);
};
new MutationObserver(()=>{ayecAttachUserCreateAction();ayecAttachBulkPasswordAction();ayecAttachUserSecurityReportAction();ayecAttachUserDeleteAction()}).observe(document.body,{subtree:true,childList:true});
