// ==================== RAPORLAR ====================
async function renderReportsPage() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
    <div class="animate-fade-in">
        <h1 class="text-2xl font-bold text-white mb-6">Raporlama</h1>
        <div class="glass rounded-2xl p-6 mb-6">
            <h3 class="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2"><span class="material-icons-outlined text-base">filter_alt</span>Rapor filtreleri</h3>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-5">
                <select id="reportWarehouse" aria-label="Depo" class="${inputClass()}">${selectOptions(allWarehouses.map(w => ({ value: w.id, label: w.name })), '', 'Tüm Depolar')}</select>
                <select id="reportCategory" aria-label="Kategori" class="${inputClass()}">${selectOptions(CATEGORIES, '', 'Tüm Kategoriler')}</select>
                <select id="reportStatus" aria-label="Durum" class="${inputClass()}">${selectOptions(STATUSES, '', 'Tüm Durumlar')}</select>
                <label class="flex items-center gap-2 text-sm text-gray-300 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 cursor-pointer">
                    <input type="checkbox" id="reportLowStock" class="rounded border-slate-600">Yalnızca kritik stok (sipariş listesi)</label>
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <button type="button" onclick="downloadReport('excel', this)" class="bg-green-600 hover:bg-green-700 text-white py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2">
                    <span class="material-icons-outlined">table_view</span>Excel Raporu İndir (.xlsx)</button>
                <button type="button" onclick="downloadReport('pdf', this)" class="bg-deneyap-red-500 hover:bg-deneyap-red-600 text-white py-3 rounded-xl font-medium text-sm flex items-center justify-center gap-2">
                    <span class="material-icons-outlined">picture_as_pdf</span>PDF Raporu İndir</button>
            </div>
            <p class="text-xs text-gray-500 mt-3">Kritik stoktaki ürünler raporlarda kırmızı ile işaretlenir. Excel raporunda ideale göre eksik miktar da yer alır.</p>
        </div>
        <div class="glass rounded-2xl p-5">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
                <h3 class="text-lg font-bold text-white flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">history</span>İşlem Kayıtları</h3>
                <div class="flex gap-2">
                    <select id="logAction" aria-label="İşlem türü" onchange="loadReportLogs()" class="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-white">
                        ${selectOptions(Object.entries(ACTION_LABELS).map(([value, label]) => ({ value, label })), '', 'Tüm işlemler')}
                    </select>
                    <button type="button" onclick="loadReportLogs()" class="text-xs text-deneyap-blue-400 hover:text-deneyap-blue-300 flex items-center gap-1 px-2"><span class="material-icons-outlined text-sm">refresh</span>Yenile</button>
                </div>
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
        const logs = await api.getLogs({ limit: 100, action: document.getElementById('logAction')?.value });
        if (logs.length === 0) { container.innerHTML = '<p class="text-center text-gray-500 py-6">Henüz işlem kaydı yok</p>'; return; }
        container.innerHTML = `<div class="overflow-x-auto"><table class="w-full">
            <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700">
                <th class="pb-3 text-left">Tarih</th><th class="pb-3 text-left">Kullanıcı</th><th class="pb-3 text-left">İşlem</th><th class="pb-3 text-left">Ürün</th><th class="pb-3 text-center">Değişim</th><th class="pb-3 text-left">Not</th>
            </tr></thead>
            <tbody>${logs.map(l => `
                <tr class="border-b border-slate-700/30 text-sm hover:bg-slate-800/30">
                    <td class="py-2.5 pr-3 text-xs text-gray-500 whitespace-nowrap">${fmtDateTime(l.created_at)}</td>
                    <td class="py-2.5 pr-3 text-gray-300">${esc(l.user_name || '-')}</td>
                    <td class="py-2.5 pr-3"><span class="${ACTION_COLORS[l.action] || 'text-gray-400'} text-xs font-medium whitespace-nowrap">${esc(ACTION_LABELS[l.action] || l.action)}</span></td>
                    <td class="py-2.5 pr-3 text-white font-medium cursor-pointer hover:text-deneyap-blue-400" onclick="showProductDetail(${l.product_id})">${esc(l.product_name || '-')}</td>
                    <td class="py-2.5 pr-3 text-center text-xs text-gray-400 whitespace-nowrap">${esc(l.previous_value ?? '')} → ${esc(l.new_value ?? '')}</td>
                    <td class="py-2.5 text-xs text-gray-500 max-w-[240px] truncate" title="${esc(l.note || '')}">${esc(l.note || '-')}</td>
                </tr>`).join('')}</tbody></table></div>`;
    } catch (err) { container.innerHTML = `<p class="text-red-400 text-center py-4">${esc(err.message)}</p>`; }
}

async function downloadReport(kind, btn) {
    const params = {
        warehouse_id: document.getElementById('reportWarehouse')?.value,
        category: document.getElementById('reportCategory')?.value,
        status: document.getElementById('reportStatus')?.value,
        low_stock: document.getElementById('reportLowStock')?.checked,
    };
    setButtonLoading(btn, true, 'Hazırlanıyor...');
    try {
        if (kind === 'excel') await api.exportExcel(params); else await api.exportPDF(params);
        showToast(kind === 'excel' ? 'Excel raporu indirildi' : 'PDF raporu indirildi');
    } catch (err) { showToast(err.message, 'error'); }
    finally { setButtonLoading(btn, false); }
}

