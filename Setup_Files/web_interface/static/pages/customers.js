// Customers Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Müşteri Listesi</h3>
                    <button class="px-4 py-2 bg-emerald-600 text-white rounded-lg text-sm font-medium hover:bg-emerald-700 transition-all">
                        <i data-lucide="user-plus" class="w-4 h-4 inline mr-1"></i>
                        Yeni Müşteri
                    </button>
                </div>
                
                <div v-if="customers.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">ID</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Ad Soyad</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Telefon</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Email</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Adres</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">İşlemler</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="customer in customers" :key="customer.id" class="border-b border-slate-100 hover:bg-slate-50 transition-all">
                                <td class="px-4 py-3 font-mono text-sm text-slate-500">#{{ customer.id }}</td>
                                <td class="px-4 py-3 font-medium text-slate-800">{{ customer.name }}</td>
                                <td class="px-4 py-3">{{ customer.phone }}</td>
                                <td class="px-4 py-3 text-sm text-slate-600">{{ customer.email || '-' }}</td>
                                <td class="px-4 py-3 text-sm text-slate-600">{{ customer.address || '-' }}</td>
                                <td class="px-4 py-3">
                                    <div class="flex gap-2">
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Detay">
                                            <i data-lucide="eye" class="w-4 h-4 text-slate-600"></i>
                                        </button>
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Düzenle">
                                            <i data-lucide="edit" class="w-4 h-4 text-slate-600"></i>
                                        </button>
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Geçmiş">
                                            <i data-lucide="history" class="w-4 h-4 text-slate-600"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="users" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p class="text-lg font-medium">Henüz müşteri kaydı yok</p>
                    <p class="text-sm mt-2">Yeni müşteri eklemek için yukarıdaki butonu kullanın</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            customers: []
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/customers')
                this.customers = await res.json()
            } catch (e) {
                console.error('Customers load error:', e)
            }
        }
    },
    mounted() {
        this.loadData()
    },
    updated() {
        if (window.lucide) window.lucide.createIcons()
    }
}
