
export default {
    template: `
    <div class="h-full flex flex-col animate-fade-in p-8">
        <!-- HEADER -->
        <div class="flex items-center justify-between mb-6 flex-shrink-0">
            <div>
                <h2 class="text-2xl font-bold text-slate-800">Yeni Servis Kaydı</h2>
                <p class="text-slate-500 text-sm">Cihaz kabul ve servis girişi</p>
            </div>
            <div class="flex gap-3">
                 <button class="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-600 font-bold hover:bg-slate-50 transition">Temizle</button>
                 <button class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-bold shadow-lg shadow-blue-200 transition flex items-center gap-2" @click="save">
                    <i data-lucide="save" class="w-5 h-5"></i> KAYDI TAMAMLA
                 </button>
            </div>
        </div>

        <!-- MAIN LAYOUT -->
        <div class="flex-1 flex gap-8 overflow-hidden">
            
            <!-- LEFT COLUMN (SCROLLABLE FORM) -->
            <div class="flex-1 overflow-y-auto pr-4 custom-scrollbar space-y-6">
                
                <!-- 1. CUSTOMER -->
                <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                     <div class="flex justify-between items-center mb-4 border-b border-slate-100 pb-2">
                        <h3 class="font-bold text-slate-700 flex items-center text-sm uppercase"><i data-lucide="user" class="w-4 h-4 mr-2 text-blue-500"></i> Müşteri Bilgileri</h3>
                        <button class="text-xs bg-slate-100 px-2 py-1 rounded text-slate-600 font-bold hover:bg-slate-200" @click="openCustomerSelect">🔍 Müşteri Seç</button>
                     </div>
                     
                     <div class="grid grid-cols-1 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-500 mb-1">MÜŞTERİ / FİRMA ADI</label>
                            <input v-model="form.customer_name" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500 font-bold text-slate-700" placeholder="Ad Soyad giriniz...">
                        </div>
                        <div class="grid grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-bold text-slate-500 mb-1">TCKN / VERGİ NO</label>
                                <input v-model="form.tax_id" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500">
                            </div>
                            <div>
                                <label class="block text-xs font-bold text-slate-500 mb-1">TELEFON</label>
                                <input v-model="form.phone" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500" placeholder="(5XX)...">
                            </div>
                        </div>
                     </div>
                </div>

                <!-- 2. DEVICE -->
                <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                     <h3 class="font-bold text-slate-700 mb-4 border-b border-slate-100 pb-2 text-sm uppercase flex items-center"><i data-lucide="smartphone" class="w-4 h-4 mr-2 text-purple-500"></i> Cihaz Bilgileri</h3>
                     <div class="grid grid-cols-2 gap-4">
                        <div>
                            <label class="block text-xs font-bold text-slate-500 mb-1">TÜR</label>
                            <select v-model="form.device_type" class="w-full p-2.5 border border-slate-200 rounded-lg bg-white">
                                <option>Telefon</option><option>Tablet</option><option>Laptop</option><option>Masaüstü</option><option>Giyilebilir</option>
                            </select>
                        </div>
                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-1">MARKA</label>
                             <input v-model="form.brand" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:border-blue-500" placeholder="Apple, Samsung...">
                        </div>
                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-1">MODEL</label>
                             <input v-model="form.model" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:border-blue-500" placeholder="iPhone 13...">
                        </div>
                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-1">SERİ NO / IMEI</label>
                             <input v-model="form.serial" type="text" class="w-full p-2.5 border border-slate-200 rounded-lg focus:border-blue-500">
                        </div>
                     </div>
                </div>

                <!-- 3. FAULT & DETAILS -->
                <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                     <h3 class="font-bold text-slate-700 mb-4 border-b border-slate-100 pb-2 text-sm uppercase flex items-center"><i data-lucide="alert-circle" class="w-4 h-4 mr-2 text-amber-500"></i> Arıza & Detaylar</h3>
                     
                     <div class="mb-4 relative">
                        <label class="block text-xs font-bold text-slate-500 mb-1">ARIZA TANIMI</label>
                        <textarea v-model="form.description" class="w-full p-3 border border-slate-200 rounded-lg focus:border-blue-500 h-24 resize-none" placeholder="Arıza detaylarını yazın..."></textarea>
                        <button class="absolute bottom-3 right-3 p-2 bg-slate-100 rounded-full hover:bg-slate-200 text-slate-600" title="Sesli Not (Jarvis)"><i data-lucide="mic" class="w-4 h-4"></i></button>
                     </div>

                     <div class="grid grid-cols-2 gap-4">
                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-1">ÖNCELİK</label>
                             <select v-model="form.urgency" class="w-full p-2.5 border border-slate-200 rounded-lg bg-white">
                                <option>Düşük</option><option>Normal</option><option>Yüksek</option><option>Kritik</option>
                            </select>
                        </div>
                        <div>
                             <label class="block text-xs font-bold text-slate-500 mb-1">TAHMİNİ TUTAR (₺)</label>
                             <input v-model="form.cost" type="number" class="w-full p-2.5 border border-slate-200 rounded-lg focus:border-blue-500">
                        </div>
                     </div>
                </div>

            </div>

            <!-- RIGHT COLUMN (FIXED) -->
            <div class="w-80 flex flex-col gap-6">
                <!-- PATTERN LOCK -->
                <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col items-center">
                    <h3 class="font-bold text-slate-700 text-sm uppercase mb-4 flex items-center"><i data-lucide="unlock" class="w-4 h-4 mr-2 text-slate-400"></i> Kilit Deseni</h3>
                    
                    <!-- Simplified Visual Pattern Grid -->
                    <div class="grid grid-cols-3 gap-4 mb-4 p-4 bg-slate-50 rounded-xl relative">
                        <div v-for="n in 9" :key="n" 
                             class="w-4 h-4 rounded-full bg-slate-300 cursor-pointer hover:bg-blue-400 hover:scale-125 transition-all"
                             @click="togglePattern(n)"
                             :class="{'bg-blue-600 scale-125 ring-2 ring-blue-200': pattern.includes(n)}">
                        </div>
                    </div>
                    <button @click="pattern = []" class="text-xs text-slate-400 hover:text-red-500 font-bold">Deseni Temizle</button>
                </div>

                <!-- PHOTO -->
                <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 flex flex-col items-center">
                    <h3 class="font-bold text-slate-700 text-sm uppercase mb-4 flex items-center"><i data-lucide="camera" class="w-4 h-4 mr-2 text-slate-400"></i> Cihaz Görseli</h3>
                    
                    <div class="w-full h-40 bg-slate-50 border-2 border-dashed border-slate-200 rounded-xl flex flex-col items-center justify-center text-slate-400 hover:bg-slate-100 hover:border-blue-300 transition cursor-pointer mb-4">
                        <i data-lucide="image-plus" class="w-8 h-8 mb-2 opacity-50"></i>
                        <span class="text-xs font-medium">Fotoğraf Yükle</span>
                    </div>
                    <span class="text-xs text-slate-400 italic">Yüklenen görsel yok</span>
                </div>
            </div>

        </div>
    </div>
    `,
    data() {
        return {
            form: {
                customer_name: '',
                tax_id: '',
                phone: '',
                device_type: 'Telefon',
                brand: '',
                model: '',
                serial: '',
                description: '',
                urgency: 'Normal',
                cost: 0
            },
            pattern: []
        }
    },
    methods: {
        togglePattern(n) {
            if (this.pattern.includes(n)) return
            this.pattern.push(n)
        },
        openCustomerSelect() {
            // Mock
            const names = ["Ahmet Yılmaz", "Veli Demir", "Ayşe Kaya", "Mehmet Öz"]
            this.form.customer_name = names[Math.floor(Math.random() * names.length)]
            this.form.phone = "5" + Math.floor(Math.random() * 1000000000)
        },
        save() {
            if (!this.form.customer_name || !this.form.brand) {
                alert("Lütfen zorunlu alanları doldurun!")
                return
            }
            alert("Kayıt Başarıyla Oluşturuldu! Servis fişi yazdırılıyor...")
        }
    },
    updated() { lucide.createIcons() },
    mounted() { lucide.createIcons() }
}
