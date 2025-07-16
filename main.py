import streamlit as st
import pydeck as pdk
import logging
from dotenv import load_dotenv
import os

from config import MAP_STYLES
import services
from utils import unix_to_datetime
from utils import uvi_to_risk_string
from utils import lat_lon_to_world_coordinates
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

def update_map_weather(lat, lon, map_style='mapbox://styles/mapbox/streets-v12', api_key=None, weather_layer='clouds_new'):
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
    zoom_level = 4
    x, y = lat_lon_to_world_coordinates(lat, lon, zoom_level)
    # Define the weather tile layer URL
    #tile_url = f"https://tile.openweathermap.org/map/{weather_layer}/{{z}}/{{x}}/{{y}}.png?appid={api_key}"
    tile_url = f"http://tile.openweathermap.org/maps/2.0/weather/{weather_layer}/{zoom_level}/{x}/{y}.png?appid={api_key}"
    print(tile_url)

    # Create the PyDeck map with the weather tile layer
    st.pydeck_chart(pdk.Deck(
        map_style=map_style,
        initial_view_state=pdk.ViewState(
            latitude=lat,
            longitude=lon,
            zoom=5,
            pitch=50,
        ),
        layers=[
            # Weather tile layer
            pdk.Layer(
                "TileLayer",
                data=None,
                get_tile_url=tile_url,
                min_zoom=0,
                max_zoom=12,
                tile_size=256,
            )
        ]
    ))

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
                update_map(lat, lon, MAP_STYLES[selected_style])
                #update_map_weather(lat, lon, map_style=MAP_STYLES[selected_style], api_key=api_key, weather_layer='clouds_new')
            else:
                st.write(f"City {selected_city} not found.")

    with weather_column:
        if selected_city and city is not None and 'lat' in locals() and 'lon' in locals():
            weather = services.get_weather(lat, lon, api_key)
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
            if 'temp' in weather['current']:
                st.write(f"Temperature: {weather['current']['temp']}°C")
            if 'feels_like' in weather['current']:
                st.write(f"Feels like: {weather['current']['feels_like']}°C")
            if 'uvi' in weather['current']:
                uvi = weather['current']['uvi']
                st.write(f"Ultra violet index: {uvi}: " + uvi_to_risk_string(uvi))
            if 'humidity' in weather['current']:
                st.write(f"Humidity: {weather['current']['humidity']}%")
            if 'wind_speed' in weather['current']:
                st.write(f"Wind Speed: {weather['current']['wind_speed']} m/s")
            if 'wind_gust' in weather['current']:
                st.write(f"Wind Gusts up to: {weather['current']['wind_gust']} m/s")
            if 'rain' in weather['current']:
                st.write(f"Rain in last hour: {weather['current']['rain']['1h']} mm")

# Entry point
if __name__ == "__main__":
    main()