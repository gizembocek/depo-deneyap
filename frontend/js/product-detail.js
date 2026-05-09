// ==================== PRODUCT DETAIL & FORM ====================
async function showProductDetail(id) {
    try {
        const p = await api.getProduct(id);
        const logs = await api.getProductLogs(id).catch(() => []);
        const isCritical = p.current_stock <= p.critical_stock;
        const stockPct = p.ideal_stock > 0 ? Math.min(100, Math.round((p.current_stock / p.ideal_stock) * 100)) : 100;

        const modalContent = `
        <div class="space-y-5">
            <!-- Image & Info -->
            <div class="flex flex-col sm:flex-row gap-5">
                <div class="w-full sm:w-48 h-48 bg-slate-800 rounded-xl overflow-hidden flex-shrink-0">
                    ${p.image_url ? `<img src="${p.image_url}" class="w-full h-full object-contain p-2" onerror="this.style.display='none'">` : '<div class="w-full h-full flex items-center justify-center"><span class="material-icons-outlined text-gray-600 text-6xl">image</span></div>'}
                </div>
                <div class="flex-1 space-y-3">
                    <div class="flex items-start justify-between gap-2">
                        <h2 class="text-xl font-bold text-white">${p.name}</h2>
                        <span class="${getStatusClass(p.status)} text-xs px-3 py-1 rounded-full font-medium">${p.status}</span>
                    </div>
                    <p class="text-sm text-gray-400">${p.description || 'Açıklama yok'}</p>
                    <div class="flex flex-wrap gap-2">
                        <span class="text-xs bg-slate-800 text-gray-300 px-3 py-1 rounded-lg flex items-center gap-1"><span class="material-icons-outlined text-xs">${getCategoryIcon(p.category)}</span>${p.category}</span>
                        ${p.courses?.map(c => `<span class="text-xs bg-deneyap-blue-500/10 text-deneyap-blue-400 px-3 py-1 rounded-lg">${c.name}</span>`).join('') || ''}
                    </div>
                </div>
            </div>

            <!-- Stock Section -->
            <div class="glass-light rounded-xl p-4">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-semibold text-gray-300">Stok Durumu</h3>
                    ${isCritical ? '<span class="text-xs text-red-400 flex items-center gap-1 stock-critical"><span class="material-icons-outlined text-sm">warning</span>Kritik Stok!</span>' : ''}
                </div>
                <div class="grid grid-cols-3 gap-4 mb-4">
                    <div class="text-center"><p class="text-2xl font-bold ${isCritical ? 'text-red-400' : 'text-white'}">${p.current_stock}</p><p class="text-xs text-gray-500">Mevcut</p></div>
                    <div class="text-center"><p class="text-2xl font-bold text-yellow-400">${p.critical_stock}</p><p class="text-xs text-gray-500">Kritik</p></div>
                    <div class="text-center"><p class="text-2xl font-bold text-green-400">${p.ideal_stock}</p><p class="text-xs text-gray-500">İdeal</p></div>
                </div>
                <div class="w-full bg-slate-700 rounded-full h-2 mb-4"><div class="bg-${isCritical ? 'red' : stockPct > 60 ? 'green' : 'yellow'}-500 h-2 rounded-full" style="width: ${stockPct}%"></div></div>
                <div class="flex items-center gap-2">
                    <button onclick="modifyStock(${p.id}, 'remove')" class="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">remove</span>Çıkar</button>
                    <button onclick="modifyStock(${p.id}, 'add')" class="flex-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">add</span>Ekle</button>
                    <button onclick="modifyStock(${p.id}, 'set')" class="flex-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 py-2.5 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">edit</span>Ayarla</button>
                </div>
            </div>

            <!-- Location -->
            <div class="glass-light rounded-xl p-4">
                <h3 class="text-sm font-semibold text-gray-300 mb-2">Konum</h3>
                <div class="flex flex-wrap gap-2 text-xs">
                    <span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg flex items-center gap-1"><span class="material-icons-outlined text-sm">warehouse</span>${p.warehouse_name || 'Atanmamış'}</span>
                    ${p.cabinet_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Dolap: ${p.cabinet_name}</span>` : ''}
                    ${p.shelf_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Raf: ${p.shelf_name}</span>` : ''}
                    ${p.compartment_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Bölme: ${p.compartment_name}</span>` : ''}
                </div>
            </div>

            <!-- Logs -->
            ${logs.length > 0 ? `
            <div class="glass-light rounded-xl p-4">
                <h3 class="text-sm font-semibold text-gray-300 mb-3">Son İşlemler</h3>
                <div class="space-y-2 max-h-40 overflow-y-auto">${logs.slice(0, 10).map(l => `
                    <div class="flex items-center justify-between text-xs py-1.5 border-b border-slate-700/30">
                        <div class="flex items-center gap-2"><span class="text-gray-400">${l.user_name || 'Sistem'}</span><span class="text-gray-600">•</span><span class="text-gray-500">${l.action}</span></div>
                        <div class="flex items-center gap-2"><span class="text-gray-400">${l.previous_value || ''} → ${l.new_value || ''}</span><span class="text-gray-600">${new Date(l.created_at).toLocaleString('tr-TR')}</span></div>
                    </div>`).join('')}
                </div>
            </div>` : ''}
        </div>`;

        const footer = `
            ${api.isAdmin() ? `<button onclick="closeModal(); showProductForm(${p.id})" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2"><span class="material-icons-outlined text-lg">edit</span>Düzenle</button>
            <button onclick="deleteProduct(${p.id})" class="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-5 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2"><span class="material-icons-outlined text-lg">delete</span>Sil</button>` : ''}
            <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">Kapat</button>`;

        showModal(p.name, modalContent, footer);
    } catch (err) { showToast(err.message, 'error'); }
}