// ==================== DERSLER ====================
async function renderCoursesPage() {
    const content = document.getElementById('pageContent');
    try {
        allCourses = await api.getCourses();
        if (currentPage !== 'courses') return;
        const admin = api.isAdmin();
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6 gap-3">
                <div><h1 class="text-2xl font-bold text-white">Ders Yönetimi</h1>
                    <p class="text-sm text-gray-400 mt-1">Bir derse tıklayarak o derste kullanılan malzemeleri görün.</p></div>
                ${admin ? `<button onclick="showCourseForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap">
                    <span class="material-icons-outlined text-lg">add</span>Yeni Ders</button>` : ''}
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                ${allCourses.length === 0 ? '<div class="col-span-full text-center py-16 text-gray-500">Henüz ders eklenmemiş</div>' : allCourses.map(c => `
                <div class="glass rounded-2xl p-5 flex items-center justify-between gap-3 product-card cursor-pointer" role="button" tabindex="0"
                    onclick="goToProducts({ course_id: '${c.id}' })" onkeydown="if(event.key==='Enter') goToProducts({ course_id: '${c.id}' })">
                    <div class="flex items-center gap-3 min-w-0">
                        <div class="w-10 h-10 rounded-xl bg-deneyap-blue-500/20 flex items-center justify-center text-deneyap-blue-400 flex-shrink-0"><span class="material-icons-outlined">school</span></div>
                        <div class="min-w-0"><p class="font-medium text-white truncate" title="${esc(c.name)}">${esc(c.name)}</p>
                            <p class="text-xs text-gray-500">${fmtNumber(c.product_count || 0)} ürün</p></div>
                    </div>
                    ${admin ? `<div class="flex flex-shrink-0" onclick="event.stopPropagation()">
                        <button type="button" onclick="showCourseForm(${c.id})" class="text-gray-500 hover:text-yellow-400 p-2" title="Yeniden adlandır" aria-label="Yeniden adlandır"><span class="material-icons-outlined text-lg">edit</span></button>
                        <button type="button" onclick="deleteCourse(${c.id})" class="text-gray-500 hover:text-red-400 p-2" title="Sil" aria-label="Sil"><span class="material-icons-outlined text-lg">delete</span></button>
                    </div>` : ''}
                </div>`).join('')}
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${esc(err.message)}</div>`; }
}

function showCourseForm(id = null) {
    const course = id ? allCourses.find(c => c.id === id) : null;
    showPromptModal(course ? 'Dersi Yeniden Adlandır' : 'Yeni Ders Ekle', 'Ders adı', course?.name || '', 'text', async (name) => {
        name = name.trim();
        if (!name) return;
        try {
            if (course) await api.renameCourse(course.id, name); else await api.createCourse({ name });
            showToast(course ? 'Ders güncellendi' : 'Ders oluşturuldu');
            await loadInitialData();
            renderCoursesPage();
        } catch (err) { showToast(err.message, 'error'); }
    });
}

async function deleteCourse(id) {
    const c = allCourses.find(x => x.id === id);
    const ok = await confirmModal('Dersi Sil', `"${c?.name}" dersi silinecek. Ürünler silinmez, sadece bu dersle bağlantıları kaldırılır.`, { confirmText: 'Sil', danger: true });
    if (!ok) return;
    try {
        await api.deleteCourse(id);
        showToast('Ders silindi');
        await loadInitialData();
        renderCoursesPage();
    } catch (err) { showToast(err.message, 'error'); }
}

// ==================== GİRİŞ / ÇIKIŞ İŞLEMLERİ ====================
let shipmentsCache = [];
const ITEM_STATUS = {
    complete: { label: 'Tamam', cls: 'text-green-400' },
    missing: { label: 'Eksik', cls: 'text-red-400' },
    extra: { label: 'Fazla', cls: 'text-blue-400' },
    pending: { label: 'Bekliyor', cls: 'text-gray-400' },
};

async function renderShipmentsPage() {
    const content = document.getElementById('pageContent');
    try {
        shipmentsCache = await api.getShipments();
        if (currentPage !== 'shipments') return;
        const admin = api.isAdmin();
        const pendingCount = shipmentsCache.filter(s => s.status === 'pending').length;
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
                <div><h1 class="text-2xl font-bold text-white">Giriş / Çıkış İşlemleri</h1>
                    <p class="text-sm text-gray-400 mt-1">Gelen koliler, garantiye/tamire giden ürünler ve demirbaştan düşülenler.${pendingCount ? ` <span class="text-deneyap-yellow-400">${pendingCount} işlem kontrol bekliyor.</span>` : ''}</p></div>
                <button onclick="showShipmentForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap">
                    <span class="material-icons-outlined text-lg">add</span>Yeni İşlem</button>
            </div>
            ${shipmentsCache.length === 0 ? '<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">local_shipping</span><p class="text-gray-400 text-lg">Henüz işlem yok</p></div>' : `
            <div class="space-y-4">${shipmentsCache.map(s => {
                const isOut = s.shipment_type === 'Çıkış';
                const images = [
                    s.has_arrival_image ? ['arrival_image_url', 'inventory_2', 'Koli Fotoğrafı', 'text-deneyap-blue-400 bg-deneyap-blue-500/10 border-deneyap-blue-500/20'] : null,
                    s.has_visual_image ? ['visual_image_url', 'image', 'Ürün Görseli', 'text-purple-400 bg-purple-500/10 border-purple-500/20'] : null,
                    s.has_invoice_image ? ['invoice_image_url', 'receipt_long', 'Fatura / İrsaliye', 'text-green-400 bg-green-500/10 border-green-500/20'] : null,
                ].filter(Boolean);
                return `
                <div class="glass rounded-2xl p-5">
                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
                        <div class="min-w-0">
                            <h3 class="text-lg font-bold text-white flex flex-wrap items-center gap-2">
                                <span class="break-words">${esc(s.name)}</span>
                                <span class="text-[10px] px-2 py-0.5 rounded-md ${isOut ? 'bg-deneyap-red-500/20 text-deneyap-red-400' : 'bg-green-500/20 text-green-400'}">${esc(s.shipment_type || 'Giriş')}</span>
                                ${s.outgoing_reason ? `<span class="text-[10px] px-2 py-0.5 rounded-md bg-slate-700 text-gray-300">${esc(s.outgoing_reason)}</span>` : ''}
                                <span class="text-[10px] px-2 py-0.5 rounded-md ${s.status === 'pending' ? 'bg-deneyap-yellow-500/20 text-deneyap-yellow-400' : 'bg-slate-700 text-gray-300'}">${s.status === 'pending' ? 'Kontrol bekliyor' : 'Kontrol edildi'}</span>
                            </h3>
                            <div class="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-xs text-gray-400">
                                ${s.shipment_date ? `<span>İşlem tarihi: ${fmtDate(s.shipment_date)}</span>` : ''}
                                ${s.check_date ? `<span>Kontrol: ${fmtDate(s.check_date)}</span>` : ''}
                                <span>Kaydeden: ${esc(s.creator_name || '-')} • ${fmtDateTime(s.created_at)}</span>
                            </div>
                        </div>
                        <div class="flex items-center gap-2 flex-shrink-0">
                            ${s.items.some(i => i.product_name) ? `<button type="button" onclick="showShipmentCheck(${s.id})" class="text-xs flex items-center gap-1 ${s.status === 'pending' ? 'bg-deneyap-yellow-500 hover:bg-deneyap-yellow-600 text-slate-900' : 'bg-slate-800 hover:bg-slate-700 text-gray-300'} px-3 py-1.5 rounded-lg font-medium">
                                <span class="material-icons-outlined text-sm">fact_check</span>${s.status === 'pending' ? 'Kontrol Et' : 'Düzelt'}</button>` : ''}
                            ${admin ? `<button type="button" onclick="deleteShipment(${s.id})" class="text-gray-400 hover:text-red-400 p-1" title="Sil" aria-label="Sil"><span class="material-icons-outlined text-lg">delete</span></button>` : ''}
                        </div>
                    </div>
                    ${images.length ? `<div class="flex flex-wrap gap-2 mb-3">${images.map(([field, icon, label, cls]) => `
                        <button type="button" onclick="showShipmentImage(${s.id}, '${field}')" class="text-xs flex items-center gap-1 ${cls} px-2 py-1 rounded border hover:opacity-80"><span class="material-icons-outlined text-[14px]">${icon}</span>${label}</button>`).join('')}</div>` : ''}
                    ${s.items.length > 0 ? `
                    <div class="overflow-x-auto"><table class="w-full text-sm">
                        <thead><tr class="text-xs text-gray-500 border-b border-slate-700"><th class="pb-2 text-left">Ürün</th><th class="pb-2 text-center">${isOut ? 'Miktar' : 'Beklenen'}</th>${isOut ? '' : '<th class="pb-2 text-center">Gelen</th>'}<th class="pb-2 text-center">Durum</th></tr></thead>
                        <tbody>${s.items.map(i => {
                            const st = ITEM_STATUS[i.status] || ITEM_STATUS.pending;
                            return `<tr class="border-b border-slate-700/30">
                                <td class="py-2 text-gray-300">${i.product_id && i.product_name ? `<button type="button" class="hover:text-deneyap-blue-400 text-left" onclick="showProductDetail(${i.product_id})">${esc(i.product_name)}</button>` : '<span class="text-gray-500">(silinmiş ürün)</span>'}</td>
                                <td class="py-2 text-center">${fmtNumber(i.expected_quantity)}</td>
                                ${isOut ? '' : `<td class="py-2 text-center font-bold ${i.actual_quantity === null ? 'text-gray-500' : i.actual_quantity !== i.expected_quantity ? 'text-red-400' : 'text-green-400'}">${i.actual_quantity !== null ? fmtNumber(i.actual_quantity) : '-'}</td>`}
                                <td class="py-2 text-center"><span class="text-xs ${st.cls}">${st.label}</span></td>
                            </tr>`;
                        }).join('')}</tbody>
                    </table></div>` : '<p class="text-sm text-gray-500">Ürün yok</p>'}
                    ${s.notes ? `<p class="text-xs text-gray-400 mt-3 border-t border-slate-700/50 pt-2 whitespace-pre-line"><span class="font-medium text-gray-300">Not:</span> ${esc(s.notes)}</p>` : ''}
                </div>`;
            }).join('')}</div>`}
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${esc(err.message)}</div>`; }
}

