"""
Google Maps Service
Geocoding, satellite imagery, and solar potential analysis
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import aiohttp
import hashlib
import json

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GeoLocation:
    """Geocoded location result"""
    latitude: float
    longitude: float
    formatted_address: str
    place_id: str
    country: str = "DE"
    postal_code: str = ""
    city: str = ""
    street: str = ""
    confidence: float = 1.0  # 0.0 to 1.0


@dataclass
class SolarPotential:
    """Solar potential analysis result"""
    max_array_area_m2: float
    max_sunshine_hours_per_year: float
    carbon_offset_factor_kg_per_mwh: float
    panels_count: int
    yearly_energy_dc_kwh: float
    roof_segments: List[Dict[str, Any]]


@dataclass
class SatelliteImage:
    """Satellite imagery result"""
    image_data: bytes
    content_type: str
    width: int
    height: int
    center_lat: float
    center_lng: float
    zoom: int


class GoogleMapsService:
    """
    Google Maps Platform Integration Service

    Provides geocoding, satellite imagery, and solar potential analysis
    for PV system planning.

    APIs Used:
        - Geocoding API: Address to coordinates
        - Static Maps API: Satellite imagery
        - Solar API: Roof analysis and solar potential (where available)

    Environment Variables:
        GOOGLE_MAPS_API_KEY: API key with appropriate services enabled
    """

    GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
    SOLAR_API_URL = "https://solar.googleapis.com/v1/buildingInsights:findClosest"

    # Simple in-memory cache (in production, use Redis)
    _geocode_cache: Dict[str, GeoLocation] = {}
    _cache_expiry: Dict[str, datetime] = {}

    def __init__(self):
        self.api_key = os.getenv("GOOGLE_MAPS_API_KEY", settings.GOOGLE_MAPS_API_KEY)
        self.is_configured = bool(self.api_key)

        if not self.is_configured:
            logger.warning("Google Maps not configured - missing API key")

    def _get_cache_key(self, *args) -> str:
        """Generate cache key from arguments"""
        return hashlib.md5(json.dumps(args, sort_keys=True).encode()).hexdigest()

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cache entry is still valid"""
        if key not in self._cache_expiry:
            return False
        return datetime.utcnow() < self._cache_expiry[key]

    # ============ GEOCODING ============

    async def geocode_address(
        self,
        address: str,
        country: str = "DE"
    ) -> Optional[GeoLocation]:
        """
        Convert address to geographic coordinates

        Args:
            address: Full address string
            country: Country code for region biasing (default: Germany)

        Returns:
            GeoLocation with coordinates and parsed address components
        """
        if not address:
            return None

        # Check cache first
        cache_key = self._get_cache_key("geocode", address, country)
        if cache_key in self._geocode_cache and self._is_cache_valid(cache_key):
            logger.debug(f"Geocode cache hit for: {address}")
            return self._geocode_cache[cache_key]

        if not self.is_configured:
            return self._simulate_geocode(address)

        try:
            params = {
                "address": address,
                "key": self.api_key,
                "region": country.lower(),
                "language": "de"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.GEOCODE_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Geocoding failed: HTTP {response.status}")
                        return self._simulate_geocode(address)

                    data = await response.json()

                    if data.get("status") != "OK":
                        logger.warning(f"Geocoding status: {data.get('status')}")
                        if data.get("status") == "ZERO_RESULTS":
                            return None
                        return self._simulate_geocode(address)

                    results = data.get("results", [])
                    if not results:
                        return None

                    result = results[0]
                    geometry = result.get("geometry", {})
                    location = geometry.get("location", {})

                    # Parse address components
                    components = {c["types"][0]: c for c in result.get("address_components", [])}

                    geo_location = GeoLocation(
                        latitude=location.get("lat", 0),
                        longitude=location.get("lng", 0),
                        formatted_address=result.get("formatted_address", address),
                        place_id=result.get("place_id", ""),
                        country=components.get("country", {}).get("short_name", country),
                        postal_code=components.get("postal_code", {}).get("long_name", ""),
                        city=components.get("locality", {}).get("long_name", "")
                              or components.get("administrative_area_level_3", {}).get("long_name", ""),
                        street=f"{components.get('route', {}).get('long_name', '')} {components.get('street_number', {}).get('long_name', '')}".strip(),
                        confidence=self._calculate_confidence(geometry)
                    )

                    # Cache result
                    self._geocode_cache[cache_key] = geo_location
                    self._cache_expiry[cache_key] = datetime.utcnow() + timedelta(days=30)

                    return geo_location

        except Exception as e:
            logger.error(f"Geocoding error: {e}")
            return self._simulate_geocode(address)

    def _calculate_confidence(self, geometry: Dict[str, Any]) -> float:
        """Calculate confidence score based on geometry precision"""
        location_type = geometry.get("location_type", "")
        confidence_map = {
            "ROOFTOP": 1.0,
            "RANGE_INTERPOLATED": 0.8,
            "GEOMETRIC_CENTER": 0.6,
            "APPROXIMATE": 0.4
        }
        return confidence_map.get(location_type, 0.5)

    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[GeoLocation]:
        """
        Convert coordinates to address

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate

        Returns:
            GeoLocation with address details
        """
        if not self.is_configured:
            return self._simulate_reverse_geocode(latitude, longitude)

        try:
            params = {
                "latlng": f"{latitude},{longitude}",
                "key": self.api_key,
                "language": "de"
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.GEOCODE_URL, params=params) as response:
                    if response.status != 200:
                        return None

                    data = await response.json()

                    if data.get("status") != "OK":
                        return None

                    results = data.get("results", [])
                    if not results:
                        return None

                    result = results[0]
                    components = {c["types"][0]: c for c in result.get("address_components", [])}

                    return GeoLocation(
                        latitude=latitude,
                        longitude=longitude,
                        formatted_address=result.get("formatted_address", ""),
                        place_id=result.get("place_id", ""),
                        country=components.get("country", {}).get("short_name", "DE"),
                        postal_code=components.get("postal_code", {}).get("long_name", ""),
                        city=components.get("locality", {}).get("long_name", ""),
                        street=f"{components.get('route', {}).get('long_name', '')} {components.get('street_number', {}).get('long_name', '')}".strip()
                    )

        except Exception as e:
            logger.error(f"Reverse geocoding error: {e}")
            return None

    # ============ SATELLITE IMAGERY ============

    async def get_satellite_image(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 19,
        width: int = 640,
        height: int = 640,
        scale: int = 2
    ) -> Optional[SatelliteImage]:
        """
        Get satellite imagery for a location

        Args:
            latitude: Center latitude
            longitude: Center longitude
            zoom: Zoom level (1-21, higher = more detail)
            width: Image width in pixels (max 640)
            height: Image height in pixels (max 640)
            scale: Scale factor (1 or 2 for high-DPI)

        Returns:
            SatelliteImage with image data
        """
        if not self.is_configured:
            return self._simulate_satellite_image(latitude, longitude, zoom, width, height)

        try:
            params = {
                "center": f"{latitude},{longitude}",
                "zoom": zoom,
                "size": f"{width}x{height}",
                "scale": scale,
                "maptype": "satellite",
                "key": self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.STATIC_MAP_URL, params=params) as response:
                    if response.status != 200:
                        logger.error(f"Satellite image failed: HTTP {response.status}")
                        return None

                    image_data = await response.read()
                    content_type = response.headers.get("Content-Type", "image/png")

                    return SatelliteImage(
                        image_data=image_data,
                        content_type=content_type,
                        width=width * scale,
                        height=height * scale,
                        center_lat=latitude,
                        center_lng=longitude,
                        zoom=zoom
                    )

        except Exception as e:
            logger.error(f"Satellite image error: {e}")
            return None

    async def get_satellite_image_with_marker(
        self,
        latitude: float,
        longitude: float,
        zoom: int = 18,
        width: int = 640,
        height: int = 480
    ) -> Optional[SatelliteImage]:
        """
        Get satellite image with a marker at the center

        Useful for showing the exact building location.
        """
        if not self.is_configured:
            return self._simulate_satellite_image(latitude, longitude, zoom, width, height)

        try:
            params = {
                "center": f"{latitude},{longitude}",
                "zoom": zoom,
                "size": f"{width}x{height}",
                "scale": 2,
                "maptype": "satellite",
                "markers": f"color:red|{latitude},{longitude}",
                "key": self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.STATIC_MAP_URL, params=params) as response:
                    if response.status != 200:
                        return None

                    image_data = await response.read()

                    return SatelliteImage(
                        image_data=image_data,
                        content_type=response.headers.get("Content-Type", "image/png"),
                        width=width * 2,
                        height=height * 2,
                        center_lat=latitude,
                        center_lng=longitude,
                        zoom=zoom
                    )

        except Exception as e:
            logger.error(f"Satellite image with marker error: {e}")
            return None

    # ============ SOLAR API ============

    async def get_solar_potential(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[SolarPotential]:
        """
        Get solar potential analysis for a building

        Uses Google Solar API to analyze roof segments and solar potential.
        Note: Solar API is only available in certain regions.

        Args:
            latitude: Building latitude
            longitude: Building longitude

        Returns:
            SolarPotential with roof analysis data
        """
        if not self.is_configured:
            return self._simulate_solar_potential(latitude, longitude)

        try:
            params = {
                "location.latitude": latitude,
                "location.longitude": longitude,
                "key": self.api_key
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(self.SOLAR_API_URL, params=params) as response:
                    if response.status == 404:
                        # Solar API not available for this location
                        logger.info(f"Solar API not available at {latitude}, {longitude}")
                        return self._estimate_solar_potential(latitude, longitude)

                    if response.status != 200:
                        logger.error(f"Solar API failed: HTTP {response.status}")
                        return self._estimate_solar_potential(latitude, longitude)

                    data = await response.json()

                    solar_potential = data.get("solarPotential", {})

                    # Parse roof segments
                    roof_segments = []
                    for segment in solar_potential.get("roofSegmentStats", []):
                        roof_segments.append({
                            "pitch_degrees": segment.get("pitchDegrees", 0),
                            "azimuth_degrees": segment.get("azimuthDegrees", 0),
                            "area_m2": segment.get("stats", {}).get("areaMeters2", 0),
                            "sunshine_hours": segment.get("stats", {}).get("sunshineQuantiles", [0])[-1] if segment.get("stats", {}).get("sunshineQuantiles") else 0
                        })

                    return SolarPotential(
                        max_array_area_m2=solar_potential.get("maxArrayAreaMeters2", 0),
                        max_sunshine_hours_per_year=solar_potential.get("maxSunshineHoursPerYear", 0),
                        carbon_offset_factor_kg_per_mwh=solar_potential.get("carbonOffsetFactorKgPerMwh", 400),
                        panels_count=solar_potential.get("maxArrayPanelsCount", 0),
                        yearly_energy_dc_kwh=solar_potential.get("solarPanelConfigs", [{}])[0].get("yearlyEnergyDcKwh", 0) if solar_potential.get("solarPanelConfigs") else 0,
                        roof_segments=roof_segments
                    )

        except Exception as e:
            logger.error(f"Solar API error: {e}")
            return self._estimate_solar_potential(latitude, longitude)

    def _estimate_solar_potential(
        self,
        latitude: float,
        longitude: float
    ) -> SolarPotential:
        """
        Estimate solar potential when Solar API is not available

        Uses location-based irradiance estimates for Germany.
        """
        # Germany irradiance varies from ~900 kWh/m2 (north) to ~1200 kWh/m2 (south)
        # Latitude ranges from ~47 (south) to ~55 (north)
        lat_factor = (55 - latitude) / (55 - 47)  # 0 = north, 1 = south
        annual_irradiance = 900 + (lat_factor * 300)  # kWh/m2

        # Assume typical commercial roof: 500 m2 usable
        assumed_roof_area = 500
        # 20% module efficiency, 15% system losses
        yearly_kwh = assumed_roof_area * annual_irradiance * 0.20 * 0.85

        return SolarPotential(
            max_array_area_m2=assumed_roof_area,
            max_sunshine_hours_per_year=annual_irradiance,
            carbon_offset_factor_kg_per_mwh=400,
            panels_count=int(assumed_roof_area / 2),  # ~2 m2 per panel
            yearly_energy_dc_kwh=yearly_kwh,
            roof_segments=[{
                "pitch_degrees": 30,
                "azimuth_degrees": 180,  # South
                "area_m2": assumed_roof_area,
                "sunshine_hours": annual_irradiance
            }]
        )

    # ============ HELPER METHODS ============

    async def geocode_and_get_satellite(
        self,
        address: str
    ) -> Tuple[Optional[GeoLocation], Optional[SatelliteImage]]:
        """
        Convenience method to geocode an address and get satellite image

        Args:
            address: Full address string

        Returns:
            Tuple of (GeoLocation, SatelliteImage)
        """
        location = await self.geocode_address(address)

        if not location:
            return None, None

        image = await self.get_satellite_image(
            latitude=location.latitude,
            longitude=location.longitude
        )

        return location, image

    # ============ SIMULATION METHODS ============

    def _simulate_geocode(self, address: str) -> GeoLocation:
        """Simulate geocoding for development"""
        # Generate deterministic coordinates based on address hash
        addr_hash = hash(address)
        # Center around Handewitt, Germany (EWS headquarters area)
        lat = 54.5 + (addr_hash % 1000) / 10000
        lng = 9.3 + ((addr_hash >> 10) % 1000) / 10000

        logger.info(f"[SIMULATION] Geocoded '{address}' to ({lat:.4f}, {lng:.4f})")

        return GeoLocation(
            latitude=lat,
            longitude=lng,
            formatted_address=address,
            place_id=f"SIM_{abs(addr_hash) % 1000000}",
            country="DE",
            postal_code="24983",
            city="Handewitt",
            street=address.split(",")[0] if "," in address else address,
            confidence=0.5
        )

    def _simulate_reverse_geocode(self, latitude: float, longitude: float) -> GeoLocation:
        """Simulate reverse geocoding"""
        return GeoLocation(
            latitude=latitude,
            longitude=longitude,
            formatted_address=f"Simulated Address near {latitude:.4f}, {longitude:.4f}",
            place_id=f"SIM_{int(latitude * 1000)}_{int(longitude * 1000)}",
            country="DE",
            postal_code="24983",
            city="Handewitt"
        )

    def _simulate_satellite_image(
        self,
        latitude: float,
        longitude: float,
        zoom: int,
        width: int,
        height: int
    ) -> SatelliteImage:
        """Return a placeholder satellite image for development"""
        # Create a simple gray placeholder image (1x1 pixel PNG)
        placeholder_png = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,  # IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,  # 1x1 pixel
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,  # IDAT chunk
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x05, 0xFE,
            0xD4, 0xEF, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,  # IEND chunk
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])

        logger.info(f"[SIMULATION] Generated placeholder satellite image for ({latitude:.4f}, {longitude:.4f})")

        return SatelliteImage(
            image_data=placeholder_png,
            content_type="image/png",
            width=width,
            height=height,
            center_lat=latitude,
            center_lng=longitude,
            zoom=zoom
        )

    def _simulate_solar_potential(self, latitude: float, longitude: float) -> SolarPotential:
        """Simulate solar potential analysis"""
        logger.info(f"[SIMULATION] Estimating solar potential for ({latitude:.4f}, {longitude:.4f})")
        return self._estimate_solar_potential(latitude, longitude)


# Singleton instance
_google_maps_service: Optional[GoogleMapsService] = None


def get_google_maps_service() -> GoogleMapsService:
    """Get or create Google Maps service instance"""
    global _google_maps_service
    if _google_maps_service is None:
        _google_maps_service = GoogleMapsService()
    return _google_maps_service
