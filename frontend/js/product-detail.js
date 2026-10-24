// ==================== ÜRÜN DETAYI VE FORMU ====================
async function showProductDetail(id) {
    try {
        const [p, logs] = await Promise.all([api.getProduct(id), api.getProductLogs(id).catch(() => [])]);
        const { isCritical, pct, color } = stockBar(p);

        const content = `
        <div class="space-y-5">
            <div class="flex flex-col sm:flex-row gap-5">
                <div class="relative w-full sm:w-48 h-48 bg-slate-800 rounded-xl overflow-hidden flex-shrink-0 flex items-center justify-center">
                    <span class="material-icons-outlined text-gray-600 text-6xl">image</span>
                    ${p.image_url ? (p.image_url.startsWith('data:')
                        ? `<img src="${esc(p.image_url)}" alt="${esc(p.name)}" class="absolute inset-0 w-full h-full object-contain p-2 bg-slate-800" onerror="this.remove()">`
                        : `<a href="${esc(p.image_url)}" target="_blank" rel="noopener" class="absolute inset-0" title="Büyük görmek için tıklayın"><img src="${esc(p.image_url)}" alt="${esc(p.name)}" class="w-full h-full object-contain p-2 bg-slate-800" onerror="this.parentElement.remove()"></a>`) : ''}
                </div>
                <div class="flex-1 space-y-3 min-w-0">
                    <div class="flex items-start justify-between gap-2">
                        <h2 class="text-xl font-bold text-white break-words">${esc(p.name)}</h2>
                        <span class="${getStatusClass(p.status)} text-xs px-3 py-1 rounded-full font-medium whitespace-nowrap">${esc(p.status)}</span>
                    </div>
                    <p class="text-sm text-gray-400 whitespace-pre-line">${esc(p.description || 'Açıklama yok')}</p>
                    <div class="flex flex-wrap gap-2">
                        <span class="text-xs bg-slate-800 text-gray-300 px-3 py-1 rounded-lg flex items-center gap-1"><span class="material-icons-outlined text-xs">${getCategoryIcon(p.category)}</span>${esc(p.category)}</span>
                        ${(p.courses || []).map(c => `<span class="text-xs bg-deneyap-blue-500/10 text-deneyap-blue-400 px-3 py-1 rounded-lg">${esc(c.name)}</span>`).join('')}
                    </div>
                </div>
            </div>

            <div class="glass-light rounded-xl p-4">
                <div class="flex items-center justify-between mb-3">
                    <h3 class="text-sm font-semibold text-gray-300">Stok Durumu</h3>
                    ${isCritical ? '<span class="text-xs text-red-400 flex items-center gap-1 stock-critical"><span class="material-icons-outlined text-sm">warning</span>Kritik Stok!</span>' : ''}
                </div>
                <div class="grid grid-cols-3 gap-4 mb-4">
                    <div class="text-center"><p class="text-2xl font-bold ${isCritical ? 'text-red-400' : 'text-white'}">${fmtNumber(p.current_stock)}</p><p class="text-xs text-gray-500">Mevcut</p></div>
                    <div class="text-center"><p class="text-2xl font-bold text-yellow-400">${fmtNumber(p.critical_stock)}</p><p class="text-xs text-gray-500">Kritik</p></div>
                    <div class="text-center"><p class="text-2xl font-bold text-green-400">${fmtNumber(p.ideal_stock)}</p><p class="text-xs text-gray-500">İdeal</p></div>
                </div>
                <div class="w-full bg-slate-700 rounded-full h-2 mb-4"><div class="${color} h-2 rounded-full" style="width: ${pct}%"></div></div>
                <div class="flex items-center gap-2">
                    <button type="button" onclick="modifyStock(${p.id}, 'remove')" class="flex-1 bg-red-500/10 hover:bg-red-500/20 text-red-400 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">remove</span>Çıkar</button>
                    <button type="button" onclick="modifyStock(${p.id}, 'add')" class="flex-1 bg-green-500/10 hover:bg-green-500/20 text-green-400 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">add</span>Ekle</button>
                    <button type="button" onclick="modifyStock(${p.id}, 'set')" class="flex-1 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 py-2.5 rounded-xl font-medium text-sm flex items-center justify-center gap-1"><span class="material-icons-outlined text-lg">edit</span>Sayım</button>
                </div>
            </div>

            <div class="glass-light rounded-xl p-4">
                <h3 class="text-sm font-semibold text-gray-300 mb-2">Konum</h3>
                <div class="flex flex-wrap gap-2 text-xs">
                    <span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg flex items-center gap-1"><span class="material-icons-outlined text-sm">warehouse</span>${esc(p.warehouse_name || 'Depo atanmamış')}</span>
                    ${p.cabinet_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Dolap: ${esc(p.cabinet_name)}</span>` : ''}
                    ${p.shelf_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Raf: ${esc(p.shelf_name)}</span>` : ''}
                    ${p.compartment_name ? `<span class="bg-slate-800 text-gray-300 px-3 py-1.5 rounded-lg">Bölme: ${esc(p.compartment_name)}</span>` : ''}
                </div>
            </div>

            ${logs.length > 0 ? `
            <div class="glass-light rounded-xl p-4">
                <h3 class="text-sm font-semibold text-gray-300 mb-3">Son İşlemler</h3>
                <div class="space-y-1 max-h-52 overflow-y-auto pr-1">${logs.slice(0, 20).map(l => `
                    <div class="flex items-center justify-between gap-3 text-xs py-1.5 border-b border-slate-700/30">
                        <div class="min-w-0">
                            <span class="${ACTION_COLORS[l.action] || 'text-gray-400'} font-medium">${esc(ACTION_LABELS[l.action] || l.action)}</span>
                            <span class="text-gray-500"> • ${esc(l.user_name || 'Sistem')}</span>
                            ${l.note ? `<p class="text-gray-500 truncate" title="${esc(l.note)}">${esc(l.note)}</p>` : ''}
                        </div>
                        <div class="text-right flex-shrink-0"><span class="text-gray-300">${esc(l.previous_value ?? '')} → ${esc(l.new_value ?? '')}</span>
                            <p class="text-gray-600">${fmtDateTime(l.created_at)}</p></div>
                    </div>`).join('')}
                </div>
            </div>` : ''}
        </div>`;

        const footer = `
            ${api.isAdmin() ? `<button type="button" onclick="closeModal(); showProductForm(${p.id})" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">edit</span>Düzenle</button>
            <button type="button" onclick="deleteProduct(${p.id})" class="bg-red-500/10 hover:bg-red-500/20 text-red-400 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">delete</span>Sil</button>` : ''}
            <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kapat</button>`;
        showModal(p.name, content, footer);
    } catch (err) { showToast(err.message, 'error'); }
}

