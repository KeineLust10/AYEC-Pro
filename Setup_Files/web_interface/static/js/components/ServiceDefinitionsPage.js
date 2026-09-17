
export default {
    props: ['loading'],
    data() {
        return {
            services: [],
            form: {
                id: null,
                service_name: '',
                price: 0.00,
                category: 'Genel',
                description: ''
            },
            searchQuery: '',
            localLoading: false
        }
    },
    template: `
    <div class="h-full flex flex-col p-6 animate-fade-in bg-slate-50 space-y-6">
        <!-- HEADER -->
        <h2 class="text-2xl font-bold text-slate-800 flex items-center gap-3">
            <i data-lucide="settings" class="w-6 h-6 text-slate-500"></i>
            Hizmet ve Ücret Yönetimi
        </h2>
        
        <!-- FORM AREA -->
        <div class="bg-white p-5 rounded-xl shadow-sm border border-slate-200">
            <div class="text-xs text-slate-400 mb-4">Hizmet tanımlarını, fiyatlarını ve açıklamalarını buradan yönetin.</div>
            
            <div class="grid grid-cols-12 gap-4 items-end">
                <!-- Hizmet Adı -->
                <div class="col-span-4">
                    <label class="block text-xs font-bold text-slate-500 mb-1">HİZMET ADI</label>
                    <input type="text" v-model="form.service_name" class="w-full px-3 py-2 rounded border border-slate-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none text-sm placeholder-slate-300" placeholder="Örn: Anakart Onarımı">
                </div>
                
                <!-- Birim Fiyat -->
                <div class="col-span-2">
                    <label class="block text-xs font-bold text-slate-500 mb-1">BİRİM FİYAT (TL)</label>
                    <input type="number" step="0.01" v-model="form.price" class="w-full px-3 py-2 rounded border border-slate-300 focus:border-blue-500 outline-none text-sm font-bold text-slate-700">
                </div>
                
                <!-- Açıklama -->
                <div class="col-span-6">
                    <label class="block text-xs font-bold text-slate-500 mb-1">AÇIKLAMA / NOTLAR</label>
                    <input type="text" v-model="form.description" class="w-full px-3 py-2 rounded border border-slate-300 focus:border-blue-500 outline-none text-sm placeholder-slate-300" placeholder="Hizmet kapsamı hakkında kısa bilgi...">
                </div>
            </div>

            <!-- Buttons -->
            <div class="flex items-center gap-3 mt-4">
                <button v-if="!form.id" @click="saveService" class="bg-emerald-500 hover:bg-emerald-600 text-white px-5 py-2 rounded font-bold text-sm flex items-center gap-2 transition shadow-sm">
                    <i data-lucide="plus" class="w-4 h-4"></i> Yeni Hizmet Ekle
                </button>
                <button v-else @click="saveService" class="bg-emerald-500 hover:bg-emerald-600 text-white px-5 py-2 rounded font-bold text-sm flex items-center gap-2 transition shadow-sm">
                    <i data-lucide="copy" class="w-4 h-4"></i> Yeni Olarak Kopyala
                </button>
                
                <button v-if="form.id" @click="updateService" class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded font-bold text-sm flex items-center gap-2 transition shadow-sm">
                    <i data-lucide="save" class="w-4 h-4"></i> Değişikliği Kaydet
                </button>
                
                <button v-if="form.id" @click="deleteService" class="bg-red-500 hover:bg-red-600 text-white px-5 py-2 rounded font-bold text-sm flex items-center gap-2 transition shadow-sm">
                    <i data-lucide="trash-2" class="w-4 h-4"></i> Seçileni Sil
                </button>

                <div class="flex-1"></div>
                
                <button @click="clearForm" class="bg-slate-100 hover:bg-slate-200 text-slate-600 px-5 py-2 rounded font-bold text-sm flex items-center gap-2 transition">
                    <i data-lucide="eraser" class="w-4 h-4"></i> Temizle
                </button>
            </div>
        </div>

        <!-- TABLE -->
        <div class="flex-1 bg-white border border-slate-300 overflow-hidden flex flex-col shadow-sm">
            <div class="bg-slate-50 border-b border-slate-300 grid grid-cols-12 px-4 py-2 text-xs font-bold text-slate-600 uppercase tracking-wide">
                <div class="col-span-1">ID</div>
                <div class="col-span-4">HİZMET ADI</div>
                <div class="col-span-2">FİYAT</div>
                <div class="col-span-5">AÇIKLAMA</div>
            </div>
            
            <div class="flex-1 overflow-auto bg-white">
                <div v-if="localLoading" class="p-8 text-center text-slate-400">Yükleniyor...</div>
                <div v-else-if="filteredServices.length === 0" class="p-8 text-center text-slate-400">Kayıt bulunamadı.</div>
                <div v-else v-for="(s, index) in filteredServices" :key="s.id" 
                    @click="selectService(s)"
                    class="grid grid-cols-12 px-4 py-2 text-sm border-b border-slate-100 cursor-pointer transition hover:bg-blue-50"
                    :class="{'bg-[#FFFDE7]': index % 2 === 0, 'bg-white': index % 2 !== 0, 'ring-2 ring-blue-500 bg-blue-50 z-10': form.id === s.id}">
                    
                    <div class="col-span-1 text-slate-500 font-mono">{{ s.id }}</div>
                    <div class="col-span-4 font-bold text-slate-700 uppercase">{{ s.service_name }}</div>
                    <div class="col-span-2 text-slate-700 font-bold">{{ parseFloat(s.price).toFixed(2) }} TL</div>
                    <div class="col-span-5 text-slate-500 truncate">{{ s.description || '-' }}</div>
                </div>
            </div>
        </div>
        
        <div class="text-xs text-slate-400 font-bold">
            Toplam {{ filteredServices.length }} kayıt listelendi
        </div>

    </div>
    `,
    computed: {
        filteredServices() {
            if (!this.searchQuery) return this.services;
            const q = this.searchQuery.toLowerCase();
            return this.services.filter(s => s.service_name.toLowerCase().includes(q));
        }
    },
    methods: {
        async loadServices() {
            this.localLoading = true;
            try {
                const res = await fetch('/api/service-definitions');
                this.services = await res.json();
            } catch (e) { console.error(e); }
            this.localLoading = false;
        },
        selectService(s) {
            this.form = { ...s };
        },
        clearForm() {
            this.form = { id: null, service_name: '', price: 0.00, category: 'Genel', description: '' };
        },
        async saveService() {
            if (!this.form.service_name) { alert("Hizmet adı giriniz!"); return; }
            try {
                const res = await fetch('/api/service-definitions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        service_name: this.form.service_name,
                        price: parseFloat(this.form.price),
                        category: this.form.category,
                        duration: 60,
                        description: this.form.description
                    })
                });
                if (res.ok) {
                    this.loadServices();
                    this.clearForm();
                } else { alert("Hata oluştu"); }
            } catch (e) { alert("Hata: " + e); }
        },
        async updateService() {
            if (!this.form.id) return;
            try {
                const res = await fetch(`/api/service-definitions/${this.form.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        service_name: this.form.service_name,
                        price: parseFloat(this.form.price),
                        category: this.form.category,
                        duration: 60,
                        description: this.form.description
                    })
                });
                if (res.ok) {
                    this.loadServices();
                    // Seçili kalması kullanıcının hoşuna gidebilir, clearForm yapmıyorum.
                    alert("Güncellendi!");
                } else { alert("Hata oluştu"); }
            } catch (e) { alert("Hata: " + e); }
        },
        async deleteService() {
            if (!this.form.id) return;
            if (!confirm("Bu hizmeti silmek istediğinize emin misiniz?")) return;
            try {
                const res = await fetch(`/api/service-definitions/${this.form.id}`, {
                    method: 'DELETE'
                });
                if (res.ok) {
                    this.loadServices();
                    this.clearForm();
                } else { alert("Hata oluştu"); }
            } catch (e) { alert("Hata: " + e); }
        }
    },
    mounted() {
        this.loadServices();
        lucide.createIcons();
    },
    updated() { lucide.createIcons(); }
}
