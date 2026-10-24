// ==================== DEPOLAR ====================
async function renderWarehousesPage() {
    const content = document.getElementById('pageContent');
    try {
        allWarehouses = await api.getWarehouses();
        if (currentPage !== 'warehouses') return;
        const admin = api.isAdmin();
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6 gap-3">
                <div>
                    <h1 class="text-2xl font-bold text-white">Depo Yönetimi</h1>
                    <p class="text-sm text-gray-400 mt-1">Depo › Dolap › Raf › Bölme yapısıyla her malzemenin yerini kaydedin.</p>
                </div>
                ${admin ? `<button onclick="showWarehouseForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Depo</button>` : ''}
            </div>
            ${allWarehouses.length === 0 ? `<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">warehouse</span>
                <p class="text-gray-400 text-lg">${admin ? 'Henüz depo eklenmemiş' : 'Size henüz bir depo yetkisi verilmemiş. Yöneticinize başvurun.'}</p></div>` : ''}
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                ${allWarehouses.map(w => `
                <div class="glass rounded-2xl p-5">
                    <div class="flex items-start justify-between mb-4 gap-3">
                        <div class="flex items-center gap-3 min-w-0">
                            <div class="w-12 h-12 rounded-xl bg-deneyap-blue-500/20 flex items-center justify-center flex-shrink-0">
                                <span class="material-icons-outlined text-deneyap-blue-400 text-2xl">warehouse</span>
                            </div>
                            <div class="min-w-0">
                                <h3 class="text-lg font-bold text-white truncate">${esc(w.name)}</h3>
                                ${w.description ? `<p class="text-xs text-gray-400">${esc(w.description)}</p>` : ''}
                                ${w.location ? `<p class="text-xs text-gray-500 mt-1 flex items-center gap-1"><span class="material-icons-outlined text-xs">location_on</span>${esc(w.location)}</p>` : ''}
                            </div>
                        </div>
                        <div class="flex items-center gap-1 flex-shrink-0">
                            <span class="text-xs bg-slate-800 text-gray-300 px-2 py-1 rounded-lg mr-1">${fmtNumber(w.product_count)} ürün</span>
                            ${admin ? `
                            <button onclick="showWarehouseForm(${w.id})" class="text-gray-400 hover:text-yellow-400 p-1.5 rounded-lg hover:bg-slate-800" title="Düzenle" aria-label="Düzenle"><span class="material-icons-outlined text-lg">edit</span></button>
                            <button onclick="deleteWarehouse(${w.id})" class="text-gray-400 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-800" title="Sil" aria-label="Sil"><span class="material-icons-outlined text-lg">delete</span></button>` : ''}
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="goToProducts({ warehouse_id: '${w.id}' })" class="flex-1 bg-slate-800 hover:bg-slate-700 text-gray-300 py-2 rounded-xl text-xs font-medium flex items-center justify-center gap-1">
                            <span class="material-icons-outlined text-sm">inventory_2</span>Ürünleri Gör</button>
                        <button onclick="showWarehouseStructure(${w.id})" class="flex-1 bg-slate-800 hover:bg-slate-700 text-gray-300 py-2 rounded-xl text-xs font-medium flex items-center justify-center gap-1">
                            <span class="material-icons-outlined text-sm">account_tree</span>Dolap/Raf Yapısı</button>
                    </div>
                </div>`).join('')}
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${esc(err.message)}</div>`; }
}

function showWarehouseForm(id = null) {
    const w = id ? allWarehouses.find(x => x.id === id) : null;
    const content = `
    <form id="warehouseForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5" for="whName">Depo adı *</label>
            <input type="text" id="whName" name="name" value="${esc(w?.name || '')}" required maxlength="255" autofocus class="${inputClass()}"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="whDesc">Açıklama</label>
            <textarea id="whDesc" name="description" rows="2" maxlength="2000" class="${inputClass()}">${esc(w?.description || '')}</textarea></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="whLoc">Konum</label>
            <input type="text" id="whLoc" name="location" value="${esc(w?.location || '')}" maxlength="255" placeholder="Örn: Atölye 1. kat" class="${inputClass()}"></div>
    </form>`;
    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button type="submit" form="warehouseForm" id="whSubmit" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">${w ? 'Güncelle' : 'Ekle'}</button>`;
    showModal(w ? 'Depoyu Düzenle' : 'Yeni Depo Ekle', content, footer, { size: 'sm' });
    document.getElementById('warehouseForm').onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const data = { name: fd.get('name').trim(), description: fd.get('description').trim(), location: fd.get('location').trim() };
        if (!data.name) return showToast('Depo adı boş olamaz', 'warning');
        const btn = document.getElementById('whSubmit');
        setButtonLoading(btn, true);
        try {
            if (w) { await api.updateWarehouse(w.id, data); showToast('Depo güncellendi'); }
            else { await api.createWarehouse(data); showToast('Depo eklendi'); }
            closeModal();
            renderWarehousesPage();
        } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
    };
}

