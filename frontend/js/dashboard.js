// ==================== ANA PANEL ====================
const CATEGORY_STYLES = {
    'Sarf Malzemesi': { icon: 'text-deneyap-red-400', bar: 'bg-deneyap-red-500' },
    'Genel / Dayanıklı Malzeme': { icon: 'text-deneyap-blue-400', bar: 'bg-deneyap-blue-500' },
    'Elektronik Bileşen': { icon: 'text-deneyap-yellow-400', bar: 'bg-deneyap-yellow-500' },
};

function updateLowStockBadge(stats) {
    const alert = document.getElementById('lowStockAlert');
    alert.classList.toggle('hidden', !(stats.low_stock_count > 0));
    document.getElementById('lowStockText').textContent = `${fmtNumber(stats.low_stock_count)} ürün kritik stokta`;
    document.getElementById('productCountBadge').textContent = fmtNumber(stats.total_products);
}

function productThumb(p, size = 'w-10 h-10') {
    return `<div class="${size} relative rounded-lg overflow-hidden bg-slate-700 flex-shrink-0 flex items-center justify-center">
        <span class="material-icons-outlined text-gray-600 text-lg">image</span>
        ${p.image_url ? `<img src="${esc(p.image_url)}" alt="" loading="lazy" class="absolute inset-0 w-full h-full object-cover bg-slate-700" onerror="this.remove()">` : ''}</div>`;
}

