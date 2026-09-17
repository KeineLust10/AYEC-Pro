
export default {
    props: ['customers', 'preselectedCustomer'],
    data() {
        return {
            step: 1,
            selectedCustomer: null,
            processDate: new Date().toISOString().split('T')[0],

            // Step 2 Data
            availableServices: [],
            searchService: '',
            selectedItems: [],
            loadingServices: false,

            // Step 1 Helper
            searchQuery: '',
            isDropdownOpen: false,

            // Save Logic
            isProcessing: false,
            isSuccess: false,
            createdTrackingNo: null
        }
    },
    template: `
    <div class="h-full flex flex-col items-center justify-center p-4 animate-fade-in bg-slate-100/50">
        
        <!-- WIZARD CONTAINER -->
        <div class="bg-white w-full max-w-6xl h-[700px] rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden">
            
            <!-- HEADER (Steps) -->
            <div class="bg-slate-50 border-b border-slate-200 px-6 py-4 flex justify-between items-center flex-shrink-0">
                <h3 class="font-bold text-slate-700 text-lg">Yeni İşlem Sihirbazı</h3>
                
                <!-- Step Indicators -->
                <div class="flex items-center gap-6">
                    <div class="flex items-center gap-2" :class="step >= 1 ? 'text-blue-600 font-bold' : 'text-slate-400'">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors" :class="step >= 1 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-slate-300'">1</div>
                        <span>Müşteri</span>
                    </div>
                    <div class="w-16 h-0.5 bg-slate-200"></div>
                     <div class="flex items-center gap-2" :class="step >= 2 ? 'text-blue-600 font-bold' : 'text-slate-400'">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors" :class="step >= 2 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-slate-300'">2</div>
                        <span>Hizmet & Ürün</span>
                    </div>
                    <div class="w-16 h-0.5 bg-slate-200"></div>
                     <div class="flex items-center gap-2" :class="step >= 3 ? 'text-blue-600 font-bold' : 'text-slate-400'">
                        <div class="w-8 h-8 rounded-full flex items-center justify-center border-2 transition-colors" :class="step >= 3 ? 'bg-blue-600 text-white border-blue-600' : 'bg-white border-slate-300'">3</div>
                        <span>Onay</span>
                    </div>
                </div>

                <button @click="$emit('close')" class="text-slate-400 hover:text-slate-600 p-2 rounded-full hover:bg-slate-200 transition"><i data-lucide="x" class="w-5 h-5"></i></button>
            </div>

            <!-- CONTENT BODY -->
            <div class="flex-1 relative bg-slate-50 overflow-hidden flex flex-col">
                
                <!-- STEP 1: MÜŞTERİ SEÇİMİ -->
                <div v-if="step === 1" class="h-full flex flex-col items-center justify-center space-y-8 animate-fade-in-up">
                    <div class="flex flex-col items-center">
                        <div class="w-20 h-20 bg-gradient-to-br from-slate-700 to-slate-900 rounded-2xl flex items-center justify-center mb-4 shadow-xl shadow-slate-300">
                            <i data-lucide="user-plus" class="w-10 h-10 text-white"></i>
                        </div>
                        <h2 class="text-3xl font-bold text-slate-800 tracking-tight">Müşteri Seçimi</h2>
                        <p class="text-slate-500 font-medium">İşlemin yapılacağı müşteriyi belirleyin</p>
                    </div>

                    <div class="bg-white p-8 rounded-2xl shadow-xl border border-slate-100 w-[500px] space-y-6 relative">
                        <!-- Müşteri Arama -->
                        <div>
                            <label class="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wide">MÜŞTERİ ARA / SEÇ</label>
                            <div class="relative group">
                                <input type="text" v-model="searchQuery" @focus="isDropdownOpen = true" @blur="closeDropdown" 
                                    class="w-full pl-11 pr-10 py-3.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:border-blue-500 focus:ring-4 focus:ring-blue-500/10 outline-none font-bold text-slate-700 transition" 
                                    :placeholder="selectedCustomer ? selectedCustomer.name : 'İsim veya Telefon Yazın...'">
                                <i data-lucide="search" class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition w-5 h-5"></i>
                                <i v-if="selectedCustomer" data-lucide="check-circle" class="absolute right-4 top-1/2 -translate-y-1/2 text-emerald-500 w-5 h-5"></i>
                                
                                <div v-if="isDropdownOpen" class="absolute top-full left-0 right-0 bg-white border border-slate-200 rounded-xl shadow-2xl mt-2 max-h-60 overflow-auto z-50 py-2">
                                    <div v-if="filteredCustomers.length === 0" class="p-4 text-slate-400 text-center text-sm font-medium">Kayıt bulunamadı</div>
                                    <div v-for="c in filteredCustomers" :key="c.id" @mousedown="selectCustomer(c)" class="px-4 py-3 hover:bg-blue-50 cursor-pointer flex justify-between items-center group/item transition-colors border-b border-slate-50 last:border-0">
                                        <div class="flex items-center gap-3">
                                            <div class="w-8 h-8 rounded-full bg-slate-100 text-slate-500 flex items-center justify-center font-bold text-xs">{{ c.name.charAt(0) }}</div>
                                            <div>
                                                <div class="font-bold text-slate-700 group-hover/item:text-blue-700">{{ c.name }}</div>
                                                <div class="text-xs text-slate-400 font-mono">{{ c.phone }}</div>
                                            </div>
                                        </div>
                                        <i data-lucide="chevron-right" class="w-4 h-4 text-slate-300"></i>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-2 uppercase tracking-wide">İŞLEM TARİHİ</label>
                             <div class="relative">
                                <input type="date" v-model="processDate" class="w-full pl-11 pr-4 py-3.5 rounded-xl border border-slate-200 bg-slate-50 focus:bg-white focus:border-blue-500 outline-none font-bold text-slate-700 transition text-sm">
                                <i data-lucide="calendar" class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 w-5 h-5"></i>
                             </div>
                        </div>

                        <button @click="goToStep2" class="w-full bg-blue-600 hover:bg-blue-700 text-white py-4 rounded-xl font-bold text-lg shadow-lg shadow-blue-200 transition transform hover:-translate-y-0.5 flex items-center justify-center gap-2 mt-4">
                            Hizmet Seçimine Geç <i data-lucide="arrow-right" class="w-5 h-5"></i>
                        </button>
                    </div>
                </div>

                <!-- STEP 2: HİZMETLER & PARÇALAR -->
                <div v-if="step === 2" class="h-full flex flex-col md:flex-row animate-fade-in overflow-hidden">
                    <div class="flex-1 flex flex-col border-r border-slate-200 bg-slate-50/50">
                        <div class="p-4 bg-white border-b border-slate-200 flex gap-3">
                            <div class="relative flex-1">
                                <i data-lucide="search" class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 w-4 h-4"></i>
                                <input type="text" v-model="searchService" placeholder="Hizmetlerde Ara..." class="w-full pl-9 pr-4 py-2.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-blue-500 transition text-sm">
                            </div>
                             <select class="px-3 py-2.5 rounded-lg border border-slate-200 bg-white text-slate-600 text-sm font-bold outline-none">
                                <option value="">Tüm Kategoriler</option>
                                <option value="Servis">Servis</option>
                                <option value="Lojistik">Lojistik</option>
                            </select>
                        </div>
                        
                        <div class="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
                            <div v-if="loadingServices" class="text-center p-10 text-slate-400"><i data-lucide="loader" class="w-8 h-8 animate-spin mx-auto mb-2"></i>Yükleniyor...</div>
                            <div v-else-if="filteredServices.length === 0" class="text-center p-10 text-slate-400">Hizmet bulunamadı.</div>
                            
                            <div v-else v-for="s in filteredServices" :key="s.id" 
                                class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-blue-400 hover:shadow-md transition cursor-pointer group relative overflow-hidden"
                                @click="addItem(s)">
                                <div class="flex justify-between items-start">
                                    <div>
                                        <div class="font-bold text-slate-700 text-sm group-hover:text-blue-700">{{ s.service_name }}</div>
                                        <div class="text-xs text-slate-400 mt-1 line-clamp-1 pr-8">{{ s.description }}</div>
                                    </div>
                                    <div class="font-bold text-emerald-600 text-sm bg-emerald-50 px-2 py-0.5 rounded border border-emerald-100 flex-shrink-0">
                                        {{ parseFloat(s.price).toLocaleString('tr-TR', {minimumFractionDigits: 2}) }} ₺
                                    </div>
                                </div>
                                <div class="absolute right-0 bottom-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                    <div class="bg-blue-600 text-white p-1.5 rounded-tl-xl rounded-br-xl shadow-lg"><i data-lucide="plus" class="w-4 h-4"></i></div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div class="w-[400px] flex flex-col bg-white h-full relative z-10 shadow-[-10px_0_30px_-15px_rgba(0,0,0,0.1)]">
                        <div class="p-5 border-b border-slate-100 bg-slate-50/50 flex justify-between items-center">
                            <h3 class="font-bold text-slate-700 flex items-center gap-2">
                                <i data-lucide="shopping-cart" class="w-5 h-5 text-blue-600"></i> İşlem Listesi
                            </h3>
                            <span class="text-xs font-bold bg-blue-100 text-blue-700 px-2 py-1 rounded-full">{{ selectedItems.length }} Kalem</span>
                        </div>

                        <div class="flex-1 overflow-y-auto p-4 space-y-2">
                            <div v-if="selectedItems.length === 0" class="h-full flex flex-col items-center justify-center text-slate-300 space-y-4">
                                <i data-lucide="shopping-bag" class="w-16 h-16 opacity-20"></i>
                                <span class="text-sm font-medium">Henüz hizmet seçilmedi</span>
                            </div>

                            <div v-else v-for="(item, idx) in selectedItems" :key="idx" class="flex gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100 relative group">
                                <div class="w-8 h-8 rounded-full bg-white text-slate-500 border border-slate-200 flex items-center justify-center font-bold text-xs shadow-sm">{{ item.qty }}x</div>
                                <div class="flex-1">
                                    <div class="font-bold text-slate-700 text-sm line-clamp-1">{{ item.name }}</div>
                                    <div class="text-xs text-slate-400">{{ (item.price * item.qty).toLocaleString('tr-TR', {minimumFractionDigits: 2}) }} ₺</div>
                                </div>
                                <button @click="removeItem(idx)" class="absolute -right-2 -top-2 bg-red-500 text-white rounded-full p-1 shadow-md opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 hover:scale-110">
                                    <i data-lucide="x" class="w-3 h-3"></i>
                                </button>
                            </div>
                        </div>

                        <div class="p-6 bg-slate-50 border-t border-slate-200 space-y-4">
                             <div class="flex justify-between items-end">
                                <span class="text-slate-500 font-bold text-sm uppercase">Genel Toplam</span>
                                <span class="text-3xl font-black text-slate-800 tracking-tight">{{ totalAmount.toLocaleString('tr-TR', {minimumFractionDigits: 2}) }} <span class="text-lg text-slate-400 font-bold">₺</span></span>
                            </div>
                            
                            <div class="flex gap-3 pt-2">
                                <button @click="step = 1" class="flex-1 py-3 rounded-xl border border-slate-300 text-slate-600 font-bold hover:bg-white transition">Geri</button>
                                <button @click="step = 3" :disabled="selectedItems.length === 0" class="flex-[2] py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2">
                                    Özete Geç <i data-lucide="arrow-right" class="w-5 h-5"></i>
                                </button>
                            </div>
                        </div>
                    </div>

                </div>
                
                <!-- STEP 3: ONAY & BAŞARI -->
                <div v-if="step === 3" class="h-full p-8 flex flex-col animate-fade-in items-center justify-center bg-slate-50/50">
                    
                    <!-- SUCCESS STATE -->
                    <div v-if="isSuccess" class="bg-white p-12 rounded-3xl shadow-xl border border-emerald-100 max-w-sm w-full text-center animate-fade-in-up">
                        <div class="w-24 h-24 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-md shadow-emerald-100 animate-pulse">
                            <i data-lucide="check" class="w-12 h-12"></i>
                        </div>
                        <h2 class="text-3xl font-bold text-slate-800 mb-2 tracking-tight">İşlem Başarılı!</h2>
                        <div class="text-slate-500 mb-8 font-medium">
                            <div class="text-slate-900 font-bold text-lg mb-1">{{ selectedCustomer?.name }}</div>
                            <div>adına kayıt oluşturuldu.</div>
                            <div class="mt-4 bg-slate-50 py-2 rounded-lg border border-slate-100 font-mono text-sm text-slate-600">
                                Takip No: <span class="font-bold text-blue-600">{{ createdTrackingNo }}</span>
                            </div>
                        </div>
                        <button onclick="window.location.reload()" class="w-full py-4 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-white font-bold shadow-lg shadow-emerald-200 transition text-lg">
                            Yeni İşlem Başlat
                        </button>
                    </div>

                    <!-- CONFIRM STATE -->
                    <div v-else class="bg-white p-10 rounded-3xl shadow-xl border border-slate-200 max-w-sm w-full text-center relative overflow-hidden">
                        <div v-if="isProcessing" class="absolute inset-0 bg-white/80 z-20 flex items-center justify-center backdrop-blur-sm">
                            <div class="flex flex-col items-center">
                                <i data-lucide="loader" class="w-10 h-10 animate-spin text-blue-600 mb-2"></i>
                                <span class="font-bold text-slate-600">Kaydediliyor...</span>
                            </div>
                        </div>

                        <div class="w-24 h-24 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto mb-6">
                            <i data-lucide="clipboard-check" class="w-10 h-10"></i>
                        </div>
                        <h2 class="text-2xl font-bold text-slate-800 mb-2">İşlem Özeti</h2>
                        <div class="text-slate-500 text-sm mb-8 space-y-1">
                            <p><b>{{ selectedCustomer?.name }}</b> adına</p>
                            <p><b>{{ selectedItems.length }} adet</b> hizmet/ürün</p>
                            <p class="text-emerald-600 font-bold text-xl pt-2">{{ totalAmount.toLocaleString('tr-TR') }} ₺</p>
                        </div>
                        <div class="flex gap-3">
                             <button @click="step = 2" class="flex-1 py-3 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 font-bold transition">Düzenle</button>
                             <button @click="saveProcess" class="flex-1 py-3 rounded-xl bg-blue-600 hover:bg-blue-700 text-white font-bold shadow-lg shadow-blue-200 transition">Onayla</button>
                        </div>
                    </div>
                </div>

            </div>
        </div>
    </div>
    `,
    computed: {
        filteredCustomers() {
            if (!this.searchQuery && !this.isDropdownOpen) return [];
            if (!this.customers) return [];
            const q = (this.searchQuery || '').toLowerCase();
            return this.customers.filter(c => c.name.toLowerCase().includes(q) || c.phone.includes(q)).slice(0, 5);
        },
        filteredServices() {
            if (!this.searchService) return this.availableServices;
            const q = this.searchService.toLowerCase();
            return this.availableServices.filter(s => s.service_name.toLowerCase().includes(q));
        },
        totalAmount() {
            return this.selectedItems.reduce((sum, item) => sum + (item.price * item.qty), 0);
        }
    },
    methods: {
        closeDropdown() { setTimeout(() => { this.isDropdownOpen = false; }, 200); },
        selectCustomer(c) { this.selectedCustomer = c; this.searchQuery = c.name; this.isDropdownOpen = false; },
        async goToStep2() {
            if (!this.selectedCustomer) { alert("Lütfen müşteri seçin!"); return; }
            this.step = 2;
            this.loadServices();
        },
        async loadServices() {
            this.loadingServices = true;
            try {
                const res = await fetch('/api/service-definitions');
                this.availableServices = await res.json();
            } catch (e) { console.error(e); }
            this.loadingServices = false;
        },
        addItem(service) {
            const existing = this.selectedItems.find(i => i.id === service.id);
            if (existing) { existing.qty++; } else { this.selectedItems.push({ id: service.id, name: service.service_name, price: service.price, qty: 1 }); }
        },
        removeItem(idx) { this.selectedItems.splice(idx, 1); },

        async saveProcess() {
            this.isProcessing = true;

            // 15 Saniye Timeout Mekanizması
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 15000);

            try {
                // Payload Validasyonu
                if (!this.selectedCustomer || !this.selectedCustomer.id) throw new Error("Müşteri bilgisi eksik/hatalı.");
                if (this.selectedItems.length === 0) throw new Error("En az bir hizmet/ürün seçmelisiniz.");

                const payload = {
                    customer_id: this.selectedCustomer.id,
                    customer_name: this.selectedCustomer.name,
                    process_date: this.processDate,
                    items: this.selectedItems.map(i => ({
                        id: i.id,
                        name: i.name || i.service_name, // fallback
                        price: parseFloat(i.price) || 0,
                        qty: parseInt(i.qty) || 1
                    }))
                };

                console.log("Gönderilen Veri:", payload); // Debug için konsola bas

                const res = await fetch('/api/process-wizard/save', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                    signal: controller.signal
                });

                clearTimeout(timeoutId); // Zamanında cevap geldi, sayacı durdur

                let data;
                try {
                    data = await res.json();
                } catch (jsonErr) {
                    throw new Error(`Sunucu geçersiz yanıt döndürdü (Status: ${res.status}).`);
                }

                if (!res.ok) {
                    throw new Error(data.detail || `Sunucu Hatası (${res.status})`);
                }

                if (data.success) {
                    this.isSuccess = true;
                    this.createdTrackingNo = data.tracking_no;
                } else {
                    throw new Error(data.detail || 'Bilinmeyen sunucu hatası.');
                }

            } catch (e) {
                console.error("Save Process Error:", e);
                let msg = e.message;
                if (e.name === 'AbortError') msg = "Sunucu yanıt vermedi (Zaman Aşımı). Bağlantınızı kontrol edin.";

                // Detaylı Hata Gösterimi
                alert('⚠️ KAYIT BAŞARISIZ OLDU\n\nSebep: ' + msg + '\n\nLütfen sayfayı yenileyip tekrar deneyin.');
            } finally {
                this.isProcessing = false; // Loading her durumda kapanır
            }
        }
    },
    updated() { lucide.createIcons(); },
    mounted() {
        lucide.createIcons();
        if (this.preselectedCustomer) {
            this.selectCustomer(this.preselectedCustomer);
        }
    }
}
