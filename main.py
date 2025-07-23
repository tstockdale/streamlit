import streamlit as st
import pydeck as pdk
import logging
from dotenv import load_dotenv
import folium
from streamlit_folium import st_folium
import os

from config import MAP_STYLES
import services
from utils import (
    unix_to_datetime,
    uvi_to_risk_string,
    celsius_to_fahrenheit,
    meters_per_second_to_miles_per_hour,
    lat_lon_to_tile_coordinates
)


import pandas as pd

from logging.handlers import RotatingFileHandler


def update_map(lat, lon, map_style='mapbox://styles/mapbox/streets-v12'):
    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=11,
            pitch=50,
        ),
))

def update_weather_map(lat, lon, map_style='mapbox://styles/mapbox/streets-v12', api_key=None, weather_layer='precipitation'):
    """
    Update the map with a weather overlay from OpenWeatherMap.

    Args:
        lat (float): Latitude of the location.
        lon (float): Longitude of the location.
        map_style (str): Mapbox style URL.
        api_key (str): OpenWeatherMap API key.
        weather_layer (str): Weather layer to display (e.g., 'clouds', 'precipitation').
    """
    if not api_key:
        st.error("API key is required to fetch weather map tiles.")
        return
    zoom_level = 9
    x, y = lat_lon_to_tile_coordinates(lat, lon, zoom_level)
    # Define the weather tile layer URL
    tile_url = f"http://tile.openweathermap.org/map/{weather_layer}/{zoom_level}/{x}/{y}.png?appid={api_key}"
    print(tile_url)

    # Create the PyDeck map with the weather tile layer
    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=zoom_level,
            pitch=50,
        ),
        layers=[
            # Weather tile layer
            pdk.Layer(
                "TileLayer",
                data=tile_url,
                #get_tile_url=tile_url,
                min_zoom=0,
                max_zoom=12,
                tile_size=2**zoom_level,
            )
        ]
    ))

def update_weather_map_folium(lat, lon, api_key=None, weather_layer='precipitation_new'):
    if not api_key:
        st.error("API key is required to fetch weather map tiles.")
        return
    zoom_level = 10
    x, y = lat_lon_to_tile_coordinates(lat, lon, zoom_level)
    # Define the weather tile layer URL
    tile_url = f"http://tile.openweathermap.org/map/{weather_layer}/{zoom_level}/{x}/{y}.png?appid={api_key}"
    print(tile_url)

    # Create the Folium map with the weather tile layer
    folium_map = folium.Map(location=[lat, lon], zoom_start=zoom_level)
    folium.TileLayer(
        tiles=tile_url,
        attr='OpenWeatherMap',
        name=weather_layer,
        overlay=True,
        control=True
    ).add_to(folium_map)
    folium_map.add_child(folium.LayerControl())
    st_folium(folium_map, width=350, height=500)


def extract_hourly_table(weather, timezone):
    hourly = weather.get('hourly', [])
    rows = []
    for h in hourly:
        rain = h.get('rain')
        wind_speed = h.get('wind_speed')
        wind_speed_mph = meters_per_second_to_miles_per_hour(wind_speed) if wind_speed is not None else None
        rows.append({
            "Time": unix_to_datetime(h['dt'], timezone),
            "Temp (°F)": celsius_to_fahrenheit(h.get('temp')) if h.get('temp') is not None else None,
            "Feels Like (°F)": celsius_to_fahrenheit(h.get('feels_like')) if h.get('feels_like') is not None else None,
            "Humidity (%)": h.get('humidity'),
            "Wind Speed (mi/h)":f"{wind_speed_mph:.1f}" if wind_speed_mph is not None else None,
            "Feels Like (°F)": celsius_to_fahrenheit(h.get('feels_like')) if h.get('feels_like') is not None else None,
            "One Hour Rain (mm)": rain.get('1h') if isinstance(rain, dict) and rain.get('1h') is not None else None,
            "Description": h.get('weather', [{}])[0].get('description', '').capitalize() if h.get('weather') else None,
        })
    return pd.DataFrame(rows)

