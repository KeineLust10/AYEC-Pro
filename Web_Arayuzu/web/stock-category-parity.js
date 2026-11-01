const CATEGORY_BRAND_MAP = {"Motor Ya\u011f\u0131":["Castrol","Mobil","Motul","Shell","Elf","Liqui Moly","Petronas"],"Filtre":["Bosch","Mann","Mahle","Filtron","Sakura","Purflux"],"Fren Sistemi":["Bosch","TRW","Valeo","Ferodo","Brembo","ATE"],"S\u00fcspansiyon / Y\u00fcr\u00fcyen Aksam":["Monroe","Sachs","Lemforder","Febi","SKF"],"Elektrik / Elektronik":["Bosch","Valeo","Hella","Delphi","NGK","Denso"],"Ayd\u0131nlatma":["Osram","Philips","Hella","Valeo"],"Motor / Mekanik":["Gates","Dayco","INA","SKF","Contitech"],"Kaporta / Trim":["Valeo","Magneti Marelli","Depo"],"G\u00fcvenlik Sistemleri":["Hikvision","Dahua","Axis","Hanwha Vision","Bosch","Uniview","Tiandy","Vivotek","Avigilon","Pelco","Honeywell","Mobotix","TVT","HiLook","Ezviz","Milesight","Reolink","Provision-ISR"],"Bilgisayar Bile\u015fenleri":["ASUS","MSI","Gigabyte","ASRock","Intel","AMD","NVIDIA","Sapphire","PowerColor","Zotac","PNY","Palit","Gainward","Corsair","Kingston","Samsung","WD","Western Digital","Seagate","Crucial","G.Skill","TeamGroup","ADATA","Apacer","DeepCool","Cooler Master","Noctua","Arctic","Thermal Grizzly","Lian Li","NZXT","Thermaltake","be quiet!","Seasonic","FSP","SilverStone","InWin","Fractal Design","Phanteks","XPG"],"Ak\u0131ll\u0131 Ev Sistemleri":["WiiHOM","WiiPro","TP-Link","Ubiquiti","MikroTik","Ruijie","Mercusys","Tenda"],"A\u011f / Network":["TP-Link","Ubiquiti","MikroTik","Ruijie","Mercusys","Tenda"]};
const CATEGORY_KEYWORDS = {"Motor Ya\u011f\u0131":["5w30","5w40","10w40","motor ya\u011f\u0131","yag","ya\u011f","antifriz"],"Filtre":["ya\u011f filtresi","hava filtresi","polen filtresi","yak\u0131t filtresi","filtre"],"Fren Sistemi":["fren","balata","disk","kampana","hidrolik"],"S\u00fcspansiyon / Y\u00fcr\u00fcyen Aksam":["amortis\u00f6r","rot","sal\u0131ncak","z rot","bilya","rulman"],"Elektrik / Elektronik":["sens\u00f6r","sensor","mar\u015f","alternat\u00f6r","ak\u00fc","buji","bobin"],"Ayd\u0131nlatma":["far","stop","ampul","sis far\u0131","led"],"Motor / Mekanik":["triger","devirdaim","conta","supap","kay\u0131\u015f"],"\u015eanz\u0131man / Debriyaj":["debriyaj","bask\u0131","balata seti","\u015fanz\u0131man"],"So\u011futma Sistemi":["radyat\u00f6r","termostat","fan m\u00fc\u015f\u00fcr\u00fc","so\u011futma"],"Kaporta / Trim":["tampon","ayna","kap\u0131 kolu","\u0131zgara","\u00e7amurluk"],"Lastik / Jant":["lastik","jant","sibop"],"Sarf / Kimyasal":["sprey","temizleyici","katk\u0131","gres","kimyasal"],"G\u00fcvenlik Sistemleri":["kamera","nvr","dvr","ip kamera","g\u00fcvenlik","guvenlik","cctv","dedekt\u00f6r","dedektor","alarm","siren","poe","bullet","dome","ptz","interkom"],"Bilgisayar Bile\u015fenleri":["anakart","i\u015flemci","islemci","cpu","ram","ssd","hdd","ekran kart\u0131","gpu","psu","g\u00fc\u00e7 kayna\u011f\u0131","guc kaynagi","kasa","monit\u00f6r","monitor","klavye","mouse","thermal","termal","so\u011futucu","sogutucu","nvme"],"Ak\u0131ll\u0131 Ev Sistemleri":["ak\u0131ll\u0131","akilli","zigbee","gateway","hub","termostat","priz","r\u00f6le","role","perde","dimmer","ayd\u0131nlatma","aydinlatma","wiihom","wiipro"],"A\u011f / Network":["router","switch","modem","access point","eri\u015fim noktas\u0131","erisim noktasi","network","a\u011f","ag","ethernet","cat6","patch panel"],"Sarf Malzeme":["kablo ba\u011f\u0131","kablo bagi","temizlik","sprey","etiket","bant","vida","termal macun"],"Aksesuar":["adapt\u00f6r","adaptor","aparat","mount","braket","ask\u0131","aski","raf","stand"]};

function suggestStockCategory(form) {
  const field = form?.elements.namedItem("category");
  if (!field) return "";
  const value = name => String(form.elements.namedItem(name)?.value || "");
  const haystack = [value("name"), value("brand"), value("code"), value("description")].join(" ").toLowerCase();
  if (!haystack.trim()) return "";
  const scores = new Map();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    const score = keywords.reduce((total, keyword) => total + Number(haystack.includes(keyword.toLowerCase())), 0);
    if (score) scores.set(category, score);
  }
  for (const [category, brands] of Object.entries(CATEGORY_BRAND_MAP)) {
    const score = brands.reduce((total, brand) => total + 2 * Number(haystack.includes(brand.toLowerCase())), 0);
    if (score) scores.set(category, (scores.get(category) || 0) + score);
  }
  if (!scores.size) return "";
  let bestCategory = "", bestScore = -1;
  for (const [category, score] of scores) {
    if (score > bestScore) { bestCategory = category; bestScore = score; }
  }
  const current = String(field.value || "").trim();
  if (current && current !== "Genel" && current !== "Diğer" && (scores.get(current) || 0) >= bestScore) return bestCategory;
  if (field.tagName === "SELECT" && !Array.from(field.options).some(option => option.value === bestCategory)) {
    field.add(new Option(bestCategory, bestCategory));
  }
  field.value = bestCategory;
  field.dispatchEvent(new Event("change", { bubbles: true }));
  return bestCategory;
}

window.ayecSuggestStockCategory = suggestStockCategory;
document.addEventListener("focusout", event => {
  const field = event.target;
  if (field?.matches?.('#dialogForm input[name="name"], #dialogForm input[name="brand"], #dialogForm input[name="code"], #dialogForm textarea[name="description"]')) {
    suggestStockCategory(field.form);
  }
});
document.addEventListener("keydown", event => {
  const field = event.target;
  if (event.key !== "Enter" || !field?.matches?.('#dialogForm input[name="code"]')) return;
  event.preventDefault();
  event.stopPropagation();
  suggestStockCategory(field.form);
});
