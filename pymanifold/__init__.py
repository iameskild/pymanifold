import json
import os
import importlib
from pathlib import Path
import logging

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

API_BASE_URL = "https://api.manifold.markets"
API_KEY = os.getenv("MANIFOLD_API_KEY")

API_DOC_PATH = Path('api.md')
MODELS_MODULE = 'pymanifold.models'

DEPRECATED = 'deprecated'

CURRENT_DIR = Path(__file__).parent
ENDPOINTS: dict[str, dict[str, str]] = json.load(open(f'{CURRENT_DIR}/endpoints.json'))

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Session:
    def __init__(
        self, 
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
        self.method = ENDPOINTS.get(self.endpoint, {}).get("method")
        self.model = get_model(self.endpoint)
    
    def __repr__(self) -> str:
        return f"Session(endpoint={self.endpoint})"

    def execute(
        self,
        url_params: dict | None = None,
        params: dict | None = None,
        json_data: dict | None = None,
    ) -> dict:
        """
        Execute the session.

        Args:
            url_params: URL parameters to replace in the endpoint (eg. {"username": "johndoe"} for "/v0/user/[username]")
            params: Query parameters to pass to the API
            json_data: JSON data to pass to the API
        """
        if url_params:
            for url_param, value in url_params.items():
                self.endpoint = self.endpoint.replace(f"[{url_param}]", value)
        return call_manifold_api(
            self.endpoint,
            method=self.method,
            params=params,
            json_data=json_data,
            api_key=self.api_key,
        )


def get_model(endpoint: str) -> BaseModel:
    module_path = MODELS_MODULE + ENDPOINTS.get(endpoint, {}).get("module_path")
    model_name = ENDPOINTS.get(endpoint, {}).get("model_name")
    logger.info(f"module_path: {module_path}")
    logger.info(f"model_name: {model_name}")

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

    Used by the Session.execute() method but made available for direct use.

    Args:
        endpoint: API endpoint path (e.g. "/v0/me")
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