async function showShipmentImage(id, field) {
    try {
        const s = await api.getShipment(id);
        const url = s[field];
        if (!url) return showToast('Görsel bulunamadı', 'warning');
        showModal(s.name, `<div class="flex justify-center"><img src="${esc(url)}" alt="" class="max-h-[70vh] rounded-xl object-contain"></div>`, '', { size: 'lg' });
    } catch (err) { showToast(err.message, 'error'); }
}

function showShipmentCheck(id) {
    const s = shipmentsCache.find(x => x.id === id);
    if (!s) return;
    const isOut = s.shipment_type === 'Çıkış';
    const rows = s.items.filter(i => i.product_name);
    const content = `
        <form id="checkForm" class="space-y-3">
            <p class="text-sm text-gray-400">${isOut ? 'Gerçekte çıkan miktarları girin.' : 'Koliden gerçekte çıkan (gelen) miktarları girin.'} Beklenenden farklıysa stok otomatik düzeltilir.</p>
            <div class="space-y-2">${rows.map(i => `
                <div class="flex items-center gap-3 bg-slate-800/50 p-3 rounded-xl">
                    <div class="flex-1 min-w-0"><p class="text-sm text-white truncate">${esc(i.product_name)}</p><p class="text-xs text-gray-500">Beklenen: ${fmtNumber(i.expected_quantity)}</p></div>
                    <label class="text-xs text-gray-400" for="chk_${i.id}">${isOut ? 'Çıkan' : 'Gelen'}</label>
                    <input type="number" id="chk_${i.id}" data-item="${i.id}" min="0" step="1" required value="${i.actual_quantity ?? i.expected_quantity}" class="w-24 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-sm text-white text-center focus:outline-none focus:border-deneyap-blue-500">
                </div>`).join('')}</div>
        </form>`;
    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button type="submit" form="checkForm" id="checkBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kaydet</button>`;
    showModal(`Kontrol: ${s.name}`, content, footer);
    document.getElementById('checkForm').onsubmit = async (e) => {
        e.preventDefault();
        const items = [...document.querySelectorAll('#checkForm [data-item]')].map(inp => ({ item_id: Number(inp.dataset.item), actual_quantity: Number(inp.value) }));
        if (items.some(i => !Number.isInteger(i.actual_quantity) || i.actual_quantity < 0)) return showToast('Miktarlar 0 veya daha büyük tam sayı olmalı', 'warning');
        const btn = document.getElementById('checkBtn');
        setButtonLoading(btn, true);
        try {
            await api.checkShipment(id, items);
            showToast('Kontrol kaydedildi, stoklar güncellendi');
            closeModal();
            renderShipmentsPage();
            refreshStatsBadge();
        } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
    };
}

async function deleteShipment(id) {
    const s = shipmentsCache.find(x => x.id === id);
    const ok = await confirmModal('İşlemi Sil', `"${s?.name}" işlemi silinecek.`, {
        confirmText: 'Sil', danger: true,
        checkbox: { label: 'Bu işlemin stok değişikliklerini geri al (önerilir)', checked: true },
    });
    if (!ok) return;
    try {
        await api.deleteShipment(id, ok.checked);
        showToast(ok.checked ? 'İşlem silindi, stoklar geri alındı' : 'İşlem silindi');
        renderShipmentsPage();
        refreshStatsBadge();
    } catch (err) { showToast(err.message, 'error'); }
}

// ---------- Yeni işlem formu ----------
let shipmentRowSeq = 0;

function showShipmentForm() {
    shipmentRowSeq = 0;
    const content = `
    <form id="shipmentForm" class="space-y-4">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5" for="shName">İşlem adı *</label>
                <input type="text" id="shName" name="name" required maxlength="255" autofocus class="${inputClass()}" placeholder="Örn: Ekim 2026 irsaliyesi"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="shType">İşlem tipi *</label>
                <select id="shType" name="shipment_type" onchange="toggleShipmentType(this.value)" class="${inputClass()}">
                    <option value="Giriş">Giriş (stoğa ekle)</option>
                    <option value="Çıkış">Çıkış (stoktan düş)</option>
                </select></div>
        </div>
        <div id="outgoingReasonDiv" class="hidden">
            <label class="block text-xs text-gray-400 mb-1.5" for="shReason">Çıkış sebebi</label>
            <select id="shReason" name="outgoing_reason" class="${inputClass()}">
                <option value="">Seçiniz...</option>
                <option value="Garanti">Garantiye gönderim</option>
                <option value="Tamir">Tamire gönderim</option>
                <option value="Demirbaştan Düşme">Demirbaştan düşme (tamir edilemez)</option>
                <option value="Başka Atölyeye Transfer">Başka atölyeye transfer</option>
                <option value="Ders / Etkinlik Kullanımı">Ders / etkinlik kullanımı (sarf)</option>
                <option value="Diğer">Diğer</option>
            </select>
        </div>
        <div id="incomingPhotosDiv" class="grid grid-cols-1 md:grid-cols-3 gap-3 bg-slate-800/40 p-3 rounded-xl border border-slate-700">
            ${[['arrival_image', 'inventory_2', 'Koli fotoğrafı'], ['visual_image', 'image', 'Ürün görseli'], ['invoice_image', 'receipt_long', 'Fatura / irsaliye']].map(([id, icon, label]) => `
            <div><label class="block text-xs text-gray-400 mb-1.5" for="${id}"><span class="material-icons-outlined text-[14px] align-middle mr-1">${icon}</span>${label}</label>
                <input type="file" id="${id}" accept="image/*" class="w-full text-xs text-gray-400 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-deneyap-blue-500/20 file:text-deneyap-blue-400 cursor-pointer"></div>`).join('')}
        </div>
        <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5" for="shDate">İşlem tarihi</label><input type="date" id="shDate" name="shipment_date" class="${inputClass()}"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5" for="shCheck">Kontrol tarihi</label><input type="date" id="shCheck" name="check_date" class="${inputClass()}"></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="shNotes">Notlar</label><textarea id="shNotes" name="notes" rows="2" maxlength="4000" class="${inputClass()}" placeholder="Kargo firması, takip no, kime teslim edildi..."></textarea></div>
        <div>
            <p class="block text-xs text-gray-400 mb-1.5">Ürünler *</p>
            <div id="shipmentItems" class="space-y-2"></div>
            <button type="button" onclick="addShipmentItem()" class="mt-2 text-xs text-deneyap-blue-400 hover:text-deneyap-blue-300 flex items-center gap-1 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700"><span class="material-icons-outlined text-sm">add</span>Satır ekle</button>
        </div>
    </form>`;
    const footer = `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button type="submit" form="shipmentForm" id="shipmentSubmit" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kaydet</button>`;
    showModal('Yeni Giriş / Çıkış İşlemi', content, footer, { size: 'lg' });
    document.getElementById('shDate').value = new Date().toISOString().slice(0, 10);
    document.getElementById('shipmentForm').onsubmit = (e) => { e.preventDefault(); submitShipmentForm(); };
    addShipmentItem();
}

