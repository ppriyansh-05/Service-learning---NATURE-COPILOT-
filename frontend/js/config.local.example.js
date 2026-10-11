// Deploy-time frontend override.
//
// Copy this file to `config.local.js` at deploy time (don't commit `config.local.js` to git) and
// edit the URL to point at your deployed backend. The dashboard will use this URL for every API
// call. If this file is missing, the dashboard falls back to same-origin, then to http://localhost:8000.
//
// Example — Render-hosted backend:
window.APP_CONFIG_OVERRIDE = {
    API_BASE_URL: "https://van-udyan-backend.onrender.com"
};
