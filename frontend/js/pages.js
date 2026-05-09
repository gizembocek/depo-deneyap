// ==================== REPORTS PAGE ====================
async function renderReportsPage() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
    <div class="animate-fade-in">
        <h1 class="text-2xl font-bold text-white mb-6">Raporlama</h1>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <div class="glass rounded-2xl p-6">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center"><span class="material-icons-outlined text-green-400 text-2xl">description</span></div>
                    <div><h3 class="text-lg font-bold text-white">Excel Raporu</h3><p class="text-xs text-gray-400">Filtrelenmiş verileri Excel'e aktar</p></div>
                </div>
                <div class="space-y-3 mb-4">
                    <select id="reportCategory" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                        <option value="">Tüm Kategoriler</option>
                        <option value="Sarf Malzemesi">Sarf Malzemesi</option>
                        <option value="Genel / Dayanıklı Malzeme">Genel / Dayanıklı</option>
                        <option value="Elektronik Bileşen">Elektronik Bileşen</option>
                    </select>
                    <select id="reportWarehouse" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                        <option value="">Tüm Depolar</option>
                        ${allWarehouses.map(w => `<option value="${w.id}">${w.name}</option>`).join('')}
                    </select>
                </div>
                <button onclick="downloadExcel()" class="w-full bg-green-500 hover:bg-green-600 text-white py-3 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2">
                    <span class="material-icons-outlined">download</span>Excel İndir (.xlsx)
                </button>
            </div>
            <div class="glass rounded-2xl p-6">
                <div class="flex items-center gap-3 mb-4">
                    <div class="w-12 h-12 rounded-xl bg-red-500/20 flex items-center justify-center"><span class="material-icons-outlined text-red-400 text-2xl">picture_as_pdf</span></div>
                    <div><h3 class="text-lg font-bold text-white">PDF Raporu</h3><p class="text-xs text-gray-400">Filtrelenmiş verileri PDF'e aktar</p></div>
                </div>
                <p class="text-sm text-gray-400 mb-4">Yukarıdaki filtre ayarları PDF raporu için de geçerlidir.</p>
                <button onclick="downloadPDF()" class="w-full bg-deneyap-red-500 hover:bg-deneyap-red-600 text-white py-3 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2">
                    <span class="material-icons-outlined">download</span>PDF İndir
                </button>
            </div>
        </div>
        <div class="glass rounded-2xl p-5">
            <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">history</span>Son İşlem Kayıtları</h3>
                <button onclick="loadReportLogs()" class="text-xs text-deneyap-blue-400 hover:text-deneyap-blue-300 flex items-center gap-1"><span class="material-icons-outlined text-sm">refresh</span>Yenile</button>
            </div>
            <div id="reportLogs"><div class="flex justify-center py-6"><div class="spinner"></div></div></div>
        </div>
    </div>`;
    loadReportLogs();
}

async function loadReportLogs() {
    const container = document.getElementById('reportLogs');
    if (!container) return;
    try {
        const logs = await api.getLogs({ limit: 50 });
        if (logs.length === 0) {
            container.innerHTML = '<p class="text-center text-gray-500 py-6">Henüz işlem kaydı yok</p>';
            return;
        }
        const actionLabels = { add: 'Stok Ekleme', remove: 'Stok Çıkarma', set: 'Stok Ayarlama', create: 'Ürün Oluşturma', status_change: 'Durum Değişikliği' };
        const actionColors = { add: 'text-green-400', remove: 'text-red-400', set: 'text-blue-400', create: 'text-purple-400', status_change: 'text-yellow-400' };
        
        container.innerHTML = `<div class="overflow-x-auto"><table class="w-full">
            <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700">
                <th class="pb-3 text-left">Tarih</th><th class="pb-3 text-left">Kullanıcı</th><th class="pb-3 text-left">İşlem</th><th class="pb-3 text-left">Ürün</th><th class="pb-3 text-center">Değişiklik</th><th class="pb-3 text-left">Not</th>
            </tr></thead>
            <tbody>${logs.map(l => `
                <tr class="border-b border-slate-700/30 text-sm hover:bg-slate-800/30 transition-colors">
                    <td class="py-2.5 text-xs text-gray-500">${new Date(l.created_at).toLocaleString('tr-TR')}</td>
                    <td class="py-2.5 text-gray-300">${l.user_name || '-'}</td>
                    <td class="py-2.5"><span class="${actionColors[l.action] || 'text-gray-400'} text-xs font-medium">${actionLabels[l.action] || l.action}</span></td>
                    <td class="py-2.5 text-white font-medium cursor-pointer hover:text-deneyap-blue-400" onclick="showProductDetail(${l.product_id})">${l.product_name || '-'}</td>
                    <td class="py-2.5 text-center text-xs text-gray-400">${l.previous_value || ''} → ${l.new_value || ''}</td>
                    <td class="py-2.5 text-xs text-gray-500 truncate max-w-[200px]">${l.note || '-'}</td>
                </tr>`).join('')}</tbody></table></div>`;
    } catch (err) { container.innerHTML = `<p class="text-red-400 text-center py-4">${err.message}</p>`; }
}

async function downloadExcel() {
    try {
        showToast('Excel raporu hazırlanıyor...', 'info');
        const params = { category: document.getElementById('reportCategory')?.value, warehouse_id: document.getElementById('reportWarehouse')?.value };
        await api.exportExcel(params);
        showToast('Excel raporu indirildi');
    } catch (err) { showToast(err.message, 'error'); }
}

async function downloadPDF() {
    try {
        showToast('PDF raporu hazırlanıyor...', 'info');
        const params = { category: document.getElementById('reportCategory')?.value, warehouse_id: document.getElementById('reportWarehouse')?.value };
        await api.exportPDF(params);
        showToast('PDF raporu indirildi');
    } catch (err) { showToast(err.message, 'error'); }
}

// ==================== COURSES PAGE ====================
async function renderCoursesPage() {
    const content = document.getElementById('pageContent');
    try {
        const courses = await api.getCourses();
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-white">Ders Yönetimi</h1>
                <button onclick="showCourseForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Ders Ekle
                </button>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${courses.length === 0 ? '<div class="col-span-full text-center py-16 text-gray-500">Henüz ders eklenmemiş</div>' : courses.map(c => `
                <div class="glass rounded-2xl p-5 flex items-center justify-between product-card">
                    <div class="flex items-center gap-3">
                        <div class="w-10 h-10 rounded-xl bg-deneyap-blue-500/20 flex items-center justify-center text-deneyap-blue-400">
                            <span class="material-icons-outlined">school</span>
                        </div>
                        <span class="font-medium text-white">${c.name}</span>
                    </div>
                    ${api.isAdmin() ? `
                    <button onclick="deleteCourse(${c.id})" class="text-gray-500 hover:text-red-400 p-2 transition-colors">
                        <span class="material-icons-outlined">delete</span>
                    </button>` : ''}
                </div>`).join('')}
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}

function showCourseForm() {
    const formContent = `
    <form id="courseForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5">Ders Adı *</label>
        <input type="text" name="name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500" placeholder="Örn: Robotik ve Kodlama"></div>
    </form>`;
    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm transition-all">İptal</button>
        <button onclick="submitCourseForm()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">Ders Oluştur</button>`;
    showModal('Yeni Ders Ekle', formContent, footer);
}