async function renderDashboard() {
    const content = document.getElementById('pageContent');
    try {
        const [stats, lowStock, logs] = await Promise.all([
            api.getProductStats(),
            api.getProductsPage({ low_stock: true, per_page: 6, sort: 'stock_asc' }),
            api.getLogs({ limit: 6 }).catch(() => []),
        ]);
        if (currentPage !== 'dashboard') return;
        updateLowStockBadge(stats);

        const card = (onclick, icon, iconBg, iconColor, value, label, badge = '') => `
            <button type="button" onclick="${onclick}" class="glass rounded-2xl p-5 text-left animate-slide-up transition-all duration-300 hover:scale-[1.03] hover:shadow-lg">
                <div class="flex items-center justify-between mb-3">
                    <div class="w-12 h-12 rounded-xl ${iconBg} flex items-center justify-center"><span class="material-icons-outlined ${iconColor} text-2xl">${icon}</span></div>
                    ${badge}
                </div>
                <p class="text-3xl font-bold text-white">${value}</p>
                <p class="text-sm text-gray-400 mt-1">${label}</p>
            </button>`;

        const lowBadge = stats.low_stock_count > 0
            ? '<span class="text-xs text-red-400 bg-red-500/10 px-2 py-1 rounded-lg">Dikkat!</span>'
            : '<span class="text-xs text-gray-500 bg-slate-800 px-2 py-1 rounded-lg">İyi</span>';

        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-8">
                <div>
                    <h1 class="text-2xl lg:text-3xl font-bold text-white">Ana Panel</h1>
                    <p class="text-gray-400 mt-1">Hoş geldiniz, ${esc(api.user?.full_name || 'Kullanıcı')}</p>
                </div>
                <div class="text-sm text-gray-500">${new Date().toLocaleDateString('tr-TR', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                ${card('goToProducts({})', 'inventory_2', 'bg-deneyap-blue-500/20', 'text-deneyap-blue-400', fmtNumber(stats.total_products), 'Ürün Çeşidi', '<span class="text-xs text-gray-500 bg-slate-800 px-2 py-1 rounded-lg">Toplam</span>')}
                ${card('goToProducts({ low_stock: true })', 'warning', 'bg-red-500/20', 'text-red-400', `<span class="${stats.low_stock_count > 0 ? 'text-red-400' : ''}">${fmtNumber(stats.low_stock_count)}</span>`, 'Kritik Stok', lowBadge)}
                ${card("goToProducts({ status: 'Bozuk / Kırık' })", 'build', 'bg-orange-500/20', 'text-orange-400', fmtNumber(stats.broken_count), 'Bozuk / Kırık')}
                ${card("navigateTo('warehouses')", 'warehouse', 'bg-deneyap-yellow-500/20', 'text-deneyap-yellow-400', fmtNumber(allWarehouses.length), 'Depo')}
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-8">
                ${Object.entries(stats.categories).map(([cat, count]) => {
                    const style = CATEGORY_STYLES[cat] || CATEGORY_STYLES['Genel / Dayanıklı Malzeme'];
                    const pct = stats.total_products > 0 ? Math.round((count / stats.total_products) * 100) : 0;
                    return `
                    <button type="button" data-category="${esc(cat)}" onclick="goToProducts({ category: this.dataset.category })" class="glass rounded-2xl p-5 text-left transition-all duration-300 hover:scale-[1.02] hover:shadow-lg">
                        <div class="flex items-center gap-3 mb-3">
                            <span class="material-icons-outlined ${style.icon}">${getCategoryIcon(cat)}</span>
                            <span class="text-sm font-medium text-gray-300">${esc(cat)}</span>
                        </div>
                        <div class="flex items-end justify-between">
                            <span class="text-2xl font-bold text-white">${fmtNumber(count)}</span>
                            <span class="text-xs text-gray-500">%${pct}</span>
                        </div>
                        <div class="w-full bg-slate-700 rounded-full h-1.5 mt-3"><div class="${style.bar} h-1.5 rounded-full" style="width: ${pct}%"></div></div>
                    </button>`;
                }).join('')}
            </div>

            <div class="grid grid-cols-1 xl:grid-cols-2 gap-4">
                ${lowStock.items.length > 0 ? `
                <div class="glass rounded-2xl p-5">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-bold text-white flex items-center gap-2"><span class="material-icons-outlined text-red-400">warning</span>Kritik Stok Uyarıları</h3>
                        <button onclick="goToProducts({ low_stock: true })" class="text-sm text-deneyap-blue-400 hover:text-deneyap-blue-300">Tümünü Gör (${fmtNumber(lowStock.total)}) →</button>
                    </div>
                    <div class="overflow-x-auto"><table class="w-full">
                        <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700">
                            <th class="pb-3 text-left">Ürün</th><th class="pb-3 text-center">Mevcut</th><th class="pb-3 text-center">Kritik</th><th class="pb-3 text-center">Depo</th>
                        </tr></thead>
                        <tbody>${lowStock.items.map(p => `
                            <tr class="border-b border-slate-700/50 hover:bg-slate-800/30 cursor-pointer" onclick="showProductDetail(${p.id})">
                                <td class="py-3"><div class="flex items-center gap-3">${productThumb(p)}
                                    <div class="min-w-0"><p class="text-sm font-medium text-white truncate">${esc(p.name)}</p><p class="text-xs text-gray-500">${esc(p.category)}</p></div>
                                </div></td>
                                <td class="py-3 text-center"><span class="text-red-400 font-bold">${fmtNumber(p.current_stock)}</span></td>
                                <td class="py-3 text-center"><span class="text-gray-400">${fmtNumber(p.critical_stock)}</span></td>
                                <td class="py-3 text-center"><span class="text-xs text-gray-500">${esc(p.warehouse_name || '-')}</span></td>
                            </tr>`).join('')}</tbody>
                    </table></div>
                </div>` : `
                <div class="glass rounded-2xl p-8 text-center flex flex-col items-center justify-center">
                    <span class="material-icons-outlined text-green-400 text-4xl mb-2">check_circle</span>
                    <p class="text-gray-300">${stats.total_products > 0 ? 'Tüm stoklar yeterli seviyede!' : 'Henüz ürün eklenmemiş.'}</p>
                    ${stats.total_products === 0 && api.isAdmin() ? `<div class="flex flex-wrap justify-center gap-2 mt-4">
                        <button onclick="navigateTo('products'); setTimeout(showProductForm, 150)" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2 rounded-xl text-sm">Ürün Ekle</button>
                        <button onclick="navigateTo('products'); setTimeout(showExcelImportModal, 150)" class="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-xl text-sm">Excel'den Aktar</button>
                    </div>` : ''}
                </div>`}

                <div class="glass rounded-2xl p-5">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-lg font-bold text-white flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">history</span>Son İşlemler</h3>
                        <button onclick="navigateTo('reports')" class="text-sm text-deneyap-blue-400 hover:text-deneyap-blue-300">Tümü →</button>
                    </div>
                    ${logs.length === 0 ? '<p class="text-center text-gray-500 py-6 text-sm">Henüz işlem kaydı yok</p>' : `
                    <div class="space-y-2">${logs.map(l => `
                        <button type="button" onclick="showProductDetail(${l.product_id})" class="w-full text-left flex items-center justify-between gap-3 text-sm py-2 border-b border-slate-700/30 hover:bg-slate-800/30 rounded">
                            <div class="min-w-0">
                                <p class="text-white truncate">${esc(l.product_name || '-')}</p>
                                <p class="text-xs text-gray-500"><span class="${ACTION_COLORS[l.action] || 'text-gray-400'}">${esc(ACTION_LABELS[l.action] || l.action)}</span> • ${esc(l.user_name || 'Sistem')}</p>
                            </div>
                            <div class="text-right flex-shrink-0">
                                <p class="text-xs text-gray-400">${esc(l.previous_value ?? '')} → ${esc(l.new_value ?? '')}</p>
                                <p class="text-[11px] text-gray-600">${fmtDateTime(l.created_at)}</p>
                            </div>
                        </button>`).join('')}</div>`}
                </div>
            </div>
        </div>`;
    } catch (err) {
        content.innerHTML = `<div class="text-center py-20 text-red-400"><span class="material-icons-outlined text-5xl mb-4">error</span><p>${esc(err.message)}</p></div>`;
    }
}
