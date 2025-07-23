"""
World Cities Weather Map - A Streamlit application for displaying weather information
and interactive maps for cities worldwide.

Entry point for the application.
"""

from src.weather_map import WeatherApp


def main():
    """Main entry point for the application."""
    app = WeatherApp()
    app.run()


if __name__ == "__main__":
    main()