async function submitCourseForm() {
    const form = document.getElementById('courseForm');
    if (!form.reportValidity()) return;
    try {
        await api.createCourse({ name: new FormData(form).get('name') });
        showToast('Ders başarıyla oluşturuldu');
        closeModal();
        renderCoursesPage();
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteCourse(id) {
    if (!confirm('Bu dersi silmek istediğinize emin misiniz?')) return;
    try {
        await api.deleteCourse(id);
        showToast('Ders silindi');
        renderCoursesPage();
    } catch (err) { showToast(err.message, 'error'); }
}

// ==================== SHIPMENTS PAGE ====================
async function renderShipmentsPage() {
    const content = document.getElementById('pageContent');
    try {
        const shipments = await api.getShipments();
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-white">Gönderim ve Kontrol</h1>
                <button onclick="showShipmentForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">add</span>Yeni İşlem (Giriş/Çıkış)
                </button>
            </div>
            ${shipments.length === 0 ? '<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">local_shipping</span><p class="text-gray-400 text-lg">Henüz gönderim/işlem yok</p></div>' : `
            <div class="space-y-4">${shipments.map(s => `
                <div class="glass rounded-2xl p-5 product-card">
                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
                        <div>
                            <h3 class="text-lg font-bold text-white flex items-center gap-2">
                                ${s.name}
                                <span class="text-[10px] px-2 py-0.5 rounded-md ${s.shipment_type === 'Çıkış' ? 'bg-deneyap-red-500/20 text-deneyap-red-400' : 'bg-green-500/20 text-green-400'}">${s.shipment_type || 'Giriş'}</span>
                                ${s.outgoing_reason ? `<span class="text-[10px] px-2 py-0.5 rounded-md bg-slate-700 text-gray-300">${s.outgoing_reason}</span>` : ''}
                            </h3>
                            <div class="flex gap-3 mt-1 text-xs text-gray-400">
                                ${s.shipment_date ? `<span>Tarih: ${new Date(s.shipment_date).toLocaleDateString('tr-TR')}</span>` : ''}
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            ${api.isAdmin() ? `<button onclick="deleteShipment(${s.id})" class="text-gray-400 hover:text-red-400 p-1"><span class="material-icons-outlined text-lg">delete</span></button>` : ''}
                        </div>
                    </div>

                    ${(s.arrival_image_url || s.visual_image_url || s.invoice_image_url) ? `
                    <div class="flex gap-2 mb-3 mt-2">
                        ${s.arrival_image_url ? `<span class="text-xs flex items-center gap-1 text-deneyap-blue-400 bg-deneyap-blue-500/10 px-2 py-1 rounded border border-deneyap-blue-500/20"><span class="material-icons-outlined text-[14px]">inventory_2</span> Koli Foto.</span>` : ''}
                        ${s.visual_image_url ? `<span class="text-xs flex items-center gap-1 text-purple-400 bg-purple-500/10 px-2 py-1 rounded border border-purple-500/20"><span class="material-icons-outlined text-[14px]">image</span> Ürün Görseli</span>` : ''}
                        ${s.invoice_image_url ? `<span class="text-xs flex items-center gap-1 text-green-400 bg-green-500/10 px-2 py-1 rounded border border-green-500/20"><span class="material-icons-outlined text-[14px]">receipt_long</span> Fatura Foto.</span>` : ''}
                    </div>` : ''}

                    ${s.items.length > 0 ? `
                    <div class="overflow-x-auto"><table class="w-full text-sm">
                        <thead><tr class="text-xs text-gray-500 border-b border-slate-700"><th class="pb-2 text-left">Ürün</th><th class="pb-2 text-center">Beklenen</th><th class="pb-2 text-center">Gerçekte Gelen</th><th class="pb-2 text-center">Durum</th></tr></thead>
                        <tbody>${s.items.map(i => `
                            <tr class="border-b border-slate-700/30">
                                <td class="py-2 text-gray-300">${i.product_name || '-'}</td>
                                <td class="py-2 text-center">${i.expected_quantity}</td>
                                <td class="py-2 text-center font-bold ${i.actual_quantity !== i.expected_quantity ? 'text-red-400' : 'text-green-400'}">${i.actual_quantity !== null ? i.actual_quantity : '-'}</td>
                                <td class="py-2 text-center"><span class="text-xs ${i.status === 'complete' ? 'text-green-400' : i.status === 'missing' ? 'text-red-400' : i.status === 'extra' ? 'text-blue-400' : 'text-gray-400'}">${i.status === 'complete' ? 'Tamam' : i.status === 'missing' ? 'Eksik' : i.status === 'extra' ? 'Fazla' : 'Bekliyor'}</span></td>
                            </tr>`).join('')}</tbody>
                    </table></div>` : '<p class="text-sm text-gray-500">Ürün yok</p>'}
                    ${s.notes ? `<p class="text-xs text-gray-500 mt-3 border-t border-slate-700/50 pt-2"><span class="font-medium text-gray-400">Not:</span> ${s.notes}</p>` : ''}
                </div>`).join('')}</div>`}
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}



function toggleShipmentType(val) {
    const outDiv = document.getElementById('outgoingReasonDiv');
    const inDiv = document.getElementById('incomingPhotosDiv');
    if (val === 'Çıkış') { outDiv.classList.remove('hidden'); inDiv.classList.add('hidden'); } 
    else { outDiv.classList.add('hidden'); inDiv.classList.remove('hidden'); }
    // Mevcut ürün satırlarını yeni tipe göre yeniden oluştur
    const container = document.getElementById('shipmentItems');
    if (container) {
        const count = container.children.length;
        container.innerHTML = '';
        for (let i = 0; i < count; i++) addShipmentItem();
    }
}

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result);
        reader.onerror = error => reject(error);
    });
}

