import unittest
from unittest.mock import patch, Mock, MagicMock, mock_open
import requests
import hvac #type: ignore
import os
from src.weather_map.services import (
    WeatherServiceFactory, 
    VaultService, 
    GeocodingService, 
    WeatherService,
    WeatherError,
    GeocodeError,
    VaultError
)


class TestVaultService(unittest.TestCase):
    """Test cases for VaultService using the service factory pattern."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.vault_service = WeatherServiceFactory.create_vault_service()
    
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_success_from_vault(self, mock_hvac_client):
        """Test successful API key retrieval from Vault."""
        # Mock the Vault client and response
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.secrets.kv.read_secret_version.return_value = {
            'data': {'data': {'api_key': 'test_api_key_123'}}
        }
        
        result = self.vault_service.get_api_key(
            'test/path', 'api_key', 'https://vault.example.com', 'test_token'
        )
        
        self.assertEqual(result, 'test_api_key_123')
        mock_hvac_client.assert_called_once_with(
            url='https://vault.example.com', 
            token='test_token'
        )
    
    @patch('src.weather_map.services.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='SECRET_KEY_VALUE = "fallback_api_key_456"')
    @patch('src.weather_map.services.toml.load')
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_vault_not_found_fallback_success(self, mock_hvac_client, mock_toml_load, mock_file, mock_exists):
        """Test API key retrieval when key is not found in Vault but found in secrets file."""
        # Mock Vault failure (key not found)
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.secrets.kv.read_secret_version.return_value = {
            'data': {'data': {'other_key': 'other_value'}}
        }
        
        # Mock secrets file exists and contains the key
        mock_exists.return_value = True
        mock_toml_load.return_value = {'SECRET_KEY_VALUE': 'fallback_api_key_456'}
        
        result = self.vault_service.get_api_key(
            'test/path', 'api_key', 'https://vault.example.com', 'test_token'
        )
        
        self.assertEqual(result, 'fallback_api_key_456')
        # Check that exists was called with the secrets file path (among other calls)
        mock_exists.assert_any_call('.streamlit/secrets.toml')
        mock_toml_load.assert_called_once()
    
    @patch('src.weather_map.services.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='SECRET_KEY_VALUE = "fallback_api_key_789"')
    @patch('src.weather_map.services.toml.load')
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_vault_connection_error_fallback_success(self, mock_hvac_client, mock_toml_load, mock_file, mock_exists):
        """Test API key retrieval when Vault connection fails but secrets file works."""
        # Mock Vault connection failure
        mock_hvac_client.side_effect = Exception("Connection failed")
        
        # Mock secrets file exists and contains the key
        mock_exists.return_value = True
        mock_toml_load.return_value = {'SECRET_KEY_VALUE': 'fallback_api_key_789'}
        
        result = self.vault_service.get_api_key(
            'test/path', 'api_key', 'https://vault.example.com', 'test_token'
        )
        
        self.assertEqual(result, 'fallback_api_key_789')
        # Check that exists was called with the secrets file path (among other calls)
        mock_exists.assert_any_call('.streamlit/secrets.toml')
        mock_toml_load.assert_called_once()
    
    @patch('src.weather_map.services.os.path.exists')
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_vault_fails_secrets_file_not_found(self, mock_hvac_client, mock_exists):
        """Test API key retrieval when both Vault and secrets file fail."""
        # Mock Vault connection failure
        mock_hvac_client.side_effect = Exception("Connection failed")
        
        # Mock secrets file doesn't exist
        def exists_side_effect(path):
            if path == '.streamlit/secrets.toml':
                return False
            return True  # Return True for other paths (like log files)
        
        mock_exists.side_effect = exists_side_effect
        
        with self.assertRaises(RuntimeError) as context:
            self.vault_service.get_api_key(
                'test/path', 'api_key', 'https://vault.example.com', 'test_token'
            )
        
        self.assertIn("Failed to retrieve API key from both Vault", str(context.exception))
        # Check that exists was called with the secrets file path (among other calls)
        mock_exists.assert_any_call('.streamlit/secrets.toml')
    
    @patch('src.weather_map.services.os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data='OTHER_KEY = "other_value"')
    @patch('src.weather_map.services.toml.load')
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_vault_fails_secrets_key_not_found(self, mock_hvac_client, mock_toml_load, mock_file, mock_exists):
        """Test API key retrieval when Vault fails and secrets file doesn't contain the key."""
        # Mock Vault connection failure
        mock_hvac_client.side_effect = Exception("Connection failed")
        
        # Mock secrets file exists but doesn't contain SECRET_KEY_VALUE
        mock_exists.return_value = True
        mock_toml_load.return_value = {'OTHER_KEY': 'other_value'}
        
        with self.assertRaises(RuntimeError) as context:
            self.vault_service.get_api_key(
                'test/path', 'api_key', 'https://vault.example.com', 'test_token'
            )
        
        self.assertIn("Failed to retrieve API key from both Vault", str(context.exception))
        # Check that exists was called with the secrets file path (among other calls)
        mock_exists.assert_any_call('.streamlit/secrets.toml')
        mock_toml_load.assert_called_once()
    
    @patch('src.weather_map.services.os.path.exists')
    @patch('builtins.open', side_effect=IOError("File read error"))
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_vault_fails_secrets_file_read_error(self, mock_hvac_client, mock_file, mock_exists):
        """Test API key retrieval when Vault fails and secrets file has read error."""
        # Mock Vault connection failure
        mock_hvac_client.side_effect = Exception("Connection failed")
        
        # Mock secrets file exists but can't be read
        mock_exists.return_value = True
        
        with self.assertRaises(RuntimeError) as context:
            self.vault_service.get_api_key(
                'test/path', 'api_key', 'https://vault.example.com', 'test_token'
            )
        
        self.assertIn("Failed to retrieve API key from both Vault", str(context.exception))
        # Check that exists was called with the secrets file path (among other calls)
        mock_exists.assert_any_call('.streamlit/secrets.toml')


