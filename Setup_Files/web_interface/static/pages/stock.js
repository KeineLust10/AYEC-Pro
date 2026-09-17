// Stock Management Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Stok Yönetimi</h3>
                    <button class="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 transition-all">
                        <i data-lucide="plus" class="w-4 h-4 inline mr-1"></i>
                        Yeni Parça
                    </button>
                </div>
                
                <div v-if="parts.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">ID</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Parça Adı</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Stok</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Min. Stok</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Fiyat</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Durum</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">İşlemler</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="part in parts" :key="part.id" class="border-b border-slate-100 hover:bg-slate-50 transition-all">
                                <td class="px-4 py-3 font-mono text-sm text-slate-500">#{{ part.id }}</td>
                                <td class="px-4 py-3 font-medium text-slate-800">{{ part.name }}</td>
                                <td class="px-4 py-3">
                                    <span :class="part.stock <= part.min_stock ? 'text-red-600 font-bold' : 'text-green-600 font-semibold'">
                                        {{ part.stock }}
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-slate-600">{{ part.min_stock }}</td>
                                <td class="px-4 py-3 font-medium">{{ part.price }} ₺</td>
                                <td class="px-4 py-3">
                                    <span v-if="part.stock <= part.min_stock" class="px-2 py-1 bg-red-100 text-red-700 rounded text-xs font-medium">
                                        Kritik
                                    </span>
                                    <span v-else-if="part.stock <= part.min_stock * 2" class="px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs font-medium">
                                        Düşük
                                    </span>
                                    <span v-else class="px-2 py-1 bg-green-100 text-green-700 rounded text-xs font-medium">
                                        Normal
                                    </span>
                                </td>
                                <td class="px-4 py-3">
                                    <div class="flex gap-2">
                                        <button class="p-1 hover:bg-slate-100 rounded" title="Stok Ekle">
                                            <i data-lucide="plus-circle" class="w-4 h-4 text-green-600"></i>
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
                    <i data-lucide="package" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p class="text-lg font-medium">Henüz parça kaydı yok</p>
                    <p class="text-sm mt-2">Yeni parça eklemek için yukarıdaki butonu kullanın</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            parts: []
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/parts')
                this.parts = await res.json()
            } catch (e) {
                console.error('Parts load error:', e)
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