async function modifyStock(productId, action) {
    const labels = { add: 'Eklenecek Miktar', remove: 'Çıkarılacak Miktar', set: 'Yeni Stok Miktarı' };
    const titles = { add: 'Stok Ekle', remove: 'Stok Çıkarma', set: 'Stok Ayarla' };
    
    showPromptModal(titles[action], labels[action], '1', 'number', async (qty) => {
        if (qty === null || qty === '') return;
        const num = parseInt(qty);
        if (isNaN(num) || num < 0) { showToast('Geçersiz miktar', 'error'); return; }
        try {
            const result = await api.updateStock(productId, { action, quantity: num });
            showToast(`Stok güncellendi: ${result.current_stock}`, result.is_critical ? 'warning' : 'success');
            showProductDetail(productId);
            if (currentPage === 'products') loadProducts();
        } catch (err) { showToast(err.message, 'error'); }
    }, () => {
        showProductDetail(productId);
    });
}

async function deleteProduct(id) {
    if (!confirm('Bu ürünü silmek istediğinize emin misiniz?')) return;
    try {
        await api.deleteProduct(id);
        showToast('Ürün silindi');
        closeModal();
        loadProducts();
    } catch (err) { showToast(err.message, 'error'); }
}

async function showProductForm(editId = null) {
    let product = null;
    if (editId) { try { product = await api.getProduct(editId); } catch(e) {} }
    const isEdit = !!product;
    const title = isEdit ? 'Ürün Düzenle' : 'Yeni Ürün Ekle';

    const formContent = `
    <form id="productForm" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">Ürün Adı *</label>
                <input type="text" name="name" value="${product?.name || ''}" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">Kategori</label>
                <select name="category" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="Genel / Dayanıklı Malzeme" ${product?.category === 'Genel / Dayanıklı Malzeme' ? 'selected' : ''}>Genel / Dayanıklı Malzeme</option>
                    <option value="Sarf Malzemesi" ${product?.category === 'Sarf Malzemesi' ? 'selected' : ''}>Sarf Malzemesi</option>
                    <option value="Elektronik Bileşen" ${product?.category === 'Elektronik Bileşen' ? 'selected' : ''}>Elektronik Bileşen</option>
                </select></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Açıklama</label>
            <textarea name="description" rows="2" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">${product?.description || ''}</textarea></div>
        <div>
            <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">photo_camera</span>Ürün Fotoğrafı</label>
            ${product?.image_url ? `<div id="imgPreviewWrap" class="mb-2 w-full h-32 bg-slate-800 rounded-xl overflow-hidden flex items-center justify-center border border-slate-700"><img id="imgPreview" src="${product.image_url}" class="h-full w-full object-contain p-1" onerror="this.parentElement.style.display='none'"></div>` : `<div id="imgPreviewWrap" class="hidden mb-2 w-full h-32 bg-slate-800 rounded-xl overflow-hidden flex items-center justify-center border border-slate-700"><img id="imgPreview" class="h-full w-full object-contain p-1"></div>`}
            <input type="file" id="imageUpload" accept="image/*" onchange="handleImageUpload(this)" class="w-full text-xs text-gray-400 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2">
            <input type="hidden" name="image_url" id="imageUrlHidden" value="${product?.image_url || ''}">
        </div>
        <div class="grid grid-cols-3 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">Stok</label><input type="number" name="current_stock" value="${product?.current_stock ?? 0}" min="0" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">Kritik Stok</label><input type="number" name="critical_stock" value="${product?.critical_stock ?? 5}" min="0" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">İdeal Stok</label><input type="number" name="ideal_stock" value="${product?.ideal_stock ?? 100}" min="0" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        </div>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">Durum</label>
                <select name="status" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    ${['Çalışan','Bozuk / Kırık','Garantide','Demirbaştan düşülecek','Kırık ürün kutusunda'].map(s => `<option value="${s}" ${product?.status === s ? 'selected' : ''}>${s}</option>`).join('')}
                </select></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">Depo</label>
                <select name="warehouse_id" onchange="loadLocationDropdowns(this.value)" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="">Seçiniz</option>
                    ${allWarehouses.map(w => `<option value="${w.id}" ${product?.warehouse_id == w.id ? 'selected' : ''}>${w.name}</option>`).join('')}
                </select></div>
        </div>
        <div id="prodLocationContainer" class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <!-- Dinamik dolap/raf yüklemesi -->
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Dersler</label>
            <div class="grid grid-cols-2 gap-2 max-h-40 overflow-y-auto bg-slate-800 rounded-xl p-3">
                ${allCourses.map(c => `<label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer"><input type="checkbox" name="course_ids" value="${c.id}" ${product?.courses?.some(pc => pc.id === c.id) ? 'checked' : ''} class="rounded border-slate-600 text-deneyap-blue-500 focus:ring-deneyap-blue-500">${c.name}</label>`).join('')}
            </div>
        </div>
    </form>`;

    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">İptal</button>
        <button onclick="submitProductForm(${editId || 'null'})" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2"><span class="material-icons-outlined text-lg">save</span>${isEdit ? 'Güncelle' : 'Ekle'}</button>`;

    showModal(title, formContent, footer);
    
    // Konum dropdown'larını başlat
    if (product?.warehouse_id) {
        setTimeout(() => loadLocationDropdowns(product.warehouse_id, product.cabinet_id, product.shelf_id, product.compartment_id), 100);
    }
}

