// ==================== REPORTS PAGE ====================
async function renderReportsPage() {
    const content = document.getElementById('pageContent');
    content.innerHTML = `
    <div class="animate-fade-in">
        <h1 class="text-2xl font-bold text-white mb-6">Raporlama</h1>
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            <!-- Export Cards -->
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
                    <select id="reportStatus" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                        <option value="">Tüm Durumlar</option>
                        <option value="Çalışan">Çalışan</option>
                        <option value="Bozuk / Kırık">Bozuk / Kırık</option>
                        <option value="Garantide">Garantide</option>
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

        <!-- Activity Logs -->
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
        container.innerHTML = `
        <div class="overflow-x-auto"><table class="w-full">
            <thead><tr class="text-xs text-gray-500 uppercase border-b border-slate-700">
                <th class="pb-3 text-left">Tarih</th><th class="pb-3 text-left">Kullanıcı</th><th class="pb-3 text-left">İşlem</th><th class="pb-3 text-left">Ürün</th><th class="pb-3 text-center">Değişiklik</th><th class="pb-3 text-left">Not</th>
            </tr></thead>
            <tbody>${logs.map(l => `
                <tr class="border-b border-slate-700/30 text-sm">
                    <td class="py-2.5 text-xs text-gray-500">${new Date(l.created_at).toLocaleString('tr-TR')}</td>
                    <td class="py-2.5 text-gray-300">${l.user_name || '-'}</td>
                    <td class="py-2.5"><span class="${actionColors[l.action] || 'text-gray-400'} text-xs font-medium">${actionLabels[l.action] || l.action}</span></td>
                    <td class="py-2.5 text-white font-medium cursor-pointer hover:text-deneyap-blue-400" onclick="showProductDetail(${l.product_id})">${l.product_name || '-'}</td>
                    <td class="py-2.5 text-center text-xs text-gray-400">${l.previous_value || ''} → ${l.new_value || ''}</td>
                    <td class="py-2.5 text-xs text-gray-500 truncate max-w-[200px]">${l.note || '-'}</td>
                </tr>`).join('')}</tbody>
        </table></div>`;
    } catch (err) { container.innerHTML = `<p class="text-red-400 text-center py-4">${err.message}</p>`; }
}

async function downloadExcel() {
    try {
        showToast('Excel raporu hazırlanıyor...', 'info');
        const params = { category: document.getElementById('reportCategory')?.value, warehouse_id: document.getElementById('reportWarehouse')?.value, status: document.getElementById('reportStatus')?.value };
        await api.exportExcel(params);
        showToast('Excel raporu indirildi');
    } catch (err) { showToast(err.message, 'error'); }
}

async function downloadPDF() {
    try {
        showToast('PDF raporu hazırlanıyor...', 'info');
        const params = { category: document.getElementById('reportCategory')?.value, warehouse_id: document.getElementById('reportWarehouse')?.value, status: document.getElementById('reportStatus')?.value };
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
    const fd = new FormData(form);
    try {
        await api.createCourse({ name: fd.get('name') });
        showToast('Ders başarıyla oluşturuldu');
        closeModal();
        renderCoursesPage();
        // Update global variables if needed
        if (typeof loadInitialData === 'function') loadInitialData();
    } catch (err) { showToast(err.message, 'error'); }
}

async function deleteCourse(id) {
    if (!confirm('Bu dersi silmek istediğinize emin misiniz?')) return;
    try {
        await api.deleteCourse(id);
        showToast('Ders silindi');
        renderCoursesPage();
        if (typeof loadInitialData === 'function') loadInitialData();
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
                    <span class="material-icons-outlined text-lg">add</span>Yeni Gönderim
                </button>
            </div>
            ${shipments.length === 0 ? '<div class="text-center py-16"><span class="material-icons-outlined text-gray-600 text-6xl mb-4">local_shipping</span><p class="text-gray-400 text-lg">Henüz gönderim yok</p></div>' : `
            <div class="space-y-4">${shipments.map(s => `
                <div class="glass rounded-2xl p-5 product-card">
                    <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
                        <div>
                            <h3 class="text-lg font-bold text-white">${s.name}</h3>
                            <div class="flex gap-3 mt-1 text-xs text-gray-400">
                                ${s.shipment_date ? `<span>Gönderim: ${new Date(s.shipment_date).toLocaleDateString('tr-TR')}</span>` : ''}
                                ${s.check_date ? `<span>Kontrol: ${new Date(s.check_date).toLocaleDateString('tr-TR')}</span>` : ''}
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="text-xs px-3 py-1 rounded-full ${s.status === 'checked' ? 'bg-green-500/10 text-green-400' : s.status === 'shipped' ? 'bg-blue-500/10 text-blue-400' : 'bg-yellow-500/10 text-yellow-400'}">${s.status === 'checked' ? 'Kontrol Edildi' : s.status === 'shipped' ? 'Gönderildi' : 'Bekliyor'}</span>
                            ${api.isAdmin() ? `<button onclick="deleteShipment(${s.id})" class="text-gray-400 hover:text-red-400 p-1"><span class="material-icons-outlined text-lg">delete</span></button>` : ''}
                        </div>
                    </div>
                    ${s.items.length > 0 ? `
                    <div class="overflow-x-auto"><table class="w-full text-sm">
                        <thead><tr class="text-xs text-gray-500 border-b border-slate-700"><th class="pb-2 text-left">Ürün</th><th class="pb-2 text-center">Beklenen</th><th class="pb-2 text-center">Gerçek</th><th class="pb-2 text-center">Durum</th></tr></thead>
                        <tbody>${s.items.map(i => `
                            <tr class="border-b border-slate-700/30"><td class="py-2 text-gray-300">${i.product_name || '-'}</td><td class="py-2 text-center">${i.expected_quantity}</td><td class="py-2 text-center">${i.actual_quantity ?? '-'}</td>
                            <td class="py-2 text-center"><span class="text-xs ${i.status === 'complete' ? 'text-green-400' : i.status === 'missing' ? 'text-red-400' : i.status === 'extra' ? 'text-blue-400' : 'text-gray-400'}">${i.status === 'complete' ? 'Tamam' : i.status === 'missing' ? 'Eksik' : i.status === 'extra' ? 'Fazla' : 'Bekliyor'}</span></td></tr>`).join('')}</tbody>
                    </table></div>` : '<p class="text-sm text-gray-500">Ürün yok</p>'}
                    ${s.notes ? `<p class="text-xs text-gray-500 mt-3">${s.notes}</p>` : ''}
                </div>`).join('')}</div>`}
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}

function showShipmentForm() {
    const formContent = `
    <form id="shipmentForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5">Gönderim Adı *</label>
            <input type="text" name="name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></div>
        <div class="grid grid-cols-2 gap-4">
            <div><label class="block text-xs text-gray-400 mb-1.5">Gönderim Tarihi</label><input type="date" name="shipment_date" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></div>
            <div><label class="block text-xs text-gray-400 mb-1.5">Kontrol Tarihi</label><input type="date" name="check_date" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Notlar</label><textarea name="notes" rows="2" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white"></textarea></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Ürünler</label>
            <div id="shipmentItems" class="space-y-2"></div>
            <button type="button" onclick="addShipmentItem()" class="mt-2 text-xs text-deneyap-blue-400 hover:text-deneyap-blue-300 flex items-center gap-1"><span class="material-icons-outlined text-sm">add</span>Ürün Ekle</button>
        </div>
    </form>`;
    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>
        <button onclick="submitShipmentForm()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Oluştur</button>`;
    showModal('Yeni Gönderim', formContent, footer);
}

