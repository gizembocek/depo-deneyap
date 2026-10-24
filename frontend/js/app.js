// ==================== GENEL DURUM ====================
let currentPage = 'dashboard';
let allProducts = [];
let allWarehouses = [];
let allCourses = [];
let appSettings = {};
let searchTimeout = null;

const PAGES = ['dashboard', 'products', 'warehouses', 'shipments', 'courses', 'reports', 'users', 'settings'];
const CATEGORIES = ['Sarf Malzemesi', 'Genel / Dayanıklı Malzeme', 'Elektronik Bileşen'];
const STATUSES = ['Çalışan', 'Bozuk / Kırık', 'Garantide', 'Demirbaştan düşülecek', 'Kırık ürün kutusunda'];
const ACTION_LABELS = { add: 'Stok Ekleme', remove: 'Stok Çıkarma', set: 'Stok Ayarlama', create: 'Ürün Oluşturma', status_change: 'Durum Değişikliği' };
const ACTION_COLORS = { add: 'text-green-400', remove: 'text-red-400', set: 'text-blue-400', create: 'text-purple-400', status_change: 'text-yellow-400' };

// ==================== GÜVENLİK: HTML KAÇIŞI ====================
// Kullanıcının girdiği her metin (ürün adı, not, depo adı...) ekrana basılmadan önce
// bu fonksiyondan geçirilir. Böylece "<script>" gibi içerikler kod olarak çalışmaz.
function esc(value) {
    if (value === null || value === undefined) return '';
    return String(value)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;')
        .replace(/`/g, '&#96;');
}

function fmtDateTime(iso) {
    if (!iso) return '-';
    // Zaman dilimi belirtilmemiş tarihler sunucuda UTC olarak tutulur
    const s = /[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z';
    const d = new Date(s);
    return isNaN(d) ? '-' : d.toLocaleString('tr-TR', { dateStyle: 'short', timeStyle: 'short' });
}

function fmtDate(iso) {
    if (!iso) return '-';
    const s = /[zZ]|[+-]\d\d:\d\d$/.test(iso) ? iso : iso + 'Z';
    const d = new Date(s);
    return isNaN(d) ? '-' : d.toLocaleDateString('tr-TR');
}

function fmtNumber(n) {
    return (n ?? 0).toLocaleString('tr-TR');
}

// ==================== BİLDİRİM VE PENCERELER ====================
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const colors = { success: 'bg-green-600', error: 'bg-red-600', warning: 'bg-yellow-600', info: 'bg-blue-600' };
    const icons = { success: 'check_circle', error: 'error', warning: 'warning', info: 'info' };
    const toast = document.createElement('div');
    toast.className = `toast ${colors[type] || colors.info} text-white px-5 py-3 rounded-xl shadow-xl flex items-center gap-3 min-w-[280px] max-w-md`;
    toast.setAttribute('role', type === 'error' ? 'alert' : 'status');
    const icon = document.createElement('span');
    icon.className = 'material-icons-outlined text-xl';
    icon.textContent = icons[type] || icons.info;
    const text = document.createElement('span');
    text.className = 'text-sm font-medium';
    text.textContent = message; // textContent: HTML olarak yorumlanmaz
    toast.append(icon, text);
    container.appendChild(toast);
    const duration = type === 'error' ? 6000 : 3500;
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, duration);
}

let modalOnClose = null;

/**
 * Pencere açılınca bir alana odaklanır. Kısa bekleme sırasında kullanıcı başka bir alana
 * geçip yazmaya başladıysa odağı geri ALMAZ (aksi halde yazılanlar yanlış alana giderdi).
 */
function focusSoon(getEl, { select = false, delay = 50 } = {}) {
    const before = document.activeElement;
    setTimeout(() => {
        const now = document.activeElement;
        if (now && now !== before && now !== document.body && now.matches?.('input, select, textarea')) return;
        const el = typeof getEl === 'function' ? getEl() : getEl;
        if (!el || !el.isConnected) return;
        el.focus();
        if (select) el.select?.();
    }, delay);
}

function showModal(title, content, footer = '', options = {}) {
    const container = document.getElementById('modalContainer');
    const width = options.size === 'lg' ? 'max-w-4xl' : options.size === 'sm' ? 'max-w-md' : 'max-w-2xl';
    modalOnClose = options.onClose || null;
    container.innerHTML = `
        <div class="modal-backdrop fixed inset-0 z-[90]" data-close-modal></div>
        <div class="fixed inset-0 z-[91] flex items-center justify-center p-4 pointer-events-none">
            <div class="glass rounded-2xl shadow-2xl w-full ${width} max-h-[90vh] flex flex-col animate-scale-in pointer-events-auto" role="dialog" aria-modal="true" aria-labelledby="modalTitle">
                <div class="flex items-center justify-between p-5 border-b border-slate-700/50">
                    <h3 id="modalTitle" class="text-lg font-bold text-white pr-4">${esc(title)}</h3>
                    <button type="button" data-close-modal class="text-gray-400 hover:text-white transition-colors" aria-label="Kapat"><span class="material-icons-outlined">close</span></button>
                </div>
                <div class="p-5 overflow-y-auto flex-1" id="modalBody">${content}</div>
                ${footer ? `<div class="p-5 border-t border-slate-700/50 flex flex-wrap justify-end gap-3" id="modalFooter">${footer}</div>` : ''}
            </div>
        </div>`;
    container.classList.remove('hidden');
    container.querySelectorAll('[data-close-modal]').forEach(el => el.addEventListener('click', () => closeModal()));
    focusSoon(() => container.querySelector('[autofocus]'));
}

function closeModal(runCallback = true) {
    const container = document.getElementById('modalContainer');
    container.classList.add('hidden');
    container.innerHTML = '';
    const cb = modalOnClose;
    modalOnClose = null;
    if (runCallback && cb) cb();
}

/**
 * Tarayıcının confirm() penceresi yerine kullanılan onay penceresi.
 * Sonuç: Promise<false | { checked: boolean }>
 */
function confirmModal(title, message, { confirmText = 'Onayla', danger = false, checkbox = null, requireText = null, onCancel = null } = {}) {
    return new Promise(resolve => {
        const content = `
            <div class="space-y-4">
                <div class="flex items-start gap-3">
                    <span class="material-icons-outlined ${danger ? 'text-red-400' : 'text-deneyap-yellow-400'} text-3xl">${danger ? 'warning' : 'help_outline'}</span>
                    <p class="text-sm text-gray-300 leading-relaxed pt-1">${esc(message)}</p>
                </div>
                ${checkbox ? `<label class="flex items-center gap-2 text-sm text-gray-300 bg-slate-800/60 p-3 rounded-xl cursor-pointer">
                    <input type="checkbox" id="confirmCheckbox" ${checkbox.checked ? 'checked' : ''} class="rounded border-slate-600">${esc(checkbox.label)}</label>` : ''}
                ${requireText ? `<div><label class="block text-xs text-gray-400 mb-1.5">Onaylamak için <b class="text-red-400">${esc(requireText)}</b> yazın:</label>
                    <input type="text" id="confirmText" autocomplete="off" autofocus class="w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-red-500"></div>` : ''}
            </div>`;
        const footer = `
            <button type="button" id="confirmCancel" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Vazgeç</button>
            <button type="button" id="confirmOk" class="${danger ? 'bg-red-600 hover:bg-red-700' : 'bg-deneyap-blue-500 hover:bg-deneyap-blue-600'} text-white px-5 py-2.5 rounded-xl text-sm font-medium">${esc(confirmText)}</button>`;
        let settled = false;
        const finish = (value) => { if (!settled) { settled = true; resolve(value); } };
        showModal(title, content, footer, { size: 'sm', onClose: () => { finish(false); if (onCancel) onCancel(); } });
        document.getElementById('confirmCancel').onclick = () => closeModal();
        document.getElementById('confirmOk').onclick = () => {
            if (requireText && document.getElementById('confirmText').value.trim().toLocaleUpperCase('tr-TR') !== requireText.toLocaleUpperCase('tr-TR')) {
                showToast(`Onaylamak için "${requireText}" yazın`, 'warning');
                return;
            }
            const checked = !!document.getElementById('confirmCheckbox')?.checked;
            finish({ checked });
            closeModal(false);
        };
        if (!requireText) focusSoon(() => document.getElementById('confirmOk'));
    });
}

function showPromptModal(title, label, defaultValue, type, onSubmit, onCancel, extraHtml = '') {
    const content = `
        <form id="promptForm" class="space-y-4 pt-2">
            <label class="block text-sm font-medium text-gray-300" for="promptInput">${esc(label)}</label>
            <input type="${type === 'number' ? 'number' : 'text'}" id="promptInput" value="${esc(defaultValue)}" ${type === 'number' ? 'min="0" inputmode="numeric"' : 'maxlength="255"'} autofocus
                class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:border-deneyap-blue-500 focus:outline-none" />
            ${extraHtml}
        </form>`;
    const footer = `
        <button type="button" id="promptCancelBtn" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">İptal</button>
        <button type="submit" form="promptForm" id="promptSubmitBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Onayla</button>`;
    showModal(title, content, footer, { size: 'sm', onClose: onCancel });
    document.getElementById('promptCancelBtn').onclick = () => closeModal();
    document.getElementById('promptForm').onsubmit = (e) => {
        e.preventDefault();
        const val = document.getElementById('promptInput').value;
        const extra = {};
        document.querySelectorAll('#promptForm [data-extra]').forEach(el => { extra[el.dataset.extra] = el.value; });
        closeModal(false);
        onSubmit(val, extra);
    };
    focusSoon(() => document.getElementById('promptInput'), { select: true, delay: 60 });
}

function setButtonLoading(btn, loading, text = 'Kaydediliyor...') {
    if (!btn) return;
    if (loading) {
        btn.dataset.originalHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner spinner-sm"></span>${esc(text)}`;
    } else {
        btn.disabled = false;
        if (btn.dataset.originalHtml) btn.innerHTML = btn.dataset.originalHtml;
    }
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('-translate-x-full');
    document.getElementById('sidebarOverlay').classList.toggle('hidden');
}

function getStatusClass(status) {
    const map = { 'Çalışan': 'status-calisan', 'Bozuk / Kırık': 'status-bozuk', 'Garantide': 'status-garantide', 'Demirbaştan düşülecek': 'status-demirbas', 'Kırık ürün kutusunda': 'status-kirik' };
    return map[status] || 'status-calisan';
}

function getCategoryIcon(cat) {
    const map = { 'Sarf Malzemesi': 'build', 'Genel / Dayanıklı Malzeme': 'devices', 'Elektronik Bileşen': 'memory' };
    return map[cat] || 'category';
}

function togglePasswordVisibility(inputId, iconElement) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    iconElement.textContent = show ? 'visibility_off' : 'visibility';
}

