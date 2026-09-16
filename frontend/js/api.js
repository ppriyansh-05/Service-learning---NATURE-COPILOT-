/**
 * Centralized API Client Service Layer
 * Consumes FastAPI backend REST endpoints cleanly without scattering fetch calls in UI.
 */
class ApiService {
    static getNgoPassword() {
        try {
            if (!window.sessionStorage) return "";
            const pass = window.sessionStorage.getItem("ngo_admin_password") || "";
            if (!pass) return "";

            const lastActiveStr = window.sessionStorage.getItem("ngo_admin_last_active");
            const now = Date.now();
            const TIMEOUT_MS = 30 * 60 * 1000; // 30-minute inactivity timeout

            if (lastActiveStr && (now - parseInt(lastActiveStr, 10)) > TIMEOUT_MS) {
                // Session expired due to inactivity
                window.sessionStorage.removeItem("ngo_admin_password");
                window.sessionStorage.removeItem("ngo_admin_last_active");
                if (window.App && typeof window.App.updateAuthStatusUI === "function") {
                    window.App.updateAuthStatusUI();
                }
                return "";
            }

            // Refresh activity timestamp
            window.sessionStorage.setItem("ngo_admin_last_active", now.toString());
            return pass;
        } catch (e) {
            return "";
        }
    }

    static setNgoPassword(password) {
        try {
            if (window.sessionStorage) {
                if (password) {
                    window.sessionStorage.setItem("ngo_admin_password", password);
                    window.sessionStorage.setItem("ngo_admin_last_active", Date.now().toString());
                } else {
                    window.sessionStorage.removeItem("ngo_admin_password");
                    window.sessionStorage.removeItem("ngo_admin_last_active");
                }
            }
        } catch (e) {}
    }

    static clearNgoPassword() {
        try {
            if (window.sessionStorage) {
                window.sessionStorage.removeItem("ngo_admin_password");
                window.sessionStorage.removeItem("ngo_admin_last_active");
            }
        } catch (e) {}
    }

    static async fetchJson(url, options = {}) {
        try {
            const headers = options.headers || {};
            const savedPass = this.getNgoPassword();
            if (savedPass && !headers["X-NGO-Admin-Password"]) {
                headers["X-NGO-Admin-Password"] = savedPass;
            }
            options.headers = headers;

            const response = await fetch(url, options);
            if (!response.ok) {
                let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
                try {
                    const errBody = await response.json();
                    if (errBody.detail) {
                        errorMsg = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
                    }
                } catch (e) {}
                if (response.status === 401) {
                    // Clear invalid cached session password on auth failure
                    this.clearNgoPassword();
                }
                throw new Error(errorMsg);
            }
            if (response.status === 204) return null;
            return await response.json();
        } catch (error) {
            console.error(`API Fetch Error [${url}]:`, error);
            throw error;
        }
    }

