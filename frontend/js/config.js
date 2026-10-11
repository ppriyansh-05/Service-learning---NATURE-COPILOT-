/**
 * Frontend Application Configuration
 *
 * API_BASE_URL resolution (first match wins):
 *   1. window.VITE_API_BASE_URL set by a build pipeline
 *   2. window.APP_CONFIG_OVERRIDE.API_BASE_URL from config.local.js (deploy-time injected file)
 *   3. The same origin as the frontend, when it is served over http/https (deployed single-origin setup)
 *   4. http://localhost:8000 (local dev with separate backend)
 */
(function () {
    function resolveApiBaseUrl() {
        if (typeof window.VITE_API_BASE_URL === "string" && window.VITE_API_BASE_URL) {
            return window.VITE_API_BASE_URL.replace(/\/+$/, "");
        }
        if (window.APP_CONFIG_OVERRIDE && typeof window.APP_CONFIG_OVERRIDE.API_BASE_URL === "string" && window.APP_CONFIG_OVERRIDE.API_BASE_URL) {
            return window.APP_CONFIG_OVERRIDE.API_BASE_URL.replace(/\/+$/, "");
        }
        // Local dev always talks to a separate backend on port 8000 (the frontend serves on 5173).
        const host = location.hostname;
        if (host === "localhost" || host === "127.0.0.1" || host === "" || host.endsWith(".localhost")) {
            return "http://localhost:8000";
        }
        // Deployed: default to the frontend's own origin. For split frontend/backend hosts,
        // set APP_CONFIG_OVERRIDE in /js/config.local.js (built by scripts/build_frontend_config.js).
        if (location.protocol === "http:" || location.protocol === "https:") {
            return location.origin;
        }
        return "http://localhost:8000";
    }

    window.APP_CONFIG = {
        API_BASE_URL: resolveApiBaseUrl(),
        API_V1_STR: "/api/v1",

        // Helper to compute full endpoint URL
        getEndpoint: function (path) {
            if (path.startsWith("/health") || path.startsWith("/uploads") || path.startsWith("/thumbs")) {
                return this.API_BASE_URL + path;
            }
            return this.API_BASE_URL + this.API_V1_STR + path;
        }
    };
})();