class TestGeocodingService(unittest.TestCase):
    """Test cases for GeocodingService using the service factory pattern."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.geocoding_service = WeatherServiceFactory.create_geocoding_service()
    
    @patch('src.weather_map.services.requests.request')
    def test_get_coordinates_success(self, mock_request):
        """Test successful geocoding API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'country': 'US'}
        ]
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'{"result": "success"}'
        mock_request.return_value = mock_response
        
        result = self.geocoding_service.get_coordinates('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'New York')
        self.assertEqual(result[0]['lat'], 40.7128)
        self.assertEqual(result[0]['lon'], -74.0060)
    
    @patch('src.weather_map.services.requests.request')
    def test_get_coordinates_no_results(self, mock_request):
        """Test geocoding API call with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'[]'
        mock_request.return_value = mock_response
        
        result = self.geocoding_service.get_coordinates('NonexistentCity', '', '', 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.request')
    def test_get_coordinates_timeout(self, mock_request):
        """Test geocoding API call timeout."""
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = self.geocoding_service.get_coordinates('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.request')
    def test_get_coordinates_request_exception(self, mock_request):
        """Test geocoding API call with request exception."""
        mock_request.side_effect = requests.exceptions.RequestException("Network error")
        
        result = self.geocoding_service.get_coordinates('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNone(result)
    
    def test_get_coordinates_empty_city(self):
        """Test geocoding with empty city name."""
        with self.assertRaises(GeocodeError) as context:
            self.geocoding_service.get_coordinates('', 'NY', 'US', 'test_api_key')
        
        self.assertIn("City name is required", str(context.exception))
    
    def test_get_coordinates_empty_api_key(self):
        """Test geocoding with empty API key."""
        with self.assertRaises(GeocodeError) as context:
            self.geocoding_service.get_coordinates('New York', 'NY', 'US', '')
        
        self.assertIn("API key is required", str(context.exception))


class TestWeatherService(unittest.TestCase):
    """Test cases for WeatherService using the service factory pattern."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.weather_service = WeatherServiceFactory.create_weather_service()
    
    @patch('src.weather_map.services.requests.request')
    def test_get_weather_data_success(self, mock_request):
        """Test successful weather API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current': {'temp': 20.5, 'humidity': 65},
            'hourly': [{'temp': 19.0, 'dt': 1609459200}]
        }
        mock_response.raise_for_status.return_value = None
        mock_response.content = b'{"result": "success"}'
        mock_request.return_value = mock_response
        
        result = self.weather_service.get_weather_data(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNotNone(result)
        self.assertIn('current', result)
        self.assertIn('hourly', result)
        self.assertEqual(result['current']['temp'], 20.5)
    
    def test_get_weather_data_invalid_coordinates(self):
        """Test weather API call with invalid coordinates."""
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(None, -74.0060, 'test_api_key')
        
        self.assertIn("Valid latitude and longitude coordinates are required", str(context.exception))
        
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(40.7128, None, 'test_api_key')
        
        self.assertIn("Valid latitude and longitude coordinates are required", str(context.exception))
    
    def test_get_weather_data_invalid_latitude_range(self):
        """Test weather API call with latitude out of range."""
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(91.0, -74.0060, 'test_api_key')
        
        self.assertIn("Invalid latitude", str(context.exception))
        
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(-91.0, -74.0060, 'test_api_key')
        
        self.assertIn("Invalid latitude", str(context.exception))
    
    def test_get_weather_data_invalid_longitude_range(self):
        """Test weather API call with longitude out of range."""
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(40.7128, 181.0, 'test_api_key')
        
        self.assertIn("Invalid longitude", str(context.exception))
        
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(40.7128, -181.0, 'test_api_key')
        
        self.assertIn("Invalid longitude", str(context.exception))
    
    def test_get_weather_data_empty_api_key(self):
        """Test weather API call with empty API key."""
        with self.assertRaises(WeatherError) as context:
            self.weather_service.get_weather_data(40.7128, -74.0060, '')
        
        self.assertIn("API key is required", str(context.exception))
    
    @patch('src.weather_map.services.requests.request')
    def test_get_weather_data_timeout(self, mock_request):
        """Test weather API call timeout."""
        mock_request.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = self.weather_service.get_weather_data(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.request')
    def test_get_weather_data_request_exception(self, mock_request):
        """Test weather API call with request exception."""
        mock_request.side_effect = requests.exceptions.RequestException("Network error")
        
        result = self.weather_service.get_weather_data(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNone(result)


class TestWeatherServiceFactory(unittest.TestCase):
    """Test cases for WeatherServiceFactory."""
    
    def test_create_vault_service(self):
        """Test creating a VaultService instance."""
        service = WeatherServiceFactory.create_vault_service()
        self.assertIsInstance(service, VaultService)
    
    def test_create_geocoding_service(self):
        """Test creating a GeocodingService instance."""
        service = WeatherServiceFactory.create_geocoding_service()
        self.assertIsInstance(service, GeocodingService)
    
    def test_create_weather_service(self):
        """Test creating a WeatherService instance."""
        service = WeatherServiceFactory.create_weather_service()
        self.assertIsInstance(service, WeatherService)


if __name__ == '__main__':
    unittest.main()
