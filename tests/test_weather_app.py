import unittest
from unittest.mock import patch, Mock, MagicMock
import pandas as pd
from src.weather_map.weather_app import WeatherApp


class TestWeatherApp(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        with patch('src.weather_map.weather_app.services.get_api_key_from_vault'):
            self.app = WeatherApp()
            self.app.api_key = 'test_api_key'
    
    def test_parse_city_input_full_format(self):
        """Test parsing city input with city, state, and country."""
        result = self.app.parse_city_input("New York, NY, US")
        self.assertEqual(result, ("New York", "NY", "US"))
    
    def test_parse_city_input_city_state_only(self):
        """Test parsing city input with city and state only."""
        result = self.app.parse_city_input("Los Angeles, CA")
        self.assertEqual(result, ("Los Angeles", "CA", ""))
    
    def test_parse_city_input_city_only(self):
        """Test parsing city input with city only."""
        result = self.app.parse_city_input("London")
        self.assertEqual(result, ("London", "", ""))
    
    def test_parse_city_input_empty_string(self):
        """Test parsing empty city input."""
        result = self.app.parse_city_input("")
        self.assertEqual(result, ("", "", ""))
        
        result = self.app.parse_city_input("   ")
        self.assertEqual(result, ("", "", ""))
    
    def test_parse_city_input_with_spaces(self):
        """Test parsing city input with extra spaces."""
        result = self.app.parse_city_input(" New York , NY , US ")
        self.assertEqual(result, ("New York", "NY", "US"))
    
    def test_parse_city_input_with_empty_components(self):
        """Test parsing city input with empty state/country."""
        result = self.app.parse_city_input("London, , UK")
        self.assertEqual(result, ("London", "", "UK"))
    
    def test_format_city_info_string_full_info(self):
        """Test formatting city info string with all components."""
        city_data = {
            'name': 'New York',
            'state': 'NY',
            'country': 'US'
        }
        result = self.app.format_city_info_string(city_data)
        self.assertEqual(result, "Current weather in New York, NY, US")
    
    def test_format_city_info_string_no_state(self):
        """Test formatting city info string without state."""
        city_data = {
            'name': 'London',
            'country': 'GB'
        }
        result = self.app.format_city_info_string(city_data)
        self.assertEqual(result, "Current weather in London, GB")
    
    def test_format_city_info_string_name_only(self):
        """Test formatting city info string with name only."""
        city_data = {'name': 'Tokyo'}
        result = self.app.format_city_info_string(city_data)
        self.assertEqual(result, "Current weather in Tokyo")
    
    def test_create_hourly_forecast_table_success(self):
        """Test creating hourly forecast table with valid data."""
        weather_data = {
            'timezone': 'UTC',
            'hourly': [
                {
                    'dt': 1609459200,  # 2021-01-01 00:00:00 UTC
                    'temp': 20.5,
                    'feels_like': 18.0,
                    'humidity': 65,
                    'wind_speed': 5.2,
                    'rain': {'1h': 0.5},
                    'weather': [{'description': 'light rain'}]
                },
                {
                    'dt': 1609462800,  # 2021-01-01 01:00:00 UTC
                    'temp': 19.8,
                    'feels_like': 17.5,
                    'humidity': 70,
                    'wind_speed': 4.8,
                    'weather': [{'description': 'cloudy'}]
                }
            ]
        }
        
        result = self.app.create_hourly_forecast_table(weather_data)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 2)
        self.assertIn('Time', result.columns)
        self.assertIn('Temp (°F)', result.columns)
        self.assertIn('Feels Like (°F)', result.columns)
        self.assertIn('One Hour Rain (mm)', result.columns)
        self.assertIn('Humidity (%)', result.columns)
        self.assertIn('Wind Speed (mi/h)', result.columns)
        self.assertIn('Description', result.columns)
        
        # Check first row values
        self.assertEqual(result.iloc[0]['Humidity (%)'], 65)
        self.assertEqual(result.iloc[0]['One Hour Rain (mm)'], 0.5)
        self.assertEqual(result.iloc[0]['Description'], 'Light rain')
        
        # Check second row (no rain data)
        self.assertIsNone(result.iloc[1]['One Hour Rain (mm)'])
        self.assertEqual(result.iloc[1]['Description'], 'Cloudy')
    
    def test_create_hourly_forecast_table_no_hourly_data(self):
        """Test creating hourly forecast table with no hourly data."""
        weather_data = {'timezone': 'UTC'}
        result = self.app.create_hourly_forecast_table(weather_data)
        self.assertIsNone(result)
        
        weather_data = {'timezone': 'UTC', 'hourly': []}
        result = self.app.create_hourly_forecast_table(weather_data)
        self.assertIsNone(result)
    
    def test_create_hourly_forecast_table_missing_fields(self):
        """Test creating hourly forecast table with missing fields."""
        weather_data = {
            'timezone': 'UTC',
            'hourly': [
                {
                    'dt': 1609459200,
                    # Missing temp, feels_like, etc.
                    'humidity': 65
                }
            ]
        }
        
        result = self.app.create_hourly_forecast_table(weather_data)
        
        self.assertIsInstance(result, pd.DataFrame)
        self.assertEqual(len(result), 1)
        self.assertIsNone(result.iloc[0]['Temp (°F)'])
        self.assertIsNone(result.iloc[0]['Feels Like (°F)'])
        self.assertEqual(result.iloc[0]['Humidity (%)'], 65)
    
    @patch('src.weather_map.weather_app.services.get_lat_lon')
    @patch('src.weather_map.weather_app.services.get_weather')
    def test_process_city_weather_success(self, mock_get_weather, mock_get_lat_lon):
        """Test successful city weather processing."""
        # Mock the API responses
        mock_get_lat_lon.return_value = [
            {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'country': 'US'}
        ]
        mock_get_weather.return_value = {
            'current': {'temp': 20.5, 'humidity': 65},
            'timezone': 'America/New_York'
        }
        
        # Mock Streamlit columns
        mock_map_column = Mock()
        mock_weather_column = Mock()
        
        with patch.object(self.app, 'create_weather_map'), \
             patch.object(self.app, 'display_current_weather'):
            
            result = self.app._process_city_weather(
                'New York', 'NY', 'US', 'Streets', 
                mock_map_column, mock_weather_column
            )
        
        self.assertIsNotNone(result)
        self.assertIn('current', result)
        self.assertEqual(result['current']['temp'], 20.5)
        mock_get_lat_lon.assert_called_once_with('New York', 'NY', 'US', 'test_api_key')
        mock_get_weather.assert_called_once_with(40.7128, -74.0060, 'test_api_key')
    
    @patch('src.weather_map.weather_app.services.get_lat_lon')
    def test_process_city_weather_city_not_found(self, mock_get_lat_lon):
        """Test city weather processing when city is not found."""
        mock_get_lat_lon.return_value = None
        
        mock_map_column = Mock()
        mock_weather_column = Mock()
        
        result = self.app._process_city_weather(
            'NonexistentCity', '', '', 'Streets',
            mock_map_column, mock_weather_column
        )
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.weather_app.services.get_lat_lon')
    @patch('src.weather_map.weather_app.services.get_weather')
    def test_process_city_weather_weather_api_failure(self, mock_get_weather, mock_get_lat_lon):
        """Test city weather processing when weather API fails."""
        mock_get_lat_lon.return_value = [
            {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'country': 'US'}
        ]
        mock_get_weather.return_value = None
        
        mock_map_column = Mock()
        mock_weather_column = Mock()
        
        with patch.object(self.app, 'create_weather_map'):
            result = self.app._process_city_weather(
                'New York', 'NY', 'US', 'Streets',
                mock_map_column, mock_weather_column
            )
        
        self.assertIsNone(result)


