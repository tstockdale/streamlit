import unittest
from unittest.mock import patch, Mock, MagicMock
import requests
import hvac
from src.weather_map.services import get_api_key_from_vault, get_lat_lon, get_weather


class TestServices(unittest.TestCase):
    
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_from_vault_success(self, mock_hvac_client):
        """Test successful API key retrieval from Vault."""
        # Mock the Vault client and response
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.secrets.kv.read_secret_version.return_value = {
            'data': {'data': {'api_key': 'test_api_key_123'}}
        }
        
        result = get_api_key_from_vault(
            'test/path', 'api_key', 'https://vault.example.com', 'test_token'
        )
        
        self.assertEqual(result, 'test_api_key_123')
        mock_hvac_client.assert_called_once_with(
            url='https://vault.example.com', 
            token='test_token'
        )
    
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_from_vault_key_not_found(self, mock_hvac_client):
        """Test API key retrieval when key is not found in Vault."""
        mock_client = Mock()
        mock_hvac_client.return_value = mock_client
        mock_client.secrets.kv.read_secret_version.return_value = {
            'data': {'data': {'other_key': 'other_value'}}
        }
        
        with self.assertRaises(ValueError) as context:
            get_api_key_from_vault(
                'test/path', 'api_key', 'https://vault.example.com', 'test_token'
            )
        
        self.assertIn("Key 'api_key' not found", str(context.exception))
    
    @patch('src.weather_map.services.hvac.Client')
    def test_get_api_key_from_vault_connection_error(self, mock_hvac_client):
        """Test API key retrieval when Vault connection fails."""
        mock_hvac_client.side_effect = Exception("Connection failed")
        
        with self.assertRaises(RuntimeError) as context:
            get_api_key_from_vault(
                'test/path', 'api_key', 'https://vault.example.com', 'test_token'
            )
        
        self.assertIn("Failed to retrieve API key from Vault", str(context.exception))
    
    @patch('src.weather_map.services.requests.get')
    def test_get_lat_lon_success(self, mock_get):
        """Test successful geocoding API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {'name': 'New York', 'lat': 40.7128, 'lon': -74.0060, 'country': 'US'}
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_lat_lon('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['name'], 'New York')
        self.assertEqual(result[0]['lat'], 40.7128)
        self.assertEqual(result[0]['lon'], -74.0060)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_lat_lon_no_results(self, mock_get):
        """Test geocoding API call with no results."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_lat_lon('NonexistentCity', '', '', 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_lat_lon_timeout(self, mock_get):
        """Test geocoding API call timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = get_lat_lon('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_lat_lon_request_exception(self, mock_get):
        """Test geocoding API call with request exception."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result = get_lat_lon('New York', 'NY', 'US', 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_weather_success(self, mock_get):
        """Test successful weather API call."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'current': {'temp': 20.5, 'humidity': 65},
            'hourly': [{'temp': 19.0, 'dt': 1609459200}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_weather(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNotNone(result)
        self.assertIn('current', result)
        self.assertIn('hourly', result)
        self.assertEqual(result['current']['temp'], 20.5)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_weather_invalid_coordinates(self, mock_get):
        """Test weather API call with invalid coordinates."""
        result = get_weather(None, -74.0060, 'test_api_key')
        self.assertIsNone(result)
        
        result = get_weather(40.7128, None, 'test_api_key')
        self.assertIsNone(result)
        
        # Ensure no API call was made
        mock_get.assert_not_called()
    
    @patch('src.weather_map.services.requests.get')
    def test_get_weather_timeout(self, mock_get):
        """Test weather API call timeout."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        
        result = get_weather(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNone(result)
    
    @patch('src.weather_map.services.requests.get')
    def test_get_weather_request_exception(self, mock_get):
        """Test weather API call with request exception."""
        mock_get.side_effect = requests.exceptions.RequestException("Network error")
        
        result = get_weather(40.7128, -74.0060, 'test_api_key')
        
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