function addShipmentItem() {
    const container = document.getElementById('shipmentItems');
    const idx = container.children.length;
    const div = document.createElement('div');
    div.className = 'flex gap-2';
    div.innerHTML = `
        <select name="product_${idx}" class="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white">
            <option value="">Ürün seçin</option>
            ${allProducts.map(p => `<option value="${p.id}">${p.name}</option>`).join('')}
        </select>
        <input type="number" name="qty_${idx}" min="1" value="1" class="w-20 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white text-center">
        <button type="button" onclick="this.parentElement.remove()" class="text-red-400 hover:text-red-300 p-1"><span class="material-icons-outlined text-sm">close</span></button>`;
    container.appendChild(div);
}

async function submitShipmentForm() {
    const form = document.getElementById('shipmentForm');
    const fd = new FormData(form);
    const items = [];
    const container = document.getElementById('shipmentItems');
    for (let i = 0; i < container.children.length; i++) {
        const pid = fd.get(`product_${i}`);
        const qty = fd.get(`qty_${i}`);
        if (pid) items.push({ product_id: parseInt(pid), expected_quantity: parseInt(qty) || 1 });
    }
    const data = {
        name: fd.get('name'),
        shipment_date: fd.get('shipment_date') ? new Date(fd.get('shipment_date')).toISOString() : null,
        check_date: fd.get('check_date') ? new Date(fd.get('check_date')).toISOString() : null,
        notes: fd.get('notes'),
        items
    };
    try { await api.createShipment(data); showToast('Gönderim oluşturuldu'); closeModal(); renderShipmentsPage(); } catch (err) { showToast(err.message, 'error'); }
}