const WEAK_PASSWORDS = ['admin123', 'user123', '123456', '12345678', 'password', 'parola', 'deneyap123'];

function passwordProblem(pw) {
    if (!pw || pw.length < 8) return 'Şifre en az 8 karakter olmalıdır';
    if (!/[A-ZÇĞİÖŞÜ]/.test(pw)) return 'Şifre en az bir büyük harf içermelidir';
    if (!/[0-9]/.test(pw)) return 'Şifre en az bir rakam içermelidir';
    return null;
}

function applyRoleVisibility(root = document) {
    root.querySelectorAll('.admin-only').forEach(el => { el.style.display = api.isAdmin() ? '' : 'none'; });
}

function inputClass(extra = '') {
    return `w-full bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 text-sm text-white focus:outline-none focus:border-deneyap-blue-500 ${extra}`;
}

// ==================== BAŞLANGIÇ, GİRİŞ VE İLK KURULUM ====================
document.addEventListener('DOMContentLoaded', async () => {
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('setupForm').addEventListener('submit', handleSetup);
    document.getElementById('mobileMenuBtn').addEventListener('click', toggleSidebar);
    document.getElementById('globalSearch').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            productFilters.search = e.target.value.trim();
            productFilters.page = 1;
            if (currentPage === 'products') loadProducts();
            else navigateTo('products');
        }, 300);
    });
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !document.getElementById('modalContainer').classList.contains('hidden')) closeModal();
    });
    window.addEventListener('hashchange', () => {
        const page = location.hash.replace('#/', '');
        if (api.isAuthenticated() && PAGES.includes(page) && page !== currentPage) navigateTo(page, false);
    });

    if (api.isAuthenticated()) {
        try {
            const me = await api.getMe();
            api.setAuth(api.token, me);
            showApp();
        } catch (e) {
            // 401 ise api.request oturumu temizleyip sayfayı yeniler
            if (e.message === 'Sunucuya bağlanılamadı') showLogin(e.message);
        }
    } else {
        showLogin();
    }
});

