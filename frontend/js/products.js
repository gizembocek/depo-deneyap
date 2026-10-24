// ==================== ÜRÜNLER SAYFASI ====================
const DEFAULT_FILTERS = { search: '', category: '', status: '', warehouse_id: '', course_id: '', low_stock: false, sort: 'newest', page: 1 };
const PER_PAGE = 48;
let productFilters = { ...DEFAULT_FILTERS };

function resetProductFilters() {
    productFilters = { ...DEFAULT_FILTERS };
    const search = document.getElementById('globalSearch');
    if (search) search.value = '';
}

// Başka sayfalardan (ana panel, depolar, dersler) filtreli olarak ürünlere gitmek için
function goToProducts(filters = {}) {
    resetProductFilters();
    Object.assign(productFilters, filters);
    if (currentPage === 'products') renderProductsPage();
    else navigateTo('products');
}

function setProductFilter(key, value) {
    productFilters[key] = value;
    productFilters.page = 1;
    loadProducts();
    updateFilterIndicators();
}

function selectOptions(options, selected, emptyLabel) {
    const opts = options.map(o => {
        const value = typeof o === 'object' ? o.value : o;
        const label = typeof o === 'object' ? o.label : o;
        return `<option value="${esc(value)}" ${String(value) === String(selected) ? 'selected' : ''}>${esc(label)}</option>`;
    }).join('');
    return (emptyLabel !== undefined ? `<option value="">${esc(emptyLabel)}</option>` : '') + opts;
}

async function renderProductsPage() {
    const content = document.getElementById('pageContent');
    const f = productFilters;
    const selectCls = 'bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500';
    content.innerHTML = `
    <div class="animate-fade-in">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <div>
                <h1 class="text-2xl font-bold text-white">Ürün Yönetimi</h1>
                <p id="productsSummary" class="text-sm text-gray-400 mt-1">&nbsp;</p>
            </div>
            <div class="flex gap-2 flex-wrap admin-only">
                <button onclick="confirmDeleteAllProducts()" class="flex items-center gap-2 bg-red-600/80 hover:bg-red-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">delete_sweep</span>Toplu Sil
                </button>
                <button onclick="showExcelImportModal()" class="flex items-center gap-2 bg-green-600 hover:bg-green-700 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">upload_file</span>Excel İle Ekle
                </button>
                <button id="addProductBtn" onclick="showProductForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Ürün Ekle
                </button>
            </div>
        </div>
        <div class="glass rounded-2xl p-4 mb-6">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
                <select id="filterCategory" aria-label="Kategori" onchange="setProductFilter('category', this.value)" class="${selectCls}">
                    ${selectOptions(CATEGORIES.map(c => ({ value: c, label: c })), f.category, 'Tüm Kategoriler')}
                </select>
                <select id="filterStatus" aria-label="Durum" onchange="setProductFilter('status', this.value)" class="${selectCls}">
                    ${selectOptions(STATUSES, f.status, 'Tüm Durumlar')}
                </select>
                <select id="filterWarehouse" aria-label="Depo" onchange="setProductFilter('warehouse_id', this.value)" class="${selectCls}">
                    ${selectOptions(allWarehouses.map(w => ({ value: w.id, label: w.name })), f.warehouse_id, 'Tüm Depolar')}
                </select>
                <select id="filterCourse" aria-label="Ders" onchange="setProductFilter('course_id', this.value)" class="${selectCls}">
                    ${selectOptions(allCourses.map(c => ({ value: c.id, label: c.name })), f.course_id, 'Tüm Dersler')}
                </select>
                <select id="filterSort" aria-label="Sıralama" onchange="setProductFilter('sort', this.value)" class="${selectCls}">
                    ${selectOptions([{ value: 'newest', label: 'En yeni' }, { value: 'name', label: 'Ada göre (A-Z)' },
                                     { value: 'stock_asc', label: 'Stok (azdan çoğa)' }, { value: 'stock_desc', label: 'Stok (çoktan aza)' }], f.sort)}
                </select>
                <div class="flex gap-2">
                    <button id="filterLowStock" type="button" aria-pressed="${f.low_stock}" onclick="setProductFilter('low_stock', !productFilters.low_stock)"
                        class="flex-1 flex items-center justify-center gap-1 border rounded-xl px-3 py-2.5 text-sm transition-all">
                        <span class="material-icons-outlined text-base">warning</span>Kritik
                    </button>
                    <button type="button" onclick="resetProductFilters(); renderProductsPage()" title="Filtreleri temizle" aria-label="Filtreleri temizle"
                        class="flex items-center justify-center bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-gray-400 hover:text-white transition-all">
                        <span class="material-icons-outlined text-base">filter_alt_off</span>
                    </button>
                </div>
            </div>
            <div id="activeSearchChip" class="hidden mt-3"></div>
        </div>
        <div id="productsGrid"></div>
        <div id="productsPagination" class="mt-6"></div>
    </div>`;
    applyRoleVisibility(content);
    const search = document.getElementById('globalSearch');
    if (search && search.value !== f.search) search.value = f.search;
    updateFilterIndicators();
    loadProducts();
}

