// ==================== WAREHOUSES PAGE ====================
async function renderWarehousesPage() {
    const content = document.getElementById('pageContent');
    try {
        const warehouses = await api.getWarehouses();
        allWarehouses = warehouses;
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-white">Depo Yönetimi</h1>
                <button onclick="showWarehouseForm()" class="admin-only flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Depo
                </button>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                ${warehouses.map(w => `
                <div class="glass rounded-2xl p-5 product-card">
                    <div class="flex items-start justify-between mb-4">
                        <div class="flex items-center gap-3">
                            <div class="w-12 h-12 rounded-xl bg-deneyap-blue-500/20 flex items-center justify-center">
                                <span class="material-icons-outlined text-deneyap-blue-400 text-2xl">warehouse</span>
                            </div>
                            <div>
                                <h3 class="text-lg font-bold text-white">${w.name}</h3>
                                <p class="text-xs text-gray-400">${w.description || ''}</p>
                                ${w.location ? `<p class="text-xs text-gray-500 mt-1 flex items-center gap-1"><span class="material-icons-outlined text-xs">location_on</span>${w.location}</p>` : ''}
                            </div>
                        </div>
                        <div class="flex gap-1 admin-only">
                            <button onclick="showWarehouseStructure(${w.id})" class="text-gray-400 hover:text-deneyap-blue-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Yapıyı Görüntüle">
                                <span class="material-icons-outlined text-lg">account_tree</span>
                            </button>
                            <button onclick="showWarehouseForm(${w.id}, '${w.name}', '${w.description||''}', '${w.location||''}')" class="text-gray-400 hover:text-yellow-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Düzenle">
                                <span class="material-icons-outlined text-lg">edit</span>
                            </button>
                            <button onclick="deleteWarehouse(${w.id})" class="text-gray-400 hover:text-red-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Sil">
                                <span class="material-icons-outlined text-lg">delete</span>
                            </button>
                        </div>
                    </div>
                    <div class="flex gap-2">
                        <button onclick="navigateTo('products'); setTimeout(()=>{ document.getElementById('filterWarehouse').value='${w.id}'; productFilters.warehouse_id='${w.id}'; loadProducts(); }, 200)" class="flex-1 bg-slate-800 hover:bg-slate-700 text-gray-300 py-2 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-1">
                            <span class="material-icons-outlined text-sm">inventory_2</span>Ürünleri Gör
                        </button>
                        <button onclick="showWarehouseStructure(${w.id})" class="flex-1 bg-slate-800 hover:bg-slate-700 text-gray-300 py-2 rounded-xl text-xs font-medium transition-all flex items-center justify-center gap-1">
                            <span class="material-icons-outlined text-sm">account_tree</span>Dolap/Raf Yapısı
                        </button>
                    </div>
                </div>`).join('')}
            </div>
            ${warehouses.length === 0 ? '<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">warehouse</span><p class="text-gray-400 text-lg">Henüz depo eklenmemiş</p></div>' : ''}
        </div>`;
        document.querySelectorAll('.admin-only').forEach(el => { el.style.display = api.isAdmin() ? '' : 'none'; });
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}

function showWarehouseForm(id = null, name = '', desc = '', loc = '') {
    const isEdit = !!id;
    const formContent = `
    <form id="warehouseForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5">Depo Adı *</label>
            <input type="text" name="name" value="${name}" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Açıklama</label>
            <textarea name="description" rows="2" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">${desc}</textarea></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Konum</label>
            <input type="text" name="location" value="${loc}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
    </form>`;
    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button onclick="submitWarehouseForm(${id || 'null'})" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">${isEdit ? 'Güncelle' : 'Ekle'}</button>`;
    showModal(isEdit ? 'Depoyu Düzenle' : 'Yeni Depo Ekle', formContent, footer);
}

async function submitWarehouseForm(id) {
    const form = document.getElementById('warehouseForm');
    const fd = new FormData(form);
    const data = { name: fd.get('name'), description: fd.get('description'), location: fd.get('location') };
    try {
        if (id) { await api.updateWarehouse(id, data); showToast('Depo güncellendi'); }
        else { await api.createWarehouse(data); showToast('Depo eklendi'); }
        closeModal(); renderWarehousesPage();
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteWarehouse(id) {
    if (!confirm('Bu depoyu ve içindeki tüm ürünleri silmek istediğinize emin misiniz?')) return;
    try { await api.deleteWarehouse(id); showToast('Depo silindi'); renderWarehousesPage(); } catch (err) { showToast(err.message, 'error'); }
}

async function showWarehouseStructure(warehouseId) {
    try {
        const structure = await api.getWarehouseStructure(warehouseId);
        let html = `<div class="space-y-3">
            <div class="flex items-center justify-between mb-4">
                <p class="text-sm text-gray-400">Dolap, raf ve bölme yapısını yönetin</p>
                <button onclick="addCabinet(${warehouseId})" class="admin-only text-xs bg-deneyap-blue-500/20 text-deneyap-blue-400 hover:bg-deneyap-blue-500/30 px-3 py-1.5 rounded-lg transition-all flex items-center gap-1"><span class="material-icons-outlined text-sm">add</span>Dolap Ekle</button>
            </div>`;
        if (structure.cabinets.length === 0) {
            html += '<p class="text-center text-gray-500 py-8">Henüz dolap eklenmemiş</p>';
        }
        structure.cabinets.forEach(cab => {
            html += `<div class="bg-slate-800/50 rounded-xl p-4 border border-slate-700/30">
                <div class="flex items-center justify-between mb-3">
                    <div class="flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">door_sliding</span><span class="text-sm font-medium text-white">${cab.name}</span></div>
                    <div class="flex gap-1 admin-only">
                        <button onclick="addShelf(${cab.id}, ${warehouseId})" class="text-xs text-gray-400 hover:text-green-400 p-1" title="Raf Ekle"><span class="material-icons-outlined text-sm">add</span></button>
                        <button onclick="deleteCabinet(${cab.id}, ${warehouseId})" class="text-xs text-gray-400 hover:text-red-400 p-1" title="Sil"><span class="material-icons-outlined text-sm">delete</span></button>
                    </div>
                </div>`;
            cab.shelves.forEach(shelf => {
                html += `<div class="ml-6 mb-2 bg-slate-700/30 rounded-lg p-3">
                    <div class="flex items-center justify-between mb-2">
                        <div class="flex items-center gap-2"><span class="material-icons-outlined text-deneyap-blue-400 text-sm">shelves</span><span class="text-xs font-medium text-gray-300">${shelf.name}</span></div>
                        <div class="flex gap-1 admin-only">
                            <button onclick="addCompartment(${shelf.id}, ${warehouseId})" class="text-gray-400 hover:text-green-400 p-0.5"><span class="material-icons-outlined text-xs">add</span></button>
                            <button onclick="deleteShelf(${shelf.id}, ${warehouseId})" class="text-gray-400 hover:text-red-400 p-0.5"><span class="material-icons-outlined text-xs">delete</span></button>
                        </div>
                    </div>`;
                if (shelf.compartments.length > 0) {
                    html += `<div class="ml-4 flex flex-wrap gap-1">${shelf.compartments.map(c => `
                        <span class="text-[10px] bg-slate-700 text-gray-400 px-2 py-1 rounded flex items-center gap-1">${c.name}
                            <button onclick="deleteCompartment(${c.id}, ${warehouseId})" class="text-gray-500 hover:text-red-400 admin-only"><span class="material-icons-outlined text-xs">close</span></button>
                        </span>`).join('')}</div>`;
                }
                html += '</div>';
            });
            html += '</div>';
        });
        html += '</div>';
        showModal(`${structure.warehouse.name} - Yapı`, html);
        document.querySelectorAll('.admin-only').forEach(el => { el.style.display = api.isAdmin() ? '' : 'none'; });
    } catch (err) { showToast(err.message, 'error'); }
}

async function addCabinet(warehouseId) {
    showPromptModal('Yeni Dolap', 'Dolap Adı:', '', 'text', async (name) => {
        if (!name) { showWarehouseStructure(warehouseId); return; }
        try { await api.createCabinet({ name, warehouse_id: warehouseId }); showToast('Dolap eklendi'); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
    }, () => showWarehouseStructure(warehouseId));
}
async function addShelf(cabinetId, warehouseId) {
    showPromptModal('Yeni Raf', 'Raf Adı:', '', 'text', async (name) => {
        if (!name) { showWarehouseStructure(warehouseId); return; }
        try { await api.createShelf({ name, cabinet_id: cabinetId }); showToast('Raf eklendi'); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
    }, () => showWarehouseStructure(warehouseId));
}
async function addCompartment(shelfId, warehouseId) {
    showPromptModal('Yeni Bölme', 'Bölme Adı:', '', 'text', async (name) => {
        if (!name) { showWarehouseStructure(warehouseId); return; }
        try { await api.createCompartment({ name, shelf_id: shelfId }); showToast('Bölme eklendi'); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
    }, () => showWarehouseStructure(warehouseId));
}
async function deleteCabinet(id, warehouseId) {
    if (!confirm('Bu dolabı silmek istediğinize emin misiniz?')) return;
    try { await api.deleteCabinet(id); showToast('Dolap silindi'); closeModal(); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
}
async function deleteShelf(id, warehouseId) {
    if (!confirm('Bu rafı silmek istediğinize emin misiniz?')) return;
    try { await api.deleteShelf(id); showToast('Raf silindi'); closeModal(); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
}
async function deleteCompartment(id, warehouseId) {
    try { await api.deleteCompartment(id); showToast('Bölme silindi'); closeModal(); showWarehouseStructure(warehouseId); } catch (err) { showToast(err.message, 'error'); }
}
