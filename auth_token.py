import requests

def get_token(client_id,client_secret,tenant_id):
    # OAuth 2.0 endpoint for token request
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"

    # Headers for the request
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    # Data to request the access token using client credentials
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope":"https://graph.microsoft.com/.default"

    }

    # Send the POST request to get the access token
    response = requests.post(token_url, headers=headers, data=data)

    # Check if the request was successful
    if response.status_code == 200:
        # Extract the access token from the response
        token_data = response.json()
        access_token = token_data["access_token"]
        print("Access Token success")
        return access_token
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None
        

    



