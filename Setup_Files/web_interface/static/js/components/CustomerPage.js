import AddCustomerModal from './AddCustomerModal.js';
import AddServiceToCustomerModal from './AddServiceToCustomerModal.js';
import ServiceHistoryModal from './ServiceHistoryModal.js';

export default {
    props: ['customers', 'loading'],
    components: { AddCustomerModal, AddServiceToCustomerModal, ServiceHistoryModal },
    data() {
        return {
            showModal: false,
            editMode: false,
            actionCustomer: null,
            modalCustomer: null,
            showServiceModal: false,
            showHistoryModal: false
        }
    },
    template: `
    <div class="h-full flex flex-col p-8 animate-fade-in relative">
        <!-- HEADER TITLE -->
        <div class="mb-6">
            <h2 class="text-3xl font-bold text-slate-800 tracking-tight">👥 Müşteri Yönetim Merkezi</h2>
            <p class="text-slate-500 font-medium">Müşteri portföyü, borç/alacak takibi ve detaylı analizler</p>
        </div>

        <!-- 1. BANNER BUTTONS ROW -->
        <div class="flex gap-6 mb-8 h-16">
            <button class="flex-1 bg-blue-600 hover:bg-blue-700 text-white rounded-xl font-bold text-lg shadow-lg shadow-blue-200 transition transform hover:-translate-y-1 flex items-center justify-center gap-3">
                <i data-lucide="users" class="w-6 h-6"></i> TÜM MÜŞTERİLER
            </button>
            <button class="flex-[0.8] bg-red-500 hover:bg-red-600 text-white rounded-xl font-bold text-lg shadow-lg shadow-red-200 transition transform hover:-translate-y-1 flex items-center justify-center gap-3">
                <i data-lucide="alert-circle" class="w-6 h-6"></i> BORCU BULUNANLAR
            </button>
            <button class="flex-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl font-bold text-lg shadow-lg shadow-emerald-200 transition transform hover:-translate-y-1 flex items-center justify-center gap-3" @click="openAddModal">
                <i data-lucide="user-plus" class="w-6 h-6"></i> + YENİ MÜŞTERİ EKLE
            </button>
        </div>

        <!-- 2. TOOLBAR & SEARCH -->
        <div class="bg-white rounded-t-2xl border border-slate-200 p-4 flex items-center justify-between shadow-sm">
            <div class="flex gap-2">
                <button class="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium text-sm flex items-center gap-2" @click="copyToClipboard"><i data-lucide="copy" class="w-4 h-4"></i> Kopyala</button>
                <button class="px-4 py-2 rounded-lg border border-slate-200 text-green-600 hover:bg-green-50 font-medium text-sm flex items-center gap-2"><i data-lucide="sheet" class="w-4 h-4"></i> Excel / CSV</button>
                <button class="px-4 py-2 rounded-lg border border-slate-200 text-rose-600 hover:bg-rose-50 font-medium text-sm flex items-center gap-2"><i data-lucide="file-text" class="w-4 h-4"></i> PDF</button>
                <button class="px-4 py-2 rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 font-medium text-sm flex items-center gap-2" @click="printPage"><i data-lucide="printer" class="w-4 h-4"></i> Yazdır</button>
            </div>
            
            <div class="relative w-72">
                <i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
                <input type="text" placeholder="Müşteri Ara..." class="w-full pl-9 pr-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:bg-white focus:border-blue-500 transition shadow-inner font-medium">
            </div>
        </div>

        <!-- 3. TABLE -->
        <div class="flex-1 bg-white border-x border-b border-slate-200 rounded-b-2xl shadow-sm overflow-hidden flex flex-col relative z-0">
            <div class="flex-1 overflow-auto">
                <table class="w-full text-left border-collapse">
                    <thead class="bg-slate-50 sticky top-0 z-10 border-b border-slate-200 shadow-sm">
                        <tr>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">M.NO</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">MÜŞTERİ ADI</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">TELEFON</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider">E-POSTA</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider text-right">BAKİYE</th>
                            <th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider text-center w-64">İŞLEMLER</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y divide-slate-100">
                        <tr v-if="loading"><td colspan="6" class="p-8 text-center text-slate-400">Yükleniyor...</td></tr>
                        <tr v-else-if="!customers || customers.length === 0"><td colspan="6" class="p-12 text-center text-slate-400 flex flex-col items-center"><i data-lucide="users" class="w-12 h-12 mb-4 opacity-20"></i>Henüz müşteri yok</td></tr>
                        
                        <tr v-else v-for="c in customers" :key="c.id" class="hover:bg-blue-50/30 transition-colors group relative z-0 h-20">
                            <td class="px-6 py-5 whitespace-nowrap">
                                <span class="bg-indigo-600 text-white px-2.5 py-1 rounded font-bold font-mono text-xs shadow-md shadow-indigo-200">{{ c.id }}</span>
                            </td>
                            <td class="px-6 py-5 font-bold text-slate-700">{{ c.name }}</td>
                            <td class="px-6 py-5 font-mono text-slate-600">{{ c.phone }}</td>
                            <td class="px-6 py-5 text-slate-500 text-sm">{{ c.email || '-' }}</td>
                            <td class="px-6 py-5 text-right font-mono font-bold" :class="c.balance > 0 ? 'text-red-600' : (c.balance < 0 ? 'text-emerald-600' : 'text-slate-400')">
                                <span>{{ formatBalance(c.balance) }} ₺</span>
                                <span v-if="c.balance > 0" class="text-xs font-normal ml-1">(Borç)</span>
                                <span v-else-if="c.balance < 0" class="text-xs font-normal ml-1">(Alacak)</span>
                            </td>
                            <td class="px-6 py-5 text-center">
                                <button @click.prevent.stop="openActionMenu(c)" class="bg-emerald-500 hover:bg-emerald-600 active:bg-emerald-700 text-white px-5 py-2 rounded-lg font-semibold text-sm shadow-sm shadow-emerald-200/50 flex items-center justify-center gap-1.5 mx-auto transition-all cursor-pointer relative z-50 hover:shadow-md hover:-translate-y-0.5 active:translate-y-0 whitespace-nowrap">
                                    <i data-lucide="more-vertical" class="w-4 h-4"></i>
                                    <span>İşlem Yap</span>
                                    <i data-lucide="chevron-down" class="w-3.5 h-3.5"></i>
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- FOOTER -->
            <div class="h-12 border-t border-slate-100 bg-slate-50 px-6 flex items-center justify-between flex-shrink-0">
                <span class="text-xs text-slate-500 font-bold">Toplam {{ customers ? customers.length : 0 }} kayıt listelendi</span>
                <div class="flex gap-2">
                    <button class="p-1 rounded hover:bg-slate-200 text-slate-400"><i data-lucide="chevron-left" class="w-4 h-4"></i></button>
                    <button class="p-1 rounded hover:bg-slate-200 text-slate-400"><i data-lucide="chevron-right" class="w-4 h-4"></i></button>
                </div>
            </div>
        </div>

        <!-- ACTION MENU MODAL (FIXED CENTER) -->
        <div v-if="actionCustomer" class="fixed inset-0 bg-slate-900/60 z-[9999] flex items-center justify-center animate-fade-in backdrop-blur-sm" @click.self="closeActionMenu">
            <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm max-h-[90vh] overflow-hidden animate-fade-in-up transform transition-all scale-100 border border-slate-200 relative flex flex-col">
                <!-- MENU HEADER -->
                <div class="bg-slate-50 px-6 py-4 border-b border-slate-100 flex justify-between items-center flex-shrink-0">
                    <div>
                        <h3 class="font-bold text-slate-800 text-lg">{{ actionCustomer.name }}</h3>
                        <p class="text-xs text-slate-500 font-mono">{{ actionCustomer.phone }}</p>
                    </div>
                    <button @click="closeActionMenu" class="bg-slate-200 p-1.5 rounded-full hover:bg-slate-300 transition text-slate-600 hover:text-red-500 relative z-50 cursor-pointer"><i data-lucide="x" class="w-5 h-5"></i></button>
                </div>
                
                <!-- MENU ITEMS (SCROLLABLE) -->
                <div class="p-3 overflow-y-auto custom-scrollbar">
                    
                    <!-- SECTION 1: INFO -->
                    <div class="px-2 py-1 text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Müşteri Bilgileri</div>
                    <div class="grid grid-cols-2 gap-2 mb-3">
                         <button class="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 p-3 rounded-xl flex flex-col items-center justify-center gap-2 transition group border border-indigo-100" @click="featureNotReady('Müşteri Karnesi')">
                            <i data-lucide="pie-chart" class="w-6 h-6 mb-1"></i>
                            <span class="text-xs font-bold">360° Karne</span>
                        </button>
                         <button class="bg-amber-50 hover:bg-amber-100 text-amber-700 p-3 rounded-xl flex flex-col items-center justify-center gap-2 transition group border border-amber-100" @click="featureNotReady('Müşteri Notları')">
                            <i data-lucide="sticky-note" class="w-6 h-6 mb-1"></i>
                            <span class="text-xs font-bold">Özel Notlar</span>
                        </button>
                    </div>

                    <button @click="editCustomer" class="w-full bg-slate-50 hover:bg-slate-100 text-slate-700 p-3 rounded-xl flex items-center gap-3 transition mb-2 border border-slate-100">
                        <div class="bg-white p-1.5 rounded-lg border border-slate-200"><i data-lucide="edit-3" class="w-4 h-4"></i></div>
                        <div class="text-sm font-bold">Bilgileri Düzenle</div>
                    </button>
                     <button @click="openHistory" class="w-full bg-slate-50 hover:bg-slate-100 text-slate-700 p-3 rounded-xl flex items-center gap-3 transition mb-2 border border-slate-100">
                        <div class="bg-white p-1.5 rounded-lg border border-slate-200"><i data-lucide="history" class="w-4 h-4"></i></div>
                        <div class="text-sm font-bold">Servis Geçmişi</div>
                    </button>
                     <button @click="featureNotReady('Cari Ekstre')" class="w-full bg-slate-50 hover:bg-slate-100 text-slate-700 p-3 rounded-xl flex items-center gap-3 transition mb-2 border border-slate-100">
                        <div class="bg-white p-1.5 rounded-lg border border-slate-200"><i data-lucide="file-bar-chart-2" class="w-4 h-4"></i></div>
                        <div class="text-sm font-bold">Cari Ekstre</div>
                    </button>

                    <div class="h-px bg-slate-100 my-2"></div>

                    <!-- SECTION 2: ACTIONS -->
                    <div class="px-2 py-1 text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Hızlı İşlemler</div>
                     <button @click="addServiceToCustomer" class="w-full bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-xl flex items-center gap-3 transition mb-2 shadow-lg shadow-blue-200">
                        <div class="bg-white/20 p-1.5 rounded-lg"><i data-lucide="plus-circle" class="w-4 h-4"></i></div>
                        <div class="text-sm font-bold">Hızlı Hizmet Ekle</div>
                        <i data-lucide="chevron-right" class="ml-auto w-4 h-4 opacity-70"></i>
                    </button>

                    <div class="grid grid-cols-3 gap-2 mb-3">
                         <button class="bg-slate-50 hover:bg-slate-100 text-slate-600 p-2 rounded-xl flex flex-col items-center justify-center gap-1 transition border border-slate-100" @click="featureNotReady('Fatura Kes')">
                            <i data-lucide="file-text" class="w-5 h-5"></i>
                            <span class="text-[10px] font-bold">Fatura</span>
                        </button>
                         <button class="bg-slate-50 hover:bg-slate-100 text-slate-600 p-2 rounded-xl flex flex-col items-center justify-center gap-1 transition border border-slate-100" @click="featureNotReady('Randevu Ver')">
                            <i data-lucide="calendar" class="w-5 h-5"></i>
                            <span class="text-[10px] font-bold">Randevu</span>
                        </button>
                         <button class="bg-slate-50 hover:bg-slate-100 text-slate-600 p-2 rounded-xl flex flex-col items-center justify-center gap-1 transition border border-slate-100" @click="featureNotReady('Tahsilat Al')">
                            <i data-lucide="wallet" class="w-5 h-5"></i>
                            <span class="text-[10px] font-bold">Tahsilat</span>
                        </button>
                    </div>

                    <div class="h-px bg-slate-100 my-2"></div>

                    <!-- SECTION 3: COMMUNICATION -->
                    <div class="px-2 py-1 text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">İletişim</div>
                    <div class="grid grid-cols-2 gap-2 mb-2">
                         <button class="bg-green-50 hover:bg-green-100 text-green-700 p-3 rounded-xl flex items-center justify-center gap-2 transition border border-green-100" @click="sendWhatsapp">
                            <i data-lucide="message-circle" class="w-5 h-5"></i> <span class="text-xs font-bold">WhatsApp</span>
                        </button>
                         <button class="bg-sky-50 hover:bg-sky-100 text-sky-700 p-3 rounded-xl flex items-center justify-center gap-2 transition border border-sky-100" @click="sendEmail">
                            <i data-lucide="mail" class="w-5 h-5"></i> <span class="text-xs font-bold">E-Posta</span>
                        </button>
                    </div>

                    <div class="h-px bg-slate-100 my-2"></div>
                    
                    <!-- SECTION 4: DELETE -->
                    <button @click="deleteCustomer" class="w-full bg-red-50 hover:bg-red-100 text-red-600 p-3 rounded-xl flex items-center justify-center gap-2 transition font-bold text-sm active:scale-95 group">
                        <i data-lucide="trash-2" class="w-4 h-4 group-hover:scale-110 transition-transform"></i> Müşteriyi Sil
                    </button>
                </div>
            </div>
        </div>

        <!-- ADD/EDIT CUSTOMER MODAL -->
        <AddCustomerModal 
            v-if="showModal" 
            :edit-mode="editMode" 
            :existing-customer="modalCustomer" 
            @close="showModal = false" 
            @saved="onSaved" 
        />

        <!-- ADD SERVICE TO CUSTOMER MODAL -->
        <AddServiceToCustomerModal
            v-if="showServiceModal"
            :customer="actionCustomer"
            @close="showServiceModal = false; closeActionMenu()"
            @saved="$emit('refresh')"
        />

        <!-- SERVICE HISTORY MODAL -->
        <ServiceHistoryModal
            v-if="showHistoryModal"
            :customer="actionCustomer"
            @close="showHistoryModal = false"
        />
    </div>
    `,
    methods: {
        openAddModal() {
            this.modalCustomer = null;
            this.editMode = false;
            this.showModal = true;
        },
        openActionMenu(customer) {
            this.actionCustomer = customer;
            this.$forceUpdate();
            this.$nextTick(() => lucide.createIcons());
        },
        closeActionMenu() {
            this.actionCustomer = null;
        },
        copyToClipboard() { alert("Liste panoya kopyalandı! (Demo)"); },
        printPage() { window.print(); },
        startProcess() {
            if (this.actionCustomer) {
                this.$emit('open-wizard', this.actionCustomer);
                this.closeActionMenu();
            }
        },
        openHistory() {
            if (this.actionCustomer) {
                this.showHistoryModal = true;
                // closeActionMenu çağırmıyoruz çünkü modal actionCustomer'a ihtiyaç duyuyor.
                // Modal kapandığında actionCustomer belki sıfırlanabilir ama şimdilik kalsın.
                // Aslında ServiceHistoryModal z-index'i yüksek olduğu için üstte görünür.
                // Background click ile action menu kapanabilir.
                // En iyisi modal'a customer prop'u pass ediyoruz, sonra menüyü kapatıyoruz?
                // Hayır, v-if="actionCustomer" menüyü tutuyor. 
                // Biz modal'a :customer="actionCustomer" veriyoruz. Menü kapanırsa actionCustomer null olur, modal hata verir.
                // Çözüm: Modal için ayrı bir 'historyCustomer' data property tutmak VEYA
                // Modal açıkken menüyü gizlemek ama actionCustomer'ı null yapmamak.
                // Basit çözüm: Modal açıkken menüyü kapatma. Modal z-index > Menu z-index.
            }
        },
        addServiceToCustomer() {
            if (this.actionCustomer) {
                this.showServiceModal = true;
            }
        },
        editCustomer() {
            if (this.actionCustomer) {
                this.modalCustomer = { ...this.actionCustomer };
                this.editMode = true;
                this.showModal = true;
                this.closeActionMenu();
            }
        },
        async deleteCustomer() {
            if (!confirm(`"${this.actionCustomer.name}" isimli müşteriyi silmek istediğinize emin misiniz?`)) return;
            try {
                const res = await fetch(`/api/customers/${this.actionCustomer.id}`, { method: 'DELETE' });
                if (res.ok) {
                    alert('Müşteri silindi.');
                    this.$emit('refresh');
                } else {
                    alert('Silinemedi.');
                }
            } catch (e) { console.error(e); alert('Hata.'); }
            this.closeActionMenu();
        },
        sendWhatsapp() {
            if (!this.actionCustomer || !this.actionCustomer.phone) {
                alert('Telefon numarası bulunamadı.');
                return;
            }
            let phone = this.actionCustomer.phone.replace(/[^0-9]/g, '');
            if (phone.startsWith('0')) phone = '9' + phone;
            else if (phone.length === 10) phone = '90' + phone;
            window.open(`https://wa.me/${phone}`, '_blank');
            this.closeActionMenu();
        },
        sendEmail() {
            if (!this.actionCustomer || !this.actionCustomer.email) {
                alert('E-posta adresi bulunamadı.');
                return;
            }
            window.location.href = `mailto:${this.actionCustomer.email}`;
            this.closeActionMenu();
        },
        featureNotReady(featureName) {
            alert(`${featureName} özelliği çok yakında kullanıma sunulacak.`);
            this.closeActionMenu();
        },
        onSaved() {
            this.$emit('refresh');
            this.showModal = false;
            this.modalCustomer = null;
        },
        formatBalance(balance) {
            const amount = Math.abs(balance || 0);
            return amount.toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        }
    },
    updated() { lucide.createIcons() },
    mounted() { lucide.createIcons() }
}
