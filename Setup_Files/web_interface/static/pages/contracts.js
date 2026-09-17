// Contracts Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Sözleşme Listesi</h3>
                    <button class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700">
                        <i data-lucide="file-plus" class="w-4 h-4 inline mr-1"></i>Yeni Sözleşme
                    </button>
                </div>
                <div v-if="contracts.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Müşteri</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Sözleşme Tipi</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Başlangıç</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Bitiş</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tutar</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Durum</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="c in contracts" :key="c.id" class="border-b border-slate-100 hover:bg-slate-50">
                                <td class="px-4 py-3 font-medium">{{ c.customer_name || 'Müşteri #' + c.customer_id }}</td>
                                <td class="px-4 py-3">{{ c.contract_type }}</td>
                                <td class="px-4 py-3">{{ formatDate(c.start_date) }}</td>
                                <td class="px-4 py-3">{{ formatDate(c.end_date) }}</td>
                                <td class="px-4 py-3 font-medium">{{ c.amount ? c.amount.toLocaleString('tr-TR') + ' ₺' : '-' }}</td>
                                <td class="px-4 py-3">
                                    <span :class="c.status === 'Active' ? 'px-2 py-1 bg-green-100 text-green-700 rounded text-xs' : 'px-2 py-1 bg-red-100 text-red-700 rounded text-xs'">
                                        {{ c.status === 'Active' ? 'Aktif' : 'Pasif' }}
                                    </span>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="file-text" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p>Henüz sözleşme kaydı yok</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return { contracts: [] }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/contracts')
                this.contracts = await res.json()
            } catch (e) {
                console.error('Contracts load error:', e)
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
