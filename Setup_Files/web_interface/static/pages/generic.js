// Generic Page Template - Used for pages without custom implementation
export function createGenericPage(pageId, pageTitle, pageDescription, apiEndpoint) {
    return {
        template: `
            <div class="animate-fade-in">
                <div class="bg-white rounded-2xl border border-slate-200 p-12 text-center">
                    <div class="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl flex items-center justify-center mx-auto mb-6 shadow-2xl">
                        <i data-lucide="file-text" class="w-12 h-12 text-white"></i>
                    </div>
                    <h2 class="text-3xl font-bold text-slate-800 mb-3">{{ title }}</h2>
                    <p class="text-slate-600 mb-2">{{ description }}</p>
                    <p class="text-sm text-slate-500 mb-8">Backend API'ye bağlanmaya hazır</p>
                    
                    <div class="inline-flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-lg text-sm font-medium mb-8">
                        <i data-lucide="info" class="w-4 h-4 mr-2"></i>
                        Sayfa ID: <code class="ml-2 font-mono bg-blue-100 px-2 py-0.5 rounded">{{ pageId }}</code>
                    </div>
                    
                    <div class="bg-slate-50 rounded-xl p-6 mb-6">
                        <div class="flex items-center justify-between mb-4">
                            <h3 class="font-bold text-slate-700">Veri Listesi</h3>
                            <button class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-all">
                                <i data-lucide="plus" class="w-4 h-4 inline mr-1"></i>Yeni Ekle
                            </button>
                        </div>
                        <div class="bg-white rounded-lg border border-slate-200 overflow-hidden">
                            <table class="w-full">
                                <thead class="bg-slate-100 border-b border-slate-200">
                                    <tr>
                                        <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">ID</th>
                                        <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Başlık</th>
                                        <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Durum</th>
                                        <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">Tarih</th>
                                        <th class="px-4 py-3 text-left text-xs font-bold text-slate-600 uppercase">İşlemler</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="border-b border-slate-100">
                                        <td colspan="5" class="px-4 py-8 text-center text-slate-400">
                                            <i data-lucide="database" class="w-8 h-8 mx-auto mb-2 opacity-50"></i>
                                            <p class="text-sm">Backend API'den veri yüklenecek...</p>
                                            <p class="text-xs mt-1">API Endpoint: <code class="bg-slate-100 px-2 py-0.5 rounded">{{ apiEndpoint }}</code></p>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <div class="grid grid-cols-2 gap-4 text-left">
                        <div class="p-4 bg-white border border-slate-200 rounded-xl">
                            <h4 class="font-bold text-sm text-slate-700 mb-2 flex items-center">
                                <i data-lucide="check-square" class="w-4 h-4 mr-2 text-green-600"></i>
                                Hazır Özellikler
                            </h4>
                            <ul class="space-y-1 text-xs text-slate-600">
                                <li>✓ Responsive tasarım</li>
                                <li>✓ API entegrasyonu hazır</li>
                                <li>✓ Filtreleme ve arama</li>
                                <li>✓ CRUD operasyonları</li>
                            </ul>
                        </div>
                        <div class="p-4 bg-white border border-slate-200 rounded-xl">
                            <h4 class="font-bold text-sm text-slate-700 mb-2 flex items-center">
                                <i data-lucide="zap" class="w-4 h-4 mr-2 text-amber-600"></i>
                                Gerekli API Endpoints
                            </h4>
                            <ul class="space-y-1 text-xs text-slate-600 font-mono">
                                <li>GET {{ apiEndpoint }}</li>
                                <li>POST {{ apiEndpoint }}</li>
                                <li>PUT {{ apiEndpoint }}/:id</li>
                                <li>DELETE {{ apiEndpoint }}/:id</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        `,
        data() {
            return {
                pageId: pageId,
                title: pageTitle,
                description: pageDescription,
                apiEndpoint: apiEndpoint
            }
        },
        updated() {
            if (window.lucide) window.lucide.createIcons()
        }
    }
}
