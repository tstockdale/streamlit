import requests
import hvac
import logging


# Retrieve the logger instance
logger = logging.getLogger(__name__)



def get_api_key_from_vault(secret_path, secret_key, vault_url, vault_token):
    """
    Retrieve the API key from HashiCorp Vault.

    Args:
        secret_path (str): The path to the secret in Vault.
        secret_key (str): The key within the secret to retrieve.

    Returns:
        str: The API key if found, otherwise None.
    """
    try:
        # Initialize the Vault client
        client = hvac.Client(
            url=vault_url,
            token=vault_token
        )

        # Read the secret from the specified path
        secret = client.secrets.kv.read_secret_version(path=secret_path, raise_on_deleted_version=False)
       

        # Retrieve the API key from the secret
        api_key = secret['data']['data'].get(secret_key)

        if api_key:
            return api_key
        else:
            logging.critical(f"Key '{secret_key}' not found in Vault secret at path '{secret_path}'.")
            raise ValueError(f"Key '{secret_key}' not found in Vault secret at path '{secret_path}'.")

    except Exception as e:
        raise RuntimeError(f"Failed to retrieve API key from Vault: {e}")


def get_lat_lon(city, state, country, api_key):
    url = f'https://api.openweathermap.org/geo/1.0/direct?q={city},{state},{country}&appid={api_key}'
    logging.info(f"Fetching coordinates for {city} from URL: {url}")
    response = requests.get(url)
    logging.info(response)
    city_data = response.json()
    logging.info(city_data)
    if city_data:
        return city_data
    else:
        logging.debug(f"City '{city}' not found.")
        return None

def get_weather(city_lat, city_lon, api_key):
    if city_lat is not None and city_lon is not None:
        url = f'https://api.openweathermap.org/data/3.0/onecall?lat={city_lat}&lon={city_lon}&appid={api_key}&units=metric'
        logging.info(f"Fetching weather data from URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching weather data: {e}")
            return None
    else:
        return None
