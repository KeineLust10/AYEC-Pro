export default {
    props: ['customer'],
    data() {
        return {
            services: [],
            selectedService: null,
            quantity: 1,
            customPrice: null,
            notes: '',
            loading: false
        }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <!-- Header -->
            <div class="px-6 py-4 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white flex justify-between items-center flex-shrink-0">
                <div>
                    <h3 class="font-bold text-xl">Hızlı Hizmet Ekle</h3>
                    <p class="text-sm opacity-90">{{ customer.name }} - {{ customer.phone }}</p>
                </div>
                <button @click="$emit('close')" class="p-2 hover:bg-white/20 rounded-full transition">
                    <i data-lucide="x" class="w-6 h-6"></i>
                </button>
            </div>

            <!-- Content -->
            <div class="p-6 space-y-5 flex-1 overflow-y-auto">
                <!-- Hizmet Seçimi -->
                <div>
                    <label class="block text-sm font-bold text-slate-700 mb-2">Hizmet Seçin</label>
                    <select v-model="selectedService" class="w-full px-4 py-3 rounded-lg border-2 border-slate-200 focus:border-emerald-500 outline-none transition font-medium">
                        <option :value="null">-- Hizmet Seçin --</option>
                        <option v-for="s in services" :key="s.id" :value="s">
                            {{ s.service_name }} - {{ parseFloat(s.price).toFixed(2) }} ₺
                        </option>
                    </select>
                </div>

                <!-- Miktar ve Fiyat -->
                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-sm font-bold text-slate-700 mb-2">Miktar</label>
                        <input type="number" v-model.number="quantity" min="1" class="w-full px-4 py-3 rounded-lg border-2 border-slate-200 focus:border-emerald-500 outline-none transition font-mono font-bold text-lg">
                    </div>
                    <div>
                        <label class="block text-sm font-bold text-slate-700 mb-2">Özel Fiyat (Opsiyonel)</label>
                        <input type="number" step="0.01" v-model.number="customPrice" :placeholder="selectedService ? parseFloat(selectedService.price).toFixed(2) : '0.00'" class="w-full px-4 py-3 rounded-lg border-2 border-slate-200 focus:border-emerald-500 outline-none transition font-mono">
                    </div>
                </div>

                <!-- Notlar -->
                <div>
                    <label class="block text-sm font-bold text-slate-700 mb-2">Notlar (Opsiyonel)</label>
                    <textarea v-model="notes" rows="3" class="w-full px-4 py-3 rounded-lg border-2 border-slate-200 focus:border-emerald-500 outline-none transition resize-none" placeholder="Ek açıklama..."></textarea>
                </div>

                <!-- Özet -->
                <div v-if="selectedService" class="bg-emerald-50 border-2 border-emerald-200 rounded-xl p-4">
                    <div class="flex justify-between items-center mb-2">
                        <span class="font-bold text-slate-700">Toplam Tutar:</span>
                        <span class="text-3xl font-black text-emerald-600">{{ totalAmount.toFixed(2) }} ₺</span>
                    </div>
                    <div class="text-xs text-slate-500">
                        {{ selectedService.service_name }} x {{ quantity }} adet
                    </div>
                </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex justify-end gap-3 flex-shrink-0">
                <button @click="$emit('close')" class="px-6 py-3 rounded-lg text-slate-600 font-bold hover:bg-slate-200 transition">
                    İptal
                </button>
                <button @click="saveService" :disabled="!selectedService || loading" class="px-8 py-3 rounded-lg bg-emerald-500 text-white font-bold hover:bg-emerald-600 shadow-lg shadow-emerald-200 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2">
                    <i v-if="loading" data-lucide="loader" class="w-5 h-5 animate-spin"></i>
                    <i v-else data-lucide="check" class="w-5 h-5"></i>
                    {{ loading ? 'Kaydediliyor...' : 'Hizmeti Ekle' }}
                </button>
            </div>
        </div>
    </div>
    `,
    computed: {
        totalAmount() {
            if (!this.selectedService) return 0;
            const price = this.customPrice !== null ? this.customPrice : parseFloat(this.selectedService.price);
            return price * this.quantity;
        }
    },
    methods: {
        async loadServices() {
            try {
                const res = await fetch('/api/service-definitions');
                this.services = await res.json();
            } catch (e) {
                console.error(e);
                alert('Hizmetler yüklenemedi!');
            }
        },
        async saveService() {
            if (!this.selectedService) {
                alert('Lütfen bir hizmet seçin!');
                return;
            }

            this.loading = true;
            try {
                const payload = {
                    customer_id: this.customer.id,
                    service_id: this.selectedService.id,
                    service_name: this.selectedService.service_name,
                    quantity: this.quantity,
                    unit_price: this.customPrice !== null ? this.customPrice : parseFloat(this.selectedService.price),
                    total_amount: this.totalAmount,
                    notes: this.notes,
                    date: new Date().toISOString().split('T')[0]
                };

                const res = await fetch('/api/customer-services', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });

                if (res.ok) {
                    alert('✅ Hizmet başarıyla eklendi!');
                    this.$emit('saved');
                    this.$emit('close');
                } else {
                    const error = await res.json();
                    alert('❌ Hata: ' + (error.detail || 'Bilinmeyen hata'));
                }
            } catch (e) {
                console.error(e);
                alert('⚠️ Sunucu hatası: ' + e.message);
            } finally {
                this.loading = false;
            }
        }
    },
    mounted() {
        this.loadServices();
        lucide.createIcons();
    },
    updated() {
        lucide.createIcons();
    }
}
