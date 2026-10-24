/*
 * Deneyap Depo — ÇEVRİM İÇİ DENEME SÜRÜMÜ
 *
 * Bu dosya yalnızca Netlify'daki deneme sitesinde yüklenir (kurulu sistemde kullanılmaz).
 * Sunucuya istek göndermek yerine, örnek atölye verilerini (demo/demo-veri.json) tarayıcıda
 * sunar. Bu veriler `python demo/olustur.py` ile GERÇEK sunucu kodundan üretilir; bu yüzden
 * ekranlar kurulu sistemle aynıdır. Değişiklik yapan işlemler kaydedilmez.
 */
(function () {
    const GITHUB = 'https://github.com/gizembocek/depo-deneyap';
    const KAYIT_YOK = 'Bu bir deneme sürümüdür; değişiklikler kaydedilmez. Sistemi atölyenizin bilgisayarına kurarak tam olarak kullanabilirsiniz.';
    const DOSYA = {
        pdf: ['/demo/ornek_stok_raporu.pdf', 'deneyap_stok_raporu.pdf', 'application/pdf'],
        excel: ['/demo/ornek_stok_raporu.xlsx', 'deneyap_stok_raporu.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
        sablon: ['/demo/deneyap_urun_sablonu.xlsx', 'deneyap_urun_sablonu.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    };
    const DEMO_KULLANICI = { id: 1, email: 'demo@deneyap.org', full_name: 'Demo Yönetici', role: 'admin', is_active: true, warehouses: [] };

    let veriSozu = null;
    const veri = () => veriSozu || (veriSozu = fetch('/demo/demo-veri.json').then(r => {
        if (!r.ok) throw new Error('Örnek veriler yüklenemedi');
        return r.json();
    }));

    // Sunucudaki tr_fold ile aynı: "Işıklı Büyüteç" -> "isikli buyutec"
    const KATLA = { 'İ': 'i', 'I': 'i', 'ı': 'i', 'Ç': 'c', 'ç': 'c', 'Ğ': 'g', 'ğ': 'g', 'Ö': 'o', 'ö': 'o',
                    'Ş': 's', 'ş': 's', 'Ü': 'u', 'ü': 'u', 'Â': 'a', 'â': 'a', 'Î': 'i', 'î': 'i', 'Û': 'u', 'û': 'u' };
    const katla = s => String(s || '').replace(/[İIıÇçĞğÖöŞşÜüÂâÎîÛû]/g, ch => KATLA[ch]).toLowerCase().trim();
    const trKarsilastir = (a, b) => String(a || '').localeCompare(String(b || ''), 'tr');

    const json = (govde, durum = 200, basliklar = {}) =>
        new Response(JSON.stringify(govde), { status: durum, headers: { 'Content-Type': 'application/json', ...basliklar } });
    const hata = (durum, mesaj) => json({ detail: mesaj }, durum);

    async function dosya(tur) {
        const [yol, ad, tip] = DOSYA[tur];
        const r = await fetch(yol);
        if (!r.ok) return hata(404, 'Örnek dosya bulunamadı');
        return new Response(await r.blob(), { status: 200, headers: { 'Content-Type': tip, 'Content-Disposition': `attachment; filename="${ad}"` } });
    }

    function urunleriSuz(urunler, q) {
        let liste = urunler.slice();
        const ara = katla(q.get('search'));
        if (ara) liste = liste.filter(p => katla(p.name).includes(ara) || katla(p.description).includes(ara));
        const kategori = q.get('category');
        if (kategori && kategori !== 'Tümü') liste = liste.filter(p => p.category === kategori);
        if (q.get('status')) liste = liste.filter(p => p.status === q.get('status'));
        if (q.get('warehouse_id')) liste = liste.filter(p => p.warehouse_id === Number(q.get('warehouse_id')));
        if (q.get('course_id')) liste = liste.filter(p => (p.courses || []).some(c => c.id === Number(q.get('course_id'))));
        if (q.get('low_stock') === 'true') liste = liste.filter(p => p.current_stock <= p.critical_stock);
        return liste;
    }

    const SIRALA = {
        newest: (a, b) => b.id - a.id,
        oldest: (a, b) => a.id - b.id,
        name: (a, b) => trKarsilastir(a.name, b.name) || a.id - b.id,
        stock_asc: (a, b) => a.current_stock - b.current_stock || a.id - b.id,
        stock_desc: (a, b) => b.current_stock - a.current_stock || a.id - b.id,
    };

    async function yanitla(yontem, yol, q) {
        if (yontem === 'POST' && yol === '/api/auth/login') {
            const v = await veri();
            return json({ access_token: 'deneme', token_type: 'bearer', user: v.me, must_change_password: false });
        }
        if (yontem !== 'GET') return hata(403, KAYIT_YOK);

        const v = await veri();
        let m;
        if (yol === '/api/health') return json({ status: 'ok', database: true, version: 'deneme' });
        if (yol === '/api/auth/setup-status') return json(v.setup_status);
        if (yol === '/api/auth/me') return json(v.me);
        if (yol === '/api/auth/users') return json(v.users);
        if (yol === '/api/settings') return json(v.settings);
        if (yol === '/api/products/stats') return json(v.stats);
        if (yol === '/api/products/count') return json({ count: urunleriSuz(v.products, q).length });
        if (yol === '/api/products/import/template') return dosya('sablon');
        if (yol === '/api/products/' || yol === '/api/products') {
            const liste = urunleriSuz(v.products, q).sort(SIRALA[q.get('sort')] || SIRALA.newest);
            const sayfa = Math.max(1, Number(q.get('page') || 1));
            const adet = Math.min(200, Math.max(1, Number(q.get('per_page') || 50)));
            return json(liste.slice((sayfa - 1) * adet, sayfa * adet), 200,
                        { 'X-Total-Count': String(liste.length), 'X-Page': String(sayfa), 'X-Per-Page': String(adet) });
        }
        if ((m = yol.match(/^\/api\/products\/(\d+)\/logs$/))) return json(v.product_logs[m[1]] || []);
        if ((m = yol.match(/^\/api\/products\/(\d+)$/))) {
            const p = v.products.find(x => x.id === Number(m[1]));
            return p ? json(p) : hata(404, 'Ürün bulunamadı');
        }
        if (yol === '/api/warehouses/' || yol === '/api/warehouses') return json(v.warehouses);
        if ((m = yol.match(/^\/api\/warehouses\/(\d+)\/structure$/))) {
            return v.structures[m[1]] ? json(v.structures[m[1]]) : hata(404, 'Depo bulunamadı');
        }
        if (yol === '/api/courses/' || yol === '/api/courses') return json(v.courses);
        if (yol === '/api/shipments/' || yol === '/api/shipments') return json(v.shipments);
        if ((m = yol.match(/^\/api\/shipments\/(\d+)$/))) {
            return v.shipment_details[m[1]] ? json(v.shipment_details[m[1]]) : hata(404, 'İşlem bulunamadı');
        }
        if (yol === '/api/reports/logs') {
            let kayitlar = v.logs;
            ['product_id', 'user_id'].forEach(k => { if (q.get(k)) kayitlar = kayitlar.filter(l => l[k] === Number(q.get(k))); });
            if (q.get('action')) kayitlar = kayitlar.filter(l => l.action === q.get('action'));
            return json(kayitlar.slice(0, Number(q.get('limit') || 100)));
        }
        if (yol === '/api/reports/export/pdf') return dosya('pdf');
        if (yol === '/api/reports/export/excel') return dosya('excel');
        if (yol === '/api/admin/db-check') return json(v.db_check);
        if (yol === '/api/admin/backup') return hata(403, 'Deneme sürümünde yedek alınamaz. ' + KAYIT_YOK);
        return hata(404, 'Bu özellik deneme sürümünde yok');
    }

    // api.js'deki istemcinin sunucu bağlantısını tarayıcı içi yanıtlarla değiştir
    api._fetch = async function (url, options = {}) {
        const adres = new URL(url, window.location.origin);
        const yanit = await yanitla((options.method || 'GET').toUpperCase(), adres.pathname, adres.searchParams);
        if (!yanit.ok) {
            const govde = await yanit.clone().json().catch(() => ({}));
            throw new Error(govde.detail || `İşlem başarısız (hata ${yanit.status})`);
        }
        return yanit;
    };

    // Ziyaretçi doğrudan sisteme girsin (giriş ekranı açılırsa bilgiler hazır gelir)
    if (!api.isAuthenticated()) api.setAuth('deneme', DEMO_KULLANICI);

    function demoEtiketi() {
        if (document.getElementById('demoEtiketi')) return;
        const e = document.createElement('div');
        e.id = 'demoEtiketi';
        e.setAttribute('role', 'note');
        e.style.cssText = 'position:fixed;left:50%;bottom:12px;transform:translateX(-50%);z-index:89;max-width:calc(100% - 24px);'
            + 'background:rgba(250,204,21,.95);color:#1e293b;border-radius:999px;padding:7px 16px;font:500 12.5px Inter,system-ui,sans-serif;'
            + 'box-shadow:0 6px 20px rgba(0,0,0,.35);display:flex;gap:10px;align-items:center;flex-wrap:wrap;justify-content:center;text-align:center';
        e.innerHTML = '<style>@media (max-width:640px){#demoEtiketi .uzun{display:none}}</style>'
            + '<span><b>DENEME SÜRÜMÜ</b><span class="uzun"> · örnek atölye verileri · değişiklikler kaydedilmez</span></span>'
            + `<a href="${GITHUB}" target="_blank" rel="noopener" style="color:#1e3a8a;font-weight:700;text-decoration:underline">Atölyenize kurun →</a>`
            + '<button type="button" aria-label="Kapat" style="background:none;border:0;font-size:16px;line-height:1;cursor:pointer;color:#1e293b">×</button>';
        e.querySelector('button').onclick = () => e.remove();
        document.body.appendChild(e);
    }

    document.addEventListener('DOMContentLoaded', () => {
        // "Kaydedilmez" uyarısı hata (kırmızı) değil bilgi (sarı) olarak görünsün
        if (typeof window.showToast === 'function') {
            const asilToast = window.showToast;
            window.showToast = (mesaj, tur, ...kalan) =>
                asilToast(mesaj, String(mesaj).startsWith('Bu bir deneme sürümüdür') || String(mesaj).startsWith('Deneme sürümünde') ? 'warning' : tur, ...kalan);
        }
        demoEtiketi();
        const eposta = document.getElementById('loginEmail');
        const sifre = document.getElementById('loginPassword');
        if (eposta && sifre) { eposta.value = DEMO_KULLANICI.email; sifre.value = 'Deneme2026'; }
        const kart = document.getElementById('loginCard');
        if (kart && !document.getElementById('demoGirisNotu')) {
            const not = document.createElement('p');
            not.id = 'demoGirisNotu';
            not.style.cssText = 'margin-top:12px;font-size:12px;color:#facc15;text-align:center';
            not.textContent = 'Deneme sürümü: "Giriş Yap" düğmesine basmanız yeterli.';
            kart.appendChild(not);
        }
        document.title = 'Deneyap Depo — Deneme Sürümü';
    });
})();
