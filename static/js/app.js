// R.O.O.K - Resilient Observation & Outlook Kernel Core JS

// App state management
const AppState = {
    activePanel: 'dashboard',
    activeTimeline: 'present', // 'past', 'present', 'future'
    activeLayers: {
        satellite: true,
        rainfall: true,
        temperature: false,
        humidity: false,
        wind: false,
        pressure: false
    },
    simulator: {
        temp: 0.0,
        rain: 0.0,
        humidity: 0.0
    },
    selectedDistrict: 'Andhra Pradesh',
    selectedLat: 15.9129,          // updated on map click / station select
    selectedLng: 79.7400,
    map: null,
    districtLayer: null,
    apGeoJSON: null,
    overlayLayers: {},
    charts: {},
    clickedMarker: null,
    satelliteLayers: null,
    darkBaseLayer: null
};

// Andhra Pradesh coordinates center & zoom bounds (post-split center)
const AP_CENTER = [15.9129, 79.7400];
const AP_ZOOM = 7;

// Fallback Andhra Pradesh boundary polygon coordinates for premium highlight if GeoJSON fails
const AP_BOUNDARY_COORDS = [
    [13.5, 80.0], [13.4, 79.2], [13.7, 78.5], [14.0, 78.0], 
    [13.8, 77.0], [14.5, 76.8], [15.2, 77.2], [15.8, 77.0], 
    [16.2, 78.0], [16.0, 79.0], [16.8, 79.8], [17.2, 80.8], 
    [17.5, 81.3], [18.2, 82.5], [18.8, 83.5], [19.1, 84.6], 
    [18.5, 84.3], [17.5, 82.5], [16.5, 81.5], [16.0, 80.5], 
    [15.2, 80.1], [14.0, 80.1]
];

// District stations coordinate mapping
const DISTRICT_STATIONS = [
    { name: "Anantapur", coords: [14.6819, 77.6006], temp: 34.2, rain: 2.1, humidity: 55, wind: 15, dir: "W", pressure: 1008 },
    { name: "Chittoor", coords: [13.2172, 79.1003], temp: 32.0, rain: 4.5, humidity: 68, wind: 12, dir: "SW", pressure: 1009 },
    { name: "East Godavari", coords: [17.2305, 81.8282], temp: 31.8, rain: 22.4, humidity: 88, wind: 22, dir: "SW", pressure: 1007 },
    { name: "Guntur", coords: [16.3067, 80.4365], temp: 33.5, rain: 11.2, humidity: 75, wind: 18, dir: "WSW", pressure: 1007 },
    { name: "Krishna", coords: [16.1667, 81.1333], temp: 32.9, rain: 14.8, humidity: 82, wind: 20, dir: "SW", pressure: 1008 },
    { name: "Kurnool", coords: [15.8281, 78.0373], temp: 35.1, rain: 1.0, humidity: 52, wind: 14, dir: "WNW", pressure: 1009 },
    { name: "Prakasam", coords: [15.5057, 79.6450], temp: 33.8, rain: 3.2, humidity: 64, wind: 16, dir: "SSW", pressure: 1010 },
    { name: "Srikakulam", coords: [18.2949, 83.8938], temp: 30.5, rain: 28.6, humidity: 92, wind: 25, dir: "SSW", pressure: 1006 },
    { name: "Nellore", coords: [14.4426, 79.9865], temp: 33.0, rain: 5.1, humidity: 70, wind: 17, dir: "S", pressure: 1011 },
    { name: "Visakhapatnam", coords: [17.6868, 83.2185], temp: 31.2, rain: 18.5, humidity: 85, wind: 24, dir: "SW", pressure: 1006 },
    { name: "Vizianagaram", coords: [18.1124, 83.3989], temp: 30.9, rain: 21.0, humidity: 89, wind: 21, dir: "SSW", pressure: 1006 },
    { name: "West Godavari", coords: [16.8105, 81.4288], temp: 32.1, rain: 19.3, humidity: 86, wind: 19, dir: "WSW", pressure: 1008 },
    { name: "YSR Kadapa", coords: [14.4673, 78.8242], temp: 34.6, rain: 1.8, humidity: 58, wind: 13, dir: "W", pressure: 1009 }
];

// ─── Windy-Style Smooth Color Gradient Stops (each parameter) ────────────────
// Format: { val: threshold, r, g, b, a (0-255 alpha) }
const TEMP_COLOR_STOPS = [
    { val: 14, r: 30,  g: 60,  b: 255, a: 200 },  // Cool blue
    { val: 20, r: 0,   g: 140, b: 220, a: 192 },  // Cyan-blue
    { val: 25, r: 0,   g: 200, b: 100, a: 185 },  // Green
    { val: 29, r: 160, g: 220, b: 0,   a: 185 },  // Yellow-green
    { val: 32, r: 255, g: 200, b: 0,   a: 185 },  // Yellow
    { val: 34, r: 255, g: 100, b: 0,   a: 190 },  // Orange
    { val: 36, r: 220, g: 20,  b: 0,   a: 195 },  // Hot red
    { val: 40, r: 180, g: 0,   b: 80,  a: 200 },  // Crimson
];

const RAIN_COLOR_STOPS = [
    { val: 0,  r: 180, g: 200, b: 240, a: 12  },  // Dry - near transparent
    { val: 1,  r: 120, g: 180, b: 255, a: 65  },  // Trace - light blue
    { val: 5,  r: 50,  g: 120, b: 255, a: 135 },  // Light - blue
    { val: 15, r: 70,  g: 40,  b: 220, a: 172 },  // Moderate - indigo
    { val: 25, r: 130, g: 0,   b: 200, a: 195 },  // Heavy - violet
    { val: 40, r: 80,  g: 0,   b: 140, a: 215 },  // Extreme - deep purple
];

const WIND_COLOR_STOPS = [
    { val: 0,  r: 80,  g: 200, b: 120, a: 140 },  // Calm - green
    { val: 8,  r: 0,   g: 200, b: 220, a: 155 },  // Light - cyan
    { val: 16, r: 200, g: 220, b: 0,   a: 172 },  // Moderate - yellow
    { val: 22, r: 255, g: 140, b: 0,   a: 188 },  // Fresh - orange
    { val: 28, r: 220, g: 30,  b: 0,   a: 200 },  // Strong - red
    { val: 40, r: 160, g: 0,   b: 120, a: 215 },  // Gale - magenta
];

const PRESSURE_COLOR_STOPS = [
    { val: 1002, r: 60,  g: 100, b: 255, a: 172 },  // Very low - blue
    { val: 1006, r: 0,   g: 200, b: 200, a: 160 },  // Low - teal
    { val: 1008, r: 100, g: 220, b: 80,  a: 150 },  // Normal - green
    { val: 1012, r: 240, g: 200, b: 0,   a: 160 },  // Normal-high - yellow
    { val: 1016, r: 220, g: 80,  b: 0,   a: 172 },  // High - orange-red
];

const HUMIDITY_COLOR_STOPS = [
    { val: 40,  r: 220, g: 170, b: 40,  a: 140 },  // Dry - amber
    { val: 58,  r: 100, g: 200, b: 80,  a: 155 },  // Moderate - green
    { val: 72,  r: 0,   g: 190, b: 160, a: 170 },  // Humid - teal
    { val: 85,  r: 0,   g: 100, b: 220, a: 185 },  // Very humid - blue
    { val: 100, r: 60,  g: 30,  b: 200, a: 200 },  // Saturated - indigo
];


