// R.O.O.K - Resilient Observation & Outlook Kernel Core JS

// App state management
const AppState = {
    activePanel: 'dashboard',
    activeTimeline: 'present', // 'past', 'present', 'future'
    activeLayers: {
        satellite: true,
        rainfall: false,
        temperature: false,
        humidity: false,
        wind: true,
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
    mapRight: null,                // simulated split screen map
    isSplitMode: false,
    playback: {
        isPlaying: false,
        speed: 1,                  // playback speed: 1, 2, 5
        intervalId: null
    },
    timeMode: 'live',
    timeYear: 2026,
    timeMonth: 6,
    timeDay: 25,
    timeHour: 15,
    currentDistrictsData: [],
    cycloneActive: false,
    cycloneEye: null,
    isEvolutionMode: false,
    activeScenario: null,          // 'heatwave', 'cyclone', 'flood', 'drought', 'uhi', 'monsoon'
    districtLayer: null,
    districtLayerRight: null,
    apGeoJSON: null,
    overlayLayers: {},
    overlayLayersRight: {},
    charts: {},
    clickedMarker: null,
    clickedMarkerRight: null,
    satelliteLayers: null,
    satelliteLayersRight: null,
    darkBaseLayer: null,
    darkBaseLayerRight: null,
    hazardLayers: [],              // tracking animated hazard lines/polygons
    hazardLayersRight: [],
    backendDistricts: null,
    baselineDistricts: null,
    windCanvasLeft: null,
    windCanvasRight: null,
    windParticlesActive: false,
    cycloneLayers: [],
    cycloneLayersRight: [],
    cycloneWindSpeed: 0
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
    AppState.map = L.map('map-left', {
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
    // ── queryLocation: calls /api/predict/ and updates the sidebar ────────────
    window.queryLocation = async function(lat, lng) {   
        const nameEl     = document.getElementById("clicked-area-name");
        const tempEl     = document.getElementById("clicked-temp");
        const rainEl     = document.getElementById("clicked-rain");
        const windElLoc  = document.getElementById("clicked-wind");
        const pressureEl = document.getElementById("clicked-pressure");
        const badge      = document.getElementById('model-source-badge');

        // PROPERLY DEFINE nearSt SO IT DOESN'T CRASH
        let nearSt = DISTRICT_STATIONS[0];
        let minDist = Infinity;
        DISTRICT_STATIONS.forEach(s => {
            const d = Math.hypot(s.coords[0] - lat, s.coords[1] - lng);
            if (d < minDist) { minDist = d; nearSt = s; }
        });
        if (nameEl) nameEl.innerText = nearSt.name;

        // 🛑 THE FIX: Check if we are on the Home Dashboard
        /*if (AppState.activePanel === 'dashboard') {
            // Update Sidebar text (even if it's hidden, keep the DOM synced)
            if (tempEl)     tempEl.innerText = `${nearSt.temp} °C`;
            if (rainEl)     rainEl.innerText = `${nearSt.rain} mm`;
            if (pressureEl) pressureEl.innerText = `${nearSt.pressure} hPa`;
            if (windElLoc)  windElLoc.innerText = `${nearSt.wind} kt ${nearSt.dir}`;

            // Update the Dashboard KPI Cards with REAL API DATA
            animateValue('kpi-temp', nearSt.temp, ' °C');
            animateValue('kpi-rain', nearSt.rain, ' mm');
            animateValue('kpi-humidity', nearSt.humidity, '%');
            animateValue('kpi-wind', nearSt.wind, ' kt');
            
            const dirEl = document.getElementById('kpi-wind-dir');
            if (dirEl) dirEl.innerText = nearSt.dir;

            return; // 🛑 Kill the function here so it doesn't fetch AI data!
        }*/

        // 🛑 HOME DASHBOARD LOGIC: Fetch actual API data on click
        if (AppState.activePanel === 'dashboard') {
            try {
                // Fetch real live data for the clicked coordinates
                const resp = await fetch(`/api/weather/?lat=${lat}&lng=${lng}`);
                
                // If backend throws a 404/500, jump to the catch block
                if (!resp.ok) throw new Error("API Route failed"); 
                
                const data = await resp.json();

                // Update Sidebar Query Info
                if (tempEl)     tempEl.innerText = `${data.current.temperature} °C`;
                if (rainEl)     rainEl.innerText = `${data.current.rainfall} mm`;
                if (pressureEl) pressureEl.innerText = `${nearSt.pressure} hPa`; // fallback if pressure isn't in API
                if (windElLoc)  windElLoc.innerText = `${data.current.wind_speed} kmph ${data.current.wind_direction}`;

                // Update the Dashboard KPI Cards
                animateValue('kpi-temp', data.current.temperature, ' °C');
                animateValue('kpi-rain', data.current.rainfall, ' mm');
                animateValue('kpi-humidity', data.current.humidity, '%');
                animateValue('kpi-wind', data.current.wind_speed, ' kmph');
                
                const dirEl = document.getElementById('kpi-wind-dir');
                if (dirEl) dirEl.innerText = data.current.wind_direction;

            } catch (err) {
                console.warn("[R.O.O.K] API fetch failed on click. Is Django WeatherAPIView ready?", err);
                // Your fallback is already handled smoothly if you keep the rest of your original try/catch intact!
            }
            return; // 🛑 Kill the function here so it doesn't fetch AI data!
        }

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
            //data.wind_speed = Math.round(data.wind_speed * 3.6);
            // UPDATE UI WITH AI DATA
            if (tempEl)     tempEl.innerText = `${data.tmax_c} °C`;
            if (rainEl)     rainEl.innerText = `${data.rainfall_mm} mm`;
            if (pressureEl) pressureEl.innerText = `${nearSt.pressure} hPa`;
            if (windElLoc)  windElLoc.innerText = `${data.wind_speed} kmph ${nearSt.dir}`;

            // UPDATE KPIs
            animateValue('kpi-temp', data.tmax_c, ' °C');
            animateValue('kpi-rain', data.rainfall_mm, ' mm');
            animateValue('kpi-humidity', nearSt.humidity, '%');
            animateValue('kpi-wind', data.wind_speed, ' kmph');
            
            const dirEl = document.getElementById('kpi-wind-dir');
            if (dirEl) dirEl.innerText = nearSt.dir;

            const currentWindEl = document.getElementById("current-cond-wind");
            if (currentWindEl) {
                currentWindEl.innerHTML = `${data.wind_speed} kmph <span class="text-[9px] text-cyan-400 font-normal">${nearSt.dir}</span>`;
            }

            if (AppState.map) {
                AppState.map.eachLayer((layer) => {
                    // Check if the layer is a marker and has our custom property
                    if (layer.stationName === nearSt.name) {
                        const newTooltipHTML = `
                            <div class="bg-navy-800 border border-slate-700 p-2 rounded text-xs text-slate-200">
                                <p class="font-bold font-display text-cyan-400">${nearSt.name}</p>
                                <p>Temp: ${data.tmax_c}°C</p>
                                <p>Rain: ${data.rainfall_mm} mm</p>
                                <p>Wind: ${data.wind_speed} kmph ${nearSt.dir}</p>
                                <p>Pressure: ${nearSt.pressure} hPa</p>
                            </div>
                        `;
                        // Update the leaflet tooltip
                        layer.setTooltipContent(newTooltipHTML);
                    }
                });
            }

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
            console.warn('[R.O.O.K] Predict API failed:', err);
            // Deterministic fallback
            const tempVal = parseFloat((28.5 + (Math.sin(lat * 12) * Math.cos(lng * 8) * 4.5)).toFixed(1));
            const rainVal = parseFloat(Math.max(0, (8.0 + (Math.cos(lat * 9) * Math.sin(lng * 12) * 12.0))).toFixed(1));
            const windVal = Math.max(2, Math.round(14 + (Math.sin(lat + lng) * 8)));
            const windDirs = ['N','NE','E','SE','S','SW','W','NW'];
            const windDir  = windDirs[Math.abs(Math.round(lat * 100 + lng * 100)) % windDirs.length];
            const pressureVal = Math.round(1006 + (Math.cos(lat * 5 + lng * 5) * 4));

            if (tempEl)     tempEl.innerText = `${tempVal} °C`;
            if (rainEl)     rainEl.innerText = `${rainVal} mm`;
            if (windElLoc)  windElLoc.innerText = `${windVal} kmph ${windDir}`;
            if (pressureEl) pressureEl.innerText = `${pressureVal} hPa`;
            animateValue('kpi-temp', tempVal, ' °C');
            animateValue('kpi-rain', rainVal, ' mm');
            animateValue('kpi-humidity', Math.min(100, Math.round(55 + tempVal * 0.5)), '%');
            animateValue('kpi-wind', windVal, ' kmph');
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
        marker.stationName = station.name; // <--- Add this line!
        /*marker.bindTooltip(`
            <div class="bg-navy-800 border border-slate-700 p-2 rounded text-xs text-slate-200">
                <p class="font-bold font-display text-cyan-400">${station.name}</p>
                <p>Temp: ${station.temp}°C</p>
                <p>Rain: ${station.rain} mm</p>
                <p>Humidity: ${station.humidity}%</p>
            </div>
        `, { direction: 'top', className: 'custom-leaflet-tooltip' });

        marker.on('click', () => {
            selectDistrict(station);
        });*/
        bindDynamicAITooltip(marker, station);

        marker.on('click', () => {
            selectDistrict(station);
        });
    });
}

// Select District Station details
function selectDistrict(station) {
    console.log(`[R.O.O.K] District selected: ${station.name}`);
    AppState.selectedDistrict = station.name;
    document.getElementById("location-indicator").innerText = station.name;
    
    // Update selected location query panel UI to loading state
    const nameEl = document.getElementById("clicked-area-name");
    const coordsEl = document.getElementById("clicked-coords");
    const tempEl = document.getElementById("clicked-temp");
    const rainEl = document.getElementById("clicked-rain");
    const windElLoc = document.getElementById("clicked-wind");
    const pressureEl = document.getElementById("clicked-pressure");
    
    if (nameEl) nameEl.innerText = station.name;
    if (coordsEl) coordsEl.innerText = `${station.coords[0].toFixed(4)}° N, ${station.coords[1].toFixed(4)}° E`;
    if (tempEl) tempEl.innerText = `Fetching...`;
    if (rainEl) rainEl.innerText = `Fetching...`;   
    if (windElLoc) windElLoc.innerText = `Fetching AI...`; // FIXED! No undefined variables here!
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

    // Set KPIs to loading
    const kpiWindEl = document.getElementById("kpi-wind");
    if (kpiWindEl) kpiWindEl.innerText = "Loading...";
    const dirEl = document.getElementById("kpi-wind-dir");
    if (dirEl) dirEl.innerText = station.dir;
    
    // Store location on district select so simulator can use it
    AppState.selectedLat = station.coords[0];
    AppState.selectedLng = station.coords[1];

    // Zoom map closer
    AppState.map.setView(station.coords, 10, { animate: true, duration: 1.5 });
    
    // Query real prediction for this station
    queryLocation(station.coords[0], station.coords[1]);
}
// Reset Map View to default
function resetMapView() {
    AppState.selectedDistrict = "Andhra Pradesh";
    document.getElementById("location-indicator").innerText = "Andhra Pradesh";
    AppState.map.setView(AP_CENTER, AP_ZOOM, { animate: true, duration: 1.5 });
    if (AppState.mapRight && AppState.isSplitMode) {
        AppState.mapRight.setView(AP_CENTER, AP_ZOOM, { animate: true, duration: 1.5 });
    }
    fetchWeatherData(); // restore original KPIs
}

// Leaflet Map Synchronization Utility
function syncMaps(mapA, mapB) {
    let activeMap = null;
    function sync(e) {
        if (activeMap && activeMap !== e.target) return;
        activeMap = e.target;
        const targetMap = (e.target === mapA) ? mapB : mapA;
        targetMap.setView(e.target.getCenter(), e.target.getZoom(), { animate: false });
        activeMap = null;
    }
    mapA.on('zoomend drag move', sync);
    mapB.on('zoomend drag move', sync);
}

// Initialize simulated right side map for split comparison
function initMapRight() {
    if (AppState.mapRight) return;

    AppState.mapRight = L.map('map-right', {
        zoomControl: false,
        attributionControl: false,
        minZoom: 5,
        maxZoom: 18
    }).setView(AppState.map.getCenter(), AppState.map.getZoom());

    // Set base map depending on satellite toggle
    AppState.darkBaseLayerRight = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        maxZoom: 19
    });
    
    const satImagery = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19
    });
    const satStreets = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19, opacity: 0.8
    });
    const satPlaces = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19, opacity: 0.95
    });
    AppState.satelliteLayersRight = L.layerGroup([satImagery, satStreets, satPlaces]);

    if (AppState.activeLayers.satellite) {
        AppState.satelliteLayersRight.addTo(AppState.mapRight);
    } else {
        AppState.darkBaseLayerRight.addTo(AppState.mapRight);
    }

    // Add boundaries
    if (AppState.apGeoJSON) {
        AppState.districtLayerRight = L.geoJSON(AppState.apGeoJSON, {
            style: {
                color: '#ffffff',
                weight: 2.0,
                opacity: 0.8,
                fillColor: 'transparent',
                fillOpacity: 0,
                dashArray: '6, 6'
            }
        }).addTo(AppState.mapRight);
    }

    // Add state label
    const stateLabelIcon = L.divIcon({
        className: 'map-state-label text-center font-display font-bold text-white tracking-widest pointer-events-none select-none',
        html: 'SIMULATED CLIMATE',
        iconSize: [200, 30],
        iconAnchor: [100, 15]
    });
    L.marker([15.80, 79.70], { icon: stateLabelIcon, interactive: false }).addTo(AppState.mapRight);

    // Sync views
    syncMaps(AppState.map, AppState.mapRight);
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

    // Sidebar Collapsible Toggle Listener
    document.getElementById("sidebar-toggle-btn")?.addEventListener("click", () => {
        const container = document.getElementById("app-container");
        if (container) {
            const isCollapsing = !container.classList.contains("sidebar-collapsed");
            container.classList.toggle("sidebar-collapsed");
            
            // GSAP micro-animation for smooth slide effect
            gsap.to("#sidebar", {
                width: isCollapsing ? 72 : 256,
                duration: 0.3,
                ease: "power2.inOut",
                onComplete: () => {
                    if (AppState.map) AppState.map.invalidateSize();
                    if (AppState.mapRight) AppState.mapRight.invalidateSize();
                }
            });
            gsap.to("#top-header", {
                left: isCollapsing ? 88 : 288,
                duration: 0.3,
                ease: "power2.inOut"
            });
        }
    });

    // Split Screen Toggle Listener
    document.getElementById("split-screen-toggle-btn")?.addEventListener("click", (e) => {
        const toggleBtn = e.currentTarget;
        const mapContainer = document.getElementById("map-container");
        AppState.isSplitMode = !AppState.isSplitMode;

        if (AppState.isSplitMode) {
            toggleBtn.classList.add("layer-btn-active");
            mapContainer.classList.add("split-active");
            initMapRight();
            setTimeout(() => {
                if (AppState.map) AppState.map.invalidateSize();
                if (AppState.mapRight) AppState.mapRight.invalidateSize();
            }, 300);
        } else {
            toggleBtn.classList.remove("layer-btn-active");
            mapContainer.classList.remove("split-active");
            setTimeout(() => {
                if (AppState.map) AppState.map.invalidateSize();
            }, 300);
        }
        updateMapLayers();
    });

    // TIME NAVIGATION & WIND PARTICLES INITIALIZATION
    initTimeNavigation();
    initWindParticles();

    // Toggle detailed prognosis matrix collapsible (GSAP powered)
    const togglePrognosisBtn = document.getElementById("toggle-prognosis-btn");
    const prognosisCollapsible = document.getElementById("prognosis-collapsible");
    const prognosisStatusTxt = document.getElementById("prognosis-status-txt");
    const prognosisChevronIcon = document.getElementById("prognosis-chevron-icon");

    if (togglePrognosisBtn && prognosisCollapsible) {
        togglePrognosisBtn.addEventListener("click", () => {
            const isHidden = prognosisCollapsible.classList.contains("hidden");
            if (isHidden) {
                prognosisCollapsible.classList.remove("hidden");
                prognosisCollapsible.style.maxHeight = "0px";
                prognosisCollapsible.style.opacity = "0";
                
                gsap.to(prognosisCollapsible, {
                    maxHeight: "350px",
                    opacity: 1,
                    duration: 0.45,
                    ease: "power2.out",
                    onComplete: () => {
                        prognosisCollapsible.style.maxHeight = "none";
                    }
                });
                if (prognosisStatusTxt) prognosisStatusTxt.innerText = "Collapse";
                if (prognosisChevronIcon) prognosisChevronIcon.style.transform = "rotate(180deg)";
            } else {
                gsap.to(prognosisCollapsible, {
                    maxHeight: "0px",
                    opacity: 0,
                    duration: 0.35,
                    ease: "power2.in",
                    onComplete: () => {
                        prognosisCollapsible.classList.add("hidden");
                    }
                });
                if (prognosisStatusTxt) prognosisStatusTxt.innerText = "Expand";
                if (prognosisChevronIcon) prognosisChevronIcon.style.transform = "rotate(0deg)";
            }
        });
    }

    // Scenario Preset Button Clicks
    document.querySelectorAll(".scenario-btn").forEach(btn => {
        btn.addEventListener("click", (e) => {
            const scenario = e.currentTarget.getAttribute("data-scenario");
            triggerScenarioPreset(scenario);
        });
    });

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
    const playbackPanel = document.getElementById("playback-panel");
    const container = document.getElementById("app-container");
    const showPlayback = ['digital-twin', 'simulator', 'weather'].includes(panelName);

    // Toggle Playback bar visibility
    if (playbackPanel) {
        if (showPlayback) {
            playbackPanel.classList.remove("hidden");
            if (container) container.classList.add("playback-active");
            gsap.fromTo(playbackPanel, { opacity: 0, y: 15 }, { opacity: 1, y: 0, duration: 0.3 });
        } else {
            playbackPanel.classList.add("hidden");
            if (container) container.classList.remove("playback-active");
            pausePlayback(); // stop playing
            AppState.backendDistricts = null;
            AppState.baselineDistricts = null;
            updateMapLayers();
        }
    }

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
    
    // Invalidate map sizes in case borders shifted
    setTimeout(() => {
        if (AppState.map) AppState.map.invalidateSize();
        if (AppState.mapRight) AppState.mapRight.invalidateSize();
    }, 300);
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
            document.getElementById("kpi-wind").innerText = data.current.wind_speed + " kmph";
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