function currentShipmentType() {
    return document.getElementById('shType')?.value || 'Giriş';
}

function toggleShipmentType(val) {
    const isOut = val === 'Çıkış';
    document.getElementById('outgoingReasonDiv').classList.toggle('hidden', !isOut);
    document.getElementById('incomingPhotosDiv').classList.toggle('hidden', isOut);
    document.querySelectorAll('#shipmentItems [data-row]').forEach(row => {
        row.querySelector('[data-actual-wrap]').classList.toggle('hidden', isOut);
        row.querySelector('[data-expected-label]').textContent = isOut ? 'MİKTAR' : 'BEKLENEN';
    });
}

function addShipmentItem() {
    const container = document.getElementById('shipmentItems');
    const idx = ++shipmentRowSeq;
    const isOut = currentShipmentType() === 'Çıkış';
    const row = document.createElement('div');
    row.dataset.row = idx;
    row.className = 'flex flex-col sm:flex-row gap-2 sm:items-center bg-slate-800/30 p-2 rounded-xl border border-slate-700/50';
    row.innerHTML = `
        <div class="flex-1 flex gap-1">
            <div class="relative flex-1">
                <input type="text" data-search placeholder="Ürün ara (en az 2 harf)..." autocomplete="off" aria-label="Ürün ara"
                    class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-deneyap-blue-500 pr-8">
                <span class="material-icons-outlined absolute right-2 top-1/2 -translate-y-1/2 text-gray-500 text-base pointer-events-none">search</span>
                <div data-dropdown class="hidden absolute z-50 top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-xl shadow-xl max-h-56 overflow-y-auto"></div>
            </div>
            ${api.isAdmin() ? `<button type="button" onclick="showQuickProductModal(${idx})" class="bg-deneyap-blue-500/20 text-deneyap-blue-400 hover:text-white px-3 rounded-xl flex items-center justify-center border border-deneyap-blue-500/30" title="Listede yoksa yeni ürün ekle" aria-label="Yeni ürün ekle"><span class="material-icons-outlined text-[18px]">add</span></button>` : ''}
        </div>
        <div class="flex gap-2 items-center bg-slate-900/50 p-1.5 rounded-lg border border-slate-700">
            <div class="flex flex-col"><span data-expected-label class="text-[9px] text-gray-400 text-center font-bold">${isOut ? 'MİKTAR' : 'BEKLENEN'}</span>
                <input type="number" data-expected min="1" step="1" value="1" aria-label="Beklenen miktar" class="w-16 bg-slate-800 border border-slate-700 rounded-lg px-1 py-1 text-sm text-white text-center focus:outline-none focus:border-deneyap-blue-500"></div>
            <div data-actual-wrap class="flex flex-col ${isOut ? 'hidden' : ''}"><span class="text-[9px] text-deneyap-blue-400 text-center font-bold">GELEN</span>
                <input type="number" data-actual min="0" step="1" placeholder="?" title="Boş bırakırsanız işlem 'kontrol bekliyor' olarak kaydedilir" aria-label="Gelen miktar" class="w-16 bg-slate-800 border border-slate-700 rounded-lg px-1 py-1 text-sm text-white text-center focus:outline-none focus:border-deneyap-blue-500"></div>
        </div>
        <button type="button" onclick="this.closest('[data-row]').remove()" class="text-red-400 hover:bg-slate-800 p-2 rounded-lg self-end sm:self-auto" aria-label="Satırı sil"><span class="material-icons-outlined text-sm">close</span></button>`;
    container.appendChild(row);

    const search = row.querySelector('[data-search]');
    const dropdown = row.querySelector('[data-dropdown]');
    let timer = null;
    search.addEventListener('input', () => {
        delete row.dataset.productId;
        search.classList.remove('border-green-500/60');
        clearTimeout(timer);
        const q = search.value.trim();
        if (q.length < 2) { dropdown.classList.add('hidden'); return; }
        timer = setTimeout(async () => {
            try {
                const items = await api.getProducts({ search: q, per_page: 20, sort: 'name' });
                if (search.value.trim() !== q) return;
                dropdown.innerHTML = items.length ? items.map(p => `
                    <button type="button" data-pick="${p.id}" class="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-slate-700">
                        ${esc(p.name)} <span class="text-xs text-gray-500">(Stok: ${fmtNumber(p.current_stock)}${p.warehouse_name ? ' • ' + esc(p.warehouse_name) : ''})</span></button>`).join('')
                    : '<p class="px-3 py-2 text-sm text-gray-500">Ürün bulunamadı</p>';
                dropdown.classList.remove('hidden');
                dropdown.querySelectorAll('[data-pick]').forEach(btn => btn.addEventListener('mousedown', (ev) => {
                    ev.preventDefault();
                    const p = items.find(x => x.id === Number(btn.dataset.pick));
                    selectShipmentProduct(row, p);
                }));
            } catch (err) { showToast(err.message, 'error'); }
        }, 250);
    });
    search.addEventListener('blur', () => setTimeout(() => dropdown.classList.add('hidden'), 150));
    // "Satır ekle" ile eklenen satırda doğrudan ürün aramaya geçilir (ilk satırda odak işlem adındadır)
    if (container.children.length > 1) search.focus();
}

function selectShipmentProduct(row, p) {
    row.dataset.productId = p.id;
    const search = row.querySelector('[data-search]');
    search.value = `${p.name} (Stok: ${p.current_stock})`;
    search.classList.add('border-green-500/60');
    row.querySelector('[data-dropdown]').classList.add('hidden');
}

// Yüklenen fotoğrafı veritabanında az yer kaplasın diye küçültür (en fazla 1600 px, JPEG)
function compressImage(file, maxSide = 1600, quality = 0.82) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(new Error('Dosya okunamadı'));
        reader.onload = () => {
            const img = new Image();
            img.onerror = () => reject(new Error('Geçersiz görsel dosyası'));
            img.onload = () => {
                const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
                const canvas = document.createElement('canvas');
                canvas.width = Math.round(img.width * scale);
                canvas.height = Math.round(img.height * scale);
                canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
                resolve(canvas.toDataURL('image/jpeg', quality));
            };
            img.src = reader.result;
        };
        reader.readAsDataURL(file);
    });
}

