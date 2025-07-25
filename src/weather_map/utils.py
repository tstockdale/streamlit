import pytz 
from datetime import datetime
import logging
import math


# Retrieve the logger instance
logger = logging.getLogger(__name__)


def unix_to_datetime(unix_time, timezone):
    tz = pytz.timezone(timezone)
    return datetime.fromtimestamp(unix_time, tz).strftime('%m-%d-%Y:%H-%M-%S-%Z')

def uvi_to_risk_string(uvi):
    risk_levels = {
        (0, 3): "Low",
        (3, 6): "Moderate",
        (6, 8): "High",
        (8, 11): "Very High",
        (11, float('inf')): "Extreme"
    }
    for range_tuple, risk in risk_levels.items():
        if range_tuple[0] <= uvi < range_tuple[1]:
            return risk
    return "Unknown"

def lat_lon_to_world_coordinates(lat, lon, zoom=0):
    """
    Convert latitude and longitude to world coordinates (x, y) using the Web Mercator projection.

    Args:
        lat (float): Latitude in degrees.
        lon (float): Longitude in degrees.
        zoom (int): Zoom level (default is 0, which gives normalized coordinates).

    Returns:
        tuple: A tuple (x, y) representing the world coordinates.
    """
    # Constants for Web Mercator projection
    TILE_SIZE = 256  # Size of a tile in pixels

    # Convert longitude to x coordinate
    x = (lon + 180) / 360  # Normalize longitude to [0, 1]

    # Convert latitude to y coordinate
    sin_lat = math.sin(math.radians(lat))
    y = 0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)

    # Adjust for zoom level
    scale = TILE_SIZE * (2 ** zoom)
    x_world = x * scale
    y_world = y * scale

    return x_world, y_world

def celsius_to_fahrenheit(celsius):
    """
    Convert temperature from Celsius to Fahrenheit.

    Args:
        celsius (float): Temperature in Celsius.

    Returns:
        float: Temperature in Fahrenheit.
    """
    return celsius * 9.0 / 5.0 + 32.0

def meters_per_second_to_miles_per_hour(mps):
    """
    Convert speed from meters per second to miles per hour.

    Args:
        mps (float): Speed in meters per second.

    Returns:
        float: Speed in miles per hour.
    """
    # Conversion factor: 1 m/s = 2.23694 mph
    # Derivation: 1 m/s × (3.28084 ft/m) × (1 mi/5280 ft) × (3600 s/hr) = 2.23694 mph
    return mps * 2.23694

def lat_lon_to_tile_coordinates(lat, lon, zoom):
    """
    Convert latitude and longitude to tile coordinates (x, y) for a given zoom level
    using the Web Mercator projection.

    Args:
        lat (float): Latitude in degrees.
        lon (float): Longitude in degrees.
        zoom (int): Zoom level.

    Returns:
        tuple: (x_tile, y_tile) tile coordinates as integers.
    """

    n = 2 ** zoom
    lat_rad = math.radians(lat)
    x_tile = int(n * ((lon + 180) / 360))
    y_tile = int(n * (1 - (math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi)) / 2)
    return x_tile, y_tile