function getLSTColor(t) {
    if (t < 28) return '#fdba74';
    if (t < 35) return '#f97316';
    if (t < 42) return '#ea580c';
    if (t < 48) return '#c2410c';
    return '#7c2d12';
}

function getSSTColor(t) {
    if (t < 27) return '#60a5fa';
    if (t < 29) return '#3b82f6';
    if (t < 31) return '#1d4ed8';
    return '#1e3a8a';
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

// Redraw spatial layers on Leaflet Map (supporting split screen comparison)
function updateMapLayers(simulated = false) {
    // 1. Clear existing layers on left map
    Object.keys(AppState.overlayLayers).forEach(key => {
        AppState.map.removeLayer(AppState.overlayLayers[key]);
    });
    AppState.overlayLayers = {};

    // 2. Clear existing layers on right map
    if (AppState.mapRight) {
        Object.keys(AppState.overlayLayersRight).forEach(key => {
            AppState.mapRight.removeLayer(AppState.overlayLayersRight[key]);
        });
        AppState.overlayLayersRight = {};
    }

    const timeMult = AppState.activeTimeline === 'past' ? 0.92 : (AppState.activeTimeline === 'future' ? 1.08 : 1.0);

    // ── Base map switching (Satellite ↔ Dark vector) for Left Map ──────────────────────────
    if (AppState.activeLayers.satellite) {
        if (!AppState.map.hasLayer(AppState.satelliteLayers)) AppState.map.addLayer(AppState.satelliteLayers);
        if (AppState.map.hasLayer(AppState.darkBaseLayer))    AppState.map.removeLayer(AppState.darkBaseLayer);
    } else {
        if (!AppState.map.hasLayer(AppState.darkBaseLayer))   AppState.map.addLayer(AppState.darkBaseLayer);
        if (AppState.map.hasLayer(AppState.satelliteLayers))  AppState.map.removeLayer(AppState.satelliteLayers);
    }

    // ── Base map switching for Right Map ────────────────────────────────────────────────
    if (AppState.mapRight && AppState.isSplitMode) {
        if (AppState.activeLayers.satellite) {
            if (!AppState.mapRight.hasLayer(AppState.satelliteLayersRight)) AppState.mapRight.addLayer(AppState.satelliteLayersRight);
            if (AppState.mapRight.hasLayer(AppState.darkBaseLayerRight))    AppState.mapRight.removeLayer(AppState.darkBaseLayerRight);
        } else {
            if (!AppState.mapRight.hasLayer(AppState.darkBaseLayerRight))   AppState.mapRight.addLayer(AppState.darkBaseLayerRight);
            if (AppState.mapRight.hasLayer(AppState.satelliteLayersRight))  AppState.mapRight.removeLayer(AppState.satelliteLayersRight);
        }
    }

    // ── Determine active weather layer & color stops ───────────────────────────
    let valueKey = null, colorStops = null;
    if      (AppState.activeLayers.temperature) { valueKey = 'temp';     colorStops = TEMP_COLOR_STOPS;     }
    else if (AppState.activeLayers.rainfall)    { valueKey = 'rain';     colorStops = RAIN_COLOR_STOPS;     }
    else if (AppState.activeLayers.wind)        { valueKey = 'wind';     colorStops = WIND_COLOR_STOPS;     }
    else if (AppState.activeLayers.pressure)    { valueKey = 'pressure'; colorStops = PRESSURE_COLOR_STOPS; }
    else if (AppState.activeLayers.humidity)    { valueKey = 'humidity'; colorStops = HUMIDITY_COLOR_STOPS; }

    let leftStations = [];
    let rightStations = [];

    if (AppState.backendDistricts) {
        const mapBackendToStation = (d) => ({
            name: d.district,
            coords: [d.latitude, d.longitude],
            temp: d.temperature,
            rain: d.rainfall,
            wind: d.wind_speed,
            pressure: d.pressure,
            humidity: d.humidity,
            dir: d.wind_direction,
            lst: d.lst,
            sst: d.sst,
            drought_risk: d.drought_risk,
            flood_risk: d.flood_risk,
            heatwave_risk: d.heatwave_risk,
            cyclone_risk: d.cyclone_risk
        });

        if (AppState.timeMode === 'scenario' && AppState.isSplitMode && AppState.baselineDistricts) {
            leftStations = AppState.baselineDistricts.map(mapBackendToStation);
        } else {
            leftStations = AppState.backendDistricts.map(mapBackendToStation);
        }
        rightStations = AppState.backendDistricts.map(mapBackendToStation);
    } else {
        const baselineSim = (AppState.isSplitMode) ? false : simulated; 
        const baselineTemp = baselineSim ? AppState.simulator.temp : 0.0;
        const baselineRain = baselineSim ? (AppState.simulator.rain / 100.0) : 0.0;
        const baselineHum  = baselineSim ? AppState.simulator.humidity : 0.0;

        leftStations = DISTRICT_STATIONS.map(s => {
            const bTemp = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'temp') : s.temp;
            const bRain = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'rain') : s.rain;
            const bWind = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'wind') : s.wind;
            const bHum  = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'humidity') : s.humidity;

            return {
                ...s,
                temp: (bTemp * timeMult) + baselineTemp,
                rain: Math.max(0, bRain * timeMult * (1.0 + baselineRain)),
                wind: bWind * timeMult,
                pressure: s.pressure * timeMult,
                humidity: Math.min(100, Math.max(0, bHum + baselineHum))
            };
        });

        const rightTemp = simulated ? AppState.simulator.temp : 0.0;
        const rightRain = simulated ? (AppState.simulator.rain / 100.0) : 0.0;
        const rightHum  = simulated ? AppState.simulator.humidity : 0.0;

        rightStations = DISTRICT_STATIONS.map(s => {
            const bTemp = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'temp') : s.temp;
            const bRain = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'rain') : s.rain;
            const bWind = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'wind') : s.wind;
            const bHum  = (AppState.playback.isPlaying || AppState.activePanel === 'digital-twin') 
                ? getMonthlyValues(AppState.playback.currentMonth, s.coords[0], s.coords[1], 'humidity') : s.humidity;

            let scenarioTemp = rightTemp;
            let scenarioRain = rightRain;
            let scenarioHum  = rightHum;
            let scenarioWind = bWind * timeMult;
            let scenarioPress = s.pressure * timeMult;

            if (AppState.activeScenario === 'heatwave') { scenarioTemp = 4.5; scenarioRain = -0.3; scenarioHum = -10; }
            else if (AppState.activeScenario === 'cyclone') { scenarioTemp = 1.0; scenarioRain = 0.35; scenarioHum = 15; scenarioWind += 15; scenarioPress -= 15; }
            else if (AppState.activeScenario === 'flood') { scenarioTemp = -0.5; scenarioRain = 0.4; scenarioHum = 10; }
            else if (AppState.activeScenario === 'drought') { scenarioTemp = 3.0; scenarioRain = -0.5; scenarioHum = -15; }
            else if (AppState.activeScenario === 'uhi') { scenarioTemp = 2.5; scenarioHum = -5; }
            else if (AppState.activeScenario === 'monsoon') { scenarioTemp = 1.5; scenarioRain = -0.25; scenarioHum = -8; }

            return {
                ...s,
                temp: (bTemp * timeMult) + scenarioTemp,
                rain: Math.max(0, bRain * timeMult * (1.0 + scenarioRain)),
                wind: scenarioWind,
                pressure: scenarioPress,
                humidity: Math.min(100, Math.max(0, bHum + scenarioHum))
            };
        });
    }

    // ── Render Weather Gradients clipped to AP boundary ─────────
    if (valueKey && colorStops) {
        const imageUrlLeft = renderWeatherCanvas(valueKey, colorStops, leftStations);
        const apBounds = [[12.3, 76.5], [19.6, 85.0]];
        const leftGradient = L.imageOverlay(imageUrlLeft, apBounds, {
            opacity: 0.74, interactive: false, className: 'weather-gradient-overlay'
        }).addTo(AppState.map);
        AppState.overlayLayers['gradient'] = leftGradient;

        if (AppState.mapRight && AppState.isSplitMode) {
            const imageUrlRight = renderWeatherCanvas(valueKey, colorStops, rightStations);
            const rightGradient = L.imageOverlay(imageUrlRight, apBounds, {
                opacity: 0.74, interactive: false, className: 'weather-gradient-overlay'
            }).addTo(AppState.mapRight);
            AppState.overlayLayersRight['gradient'] = rightGradient;
        }
    }

    // ── Render AWS Station Reference Markers ────────────────────────
    const stationsGroupLeft = L.layerGroup();
    leftStations.forEach(station => {
        const dotIcon = L.divIcon({
            className: 'weather-layer-div-icon',
            html: `<div class="station-ref-dot"></div>`,
            iconSize: [8, 8], iconAnchor: [4, 4]
        });
        const marker = L.marker(station.coords, { icon: dotIcon, interactive: true });
        marker.stationName = station.name;
        bindDynamicAITooltip(marker, station);
        marker.on('click', () => selectDistrict(station));
        stationsGroupLeft.addLayer(marker);
    });
    stationsGroupLeft.addTo(AppState.map);
    AppState.overlayLayers['stations'] = stationsGroupLeft;

    if (AppState.mapRight && AppState.isSplitMode) {
        const stationsGroupRight = L.layerGroup();
        rightStations.forEach(station => {
            const dotIcon = L.divIcon({
                className: 'weather-layer-div-icon',
                html: `<div class="station-ref-dot"></div>`,
                iconSize: [8, 8], iconAnchor: [4, 4]
            });
            const marker = L.marker(station.coords, { icon: dotIcon, interactive: true });
            marker.stationName = station.name;
            bindDynamicAITooltip(marker, station);
            marker.on('click', () => selectDistrict(station));
            stationsGroupRight.addLayer(marker);
        });
        stationsGroupRight.addTo(AppState.mapRight);
        AppState.overlayLayersRight['stations'] = stationsGroupRight;
    }
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