async function submitShipmentForm() {
    const form = document.getElementById('shipmentForm');
    const fd = new FormData(form);
    const name = (fd.get('name') || '').trim();
    if (!name) return showToast('İşlem adı boş olamaz', 'warning');
    const type = fd.get('shipment_type');
    const isOut = type === 'Çıkış';

    const items = [];
    let invalid = false;
    document.querySelectorAll('#shipmentItems [data-row]').forEach(row => {
        const productId = Number(row.dataset.productId);
        const searchText = row.querySelector('[data-search]').value.trim();
        if (!productId) { if (searchText) invalid = true; return; }
        const expected = Number(row.querySelector('[data-expected]').value);
        const actualRaw = row.querySelector('[data-actual]').value;
        const actual = isOut ? expected : (actualRaw === '' ? null : Number(actualRaw));
        if (!Number.isInteger(expected) || expected < 1 || (actual !== null && (!Number.isInteger(actual) || actual < 0))) invalid = true;
        items.push({ product_id: productId, expected_quantity: expected, actual_quantity: actual });
    });
    if (invalid) return showToast('Her satırda listeden bir ürün seçin ve geçerli miktar girin', 'warning');
    if (items.length === 0) return showToast('Lütfen en az bir ürün ekleyin', 'warning');

    const dateOrNull = (v) => v ? `${v}T12:00:00` : null;
    const data = {
        name, shipment_type: type,
        outgoing_reason: isOut ? (fd.get('outgoing_reason') || null) : null,
        shipment_date: dateOrNull(fd.get('shipment_date')),
        check_date: dateOrNull(fd.get('check_date')),
        notes: (fd.get('notes') || '').trim() || null,
        items,
    };
    const btn = document.getElementById('shipmentSubmit');
    setButtonLoading(btn, true);
    try {
        if (!isOut) {
            for (const [field, inputId] of [['arrival_image_url', 'arrival_image'], ['visual_image_url', 'visual_image'], ['invoice_image_url', 'invoice_image']]) {
                const file = document.getElementById(inputId)?.files[0];
                if (file) data[field] = await compressImage(file);
            }
        }
        const created = await api.createShipment(data);
        showToast(created.status === 'pending' ? 'İşlem kaydedildi (kontrol bekliyor)' : 'İşlem kaydedildi, stoklar güncellendi');
        closeModal();
        renderShipmentsPage();
        refreshStatsBadge();
    } catch (err) {
        showToast(err.message, 'error');
        setButtonLoading(btn, false);
    }
}

// ---------- Hızlı ürün ekleme (işlem formunun üstünde açılır) ----------
function showQuickProductModal(rowIdx) {
    const overlay = document.createElement('div');
    overlay.id = 'quickProductOverlay';
    overlay.className = 'fixed inset-0 z-[110] bg-black/70 flex items-center justify-center p-4 animate-fade-in';
    overlay.innerHTML = `
        <div class="glass rounded-2xl p-6 w-full max-w-sm shadow-2xl border border-deneyap-blue-500/30 animate-scale-in" role="dialog" aria-modal="true">
            <h3 class="text-lg font-bold text-white mb-4 flex items-center gap-2"><span class="material-icons-outlined text-deneyap-blue-400">add_box</span>Hızlı Ürün Ekle</h3>
            <form id="quickProductForm" class="space-y-3">
                <div><label class="block text-xs text-gray-400 mb-1.5" for="qpName">Ürün adı *</label>
                    <input type="text" id="qpName" name="name" required maxlength="255" class="${inputClass()}" placeholder="Örn: Arduino Uno"></div>
                <div><label class="block text-xs text-gray-400 mb-1.5" for="qpCat">Kategori</label>
                    <select id="qpCat" name="category" class="${inputClass()}">${selectOptions(CATEGORIES, 'Genel / Dayanıklı Malzeme')}</select></div>
                <div><label class="block text-xs text-gray-400 mb-1.5" for="qpWh">Depo</label>
                    <select id="qpWh" name="warehouse_id" class="${inputClass()}">${selectOptions(allWarehouses.map(w => ({ value: w.id, label: w.name })), '', 'Depo seçilmedi')}</select></div>
                <p class="text-xs text-gray-500">Ürün 0 stokla oluşturulur; miktar bu işlemle eklenir.</p>
                <div class="flex justify-end gap-2 pt-2">
                    <button type="button" id="qpCancel" class="bg-slate-700 hover:bg-slate-600 text-white px-4 py-2 rounded-xl text-sm">İptal</button>
                    <button type="submit" id="qpSave" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-1"><span class="material-icons-outlined text-[18px]">save</span>Kaydet</button>
                </div>
            </form>
        </div>`;
    document.body.appendChild(overlay);
    const row = document.querySelector(`#shipmentItems [data-row="${rowIdx}"]`);
    const typed = row?.querySelector('[data-search]').value.trim() || '';
    document.getElementById('qpName').value = typed.replace(/\s*\(Stok:.*\)$/, '');
    document.getElementById('qpName').focus();
    document.getElementById('qpCancel').onclick = () => overlay.remove();
    document.getElementById('quickProductForm').onsubmit = async (e) => {
        e.preventDefault();
        const fd = new FormData(e.target);
        const name = fd.get('name').trim();
        if (!name) return showToast('Ürün adı boş olamaz', 'warning');
        const btn = document.getElementById('qpSave');
        setButtonLoading(btn, true);
        try {
            const p = await api.createProduct({
                name, category: fd.get('category'), status: 'Çalışan', current_stock: 0, critical_stock: 5, ideal_stock: 10,
                warehouse_id: fd.get('warehouse_id') ? Number(fd.get('warehouse_id')) : null,
            });
            showToast('Ürün eklendi');
            if (row) selectShipmentProduct(row, p);
            overlay.remove();
        } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
    };
}

// ==================== KULLANICILAR ====================
let usersCache = [];

