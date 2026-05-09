// ==================== PRODUCTS PAGE ====================
let productFilters = { search: '', category: '', status: '', warehouse_id: '', low_stock: false, page: 1 };

async function renderProductsPage() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
    <div class="animate-fade-in">
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
            <h1 class="text-2xl font-bold text-white">Ürün Yönetimi</h1>
            <div class="flex gap-2">
                <button onclick="showExcelImportModal()" class="admin-only flex items-center gap-2 bg-green-500 hover:bg-green-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">upload_file</span>Excel İle Ekle
                </button>
                <button id="addProductBtn" onclick="showProductForm()" class="admin-only flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Ürün Ekle
                </button>
            </div>
        </div>
        <!-- Filters -->
        <div class="glass rounded-2xl p-4 mb-6">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                <select id="filterCategory" onchange="productFilters.category=this.value; productFilters.page=1; loadProducts()" class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="">Tüm Kategoriler</option>
                    <option value="Sarf Malzemesi">Sarf Malzemesi</option>
                    <option value="Genel / Dayanıklı Malzeme">Genel / Dayanıklı</option>
                    <option value="Elektronik Bileşen">Elektronik Bileşen</option>
                </select>
                <select id="filterStatus" onchange="productFilters.status=this.value; productFilters.page=1; loadProducts()" class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="">Tüm Durumlar</option>
                    <option value="Çalışan">Çalışan</option>
                    <option value="Bozuk / Kırık">Bozuk / Kırık</option>
                    <option value="Garantide">Garantide</option>
                    <option value="Demirbaştan düşülecek">Demirbaştan düşülecek</option>
                    <option value="Kırık ürün kutusunda">Kırık ürün kutusunda</option>
                </select>
                <select id="filterWarehouse" onchange="productFilters.warehouse_id=this.value; productFilters.page=1; loadProducts()" class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="">Tüm Depolar</option>
                    ${allWarehouses.map(w => `<option value="${w.id}">${w.name}</option>`).join('')}
                </select>
                <button data-filter="low" onclick="productFilters.low_stock=!productFilters.low_stock; this.classList.toggle('bg-red-500/20'); this.classList.toggle('border-red-500/50'); productFilters.page=1; loadProducts()" class="flex items-center justify-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-gray-300 hover:border-red-500/50 transition-all">
                    <span class="material-icons-outlined text-base">warning</span>Kritik Stok
                </button>
                <button onclick="resetFilters()" class="flex items-center justify-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-gray-400 hover:text-white transition-all">
                    <span class="material-icons-outlined text-base">refresh</span>Temizle
                </button>
            </div>
        </div>
        <div id="productsGrid"></div>
        <div id="productsPagination" class="mt-6 flex justify-center"></div>
    </div>`;
    document.querySelectorAll('.admin-only').forEach(el => { el.style.display = api.isAdmin() ? '' : 'none'; });
    loadProducts();
}

function resetFilters() {
    productFilters = { search: '', category: '', status: '', warehouse_id: '', low_stock: false, page: 1 };
    document.getElementById('filterCategory').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterWarehouse').value = '';
    document.getElementById('globalSearch').value = '';
    loadProducts();
}

async function loadProducts(extraParams = {}) {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;
    grid.innerHTML = '<div class="flex justify-center py-10"><div class="spinner"></div></div>';
    const params = { ...productFilters, ...extraParams, per_page: 50 };
    if (extraParams.search !== undefined) productFilters.search = extraParams.search;
    try {
        const products = await api.getProducts(params);
        allProducts = products;
        if (products.length === 0) {
            grid.innerHTML = '<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">inventory_2</span><p class="text-gray-400 text-lg">Ürün bulunamadı</p><p class="text-gray-500 text-sm mt-1">Farklı filtreler deneyin veya yeni ürün ekleyin</p></div>';
            return;
        }
        grid.innerHTML = `<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">${products.map(p => renderProductCard(p)).join('')}</div>`;
    } catch (err) { grid.innerHTML = `<div class="text-center py-10 text-red-400">${err.message}</div>`; }
}

