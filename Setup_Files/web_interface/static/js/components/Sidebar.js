
export default {
    props: ['currentInfo'],
    data() {
        return {
            // Varsayılan olarak hangi grupların açık olacağı
            openGroups: {
                'service': true,
                'customer': true,
                'stock': true,
                'finance': true,
                'tools': true,
                'hr': true
            },
            menuStructure: [
                {
                    id: 'service', title: 'Servis Yönetimi', icon: 'tool', color: 'text-blue-600', bg: 'bg-blue-50',
                    items: [
                        { id: 'kanban', label: 'İş Emirleri (Pano)' },
                        { id: 'service-status', label: 'Durum Ekranı' },
                        { id: 'technician', label: 'Teknisyen Paneli' },
                        { id: 'logistics', label: 'Lojistik & Garanti' },
                        { id: 'field-map', label: 'Saha Haritası' },
                        { id: 'appointments', label: 'Randevular' },
                        { id: 'new-process', label: 'Yeni İşlem (Sihirbaz)', specialCls: 'text-blue-600 font-bold bg-blue-50/50 border border-blue-100' }
                    ]
                },
                {
                    id: 'customer', title: 'Müşteri Hub', icon: 'users', color: 'text-emerald-600', bg: 'bg-emerald-50',
                    items: [
                        { id: 'customers', label: 'Müşteri Listesi' },
                        { id: 'contracts', label: 'Sözleşmeler' },
                        { id: 'reminders', label: 'Hatırlatıcılar' },
                        { id: 'announcements', label: 'Duyurular' }
                    ]
                },
                {
                    id: 'stock', title: 'Stok & Satış', icon: 'package', color: 'text-amber-600', bg: 'bg-amber-50',
                    items: [
                        { id: 'stock', label: 'Stok Yönetimi' },
                        { id: 'pos', label: 'Hızlı Satış (POS)' },
                        { id: 'service-defs', label: 'Hizmet Tanımları' }
                    ]
                },
                {
                    id: 'finance', title: 'Finans', icon: 'wallet', color: 'text-indigo-600', bg: 'bg-indigo-50',
                    items: [
                        { id: 'accounting', label: 'Gelir / Gider' },
                        { id: 'reports', label: 'Raporlar' }
                    ]
                },
                {
                    id: 'tools', title: 'Araçlar', icon: 'settings', color: 'text-slate-600', bg: 'bg-slate-50',
                    items: [
                        { id: 'ai', label: 'AI Asistan' },
                        { id: 'knowledge-base', label: 'Bilgi Bankası' },
                        { id: 'settings', label: 'Ayarlar' },
                        { id: 'logs', label: 'Log Kayıtları' },
                        { id: 'support', label: 'Destek' }
                    ]
                },
                {
                    id: 'hr', title: 'İK & Personel', icon: 'briefcase', color: 'text-purple-600', bg: 'bg-purple-50',
                    items: [
                        { id: 'personnel', label: 'Personel' }
                    ]
                }
            ]
        }
    },
    methods: {
        async loadNavigation() {
            try {
                const response = await fetch('/api/navigation');
                if (!response.ok) return;
                const payload = await response.json();
                const icons = ['tool', 'settings', 'users', 'folder-kanban', 'package', 'file-text', 'wallet', 'briefcase', 'circle-help'];
                const colors = ['blue', 'slate', 'emerald', 'cyan', 'amber', 'violet', 'indigo', 'purple', 'slate'];
                const labels = {};
                this.menuStructure = (payload.groups || [])
                    .map((group, index) => {
                        const color = colors[index % colors.length];
                        const items = (group.items || []).filter(item => item.id !== 'dashboard');
                        items.forEach(item => { labels[item.id] = item.label; });
                        this.openGroups[group.id] = true;
                        return {
                            ...group,
                            items,
                            icon: icons[index % icons.length],
                            color: `text-${color}-600`,
                            bg: `bg-${color}-50`
                        };
                    })
                    .filter(group => group.items.length);
                window.__ayecNavigationLabels = labels;
            } catch (error) {
                console.warn('Navigation settings could not be loaded.', error);
            }
        },
        toggleGroup(groupId) {
            // Vue 2/3 reactive update
            this.openGroups[groupId] = !this.openGroups[groupId];
            // Force Update for reactivity if needed (usually handled by Vue)
            this.$forceUpdate();
            this.$nextTick(() => lucide.createIcons());
        }
    },
    template: `
    <aside class="w-72 bg-white border-r border-slate-200 flex flex-col flex-shrink-0 z-20 shadow-sm h-full font-sans select-none">
        <!-- HEADER -->
        <div class="h-28 flex flex-col items-center justify-center border-b border-slate-100 bg-white relative overflow-hidden flex-shrink-0">
            <div class="flex items-center space-x-3 z-10 cursor-pointer" @click="$emit('page-change', 'dashboard')">
                <div class="text-4xl">🌩️</div>
                <div class="flex flex-col">
                    <span class="text-xl font-bold text-slate-700 tracking-tight">bulutteknoloji</span>
                    <span class="text-xs text-slate-400 font-medium tracking-wide">Bilişim ve Güvenlik</span>
                </div>
            </div>
            <div class="absolute -top-10 -right-10 w-32 h-32 bg-blue-50 rounded-full blur-3xl opacity-50"></div>
        </div>

        <!-- MENU SCROLL -->
        <nav class="flex-1 overflow-y-auto py-4 px-3 space-y-1 custom-scrollbar">
            
            <!-- GENEL BAKIŞ (Static) -->
            <button @click="$emit('page-change', 'dashboard')" 
                class="w-full flex items-center px-4 py-3 rounded-xl transition-all mb-4 group"
                :class="currentInfo.id === 'dashboard' ? 'bg-gradient-to-r from-blue-50 to-white text-blue-600 font-bold shadow-sm border border-blue-100' : 'text-slate-600 hover:bg-slate-50'">
                <i data-lucide="layout-dashboard" class="w-5 h-5 mr-3" :class="currentInfo.id === 'dashboard' ? 'text-blue-600' : 'text-slate-400'"></i>
                <span class="text-sm font-bold">Genel Bakış</span>
            </button>
            
            <div class="h-px bg-slate-100 my-4 mx-2"></div>

            <!-- DYNAMIC GROUPS -->
            <div v-for="group in menuStructure" :key="group.id" class="mb-2">
                <!-- Group Header -->
                <button @click="toggleGroup(group.id)" class="w-full flex items-center justify-between px-3 py-3 rounded-xl transition-all group hover:bg-slate-50 mb-1">
                    <div class="flex items-center">
                        <div class="w-8 h-8 rounded-lg flex items-center justify-center mr-3 transition-colors shadow-sm" :class="[group.bg, group.color]">
                            <i :data-lucide="group.icon" class="w-4 h-4"></i>
                        </div>
                        <span class="font-bold text-slate-700 text-sm tracking-tight">{{ group.title }}</span>
                    </div>
                    <i data-lucide="chevron-down" class="w-4 h-4 text-slate-400 transition-transform duration-300" :class="{'rotate-180': !openGroups[group.id]}"></i>
                </button>

                <!-- Group Items -->
                <div v-if="openGroups[group.id]" class="pl-3 pr-2 space-y-0.5 animate-fade-in-up">
                    <button v-for="item in group.items" :key="item.id" 
                        @click="$emit('page-change', item.id)"
                        class="w-full flex items-center px-4 py-2.5 rounded-xl transition-all mb-1 group"
                        :class="[
                            currentInfo.id === item.id ? 'bg-gradient-to-r from-slate-100 to-white text-blue-600 font-bold shadow-sm border border-slate-200' : 'text-slate-500 hover:bg-slate-50 hover:text-slate-900',
                            item.specialCls || ''
                        ]">
                        <div class="w-1.5 h-1.5 rounded-full mr-4 transition-colors flex-shrink-0" :class="currentInfo.id === item.id ? 'bg-blue-600' : 'bg-slate-300 group-hover:bg-slate-400'"></div>
                        <span class="text-sm truncate font-medium">{{ item.label }}</span>
                        <i v-if="item.id === 'new-process'" data-lucide="zap" class="w-3 h-3 ml-auto text-amber-500 fill-amber-500"></i>
                    </button>
                </div>
            </div>

        </nav>

        <!-- FOOTER -->
        <div class="flex-shrink-0 bg-white border-t border-slate-100 flex flex-col">
            <!-- Jarvis Status -->
            <div class="px-4 py-3 bg-[#1C1C1E] flex items-center gap-3">
                 <div class="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                 <span class="text-xs font-bold text-slate-300 tracking-wide font-mono">JARVIS ANALİZ YAPIYOR...</span>
            </div>
            <div class="h-8 flex items-center justify-center text-[10px] text-slate-400 font-mono">
                v68.0.0 Premium © 2026
            </div>
        </div>
    </aside>
    `,
    updated() { lucide.createIcons(); },
    mounted() {
        this.loadNavigation();
        lucide.createIcons();
    }
}
