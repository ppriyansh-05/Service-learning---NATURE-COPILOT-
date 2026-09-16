/**
 * Frontend Application Configuration
 * Configurable API base URL for FastAPI backend connection.
 */
window.APP_CONFIG = {
    // Configurable API base URL (can be overridden via environment or global variable)
    API_BASE_URL: window.VITE_API_BASE_URL || "http://localhost:8000",
    API_V1_STR: "/api/v1",
    
    // Helper to compute full endpoint URL
    getEndpoint: function(path) {
        if (path.startsWith("/health")) {
            return this.API_BASE_URL + path;
        }
        return this.API_BASE_URL + this.API_V1_STR + path;
    }
};