function updateFilterIndicators() {
    const low = document.getElementById('filterLowStock');
    if (low) {
        low.className = `flex-1 flex items-center justify-center gap-1 border rounded-xl px-3 py-2.5 text-sm transition-all ${productFilters.low_stock
            ? 'bg-red-500/20 border-red-500/60 text-red-300' : 'bg-slate-800 border-slate-700 text-gray-300 hover:border-red-500/50'}`;
        low.setAttribute('aria-pressed', productFilters.low_stock);
    }
    const chip = document.getElementById('activeSearchChip');
    if (chip) {
        if (productFilters.search) {
            chip.classList.remove('hidden');
            chip.innerHTML = `<span class="inline-flex items-center gap-2 text-xs bg-deneyap-blue-500/15 text-deneyap-blue-300 px-3 py-1.5 rounded-lg">
                Arama: "<b>${esc(productFilters.search)}</b>"
                <button type="button" onclick="document.getElementById('globalSearch').value=''; setProductFilter('search', '')" class="material-icons-outlined text-sm" aria-label="Aramayı temizle">close</button></span>`;
        } else {
            chip.classList.add('hidden');
            chip.innerHTML = '';
        }
    }
}

async function loadProducts() {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="flex justify-center py-10"><div class="spinner"></div></div>';
    const params = { ...productFilters, per_page: PER_PAGE };
    const requestedFilters = JSON.stringify(productFilters);
    try {
        const { items, total } = await api.getProductsPage(params);
        if (JSON.stringify(productFilters) !== requestedFilters) return; // bu arada filtre değişti
        allProducts = items;
        const summary = document.getElementById('productsSummary');
        if (summary) summary.textContent = `${fmtNumber(total)} ürün bulundu`;

        const lastPage = Math.max(1, Math.ceil(total / PER_PAGE));
        if (productFilters.page > lastPage && total > 0) { productFilters.page = lastPage; return loadProducts(); }

        if (items.length === 0) {
            grid.innerHTML = `<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">inventory_2</span>
                <p class="text-gray-400 text-lg">Ürün bulunamadı</p><p class="text-gray-500 text-sm mt-1">Farklı filtreler deneyin veya yeni ürün ekleyin</p></div>`;
        } else {
            grid.innerHTML = `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">${items.map(renderProductCard).join('')}</div>`;
        }
        renderPagination(total, lastPage);
    } catch (err) {
        grid.innerHTML = `<div class="text-center py-10 text-red-400">${esc(err.message)}</div>`;
    }
}