class TestWeatherAppIntegration(unittest.TestCase):
    """Integration tests for WeatherApp that test component interactions."""
    
    @patch('src.weather_map.weather_app.services.get_api_key_from_vault')
    def test_initialization_with_vault_success(self, mock_get_api_key):
        """Test WeatherApp initialization with successful Vault connection."""
        mock_get_api_key.return_value = 'test_api_key_123'
        
        app = WeatherApp()
        
        self.assertEqual(app.api_key, 'test_api_key_123')
        mock_get_api_key.assert_called_once()
    
    @patch('src.weather_map.weather_app.services.get_api_key_from_vault')
    def test_initialization_with_vault_failure(self, mock_get_api_key):
        """Test WeatherApp initialization with Vault connection failure."""
        mock_get_api_key.side_effect = RuntimeError("Vault connection failed")
        
        app = WeatherApp()
        
        self.assertIsNone(app.api_key)
    
    def test_end_to_end_data_flow(self):
        """Test the complete data flow from input parsing to table creation."""
        with patch('src.weather_map.weather_app.services.get_api_key_from_vault'):
            app = WeatherApp()
            app.api_key = 'test_api_key'
        
        # Test input parsing
        city, state, country = app.parse_city_input("New York, NY, US")
        self.assertEqual((city, state, country), ("New York", "NY", "US"))
        
        # Test city info formatting
        city_data = {'name': city, 'state': state, 'country': country}
        city_info = app.format_city_info_string(city_data)
        self.assertEqual(city_info, "Current weather in New York, NY, US")
        
        # Test hourly forecast table creation
        weather_data = {
            'timezone': 'America/New_York',
            'hourly': [
                {
                    'dt': 1609459200,
                    'temp': 20.5,
                    'feels_like': 18.0,
                    'humidity': 65,
                    'wind_speed': 5.2,
                    'weather': [{'description': 'clear sky'}]
                }
            ]
        }
        
        df = app.create_hourly_forecast_table(weather_data)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertIn('Time', df.columns)


if __name__ == '__main__':
    unittest.main()
