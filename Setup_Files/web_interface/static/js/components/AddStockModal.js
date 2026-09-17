
export default {
    props: [],
    data() {
        return {
            part: {
                part_name: '',
                stock: 0,
                min_stock: 5,
                price: 0.0,
                category: 'Genel' // Backend modelinde category yoksa bile frontendde tutabilirim veya model güncellemesi gerekebilir. Main.py PartModel'de category YOKMUŞ.
                // Main.py: class PartModel(BaseModel): part_name, stock, min_stock, price.
                // Kategori backend'de desteklenmiyor şu anlık. O alanı göstermelik koyup backend'e göndermeyeceğim veya main.py'yi güncelleyeceğim.
                // Main.py'yi güncellemek riskli olabilir şimdi. Göndermeden önce temizleyeceğim.
            },
            loading: false
        }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
            <!-- Header -->
            <div class="px-6 py-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
                <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-orange-100 text-orange-600 flex items-center justify-center"><i data-lucide="package-plus" class="w-4 h-4"></i></div>
                    Yeni Ürün / Stok Ekle
                </h3>
                <button @click="$emit('close')" class="p-2 hover:bg-slate-200 rounded-full transition"><i data-lucide="x" class="w-5 h-5 text-slate-500"></i></button>
            </div>

            <!-- Form -->
            <div class="p-6 space-y-5">
                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">ÜRÜN / PARÇA ADI <span class="text-red-500">*</span></label>
                    <input type="text" v-model="part.part_name" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-orange-500 focus:ring-4 focus:ring-orange-500/10 outline-none transition font-bold text-slate-700" placeholder="Örn: iPhone 11 Ekran">
                </div>

                <div class="grid grid-cols-2 gap-4">
                     <div>
                        <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">SATIŞ FİYATI (₺)</label>
                        <div class="relative">
                            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-bold">₺</span>
                            <input type="number" step="0.01" v-model="part.price" class="w-full pl-8 pr-3 py-2.5 rounded-lg border border-slate-300 focus:border-orange-500 outline-none transition font-mono font-bold">
                        </div>
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">STOK ADEDİ</label>
                        <input type="number" v-model="part.stock" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-orange-500 outline-none transition font-mono font-bold">
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                     <div>
                        <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">KRİTİK STOK UYARISI</label>
                        <input type="number" v-model="part.min_stock" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-orange-500 outline-none transition font-mono">
                         <p class="text-[10px] text-slate-400 mt-1">Stok bu sayının altına düştüğünde uyarı verir.</p>
                    </div>
                    <div>
                        <!-- Category placeholder (Not stored in basic DB model currently) -->
                         <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">KATEGORİ</label>
                         <select class="w-full px-3 py-2.5 rounded-lg border border-slate-300 bg-slate-50 text-slate-500 cursor-not-allowed" disabled>
                            <option>Yedek Parça</option>
                         </select>
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
                <button @click="$emit('close')" class="px-5 py-2.5 rounded-xl text-slate-600 font-bold hover:bg-slate-200 transition">İptal</button>
                <button @click="save" :disabled="loading" class="px-6 py-2.5 rounded-xl bg-orange-500 text-white font-bold hover:bg-orange-600 shadow-lg shadow-orange-200 transition flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed">
                    <i v-if="loading" data-lucide="loader" class="w-4 h-4 animate-spin"></i>
                    <i v-else data-lucide="check" class="w-4 h-4"></i>
                    {{ loading ? 'Kaydediliyor...' : 'Stok Ekle' }}
                </button>
            </div>
        </div>
    </div>
    `,
    methods: {
        async save() {
            if (!this.part.part_name) {
                alert("Ürün adı giriniz!");
                return;
            }

            this.loading = true;
            try {
                // Main.py Model: part_name, stock, min_stock, price
                const payload = {
                    part_name: this.part.part_name,
                    stock: parseInt(this.part.stock) || 0,
                    min_stock: parseInt(this.part.min_stock) || 5,
                    price: parseFloat(this.part.price) || 0.0
                };

                const res = await fetch('/api/parts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (data.success) {
                    this.$emit('saved', { ...payload, id: data.id });
                    this.$emit('close');
                } else {
                    alert('Kayıt Başarısız: ' + (data.detail || JSON.stringify(data)));
                }
            } catch (e) {
                console.error(e);
                alert('Sistem Hatası: ' + e);
            } finally {
                this.loading = false;
            }
        }
    },
    updated() { lucide.createIcons(); },
    mounted() { lucide.createIcons(); }
}
