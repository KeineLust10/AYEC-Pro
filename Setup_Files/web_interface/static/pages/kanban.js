// Kanban / Services Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Servis Listesi</h3>
                    <button class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-all">
                        <i data-lucide="plus" class="w-4 h-4 inline mr-1"></i>
                        Yeni Servis
                    </button>
                </div>
                
                <div v-if="services.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Takip No</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Müşteri</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Cihaz</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Arıza</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Durum</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tarih</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">İşlemler</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="service in services" :key="service.id" class="border-b border-slate-100 hover:bg-slate-50 transition-all">
                                <td class="px-4 py-3 font-mono text-sm text-blue-600 font-medium">{{ service.tracking_no }}</td>
                                <td class="px-4 py-3">{{ service.customer_name }}</td>
                                <td class="px-4 py-3">{{ service.device_brand }} {{ service.device_model }}</td>
                                <td class="px-4 py-3 text-sm text-slate-600">{{ service.fault_description }}</td>
                                <td class="px-4 py-3">
                                    <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                                        {{ service.status }}
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-sm text-slate-500">{{ formatDate(service.entry_date) }}</td>
                                <td class="px-4 py-3">
                                    <div class="flex gap-2">
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Detay">
                                            <i data-lucide="eye" class="w-4 h-4 text-slate-600"></i>
                                        </button>
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Düzenle">
                                            <i data-lucide="edit" class="w-4 h-4 text-slate-600"></i>
                                        </button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="inbox" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p class="text-lg font-medium">Henüz servis kaydı yok</p>
                    <p class="text-sm mt-2">Yeni servis eklemek için yukarıdaki butonu kullanın</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            services: []
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/services')
                this.services = await res.json()
            } catch (e) {
                console.error('Services load error:', e)
            }
        },
        formatDate(dateStr) {
            if (!dateStr) return '-'
            try {
                return new Date(dateStr).toLocaleDateString('tr-TR')
            } catch {
                return dateStr
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