function addShipmentItem() {
    const container = document.getElementById('shipmentItems');
    const idx = container.children.length;
    const selectId = `productSelect_${idx}`;
    const searchId = `productSearch_${idx}`;
    const dropdownId = `productDropdown_${idx}`;
    // Mevcut gönderim tipini oku
    const shipmentTypeSelect = document.querySelector('select[name="shipment_type"]');
    const isCikis = shipmentTypeSelect?.value === 'Çıkış';

    const div = document.createElement('div');
    div.className = 'flex gap-2 items-center mb-2 bg-slate-800/30 p-2 rounded-xl border border-slate-700/50';

    const qtySection = isCikis
        ? `<div class="flex gap-2 items-center bg-slate-900/50 p-1.5 rounded-lg border border-red-500/30">
            <div class="flex flex-col">
                <span class="text-[9px] text-red-400 text-center font-bold">MİKTAR</span>
                <input type="number" name="qty_single_${idx}" min="1" value="1" class="w-16 bg-slate-800 border border-slate-700 rounded-lg px-1 py-1 text-sm text-white text-center focus:outline-none focus:border-red-500">
            </div>
           </div>`
        : `<div class="flex gap-2 items-center bg-slate-900/50 p-1.5 rounded-lg border border-slate-700">
            <div class="flex flex-col">
                <span class="text-[9px] text-gray-500 text-center font-bold">BEKLENEN</span>
                <input type="number" name="expected_qty_${idx}" min="1" value="1" oninput="checkMismatch(this)" class="w-14 bg-slate-800 border border-slate-700 rounded-lg px-1 py-1 text-sm text-white text-center focus:outline-none focus:border-deneyap-blue-500">
            </div>
            <div class="flex flex-col">
                <span class="text-[9px] text-deneyap-blue-400 text-center font-bold">GELEN</span>
                <input type="number" name="actual_qty_${idx}" min="0" value="1" oninput="checkMismatch(this)" class="w-14 bg-slate-800 border border-slate-700 rounded-lg px-1 py-1 text-sm text-white text-center focus:outline-none focus:border-deneyap-blue-500">
            </div>
            <span id="warning_${idx}" class="material-icons-outlined text-red-500 hidden text-lg" title="Eksik veya Fazla Ürün!">error</span>
           </div>`;

    div.innerHTML = `
        <div class="flex-1 flex gap-1">
            <div class="relative flex-1">
                <input type="text" id="${searchId}" placeholder="Ürün ara..." autocomplete="off"
                    class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-deneyap-blue-500 pr-8"
                    oninput="filterProductDropdown('${searchId}', '${dropdownId}', '${selectId}')"
                    onfocus="showProductDropdown('${dropdownId}')"
                    onblur="setTimeout(() => hideProductDropdown('${dropdownId}'), 200)">
                <span class="material-icons-outlined absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 text-base pointer-events-none">search</span>
                <div id="${dropdownId}" class="hidden absolute z-50 top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-xl shadow-xl max-h-48 overflow-y-auto">
                    ${allProducts.map(p => `<div class="px-3 py-2 text-sm text-gray-300 hover:bg-slate-700 cursor-pointer" onmousedown="selectProductItem('${searchId}', '${dropdownId}', '${selectId}', ${p.id}, '${p.name.replace(/'/g, '&#39;').replace(/"/g, '&quot;')}', ${p.current_stock})">${p.name} <span class="text-xs text-gray-500">(Stok: ${p.current_stock})</span></div>`).join('')}
                </div>
            </div>
            <select id="${selectId}" name="product_${idx}" class="hidden">
                <option value=""></option>
                ${allProducts.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
            </select>
            <button type="button" onclick="showQuickProductModal('${selectId}', '${searchId}')" class="bg-deneyap-blue-500/20 text-deneyap-blue-400 hover:text-white px-3 rounded-xl flex items-center justify-center transition-all border border-deneyap-blue-500/30" title="Hızlı Ürün Ekle"><span class="material-icons-outlined text-[18px]">add</span></button>
        </div>
        ${qtySection}
        <button type="button" onclick="this.parentElement.remove()" class="text-red-400 hover:bg-slate-800 p-2 rounded-lg transition-colors"><span class="material-icons-outlined text-sm">close</span></button>`;
    container.appendChild(div);
}

function showProductDropdown(dropdownId) {
    document.getElementById(dropdownId)?.classList.remove('hidden');
}

function hideProductDropdown(dropdownId) {
    document.getElementById(dropdownId)?.classList.add('hidden');
}

function filterProductDropdown(searchId, dropdownId, selectId) {
    const searchVal = document.getElementById(searchId)?.value.toLowerCase() || '';
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    dropdown.classList.remove('hidden');
    const items = dropdown.querySelectorAll('div');
    items.forEach(item => {
        const text = item.textContent.toLowerCase();
        item.style.display = text.includes(searchVal) ? '' : 'none';
    });
}

function selectProductItem(searchId, dropdownId, selectId, productId, productName, productStock) {
    const searchInput = document.getElementById(searchId);
    const selectEl = document.getElementById(selectId);
    if (searchInput) searchInput.value = `${productName} (Stok: ${productStock})`;
    if (selectEl) selectEl.value = productId;
    hideProductDropdown(dropdownId);
}

function checkMismatch(inputElem) {
    const parent = inputElem.closest('.flex.gap-2.items-center');
    const expected = parseInt(parent.querySelector('input[name^="expected_qty_"]').value) || 0;
    const actual = parseInt(parent.querySelector('input[name^="actual_qty_"]').value) || 0;
    const warningIcon = parent.querySelector('span[id^="warning_"]');
    
    if (expected !== actual) warningIcon.classList.remove('hidden');
    else warningIcon.classList.add('hidden');
}

// Fonksiyonun başına "async" ekledik
async function showShipmentForm() {
    
    // SİHİRLİ DOKUNUŞ: Form ekrana çizilmeden hemen önce güncel ürünleri zorla çektiriyoruz!
    try {
        allProducts = await api.getProducts();
    } catch(e) { 
        console.error("Ürünler yüklenemedi", e); 
    }

    const formContent = `
    <form id="shipmentForm" class="space-y-4">
        <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">İşlem / Gönderim Adı *</label>
            <input type="text" name="name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500" placeholder="Örn: Ağustos İrsaliyesi"></div>
            
            <div><label class="block text-xs text-gray-400 mb-1.5">İşlem Tipi *</label>
            <select name="shipment_type" onchange="toggleShipmentType(this.value)" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                <option value="Giriş">Giriş (Stoğa Ekle)</option>
                <option value="Çıkış">Çıkış (Stoktan Düş)</option>
            </select></div>
        </div>

        <div id="outgoingReasonDiv" class="hidden animate-fade-in">
            <label class="block text-xs text-gray-400 mb-1.5">Çıkış Sebebi</label>
            <select name="outgoing_reason" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                <option value="">Seçiniz...</option>
                <option value="Garanti">Garantiye Gönderim</option>
                <option value="Demirbaştan Düşme">Demirbaştan Düşme (Tamir Edilemez)</option>
            </select>
        </div>

        <div id="incomingPhotosDiv" class="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-800/40 p-3 rounded-xl border border-slate-700 animate-fade-in">
            <div><label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">inventory_2</span>Koli Fotoğrafı</label>
            <input type="file" id="arrival_image" accept="image/*" class="w-full text-xs text-gray-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer"></div>
            
            <div><label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">image</span>Ürün Görseli</label>
            <input type="file" id="visual_image" accept="image/*" class="w-full text-xs text-gray-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer"></div>
            
            <div><label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">receipt_long</span>Fatura Fotoğrafı</label>
            <input type="file" id="invoice_image" accept="image/*" class="w-full text-xs text-gray-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer"></div>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">İşlem Tarihi</label><input type="date" name="shipment_date" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">Kontrol Tarihi</label><input type="date" name="check_date" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Notlar</label><textarea name="notes" rows="2" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white" placeholder="Eklemek istediğiniz notlar..."></textarea></div>
        
        <div>
            <label class="block text-xs text-gray-400 mb-1.5">Ürünler</label>
            <div id="shipmentItems" class="space-y-2"></div>
            <button type="button" onclick="addShipmentItem()" class="mt-2 text-xs text-deneyap-blue-400 hover:text-deneyap-blue-300 flex items-center gap-1 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700"><span class="material-icons-outlined text-sm">add</span>Listeye Satır Ekle</button>
        </div>
    </form>`;
    
    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm transition-all">İptal</button>
        <button onclick="submitShipmentForm()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">Kaydet</button>`;
    
    showModal('Yeni İşlem Ekle', formContent, footer);
    setTimeout(() => toggleShipmentType('Giriş'), 50);
}

