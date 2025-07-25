"""
WeatherApp class - Main application logic for the World Cities Weather Map.
"""

import streamlit as st
import os
import pandas as pd
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium # type: ignore
from typing import Optional, Dict, Any, Tuple

from . import services
from .utils import (
    unix_to_datetime,
    uvi_to_risk_string,
    celsius_to_fahrenheit,
    meters_per_second_to_miles_per_hour,
    lat_lon_to_tile_coordinates
)
from .services import (
    WeatherServiceFactory
)

from .logging_config import setup_logging, get_logger, PerformanceLogger

# Constants
DEFAULT_ZOOM_LEVEL = 10
MAP_WIDTH = 350
MAP_HEIGHT = 500

# Available weather layers
WEATHER_LAYERS = {
    'precipitation_new': 'Precipitation',
    'temp_new': 'Temperature',
    'clouds_new': 'Clouds',
    'wind_new': 'Wind Speed',
    'pressure_new': 'Pressure'
}


class WeatherApp:
    """Main weather application class."""
    
    def __init__(self):
        """Initialize the weather application."""
        self.api_key = None
        self._setup_logging()
        self.logger = get_logger(__name__)
        self._load_environment()
        self._initialize_api_key()
    
    def _setup_logging(self) -> None:
        """Configure application logging."""
        setup_logging()
    
    def _load_environment(self) -> None:
        """Load environment variables."""
        load_dotenv()
        self.secret_path = os.getenv("SECRET_PATH")
        self.secret_key = os.getenv("SECRET_KEY")
        self.vault_url = os.getenv("VAULT_ADDR")
        self.vault_token = os.getenv("VAULT_TOKEN")
    
    def _initialize_api_key(self) -> None:
        """Initialize API key from vault."""
        try:
            # Validate that all required environment variables are present
            if (self.secret_path is None or self.secret_key is None or 
                self.vault_url is None or self.vault_token is None):
                missing_vars = []
                if self.secret_path is None:
                    missing_vars.append("SECRET_PATH")
                if self.secret_key is None:
                    missing_vars.append("SECRET_KEY")
                if self.vault_url is None:
                    missing_vars.append("VAULT_ADDR")
                if self.vault_token is None:
                    missing_vars.append("VAULT_TOKEN")
                
                error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
                self.logger.critical(error_msg)
                raise RuntimeError(error_msg)
            
            # At this point, mypy knows all variables are not None
            self.logger.info("Attempting to retrieve API key from Vault.")
            vault_service = WeatherServiceFactory.create_vault_service()
            
            self.api_key = vault_service.get_api_key(
                self.secret_path, self.secret_key, self.vault_url, self.vault_token
            )
            self.logger.info("API key retrieved successfully from Vault.")
        except RuntimeError as e:
            self.logger.critical(f"Error retrieving API key: {e}")
            st.error(f"Error retrieving API key: {e}")
            self.api_key = None
    
    def parse_city_input(self, city_input: str) -> Tuple[str, str, str]:
        """
        Parse city input string into components.
        
        Args:
            city_input: Input string in format "[city], [state], [country]"
            
        Returns:
            Tuple of (city_name, state_name, country_name)
        """
        if not city_input.strip():
            return '', '', ''
        
        city_info = [part.strip() for part in city_input.split(',')]
        
        if len(city_info) >= 3:
            return city_info[0], city_info[1], city_info[2]
        elif len(city_info) == 2:
            return city_info[0], city_info[1], ''
        elif len(city_info) == 1:
            return city_info[0], '', ''
        else:
            return '', '', ''
    
    def create_weather_map(
        self, 
        lat: float, 
        lon: float, 
        weather_layer: str = 'precipitation_new',
        zoom_level: int = DEFAULT_ZOOM_LEVEL
    ) -> None:
        """
        Create and display a Folium weather map with weather overlay.
        
        Args:
            lat: Latitude coordinate
            lon: Longitude coordinate
            weather_layer: Weather layer type to display
            zoom_level: Initial zoom level for the map
        """
        if not self.api_key:
            st.error("API key is required to fetch weather map tiles.")
            return
        
        # Create tile layer URL template for dynamic loading at all zoom levels
        tile_url_template = f"http://tile.openweathermap.org/map/{weather_layer}/{{z}}/{{x}}/{{y}}.png?appid={self.api_key}"
        
        self.logger.debug(f"Weather tile URL template: {tile_url_template}")
        
        # Create the base map
        folium_map = folium.Map(location=[lat, lon], zoom_start=zoom_level)
        
        # Add the weather layer as an overlay
        weather_layer_name = WEATHER_LAYERS.get(weather_layer, weather_layer.replace('_', ' ').title())
        folium.TileLayer(
            tiles=tile_url_template,
            attr='OpenWeatherMap',
            name=weather_layer_name,
            overlay=True,
            control=True
        ).add_to(folium_map)
        
        # Add layer control to allow toggling the weather overlay
        folium_map.add_child(folium.LayerControl())
        
        # Display the map
        st_folium(folium_map, width=MAP_WIDTH, height=MAP_HEIGHT)
    
    def format_city_info_string(self, city_data: Dict[str, Any]) -> str:
        """
        Format city information string for display.
        
        Args:
            city_data: City data dictionary from API
            
        Returns:
            Formatted city information string
        """
        city_info_parts = [f"Current weather in {city_data['name']}"]
        
        if 'state' in city_data:
            city_info_parts.append(city_data['state'])
        if 'country' in city_data:
            city_info_parts.append(city_data['country'])
        
        return ', '.join(city_info_parts)
    
    def display_current_weather(self, weather_data: Dict[str, Any], city_data: Dict[str, Any]) -> None:
        """
        Display current weather information.
        
        Args:
            weather_data: Weather data from API
            city_data: City data from API
        """
        current = weather_data.get('current', {})
        
        # City and basic info
        st.write(self.format_city_info_string(city_data))
        st.write(f"Timezone: {weather_data['timezone']}")
        st.write(f"Current time: {unix_to_datetime(current['dt'], weather_data['timezone'])}")
        st.write(f"Sunrise: {unix_to_datetime(current['sunrise'], weather_data['timezone'])}")
        st.write(f"Sunset: {unix_to_datetime(current['sunset'], weather_data['timezone'])}")
        
        # Weather description
        weather_desc = current.get('weather', [{}])[0].get('description', '')
        if weather_desc:
            st.write(f"Description: {weather_desc.capitalize()}")
        
        # Temperature information
        self._display_temperature_info(current)
        
        # Environmental conditions
        self._display_environmental_info(current)
        
        # Wind information
        self._display_wind_info(current)
        
        # Precipitation information
        self._display_precipitation_info(current)
    
    def _display_temperature_info(self, current: Dict[str, Any]) -> None:
        """Display temperature-related information."""
        temp = current.get('temp')
        if temp is not None:
            fahrenheit = celsius_to_fahrenheit(temp)
            st.write(f"Temperature: {temp}°C / {fahrenheit:.1f}°F")
        
        feels_like = current.get('feels_like')
        if feels_like is not None:
            fahrenheit = celsius_to_fahrenheit(feels_like)
            st.write(f"Feels like: {fahrenheit:.1f}°F")
    
    def _display_environmental_info(self, current: Dict[str, Any]) -> None:
        """Display environmental information (UV, humidity)."""
        uvi = current.get('uvi')
        if uvi is not None:
            st.write(f"Ultra violet index: {uvi}: {uvi_to_risk_string(uvi)}")
        
        humidity = current.get('humidity')
        if humidity is not None:
            st.write(f"Humidity: {humidity}%")
    
    def _display_wind_info(self, current: Dict[str, Any]) -> None:
        """Display wind-related information."""
        wind_speed = current.get('wind_speed')
        if wind_speed is not None:
            wind_speed_mph = meters_per_second_to_miles_per_hour(wind_speed)
            st.write(f"Wind Speed: {wind_speed_mph:.1f} mi/h")
        
        wind_gust = current.get('wind_gust')
        if wind_gust is not None:
            wind_gust_mph = meters_per_second_to_miles_per_hour(wind_gust)
            st.write(f"Wind Gusts up to: {wind_gust_mph:.1f} mi/h")
    
    def _display_precipitation_info(self, current: Dict[str, Any]) -> None:
        """Display precipitation information."""
        rain = current.get('rain')
        if isinstance(rain, dict):
            rain_1h = rain.get('1h')
            if rain_1h is not None:
                st.write(f"Rain in last hour: {rain_1h} mm")
    
    def create_hourly_forecast_table(self, weather_data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Create hourly forecast table from weather data.
        
        Args:
            weather_data: Weather data from API
            
        Returns:
            DataFrame with hourly forecast data or None if no data
        """
        hourly = weather_data.get('hourly', [])
        if not hourly:
            return None
        
        rows = []
        timezone = weather_data['timezone']
        
        for hour_data in hourly:
            rain = hour_data.get('rain')
            wind_speed = hour_data.get('wind_speed')
            wind_speed_mph = (
                meters_per_second_to_miles_per_hour(wind_speed) 
                if wind_speed is not None else None
            )
            
            row = {
                "Time": unix_to_datetime(hour_data['dt'], timezone),
                "Temp (°F)": (
                    celsius_to_fahrenheit(hour_data.get('temp')) 
                    if hour_data.get('temp') is not None else None
                ),
                "Feels Like (°F)": (
                    celsius_to_fahrenheit(hour_data.get('feels_like')) 
                    if hour_data.get('feels_like') is not None else None
                ),
                "One Hour Rain (mm)": (
                    rain.get('1h') if isinstance(rain, dict) and rain.get('1h') is not None else None
                ),
                "Humidity (%)": hour_data.get('humidity'),
                "Wind Speed (mi/h)": (
                    wind_speed_mph if wind_speed_mph is not None else None
                ),
                "Description": (
                    hour_data.get('weather', [{}])[0].get('description', '').capitalize() 
                    if hour_data.get('weather') else None
                ),
            }
            rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # Convert NaN values back to None for specific columns where we want None instead of NaN
        # This is important for test compatibility and cleaner data representation
        # Use object dtype to preserve None values instead of converting to NaN
        for col in ["One Hour Rain (mm)"]:
            if col in df.columns:
                df[col] = df[col].astype('object').where(pd.notna(df[col]), None)
        
        return df
    
    def render_ui(self) -> None:
        """Render the main user interface."""
        st.title('World Cities Weather Map')
        
        # Input controls
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_city = st.text_input(
                'Enter a city 👇', 
                placeholder='[city], [state code or ""], [country code or ""]'
            )
        
        with col2:
            selected_weather_layer = st.selectbox(
                'Weather Layer',
                options=list(WEATHER_LAYERS.keys()),
                format_func=lambda x: WEATHER_LAYERS[x],
                index=0  # Default to precipitation
            )
        
        # Main content area
        map_column, weather_column = st.columns(2)

        # Process city input and display results
        if selected_city:
            city_name, state_name, country_name = self.parse_city_input(selected_city)
            
            if city_name:  # Only proceed if we have at least a city name
                weather_data = self._process_city_weather(
                    city_name, state_name, country_name, 
                    map_column, weather_column,
                    selected_weather_layer
                )
                
                # Display hourly forecast in a separate full-width section
                if weather_data:
                    self._render_hourly_forecast_section(weather_data, city_name)
    
    def _process_city_weather(
        self, 
        city_name: str, 
        state_name: str, 
        country_name: str,
        map_column,
        weather_column,
        weather_layer: str = 'precipitation_new'
    ) -> Optional[Dict[str, Any]]:
        """
        Process city weather data and display results.
        
        Args:
            city_name: Name of the city
            state_name: State/province name
            country_name: Country name
            map_column: Streamlit column for map
            weather_column: Streamlit column for weather info
            weather_layer: Weather layer type to display on map
            
        Returns:
            Weather data dictionary or None if processing failed
        """
        with PerformanceLogger(f"process_city_weather_{city_name}", self.logger):
            # Get city coordinates
            with PerformanceLogger(f"get_coordinates_{city_name}", self.logger):
                geocoding_service = WeatherServiceFactory.create_geocoding_service()
                city_data = geocoding_service.get_coordinates(
                    city_name, 
                    state_name, 
                    country_name, 
                    self.api_key,
                    limit = 3
                )
                self.logger.info(f"Processing weather request for: {city_name}, {state_name}, {country_name}")
            
            if not city_data:
                self.logger.warning(f"No location data found for: {city_name}")
                with weather_column:
                    st.write(f"City '{city_name}' not found.")
                return None
            
            city_info = city_data[0]
            lat, lon = city_info['lat'], city_info['lon']
            self.logger.info(f"Using coordinates: ({lat}, {lon}) for {city_info.get('name', city_name)}")
            
            # Display map
            with PerformanceLogger(f"create_map_{city_name}", self.logger):
                with map_column:
                    self.create_weather_map(lat, lon, weather_layer)
            
            # Get and display weather data
            with PerformanceLogger(f"get_weather_data_{city_name}", self.logger):
                weather_service = WeatherServiceFactory.create_weather_service()
                weather_data = weather_service.get_weather_data(
                    lat, 
                    lon,
                    self.api_key
                )

            if not weather_data:
                self.logger.error(f"Failed to retrieve weather data for {city_name}")
                with weather_column:
                    st.write("Unable to retrieve weather data.")
                return None
            
            self.logger.info(f"Successfully processed weather data for {city_name}")
            
            # Display current weather
            with PerformanceLogger(f"display_current_weather_{city_name}", self.logger):
                with weather_column:
                    self.display_current_weather(weather_data, city_info)
            
            return weather_data
    
    def _render_hourly_forecast_section(self, weather_data: Dict[str, Any], city_name: str) -> None:
        """
        Render the hourly forecast section in a separate full-width column.
        
        Args:
            weather_data: Weather data from API
            city_name: Name of the city for logging
        """
        if 'hourly' not in weather_data:
            return
            
        # Create a separator and section header
        st.markdown("---")
        
        # Create a single full-width column for the hourly forecast
        forecast_column = st.columns(1)[0]
        
        with forecast_column:
            st.subheader("📊 Hourly Forecast")
            
            with PerformanceLogger(f"create_hourly_forecast_{city_name}", self.logger):
                hourly_df = self.create_hourly_forecast_table(weather_data)
                if hourly_df is not None and not hourly_df.empty:
                    # Display the table with full container width
                    st.dataframe(
                        hourly_df.sort_values(by="Time", ascending=True),
                        use_container_width=True,
                        height=400  # Set a reasonable height for scrolling
                    )
                    self.logger.info(f"Displayed hourly forecast with {len(hourly_df)} entries")
                else:
                    st.info("No hourly forecast data available.")
    
    def run(self) -> None:
        """Run the weather application."""
        if self.api_key is None:
            st.error("Cannot run application without API key. Please check your configuration.")
            return
        
        self.render_ui()