async function renderUsersPage() {
    if (!api.isAdmin()) { navigateTo('dashboard'); return; }
    const content = document.getElementById('pageContent');
    try {
        usersCache = await api.getUsers();
        if (currentPage !== 'users') return;
        const meId = api.user?.id;
        const whName = (id) => allWarehouses.find(w => w.id === id)?.name;
        content.innerHTML = `
        <div class="animate-fade-in">
            <div class="flex items-center justify-between mb-6 gap-3">
                <div><h1 class="text-2xl font-bold text-white">Kullanıcı Yönetimi</h1>
                    <p class="text-sm text-gray-400 mt-1">Yöneticiler her şeyi görür. Kullanıcılar yalnızca yetki verilen depoları görür ve stok işlemi yapabilir.</p></div>
                <button onclick="showUserForm()" class="flex items-center gap-2 bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap">
                    <span class="material-icons-outlined text-lg">person_add</span>Yeni Kullanıcı</button>
            </div>
            <div class="glass rounded-2xl overflow-hidden">
                <div class="overflow-x-auto"><table class="w-full text-sm">
                    <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700 bg-slate-800/50">
                        <th class="px-5 py-4 text-left">Kullanıcı</th><th class="px-5 py-4 text-center">Rol</th><th class="px-5 py-4 text-center">Durum</th><th class="px-5 py-4 text-left">Depolar</th><th class="px-5 py-4 text-center">İşlem</th>
                    </tr></thead>
                    <tbody>${usersCache.map(u => {
                        const isMe = u.id === meId;
                        const whs = u.role === 'admin' ? '<span class="text-xs text-gray-500">Tümü (yönetici)</span>'
                            : (u.warehouse_ids.length ? u.warehouse_ids.map(id => `<span class="inline-block text-[11px] bg-slate-800 text-gray-300 px-2 py-0.5 rounded mr-1 mb-1">${esc(whName(id) || '#' + id)}</span>`).join('')
                            : '<span class="text-xs text-deneyap-yellow-400">Depo yetkisi yok</span>');
                        const act = (fn, icon, title, color, disabled = false) => `<button type="button" onclick="${fn}" ${disabled ? 'disabled' : ''} class="text-gray-400 ${color} p-1.5 rounded-lg hover:bg-slate-800" title="${title}" aria-label="${title}"><span class="material-icons-outlined text-lg">${icon}</span></button>`;
                        return `
                        <tr class="border-b border-slate-700/30 hover:bg-slate-800/30">
                            <td class="px-5 py-4"><div class="flex items-center gap-3">
                                <div class="w-9 h-9 rounded-full bg-gradient-to-br ${u.role === 'admin' ? 'from-deneyap-red-500 to-deneyap-yellow-500' : 'from-deneyap-blue-500 to-deneyap-blue-700'} flex items-center justify-center text-white font-bold text-sm flex-shrink-0">${esc((u.full_name || '?').charAt(0).toLocaleUpperCase('tr-TR'))}</div>
                                <div class="min-w-0"><p class="font-medium text-white">${esc(u.full_name)}${isMe ? ' <span class="text-xs text-gray-500">(siz)</span>' : ''}</p><p class="text-xs text-gray-500">${esc(u.email)}</p></div>
                            </div></td>
                            <td class="px-5 py-4 text-center"><span class="text-xs px-2.5 py-1 rounded-full ${u.role === 'admin' ? 'bg-deneyap-red-500/10 text-deneyap-red-400' : 'bg-deneyap-blue-500/10 text-deneyap-blue-400'}">${u.role === 'admin' ? 'Yönetici' : 'Kullanıcı'}</span></td>
                            <td class="px-5 py-4 text-center"><span class="text-xs px-2.5 py-1 rounded-full ${u.is_active ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}">${u.is_active ? 'Aktif' : 'Pasif'}</span></td>
                            <td class="px-5 py-4 max-w-[260px]">${whs}</td>
                            <td class="px-5 py-4"><div class="flex justify-center gap-1">
                                ${act(`showUserAccess(${u.id})`, 'key', 'Depo erişimi', 'hover:text-deneyap-blue-400', u.role === 'admin')}
                                ${act(`resetUserPassword(${u.id})`, 'lock_reset', 'Şifre sıfırla', 'hover:text-deneyap-yellow-400')}
                                ${act(`toggleUserRole(${u.id})`, 'swap_horiz', 'Rol değiştir', 'hover:text-yellow-400', isMe)}
                                ${act(`toggleUserStatus(${u.id})`, u.is_active ? 'block' : 'check_circle', u.is_active ? 'Pasif yap' : 'Aktif yap', u.is_active ? 'hover:text-red-400' : 'hover:text-green-400', isMe)}
                                ${act(`deleteUser(${u.id})`, 'delete_forever', 'Kullanıcıyı sil', 'hover:text-red-500', isMe)}
                            </div></td>
                        </tr>`;
                    }).join('')}</tbody>
                </table></div>
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${esc(err.message)}</div>`; }
}

function showUserAccess(userId) {
    const u = usersCache.find(x => x.id === userId);
    if (!u) return;
    const content = allWarehouses.length === 0
        ? '<p class="text-sm text-gray-400">Önce Depolar sayfasından depo oluşturun.</p>'
        : `<form id="accessForm" class="space-y-2">
            <p class="text-sm text-gray-400 mb-3"><b class="text-white">${esc(u.full_name)}</b> hangi depoları görebilsin ve stok işlemi yapabilsin?</p>
            ${allWarehouses.map(w => `<label class="flex items-center gap-3 bg-slate-800/60 hover:bg-slate-800 p-3 rounded-xl cursor-pointer">
                <input type="checkbox" value="${w.id}" ${u.warehouse_ids.includes(w.id) ? 'checked' : ''} class="rounded border-slate-600">
                <span class="text-sm text-white">${esc(w.name)}</span><span class="text-xs text-gray-500 ml-auto">${fmtNumber(w.product_count)} ürün</span></label>`).join('')}
            <p class="text-xs text-gray-500 pt-2">Depoya atanmamış (genel) ürünleri herkes görebilir.</p>
        </form>`;
    const footer = allWarehouses.length ? `
        <button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button type="submit" form="accessForm" id="accessBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kaydet</button>` : '';
    showModal('Depo Erişimi', content, footer, { size: 'sm' });
    const form = document.getElementById('accessForm');
    if (!form) return;
    form.onsubmit = async (e) => {
        e.preventDefault();
        const ids = [...form.querySelectorAll('input[type=checkbox]:checked')].map(cb => Number(cb.value));
        const btn = document.getElementById('accessBtn');
        setButtonLoading(btn, true);
        try {
            await api.setUserWarehouses(userId, ids);
            showToast('Depo erişimi güncellendi');
            closeModal();
            renderUsersPage();
        } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
    };
}

function resetUserPassword(userId) {
    const u = usersCache.find(x => x.id === userId);
    const extra = '<p class="text-xs text-gray-500">En az 8 karakter, bir büyük harf ve bir rakam. Yeni şifreyi kullanıcıya iletin; kullanıcı giriş yaptıktan sonra kendisi değiştirebilir.</p>';
    showPromptModal('Şifre Sıfırla', `${u?.full_name || ''} için yeni şifre`, '', 'text', async (pw) => {
        const problem = passwordProblem(pw);
        if (problem) { showToast(problem, 'warning'); return resetUserPassword(userId); }
        try {
            const r = await api.resetUserPassword(userId, pw);
            showToast(r.message);
        } catch (err) { showToast(err.message, 'error'); }
    }, null, extra);
}

async function toggleUserRole(userId) {
    const u = usersCache.find(x => x.id === userId);
    const newRole = u.role === 'admin' ? 'user' : 'admin';
    const ok = await confirmModal('Rol Değiştir', `${u.full_name} kullanıcısının rolü "${newRole === 'admin' ? 'Yönetici' : 'Kullanıcı'}" olarak değiştirilsin mi?`, { confirmText: 'Değiştir' });
    if (!ok) return;
    try { await api.updateUser(userId, { role: newRole }); showToast('Rol güncellendi'); renderUsersPage(); }
    catch (err) { showToast(err.message, 'error'); }
}

async function toggleUserStatus(userId) {
    const u = usersCache.find(x => x.id === userId);
    try { await api.updateUser(userId, { is_active: !u.is_active }); showToast(u.is_active ? 'Kullanıcı pasif yapıldı' : 'Kullanıcı aktif edildi'); renderUsersPage(); }
    catch (err) { showToast(err.message, 'error'); }
}

async function deleteUser(userId) {
    const u = usersCache.find(x => x.id === userId);
    const ok = await confirmModal('Kullanıcıyı Sil', `${u.full_name} (${u.email}) kalıcı olarak silinecek. Geçmiş işlem kayıtları korunur.`, { confirmText: 'Sil', danger: true });
    if (!ok) return;
    try { await api.deleteUser(userId); showToast('Kullanıcı silindi'); renderUsersPage(); }
    catch (err) { showToast(err.message, 'error'); }
}

