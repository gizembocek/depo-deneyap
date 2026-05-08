// ==================== DASHBOARD PAGE ====================
async function renderDashboard() {
    const content = document.getElementById('pageContent');
    try {
        const stats = await api.getProductStats();
        const lowStockProducts = await api.getProducts({ low_stock: true, per_page: 10 });

        if (stats.low_stock_count > 0) {
            document.getElementById('lowStockAlert').classList.remove('hidden');
            document.getElementById('lowStockText').textContent = `${stats.low_stock_count} ürün kritik stokta`;
        }
        document.getElementById('productCountBadge').textContent = stats.total_products;

        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-8">
                <div>
                    <h1 class="text-2xl lg:text-3xl font-bold text-white">Ana Panel</h1>
                    <p class="text-gray-400 mt-1">Hoş geldiniz, ${api.user?.full_name || 'Kullanıcı'}</p>
                </div>
                <div class="text-sm text-gray-500">${new Date().toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
            </div>

            <!-- Stats Cards -->
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                <div class="glass rounded-2xl p-5 animate-slide-up" style="animation-delay: 0.05s">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-12 h-12 rounded-xl bg-deneyap-blue-500/20 flex items-center justify-center">
                            <span class="material-icons-outlined text-deneyap-blue-400 text-2xl">inventory_2</span>
                        </div>
                        <span class="text-xs text-gray-500 bg-slate-800 px-2 py-1 rounded-lg">Toplam</span>
                    </div>
                    <p class="text-3xl font-bold text-white">${stats.total_products}</p>
                    <p class="text-sm text-gray-400 mt-1">Ürün Çeşidi</p>
                </div>
                <div class="glass rounded-2xl p-5 animate-slide-up" style="animation-delay: 0.1s">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center">
                            <span class="material-icons-outlined text-red-400 text-2xl">warning</span>
                        </div>
                        <span class="text-xs ${stats.low_stock_count > 0 ? 'text-red-400 bg-red-500/10' : 'text-gray-500 bg-slate-800'} px-2 py-1 rounded-lg">${stats.low_stock_count > 0 ? 'Dikkat!' : 'İyi'}</span>
                    </div>
                    <p class="text-3xl font-bold ${stats.low_stock_count > 0 ? 'text-red-400' : 'text-white'}">${stats.low_stock_count}</p>
                    <p class="text-sm text-gray-400 mt-1">Kritik Stok</p>
                </div>
                <div class="glass rounded-2xl p-5 animate-slide-up" style="animation-delay: 0.15s">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center">
                            <span class="material-icons-outlined text-orange-400 text-2xl">build</span>
                        </div>
                    </div>
                    <p class="text-3xl font-bold text-white">${stats.broken_count}</p>
                    <p class="text-sm text-gray-400 mt-1">Bozuk / Kırık</p>
                </div>
                <div class="glass rounded-2xl p-5 animate-slide-up" style="animation-delay: 0.2s">
                    <div class="flex items-center justify-between mb-3">
                        <div class="w-12 h-12 rounded-xl bg-deneyap-yellow-500/20 flex items-center justify-center">
                            <span class="material-icons-outlined text-deneyap-yellow-400 text-2xl">warehouse</span>
                        </div>
                    </div>
                    <p class="text-3xl font-bold text-white">${allWarehouses.length}</p>
                    <p class="text-sm text-gray-400 mt-1">Depo</p>
                </div>
            </div>

            <!-- Category Breakdown -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
                ${Object.entries(stats.categories).map(([cat, count]) => {
                    const colors = { 'Sarf Malzemesi': 'deneyap-red', 'Genel / Dayanıklı Malzeme': 'deneyap-blue', 'Elektronik Bileşen': 'deneyap-yellow' };
                    const c = colors[cat] || 'deneyap-blue';
                    const pct = stats.total_products > 0 ? Math.round((count / stats.total_products) * 100) : 0;
                    return `
                    <div class="glass rounded-2xl p-5">
                        <div class="flex items-center gap-3 mb-3">
                            <span class="material-icons-outlined text-${c}-400">${getCategoryIcon(cat)}</span>
                            <span class="text-sm font-medium text-gray-300">${cat}</span>
                        </div>
                        <div class="flex items-end justify-between">
                            <span class="text-2xl font-bold text-white">${count}</span>
                            <span class="text-xs text-gray-500">%${pct}</span>
                        </div>
                        <div class="w-full bg-slate-700 rounded-full h-1.5 mt-3">
                            <div class="bg-${c}-500 h-1.5 rounded-full transition-all" style="width: ${pct}%"></div>
                        </div>
                    </div>`;
                }).join('')}
            </div>

            <!-- Low Stock Products -->
            ${lowStockProducts.length > 0 ? `
            <div class="glass rounded-2xl p-5">
                <div class="flex items-center justify-between mb-4">
                    <h3 class="text-lg font-bold text-white flex items-center gap-2">
                        <span class="material-icons-outlined text-red-400">warning</span>Kritik Stok Uyarıları
                    </h3>
                    <button onclick="navigateTo('products'); setTimeout(() => { document.querySelector('[data-filter=low]')?.click(); }, 200)" class="text-sm text-deneyap-blue-400 hover:text-deneyap-blue-300">Tümünü Gör →</button>
                </div>
                <div class="overflow-x-auto"><table class="w-full">
                    <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700">
                        <th class="pb-3 text-left">Ürün</th><th class="pb-3 text-center">Mevcut</th><th class="pb-3 text-center">Kritik</th><th class="pb-3 text-center">Depo</th>
                    </tr></thead>
                    <tbody>${lowStockProducts.slice(0, 5).map(p => `
                        <tr class="border-b border-slate-700/50 hover:bg-slate-800/30 cursor-pointer" onclick="showProductDetail(${p.id})">
                            <td class="py-3"><div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg overflow-hidden bg-slate-700 flex-shrink-0">
                                    ${p.image_url ? `<img src="${p.image_url}" class="w-full h-full object-cover" onerror="this.parentElement.innerHTML='<span class=\\'material-icons-outlined text-gray-600 w-full h-full flex items-center justify-center\\'>image</span>'">` : '<span class="material-icons-outlined text-gray-600 w-full h-full flex items-center justify-center">image</span>'}
                                </div>
                                <div><p class="text-sm font-medium text-white">${p.name}</p><p class="text-xs text-gray-500">${p.category}</p></div>
                            </div></td>
                            <td class="py-3 text-center"><span class="text-red-400 font-bold">${p.current_stock}</span></td>
                            <td class="py-3 text-center"><span class="text-gray-400">${p.critical_stock}</span></td>
                            <td class="py-3 text-center"><span class="text-xs text-gray-500">${p.warehouse_name || '-'}</span></td>
                        </tr>`).join('')}</tbody>
                </table></div>
            </div>` : '<div class="glass rounded-2xl p-8 text-center"><span class="material-icons-outlined text-green-400 text-4xl mb-2">check_circle</span><p class="text-gray-300">Tüm stoklar yeterli seviyede!</p></div>'}
        </div>`;
    } catch (err) {
        content.innerHTML = `<div class="text-center py-20 text-red-400"><span class="material-icons-outlined text-5xl mb-4">error</span><p>${err.message}</p></div>`;
    }
}
