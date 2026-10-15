/**
 * Single Page Application (SPA) Controller Engine
 * Handles navigation tabs, Leaflet GIS map, Chart.js KPI charts, species search, observation filters,
 * pagination, observation details & species review, plantation management modals, dataset export
 * downloads, and password-protected editing.
 */

document.addEventListener("DOMContentLoaded", () => {
    App.init();
});

const App = {
    currentTab: "overview",
    leafletMap: null,
    mapLayerGroup: null,
    charts: {},

    // State Variables
    obsPage: 1,
    obsLimit: 15,
    obsFilters: { source: "", zone: "", quality_grade: "", species: "" },
    
    speciesPage: 1,
    speciesLimit: 15,
    speciesSearch: "",

    plantedPage: 1,
    plantedLimit: 10,
    plantedFilters: { status: "", zone: "", species: "" },
    editingPlantId: null,

    // Phase 15 Auth Callback Holder
    pendingAction: null,

    async init() {
        this.setupNavigation();
        this.setupModalDismissal();
        this.setupPhotoGpsListeners();
        this.updateAuthStatusUI();
        this.initHeaderClock();
        this.initWeatherPill();
        await this.checkBackendHealth();

        // OAuth callback returns to ?inat=connected#verify (or an error state).
        const inatCallbackState = new URLSearchParams(location.search).get("inat");
        if (inatCallbackState) {
            history.replaceState(null, "", `${location.pathname}#verify`);
        }

        // Open the tab named in the URL (e.g. #map), otherwise the overview
        const initialTab = (location.hash || "").replace("#", "");
        if (initialTab && initialTab !== "overview" && document.getElementById(`tab-${initialTab}`)) {
            await this.switchTab(initialTab);
        } else {
            try {
                await this.loadOverview();
            } catch (err) {
                this.showErrorBanner(`Could not load the overview: ${err.message}`);
            }
        }
        if (inatCallbackState === "connected") this.notify("iNaturalist account connected. Select verified planted-tree records to review and approve.", "success", 7000);
        else if (inatCallbackState === "error") this.notify("iNaturalist connection failed. Check backend OAuth configuration and try again.", "error", 8000);
        else if (inatCallbackState === "cancelled") this.notify("iNaturalist connection was cancelled.", "warning");
    },

    // =====================================================================
    // UI helpers
    // =====================================================================

    // Escapes user- or data-provided text before inserting it as HTML
    esc(value) {
        if (value === null || value === undefined) return "";
        return String(value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
    },

    // Non-blocking notification in the bottom-right corner
    notify(message, type = "success", timeoutMs = 4500) {
        const container = document.getElementById("toast-container");
        if (!container) { alert(message); return; }
        const toast = document.createElement("div");
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add("leaving");
            setTimeout(() => toast.remove(), 300);
        }, timeoutMs);
    },

    photoSrc(photoUrl) {
        if (!photoUrl) return "";
        if (/^https?:\/\//i.test(photoUrl)) return photoUrl;
        return window.APP_CONFIG.getEndpoint(photoUrl);
    },

    // Small cached preview for uploaded photos (falls back to the original for other URLs)
    thumbSrc(photoUrl) {
        const m = /^\/uploads\/(upload_[A-Za-z0-9_]+\.(jpg|jpeg|png|webp))$/i.exec(photoUrl || "");
        return m ? window.APP_CONFIG.getEndpoint(`/thumbs/${m[1]}`) : this.photoSrc(photoUrl);
    },

    zoneLabel(zone) {
        if (!zone) return '<span class="zone-text outside">Outside zones</span>';
        const cls = { "ZONE A": "zone-a", "ZONE B": "zone-b", "ZONE C": "zone-c" }[zone.toUpperCase()] || "";
        return `<span class="zone-text ${cls}">${this.esc(zone)}</span>`;
    },

    sourceLabel(source) {
        if (source === "NGO / New Upload") return '<span class="pill pill-orange">RSWF field upload</span>';
        if (source === "iNaturalist") return '<span class="pill pill-green">iNaturalist</span>';
        return `<span class="pill pill-grey">${this.esc(source || "Unknown")}</span>`;
    },

    // Status badge: review state for RSWF uploads, quality grade for iNaturalist records
    statusBadge(o) {
        if (o.source === "NGO / New Upload") {
            const map = {
                verified: ["verified", "✓ Verified"],
                corrected: ["corrected", "✓ Corrected"],
                ai_suggested: ["ai", "AI suggested"],
                needs_review: ["review", "Needs review"]
            };
            const [cls, label] = map[o.identification_status] || (o.scientific_name ? ["review", "Unconfirmed"] : ["review", "Needs ID"]);
            return `<span class="id-badge ${cls}">${label}</span>`;
        }
        const grades = { research: ["verified", "Research grade"], needs_id: ["review", "Needs ID"], casual: ["reference", "Casual"] };
        const [cls, label] = grades[o.quality_grade] || ["reference", this.esc(o.quality_grade || "—")];
        return `<span class="id-badge ${cls}">${label}</span>`;
    },

    // Collects every page of a paginated list endpoint (the API returns at most 200 per page)
    async fetchAllPages(fetchPage, pageSize = 200, maxPages = 50) {
        const all = [];
        for (let page = 1; page <= maxPages; page++) {
            const res = await fetchPage({ page, limit: pageSize });
            all.push(...(res.data || []));
            if (!res.total_pages || page >= res.total_pages) break;
        }
        return all;
    },

    // Swaps a broken <img> (photo file missing on the server) for a placeholder box
    replaceMissingPhoto(el, className, text) {
        const box = document.createElement("div");
        box.className = className;
        box.title = "Photo file missing";
        box.textContent = text;
        el.replaceWith(box);
    },

    isAwaitingReview(o) {
        return o.source === "NGO / New Upload" && !["verified", "corrected"].includes(o.identification_status);
    },

    setupModalDismissal() {
        const closers = {
            "obs-detail-modal": () => this.closeObservationDetail(),
            "plant-modal": () => this.closePlantModal(),
            "ngo-obs-modal": () => this.closeNgoObsModal(),
            "upload-photo-modal": () => this.closeUploadPhotoModal(),
            "plant-monitoring-modal": () => this.closeMonitoringModal(),
            "plant-history-modal": () => this.closePlantHistoryModal(),
            "water-date-modal": () => this.closeWaterDateModal(),
            "ngo-auth-modal": () => this.closeAuthModal()
        };
        // Click on the dark backdrop (outside the card) closes the dialog
        Object.entries(closers).forEach(([id, close]) => {
            const el = document.getElementById(id);
            if (el) el.addEventListener("mousedown", (e) => { if (e.target === el) close(); });
        });
        // Escape closes the top-most open dialog
        document.addEventListener("keydown", (e) => {
            if (e.key !== "Escape") return;
            const open = Object.keys(closers).filter(id => {
                const el = document.getElementById(id);
                return el && el.style.display !== "none";
            });
            if (open.length) closers[open[open.length - 1]]();
        });
    },

    setupPhotoGpsListeners() {
        const plantPhotoInput = document.getElementById("form-plant-photo-file");
        if (plantPhotoInput) {
            plantPhotoInput.addEventListener("change", async (e) => {
                if (!e.target.files || e.target.files.length === 0) return;
                const badge = document.getElementById("plant-photo-gps-badge");
                if (badge) {
                    badge.textContent = "⏳ Checking photo for GPS / geotag...";
                    badge.style.display = "block";
                    badge.style.color = "#60a5fa";
                }
                try {
                    const info = await ApiService.inspectPhoto(e.target.files[0]);
                    if (info.gps_available && info.latitude && info.longitude) {
                        const latInput = document.getElementById("form-latitude");
                        const lngInput = document.getElementById("form-longitude");
                        const zoneInput = document.getElementById("form-zone-code");
                        if (latInput && !latInput.value) latInput.value = info.latitude;
                        if (lngInput && !lngInput.value) lngInput.value = info.longitude;
                        if (zoneInput && !zoneInput.value && info.zone && info.zone !== "Outside Active Zones") zoneInput.value = info.zone;
                        if (badge) {
                            badge.innerHTML = `✓ ${info.gps_description} (${info.latitude.toFixed(6)}, ${info.longitude.toFixed(6)})`;
                            badge.style.color = "#34d399";
                        }
                    } else if (badge) {
                        badge.innerHTML = "ℹ️ No GPS metadata or visible geotag found in this photo.";
                        badge.style.color = "#94a3b8";
                    }
                } catch (err) {
                    if (badge) {
                        badge.innerHTML = `⚠️ Notice: ${err.message}`;
                        badge.style.color = "#f87171";
                    }
                }
            });
        }

        const ngoPhotoInput = document.getElementById("ngo-photo-file");
        if (ngoPhotoInput) {
            ngoPhotoInput.addEventListener("change", async (e) => {
                if (!e.target.files || e.target.files.length === 0) return;
                const badge = document.getElementById("ngo-photo-gps-badge");
                if (badge) {
                    badge.textContent = "⏳ Checking photo for GPS / geotag...";
                    badge.style.display = "block";
                    badge.style.color = "#60a5fa";
                }
                try {
                    const info = await ApiService.inspectPhoto(e.target.files[0]);
                    if (info.gps_available && info.latitude && info.longitude) {
                        const latInput = document.getElementById("ngo-latitude");
                        const lngInput = document.getElementById("ngo-longitude");
                        if (latInput && !latInput.value) latInput.value = info.latitude;
                        if (lngInput && !lngInput.value) lngInput.value = info.longitude;
                        if (badge) {
                            badge.innerHTML = `✓ ${info.gps_description} (${info.latitude.toFixed(6)}, ${info.longitude.toFixed(6)})`;
                            badge.style.color = "#34d399";
                        }
                    } else if (badge) {
                        badge.innerHTML = "ℹ️ No GPS metadata or visible geotag found in this photo.";
                        badge.style.color = "#94a3b8";
                    }
                } catch (err) {
                    if (badge) {
                        badge.innerHTML = `⚠️ Notice: ${err.message}`;
                        badge.style.color = "#f87171";
                    }
                }
            });
        }
    },

    // =====================================================================
    // Phase 15 — Password-Protected Auth UI Handlers
    // =====================================================================

    updateAuthStatusUI() {
        const btn = document.getElementById("ngo-auth-status-btn");
        if (!btn) return;
        const pass = ApiService.getNgoPassword();
        if (pass) {
            btn.textContent = "🔓 Editing unlocked · Lock";
            btn.classList.add("unlocked");
            btn.title = "RSWF editing is unlocked in this browser. Click to lock again.";
        } else {
            btn.textContent = "🔒 View only · Unlock editing";
            btn.classList.remove("unlocked");
            btn.title = "RSWF staff can unlock editing with the admin password";
        }
    },

    toggleAuthSession() {
        const pass = ApiService.getNgoPassword();
        if (pass) {
            ApiService.clearNgoPassword();
            this.updateAuthStatusUI();
            this.notify("Editing locked. You are now in view-only mode.");
        } else {
            this.openAuthModal(null);
        }
    },

    requireAuth(actionCallback) {
        const wrapped = async () => {
            try {
                await actionCallback();
            } catch (err) {
                // If the server rejected a cached password, re-prompt instead of silently failing.
                // (buildApiError auto-clears the password on 401.)
                if (err && err.status === 401) {
                    this.notify("Editing password doesn't match any more. Please unlock again.", "warning", 6000);
                    this.updateAuthStatusUI();
                    this.openAuthModal(actionCallback);
                    return;
                }
                throw err;
            }
        };
        if (ApiService.getNgoPassword()) {
            wrapped();
        } else {
            this.openAuthModal(actionCallback);
        }
    },

    openAuthModal(actionCallback = null) {
        this.pendingAction = actionCallback;
        const passInput = document.getElementById("ngo-auth-password");
        const errDiv = document.getElementById("auth-error-msg");
        const toggle = document.getElementById("ngo-auth-password-toggle");
        if (passInput) {
            passInput.value = "";
            // Always open with the password hidden, even if the user left it visible last time.
            passInput.type = "password";
        }
        if (toggle) {
            toggle.setAttribute("aria-pressed", "false");
            toggle.setAttribute("aria-label", "Show password");
        }
        if (errDiv) errDiv.style.display = "none";
        document.getElementById("ngo-auth-modal").style.display = "flex";
        if (passInput) passInput.focus();
    },

    closeAuthModal() {
        this.pendingAction = null;
        document.getElementById("ngo-auth-modal").style.display = "none";
    },

    // Flip the input between type=password and type=text so the user can double-check their typing.
    // Preserves the caret position and keeps focus so typing can continue uninterrupted.
    togglePasswordVisibility(inputId, buttonEl) {
        const input = document.getElementById(inputId);
        if (!input) return;
        const willShow = input.type === "password";
        const caret = input.selectionStart;
        input.type = willShow ? "text" : "password";
        if (buttonEl) {
            buttonEl.setAttribute("aria-pressed", String(willShow));
            buttonEl.setAttribute("aria-label", willShow ? "Hide password" : "Show password");
            buttonEl.title = willShow ? "Hide password" : "Show password";
        }
        // Firefox / Safari drop focus when type changes; restore it.
        try {
            input.focus();
            if (caret != null) input.setSelectionRange(caret, caret);
        } catch (_) {}
    },

    async handleAuthSubmit(e) {
        e.preventDefault();
        const passInput = document.getElementById("ngo-auth-password");
        const errDiv = document.getElementById("auth-error-msg");
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const password = (passInput && passInput.value) || "";
        if (!password) return;

        if (errDiv) errDiv.style.display = "none";
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.dataset.originalText = submitBtn.dataset.originalText || submitBtn.textContent;
            submitBtn.textContent = "Checking...";
        }

        // Verify server-side before caching the password locally so a wrong try doesn't poison the session.
        let ok = false;
        try {
            ok = await ApiService.verifyAdminPassword(password);
        } catch (err) {
            if (errDiv) {
                errDiv.style.display = "block";
                errDiv.textContent = `Could not reach the server: ${err.message}`;
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = submitBtn.dataset.originalText || "Unlock & Continue";
            }
            return;
        }

        if (!ok) {
            if (errDiv) {
                errDiv.style.display = "block";
                errDiv.textContent = "That password doesn't match. Ask your RSWF admin for the current one.";
            }
            if (passInput) {
                passInput.value = "";
                passInput.focus();
            }
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = submitBtn.dataset.originalText || "Unlock & Continue";
            }
            return;
        }

        ApiService.setNgoPassword(password);
        this.updateAuthStatusUI();
        document.getElementById("ngo-auth-modal").style.display = "none";
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = submitBtn.dataset.originalText || "Unlock & Continue";
        }

        if (this.pendingAction) {
            const act = this.pendingAction;
            this.pendingAction = null;
            act();
        }
    },

    setupNavigation() {
        document.querySelectorAll(".nav-item button").forEach(btn => {
            btn.addEventListener("click", async () => {
                const targetTab = btn.getAttribute("data-tab");
                if (targetTab === this.currentTab) return;
                await this.switchTab(targetTab);
            });
        });
        window.addEventListener("hashchange", () => {
            const tab = (location.hash || "#overview").replace("#", "");
            if (tab !== this.currentTab && document.getElementById(`tab-${tab}`)) this.switchTab(tab);
        });
    },

    async switchTab(targetTab) {
        document.querySelectorAll(".nav-item button").forEach(b => {
            b.classList.toggle("active", b.getAttribute("data-tab") === targetTab);
        });
        document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
        const targetPane = document.getElementById(`tab-${targetTab}`);
        if (targetPane) targetPane.classList.add("active");

        this.currentTab = targetTab;
        if (location.hash !== `#${targetTab}`) history.replaceState(null, "", `#${targetTab}`);
        const main = document.querySelector(".main-content");
        if (main) main.scrollTop = 0;
        await this.handleTabSwitch(targetTab);
    },

    async checkBackendHealth() {
        const badge = document.getElementById("backend-status-badge");
        try {
            await ApiService.getHealth();
            if (badge) {
                badge.classList.remove("offline");
                badge.innerHTML = `<span class="dot"></span> Live data connected`;
            }
            this.clearErrorBanner();
        } catch (err) {
            if (badge) {
                badge.classList.add("offline");
                badge.innerHTML = `<span class="dot"></span> Offline · retrying`;
            }
            this.showErrorBanner("Cannot reach the data server. Make sure the backend is running (http://localhost:8000), then press Retry.");
        }
    },

    // Re-runs the loader for the tab currently on screen; wired to the Retry button in the
    // top error banner so a transient failure (free-tier backend waking up) can be re-tried
    // without a full page reload.
    async retryCurrentTab() {
        await this.checkBackendHealth();
        await this.handleTabSwitch(this.currentTab || "overview");
    },

    async handleTabSwitch(tabName) {
        this.clearErrorBanner();
        try {
            switch (tabName) {
                case "overview":
                    await this.loadOverview();
                    break;
                case "map":
                    await this.loadMap();
                    break;
                case "species":
                    await this.loadSpecies();
                    break;
                case "observations":
                    await this.loadObservations();
                    break;
                case "zones":
                    await this.loadZones();
                    break;
                case "watering":
                    await this.loadWateringQueue();
                    break;
                case "verify":
                    await this.loadInatUploadQueue();
                    break;
                case "compliance":
                    await this.loadCompliance();
                    break;
                case "management":
                    await this.loadPlantedPlants();
                    break;
                case "export":
                    // Export UI static triggers ready
                    break;
            }
        } catch (err) {
            this.showErrorBanner(`Failed to load data for ${tabName}: ${err.message}`);
        }
    },

    // 1. Overview Tab Loader
    async loadOverview() {
        const stats = await ApiService.getStatisticsOverview();

        document.getElementById("kpi-total-obs").textContent = stats.total_observations.toLocaleString();
        document.getElementById("kpi-total-species").textContent = stats.unique_species_count.toLocaleString();
        
        const zoneCounts = stats.observations_by_zone || {};
        const activeZonesCount = (zoneCounts["ZONE A"] || 0) + (zoneCounts["ZONE B"] || 0) + (zoneCounts["ZONE C"] || 0);
        document.getElementById("kpi-inside-zones").textContent = activeZonesCount.toLocaleString();
        const pct = stats.total_observations ? Math.round((activeZonesCount / stats.total_observations) * 100) : 0;
        const insideSub = document.getElementById("kpi-inside-zones-sub");
        if (insideSub) insideSub.textContent = `${pct}% of all records, inside Zones A–C`;

        const coverage = document.getElementById("coverage-taxa-count");
        if (coverage) coverage.textContent = `The ${stats.unique_species_count.toLocaleString()}`;

        this.renderZoneChart(zoneCounts);
        this.renderSourceChart(stats.observations_by_source || {});
        await Promise.all([this.loadActionPriorities(), this.loadReviewCount(), this.loadWaterKpi()]);
    },

    // Compact "water today" KPI on the overview — just the overdue + due_soon count.
    async loadWaterKpi() {
        const el = document.getElementById("kpi-water-today");
        const sub = document.getElementById("kpi-water-sub");
        const card = document.getElementById("kpi-water-card");
        if (!el) return;
        try {
            const res = await ApiService.getWateringQueue();
            const s = res.summary || {};
            if (s.is_monsoon) {
                el.textContent = "—";
                if (sub) sub.textContent = "Monsoon season · reminders paused";
                if (card) card.classList.remove("attention");
            } else {
                const n = s.needs_water_today || 0;
                el.textContent = n.toLocaleString();
                if (sub) sub.textContent = n === 0
                    ? "All plants have been watered recently"
                    : `${s.counts?.overdue || 0} overdue · ${s.counts?.due_soon || 0} due soon · View →`;
                if (card) card.classList.toggle("attention", n > 0);
            }
        } catch (err) {
            el.textContent = "–";
            if (sub) sub.textContent = `Could not load (${err.message || "error"})`;
        }
    },

    // Number of RSWF field uploads whose species has not been confirmed or corrected yet
    async loadReviewCount() {
        const el = document.getElementById("kpi-review");
        if (!el) return;
        try {
            const records = await this.fetchAllPages((params) => ApiService.getObservations({ ...params, source: "NGO / New Upload" }));
            el.textContent = records.filter(o => this.isAwaitingReview(o)).length.toLocaleString();
        } catch (err) {
            el.textContent = "–";
        }
    },

    // Opens the Observations tab showing RSWF field uploads (the review queue)
    async openReviewQueue() {
        this.obsFilters = { source: "NGO / New Upload", zone: "", quality_grade: "", species: "" };
        this.obsPage = 1;
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
        set("obs-source-filter", "NGO / New Upload");
        set("obs-zone-filter", "");
        set("obs-quality-filter", "");
        set("obs-species-filter", "");
        await this.switchTab("observations");
    },

    async loadActionPriorities() {
        const container = document.getElementById("action-priorities-container");
        if (!container) return;

        try {
            const data = await ApiService.getAnalyticsActionPriorities();
            if (!data.priorities || data.priorities.length === 0) {
                container.innerHTML = `<div class="loading-text">No actions are suggested by the current data.</div>`;
                return;
            }

            const levels = {
                HIGH: { color: "#ef4444", bg: "rgba(239, 68, 68, 0.2)", label: "High priority" },
                MEDIUM: { color: "#f59e0b", bg: "rgba(245, 158, 11, 0.2)", label: "Medium priority" },
                LOW: { color: "#60a5fa", bg: "rgba(59, 130, 246, 0.2)", label: "Low priority" }
            };
            const areaName = (code) => code === "OUTSIDE_ACTIVE_ZONES" ? "Outside active zones" : code;
            const typeName = (t) => (t || "").replace(/_/g, " ").toLowerCase().replace(/^\w/, c => c.toUpperCase());

            container.innerHTML = data.priorities.map(p => {
                const lvl = levels[p.priority_level] || { color: "#10b981", bg: "rgba(16, 185, 129, 0.2)", label: typeName(p.priority_level) };
                return `
                    <div class="action-card" style="border-left-color:${lvl.color}">
                        <div class="action-card-head">
                            <b>${this.esc(areaName(p.area_code))}</b>
                            <span class="status-badge" style="background:${lvl.bg};color:${lvl.color}" title="${this.esc(lvl.label)}">${this.esc(typeName(p.priority_type))}</span>
                        </div>
                        <p><b>Why:</b> ${this.esc(p.reason)}</p>
                        <div class="action-do"><b>Suggested action:</b> ${this.esc(p.recommended_action)}</div>
                    </div>
                `;
            }).join("");
        } catch (err) {
            container.innerHTML = `<div style="color:#f87171;font-size:0.85rem">Could not load suggested actions: ${this.esc(err.message)}</div>`;
        }
    },

    renderZoneChart(zoneCounts) {
        const ctx = document.getElementById("chart-zone-breakdown");
        if (!ctx) return;

        if (this.charts.zoneChart) this.charts.zoneChart.destroy();

        this.charts.zoneChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: ["Zone A", "Zone B", "Zone C", "Outside Active Zones"],
                datasets: [{
                    label: "Observations",
                    data: [
                        zoneCounts["ZONE A"] || 0,
                        zoneCounts["ZONE B"] || 0,
                        zoneCounts["ZONE C"] || 0,
                        zoneCounts["OUTSIDE_ACTIVE_ZONES"] || 0
                    ],
                    backgroundColor: [
                        "rgba(16, 185, 129, 0.7)",
                        "rgba(59, 130, 246, 0.7)",
                        "rgba(139, 92, 246, 0.7)",
                        "rgba(249, 115, 22, 0.7)"
                    ],
                    borderColor: ["#10b981", "#3b82f6", "#8b5cf6", "#f97316"],
                    borderWidth: 1.5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { callbacks: { label: (c) => ` ${c.parsed.y} observations` } }
                },
                scales: {
                    y: { beginAtZero: true, ticks: { color: "#94a3b8", precision: 0 }, grid: { color: "rgba(46,117,89,0.15)" } },
                    x: { ticks: { color: "#94a3b8" }, grid: { display: false } }
                }
            }
        });
    },

    renderSourceChart(sourceCounts) {
        const ctx = document.getElementById("chart-source-breakdown");
        if (!ctx) return;

        if (this.charts.sourceChart) this.charts.sourceChart.destroy();

        const friendly = { "iNaturalist": "iNaturalist (public records)", "NGO / New Upload": "RSWF field uploads" };
        const colors = { "iNaturalist": "#10b981", "NGO / New Upload": "#f97316" };
        const keys = Object.keys(sourceCounts);
        const values = Object.values(sourceCounts);

        this.charts.sourceChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: keys.map(k => friendly[k] || k),
                datasets: [{
                    data: values,
                    backgroundColor: keys.map((k, i) => colors[k] || ["#3b82f6", "#8b5cf6"][i % 2]),
                    borderColor: "#0c2019",
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "58%",
                plugins: {
                    legend: { position: "bottom", labels: { color: "#e2e8f0", padding: 16 } },
                    tooltip: {
                        callbacks: {
                            label: (c) => {
                                const total = c.dataset.data.reduce((a, b) => a + b, 0) || 1;
                                return ` ${c.parsed} observations (${Math.round((c.parsed / total) * 100)}%)`;
                            }
                        }
                    }
                }
            }
        });
    },

    // 2. Interactive Leaflet GIS Map Loader
    async loadMap() {
        if (!this.leafletMap) {
            this.leafletMap = L.map("leaflet-map", {
                maxZoom: 23,
                minZoom: 13,
                zoomSnap: 0.25,
                zoomDelta: 0.5,
                wheelPxPerZoomLevel: 100
            }).setView([18.5195, 73.7800], 17);

            const street = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxNativeZoom: 19,
                maxZoom: 23,
                attribution: "© OpenStreetMap contributors | RSWF NGO"
            }).addTo(this.leafletMap);
            const satellite = L.tileLayer("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", {
                maxNativeZoom: 19,
                maxZoom: 23,
                attribution: "Imagery © Esri | RSWF NGO"
            });
            const googleHybrid = L.tileLayer("https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}", {
                maxNativeZoom: 20,
                maxZoom: 23,
                attribution: "Imagery © Google | RSWF NGO"
            });

            this.mapLayers = {
                boundary: L.layerGroup().addTo(this.leafletMap),
                zones: L.layerGroup().addTo(this.leafletMap),
                inat: L.layerGroup().addTo(this.leafletMap),
                ngo: L.layerGroup().addTo(this.leafletMap),
                planted: L.layerGroup().addTo(this.leafletMap)
            };
            // Kept for compatibility with code that expects a single group
            this.mapLayerGroup = this.mapLayers.inat;

            L.control.layers(
                { "Street map": street, "Satellite (Esri)": satellite, "Satellite (Google Hybrid)": googleHybrid },
                {
                    "Site boundary": this.mapLayers.boundary,
                    "Zones A / B / C": this.mapLayers.zones,
                    "iNaturalist records": this.mapLayers.inat,
                    "RSWF field uploads": this.mapLayers.ngo,
                    "RSWF planted plants": this.mapLayers.planted
                },
                { collapsed: window.innerWidth < 900 }
            ).addTo(this.leafletMap);
            L.control.scale({ imperial: false, maxWidth: 150 }).addTo(this.leafletMap);

            // Reset View (Fit Site) button on map toolbar
            const ResetViewControl = L.Control.extend({
                options: { position: "topleft" },
                onAdd: () => {
                    const container = L.DomUtil.create("div", "leaflet-bar leaflet-control");
                    const btn = L.DomUtil.create("a", "leaflet-control-reset-btn", container);
                    btn.innerHTML = "🎯";
                    btn.title = "Fit Site Boundary (Reset Zoom)";
                    btn.href = "#";
                    btn.setAttribute("role", "button");
                    btn.setAttribute("aria-label", "Fit Site Boundary");
                    btn.style.cssText = "display:flex;align-items:center;justify-content:center;font-size:15px;text-decoration:none;background:#0c251c;color:#10b981;cursor:pointer;width:30px;height:30px;line-height:30px;";
                    L.DomEvent.disableClickPropagation(container);
                    L.DomEvent.on(btn, "click", (e) => {
                        L.DomEvent.stop(e);
                        this.resetMapView();
                    });
                    return container;
                }
            });
            new ResetViewControl().addTo(this.leafletMap);
        }

        Object.values(this.mapLayers).forEach(g => g.clearLayers());

        const [boundaryGeoJSON, zonesGeoJSONList, mapObsGeoJSON, plantedRes] = await Promise.all([
            ApiService.getGeography(),
            ApiService.getZones(),
            ApiService.getMapObservations(),
            this.fetchAllPages((params) => ApiService.getPlantedPlants(params)).then(data => ({ data })).catch(() => ({ data: [] }))
        ]);

        if (boundaryGeoJSON && boundaryGeoJSON.features) {
            const bLayer = L.geoJSON(boundaryGeoJSON, {
                style: { color: "#f59e0b", weight: 3, fillOpacity: 0.06, dashArray: "6, 6" }
            }).addTo(this.mapLayers.boundary);

            if (!this.mapFitted) {
                this.leafletMap.fitBounds(bLayer.getBounds(), { padding: [20, 20] });
                this.mapFitted = true;
            }
        }

        const colorMap = { "ZONE A": "#10b981", "ZONE B": "#3b82f6", "ZONE C": "#8b5cf6" };
        zonesGeoJSONList.forEach(z => {
            const zColor = colorMap[z.zone_code] || "#10b981";
            L.geoJSON(z.geometry, {
                style: { color: zColor, weight: 2, fillColor: zColor, fillOpacity: 0.22 }
            }).bindTooltip(this.esc(z.zone_code), { permanent: true, direction: "center", className: "zone-label-tooltip" })
              .addTo(this.mapLayers.zones);
        });

        const popupRow = (label, value) => value ? `<div class="popup-row"><b>${label}:</b> ${value}</div>` : "";

        if (mapObsGeoJSON && mapObsGeoJSON.features) {
            mapObsGeoJSON.features.forEach(feat => {
                const [lng, lat] = feat.geometry.coordinates;
                const props = feat.properties;
                const isNgo = props.source === "NGO / New Upload";
                const isRswfPlanted = isNgo && props.observation_type === "planted_rswf";

                const circleMarker = L.circleMarker([lat, lng], {
                    radius: isNgo ? 7 : 6,
                    fillColor: isRswfPlanted ? "#ef4444" : (isNgo ? "#f97316" : "#10b981"),
                    color: "#ffffff",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.85
                });

                const photo = props.photo_url ? this.photoSrc(props.photo_url) : "";
                const thumb = props.photo_url ? this.thumbSrc(props.photo_url) : "";
                const popupContent = `
                    <div>
                        <div class="popup-title">${this.esc(props.common_name || props.scientific_name || "Unidentified plant")}</div>
                        ${photo ? `<a href="${this.esc(photo)}" target="_blank" rel="noopener"><img class="popup-photo" src="${this.esc(thumb)}" alt="Observation photo" loading="lazy" onerror="App.replaceMissingPhoto(this.parentElement, 'popup-photo-empty', '📷 Photo file missing')"></a>` : ""}
                        ${popupRow("Scientific name", props.scientific_name ? `<i>${this.esc(props.scientific_name)}</i>` : "Not identified yet")}
                        ${popupRow("Observed", this.esc(props.observed_on))}
                        ${popupRow("Observer", this.esc(props.observer))}
                        ${popupRow("Zone", this.esc(props.zone || "Outside active zones"))}
                        ${popupRow("Source", isRswfPlanted ? "RSWF planted plant" : (isNgo ? "RSWF field upload" : "iNaturalist"))}
                        ${props.id ? `<div style="margin-top:6px"><button class="link-btn" onclick="App.openObservationDetail(${Number(props.id)})">View full details →</button></div>` : ""}
                    </div>
                `;

                circleMarker.bindPopup(popupContent, { maxWidth: 250 });
                (isNgo ? this.mapLayers.ngo : this.mapLayers.inat).addLayer(circleMarker);
            });
        }

        (plantedRes.data || []).forEach(p => {
            if (p.latitude == null || p.longitude == null) return;
            const statusColor = { Alive: "#10b981", Dead: "#ef4444", Unknown: "#f97316" }[p.status] || "#94a3b8";
            // RSWF-planted plants use a red fill; the outline still indicates health status.
            const marker = L.circleMarker([p.latitude, p.longitude], {
                radius: 7, fillColor: "#ef4444", color: statusColor, weight: 2.5, opacity: 1, fillOpacity: 0.9
            });
            marker.bindPopup(`
                <div>
                    <div class="popup-title" style="color:#60a5fa">🌱 ${this.esc(p.common_name || p.scientific_name || p.plant_code)}</div>
                    ${popupRow("Plant code", this.esc(p.plant_code))}
                    ${popupRow("Scientific name", p.scientific_name ? `<i>${this.esc(p.scientific_name)}</i>` : "")}
                    ${popupRow("Planted", this.esc(p.planted_on))}
                    ${popupRow("Health", `<span style="color:${statusColor};font-weight:600">${this.esc(p.status)}</span>`)}
                    ${popupRow("Zone", this.esc(p.zone_code || "Outside active zones"))}
                </div>`, { maxWidth: 250 });
            this.mapLayers.planted.addLayer(marker);
        });

        setTimeout(() => this.leafletMap.invalidateSize(), 200);
    },

    // Opens the map and zooms to one zone
    async showZoneOnMap(zoneCode) {
        await this.switchTab("map");
        const zones = await ApiService.getZones();
        const z = zones.find(x => x.zone_code === zoneCode);
        if (z && this.leafletMap) this.leafletMap.fitBounds(L.geoJSON(z.geometry).getBounds(), { padding: [40, 40] });
    },

    resetMapView() {
        if (!this.leafletMap) return;
        const bLayers = this.mapLayers && this.mapLayers.boundary ? this.mapLayers.boundary.getLayers() : [];
        if (bLayers.length > 0 && typeof bLayers[0].getBounds === "function") {
            this.leafletMap.fitBounds(bLayers[0].getBounds(), { padding: [25, 25] });
        } else {
            this.leafletMap.setView([18.5195, 73.7800], 17);
        }
    },

    async showObservationOnMap(lat, lng) {
        await this.switchTab("map");
        if (this.leafletMap && lat && lng) {
            this.leafletMap.setView([lat, lng], 21);
        }
    },

    // Opens the Observations tab filtered to one zone
    async showZoneObservations(zoneCode) {
        this.obsFilters = { source: "", zone: zoneCode, quality_grade: "", species: "" };
        this.obsPage = 1;
        const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v; };
        set("obs-source-filter", "");
        set("obs-zone-filter", zoneCode);
        set("obs-quality-filter", "");
        set("obs-species-filter", "");
        await this.switchTab("observations");
    },

    // 3. Species Tab Loader
    async loadSpecies() {
        const searchInput = document.getElementById("species-search");
        if (searchInput && !searchInput.dataset.bound) {
            searchInput.dataset.bound = "true";
            searchInput.addEventListener("input", (e) => {
                this.speciesSearch = e.target.value;
                this.speciesPage = 1;
                this.loadSpecies();
            });
        }

        const res = await ApiService.getSpecies({
            page: this.speciesPage,
            limit: this.speciesLimit,
            species_name: this.speciesSearch
        });

        const tbody = document.getElementById("species-table-body");
        if (!tbody) return;

        if (res.data.length === 0) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No species match “${this.esc(this.speciesSearch)}”.</td></tr>`;
            document.getElementById("species-page-info").textContent = "No results";
            document.getElementById("species-prev-btn").disabled = true;
            document.getElementById("species-next-btn").disabled = true;
            return;
        }

        const rankPill = (rank) => {
            const r = (rank || "species").toLowerCase();
            const cls = r === "species" ? "pill-green" : r === "genus" ? "pill-blue" : "pill-purple";
            return `<span class="pill ${cls}">${this.esc(r)}</span>`;
        };

        tbody.innerHTML = res.data.map(s => `
            <tr class="row-clickable" onclick="App.openSpeciesProfile('${this.esc(s.scientific_name).replace(/'/g, "\\'")}')">
                <td class="faint">${s.id}</td>
                <td><b><i>${this.esc(s.scientific_name)}</i></b></td>
                <td>${s.common_name ? this.esc(s.common_name) : '<span class="faint">—</span>'}</td>
                <td>${rankPill(s.taxon_rank)}</td>
                <td><b>${s.record_count}</b> <span class="muted">${s.record_count === 1 ? "sighting" : "sightings"}</span></td>
            </tr>
        `).join("");

        document.getElementById("species-page-info").textContent = `Page ${res.page} of ${res.total_pages} · ${res.total_records} species & taxa`;
        document.getElementById("species-prev-btn").disabled = res.page <= 1;
        document.getElementById("species-next-btn").disabled = res.page >= res.total_pages;
    },

    changeSpeciesPage(delta) {
        this.speciesPage += delta;
        this.loadSpecies();
    },

    // 4. Observations Tab Loader
    async loadObservations() {
        const res = await ApiService.getObservations({
            page: this.obsPage,
            limit: this.obsLimit,
            source: this.obsFilters.source,
            zone: this.obsFilters.zone,
            quality_grade: this.obsFilters.quality_grade,
            species: this.obsFilters.species
        });

        const tbody = document.getElementById("obs-table-body");
        if (!tbody) return;

        if (res.data.length === 0) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="9">No observations match the current filters.</td></tr>`;
            document.getElementById("obs-page-info").textContent = "No results";
            document.getElementById("obs-prev-btn").disabled = true;
            document.getElementById("obs-next-btn").disabled = true;
            return;
        }

        tbody.innerHTML = res.data.map(o => {
            const photo = o.photo_url && o.source === "NGO / New Upload" ? this.thumbSrc(o.photo_url) : "";
            const thumb = photo
                ? `<img class="obs-thumb" src="${this.esc(photo)}" alt="" loading="lazy" onerror="App.replaceMissingPhoto(this, 'obs-thumb-empty', '–')">`
                : `<div class="obs-thumb-empty" title="${o.observation_url ? "Photo on iNaturalist" : "No photo"}">${o.observation_url ? "↗" : "–"}</div>`;
            return `
            <tr class="row-clickable" tabindex="0" onclick="App.openObservationDetail(${Number(o.id)})" onkeydown="if(event.key==='Enter')App.openObservationDetail(${Number(o.id)})" title="View details">
                <td class="faint">${o.id}</td>
                <td>${thumb}</td>
                <td>${o.scientific_name ? `<b><i>${this.esc(o.scientific_name)}</i></b>` : '<span class="muted">Not identified yet</span>'}</td>
                <td>${o.common_name ? this.esc(o.common_name) : '<span class="faint">—</span>'}</td>
                <td style="white-space:nowrap">${this.esc(o.observer || "—")}</td>
                <td style="white-space:nowrap">${this.esc(o.observed_on || "—")}</td>
                <td>${this.zoneLabel(o.zone)}</td>
                <td>${this.statusBadge(o)}</td>
                <td>${this.sourceLabel(o.source)}</td>
            </tr>`;
        }).join("");

        document.getElementById("obs-page-info").textContent = `Page ${res.page} of ${res.total_pages} · ${res.total_records} observations`;
        document.getElementById("obs-prev-btn").disabled = res.page <= 1;
        document.getElementById("obs-next-btn").disabled = res.page >= res.total_pages;
    },

    changeObsPage(delta) {
        this.obsPage += delta;
        this.loadObservations();
    },

    applyObsFilter(field, value) {
        this.obsFilters[field] = value;
        this.obsPage = 1;
        this.loadObservations();
    },

    // 5. Active Zones Tab Loader
    async loadZones() {
        const container = document.getElementById("zones-cards-container");
        if (!container) return;

        // Every call wrapped in catch so one slow endpoint doesn't blank the whole tab.
        // Analytics / coverage are enrichment; the zone polygons from /zones are the backbone.
        const [zones, analytics, coverage] = await Promise.all([
            ApiService.getZones().catch(() => []),
            ApiService.getAnalyticsZones().catch(() => ({ zones: {} })),
            ApiService.getAnalyticsCoverage().catch(() => null)
        ]);
        if (!zones || !zones.length) {
            container.innerHTML = `
                <div class="loading-text" style="grid-column:1/-1">
                    Could not load zone boundaries. The data server may be waking up.
                    <button class="btn-action" style="margin-left:0.5rem" onclick="App.loadZones()">Retry</button>
                </div>`;
            return;
        }
        const stats = (analytics && analytics.zones) || {};
        const colors = { "ZONE A": "#10b981", "ZONE B": "#3b82f6", "ZONE C": "#8b5cf6" };

        container.innerHTML = zones.map(z => {
            const s = stats[z.zone_code] || {};
            const plants = s.plant_status_counts || {};
            const isActive = (z.status || "").toLowerCase().includes("active");
            const area = s.area_ha != null ? `${s.area_ha} ha (≈ ${Math.round(s.area_ha * 10000).toLocaleString()} m²)` : "";
            const code = this.esc(z.zone_code);
            return `
            <div class="zone-card" style="--zone-color:${colors[z.zone_code] || "#10b981"}">
                <div class="zone-card-head">
                    <h3>${code}</h3>
                    <span class="source-badge"><span class="dot"></span> ${isActive ? "Active" : this.esc(z.status)}</span>
                </div>
                <div class="zone-card-desc">RSWF planting and monitoring area${area ? ` · ${area}` : ""}.</div>
                <div class="zone-stats">
                    <div class="zone-stat"><b>${s.recorded_observations_count ?? "–"}</b><span>Observations</span></div>
                    <div class="zone-stat"><b>${s.unique_recorded_taxa_count ?? "–"}</b><span>Species &amp; taxa</span></div>
                    <div class="zone-stat"><b>${s.planted_plants_count ?? "–"}</b><span>Planted plants</span></div>
                    <div class="zone-stat"><b>${s.total_monitoring_visits_logged ?? "–"}</b><span>Health-check visits</span></div>
                </div>
                <div class="zone-health">
                    <span class="status-badge alive">${plants.Alive || 0} alive</span>
                    <span class="status-badge dead">${plants.Dead || 0} dead</span>
                    <span class="status-badge unknown">${plants.Unknown || 0} unknown</span>
                </div>
                <div class="zone-card-foot">
                    <span>Boundary mapped from the RSWF site survey</span>
                    <span style="display:flex;gap:0.9rem">
                        <button class="link-btn" onclick="App.showZoneOnMap('${code}')">View on map</button>
                        <button class="link-btn" onclick="App.showZoneObservations('${code}')">Observations →</button>
                    </span>
                </div>
            </div>`;
        }).join("");

        const note = document.getElementById("zones-coverage-note");
        if (note && coverage) {
            const a = coverage.active_zones_summary || {};
            const n = coverage.non_active_portion_summary || {};
            note.innerHTML = `📍 <b>Coverage:</b> the three zones cover ${a.area_ha ?? "–"} ha of the ${coverage.total_project_area_ha ?? "–"} ha site, and hold ${a.observation_percentage ?? "–"}% of all observations.
                The remaining ${n.area_ha ?? "–"} ha outside the zones has ${n.recorded_observations ?? "–"} records. Parts with no records are monitoring gaps, not areas without plants.`;
            note.style.display = "block";
        }
    },

    // 6. Data Management Tab Loader (Phase 7 CRUD)
    async loadPlantedPlants() {
        const res = await ApiService.getPlantedPlants({
            page: this.plantedPage,
            limit: this.plantedLimit,
            status: this.plantedFilters.status,
            zone: this.plantedFilters.zone,
            species: this.plantedFilters.species
        });

        const tbody = document.getElementById("planted-table-body");
        if (!tbody) return;

        if (res.data.length === 0) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="7">No planted plants match. Use <b>Add Planted Plant</b> to register a new plantation record.</td></tr>`;
            document.getElementById("planted-page-info").textContent = "No results";
            document.getElementById("planted-prev-btn").disabled = true;
            document.getElementById("planted-next-btn").disabled = true;
            return;
        }

        tbody.innerHTML = res.data.map(p => {
            const stClass = (p.status || "unknown").toLowerCase();
            // Plant codes are passed to handlers as JSON strings so quotes in codes cannot break the markup
            const codeArg = this.esc(JSON.stringify(p.plant_code || ""));
            return `
                <tr>
                    <td><b>${this.esc(p.plant_code)}</b></td>
                    <td>${p.scientific_name ? `<b><i>${this.esc(p.scientific_name)}</i></b>` : '<span class="muted">Not specified</span>'}</td>
                    <td>${p.common_name ? this.esc(p.common_name) : '<span class="faint">—</span>'}</td>
                    <td style="white-space:nowrap">${this.esc(p.planted_on || "—")}</td>
                    <td>${this.zoneLabel(p.zone_code)}</td>
                    <td><span class="status-badge ${this.esc(stClass)}">${this.esc(p.status)}</span></td>
                    <td class="cell-actions">
                        <button class="btn-action info" onclick="App.openPlantHistoryModal(${Number(p.id)}, ${codeArg})" title="See all health-check visits">📋 History</button>
                        <button class="btn-action success" onclick="App.openMonitoringModal(${Number(p.id)}, ${codeArg})" title="Record a health-check visit">➕ Visit</button>
                        <button class="btn-action" onclick="App.openEditPlantModal(${Number(p.id)})">Edit</button>
                        <button class="btn-action delete" onclick="App.confirmDeletePlant(${Number(p.id)}, ${codeArg})">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");

        document.getElementById("planted-page-info").textContent = `Page ${res.page} of ${res.total_pages} · ${res.total_records} planted plants`;
        document.getElementById("planted-prev-btn").disabled = res.page <= 1;
        document.getElementById("planted-next-btn").disabled = res.page >= res.total_pages;
    },

    changePlantedPage(delta) {
        this.plantedPage += delta;
        this.loadPlantedPlants();
    },

    applyPlantedFilter(field, value) {
        this.plantedFilters[field] = value;
        this.plantedPage = 1;
        this.loadPlantedPlants();
    },

    // =====================================================================
    // Watering tab
    // =====================================================================

    async loadWateringQueue() {
        const tbody = document.getElementById("watering-table-body");
        const summary = document.getElementById("watering-summary");
        if (!tbody) return;

        try {
            const res = await ApiService.getWateringQueue();
            const s = res.summary || {};
            const c = s.counts || {};

            // Summary KPI cards
            const monsoonBanner = s.is_monsoon
                ? `<div class="note-card" style="grid-column:1/-1;background:rgba(59,130,246,0.08);border-color:rgba(59,130,246,0.35);color:#60a5fa"><b>🌧️ Monsoon season active.</b> Watering reminders are paused until October — the plants are getting enough rain.</div>`
                : "";
            if (summary) {
                summary.innerHTML = `
                    ${monsoonBanner}
                    <div class="kpi-card ${c.overdue ? 'attention' : ''}">
                        <span class="kpi-label">🔴 Overdue</span>
                        <span class="kpi-value">${(c.overdue || 0).toLocaleString()}</span>
                        <span class="kpi-subtext">Should have been watered already</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">🟡 Due Soon</span>
                        <span class="kpi-value">${(c.due_soon || 0).toLocaleString()}</span>
                        <span class="kpi-subtext">Water today or tomorrow</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">✅ OK</span>
                        <span class="kpi-value">${(c.ok || 0).toLocaleString()}</span>
                        <span class="kpi-subtext">Watered recently enough</span>
                    </div>
                    <div class="kpi-card">
                        <span class="kpi-label">🚫 Skipped</span>
                        <span class="kpi-value">${(c.skip || 0).toLocaleString()}</span>
                        <span class="kpi-subtext">Monsoon, dead or opted out</span>
                    </div>
                `;
            }

            const queue = res.queue || [];
            if (!queue.length) {
                tbody.innerHTML = `<tr class="empty-row"><td colspan="8">No planted plants registered yet.</td></tr>`;
                return;
            }

            const bucketPill = (bucket) => {
                const map = {
                    overdue: ['<span class="pill" style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.5)">🔴 Overdue</span>'],
                    due_soon: ['<span class="pill" style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.5)">🟡 Due soon</span>'],
                    ok: ['<span class="pill" style="background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.5)">✅ OK</span>'],
                    skip: ['<span class="pill" style="background:rgba(148,163,184,0.15);color:#cbd5e1;border:1px solid rgba(148,163,184,0.5)">🚫 Skip</span>'],
                };
                return map[bucket] || map.skip;
            };

            tbody.innerHTML = queue.map(a => {
                const w = a.watering || {};
                const nameParts = [];
                if (a.scientific_name) nameParts.push(`<i>${this.esc(a.scientific_name)}</i>`);
                if (a.common_name) nameParts.push(this.esc(a.common_name));
                const name = nameParts.join(" · ") || '<span class="muted">Unspecified</span>';
                const lastW = w.last_watered
                    ? new Date(w.last_watered + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
                    : '<span class="faint">Never</span>';
                const nextD = w.next_due
                    ? new Date(w.next_due + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short" })
                    : "—";
                const canWater = w.bucket !== "skip";
                const btn = canWater
                    ? `<div style="display:flex;gap:0.35rem;flex-wrap:wrap">
                        <button class="btn-action success" style="padding:0.25rem 0.55rem;font-size:0.78rem" onclick="App.markWatered(${Number(a.plant_id)}, ${this.esc(JSON.stringify(a.plant_code || ""))})" title="Quick mark: watered today">✓ Today</button>
                        <button class="btn-action" style="padding:0.25rem 0.55rem;font-size:0.78rem" onclick="App.openWaterDateModal(${Number(a.plant_id)}, ${this.esc(JSON.stringify(a.plant_code || ""))}, ${this.esc(JSON.stringify(w.last_watered || ""))})" title="Edit or pick custom watering date">✏️ Edit Date</button>
                       </div>`
                    : `<button class="btn-action" style="padding:0.25rem 0.55rem;font-size:0.78rem" onclick="App.openWaterDateModal(${Number(a.plant_id)}, ${this.esc(JSON.stringify(a.plant_code || ""))}, ${this.esc(JSON.stringify(w.last_watered || ""))})" title="Set watering date">✏️ Set Date</button>`;
                return `
                    <tr>
                        <td>${bucketPill(w.bucket)}</td>
                        <td><b>${this.esc(a.plant_code)}</b></td>
                        <td>${name}</td>
                        <td>${this.zoneLabel(a.zone_code)}</td>
                        <td style="white-space:nowrap">${lastW}</td>
                        <td style="white-space:nowrap">${nextD}</td>
                        <td>${this.esc(w.note || "")}</td>
                        <td class="cell-actions">${btn}</td>
                    </tr>
                `;
            }).join("");
        } catch (err) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="8" style="color:#f87171">Could not load watering queue: ${this.esc(err.message)}</td></tr>`;
        }
    },

    openWaterDateModal(plantId, plantCode, lastWateredDate) {
        this.requireAuth(() => this._doOpenWaterDateModal(plantId, plantCode, lastWateredDate));
    },

    _doOpenWaterDateModal(plantId, plantCode, lastWateredDate) {
        this.currentWateringPlantId = plantId;
        const sub = document.getElementById("water-modal-subtitle");
        if (sub) sub.textContent = `Plant ${plantCode}: set or adjust the last watered date. The next due date and status will recalculate accordingly.`;
        const dateInput = document.getElementById("water-modal-date");
        if (dateInput) {
            dateInput.value = lastWateredDate || new Date().toISOString().split("T")[0];
            dateInput.max = new Date().toISOString().split("T")[0];
        }
        const obsInput = document.getElementById("water-modal-observer");
        if (obsInput) obsInput.value = "RSWF Field Team";
        const modal = document.getElementById("water-date-modal");
        if (modal) modal.style.display = "flex";
    },

    closeWaterDateModal() {
        const modal = document.getElementById("water-date-modal");
        if (modal) modal.style.display = "none";
        this.currentWateringPlantId = null;
    },

    async handleWaterDateSubmit(e) {
        e.preventDefault();
        const plantId = this.currentWateringPlantId;
        if (!plantId) return;
        const onDate = document.getElementById("water-modal-date").value;
        const observer = document.getElementById("water-modal-observer").value.trim() || null;
        try {
            await ApiService.markPlantWatered(plantId, onDate, observer);
            this.closeWaterDateModal();
            this.notify(`💧 Plant #${plantId} watering date updated to ${onDate}.`);
            await this.loadWateringQueue();
            this.loadWaterKpi();
        } catch (err) {
            this.notify(`Could not update watering date: ${err.message}`, "error", 7000);
        }
    },

    markWatered(plantId, plantCode) {
        this.requireAuth(async () => {
            try {
                const res = await ApiService.markPlantWatered(plantId);
                this.notify(`💧 Marked ${plantCode || "plant #" + plantId} as watered today.`);
                await this.loadWateringQueue();
                this.loadWaterKpi();
            } catch (err) {
                this.notify(`Could not mark as watered: ${err.message}`, "error", 7000);
            }
        });
    },

    openAddPlantModal() {
        this.requireAuth(() => this._doOpenAddPlantModal());
    },

    _doOpenAddPlantModal() {
        this.editingPlantId = null;
        document.getElementById("plant-modal-title").textContent = "Add New Planted Plant Record";
        document.getElementById("plant-form").reset();
        document.getElementById("plant-modal").style.display = "flex";
    },

    openEditPlantModal(id) {
        this.requireAuth(() => this._doOpenEditPlantModal(id));
    },

    async _doOpenEditPlantModal(id) {
        try {
            const plant = await ApiService.getPlantedPlantById(id);
            if (!plant) return;

            this.editingPlantId = id;
            document.getElementById("plant-modal-title").textContent = `Edit Plant Record: ${plant.plant_code}`;
            
            document.getElementById("form-plant-code").value = plant.plant_code || "";
            document.getElementById("form-scientific-name").value = plant.scientific_name || "";
            document.getElementById("form-common-name").value = plant.common_name || "";
            document.getElementById("form-planted-on").value = plant.planted_on || "";
            document.getElementById("form-status").value = plant.status || "Alive";
            document.getElementById("form-latitude").value = plant.latitude || "";
            document.getElementById("form-longitude").value = plant.longitude || "";
            document.getElementById("form-zone-code").value = plant.zone_code || "";
            document.getElementById("form-watering-interval").value = plant.watering_interval_days ?? "";
            document.getElementById("form-last-watered-on").value = plant.last_watered_on || "";
            document.getElementById("form-notes").value = plant.notes || "";

            document.getElementById("plant-modal").style.display = "flex";
        } catch (err) {
            this.showErrorBanner(`Failed to fetch plant details: ${err.message}`);
        }
    },

    closePlantModal() {
        document.getElementById("plant-modal").style.display = "none";
    },

    async handlePlantFormSubmit(e) {
        e.preventDefault();

        const photoFileInput = document.getElementById("form-plant-photo-file");
        let uploadedPhotoUrl = null;
        if (photoFileInput && photoFileInput.files && photoFileInput.files.length > 0) {
            try {
                const uploadRes = await ApiService.uploadPhotoObservation(photoFileInput.files[0]);
                if (uploadRes && uploadRes.photo_url) {
                    uploadedPhotoUrl = uploadRes.photo_url;
                }
            } catch (uploadErr) {
                // Photo already stored for another observation: reuse its file
                if (uploadErr.duplicate && uploadErr.duplicate.photo_url) {
                    uploadedPhotoUrl = uploadErr.duplicate.photo_url;
                } else {
                    console.warn("Photo upload warning:", uploadErr);
                }
            }
        }

        const payload = {
            plant_code: document.getElementById("form-plant-code").value.trim(),
            scientific_name: document.getElementById("form-scientific-name").value.trim() || null,
            common_name: document.getElementById("form-common-name").value.trim() || null,
            planted_on: document.getElementById("form-planted-on").value || null,
            status: document.getElementById("form-status").value,
            latitude: parseFloat(document.getElementById("form-latitude").value),
            longitude: parseFloat(document.getElementById("form-longitude").value),
            zone_code: document.getElementById("form-zone-code").value || null,
            watering_interval_days: (() => {
                const v = document.getElementById("form-watering-interval").value;
                return v === "" ? null : parseInt(v, 10);
            })(),
            last_watered_on: document.getElementById("form-last-watered-on").value || null,
            notes: document.getElementById("form-notes").value.trim() || null,
            photo_url: uploadedPhotoUrl || document.getElementById("form-photo-url")?.value || null
        };

        try {
            if (this.editingPlantId) {
                await ApiService.updatePlantedPlant(this.editingPlantId, payload);
            } else {
                await ApiService.createPlantedPlant(payload);
            }

            this.closePlantModal();
            this.notify(`🌱 Plant ${payload.plant_code} ${this.editingPlantId ? "updated" : "added"}.`);
            await this.loadPlantedPlants();
            await this.loadOverview();
        } catch (err) {
            this.notify(`Could not save the plant record: ${err.message}`, "error", 7000);
        }
    },

    confirmDeletePlant(id, code) {
        this.requireAuth(() => this._doConfirmDeletePlant(id, code));
    },

    async _doConfirmDeletePlant(id, code) {
        if (confirm(`Are you sure you want to delete Planted Plant '${code}' (ID: ${id})?\n\nThis action cannot be undone.`)) {
            try {
                await ApiService.deletePlantedPlant(id);
                this.notify(`Plant ${code} deleted.`);
                await this.loadPlantedPlants();
                await this.loadOverview();
            } catch (err) {
                this.notify(`Could not delete the plant record: ${err.message}`, "error", 7000);
            }
        }
    },

    openMonitoringModal(plantId, plantCode) {
        this.requireAuth(() => this._doOpenMonitoringModal(plantId, plantCode));
    },

    _doOpenMonitoringModal(plantId, plantCode) {
        this.currentMonitoringPlantId = plantId;
        document.getElementById("plant-monitoring-form").reset();
        document.getElementById("monitoring-plant-subtitle").textContent = `Record a field visit for plant ${plantCode}. The plant's health status will be updated to what you record here.`;
        document.getElementById("mon-date").value = new Date().toISOString().split('T')[0];
        document.getElementById("plant-monitoring-modal").style.display = "flex";
    },

    closeMonitoringModal() {
        document.getElementById("plant-monitoring-modal").style.display = "none";
    },

    async handleMonitoringSubmit(e) {
        e.preventDefault();
        if (!this.currentMonitoringPlantId) return;

        const payload = {
            status: document.getElementById("mon-status").value,
            monitoring_date: document.getElementById("mon-date").value,
            observer: document.getElementById("mon-observer").value.trim() || "RSWF Field Team",
            notes: document.getElementById("mon-notes").value.trim() || null
        };

        try {
            await ApiService.addPlantMonitoringVisit(this.currentMonitoringPlantId, payload);
            this.closeMonitoringModal();
            this.notify(`✅ Visit saved. Plant health is now: ${payload.status}.`);
            await this.loadPlantedPlants();
            await this.loadOverview();
        } catch (err) {
            this.notify(`Could not save the visit: ${err.message}`, "error", 7000);
        }
    },

    async openPlantHistoryModal(plantId, plantCode) {
        document.getElementById("history-modal-title").textContent = `📋 ${plantCode} · Visit History`;
        document.getElementById("history-plant-subtitle").textContent = "All recorded health-check visits for this plant, newest first.";
        const tbody = document.getElementById("history-table-body");
        tbody.innerHTML = `<tr class="empty-row"><td colspan="4">Loading visit history...</td></tr>`;
        document.getElementById("plant-history-modal").style.display = "flex";

        try {
            const history = await ApiService.getPlantMonitoringHistory(plantId);
            if (!history || history.length === 0) {
                tbody.innerHTML = `<tr class="empty-row"><td colspan="4">No visits recorded yet. Use <b>➕ Visit</b> to record the first health check.</td></tr>`;
                return;
            }

            const sorted = [...history].sort((a, b) => String(b.monitoring_date).localeCompare(String(a.monitoring_date)));
            tbody.innerHTML = sorted.map(h => {
                const stClass = (h.status || "unknown").toLowerCase();
                return `
                    <tr>
                        <td style="white-space:nowrap"><b>${this.esc(h.monitoring_date)}</b></td>
                        <td><span class="status-badge ${this.esc(stClass)}">${this.esc(h.status)}</span></td>
                        <td>${this.esc(h.observer || "RSWF Field Team")}</td>
                        <td>${h.notes ? this.esc(h.notes) : '<span class="faint">No notes</span>'}</td>
                    </tr>
                `;
            }).join("");
        } catch (err) {
            tbody.innerHTML = `<tr class="empty-row"><td colspan="4" style="color:#f87171">Could not load history: ${this.esc(err.message)}</td></tr>`;
        }
    },

    closePlantHistoryModal() {
        document.getElementById("plant-history-modal").style.display = "none";
    },

    openAddNgoObsModal() {
        document.getElementById("ngo-obs-form").reset();
        document.getElementById("ngo-obs-modal").style.display = "flex";
    },

    closeNgoObsModal() {
        document.getElementById("ngo-obs-modal").style.display = "none";
    },

    async handleNgoObsSubmit(e) {
        e.preventDefault();

        const photoFileInput = document.getElementById("ngo-photo-file");
        let uploadedPhotoUrl = null;
        if (photoFileInput && photoFileInput.files && photoFileInput.files.length > 0) {
            try {
                const uploadRes = await ApiService.uploadPhotoObservation(photoFileInput.files[0]);
                if (uploadRes && uploadRes.photo_url) {
                    uploadedPhotoUrl = uploadRes.photo_url;
                }
            } catch (uploadErr) {
                // Photo already stored for another observation: reuse its file
                if (uploadErr.duplicate && uploadErr.duplicate.photo_url) {
                    uploadedPhotoUrl = uploadErr.duplicate.photo_url;
                } else {
                    console.warn("Photo upload warning:", uploadErr);
                }
            }
        }

        const payload = {
            scientific_name: document.getElementById("ngo-scientific-name").value.trim() || null,
            common_name: document.getElementById("ngo-common-name").value.trim() || null,
            observed_on: document.getElementById("ngo-observed-on").value || null,
            observer: document.getElementById("ngo-observer").value.trim() || "RSWF NGO Team",
            latitude: parseFloat(document.getElementById("ngo-latitude").value),
            longitude: parseFloat(document.getElementById("ngo-longitude").value),
            notes: document.getElementById("ngo-notes").value.trim() || null,
            photo_url: uploadedPhotoUrl || document.getElementById("ngo-photo-url")?.value || null
        };

        await this._submitNgoSighting(payload, { allowNearbyDuplicate: false });
    },

    // Shared submit used by both the initial save and the "record anyway" override
    // when the 1-metre same-plant guard fires.
    async _submitNgoSighting(payload, { allowNearbyDuplicate }) {
        try {
            const created = await ApiService.createNGOObservation(payload, { allowNearbyDuplicate });
            this.closeNgoObsModal();
            this.notify(`📝 Field sighting saved${created && created.id ? ` as observation #${created.id}` : ""}.`);
            await this.loadObservations();
            await this.loadOverview();
        } catch (err) {
            if (err && err.duplicate) {
                const d = err.duplicate;
                if (d.overridable) {
                    this._pendingNgoSightingPayload = payload;
                    const name = d.scientific_name ? `(${d.scientific_name})` : "";
                    const ok = confirm(
                        `A plant ${name} is already recorded within 1 metre of this spot as Observation #${d.existing_observation_id}.\n\n` +
                        `This is probably the same plant.\n\n` +
                        `Click OK only if two plants really do grow this close together, and you want to record a second one.`
                    );
                    if (ok) {
                        this.notify("Recording as a separate plant anyway...", "warning", 3000);
                        await this._submitNgoSighting(payload, { allowNearbyDuplicate: true });
                    } else {
                        this.closeNgoObsModal();
                        this.notify(`Linked to existing observation #${d.existing_observation_id} — no new record created.`);
                    }
                } else {
                    this.notify(`This observation already exists (#${d.existing_observation_id}).`, "warning", 7000);
                }
                return;
            }
            this.notify(`Could not save the field sighting: ${err.message}`, "error", 7000);
        }
    },

    // =====================================================================
    // Phase 8 — Dataset Export Download Handlers
    // =====================================================================

    downloadObsExport(format) {
        const source = document.getElementById("export-obs-source").value;
        const zone = document.getElementById("export-obs-zone").value;
        const quality = document.getElementById("export-obs-quality").value;

        const path = format === 'geojson' ? '/observations.geojson' : '/observations.csv';
        const url = ApiService.buildExportUrl(path, {
            source: source,
            zone: zone,
            quality_grade: quality
        });
        ApiService.triggerDownload(url);
    },

    downloadPlantedExport(format) {
        const status = document.getElementById("export-planted-status").value;
        const zone = document.getElementById("export-planted-zone").value;

        const path = format === 'geojson' ? '/planted-plants.geojson' : '/planted-plants.csv';
        const url = ApiService.buildExportUrl(path, {
            status: status,
            zone: zone
        });
        ApiService.triggerDownload(url);
    },

    downloadSpeciesExport() {
        const url = ApiService.buildExportUrl('/species.csv');
        ApiService.triggerDownload(url);
    },

    downloadCompletePackage() {
        const url = ApiService.buildExportUrl('/package.zip');
        ApiService.triggerDownload(url);
    },

    // Phase 14 — Conservation & SDG PDF Report Download Handlers
    downloadConservationReportPdf() {
        ApiService.downloadConservationReportPdf();
    },

    downloadSdgReportPdf() {
        ApiService.downloadSdgReportPdf();
    },

    // =====================================================================
    // Phase 9 — Photo Upload & EXIF GPS Modal Handlers
    // =====================================================================

    openUploadPhotoModal() {
        document.getElementById("upload-photo-form").reset();
        document.getElementById("upload-file-info").style.display = "none";
        document.getElementById("upload-status-indicator").style.display = "none";
        document.getElementById("upload-result-card").style.display = "none";
        document.getElementById("upload-result-preview").style.display = "none";
        // reset type selector to sighted
        const sightedRadio = document.getElementById("upload-type-sighted");
        if (sightedRadio) { sightedRadio.checked = true; this.onUploadTypeChange(); }
        document.getElementById("upload-photo-modal").style.display = "flex";
    },

    closeUploadPhotoModal() {
        document.getElementById("upload-photo-modal").style.display = "none";
    },

    handlePhotoSelectionChanged(e) {
        const fileInput = e.target;
        const fileInfo = document.getElementById("upload-file-info");
        if (fileInput.files && fileInput.files.length > 0) {
            const file = fileInput.files[0];
            fileInfo.textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
            fileInfo.style.display = "block";
        } else {
            fileInfo.style.display = "none";
        }
    },

    onUploadTypeChange() {
        const v = document.querySelector('input[name="upload-obs-type"]:checked')?.value || "sighted";
        const slbl = document.getElementById("upload-type-sighted-lbl");
        const plbl = document.getElementById("upload-type-planted-lbl");
        if (slbl) slbl.style.borderColor = v === "sighted" ? "#10b981" : "var(--border-color)";
        if (plbl) plbl.style.borderColor = v === "planted_rswf" ? "#10b981" : "var(--border-color)";
    },

    onBulkTypeChange() {
        const v = document.querySelector('input[name="bulk-obs-type"]:checked')?.value || "sighted";
        const slbl = document.getElementById("bulk-type-sighted-lbl");
        const plbl = document.getElementById("bulk-type-planted-lbl");
        if (slbl) slbl.style.borderColor = v === "sighted" ? "#10b981" : "var(--border-color)";
        if (plbl) plbl.style.borderColor = v === "planted_rswf" ? "#10b981" : "var(--border-color)";
    },

    async handlePhotoUploadSubmit(e) {
        e.preventDefault();
        const fileInput = document.getElementById("upload-photo-file");
        if (!fileInput.files || fileInput.files.length === 0) {
            this.notify("Please choose a photo to upload first.", "warning");
            return;
        }

        const file = fileInput.files[0];
        const obsType = document.querySelector('input[name="upload-obs-type"]:checked')?.value || "sighted";
        const statusInd = document.getElementById("upload-status-indicator");
        const resultCard = document.getElementById("upload-result-card");
        const resultTitle = document.getElementById("upload-result-title");
        const resultDetails = document.getElementById("upload-result-details");
        const resultPreview = document.getElementById("upload-result-preview");
        const confirmBox = document.getElementById("geotag-confirmation-box");
        const aiContainer = document.getElementById("upload-ai-trigger-container");
        const submitBtn = document.getElementById("btn-upload-submit");

        statusInd.style.display = "block";
        resultCard.style.display = "none";
        if (confirmBox) confirmBox.style.display = "none";
        if (aiContainer) aiContainer.style.display = "none";
        submitBtn.disabled = true;

        try {
            const res = await ApiService.uploadPhotoObservation(file, { obsType });
            statusInd.style.display = "none";
            submitBtn.disabled = false;

            if (res.photo_url) {
                const fullPhotoUrl = window.APP_CONFIG.getEndpoint(res.photo_url);
                resultPreview.src = fullPhotoUrl;
                resultPreview.alt = "Uploaded photo";
                resultPreview.onerror = () => { resultPreview.style.display = "none"; };
                resultPreview.style.display = "block";
            }

            // CASE 1: EXIF GPS (Detected from photo metadata)
            if (res.gps_source === "EXIF") {
                resultTitle.innerHTML = "✓ GPS Found";
                resultCard.style.background = "rgba(16, 185, 129, 0.1)";
                resultCard.style.borderColor = "rgba(16, 185, 129, 0.3)";
                resultTitle.style.color = "#10b981";

                resultDetails.innerHTML = `
                    <div style="font-weight:600;color:#10b981;margin-bottom:0.4rem">✓ GPS detected from photo metadata</div>
                    <div><b>Source:</b> GPS data stored in the photo</div>
                    <div><b>Latitude:</b> ${res.latitude.toFixed(6)}</div>
                    <div><b>Longitude:</b> ${res.longitude.toFixed(6)}</div>
                    <div><b>Zone Assignment:</b> <span style="color:#10b981;font-weight:600">${res.zone}</span></div>
                    <div><b>Observation ID:</b> #${res.observation_id}</div>
                    <div style="margin-top:0.4rem;color:#94a3b8">${res.message}</div>
                    ${this.nearbyObservationsNote(res)}
                `;

                if (confirmBox) confirmBox.style.display = "none";
                if (aiContainer) aiContainer.style.display = "flex";
                this.currentUploadedObsId = res.observation_id;
                if (res.plant_code) {
                    resultDetails.innerHTML += `<div style="margin-top:0.5rem;color:#f87171;font-weight:600">🌱 Registered for RSWF monitoring · Plant code: ${this.esc(res.plant_code)}. Species and planting date still need verification.</div>`;
                }

                await this.loadObservations();
                await this.loadOverview();
                if (this.map) await this.loadMapData();
            }
            // CASE 2: VISIBLE IMAGE GEOTAG (Detected from visible overlay - User Confirmation Required)
            else if (res.gps_source === "IMAGE_GEOTAG") {
                resultTitle.innerHTML = "✓ GPS Found";
                resultCard.style.background = "rgba(245, 158, 11, 0.1)";
                resultCard.style.borderColor = "rgba(245, 158, 11, 0.35)";
                resultTitle.style.color = "#fbbf24";

                resultDetails.innerHTML = `
                    <div style="font-weight:600;color:#fbbf24;margin-bottom:0.4rem">✓ GPS detected from image geotag</div>
                    <div><b>Source:</b> Visible Image Geotag</div>
                    <div><b>Latitude:</b> ${res.latitude.toFixed(6)}</div>
                    <div><b>Longitude:</b> ${res.longitude.toFixed(6)}</div>
                    <div><b>Zone Assignment:</b> <span style="color:#fbbf24;font-weight:600">${res.zone}</span></div>
                    <div style="margin-top:0.4rem;color:#cbd5e1">${res.message}</div>
                    ${this.nearbyObservationsNote(res)}
                `;

                this.pendingGeotagData = res;
                if (confirmBox) confirmBox.style.display = "block";
                if (aiContainer) aiContainer.style.display = "none";
            }
            // CASE 3: NO LOCATION
            else {
                resultTitle.innerHTML = "❌ Location not available";
                resultCard.style.background = "rgba(239, 68, 68, 0.1)";
                resultCard.style.borderColor = "rgba(239, 68, 68, 0.3)";
                resultTitle.style.color = "#ef4444";

                resultDetails.innerHTML = `
                    <div style="color:#f87171;font-weight:600;margin-bottom:0.25rem">No GPS metadata or visible geotag was detected in this photo.</div>
                    <div style="color:#94a3b8">GPS information could not be found in the photo metadata or visible image geotag. A valid spatial location within Van Udyan is required for biodiversity mapping.</div>
                `;
                resultPreview.style.display = "none";
                if (confirmBox) confirmBox.style.display = "none";
                if (aiContainer) aiContainer.style.display = "none";
            }

            resultCard.style.display = "block";

        } catch (err) {
            statusInd.style.display = "none";
            submitBtn.disabled = false;

            if (err.duplicate) {
                this.showDuplicateUploadResult(err.duplicate);
                return;
            }

            const isOutside = err.message && err.message.toLowerCase().includes("outside");

            resultTitle.innerHTML = isOutside ? "⚠️ Outside Project Boundary" : "❌ Location not available";
            resultCard.style.background = "rgba(239, 68, 68, 0.1)";
            resultCard.style.borderColor = "rgba(239, 68, 68, 0.3)";
            resultTitle.style.color = "#ef4444";

            resultDetails.innerHTML = `
                <div style="color:#f87171;font-weight:600;margin-bottom:0.25rem">${isOutside ? "Location is outside the Van Udyan project boundary." : "No GPS metadata or visible geotag was detected in this photo."}</div>
                <div style="color:#94a3b8">${err.message}</div>
            `;
            resultPreview.style.display = "none";
            if (confirmBox) confirmBox.style.display = "none";
            if (aiContainer) aiContainer.style.display = "none";
            resultCard.style.display = "block";
        }
    },

    async handleConfirmGeotagLocation() {
        if (!this.pendingGeotagData) {
            this.notify("There is no location waiting to be confirmed.", "warning");
            return;
        }

        const confirmBtn = document.getElementById("btn-confirm-location");
        const confirmBox = document.getElementById("geotag-confirmation-box");
        const aiContainer = document.getElementById("upload-ai-trigger-container");
        const resultTitle = document.getElementById("upload-result-title");
        const resultCard = document.getElementById("upload-result-card");
        const resultDetails = document.getElementById("upload-result-details");

        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = "⏳ Confirming & Saving Observation...";
        }

        try {
            const data = this.pendingGeotagData;
            const res = await ApiService.confirmGeotagLocation(
                data.photo_url,
                data.latitude,
                data.longitude,
                data.captured_at,
                "RSWF Field Volunteer",
                null,
                !!this.pendingGeotagAllowNearby,
                data.observation_type || "sighted",
            );
            this.pendingGeotagAllowNearby = false;

            this.currentUploadedObsId = res.observation_id;
            this.pendingGeotagData = null;
            if (res.plant_code) {
                this.notify(`🌱 Planted plant registered as ${res.plant_code}. Species and planting date still need RSWF verification.`, "success", 7000);
            }

            resultTitle.innerHTML = "✅ Photo Observation Spatially Verified & Saved!";
            resultCard.style.background = "rgba(16, 185, 129, 0.1)";
            resultCard.style.borderColor = "rgba(16, 185, 129, 0.3)";
            resultTitle.style.color = "#10b981";

            resultDetails.innerHTML = `
                <div style="font-weight:600;color:#10b981;margin-bottom:0.4rem">✓ Location Confirmed by User</div>
                <div><b>Source:</b> Visible Image Geotag (Confirmed)</div>
                <div><b>Observation ID:</b> #${res.observation_id}</div>
                <div><b>Latitude:</b> ${res.latitude.toFixed(6)}</div>
                <div><b>Longitude:</b> ${res.longitude.toFixed(6)}</div>
                <div><b>Zone Assignment:</b> <span style="color:#10b981;font-weight:600">${res.zone}</span></div>
                <div style="margin-top:0.4rem;color:#94a3b8">${res.message}</div>
                <div style="margin-top:0.75rem">
                    <button type="button" class="btn-primary btn-green btn-small" onclick="App.addCurrentUploadAsPlantedPlant()">
                        🌱 Also Add as Planted Plant (Track Watering & Monitoring)
                    </button>
                </div>
            `;

            if (confirmBox) confirmBox.style.display = "none";
            if (aiContainer) aiContainer.style.display = "flex";

            await this.loadObservations();
            await this.loadOverview();
            if (this.map) await this.loadMapData();

        } catch (err) {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = "Confirm Location";
            }
            if (err.duplicate) {
                this.pendingGeotagData = null;
                this.showDuplicateUploadResult(err.duplicate);
                return;
            }
            this.notify(`Could not confirm the location: ${err.message}`, "error", 7000);
        }
    },

    // Shown when the upload matches an existing record. Two flavours:
    //   - "exact": identical photo already uploaded. The existing record becomes the active one.
    //   - "nearby": a different photo within ~1 m of an existing plant. User can override.
    showDuplicateUploadResult(dup) {
        const resultCard = document.getElementById("upload-result-card");
        const resultTitle = document.getElementById("upload-result-title");
        const resultDetails = document.getElementById("upload-result-details");
        const resultPreview = document.getElementById("upload-result-preview");
        const confirmBox = document.getElementById("geotag-confirmation-box");
        const aiContainer = document.getElementById("upload-ai-trigger-container");

        const isNearby = dup.duplicate_kind === "nearby" || dup.overridable;

        resultTitle.innerHTML = isNearby
            ? "📍 Looks like the same plant"
            : "📋 This photo is already in the records";
        resultCard.style.background = "rgba(245, 158, 11, 0.08)";
        resultCard.style.borderColor = "rgba(245, 158, 11, 0.35)";
        resultTitle.style.color = "#fbbf24";

        const lat = typeof dup.latitude === "number" ? dup.latitude.toFixed(6) : dup.latitude;
        const lng = typeof dup.longitude === "number" ? dup.longitude.toFixed(6) : dup.longitude;
        const observedOn = dup.observed_on
            ? new Date(dup.observed_on + "T00:00:00").toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })
            : "—";
        const species = dup.scientific_name
            ? `<i>${dup.scientific_name}</i>${dup.identification_status === "verified" ? ' <span style="color:#10b981;font-weight:600">✓ Verified</span>' : ' <span style="color:#94a3b8">(unverified)</span>'}`
            : '<span style="color:#94a3b8">Not identified yet</span>';

        const row = (label, value) => `
            <div style="color:#94a3b8">${label}</div>
            <div style="color:#e2e8f0">${value}</div>`;

        const intro = isNearby
            ? `A plant is already recorded within <b>0.5 metres</b> of this spot as
                <b style="color:#fbbf24">Observation #${dup.existing_observation_id}</b>.
                This is probably the same plant from a different angle — the camera's GPS reading
                naturally wobbles by a metre or two. If so, no new record is needed.`
            : `You've uploaded this photo before. It's saved as
                <b style="color:#fbbf24">Observation #${dup.existing_observation_id}</b>,
                so no new record was added.`;

        const overrideBtn = isNearby ? `
            <div style="margin-top:0.75rem;display:flex;gap:0.5rem;flex-wrap:wrap;align-items:center">
                <button type="button" class="btn-primary btn-small" onclick="App.recordNearbyAnyway()" style="background:#f59e0b;color:#0f172a;font-weight:600">
                    ⚠️ This is a different plant — record anyway
                </button>
                <button type="button" class="btn-action" onclick="App.openObservationDetail(${Number(dup.existing_observation_id)})">
                    🔍 View Existing #${dup.existing_observation_id}
                </button>
            </div>` : `
            <div style="margin-top:0.75rem">
                <button type="button" class="btn-action" onclick="App.openObservationDetail(${Number(dup.existing_observation_id)})">
                    🔍 View Existing #${dup.existing_observation_id}
                </button>
            </div>`;

        resultDetails.innerHTML = `
            <div style="color:#e2e8f0;margin-bottom:0.75rem;line-height:1.5">${intro}</div>
            <div style="display:grid;grid-template-columns:max-content 1fr;gap:0.3rem 1rem;font-size:0.9rem;padding:0.6rem 0.75rem;background:rgba(15,23,42,0.45);border-radius:8px">
                ${row("Species", species)}
                ${row("Zone", `<span style="color:#fbbf24;font-weight:600">${dup.zone}</span>`)}
                ${row("Coordinates", `${lat}, ${lng}`)}
                ${row("Recorded on", observedOn)}
            </div>
            ${overrideBtn}
            <div style="margin-top:0.75rem;color:#94a3b8;font-size:0.85rem;line-height:1.5">
                To identify it again, use the <b style="color:#cbd5e1">Pl@ntNet AI</b> button below.
                To record a new sighting of a different plant, upload a photo from further away.
            </div>
        `;

        if (dup.photo_url) {
            resultPreview.src = window.APP_CONFIG.getEndpoint(dup.photo_url);
            resultPreview.alt = "Existing photo";
            resultPreview.onerror = () => { resultPreview.style.display = "none"; };
            resultPreview.style.display = "block";
        } else {
            resultPreview.style.display = "none";
        }

        this.currentUploadedObsId = dup.existing_observation_id;
        if (confirmBox) confirmBox.style.display = "none";
        if (aiContainer) aiContainer.style.display = "flex";
        resultCard.style.display = "block";
    },

    // Retries the upload with allow_nearby_duplicate=true so the backend records it as a new
    // plant even though it sits within the 1-metre same-plant guard.
    async recordNearbyAnyway() {
        const fileInput = document.getElementById("upload-photo-file");
        if (!fileInput || !fileInput.files || !fileInput.files.length) {
            this.notify("Please pick the photo again — the file was cleared.", "warning");
            return;
        }
        const file = fileInput.files[0];
        try {
            const res = await ApiService.uploadPhotoObservation(file, { allowNearbyDuplicate: true });
            if (res.requires_confirmation) {
                this.pendingGeotagData = res;
                this.pendingGeotagAllowNearby = true;
                this.notify("Confirm the location to finish saving the new plant.", "warning");
                document.getElementById("geotag-confirmation-box").style.display = "block";
                return;
            }
            this.notify(`✓ Recorded as Observation #${res.observation_id}.`);
            this.currentUploadedObsId = res.observation_id;
            await this.loadObservations();
            await this.loadOverview();
            if (this.map) await this.loadMapData();
            this.closeUploadPhotoModal();
        } catch (err) {
            this.notify(`Could not save: ${err.message}`, "error", 7000);
        }
    },

    // Note for results where other observations exist at (almost) the same coordinates.
    nearbyObservationsNote(res) {
        const ids = res.nearby_observation_ids || [];
        if (!ids.length) return "";
        return `<div style="margin-top:0.4rem;color:#fbbf24">⚠️ ${ids.length === 1 ? "Another observation exists" : "Other observations exist"} at the same location (${ids.map(id => "#" + id).join(", ")}). If this is the same plant, it may be a duplicate.</div>`;
    },

    // =====================================================================
    // Phase 10 — Pl@ntNet AI Identification & Verification Handlers
    // =====================================================================

    async triggerCurrentObsAI() {
        if (!this.currentUploadedObsId) {
            this.notify("Upload a photo first, then run the AI identification.", "warning");
            return;
        }

        const organ = document.getElementById("upload-organ-select").value || "auto";
        const aiCard = document.getElementById("ai-prediction-card");
        const aiList = document.getElementById("ai-predictions-list");
        const btnTrigger = document.getElementById("btn-trigger-ai");

        btnTrigger.disabled = true;
        btnTrigger.textContent = "⏳ Analyzing via Pl@ntNet AI...";
        aiCard.style.display = "block";
        aiList.innerHTML = `<div style="color:#a78bfa;font-size:0.85rem">Contacting Pl@ntNet REST API service...</div>`;

        try {
            const res = await ApiService.identifyObservationPlant(this.currentUploadedObsId, organ);
            btnTrigger.disabled = false;
            btnTrigger.textContent = "🤖 Re-run Pl@ntNet AI";

            if (!res.predictions || res.predictions.length === 0) {
                const errMsg = res.result_summary ? res.result_summary.message : "No predictions returned.";
                aiList.innerHTML = `<div style="color:#f87171;padding:0.5rem">⚠️ AI Identification Notice: ${errMsg}</div>`;
                return;
            }

            let html = "";
            res.predictions.forEach(p => {
                let badgeColor = "#ef4444"; // LOW
                let badgeBg = "rgba(239, 68, 68, 0.2)";
                if (p.confidence_level === "HIGH CONFIDENCE") {
                    badgeColor = "#10b981";
                    badgeBg = "rgba(16, 185, 129, 0.2)";
                } else if (p.confidence_level === "MEDIUM CONFIDENCE") {
                    badgeColor = "#f59e0b";
                    badgeBg = "rgba(245, 158, 11, 0.2)";
                }

                html += `
                    <div style="margin-bottom:0.75rem;padding:0.75rem;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:6px">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div>
                                <span style="font-weight:700;color:#c084fc">#${p.rank}</span>
                                <span style="font-weight:600;color:#fff;margin-left:0.4rem">${p.scientific_name}</span>
                                ${p.common_name ? `<span style="color:#94a3b8;font-size:0.8rem"> (${p.common_name})</span>` : ''}
                            </div>
                            <span class="status-badge" style="background:${badgeBg};color:${badgeColor};font-size:0.75rem">${p.confidence_level} (${p.confidence_percentage})</span>
                        </div>
                        
                        <div style="margin-top:0.4rem;background:rgba(255,255,255,0.1);height:6px;border-radius:3px;overflow:hidden">
                            <div style="width:${p.confidence_percentage};background:${badgeColor};height:100%"></div>
                        </div>

                        <div style="display:flex;justify-content:flex-end;gap:0.5rem;margin-top:0.6rem">
                            <button type="button" class="btn-action" style="font-size:0.75rem;padding:0.25rem 0.5rem;background:rgba(16,185,129,0.2);color:#34d399;border:1px solid rgba(16,185,129,0.4)" 
                                onclick="App.confirmAiPredictionRank(${this.currentUploadedObsId}, ${p.rank})">
                                ✅ Confirm #${p.rank} (${p.scientific_name})
                            </button>
                        </div>
                    </div>
                `;
            });

            // Action toolbar for manual correction or flagging review
            html += `
                <div style="display:flex;gap:0.5rem;margin-top:1rem;padding-top:0.75rem;border-top:1px solid rgba(255,255,255,0.1)">
                    <button type="button" class="btn-action" style="flex:1;font-size:0.8rem;background:rgba(59,130,246,0.2);color:#60a5fa;border:1px solid rgba(59,130,246,0.4)" onclick="App.toggleCorrectionForm()">
                        ✏️ Correct Identification
                    </button>
                    <button type="button" class="btn-action" style="flex:1;font-size:0.8rem;background:rgba(245,158,11,0.2);color:#fbbf24;border:1px solid rgba(245,158,11,0.4)" onclick="App.markNeedsReview(${this.currentUploadedObsId})">
                        ❓ Needs Expert Review
                    </button>
                </div>

                <!-- Manual Correction Form (Hidden by default) -->
                <div id="ai-correction-form" style="display:none;margin-top:1rem;padding:0.85rem;background:rgba(15,23,42,0.6);border:1px solid var(--border-color);border-radius:6px">
                    <div style="font-weight:600;color:#e2e8f0;font-size:0.85rem;margin-bottom:0.6rem">✏️ Manual Species Correction Form</div>
                    <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:0.5rem">
                        <input type="text" id="verif-correct-sci" placeholder="Scientific Name (Required, e.g. Moringa oleifera)" class="search-input" style="width:100%;font-size:0.8rem">
                        <input type="text" id="verif-correct-com" placeholder="Common Name (e.g. Drumstick Tree)" class="search-input" style="width:100%;font-size:0.8rem">
                    </div>
                    <input type="text" id="verif-correct-notes" placeholder="Correction Reason / Notes (Optional)" class="search-input" style="width:100%;font-size:0.8rem;margin-bottom:0.6rem">
                    <div style="display:flex;justify-content:flex-end;gap:0.5rem">
                        <button type="button" class="btn-action" style="font-size:0.75rem" onclick="App.toggleCorrectionForm()">Cancel</button>
                        <button type="button" class="btn-primary" style="font-size:0.75rem;background:linear-gradient(135deg,#3b82f6,#1d4ed8)" onclick="App.submitManualCorrection(${this.currentUploadedObsId})">Save Correction</button>
                    </div>
                </div>
            `;

            aiList.innerHTML = html;

        } catch (err) {
            btnTrigger.disabled = false;
            btnTrigger.textContent = "🤖 Run Pl@ntNet AI";
            aiList.innerHTML = `<div style="color:#f87171;padding:0.5rem">❌ AI Identification Error: ${err.message}</div>`;
        }
    },

    confirmAiPredictionRank(obsId, rank) {
        this.requireAuth(() => this._doConfirmAiPredictionRank(obsId, rank));
    },

    async _doConfirmAiPredictionRank(obsId, rank) {
        try {
            const res = await ApiService.verifyObservation(obsId, {
                decision: "confirm",
                selected_prediction_rank: rank
            });
            this.notify(`✅ Observation #${obsId} confirmed as ${res.scientific_name}.`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            this.notify(`Could not confirm the species: ${err.message}`, "error", 7000);
        }
    },

    toggleCorrectionForm() {
        const form = document.getElementById("ai-correction-form");
        if (form) {
            form.style.display = form.style.display === "none" ? "block" : "none";
        }
    },

    submitManualCorrection(obsId) {
        this.requireAuth(() => this._doSubmitManualCorrection(obsId));
    },

    async _doSubmitManualCorrection(obsId) {
        const sci = document.getElementById("verif-correct-sci")?.value?.trim();
        const com = document.getElementById("verif-correct-com")?.value?.trim();
        const notes = document.getElementById("verif-correct-notes")?.value?.trim();

        if (!sci) {
            this.notify("Please enter the correct scientific name.", "warning");
            return;
        }

        try {
            const res = await ApiService.verifyObservation(obsId, {
                decision: "correct",
                scientific_name: sci,
                common_name: com || null,
                notes: notes || null
            });
            this.notify(`✏️ Observation #${obsId} corrected to ${res.scientific_name}.`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            this.notify(`Could not save the correction: ${err.message}`, "error", 7000);
        }
    },

    markNeedsReview(obsId) {
        this.requireAuth(() => this._doMarkNeedsReview(obsId));
    },

    async _doMarkNeedsReview(obsId) {
        try {
            await ApiService.verifyObservation(obsId, {
                decision: "needs_review",
                notes: "Flagged by user for expert review"
            });
            this.notify(`❓ Observation #${obsId} flagged for expert review.`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            this.notify(`Could not update the status: ${err.message}`, "error", 7000);
        }
    },

    // =====================================================================
    // Observation details & species review
    // =====================================================================

    async openObservationDetail(obsId) {
        const modal = document.getElementById("obs-detail-modal");
        const body = document.getElementById("obs-detail-body");
        if (!modal || !body) return;
        if (this.leafletMap) this.leafletMap.closePopup();
        document.getElementById("obs-detail-title").textContent = `Observation #${obsId}`;
        body.innerHTML = `<div class="loading-text">Loading observation...</div>`;
        modal.style.display = "flex";
        try {
            const obs = await ApiService.getObservationById(obsId);
            this.currentDetailObs = obs;
            this.renderObservationDetail(obs);
        } catch (err) {
            body.innerHTML = `<div style="color:#f87171">Could not load observation #${Number(obsId)}: ${this.esc(err.message)}</div>`;
        }
    },

    closeObservationDetail() {
        const modal = document.getElementById("obs-detail-modal");
        if (modal) modal.style.display = "none";
        this.currentDetailObs = null;
    },

    renderObservationDetail(o, freshPredictions = null) {
        const body = document.getElementById("obs-detail-body");
        if (!body) return;
        const isNgo = o.source === "NGO / New Upload";
        const id = Number(o.id);

        const photo = o.photo_url && (isNgo || /^https?:\/\//i.test(o.photo_url)) ? this.photoSrc(o.photo_url) : "";
        const photoHtml = photo
            ? `<a href="${this.esc(photo)}" target="_blank" rel="noopener" title="Open full-size photo"><img class="detail-photo" src="${this.esc(photo)}" alt="Observation photo" onerror="App.replaceMissingPhoto(this.parentElement, 'detail-photo-empty', 'Photo file is missing on the server')"></a>`
            : `<div class="detail-photo-empty">${o.observation_url ? "Photo available on iNaturalist" : "No photo attached"}</div>`;

        const gpsSources = {
            EXIF: "GPS data stored in the photo",
            IMAGE_GEOTAG: "Printed location stamp on the photo (confirmed)"
        };
        const lat = typeof o.latitude === "number" ? o.latitude.toFixed(6) : o.latitude;
        const lng = typeof o.longitude === "number" ? o.longitude.toFixed(6) : o.longitude;
        const mapsUrl = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(lat + "," + lng)}`;

        const meta = [
            ["Status", this.statusBadge(o)],
            ["Source", this.sourceLabel(o.source)],
            ["Observed on", this.esc(o.observed_on || "—")],
            ["Observer", this.esc(o.observer || "—")],
            ["Zone", this.zoneLabel(o.zone)],
            ["Coordinates", `${this.esc(lat)}, ${this.esc(lng)} · <a href="${mapsUrl}" target="_blank" rel="noopener">Google Maps ↗</a>`],
            ["Location from", isNgo ? this.esc(gpsSources[o.gps_source] || o.gps_source || "Entered manually") : "iNaturalist record"],
            ["Confidence", o.identification_confidence ? this.esc({ high: "High", medium: "Medium", none: "Not identified" }[o.identification_confidence] || o.identification_confidence) : ""],
            ["iNaturalist", o.observation_url ? `<a href="${this.esc(o.observation_url)}" target="_blank" rel="noopener">View original record ↗</a>` : ""]
        ].filter(([, v]) => v);

        const suggestions = freshPredictions || o.ai_top_predictions || [];
        const canReview = isNgo;
        const suggestionHtml = suggestions.length ? suggestions.map(p => {
            const name = p.scientific_name || "";
            const nameArg = this.esc(JSON.stringify(name));
            const comArg = this.esc(JSON.stringify(p.common_name || ""));
            return `
                <div class="suggestion-row">
                    <span><b>${Number(p.rank) || ""}.</b> <i>${this.esc(name)}</i>${p.common_name ? ` <span class="muted">(${this.esc(p.common_name)})</span>` : ""}</span>
                    <span style="display:flex;align-items:center;gap:0.5rem">
                        <span class="conf">${this.esc(p.confidence_percentage || "")}</span>
                        ${canReview ? `<button type="button" class="btn-action success" style="margin:0" onclick="App.reviewConfirm(${id}, ${nameArg}, ${comArg})">Use this</button>` : ""}
                    </span>
                </div>`;
        }).join("") : `<div class="loading-text">No AI suggestions saved for this record yet.</div>`;

        const current = o.scientific_name ? this.esc(JSON.stringify(o.scientific_name)) : null;
        const currentCom = this.esc(JSON.stringify(o.common_name || ""));
        const reviewHtml = canReview ? `
            <div class="review-actions">
                ${current && !["verified", "corrected"].includes(o.identification_status)
                    ? `<button type="button" class="btn-primary btn-small" onclick="App.reviewConfirm(${id}, ${current}, ${currentCom})">✅ Confirm ${this.esc(o.scientific_name)}</button>` : ""}
                <button type="button" class="btn-primary btn-blue btn-small" onclick="App.toggleReviewCorrection()">✏️ Enter correct species</button>
                <button type="button" class="btn-action" onclick="App.reviewNeedsExpert(${id})">❓ Needs expert review</button>
                <button type="button" class="btn-action" id="btn-detail-rerun-ai" onclick="App.rerunDetailAI(${id})">🤖 ${suggestions.length ? "Re-run" : "Run"} Pl@ntNet AI</button>
                <button type="button" class="btn-primary btn-green btn-small" onclick="App.addObservationAsPlantedPlant(${id})" title="Track this plant for watering and health monitoring">🌱 Add as Planted Plant</button>
                <button type="button" class="btn-action delete" onclick="App.confirmDeleteObservation(${id})">🗑️ Delete</button>
            </div>
            <div id="review-correction-form" class="review-form" style="display:none">
                <div class="form-grid-2">
                    <div class="form-group"><label for="review-sci">Scientific name <span class="req">*</span></label><input type="text" id="review-sci" placeholder="e.g. Moringa oleifera" value="${this.esc(o.scientific_name || "")}"></div>
                    <div class="form-group"><label for="review-com">Common name</label><input type="text" id="review-com" placeholder="e.g. Drumstick tree" value="${this.esc(o.common_name || "")}"></div>
                </div>
                <div class="form-group"><label for="review-notes">Reason / notes</label><input type="text" id="review-notes" placeholder="e.g. Checked leaves and flowers in the field"></div>
                <div style="display:flex;justify-content:flex-end;gap:0.5rem">
                    <button type="button" class="btn-action" onclick="App.toggleReviewCorrection()">Cancel</button>
                    <button type="button" class="btn-primary btn-blue btn-small" onclick="App.reviewCorrect(${id})">Save species</button>
                </div>
            </div>
            <div class="form-hint">Confirming or correcting a species needs the RSWF admin password.</div>`
            : `<div class="note-card" style="margin-top:1rem">iNaturalist records are public reference data and are kept exactly as published, so they cannot be edited here.</div>`;

        body.innerHTML = `
            <div class="detail-layout">
                <div>${photoHtml}</div>
                <div>
                    <div class="detail-name">${o.scientific_name ? `<i>${this.esc(o.scientific_name)}</i>` : "Not identified yet"}</div>
                    ${o.common_name ? `<div class="detail-common">${this.esc(o.common_name)}</div>` : ""}
                    <dl class="detail-meta">${meta.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
                    ${isNgo ? `<div class="detail-section-title">${freshPredictions ? "New AI suggestions" : "AI suggestions (Pl@ntNet)"}</div>${suggestionHtml}` : ""}
                    ${o.verification_notes || o.notes ? `<div class="detail-section-title">Notes</div><div class="detail-notes">${this.esc(o.verification_notes || o.notes)}</div>` : ""}
                    ${reviewHtml}
                </div>
            </div>`;
    },


    // Convert observation into a planted plant record so it gets tracked for watering & monitoring
    addObservationAsPlantedPlant(obsId) {
        const o = this.currentDetailObs;
        if (!o) return;
        this.closeObservationDetail();
        this.openAddPlantModal();
        setTimeout(() => {
            const sci = document.getElementById("form-scientific-name");
            const com = document.getElementById("form-common-name");
            const lat = document.getElementById("form-latitude");
            const lng = document.getElementById("form-longitude");
            const zone = document.getElementById("form-zone-code");
            const photoUrl = document.getElementById("form-photo-url");
            const notes = document.getElementById("form-notes");

            if (sci && o.scientific_name) sci.value = o.scientific_name;
            if (com && o.common_name) com.value = o.common_name;
            if (lat && o.latitude) lat.value = o.latitude;
            if (lng && o.longitude) lng.value = o.longitude;
            if (zone && o.zone && o.zone !== "Outside Active Zones") zone.value = o.zone;
            if (photoUrl && o.photo_url) photoUrl.value = o.photo_url;
            if (notes) notes.value = `Recorded from Field Observation #${o.id}.`;
        }, 100);
    },

    // Convert freshly verified geotag upload into a planted plant record
    addCurrentUploadAsPlantedPlant() {
        const obsId = this.currentUploadedObsId;
        this.closeUploadPhotoModal();
        this.openAddPlantModal();
        if (obsId) {
            ApiService.getObservationById(obsId).then(o => {
                const sci = document.getElementById("form-scientific-name");
                const com = document.getElementById("form-common-name");
                const lat = document.getElementById("form-latitude");
                const lng = document.getElementById("form-longitude");
                const zone = document.getElementById("form-zone-code");
                const photoUrl = document.getElementById("form-photo-url");
                const notes = document.getElementById("form-notes");

                if (sci && o.scientific_name) sci.value = o.scientific_name;
                if (com && o.common_name) com.value = o.common_name;
                if (lat && o.latitude) lat.value = o.latitude;
                if (lng && o.longitude) lng.value = o.longitude;
                if (zone && o.zone && o.zone !== "Outside Active Zones") zone.value = o.zone;
                if (photoUrl && o.photo_url) photoUrl.value = o.photo_url;
                if (notes) notes.value = `Recorded from Geotagged Photo (Observation #${o.id}).`;
            }).catch(() => {});
        }
    },

    confirmDeleteObservation(obsId) {
        this.requireAuth(() => this._doConfirmDeleteObservation(obsId));
    },

    async _doConfirmDeleteObservation(obsId) {
        if (!confirm(`Are you sure you want to delete Observation #${obsId}? This action cannot be undone.`)) return;
        try {
            await ApiService.deleteObservation(obsId);
            this.notify(`✓ Observation #${obsId} deleted.`);
            this.closeObservationDetail();
            await this.loadObservations();
            await this.loadOverview();
            if (this.map) await this.loadMapData();
        } catch (err) {
            this.notify(`Could not delete observation: ${err.message}`, "error");
        }
    },

    toggleReviewCorrection() {
        const form = document.getElementById("review-correction-form");
        if (form) form.style.display = form.style.display === "none" ? "block" : "none";
    },

    async afterReview(obsId, message) {
        this.notify(message);
        const refreshed = await ApiService.getObservationById(obsId).catch(() => null);
        if (refreshed && document.getElementById("obs-detail-modal").style.display !== "none") {
            this.currentDetailObs = refreshed;
            this.renderObservationDetail(refreshed);
        }
        if (this.currentTab === "observations") await this.loadObservations();
        this.loadReviewCount();
    },

    reviewConfirm(obsId, scientificName, commonName) {
        this.requireAuth(async () => {
            try {
                const res = await ApiService.verifyObservation(obsId, {
                    decision: "confirm",
                    scientific_name: scientificName,
                    common_name: commonName || null
                });
                await this.afterReview(obsId, `✅ Observation #${obsId} confirmed as ${res.scientific_name || scientificName}.`);
            } catch (err) {
                this.notify(`Could not confirm the species: ${err.message}`, "error", 7000);
            }
        });
    },

    reviewCorrect(obsId) {
        const sci = document.getElementById("review-sci")?.value?.trim();
        const com = document.getElementById("review-com")?.value?.trim();
        const notes = document.getElementById("review-notes")?.value?.trim();
        if (!sci) {
            this.notify("Please enter the correct scientific name.", "warning");
            return;
        }
        this.requireAuth(async () => {
            try {
                const res = await ApiService.verifyObservation(obsId, {
                    decision: "correct",
                    scientific_name: sci,
                    common_name: com || null,
                    notes: notes || null
                });
                await this.afterReview(obsId, `✏️ Observation #${obsId} saved as ${res.scientific_name || sci}.`);
            } catch (err) {
                this.notify(`Could not save the species: ${err.message}`, "error", 7000);
            }
        });
    },

    reviewNeedsExpert(obsId) {
        this.requireAuth(async () => {
            try {
                await ApiService.verifyObservation(obsId, { decision: "needs_review", notes: "Flagged for expert review" });
                await this.afterReview(obsId, `❓ Observation #${obsId} flagged for expert review.`);
            } catch (err) {
                this.notify(`Could not update the status: ${err.message}`, "error", 7000);
            }
        });
    },

    async rerunDetailAI(obsId) {
        const btn = document.getElementById("btn-detail-rerun-ai");
        if (btn) { btn.disabled = true; btn.textContent = "⏳ Asking Pl@ntNet..."; }
        try {
            const res = await ApiService.identifyObservationPlant(obsId, "auto");
            if (!res.predictions || res.predictions.length === 0) {
                const msg = res.result_summary ? res.result_summary.message : "No suggestions returned.";
                this.notify(`Pl@ntNet: ${msg}`, "warning", 8000);
                if (btn) { btn.disabled = false; btn.textContent = "🤖 Re-run Pl@ntNet AI"; }
                return;
            }
            if (this.currentDetailObs && Number(this.currentDetailObs.id) === Number(obsId)) {
                this.renderObservationDetail(this.currentDetailObs, res.predictions);
            }
        } catch (err) {
            this.notify(`AI identification failed: ${err.message}`, "error", 7000);
            if (btn) { btn.disabled = false; btn.textContent = "🤖 Re-run Pl@ntNet AI"; }
        }
    },

    // Helpers
    showErrorBanner(msg) {
        const banner = document.getElementById("global-error-banner");
        if (banner) {
            banner.style.display = "flex";
            document.getElementById("global-error-message").textContent = msg;
        }
    },

    clearErrorBanner() {
        const banner = document.getElementById("global-error-banner");
        if (banner) banner.style.display = "none";
    },

    /* ================================================================
       Phase-15 features: weather, insights, verify queue, species
       profile, bulk upload, 3D terrain
       ================================================================ */

    // --- Live header clock (text-only tick, zero animation overhead) ---
    initHeaderClock() {
        const dateEl = document.getElementById("clock-date");
        const timeEl = document.getElementById("clock-time");
        if (!dateEl || !timeEl) return;
        const fmtDate = new Intl.DateTimeFormat("en-IN", { weekday: "short", month: "short", day: "numeric", timeZone: "Asia/Kolkata" });
        const fmtTime = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", second: "2-digit", hour12: true, timeZone: "Asia/Kolkata" });
        const tick = () => {
            const now = new Date();
            dateEl.textContent = fmtDate.format(now);
            timeEl.textContent = fmtTime.format(now);
        };
        tick();
        // align to the next whole second so the digit changes aren't jittery
        const msToNextSec = 1000 - (Date.now() % 1000);
        setTimeout(() => { tick(); setInterval(tick, 1000); }, msToNextSec);
    },

    // --- Weather pill (direct Open-Meteo fetch, no backend proxy) ---
    _wmoLabel(code) {
        const T = {
            0:["Clear","☀️"],1:["Mostly clear","🌤"],2:["Partly cloudy","⛅"],3:["Overcast","☁️"],
            45:["Fog","🌫"],48:["Rime fog","🌫"],
            51:["Light drizzle","🌦"],53:["Drizzle","🌦"],55:["Dense drizzle","🌧"],
            61:["Light rain","🌦"],63:["Rain","🌧"],65:["Heavy rain","🌧"],
            71:["Light snow","🌨"],73:["Snow","🌨"],75:["Heavy snow","❄️"],
            80:["Light showers","🌦"],81:["Showers","🌧"],82:["Violent showers","⛈"],
            95:["Thunderstorm","⛈"],96:["T-storm w/ hail","⛈"],99:["T-storm w/ heavy hail","⛈"]
        };
        const t = T[Number(code)] || ["", "🌡"];
        return { name: t[0], icon: t[1] };
    },

    async initWeatherPill() {
        try {
            const url = "https://api.open-meteo.com/v1/forecast?latitude=18.5195&longitude=73.7802"
                      + "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code,wind_speed_10m"
                      + "&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"
                      + "&past_days=7&forecast_days=4&timezone=Asia%2FKolkata";
            const res = await fetch(url, { cache: "no-store" });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            this._weather = await res.json();
        } catch (e) {
            this._weather = null;
            this._weatherErr = e.message;
        }
        this._renderWeatherPill();
        // Refresh every 20 minutes
        if (!this._weatherTimer) {
            this._weatherTimer = setInterval(() => this.initWeatherPill(), 20 * 60 * 1000);
        }
    },

    _renderWeatherPill() {
        const icon = document.getElementById("weather-icon");
        const temp = document.getElementById("weather-temp");
        const body = document.getElementById("weather-pop-body");
        if (!icon || !temp || !body) return;
        const w = this._weather;
        if (!w) {
            icon.textContent = "🌐";
            temp.textContent = "—°";
            body.innerHTML = `<div class="muted" style="padding:0.5rem 0">Weather feed unavailable. Retrying automatically.</div>`;
            return;
        }
        const cur = w.current || {};
        const dLabels = w.daily?.time || [];
        const rain = w.daily?.precipitation_sum || [];
        const tmax = w.daily?.temperature_2m_max || [];
        const tmin = w.daily?.temperature_2m_min || [];
        const codes = w.daily?.weather_code || [];
        const TODAY = 7;
        const nowLabel = this._wmoLabel(cur.weather_code);
        icon.textContent = nowLabel.icon;
        temp.textContent = `${Math.round(cur.temperature_2m ?? 0)}°`;

        const past = [], future = [];
        for (let i = 0; i < dLabels.length; i++) {
            const row = { date: dLabels[i], rain: Number(rain[i] || 0), tmax: tmax[i], tmin: tmin[i], label: this._wmoLabel(codes[i]) };
            (i < TODAY ? past : future).push(row);
        }
        // Scale: 0 bars = 0%, cap at 20mm = 100%
        const bars = past.map(d => {
            const mm = Math.max(0, d.rain || 0);
            const pct = Math.min(100, (mm / 20) * 100);
            const dl = new Date(d.date + "T00:00:00").toLocaleDateString(undefined, { weekday: "short" }).slice(0, 3);
            return `<div class="bar"><div class="track"><div class="fill" style="height:${pct}%"></div></div><div class="d">${dl}</div><div class="mm">${mm.toFixed(0)}</div></div>`;
        }).join("");
        const fc = future.slice(0, 3).map(d => `<div class="fc">
            <div class="d">${new Date(d.date + 'T00:00:00').toLocaleDateString(undefined,{weekday:'short'})}</div>
            <div class="ic">${d.label.icon}</div>
            <div class="t">${Math.round(d.tmax)}°/${Math.round(d.tmin)}°</div>
            <div class="r">${(d.rain || 0).toFixed(0)}mm</div>
        </div>`).join("");
        const rain24 = past.length ? past[past.length - 1].rain : 0;
        const rain7 = past.reduce((s, p) => s + (p.rain || 0), 0);
        const autoPause = rain24 >= 5;

        body.innerHTML = `
            <div class="wx-head">
                <div class="ic">${nowLabel.icon}</div>
                <div>
                    <div class="temp">${Math.round(cur.temperature_2m)}°C</div>
                    <div class="sub">${nowLabel.name} · ${Math.round(cur.relative_humidity_2m)}% RH · ${Math.round(cur.wind_speed_10m)} km/h</div>
                </div>
            </div>
            <div class="wx-label">Rain · last 7 days (mm)</div>
            <div class="wx-bars">${bars}</div>
            <div class="wx-label">Next 3 days</div>
            <div class="wx-fc">${fc}</div>
            <div class="wx-footer"><span>Week: <b>${rain7.toFixed(0)} mm</b></span><span>Last 24h: <b>${rain24.toFixed(1)} mm</b></span></div>
            ${autoPause ? `<div style="margin-top:0.6rem;padding:0.5rem 0.65rem;border:1px solid rgba(56,189,248,0.3);background:rgba(56,189,248,0.08);border-radius:8px;font-size:0.74rem;color:#BAE6FD">💧 Auto-pause suggested — ${rain24.toFixed(1)} mm in the last 24h.</div>` : ''}
        `;
    },

    /* ================================================================
       Plan Compliance (Sacred Grove / Devrai master grid audit)
       ================================================================ */
    async loadCompliance() {
        const kpi = document.getElementById("compliance-kpis");
        const grid = document.getElementById("compliance-grid");
        const mBody = document.getElementById("compliance-mismatch-body");
        const sBody = document.getElementById("compliance-spacing-body");
        const mCount = document.getElementById("compliance-mismatch-count");
        const sCount = document.getElementById("compliance-spacing-count");
        if (!kpi || !grid) return;

        try {
            const [audit, hmap, spacing] = await Promise.all([
                ApiService.getComplianceAudit(),
                ApiService.getComplianceHeatmap(),
                ApiService.getComplianceSpacingWarnings().catch(() => ({ pairs: [], min_distance_m: 6 })),
            ]);
            this._compliance = { audit, heatmap: hmap, spacing };
            const s = audit.summary || {};
            kpi.innerHTML = `
                <div class="kpi-card"><div class="kpi-label">Planted total</div><div class="kpi-value">${s.total || 0}</div><div class="kpi-subtext">with usable GPS</div></div>
                <div class="kpi-card"><div class="kpi-label">Correct</div><div class="kpi-value">${s.correct || 0}</div><div class="kpi-subtext">right species, right cell</div></div>
                <div class="kpi-card attention"><div class="kpi-label">Wrong / misplaced</div><div class="kpi-value">${(s.wrong_species || 0) + (s.misplaced_species || 0)}</div><div class="kpi-subtext">need review</div></div>
                <div class="kpi-card"><div class="kpi-label">Outside plot</div><div class="kpi-value">${s.outside_plot || 0}</div><div class="kpi-subtext">GPS not inside the 1-acre grid</div></div>
                <div class="kpi-card"><div class="kpi-label">Needs identification</div><div class="kpi-value">${s.needs_review || 0}</div><div class="kpi-subtext">species not verified yet</div></div>
            `;

            // Grid heatmap (SVG for crispness and tooltips)
            grid.innerHTML = this._renderPlanGrid(hmap.cells || []);

            // Mismatch table
            const bad = (audit.rows || []).filter(r => ["wrong_species", "misplaced_species", "needs_review"].includes(r.status));
            mCount.textContent = `${bad.length} issue${bad.length === 1 ? "" : "s"}`;
            if (!bad.length) {
                mBody.innerHTML = `<tr class="empty-row"><td colspan="6">No mismatches — every planted record matches the plan.</td></tr>`;
            } else {
                mBody.innerHTML = bad.map(r => {
                    const statusPill = r.status === "needs_review"
                        ? `<span class="pill pill-red">needs identification</span>`
                        : r.status === "wrong_species"
                        ? `<span class="pill pill-orange">wrong species</span>`
                        : `<span class="pill pill-blue">misplaced</span>`;
                    const should = r.rightful_cells_for_species && r.rightful_cells_for_species.length
                        ? r.rightful_cells_for_species.join(", ")
                        : `<span class="faint">not in plan</span>`;
                    return `<tr>
                        <td>${statusPill}</td>
                        <td><b>${this.esc(r.label || "")}</b></td>
                        <td><i>${this.esc(r.scientific_name || "—")}</i></td>
                        <td><i>${this.esc(r.prescribed_species || "—")}</i>${r.prescribed_marathi ? ` <span class="muted">(${this.esc(r.prescribed_marathi)})</span>` : ""}</td>
                        <td class="mono">${r.cell ?? "—"}</td>
                        <td class="mono">${should}</td>
                    </tr>`;
                }).join("");
            }

            // Spacing warnings
            const pairs = spacing.pairs || [];
            sCount.textContent = `${pairs.length} pair${pairs.length === 1 ? "" : "s"} too close`;
            if (!pairs.length) {
                sBody.innerHTML = `<div class="muted" style="padding:0.5rem">No large-canopy pairs are closer than ${spacing.min_distance_m} m.</div>`;
            } else {
                sBody.innerHTML = `<div style="display:flex;flex-direction:column;gap:0.5rem">${
                    pairs.slice(0, 50).map(p => `
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:0.75rem;padding:0.6rem 0.8rem;border:1px solid var(--v-stroke);border-radius:10px;background:var(--v-ink-3)">
                            <div><b>${this.esc(p.a.label)}</b> <i class="muted">${this.esc(p.a.scientific_name || "—")}</i> ↔ <b>${this.esc(p.b.label)}</b> <i class="muted">${this.esc(p.b.scientific_name || "—")}</i></div>
                            <div class="mono" style="color:#F97316;font-weight:700">${p.distance_m} m</div>
                        </div>
                    `).join("")
                }</div>`;
            }
        } catch (e) {
            kpi.innerHTML = `<div class="kpi-card"><div class="kpi-label">Error</div><div class="kpi-subtext">${this.esc(e.message)}</div></div>`;
        }
    },

    _renderPlanGrid(cells) {
        if (!cells || !cells.length) return `<div class="muted">No grid data.</div>`;
        // 20x20. We render as a CSS grid with 400 cells, colour by status.
        const legend = (st) => ({
            correct: "#22C55E",
            wrong: "#F97316",
            needs_review: "#EF4444",
            missing: "rgba(255,255,255,0.06)",
            non_plantable: "#64748B",
            void: "rgba(255,255,255,0.02)",
        }[st] || "rgba(255,255,255,0.04)");
        return cells.map(c => {
            const label = c.prescribed || (c.note ? c.note : "·");
            const title = `Cell ${c.cell} · ${c.prescribed_type || ""}
Should be: ${c.prescribed || c.note || "—"}
${c.occupants && c.occupants.length ? "Here: " + c.occupants.map(o => (o.scientific_name || "unknown") + " [" + o.label + "]").join(", ") : "No plant recorded"}
Status: ${c.status}`;
            const txt = c.prescribed ? (c.prescribed.split(" ").map(w => w[0]).slice(0, 2).join("").toUpperCase()) : (c.note ? c.note[0] : "");
            return `<div class="plan-cell" data-cell="${c.cell}" data-status="${c.status}" style="background:${legend(c.status)}" title="${title.replace(/"/g, '&quot;')}"><span class="num">${c.cell}</span><span class="lbl">${txt}</span></div>`;
        }).join("");
    },

    exportComplianceCsv() {
        const audit = this._compliance?.audit;
        if (!audit) { this.notify("Open the Plan Compliance tab first to load data.", "error"); return; }
        const rows = audit.rows || [];
        const header = ["id","source","label","scientific_name","cell","prescribed_species","status","rightful_cells","latitude","longitude","zone_code"];
        const csv = [header.join(",")].concat(rows.map(r => [
            r.id, r.source, r.label,
            `"${(r.scientific_name || "").replace(/"/g, '""')}"`,
            r.cell ?? "",
            `"${(r.prescribed_species || "").replace(/"/g, '""')}"`,
            r.status,
            (r.rightful_cells_for_species || []).join(";"),
            r.latitude, r.longitude, r.zone_code || ""
        ].join(","))).join("\n");
        const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `van-udyan-compliance-${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
    },

    async openCalibrationModal() {
        try {
            const cal = await ApiService.getComplianceCalibration();
            const c = cal.corners || {};
            document.getElementById("cal-nw-lat").value = c.nw?.lat ?? "";
            document.getElementById("cal-nw-lon").value = c.nw?.lon ?? "";
            document.getElementById("cal-ne-lat").value = c.ne?.lat ?? "";
            document.getElementById("cal-ne-lon").value = c.ne?.lon ?? "";
            document.getElementById("cal-se-lat").value = c.se?.lat ?? "";
            document.getElementById("cal-se-lon").value = c.se?.lon ?? "";
            document.getElementById("cal-sw-lat").value = c.sw?.lat ?? "";
            document.getElementById("cal-sw-lon").value = c.sw?.lon ?? "";
            document.getElementById("cal-spacing").value = cal.spacing_rules?.large_canopy_min_m ?? 6;
            document.getElementById("calibration-modal").style.display = "flex";
        } catch (e) {
            this.notify(`Could not load calibration: ${e.message}`, "error", 7000);
        }
    },
    closeCalibrationModal() { document.getElementById("calibration-modal").style.display = "none"; },

    async saveCalibration(ev) {
        ev.preventDefault();
        if (!ApiService.getNgoPassword()) { this.openAuthModal(); return; }
        const num = (id) => parseFloat(document.getElementById(id).value);
        const payload = {
            corners: {
                nw: { lat: num("cal-nw-lat"), lon: num("cal-nw-lon") },
                ne: { lat: num("cal-ne-lat"), lon: num("cal-ne-lon") },
                se: { lat: num("cal-se-lat"), lon: num("cal-se-lon") },
                sw: { lat: num("cal-sw-lat"), lon: num("cal-sw-lon") },
            },
            grid: { rows: 20, cols: 20 },
            cell_side_m: 3.048,
            spacing_rules: { large_canopy_min_m: num("cal-spacing") || 6.0 },
            updated_at: new Date().toISOString().slice(0, 10),
        };
        try {
            await ApiService.updateComplianceCalibration(payload);
            this.notify("Calibration saved. Reloading audit…");
            this.closeCalibrationModal();
            await this.loadCompliance();
        } catch (e) {
            this.notify(`Could not save calibration: ${e.message}`, "error", 7000);
        }
    },

    _setWeatherPopOpen(open) {
        const btn = document.getElementById("header-weather");
        const pop = document.getElementById("weather-pop");
        if (!btn || !pop) return;
        pop.classList.toggle("open", open);
        btn.setAttribute("aria-expanded", String(open));
        pop.setAttribute("aria-hidden", String(!open));
    },

    toggleWeatherPill(ev) {
        if (ev) ev.stopPropagation();
        const pop = document.getElementById("weather-pop");
        if (!pop) return;
        this._setWeatherPopOpen(!pop.classList.contains("open"));
        if (this._weatherOutsideBound) return;
        this._weatherOutsideBound = true;
        document.addEventListener("click", (e) => {
            const p = document.getElementById("weather-pop");
            const b = document.getElementById("header-weather");
            if (p && p.classList.contains("open") && !p.contains(e.target) && !(b && b.contains(e.target))) {
                this._setWeatherPopOpen(false);
            }
        });
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                const p = document.getElementById("weather-pop");
                if (p && p.classList.contains("open")) this._setWeatherPopOpen(false);
            }
        });
    },

    // --- iNaturalist Upload Queue (replaces old Verification Queue) ---
    async loadInatUploadQueue() {
        const empty = document.getElementById("inat-queue-empty");
        const list = document.getElementById("inat-queue-list");
        const selectBar = document.getElementById("inat-select-bar");
        const reviewBtn = document.getElementById("btn-review-inat");
        if (!empty || !list) return;
        empty.style.display = "block";
        empty.innerHTML = `<div class="muted">Loading…</div>`;
        list.innerHTML = "";
        if (selectBar) selectBar.style.display = "none";
        if (reviewBtn) reviewBtn.style.display = "none";
        const approvalPanel = document.getElementById("inat-approval-panel");
        if (approvalPanel) approvalPanel.style.display = "none";
        try {
            const connection = await ApiService.getInaturalistStatus();
            this.updateInatConnectionUI(connection);
            // Only RSWF-owned planted-tree records belong in this workflow.
            // The API caps a page at 200 records. Fetch all pages so older planted
            // records are not silently missing from the upload queue.
            const records = await this.fetchAllPages(
                (params) => ApiService.getObservations({ ...params, source: "NGO / New Upload" })
            );
            const items = records.filter(o =>
                o.source !== "iNaturalist" && o.observation_type === "planted_rswf"
            );
            this._inatQueue = items;
            if (!items.length) {
                empty.innerHTML = `<div style="font-size:2.5rem;margin-bottom:0.5rem">🌱</div><div>No RSWF planted-tree uploads found. Upload a tree photo and mark it as <strong>Planted by RSWF</strong>. After an NGO reviewer verifies its species, it will appear here.</div>`;
                return;
            }
            empty.style.display = "none";
            if (selectBar) selectBar.style.display = "flex";
            list.innerHTML = `
                <div class="table-scroll">
                <table class="data-table">
                    <thead><tr>
                        <th style="width:2rem"></th>
                        <th>Photo</th>
                        <th>Species</th>
                        <th>Type</th>
                        <th>Date</th>
                        <th>Zone</th>
                        <th>Verification / iNaturalist</th>
                        <th>Actions</th>
                    </tr></thead>
                    <tbody id="inat-queue-tbody">${items.map((o, i) => this._inatQueueRow(o, i)).join("")}</tbody>
                </table>
                </div>`;
            this._updateInatSelectedCount();
        } catch (e) {
            empty.style.display = "block";
            empty.innerHTML = `<div class="muted">Could not load the iNaturalist queue: ${this.esc(e.message)}</div>`;
            this.notify("Could not refresh the iNaturalist connection or queue.", "error");
        }
    },

    updateInatConnectionUI(connection) {
        this._inatConnected = Boolean(connection && connection.connected);
        const indicator = document.getElementById("inat-connection-indicator");
        const status = document.getElementById("inat-connection-status");
        const button = document.getElementById("btn-connect-inat");
        if (indicator) {
            indicator.className = this._inatConnected ? "pill pill-green" : "pill pill-grey";
            indicator.textContent = this._inatConnected ? "✓ Connected" : (connection && connection.configured ? "Not connected" : "Setup required");
        }
        if (status) {
            status.textContent = this._inatConnected
                ? `Authorized account: ${connection.username || "iNaturalist"}. Publishing still requires NGO approval.`
                : (connection && connection.configured
                    ? "Connect the authorized NGO iNaturalist account to enable the approval and upload step."
                    : `Backend setup is required. Missing/invalid settings: ${(connection && connection.missing_configuration || []).join(", ") || "check the backend logs"}.`);
        }
        if (button) {
            button.textContent = this._inatConnected ? "↻ Reconnect iNaturalist" : "🔗 Connect iNaturalist";
            button.disabled = !(connection && connection.configured);
            button.title = button.disabled ? "iNaturalist OAuth environment settings are missing on the backend." : "Authorize Nature Copilot using iNaturalist's official sign-in page.";
        }
    },

    _inatQueueRow(o, i) {
        const photo = o.photo_url
            ? `<img src="${this.esc(this.thumbSrc(o.photo_url))}" alt="Tree photo" style="width:52px;height:52px;object-fit:cover;border-radius:6px;border:1px solid var(--v-stroke)" onerror="this.outerHTML='<span class=&quot;muted&quot;>no photo</span>'">`
            : `<span class="muted">📷</span>`;
        const typeLabel = `<span class="pill pill-green">🌱 Planted</span>`;
        const status = String(o.identification_status || o.verification_status || "pending").toLowerCase();
        const verified = ["verified", "corrected"].includes(String(o.identification_status || "").toLowerCase());
        const uploadState = String(o.inaturalist_upload_status || "").toLowerCase();
        const hasRemoteRecord = Boolean(o.observation_url || o.inaturalist_observation_id);
        const remoteId = String(o.inaturalist_observation_id || ((o.observation_url || "").match(/\/observations\/(\d+)/) || [])[1] || "");
        const editUrl = /^\d+$/.test(remoteId) ? `https://www.inaturalist.org/observations/${remoteId}/edit` : "";
        const uploaded = uploadState === "published" || (hasRemoteRecord && uploadState !== "photo_failed");
        const statusBadge = uploaded
            ? `<span class="pill pill-green">✓ Published to iNaturalist</span>`
            : uploadState === "publishing" || uploadState === "photo_uploading"
                ? `<span class="pill pill-orange">⏳ Publishing…</span>`
                : uploadState === "photo_failed"
                    ? `<span class="pill pill-orange" title="${this.esc(o.inaturalist_upload_error || "Photo upload failed")}">⚠ Remote record exists · retry photo</span>`
                    : uploadState === "failed"
                        ? `<span class="pill pill-orange" title="${this.esc(o.inaturalist_upload_error || "Upload failed")}">⚠ Upload failed · retry available</span>`
                        : ["verified", "corrected", "confirmed"].includes(status)
                            ? `<span class="pill pill-green">${status === "corrected" ? "Corrected & verified" : "Verified"}</span>`
                            : status === "needs_review"
                                ? `<span class="pill pill-orange">⚠️ Needs review</span>`
                                : `<span class="pill pill-grey">Pending verification</span>`;
        const selectDisabled = !verified || uploaded || ["publishing", "photo_uploading"].includes(uploadState);
        const selectTitle = uploaded
            ? "Already published to iNaturalist"
            : uploadState === "publishing"
                ? "This record is currently publishing"
                : "NGO verification is required before publishing";
        return `<tr id="inat-row-${i}">
            <td><input type="checkbox" class="inat-select-cb" data-idx="${i}" data-id="${o.id}" ${selectDisabled ? `disabled title="${selectTitle}"` : ""} onchange="App._updateInatSelectedCount()"></td>
            <td>${photo}</td>
            <td style="font-size:0.82rem">${this.esc(o.scientific_name || '—')}<br><span class="muted">${this.esc(o.common_name || '')}</span></td>
            <td>${typeLabel}</td>
            <td style="font-size:0.82rem">${this.esc(o.observed_on || '—')}</td>
            <td style="font-size:0.82rem">${this.esc(o.zone || '—')}</td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn-action" style="font-size:0.78rem" onclick="App.openObservationDetail(${Number(o.id)})">View</button>
                ${o.observation_url ? `<a class="btn-action" style="font-size:0.78rem;display:inline-block;text-decoration:none" href="${this.esc(o.observation_url)}" target="_blank" rel="noopener">View iNaturalist record ↗</a>` : `<button class="btn-action" style="font-size:0.78rem" onclick="App.linkInaturalistRecord(${Number(o.id)})">Link existing record</button>`}
                ${editUrl ? `<a class="btn-action" style="font-size:0.78rem;display:inline-block;text-decoration:none" href="${editUrl}" target="_blank" rel="noopener" title="Edit the published observation on iNaturalist. The original NGO register remains unchanged.">Edit on iNaturalist ↗</a>` : ""}
                ${!verified && !uploaded ? `<button class="btn-primary" style="font-size:0.78rem;padding:0.25rem 0.6rem" onclick="App._inatQuickConfirm(${i})">Confirm</button>` : ""}
            </td>
        </tr>`;
    },

    _updateInatSelectedCount() {
        const cbs = document.querySelectorAll(".inat-select-cb:checked:not(:disabled)");
        const el = document.getElementById("inat-selected-count");
        if (el) el.textContent = `${cbs.length} selected`;
        const allCb = document.getElementById("inat-select-all");
        const totalCbs = document.querySelectorAll(".inat-select-cb:not(:disabled)");
        if (allCb) allCb.indeterminate = cbs.length > 0 && cbs.length < totalCbs.length;
        if (allCb) allCb.checked = totalCbs.length > 0 && cbs.length === totalCbs.length;
        const reviewBtn = document.getElementById("btn-review-inat");
        if (reviewBtn) reviewBtn.style.display = cbs.length > 0 ? "inline-block" : "none";
    },

    inatToggleSelectAll(checked) {
        document.querySelectorAll(".inat-select-cb:not(:disabled)").forEach(cb => cb.checked = checked);
        this._updateInatSelectedCount();
    },

    async _inatQuickConfirm(idx) {
        const o = (this._inatQueue || [])[idx];
        if (!o) return;
        if (!ApiService.getNgoPassword()) { this.openAuthModal(); return; }
        try {
            await ApiService.verifyObservation(o.id, { decision: "confirm" });
            this.notify(`Observation #${o.id} confirmed ✔`, "success");
            await this.loadInatUploadQueue();
        } catch (e) { this.notify(`Failed: ${e.message}`, "error"); }
    },

    async linkInaturalistRecord(obsId) {
        if (!ApiService.getNgoPassword()) { this.openAuthModal(); return; }
        const url = window.prompt("After submitting on iNaturalist, paste the new observation URL (https://www.inaturalist.org/observations/123456).");
        if (url === null) return;
        const clean = url.trim();
        if (!/^https:\/\/www\.inaturalist\.org\/observations\/\d+(?:[?#].*)?$/.test(clean)) {
            this.notify("Enter a valid iNaturalist observation URL.", "warning");
            return;
        }
        try {
            await ApiService.updateObservation(obsId, { observation_url: clean });
            this.notify("iNaturalist record link saved. Use “Manage on iNaturalist” to edit or delete it on iNaturalist.", "success", 7000);
            await this.loadInatUploadQueue();
        } catch (e) {
            this.notify(`Could not save iNaturalist link: ${e.message}`, "error");
        }
    },

    async connectInaturalist() {
        if (!ApiService.getNgoPassword()) {
            this.openAuthModal(() => this.connectInaturalist());
            return;
        }
        try {
            const status = await ApiService.getInaturalistStatus();
            this.updateInatConnectionUI(status);
            if (!status.configured) {
                this.notify("iNaturalist OAuth is not configured on the backend yet. See docs/inaturalist_publishing.md and add the required Render environment variables.", "warning", 9000);
                return;
            }
            const result = await ApiService.startInaturalistConnection();
            if (!result || !result.authorization_url) throw new Error("The backend did not return an iNaturalist authorization URL.");
            window.location.href = result.authorization_url;
        } catch (e) {
            this.notify(`Could not start iNaturalist sign-in: ${e.message}`, "error", 7000);
        }
    },

    _getSelectedInatRecords() {
        const ids = Array.from(document.querySelectorAll(".inat-select-cb:checked")).map(cb => String(cb.dataset.id));
        return (this._inatQueue || []).filter(o =>
            ids.includes(String(o.id)) &&
            o.observation_type === "planted_rswf" &&
            ((!o.observation_url && !o.inaturalist_observation_id) || String(o.inaturalist_upload_status || "").toLowerCase() === "photo_failed") &&
            ["verified", "corrected"].includes(String(o.identification_status || "").toLowerCase()) &&
            !["publishing", "photo_uploading", "published"].includes(String(o.inaturalist_upload_status || "").toLowerCase())
        );
    },

    reviewSelectedForInat() {
        if (!this._inatConnected) {
            this.notify("Connect an iNaturalist account before reviewing records for publication.", "warning", 7000);
            return;
        }
        const items = this._getSelectedInatRecords();
        if (!items.length) {
            this.notify("Select at least one eligible, verified planted-tree record.", "warning");
            return;
        }
        this._inatReviewItems = items;
        const panel = document.getElementById("inat-approval-panel");
        const container = document.getElementById("inat-approval-records");
        const progress = document.getElementById("inat-upload-progress");
        if (!panel || !container) return;
        if (progress) progress.textContent = "";
        container.innerHTML = items.map(o => {
            const photo = o.photo_url ? `<img src="${this.esc(this.thumbSrc(o.photo_url))}" alt="Tree photo" style="width:92px;height:92px;object-fit:cover;border-radius:8px">` : "";
            return `<div class="panel" style="display:flex;gap:1rem;align-items:flex-start;flex-wrap:wrap">
                ${photo}
                <div style="flex:1;min-width:180px">
                    <strong>${this.esc(o.scientific_name || "Unknown species")}</strong>
                    <div class="muted" style="font-size:0.84rem">${this.esc(o.common_name || "")}</div>
                    <div style="margin-top:0.4rem;font-size:0.85rem">Date: ${this.esc(o.observed_on || "Missing date")} · Zone: ${this.esc(o.zone || "—")}</div>
                    <div style="font-size:0.85rem">GPS: ${this.esc(o.latitude)} , ${this.esc(o.longitude)}</div>
                    <div class="muted" style="font-size:0.82rem;margin-top:0.35rem">Record #${this.esc(o.id)} · NGO verification: ${this.esc(o.identification_status)}</div>
                    ${o.notes ? `<p style="font-size:0.84rem;margin:0.4rem 0 0">${this.esc(o.notes)}</p>` : ""}
                </div>
            </div>`;
        }).join("");
        panel.style.display = "block";
        panel.scrollIntoView({ behavior: "smooth", block: "start" });
    },

    cancelInatReview() {
        this._inatReviewItems = [];
        const panel = document.getElementById("inat-approval-panel");
        if (panel) panel.style.display = "none";
    },

    async approveAndUploadToInat() {
        if (!this._inatConnected) {
            this.notify("Reconnect your iNaturalist account before publishing.", "warning");
            return;
        }
        const items = this._inatReviewItems || [];
        if (!items.length) {
            this.notify("Review selected records before approving.", "warning");
            return;
        }
        if (!ApiService.getNgoPassword()) {
            this.openAuthModal(() => this.approveAndUploadToInat());
            return;
        }
        const names = items.map(o => o.scientific_name || `#${o.id}`).join(", ");
        if (!window.confirm(`Approve and publish ${items.length} observation(s) to iNaturalist under the connected account?\n\n${names}\n\nThe photo and GPS coordinates will be sent to iNaturalist.`)) return;

        const approveButton = document.getElementById("btn-approve-upload-inat");
        const progress = document.getElementById("inat-upload-progress");
        if (approveButton) approveButton.disabled = true;
        const results = [];
        try {
            for (let index = 0; index < items.length; index++) {
                const item = items[index];
                if (progress) progress.textContent = `Publishing ${index + 1} of ${items.length}: ${item.scientific_name || "observation"}…`;
                try {
                    const result = await ApiService.publishInaturalistObservation(item.id);
                    results.push({ ok: true, item, result });
                } catch (error) {
                    results.push({ ok: false, item, error });
                }
            }
            const success = results.filter(r => r.ok);
            const failed = results.filter(r => !r.ok);
            if (progress) {
                progress.textContent = [
                    ...success.map(r => `✓ ${r.item.scientific_name || "#" + r.item.id}: ${r.result.observation_url}`),
                    ...failed.map(r => `⚠ ${r.item.scientific_name || "#" + r.item.id}: ${r.error.message}`)
                ].join(" · ");
            }
            if (success.length) this.notify(`Published ${success.length} observation(s) to iNaturalist.`, "success", 7000);
            if (failed.length) this.notify(`${failed.length} observation(s) failed. Check their status and retry after fixing the issue.`, "warning", 8000);
            await this.loadInatUploadQueue();
            this._inatReviewItems = [];
            const panel = document.getElementById("inat-approval-panel");
            if (panel) panel.style.display = "none";
        } finally {
            if (approveButton) approveButton.disabled = false;
        }
    },

    // Keep old verification queue functions for backward compat (no longer shown in nav)
    async loadVerificationQueue() { await this.loadInatUploadQueue(); },

    // --- Per-species profile modal ---
    async openSpeciesProfile(scientificName) {
        document.getElementById("species-profile-modal").style.display = "flex";
        document.getElementById("species-profile-title").textContent = scientificName;
        const body = document.getElementById("species-profile-body");
        body.innerHTML = `<div class="muted">Loading profile…</div>`;
        try {
            const p = await ApiService.getSpeciesProfile(scientificName);
            if (!p.found) { body.innerHTML = `<div class="muted">No records found for ${scientificName}.</div>`; return; }
            const rarityColor = {rare:'#F97316', uncommon:'#FACC15', common:'#22C55E', very_common:'#4ADE80'}[p.rarity] || '#A6B8AD';
            const zones = (p.zones || []).map(z => `<span class="pill pill-green">${z.zone} · ${z.count}</span>`).join(" ");
            const phenBars = (p.phenology || []).map(m => {
                const h = Math.min(60, m.count * 4);
                const monthLabel = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m.month - 1];
                return `<div style="display:flex;flex-direction:column;align-items:center;gap:3px;min-width:30px">
                    <div style="height:60px;display:flex;align-items:flex-end"><div style="width:14px;height:${h}px;border-radius:3px;background:#22C55E" title="${m.count} obs"></div></div>
                    <div class="muted" style="font-size:0.68rem">${monthLabel}</div>
                </div>`;
            }).join("");
            body.innerHTML = `
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.5rem">
                    <div>
                        <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.4rem">
                            <span style="padding:3px 10px;border-radius:999px;background:${rarityColor}20;color:${rarityColor};font-size:0.72rem;font-weight:600;text-transform:uppercase;letter-spacing:0.08em">${p.rarity.replace('_',' ')}</span>
                            <span class="muted" style="font-size:0.8rem">${p.total_observations} sightings</span>
                        </div>
                        <h3 style="margin:0;font-style:italic">${p.scientific_name}</h3>
                        <div class="muted">${p.common_name || "—"}</div>
                        <div style="margin-top:0.75rem;font-size:0.85rem;line-height:1.7">
                            <div><b>First seen:</b> ${p.first_seen || "—"}</div>
                            <div><b>Last seen:</b> ${p.last_seen || "—"}</div>
                            <div><b>RSWF planted?</b> ${p.planted_count ? `Yes — ${p.planted_count} on site` : "No"}</div>
                        </div>
                        <div style="margin-top:0.75rem">${zones || '<span class="muted">No zone data</span>'}</div>
                    </div>
                    <div>
                        <div class="muted" style="font-size:0.72rem;letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.3rem">Phenology (sightings per month)</div>
                        <div style="display:flex;gap:4px;align-items:flex-end;padding:0.5rem;background:var(--v-ink-3);border-radius:10px;border:1px solid var(--v-stroke)">${phenBars}</div>
                        <div class="muted" style="font-size:0.78rem;margin-top:0.75rem">Peak month tells you when this species is easiest to find in Van Udyan.</div>
                    </div>
                </div>
                <div style="margin-top:1rem"><a target="_blank" rel="noopener" href="https://en.wikipedia.org/wiki/${encodeURIComponent(p.scientific_name.replace(/ /g,'_'))}" class="link-btn">↗ Read on Wikipedia</a></div>
            `;
        } catch (e) {
            body.innerHTML = `<div class="muted">Error: ${e.message}</div>`;
        }
    },
    closeSpeciesProfile() { document.getElementById("species-profile-modal").style.display = "none"; },

    // --- Bulk upload ---
    openBulkUploadModal() {
        document.getElementById("bulk-upload-modal").style.display = "flex";
        document.getElementById("bulk-results").innerHTML = "";
        document.getElementById("bulk-progress").style.display = "none";
        // reset type selector
        const sightedRadio = document.getElementById("bulk-type-sighted");
        if (sightedRadio) { sightedRadio.checked = true; this.onBulkTypeChange(); }
    },
    closeBulkUploadModal() { document.getElementById("bulk-upload-modal").style.display = "none"; },

    async keepBulkDuplicate(index) {
        const row = this.bulkReviewRows?.[index];
        if (!row || row.result.status !== "duplicate") return;
        const dup = row.result.duplicate || {};
        if (dup.duplicate_kind !== "nearby" && !dup.overridable) {
            this.notify("This is the same photo already recorded. Open the existing observation or discard this duplicate row.", "warning", 6500);
            if (dup.existing_observation_id) this.openObservationDetail(dup.existing_observation_id);
            return;
        }
        const file = row.file;
        if (!file) { this.notify("Original photo is no longer available in this review. Please select it again.", "error"); return; }
        const obsType = document.getElementById(`bulk-row-type-${index}`)?.value || row.obsType || "sighted";
        const btn = document.getElementById(`bulk-row-keep-${index}`);
        if (btn) { btn.disabled = true; btn.textContent = "Keeping…"; }
        try {
            const batch = await ApiService.bulkUploadPhotos([file], { obsType, allowNearbyDuplicate: true });
            const saved = (batch.results || [])[0];
            if (!saved || !saved.ok) throw new Error(saved?.error || saved?.message || "Could not keep this nearby duplicate.");
            row.result = saved;
            row.predictions = [];
            row.predictionMessage = "Prediction not run yet";
            if (saved.observation_id) {
                try {
                    const ai = await ApiService.identifyObservationPlant(saved.observation_id, "auto");
                    row.predictions = Array.isArray(ai.predictions) ? ai.predictions : [];
                    row.predictionMessage = ai.result_summary?.message || "No prediction returned";
                } catch (aiErr) { row.predictionMessage = aiErr.message || "Prediction unavailable"; }
            }
            this.renderBulkReviewRows();
            this.notify("Nearby photo kept as a separate observation. Please review the species and details.", "success", 6000);
        } catch (err) {
            row.keepError = err.message || String(err);
            this.renderBulkReviewRows();
            this.notify(`Could not keep duplicate: ${row.keepError}`, "error", 7000);
        }
    },

    discardBulkRow(index) {
        if (!this.bulkReviewRows || !this.bulkReviewRows[index]) return;
        const row = this.bulkReviewRows[index];
        if (row.result?.ok && row.result?.observation_id) {
            this.notify("This photo is already saved. Discard only hides it from this review; it does not delete the saved observation.", "warning", 7000);
        }
        this.bulkReviewRows[index].discarded = true;
        this.renderBulkReviewRows();
    },

    async saveBulkRow(index) {
        const row = this.bulkReviewRows?.[index];
        const r = row?.result;
        if (!r?.observation_id || !r.ok || r.requires_confirmation) {
            this.notify("Save is available after the photo has a saved observation record and any GPS confirmation is complete.", "warning", 6000);
            return;
        }
        const value = (id) => document.getElementById(`bulk-row-${id}-${index}`)?.value ?? "";
        const payload = {
            scientific_name: value("scientific").trim() || null,
            common_name: value("common").trim() || null,
            observed_on: value("date") || null,
            observer: value("observer").trim() || null,
            notes: value("notes").trim() || null,
            observation_type: value("type") || row.obsType || "sighted"
        };
        const btn = document.getElementById(`bulk-row-save-${index}`);
        if (btn) { btn.disabled = true; btn.textContent = "Saving…"; }
        try {
            await ApiService.updateObservation(r.observation_id, payload);
            if (payload.scientific_name) {
                await ApiService.verifyObservation(r.observation_id, {
                    decision: "correct",
                    selected_prediction_rank: 1,
                    scientific_name: payload.scientific_name,
                    common_name: payload.common_name,
                    notes: payload.notes || "Species name edited during bulk upload review."
                });
            }
            row.savedDetails = true;
            this.notify(`Bulk row saved for observation #${r.observation_id}.`, "success");
            await this.loadObservations();
            this.renderBulkReviewRows();
        } catch (err) {
            if (btn) { btn.disabled = false; btn.textContent = "Save details"; }
            this.notify(`Could not save bulk row: ${err.message}`, "error", 7000);
        }
    },

    renderBulkReviewRows() {
        const target = document.getElementById("bulk-results");
        if (!target) return;
        const rows = (this.bulkReviewRows || []).map((row, index) => {
            if (row.discarded) return "";
            const r = row.result || {};
            const dup = r.duplicate || {};
            const isDup = r.status === "duplicate";
            const badge = r.ok ? (r.requires_confirmation ? '<span class="pill pill-orange">needs GPS confirmation</span>' : '<span class="pill pill-green">saved</span>') :
                isDup ? '<span class="pill pill-purple">duplicate</span>' :
                r.status === "no_gps" ? '<span class="pill pill-grey">no GPS</span>' :
                '<span class="pill pill-grey">' + this.esc(r.status || "error") + '</span>';
            const msg = r.error || r.message || (r.observation_id ? `#${r.observation_id} · ${r.zone || ""}` : dup.message || "");
            const suggestions = row.predictions || [];
            const predicted = suggestions[0] || {};
            const name = predicted.scientific_name || predicted.name || r.scientific_name || "";
            const common = predicted.common_name || r.common_name || "";
            const predictionHtml = suggestions.length ? suggestions.slice(0, 3).map(p => {
                const nm = this.esc(p.scientific_name || p.name || "Unknown");
                const cm = p.common_name ? ` <span class="muted">(${this.esc(p.common_name)})</span>` : "";
                const score = p.confidence_percentage || p.score || p.confidence || "";
                return `<div><i>${nm}</i>${cm}${score !== "" ? ` <span class="conf">${this.esc(String(score))}</span>` : ""}</div>`;
            }).join("") : `<span class="muted">${this.esc(row.predictionMessage || "No prediction available")}</span>`;
            const canEdit = !!(r.ok && r.observation_id && !r.requires_confirmation);
            const details = canEdit ? `
                <details style="min-width:250px;margin-top:.5rem">
                  <summary style="cursor:pointer;color:var(--v-accent,#10b981)">Edit details / predicted name</summary>
                  <div style="display:grid;gap:.4rem;min-width:230px;padding:.5rem 0">
                    <label class="muted">Scientific / predicted name<input id="bulk-row-scientific-${index}" value="${this.esc(name)}" placeholder="Enter or correct species name" style="width:100%"></label>
                    <label class="muted">Common name<input id="bulk-row-common-${index}" value="${this.esc(common)}" placeholder="Common name" style="width:100%"></label>
                    <label class="muted">Observation date<input id="bulk-row-date-${index}" type="date" value="${this.esc(r.observed_on || r.captured_at || "")}" style="width:100%"></label>
                    <label class="muted">Observer<input id="bulk-row-observer-${index}" value="${this.esc(r.observer || "RSWF Field Volunteer")}" style="width:100%"></label>
                    <label class="muted">Record type<select id="bulk-row-type-${index}" style="width:100%"><option value="sighted" ${(r.observation_type || row.obsType || "sighted") === "sighted" ? "selected" : ""}>Sighted</option><option value="planted_rswf" ${(r.observation_type || row.obsType) === "planted_rswf" ? "selected" : ""}>Planted by RSWF</option></select></label>
                    <label class="muted">Notes<textarea id="bulk-row-notes-${index}" rows="2" placeholder="Field notes" style="width:100%">${this.esc(r.notes || "")}</textarea></label>
                    <button id="bulk-row-save-${index}" type="button" class="btn-primary btn-small" onclick="App.saveBulkRow(${index})">Save details</button>
                  </div>
                </details>` : "";
            const actions = isDup
                ? `<div style="display:flex;gap:.35rem;flex-wrap:wrap"><button id="bulk-row-keep-${index}" type="button" class="btn-primary btn-small" onclick="App.keepBulkDuplicate(${index})">${(dup.duplicate_kind === "nearby" || dup.overridable) ? "Keep as separate" : "Open existing"}</button><button type="button" class="btn-action btn-small" onclick="App.discardBulkRow(${index})">Discard</button></div>`
                : `<div style="display:flex;gap:.35rem;flex-wrap:wrap">${canEdit ? `<button type="button" class="btn-primary btn-small" onclick="App.openObservationDetail(${Number(r.observation_id)})">Open record</button>` : ""}<button type="button" class="btn-action btn-small" onclick="App.discardBulkRow(${index})">Discard row</button></div>${details}`;
            return `<tr><td>${this.esc(r.filename || row.file?.name || "Photo")}</td><td>${badge}</td><td>${predictionHtml}</td><td class="muted">${this.esc(String(msg || row.keepError || ""))}</td><td>${actions}</td></tr>`;
        }).join("");
        const remaining = (this.bulkReviewRows || []).filter(r => !r.discarded).length;
        target.innerHTML = `
            <table class="data-table" style="margin-top:.75rem">
              <thead><tr><th>File</th><th>Result</th><th>Plant prediction</th><th>Note</th><th>Review / action</th></tr></thead>
              <tbody>${rows || '<tr><td colspan="5" class="muted">No rows left in this review.</td></tr>'}</tbody>
            </table>
            <p class="muted" style="font-size:.8rem;margin-top:.5rem">“Discard row” only removes the row from this review. It does not delete a saved observation. Exact duplicate photos cannot be saved twice; nearby-plant matches can be kept only when they are genuinely different plants.</p>
            <div style="display:flex;justify-content:flex-end;margin-top:.75rem"><button class="btn-primary" onclick="App.closeBulkUploadModal(); App.loadObservations()">Done</button></div>`;
    },

    async handleBulkDrop(e) {
        e.preventDefault();
        const dz = document.getElementById("bulk-dropzone");
        if (dz) dz.classList.remove("drag");
        const files = e.dataTransfer ? Array.from(e.dataTransfer.files) : Array.from(e.target.files || []);
        const imgs = files.filter(f => /\.(jpe?g|png|webp)$/i.test(f.name));
        if (!imgs.length) { this.notify("No JPG/PNG/WEBP files found.", "error"); return; }
        const MAX_FILE_BYTES = 50 * 1024 * 1024;
        const tooLarge = imgs.filter(f => f.size > MAX_FILE_BYTES);
        if (tooLarge.length) {
            this.notify(`These files exceed 50 MB: ${tooLarge.slice(0, 3).map(f => f.name).join(", ")}${tooLarge.length > 3 ? "…" : ""}. Compress them and retry.`, "error", 7000);
            return;
        }
        const obsType = document.querySelector('input[name="bulk-obs-type"]:checked')?.value || "sighted";
        const prog = document.getElementById("bulk-progress");
        prog.style.display = "block"; prog.style.color = "";
        prog.textContent = `Preparing ${imgs.length} photos for upload…`;
        this.bulkReviewRows = [];
        try {
            const MAX_CHUNK_BYTES = 10 * 1024 * 1024, MAX_CHUNK_FILES = 2;
            const chunks = []; let chunk = [], chunkBytes = 0;
            for (const file of imgs) {
                if (chunk.length && (chunk.length >= MAX_CHUNK_FILES || chunkBytes + file.size > MAX_CHUNK_BYTES)) {
                    chunks.push(chunk); chunk = []; chunkBytes = 0;
                }
                chunk.push(file); chunkBytes += file.size;
            }
            if (chunk.length) chunks.push(chunk);
            let completed = 0;
            for (let i = 0; i < chunks.length; i++) {
                prog.textContent = `Uploading batch ${i + 1}/${chunks.length} (${completed}/${imgs.length} photos completed)…`;
                let results = [];
                try {
                    const batch = await ApiService.bulkUploadPhotos(chunks[i], { obsType });
                    results = batch.results || [];
                } catch (batchErr) {
                    results = chunks[i].map(file => ({ filename: file.name, ok: false, status: "error", error: `Batch upload failed: ${batchErr.message || String(batchErr)}` }));
                }
                for (let j = 0; j < chunks[i].length; j++) {
                    const file = chunks[i][j];
                    const r = results[j] || { filename: file.name, ok: false, status: "error", error: "No result returned for this file." };
                    const row = { file, result: r, predictions: [], predictionMessage: "", obsType };
                    if (r.observation_id && r.ok && !r.requires_confirmation) {
                        try {
                            const ai = await ApiService.identifyObservationPlant(r.observation_id, "auto");
                            row.predictions = Array.isArray(ai.predictions) ? ai.predictions : [];
                            if (!row.predictions.length) row.predictionMessage = ai.result_summary?.message || "No prediction returned";
                        } catch (aiErr) { row.predictionMessage = aiErr.message || "Prediction unavailable"; }
                    } else if (r.requires_confirmation) row.predictionMessage = "Confirm GPS location before prediction";
                    else if (r.status === "duplicate") row.predictionMessage = r.duplicate?.scientific_name ? `Existing record: ${r.duplicate.scientific_name}` : "Prediction unavailable for this upload";
                    else row.predictionMessage = "Prediction unavailable for this upload";
                    this.bulkReviewRows.push(row);
                    completed++;
                    prog.textContent = `Processed ${completed}/${imgs.length} photos; checking predictions…`;
                }
                this.renderBulkReviewRows();
            }
            const count = { ok: 0, needs_confirmation: 0, duplicates: 0, rejected: 0, errors: 0 };
            for (const row of this.bulkReviewRows) {
                const r = row.result || {};
                if (r.ok) count.ok++;
                else if (r.status === "duplicate") count.duplicates++;
                else if (r.status === "rejected") count.rejected++;
                else count.errors++;
                if (r.requires_confirmation) count.needs_confirmation++;
            }
            prog.textContent = `Done: ${count.ok} ok · ${count.needs_confirmation} need confirmation · ${count.duplicates} duplicates · ${count.rejected} rejected · ${count.errors} errors.`;
        } catch (err) {
            prog.style.color = "#f87171";
            prog.textContent = `Bulk upload failed: ${err.message || String(err)}`;
        } finally {
            const input = document.getElementById("bulk-file-input");
            if (input) input.value = "";
        }
    },

};

window.App = App;