async function submitShipmentForm() {
    const form = document.getElementById('shipmentForm');
    if (!form.reportValidity()) return;
    const fd = new FormData(form);

    const items = [];
    const container = document.getElementById('shipmentItems');
    const shipmentType = fd.get('shipment_type');
    const isCikis = shipmentType === 'Çıkış';
    Array.from(container.children).forEach((row, idx) => {
        const productId = parseInt(row.querySelector(`select[name^="product_"]`)?.value);
        if (!productId) return;
        if (isCikis) {
            // Çıkış: tek miktar alanı, expected = actual = miktar
            const qty = parseInt(row.querySelector(`input[name^="qty_single_"]`)?.value) || 1;
            items.push({ product_id: productId, expected_quantity: qty, actual_quantity: qty });
        } else {
            // Giriş: beklenen + gelen
            const expected = parseInt(row.querySelector(`input[name^="expected_qty_"]`)?.value) || 1;
            const actual = parseInt(row.querySelector(`input[name^="actual_qty_"]`)?.value);
            items.push({ product_id: productId, expected_quantity: expected, actual_quantity: isNaN(actual) ? null : actual });
        }
    });

    if (items.length === 0) return showToast('Lütfen listeye en az bir ürün ekleyin!', 'error');

    const data = {
        name: fd.get('name'),
        shipment_type: shipmentType,
        outgoing_reason: isCikis ? fd.get('outgoing_reason') : null,
        shipment_date: fd.get('shipment_date') ? new Date(fd.get('shipment_date')).toISOString() : null,
        check_date: fd.get('check_date') ? new Date(fd.get('check_date')).toISOString() : null,
        notes: fd.get('notes'),
        items: items
    };

    const btn = form.querySelector('button[onclick="submitShipmentForm()"]');
    if(btn) { btn.disabled = true; btn.innerHTML = '<div class="spinner border-t-white w-4 h-4 mr-2 inline-block"></div>Yükleniyor...'; }

    try {
        if (shipmentType === 'Giriş') {
            const arrivalImg = document.getElementById('arrival_image')?.files[0];
            const visualImg = document.getElementById('visual_image')?.files[0];
            const invoiceImg = document.getElementById('invoice_image')?.files[0];

            if (arrivalImg) data.arrival_image_url = await fileToBase64(arrivalImg);
            if (visualImg) data.visual_image_url = await fileToBase64(visualImg);
            if (invoiceImg) data.invoice_image_url = await fileToBase64(invoiceImg);
        }

        await api.createShipment(data); 
        showToast('İşlem başarıyla kaydedildi', 'success'); 
        closeModal(); 
        
        // Sistemi ve listeleri hemen yenile
        if (typeof loadInitialData === 'function') await loadInitialData(); 
        renderShipmentsPage(); 
    } catch (err) { 
        showToast(err.message, 'error'); 
        if(btn) { btn.disabled = false; btn.innerHTML = 'Kaydet'; }
    }
}