async function showLogin(errorMessage) {
    document.getElementById('mainApp').classList.add('hidden');
    document.getElementById('loginPage').classList.remove('hidden');
    try {
        const status = await api.setupStatus();
        const name = status.atolye_adi;
        document.getElementById('loginSubtitle').textContent = name ? name : 'Atölye stok takip sistemi';
        document.getElementById('setupCard').classList.toggle('hidden', !status.needs_setup);
        document.getElementById('loginCard').classList.toggle('hidden', status.needs_setup);
        const old = status.tasinmamis_veri;
        document.getElementById('setupMigrationWarning').classList.toggle('hidden', !old);
        if (old) {
            document.getElementById('setupMigrationText').textContent =
                `Bu veritabanı boş, ancak bilgisayardaki eski veritabanı dosyasında (${old.dosya}) ${fmtNumber(old.urun)} ürün ve ` +
                `${fmtNumber(old.kullanici)} kullanıcı var. Yeni kurulum yapmayın: siyah sunucu penceresini kapatıp proje klasöründeki ` +
                `SQL_Server_Kurulum.bat dosyasını çalıştırın, verileriniz SQL Server'a taşınır.`;
        }
    } catch (e) {
        const err = document.getElementById('loginError');
        err.textContent = errorMessage || e.message;
        err.classList.remove('hidden');
    }
}

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    const btn = document.getElementById('loginBtn');
    errorDiv.classList.add('hidden');
    setButtonLoading(btn, true, 'Giriş yapılıyor...');
    try {
        const data = await api.login(email, password);
        api.setAuth(data.access_token, data.user);
        document.getElementById('loginPassword').value = '';
        await showApp();
        if (data.must_change_password) {
            showChangePasswordModal({ forced: true, currentPassword: password });
        } else {
            showToast('Giriş başarılı!');
        }
    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.classList.remove('hidden');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function handleSetup(e) {
    e.preventDefault();
    const form = e.target;
    const fd = new FormData(form);
    const errorDiv = document.getElementById('setupError');
    errorDiv.classList.add('hidden');
    const password = fd.get('password');
    const problem = passwordProblem(password);
    if (problem) { errorDiv.textContent = problem; errorDiv.classList.remove('hidden'); return; }
    if (password !== fd.get('password2')) { errorDiv.textContent = 'Şifreler aynı değil'; errorDiv.classList.remove('hidden'); return; }
    const btn = document.getElementById('setupBtn');
    setButtonLoading(btn, true, 'Kuruluyor...');
    try {
        const data = await api.setup({
            atolye_adi: fd.get('atolye_adi'), il: fd.get('il'), full_name: fd.get('full_name'),
            email: fd.get('email'), password, standart_dersler: fd.get('standart_dersler') === 'on',
        });
        api.setAuth(data.access_token, data.user);
        showApp();
        showToast('Kurulum tamamlandı. Hoş geldiniz!');
    } catch (err) {
        errorDiv.textContent = err.message;
        errorDiv.classList.remove('hidden');
    } finally {
        setButtonLoading(btn, false);
    }
}

function logout() {
    api.clearAuth();
    allProducts = []; allWarehouses = []; allCourses = [];
    history.replaceState(null, '', location.pathname);
    showLogin();
    showToast('Çıkış yapıldı', 'info');
}

async function loadInitialData() {
    try {
        [allWarehouses, allCourses, appSettings] = await Promise.all([api.getWarehouses(), api.getCourses(), api.getSettings()]);
    } catch (e) { console.error('Veri yükleme hatası:', e); }
    const name = appSettings?.atolye_adi || 'Deneyap Atölyesi';
    const sidebarName = document.getElementById('sidebarAtolye');
    sidebarName.textContent = name;
    sidebarName.title = name;
    document.title = `${name} - Depo Yönetimi`;
    document.getElementById('appVersion').textContent = `Depo Yönetimi v${appSettings?.version || '2'}`;
}

async function showApp() {
    document.getElementById('loginPage').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');
    const user = api.user;
    if (user) {
        document.getElementById('userName').textContent = user.full_name;
        document.getElementById('userRole').textContent = user.role === 'admin' ? 'Yönetici' : 'Kullanıcı';
        document.getElementById('userAvatar').textContent = (user.full_name || '?').charAt(0).toLocaleUpperCase('tr-TR');
    }
    applyRoleVisibility();
    await loadInitialData();
    const page = location.hash.replace('#/', '');
    navigateTo(PAGES.includes(page) ? page : 'dashboard');
}

function navigateTo(page, updateHash = true) {
    if (!PAGES.includes(page)) page = 'dashboard';
    if ((page === 'users' || page === 'settings') && !api.isAdmin()) page = 'dashboard';
    if (page !== 'products' && productFilters.search) {
        // Arama kutusu ürünlere aittir; başka sayfaya geçince temizlenir
        productFilters.search = '';
        document.getElementById('globalSearch').value = '';
    }
    currentPage = page;
    if (updateHash && location.hash !== `#/${page}`) history.pushState(null, '', `#/${page}`);
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.toggle('active', l.dataset.page === page));
    if (window.innerWidth < 1024) {
        document.getElementById('sidebar').classList.add('-translate-x-full');
        document.getElementById('sidebarOverlay').classList.add('hidden');
    }
    const content = document.getElementById('pageContent');
    content.innerHTML = '<div class="flex justify-center py-20"><div class="spinner"></div></div>';
    window.scrollTo(0, 0);
    switch (page) {
        case 'dashboard': renderDashboard(); break;
        case 'products': renderProductsPage(); break;
        case 'warehouses': renderWarehousesPage(); break;
        case 'shipments': renderShipmentsPage(); break;
        case 'courses': renderCoursesPage(); break;
        case 'reports': renderReportsPage(); break;
        case 'users': renderUsersPage(); break;
        case 'settings': renderSettingsPage(); break;
    }
}