// --- NEW DYNAMIC HOVER TOOLTIP FUNCTION ---
function bindDynamicAITooltip(marker, station) {
    // 1. Initial scanning tooltip
    marker.bindTooltip(`
        <div style="font-family:Inter,sans-serif;font-size:11px;padding:2px; min-width: 140px;">
            <p style="font-weight:700;color:#26C6DA;margin:0 0 4px">${station.name}</p>
            <p style="margin:2px 0;color:#94a3b8;font-style:italic;">Scanning atmosphere...</p>
        </div>
    `, { className: 'custom-leaflet-tooltip', direction: 'top', offset: [0, -6] });

    // 2. Logic gate on hover
    marker.on('mouseover', async () => {
        const aiPanels = ['weather', 'forecast', 'analytics'];
        const isAIPanel = aiPanels.includes(AppState.activePanel);

        // HOME (Dashboard) or other non-AI panels: Use original raw data!
        /*if (!isAIPanel) {
            marker.setTooltipContent(`
                <div style="font-family:Inter,sans-serif;font-size:11px;padding:2px;">
                    <p style="font-weight:700;color:#26C6DA;margin:0 0 4px">${station.name} <span style="color:#eab308;font-size:9px;">📡 Live API</span></p>
                    <p style="margin:2px 0;color:#e2e8f0">Temp: ${station.temp.toFixed(1)}°C &nbsp; Rain: ${station.rain.toFixed(1)}mm</p>
                    <p style="margin:2px 0;color:#e2e8f0">Wind: ${station.wind} kt ${station.dir} &nbsp; Hum: ${station.humidity}%</p>
                    <p style="margin:2px 0;color:#e2e8f0">Pressure: ${station.pressure} hPa</p>
                </div>
            `);
            return; // Stop execution here, don't fetch AI
        }*/

        // 🏠 HOME DASHBOARD: Fetch Real API Data
        if (!isAIPanel) {
            // Check cache first so we don't spam the server
            if (station.apiLoaded && station.apiData) {
                applyAPITooltip(marker, station.apiData, station);
                return;
            }
            
            try {
                // Pass coords to your Django backend using query params
                const resp = await fetch(`/api/weather/?lat=${station.coords[0]}&lng=${station.coords[1]}`);
                const data = await resp.json();
                
                // Cache it
                station.apiLoaded = true;
                station.apiData = data;
                applyAPITooltip(marker, data, station);
            } catch (err) {
                console.warn("[R.O.O.K] Live API fetch failed, falling back to static:", err);
                // Fallback to static array data if your backend crashes
                applyAPITooltip(marker, { current: { temperature: station.temp, rainfall: station.rain, wind_speed: station.wind, wind_direction: station.dir, humidity: station.humidity } }, station);
            }
            return;
        }

        // AI PANELS: Check cache
        if (station.aiLoaded && station.aiData) {
            applyAITooltip(marker, station.aiData, station);
            return;
        }

        // Fetch new AI Data
        try {
            const resp = await fetch('/api/predict/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken') },
                body: JSON.stringify({ lat: station.coords[0], lng: station.coords[1], date: new Date().toISOString() })
            });
            const data = await resp.json();
            
            // CACHE IT, BUT DO NOT MUTATE BASE STATION DATA 🚫
            station.aiLoaded = true; 
            station.aiData = data; 

            // Render it
            applyAITooltip(marker, data, station);
        } catch (err) {
            console.error("AI Hover fetch failed", err);
        }
    });
}

