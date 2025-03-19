import requests
from datetime import datetime, timedelta

async def get_token(username, password):
    url = "https://example.com/api/token"  # Replace this with the actual API endpoint
    
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, data=data)
    
    if response.status_code == 200:
        return response.json().get("token")
    else:
        print("Error:", response.text)
        return None

# Function to check if the token is expired
async def is_token_expired(token_expiry):
    return datetime.now() >= token_expiry

# Function to retrieve or refresh the token
async def get_or_refresh_token(username, password, current_token=None):
    if current_token:
        # If the current token exists, check if it's expired
        if not is_token_expired(current_token['expiry']):
            return current_token['value']
    
    # If the token is expired or doesn't exist, get a new one
    new_token_value = await get_token(username, password)
    if new_token_value:
        # Set token expiry to 1 hour from now (example)
        token_expiry = datetime.now() + timedelta(hours=1)
        return {'value': new_token_value, 'expiry': token_expiry}
    else:
        return None