async function deleteShipment(id) {
    if (!confirm('Bu işlemi silmek istediğinize emin misiniz?')) return;
    try { await api.deleteShipment(id); showToast('İşlem silindi', 'success'); renderShipmentsPage(); } catch (err) { showToast(err.message, 'error'); }
}

// ==================== HIZLI ÜRÜN EKLEME ====================
function showQuickProductModal(selectId, searchId) {
    const overlay = document.createElement('div');
    overlay.id = 'quickProductOverlay';
    overlay.className = 'fixed inset-0 z-[110] bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 animate-fade-in';
    
    const warehouseOptions = allWarehouses.map(w => `<option value="${w.id}">${w.name}</option>`).join('');

    overlay.innerHTML = `
        <div class="glass rounded-2xl p-6 w-full max-w-sm shadow-2xl border border-deneyap-blue-500/30 animate-scale-in">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2"><span class="material-icons-outlined text-deneyap-blue-400">add_box</span>Hızlı Ürün Ekle</h3>
            <form id="quickProductForm" class="space-y-3" onsubmit="event.preventDefault(); submitQuickProduct('${selectId}', '${searchId || ''}');">
                <div>
                    <label class="block text-xs text-gray-400 mb-1.5">Ürün Adı *</label>
                    <input type="text" name="name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500" placeholder="Örn: Arduino Uno">
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1.5">Kategori</label>
                    <select name="category" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                        <option value="Genel / Dayanıklı Malzeme">Genel / Dayanıklı Malzeme</option>
                        <option value="Sarf Malzemesi">Sarf Malzemesi</option>
                        <option value="Elektronik Bileşen">Elektronik Bileşen</option>
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">warehouse</span>Depo</label>
                    <select name="warehouse_id" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                        <option value="">Depo seçilmedi</option>
                        ${warehouseOptions}
                    </select>
                </div>
                <div>
                    <label class="block text-xs text-gray-400 mb-1.5"><span class="material-icons-outlined text-[14px] align-middle mr-1">photo_camera</span>Ürün Fotoğrafı (İsteğe Bağlı)</label>
                    <div id="quickImgPreviewWrap" class="hidden mb-2 w-full h-28 bg-slate-800 rounded-xl overflow-hidden flex items-center justify-center border border-slate-700">
                        <img id="quickImgPreview" class="h-full w-full object-contain p-1">
                    </div>
                    <input type="file" id="quickImageFile" accept="image/*" onchange="previewQuickImage(this)" class="w-full text-xs text-gray-400 file:mr-2 file:py-1.5 file:px-3 file:rounded-lg file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 hover:file:bg-deneyap-blue-500/30 cursor-pointer bg-slate-800 border border-slate-700 rounded-xl px-3 py-2">
                </div>
                <div class="flex justify-end gap-2 mt-4 pt-2">
                    <button type="button" onclick="document.getElementById('quickProductOverlay').remove()" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-xl text-sm transition-all">İptal</button>
                    <button type="submit" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium transition-all flex items-center gap-1"><span class="material-icons-outlined text-[18px]">save</span>Kaydet</button>
                </div>
            </form>
        </div>
    `;
    document.body.appendChild(overlay);
}

