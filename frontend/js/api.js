// API Helper Module
const API_BASE = '';

class ApiClient {
    constructor() {
        this.token = localStorage.getItem('token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    setAuth(token, user) {
        this.token = token;
        this.user = user;
        localStorage.setItem('token', token);
        localStorage.setItem('user', JSON.stringify(user));
    }

    clearAuth() {
        this.token = null;
        this.user = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }

    isAuthenticated() {
        return !!this.token;
    }

    isAdmin() {
        return this.user?.role === 'admin';
    }

    async request(url, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(`${API_BASE}${url}`, {
                ...options,
                headers
            });

            if (response.status === 401) {
                this.clearAuth();
                window.location.reload();
                throw new Error('Oturum süresi doldu');
            }

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Bir hata oluştu' }));
                throw new Error(error.detail || 'Bir hata oluştu');
            }

            // Handle downloads
            const contentType = response.headers.get('content-type');
            if (contentType && (contentType.includes('spreadsheet') || contentType.includes('pdf'))) {
                return response;
            }

            return await response.json();
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('Sunucuya bağlanılamadı');
            }
            throw error;
        }
    }

    // Auth
    async login(email, password) {
        // Don't use this.request() here — it intercepts 401 as "session expired"
        try {
            const response = await fetch(`${API_BASE}/api/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Bir hata oluştu' }));
                throw new Error(error.detail || 'Geçersiz e-posta veya şifre');
            }

            return await response.json();
        } catch (error) {
            if (error.message === 'Failed to fetch') {
                throw new Error('Sunucuya bağlanılamadı');
            }
            throw error;
        }
    }

    async getMe() {
        return this.request('/api/auth/me');
    }

    async registerUser(data) {
        return this.request('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getUsers() {
        return this.request('/api/auth/users');
    }

    async updateUser(userId, data) {
        return this.request(`/api/auth/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteUser(userId) {
        return this.request(`/api/auth/users/${userId}`, {
            method: 'DELETE'
        });
    }

    async grantWarehouseAccess(userId, warehouseId) {
        return this.request(`/api/auth/users/${userId}/warehouses/${warehouseId}`, {
            method: 'POST'
        });
    }

    async revokeWarehouseAccess(userId, warehouseId) {
        return this.request(`/api/auth/users/${userId}/warehouses/${warehouseId}`, {
            method: 'DELETE'
        });
    }

    // Products
    async getProducts(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') {
                query.append(key, val);
            }
        });
        return this.request(`/api/products/?${query.toString()}`);
    }

    async getProductCount(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') {
                query.append(key, val);
            }
        });
        return this.request(`/api/products/count?${query.toString()}`);
    }

    async getProductStats() {
        return this.request('/api/products/stats');
    }

    async getProduct(id) {
        return this.request(`/api/products/${id}`);
    }

    async createProduct(data) {
        return this.request('/api/products/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateProduct(id, data) {
        return this.request(`/api/products/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteProduct(id) {
        return this.request(`/api/products/${id}`, {
            method: 'DELETE'
        });
    }

    async updateStock(productId, data) {
        return this.request(`/api/products/${productId}/stock`, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async getProductLogs(productId) {
        return this.request(`/api/products/${productId}/logs`);
    }

    async importExcelProducts(file, warehouseId) {
        const formData = new FormData();
        formData.append('file', file);
        if (warehouseId) formData.append('warehouse_id', warehouseId);
        
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE}/api/products/import/excel`, {
            method: 'POST',
            headers,
            body: formData
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Bir hata oluştu' }));
            throw new Error(error.detail || 'Bir hata oluştu');
        }
        return await response.json();
    }

    async uploadImage(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        const headers = {};
        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${API_BASE}/api/products/upload-image`, {
            method: 'POST',
            headers,
            body: formData
        });

        if (!response.ok) {
            throw new Error('Görsel yüklenemedi');
        }

        return await response.json();
    }

    // Warehouses
    async getWarehouses() {
        return this.request('/api/warehouses/');
    }

    async createWarehouse(data) {
        return this.request('/api/warehouses/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async updateWarehouse(id, data) {
        return this.request(`/api/warehouses/${id}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async deleteWarehouse(id) {
        return this.request(`/api/warehouses/${id}`, {
            method: 'DELETE'
        });
    }

    async getWarehouseStructure(id) {
        return this.request(`/api/warehouses/${id}/structure`);
    }

    async createCabinet(data) {
        return this.request('/api/warehouses/cabinets', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async deleteCabinet(id) {
        return this.request(`/api/warehouses/cabinets/${id}`, {
            method: 'DELETE'
        });
    }

    async createShelf(data) {
        return this.request('/api/warehouses/shelves', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async deleteShelf(id) {
        return this.request(`/api/warehouses/shelves/${id}`, {
            method: 'DELETE'
        });
    }

    async createCompartment(data) {
        return this.request('/api/warehouses/compartments', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async deleteCompartment(id) {
        return this.request(`/api/warehouses/compartments/${id}`, {
            method: 'DELETE'
        });
    }

    // Courses
    async getCourses() {
        return this.request('/api/courses/');
    }

    async createCourse(data) {
        return this.request('/api/courses/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async deleteCourse(id) {
        return this.request(`/api/courses/${id}`, {
            method: 'DELETE'
        });
    }

    // Shipments
    async getShipments() {
        return this.request('/api/shipments/');
    }

    async createShipment(data) {
        return this.request('/api/shipments/', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async checkShipment(id, items) {
        return this.request(`/api/shipments/${id}/check`, {
            method: 'PUT',
            body: JSON.stringify(items)
        });
    }

    async deleteShipment(id) {
        return this.request(`/api/shipments/${id}`, {
            method: 'DELETE'
        });
    }

    // Reports
    async getLogs(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') {
                query.append(key, val);
            }
        });
        return this.request(`/api/reports/logs?${query.toString()}`);
    }

    async exportExcel(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') {
                query.append(key, val);
            }
        });
        
        query.append('token', this.token);
        const url = `${API_BASE}/api/reports/export/excel?${query.toString()}`;
        
        // Native browser download bypasses Blob bugs and uses the filename provided by the server's Content-Disposition header.
        window.location.href = url;
        
        // Return a dummy promise resolving after a short delay since it's a direct navigation
        return new Promise(resolve => setTimeout(resolve, 500));
    }

    async exportPDF(params = {}) {
        const query = new URLSearchParams();
        Object.entries(params).forEach(([key, val]) => {
            if (val !== null && val !== undefined && val !== '') {
                query.append(key, val);
            }
        });
        
        query.append('token', this.token);
        const url = `${API_BASE}/api/reports/export/pdf?${query.toString()}`;
        
        window.location.href = url;
        
        return new Promise(resolve => setTimeout(resolve, 500));
    }
}

const api = new ApiClient();