function showUserForm() {
    const content = `
    <form id="userForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5" for="ufName">Ad soyad *</label><input id="ufName" type="text" name="full_name" required maxlength="255" autofocus class="${inputClass()}"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="ufEmail">E-posta *</label><input id="ufEmail" type="email" name="email" required class="${inputClass()}"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="ufPass">Şifre *</label>
            <div class="relative"><input id="ufPass" type="password" name="password" required autocomplete="new-password" class="${inputClass('pr-11')}">
            <button type="button" onclick="togglePasswordVisibility('ufPass', this)" class="material-icons-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-lg" aria-label="Şifreyi göster">visibility</button></div>
            <p class="text-[11px] text-gray-500 mt-1">En az 8 karakter, bir büyük harf ve bir rakam.</p></div>
        <div><label class="block text-xs text-gray-400 mb-1.5" for="ufRole">Rol</label>
            <select id="ufRole" name="role" class="${inputClass()}">
                <option value="user">Kullanıcı (eğitmen / görevli)</option><option value="admin">Yönetici</option>
            </select></div>
        ${allWarehouses.length ? `<div><p class="block text-xs text-gray-400 mb-1.5">Depo erişimi (kullanıcı rolü için)</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-2 bg-slate-800 rounded-xl p-3 max-h-40 overflow-y-auto">
            ${allWarehouses.map(w => `<label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer"><input type="checkbox" name="warehouse_ids" value="${w.id}" class="rounded border-slate-600">${esc(w.name)}</label>`).join('')}
            </div></div>` : ''}
    </form>`;
    const footer = `<button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button type="submit" form="userForm" id="userSubmit" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kullanıcı Oluştur</button>`;
    showModal('Yeni Kullanıcı Ekle', content, footer);
    document.getElementById('userForm').onsubmit = async (e) => {
        e.preventDefault();
        const form = e.target;
        const fd = new FormData(form);
        const problem = passwordProblem(fd.get('password'));
        if (problem) return showToast(problem, 'warning');
        const btn = document.getElementById('userSubmit');
        setButtonLoading(btn, true);
        try {
            const user = await api.registerUser({ full_name: fd.get('full_name').trim(), email: fd.get('email').trim(), password: fd.get('password'), role: fd.get('role') });
            const whIds = [...form.querySelectorAll('[name="warehouse_ids"]:checked')].map(cb => Number(cb.value));
            if (whIds.length && user.role !== 'admin') await api.setUserWarehouses(user.id, whIds);
            showToast('Kullanıcı oluşturuldu');
            closeModal();
            renderUsersPage();
        } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
    };
}