function previewQuickImage(input) {
    const wrap = document.getElementById('quickImgPreviewWrap');
    const img = document.getElementById('quickImgPreview');
    if (input.files && input.files[0]) {
        const reader = new FileReader();
        reader.onload = (e) => { img.src = e.target.result; wrap.classList.remove('hidden'); wrap.style.display = 'flex'; };
        reader.readAsDataURL(input.files[0]);
    }
}

async function submitQuickProduct(selectId, searchId) {
    const form = document.getElementById('quickProductForm');
    if (!form.reportValidity()) return;
    const fd = new FormData(form);
    const warehouseId = fd.get('warehouse_id') ? parseInt(fd.get('warehouse_id')) : null;
    const data = { 
        name: fd.get('name'), 
        category: fd.get('category'), 
        status: 'Çalışan', 
        current_stock: 0, 
        critical_stock: 5, 
        ideal_stock: 10,
        warehouse_id: warehouseId
    };
    
    // Fotoğraf varsa base64'e çevir ve ekle
    const imgFile = document.getElementById('quickImageFile')?.files[0];
    if (imgFile) {
        try { data.image_url = await fileToBase64(imgFile); } catch(e) {}
    }
    
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) { submitBtn.disabled = true; submitBtn.innerHTML = '<div class="spinner border-t-white w-4 h-4 mr-2 inline-block"></div>Kaydediliyor...'; }

    try {
        const newProduct = await api.createProduct(data);
        showToast('Ürün başarıyla eklendi!', 'success');
        
        // allProducts listesini güncelle (global)
        if(typeof loadInitialData === 'function') await loadInitialData();
        // Eğer kullanıcı ürünler sayfasındaysa listeyi yenile
        if(currentPage === 'products' && typeof loadProducts === 'function') loadProducts();
        
        // Hızlı formdaki gizli select'e yeni ürünü ekle ve seç
        document.querySelectorAll('select[name^="product_"]').forEach(select => {
            const opt = document.createElement('option');
            opt.value = newProduct.id; 
            opt.textContent = `${newProduct.name} (Stok: 0)`; 
            select.appendChild(opt);
        });
        
        const targetSelect = document.getElementById(selectId);
        if(targetSelect) targetSelect.value = newProduct.id;

        // Arama inputunu da doldur
        if (searchId) {
            const searchInput = document.getElementById(searchId);
            if (searchInput) searchInput.value = `${newProduct.name} (Stok: 0)`;
        }
        
        document.getElementById('quickProductOverlay').remove();
    } catch(err) { 
        showToast(err.message, 'error');
        if (submitBtn) { submitBtn.disabled = false; submitBtn.innerHTML = '<span class="material-icons-outlined text-[18px]">save</span>Kaydet'; }
    }
}

