import json
import os
import importlib
from pathlib import Path

import httpx
from pydantic import BaseModel

API_BASE_URL = "https://api.manifold.markets"
API_KEY = os.getenv("MANIFOLD_API_KEY")

API_DOC_PATH = Path('api.md')
MODELS_MODULE = 'pymanifold.models'

DEPRECATED = 'deprecated'

endpoints: dict[str, dict[str, str]] = json.load(open('endpoints.json'))


class Session:
    def __init__(self, 
        endpoint: str,
        version: str = "v0",
        api_key: str | None = API_KEY,
    ):
        """
        Create a session for interacting with the Manifold Markets API.

        Args:
            endpoint: API endpoint path (e.g. "/bet")
            version: API version (default is "v0")
            api_key: Optional API key for authenticated endpoints
        """
        if endpoint.startswith('/v0') or endpoint.startswith('v0'):
            endpoint = endpoint.replace('/v0', '')
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        if version != "v0":
            raise ValueError("Only v0 is supported")
        
        self.api_key = api_key
        self.endpoint = f"/{version}{endpoint}"
        self.method = endpoints.get(self.endpoint, {}).get("method")
        self.model = get_model(self.endpoint)
    
    def __repr__(self) -> str:
        return f"Session(endpoint={self.endpoint})"

    def call_api(self) -> dict:
        return call_manifold_api(
            self.endpoint,
            method=self.method,
            # json_data=self.model.model_dump(),
            api_key=self.api_key,
        )


def get_model(endpoint: str) -> BaseModel:
    module_path = MODELS_MODULE + '.' + endpoints.get(endpoint, {}).get("module_path")
    model_name = endpoints.get(endpoint, {}).get("model_name")
    print(f"module_path: {module_path}")
    print(f"model_name: {model_name}")

    try:
        client = getattr(importlib.import_module(module_path), model_name)
    except ModuleNotFoundError:
        raise ValueError(f"Model not found for endpoint: {endpoint}")
    
    return client
    

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
    url = f"{API_BASE_URL}{endpoint}"

    headers = {}
    if api_key:
        headers["Authorization"] = f"Key {api_key}"

    response = httpx.request(
        method=method,
        url=url,
        params=params,
        json=json_data,
        headers=headers if headers else None,
    )
    response.raise_for_status()
    return response.json()





# mapping = create_mapping()

# if __name__ == "__main__":
#     print(mapping)