async function deleteWarehouse(id) {
    const w = allWarehouses.find(x => x.id === id);
    if (!w) return;
    const ok = await confirmModal('Depoyu Sil',
        `"${w.name}" deposu, içindeki dolap/raf/bölmeler ve ${w.product_count} ürün kalıcı olarak silinecek. Bu işlem geri alınamaz.`,
        { confirmText: 'Depoyu Sil', danger: true, requireText: w.product_count > 0 ? 'SİL' : null });
    if (!ok) return;
    try {
        await api.deleteWarehouse(id);
        showToast('Depo silindi');
        await loadInitialData();
        renderWarehousesPage();
        refreshStatsBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

// ---------- Dolap / Raf / Bölme yapısı ----------
async function showWarehouseStructure(warehouseId) {
    try {
        const structure = await api.getWarehouseStructure(warehouseId);
        const admin = api.isAdmin();
        const btn = (onclick, icon, title, color) => admin
            ? `<button type="button" onclick="${onclick}" class="text-gray-400 ${color} p-1" title="${title}" aria-label="${title}"><span class="material-icons-outlined text-sm">${icon}</span></button>` : '';
        let html = `<div class="space-y-3">
            <div class="flex items-center justify-between mb-2 gap-3">
                <p class="text-sm text-gray-400">${admin ? 'Dolap, raf ve bölmeleri ekleyin, adlandırın veya silin.' : 'Bu deponun fiziksel yerleşimi.'}</p>
                ${admin ? `<button type="button" onclick="addLocation('cabinet', ${warehouseId}, ${warehouseId})" class="text-xs bg-deneyap-blue-500/20 text-deneyap-blue-400 hover:bg-deneyap-blue-500/30 px-3 py-1.5 rounded-lg flex items-center gap-1 whitespace-nowrap"><span class="material-icons-outlined text-sm">add</span>Dolap Ekle</button>` : ''}
            </div>`;
        if (structure.cabinets.length === 0) html += '<p class="text-center text-gray-500 py-8">Henüz dolap eklenmemiş</p>';
        structure.cabinets.forEach(cab => {
            html += `<div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">door_sliding</span><span class="text-sm font-medium text-white">${esc(cab.name)}</span></div>
                    <div class="flex gap-1">
                        ${btn(`addLocation('shelf', ${cab.id}, ${warehouseId})`, 'add', 'Raf ekle', 'hover:text-green-400')}
                        ${btn(`renameLocation('cabinet', ${cab.id}, ${warehouseId})`, 'edit', 'Yeniden adlandır', 'hover:text-yellow-400')}
                        ${btn(`deleteLocation('cabinet', ${cab.id}, ${warehouseId})`, 'delete', 'Sil', 'hover:text-red-400')}
                    </div>
                </div>`;
            cab.shelves.forEach(shelf => {
                html += `<div class="ml-4 sm:ml-6 mb-2 bg-slate-700/30 rounded-lg p-3">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2"><span class="material-icons-outlined text-deneyap-blue-400 text-sm">shelves</span><span class="text-xs font-medium text-gray-300">${esc(shelf.name)}</span></div>
                        <div class="flex gap-1">
                            ${btn(`addLocation('compartment', ${shelf.id}, ${warehouseId})`, 'add', 'Bölme ekle', 'hover:text-green-400')}
                            ${btn(`renameLocation('shelf', ${shelf.id}, ${warehouseId})`, 'edit', 'Yeniden adlandır', 'hover:text-yellow-400')}
                            ${btn(`deleteLocation('shelf', ${shelf.id}, ${warehouseId})`, 'delete', 'Sil', 'hover:text-red-400')}
                        </div>
                    </div>
                    ${shelf.compartments.length ? `<div class="ml-4 flex flex-wrap gap-1">${shelf.compartments.map(c => `
                        <span class="text-[11px] bg-slate-700 text-gray-300 px-2 py-1 rounded flex items-center gap-1">${esc(c.name)}
                            ${btn(`renameLocation('compartment', ${c.id}, ${warehouseId})`, 'edit', 'Yeniden adlandır', 'hover:text-yellow-400')}
                            ${btn(`deleteLocation('compartment', ${c.id}, ${warehouseId})`, 'close', 'Sil', 'hover:text-red-400')}
                        </span>`).join('')}</div>` : ''}
                </div>`;
            });
            html += '</div>';
        });
        html += '</div>';
        window._structureCache = structure;
        showModal(`${structure.warehouse.name} - Yapı`, html, '', { size: 'lg' });
    } catch (err) { showToast(err.message, 'error'); }
}

const LOCATION_LABELS = { cabinet: 'Dolap', shelf: 'Raf', compartment: 'Bölme' };

function findLocationName(kind, id) {
    const s = window._structureCache;
    if (!s) return '';
    for (const cab of s.cabinets) {
        if (kind === 'cabinet' && cab.id === id) return cab.name;
        for (const shelf of cab.shelves) {
            if (kind === 'shelf' && shelf.id === id) return shelf.name;
            for (const c of shelf.compartments) if (kind === 'compartment' && c.id === id) return c.name;
        }
    }
    return '';
}

function addLocation(kind, parentId, warehouseId) {
    const label = LOCATION_LABELS[kind];
    showPromptModal(`Yeni ${label}`, `${label} adı`, '', 'text', async (name) => {
        name = name.trim();
        if (!name) return showWarehouseStructure(warehouseId);
        try {
            if (kind === 'cabinet') await api.createCabinet({ name, warehouse_id: parentId });
            if (kind === 'shelf') await api.createShelf({ name, cabinet_id: parentId });
            if (kind === 'compartment') await api.createCompartment({ name, shelf_id: parentId });
            showToast(`${label} eklendi`);
        } catch (err) { showToast(err.message, 'error'); }
        showWarehouseStructure(warehouseId);
    }, () => showWarehouseStructure(warehouseId));
}

function renameLocation(kind, id, warehouseId) {
    const label = LOCATION_LABELS[kind];
    showPromptModal(`${label} Adını Değiştir`, `Yeni ${label.toLocaleLowerCase('tr-TR')} adı`, findLocationName(kind, id), 'text', async (name) => {
        name = name.trim();
        if (!name) return showWarehouseStructure(warehouseId);
        try {
            if (kind === 'cabinet') await api.renameCabinet(id, name);
            if (kind === 'shelf') await api.renameShelf(id, name);
            if (kind === 'compartment') await api.renameCompartment(id, name);
            showToast(`${label} adı güncellendi`);
        } catch (err) { showToast(err.message, 'error'); }
        showWarehouseStructure(warehouseId);
    }, () => showWarehouseStructure(warehouseId));
}

async function deleteLocation(kind, id, warehouseId) {
    const label = LOCATION_LABELS[kind];
    const extra = kind === 'compartment' ? '' : ' İçindeki alt birimler de silinir.';
    const ok = await confirmModal(`${label} Sil`, `"${findLocationName(kind, id)}" silinecek.${extra} İçindeki ürünler silinmez, sadece konumları boşaltılır.`,
        { confirmText: 'Sil', danger: true, onCancel: () => showWarehouseStructure(warehouseId) });
    if (!ok) return;
    try {
        if (kind === 'cabinet') await api.deleteCabinet(id);
        if (kind === 'shelf') await api.deleteShelf(id);
        if (kind === 'compartment') await api.deleteCompartment(id);
        showToast(`${label} silindi`);
    } catch (err) { showToast(err.message, 'error'); }
    showWarehouseStructure(warehouseId);
}