function modifyStock(productId, action) {
    const labels = { add: 'Eklenecek miktar', remove: 'Çıkarılacak miktar', set: 'Sayım sonucu (yeni stok miktarı)' };
    const titles = { add: 'Stok Ekle', remove: 'Stok Çıkar', set: 'Stok Sayımı' };
    const noteField = `<div><label class="block text-xs text-gray-400 mb-1.5" for="stockNote">Not (isteğe bağlı)</label>
        <input type="text" id="stockNote" data-extra="note" maxlength="500" placeholder="${action === 'remove' ? 'Örn: Robotik dersinde kullanıldı' : 'Örn: Bağış, yıl sonu sayımı'}" class="${inputClass()}"></div>`;
    showPromptModal(titles[action], labels[action], action === 'set' ? '' : '1', 'number', async (qty, extra) => {
        const num = Number(qty);
        if (qty === '' || !Number.isInteger(num) || num < 0 || (action !== 'set' && num === 0)) {
            showToast('Geçerli bir miktar girin', 'error');
            return modifyStock(productId, action);
        }
        try {
            const result = await api.updateStock(productId, { action, quantity: num, note: extra.note || null });
            showToast(`Stok güncellendi: ${result.current_stock}`, result.is_critical ? 'warning' : 'success');
            showProductDetail(productId);
            if (currentPage === 'products') loadProducts();
            refreshStatsBadge();
        } catch (err) {
            showToast(err.message, 'error');
            showProductDetail(productId);
        }
    }, () => showProductDetail(productId), noteField);
}