async function loadLocationDropdowns(warehouseId, cabId = null, shelfId = null, compId = null) {
    const container = document.getElementById('prodLocationContainer');
    if (!warehouseId) { container.innerHTML = ''; return; }
    try {
        const struct = await api.getWarehouseStructure(warehouseId);
        window.currentWarehouseStructure = struct;
        renderLocationDropdowns(cabId, shelfId, compId);
    } catch(e) {}
}

window.renderLocationDropdowns = function(cabId, shelfId, compId) {
    const struct = window.currentWarehouseStructure;
    if (!struct) return;
    
    let cabinets = struct.cabinets || [];
    let selectedCab = cabinets.find(c => c.id == cabId);
    let shelves = selectedCab ? selectedCab.shelves : [];
    let selectedShelf = shelves.find(s => s.id == shelfId);
    let compartments = selectedShelf ? selectedShelf.compartments : [];
    
    const html = `
        <div><label class="block text-xs text-gray-400 mb-1.5">Dolap</label>
            <select name="cabinet_id" onchange="renderLocationDropdowns(this.value, null, null)" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white">
                <option value="">Açıkta / Seçilmedi</option>
                ${cabinets.map(c => `<option value="${c.id}" ${c.id == cabId ? 'selected' : ''}>${c.name}</option>`).join('')}
            </select>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Raf</label>
            <select name="shelf_id" onchange="renderLocationDropdowns(document.querySelector('[name=cabinet_id]').value, this.value, null)" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white">
                <option value="">Seçilmedi</option>
                ${shelves.map(s => `<option value="${s.id}" ${s.id == shelfId ? 'selected' : ''}>${s.name}</option>`).join('')}
            </select>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Bölme</label>
            <select name="compartment_id" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white">
                <option value="">Seçilmedi</option>
                ${compartments.map(c => `<option value="${c.id}" ${c.id == compId ? 'selected' : ''}>${c.name}</option>`).join('')}
            </select>
        </div>
    `;
    const container = document.getElementById('prodLocationContainer');
    if(container) container.innerHTML = html;
}

async function handleImageUpload(input) {
    if (!input.files.length) return;
    try {
        const result = await api.uploadImage(input.files[0]);
        // Gizli hidden input'a URL'i yaz
        const hiddenInput = document.getElementById('imageUrlHidden');
        if (hiddenInput) hiddenInput.value = result.url;
        // Önizleme göster
        const wrap = document.getElementById('imgPreviewWrap');
        const img = document.getElementById('imgPreview');
        if (wrap && img) { img.src = result.url; wrap.classList.remove('hidden'); wrap.style.display = 'flex'; }
        showToast('Görsel yüklendi');
    } catch (err) { showToast(err.message, 'error'); }
}

async function submitProductForm(editId) {
    const form = document.getElementById('productForm');
    const fd = new FormData(form);
    const courseCheckboxes = form.querySelectorAll('[name="course_ids"]:checked');
    const courseIds = Array.from(courseCheckboxes).map(cb => parseInt(cb.value));
    
    const data = {
        name: fd.get('name'),
        description: fd.get('description'),
        image_url: fd.get('image_url') || null,
        category: fd.get('category'),
        status: fd.get('status'),
        current_stock: parseInt(fd.get('current_stock')) || 0,
        critical_stock: parseInt(fd.get('critical_stock')) || 5,
        ideal_stock: parseInt(fd.get('ideal_stock')) || 100,
        warehouse_id: fd.get('warehouse_id') ? parseInt(fd.get('warehouse_id')) : null,
        cabinet_id: fd.get('cabinet_id') ? parseInt(fd.get('cabinet_id')) : null,
        shelf_id: fd.get('shelf_id') ? parseInt(fd.get('shelf_id')) : null,
        compartment_id: fd.get('compartment_id') ? parseInt(fd.get('compartment_id')) : null,
        course_ids: courseIds
    };

    try {
        if (editId) { await api.updateProduct(editId, data); showToast('Ürün güncellendi'); }
        else { await api.createProduct(data); showToast('Ürün eklendi'); }
        closeModal();
        loadProducts();
    } catch (err) { showToast(err.message, 'error'); }
}
