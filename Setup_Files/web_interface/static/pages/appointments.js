// Appointments Page Component
export default {
    template: `
        <div class="animate-fade-in">
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">Randevu Takvimi</h3>
                    <button @click="showNewAppointment = true" class="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-all">
                        <i data-lucide="calendar-plus" class="w-4 h-4 inline mr-1"></i>
                        Yeni Randevu
                    </button>
                </div>
                
                <div v-if="appointments.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tarih</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Saat</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Müşteri</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Telefon</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Hizmet</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Durum</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">İşlemler</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="apt in appointments" :key="apt.id" class="border-b border-slate-100 hover:bg-slate-50">
                                <td class="px-4 py-3">{{ formatDate(apt.date) }}</td>
                                <td class="px-4 py-3 font-medium">{{ apt.time }}</td>
                                <td class="px-4 py-3">{{ apt.customer_name }}</td>
                                <td class="px-4 py-3">{{ apt.phone }}</td>
                                <td class="px-4 py-3 text-sm">{{ apt.description || '-' }}</td>
                                <td class="px-4 py-3">
                                    <span :class="getStatusClass(apt.status)">{{ apt.status }}</span>
                                </td>
                                <td class="px-4 py-3">
                                    <div class="flex gap-2">
                                        <button class="p-1 hover:bg-slate-100 rounded"><i data-lucide="check" class="w-4 h-4 text-green-600"></i></button>
                                        <button class="p-1 hover:bg-slate-100 rounded"><i data-lucide="x" class="w-4 h-4 text-red-600"></i></button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="calendar" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p>Henüz randevu yok</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            appointments: [],
            showNewAppointment: false
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/appointments')
                this.appointments = await res.json()
            } catch (e) {
                console.error('Appointments load error:', e)
            }
        },
        formatDate(dateStr) {
            if (!dateStr) return '-'
            try {
                return new Date(dateStr).toLocaleDateString('tr-TR')
            } catch {
                return dateStr
            }
        },
        getStatusClass(status) {
            const classes = {
                'Bekliyor': 'px-2 py-1 bg-yellow-100 text-yellow-700 rounded text-xs',
                'Onaylandı': 'px-2 py-1 bg-green-100 text-green-700 rounded text-xs',
                'İptal': 'px-2 py-1 bg-red-100 text-red-700 rounded text-xs'
            }
            return classes[status] || 'px-2 py-1 bg-slate-100 text-slate-700 rounded text-xs'
        }
    },
    mounted() {
        this.loadData()
    },
    updated() {
        if (window.lucide) window.lucide.createIcons()
    }
}
