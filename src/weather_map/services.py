"""
Weather Map Services Module

This module provides services for interacting with external APIs including:
- HashiCorp Vault for secure API key management
- OpenWeatherMap Geocoding API for location coordinates
- OpenWeatherMap One Call API for weather data

The module is designed with proper error handling, logging, and performance monitoring.
"""

import requests
import hvac
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Union
from enum import Enum

from .logging_config import get_logger, APILogger, PerformanceLogger


# Configuration and Constants
@dataclass
class APIConfig:
    """Configuration for API services."""
    geocoding_base_url: str = "https://api.openweathermap.org/geo/1.0"
    weather_base_url: str = "https://api.openweathermap.org/data/3.0"
    default_timeout: int = 10
    weather_timeout: int = 15
    max_retries: int = 3
    retry_delay: float = 1.0


class APIError(Exception):
    """Base exception for API-related errors."""
    pass


class VaultError(APIError):
    """Exception for Vault-related errors."""
    pass


class GeocodeError(APIError):
    """Exception for geocoding-related errors."""
    pass


class WeatherError(APIError):
    """Exception for weather API-related errors."""
    pass


# Base Service Class
class BaseAPIService(ABC):
    """Base class for API services with common functionality."""
    
    def __init__(self, config: APIConfig = None):
        """
        Initialize the base API service.
        
        Args:
            config: API configuration object
        """
        self.config = config or APIConfig()
        self.logger = get_logger(self.__class__.__module__)
        self.api_logger = APILogger()
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        params: Dict[str, Any] = None,
        timeout: int = None,
        operation_name: str = None
    ) -> Optional[requests.Response]:
        """
        Make an HTTP request with proper logging and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            params: Request parameters
            timeout: Request timeout in seconds
            operation_name: Name for performance logging
            
        Returns:
            Response object or None if request fails
            
        Raises:
            APIError: If request fails after retries
        """
        timeout = timeout or self.config.default_timeout
        operation_name = operation_name or f"{method.lower()}_request"
        
        with PerformanceLogger(operation_name, self.logger):
            for attempt in range(self.config.max_retries):
                try:
                    # Log the API request
                    self.api_logger.log_request(method, url, params)
                    
                    start_time = time.time()
                    response = requests.request(
                        method=method,
                        url=url,
                        params=params,
                        timeout=timeout
                    )
                    response_time = time.time() - start_time
                    
                    # Log the API response
                    self.api_logger.log_response(
                        response.status_code,
                        response_time,
                        len(response.content) if response.content else 0
                    )
                    
                    response.raise_for_status()
                    return response
                    
                except requests.exceptions.Timeout as e:
                    error_msg = f"Timeout on attempt {attempt + 1}/{self.config.max_retries}: {e}"
                    self.logger.warning(error_msg)
                    if attempt == self.config.max_retries - 1:
                        self.api_logger.log_error(e, {'url': url, 'params': params})
                        raise APIError(f"Request timed out after {self.config.max_retries} attempts")
                        
                except requests.exceptions.RequestException as e:
                    error_msg = f"Request failed on attempt {attempt + 1}/{self.config.max_retries}: {e}"
                    self.logger.warning(error_msg)
                    if attempt == self.config.max_retries - 1:
                        self.api_logger.log_error(e, {'url': url, 'params': params})
                        raise APIError(f"Request failed after {self.config.max_retries} attempts: {e}")
                
                # Wait before retry
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay * (attempt + 1))
        
        return None


# Vault Service
class VaultService:
    """Service for interacting with HashiCorp Vault."""
    
    def __init__(self):
        """Initialize the Vault service."""
        self.logger = get_logger(__name__)
    
    def get_api_key(
        self, 
        secret_path: str, 
        secret_key: str, 
        vault_url: str, 
        vault_token: str
    ) -> str:
        """
        Retrieve an API key from HashiCorp Vault.

        Args:
            secret_path: The path to the secret in Vault
            secret_key: The key within the secret to retrieve
            vault_url: URL of the Vault instance
            vault_token: Authentication token for Vault

        Returns:
            The API key if found
            
        Raises:
            RuntimeError: If unable to retrieve the API key
            ValueError: If the key is not found in the secret
        """
        with PerformanceLogger("vault_api_key_retrieval", self.logger):
            try:
                self.logger.info(f"Retrieving API key from Vault at path: {secret_path}")
                
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
                    self.logger.info("API key successfully retrieved from Vault")
                    return api_key
                else:
                    error_msg = f"Key '{secret_key}' not found in Vault secret at path '{secret_path}'"
                    self.logger.critical(error_msg)
                    raise ValueError(error_msg)

            except ValueError:
                # Re-raise ValueError as-is for backward compatibility
                raise
            except Exception as e:
                error_msg = f"Failed to retrieve API key from Vault: {e}"
                self.logger.error(error_msg, exc_info=True)
                raise RuntimeError(error_msg)


