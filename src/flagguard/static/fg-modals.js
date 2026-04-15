(function(){
    // ═══════════════════════════════════════════════════════════════════
    // FlagGuard — Cookie Consent + Legal Document Modal System
    // This file is served by FastAPI and injected via middleware.
    // It creates overlay elements directly on document.body,
    // completely bypassing Gradio's DOMPurify sanitization.
    // ═══════════════════════════════════════════════════════════════════

    var LEGAL_TITLES = {
        privacy: 'Privacy Policy',
        terms: 'Terms of Service',
        aup: 'Acceptable Use Policy',
        accessibility: 'Accessibility Statement',
        ai: 'AI Transparency Statement',
        data: 'Data Inventory & Classification'
    };

    // ── Create overlay elements ─────────────────────────────────────
    function createOverlays() {
        if (document.getElementById('fg-cookie-overlay')) return; // already created

        // COOKIE CONSENT OVERLAY
        var cookie = document.createElement('div');
        cookie.id = 'fg-cookie-overlay';
        cookie.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:2147483647;background:rgba(0,0,0,0.75);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);';
        cookie.innerHTML =
            '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:min(90vw,500px);background:#1a1a2e;border:1px solid rgba(212,175,55,0.2);border-radius:16px;padding:36px 32px;box-shadow:0 25px 80px rgba(0,0,0,0.6);font-family:Inter,sans-serif;color:#e2e8f0;text-align:center;">' +
            '<div style="font-size:2.2rem;margin-bottom:14px;">&#127850;</div>' +
            '<h2 style="font-family:Outfit,sans-serif;color:#f59e0b;margin:0 0 10px;font-size:1.3rem;font-weight:700;">We value your privacy</h2>' +
            '<p style="color:#94a3b8;font-size:0.88rem;line-height:1.6;margin:0 0 24px;">We use cookies for platform security, session management, and telemetry analytics.<br><small>View our <a href="#" data-legal="privacy" style="color:#d4af37;">Privacy Policy</a> for details.</small></p>' +
            '<div style="display:flex;gap:10px;justify-content:center;flex-wrap:wrap;">' +
            '<button data-consent="accepted" style="padding:10px 22px;border-radius:10px;border:1px solid rgba(48,209,88,0.4);background:rgba(48,209,88,0.12);color:#30d158;font-weight:600;font-family:Outfit,sans-serif;cursor:pointer;font-size:0.85rem;transition:all 0.2s;">&#10003; Accept All</button>' +
            '<button data-consent="essential" style="padding:10px 22px;border-radius:10px;border:1px solid rgba(212,175,55,0.3);background:rgba(212,175,55,0.08);color:#d4af37;font-weight:600;font-family:Outfit,sans-serif;cursor:pointer;font-size:0.85rem;transition:all 0.2s;">&#9881; Essential Only</button>' +
            '<button data-consent="rejected" style="padding:10px 22px;border-radius:10px;border:1px solid rgba(239,68,68,0.3);background:rgba(239,68,68,0.08);color:#ef4444;font-weight:600;font-family:Outfit,sans-serif;cursor:pointer;font-size:0.85rem;transition:all 0.2s;">&#10005; Decline All</button>' +
            '</div></div>';
        document.body.appendChild(cookie);

        // LEGAL DOCUMENT READER OVERLAY
        var legal = document.createElement('div');
        legal.id = 'fg-legal-overlay';
        legal.style.cssText = 'display:none;position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:2147483646;background:rgba(0,0,0,0.8);backdrop-filter:blur(8px);-webkit-backdrop-filter:blur(8px);';
        legal.innerHTML =
            '<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:min(92vw,900px);height:min(85vh,700px);background:#1a1a2e;border:1px solid rgba(212,175,55,0.15);border-radius:16px;box-shadow:0 30px 100px rgba(0,0,0,0.7);font-family:Inter,sans-serif;color:#e2e8f0;display:flex;flex-direction:column;overflow:hidden;">' +
            '<div style="display:flex;justify-content:space-between;align-items:center;padding:20px 28px;border-bottom:1px solid rgba(212,175,55,0.1);flex-shrink:0;">' +
            '<h2 id="fg-legal-title" style="margin:0;font-family:Outfit,sans-serif;color:#f59e0b;font-size:1.1rem;font-weight:700;">Document</h2>' +
            '<button id="fg-legal-close" style="width:34px;height:34px;border-radius:8px;border:1px solid rgba(255,255,255,0.1);background:rgba(255,255,255,0.05);color:#fff;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:background 0.2s;">&#10005;</button>' +
            '</div>' +
            '<div id="fg-legal-content" style="flex:1;overflow-y:auto;padding:28px;font-size:0.92rem;line-height:1.7;color:#cbd5e1;"></div>' +
            '</div>';
        document.body.appendChild(legal);

        // INJECT STYLES
        var style = document.createElement('style');
        style.textContent =
            '#fg-legal-content h1{color:#f59e0b;font-family:Outfit,sans-serif;font-size:1.4rem;margin:1.5em 0 .5em;font-weight:700}' +
            '#fg-legal-content h2{color:#d4af37;font-family:Outfit,sans-serif;font-size:1.15rem;margin:1.3em 0 .4em;font-weight:600}' +
            '#fg-legal-content h3{color:#94a3b8;font-family:Outfit,sans-serif;font-size:1rem;margin:1em 0 .3em;font-weight:600}' +
            '#fg-legal-content hr{border:none;border-top:1px solid rgba(212,175,55,0.15);margin:1.5em 0}' +
            '#fg-legal-content li{margin:4px 0;padding-left:8px}' +
            '#fg-legal-content code{background:rgba(212,175,55,0.1);padding:2px 6px;border-radius:4px;font-size:.85em;color:#d4af37}' +
            '#fg-legal-content strong{color:#e2e8f0}' +
            '#fg-legal-content a{color:#d4af37}' +
            '#fg-legal-content p{margin:.5em 0}' +
            '#fg-legal-content::-webkit-scrollbar{width:6px}' +
            '#fg-legal-content::-webkit-scrollbar-track{background:transparent}' +
            '#fg-legal-content::-webkit-scrollbar-thumb{background:rgba(212,175,55,0.3);border-radius:3px}' +
            '#fg-legal-close:hover{background:rgba(239,68,68,0.2)!important}' +
            '[data-legal]{cursor:pointer;transition:color .2s}' +
            '[data-legal]:hover{color:#d4af37!important}' +
            '[data-consent]{transition:all .2s}' +
            '[data-consent]:hover{filter:brightness(1.3);transform:scale(1.02)}' +
            '[data-help]{cursor:pointer;transition:all .2s;text-decoration:none}' +
            '[data-help]:hover{filter:brightness(1.2);transform:scale(1.03)}';
        document.head.appendChild(style);

        // Show cookie consent if not yet given
        var hasCookie = document.cookie.split(';').some(function(c) {
            return c.trim().indexOf('flagguard_consent=') === 0;
        });
        if (!hasCookie) {
            cookie.style.display = 'block';
        }
    }

    // ── Global event delegation ─────────────────────────────────────
    document.addEventListener('click', function(e) {
        var t = e.target;

        // Cookie consent buttons
        var consentBtn = t.closest ? t.closest('[data-consent]') : null;
        if (consentBtn) {
            var choice = consentBtn.getAttribute('data-consent');
            document.cookie = 'flagguard_consent=' + choice + ';path=/;max-age=31536000;SameSite=Lax';
            var co = document.getElementById('fg-cookie-overlay');
            if (co) co.style.display = 'none';
            try {
                fetch('/api/v1/consent', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({type: choice})
                });
            } catch(x) {}
            e.preventDefault();
            return;
        }

        // Legal document links
        var legalLink = t.closest ? t.closest('[data-legal]') : null;
        if (legalLink) {
            var docKey = legalLink.getAttribute('data-legal');
            var overlay = document.getElementById('fg-legal-overlay');
            var content = document.getElementById('fg-legal-content');
            var title = document.getElementById('fg-legal-title');
            if (overlay && content && title) {
                title.textContent = LEGAL_TITLES[docKey] || 'Document';
                content.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:40px;">Loading...</p>';
                overlay.style.display = 'block';
                fetch('/api/v1/legal/' + docKey)
                    .then(function(r) { return r.text(); })
                    .then(function(h) { content.innerHTML = h; })
                    .catch(function() { content.innerHTML = '<p style="color:#ef4444;">Failed to load document.</p>'; });
            }
            e.preventDefault();
            return;
        }

        // "How To Use" help guide buttons
        var helpLink = t.closest ? t.closest('[data-help]') : null;
        if (helpLink) {
            var role = helpLink.getAttribute('data-help');
            var helpTitles = {
                viewer: '👁 Viewer Dashboard — How To Use',
                analyst: '🔬 Analyst Dashboard — How To Use',
                admin: '👑 Admin Dashboard — How To Use'
            };
            var overlay = document.getElementById('fg-legal-overlay');
            var content = document.getElementById('fg-legal-content');
            var title = document.getElementById('fg-legal-title');
            if (overlay && content && title) {
                title.textContent = helpTitles[role] || 'How To Use';
                content.innerHTML = '<p style="color:#94a3b8;text-align:center;padding:40px;">Loading guide...</p>';
                overlay.style.display = 'block';
                fetch('/api/v1/help/' + role)
                    .then(function(r) { return r.text(); })
                    .then(function(h) { content.innerHTML = h; })
                    .catch(function() { content.innerHTML = '<p style="color:#ef4444;">Failed to load guide.</p>'; });
            }
            e.preventDefault();
            return;
        }

        // Close button on legal reader
        var closeBtn = t.closest ? t.closest('#fg-legal-close') : null;
        if (closeBtn) {
            var lo = document.getElementById('fg-legal-overlay');
            if (lo) lo.style.display = 'none';
            return;
        }

        // Backdrop click on legal overlay
        if (t.id === 'fg-legal-overlay') {
            t.style.display = 'none';
            return;
        }
    });

    // Close on Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            var lo = document.getElementById('fg-legal-overlay');
            if (lo) lo.style.display = 'none';
        }
    });

    // ── Password show/hide toggle ─────────────────────────────────────
    function addPasswordToggles() {
        var inputs = document.querySelectorAll('input[type="password"]');
        inputs.forEach(function(inp) {
            if (inp.dataset.fgToggled) return; // already has toggle
            inp.dataset.fgToggled = '1';
            var wrapper = inp.parentElement;
            if (!wrapper) return;
            wrapper.style.position = 'relative';
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.innerHTML = '&#128065;'; // 👁 eye icon
            btn.title = 'Show/Hide password';
            btn.style.cssText = 'position:absolute;right:8px;top:50%;transform:translateY(-50%);background:none;border:none;cursor:pointer;font-size:1.1rem;color:#94a3b8;padding:4px;z-index:10;opacity:0.7;transition:opacity 0.2s;';
            btn.addEventListener('mouseenter', function() { btn.style.opacity = '1'; });
            btn.addEventListener('mouseleave', function() { btn.style.opacity = '0.7'; });
            btn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                if (inp.type === 'password') {
                    inp.type = 'text';
                    btn.innerHTML = '&#128064;'; // 👀
                    btn.title = 'Hide password';
                } else {
                    inp.type = 'password';
                    btn.innerHTML = '&#128065;'; // 👁
                    btn.title = 'Show password';
                }
            });
            wrapper.appendChild(btn);
            inp.style.paddingRight = '36px';
        });
    }

    // ── Init: retry until body is available ──────────────────────────
    function tryInit() {
        if (document.body) {
            createOverlays();
            addPasswordToggles();
        } else {
            setTimeout(tryInit, 100);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', tryInit);
    } else {
        tryInit();
    }

    // Safety net: retry every 500ms for 10s in case Gradio rebuilds DOM
    var retries = 0;
    var interval = setInterval(function() {
        createOverlays();
        addPasswordToggles();
        retries++;
        if (retries > 20) clearInterval(interval);
    }, 500);
})();
