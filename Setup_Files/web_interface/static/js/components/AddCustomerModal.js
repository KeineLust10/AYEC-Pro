export default {
    props: ['editMode', 'existingCustomer'],
    data() {
        return {
            customer: {
                name: '',
                phone: '',
                email: '',
                address: '',
                tax_id: ''
            },
            loading: false
        }
    },
    computed: {
        title() { return this.editMode ? 'Müşteriyi Düzenle' : 'Yeni Müşteri Ekle' },
        btnText() { return this.editMode ? (this.loading ? 'Güncelleniyor...' : 'Güncelle') : (this.loading ? 'Kaydediliyor...' : 'Kaydet') }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col">
            <!-- Header -->
            <div class="px-6 py-4 bg-slate-50 border-b border-slate-100 flex justify-between items-center">
                <h3 class="font-bold text-lg text-slate-800 flex items-center gap-2">
                    <div class="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                        <i :data-lucide="editMode ? 'edit-2' : 'user-plus'" class="w-4 h-4"></i>
                    </div>
                    {{ title }}
                </h3>
                <button @click="$emit('close')" class="p-2 hover:bg-slate-200 rounded-full transition"><i data-lucide="x" class="w-5 h-5 text-slate-500"></i></button>
            </div>

            <!-- Form -->
            <div class="p-6 space-y-4">
                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">AD SOYAD / FİRMA ADI <span class="text-red-500">*</span></label>
                    <input type="text" v-model="customer.name" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 outline-none transition font-bold text-slate-700" placeholder="Örn: Ahmet Yılmaz">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">TELEFON <span class="text-red-500">*</span></label>
                        <input type="tel" v-model="customer.phone" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 outline-none transition" placeholder="05XX XXX XX XX">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">E-POSTA</label>
                        <input type="email" v-model="customer.email" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 outline-none transition" placeholder="ornek@email.com">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">ADRES</label>
                    <textarea v-model="customer.address" rows="3" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 outline-none transition resize-none"></textarea>
                </div>

                <div>
                     <label class="block text-xs font-bold text-slate-500 mb-1 uppercase">VERGİ NO / TC</label>
                     <input type="text" v-model="customer.tax_id" class="w-full px-3 py-2.5 rounded-lg border border-slate-300 focus:border-blue-500 outline-none transition">
                </div>
            </div>

            <!-- Footer -->
            <div class="px-6 py-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
                <button @click="$emit('close')" class="px-5 py-2.5 rounded-xl text-slate-600 font-bold hover:bg-slate-200 transition">İptal</button>
                <button @click="save" :disabled="loading" class="px-6 py-2.5 rounded-xl bg-blue-600 text-white font-bold hover:bg-blue-700 shadow-lg shadow-blue-200 transition flex items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed">
                    <i v-if="loading" data-lucide="loader" class="w-4 h-4 animate-spin"></i>
                    <i v-else data-lucide="check" class="w-4 h-4"></i>
                    {{ btnText }}
                </button>
            </div>
        </div>
    </div>
    `,
    methods: {
        async save() {
            if (!this.customer.name || !this.customer.phone) {
                alert("Lütfen zorunlu alanları (Ad, Telefon) doldurun!");
                return;
            }

            this.loading = true;
            try {
                const url = this.editMode ? `/api/customers/${this.existingCustomer.id}` : '/api/customers';
                const method = this.editMode ? 'PUT' : 'POST';

                const payload = {
                    name: this.customer.name,
                    phone: this.customer.phone,
                    email: this.customer.email || '',
                    address: this.customer.address || '',
                    tax_id: this.customer.tax_id || ''
                };

                const res = await fetch(url, {
                    method: method,
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();

                if (data.success) {
                    this.$emit('saved');
                    this.$emit('close');
                } else {
                    alert('Hata: ' + (data.detail || 'Bilinmeyen Hata'));
                }
            } catch (e) {
                console.error(e);
                alert('Bağlantı hatası!');
            } finally {
                this.loading = false;
            }
        }
    },
    mounted() {
        lucide.createIcons();
        if (this.editMode && this.existingCustomer) {
            this.customer = {
                name: this.existingCustomer.name,
                phone: this.existingCustomer.phone,
                email: this.existingCustomer.email,
                address: this.existingCustomer.address,
                tax_id: this.existingCustomer.tax_id || this.existingCustomer.tax_no || ''
            };
        }
    },
    updated() { lucide.createIcons(); }
}