async function deleteProduct(id) {
    const ok = await confirmModal('Ürünü Sil', 'Bu ürün ve tüm stok geçmişi kalıcı olarak silinecek. Emin misiniz?',
        { confirmText: 'Sil', danger: true, onCancel: () => showProductDetail(id) });
    if (!ok) return;
    try {
        await api.deleteProduct(id);
        showToast('Ürün silindi');
        if (currentPage === 'products') loadProducts();
        else if (currentPage === 'dashboard') renderDashboard();
        refreshStatsBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

async function showProductForm(editId = null) {
    let product = null;
    if (editId) {
        try { product = await api.getProduct(editId); }
        catch (e) { return showToast(e.message, 'error'); }
    }
    const isEdit = !!product;
    const num = (v, d) => (v === null || v === undefined ? d : v);

    const content = `
    <form id="productForm" class="space-y-4" novalidate>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfName">Ürün adı *</label>
                <input type="text" id="pfName" name="name" value="${esc(product?.name || '')}" required maxlength="255" autofocus class="${inputClass()}"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfCategory">Kategori</label>
                <select id="pfCategory" name="category" class="${inputClass()}">${selectOptions(CATEGORIES, product?.category || 'Genel / Dayanıklı Malzeme')}</select></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="pfDesc">Açıklama</label>
            <textarea id="pfDesc" name="description" rows="2" maxlength="4000" class="${inputClass()}">${esc(product?.description || '')}</textarea></div>
        <div>
            <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">photo_camera</span>Ürün fotoğrafı</label>
            <div id="imgPreviewWrap" class="${product?.image_url ? 'flex' : 'hidden'} relative mb-2 w-full h-32 bg-slate-800 rounded-xl overflow-hidden items-center justify-center border border-slate-700">
                <img id="imgPreview" src="${esc(product?.image_url || '')}" alt="" class="h-full w-full object-contain p-1">
                <button type="button" onclick="clearProductImage()" class="absolute top-2 right-2 bg-slate-900/80 hover:bg-red-600 text-white rounded-lg p-1" title="Fotoğrafı kaldır" aria-label="Fotoğrafı kaldır"><span class="material-icons-outlined text-base">delete</span></button>
            </div>
            <input type="file" id="imageUpload" accept="image/png,image/jpeg,image/gif,image/webp" onchange="handleImageUpload(this)" class="w-full text-xs text-gray-400 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2">
            <input type="hidden" name="image_url" id="imageUrlHidden" value="${esc(product?.image_url || '')}">
        </div>
        <div class="grid grid-cols-3 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfStock">Mevcut stok</label><input id="pfStock" type="number" name="current_stock" value="${num(product?.current_stock, 0)}" min="0" step="1" class="${inputClass()}"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfCritical">Kritik stok</label><input id="pfCritical" type="number" name="critical_stock" value="${num(product?.critical_stock, 5)}" min="0" step="1" class="${inputClass()}"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfIdeal">İdeal stok</label><input id="pfIdeal" type="number" name="ideal_stock" value="${num(product?.ideal_stock, 10)}" min="0" step="1" class="${inputClass()}"></div>
        </div>
        <p class="text-[11px] text-gray-500 -mt-2">Mevcut stok, kritik stok değerine eşit veya altına düştüğünde ürün "Kritik" olarak işaretlenir.</p>
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfStatus">Durum</label>
                <select id="pfStatus" name="status" class="${inputClass()}">${selectOptions(STATUSES, product?.status || 'Çalışan')}</select></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="pfWarehouse">Depo</label>
                <select id="pfWarehouse" name="warehouse_id" onchange="loadLocationDropdowns(this.value)" class="${inputClass()}">
                    ${selectOptions(allWarehouses.map(w => ({ value: w.id, label: w.name })), product?.warehouse_id ?? '', 'Depo seçilmedi')}
                </select></div>
        </div>
        <div id="prodLocationContainer" class="grid grid-cols-1 sm:grid-cols-3 gap-4"></div>
        <div><p class="block text-xs text-gray-400 mb-1.5">Dersler</p>
            ${allCourses.length ? `<div class="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-40 overflow-y-auto bg-slate-800 rounded-xl p-3">
                ${allCourses.map(c => `<label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer"><input type="checkbox" name="course_ids" value="${c.id}" ${product?.courses?.some(pc => pc.id === c.id) ? 'checked' : ''} class="rounded border-slate-600">${esc(c.name)}</label>`).join('')}
            </div>` : '<p class="text-xs text-gray-500">Henüz ders eklenmemiş. Dersler sayfasından ekleyebilirsiniz.</p>'}
        </div>
    </form>`;

    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">İptal</button>
        <button type="submit" form="productForm" id="productSubmitBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">save</span>${isEdit ? 'Güncelle' : 'Ekle'}</button>`;

    showModal(isEdit ? 'Ürün Düzenle' : 'Yeni Ürün Ekle', content, footer);
    document.getElementById('productForm').onsubmit = (e) => { e.preventDefault(); submitProductForm(editId); };
    if (product?.warehouse_id) loadLocationDropdowns(product.warehouse_id, product.cabinet_id, product.shelf_id, product.compartment_id);
}

let currentWarehouseStructure = null;

async function loadLocationDropdowns(warehouseId, cabId = null, shelfId = null, compId = null) {
    const container = document.getElementById('prodLocationContainer');
    if (!container) return;
    if (!warehouseId) { container.innerHTML = ''; currentWarehouseStructure = null; return; }
    try {
        currentWarehouseStructure = await api.getWarehouseStructure(warehouseId);
        renderLocationDropdowns(cabId, shelfId, compId);
    } catch (e) { container.innerHTML = ''; }
}

function renderLocationDropdowns(cabId, shelfId, compId) {
    const struct = currentWarehouseStructure;
    const container = document.getElementById('prodLocationContainer');
    if (!struct || !container) return;
    const cabinets = struct.cabinets || [];
    const selectedCab = cabinets.find(c => String(c.id) === String(cabId));
    const shelves = selectedCab ? selectedCab.shelves : [];
    const selectedShelf = shelves.find(s => String(s.id) === String(shelfId));
    const compartments = selectedShelf ? selectedShelf.compartments : [];
    if (cabinets.length === 0) {
        container.innerHTML = '<p class="text-xs text-gray-500 sm:col-span-3">Bu depoda henüz dolap tanımlanmamış (Depolar > Dolap/Raf Yapısı).</p>';
        return;
    }
    container.innerHTML = `
        <div><label class="block text-xs text-gray-400 mb-1.5" for="pfCabinet">Dolap</label>
            <select id="pfCabinet" name="cabinet_id" onchange="renderLocationDropdowns(this.value, null, null)" class="${inputClass()}">
                ${selectOptions(cabinets.map(c => ({ value: c.id, label: c.name })), cabId ?? '', 'Seçilmedi')}
            </select></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="pfShelf">Raf</label>
            <select id="pfShelf" name="shelf_id" ${selectedCab ? '' : 'disabled'} onchange="renderLocationDropdowns(document.getElementById('pfCabinet').value, this.value, null)" class="${inputClass()}">
                ${selectOptions(shelves.map(s => ({ value: s.id, label: s.name })), shelfId ?? '', 'Seçilmedi')}
            </select></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="pfComp">Bölme</label>
            <select id="pfComp" name="compartment_id" ${selectedShelf ? '' : 'disabled'} class="${inputClass()}">
                ${selectOptions(compartments.map(c => ({ value: c.id, label: c.name })), compId ?? '', 'Seçilmedi')}
            </select></div>`;
}

function clearProductImage() {
    document.getElementById('imageUrlHidden').value = '';
    document.getElementById('imageUpload').value = '';
    const wrap = document.getElementById('imgPreviewWrap');
    wrap.classList.add('hidden');
    wrap.classList.remove('flex');
}

async function handleImageUpload(input) {
    if (!input.files.length) return;
    const file = input.files[0];
    if (file.size > 5 * 1024 * 1024) { input.value = ''; return showToast("Dosya 5 MB'dan büyük olamaz", 'error'); }
    const btn = document.getElementById('productSubmitBtn');
    setButtonLoading(btn, true, 'Görsel yükleniyor...');
    try {
        const result = await api.uploadImage(file);
        document.getElementById('imageUrlHidden').value = result.url;
        const wrap = document.getElementById('imgPreviewWrap');
        document.getElementById('imgPreview').src = result.url;
        wrap.classList.remove('hidden');
        wrap.classList.add('flex');
        showToast('Görsel yüklendi');
    } catch (err) {
        input.value = '';
        showToast(err.message, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function submitProductForm(editId) {
    const form = document.getElementById('productForm');
    const fd = new FormData(form);
    const name = (fd.get('name') || '').trim();
    if (!name) { showToast('Ürün adı boş olamaz', 'warning'); document.getElementById('pfName').focus(); return; }
    const intOr = (key, fallback) => {
        const v = fd.get(key);
        if (v === null || v === '') return fallback;
        const n = Number(v);
        return Number.isInteger(n) && n >= 0 ? n : NaN;
    };
    const data = {
        name,
        description: (fd.get('description') || '').trim() || null,
        image_url: fd.get('image_url') || null,
        category: fd.get('category'),
        status: fd.get('status'),
        current_stock: intOr('current_stock', 0),
        critical_stock: intOr('critical_stock', 0),
        ideal_stock: intOr('ideal_stock', 0),
        warehouse_id: fd.get('warehouse_id') ? Number(fd.get('warehouse_id')) : null,
        cabinet_id: fd.get('cabinet_id') ? Number(fd.get('cabinet_id')) : null,
        shelf_id: fd.get('shelf_id') ? Number(fd.get('shelf_id')) : null,
        compartment_id: fd.get('compartment_id') ? Number(fd.get('compartment_id')) : null,
        course_ids: [...form.querySelectorAll('[name="course_ids"]:checked')].map(cb => Number(cb.value)),
    };
    if ([data.current_stock, data.critical_stock, data.ideal_stock].some(Number.isNaN)) {
        return showToast('Stok değerleri 0 veya daha büyük tam sayı olmalıdır', 'warning');
    }
    const btn = document.getElementById('productSubmitBtn');
    setButtonLoading(btn, true);
    try {
        if (editId) { await api.updateProduct(editId, data); showToast('Ürün güncellendi'); }
        else { await api.createProduct(data); showToast('Ürün eklendi'); }
        closeModal();
        if (currentPage === 'products') loadProducts();
        else if (currentPage === 'dashboard') renderDashboard();
        refreshStatsBadge();
    } catch (err) {
        showToast(err.message, 'error');
        setButtonLoading(btn, false);
    }
}
