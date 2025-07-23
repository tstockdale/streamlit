import unittest
import math
import pytz
from datetime import datetime
from utils import (
    unix_to_datetime,
    uvi_to_risk_string,
    lat_lon_to_world_coordinates,
    celsius_to_fahrenheit,
    meters_per_second_to_miles_per_hour,
    lat_lon_to_tile_coordinates
)


class TestUtils(unittest.TestCase):
    
    def test_unix_to_datetime(self):
        """Test unix timestamp to datetime conversion."""
        # Test with UTC timezone
        result = unix_to_datetime(1609459200, 'UTC')  # 2021-01-01 00:00:00 UTC
        self.assertEqual(result, '01-01-2021:00-00-00-UTC')
        
        # Test with EST timezone
        result = unix_to_datetime(1609459200, 'US/Eastern')  # 2020-12-31 19:00:00 EST
        self.assertEqual(result, '12-31-2020:19-00-00-EST')
        
        # Test with PST timezone
        result = unix_to_datetime(1609459200, 'US/Pacific')  # 2020-12-31 16:00:00 PST
        self.assertEqual(result, '12-31-2020:16-00-00-PST')
        
        # Test with different timestamp
        result = unix_to_datetime(0, 'UTC')  # 1970-01-01 00:00:00 UTC
        self.assertEqual(result, '01-01-1970:00-00-00-UTC')
    
    def test_uvi_to_risk_string(self):
        """Test UV index to risk level conversion."""
        # Test Low risk (0-3)
        self.assertEqual(uvi_to_risk_string(0), "Low")
        self.assertEqual(uvi_to_risk_string(1.5), "Low")
        self.assertEqual(uvi_to_risk_string(2.9), "Low")
        
        # Test Moderate risk (3-6)
        self.assertEqual(uvi_to_risk_string(3), "Moderate")
        self.assertEqual(uvi_to_risk_string(4.5), "Moderate")
        self.assertEqual(uvi_to_risk_string(5.9), "Moderate")
        
        # Test High risk (6-8)
        self.assertEqual(uvi_to_risk_string(6), "High")
        self.assertEqual(uvi_to_risk_string(7), "High")
        self.assertEqual(uvi_to_risk_string(7.9), "High")
        
        # Test Very High risk (8-11)
        self.assertEqual(uvi_to_risk_string(8), "Very High")
        self.assertEqual(uvi_to_risk_string(9.5), "Very High")
        self.assertEqual(uvi_to_risk_string(10.9), "Very High")
        
        # Test Extreme risk (11+)
        self.assertEqual(uvi_to_risk_string(11), "Extreme")
        self.assertEqual(uvi_to_risk_string(15), "Extreme")
        self.assertEqual(uvi_to_risk_string(100), "Extreme")
        
        # Test negative values (edge case)
        self.assertEqual(uvi_to_risk_string(-1), "Unknown")
    
    def test_lat_lon_to_world_coordinates(self):
        """Test latitude/longitude to world coordinates conversion."""
        # Test equator and prime meridian (0, 0)
        x, y = lat_lon_to_world_coordinates(0, 0, zoom=0)
        self.assertAlmostEqual(x, 128.0, places=1)  # 256 * 0.5
        self.assertAlmostEqual(y, 128.0, places=1)  # 256 * 0.5
        
        # Test North Pole approximation (85, 0) - Web Mercator doesn't handle exact poles
        x, y = lat_lon_to_world_coordinates(85, 0, zoom=0)
        self.assertAlmostEqual(x, 128.0, places=1)
        self.assertLess(y, 10)  # Should be very close to 0
        
        # Test South Pole approximation (-85, 0)
        x, y = lat_lon_to_world_coordinates(-85, 0, zoom=0)
        self.assertAlmostEqual(x, 128.0, places=1)
        self.assertGreater(y, 246)  # Should be very close to 256
        
        # Test with different longitude (0, 180)
        x, y = lat_lon_to_world_coordinates(0, 180, zoom=0)
        self.assertAlmostEqual(x, 256.0, places=1)
        self.assertAlmostEqual(y, 128.0, places=1)
        
        # Test with negative longitude (0, -180)
        x, y = lat_lon_to_world_coordinates(0, -180, zoom=0)
        self.assertAlmostEqual(x, 0.0, places=1)
        self.assertAlmostEqual(y, 128.0, places=1)
        
        # Test with zoom level 1
        x, y = lat_lon_to_world_coordinates(0, 0, zoom=1)
        self.assertAlmostEqual(x, 256.0, places=1)  # 512 * 0.5
        self.assertAlmostEqual(y, 256.0, places=1)  # 512 * 0.5
        
        # Test specific coordinates (New York City approximately)
        x, y = lat_lon_to_world_coordinates(40.7128, -74.0060, zoom=0)
        self.assertGreater(x, 0)
        self.assertLess(x, 256)
        self.assertGreater(y, 0)
        self.assertLess(y, 256)
    
    def test_celsius_to_fahrenheit(self):
        """Test Celsius to Fahrenheit conversion."""
        # Test freezing point of water
        self.assertAlmostEqual(celsius_to_fahrenheit(0), 32.0, places=1)
        
        # Test boiling point of water
        self.assertAlmostEqual(celsius_to_fahrenheit(100), 212.0, places=1)
        
        # Test room temperature
        self.assertAlmostEqual(celsius_to_fahrenheit(20), 68.0, places=1)
        
        # Test negative temperature
        self.assertAlmostEqual(celsius_to_fahrenheit(-40), -40.0, places=1)
        
        # Test body temperature
        self.assertAlmostEqual(celsius_to_fahrenheit(37), 98.6, places=1)
        
        # Test decimal values
        self.assertAlmostEqual(celsius_to_fahrenheit(25.5), 77.9, places=1)
        
        # Test zero
        self.assertAlmostEqual(celsius_to_fahrenheit(0.0), 32.0, places=1)
    
    def test_meters_per_second_to_miles_per_hour(self):
        """Test meters per second to miles per hour conversion."""
        # Test zero speed
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(0), 0.0, places=2)
        
        # Test 1 m/s
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(1), 2.23694, places=4)
        
        # Test 10 m/s (typical running speed)
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(10), 22.3694, places=3)
        
        # Test highway speed equivalent (30 m/s ≈ 67 mph)
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(30), 67.1082, places=3)
        
        # Test decimal values
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(5.5), 12.30317, places=4)
        
        # Test very small values
        self.assertAlmostEqual(meters_per_second_to_miles_per_hour(0.1), 0.223694, places=5)
    
    def test_lat_lon_to_tile_coordinates(self):
        """Test latitude/longitude to tile coordinates conversion."""
        # Test equator and prime meridian at zoom 0
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 0, 0)
        self.assertEqual(x_tile, 0)
        self.assertEqual(y_tile, 0)
        
        # Test at zoom level 1
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 0, 1)
        self.assertEqual(x_tile, 1)
        self.assertEqual(y_tile, 1)
        
        # Test at zoom level 2
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 0, 2)
        self.assertEqual(x_tile, 2)
        self.assertEqual(y_tile, 2)
        
        # Test with positive longitude
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 90, 1)
        self.assertEqual(x_tile, 1)  # 2 * ((90 + 180) / 360) = 2 * 0.75 = 1.5 -> 1
        self.assertEqual(y_tile, 1)
        
        # Test with negative longitude
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, -90, 1)
        self.assertEqual(x_tile, 0)  # 2 * ((-90 + 180) / 360) = 2 * 0.25 = 0.5 -> 0
        self.assertEqual(y_tile, 1)
        
        # Test with positive latitude (Northern hemisphere)
        x_tile, y_tile = lat_lon_to_tile_coordinates(45, 0, 1)
        self.assertEqual(x_tile, 1)
        self.assertEqual(y_tile, 0)  # Should be in upper half
        
        # Test with negative latitude (Southern hemisphere)
        x_tile, y_tile = lat_lon_to_tile_coordinates(-45, 0, 1)
        self.assertEqual(x_tile, 1)
        self.assertEqual(y_tile, 1)  # Should be in lower half
        
        # Test specific location (New York City) at zoom 10
        x_tile, y_tile = lat_lon_to_tile_coordinates(40.7128, -74.0060, 10)
        self.assertIsInstance(x_tile, int)
        self.assertIsInstance(y_tile, int)
        self.assertGreaterEqual(x_tile, 0)
        self.assertGreaterEqual(y_tile, 0)
        self.assertLess(x_tile, 2**10)  # Should be within valid range for zoom level
        self.assertLess(y_tile, 2**10)
        
        # Test edge cases - extreme coordinates
        # Test maximum longitude
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 180, 1)
        self.assertEqual(x_tile, 2)  # Should wrap to edge
        
        # Test minimum longitude
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, -180, 1)
        self.assertEqual(x_tile, 0)
        
        # Test high zoom level
        x_tile, y_tile = lat_lon_to_tile_coordinates(0, 0, 10)
        self.assertEqual(x_tile, 512)  # 2^10 / 2 = 512
        self.assertEqual(y_tile, 512)


if __name__ == '__main__':
    unittest.main()
