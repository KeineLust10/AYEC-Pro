// Accounting Page Component
export default {
    template: `
        <div class="animate-fade-in space-y-6">
            <!-- Summary Cards -->
            <div class="grid grid-cols-3 gap-6">
                <div class="bg-white p-6 rounded-2xl border border-slate-200">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-green-100 rounded-xl"><i data-lucide="trending-up" class="w-6 h-6 text-green-600"></i></div>
                    </div>
                    <h3 class="text-2xl font-bold text-slate-800">{{ totalIncome.toLocaleString('tr-TR') }} ₺</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Toplam Gelir</p>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-200">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-red-100 rounded-xl"><i data-lucide="trending-down" class="w-6 h-6 text-red-600"></i></div>
                    </div>
                    <h3 class="text-2xl font-bold text-slate-800">{{ totalExpense.toLocaleString('tr-TR') }} ₺</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Toplam Gider</p>
                </div>
                <div class="bg-white p-6 rounded-2xl border border-slate-200">
                    <div class="flex items-center justify-between mb-4">
                        <div class="p-3 bg-blue-100 rounded-xl"><i data-lucide="wallet" class="w-6 h-6 text-blue-600"></i></div>
                    </div>
                    <h3 class="text-2xl font-bold text-slate-800">{{ (totalIncome - totalExpense).toLocaleString('tr-TR') }} ₺</h3>
                    <p class="text-xs text-slate-500 font-medium mt-1">Net Kar/Zarar</p>
                </div>
            </div>

            <!-- Transactions Table -->
            <div class="bg-white rounded-2xl border border-slate-200 p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="font-bold text-lg">İşlem Geçmişi</h3>
                    <button class="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700">
                        <i data-lucide="plus" class="w-4 h-4 inline mr-1"></i>Yeni İşlem
                    </button>
                </div>
                
                <div v-if="transactions.length > 0" class="overflow-x-auto">
                    <table class="w-full">
                        <thead class="bg-slate-100 border-b border-slate-200">
                            <tr>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tarih</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Açıklama</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Kategori</th>
                                <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tip</th>
                                <th class="px-4 py-3 text-right text-xs font-bold text-slate-600 uppercase">Tutar</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="tx in transactions" :key="tx.id" class="border-b border-slate-100 hover:bg-slate-50">
                                <td class="px-4 py-3">{{ formatDate(tx.date) }}</td>
                                <td class="px-4 py-3">{{ tx.description }}</td>
                                <td class="px-4 py-3 text-sm">{{ tx.category }}</td>
                                <td class="px-4 py-3">
                                    <span :class="tx.type === 'Gelir' ? 'px-2 py-1 bg-green-100 text-green-700 rounded text-xs' : 'px-2 py-1 bg-red-100 text-red-700 rounded text-xs'">
                                        {{ tx.type }}
                                    </span>
                                </td>
                                <td class="px-4 py-3 text-right font-bold" :class="tx.type === 'Gelir' ? 'text-green-600' : 'text-red-600'">
                                    {{ tx.type === 'Gelir' ? '+' : '-' }}{{ tx.amount.toLocaleString('tr-TR') }} ₺
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div v-else class="text-center py-12 text-slate-400">
                    <i data-lucide="receipt" class="w-16 h-16 mx-auto mb-4 opacity-50"></i>
                    <p>Henüz işlem kaydı yok</p>
                </div>
            </div>
        </div>
    `,
    data() {
        return {
            transactions: []
        }
    },
    computed: {
        totalIncome() {
            return this.transactions.filter(t => t.type === 'Gelir').reduce((sum, t) => sum + t.amount, 0)
        },
        totalExpense() {
            return this.transactions.filter(t => t.type === 'Gider').reduce((sum, t) => sum + t.amount, 0)
        }
    },
    methods: {
        async loadData() {
            try {
                const res = await fetch('/api/accounting')
                this.transactions = await res.json()
            } catch (e) {
                console.error('Accounting load error:', e)
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
