import requests
import hvac
import time
from typing import Optional, Dict, Any, List

from .logging_config import get_logger, APILogger, PerformanceLogger

# Get logger instance
logger = get_logger(__name__)
api_logger = APILogger()



def get_api_key_from_vault(secret_path: str, secret_key: str, vault_url: str, vault_token: str) -> str:
    """
    Retrieve the API key from HashiCorp Vault.

    Args:
        secret_path: The path to the secret in Vault.
        secret_key: The key within the secret to retrieve.
        vault_url: URL of the Vault instance.
        vault_token: Authentication token for Vault.

    Returns:
        The API key if found.
        
    Raises:
        RuntimeError: If unable to retrieve the API key.
        ValueError: If the key is not found in the secret.
    """
    with PerformanceLogger("vault_api_key_retrieval", logger):
        try:
            logger.info(f"Retrieving API key from Vault at path: {secret_path}")
            
            # Initialize the Vault client
            client = hvac.Client(url=vault_url, token=vault_token)

            # Read the secret from the specified path
            secret = client.secrets.kv.read_secret_version(
                path=secret_path, 
                raise_on_deleted_version=False
            )

            # Retrieve the API key from the secret
            api_key = secret['data']['data'].get(secret_key)

            if api_key:
                logger.info("API key successfully retrieved from Vault")
                return api_key
            else:
                error_msg = f"Key '{secret_key}' not found in Vault secret at path '{secret_path}'"
                logger.critical(error_msg)
                raise ValueError(error_msg)

        except Exception as e:
            error_msg = f"Failed to retrieve API key from Vault: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg)


def get_lat_lon(city: str, state: str, country: str, api_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get latitude and longitude coordinates for a city using OpenWeatherMap Geocoding API.
    
    Args:
        city: City name
        state: State/province name
        country: Country name
        api_key: OpenWeatherMap API key
        
    Returns:
        List of location data dictionaries, or None if not found
    """
    # Build query string
    query_parts = [part for part in [city, state, country] if part.strip()]
    query = ','.join(query_parts)
    
    url = f'https://api.openweathermap.org/geo/1.0/direct'
    params = {'q': query, 'appid': api_key, 'limit': 5}
    
    with PerformanceLogger(f"geocoding_api_call_{city}", logger):
        try:
            # Log the API request
            api_logger.log_request('GET', url, params)
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            # Log the API response
            api_logger.log_response(
                response.status_code, 
                response_time, 
                len(response.content) if response.content else 0
            )
            
            response.raise_for_status()
            city_data = response.json()
            
            if city_data:
                logger.info(f"Found {len(city_data)} location(s) for query: {query}")
                logger.debug(f"Location data: {city_data}")
                return city_data
            else:
                logger.warning(f"No locations found for query: {query}")
                return None
                
        except requests.exceptions.Timeout:
            error_msg = f"Timeout while fetching coordinates for {query}"
            logger.error(error_msg)
            api_logger.log_error(requests.exceptions.Timeout(error_msg), {'query': query})
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching coordinates for {query}: {e}"
            logger.error(error_msg)
            api_logger.log_error(e, {'query': query, 'url': url})
            return None


def get_weather(city_lat: float, city_lon: float, api_key: str) -> Optional[Dict[str, Any]]:
    """
    Get weather data for given coordinates using OpenWeatherMap One Call API.
    
    Args:
        city_lat: Latitude coordinate
        city_lon: Longitude coordinate
        api_key: OpenWeatherMap API key
        
    Returns:
        Weather data dictionary, or None if request fails
    """
    if city_lat is None or city_lon is None:
        logger.warning("Invalid coordinates provided for weather request")
        return None
    
    url = f'https://api.openweathermap.org/data/3.0/onecall'
    params = {
        'lat': city_lat,
        'lon': city_lon,
        'appid': api_key,
        'units': 'metric',
        'exclude': 'minutely,alerts'  # Exclude unnecessary data to reduce response size
    }
    
    with PerformanceLogger(f"weather_api_call_{city_lat}_{city_lon}", logger):
        try:
            # Log the API request
            api_logger.log_request('GET', url, params)
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=15)
            response_time = time.time() - start_time
            
            # Log the API response
            api_logger.log_response(
                response.status_code, 
                response_time, 
                len(response.content) if response.content else 0
            )
            
            response.raise_for_status()
            weather_data = response.json()
            
            logger.info(f"Successfully retrieved weather data for coordinates ({city_lat}, {city_lon})")
            logger.debug(f"Weather data keys: {list(weather_data.keys())}")
            
            return weather_data
            
        except requests.exceptions.Timeout:
            error_msg = f"Timeout while fetching weather data for coordinates ({city_lat}, {city_lon})"
            logger.error(error_msg)
            api_logger.log_error(requests.exceptions.Timeout(error_msg), {
                'lat': city_lat, 'lon': city_lon
            })
            return None
        except requests.exceptions.RequestException as e:
            error_msg = f"Error fetching weather data for coordinates ({city_lat}, {city_lon}): {e}"
            logger.error(error_msg)
            api_logger.log_error(e, {
                'lat': city_lat, 'lon': city_lon, 'url': url
            })
            return None
