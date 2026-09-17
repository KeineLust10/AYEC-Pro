
import AddStockModal from './AddStockModal.js';

export default {
    props: ['parts', 'loading', 'openModal'],
    components: { AddStockModal },
    data() {
        return {
            showModal: false
        }
    },
    watch: {
        openModal(val) {
            if (val) this.showModal = true;
        }
    },
    template: `
    <div class="h-full flex flex-col p-8 animate-fade-in space-y-8 relative">
        <!-- HEADER ROW -->
        <div class="flex items-end justify-between">
            <div>
                <h2 class="text-3xl font-bold text-slate-800 tracking-tight">Stok & Envanter Yönetimi</h2>
                <p class="text-slate-500 font-medium mt-1">Ürünler, yedek parçalar ve stok hareketlerini buradan yönetebilirsiniz.</p>
            </div>
            
            <div class="flex gap-4">
                 <div class="flex gap-2">
                    <button class="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-600 font-bold hover:bg-slate-50 transition flex items-center gap-2">
                        <i data-lucide="download" class="w-4 h-4"></i> İçe Aktar
                    </button>
                    <button class="px-5 py-2.5 rounded-xl border border-slate-300 text-slate-600 font-bold hover:bg-slate-50 transition flex items-center gap-2">
                        <i data-lucide="upload" class="w-4 h-4"></i> Dışa Aktar
                    </button>
                 </div>
                 <button class="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2.5 rounded-xl font-bold text-sm shadow-lg shadow-blue-200 transition flex items-center gap-2" @click="showModal = true">
                    <i data-lucide="plus" class="w-5 h-5"></i> Yeni Ürün Ekle
                </button>
            </div>
        </div>

        <!-- TABS -->
        <div class="border-b border-slate-200 flex space-x-8">
            <button class="pb-3 border-b-2 border-blue-600 text-blue-600 font-bold text-sm">📦 Stok Durumu</button>
            <button class="pb-3 border-b-2 border-transparent text-slate-500 font-bold text-sm hover:text-slate-700 transition">📋 Stok Hareketleri</button>
        </div>

        <!-- STAT CARDS -->
        <div class="grid grid-cols-3 gap-6">
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5 hover:border-blue-400 transition cursor-default">
                <div class="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center"><i data-lucide="package" class="w-7 h-7"></i></div>
                <div><div class="text-2xl font-black text-slate-800">{{ parts ? parts.length : 0 }}</div><div class="text-xs font-bold text-slate-400 uppercase tracking-widest">TOPLAM ÜRÜN</div></div>
            </div>
            <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5 hover:border-emerald-400 transition cursor-default">
                <div class="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center"><i data-lucide="wallet" class="w-7 h-7"></i></div>
                <div><div class="text-2xl font-black text-slate-800">{{ totalValue }} ₺</div><div class="text-xs font-bold text-slate-400 uppercase tracking-widest">ENVANTER DEĞERİ</div></div>
            </div>
             <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm flex items-center gap-5 hover:border-red-400 transition cursor-default">
                <div class="w-14 h-14 rounded-full bg-slate-50 text-slate-400 flex items-center justify-center"><i data-lucide="alert-triangle" class="w-7 h-7"></i></div>
                <div><div class="text-2xl font-black text-slate-800">0</div><div class="text-xs font-bold text-slate-400 uppercase tracking-widest">KRİTİK STOK</div></div>
            </div>
        </div>

        <!-- Main Content Area -->
        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
            <!-- Toolbar -->
            <div class="p-4 border-b border-slate-100 flex items-center gap-4 bg-white">
                <div class="relative w-80">
                     <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                     <input type="text" placeholder="Barkod veya Ürün Adı ile Ara..." class="w-full pl-9 pr-4 py-2.5 rounded-lg border border-slate-200 bg-slate-50 focus:bg-white focus:border-blue-500 transition font-medium text-sm">
                </div>
                <button class="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2.5 rounded-lg font-bold text-sm shadow-md shadow-amber-200 transition flex items-center gap-2">
                    <i data-lucide="shopping-cart" class="w-4 h-4"></i> Hızlı Satış
                </button>
                <button class="bg-white border border-red-200 text-red-600 hover:bg-red-50 px-4 py-2.5 rounded-lg font-bold text-sm transition flex items-center gap-2">
                    <i data-lucide="alert-octagon" class="w-4 h-4"></i> Kritik Stoklar
                </button>
                <div class="flex-1"></div>
                <button class="text-slate-400 hover:text-blue-600 font-bold text-sm flex items-center gap-1" @click="$emit('refresh')"><i data-lucide="refresh-cw" class="w-4 h-4"></i> Yenile</button>
                <button class="text-emerald-500 hover:text-emerald-700 font-bold text-sm flex items-center gap-1"><i data-lucide="file-spreadsheet" class="w-4 h-4"></i> Excel</button>
            </div>

            <!-- Table -->
            <div class="flex-1 overflow-auto">
                 <table class="w-full text-left">
                    <thead class="bg-slate-50 sticky top-0 z-10 border-b border-slate-200">
                        <tr>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider w-20">ID</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider font-mono">BARKOD</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">PARÇA / ÜRÜN ADI</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">KATEGORİ</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider text-center">STOK</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">FİYAT</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">LİMİT</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                         <tr v-if="!parts || parts.length === 0"><td colspan="7" class="p-16 text-center text-slate-400 flex flex-col items-center"><i data-lucide="package-open" class="w-16 h-16 mb-4 opacity-20"></i><span class="font-medium text-lg">Stok Kaydı Bulunamadı</span><span class="text-sm mt-1">Envanteriniz boş görünüyor. Yeni ürün ekleyerek başlayın.</span><button class="mt-4 text-blue-600 font-bold hover:underline" @click="showModal = true">Yeni Ürün Ekle</button></td></tr>
                         <tr v-else v-for="p in parts" :key="p.id" class="hover:bg-blue-50/50 transition cursor-pointer group">
                             <td class="px-6 py-4 text-slate-500 font-mono text-xs">{{ p.id }}</td>
                             <td class="px-6 py-4 font-mono text-slate-600 text-xs bg-slate-50 rounded mx-2 w-max border border-slate-100 px-2 py-0.5">{{ p.code || '-' }}</td>
                             <td class="px-6 py-4 font-bold text-slate-700">{{ p.part_name }}</td>
                             <td class="px-6 py-4 text-slate-500 text-sm">{{ p.category || 'Genel' }}</td>
                             <td class="px-6 py-4 text-center">
                                 <span class="px-3 py-1 rounded-full font-bold text-xs" :class="p.stock <= (p.min_stock || 5) ? 'bg-red-50 text-red-600 ring-1 ring-red-100' : 'bg-emerald-50 text-emerald-600 ring-1 ring-emerald-100'">
                                     {{ p.stock }} Adet
                                 </span>
                             </td>
                             <td class="px-6 py-4 font-bold text-slate-700">{{ p.price }} ₺</td>
                             <td class="px-6 py-4 text-slate-400 text-xs font-bold">{{ p.min_stock || 5 }}</td>
                         </tr>
                    </tbody>
                 </table>
            </div>
        </div>

        <!-- MODAL -->
        <AddStockModal v-if="showModal" @close="showModal = false" @saved="$emit('refresh')" />
    </div>
    `,
    computed: {
        totalValue() {
            if (!this.parts) return "0.00";
            let sum = 0;
            this.parts.forEach(p => sum += (parseFloat(p.price) || 0) * (parseInt(p.stock) || 0));
            return sum.toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }
    },
    updated() { lucide.createIcons() },
    mounted() { lucide.createIcons(); if (this.openModal) { this.showModal = true; } }
}
