
import Sidebar from './components/Sidebar.js';
import NewServiceForm from './components/NewServiceForm.js';
import CustomerPage from './components/CustomerPage.js';
import StockPage from './components/StockPage.js';
import NewProcessWizard from './components/NewProcessWizard.js';
import ServiceDefinitionsPage from './components/ServiceDefinitionsPage.js';

const TechnicianPanelModal = {
    props: ['service', 'parts'],
    data() {
        return { activeTab: 'general', localService: { ...this.service } }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-8 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-7xl h-full max-h-[92vh] flex flex-col overflow-hidden border border-slate-700/50">
            <!-- Header -->
            <div class="h-16 border-b border-slate-200 flex items-center justify-between px-6 bg-slate-50 flex-shrink-0">
                <div class="flex items-center">
                    <div class="w-10 h-10 bg-blue-100 text-blue-600 rounded-lg flex items-center justify-center mr-4"><i data-lucide="tool" class="w-5 h-5"></i></div>
                    <div><div class="font-bold text-lg text-slate-800">Teknisyen Paneli</div><div class="text-xs text-slate-500 font-mono flex items-center gap-2"><span class="bg-slate-200 text-slate-700 px-1.5 rounded">#{{ localService.tracking_no }}</span><span>{{ localService.device_brand }} {{ localService.device_model }}</span></div></div>
                </div>
                <button @click="$emit('close')" class="p-2 hover:bg-slate-200 rounded-full transition"><i data-lucide="x" class="w-6 h-6 text-slate-500"></i></button>
            </div>
            <!-- Tabs -->
            <div class="flex px-6 border-b border-slate-200 bg-white flex-shrink-0">
                <button v-for="tab in [['general', '📍 Genel İşlemler'], ['test', '📋 Cihaz Test Formu'], ['logs', '🕒 İşlem Geçmişi']]" :key="tab[0]" @click="activeTab = tab[0]" class="px-6 py-3 font-semibold text-sm border-b-2 transition-colors relative top-[1px]" :class="activeTab === tab[0] ? 'text-blue-600 border-blue-600 bg-blue-50/50 rounded-t-lg' : 'text-slate-500 border-transparent hover:text-slate-700 hover:bg-slate-50'">{{ tab[1] }}</button>
            </div>
            <!-- Content -->
            <div class="flex-1 overflow-y-auto bg-slate-50/50 p-8">
                <div v-if="activeTab === 'general'" class="space-y-8 animate-fade-in">
                    <div class="grid grid-cols-2 gap-8">
                        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <h3 class="font-bold text-slate-800 mb-5 flex items-center text-sm uppercase tracking-wide border-b pb-2"><i data-lucide="package" class="w-4 h-4 mr-2 text-blue-500"></i> Servis ve Finans</h3>
                            <div class="grid grid-cols-2 gap-5">
                                <div><label class="block text-xs font-bold text-slate-500 mb-1">DURUM</label><select v-model="localService.status" class="w-full p-2 border rounded-lg bg-slate-50 font-bold"><option>Bekliyor</option><option>Tamirde</option><option>Parça Bekliyor</option><option>Test Sürecinde</option><option>Hazır</option><option>Teslim Edildi</option></select></div>
                                <div><label class="block text-xs font-bold text-slate-500 mb-1">ÖDEME TİPİ</label><select class="w-full p-2 border rounded-lg bg-slate-50"><option>Nakit</option><option>Kredi Kartı</option><option>Havale</option></select></div>
                            </div>
                        </div>
                        <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm">
                            <h3 class="font-bold text-slate-800 mb-5 flex items-center text-sm uppercase tracking-wide border-b pb-2"><i data-lucide="shield-check" class="w-4 h-4 mr-2 text-emerald-500"></i> Garanti & Teslimat</h3>
                            <div class="grid grid-cols-2 gap-5">
                                <div><label class="block text-xs font-bold text-slate-500 mb-1">GARANTİ</label><select class="w-full p-2 border rounded-lg bg-slate-50"><option>Yok</option><option>Var</option><option>Bitti</option></select></div>
                                <div><label class="block text-xs font-bold text-slate-500 mb-1">BİTİŞ TARİHİ</label><input type="date" class="w-full p-2 border rounded-lg"></div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <!-- Footer -->
            <div class="h-20 bg-white border-t border-slate-200 px-8 flex items-center justify-between flex-shrink-0">
                <button @click="$emit('close')" class="px-6 py-2.5 rounded-lg border border-slate-300 text-slate-600 font-bold hover:bg-slate-50 transition">İptal / Kapat</button>
                <div class="flex gap-4">
                    <button class="px-6 py-2.5 rounded-lg bg-slate-100 text-slate-700 font-bold hover:bg-slate-200 flex items-center transition"><i data-lucide="printer" class="w-4 h-4 mr-2"></i> Fiş Yazdır</button>
                    <button class="px-8 py-2.5 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 shadow-lg shadow-blue-200 transition-all flex items-center transform hover:-translate-y-0.5" @click="$emit('save', localService)"><i data-lucide="save" class="w-4 h-4 mr-2"></i> DEĞİŞİKLİKLERİ KAYDET</button>
                </div>
            </div>
        </div>
    </div>`,
    updated() { lucide.createIcons() }, mounted() { lucide.createIcons() }
}

const AppointmentDetailModal = {
    props: ['appointment'],
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden border border-slate-200">
            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold text-lg">📅</div>
                    <div>
                        <h3 class="font-bold text-lg text-slate-800">Randevu Detayı</h3>
                        <div class="text-xs text-slate-500 font-mono">{{ appointment.date }} - {{ appointment.time }}</div>
                    </div>
                </div>
                <button @click="$emit('close')" class="text-slate-400 hover:text-slate-600"><i data-lucide="x" class="w-5 h-5"></i></button>
            </div>
            
            <div class="p-6 space-y-6">
                <!-- Müşteri Bilgisi -->
                <div class="flex items-start gap-4 p-4 bg-slate-50 rounded-xl border border-slate-100">
                    <div class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500"><i data-lucide="user" class="w-5 h-5"></i></div>
                    <div>
                        <div class="text-xs font-bold text-slate-400 uppercase">Müşteri</div>
                        <div class="font-bold text-slate-800 text-lg">{{ appointment.customer_name }}</div>
                        <div class="text-sm text-slate-500">{{ appointment.phone }}</div>
                    </div>
                </div>

                <!-- Durum ve Açıklama -->
                <div>
                    <div class="text-xs font-bold text-slate-400 uppercase mb-2">Hizmet / Notlar</div>
                    <div class="p-4 bg-white border border-slate-200 rounded-xl text-slate-700 text-sm leading-relaxed shadow-sm">
                        {{ appointment.description || 'Açıklama yok.' }}
                    </div>
                </div>

                <!-- Aksiyon Butonları -->
                <div>
                    <div class="text-xs font-bold text-slate-400 uppercase mb-3">İşlemler</div>
                    <div class="grid grid-cols-2 gap-3" v-if="appointment.status !== 'Tamamlandı' && appointment.status !== 'İptal'">
                        <button v-if="appointment.status === 'Bekliyor'" @click="$emit('update-status', appointment.id, 'Gidildi')" class="p-3 rounded-xl bg-purple-50 text-purple-600 font-bold hover:bg-purple-100 border border-purple-200 transition text-sm flex items-center justify-center gap-2"><i data-lucide="map-pin" class="w-4 h-4"></i> Müşteriye Gidildi</button>
                        <button v-if="appointment.status === 'Bekliyor'" @click="$emit('update-status', appointment.id, 'Gidilmedi')" class="p-3 rounded-xl bg-red-50 text-red-600 font-bold hover:bg-red-100 border border-red-200 transition text-sm flex items-center justify-center gap-2"><i data-lucide="x-circle" class="w-4 h-4"></i> Gidilmedi / Yok</button>
                        
                        <button v-if="['Bekliyor', 'Gidildi'].includes(appointment.status)" @click="$emit('update-status', appointment.id, 'İşlemde')" class="p-3 rounded-xl bg-amber-50 text-amber-600 font-bold hover:bg-amber-100 border border-amber-200 transition text-sm flex items-center justify-center gap-2 col-span-2"><i data-lucide="loader" class="w-4 h-4"></i> İşleme Başla</button>
                        
                        <button @click="$emit('update-status', appointment.id, 'Tamamlandı')" class="p-3 rounded-xl bg-emerald-50 text-emerald-600 font-bold hover:bg-emerald-100 border border-emerald-200 transition text-sm flex items-center justify-center gap-2"><i data-lucide="check-circle" class="w-4 h-4"></i> Tamamla</button>
                        <button @click="$emit('update-status', appointment.id, 'İptal')" class="p-3 rounded-xl bg-slate-100 text-slate-600 font-bold hover:bg-slate-200 border border-slate-200 transition text-sm flex items-center justify-center gap-2"><i data-lucide="ban" class="w-4 h-4"></i> İptal Et</button>
                    </div>
                    <div v-else class="text-center p-4 bg-slate-50 rounded-xl border border-slate-200 text-slate-500 font-bold">
                        Bu randevu {{ appointment.status }} durumunda.
                    </div>
                </div>
            </div>
        </div>
    </div>
    `, updated() { lucide.createIcons() }, mounted() { lucide.createIcons() }
}


const NewAppointmentModal = {
    data() {
        return {
            form: {
                customer_name: '', phone: '', appointment_date: new Date().toISOString().split('T')[0],
                appointment_time: '09:00', service_type: 'Genel Bakım', notes: ''
            }
        }
    },
    template: `
    <div class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fade-in" @click.self="$emit('close')">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-md overflow-hidden border border-slate-200">
            <div class="px-6 py-4 border-b border-slate-100 flex justify-between items-center bg-slate-50">
                <h3 class="font-bold text-lg text-slate-800">Yeni Randevu Oluştur</h3>
                <button @click="$emit('close')" class="text-slate-400 hover:text-slate-600"><i data-lucide="x" class="w-5 h-5"></i></button>
            </div>
            <div class="p-6 space-y-4">
                <div><label class="block text-xs font-bold text-slate-500 mb-1">MÜŞTERİ ADI</label><input v-model="form.customer_name" type="text" class="w-full p-2.5 rounded-lg border border-slate-200 focus:border-blue-500 focus:ring-2 focus:ring-blue-100 outline-none transition font-semibold" placeholder="Ad Soyad"></div>
                <div><label class="block text-xs font-bold text-slate-500 mb-1">TELEFON</label><input v-model="form.phone" type="tel" class="w-full p-2.5 rounded-lg border border-slate-200 focus:border-blue-500 outline-none transition" placeholder="0555..."></div>
                <div class="grid grid-cols-2 gap-4">
                    <div><label class="block text-xs font-bold text-slate-500 mb-1">TARİH</label><input v-model="form.appointment_date" type="date" class="w-full p-2.5 rounded-lg border border-slate-200 outline-none"></div>
                    <div><label class="block text-xs font-bold text-slate-500 mb-1">SAAT</label><input v-model="form.appointment_time" type="time" class="w-full p-2.5 rounded-lg border border-slate-200 outline-none"></div>
                </div>
                <div><label class="block text-xs font-bold text-slate-500 mb-1">HİZMET TİPİ</label><select v-model="form.service_type" class="w-full p-2.5 rounded-lg border border-slate-200 outline-none bg-white"><option>Genel Bakım</option><option>Arıza Tespit</option><option>Kurulum</option><option>Yerinde Servis</option><option>Yazılım Desteği</option></select></div>
                <div><label class="block text-xs font-bold text-slate-500 mb-1">NOTLAR</label><textarea v-model="form.notes" rows="2" class="w-full p-2.5 rounded-lg border border-slate-200 outline-none resize-none" placeholder="Opsiyonel açıklama..."></textarea></div>
            </div>
            <div class="p-4 bg-slate-50 border-t border-slate-100 flex justify-end gap-3">
                <button @click="$emit('close')" class="px-4 py-2 rounded-lg text-slate-600 font-bold hover:bg-slate-200 transition text-sm">İptal</button>
                <button @click="$emit('save', form)" class="px-6 py-2 rounded-lg bg-blue-600 text-white font-bold hover:bg-blue-700 shadow-md transition text-sm flex items-center"><i data-lucide="check" class="w-4 h-4 mr-2"></i> Randevu Oluştur</button>
            </div>
        </div>
    </div>
    `, updated() { lucide.createIcons() }, mounted() { lucide.createIcons() }
}
const GenericPage = {
    props: ['title', 'data', 'columns', 'loading'],
    template: `
    <div class="flex flex-col h-full animate-fade-in p-8">
        <div class="flex items-center justify-between mb-6"><h2 class="text-2xl font-bold text-slate-800">{{ title }}</h2><button @click="$emit('create-new')" class="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2.5 rounded-xl font-bold text-sm shadow-md transition flex items-center gap-2"><i data-lucide="plus" class="w-4 h-4"></i> Yeni Kayıt</button></div>
        <div class="bg-white rounded-2xl border border-slate-200 shadow-sm flex-1 overflow-hidden flex flex-col">
            <div class="h-14 border-b border-slate-100 flex items-center px-4 gap-4"><div class="relative flex-1 max-w-sm"><i data-lucide="search" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"></i><input type="text" placeholder="Ara..." class="w-full pl-9 pr-4 py-2 rounded-lg border border-slate-200 text-sm focus:outline-none focus:border-blue-500"></div><div class="flex gap-2"><button class="p-2 border rounded-lg hover:bg-slate-50" title="Filtrele"><i data-lucide="filter" class="w-4 h-4 text-slate-500"></i></button><button class="p-2 border rounded-lg hover:bg-slate-50" title="İndir"><i data-lucide="download" class="w-4 h-4 text-slate-500"></i></button></div></div>
            <div class="flex-1 overflow-auto">
                <table class="w-full text-left text-sm"><thead class="bg-slate-50 sticky top-0 z-10"><tr><th v-for="col in columns" :key="col.key" class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider border-b border-slate-200">{{ col.label }}</th><th class="px-6 py-4 font-bold text-slate-500 uppercase text-xs tracking-wider border-b border-slate-200 text-center w-24">İşlemler</th></tr></thead>
                <tbody class="divide-y divide-slate-100"><tr v-if="loading"><td :colspan="columns.length + 1" class="p-8 text-center text-slate-400">Yükleniyor...</td></tr><tr v-else-if="!data || data.length === 0"><td :colspan="columns.length + 1" class="p-12 text-center flex flex-col items-center justify-center text-slate-400"><i data-lucide="inbox" class="w-12 h-12 mb-4 opacity-20"></i><span class="font-medium">Kayıt bulunamadı</span></td></tr>
                <tr v-else v-for="item in data" :key="item.id" class="hover:bg-blue-50/50 transition-colors group cursor-pointer" @click="$emit('row-click', item)"><td v-for="col in columns" :key="col.key" class="px-6 py-4 text-slate-700 font-medium whitespace-nowrap"><span>{{ item[col.key] }}</span></td><td class="px-6 py-4 text-center"><button class="p-2 hover:bg-slate-200 rounded-lg text-slate-500 hover:text-blue-600 transition"><i data-lucide="more-horizontal" class="w-4 h-4"></i></button></td></tr></tbody></table>
            </div>
            <div class="h-12 border-t border-slate-100 flex items-center justify-between px-6 bg-slate-50/50"><span class="text-xs text-slate-500">Toplam {{ data ? data.length : 0 }} kayıt</span><div class="flex gap-2"><button class="p-1 rounded hover:bg-slate-200 disabled:opacity-50" disabled><i data-lucide="chevron-left" class="w-4 h-4"></i></button><button class="p-1 rounded hover:bg-slate-200 disabled:opacity-50" disabled><i data-lucide="chevron-right" class="w-4 h-4"></i></button></div></div>
        </div>
    </div>
    `, updated() { lucide.createIcons() }, mounted() { lucide.createIcons() }
}

export default {
    components: { Sidebar, TechnicianPanelModal, NewAppointmentModal, AppointmentDetailModal, GenericPage, NewServiceForm, CustomerPage, StockPage, NewProcessWizard, ServiceDefinitionsPage },
    data() {
        return {
            page: new URLSearchParams(window.location.search).get('page') || 'dashboard',
            showTechModal: false, showAppointmentModal: false, showAppointmentDetailModal: false,
            selectedService: {}, selectedAppointment: {},
            dashboardData: {}, services: [], customers: [], parts: [], appointments: [], loading: false,
            preselectedCustomer: null, shouldOpenStockModal: false
        }
    },
    computed: {
        pageColumns() {
            const map = {
                'technician': [{ key: 'tracking_no', label: 'Takip No' }, { key: 'device_brand', label: 'Marka' }, { key: 'device_model', label: 'Model' }, { key: 'customer_name', label: 'Müşteri' }, { key: 'status', label: 'Durum' }, { key: 'entry_date', label: 'Giriş Tarihi' }],
                'kanban': [{ key: 'tracking_no', label: 'İş Emri No' }, { key: 'customer_name', label: 'Müşteri' }, { key: 'fault_description', label: 'Arıza' }, { key: 'status', label: 'Aşama' }, { key: 'urgency', label: 'Aciliyet' }],
                'service-status': [{ key: 'tracking_no', label: 'Takip Kodu' }, { key: 'customer_name', label: 'Müşteri' }, { key: 'device_model', label: 'Cihaz' }, { key: 'status', label: 'Son Durum' }],
                'logistics': [{ key: 'tracking_no', label: 'Gönderi No' }, { key: 'customer_name', label: 'Alıcı/Gönderen' }, { key: 'status', label: 'Kargo Durumu' }, { key: 'date', label: 'Tarih' }],
                'field-map': [{ key: 'id', label: 'Saha ID' }, { key: 'personnel', label: 'Teknisyen' }, { key: 'location', label: 'Konum' }, { key: 'status', label: 'Durum' }],
                'appointments': [{ key: 'date', label: 'Tarih' }, { key: 'time', label: 'Saat' }, { key: 'customer_name', label: 'Müşteri' }, { key: 'description', label: 'Hizmet / Açıklama' }, { key: 'status', label: 'Durum' }],

                'customers': [{ key: 'id', label: 'ID' }, { key: 'name', label: 'İsim' }, { key: 'phone', label: 'Telefon' }, { key: 'email', label: 'E-posta' }, { key: 'balance', label: 'Bakiye' }],
                'contracts': [{ key: 'contract_no', label: 'Sözleşme No' }, { key: 'customer_name', label: 'Müşteri' }, { key: 'contract_type', label: 'Türü' }, { key: 'end_date', label: 'Bitiş' }],
                'reminders': [{ key: 'date', label: 'Tarih' }, { key: 'title', label: 'Başlık' }, { key: 'customer_name', label: 'İlgili Kişi' }],
                'announcements': [{ key: 'date', label: 'Tarih' }, { key: 'title', label: 'Konu' }, { key: 'target', label: 'Hedef Kitle' }],

                'stock': [{ key: 'code', label: 'Barkod' }, { key: 'part_name', label: 'Ürün Adı' }, { key: 'stock', label: 'Adet' }, { key: 'price', label: 'Fiyat' }],
                'pos': [{ key: 'sale_id', label: 'Satış No' }, { key: 'date', label: 'Tarih' }, { key: 'total', label: 'Tutar' }, { key: 'payment_method', label: 'Ödeme' }],
                'service-defs': [{ key: 'service_name', label: 'Hizmet Adı' }, { key: 'category', label: 'Kategori' }, { key: 'price', label: 'Fiyat' }],

                'accounting': [{ key: 'date', label: 'Tarih' }, { key: 'description', label: 'Açıklama' }, { key: 'category', label: 'Kategori' }, { key: 'type', label: 'Tür' }, { key: 'amount', label: 'Tutar' }],
                'reports': [{ key: 'report_name', label: 'Rapor Adı' }, { key: 'generated_at', label: 'Oluşturma Tarihi' }, { key: 'type', label: 'Format' }],

                'ai': [{ key: 'query', label: 'Sorgu' }, { key: 'response', label: 'Yanıt' }, { key: 'timestamp', label: 'Zaman' }],
                'knowledge-base': [{ key: 'title', label: 'Başlık' }, { key: 'category', label: 'Kategori' }, { key: 'views', label: 'Görüntüleme' }],
                'settings': [{ key: 'setting_key', label: 'Ayar' }, { key: 'value', label: 'Değer' }],
                'logs': [{ key: 'timestamp', label: 'Zaman' }, { key: 'level', label: 'Seviye' }, { key: 'message', label: 'Mesaj' }],
                'support': [{ key: 'ticket_id', label: 'Talep No' }, { key: 'subject', label: 'Konu' }, { key: 'status', label: 'Durum' }],

                'personnel': [{ key: 'name', label: 'Personel Adı' }, { key: 'role', label: 'Görevi' }, { key: 'phone', label: 'Tel' }, { key: 'email', label: 'E-posta' }]
            }
            return map[this.page] || [{ key: 'id', label: 'ID' }, { key: 'name', label: 'Adı' }]
        },
        pageData() {
            // MOCK Data mapping for missing APIs to prevent empty screens
            const map = {
                'technician': this.services,
                'kanban': this.services,
                'service-status': this.services,
                'customers': this.customers,
                'stock': this.parts,
                'service-defs': [], // Handled by component
                // Use services as mock for logistics/field for now
                'appointments': this.appointments,
                'logistics': [], 'field-map': [],
                'contracts': [], 'reminders': [], 'announcements': [],
                'pos': [], 'accounting': [], 'reports': [],
                'ai': [], 'knowledge-base': [], 'settings': [], 'logs': [], 'support': [], 'personnel': []
            }
            return map[this.page] || []
        },
        pageTitle() {
            const titles = {
                dashboard: 'Genel Bakış',
                kanban: 'İş Emirleri (Pano)',
                'service-status': 'Durum Ekranı',
                technician: 'Teknisyen Paneli',
                logistics: 'Lojistik & Garanti',
                'field-map': 'Saha Haritası',
                appointments: 'Randevular',
                'new-process': 'Yeni İşlem Sihirbazı',

                customers: 'Müşteri Listesi',
                contracts: 'Sözleşmeler',
                reminders: 'Hatırlatıcılar',
                announcements: 'Duyurular',

                stock: 'Stok Yönetimi',
                pos: 'Hızlı Satış (POS)',
                'service-defs': 'Hizmet Tanımları',

                accounting: 'Gelir / Gider',
                reports: 'Finansal Raporlar',

                ai: 'AI Asistan',
                'knowledge-base': 'Bilgi Bankası',
                settings: 'Sistem Ayarları',
                logs: 'Log Kayıtları',
                support: 'Destek Talepleri',

                personnel: 'Personel Listesi'
            }
            const customLabels = window.__ayecNavigationLabels || {}
            return customLabels[this.page] || titles[this.page] || 'Sayfa'
        },
        currentInfo() { return { id: this.page, title: this.pageTitle } }
    },
    methods: {
        async loadAllData() {
            this.loading = true
            try {
                const [d, s, c, p, a] = await Promise.all([
                    fetch('/api/dashboard').then(r => r.json()).catch(() => ({})),
                    fetch('/api/services').then(r => r.json()).catch(() => ([])),
                    fetch('/api/customers').then(r => r.json()).catch(() => ([])),
                    fetch('/api/parts').then(r => r.json()).catch(() => ([])),
                    fetch('/api/appointments').then(r => r.json()).catch(() => ([]))
                ])
                this.dashboardData = d; this.services = s; this.parts = p; this.appointments = a;

                // Müşterilere bakiye ekle
                this.customers = await Promise.all(c.map(async (customer) => {
                    try {
                        const balanceRes = await fetch(`/api/customers/${customer.id}/balance`);
                        const balanceData = await balanceRes.json();
                        return { ...customer, balance: balanceData.balance || 0 };
                    } catch (e) {
                        return { ...customer, balance: 0 };
                    }
                }));
            } catch (e) { console.error(e) }
            this.loading = false
        },
        handleRowClick(item) {
            if (this.page === 'technician' || this.page === 'kanban') {
                this.selectedService = { ...item }
                this.showTechModal = true
            } else if (this.page === 'appointments') {
                this.selectedAppointment = { ...item }
                this.showAppointmentDetailModal = true
            }
        },
        async saveService(updatedService) {
            try {
                // Backend API call to update status
                const res = await fetch(`/api/services/${updatedService.id}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: updatedService.status })
                });

                if (res.ok) {
                    // Update Local State
                    const idx = this.services.findIndex(s => s.id === updatedService.id)
                    if (idx !== -1) this.services[idx] = updatedService;

                    this.showTechModal = false;
                    alert("✅ Başarılı: Veriler masaüstü uygulaması ile senkronize edildi.");
                    this.loadAllData(); // Refresh to ensure consistency
                } else {
                    alert("❌ Hata: Güncelleme başarısız.");
                }
            } catch (e) {
                console.error(e);
                alert("⚠️ Hata: Sunucu ile iletişim kurulamadı.");
            }
        },
        handleOpenWizard(customer) {
            this.preselectedCustomer = customer;
            this.page = 'new-process';
        },
        openStockPage() {
            this.page = 'stock';
            this.shouldOpenStockModal = true;
            setTimeout(() => this.shouldOpenStockModal = false, 1000);
        },
        handleCreateNew() {
            if (this.page === 'appointments') {
                this.showAppointmentModal = true;
            } else {
                this.page = 'new-process';
            }
        },
        async saveAppointment(form) {
            try {
                const res = await fetch('/api/appointments', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(form)
                });
                if (res.ok) {
                    this.showAppointmentModal = false;
                    alert("✅ Randevu başarıyla oluşturuldu.");
                    this.loadAllData();
                } else {
                    alert("❌ Hata oluştu.");
                }
            } catch (e) { console.error(e); alert("Sunucu hatası"); }
        },
        async updateAppointmentStatus(id, status) {
            if (!confirm(status + " olarak işaretlensin mi?")) return;
            try {
                const res = await fetch(`/api/appointments/${id}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status })
                });
                if (res.ok) {
                    this.showAppointmentDetailModal = false;
                    // Optimistic update
                    const idx = this.appointments.findIndex(a => a.id === id);
                    if (idx !== -1) this.appointments[idx].status = status;
                    alert("✅ Durum güncellendi.");
                } else {
                    alert("❌ Hata oluştu.");
                }
            } catch (e) { console.error(e); }
        }
    },
    template: `
    <div class="flex h-screen w-full bg-[#f8fafc] text-slate-800 font-sans">
        <Sidebar :currentInfo="currentInfo" @page-change="page = $event" />
        <main class="flex-1 flex flex-col h-full overflow-hidden relative">
            
            <div class="flex-1 overflow-hidden relative">
                
                <!-- DASHBOARD PAGE -->
                <div v-if="page === 'dashboard'" class="h-full flex flex-col p-8 space-y-6 animate-fade-in bg-[#f8fafc]">
                     
                     <!-- Stats Grid -->
                     <div class="grid grid-cols-5 gap-6 flex-shrink-0">
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-blue-500 transition cursor-pointer group flex flex-col justify-between"><div class="flex justify-between items-start"><div class="text-sm font-bold text-slate-400 uppercase tracking-wide">Aktif Servis</div><div class="p-2 rounded-lg bg-blue-50 text-blue-600"><i data-lucide="activity" class="w-5 h-5"></i></div></div><div class="text-3xl font-extrabold text-slate-800 mt-4">{{ dashboardData.active_services || 0 }}</div></div>
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-emerald-500 transition cursor-pointer group flex flex-col justify-between"><div class="flex justify-between items-start"><div class="text-sm font-bold text-slate-400 uppercase tracking-wide">Bugün Gelen</div><div class="p-2 rounded-lg bg-emerald-50 text-emerald-600"><i data-lucide="check-circle" class="w-5 h-5"></i></div></div><div class="text-3xl font-extrabold text-slate-800 mt-4">{{ dashboardData.today_new || 0 }}</div></div>
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-purple-500 transition cursor-pointer group flex flex-col justify-between"><div class="flex justify-between items-start"><div class="text-sm font-bold text-slate-400 uppercase tracking-wide">Müşteriler</div><div class="p-2 rounded-lg bg-purple-50 text-purple-600"><i data-lucide="users" class="w-5 h-5"></i></div></div><div class="text-3xl font-extrabold text-slate-800 mt-4">{{ dashboardData.total_customers || 0 }}</div></div>
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-amber-500 transition cursor-pointer group flex flex-col justify-between"><div class="flex justify-between items-start"><div class="text-sm font-bold text-slate-400 uppercase tracking-wide">Kritik Stok</div><div class="p-2 rounded-lg bg-amber-50 text-amber-600"><i data-lucide="alert-triangle" class="w-5 h-5"></i></div></div><div class="text-3xl font-extrabold text-slate-800 mt-4">{{ dashboardData.low_stock || 0 }}</div></div>
                        <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm hover:border-indigo-500 transition cursor-pointer group flex flex-col justify-between"><div class="flex justify-between items-start"><div class="text-sm font-bold text-slate-400 uppercase tracking-wide">Toplam Cihaz</div><div class="p-2 rounded-lg bg-indigo-50 text-indigo-600"><i data-lucide="smartphone" class="w-5 h-5"></i></div></div><div class="text-3xl font-extrabold text-slate-800 mt-4">{{ (dashboardData.total_active || 0) + (dashboardData.total_done || 0) }}</div></div>
                     </div>

                     <!-- Split Content -->
                     <div class="flex gap-6 flex-1 overflow-hidden">
                        
                        <!-- Main Table Area -->
                        <div class="flex-1 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden">
                            <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
                                <h3 class="font-bold text-lg text-slate-800">Son İşlemler</h3>
                                <button class="text-blue-600 font-bold text-sm hover:bg-blue-50 px-3 py-1.5 rounded-lg transition" @click="page='kanban'">Tümünü Gör ›</button>
                            </div>
                            <div class="flex-1 overflow-auto">
                                <table class="w-full text-left text-sm">
                                    <thead class="bg-slate-50 sticky top-0 z-10 text-xs text-slate-400 uppercase font-bold text-left">
                                        <tr>
                                            <th class="px-6 py-3 border-b">Takip No</th>
                                            <th class="px-6 py-3 border-b">Müşteri</th>
                                            <th class="px-6 py-3 border-b">Cihaz</th>
                                            <th class="px-6 py-3 border-b text-center">Durum</th>
                                            <th class="px-6 py-3 border-b text-center">İşlemler</th>
                                        </tr>
                                    </thead>
                                    <tbody class="divide-y divide-slate-50">
                                        <tr v-for="s in services" :key="s.id" class="group hover:bg-blue-50/50 transition cursor-pointer" @click="handleRowClick(s)">
                                            <td class="px-6 py-3 font-mono text-slate-900 font-bold">#{{ s.tracking_no }}</td>
                                            <td class="px-6 py-3 font-medium text-slate-700">{{ s.customer_name }}</td>
                                            <td class="px-6 py-3 text-slate-500">{{ s.device_model || 'Bilinmiyor' }}</td>
                                            <td class="px-6 py-3 text-center"><span class="px-3 py-1 rounded-md text-xs font-bold text-white shadow-sm" :class="{'bg-blue-500': ['Tamirde','Serviste'].includes(s.status), 'bg-emerald-500': ['Hazır','Teslim Edildi'].includes(s.status), 'bg-slate-400': !['Tamirde','Serviste','Hazır','Teslim Edildi'].includes(s.status)}">{{ s.status }}</span></td>
                                            <td class="px-6 py-3 text-center flex justify-center gap-2">
                                                <button class="p-1.5 rounded bg-amber-100 text-amber-600 hover:bg-amber-200" title="Düzenle" @click.stop="handleRowClick(s)"><i data-lucide="edit-3" class="w-4 h-4"></i></button>
                                                <button class="p-1.5 rounded bg-blue-100 text-blue-600 hover:bg-blue-200" title="Detay" @click.stop="handleRowClick(s)"><i data-lucide="eye" class="w-4 h-4"></i></button>
                                            </td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Right Sidebar -->
                        <div class="w-80 flex flex-col gap-6 overflow-y-auto pr-1">
                             
                             <!-- Quick Actions -->
                             <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
                                 <h4 class="font-bold text-slate-800 text-base">Hızlı Ulaşım</h4>
                                 <div class="flex flex-col gap-3">
                                     <button @click="page='customers'" class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-purple-300 hover:shadow-md transition group text-left">
                                         <span class="w-10 h-10 rounded-lg bg-purple-100 text-purple-600 flex items-center justify-center mr-3 font-bold text-lg">👤</span>
                                         <span class="font-bold text-slate-700 group-hover:text-purple-600">Yeni Müşteri Ekle</span>
                                     </button>
                                     <button @click="page='new-process'" class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-emerald-300 hover:shadow-md transition group text-left">
                                         <span class="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-600 flex items-center justify-center mr-3 font-bold text-lg">🛠️</span>
                                         <span class="font-bold text-slate-700 group-hover:text-emerald-600">Servis Formu</span>
                                     </button>
                                     <button @click="page='technician'" class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-amber-300 hover:shadow-md transition group text-left">
                                         <span class="w-10 h-10 rounded-lg bg-amber-100 text-amber-600 flex items-center justify-center mr-3 font-bold text-lg">🔧</span>
                                         <span class="font-bold text-slate-700 group-hover:text-amber-600">Teknisyen Paneli</span>
                                     </button>
                                     <button @click="openStockPage" class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-blue-300 hover:shadow-md transition group text-left">
                                         <span class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center mr-3 font-bold text-lg">📦</span>
                                         <span class="font-bold text-slate-700 group-hover:text-blue-600">Stok Ekle</span>
                                     </button>
                                     <button @click="page='accounting'" class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-red-300 hover:shadow-md transition group text-left">
                                         <span class="w-10 h-10 rounded-lg bg-red-100 text-red-600 flex items-center justify-center mr-3 font-bold text-lg">💰</span>
                                         <span class="font-bold text-slate-700 group-hover:text-red-600">Cari İşlemler</span>
                                     </button>
                                 </div>
                             </div>

                             <!-- Filters -->
                             <div class="bg-white rounded-2xl border border-slate-200 shadow-sm p-5 space-y-4">
                                 <h4 class="font-bold text-slate-800 text-base">Görünüm Filtreleri</h4>
                                 <div class="flex flex-col gap-2">
                                     <button class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-slate-400 transition text-left font-bold text-slate-600 text-sm">
                                         <span class="mr-3">📅</span> Bugün Gelenler
                                     </button>
                                     <button class="flex items-center w-full p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-white hover:border-amber-300 transition text-left font-bold text-slate-600 text-sm">
                                         <span class="mr-3">⏳</span> Onay Bekleyenler
                                     </button>
                                     <button class="flex items-center w-full p-3 rounded-xl bg-blue-600 border border-blue-600 text-white shadow-md transition text-left font-bold text-sm">
                                         <span class="mr-3">📋</span> Tüm Kayıtlar
                                     </button>
                                 </div>
                             </div>

                        </div>
                     </div>
                </div>

                <!-- Custom Pages -->
                <NewServiceForm v-else-if="page === 'new-service'" />
                <NewProcessWizard v-else-if="page === 'new-process'" :customers="customers" :preselected-customer="preselectedCustomer" @close="page = 'customers'" />
                <CustomerPage v-else-if="page === 'customers'" :customers="customers" :loading="loading" @open-wizard="handleOpenWizard" @refresh="loadAllData" />
                <StockPage v-else-if="page === 'stock'" :parts="parts" :loading="loading" @refresh="loadAllData" :open-modal="shouldOpenStockModal" />
                <ServiceDefinitionsPage v-else-if="page === 'service-defs'" />

                <!-- Generic -->
                <GenericPage v-else 
                    :title="pageTitle" 
                    :data="pageData" 
                    :columns="pageColumns" 
                    :loading="loading"
                    @row-click="handleRowClick"
                    @create-new="handleCreateNew"
                />
            </div>
        </main>
        <TechnicianPanelModal v-if="showTechModal" :service="selectedService" :parts="parts" @close="showTechModal = false" @save="saveService" />
        <NewAppointmentModal v-if="showAppointmentModal" @close="showAppointmentModal = false" @save="saveAppointment" />
        <AppointmentDetailModal v-if="showAppointmentDetailModal" :appointment="selectedAppointment" @close="showAppointmentDetailModal = false" @update-status="updateAppointmentStatus" />
    </div>
    `,
    mounted() { this.loadAllData() }, updated() { lucide.createIcons() }
}