// ==================== USERS PAGE ====================
async function renderUsersPage() {
    if (!api.isAdmin()) { navigateTo('dashboard'); return; }
    const content = document.getElementById('pageContent');
    try {
        const users = await api.getUsers();
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6">
                <h1 class="text-2xl font-bold text-white">Kullanıcı Yönetimi</h1>
                <button onclick="showUserForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium transition-all">
                    <span class="material-icons-outlined text-lg">person_add</span>Yeni Kullanıcı
                </button>
            </div>
            <div class="glass rounded-2xl overflow-hidden">
                <div class="overflow-x-auto"><table class="w-full text-sm">
                    <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700 bg-slate-800/50">
                        <th class="px-5 py-4 text-left">Kullanıcı</th><th class="px-5 py-4 text-center">Rol</th><th class="px-5 py-4 text-center">Durum</th><th class="px-5 py-4 text-center">Depolar</th><th class="px-5 py-4 text-center">İşlem</th>
                    </tr></thead>
                    <tbody>${users.map(u => `
                        <tr class="border-b border-slate-700/30 hover:bg-slate-800/30 transition-colors">
                            <td class="px-5 py-4"><div class="flex items-center gap-3">
                                <div class="w-9 h-9 rounded-full bg-gradient-to-br ${u.role === 'admin' ? 'from-deneyap-red-500 to-deneyap-yellow-500' : 'from-deneyap-blue-500 to-deneyap-blue-700'} flex items-center justify-center text-white font-bold text-sm">${u.full_name.charAt(0)}</div>
                                <div><p class="font-medium text-white">${u.full_name}</p><p class="text-xs text-gray-500">${u.email}</p></div>
                            </div></td>
                            <td class="px-5 py-4 text-center"><span class="text-xs px-2.5 py-1 rounded-full ${u.role === 'admin' ? 'bg-deneyap-red-500/10 text-deneyap-red-400' : 'bg-deneyap-blue-500/10 text-deneyap-blue-400'}">${u.role === 'admin' ? 'Yönetici' : 'Kullanıcı'}</span></td>
                            <td class="px-5 py-4 text-center"><span class="text-xs px-2.5 py-1 rounded-full ${u.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}">${u.is_active ? 'Aktif' : 'Pasif'}</span></td>
                            <td class="px-5 py-4 text-center"><span class="text-xs text-gray-400">${u.warehouse_ids.length} depo</span></td>
                            <td class="px-5 py-4 text-center"><div class="flex justify-center gap-1">
                                <button onclick="showUserAccess(${u.id}, '${u.full_name}')" class="text-gray-400 hover:text-deneyap-blue-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Depo Erişimi"><span class="material-icons-outlined text-lg">key</span></button>
                                <button onclick="toggleUserRole(${u.id}, '${u.role}')" class="text-gray-400 hover:text-yellow-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Rol Değiştir"><span class="material-icons-outlined text-lg">swap_horiz</span></button>
                                <button onclick="toggleUserStatus(${u.id}, ${u.is_active})" class="text-gray-400 hover:text-${u.is_active ? 'red' : 'green'}-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Durum Değiştir"><span class="material-icons-outlined text-lg">${u.is_active ? 'block' : 'check_circle'}</span></button>
                                <button onclick="deleteUser(${u.id}, '${u.full_name}')" class="text-gray-400 hover:text-red-500 p-1.5 rounded-lg hover:bg-slate-800 transition-all" title="Kullanıcıyı Sil"><span class="material-icons-outlined text-lg">delete_forever</span></button>
                            </div></td>
                        </tr>`).join('')}</tbody>
                </table></div>
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}

async function deleteUser(userId, userName) {
    if (!confirm(`${userName} isimli kullanıcıyı tamamen silmek istediğinize emin misiniz?`)) return;
    try {
        await api.deleteUser(userId);
        showToast('Kullanıcı başarıyla silindi', 'success');
        renderUsersPage();
    } catch (err) { showToast(err.message, 'error'); }
}

async function toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    if (!confirm(`Rol ${newRole === 'admin' ? 'Yönetici' : 'Kullanıcı'} olarak değiştirilsin mi?`)) return;
    try { await api.updateUser(userId, { role: newRole }); showToast('Rol güncellendi'); renderUsersPage(); } catch (err) { showToast(err.message, 'error'); }
}