function renderPagination(total, lastPage) {
    const el = document.getElementById('productsPagination');
    if (!el) return;
    if (lastPage <= 1) { el.innerHTML = ''; return; }
    const page = productFilters.page;
    const pages = new Set([1, lastPage, page - 1, page, page + 1, page - 2, page + 2].filter(p => p >= 1 && p <= lastPage));
    const sorted = [...pages].sort((a, b) => a - b);
    let html = '';
    let prev = 0;
    for (const p of sorted) {
        if (p - prev > 1) html += '<span class="px-2 text-gray-500">…</span>';
        html += `<button type="button" onclick="goToPage(${p})" ${p === page ? 'aria-current="page"' : ''}
            class="min-w-[40px] h-10 px-3 rounded-xl text-sm font-medium transition-all ${p === page ? 'bg-deneyap-blue-500 text-white' : 'bg-slate-800 text-gray-300 hover:bg-slate-700'}">${p}</button>`;
        prev = p;
    }
    const from = (page - 1) * PER_PAGE + 1;
    const to = Math.min(page * PER_PAGE, total);
    el.innerHTML = `
        <div class="flex flex-col sm:flex-row items-center justify-between gap-3">
            <p class="text-sm text-gray-400">${fmtNumber(from)}–${fmtNumber(to)} / ${fmtNumber(total)} ürün</p>
            <div class="flex items-center gap-1 flex-wrap justify-center">
                <button type="button" onclick="goToPage(${page - 1})" ${page <= 1 ? 'disabled' : ''} aria-label="Önceki sayfa" class="h-10 px-3 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700"><span class="material-icons-outlined text-base align-middle">chevron_left</span></button>
                ${html}
                <button type="button" onclick="goToPage(${page + 1})" ${page >= lastPage ? 'disabled' : ''} aria-label="Sonraki sayfa" class="h-10 px-3 rounded-xl bg-slate-800 text-gray-300 hover:bg-slate-700"><span class="material-icons-outlined text-base align-middle">chevron_right</span></button>
            </div>
        </div>`;
}