async function deleteShipment(id) {
    if (!confirm('Bu gönderimi silmek istediğinize emin misiniz?')) return;
    try { await api.deleteShipment(id); showToast('Gönderim silindi'); renderShipmentsPage(); } catch (err) { showToast(err.message, 'error'); }
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
                        <tr class="border-b border-slate-700/30 hover:bg-slate-800/30">
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
                                <button onclick="toggleUserStatus(${u.id}, ${u.is_active})" class="text-gray-400 hover:text-${u.is_active ? 'red' : 'green'}-400 p-1.5 rounded-lg hover:bg-slate-800 transition-all"><span class="material-icons-outlined text-lg">${u.is_active ? 'block' : 'check_circle'}</span></button>
                            </div></td>
                        </tr>`).join('')}</tbody>
                </table></div>
            </div>
        </div>`;
    } catch (err) { content.innerHTML = `<div class="text-center py-20 text-red-400">${err.message}</div>`; }
}

async function toggleUserRole(userId, currentRole) {
    const newRole = currentRole === 'admin' ? 'user' : 'admin';
    if (!confirm(`Rol ${newRole === 'admin' ? 'Yönetici' : 'Kullanıcı'} olarak değiştirilsin mi?`)) return;
    try { await api.updateUser(userId, { role: newRole }); showToast('Rol güncellendi'); renderUsersPage(); } catch (err) { showToast(err.message, 'error'); }
}

async function toggleUserStatus(userId, isActive) {
    try { await api.updateUser(userId, { is_active: !isActive }); showToast('Durum güncellendi'); renderUsersPage(); } catch (err) { showToast(err.message, 'error'); }
}

async function showUserAccess(userId, userName) {
    const html = `<div class="space-y-3">
        <p class="text-sm text-gray-400 mb-4">Kullanıcının erişebileceği depoları seçin:</p>
        ${allWarehouses.map(w => `
        <label class="flex items-center justify-between p-3 bg-slate-800/50 rounded-xl cursor-pointer hover:bg-slate-800 transition-all">
            <div class="flex items-center gap-3"><span class="material-icons-outlined text-deneyap-blue-400">warehouse</span><span class="text-sm text-white">${w.name}</span></div>
            <input type="checkbox" data-wid="${w.id}" onchange="toggleWarehouseAccess(${userId}, ${w.id}, this.checked)" class="rounded border-slate-600 text-deneyap-blue-500 focus:ring-deneyap-blue-500">
        </label>`).join('')}
    </div>`;
    showModal(`${userName} - Depo Erişimi`, html);
    // Load current access
    try {
        const users = await api.getUsers();
        const user = users.find(u => u.id === userId);
        if (user) {
            user.warehouse_ids.forEach(wid => {
                const cb = document.querySelector(`input[data-wid="${wid}"]`);
                if (cb) cb.checked = true;
            });
        }
    } catch(e) {}
}

async function toggleWarehouseAccess(userId, warehouseId, grant) {
    try {
        if (grant) { await api.grantWarehouseAccess(userId, warehouseId); showToast('Erişim verildi'); }
        else { await api.revokeWarehouseAccess(userId, warehouseId); showToast('Erişim kaldırıldı'); }
    } catch (err) { showToast(err.message, 'error'); }
}

function showUserForm() {
    const formContent = `
    <form id="userForm" class="space-y-4">
        <div><label class="block text-xs text-gray-400 mb-1.5">Ad Soyad *</label>
            <input type="text" name="full_name" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">E-posta *</label>
            <input type="email" name="email" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500"></div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Şifre *</label>
            <div class="relative">
                <input type="password" name="password" required class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500 pr-10">
                <button type="button" onclick="togglePasswordVisibility('password', this)" class="material-icons-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 transition-colors cursor-pointer text-lg">visibility</button>
            </div>
        </div>
        <div><label class="block text-xs text-gray-400 mb-1.5">Kullanıcı Rolü</label>
            <select name="role" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500">
                <option value="user">Kullanıcı (Eğitmen / Görevli)</option>
                <option value="admin">Yönetici (Admin)</option>
            </select>
        </div>
    </form>`;
    const footer = `
        <button onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm transition-all text-medium">İptal</button>
        <button onclick="submitUserForm()" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">Kullanıcı Oluştur</button>`;
    showModal('Yeni Kullanıcı Ekle', formContent, footer);
}

async function submitUserForm() {
    const form = document.getElementById('userForm');
    if (!form.reportValidity()) return;
    const fd = new FormData(form);
    const data = {
        full_name: fd.get('full_name'),
        email: fd.get('email'),
        password: fd.get('password'),
        role: fd.get('role')
    };
    try {
        await api.registerUser(data);
        showToast('Kullanıcı başarıyla oluşturuldu.');
        closeModal();
        renderUsersPage();
    } catch (err) {
        showToast(err.message, 'error');
    }
}