# Geocoding Service
class GeocodingService(BaseAPIService):
    """Service for geocoding operations using OpenWeatherMap API."""
    
    def get_coordinates(
        self, 
        city: str, 
        state: str = "", 
        country: str = "", 
        api_key: str = "",
        limit: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get latitude and longitude coordinates for a location.
        
        Args:
            city: City name
            state: State/province name (optional)
            country: Country name (optional)
            api_key: OpenWeatherMap API key
            limit: Maximum number of results to return
            
        Returns:
            List of location data dictionaries, or None if not found
            
        Raises:
            GeocodeError: If geocoding request fails
        """
        if not city.strip():
            raise GeocodeError("City name is required for geocoding")
        
        if not api_key.strip():
            raise GeocodeError("API key is required for geocoding")
        
        # Build query string
        query_parts = [part.strip() for part in [city, state, country] if part.strip()]
        query = ','.join(query_parts)
        
        url = f"{self.config.geocoding_base_url}/direct"
        params = {
            'q': query, 
            'appid': api_key, 
            'limit': min(limit, 10)  # Cap at 10 for API limits
        }
        
        try:
            response = self._make_request(
                'GET', 
                url, 
                params, 
                self.config.default_timeout,
                f"geocoding_{city}"
            )
            
            if response is None:
                return None
            
            city_data = response.json()
            
            if city_data:
                self.logger.info(f"Found {len(city_data)} location(s) for query: {query}")
                self.logger.debug(f"Location data: {city_data}")
                return city_data
            else:
                self.logger.warning(f"No locations found for query: {query}")
                return None
                
        except APIError as e:
            self.logger.error(f"Geocoding failed for query '{query}': {e}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error during geocoding for '{query}': {e}"
            self.logger.error(error_msg, exc_info=True)
            raise GeocodeError(error_msg)


# Weather Service
class WeatherService(BaseAPIService):
    """Service for weather data operations using OpenWeatherMap API."""
    
    def get_weather_data(
        self, 
        latitude: float, 
        longitude: float, 
        api_key: str,
        units: str = "metric",
        exclude: List[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get weather data for given coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            api_key: OpenWeatherMap API key
            units: Temperature units (metric, imperial, kelvin)
            exclude: List of data blocks to exclude
            
        Returns:
            Weather data dictionary, or None if request fails
            
        Raises:
            WeatherError: If weather request fails
        """
        # Validate inputs
        if latitude is None or longitude is None:
            raise WeatherError("Valid latitude and longitude coordinates are required")
        
        if not api_key.strip():
            raise WeatherError("API key is required for weather data")
        
        if not (-90 <= latitude <= 90):
            raise WeatherError(f"Invalid latitude: {latitude}. Must be between -90 and 90")
        
        if not (-180 <= longitude <= 180):
            raise WeatherError(f"Invalid longitude: {longitude}. Must be between -180 and 180")
        
        # Set default exclusions to reduce response size
        if exclude is None:
            exclude = ['minutely', 'alerts']
        
        url = f"{self.config.weather_base_url}/onecall"
        params = {
            'lat': latitude,
            'lon': longitude,
            'appid': api_key,
            'units': units,
            'exclude': ','.join(exclude)
        }
        
        try:
            response = self._make_request(
                'GET',
                url,
                params,
                self.config.weather_timeout,
                f"weather_{latitude}_{longitude}"
            )
            
            if response is None:
                return None
            
            weather_data = response.json()
            
            self.logger.info(f"Successfully retrieved weather data for coordinates ({latitude}, {longitude})")
            self.logger.debug(f"Weather data keys: {list(weather_data.keys())}")
            
            return weather_data
            
        except APIError as e:
            self.logger.error(f"Weather request failed for coordinates ({latitude}, {longitude}): {e}")
            return None
        except Exception as e:
            error_msg = f"Unexpected error retrieving weather data for ({latitude}, {longitude}): {e}"
            self.logger.error(error_msg, exc_info=True)
            raise WeatherError(error_msg)


# Service Factory
class WeatherServiceFactory:
    """Factory for creating weather-related services."""
    
    @staticmethod
    def create_vault_service() -> VaultService:
        """Create a Vault service instance."""
        return VaultService()
    
    @staticmethod
    def create_geocoding_service(config: APIConfig = None) -> GeocodingService:
        """Create a geocoding service instance."""
        return GeocodingService(config)
    
    @staticmethod
    def create_weather_service(config: APIConfig = None) -> WeatherService:
        """Create a weather service instance."""
        return WeatherService(config)


# Backward compatibility functions (maintain existing API)
def get_api_key_from_vault(secret_path: str, secret_key: str, vault_url: str, vault_token: str) -> str:
    """
    Retrieve the API key from HashiCorp Vault.
    
    This function maintains backward compatibility with the existing API.
    """
    vault_service = WeatherServiceFactory.create_vault_service()
    return vault_service.get_api_key(secret_path, secret_key, vault_url, vault_token)


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
    
    logger = get_logger(__name__)
    api_logger = APILogger()
    
    with PerformanceLogger(f"geocoding_api_call_{city}", logger):
        try:
            # Log the API request
            api_logger.log_request('GET', url, params)
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=10)
            response_time = time.time() - start_time
            
            # Log the API response
            try:
                content_length = len(response.content) if hasattr(response, 'content') and response.content else 0
            except (TypeError, AttributeError):
                content_length = 0
            
            api_logger.log_response(
                response.status_code, 
                response_time, 
                content_length
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
        logger = get_logger(__name__)
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
    
    logger = get_logger(__name__)
    api_logger = APILogger()
    
    with PerformanceLogger(f"weather_api_call_{city_lat}_{city_lon}", logger):
        try:
            # Log the API request
            api_logger.log_request('GET', url, params)
            
            start_time = time.time()
            response = requests.get(url, params=params, timeout=15)
            response_time = time.time() - start_time
            
            # Log the API response
            try:
                content_length = len(response.content) if hasattr(response, 'content') and response.content else 0
            except (TypeError, AttributeError):
                content_length = 0
            
            api_logger.log_response(
                response.status_code, 
                response_time, 
                content_length
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
