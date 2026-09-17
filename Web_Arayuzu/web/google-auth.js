/* Google Identity Services; credentials are verified by the AYEC server. */
(() => {
 let sdk;
 function loadSdk(){
  if(window.google?.accounts?.id)return Promise.resolve();
  if(!sdk)sdk=new Promise((resolve,reject)=>{
   const script=document.createElement("script");
   script.src="https://accounts.google.com/gsi/client";
   script.async=true;script.onload=resolve;
   script.onerror=()=>{sdk=null;script.remove();reject(new Error("Google baglantisi yuklenemedi."))};
   document.head.append(script);
  });
  return sdk;
 }
 async function attachGoogle(mode){
  const form=document.getElementById(mode==="register"?"registerForm":"loginForm");
  if(!form || form.dataset.googleAttached)return;
  form.dataset.googleAttached="1";
  try{
   const config=await apiFetch("/api/auth/google/config");
   if(!config.enabled || !form.isConnected)return;
   await loadSdk();
   if(!form.isConnected)return;
   const box=document.createElement("div");box.className="auth-google";
   box.style.cssText="margin:20px 0;display:grid;justify-items:center;gap:12px";
   const note=document.createElement("small");
   note.textContent=mode==="register"?"Firma, sekt\u00f6r ve kullan\u0131c\u0131 ad\u0131n\u0131 girip Google ile kaydolun.":"veya Google hesab\u0131n\u0131zla devam edin";
   const button=document.createElement("div");box.append(note,button);form.after(box);
   let credential="";
   const submit=async()=>{
    const values=Object.fromEntries(new FormData(form));
    if(mode==="register"){
     const required=[form.elements.company_name,form.elements.sector,form.elements.username];
     const invalid=required.find(field=>!field?.checkValidity());
     if(invalid){invalid.reportValidity();return}
    }
    setAuthBusy(form,true,"Google hesab\u0131 do\u011frulan\u0131yor...");
    try{
     const result=await apiFetch("/api/auth/google",{method:"POST",body:JSON.stringify({...values,mode,credential})});
     updateCurrentUser(result.user);hideAuth();await startApplication();
     if(result.created && !result.mail_sent)toast(result.mail_message||"Hesap olu\u015fturuldu; e-posta g\u00f6nderilemedi.","warning");
    }catch(error){toast(error.message,"error");box.remove();delete form.dataset.googleAttached;attachGoogle(mode)}
    finally{setAuthBusy(form,false)}
   };
   const oldSubmit=form.onsubmit;
   form.onsubmit=event=>{if(!credential)return oldSubmit?.(event);event.preventDefault();submit()};
   google.accounts.id.initialize({client_id:config.client_id,nonce:config.nonce,auto_select:false,callback:response=>{
    credential=response.credential;
    if(mode==="register"){
     try{
      const part=credential.split(".")[1].replace(/-/g,"+").replace(/_/g,"/");
      const bytes=Uint8Array.from(atob(part),char=>char.charCodeAt(0));
      const display=JSON.parse(new TextDecoder().decode(bytes));
      if(form.elements.email)form.elements.email.value=display.email||"";
      if(form.elements.full_name && !form.elements.full_name.value)form.elements.full_name.value=display.name||"";
     }catch{}
    }
    submit();
   }});
   google.accounts.id.renderButton(button,{type:"standard",theme:"outline",size:"large",text:mode==="register"?"signup_with":"signin_with",locale:"tr",width:280});
  }catch(error){console.warn("Google sign-in could not be loaded.")}
 }
 const login=renderLogin;
 renderLogin=function(...args){login(...args);attachGoogle("login")};
 const register=renderRegistration;
 renderRegistration=function(...args){register(...args);attachGoogle("register")};
 if(document.getElementById("loginForm"))attachGoogle("login");
 if(document.getElementById("registerForm"))attachGoogle("register");
})();
