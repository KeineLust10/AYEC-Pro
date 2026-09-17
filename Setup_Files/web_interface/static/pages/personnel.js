// Personnel Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Personel Listesi</h3>
                    <button class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700">
                        <i data-lucide="user-plus" class="w-4 h-4 inline mr-1"></i>Yeni Personel
                    </button>
                </div>
                <div v-if="personnel.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Ad Soyad</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Rol</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Telefon</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Email</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Maaş</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="p in personnel" :key="p.id" class="border-b border-slate-100 hover:bg-slate-50">
                                <td class="px-4 py-3 font-medium">{{ p.name }}</td>
                                <td class="px-4 py-3"><span class="px-2 py-1 bg-purple-100 text-purple-700 rounded text-xs">{{ p.role }}</span></td>
                                <td class="px-4 py-3">{{ p.phone }}</td>
                                <td class="px-4 py-3">{{ p.email }}</td>
                                <td class="px-4 py-3 font-medium">{{ p.salary ? p.salary.toLocaleString('tr-TR') + ' ₺' : '-' }}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="users" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p>Henüz personel kaydı yok</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return { personnel: [] }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/personnel')
                this.personnel = await res.json()
            } catch (e) {
                console.error('Personnel load error:', e)
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