// Helper for LIVE API Tooltip
function applyAPITooltip(marker, data, station) {
    marker.setTooltipContent(`
        <div style="font-family:Inter,sans-serif;font-size:11px;padding:2px;">
            <p style="font-weight:700;color:#26C6DA;margin:0 0 4px">${station.name} <span style="color:#eab308;font-size:9px;">📡 Live API</span></p>
            <p style="margin:2px 0;color:#e2e8f0">Temp: ${data.current.temperature}°C &nbsp; Rain: ${data.current.rainfall}mm</p>
            <p style="margin:2px 0;color:#e2e8f0">Wind: ${data.current.wind_speed} kmph ${data.current.wind_direction} &nbsp; Hum: ${data.current.humidity}%</p>
            <p style="margin:2px 0;color:#e2e8f0">Pressure: ${station.pressure} hPa</p>
        </div>
    `);
}

// Helper to keep code clean fr
function applyAITooltip(marker, data, station) {
    marker.setTooltipContent(`
        <div style="font-family:Inter,sans-serif;font-size:11px;padding:2px;">
            <p style="font-weight:700;color:#26C6DA;margin:0 0 4px">${station.name} <span style="color:#10b981;font-size:9px;">⚡ AI Sync</span></p>
            <p style="margin:2px 0;color:#e2e8f0">Temp: ${data.tmax_c.toFixed(1)}°C &nbsp; Rain: ${data.rainfall_mm.toFixed(1)}mm</p>
            <p style="margin:2px 0;color:#e2e8f0">Wind: ${data.wind_speed} kmph ${station.dir} &nbsp; Hum: ${station.humidity}%</p>
            <p style="margin:2px 0;color:#e2e8f0">Pressure: ${station.pressure} hPa</p>
        </div>
    `);
}

// ─── Playback & Time Navigation Engine ──────────────────────────────────────────

function populateCalendarDays() {
    const yearSelect = document.getElementById("cal-year");
    const monthSelect = document.getElementById("cal-month");
    const daySelect = document.getElementById("cal-day");
    if (!yearSelect || !monthSelect || !daySelect) return;
    
    const year = parseInt(yearSelect.value);
    const month = parseInt(monthSelect.value);
    
    const daysInMonth = new Date(year, month, 0).getDate();
    const currentSelected = parseInt(daySelect.value) || AppState.timeDay || 1;
    
    daySelect.innerHTML = "";
    for (let d = 1; d <= daysInMonth; d++) {
        const opt = document.createElement("option");
        opt.value = d;
        opt.innerText = d;
        if (d === currentSelected || (d === daysInMonth && currentSelected > daysInMonth)) {
            opt.selected = true;
        }
        daySelect.appendChild(opt);
    }
    
    AppState.timeYear = year;
    AppState.timeMonth = month;
    AppState.timeDay = parseInt(daySelect.value);
}

function initTimeNavigation() {
    populateCalendarDays();
    
    document.getElementById("cal-year")?.addEventListener("change", () => {
        populateCalendarDays();
        updateTimeNavigationState();
    });
    
    document.getElementById("cal-month")?.addEventListener("change", () => {
        populateCalendarDays();
        updateTimeNavigationState();
    });
    
    document.getElementById("cal-day")?.addEventListener("change", (e) => {
        AppState.timeDay = parseInt(e.target.value);
        updateTimeNavigationState();
    });
    
    const modeButtons = ["history", "live", "forecast", "scenario"];
    modeButtons.forEach(m => {
        const btn = document.getElementById(`mode-${m}`);
        if (btn) {
            btn.addEventListener("click", () => {
                modeButtons.forEach(x => {
                    const b = document.getElementById(`mode-${x}`);
                    if (b) {
                        b.classList.remove("bg-cyan-500", "text-navy-900");
                        b.classList.add("text-slate-400");
                    }
                });
                btn.classList.add("bg-cyan-500", "text-navy-900");
                btn.classList.remove("text-slate-400");
                AppState.timeMode = m;
                
                if (m !== 'scenario') {
                    AppState.activeScenario = null;
                    document.querySelectorAll(".scenario-btn").forEach(sb => {
                        sb.classList.remove("bg-cyan-500/20", "border-cyan-500/50");
                        sb.style.boxShadow = "";
                    });
                }
                
                updateTimeNavigationState();
            });
        }
    });
    
    document.getElementById("pb-play-btn")?.addEventListener("click", () => {
        startPlayback();
    });
    
    document.getElementById("pb-pause-btn")?.addEventListener("click", () => {
        pausePlayback();
    });
    
    document.getElementById("pb-stop-btn")?.addEventListener("click", () => {
        stopPlayback();
    });
    
    document.getElementById("pb-prev-btn")?.addEventListener("click", () => {
        pausePlayback();
        AppState.timeHour--;
        if (AppState.timeHour < 0) {
            AppState.timeHour = 23;
            AppState.timeDay--;
            if (AppState.timeDay < 1) {
                AppState.timeMonth--;
                if (AppState.timeMonth < 1) {
                    AppState.timeMonth = 12;
                    AppState.timeYear--;
                }
                const maxDays = new Date(AppState.timeYear, AppState.timeMonth, 0).getDate();
                AppState.timeDay = maxDays;
            }
            document.getElementById("cal-year").value = AppState.timeYear;
            document.getElementById("cal-month").value = AppState.timeMonth;
            populateCalendarDays();
            document.getElementById("cal-day").value = AppState.timeDay;
        }
        updateTimeNavigationState();
    });
    
    document.getElementById("pb-next-btn")?.addEventListener("click", () => {
        pausePlayback();
        AppState.timeHour++;
        if (AppState.timeHour > 23) {
            AppState.timeHour = 0;
            AppState.timeDay++;
            const maxDays = new Date(AppState.timeYear, AppState.timeMonth, 0).getDate();
            if (AppState.timeDay > maxDays) {
                AppState.timeDay = 1;
                AppState.timeMonth++;
                if (AppState.timeMonth > 12) {
                    AppState.timeMonth = 1;
                    AppState.timeYear++;
                }
            }
            document.getElementById("cal-year").value = AppState.timeYear;
            document.getElementById("cal-month").value = AppState.timeMonth;
            populateCalendarDays();
            document.getElementById("cal-day").value = AppState.timeDay;
        }
        updateTimeNavigationState();
    });
    
    document.querySelectorAll(".timeline-hour-dot").forEach(dot => {
        dot.addEventListener("click", () => {
            pausePlayback();
            AppState.timeHour = parseInt(dot.getAttribute("data-hour"));
            updateTimeNavigationState();
        });
    });

    document.querySelectorAll(".pb-speed-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".pb-speed-btn").forEach(b => {
                b.classList.remove("bg-cyan-500", "text-navy-900", "active");
                b.classList.add("text-slate-400");
            });
            btn.classList.add("bg-cyan-500", "text-navy-900", "active");
            btn.classList.remove("text-slate-400");
            AppState.playback.speed = parseInt(btn.getAttribute("data-speed"));
        });
    });
}

function updateTimeNavigationState() {
    const yr = AppState.timeYear;
    const mo = String(AppState.timeMonth).padStart(2, '0');
    const dy = String(AppState.timeDay).padStart(2, '0');
    const hr = String(AppState.timeHour).padStart(2, '0');
    const dtStr = `${yr}-${mo}-${dy}T${hr}:00`;
    
    const activeDot = document.querySelector(`.timeline-hour-dot[data-hour="${AppState.timeHour}"]`);
    const caret = document.getElementById("timeline-caret");
    if (activeDot && caret) {
        const rowContainer = activeDot.closest('.relative');
        if (rowContainer) {
            rowContainer.appendChild(caret);
            caret.style.left = `${activeDot.offsetLeft + activeDot.offsetWidth / 2}px`;
            caret.style.bottom = `-10px`;
            caret.style.opacity = "1";
        }
    }
    
    document.querySelectorAll(".timeline-hour-dot").forEach(dot => {
        const dotHr = parseInt(dot.getAttribute("data-hour"));
        dot.classList.remove("active", "passed");
        if (dotHr === AppState.timeHour) {
            dot.classList.add("active");
        } else if (dotHr < AppState.timeHour) {
            dot.classList.add("passed");
        }
    });
    
    const progressRow1 = document.getElementById("timeline-progress-row1");
    const progressRow2 = document.getElementById("timeline-progress-row2");
    
    if (AppState.timeHour <= 11) {
        const pct = (AppState.timeHour / 11) * 100;
        if (progressRow1) progressRow1.style.width = `${pct}%`;
        if (progressRow2) progressRow2.style.width = `0%`;
    } else {
        if (progressRow1) progressRow1.style.width = `100%`;
        const pct = ((AppState.timeHour - 12) / 11) * 100;
        if (progressRow2) progressRow2.style.width = `${pct}%`;
    }
    
    return fetchTimeNavigationData(dtStr, AppState.timeMode);
}