function renderProductCard(p) {
    const isCritical = p.current_stock <= p.critical_stock;
    const stockPct = p.ideal_stock > 0 ? Math.min(100, Math.round((p.current_stock / p.ideal_stock) * 100)) : 100;
    const stockColor = isCritical ? 'red' : stockPct > 60 ? 'green' : 'yellow';
    return `
    <div class="product-card glass rounded-2xl overflow-hidden cursor-pointer" onclick="showProductDetail(${p.id})">
        <div class="relative h-40 bg-slate-800 overflow-hidden">
            ${p.image_url ? `<img src="${p.image_url}" class="w-full h-full object-contain p-2" onerror="this.style.display='none'; this.nextElementSibling.style.display='flex'"><div class="hidden w-full h-full items-center justify-center"><span class="material-icons-outlined text-gray-600 text-5xl">image</span></div>` : '<div class="w-full h-full flex items-center justify-center"><span class="material-icons-outlined text-gray-600 text-5xl">image</span></div>'}
            ${isCritical ? '<div class="absolute top-2 right-2 bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full stock-critical flex items-center gap-1"><span class="material-icons-outlined text-xs">warning</span>Kritik</div>' : ''}
            <div class="absolute top-2 left-2 ${getStatusClass(p.status)} text-[10px] font-medium px-2 py-0.5 rounded-full">${p.status}</div>
        </div>
        <div class="p-4">
            <h3 class="text-sm font-semibold text-white truncate mb-1" title="${p.name}">${p.name}</h3>
            <p class="text-xs text-gray-500 truncate mb-3">${p.description || ''}</p>
            <div class="flex items-center justify-between mb-2">
                <span class="text-xs text-gray-400 flex items-center gap-1"><span class="material-icons-outlined text-xs">${getCategoryIcon(p.category)}</span>${p.category.split(' ')[0]}</span>
                <span class="text-lg font-bold ${isCritical ? 'text-red-400' : 'text-white'}">${p.current_stock}</span>
            </div>
            <div class="w-full bg-slate-700 rounded-full h-1.5"><div class="bg-${stockColor}-500 h-1.5 rounded-full transition-all" style="width: ${stockPct}%"></div></div>
            <div class="flex items-center justify-between mt-2">
                <span class="text-[10px] text-gray-500">${p.warehouse_name || 'Atanmamış'}</span>
                <div class="flex gap-1" onclick="event.stopPropagation()">
                    <button onclick="quickStock(${p.id}, 'remove')" class="w-7 h-7 rounded-lg bg-red-500/10 text-red-400 hover:bg-red-500/20 flex items-center justify-center transition-all text-xs font-bold">−</button>
                    <button onclick="quickStock(${p.id}, 'add')" class="w-7 h-7 rounded-lg bg-green-500/10 text-green-400 hover:bg-green-500/20 flex items-center justify-center transition-all text-xs font-bold">+</button>
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
    } catch (err) { showToast(err.message, 'error'); }
}

// ==================== EXCEL IMPORT ====================
function showExcelImportModal() {
    const warehouseOptions = allWarehouses.map(w => `<option value="${w.id}">${w.name}</option>`).join('');
    
    const formContent = `
    <div class="space-y-4">
        <div class="bg-slate-800/50 p-4 rounded-xl border border-slate-700/50">
            <p class="text-sm text-gray-300 mb-2 font-medium">Nasıl Yüklenir?</p>
            <ul class="text-xs text-gray-400 space-y-1 list-disc pl-4">
                <li>İlk satır mutlaka <b>başlıkları</b> içermelidir (Ürün Adı, Kategori, Stok vb.).</li>
                <li>Zorunlu olan tek sütun <b>"Ürün Adı"</b> sütunudur.</li>
                <li>Mevcut olan ürünler otomatik olarak atlanır (kopyalanmaz).</li>
            </ul>
        </div>
        
        <form id="excelImportForm" onsubmit="event.preventDefault(); submitExcelImport();">
            <div class="mb-4">
                <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">warehouse</span>Hangi Depoya Eklenecek?</label>
                <select name="warehouse_id" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                    <option value="">Depo Seçilmedi (Genel Ürün)</option>
                    ${warehouseOptions}
                </select>
            </div>
            <div>
                <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">description</span>Excel Dosyası (.xlsx, .xls)</label>
                <input type="file" id="excelFile" accept=".xlsx, .xls" required class="w-full text-sm text-gray-400 file:mr-3 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2">
            </div>
        </form>
    </div>`;

    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">İptal</button>
        <button onclick="submitExcelImport()" class="bg-green-500 hover:bg-green-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all flex items-center gap-2"><span class="material-icons-outlined text-lg">upload</span>Yükle ve Aktar</button>`;

    showModal("Excel'den Toplu Ürün Ekle", formContent, footer);
}

async function submitExcelImport() {
    const fileInput = document.getElementById('excelFile');
    if (!fileInput.files.length) {
        showToast('Lütfen bir Excel dosyası seçin', 'warning');
        return;
    }
    
    const warehouseId = document.querySelector('#excelImportForm select[name="warehouse_id"]').value;
    const btn = document.querySelector('button[onclick="submitExcelImport()"]');
    const originalText = btn.innerHTML;
    
    btn.disabled = true; 
    btn.innerHTML = '<div class="spinner border-t-white w-4 h-4 mr-2 inline-block"></div>Yükleniyor...';
    
    try {
        const result = await api.importExcelProducts(fileInput.files[0], warehouseId || null);
        showToast(`${result.added} yeni ürün eklendi, ${result.skipped} ürün atlandı.`, 'success');
        closeModal();
        if(typeof loadInitialData === 'function') await loadInitialData();
        loadProducts();
    } catch (err) {
        showToast(err.message, 'error');
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}