    static getHealth() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/health"));
    }

    static getDbHealth() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/health/db"));
    }

    static getObservations(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.page) queryParams.append("page", params.page);
        if (params.limit) queryParams.append("limit", params.limit);
        if (params.source) queryParams.append("source", params.source);
        if (params.species) queryParams.append("species", params.species);
        if (params.zone) queryParams.append("zone", params.zone);
        if (params.quality_grade) queryParams.append("quality_grade", params.quality_grade);

        const queryString = queryParams.toString();
        const path = `/observations${queryString ? '?' + queryString : ''}`;
        return this.fetchJson(window.APP_CONFIG.getEndpoint(path));
    }

    static getObservationById(id) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/observations/${id}`));
    }

    static createNGOObservation(data) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/observations/ngo"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    // Photo Upload & Location Detection (EXIF & Image Geotag)
    static async uploadPhotoObservation(file, confirmLocation = false) {
        const formData = new FormData();
        formData.append("file", file);

        const endpoint = confirmLocation ? "/observations/upload?confirm_location=true" : "/observations/upload";
        const url = window.APP_CONFIG.getEndpoint(endpoint);
        const response = await fetch(url, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
            try {
                const errBody = await response.json();
                if (errBody.detail) {
                    errorMsg = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
                }
            } catch (e) {}
            throw new Error(errorMsg);
        }
        return await response.json();
    }

    static async confirmGeotagLocation(photoUrl, latitude, longitude, observedOn = null, observer = "RSWF Field Volunteer", notes = null) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/observations/confirm-location"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                photo_url: photoUrl,
                latitude: latitude,
                longitude: longitude,
                observed_on: observedOn,
                observer: observer,
                notes: notes
            })
        });
    }

    static async inspectPhoto(file) {
        const formData = new FormData();
        formData.append("file", file);

        const url = window.APP_CONFIG.getEndpoint("/observations/inspect-photo");
        const response = await fetch(url, {
            method: "POST",
            body: formData
        });

        if (!response.ok) {
            let errorMsg = `HTTP Error ${response.status}: ${response.statusText}`;
            try {
                const errBody = await response.json();
                if (errBody.detail) errorMsg = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
            } catch (e) {}
            throw new Error(errorMsg);
        }
        return await response.json();
    }

    static getSpecies(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.page) queryParams.append("page", params.page);
        if (params.limit) queryParams.append("limit", params.limit);
        if (params.species_name) queryParams.append("species_name", params.species_name);
        if (params.taxon_rank) queryParams.append("taxon_rank", params.taxon_rank);

        const queryString = queryParams.toString();
        const path = `/species${queryString ? '?' + queryString : ''}`;
        return this.fetchJson(window.APP_CONFIG.getEndpoint(path));
    }

    static getZones() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/zones"));
    }

    static getGeography() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/geography"));
    }

    static getMapObservations(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.source) queryParams.append("source", params.source);
        if (params.zone) queryParams.append("zone", params.zone);

        const queryString = queryParams.toString();
        const path = `/map/observations${queryString ? '?' + queryString : ''}`;
        return this.fetchJson(window.APP_CONFIG.getEndpoint(path));
    }

    static getStatisticsOverview() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/statistics/overview"));
    }

    // Phase 7 Planted Plants CRUD Client Methods
    static getPlantedPlants(params = {}) {
        const queryParams = new URLSearchParams();
        if (params.page) queryParams.append("page", params.page);
        if (params.limit) queryParams.append("limit", params.limit);
        if (params.status) queryParams.append("status", params.status);
        if (params.zone) queryParams.append("zone", params.zone);
        if (params.species) queryParams.append("species", params.species);

        const queryString = queryParams.toString();
        const path = `/planted-plants${queryString ? '?' + queryString : ''}`;
        return this.fetchJson(window.APP_CONFIG.getEndpoint(path));
    }

    static getPlantedPlantById(id) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/planted-plants/${id}`));
    }

    static createPlantedPlant(data) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint("/planted-plants"), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    static updatePlantedPlant(id, data) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/planted-plants/${id}`), {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    static deletePlantedPlant(id) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/planted-plants/${id}`), {
            method: "DELETE"
        });
    }

    // Phase 8 Dataset Export Download Helpers
    static buildExportUrl(path, params = {}) {
        const queryParams = new URLSearchParams();
        Object.keys(params).forEach(key => {
            if (params[key]) queryParams.append(key, params[key]);
        });
        const queryString = queryParams.toString();
        return window.APP_CONFIG.getEndpoint(`/export${path}${queryString ? '?' + queryString : ''}`);
    }

    static triggerDownload(url, filename = "") {
        const a = document.createElement("a");
        a.href = url;
        if (filename) a.download = filename;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    // Phase 10 Pl@ntNet AI Plant Identification Methods
    static identifyObservationPlant(obsId, organ = "auto") {
        const path = `/observations/${obsId}/identify?organ=${encodeURIComponent(organ)}`;
        return this.fetchJson(window.APP_CONFIG.getEndpoint(path), {
            method: "POST"
        });
    }

    static getObservationPredictions(obsId) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/observations/${obsId}/predictions`));
    }

    static verifyObservation(obsId, data) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/observations/${obsId}/verify`), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    static deleteObservation(obsId) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/observations/${obsId}`), {
            method: "DELETE"
        });
    }

    static getAIFeedbackMetrics() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/observations/ai-feedback'));
    }

    // Phase 12 Plant Status & Survival Monitoring Methods
    static addPlantMonitoringVisit(plantId, data) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/planted-plants/${plantId}/monitoring`), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    }

    static getPlantMonitoringHistory(plantId) {
        return this.fetchJson(window.APP_CONFIG.getEndpoint(`/planted-plants/${plantId}/monitoring`));
    }

    static getPlantSurvivalStatistics() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/planted-plants/monitoring/statistics'));
    }

    // Phase 13 Advanced Biodiversity & Conservation Analytics Methods
    static getAnalyticsBiodiversity() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/biodiversity'));
    }

    static getAnalyticsZones() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/zones'));
    }

    static getAnalyticsCoverage() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/coverage'));
    }

    static getAnalyticsActionPriorities() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/action-priorities'));
    }

    static getAnalyticsSpecies() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/species'));
    }

    static getAnalyticsTemporal() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/analytics/temporal'));
    }

    // Phase 14 / 14.1 Conservation & SDG Report Methods
    static getConservationReportJson() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/reports/conservation'));
    }

    static getSdgReportJson() {
        return this.fetchJson(window.APP_CONFIG.getEndpoint('/reports/sdg'));
    }

    static downloadConservationReportPdf() {
        const url = window.APP_CONFIG.getEndpoint('/reports/conservation.pdf');
        this.triggerDownload(url, "van_udyan_conservation_plantation_report.pdf");
    }

    static downloadSdgReportPdf() {
        const url = window.APP_CONFIG.getEndpoint('/reports/sdg.pdf');
        this.triggerDownload(url, "van_udyan_sdg_project_report.pdf");
    }
}

window.ApiService = ApiService;