document.addEventListener("DOMContentLoaded", () => {
    // Initial active panel - read from main-layout div (Django sets it there via template)
    const mainLayout = document.querySelector(".main-layout[data-active-panel]");
    const initialPanel = (mainLayout && mainLayout.dataset.activePanel) || 'dashboard';
    initMap();
    initCharts();
    setupEventListeners();
    switchPanel(initialPanel);
    fetchWeatherData();
    fetchAlerts();
    syncLayerButtonsUI();
    updateMapLegend();
    updateMapLayers();
    checkModelStatus();    // Show XGBoost/IDW badge

    // Fade-in dashboard layout elements
    gsap.from(".main-layout", { opacity: 0, duration: 0.8, ease: "power2.out" });
});

// Check model status on load — updates the data-source badge in Live Weather panel
async function checkModelStatus() {
    try {
        const resp = await fetch('/api/model-status/');
        const data = await resp.json();
        const badge = document.getElementById('model-source-badge');
        if (badge) {
            if (data.loaded) {
                badge.textContent = '⚡ XGBoost Model Active';
                badge.className = 'text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
            } else {
                badge.textContent = '📍 IDW Spatial Estimate';
                badge.className = 'text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/30';
            }
        }
    } catch (e) {
        console.warn('[R.O.O.K] Model status check failed:', e);
    }
}

// Map Initialization
function initMap() {
    // Create map with zoom controls disabled (custom buttons used)
    AppState.map = L.map('map', {
        zoomControl: false,
        attributionControl: false,
        minZoom: 5,
        maxZoom: 18 // Increase zoom level to allow detailed close-up views of streets
    }).setView(AP_CENTER, AP_ZOOM);

    // Create satellite layers group
    const satImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, USDA, USGS'
    });
    const satStreets = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        opacity: 0.8,
        attribution: 'Reference &copy; Esri, OSM'
    });
    const satPlaces = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        opacity: 0.95
    });

    AppState.satelliteLayers = L.layerGroup([satImagery, satStreets, satPlaces]);
    AppState.darkBaseLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19,
        attribution: '&copy; CartoDB &copy; OpenStreetMap'
    });

    // Add base layer based on active state
    if (AppState.activeLayers.satellite) {
        AppState.satelliteLayers.addTo(AppState.map);
    } else {
        AppState.darkBaseLayer.addTo(AppState.map);
    }

    // Map Click Listener for Geographic Queries
    AppState.map.on('click', async (e) => {
        const lat = e.latlng.lat;
        const lng = e.latlng.lng;
        
        // Draw clicked marker immediately (no delay)
        if (AppState.clickedMarker) AppState.map.removeLayer(AppState.clickedMarker);
        const clickIcon = L.divIcon({
            className: 'weather-layer-div-icon',
            html: `
                <div class="weather-station-marker" style="--windy-color: #ffffff">
                    <div class="radar-ping" style="border-color: rgba(255,255,255,0.7)"></div>
                    <div class="station-core" style="border-color: #ffffff; box-shadow: 0 0 10px rgba(255,255,255,0.8)">
                        <div class="w-1.5 h-1.5 bg-white rounded-full"></div>
                    </div>
                </div>
            `,
            iconSize: [28, 28], iconAnchor: [14, 14]
        });
        AppState.clickedMarker = L.marker([lat, lng], { icon: clickIcon }).addTo(AppState.map);

        // Store location for simulator to use
        AppState.selectedLat = lat;
        AppState.selectedLng = lng;

        // Update coordinates immediately
        const coordsEl = document.getElementById("clicked-coords");
        if (coordsEl) coordsEl.innerText = `${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`;
        const locInd = document.getElementById("location-indicator");
        if (locInd) locInd.innerText = `${lat.toFixed(2)}, ${lng.toFixed(2)}`;

        // Query real API for predictions
        await queryLocation(lat, lng);
    });

    // ── queryLocation: calls /api/predict/ and updates the sidebar ────────────
    window.queryLocation = async function(lat, lng) {
        const nameEl     = document.getElementById("clicked-area-name");
        const tempEl     = document.getElementById("clicked-temp");
        const rainEl     = document.getElementById("clicked-rain");
        const windElLoc  = document.getElementById("clicked-wind");
        const pressureEl = document.getElementById("clicked-pressure");
        const badge      = document.getElementById('model-source-badge');

        // Find nearest station name for display
        let nearestName = 'Andhra Pradesh';
        let minDist = Infinity;
        DISTRICT_STATIONS.forEach(s => {
            const d = Math.hypot(s.coords[0] - lat, s.coords[1] - lng);
            if (d < minDist) { minDist = d; nearestName = 'Near ' + s.name; }
        });
        if (nameEl) nameEl.innerText = nearestName;

        try {
            const resp = await fetch('/api/predict/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({ lat, lng, date: new Date().toISOString() })
            });
            const data = await resp.json();

            if (tempEl)     tempEl.innerText = `${data.tmax_c} °C`;
            if (rainEl)     rainEl.innerText = `${data.rainfall_mm} mm`;
            // Wind/pressure from nearest station (not yet in model output)
            const nearSt = DISTRICT_STATIONS.reduce((a, b) =>
                Math.hypot(a.coords[0]-lat, a.coords[1]-lng) < Math.hypot(b.coords[0]-lat, b.coords[1]-lng) ? a : b
            );
            if (windElLoc)  windElLoc.innerText = `${nearSt.wind} kt ${nearSt.dir}`;
            if (pressureEl) pressureEl.innerText = `${nearSt.pressure} hPa`;

            // Update home KPIs
            animateValue('kpi-temp', data.tmax_c, ' °C');
            animateValue('kpi-rain', data.rainfall_mm, ' mm');
            animateValue('kpi-humidity', nearSt.humidity, '%');
            animateValue('kpi-wind', nearSt.wind, ' kt');
            const dirEl = document.getElementById('kpi-wind-dir');
            if (dirEl) dirEl.innerText = nearSt.dir;

            // Update model source badge
            if (badge) {
                if (data.source === 'xgboost') {
                    badge.textContent = '⚡ XGBoost Model';
                    badge.className = 'text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
                } else {
                    badge.textContent = '📍 IDW Estimate';
                    badge.className = 'text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-amber-500/20 text-amber-400 border border-amber-500/30';
                }
            }

        } catch (err) {
            console.warn('[R.O.O.K] Predict API failed, using deterministic mock:', err);
            // Deterministic fallback (coordinate-seeded, never undefined)
            const tempVal = parseFloat((28.5 + (Math.sin(lat * 12) * Math.cos(lng * 8) * 4.5)).toFixed(1));
            const rainVal = parseFloat(Math.max(0, (8.0 + (Math.cos(lat * 9) * Math.sin(lng * 12) * 12.0))).toFixed(1));
            const windVal = Math.max(2, Math.round(14 + (Math.sin(lat + lng) * 8)));
            const windDirs = ['N','NE','E','SE','S','SW','W','NW'];
            const windDir  = windDirs[Math.abs(Math.round(lat * 100 + lng * 100)) % windDirs.length];
            const pressureVal = Math.round(1006 + (Math.cos(lat * 5 + lng * 5) * 4));

            if (tempEl)     tempEl.innerText = `${tempVal} °C`;
            if (rainEl)     rainEl.innerText = `${rainVal} mm`;
            if (windElLoc)  windElLoc.innerText = `${windVal} kt ${windDir}`;
            if (pressureEl) pressureEl.innerText = `${pressureVal} hPa`;
            animateValue('kpi-temp', tempVal, ' °C');
            animateValue('kpi-rain', rainVal, ' mm');
            animateValue('kpi-humidity', Math.min(100, Math.round(55 + tempVal * 0.5)), '%');
            animateValue('kpi-wind', windVal, ' kt');
            const dirEl = document.getElementById('kpi-wind-dir');
            if (dirEl) dirEl.innerText = windDir;
            if (badge) { badge.textContent = '⚠️ Offline Mock'; badge.className = 'text-[9px] px-2 py-0.5 rounded font-bold uppercase tracking-wider bg-slate-700/40 text-slate-400 border border-slate-600/30'; }
        }
    };

    // Fetch and render high-fidelity precise Andhra Pradesh GeoJSON boundary (post-split)
    fetch('/static/geojson/andhra_pradesh.geojson')
        .then(res => {
            if (!res.ok) throw new Error("GeoJSON not found");
            return res.json();
        })
        .then(data => {
            AppState.apGeoJSON = data;
            AppState.districtLayer = L.geoJSON(data, {
                style: {
                    color: '#ffffff',
                    weight: 2.5,
                    opacity: 0.95,
                    fillColor: 'transparent',
                    fillOpacity: 0,
                    dashArray: '6, 6',
                    className: 'ap-boundary-path' // CSS Animated Neon border glow
                }
            }).addTo(AppState.map);
            
            // Add prominent state label centered in the state, matching DT.png
            const stateLabelIcon = L.divIcon({
                className: 'map-state-label text-center font-display font-bold text-white tracking-widest pointer-events-none select-none',
                html: 'ANDHRA PRADESH',
                iconSize: [200, 30],
                iconAnchor: [100, 15]
            });
            L.marker([15.80, 79.70], { icon: stateLabelIcon, interactive: false }).addTo(AppState.map);

            // Re-render spatial layers now that the high-fidelity GeoJSON boundary is loaded
            updateMapLayers();
        })
        .catch(err => {
            console.warn("Falling back to approximate coords due to GeoJSON error: ", err);
            // Fallback highlight polygon
            AppState.districtLayer = L.polygon(AP_BOUNDARY_COORDS, {
                color: '#ffffff',
                weight: 2.5,
                opacity: 0.95,
                fillColor: 'transparent',
                fillOpacity: 0,
                dashArray: '6, 6',
                className: 'ap-boundary-path'
            }).addTo(AppState.map);
            
            const stateLabelIcon = L.divIcon({
                className: 'map-state-label text-center font-display font-bold text-white tracking-widest pointer-events-none select-none',
                html: 'ANDHRA PRADESH',
                iconSize: [200, 30],
                iconAnchor: [100, 15]
            });
            L.marker([15.80, 79.70], { icon: stateLabelIcon, interactive: false }).addTo(AppState.map);
        });

    // Add district markers
    DISTRICT_STATIONS.forEach(station => {
        const markerIcon = L.divIcon({
            className: 'weather-station-div-icon',
            html: `
                <div class="weather-station-marker">
                    <div class="radar-ping"></div>
                    <div class="station-core">
                        <svg class="anemometer-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="3"></circle>
                            <line x1="12" y1="2" x2="12" y2="10"></line>
                            <line x1="12" y1="14" x2="12" y2="22"></line>
                            <line x1="2" y1="12" x2="10" y2="12"></line>
                            <line x1="14" y1="12" x2="22" y2="12"></line>
                        </svg>
                    </div>
                </div>
            `,
            iconSize: [28, 28],
            iconAnchor: [14, 14]
        });

        const marker = L.marker(station.coords, { icon: markerIcon }).addTo(AppState.map);
        marker.bindTooltip(`
            <div class="bg-navy-800 border border-slate-700 p-2 rounded text-xs text-slate-200">
                <p class="font-bold font-display text-cyan-400">${station.name}</p>
                <p>Temp: ${station.temp}°C</p>
                <p>Rain: ${station.rain} mm</p>
                <p>Humidity: ${station.humidity}%</p>
            </div>
        `, { direction: 'top', className: 'custom-leaflet-tooltip' });

        marker.on('click', () => {
            selectDistrict(station);
        });
    });
}