// ==================== ŞİFRE DEĞİŞTİRME ====================
function showChangePasswordModal({ forced = false, currentPassword = '' } = {}) {
    const field = (id, label) => `
        <div><label class="block text-xs text-gray-400 mb-1.5" for="${id}">${label}</label>
            <div class="relative"><input type="password" id="${id}" required autocomplete="${id === 'cpCurrent' ? 'current-password' : 'new-password'}" class="${inputClass('pr-11')}">
            <button type="button" onclick="togglePasswordVisibility('${id}', this)" class="material-icons-outlined absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-lg" aria-label="Şifreyi göster">visibility</button></div></div>`;
    const content = `
        <form id="changePasswordForm" class="space-y-4">
            ${forced ? `<div class="bg-red-500/10 border border-red-500/30 text-red-300 text-sm p-3 rounded-xl flex gap-2">
                <span class="material-icons-outlined">gpp_maybe</span>
                <span>Şifreniz çok basit veya varsayılan bir şifre. Hesabınızın güvenliği için devam etmeden önce yeni bir şifre belirleyin.</span></div>` : ''}
            ${field('cpCurrent', 'Mevcut şifre')}
            ${field('cpNew', 'Yeni şifre')}
            ${field('cpNew2', 'Yeni şifre (tekrar)')}
            <p class="text-xs text-gray-500">En az 8 karakter, en az bir büyük harf ve bir rakam.</p>
        </form>`;
    const footer = `
        ${forced ? `<button type="button" onclick="closeModal(false); logout()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">Çıkış Yap</button>`
                 : `<button type="button" onclick="closeModal()" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm">İptal</button>`}
        <button type="submit" form="changePasswordForm" id="cpBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium">Şifreyi Değiştir</button>`;
    showModal(forced ? 'Yeni Şifre Belirleyin' : 'Şifremi Değiştir', content, footer,
        { size: 'sm', onClose: forced ? () => showChangePasswordModal({ forced, currentPassword }) : null });
    if (forced && currentPassword) document.getElementById('cpCurrent').value = currentPassword;
    if (forced) document.querySelectorAll('#modalContainer [data-close-modal]').forEach(el => el.replaceWith(el.cloneNode(true)));
    document.getElementById('changePasswordForm').onsubmit = async (e) => {
        e.preventDefault();
        const current = document.getElementById('cpCurrent').value;
        const next = document.getElementById('cpNew').value;
        const problem = passwordProblem(next) || (WEAK_PASSWORDS.includes(next.toLowerCase()) ? 'Bu şifre çok yaygın, başka bir şifre seçin' : null);
        if (problem) return showToast(problem, 'warning');
        if (next !== document.getElementById('cpNew2').value) return showToast('Yeni şifreler aynı değil', 'warning');
        const btn = document.getElementById('cpBtn');
        setButtonLoading(btn, true);
        try {
            const result = await api.changePassword(current, next);
            api.setAuth(result.access_token, api.user);
            closeModal(false);
            showToast('Şifreniz değiştirildi');
        } catch (err) {
            showToast(err.message, 'error');
            setButtonLoading(btn, false);
        }
    };
}