// ==================== AYARLAR VE YEDEK ====================
async function renderSettingsPage() {
    if (!api.isAdmin()) { navigateTo('dashboard'); return; }
    const content = document.getElementById('pageContent');
    try {
        appSettings = await api.getSettings();
        content.innerHTML = `
        <div class="animate-fade-in max-w-3xl">
            <h1 class="text-2xl font-bold text-white mb-6">Ayarlar ve Yedek</h1>
            <div class="glass rounded-2xl p-6 mb-6">
                <h3 class="text-lg font-bold text-white mb-1 flex items-center gap-2"><span class="material-icons-outlined text-deneyap-blue-400">apartment</span>Atölye Bilgileri</h3>
                <p class="text-xs text-gray-400 mb-4">Atölye adı menüde, giriş ekranında ve rapor başlıklarında görünür.</p>
                <form id="settingsForm" class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div class="sm:col-span-2"><label class="block text-xs text-gray-400 mb-1.5" for="stName">Atölye adı</label>
                        <input id="stName" name="atolye_adi" required maxlength="255" value="${esc(appSettings.atolye_adi || '')}" class="${inputClass()}"></div>
                    <div><label class="block text-xs text-gray-400 mb-1.5" for="stIl">İl</label>
                        <input id="stIl" name="il" maxlength="100" value="${esc(appSettings.il || '')}" class="${inputClass()}"></div>
                    <div class="sm:col-span-3 flex justify-end"><button type="submit" id="settingsBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Kaydet</button></div>
                </form>
            </div>
            <div class="glass rounded-2xl p-6 mb-6">
                <h3 class="text-lg font-bold text-white mb-1 flex items-center gap-2"><span class="material-icons-outlined text-green-400">backup</span>Yedekleme</h3>
                <p class="text-sm text-gray-400 mb-4">Tüm verilerin (ürünler, depolar, kullanıcılar, işlem geçmişi) tek dosyalık yedeğini indirin. Ayda en az bir kez yedek alıp dosyayı bilgisayar dışında (USB bellek, bulut) saklamanız önerilir.</p>
                <button type="button" onclick="downloadBackup(this)" class="bg-green-600 hover:bg-green-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">download</span>Yedek İndir (.json)</button>
                <p class="text-xs text-gray-500 mt-3">Geri yükleme: bilgisayarın format atılması gibi durumlarda boş kuruluma <code class="text-gray-300">backend</code> klasöründe <code class="text-gray-300">python yedekleme.py yukle dosya.json</code> komutuyla yapılır (bkz. KURULUM.md).</p>
            </div>
            <div class="glass rounded-2xl p-6 mb-6">
                <h3 class="text-lg font-bold text-white mb-1 flex items-center gap-2"><span class="material-icons-outlined text-deneyap-yellow-400">health_and_safety</span>Veritabanı Sağlık Kontrolü</h3>
                <p class="text-sm text-gray-400 mb-4">Varsayılan şifreli hesapları, tekrar eden ürün ve dersleri, iki kez aktarılmış Excel listelerini ve SQL Server'a taşımayı engelleyecek hatalı kayıtları bulur.</p>
                <button type="button" onclick="runDbCheck(this)" class="bg-deneyap-yellow-500 hover:bg-deneyap-yellow-600 text-slate-900 px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">search</span>Kontrol Et</button>
                <div id="dbCheckResult" class="mt-4"></div>
            </div>
            <div class="glass rounded-2xl p-6">
                <h3 class="text-lg font-bold text-white mb-3 flex items-center gap-2"><span class="material-icons-outlined text-gray-400">info</span>Sistem</h3>
                <dl class="grid grid-cols-2 gap-y-2 text-sm">
                    <dt class="text-gray-400">Sürüm</dt><dd class="text-white">${esc(appSettings.version || '-')}</dd>
                    <dt class="text-gray-400">Ürün sayısı</dt><dd class="text-white" id="sysProducts">-</dd>
                    <dt class="text-gray-400">Depo sayısı</dt><dd class="text-white">${fmtNumber(allWarehouses.length)}</dd>
                    <dt class="text-gray-400">API belgeleri</dt><dd><a href="/docs" target="_blank" rel="noopener" class="text-deneyap-blue-400 hover:underline">/docs</a></dd>
                </dl>
            </div>
        </div>`;
        api.getProductStats().then(s => { const el = document.getElementById('sysProducts'); if (el) el.textContent = fmtNumber(s.total_products); }).catch(() => {});
        document.getElementById('settingsForm').onsubmit = async (e) => {
            e.preventDefault();
            const fd = new FormData(e.target);
            const btn = document.getElementById('settingsBtn');
            setButtonLoading(btn, true);
            try {
                appSettings = await api.updateSettings({ atolye_adi: fd.get('atolye_adi').trim(), il: fd.get('il').trim() });
                await loadInitialData();
                showToast('Ayarlar kaydedildi');
            } catch (err) { showToast(err.message, 'error'); }
            finally { setButtonLoading(btn, false); }
        };
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${esc(err.message)}</div>`; }
}

async function downloadBackup(btn) {
    setButtonLoading(btn, true, 'Hazırlanıyor...');
    try { const name = await api.downloadBackup(); showToast(`Yedek indirildi: ${name}`); }
    catch (err) { showToast(err.message, 'error'); }
    finally { setButtonLoading(btn, false); }
}

// ---------- Veritabanı sağlık kontrolü ----------
const SEVERITY_STYLE = {
    'KRİTİK': 'bg-red-500/15 text-red-300 border-red-500/30',
    'UYARI': 'bg-deneyap-yellow-500/15 text-deneyap-yellow-300 border-deneyap-yellow-500/30',
    'BİLGİ': 'bg-slate-700/60 text-gray-300 border-slate-600',
};

function renderDbFindings(findings, actions = null) {
    const el = document.getElementById('dbCheckResult');
    if (!el) return;
    const problems = findings.filter(b => b.kod !== 'OZET');
    const summary = findings.find(b => b.kod === 'OZET');
    const fixable = problems.some(b => b.duzeltme);
    const hasDupProducts = problems.some(b => b.kod === 'TEKRAR_URUN');
    const hasEmptyShipments = problems.some(b => b.kod === 'BOS_GONDERIM');
    const hasCopies = problems.some(b => b.kod === 'KOPYA_AKTARIM');
    el.innerHTML = `
        ${actions ? `<div class="bg-green-500/10 border border-green-500/30 rounded-xl p-4 mb-4 text-sm">
            <p class="text-green-300 font-medium mb-1">Uygulanan düzeltmeler (önce yedek alındı):</p>
            <ul class="list-disc pl-5 text-gray-300 space-y-0.5">${actions.yapilan.length ? actions.yapilan.map(a => `<li>${esc(a)}</li>`).join('') : '<li>Düzeltilecek bir şey yoktu</li>'}</ul>
            <p class="text-xs text-gray-500 mt-2">Yedek dosyası: ${esc(actions.backup)}</p></div>` : ''}
        ${problems.length === 0 ? '<p class="text-green-400 text-sm flex items-center gap-2"><span class="material-icons-outlined">check_circle</span>Sorun bulunmadı.</p>' : ''}
        <div class="space-y-3">${problems.map(b => `
            <details class="border rounded-xl ${SEVERITY_STYLE[b.seviye] || SEVERITY_STYLE['BİLGİ']}" ${b.seviye === 'KRİTİK' ? 'open' : ''}>
                <summary class="cursor-pointer p-3 text-sm font-medium flex items-center gap-2">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-black/20">${esc(b.seviye)}</span>
                    <span class="flex-1">${esc(b.baslik)}</span>${b.adet ? `<span class="text-xs opacity-80">${fmtNumber(b.adet)}</span>` : ''}
                </summary>
                <div class="px-4 pb-3 text-xs text-gray-300 space-y-2">
                    ${b.detay.length ? `<ul class="list-disc pl-5 space-y-0.5 max-h-48 overflow-y-auto">${b.detay.map(d => `<li class="whitespace-pre-line">${esc(d)}</li>`).join('')}</ul>` : ''}
                    ${b.duzeltme ? `<p class="text-green-300">Otomatik düzeltme: ${esc(b.duzeltme)}</p>` : ''}
                    ${b.oneri ? `<p class="text-deneyap-yellow-200">Öneri: ${esc(b.oneri)}</p>` : ''}
                </div>
            </details>`).join('')}</div>
        ${summary ? `<p class="text-xs text-gray-500 mt-3">${summary.detay.map(esc).join(' • ')}</p>` : ''}
        ${fixable || hasDupProducts || hasEmptyShipments || hasCopies ? `
        <div class="mt-4 border-t border-slate-700/50 pt-4 space-y-3">
            ${hasCopies ? `<label class="flex items-start gap-2 text-sm text-gray-300 cursor-pointer"><input type="checkbox" id="fixCopies" class="rounded border-slate-600 mt-0.5">
                <span>Birden fazla kez aktarılmış listelerin fazla kopyalarını sil <span class="text-gray-500">("tutulacak" işaretli kopya kalır; stok hareketi olan bir kopya asla silinmez)</span></span></label>` : ''}
            ${hasDupProducts ? `<label class="flex items-start gap-2 text-sm text-gray-300 cursor-pointer"><input type="checkbox" id="fixDupProducts" class="rounded border-slate-600 mt-0.5">
                <span>Aynı depodaki aynı adlı ürünleri tek kayıtta birleştir <span class="text-gray-500">(stok olarak en büyük değer alınır, dersler ve geçmiş birleşir)</span></span></label>` : ''}
            ${hasEmptyShipments ? `<label class="flex items-start gap-2 text-sm text-gray-300 cursor-pointer"><input type="checkbox" id="fixEmptyShipments" class="rounded border-slate-600 mt-0.5">
                <span>Ürünsüz (boş) gönderim kayıtlarını sil</span></label>` : ''}
            <button type="button" onclick="runDbFix(this)" class="bg-green-600 hover:bg-green-700 text-white px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2"><span class="material-icons-outlined text-lg">build</span>Düzeltmeleri Uygula</button>
            <p class="text-xs text-gray-500">Düzeltmeden önce sunucuda otomatik yedek alınır (backend\\yedekler).</p>
        </div>` : ''}`;
}

async function runDbCheck(btn) {
    setButtonLoading(btn, true, 'Kontrol ediliyor...');
    try { renderDbFindings(await api.dbCheck()); }
    catch (err) { showToast(err.message, 'error'); }
    finally { setButtonLoading(btn, false); }
}

async function runDbFix(btn) {
    const dup = document.getElementById('fixDupProducts')?.checked || false;
    const empty = document.getElementById('fixEmptyShipments')?.checked || false;
    const copies = document.getElementById('fixCopies')?.checked || false;
    const extra = [copies ? 'fazla liste kopyaları silinecek' : null, dup ? 'tekrar eden ürünler birleştirilecek' : null,
                   empty ? 'boş gönderimler silinecek' : null].filter(Boolean);
    const ok = await confirmModal('Düzeltmeleri Uygula',
        `Önce otomatik yedek alınacak, sonra güvenli düzeltmeler uygulanacak${extra.length ? ' ve ' + extra.join(', ') : ''}. Devam edilsin mi?`,
        { confirmText: 'Uygula', danger: dup || empty || copies });
    if (!ok) return;
    setButtonLoading(btn, true, 'Uygulanıyor...');
    try {
        const r = await api.dbFix({ tekrar_urun: dup, bos_gonderim: empty, kopya_aktarim: copies });
        renderDbFindings(r.bulgular, r);
        showToast('Düzeltmeler uygulandı');
        await loadInitialData();
        refreshStatsBadge();
    } catch (err) { showToast(err.message, 'error'); setButtonLoading(btn, false); }
}
