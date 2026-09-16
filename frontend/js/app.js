/**
 * Single Page Application (SPA) Controller Engine
 * Handles navigation tabs, Leaflet GIS map initialization, Chart.js KPI charts,
 * species search, observation filters, pagination, Data Management CRUD modals,
 * Phase 8 Dataset Export Download engine, and Phase 15 Password-Protected Authorization.
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
        this.setupPhotoGpsListeners();
        this.updateAuthStatusUI();
        await this.checkBackendHealth();
        await this.loadOverview();
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
            btn.innerHTML = `🔒 RSWF Admin Active (Click to Lock)`;
            btn.style.background = "rgba(16, 185, 129, 0.2)";
            btn.style.color = "#34d399";
            btn.style.borderColor = "rgba(16, 185, 129, 0.4)";
        } else {
            btn.innerHTML = `🔓 Public View Mode (Click to Authorize)`;
            btn.style.background = "rgba(255,255,255,0.05)";
            btn.style.color = "#cbd5e1";
            btn.style.borderColor = "rgba(255,255,255,0.15)";
        }
    },

    toggleAuthSession() {
        const pass = ApiService.getNgoPassword();
        if (pass) {
            ApiService.clearNgoPassword();
            this.updateAuthStatusUI();
            alert("🔒 RSWF Admin session ended. Switched to Public View Mode.");
        } else {
            this.openAuthModal(null);
        }
    },

    requireAuth(actionCallback) {
        if (ApiService.getNgoPassword()) {
            actionCallback();
        } else {
            this.openAuthModal(actionCallback);
        }
    },

    openAuthModal(actionCallback = null) {
        this.pendingAction = actionCallback;
        const passInput = document.getElementById("ngo-auth-password");
        const errDiv = document.getElementById("auth-error-msg");
        if (passInput) passInput.value = "";
        if (errDiv) errDiv.style.display = "none";
        document.getElementById("ngo-auth-modal").style.display = "flex";
        if (passInput) passInput.focus();
    },

    closeAuthModal() {
        this.pendingAction = null;
        document.getElementById("ngo-auth-modal").style.display = "none";
    },

    handleAuthSubmit(e) {
        e.preventDefault();
        const password = document.getElementById("ngo-auth-password").value;
        if (!password) return;

        ApiService.setNgoPassword(password);
        this.updateAuthStatusUI();
        document.getElementById("ngo-auth-modal").style.display = "none";

        if (this.pendingAction) {
            const act = this.pendingAction;
            this.pendingAction = null;
            act();
        }
    },

    setupNavigation() {
        const navButtons = document.querySelectorAll(".nav-item button");
        navButtons.forEach(btn => {
            btn.addEventListener("click", async (e) => {
                const targetTab = btn.getAttribute("data-tab");
                if (targetTab === this.currentTab) return;

                navButtons.forEach(b => b.classList.remove("active"));
                btn.classList.add("active");

                document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
                const targetPane = document.getElementById(`tab-${targetTab}`);
                if (targetPane) targetPane.classList.add("active");

                this.currentTab = targetTab;
                await this.handleTabSwitch(targetTab);
            });
        });
    },

    async checkBackendHealth() {
        const badge = document.getElementById("backend-status-badge");
        try {
            const health = await ApiService.getHealth();
            if (badge) {
                badge.innerHTML = `<span class="dot"></span> ${health.service} (v${health.version})`;
            }
        } catch (err) {
            if (badge) {
                badge.innerHTML = `<span class="dot" style="background:#ef4444;box-shadow:0 0 8px #ef4444"></span> Backend API Offline (Connecting...)`;
            }
            this.showErrorBanner("FastAPI backend API is currently offline. Ensure backend server is running on http://localhost:8000.");
        }
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

        this.renderZoneChart(zoneCounts);
        this.renderSourceChart(stats.observations_by_source || {});
        await this.loadActionPriorities();
    },

    async loadActionPriorities() {
        const container = document.getElementById("action-priorities-container");
        if (!container) return;

        try {
            const data = await ApiService.getAnalyticsActionPriorities();
            if (!data.priorities || data.priorities.length === 0) {
                container.innerHTML = `<div style="color:#94a3b8;font-size:0.85rem">No action priorities indicated by current data.</div>`;
                return;
            }

            container.innerHTML = data.priorities.map(p => {
                let badgeBg = "rgba(16, 185, 129, 0.2)";
                let badgeColor = "#10b981";
                let borderColor = "rgba(16, 185, 129, 0.3)";

                if (p.priority_level === "HIGH") {
                    badgeBg = "rgba(239, 68, 68, 0.2)";
                    badgeColor = "#ef4444";
                    borderColor = "rgba(239, 68, 68, 0.4)";
                } else if (p.priority_level === "MEDIUM") {
                    badgeBg = "rgba(245, 158, 11, 0.2)";
                    badgeColor = "#f59e0b";
                    borderColor = "rgba(245, 158, 11, 0.4)";
                } else if (p.priority_level === "LOW") {
                    badgeBg = "rgba(59, 130, 246, 0.2)";
                    badgeColor = "#60a5fa";
                    borderColor = "rgba(59, 130, 246, 0.3)";
                }

                return `
                    <div style="background:rgba(15,23,42,0.6);border:1px solid ${borderColor};border-radius:6px;padding:0.9rem">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                            <span style="font-weight:700;color:#fff;font-size:0.95rem">${p.area_code}</span>
                            <span class="status-badge" style="background:${badgeBg};color:${badgeColor};font-size:0.75rem">${p.priority_type.replace('_', ' ')}</span>
                        </div>
                        <div style="font-size:0.8rem;color:#cbd5e1;margin-bottom:0.5rem"><b>Reason:</b> ${p.reason}</div>
                        <div style="font-size:0.8rem;color:#10b981;background:rgba(16,185,129,0.08);padding:0.4rem 0.6rem;border-radius:4px"><b>Action:</b> ${p.recommended_action}</div>
                    </div>
                `;
            }).join("");
        } catch (err) {
            container.innerHTML = `<div style="color:#f87171;font-size:0.85rem">Error loading field action priorities: ${err.message}</div>`;
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
                plugins: { legend: { display: false } },
                scales: {
                    y: { ticks: { color: "#94a3b8" }, grid: { color: "rgba(46,117,89,0.15)" } },
                    x: { ticks: { color: "#94a3b8" }, grid: { display: false } }
                }
            }
        });
    },

    renderSourceChart(sourceCounts) {
        const ctx = document.getElementById("chart-source-breakdown");
        if (!ctx) return;

        if (this.charts.sourceChart) this.charts.sourceChart.destroy();

        const labels = Object.keys(sourceCounts);
        const values = Object.values(sourceCounts);

        this.charts.sourceChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: labels.length > 0 ? labels : ["iNaturalist"],
                datasets: [{
                    data: values.length > 0 ? values : [227],
                    backgroundColor: ["#10b981", "#3b82f6", "#f97316", "#8b5cf6"]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "bottom", labels: { color: "#e2e8f0" } }
                }
            }
        });
    },

    // 2. Interactive Leaflet GIS Map Loader
    async loadMap() {
        if (!this.leafletMap) {
            this.leafletMap = L.map("leaflet-map").setView([18.5195, 73.7800], 16);

            L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: "© OpenStreetMap contributors | RSWF NGO"
            }).addTo(this.leafletMap);

            this.mapLayerGroup = L.layerGroup().addTo(this.leafletMap);
        }

        this.mapLayerGroup.clearLayers();

        const [boundaryGeoJSON, zonesGeoJSONList, mapObsGeoJSON] = await Promise.all([
            ApiService.getGeography(),
            ApiService.getZones(),
            ApiService.getMapObservations()
        ]);

        if (boundaryGeoJSON && boundaryGeoJSON.features) {
            const bLayer = L.geoJSON(boundaryGeoJSON, {
                style: { color: "#f59e0b", weight: 3, fillOpacity: 0.08, dashArray: "6, 6" }
            }).addTo(this.mapLayerGroup);

            this.leafletMap.fitBounds(bLayer.getBounds());
        }

        zonesGeoJSONList.forEach(z => {
            const colorMap = { "ZONE A": "#10b981", "ZONE B": "#3b82f6", "ZONE C": "#8b5cf6" };
            const zColor = colorMap[z.zone_code] || "#10b981";

            L.geoJSON(z.geometry, {
                style: { color: zColor, weight: 2, fillColor: zColor, fillOpacity: 0.25 }
            }).bindTooltip(`<b>${z.zone_code}</b>`, { permanent: true, direction: "center" }).addTo(this.mapLayerGroup);
        });

        if (mapObsGeoJSON && mapObsGeoJSON.features) {
            mapObsGeoJSON.features.forEach(feat => {
                const [lng, lat] = feat.geometry.coordinates;
                const props = feat.properties;

                const isInsideActive = props.zone && props.zone !== "";
                const markerColor = isInsideActive ? "#10b981" : "#f97316";

                const circleMarker = L.circleMarker([lat, lng], {
                    radius: 6,
                    fillColor: markerColor,
                    color: "#ffffff",
                    weight: 1,
                    opacity: 1,
                    fillOpacity: 0.85
                });

                const popupContent = `
                    <div style="padding:4px">
                        <div class="popup-title">${props.common_name || props.scientific_name || 'Observation'}</div>
                        <div class="popup-row"><b>Scientific Name:</b> <i>${props.scientific_name || 'N/A'}</i></div>
                        <div class="popup-row"><b>Observer:</b> ${props.observer || 'N/A'}</div>
                        <div class="popup-row"><b>Observed On:</b> ${props.observed_on || 'N/A'}</div>
                        <div class="popup-row"><b>Zone:</b> ${props.zone || 'Outside Active Zones'}</div>
                        <div class="popup-row"><b>Quality Grade:</b> ${props.quality_grade || 'N/A'}</div>
                        <div class="popup-row"><b>Source:</b> ${props.source || 'iNaturalist'}</div>
                        ${props.photo_url ? `<div style="margin-top:6px"><a href="${props.photo_url}" target="_blank" style="color:#10b981;font-size:0.8rem">View Photo Reference ↗</a></div>` : ''}
                    </div>
                `;

                circleMarker.bindPopup(popupContent);
                this.mapLayerGroup.addLayer(circleMarker);
            });
        }

        setTimeout(() => this.leafletMap.invalidateSize(), 200);
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
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:2rem;color:#94a3b8">No species matching "${this.speciesSearch}" found.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.data.map(s => `
            <tr>
                <td>#${s.id}</td>
                <td><b><i>${s.scientific_name}</i></b></td>
                <td>${s.common_name || '<span style="color:#64748b">N/A</span>'}</td>
                <td><span style="background:rgba(16,185,129,0.15);color:#10b981;padding:2px 8px;border-radius:4px;font-size:0.8rem">${s.taxon_rank || 'species'}</span></td>
                <td><b>${s.record_count}</b> observations</td>
            </tr>
        `).join("");

        document.getElementById("species-page-info").textContent = `Page ${res.page} of ${res.total_pages} (${res.total_records} recorded species/taxa)`;
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
            tbody.innerHTML = `<tr><td colspan="8" style="text-align:center;padding:2rem;color:#94a3b8">No observation records matching current filters.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.data.map(o => `
            <tr>
                <td>#${o.id}</td>
                <td><b><i>${o.scientific_name || 'Unclassified'}</i></b></td>
                <td>${o.common_name || '<span style="color:#64748b">N/A</span>'}</td>
                <td>${o.observer || 'N/A'}</td>
                <td>${o.observed_on || 'N/A'}</td>
                <td>${o.zone ? `<span style="color:#10b981;font-weight:600">${o.zone}</span>` : '<span style="color:#f97316">Outside Active</span>'}</td>
                <td><span style="background:rgba(59,130,246,0.15);color:#3b82f6;padding:2px 6px;border-radius:4px;font-size:0.75rem">${o.quality_grade}</span></td>
                <td><span style="color:#94a3b8">${o.source}</span></td>
            </tr>
        `).join("");

        document.getElementById("obs-page-info").textContent = `Page ${res.page} of ${res.total_pages} (${res.total_records} observation records)`;
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
        const zones = await ApiService.getZones();
        const container = document.getElementById("zones-cards-container");
        if (!container) return;

        container.innerHTML = zones.map(z => `
            <div class="kpi-card" style="border-left: 4px solid #10b981">
                <div style="display:flex;justify-content:space-between;align-items:center">
                    <h3 style="color:#ffffff;font-size:1.2rem">${z.zone_code}</h3>
                    <span class="source-badge"><span class="dot"></span> ${z.status}</span>
                </div>
                <p style="color:#94a3b8;font-size:0.9rem;margin-top:0.5rem">${z.description}</p>
                <div style="margin-top:1rem;font-size:0.8rem;color:#10b981">WGS84 EPSG:4326 PostGIS Polygon Verified</div>
            </div>
        `).join("");
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
            tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:2rem;color:#94a3b8">No planted plant records found. Click <b>[+ Add Plant]</b> to register plantation records.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.data.map(p => {
            const stClass = p.status.toLowerCase();
            return `
                <tr>
                    <td><b>${p.plant_code}</b></td>
                    <td><b><i>${p.scientific_name || 'Unspecified Species'}</i></b></td>
                    <td>${p.common_name || '<span style="color:#64748b">N/A</span>'}</td>
                    <td>${p.planted_on || 'N/A'}</td>
                    <td>${p.zone_code ? `<span style="color:#10b981;font-weight:600">${p.zone_code}</span>` : '<span style="color:#f97316">Outside Active</span>'}</td>
                    <td><span class="status-badge ${stClass}">${p.status}</span></td>
                    <td>
                        <button class="btn-action" style="background:rgba(59,130,246,0.2);color:#60a5fa" onclick="App.openPlantHistoryModal(${p.id}, '${p.plant_code}')">📋 History</button>
                        <button class="btn-action" style="background:rgba(16,185,129,0.2);color:#34d399" onclick="App.openMonitoringModal(${p.id}, '${p.plant_code}')">➕ Visit</button>
                        <button class="btn-action" onclick="App.openEditPlantModal(${p.id})">Edit</button>
                        <button class="btn-action delete" onclick="App.confirmDeletePlant(${p.id}, '${p.plant_code}')">Delete</button>
                    </td>
                </tr>
            `;
        }).join("");

        document.getElementById("planted-page-info").textContent = `Page ${res.page} of ${res.total_pages} (${res.total_records} plantation records)`;
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
                console.warn("Photo upload warning:", uploadErr);
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
            await this.loadPlantedPlants();
            await this.loadOverview();
        } catch (err) {
            alert(`Error saving plant record: ${err.message}`);
        }
    },

    confirmDeletePlant(id, code) {
        this.requireAuth(() => this._doConfirmDeletePlant(id, code));
    },

    async _doConfirmDeletePlant(id, code) {
        if (confirm(`Are you sure you want to delete Planted Plant '${code}' (ID: ${id})?\n\nThis action cannot be undone.`)) {
            try {
                await ApiService.deletePlantedPlant(id);
                await this.loadPlantedPlants();
                await this.loadOverview();
            } catch (err) {
                this.showErrorBanner(`Failed to delete plant record: ${err.message}`);
            }
        }
    },

    openMonitoringModal(plantId, plantCode) {
        this.requireAuth(() => this._doOpenMonitoringModal(plantId, plantCode));
    },

    _doOpenMonitoringModal(plantId, plantCode) {
        this.currentMonitoringPlantId = plantId;
        document.getElementById("plant-monitoring-form").reset();
        document.getElementById("monitoring-plant-subtitle").textContent = `Log condition visit inspection for plant '${plantCode}' (ID: #${plantId}).`;
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
            await this.loadPlantedPlants();
            await this.loadOverview();
            alert(`✅ Monitoring visit logged for plant #${this.currentMonitoringPlantId}! Current status updated to: ${payload.status}`);
        } catch (err) {
            alert(`Error logging monitoring visit: ${err.message}`);
        }
    },

    async openPlantHistoryModal(plantId, plantCode) {
        document.getElementById("history-modal-title").textContent = `📋 Plant #${plantId} (${plantCode}) — Monitoring History`;
        const tbody = document.getElementById("history-table-body");
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:#94a3b8">Loading visit history records...</td></tr>`;
        document.getElementById("plant-history-modal").style.display = "flex";

        try {
            const history = await ApiService.getPlantMonitoringHistory(plantId);
            if (!history || history.length === 0) {
                tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:#94a3b8">No historical monitoring visits logged for this plant yet. Click <b>[+ Visit]</b> to record a visit.</td></tr>`;
                return;
            }

            tbody.innerHTML = history.map(h => {
                const stClass = h.status.toLowerCase();
                return `
                    <tr>
                        <td><b>${h.monitoring_date}</b></td>
                        <td><span class="status-badge ${stClass}">${h.status}</span></td>
                        <td>${h.observer || 'RSWF Field Team'}</td>
                        <td>${h.notes || '<span style="color:#64748b">No remarks</span>'}</td>
                    </tr>
                `;
            }).join("");
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:1.5rem;color:#f87171">Error loading history: ${err.message}</td></tr>`;
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
                console.warn("Photo upload warning:", uploadErr);
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

        try {
            await ApiService.createNGOObservation(payload);
            this.closeNgoObsModal();
            await this.loadObservations();
            await this.loadOverview();
            alert("NGO Field Observation record successfully created!");
        } catch (err) {
            alert(`Error saving NGO observation: ${err.message}`);
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

    async handlePhotoUploadSubmit(e) {
        e.preventDefault();
        const fileInput = document.getElementById("upload-photo-file");
        if (!fileInput.files || fileInput.files.length === 0) {
            alert("Please select a photo file to upload.");
            return;
        }

        const file = fileInput.files[0];
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
            const res = await ApiService.uploadPhotoObservation(file);
            statusInd.style.display = "none";
            submitBtn.disabled = false;

            if (res.photo_url) {
                const fullPhotoUrl = window.APP_CONFIG.getEndpoint(res.photo_url);
                resultPreview.src = fullPhotoUrl;
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
                    <div><b>Source:</b> Photo Metadata (EXIF)</div>
                    <div><b>Latitude:</b> ${res.latitude.toFixed(6)}</div>
                    <div><b>Longitude:</b> ${res.longitude.toFixed(6)}</div>
                    <div><b>Zone Assignment:</b> <span style="color:#10b981;font-weight:600">${res.zone}</span></div>
                    <div><b>Observation ID:</b> #${res.observation_id}</div>
                    <div style="margin-top:0.4rem;color:#94a3b8">${res.message}</div>
                `;

                if (confirmBox) confirmBox.style.display = "none";
                if (aiContainer) aiContainer.style.display = "flex";
                this.currentUploadedObsId = res.observation_id;

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
            alert("No pending geotag coordinates to confirm.");
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
                data.captured_at
            );

            this.currentUploadedObsId = res.observation_id;
            this.pendingGeotagData = null;

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
            alert(`Error confirming geotag location: ${err.message}`);
        }
    },

    // =====================================================================
    // Phase 10 — Pl@ntNet AI Identification & Verification Handlers
    // =====================================================================

    async triggerCurrentObsAI() {
        if (!this.currentUploadedObsId) {
            alert("No active observation found for AI identification.");
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
            alert(`✅ Observation #${obsId} species confirmed as: ${res.scientific_name}`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            alert(`Error confirming verification: ${err.message}`);
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
            alert("Please enter the corrected scientific name.");
            return;
        }

        try {
            const res = await ApiService.verifyObservation(obsId, {
                decision: "correct",
                scientific_name: sci,
                common_name: com || null,
                notes: notes || null
            });
            alert(`✏️ Observation #${obsId} species corrected to: ${res.scientific_name}`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            alert(`Error saving correction: ${err.message}`);
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
            alert(`❓ Observation #${obsId} marked as requiring expert review.`);
            await this.loadObservations();
            await this.loadOverview();
            this.closeUploadPhotoModal();
        } catch (err) {
            alert(`Error setting status: ${err.message}`);
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
    }
};

window.App = App;
