// ==================== UTILITY FUNCTIONS ====================
let currentPage = 'dashboard';
let allProducts = [];
let allWarehouses = [];
let allCourses = [];
let searchTimeout = null;

function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const colors = { success: 'bg-green-500', error: 'bg-red-500', warning: 'bg-yellow-500', info: 'bg-blue-500' };
    const icons = { success: 'check_circle', error: 'error', warning: 'warning', info: 'info' };
    const toast = document.createElement('div');
    toast.className = `toast ${colors[type]} text-white px-5 py-3 rounded-xl shadow-xl flex items-center gap-3 min-w-[280px] max-w-md`;
    toast.innerHTML = `<span class="material-icons-outlined text-xl">${icons[type]}</span><span class="text-sm font-medium">${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 0.3s'; setTimeout(() => toast.remove(), 300); }, 3000);
}

function showModal(title, content, footer = '') {
    const container = document.getElementById('modalContainer');
    container.innerHTML = `
        <div class="modal-backdrop fixed inset-0 z-[90]" onclick="closeModal()"></div>
        <div class="fixed inset-0 z-[91] flex items-center justify-center p-4 pointer-events-none">
            <div class="glass rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col animate-scale-in pointer-events-auto">
                <div class="flex items-center justify-between p-5 border-b border-slate-700/50">
                    <h3 class="text-lg font-bold text-white">${title}</h3>
                    <button onclick="closeModal()" class="text-gray-400 hover:text-white transition-colors"><span class="material-icons-outlined">close</span></button>
                </div>
                <div class="p-5 overflow-y-auto flex-1">${content}</div>
                ${footer ? `<div class="p-5 border-t border-slate-700/50 flex justify-end gap-3">${footer}</div>` : ''}
            </div>
        </div>`;
    container.classList.remove('hidden');
}

function closeModal() { document.getElementById('modalContainer').classList.add('hidden'); }

function showPromptModal(title, label, defaultValue, type, onSubmit, onCancel) {
    const content = `
        <div class="space-y-4 pt-2">
            <label class="block text-sm font-medium text-gray-300">${label}</label>
            <input type="${type}" id="promptInput" value="${defaultValue}" class="w-full bg-slate-800 border border-slate-700 rounded-xl px-4 py-3 text-white focus:border-deneyap-blue-500 focus:outline-none" />
        </div>
    `;
    const footer = `
        <button id="promptCancelBtn" class="bg-slate-700 hover:bg-slate-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all">İptal</button>
        <button id="promptSubmitBtn" class="bg-deneyap-blue-500 hover:bg-deneyap-blue-600 text-white px-5 py-2.5 rounded-xl text-sm font-medium transition-all shadow-lg hover:shadow-deneyap-blue-500/25">Onayla</button>
    `;
    
    showModal(title, content, footer);
    
    document.getElementById('promptCancelBtn').onclick = () => { closeModal(); if(onCancel) onCancel(); };
    document.getElementById('promptSubmitBtn').onclick = () => {
        const val = document.getElementById('promptInput').value;
        closeModal();
        onSubmit(val);
    };
    
    // allow enter key
    document.getElementById('promptInput').addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            document.getElementById('promptSubmitBtn').click();
        }
    });

    setTimeout(() => document.getElementById('promptInput').focus(), 100);
}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('-translate-x-full');
    overlay.classList.toggle('hidden');
}

function getStatusClass(status) {
    const map = { 'Çalışan': 'status-calisan', 'Bozuk / Kırık': 'status-bozuk', 'Garantide': 'status-garantide', 'Demirbaştan düşülecek': 'status-demirbas', 'Kırık ürün kutusunda': 'status-kirik' };
    return map[status] || 'status-calisan';
}

function togglePasswordVisibility(inputId, iconElement) {
    const input = document.getElementById(inputId) || document.querySelector(`[name="${inputId}"]`);
    if (input.type === 'password') {
        input.type = 'text';
        iconElement.textContent = 'visibility_off';
    } else {
        input.type = 'password';
        iconElement.textContent = 'visibility';
    }
}

function getCategoryIcon(cat) {
    const map = { 'Sarf Malzemesi': 'build', 'Genel / Dayanıklı Malzeme': 'devices', 'Elektronik Bileşen': 'memory' };
    return map[cat] || 'category';
}

// ==================== INIT & AUTH ====================
document.addEventListener('DOMContentLoaded', () => {
    if (api.isAuthenticated()) { showApp(); } else { showLogin(); }
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.getElementById('mobileMenuBtn').addEventListener('click', toggleSidebar);
    document.getElementById('globalSearch').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => { if (currentPage === 'products') loadProducts({ search: e.target.value }); else { navigateTo('products'); setTimeout(() => loadProducts({ search: e.target.value }), 100); } }, 300);
    });
});

async function handleLogin(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    const errorDiv = document.getElementById('loginError');
    const btn = document.getElementById('loginBtn');
    btn.disabled = true; btn.innerHTML = '<div class="spinner"></div>';
    try {
        const data = await api.login(email, password);
        api.setAuth(data.access_token, data.user);
        showApp();
        showToast('Giriş başarılı!');
    } catch (err) {
        errorDiv.textContent = err.message; errorDiv.classList.remove('hidden');
    } finally { btn.disabled = false; btn.innerHTML = '<span class="material-icons-outlined text-xl">login</span> Giriş Yap'; }
}

function logout() { api.clearAuth(); showLogin(); showToast('Çıkış yapıldı', 'info'); }
function showLogin() { document.getElementById('loginPage').classList.remove('hidden'); document.getElementById('mainApp').classList.add('hidden'); }

async function loadInitialData() {
    try { 
        allWarehouses = await api.getWarehouses(); 
        allCourses = await api.getCourses(); 
    } catch(e) { console.error("Veri yükleme hatası:", e); }
}

async function showApp() {
    document.getElementById('loginPage').classList.add('hidden');
    document.getElementById('mainApp').classList.remove('hidden');
    const user = api.user;
    if (user) {
        document.getElementById('userName').textContent = user.full_name;
        document.getElementById('userRole').textContent = user.role === 'admin' ? 'Yönetici' : 'Kullanıcı';
        document.getElementById('userAvatar').textContent = user.full_name.charAt(0).toUpperCase();
    }
    document.querySelectorAll('.admin-only').forEach(el => { el.style.display = api.isAdmin() ? '' : 'none'; });
    await loadInitialData();
    navigateTo('dashboard');
}

function navigateTo(page) {
    currentPage = page;
    document.querySelectorAll('.sidebar-link').forEach(l => l.classList.remove('active'));
    document.querySelector(`.sidebar-link[data-page="${page}"]`)?.classList.add('active');
    if (window.innerWidth < 1024) { document.getElementById('sidebar').classList.add('-translate-x-full'); document.getElementById('sidebarOverlay').classList.add('hidden'); }
    const content = document.getElementById('pageContent');
    content.innerHTML = '<div class="flex justify-center py-20"><div class="spinner"></div></div>';
    switch(page) {
        case 'dashboard': renderDashboard(); break;
        case 'products': renderProductsPage(); break;
        case 'warehouses': renderWarehousesPage(); break;
        case 'shipments': renderShipmentsPage(); break;
        case 'courses': renderCoursesPage(); break;
        case 'reports': renderReportsPage(); break;
        case 'users': renderUsersPage(); break;
    }
}