// Select District Station details
function selectDistrict(station) {
    AppState.selectedDistrict = station.name;
    document.getElementById("location-indicator").innerText = station.name;
    
    // Update selected location query panel UI
    const nameEl = document.getElementById("clicked-area-name");
    const coordsEl = document.getElementById("clicked-coords");
    const tempEl = document.getElementById("clicked-temp");
    const rainEl = document.getElementById("clicked-rain");
    const windElLoc = document.getElementById("clicked-wind");
    const pressureEl = document.getElementById("clicked-pressure");
    
    if (nameEl) nameEl.innerText = station.name;
    if (coordsEl) coordsEl.innerText = `${station.coords[0].toFixed(4)}° N, ${station.coords[1].toFixed(4)}° E`;
    if (tempEl) tempEl.innerText = `${station.temp} °C`;
    if (rainEl) rainEl.innerText = `${station.rain} mm`;
    if (windElLoc) windElLoc.innerText = `${station.wind} kt ${station.dir}`;
    if (pressureEl) pressureEl.innerText = `${station.pressure} hPa`;

    // Draw temporary clicked marker pulse
    if (AppState.clickedMarker) {
        AppState.map.removeLayer(AppState.clickedMarker);
    }
    const clickIcon = L.divIcon({
        className: 'weather-layer-div-icon',
        html: `
            <div class="weather-station-marker" style="--windy-color: #ffffff">
                <div class="radar-ping" style="border-color: rgba(255,255,255,0.7)"></div>
                <div class="station-core" style="border-color: #ffffff; box-shadow: 0 0 10px rgba(255,255,255,0.8)">
                    <div class="w-1.5 h-1.5 bg-white rounded-full"></div>
                </div>
            </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14]
    });
    AppState.clickedMarker = L.marker(station.coords, { icon: clickIcon }).addTo(AppState.map);

    // Animate KPI Updates
    animateValue("kpi-temp", station.temp, " °C");
    animateValue("kpi-rain", station.rain, " mm");
    animateValue("kpi-humidity", station.humidity, "%");
    animateValue("kpi-wind", station.wind, " kt");
    const dirEl = document.getElementById("kpi-wind-dir");
    if (dirEl) dirEl.innerText = station.dir;

    // Update bottom row Current Conditions values
    animateValue("current-cond-rain", station.rain, " mm");
    animateValue("current-cond-temp-max", (station.temp + 1.2), " °C");
    animateValue("current-cond-temp-min", (station.temp - 6.5), " °C");
    animateValue("current-cond-humidity", station.humidity, "%");
    const windEl = document.getElementById("current-cond-wind");
    if (windEl) {
        windEl.innerHTML = `${station.wind} kt <span class="text-[9px] text-cyan-400 font-normal">${station.dir}</span>`;
    }
    
    // Store location on district select so simulator can use it
    AppState.selectedLat = station.coords[0];
    AppState.selectedLng = station.coords[1];

    // Zoom map closer (zoom level 10 is perfect for street level context)
    AppState.map.setView(station.coords, 10, { animate: true, duration: 1.5 });
    
    // Also query real prediction for this station
    queryLocation(station.coords[0], station.coords[1]);
}

// Reset Map View to default
function resetMapView() {
    AppState.selectedDistrict = "Andhra Pradesh";
    document.getElementById("location-indicator").innerText = "Andhra Pradesh";
    AppState.map.setView(AP_CENTER, AP_ZOOM, { animate: true, duration: 1.5 });
    fetchWeatherData(); // restore original KPIs
}

// Custom value animation
function animateValue(id, value, suffix) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = parseFloat(el.innerText) || 0;
    const duration = 0.5;
    const obj = { val: start };
    
    gsap.to(obj, {
        val: value,
        duration: duration,
        onUpdate: () => {
            el.innerText = obj.val.toFixed(1) + suffix;
        }
    });
}

function getPressureColor(p) {
    if (p < 1004) return '#60a5fa'; // Low pressure - blue
    if (p < 1008) return '#2dd4bf'; // Normal pressure - teal
    if (p < 1012) return '#eab308'; // High pressure - yellow
    return '#ef4444'; // Extreme high pressure - red
}

function syncLayerButtonsUI() {
    document.querySelectorAll(".layer-btn").forEach(btn => {
        const layer = btn.getAttribute("data-layer");
        const isActive = AppState.activeLayers[layer];
        if (isActive) {
            btn.style.background = 'rgba(0, 188, 212, 0.22)';
            btn.style.color = '#26C6DA';
            btn.style.boxShadow = '0 0 14px rgba(0, 188, 212, 0.25) inset';
        } else {
            btn.style.background = '';
            btn.style.color = '';
            btn.style.boxShadow = '';
        }
    });
}

function updateMapLegend() {
    const legendEl = document.getElementById("map-legend");
    if (!legendEl) return;

    let title = "";
    let stops = null;
    let explanation = "";

    if (AppState.activeLayers.rainfall) {
        title = 'Rainfall (mm)';
        stops = RAIN_COLOR_STOPS;
        explanation = "Dry ➔ Light ➔ Heavy ➔ Extreme";
    } else if (AppState.activeLayers.temperature) {
        title = 'Temperature (°C)';
        stops = TEMP_COLOR_STOPS;
        explanation = "Cool ➔ Mild ➔ Warm ➔ Hot ➔ Extreme";
    } else if (AppState.activeLayers.wind) {
        title = 'Wind Speed (kt)';
        stops = WIND_COLOR_STOPS;
        explanation = "Calm ➔ Light ➔ Fresh ➔ Gale";
    } else if (AppState.activeLayers.pressure) {
        title = 'Pressure (hPa)';
        stops = PRESSURE_COLOR_STOPS;
        explanation = "Low (Stormy) ➔ Normal ➔ High (Fair)";
    } else if (AppState.activeLayers.humidity) {
        title = 'Humidity (%)';
        stops = HUMIDITY_COLOR_STOPS;
        explanation = "Dry ➔ Moderate ➔ Humid ➔ Saturated";
    } else {
        legendEl.classList.add("hidden");
        return;
    }

    legendEl.classList.remove("hidden");

    // Build horizontal CSS gradient from color stops (full opacity for legend)
    const gradColors = stops.map(s => `rgb(${s.r},${s.g},${s.b})`).join(', ');

    let html = `<p style="font-size:8px;font-weight:700;letter-spacing:0.1em;text-transform:uppercase;color:#94a3b8;margin:0 0 6px 0;">${title}</p>`;
    html += `<div style="width:130px;height:9px;border-radius:5px;background:linear-gradient(to right,${gradColors});"></div>`;
    html += `<div style="display:flex;justify-content:space-between;font-size:8px;color:#64748b;font-family:monospace;margin-top:4px;">`;
    html += `<span>${stops[0].val}</span>`;
    html += `<span>${stops[Math.floor(stops.length / 2)].val}</span>`;
    html += `<span>${stops[stops.length - 1].val}+</span>`;
    html += `</div>`;
    html += `<p style="font-size:7.5px;color:#cbd5e1;margin-top:5px;font-style:italic;text-align:center;letter-spacing:0.02em;">${explanation}</p>`;

    legendEl.innerHTML = html;
}

// Setup Event Listeners
function setupEventListeners() {
    // Nav Items Panel Toggle
    document.querySelectorAll(".nav-item").forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const panel = item.getAttribute("data-panel");
            if (panel) {
                switchPanel(panel);
                window.history.pushState({}, '', `/${panel === 'dashboard' ? '' : panel + '/'}`);
            }
        });
    });

    // Timeline Selector Slider
    const timelineSteps = ['past', 'present', 'future'];
    const rangeSlider = document.getElementById("timelineRange");
    if (rangeSlider) {
        rangeSlider.addEventListener("input", (e) => {
            const val = e.target.value;
            const step = timelineSteps[val];
            setTimeline(step);
        });
    }

    // Map Layer Toggles
    document.querySelectorAll(".layer-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const layer = btn.getAttribute("data-layer");
            if (layer === 'satellite') {
                AppState.activeLayers.satellite = !AppState.activeLayers.satellite;
            } else {
                const wasActive = AppState.activeLayers[layer];
                const weatherLayers = ['rainfall', 'temperature', 'humidity', 'wind', 'pressure'];
                weatherLayers.forEach(l => {
                    AppState.activeLayers[l] = false;
                });
                AppState.activeLayers[layer] = !wasActive;
            }
            
            syncLayerButtonsUI();
            updateMapLegend();
            updateMapLayers();
        });
    });

    // Custom Map zoom controls
    document.getElementById("zoom-in")?.addEventListener("click", () => AppState.map.zoomIn());
    document.getElementById("zoom-out")?.addEventListener("click", () => AppState.map.zoomOut());
    document.getElementById("re-center")?.addEventListener("click", () => resetMapView());

    // Scenario Simulator Perturbations
    const sliders = ['temp', 'rain', 'humidity'];
    sliders.forEach(key => {
        const slider = document.getElementById(`sim-${key}`);
        const valIndicator = document.getElementById(`sim-${key}-val`);
        if (slider) {
            slider.addEventListener("input", (e) => {
                let displayVal = e.target.value;
                if (key === 'temp') displayVal = (parseFloat(displayVal) > 0 ? '+' : '') + parseFloat(displayVal).toFixed(1) + '°C';
                if (key === 'rain') displayVal = (parseInt(displayVal) > 0 ? '+' : '') + displayVal + '%';
                if (key === 'humidity') displayVal = (parseInt(displayVal) > 0 ? '+' : '') + displayVal + '%';
                
                valIndicator.innerText = displayVal;
                AppState.simulator[key] = parseFloat(e.target.value);
                triggerSimulation();
            });
        }
    });

    // Handle Report Generators
    document.getElementById("btn-generate-report")?.addEventListener("click", () => generateReport("monsoon"));
    document.getElementById("btn-export-csv")?.addEventListener("click", () => exportCSV("monsoon"));

    // Search Autocomplete Logic
    const searchInput = document.getElementById("search-input");
    const searchDropdown = document.getElementById("search-dropdown");

    if (searchInput && searchDropdown) {
        searchInput.addEventListener("input", (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                searchDropdown.innerHTML = "";
                searchDropdown.classList.add("hidden");
                return;
            }

            // Filter DISTRICT_STATIONS
            const matches = DISTRICT_STATIONS.filter(s => s.name.toLowerCase().includes(query));

            if (matches.length === 0) {
                searchDropdown.innerHTML = `<div class="px-4 py-2.5 text-xs text-slate-500 italic">No matches found</div>`;
            } else {
                searchDropdown.innerHTML = matches.map(s => `
                    <button class="w-full text-left px-4 py-2.5 text-xs text-slate-300 hover:bg-cyan-500/20 hover:text-cyan-400 transition-colors border-b border-slate-800/30 last:border-b-0 flex items-center justify-between" onclick="handleSearchSelect('${s.name}')">
                        <span class="font-semibold">${s.name}</span>
                        <span class="text-[9px] text-slate-500 font-mono">${s.coords[0].toFixed(2)}, ${s.coords[1].toFixed(2)}</span>
                    </button>
                `).join('');
            }
            searchDropdown.classList.remove("hidden");
        });

        searchInput.addEventListener("keydown", (e) => {
            if (e.key === "Enter") {
                const query = searchInput.value.toLowerCase().trim();
                const match = DISTRICT_STATIONS.find(s => s.name.toLowerCase() === query);
                if (match) {
                    handleSearchSelect(match.name);
                } else {
                    const firstMatch = DISTRICT_STATIONS.find(s => s.name.toLowerCase().includes(query));
                    if (firstMatch) {
                        handleSearchSelect(firstMatch.name);
                    }
                }
            }
        });

        // Hide dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.classList.add("hidden");
            }
        });
    }

    // Global helper for search selection
    window.handleSearchSelect = function(name) {
        const station = DISTRICT_STATIONS.find(s => s.name === name);
        if (station) {
            selectDistrict(station);
            if (searchInput) searchInput.value = station.name;
            if (searchDropdown) {
                searchDropdown.innerHTML = "";
                searchDropdown.classList.add("hidden");
            }
        }
    };
}

// Switch Sidebar Panels
function switchPanel(panelName) {
    AppState.activePanel = panelName;

    // Toggle nav active state
    document.querySelectorAll(".nav-item").forEach(item => {
        if (item.getAttribute("data-panel") === panelName) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });

    const dashboardWidgets = document.getElementById("dashboard-widgets");
    const rightPanelContainer = document.getElementById("right-side-panel-container");
    const layersPanel = document.getElementById("map-layers-panel");
    const mapLegend = document.getElementById("map-legend");

    if (panelName === 'dashboard') {
        // Show dashboard widgets with animation
        if (dashboardWidgets) {
            dashboardWidgets.classList.remove("hidden");
            dashboardWidgets.style.display = "block";
            gsap.to("#dashboard-left-col", { opacity: 1, x: 0, duration: 0.4, ease: "power2.out" });
        }
        if (rightPanelContainer) {
            rightPanelContainer.classList.add("hidden");
        }
        if (layersPanel) {
            layersPanel.classList.add("hidden");
        }
        if (mapLegend) {
            mapLegend.classList.remove("hidden");
        }
    } else {
        // Hide dashboard widgets
        if (dashboardWidgets) {
            dashboardWidgets.classList.add("hidden");
            dashboardWidgets.style.display = "none";
        }
        
        // Show right panel container
        if (rightPanelContainer) {
            rightPanelContainer.classList.remove("hidden");
        }

        // Toggle layers panel for map-centric overlays
        if (layersPanel) {
            if (['weather', 'satellite', 'digital-twin', 'simulator'].includes(panelName)) {
                layersPanel.classList.remove("hidden");
            } else {
                layersPanel.classList.add("hidden");
            }
        }

        // Keep legend on weather/satellite/analytics
        if (mapLegend) {
            if (['weather', 'satellite', 'digital-twin', 'analytics'].includes(panelName)) {
                mapLegend.classList.remove("hidden");
            } else {
                mapLegend.classList.add("hidden");
            }
        }

        // Hide all panel wrappers, then show requested with GSAP transition
        const wrappers = document.querySelectorAll(".floating-panel-wrapper");
        wrappers.forEach(wrap => {
            wrap.classList.add("hidden");
            wrap.style.opacity = 0;
        });

        const activeWrap = document.getElementById(`panel-${panelName}`);
        if (activeWrap) {
            activeWrap.classList.remove("hidden");
            gsap.to(activeWrap, { opacity: 1, duration: 0.4, x: 0, ease: "power2.out" });
        }

        // Re-initialize/resize ApexCharts on Analytics panel activation to recalculate widths
        if (panelName === 'analytics') {
            setTimeout(() => {
                initCharts();
            }, 100);
        }
    }
}

// Timeline State Manipulator
function setTimeline(step) {
    AppState.activeTimeline = step;
    const label = document.getElementById("timeline-step-label");
    const indicator = document.getElementById("timeline-indicator-text");
    
    if (step === 'past') {
        label.innerText = "Historical Reanalysis (2020)";
        indicator.innerText = "HISTORICAL";
        indicator.className = "text-yellow-400 font-bold tracking-wider text-[10px] bg-yellow-400/10 px-2 py-0.5 rounded";
    } else if (step === 'present') {
        label.innerText = "Real-time Operations (2026)";
        indicator.innerText = "REAL-TIME OPERATIONAL";
        indicator.className = "text-cyan-400 font-bold tracking-wider text-[10px] bg-cyan-400/10 px-2 py-0.5 rounded";
    } else {
        label.innerText = "AI Ensemble Projections (2036)";
        indicator.innerText = "PROJECTION MODEL";
        indicator.className = "text-rose-400 font-bold tracking-wider text-[10px] bg-rose-400/10 px-2 py-0.5 rounded";
    }

    // Fetch new digital twin spatial layers
    fetchDigitalTwinData(step);
}

// Fetch APIs
function fetchWeatherData() {
    fetch('/api/weather/')
        .then(res => res.json())
        .then(data => {
            document.getElementById("kpi-temp").innerText = data.current.temperature + " °C";
            document.getElementById("kpi-rain").innerText = data.current.rainfall + " mm";
            document.getElementById("kpi-humidity").innerText = data.current.humidity + "%";
            document.getElementById("kpi-wind").innerText = data.current.wind_speed + " kt";
            document.getElementById("kpi-wind-dir").innerText = data.current.wind_direction;

            // Update Analytics Current Conditions defaults
            document.getElementById("current-cond-rain").innerText = data.current.rainfall + " mm";
            document.getElementById("current-cond-temp-max").innerText = "33.1 °C";
            document.getElementById("current-cond-temp-min").innerText = "25.6 °C";
            document.getElementById("current-cond-humidity").innerText = data.current.humidity + "%";
            const windEl = document.getElementById("current-cond-wind");
            if (windEl) {
                windEl.innerHTML = `${data.current.wind_speed} kt <span class="text-[9px] text-cyan-400 font-normal">${data.current.wind_direction}</span>`;
            }
        });
}

function fetchAlerts() {
    fetch('/api/alerts/')
        .then(res => res.json())
        .then(data => {
            const container = document.getElementById("alerts-container");
            if (!container) return;
            container.innerHTML = "";
            
            data.forEach(alert => {
                let badgeClass = "badge-low";
                if (alert.severity === "Critical") badgeClass = "badge-critical";
                else if (alert.severity === "High") badgeClass = "badge-high";
                else if (alert.severity === "Medium") badgeClass = "badge-medium";

                container.innerHTML += `
                    <div class="p-3 bg-navy-800/80 rounded border border-slate-700/60 transition duration-200 hover:border-slate-600 flex flex-col gap-1.5 animate-float" style="animation-delay: ${alert.id * 0.1}s">
                        <div class="flex items-center justify-between">
                            <span class="${badgeClass} text-[10px] px-2 py-0.5 rounded uppercase font-bold tracking-wider">${alert.severity}</span>
                            <span class="text-[11px] text-cyan-400 font-display font-medium">${alert.type} Alert</span>
                        </div>
                        <p class="text-xs text-slate-300 font-semibold mt-1">${alert.district}</p>
                        <p class="text-[11px] text-slate-400 leading-relaxed">${alert.description}</p>
                    </div>
                `;
            });
        });
}

// Trigger Scenario Simulation API — now routes through XGBoost /api/predict-simulate/
async function triggerSimulation() {
    const lat = AppState.selectedLat || 15.9129;
    const lng = AppState.selectedLng || 79.7400;

    try {
        const resp = await fetch('/api/predict-simulate/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                lat,
                lng,
                temp_delta:       AppState.simulator.temp,
                rain_delta:       AppState.simulator.rain,
                humidity_change:  AppState.simulator.humidity
            })
        });
        const data = await resp.json();

        // Update Simulator Dashboard
        updateRiskBadge('risk-drought',  data.drought_risk || (data.risk || {}).drought || 'Low');
        updateRiskBadge('risk-flood',    data.flood_risk   || (data.risk || {}).flood   || 'Low');
        updateRiskBadge('risk-heatwave', data.heatwave_risk|| (data.risk || {}).heatwave|| 'Low');
        
        const agriEl = document.getElementById('risk-agri');
        if (agriEl) agriEl.innerText = data.agricultural_impact || 'Optimal Yield Output';
        
        const waterEl = document.getElementById('risk-water');
        if (waterEl) waterEl.innerText = (data.water_stress_index || 45).toFixed(1) + '%';
        
        const progressEl = document.getElementById('stress-progress');
        if (progressEl) progressEl.style.width = (data.water_stress_index || 45) + '%';

        // Modify map boundary style based on risk
        if (AppState.districtLayer) {
            const dr = data.drought_risk || (data.risk || {}).drought;
            const fr = data.flood_risk   || (data.risk || {}).flood;
            if (fr === 'High' || fr === 'Critical') {
                AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#f87171', dashArray: '6, 6' });
            } else if (dr === 'High' || dr === 'Critical') {
                AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#fb923c', dashArray: '6, 6' });
            } else {
                AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', dashArray: '6, 6' });
            }
        }

        // Trigger canvas gradient update with simulation adjustments
        updateMapLayers(true);

    } catch (err) {
        console.warn('[R.O.O.K] Simulate API failed, using legacy engine:', err);
        // Fallback to old SimulatorAPIView
        fetch('/api/simulator/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
            body: JSON.stringify({
                temp_change:      AppState.simulator.temp,
                rainfall_change:  AppState.simulator.rain,
                humidity_change:  AppState.simulator.humidity
            })
        })
        .then(res => res.json())
        .then(data => {
            updateRiskBadge('risk-drought', data.drought_risk);
            updateRiskBadge('risk-flood', data.flood_risk);
            updateRiskBadge('risk-heatwave', data.heatwave_risk);
            document.getElementById('risk-agri').innerText = data.agricultural_impact;
            document.getElementById('risk-water').innerText = data.water_stress_index.toFixed(1) + '%';
            document.getElementById('stress-progress').style.width = data.water_stress_index + '%';
            if (AppState.districtLayer) {
                if (data.flood_risk === 'Critical' || data.flood_risk === 'High') {
                    AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#f87171', dashArray: '6, 6' });
                } else if (data.drought_risk === 'Critical' || data.drought_risk === 'High') {
                    AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#fb923c', dashArray: '6, 6' });
                } else {
                    AppState.districtLayer.setStyle({ fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', dashArray: '6, 6' });
                }
            }
            updateMapLayers(true);
        });
    }
}

function updateRiskBadge(id, level) {
    const el = document.getElementById(id);
    if (!el) return;
    el.innerText = level;
    el.className = "text-xs px-2 py-0.5 rounded font-bold uppercase ";
    if (level === "Critical") el.classList.add("badge-critical");
    else if (level === "High") el.classList.add("badge-high");
    else if (level === "Medium") el.classList.add("badge-medium");
    else el.classList.add("badge-low");
}

// Fetch timeline digital twin interpolation
function fetchDigitalTwinData(step) {
    fetch(`/api/digital-twin/?step=${step}`)
        .then(res => res.json())
        .then(data => {
            updateMapLayers();
        });
}

// Windy color scale helpers
function getTempColor(t) {
    if (t < 20) return '#00d2ff'; // Cool cyan
    if (t < 25) return '#10b981'; // Mild emerald
    if (t < 30) return '#eab308'; // Warm yellow
    if (t < 34) return '#f97316'; // Hot orange
    if (t < 38) return '#ef4444'; // Very hot red
    return '#be123c'; // Extreme crimson
}

function getRainColor(r) {
    if (r <= 0.2) return 'rgba(148, 163, 184, 0.4)'; // dry/trace slate
    if (r <= 5) return '#38bdf8'; // light sky blue
    if (r <= 12) return '#0284c7'; // moderate blue
    if (r <= 22) return '#4f46e5'; // heavy indigo
    return '#7c3aed'; // violent purple
}

function getWindColor(w) {
    if (w < 10) return '#10b981'; // Light emerald
    if (w < 18) return '#00d2ff'; // Moderate cyan
    if (w < 24) return '#eab308'; // Fresh yellow
    if (w < 30) return '#f97316'; // Strong orange
    return '#ef4444'; // Gale red
}

function getHumidityColor(h) {
    if (h < 50) return '#a7f3d0'; // dry pale green
    if (h < 75) return '#0d9488'; // moderate teal
    return '#047857'; // humid dark green
}

function getWindAngle(dir) {
    const mapping = {
        'N': 0, 'NNE': 22.5, 'NE': 45, 'ENE': 67.5,
        'E': 90, 'ESE': 112.5, 'SE': 135, 'SSE': 157.5,
        'S': 180, 'SSW': 202.5, 'SW': 225, 'WSW': 247.5,
        'W': 270, 'WNW': 292.5, 'NW': 315, 'NNW': 337.5
    };
    return mapping[dir] || 0;
}

// ─── Windy-Style IDW Canvas Gradient Helpers ──────────────────────────────────

// Linear interpolation between RGBA color stops
function interpolateColorStops(stops, value) {
    if (value <= stops[0].val) return { r: stops[0].r, g: stops[0].g, b: stops[0].b, a: stops[0].a };
    if (value >= stops[stops.length - 1].val) {
        const s = stops[stops.length - 1];
        return { r: s.r, g: s.g, b: s.b, a: s.a };
    }
    for (let i = 0; i < stops.length - 1; i++) {
        if (value >= stops[i].val && value <= stops[i + 1].val) {
            const t = (value - stops[i].val) / (stops[i + 1].val - stops[i].val);
            const s0 = stops[i], s1 = stops[i + 1];
            return {
                r: Math.round(s0.r + t * (s1.r - s0.r)),
                g: Math.round(s0.g + t * (s1.g - s0.g)),
                b: Math.round(s0.b + t * (s1.b - s0.b)),
                a: Math.round(s0.a + t * (s1.a - s0.a))
            };
        }
    }
    return stops[stops.length - 1];
}

// Inverse Distance Weighting spatial interpolation from station data
function idwInterpolate(lat, lng, valueKey, stations) {
    let totalWeight = 0, totalValue = 0;
    stations.forEach(station => {
        const dlat = lat - station.coords[0];
        const dlng = lng - station.coords[1];
        const dist2 = dlat * dlat + dlng * dlng;
        const weight = dist2 < 0.00001 ? 1e12 : 1.0 / (dist2 * dist2);
        totalWeight += weight;
        totalValue += weight * (station[valueKey] || 0);
    });
    return totalWeight > 0 ? totalValue / totalWeight : 0;
}

// Extract all MultiPolygons or Polygons from GeoJSON
function getPolygonsFromGeoJSON(geojson) {
    const polygons = [];
    if (!geojson) return polygons;
    if (geojson.type === "FeatureCollection") {
        geojson.features.forEach(f => {
            if (f.geometry) {
                if (f.geometry.type === "Polygon") {
                    polygons.push(f.geometry.coordinates);
                } else if (f.geometry.type === "MultiPolygon") {
                    f.geometry.coordinates.forEach(poly => {
                        polygons.push(poly);
                    });
                }
            }
        });
    } else if (geojson.type === "Feature") {
        if (geojson.geometry) {
            if (geojson.geometry.type === "Polygon") {
                polygons.push(geojson.geometry.coordinates);
            } else if (geojson.geometry.type === "MultiPolygon") {
                geojson.geometry.coordinates.forEach(poly => {
                    polygons.push(poly);
                });
            }
        }
    }
    return polygons;
}

// Convert Lat/Lng to pixel coordinate on canvas
function latLngToCanvasXY(lat, lng, W, H) {
    const LAT_MIN = 12.3, LAT_MAX = 19.6;
    const LNG_MIN = 76.5, LNG_MAX = 85.0;
    const x = ((lng - LNG_MIN) / (LNG_MAX - LNG_MIN)) * W;
    const y = ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * H;
    return { x, y };
}

// Render Windy-style gradient canvas using IDW spatial interpolation and clipped to Andhra Pradesh boundary
function renderWeatherCanvas(valueKey, colorStops, stations) {
    const W = 240, H = 180;  // High-fidelity rendering canvas
    
    // Create temporary canvas to draw the raw IDW gradient
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = W;
    tempCanvas.height = H;
    const tempCtx = tempCanvas.getContext('2d');
    const imageData = tempCtx.createImageData(W, H);
    const data = imageData.data;
    
    const LAT_MIN = 12.3, LAT_MAX = 19.6;
    const LNG_MIN = 76.5, LNG_MAX = 85.0;

    for (let py = 0; py < H; py++) {
        for (let px = 0; px < W; px++) {
            const lat = LAT_MAX - (py / (H - 1)) * (LAT_MAX - LAT_MIN);
            const lng = LNG_MIN + (px / (W - 1)) * (LNG_MAX - LNG_MIN);
            const value = idwInterpolate(lat, lng, valueKey, stations);
            const c = interpolateColorStops(colorStops, value);
            const idx = (py * W + px) * 4;
            data[idx]     = c.r;
            data[idx + 1] = c.g;
            data[idx + 2] = c.b;
            data[idx + 3] = c.a;
        }
    }
    tempCtx.putImageData(imageData, 0, 0);

    // Create main canvas where we will clip and draw the gradient
    const mainCanvas = document.createElement('canvas');
    mainCanvas.width = W;
    mainCanvas.height = H;
    const ctx = mainCanvas.getContext('2d');

    // Get polygons for clipping
    let polygons = [];
    if (AppState.apGeoJSON) {
        polygons = getPolygonsFromGeoJSON(AppState.apGeoJSON);
    } else {
        const fallbackOuter = AP_BOUNDARY_COORDS.map(c => [c[1], c[0]]);
        polygons.push([fallbackOuter]);
    }

    // Set up clipping path
    ctx.beginPath();
    polygons.forEach(polygon => {
        const outerRing = polygon[0];
        if (outerRing && outerRing.length > 0) {
            const firstPt = latLngToCanvasXY(outerRing[0][1], outerRing[0][0], W, H);
            ctx.moveTo(firstPt.x, firstPt.y);
            for (let i = 1; i < outerRing.length; i++) {
                const pt = latLngToCanvasXY(outerRing[i][1], outerRing[i][0], W, H);
                ctx.lineTo(pt.x, pt.y);
            }
            ctx.closePath();
        }
    });

    ctx.clip();

    // Apply high-fidelity blending filter and draw raw gradient onto clipped main canvas
    ctx.filter = 'blur(6px)';
    ctx.drawImage(tempCanvas, 0, 0);

    return mainCanvas.toDataURL('image/png');
}

// Redraw spatial layers on Leaflet Map
function updateMapLayers(simulated = false) {
    // Clear existing overlay layers
    Object.keys(AppState.overlayLayers).forEach(key => {
        AppState.map.removeLayer(AppState.overlayLayers[key]);
    });
    AppState.overlayLayers = {};

    const simTemp = simulated ? AppState.simulator.temp : 0.0;
    const simRain = simulated ? (AppState.simulator.rain / 100.0) : 0.0;
    const simHumidity = simulated ? AppState.simulator.humidity : 0.0;
    const timeMult = AppState.activeTimeline === 'past' ? 0.92 : (AppState.activeTimeline === 'future' ? 1.08 : 1.0);

    // ── Base map switching (Satellite ↔ Dark vector) ──────────────────────────
    if (AppState.activeLayers.satellite) {
        if (!AppState.map.hasLayer(AppState.satelliteLayers)) AppState.map.addLayer(AppState.satelliteLayers);
        if (AppState.map.hasLayer(AppState.darkBaseLayer))    AppState.map.removeLayer(AppState.darkBaseLayer);
    } else {
        if (!AppState.map.hasLayer(AppState.darkBaseLayer))   AppState.map.addLayer(AppState.darkBaseLayer);
        if (AppState.map.hasLayer(AppState.satelliteLayers))  AppState.map.removeLayer(AppState.satelliteLayers);
    }

    // ── Build station dataset adjusted for simulation/timeline ────────────────
    const adjustedStations = DISTRICT_STATIONS.map(s => ({
        ...s,
        temp: (s.temp * timeMult) + simTemp,
        rain: Math.max(0, s.rain * timeMult * (1.0 + simRain)),
        humidity: Math.min(100, Math.max(0, s.humidity + simHumidity))
    }));

    // ── Determine active weather layer & color stops ───────────────────────────
    let valueKey = null, colorStops = null;
    if      (AppState.activeLayers.temperature) { valueKey = 'temp';     colorStops = TEMP_COLOR_STOPS;     }
    else if (AppState.activeLayers.rainfall)    { valueKey = 'rain';     colorStops = RAIN_COLOR_STOPS;     }
    else if (AppState.activeLayers.wind)        { valueKey = 'wind';     colorStops = WIND_COLOR_STOPS;     }
    else if (AppState.activeLayers.pressure)    { valueKey = 'pressure'; colorStops = PRESSURE_COLOR_STOPS; }
    else if (AppState.activeLayers.humidity)    { valueKey = 'humidity'; colorStops = HUMIDITY_COLOR_STOPS; }

    // ── Render Windy-style IDW canvas gradient clipped to AP boundary ─────────
    if (valueKey && colorStops) {
        const imageUrl = renderWeatherCanvas(valueKey, colorStops, adjustedStations);
        const apBounds = [[12.3, 76.5], [19.6, 85.0]];  // AP bounding box
        const gradientOverlay = L.imageOverlay(imageUrl, apBounds, {
            opacity: 0.74,
            interactive: false,
            className: 'weather-gradient-overlay'
        });
        gradientOverlay.addTo(AppState.map);
        AppState.overlayLayers['gradient'] = gradientOverlay;
    }

    // ── Small station reference dots (clickable, show tooltip on hover) ────────
    const stationsGroup = L.layerGroup();
    adjustedStations.forEach(station => {
        const dotIcon = L.divIcon({
            className: 'weather-layer-div-icon',
            html: `<div class="station-ref-dot"></div>`,
            iconSize: [8, 8],
            iconAnchor: [4, 4]
        });
        const marker = L.marker(station.coords, { icon: dotIcon, interactive: true });
        marker.bindTooltip(
            `<div style="font-family:Inter,sans-serif;font-size:11px;padding:2px;">
                <p style="font-weight:700;color:#26C6DA;margin:0 0 4px">${station.name}</p>
                <p style="margin:2px 0;color:#e2e8f0">Temp: ${station.temp.toFixed(1)}°C &nbsp; Rain: ${station.rain.toFixed(1)}mm</p>
                <p style="margin:2px 0;color:#e2e8f0">Wind: ${station.wind}kt ${station.dir} &nbsp; Hum: ${station.humidity}%</p>
                <p style="margin:2px 0;color:#e2e8f0">Pressure: ${station.pressure} hPa</p>
            </div>`,
            { className: 'custom-leaflet-tooltip', direction: 'top', offset: [0, -6] }
        );
        marker.on('click', () => selectDistrict(station));
        stationsGroup.addLayer(marker);
    });
    stationsGroup.addTo(AppState.map);
    AppState.overlayLayers['stations'] = stationsGroup;
}

// Setup Forecast and Simulation Charts

function initCharts() {
    fetch('/api/forecast/')
        .then(res => res.json())
        .then(data => {
            const dailyData = data.daily;
            
            // Extract values
            const days = dailyData.map(d => d.day.substring(0, 3).toUpperCase()); // abbreviate SUN, MON etc
            const temps = dailyData.map(d => d.temperature);
            const rains = dailyData.map(d => d.rainfall);

            // Chart Option Setup (ApexCharts for premium glow styling, sized at 155px height)
            const trendOptions = {
                series: [
                    { name: 'Temperature (°C)', data: temps, type: 'line' },
                    { name: 'Rainfall (mm)', data: rains, type: 'area' }
                ],
                chart: {
                    height: 155,
                    type: 'line',
                    background: 'transparent',
                    toolbar: { show: false },
                    sparkline: { enabled: false }
                },
                theme: { mode: 'dark' },
                stroke: {
                    width: [2.5, 1.8],
                    curve: 'smooth'
                },
                colors: ['#FF9800', '#00D2FF'],
                fill: {
                    type: ['solid', 'gradient'],
                    gradient: {
                        shadeIntensity: 0.5,
                        opacityFrom: 0.25,
                        opacityTo: 0.02,
                        stops: [0, 90, 100]
                    }
                },
                markers: { size: 3, colors: ['#FF9800', '#00D2FF'], strokeWidth: 0 },
                xaxis: {
                    categories: days,
                    axisBorder: { show: false },
                    axisTicks: { show: false },
                    labels: { style: { fontSize: '9px', colors: '#94a3b8' } }
                },
                yaxis: [
                    { 
                        title: { text: 'Temp (°C)', style: { color: '#FF9800', fontSize: '9px' } },
                        labels: { style: { fontSize: '9px', colors: '#94a3b8' } }
                    },
                    { 
                        opposite: true, 
                        title: { text: 'Rain (mm)', style: { color: '#00D2FF', fontSize: '9px' } },
                        labels: { style: { fontSize: '9px', colors: '#94a3b8' } }
                    }
                ],
                grid: {
                    borderColor: 'rgba(255, 255, 255, 0.04)',
                    strokeDashArray: 2
                },
                legend: { show: false } // Disable legend to save space, matching DT.png
            };

            if (AppState.charts.trends) {
                AppState.charts.trends.destroy();
            }
            AppState.charts.trends = new ApexCharts(document.querySelector("#chart-trends"), trendOptions);
            AppState.charts.trends.render();

            // Hourly Chart
            const hourlyTime = data.hourly.filter((h, idx) => idx % 3 === 0).map(h => h.time);
            const hourlyRain = data.hourly.filter((h, idx) => idx % 3 === 0).map(h => h.rainfall);

            const hourlyOptions = {
                series: [{ name: 'Rainfall Hourly', data: hourlyRain }],
                chart: {
                    height: 120,
                    type: 'bar',
                    background: 'transparent',
                    toolbar: { show: false }
                },
                colors: ['#00D2FF'],
                plotOptions: {
                    bar: {
                        borderRadius: 2,
                        columnWidth: '35%'
                    }
                },
                grid: { show: false },
                xaxis: {
                    categories: hourlyTime,
                    axisBorder: { show: false },
                    axisTicks: { show: false },
                    labels: { style: { fontSize: '9px', colors: '#94a3b8' } }
                },
                yaxis: { show: false },
                dataLabels: { enabled: false }
            };

            if (AppState.charts.hourly) {
                AppState.charts.hourly.destroy();
            }
            AppState.charts.hourly = new ApexCharts(document.querySelector("#chart-hourly"), hourlyOptions);
            AppState.charts.hourly.render();
        });
}

// Generate & Download Reports
function generateReport(type) {
    fetch(`/api/reports/?type=${type}`)
        .then(res => res.json())
        .then(data => {
            const reportContent = document.getElementById("report-results");
            if (!reportContent) return;
            
            reportContent.classList.remove("hidden");
            gsap.from(reportContent, { opacity: 0, y: 10, duration: 0.3 });

            reportContent.innerHTML = `
                <div class="p-3 bg-navy-900/60 rounded border border-slate-700/50 mt-2">
                    <p class="font-display font-bold text-cyan-400 text-xs">${data.title}</p>
                    <p class="text-[10px] text-slate-500 mb-2">Generated: ${data.generated_at}</p>
                    <p class="text-[11px] text-slate-300 leading-relaxed mb-3">${data.summary}</p>
                    <div class="grid grid-cols-2 gap-2">
                        ${data.metrics.map(m => `
                            <div class="bg-navy-950/40 p-2 rounded border border-slate-800/40">
                                <span class="text-[9px] text-slate-400 block">${m.indicator}</span>
                                <span class="text-xs font-semibold text-slate-200">${m.value}</span>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        });
}

function exportCSV(type) {
    window.location.href = `/api/reports/?type=${type}&format=csv`;
}

// Force refresh feeds helper
function refreshData() {
    fetchWeatherData();
    fetchAlerts();
    initCharts();
    const lastUpdatedEl = document.getElementById("last-updated-time");
    if (lastUpdatedEl) {
        const now = new Date();
        const timeStr = now.toLocaleDateString('en-US', { day: '2-digit', month: 'short', year: 'numeric' }) + ", " + now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true }) + " IST";
        lastUpdatedEl.innerText = timeStr;
    }
}

// CSRF Token Helper
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
