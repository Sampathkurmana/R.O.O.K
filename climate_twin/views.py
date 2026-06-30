from django.shortcuts import render
import os
import urllib.request
import json
from django.conf import settings

def download_and_extract_ap_geojson():
    import ssl
    geojson_dir = os.path.join(settings.BASE_DIR, 'static', 'geojson')
    os.makedirs(geojson_dir, exist_ok=True)
    geojson_path = os.path.join(geojson_dir, 'andhra_pradesh.geojson')
    
    # Cache invalidation: if the cached file is pre-split (doesn't have our verified tag), delete it
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            if cached_data.get("source") == "datta07_post_split":
                return
            else:
                os.remove(geojson_path)
                print("Old pre-split AP GeoJSON detected. Deleting to re-download post-split border.")
        except Exception:
            try:
                os.remove(geojson_path)
            except Exception:
                pass
        
    # URL 1: subhashb's pre-filtered post-split AP GeoJSON (very small, fast)
    # URL 2: datta07's INDIAN-SHAPEFILES states GeoJSON (post-split, complete)
    urls = [
        ("https://raw.githubusercontent.com/subhashb/India-State-GeoJSON/master/Andhra_Pradesh.geojson", True),
        ("https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/india_states.geojson", False)
    ]
    
    # Create unverified SSL context to prevent certificate validation errors on Windows
    ssl_context = ssl._create_unverified_context()
    
    for url, is_pre_filtered in urls:
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            if is_pre_filtered:
                # The file is already just Andhra Pradesh
                # Let's ensure it has the verified source tag
                data["source"] = "datta07_post_split"
                with open(geojson_path, "w", encoding='utf-8') as f:
                    json.dump(data, f, indent=2)
                print(f"Successfully saved post-split AP GeoJSON from pre-filtered {url}")
                return
            else:
                # Filter from the complete states file
                ap_feature = None
                for feature in data.get("features", []):
                    properties = feature.get("properties", {})
                    state_name = ""
                    for key in ["NAME_1", "state_name", "name", "State_Name", "NAME"]:
                        if key in properties and properties[key]:
                            state_name = str(properties[key]).strip()
                            break
                    
                    if state_name and "andhra pradesh" in state_name.lower():
                        ap_feature = feature
                        break
                
                if ap_feature:
                    ap_geojson = {
                        "type": "FeatureCollection",
                        "source": "datta07_post_split",
                        "features": [ap_feature]
                    }
                    with open(geojson_path, "w", encoding='utf-8') as f:
                        json.dump(ap_geojson, f, indent=2)
                    print(f"Successfully saved post-split AP GeoJSON from complete {url}")
                    return
        except Exception as e:
            print(f"Failed to fetch from {url}: {e}")


def index(request, panel='dashboard'):
    """
    Renders the unified Climate Digital Twin dashboard, 
    pre-opening the active panel based on the URL context.
    """
    import datetime
    from climate_twin.models import ClimateObservation
    today = datetime.date.today()
    if not ClimateObservation.objects.filter(date=today).exists():
        print(f"[R.O.O.K] Today's observations for {today} are missing. Seeding database in-process...")
        try:
            import populate_db
            populate_db.seed_data()
        except Exception as e:
            print(f"[R.O.O.K] In-process database seeding failed: {e}")

    import ssl
    import urllib.request
    import json
    import os
    import shutil
    
    # Copy generated satellite image to static folder
    try:
        src_img = r"C:\Users\Sampath Kurmana\.gemini\antigravity-ide\brain\20f7727b-6b5e-4f9e-90c9-e5ac844de4ad\realistic_satellite_1782814052647.png"
        dst_img = os.path.join(settings.BASE_DIR, 'static', 'img', 'satellite.png')
        if os.path.exists(src_img):
            os.makedirs(os.path.dirname(dst_img), exist_ok=True)
            shutil.copy(src_img, dst_img)
            print("✓ [R.O.O.K] Generated realistic satellite image copied to static/img/satellite.png")
        
        # Cleanup temporary copy script
        temp_script = os.path.join(settings.BASE_DIR, 'copy_image.py')
        if os.path.exists(temp_script):
            os.remove(temp_script)
    except Exception as e:
        print("Error copying generated satellite image:", e)
    
    geojson_dir = os.path.join(settings.BASE_DIR, 'static', 'geojson')
    os.makedirs(geojson_dir, exist_ok=True)
    geojson_path = os.path.join(geojson_dir, 'andhra_pradesh.geojson')
    
    # Cache invalidation: if the cached file is pre-split, delete it to fetch correct boundary
    if os.path.exists(geojson_path):
        try:
            with open(geojson_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            if cached_data.get("source") != "datta07_post_split":
                os.remove(geojson_path)
                print("Old pre-split GeoJSON cache cleared.")
        except Exception:
            try:
                os.remove(geojson_path)
            except Exception:
                pass

    if not os.path.exists(geojson_path):
        url = "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES/master/INDIA/INDIA_STATES.geojson"
        ssl_context = ssl._create_unverified_context()
        try:
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
            )
            with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
                data = json.loads(response.read().decode('utf-8'))
                
            ap_feature = None
            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                state_name = ""
                # Try all common keys for Indian boundaries
                for key in ["STNAME_SH", "STNAME", "NAME_1", "state_name", "name", "State_Name", "NAME", "ST_NM", "StateName"]:
                    if key in properties and properties[key]:
                        state_name = str(properties[key]).strip()
                        break
                
                if state_name and "andhra pradesh" in state_name.lower():
                    ap_feature = feature
                    break
            
            if ap_feature:
                ap_geojson = {
                    "type": "FeatureCollection",
                    "source": "datta07_post_split",
                    "features": [ap_feature]
                }
                with open(geojson_path, "w", encoding='utf-8') as f:
                    json.dump(ap_geojson, f, indent=2)
                print(f"Successfully extracted post-split Andhra Pradesh border to {geojson_path}")
                # Clean up debug log file
                try:
                    os.remove(os.path.join(settings.BASE_DIR, 'debug_log.txt'))
                except Exception:
                    pass
            else:
                print("Andhra Pradesh state not found in the GeoJSON dataset.")
        except Exception as e:
            print(f"Error fetching GeoJSON boundary from {url}: {e}")

    context = {
        'active_panel': panel,
    }
    return render(request, 'index.html', context)





