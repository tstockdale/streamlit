import hvac

client = hvac.Client(
    url='http://127.0.0.1:8200',
    token='dev-only-token',
)

create_response = client.secrets.kv.v2.create_or_update_secret(
    path='openweathermap_api',
    secret=dict(key=''),
)