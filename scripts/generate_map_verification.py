"""
Generate Map Verification HTML for Phase 1 Geographical Foundation
Creates a standalone Leaflet HTML page for visual verification of polygons.
"""

import json
import os

def generate_map_html():
    raw_boundary_path = os.path.join('data', 'raw', 'van_udyan_boundary.geojson')
    raw_zones_path = os.path.join('data', 'raw', 'van_udyan_zones.geojson')
    output_html_path = os.path.join('docs', 'map_verification.html')
    
    with open(raw_boundary_path, 'r', encoding='utf-8') as f:
        boundary_data = json.load(f)
        
    with open(raw_zones_path, 'r', encoding='utf-8') as f:
        zones_data = json.load(f)
        
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bavdhan Van Udyan - Geographical Foundation Verification</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <style>
        body {{ margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
        #map {{ height: 85vh; width: 100%; }}
        .header {{ background-color: #1b4332; color: white; padding: 15px 20px; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
        .header h1 {{ margin: 0; font-size: 20px; }}
        .header p {{ margin: 5px 0 0 0; font-size: 13px; opacity: 0.9; }}
        .legend {{ background: white; padding: 12px 15px; border-radius: 8px; box-shadow: 0 0 15px rgba(0,0,0,0.2); font-size: 13px; line-height: 1.8; }}
        .legend-color {{ display: inline-block; width: 14px; height: 14px; margin-right: 8px; vertical-align: middle; border-radius: 3px; border: 1px solid #333; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌳 Bavdhan Van Udyan — Geographical Foundation Verification (Phase 1)</h1>
        <p>Location: Plus Code GQ9J+74Q | Address: Lantana Gardens, Bavdhan, Pune, Maharashtra 411021</p>
    </div>
    <div id="map"></div>

    <script>
        const map = L.map('map').setView([18.5188, 73.7800], 17);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 19,
            attribution: '© OpenStreetMap contributors | RSWF NGO'
        }}).addTo(map);

        const boundaryData = {json.dumps(boundary_data)};
        const zonesData = {json.dumps(zones_data)};

        // Render Van Udyan Boundary
        const boundaryLayer = L.geoJSON(boundaryData, {{
            style: {{
                color: '#d90429',
                weight: 3,
                opacity: 0.9,
                fillColor: '#ef233c',
                fillOpacity: 0.15,
                dashArray: '5, 5'
            }},
            onEachFeature: function(feature, layer) {{
                layer.bindPopup('<b>' + feature.properties.name + '</b><br>Complete Project Area Boundary<br>CRS: EPSG:4326');
            }}
        }}).addTo(map);

        const zoneColors = {{
            'ZONE A': '#0077b6',
            'ZONE B': '#2a9d8f',
            'ZONE C': '#e76f51'
        }};

        // Render Active Zones
        const zonesLayer = L.geoJSON(zonesData, {{
            style: function(feature) {{
                const name = feature.properties.name;
                const color = zoneColors[name] || '#9b5de5';
                return {{
                    color: color,
                    weight: 2.5,
                    opacity: 1.0,
                    fillColor: color,
                    fillOpacity: 0.45
                }};
            }},
            onEachFeature: function(feature, layer) {{
                layer.bindPopup('<b>' + feature.properties.name + '</b><br>Active RSWF Working Zone<br>Status: ' + feature.properties.status);
            }}
        }}).addTo(map);

        map.fitBounds(boundaryLayer.getBounds());

        // Legend
        const legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function(map) {{
            const div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<b>Layer Legend</b><br>' +
                '<div><span class="legend-color" style="background: #ef233c; border-style: dashed;"></span> Full Van Udyan Boundary</div>' +
                '<div><span class="legend-color" style="background: #0077b6;"></span> Zone A (Active)</div>' +
                '<div><span class="legend-color" style="background: #2a9d8f;"></span> Zone B (Active)</div>' +
                '<div><span class="legend-color" style="background: #e76f51;"></span> Zone C (Active)</div>';
            return div;
        }};
        legend.addTo(map);
    </script>
</body>
</html>
"""
    with open(output_html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Generated visual verification map: {output_html_path}")

if __name__ == "__main__":
    generate_map_html()
