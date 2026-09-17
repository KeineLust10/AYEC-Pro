// Dashboard Page Component
export default {
    template: `
        <div class="animate-fade-in space-y-6">
            <!-- Stats Cards -->
            <div class="grid grid-cols-4 gap-6">
                <div class="bg-white p-6 rounded-2xl border border-slate-200 hover:shadow-lg transition-all">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-blue-100 rounded-xl">
                            <i data-lucide="activity" class="w-6 h-6 text-blue-600"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-800">{{ stats.active_services || 0 }}</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Aktif Servis</p>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-200 hover:shadow-lg transition-all">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-emerald-100 rounded-xl">
                            <i data-lucide="plus-circle" class="w-6 h-6 text-emerald-600"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-800">{{ stats.today_new || 0 }}</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Bugün Gelen</p>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-200 hover:shadow-lg transition-all">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-purple-100 rounded-xl">
                            <i data-lucide="users" class="w-6 h-6 text-purple-600"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-800">{{ stats.total_customers || 0 }}</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Toplam Müşteri</p>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-200 hover:shadow-lg transition-all">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-amber-100 rounded-xl">
                            <i data-lucide="alert-triangle" class="w-6 h-6 text-amber-600"></i>
                        </div>
                    </div>
                    <h3 class="text-3xl font-bold text-slate-800">{{ stats.low_stock || 0 }}</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Kritik Stok</p>
                </div>
            </div>

            <!-- Recent Activities -->
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <h3 class="font-bold text-lg mb-4">Son Aktiviteler</h3>
                <div v-if="services.length > 0" class="space-y-3">
                    <div v-for="service in services.slice(0, 5)" :key="service.id" 
                         class="flex items-center p-3 bg-slate-50 rounded-lg hover:bg-slate-100 transition-all cursor-pointer">
                        <i data-lucide="package" class="w-5 h-5 text-blue-600 mr-3"></i>
                        <div class="flex-1">
                            <span class="font-medium">{{ service.tracking_no }}</span> - 
                            {{ service.customer_name }} / {{ service.device_brand }} {{ service.device_model }}
                        </div>
                        <span class="text-xs text-slate-500">{{ formatDate(service.entry_date) }}</span>
                    </div>
                </div>
                <div v-else class="text-center py-8 text-slate-400">
                    <i data-lucide="inbox" class="w-12 h-12 mx-auto mb-2 opacity-50"></i>
                    <p>Henüz aktivite yok</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            stats: {},
            services: []
        }
    },
    methods: {
        async loadData() {
            try {
                const statsRes = await fetch('/api/dashboard')
                this.stats = await statsRes.json()

                const servicesRes = await fetch('/api/services')
                this.services = await servicesRes.json()
            } catch (e) {
                console.error('Dashboard load error:', e)
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
