import os

def main():
    filepath = r"static/js/app.js"
    if not os.path.exists(filepath):
        print(f"Error: {filepath} not found.")
        return

    print("Reading static/js/app.js...")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Find conflict markers
    start_marker = "<<<<<<< HEAD"
    middle_marker = "======="
    end_marker = ">>>>>>> 14b311f (merged remote main, keeping locally trained models)"

    if start_marker not in content or middle_marker not in content:
        print("Error: Conflict markers not found in app.js. Are they already resolved?")
        return

    # Split the file around the conflict markers
    # The file is structured as:
    # [start_marker]
    # [remote version of app.js]
    # [middle_marker]
    # [local version of app.js]
    # [end_marker]
    
    parts_by_start = content.split(start_marker)
    pre_conflict = parts_by_start[0] # Should be empty or whitespace since it starts at line 1
    
    conflict_body = parts_by_start[1]
    parts_by_middle = conflict_body.split(middle_marker)
    
    remote_version = parts_by_middle[0]
    
    local_and_post = parts_by_middle[1]
    
    # We split local_and_post by end_marker, but there could be variations of the hash/message in git.
    # Let's find index of >>>>>>> to be flexible
    end_idx = local_and_post.find(">>>>>>>")
    if end_idx == -1:
        print("Error: End conflict marker not found.")
        return
        
    local_version = local_and_post[:end_idx]
    post_conflict = local_and_post[local_and_post.find("\n", end_idx):] # Anything after end marker line

    print("Successfully separated remote and local versions.")

    # Now we modify the local_version to integrate the 6-day forecast code.
    
    # 1. Inject forecastData: [] into AppState definition
    app_state_target = "cycloneWindSpeed: 0"
    if app_state_target in local_version:
        print("Injecting forecastData into AppState...")
        local_version = local_version.replace(
            app_state_target,
            "cycloneWindSpeed: 0,\n    forecastData: []"
        )
    else:
        print("Warning: AppState target not found.")

    # 2. Inject fetchSixDayForecast call into window.queryLocation
    query_location_target = "window.queryLocation = async function (lat, lng) {"
    if query_location_target in local_version:
        print("Injecting fetchSixDayForecast call into window.queryLocation...")
        local_version = local_version.replace(
            query_location_target,
            "window.queryLocation = async function (lat, lng) {\n        fetchSixDayForecast(lat, lng);"
        )
    else:
        print("Warning: window.queryLocation target not found.")

    # 3. Add helper functions at the end of the local_version (before the closing IIFE)
    # The local_version ends with something like:
    # })();
    # Let's replace the last })(); with the functions + })();
    iife_end = "})();"
    last_iife_idx = local_version.rfind(iife_end)
    if last_iife_idx != -1:
        print("Injecting forecast helper functions...")
        forecast_funcs = """

// Extend your AppState to include a container for the fetched forecast data
AppState.forecastData = [];

// Create a core function to handle the async API request
async function fetchSixDayForecast(lat, lng) {
    try {
        const response = await fetch(`/api/climate/forecast/?lat=${lat}&lng=${lng}`);
        if (!response.ok) throw new Error('Network response was not looking good.');
        
        const data = await response.json();
        if (data.status === 'success') {
            AppState.forecastData = data.forecast;
            renderForecastUI();
        }
    } catch (error) {
        console.error('❌ Failed to fetch XGBoost forecast data:', error);
    }
}

// Dynamically generate cards inside your live weather panel container
function renderForecastUI() {
    const forecastContainer = document.getElementById('forecast-cards-container');
    if (!forecastContainer) return; // Guard clause if element isn't in view
    
    forecastContainer.innerHTML = ''; // Clear out past elements
    
    AppState.forecastData.forEach(card => {
        const cardHTML = `
            <div class="forecast-card bg-surface p-4 rounded-lg flex flex-col items-center shadow border border-slate-800/40">
                <span class="text-sm font-semibold opacity-80">${card.day_name}</span>
                <span class="text-xs opacity-50 mb-2">${card.date}</span>
                <div class="text-2xl font-bold my-1 text-cyan-400">${card.temperature}°C</div>
                <div class="flex flex-col text-xs space-y-1 opacity-70 w-full mt-2 border-t pt-2 border-slate-850">
                    <div class="flex justify-between">💧 Rain: <span>${card.rainfall} mm</span></div>
                    <div class="flex justify-between">🌫️ Humid: <span>${card.humidity}%</span></div>
                    <div class="flex justify-between">💨 Wind: <span>${card.wind_speed} kt</span></div>
                </div>
            </div>
        `;
        forecastContainer.insertAdjacentHTML('beforeend', cardHTML);
    });
}

// Hook this function inside your existing map click/station selection listener
const originalUpdateMapData = window.updateMapData;
window.updateMapData = function() {
    if (typeof originalUpdateMapData === 'function') {
        originalUpdateMapData.apply(this, arguments);
    }
    fetchSixDayForecast(AppState.selectedLat, AppState.selectedLng);
};
"""
        # We replace the last occurrence of })(); with the functions + })();
        local_version = local_version[:last_iife_idx] + forecast_funcs + local_version[last_iife_idx:]
    else:
        print("Warning: IIFE closing tag not found.")

    # Reconstruct the file contents
    new_content = pre_conflict + local_version.strip() + "\n" + post_conflict.strip() + "\n"

    print("Writing resolved static/js/app.js...")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("✓ Successfully resolved all conflicts in static/js/app.js!")

if __name__ == "__main__":
    main()
