// API yardımcı modülü: sunucu ile tüm iletişim buradan yapılır.
const API_BASE = '';

function buildQuery(params = {}) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
        if (val !== null && val !== undefined && val !== '' && val !== false) query.append(key, val);
    });
    const s = query.toString();
    return s ? `?${s}` : '';
}

class ApiClient {
    constructor() {
        this.token = null;
        this.user = null;
        try {
            this.token = localStorage.getItem('token');
            this.user = JSON.parse(localStorage.getItem('user') || 'null');
        } catch (e) { /* tarayıcı depolaması kapalı olabilir */ }
    }

    setAuth(token, user) {
        this.token = token;
        this.user = user;
        try {
            localStorage.setItem('token', token);
            localStorage.setItem('user', JSON.stringify(user));
        } catch (e) { /* yoksay */ }
    }

    clearAuth() {
        this.token = null;
        this.user = null;
        try {
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        } catch (e) { /* yoksay */ }
    }

    isAuthenticated() { return !!this.token; }
    isAdmin() { return this.user?.role === 'admin'; }

    async _fetch(url, options = {}) {
        const headers = { ...(options.headers || {}) };
        if (!(options.body instanceof FormData) && options.body !== undefined) headers['Content-Type'] = 'application/json';
        if (this.token) headers['Authorization'] = `Bearer ${this.token}`;
        let response;
        try {
            response = await fetch(`${API_BASE}${url}`, { ...options, headers });
        } catch (e) {
            throw new Error('Sunucuya bağlanılamadı');
        }
        if (response.status === 401 && this.token && !options.noAuthRedirect) {
            this.clearAuth();
            setTimeout(() => window.location.reload(), 800);
            throw new Error('Oturumunuz sona erdi, lütfen tekrar giriş yapın');
        }
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            let detail = error.detail;
            if (Array.isArray(detail)) detail = detail.map(d => d.msg).join(', ');
            throw new Error(detail || `İşlem başarısız (hata ${response.status})`);
        }
        return response;
    }

    async request(url, options = {}) {
        const response = await this._fetch(url, options);
        if (response.status === 204) return null;
        const text = await response.text();
        return text ? JSON.parse(text) : null;
    }

    // Dosya indirme (Excel, PDF, yedek): token adres çubuğunda görünmeden indirilir
    async download(url, fallbackName) {
        const response = await this._fetch(url);
        const blob = await response.blob();
        const disposition = response.headers.get('content-disposition') || '';
        const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
        const filename = match ? decodeURIComponent(match[1]) : fallbackName;
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        setTimeout(() => { URL.revokeObjectURL(link.href); link.remove(); }, 1000);
        return filename;
    }

    // --- Kimlik doğrulama ---
    setupStatus() { return this.request('/api/auth/setup-status', { noAuthRedirect: true }); }
    setup(data) { return this.request('/api/auth/setup', { method: 'POST', body: JSON.stringify(data), noAuthRedirect: true }); }
    login(email, password) {
        return this.request('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }), noAuthRedirect: true });
    }
    getMe() { return this.request('/api/auth/me'); }
    changePassword(current_password, new_password) {
        return this.request('/api/auth/change-password', { method: 'POST', body: JSON.stringify({ current_password, new_password }), noAuthRedirect: true });
    }

    // --- Kullanıcılar ---
    registerUser(data) { return this.request('/api/auth/register', { method: 'POST', body: JSON.stringify(data) }); }
    getUsers() { return this.request('/api/auth/users'); }
    updateUser(userId, data) { return this.request(`/api/auth/users/${userId}`, { method: 'PUT', body: JSON.stringify(data) }); }
    deleteUser(userId) { return this.request(`/api/auth/users/${userId}`, { method: 'DELETE' }); }
    resetUserPassword(userId, new_password) {
        return this.request(`/api/auth/users/${userId}/reset-password`, { method: 'POST', body: JSON.stringify({ new_password }) });
    }
    setUserWarehouses(userId, warehouse_ids) {
        return this.request(`/api/auth/users/${userId}/warehouses`, { method: 'PUT', body: JSON.stringify({ warehouse_ids }) });
    }

    // --- Ürünler ---
    getProducts(params = {}) { return this.request(`/api/products/${buildQuery(params)}`); }
    async getProductsPage(params = {}) {
        const response = await this._fetch(`/api/products/${buildQuery(params)}`);
        const items = await response.json();
        return { items, total: parseInt(response.headers.get('X-Total-Count') || items.length, 10) };
    }
    getProductCount(params = {}) { return this.request(`/api/products/count${buildQuery(params)}`); }
    getProductStats() { return this.request('/api/products/stats'); }
    getProduct(id) { return this.request(`/api/products/${id}`); }
    createProduct(data) { return this.request('/api/products/', { method: 'POST', body: JSON.stringify(data) }); }
    updateProduct(id, data) { return this.request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
    deleteProduct(id) { return this.request(`/api/products/${id}`, { method: 'DELETE' }); }
    deleteAllProducts(scope) {
        const params = scope === 'unassigned' ? { unassigned: true } : { warehouse_id: scope };
        return this.request(`/api/products/all${buildQuery(params)}`, { method: 'DELETE' });
    }
    updateStock(productId, data) { return this.request(`/api/products/${productId}/stock`, { method: 'POST', body: JSON.stringify(data) }); }
    getProductLogs(productId) { return this.request(`/api/products/${productId}/logs`); }
    importExcelProducts(file, warehouseId) {
        const formData = new FormData();
        formData.append('file', file);
        if (warehouseId) formData.append('warehouse_id', warehouseId);
        return this.request('/api/products/import/excel', { method: 'POST', body: formData });
    }
    downloadImportTemplate() { return this.download('/api/products/import/template', 'deneyap_urun_sablonu.xlsx'); }
    uploadImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.request('/api/products/upload-image', { method: 'POST', body: formData });
    }

    // --- Depolar ---
    getWarehouses() { return this.request('/api/warehouses/'); }
    createWarehouse(data) { return this.request('/api/warehouses/', { method: 'POST', body: JSON.stringify(data) }); }
    updateWarehouse(id, data) { return this.request(`/api/warehouses/${id}`, { method: 'PUT', body: JSON.stringify(data) }); }
    deleteWarehouse(id) { return this.request(`/api/warehouses/${id}`, { method: 'DELETE' }); }
    getWarehouseStructure(id) { return this.request(`/api/warehouses/${id}/structure`); }
    createCabinet(data) { return this.request('/api/warehouses/cabinets', { method: 'POST', body: JSON.stringify(data) }); }
    renameCabinet(id, name) { return this.request(`/api/warehouses/cabinets/${id}`, { method: 'PUT', body: JSON.stringify({ name }) }); }
    deleteCabinet(id) { return this.request(`/api/warehouses/cabinets/${id}`, { method: 'DELETE' }); }
    createShelf(data) { return this.request('/api/warehouses/shelves', { method: 'POST', body: JSON.stringify(data) }); }
    renameShelf(id, name) { return this.request(`/api/warehouses/shelves/${id}`, { method: 'PUT', body: JSON.stringify({ name }) }); }
    deleteShelf(id) { return this.request(`/api/warehouses/shelves/${id}`, { method: 'DELETE' }); }
    createCompartment(data) { return this.request('/api/warehouses/compartments', { method: 'POST', body: JSON.stringify(data) }); }
    renameCompartment(id, name) { return this.request(`/api/warehouses/compartments/${id}`, { method: 'PUT', body: JSON.stringify({ name }) }); }
    deleteCompartment(id) { return this.request(`/api/warehouses/compartments/${id}`, { method: 'DELETE' }); }

    // --- Dersler ---
    getCourses() { return this.request('/api/courses/'); }
    createCourse(data) { return this.request('/api/courses/', { method: 'POST', body: JSON.stringify(data) }); }
    renameCourse(id, name) { return this.request(`/api/courses/${id}`, { method: 'PUT', body: JSON.stringify({ name }) }); }
    deleteCourse(id) { return this.request(`/api/courses/${id}`, { method: 'DELETE' }); }

    // --- Gönderimler ---
    getShipments() { return this.request('/api/shipments/'); }
    getShipment(id) { return this.request(`/api/shipments/${id}`); }
    createShipment(data) { return this.request('/api/shipments/', { method: 'POST', body: JSON.stringify(data) }); }
    checkShipment(id, items) { return this.request(`/api/shipments/${id}/check`, { method: 'PUT', body: JSON.stringify(items) }); }
    deleteShipment(id, revertStock = true) {
        return this.request(`/api/shipments/${id}?revert_stock=${revertStock ? 'true' : 'false'}`, { method: 'DELETE' });
    }

    // --- Raporlar ---
    getLogs(params = {}) { return this.request(`/api/reports/logs${buildQuery(params)}`); }
    exportExcel(params = {}) { return this.download(`/api/reports/export/excel${buildQuery(params)}`, 'deneyap_stok_raporu.xlsx'); }
    exportPDF(params = {}) { return this.download(`/api/reports/export/pdf${buildQuery(params)}`, 'deneyap_stok_raporu.pdf'); }

    // --- Ayarlar / Yedek ---
    getSettings() { return this.request('/api/settings'); }
    updateSettings(data) { return this.request('/api/settings', { method: 'PUT', body: JSON.stringify(data) }); }
    downloadBackup() { return this.download('/api/admin/backup', 'deneyap_yedek.json'); }
    dbCheck() { return this.request('/api/admin/db-check'); }
    dbFix(options = {}) { return this.request('/api/admin/db-check/fix', { method: 'POST', body: JSON.stringify(options) }); }
}

const api = new ApiClient();
