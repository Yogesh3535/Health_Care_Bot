"""
Nearest doctor / clinic / hospital lookup using OpenStreetMap's free
Overpass API (no API key required). Requires internet access at
runtime on the machine running this app.

Given a latitude/longitude (from the browser's geolocation, sent by
the frontend), this queries nearby nodes tagged as amenity=doctors,
amenity=clinic, or amenity=hospital within a radius, then sorts them
by straight-line (haversine) distance.
"""

import math
import requests

# Overpass has several public mirrors; if the primary is down, rate-limiting,
# or (as with a 406) rejecting the request, we fall back to the next one.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
]

# Overpass servers reject requests with no/blocked User-Agent (this is what
# was causing the "406 Not Acceptable" error - Python's default requests
# User-Agent is filtered out). A descriptive custom User-Agent fixes it.
REQUEST_HEADERS = {
    "User-Agent": "HealthChatbot-Demo/1.0 (educational project; contact: demo@example.com)",
    "Accept": "application/json",
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _query_overpass(query):
    """Try each mirror in turn; return the first successful JSON response."""
    last_error = None
    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url, data={"data": query}, headers=REQUEST_HEADERS, timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            continue
    # All mirrors failed - raise the last error so the caller can report it.
    raise last_error


def find_nearby_medical(lat, lon, radius_m=3000, limit=10):
    """
    Returns a list of dicts: {name, type, lat, lon, distance_km, address}
    sorted by distance. Raises requests.RequestException if every mirror fails.
    """
    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"="doctors"](around:{radius_m},{lat},{lon});
      node["amenity"="clinic"](around:{radius_m},{lat},{lon});
      node["amenity"="hospital"](around:{radius_m},{lat},{lon});
      node["amenity"="pharmacy"](around:{radius_m},{lat},{lon});
    );
    out center;
    """
    data = _query_overpass(query)

    results = []
    for element in data.get("elements", []):
        tags = element.get("tags", {})
        name = tags.get("name", "Unnamed facility")
        amenity = tags.get("amenity", "medical")
        e_lat = element.get("lat")
        e_lon = element.get("lon")
        if e_lat is None or e_lon is None:
            continue

        dist = haversine_km(lat, lon, e_lat, e_lon)
        address_parts = [
            tags.get("addr:housenumber", ""),
            tags.get("addr:street", ""),
            tags.get("addr:city", ""),
        ]
        address = " ".join(p for p in address_parts if p).strip() or "Address not available"

        results.append({
            "name": name,
            "type": amenity,
            "lat": e_lat,
            "lon": e_lon,
            "distance_km": round(dist, 2),
            "address": address,
        })

    results.sort(key=lambda r: r["distance_km"])
    return results[:limit]