async function toggleUserStatus(userId, isActive) {
    try { await api.updateUser(userId, { is_active: !isActive }); showToast('Durum güncellendi'); renderUsersPage(); } catch (err) { showToast(err.message, 'error'); }
}

function showUserForm() {
    const formContent = `
    <form id="userForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5">Ad Soyad *</label><input type="text" name="full_name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">E-posta *</label><input type="email" name="email" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Şifre *</label><input type="password" name="password" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Kullanıcı Rolü</label>
            <select name="role" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                <option value="user">Kullanıcı (Eğitmen / Görevli)</option><option value="admin">Yönetici (Admin)</option>
            </select>
        </div>
    </form>`;
    const footer = `<button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm transition-all">İptal</button><button onclick="submitUserForm()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">Kullanıcı Oluştur</button>`;
    showModal('Yeni Kullanıcı Ekle', formContent, footer);
}

async function submitUserForm() {
    const form = document.getElementById('userForm');
    if (!form.reportValidity()) return;
    const fd = new FormData(form);
    try { await api.registerUser({ full_name: fd.get('full_name'), email: fd.get('email'), password: fd.get('password'), role: fd.get('role') }); showToast('Kullanıcı oluşturuldu.'); closeModal(); renderUsersPage(); } catch (err) { showToast(err.message, 'error'); }
}