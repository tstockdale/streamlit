"""
Weather Map Services Module

This module provides services for interacting with external APIs including:
- HashiCorp Vault for secure API key management
- OpenWeatherMap Geocoding API for location coordinates
- OpenWeatherMap One Call API for weather data

The module is designed with proper error handling, logging, and performance monitoring.
"""

import requests # type: ignore
import hvac  # type: ignore
import time
import toml  # type: ignore
import os
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
    
    def __init__(self, config: Optional[APIConfig] = None):
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
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        operation_name: Optional[str] = None
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
        Retrieve an API key from HashiCorp Vault with fallback to Streamlit secrets.

        Args:
            secret_path: The path to the secret in Vault
            secret_key: The key within the secret to retrieve
            vault_url: URL of the Vault instance
            vault_token: Authentication token for Vault

        Returns:
            The API key if found
            
        Raises:
            RuntimeError: If unable to retrieve the API key from either source
            ValueError: If the key is not found in either source
        """
        with PerformanceLogger("vault_api_key_retrieval", self.logger):
            # First, try to retrieve from Vault
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
                    self.logger.warning(f"Key '{secret_key}' not found in Vault secret at path '{secret_path}', trying fallback")

            except Exception as e:
                self.logger.warning(f"Failed to retrieve API key from Vault: {e}, trying fallback")

            # Fallback: try to read from Streamlit secrets file
            try:
                self.logger.info("Attempting to retrieve API key from Streamlit secrets file")
                secrets_path = ".streamlit/secrets.toml"
                
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'r') as f:
                        secrets_data = toml.load(f)
                    
                    api_key = secrets_data.get('SECRET_KEY_VALUE')
                    
                    if api_key:
                        self.logger.info("API key successfully retrieved from Streamlit secrets file")
                        return api_key
                    else:
                        self.logger.error("SECRET_KEY_VALUE not found in Streamlit secrets file")
                else:
                    self.logger.error(f"Streamlit secrets file not found at: {secrets_path}")
                    
            except Exception as e:
                self.logger.error(f"Failed to read from Streamlit secrets file: {e}")

            # If both methods fail, raise an error
            error_msg = f"Failed to retrieve API key from both Vault (path: '{secret_path}', key: '{secret_key}') and Streamlit secrets file"
            self.logger.critical(error_msg)
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
        exclude: Optional[List[str]] = None
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
    def create_geocoding_service(config: Optional[APIConfig] = None) -> GeocodingService:
        """Create a geocoding service instance."""
        return GeocodingService(config or APIConfig())
    
    @staticmethod
    def create_weather_service(config: Optional[APIConfig] = None) -> WeatherService:
        """Create a weather service instance."""
        return WeatherService(config or APIConfig())
