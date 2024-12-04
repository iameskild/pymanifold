import httpx
import os

from models.username import UserUsername as Username


BASE_URL = "https://api.manifold.markets/v0" 
API_KEY = os.getenv("MANIFOLD_API_KEY")


def call_manifold_api(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
    json_data: dict | None = None,
    api_key: str | None = API_KEY,
) -> dict:
    """Make a request to the Manifold Markets API.
    
    Args:
        endpoint: API endpoint path (e.g. "/bet")
        method: HTTP method to use ("GET", "POST", etc)
        params: Optional query parameters
        json_data: Optional JSON data for POST/PUT requests
        api_key: Optional API key for authenticated endpoints
    
    Returns:
        API response as a dictionary
        
    Raises:
        httpx.HTTPError: If the request fails
    """
    url = f"{BASE_URL}{endpoint}"
    
    headers = {}
    if api_key:
        headers["Authorization"] = f"Key {api_key}"
    
    response = httpx.request(
        method=method,
        url=url,
        params=params,
        json=json_data,
        headers=headers if headers else None
    )
    response.raise_for_status()
    return response.json()


# test call
# if __name__ == "__main__":
#     username = Username(username="iameskild")
#     print(username)

#     print(call_manifold_api(f"/user/{username.username}", api_key=API_KEY))