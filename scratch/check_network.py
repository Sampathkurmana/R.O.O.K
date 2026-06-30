import urllib.request
import ssl

try:
    context = ssl._create_unverified_context()
    response = urllib.request.urlopen("https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/0/0/0", timeout=5, context=context)
    print("ESRI Tile Status:", response.getcode())
except Exception as e:
    print("ESRI Tile Error:", e)

try:
    response2 = urllib.request.urlopen("https://tile.openstreetmap.org/0/0/0.png", timeout=5, context=context)
    print("OSM Tile Status:", response2.getcode())
except Exception as e:
    print("OSM Tile Error:", e)