async function fetchTimeNavigationData(dtStr, modeVal) {
    let url = `/api/playback?datetime=${encodeURIComponent(dtStr)}&mode=${encodeURIComponent(modeVal)}&lat=${AppState.selectedLat}&lng=${AppState.selectedLng}`;
    if (modeVal === 'scenario') {
        url += `&temp_delta=${AppState.simulator.temp}&rain_delta=${AppState.simulator.rain}&humidity_change=${AppState.simulator.humidity}&scenario_category=${AppState.activeScenario || 'Custom'}`;
    }
    
    if (modeVal === 'scenario' && AppState.isSplitMode) {
        let baselineUrl = `/api/playback?datetime=${encodeURIComponent(dtStr)}&mode=scenario&temp_delta=0&rain_delta=0&humidity_change=0&scenario_category=Custom`;
        try {
            const res = await fetch(baselineUrl);
            const baselineData = await res.json();
            AppState.baselineDistricts = baselineData.districts;
        } catch (e) {
            console.error("Failed to fetch baseline for split mode", e);
        }
    } else {
        AppState.baselineDistricts = null;
    }
    
    try {
        const resp = await fetch(url);
        const data = await resp.json();
        
        AppState.backendDistricts = data.districts;
        
        const parsedDate = new Date(data.date);
        AppState.timeYear = parsedDate.getFullYear();
        AppState.timeMonth = parsedDate.getMonth() + 1;
        AppState.timeDay = parsedDate.getDate();
        AppState.timeHour = data.hour;
        
        document.getElementById("cal-year").value = AppState.timeYear;
        document.getElementById("cal-month").value = AppState.timeMonth;
        populateCalendarDays();
        document.getElementById("cal-day").value = AppState.timeDay;
        
        const monthsAbbrev = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const dtDisp = document.getElementById("active-datetime-display");
        if (dtDisp) {
            const displayHour = AppState.timeHour === 0 ? "12:00 AM" : 
                                AppState.timeHour === 12 ? "12:00 PM" : 
                                AppState.timeHour > 12 ? `${AppState.timeHour - 12}:00 PM` : `${AppState.timeHour}:00 AM`;
            dtDisp.innerText = `${AppState.timeDay} ${monthsAbbrev[AppState.timeMonth - 1]} ${AppState.timeYear}, ${displayHour} IST`;
        }
        
        animateValue('kpi-temp', data.metrics.temperature, ' °C');
        animateValue('kpi-rain', data.metrics.rainfall, ' mm');
        animateValue('kpi-humidity', Math.round(data.metrics.humidity), '%');
        animateValue('kpi-wind', data.metrics.wind_speed, ' kmph');
        
        const currentDistrictData = data.districts.find(d => d.district.toLowerCase() === AppState.selectedDistrict.toLowerCase()) || data.districts[0];
        if (currentDistrictData) {
            const clickedTempEl = document.getElementById("clicked-temp");
            if (clickedTempEl) clickedTempEl.innerText = `${currentDistrictData.temperature.toFixed(1)} °C`;
            const clickedRainEl = document.getElementById("clicked-rain");
            if (clickedRainEl) clickedRainEl.innerText = `${currentDistrictData.rainfall.toFixed(1)} mm`;
            const clickedWindEl = document.getElementById("clicked-wind");
            if (clickedWindEl) clickedWindEl.innerText = `${currentDistrictData.wind_speed.toFixed(1)} kmph ${currentDistrictData.wind_direction}`;
            const clickedPressureEl = document.getElementById("clicked-pressure");
            if (clickedPressureEl) clickedPressureEl.innerText = `${currentDistrictData.pressure.toFixed(1)} hPa`;
            
            const windDirEl = document.getElementById("kpi-wind-dir");
            if (windDirEl) windDirEl.innerText = currentDistrictData.wind_direction;
            
            const navigationIcon = document.querySelector("#dashboard-widgets .glow-wind i[data-lucide='navigation']");
            if (navigationIcon) {
                const angle = getWindAngle(currentDistrictData.wind_direction);
                navigationIcon.style.transform = `rotate(${angle}deg)`;
            }
            
            updateRiskBadge('risk-drought', currentDistrictData.drought_risk);
            updateRiskBadge('risk-flood', currentDistrictData.flood_risk);
            updateRiskBadge('risk-heatwave', currentDistrictData.heatwave_risk);
            
            const agriEl = document.getElementById('risk-agri');
            if (agriEl) {
                const agriMap = {'Low': 'Optimal Yield Output', 'Medium': 'Moderate Stress', 'High': 'Critical Yield Loss', 'Critical': 'Severe Crop Wilting / Stress'};
                agriEl.innerText = agriMap[currentDistrictData.agriculture_risk] || 'Optimal Yield Output';
            }
            
            const waterEl = document.getElementById('risk-water');
            if (waterEl) waterEl.innerText = currentDistrictData.water_stress.toFixed(1) + '%';
            
            const progressEl = document.getElementById('stress-progress');
            if (progressEl) progressEl.style.width = currentDistrictData.water_stress + '%';
        }
        
        const alertsContainer = document.getElementById("alerts-container");
        if (alertsContainer && data.alerts) {
            alertsContainer.innerHTML = "";
            data.alerts.forEach(alert => {
                let badgeClass = "badge-low";
                if (alert.severity === "Critical") badgeClass = "badge-critical";
                else if (alert.severity === "High") badgeClass = "badge-high";
                else if (alert.severity === "Medium") badgeClass = "badge-medium";

                alertsContainer.innerHTML += `
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
        }
        
        updateMapLayers(modeVal === 'scenario');
        drawCycloneOverlay(data.cyclone);
        updatePrognosisMatrix(data.charts);
        updatePrognosisCharts(data.charts);
        
    } catch (e) {
        console.error("Time navigation fetch failed:", e);
    }
}

function updatePrognosisMatrix(charts) {
    if (!charts) return;
    
    // 1. Air Temperature Row (Continuous Heat Strip)
    let tempRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    tempRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5 min-w-[120px]"><i data-lucide="thermometer" class="w-3.5 h-3.5 text-orange-400"></i> Temp (°C)</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.temperature[h];
        const color = getTempColor(val);
        const textColor = (val < 30) ? '#081420' : '#ffffff';
        tempRow += `<td class="p-1 text-center font-extrabold text-[9.5px]" style="background-color: ${color}; color: ${textColor}; border-right: 1px solid rgba(8, 20, 32, 0.15)">${val.toFixed(1)}°</td>`;
    }
    tempRow += `</tr>`;
    
    // 2. Land Surface Temperature (LST) Row (Copper/Thermal Strip)
    let lstRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    lstRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="sun" class="w-3.5 h-3.5 text-amber-500"></i> LST (°C)</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.lst[h];
        const color = getLSTColor(val);
        const textColor = (val < 35) ? '#081420' : '#ffffff';
        lstRow += `<td class="p-1 text-center font-extrabold text-[9.5px]" style="background-color: ${color}; color: ${textColor}; border-right: 1px solid rgba(8, 20, 32, 0.15)">${val.toFixed(1)}°</td>`;
    }
    lstRow += `</tr>`;

    // 3. Sea Surface Temperature (SST) Row (Ocean Blue/Purple Thermal Strip for Coastal)
    let sstRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    sstRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="waves" class="w-3.5 h-3.5 text-cyan-400"></i> SST (°C)</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.sst[h];
        if (val > 0) {
            const color = getSSTColor(val);
            const textColor = '#ffffff';
            sstRow += `<td class="p-1 text-center font-extrabold text-[9.5px]" style="background-color: ${color}; color: ${textColor}; border-right: 1px solid rgba(8, 20, 32, 0.15)">${val.toFixed(1)}°</td>`;
        } else {
            sstRow += `<td class="p-1 text-center text-slate-500 font-normal" style="color: #475569; border-right: 1px solid rgba(255,255,255,0.02)">-</td>`;
        }
    }
    sstRow += `</tr>`;
    
    // 4. Rainfall Row (Vertical bar scan + numbers)
    let rainRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    rainRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="cloud-rain" class="w-3.5 h-3.5 text-blue-400"></i> Rain (mm)</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.rainfall[h];
        if (val > 0) {
            const intensity = Math.min(100, (val / 15.0) * 100);
            rainRow += `<td class="p-1 text-center font-bold text-sky-400" style="background-color: rgba(56, 189, 248, 0.05); border-right: 1px solid rgba(255,255,255,0.02)">
                <div class="flex flex-col items-center justify-end h-8 gap-0.5">
                    <span class="text-[9px]">${val.toFixed(1)}</span>
                    <div class="w-2.5 bg-sky-500/80 rounded-t-sm" style="height: ${Math.max(3, intensity * 0.2)}px;"></div>
                </div>
            </td>`;
        } else {
            rainRow += `<td class="p-1 text-center text-slate-600 font-normal" style="border-right: 1px solid rgba(255,255,255,0.02)">-</td>`;
        }
    }
    rainRow += `</tr>`;
    
    // 5. Wind Velocity Row (Rotated arrows + speed + speed background)
    let windRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    windRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="wind" class="w-3.5 h-3.5 text-cyan-400"></i> Wind (kt)</td>`;
    for (let h = 0; h < 24; h++) {
        const speed = charts.wind_speed[h];
        const dir = charts.wind_direction[h];
        const angle = getWindAngle(dir);
        const color = getWindColor(speed);
        
        windRow += `<td class="p-1 text-center font-bold" style="background-color: ${color}1e; border-right: 1px solid rgba(255,255,255,0.02)">
            <div class="flex flex-col items-center justify-center gap-1">
                <svg viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="2.5" class="w-3.5 h-3.5 transition-transform" style="transform: rotate(${angle}deg);">
                    <line x1="12" y1="5" x2="12" y2="19"></line>
                    <polyline points="19 12 12 19 5 12"></polyline>
                </svg>
                <span style="color: ${color}; font-size: 9px;">${Math.round(speed)}</span>
            </div>
        </td>`;
    }
    windRow += `</tr>`;
    
    // 6. Humidity Row (Color-coded text + background tint)
    let humidityRow = `<tr class="border-b border-slate-900/35 hover:bg-slate-800/10">`;
    humidityRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="droplet" class="w-3.5 h-3.5 text-teal-400"></i> Humidity</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.humidity[h];
        const color = getHumidityColor(val);
        humidityRow += `<td class="p-1 text-center font-bold" style="background-color: ${color}14; color: ${color}; border-right: 1px solid rgba(255,255,255,0.02)">${Math.round(val)}%</td>`;
    }
    humidityRow += `</tr>`;
    
    // 7. Atmospheric Pressure Row (Color-coded text + background tint)
    let pressureRow = `<tr class="hover:bg-slate-800/10">`;
    pressureRow += `<td class="py-2.5 px-2 text-slate-400 font-semibold border-r border-slate-900/30 flex items-center gap-1.5"><i data-lucide="gauge" class="w-3.5 h-3.5 text-indigo-400"></i> Pressure</td>`;
    for (let h = 0; h < 24; h++) {
        const val = charts.pressure[h];
        const color = getPressureColor(val);
        pressureRow += `<td class="p-1 text-center font-bold" style="background-color: ${color}14; color: ${color}; border-right: 1px solid rgba(255,255,255,0.02)">${Math.round(val)}</td>`;
    }
    pressureRow += `</tr>`;
    
    const container = document.getElementById("prognosis-rows-container");
    if (container) {
        container.innerHTML = tempRow + lstRow + sstRow + rainRow + windRow + humidityRow + pressureRow;
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    }
}

function updatePrognosisCharts(charts) {
    if (!charts) return;
    
    if (AppState.charts.hourly) {
        AppState.charts.hourly.updateSeries([{
            name: 'Rainfall Hourly',
            data: charts.rainfall
        }]);
        AppState.charts.hourly.updateOptions({
            xaxis: {
                categories: charts.time
            }
        });
    }
    
    if (AppState.charts.trends) {
        AppState.charts.trends.updateSeries([
            { name: 'Temperature (°C)', data: charts.temperature, type: 'line' },
            { name: 'Rainfall (mm)', data: charts.rainfall, type: 'area' }
        ]);
        AppState.charts.trends.updateOptions({
            xaxis: {
                categories: charts.time
            }
        });
    }
}

function initWindParticles() {
    const leftMapContainer = document.getElementById("map-left");
    if (leftMapContainer && !document.getElementById("wind-canvas-left")) {
        const canvas = document.createElement("canvas");
        canvas.id = "wind-canvas-left";
        canvas.className = "absolute inset-0 w-full h-full pointer-events-none wind-overlay-canvas";
        canvas.style.zIndex = "400";
        leftMapContainer.appendChild(canvas);
        AppState.windCanvasLeft = canvas;
    }
    
    const rightMapContainer = document.getElementById("map-right");
    if (rightMapContainer && !document.getElementById("wind-canvas-right")) {
        const canvas = document.createElement("canvas");
        canvas.id = "wind-canvas-right";
        canvas.className = "absolute inset-0 w-full h-full pointer-events-none wind-overlay-canvas";
        canvas.style.zIndex = "400";
        rightMapContainer.appendChild(canvas);
        AppState.windCanvasRight = canvas;
    }
    
    AppState.windParticlesActive = true;
    animateWindParticles();
}

let cycloneRadarOverlayLeft = null;
let cycloneRadarOverlayRight = null;
let cycloneRadarRotation = 0;
let cycloneInterval = null;

function clearCycloneRadar() {
    if (cycloneRadarOverlayLeft && AppState.map) {
        AppState.map.removeLayer(cycloneRadarOverlayLeft);
        cycloneRadarOverlayLeft = null;
    }
    if (cycloneRadarOverlayRight && AppState.mapRight) {
        AppState.mapRight.removeLayer(cycloneRadarOverlayRight);
        cycloneRadarOverlayRight = null;
    }
}

function updateCycloneRadarOverlay(map, eye, isLeft) {
    if (!eye) return;
    
    const size = 128; // 128x128 canvas is extremely fast to calculate and renders smoothly when scaled
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    const imgData = ctx.createImageData(size, size);
    const data = imgData.data;
    
    const cx = size / 2;
    const cy = size / 2;
    const alpha = cycloneRadarRotation;
    
    for (let y = 0; y < size; y++) {
        for (let x = 0; x < size; x++) {
            const dx = x - cx;
            const dy = y - cy;
            const r = Math.hypot(dx, dy);
            
            if (r > cx - 2) continue;
            
            const phi = Math.atan2(dy, dx);
            const eyeRadius = 9; // eye radius on 128x128 canvas
            let intensity = 0;
            
            if (r >= eyeRadius) {
                // Spiral arms equation (counter-clockwise spin)
                const spiralVal = Math.sin(r / 6 - 3 * phi - alpha);
                
                // Eyewall peak intensity
                const eyewall = Math.exp(-Math.pow(r - 14, 2) / 25) * 0.95;
                
                // Spiral arms intensity
                const arms = Math.exp(-Math.pow(r - 40, 2) / 400) * Math.max(0, spiralVal) * 0.75;
                
                intensity = Math.max(eyewall, arms);
            }
            
            // Fade out towards the outer edges
            intensity *= Math.exp(-Math.pow(r / (size * 0.45), 4));
            
            const pixelIdx = (y * size + x) * 4;
            if (intensity > 0.15) {
                let r_col = 0, g_col = 0, b_col = 0, a_col = 0;
                
                if (intensity > 0.8) {
                    // Eyewall core - intense red/magenta
                    r_col = 255; g_col = 0; b_col = 128; a_col = Math.floor(intensity * 180);
                } else if (intensity > 0.6) {
                    // Inner bands - red
                    r_col = 239; g_col = 68; b_col = 68; a_col = Math.floor(intensity * 170);
                } else if (intensity > 0.45) {
                    // Mid bands - orange/yellow
                    r_col = 245; g_col = 158; b_col = 11; a_col = Math.floor(intensity * 150);
                } else if (intensity > 0.3) {
                    // Outer bands - green
                    r_col = 16; g_col = 185; b_col = 129; a_col = Math.floor(intensity * 130);
                } else {
                    // Outermost bands - blue/cyan
                    r_col = 6; g_col = 182; b_col = 212; a_col = Math.floor(intensity * 110);
                }
                
                data[pixelIdx] = r_col;
                data[pixelIdx + 1] = g_col;
                data[pixelIdx + 2] = b_col;
                data[pixelIdx + 3] = a_col;
            } else {
                data[pixelIdx + 3] = 0; // Transparent
            }
        }
    }
    
    ctx.putImageData(imgData, 0, 0);
    const dataUrl = canvas.toDataURL();
    
    const latSpan = 5.0; // 5 degrees latitude wide (approx 550 km)
    const lngSpan = 5.0;
    const overlayBounds = [
        [eye[0] - latSpan/2, eye[1] - lngSpan/2],
        [eye[0] + latSpan/2, eye[1] + lngSpan/2]
    ];
    
    if (isLeft) {
        if (cycloneRadarOverlayLeft) {
            cycloneRadarOverlayLeft.setUrl(dataUrl);
            cycloneRadarOverlayLeft.setBounds(overlayBounds);
        } else {
            cycloneRadarOverlayLeft = L.imageOverlay(dataUrl, overlayBounds, {
                opacity: 0.75,
                interactive: false,
                zIndex: 350
            }).addTo(map);
        }
    } else {
        if (cycloneRadarOverlayRight) {
            cycloneRadarOverlayRight.setUrl(dataUrl);
            cycloneRadarOverlayRight.setBounds(overlayBounds);
        } else {
            cycloneRadarOverlayRight = L.imageOverlay(dataUrl, overlayBounds, {
                opacity: 0.75,
                interactive: false,
                zIndex: 350
            }).addTo(map);
        }
    }
}

function animateWindParticles() {
    if (!AppState.windParticlesActive) return;
    
    requestAnimationFrame(animateWindParticles);
    
    const stationsSource = AppState.backendDistricts || DISTRICT_STATIONS;
    
    // Update smooth eye movement before drawing
    if (AppState.cycloneActive && AppState.cycloneEye) {
        // Track previous eye position to calculate movement delta for particles
        AppState.prevCycloneEye = [...AppState.cycloneEye];

        if (AppState.cycloneTargetEye) {
            const currentEye = AppState.cycloneEye;
            const targetEye = AppState.cycloneTargetEye;
            
            const dLat = targetEye[0] - currentEye[0];
            const dLng = targetEye[1] - currentEye[1];
            const dist = Math.hypot(dLat, dLng);
            
            if (dist > 0.001) {
                // Move eye 1.5% of the way to the target on each frame
                AppState.cycloneEye = [
                    currentEye[0] + dLat * 0.015,
                    currentEye[1] + dLng * 0.015
                ];
            } else {
                AppState.cycloneEye = targetEye;
            }
        }
    } else {
        AppState.prevCycloneEye = null;
    }

    if (AppState.windCanvasLeft && AppState.map) {
        drawWindCanvas(AppState.windCanvasLeft, AppState.map, stationsSource);
    }
    
    if (AppState.windCanvasRight && AppState.mapRight && AppState.isSplitMode) {
        drawWindCanvas(AppState.windCanvasRight, AppState.mapRight, stationsSource);
    }

    // Clean up radar overlays since they are disabled
    clearCycloneRadar();
}

function drawWindCanvas(canvas, map, stations) {
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    const mapContainer = map.getContainer();
    const rect = mapContainer.getBoundingClientRect();
    if (canvas.width !== rect.width || canvas.height !== rect.height) {
        canvas.width = rect.width;
        canvas.height = rect.height;
        canvas.particles = [];
    }
    
    ctx.globalCompositeOperation = 'destination-out';
    ctx.fillStyle = 'rgba(0, 0, 0, 0.12)'; 
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.globalCompositeOperation = 'source-over';
    
    if (!AppState.activeLayers.wind && !AppState.cycloneActive) return;
    
    const districtsData = stations.map(d => {
        const speed = d.wind_speed || d.wind || 0;
        const dir = d.wind_direction || d.dir || 'SW';
        const angle = getWindAngle(dir);
        const angleRad = (angle * Math.PI) / 180;
        return {
            lat: d.coords ? d.coords[0] : d.latitude,
            lng: d.coords ? d.coords[1] : d.longitude,
            u: -speed * Math.sin(angleRad),
            v: -speed * Math.cos(angleRad)
        };
    });
    
    let particles = canvas.particles || [];
    // Increase density specifically when the cyclone is active
    const targetMaxParticles = AppState.cycloneActive ? 2500 : 1500;
    const bounds = map.getBounds();
    
    if (particles.length < targetMaxParticles) {
        const toAdd = targetMaxParticles - particles.length;
        for (let i = 0; i < toAdd; i++) {
            particles.push(spawnParticle(bounds));
        }
        canvas.particles = particles;
    } else if (particles.length > targetMaxParticles) {
        particles.length = targetMaxParticles;
    }
    
    const dt = 0.0003; 
    
    // Calculate eye movement delta to apply to cyclone particles
    let eyeDeltaLat = 0;
    let eyeDeltaLng = 0;
    if (AppState.cycloneActive && AppState.cycloneEye && AppState.prevCycloneEye) {
        eyeDeltaLat = AppState.cycloneEye[0] - AppState.prevCycloneEye[0];
        eyeDeltaLng = AppState.cycloneEye[1] - AppState.prevCycloneEye[1];
    }
    
    particles.forEach(p => {
        // If inside the cyclone, first shift the particle by the eye's movement delta
        if (AppState.cycloneActive && AppState.cycloneEye) {
            const eyeLat = AppState.cycloneEye[0];
            const eyeLng = AppState.cycloneEye[1];
            
            // Check distance relative to previous eye to apply proper delta tracking
            const refLat = AppState.prevCycloneEye ? AppState.prevCycloneEye[0] : eyeLat;
            const refLng = AppState.prevCycloneEye ? AppState.prevCycloneEye[1] : eyeLng;
            const distToRef = Math.hypot(p.lat - refLat, p.lng - refLng);
            
            if (distToRef < 3.5) {
                p.lat += eyeDeltaLat;
                p.lng += eyeDeltaLng;
            }
        }

        const ptStart = map.latLngToContainerPoint([p.lat, p.lng]);
        
        let u = idwInterpolateVector(p.lat, p.lng, 'u', districtsData);
        let v = idwInterpolateVector(p.lat, p.lng, 'v', districtsData);
        let isInsideCyclone = false;
        let dist = 999;
        
        if (AppState.cycloneActive && AppState.cycloneEye) {
            const eyeLat = AppState.cycloneEye[0];
            const eyeLng = AppState.cycloneEye[1];
            const dlat = p.lat - eyeLat;
            const dlng = p.lng - eyeLng;
            dist = Math.hypot(dlat, dlng);
            const cycloneRadius = 3.5;
            
            if (dist < cycloneRadius) {
                isInsideCyclone = true;
                
                // If particle is too close to the eye, respawn it at the outer edge to prevent bunching in center
                if (dist < 0.35) {
                    const r = 2.5 + Math.random() * 1.0; // spawn in outer rings (2.5 to 3.5 deg)
                    const theta = Math.random() * 2 * Math.PI;
                    p.lat = AppState.cycloneEye[0] + r * Math.sin(theta);
                    p.lng = AppState.cycloneEye[1] + r * Math.cos(theta);
                    p.age = 20 + Math.floor(Math.random() * 30);
                    return;
                }
                
                const speed = AppState.cycloneWindSpeed || 75;
                // Swirl speed curve peaking around eyewall (0.6 deg) and dropping off
                const vt = speed * 1.6 * (dist / (dist + 0.3)) * Math.exp(-dist / 1.8);
                const vr = -vt * 0.18; // Inward velocity for spiraling effect
                
                const cosTheta = dlng / dist;
                const sinTheta = dlat / dist;
                
                const u_spiral = vr * cosTheta - vt * sinTheta;
                const v_spiral = vr * sinTheta + vt * cosTheta;
                
                // Blend with environmental wind at the outer edges of the cyclone
                let blend = 1.0;
                if (dist > 2.5) {
                    blend = Math.max(0.0, 1.0 - (dist - 2.5) / 1.0);
                }
                u = u * (1.0 - blend) + u_spiral * blend;
                v = v * (1.0 - blend) + v_spiral * blend;
            }
        }
        
        p.lng += u * dt;
        p.lat += v * dt;
        p.age--;
        
        const ptEnd = map.latLngToContainerPoint([p.lat, p.lng]);
        const speedVal = Math.hypot(u, v);
        
        let opacityMultiplier = 1.0;
        if (!AppState.activeLayers.wind && AppState.cycloneActive && AppState.cycloneEye) {
            if (dist > 3.5) {
                opacityMultiplier = 0.0;
            } else {
                opacityMultiplier = 1.0 - (dist / 3.5);
            }
        }

        if (p.age > 0 && bounds.contains([p.lat, p.lng]) &&
            ptStart.x >= 0 && ptStart.x <= canvas.width &&
            ptStart.y >= 0 && ptStart.y <= canvas.height) {
            
            const alphaMultiplier = opacityMultiplier;
            if (alphaMultiplier > 0) {
                ctx.beginPath();
                if (isInsideCyclone) {
                    // Custom concentric color palette & size profile (glowing white, cyan, sky blue, indigo. NO red!)
                    let dotColor;
                    let dotRadius;
                    
                    if (dist < 0.8) {
                        // Eyewall core - intense glowing white/cyan
                        dotColor = `rgba(255, 255, 255, ${0.95 * alphaMultiplier})`;
                        dotRadius = 2.0;
                    } else if (dist < 1.6) {
                        // Inner swirling band - cyan
                        dotColor = `rgba(34, 211, 238, ${0.85 * alphaMultiplier})`;
                        dotRadius = 1.6;
                    } else if (dist < 2.5) {
                        // Middle swirling band - sky blue
                        dotColor = `rgba(56, 189, 248, ${0.75 * alphaMultiplier})`;
                        dotRadius = 1.3;
                    } else {
                        // Outer band - deep blue/indigo
                        dotColor = `rgba(99, 102, 241, ${0.6 * alphaMultiplier})`;
                        dotRadius = 1.1;
                    }
                    
                    ctx.arc(ptEnd.x, ptEnd.y, dotRadius, 0, 2 * Math.PI);
                    ctx.fillStyle = dotColor;
                    ctx.fill();
                } else {
                    let baseColor;
                    if (speedVal < 10) {
                        baseColor = [255, 255, 255, 0.45];
                    } else if (speedVal < 18) {
                        baseColor = [34, 211, 238, 0.65]; 
                    } else if (speedVal < 26) {
                        baseColor = [163, 230, 53, 0.75]; 
                    } else {
                        baseColor = [245, 158, 11, 0.8]; // Orange/amber instead of red for environmental high winds
                    }
                    ctx.moveTo(ptStart.x, ptStart.y);
                    ctx.lineTo(ptEnd.x, ptEnd.y);
                    ctx.lineWidth = 1.0;
                    ctx.strokeStyle = `rgba(${baseColor[0]}, ${baseColor[1]}, ${baseColor[2]}, ${baseColor[3] * alphaMultiplier})`;
                    ctx.stroke();
                }
            }
        } else {
            const respawned = spawnParticle(bounds);
            p.lat = respawned.lat;
            p.lng = respawned.lng;
            p.age = respawned.age;
        }
    });
}

function spawnParticle(bounds) {
    if (AppState.cycloneActive && AppState.cycloneEye) {
        // Spawn 65% of new particles inside the cyclone to keep it dense, 35% elsewhere
        if (Math.random() < 0.65 || !AppState.activeLayers.wind) {
            const r = Math.random() * 3.5; 
            const theta = Math.random() * 2 * Math.PI;
            return {
                lat: AppState.cycloneEye[0] + r * Math.sin(theta),
                lng: AppState.cycloneEye[1] + r * Math.cos(theta),
                age: 20 + Math.floor(Math.random() * 40)
            };
        }
    }
    const lat = bounds.getSouth() + Math.random() * (bounds.getNorth() - bounds.getSouth());
    const lng = bounds.getWest() + Math.random() * (bounds.getEast() - bounds.getWest());
    return {
        lat: lat,
        lng: lng,
        age: 25 + Math.floor(Math.random() * 45)
    };
}

function idwInterpolateVector(lat, lng, key, districtsData) {
    let totalWeight = 0, totalValue = 0;
    districtsData.forEach(d => {
        const dlat = lat - d.lat;
        const dlng = lng - d.lng;
        const dist2 = dlat * dlat + dlng * dlng;
        const weight = dist2 < 0.00001 ? 1e12 : 1.0 / (dist2 * dist2);
        totalWeight += weight;
        totalValue += weight * (d[key] || 0);
    });
    return totalWeight > 0 ? totalValue / totalWeight : 0;
}

// ─── Cyclone Overlay Renderers ──────────────────────────────────────────────

function drawCycloneOverlay(cyclone) {
    if (AppState.cycloneLayers) {
        AppState.cycloneLayers.forEach(l => AppState.map.removeLayer(l));
    }
    AppState.cycloneLayers = [];
    
    if (AppState.cycloneLayersRight && AppState.mapRight) {
        AppState.cycloneLayersRight.forEach(l => AppState.mapRight.removeLayer(l));
    }
    AppState.cycloneLayersRight = [];

    if (!cyclone || !cyclone.active) {
        AppState.cycloneActive = false;
        AppState.cycloneEye = null;
        AppState.cycloneTargetEye = null;
        return;
    }

    AppState.cycloneActive = true;
    AppState.cycloneTargetEye = cyclone.eye;
    
    // Initialize eye if it doesn't exist yet, to prevent jumping from [0,0]
    if (!AppState.cycloneEye) {
        AppState.cycloneEye = [...cyclone.eye];
    }
    AppState.cycloneWindSpeed = cyclone.wind_speed_kt;

    addCycloneToMap(AppState.map, cyclone, AppState.cycloneLayers);

    if (AppState.mapRight && AppState.isSplitMode) {
        addCycloneToMap(AppState.mapRight, cyclone, AppState.cycloneLayersRight);
    }
}

function addCycloneToMap(map, cyclone, layerList) {
    // Cyclone wind particles and dynamic overlays are handled directly on the wind canvas and image overlays.
}

// ─── Playback Cycle Control ──────────────────────────────────────────────────

let playbackInterval = null;

function startPlayback() {
    if (AppState.playback.isPlaying) return;
    
    AppState.playback.isPlaying = true;
    document.getElementById("pb-play-btn")?.classList.add("hidden");
    document.getElementById("pb-pause-btn")?.classList.remove("hidden");
    
    runPlaybackCycle();
}

function pausePlayback() {
    AppState.playback.isPlaying = false;
    document.getElementById("pb-play-btn")?.classList.remove("hidden");
    document.getElementById("pb-pause-btn")?.classList.add("hidden");
    if (playbackInterval) {
        clearTimeout(playbackInterval);
        playbackInterval = null;
    }
}

function stopPlayback() {
    pausePlayback();
    AppState.timeHour = 0;
    updateTimeNavigationState();
}

function resetPlayback() {
    stopPlayback();
}

async function runPlaybackCycle() {
    if (!AppState.playback.isPlaying) return;
    
    AppState.timeHour++;
    if (AppState.timeHour > 23) {
        AppState.timeHour = 0;
        AppState.timeDay++;
        const maxDays = new Date(AppState.timeYear, AppState.timeMonth, 0).getDate();
        if (AppState.timeDay > maxDays) {
            AppState.timeDay = 1;
            AppState.timeMonth++;
            if (AppState.timeMonth > 12) {
                AppState.timeMonth = 1;
                AppState.timeYear++;
            }
        }
        document.getElementById("cal-year").value = AppState.timeYear;
        document.getElementById("cal-month").value = AppState.timeMonth;
        populateCalendarDays();
        document.getElementById("cal-day").value = AppState.timeDay;
    }
    
    const startTime = Date.now();
    try {
        await updateTimeNavigationState();
    } catch (e) {
        console.error("Playback fetch failed in cycle:", e);
    }
    
    const elapsed = Date.now() - startTime;
    const speedMs = 1800 / AppState.playback.speed;
    const delay = Math.max(50, speedMs - elapsed);
    
    playbackInterval = setTimeout(runPlaybackCycle, delay);
}

// ─── Visual Hazard Renderings ────────────────────────────────────────────────
function clearHazards() {
    AppState.hazardLayers.forEach(l => AppState.map.removeLayer(l));
    AppState.hazardLayers = [];
    
    if (AppState.mapRight) {
        AppState.hazardLayersRight.forEach(l => AppState.mapRight.removeLayer(l));
        AppState.hazardLayersRight = [];
    }

    if (AppState.districtLayer) {
        AppState.districtLayer.setStyle({ color: '#ffffff', fillColor: 'transparent', fillOpacity: 0 });
    }
    if (AppState.districtLayerRight) {
        AppState.districtLayerRight.setStyle({ color: '#ffffff', fillColor: 'transparent', fillOpacity: 0 });
    }

    // Reset cyclone state
    AppState.cycloneActive = false;
    AppState.cycloneEye = null;
    AppState.cycloneTargetEye = null;
    if (cycloneInterval) {
        clearInterval(cycloneInterval);
        cycloneInterval = null;
    }
    clearCycloneRadar();
}

function updateVisualHazards() {
    clearHazards();

    const scenario = AppState.activeScenario;
    if (!scenario) return;

    if (scenario === 'cyclone') {
        const trackPoints = [
            [14.0, 83.5], 
            [15.2, 82.8],
            [16.4, 82.1],
            [17.68, 83.21] 
        ];

        AppState.cycloneActive = true;
        AppState.cycloneWindSpeed = 75;
        
        // Initialize eye coordinates. They will be driven dynamically by the timeline.
        if (!AppState.cycloneEye) {
            AppState.cycloneEye = [...trackPoints[0]];
        }
        AppState.cycloneTargetEye = [...trackPoints[0]];
    } else if (scenario === 'flood') {
        const floodStyle = { fillColor: '#3b82f6', fillOpacity: 0.35, color: '#2563eb', weight: 3 };
        
        if (AppState.districtLayer) {
            AppState.districtLayer.setStyle(feature => {
                const name = feature.properties.NAME_1 || feature.properties.state_name || feature.properties.STNAME || "";
                if (["Krishna", "Guntur", "Godavari"].some(d => name.toLowerCase().includes(d.toLowerCase()))) {
                    return floodStyle;
                }
                return { fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', weight: 1 };
            });
        }
        
        if (AppState.mapRight && AppState.isSplitMode && AppState.districtLayerRight) {
            AppState.districtLayerRight.setStyle(feature => {
                const name = feature.properties.NAME_1 || feature.properties.state_name || feature.properties.STNAME || "";
                if (["Krishna", "Guntur", "Godavari"].some(d => name.toLowerCase().includes(d.toLowerCase()))) {
                    return floodStyle;
                }
                return { fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', weight: 1 };
            });
        }

    } else if (scenario === 'drought') {
        const droughtStyle = { fillColor: '#b45309', fillOpacity: 0.35, color: '#d97706', weight: 3 };
        
        if (AppState.districtLayer) {
            AppState.districtLayer.setStyle(feature => {
                const name = feature.properties.NAME_1 || feature.properties.state_name || feature.properties.STNAME || "";
                if (["Anantapur", "Kurnool", "Kadapa"].some(d => name.toLowerCase().includes(d.toLowerCase()))) {
                    return droughtStyle;
                }
                return { fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', weight: 1 };
            });
        }

        if (AppState.mapRight && AppState.isSplitMode && AppState.districtLayerRight) {
            AppState.districtLayerRight.setStyle(feature => {
                const name = feature.properties.NAME_1 || feature.properties.state_name || feature.properties.STNAME || "";
                if (["Anantapur", "Kurnool", "Kadapa"].some(d => name.toLowerCase().includes(d.toLowerCase()))) {
                    return droughtStyle;
                }
                return { fillColor: 'transparent', fillOpacity: 0, color: '#ffffff', weight: 1 };
            });
        }
    }
}

// ─── Digital Twin Evolution Mode ──────────────────────────────────────────────
function triggerEvolutionMode() {
    if (AppState.isEvolutionMode) return;
    AppState.isEvolutionMode = true;

    showNotification("Digital Twin Evolution", "Initiating multi-era climate progression.", "success");

    let era = 0;
    const eras = ['past', 'present', 'future', 'scenario'];
    
    const interval = setInterval(() => {
        if (!AppState.isEvolutionMode) {
            clearInterval(interval);
            return;
        }

        const currentEra = eras[era];
        if (currentEra === 'scenario') {
            showNotification("Evolution Stage", "Phase 4: Simulated Extreme Heatwave Scenario (+4.5°C)", "warning");
            triggerScenarioPreset('heatwave');
        } else {
            setTimeline(currentEra);
            const slider = document.getElementById("timelineRange");
            if (slider) slider.value = era;
            showNotification("Evolution Stage", `Phase ${era + 1}: ${currentEra.toUpperCase()} climate state`, "success");
        }

        era++;
        if (era >= eras.length) {
            clearInterval(interval);
            AppState.isEvolutionMode = false;
            showNotification("Evolution Complete", "Atmospheric timeline re-synchronized to operational mode.", "success");
            resetPlayback();
        }
    }, 4500);
}

function showNotification(title, message, type = 'info') {
    const alertId = Date.now();
    const container = document.getElementById("alerts-container");
    
    let badgeClass = "badge-low";
    if (type === "warning") badgeClass = "badge-high";
    else if (type === "error" || type === "critical") badgeClass = "badge-critical";
    else if (type === "success") badgeClass = "badge-low"; 

    const html = `
        <div id="toast-${alertId}" class="p-3 bg-navy-800/90 rounded border border-slate-700/60 shadow-xl flex flex-col gap-1 transition duration-300 transform translate-y-2 opacity-0">
            <div class="flex items-center justify-between">
                <span class="${badgeClass} text-[9px] px-1.5 py-0.5 rounded uppercase font-bold tracking-wider">${type}</span>
                <span class="text-[10px] text-cyan-400 font-display font-medium">${title}</span>
            </div>
            <p class="text-[11px] text-slate-300 leading-normal mt-1">${message}</p>
        </div>
    `;

    if (container) {
        container.insertAdjacentHTML('afterbegin', html);
        const toast = document.getElementById(`toast-${alertId}`);
        gsap.to(toast, { opacity: 1, y: 0, duration: 0.3 });
        
        setTimeout(() => {
            gsap.to(toast, { opacity: 0, y: -10, duration: 0.3, onComplete: () => toast.remove() });
        }, 4000);
    }
}

function triggerScenarioPreset(scenario) {
    AppState.activeScenario = scenario;

    document.querySelectorAll(".scenario-btn").forEach(btn => {
        btn.classList.remove("bg-cyan-500/20", "border-cyan-500/50");
        btn.style.boxShadow = "";
    });

    const activeBtn = document.querySelector(`.scenario-btn[data-scenario="${scenario}"]`);
    if (activeBtn) {
        activeBtn.classList.add("bg-cyan-500/20", "border-cyan-500/50");
        activeBtn.style.boxShadow = "0 0 10px rgba(0, 210, 255, 0.2) inset";
    }

    let temp = 0.0, rain = 0, hum = 0;
    if (scenario === 'heatwave') { temp = 4.5; rain = -30; hum = -10; AppState.activeLayers.temperature = true; }
    else if (scenario === 'cyclone') { temp = 1.0; rain = 35; hum = 15; AppState.activeLayers.wind = true; }
    else if (scenario === 'flood') { temp = -0.5; rain = 40; hum = 10; AppState.activeLayers.rainfall = true; }
    else if (scenario === 'drought') { temp = 3.0; rain = -50; hum = -15; AppState.activeLayers.humidity = true; }
    else if (scenario === 'uhi') { temp = 2.5; rain = -5; hum = -5; AppState.activeLayers.temperature = true; }
    else if (scenario === 'monsoon') { temp = 1.5; rain = -25; hum = -8; AppState.activeLayers.rainfall = true; }

    AppState.simulator.temp = temp;
    AppState.simulator.rain = rain;
    AppState.simulator.humidity = hum;

    const tempSlider = document.getElementById("sim-temp");
    if (tempSlider) tempSlider.value = temp;
    const tempVal = document.getElementById("sim-temp-val");
    if (tempVal) tempVal.innerText = (temp > 0 ? '+' : '') + temp.toFixed(1) + '°C';

    const rainSlider = document.getElementById("sim-rain");
    if (rainSlider) rainSlider.value = rain;
    const rainVal = document.getElementById("sim-rain-val");
    if (rainVal) rainVal.innerText = (rain > 0 ? '+' : '') + rain + '%';

    const humSlider = document.getElementById("sim-humidity");
    if (humSlider) humSlider.value = hum;
    const humVal = document.getElementById("sim-humidity-val");
    if (humVal) humVal.innerText = (hum > 0 ? '+' : '') + hum + '%';

    syncLayerButtonsUI();
    updateMapLegend();
    updateVisualHazards();
    triggerSimulation();
}