def main():

    load_dotenv()

    SECRET_PATH = os.getenv("SECRET_PATH")
    SECRET_KEY =  os.getenv("SECRET_KEY")
    VAULT_URL = os.getenv("VAULT_URL")
    VAULT_TOKEN = os.getenv("VAULT_TOKEN")

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler("app.log", maxBytes=10 * 1024 * 1024, backupCount=5),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)

    # Get API key from vault
    try:
        api_key = services.get_api_key_from_vault(SECRET_PATH, SECRET_KEY, VAULT_URL, VAULT_TOKEN)
        logging.info("API key retrieved successfully from Vault.")
    except RuntimeError as e:
        logging.critical(f"Error retrieving API key: {e}")
        st.error(f"Error retrieving API key: {e}")
        api_key = None


    # Streamlit app
    st.title('World Cities Weather Map')

    # Layout
    city_input_column, map_style_column = st.columns(2)
    with city_input_column:
        selected_city = st.text_input(
            'Enter a city 👇', 
            placeholder='[city], [state code or ""], [country code or ""]'
        )
        city_info = selected_city.split(',')

        if len(city_info) == 3:
            city_name, state_name, country_name = city_info
        elif len(city_info) == 2:
            city_name, state_name = city_info
            country_name = ''
        elif len(city_info) == 1:
            city_name = city_info[0]
            state_name = ''
            country_name = ''
        else:
            city_name = state_name = country_name = ''
            
    with map_style_column:
        selected_style = st.selectbox(
            "Select Map Style 👇", 
            options=list(MAP_STYLES.keys())
        )

    map_column, weather_column = st.columns(2)

    # Handle city and map style selection
    with map_column:
        if selected_city and selected_style:
            city = services.get_lat_lon(city_name, state_name, country_name, api_key)
            logging.info(city)
            if city is not None:
                lat, lon = city[0]['lat'], city[0]['lon']
                #update_map(lat, lon, MAP_STYLES[selected_style])
                #update_weather_map(lat, lon, MAP_STYLES[selected_style], api_key,'precipitation_new')
                update_weather_map_folium(lat, lon, api_key)
            else:
                st.write(f"City {selected_city} not found.")

    hourly_df = None
    with weather_column:
        if selected_city and city is not None and 'lat' in locals() and 'lon' in locals():
            weather = services.get_weather(lat, lon, api_key)
            if weather and 'hourly' in weather:
                hourly_df = extract_hourly_table(weather, weather['timezone'])
            logging.info(weather)
            city_info_str = f"Current weather in {city[0]['name']}"
            if 'state' in city[0]:
                city_info_str = city_info_str + f", {city[0]['state']}"
            if 'country' in city[0]:
                city_info_str = city_info_str + f", {city[0]['country']}"

            st.write(city_info_str)
            st.write(f"Timezone: {weather['timezone']}")
            st.write(f"Current time: " + unix_to_datetime(weather['current']['dt'], weather['timezone']))
            st.write(f"Sunrise: " + unix_to_datetime(weather['current']['sunrise'], weather['timezone']))
            st.write(f"Sunset: " + unix_to_datetime(weather['current']['sunset'], weather['timezone']))
            st.write(f"Description: {weather['current']['weather'][0]['description'].capitalize()}")
            current = weather.get('current', {})
            # Temperature
            temp = current.get('temp')
            if temp is not None:
                fahrenheit = celsius_to_fahrenheit(temp)
                st.write(f"Temperature: {temp}°C / {fahrenheit:.1f}°F")
            # Feels like
            feels_like = current.get('feels_like')
            if feels_like is not None:
                fahrenheit = celsius_to_fahrenheit(feels_like)
                st.write(f"Feels like: {feels_like}°C / {fahrenheit:.1f}°F")
            # UV Index
            uvi = current.get('uvi')
            if uvi is not None:
                st.write(f"Ultra violet index: {uvi}: " + uvi_to_risk_string(uvi))
            # Humidity
            humidity = current.get('humidity')
            if humidity is not None:
                st.write(f"Humidity: {humidity}%")
            # Wind speed
            wind_speed = meters_per_second_to_miles_per_hour(current.get('wind_speed'))
            if wind_speed is not None:
                st.write(f"Wind Speed: {wind_speed:.1f} mi/h")
            # Wind gust
            wind_gust = meters_per_second_to_miles_per_hour(current.get('wind_gust'))
            if wind_gust is not None:
                st.write(f"Wind Gusts up to: {wind_gust:.1f} mi/h")
            # Rain
            rain = current.get('rain')
            if isinstance(rain, dict):
                rain_1h = rain.get('1h')
                if rain_1h is not None:
                    st.write(f"Rain in last hour: {rain_1h} mm")

     # After map and weather columns:
    if hourly_df is not None and not hourly_df.empty:
        st.write("## Hourly Forecast")
        st.dataframe(
            hourly_df.sort_values(by="Time", ascending=True).reset_index(drop=True),
            use_container_width=False,   
        )

# Entry point
if __name__ == "__main__":
    main()