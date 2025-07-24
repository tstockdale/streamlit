# Weather Map Application

A Streamlit-based web application that displays weather information and interactive maps for cities worldwide using the OpenWeatherMap API.

## Features

- **Interactive Weather Maps**: View weather overlays on interactive maps using Folium
- **Current Weather Data**: Get real-time weather information including temperature, humidity, wind speed, and more
- **Hourly Forecasts**: View detailed hourly weather forecasts in tabular format
- **Multiple Map Styles**: Choose from various Mapbox map styles (Streets, Light, Dark, Outdoors, Satellite)
- **Global City Search**: Search for weather data in cities worldwide with support for state/country specifications
- **Secure API Key Management**: Integration with HashiCorp Vault for secure API key storage

## Project Structure

```
weather-map-app/
├── src/
│   └── weather_map/
│       ├── __init__.py
│       ├── weather_app.py      # Main application class
│       ├── config.py           # Configuration constants
│       ├── logging_config.py   # Logging configuration and utilities
│       ├── services.py         # API service functions
│       └── utils.py            # Utility functions
├── tests/
│   ├── __init__.py
│   ├── test_utils.py          # Unit tests for utility functions
│   ├── test_services.py       # Unit tests for API services and Vault integration
│   ├── test_weather_app.py    # Unit tests for WeatherApp class and methods
│   ├── test_logging_config.py # Unit tests for logging configuration and classes
│   └── test_config.py         # Unit tests for configuration constants
├── docs/                      # Documentation directory
│   └── logging_guide.md       # Comprehensive logging best practices guide
├── main.py                    # Application entry point
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup configuration
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/weather-map-app.git
   cd weather-map-app
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   Create a `.env` file in the root directory with the following variables:
   ```
   SECRET_PATH=your/vault/secret/path
   SECRET_KEY=your_api_key_name
   VAULT_URL=https://your-vault-instance.com
   VAULT_TOKEN=your_vault_token
   ```

## Usage

### Running the Application

```bash
streamlit run main.py
```

The application will be available at `http://localhost:8501`

### Using the Application

1. **Enter a City**: Type a city name in the format `[city], [state], [country]`
   - Examples: `New York, NY, US` or `London, , UK` or `Tokyo`

2. **Select Map Style**: Choose from available Mapbox styles

3. **View Results**: 
   - Interactive weather map on the left
   - Current weather information on the right
   - Hourly forecast table below

### Running Tests

```bash
python -m pytest tests/
```

Or run specific test files:
```bash
python -m unittest tests.test_utils
```

## API Requirements

This application requires:
- **OpenWeatherMap API Key**: For weather data and map tiles
- **HashiCorp Vault**: For secure API key storage (optional - can be modified for direct API key usage)

## Configuration

### Map Styles

The application supports multiple Mapbox map styles defined in `src/weather_map/config.py`:
- Streets
- Light
- Dark
- Outdoors
- Satellite

### Weather Layers

Currently supports precipitation overlay maps from OpenWeatherMap.

## Development

### Project Architecture

- **`WeatherApp` Class**: Main application logic encapsulated in a class-based structure
- **Modular Design**: Separate modules for configuration, services, and utilities
- **Type Hints**: Comprehensive type annotations for better code documentation
- **Error Handling**: Robust error handling throughout the application
- **Logging**: Structured logging with rotating file handlers

### Adding New Features

1. **New Utility Functions**: Add to `src/weather_map/utils.py` with corresponding tests
2. **New API Services**: Add to `src/weather_map/services.py`
3. **New Configuration**: Add to `src/weather_map/config.py`
4. **New UI Components**: Add methods to the `WeatherApp` class

### Code Style

- Follow PEP 8 guidelines
- Use type hints for all function parameters and return values
- Include comprehensive docstrings
- Write unit tests for new functionality

## Dependencies

Key dependencies include:
- `streamlit`: Web application framework
- `folium`: Interactive maps
- `streamlit-folium`: Streamlit-Folium integration
- `requests`: HTTP requests for API calls
- `pandas`: Data manipulation
- `python-dotenv`: Environment variable management
- `hvac`: HashiCorp Vault client
- `pytz`: Timezone handling

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

For support, please open an issue on the GitHub repository or contact [your.email@example.com].
