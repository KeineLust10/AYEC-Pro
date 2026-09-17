export default {
    props: ['customer'],
    data() {
        return {
            history: [],
            loading: false
        }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100] flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-4xl max-h-[90vh] flex flex-col overflow-hidden">
            <!-- Header -->
            <div class="px-6 py-4 bg-slate-50 border-b border-slate-200 flex justify-between items-center flex-shrink-0">
                <div>
                    <h3 class="font-bold text-xl text-slate-800">Servis Geçmişi</h3>
                    <p class="text-xs text-slate-500 font-mono">{{ customer.name }}</p>
                </div>
                <button @click="$emit('close')" class="p-2 hover:bg-slate-200 rounded-full transition">
                    <i data-lucide="x" class="w-6 h-6 text-slate-500"></i>
                </button>
            </div>

            <!-- Content -->
            <div class="flex-1 overflow-y-auto p-6 bg-slate-50/50">
                <div v-if="loading" class="text-center p-12 text-slate-400">
                    <i data-lucide="loader" class="w-8 h-8 animate-spin mx-auto mb-3"></i>
                    Yükleniyor...
                </div>
                
                <div v-else-if="history.length === 0" class="text-center p-12 bg-white rounded-xl border border-slate-200 shadow-sm">
                    <i data-lucide="history" class="w-12 h-12 mx-auto mb-3 text-slate-300"></i>
                    <p class="text-slate-500">Kayıtlı işlem bulunamadı.</p>
                </div>

                <div v-else class="space-y-4">
                    <div v-for="item in history" :key="item.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex items-center gap-4 hover:shadow-md transition">
                        <!-- Icon -->
                        <div class="w-12 h-12 rounded-full flex items-center justify-center flex-shrink-0" :class="getIconClass(item.type)">
                            <i :data-lucide="getIcon(item.type)" class="w-6 h-6"></i>
                        </div>

                        <!-- Info -->
                        <div class="flex-1">
                            <div class="flex justify-between items-start">
                                <div>
                                    <h4 class="font-bold text-slate-800 text-sm">{{ item.description }}</h4>
                                    <span class="text-xs font-bold px-2 py-0.5 rounded-full mt-1 inline-block" :class="getStatusClass(item.status)">{{ item.status }}</span>
                                </div>
                                <div class="text-right">
                                    <div class="font-bold text-slate-800">{{ item.amount > 0 ? formatCurrency(item.amount) : '-' }}</div>
                                    <div class="text-xs text-slate-400">{{ formatDate(item.date) }}</div>
                                </div>
                            </div>
                            <div class="text-xs text-slate-500 mt-2 flex items-center gap-2">
                                <span class="bg-slate-100 px-2 py-1 rounded text-slate-600 font-mono">{{ item.type }}</span>
                                <span v-if="item.notes" class="truncate max-w-xs" :title="item.notes">- {{ item.notes }}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `,
    methods: {
        async loadHistory() {
            this.loading = true;
            try {
                const res = await fetch(`/api/customers/${this.customer.id}/history`);
                if (res.ok) {
                    this.history = await res.json();
                }
            } catch (e) {
                console.error(e);
            } finally {
                this.loading = false;
                this.$nextTick(() => lucide.createIcons());
            }
        },
        getIcon(type) {
            if (type === 'Cihaz Servisi') return 'smartphone';
            if (type === 'Hizmet') return 'zap';
            if (type === 'Satış') return 'shopping-bag';
            if (type === 'Tahsilat') return 'wallet';
            return 'file-text';
        },
        getIconClass(type) {
            if (type === 'Cihaz Servisi') return 'bg-blue-100 text-blue-600';
            if (type === 'Hizmet') return 'bg-purple-100 text-purple-600';
            if (type === 'Tahsilat') return 'bg-green-100 text-green-600';
            return 'bg-slate-100 text-slate-600';
        },
        getStatusClass(status) {
            if (!status) return 'bg-slate-100 text-slate-500';
            if (['Tamamlandı', 'Teslim Edildi'].includes(status)) return 'bg-green-100 text-green-700';
            if (['Yeni Kayıt', 'Bekliyor'].includes(status)) return 'bg-yellow-100 text-yellow-700';
            if (['İptal'].includes(status)) return 'bg-red-100 text-red-700';
            return 'bg-blue-100 text-blue-700';
        },
        formatDate(dateStr) {
            if (!dateStr) return '-';
            return new Date(dateStr).toLocaleDateString('tr-TR');
        },
        formatCurrency(val) {
            return parseFloat(val).toFixed(2) + ' ₺';
        }
    },
    mounted() {
        this.loadHistory();
    }
}