function goToPage(page) {
    productFilters.page = page;
    loadProducts();
    document.getElementById('pageContent')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function stockBar(p) {
    const isCritical = p.current_stock <= p.critical_stock;
    const pct = p.ideal_stock > 0 ? Math.min(100, Math.round((p.current_stock / p.ideal_stock) * 100)) : 100;
    const color = isCritical ? 'bg-red-500' : pct > 60 ? 'bg-green-500' : 'bg-yellow-500';
    return { isCritical, pct, color };
}

function renderProductCard(p) {
    const { isCritical, pct, color } = stockBar(p);
    const location = [p.warehouse_name || 'Depo atanmamış', p.cabinet_name, p.shelf_name, p.compartment_name].filter(Boolean).join(' › ');
    return `
    <div class="product-card glass rounded-2xl overflow-hidden cursor-pointer" role="button" tabindex="0" onclick="showProductDetail(${p.id})" onkeydown="if(event.key==='Enter') showProductDetail(${p.id})">
        <div class="relative h-40 bg-slate-800 overflow-hidden flex items-center justify-center">
            <span class="material-icons-outlined text-gray-600 text-5xl">image</span>
            ${p.image_url ? `<img src="${esc(p.image_url)}" alt="" loading="lazy" class="absolute inset-0 w-full h-full object-contain p-2 bg-slate-800" onerror="this.remove()">` : ''}
            ${isCritical ? '<div class="absolute top-2 right-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full stock-critical flex items-center gap-1"><span class="material-icons-outlined text-xs">warning</span>Kritik</div>' : ''}
            <div class="absolute top-2 left-2 ${getStatusClass(p.status)} text-[10px] font-medium px-2 py-0.5 rounded-full">${esc(p.status)}</div>
        </div>
        <div class="p-4">
            <h3 class="text-sm font-semibold text-white truncate mb-1" title="${esc(p.name)}">${esc(p.name)}</h3>
            <p class="text-xs text-gray-500 truncate mb-3" title="${esc(p.description || '')}">${esc(p.description || '')}&nbsp;</p>
            <div class="flex items-center justify-between mb-2">
                <span class="text-xs text-gray-400 flex items-center gap-1"><span class="material-icons-outlined text-xs">${getCategoryIcon(p.category)}</span>${esc(p.category.split(' ')[0])}</span>
                <span class="text-lg font-bold ${isCritical ? 'text-red-400' : 'text-white'}">${fmtNumber(p.current_stock)}</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-1.5"><div class="${color} h-1.5 rounded-full" style="width: ${pct}%"></div></div>
            <div class="flex items-center justify-between mt-2 gap-2">
                <span class="text-[10px] text-gray-500 truncate" title="${esc(location)}">${esc(location)}</span>
                <div class="flex gap-1 flex-shrink-0" onclick="event.stopPropagation()" onkeydown="event.stopPropagation()">
                    <button type="button" onclick="quickStock(${p.id}, 'remove')" title="1 adet çıkar" aria-label="1 adet çıkar" class="w-7 h-7 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center justify-center transition-all text-sm font-bold">−</button>
                    <button type="button" onclick="quickStock(${p.id}, 'add')" title="1 adet ekle" aria-label="1 adet ekle" class="w-7 h-7 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 flex items-center justify-center transition-all text-sm font-bold">+</button>
                </div>
            </div>
        </div>
    </div>`;
}

async function quickStock(productId, action) {
    try {
        const result = await api.updateStock(productId, { action, quantity: 1 });
        showToast(`Stok güncellendi: ${result.current_stock}`, result.is_critical ? 'warning' : 'success');
        loadProducts();
        refreshStatsBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

async function refreshStatsBadge() {
    try { updateLowStockBadge(await api.getProductStats()); } catch (e) { /* yoksay */ }
}

// ==================== EXCEL İÇE AKTARMA ====================
function showExcelImportModal() {
    const content = `
    <div class="space-y-4">
        <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <p class="text-sm text-gray-300 mb-2 font-medium">Nasıl yüklenir?</p>
            <ul class="text-xs text-gray-400 space-y-1 list-disc pl-4">
                <li>Zorunlu tek sütun <b>"Malzeme Adı"</b> (veya "Ürün Adı") sütunudur; ilk 20 satırdan birinde başlık olarak bulunmalıdır.</li>
                <li>İsteğe bağlı sütunlar: <b>Miktar</b> (veya "6 Adet" yazılı <b>Birim</b>), <b>Kategori</b>, <b>Durum</b>, <b>Kritik Stok</b>, <b>İdeal Stok</b>, <b>Ders</b>, <b>Açıklama</b>.</li>
                <li>Dosyadaki tüm sayfalar taranır. Sayfa adı bir ders adıysa ürünler o derse bağlanır.</li>
                <li>Seçilen depoda aynı isimde ürün varsa tekrar eklenmez (atlanır).</li>
            </ul>
            <button type="button" onclick="downloadTemplate(this)" class="mt-3 text-xs text-green-400 hover:text-green-300 flex items-center gap-1">
                <span class="material-icons-outlined text-sm">download</span>Örnek Excel şablonunu indir
            </button>
        </div>
        <form id="excelImportForm" class="space-y-4">
            <div>
                <label class="block text-xs text-gray-400 mb-1.5" for="excelWarehouse"><span class="material-icons-outlined text-[14px] align-middle mr-1">warehouse</span>Hangi depoya eklenecek?</label>
                <select id="excelWarehouse" name="warehouse_id" class="${inputClass()}">
                    ${selectOptions(allWarehouses.map(w => ({ value: w.id, label: w.name })), '', 'Depo seçilmedi (genel ürün)')}
                </select>
            </div>
            <div>
                <label class="block text-xs text-gray-400 mb-1.5" for="excelFile"><span class="material-icons-outlined text-[14px] align-middle mr-1">description</span>Excel dosyası (.xlsx)</label>
                <input type="file" id="excelFile" accept=".xlsx,.xlsm" required class="w-full text-sm text-gray-400 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2">
            </div>
        </form>
    </div>`;
    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">İptal</button>
        <button type="submit" form="excelImportForm" id="excelImportBtn" class="bg-green-600 hover:bg-green-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">upload</span>Yükle ve Aktar</button>`;
    showModal("Excel'den Toplu Ürün Ekle", content, footer);
    document.getElementById('excelImportForm').onsubmit = (e) => { e.preventDefault(); submitExcelImport(); };
}

async function downloadTemplate(btn) {
    try { await api.downloadImportTemplate(); showToast('Şablon indirildi'); }
    catch (err) { showToast(err.message, 'error'); }
}

async function submitExcelImport() {
    const fileInput = document.getElementById('excelFile');
    if (!fileInput.files.length) return showToast('Lütfen bir Excel dosyası seçin', 'warning');
    const warehouseId = document.getElementById('excelWarehouse').value;
    const btn = document.getElementById('excelImportBtn');
    setButtonLoading(btn, true, 'Yükleniyor...');
    try {
        const r = await api.importExcelProducts(fileInput.files[0], warehouseId || null);
        await loadInitialData();
        const content = `
            <div class="space-y-4 text-sm">
                <div class="grid grid-cols-2 gap-3">
                    <div class="bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center"><p class="text-3xl font-bold text-green-400">${fmtNumber(r.added)}</p><p class="text-gray-400 text-xs mt-1">yeni ürün eklendi</p></div>
                    <div class="bg-slate-800 border border-slate-700 rounded-xl p-4 text-center"><p class="text-3xl font-bold text-gray-300">${fmtNumber(r.skipped)}</p><p class="text-gray-400 text-xs mt-1">zaten vardı (atlandı)</p></div>
                </div>
                ${r.sheets?.length ? `<div><p class="text-gray-400 text-xs mb-1">Aktarılan sayfalar</p><ul class="list-disc pl-5 text-gray-300">${r.sheets.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>` : ''}
                ${r.skipped_sheets?.length ? `<div><p class="text-gray-400 text-xs mb-1">Ürün bulunamayan sayfalar (atlandı)</p><p class="text-gray-500">${r.skipped_sheets.map(esc).join(', ')}</p></div>` : ''}
            </div>`;
        showModal('İçe Aktarma Tamamlandı', content, `<button type="button" onclick="closeModal()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Tamam</button>`, { size: 'sm' });
        resetProductFilters();
        if (currentPage === 'products') renderProductsPage(); else navigateTo('products');
        refreshStatsBadge();
    } catch (err) {
        showToast(err.message, 'error');
        setButtonLoading(btn, false);
    }
}

// ==================== TOPLU SİLME ====================
async function confirmDeleteAllProducts() {
    const content = `
    <form id="deleteAllForm" class="space-y-4">
        <div class="bg-red-500/10 border border-red-500/30 p-4 rounded-xl flex items-start gap-3">
            <span class="material-icons-outlined text-red-400 text-3xl">warning</span>
            <div><p class="text-red-400 font-bold">Bu işlem geri alınamaz!</p>
            <p class="text-gray-400 text-sm mt-1">Seçilen ürünler, stok geçmişleri, ders bağlantıları ve giriş/çıkış satırları kalıcı olarak silinir. Önce Ayarlar sayfasından yedek almanız önerilir.</p></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="deleteScope">Silinecek ürünler</label>
            <select id="deleteScope" class="${inputClass()}">
                <option value="">TÜM ürünler (bütün depolar)</option>
                <option value="unassigned">Sadece depo atanmamış ürünler</option>
                ${allWarehouses.map(w => `<option value="${w.id}">Sadece "${esc(w.name)}" deposundakiler (${fmtNumber(w.product_count)} ürün)</option>`).join('')}
            </select></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="deleteConfirmInput">Onaylamak için <b class="text-red-400">SİL</b> yazın:</label>
            <input type="text" id="deleteConfirmInput" autocomplete="off" placeholder="SİL" class="${inputClass('focus:border-red-500')}"></div>
    </form>`;
    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">İptal</button>
        <button type="submit" form="deleteAllForm" id="deleteAllBtn" class="bg-red-600 hover:bg-red-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">delete_forever</span>Sil</button>`;
    showModal('Toplu Ürün Silme', content, footer);
    document.getElementById('deleteAllForm').onsubmit = async (e) => {
        e.preventDefault();
        const typed = document.getElementById('deleteConfirmInput').value.trim().toLocaleUpperCase('tr-TR');
        if (typed !== 'SİL') return showToast('Lütfen onaylamak için "SİL" yazın', 'warning');
        const btn = document.getElementById('deleteAllBtn');
        setButtonLoading(btn, true, 'Siliniyor...');
        try {
            const result = await api.deleteAllProducts(document.getElementById('deleteScope').value || null);
            showToast(result.message, 'success');
            closeModal();
            await loadInitialData();
            loadProducts();
            refreshStatsBadge();
        } catch (err) {
            showToast(err.message, 'error');
            setButtonLoading(btn, false);
        }
    };
}
