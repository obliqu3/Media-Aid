"""Clinics Route — Nearby healthcare facility lookup"""

from fastapi import APIRouter, Query
import httpx

router = APIRouter()


@router.get("/nearby")
async def nearby_clinics(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(5000, le=20000, description="Search radius in meters"),
):
    """
    Find nearby clinics using OpenStreetMap Overpass API.
    Free, no API key required — great for low-resource deployments.
    """
    overpass_query = f"""
    [out:json][timeout:15];
    (
      node["amenity"~"hospital|clinic|pharmacy|doctors|health_centre"](around:{radius},{lat},{lon});
      way["amenity"~"hospital|clinic|pharmacy|doctors|health_centre"](around:{radius},{lat},{lon});
    );
    out body center 20;
    """
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data=overpass_query,
            )
            data = resp.json()

        clinics = []
        for el in data.get("elements", []):
            tags = el.get("tags", {})
            lat_c = el.get("lat") or el.get("center", {}).get("lat")
            lon_c = el.get("lon") or el.get("center", {}).get("lon")
            if not (lat_c and lon_c):
                continue
            clinics.append({
                "name": tags.get("name", "Unnamed Facility"),
                "type": tags.get("amenity", "clinic"),
                "latitude": lat_c,
                "longitude": lon_c,
                "phone": tags.get("phone") or tags.get("contact:phone"),
                "address": tags.get("addr:full") or f"{tags.get('addr:street', '')} {tags.get('addr:city', '')}".strip(),
                "opening_hours": tags.get("opening_hours"),
                "emergency": tags.get("emergency") == "yes",
                "wheelchair": tags.get("wheelchair"),
            })

        return {"clinics": clinics[:20], "total": len(clinics), "radius_m": radius}

    except Exception as e:
        return {"clinics": [], "error": f"Location service unavailable: {str(e)}"}
