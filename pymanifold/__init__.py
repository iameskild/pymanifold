import os
import importlib
from pathlib import Path
import shutil

import httpx
from pydantic import BaseModel
import mistune

API_BASE_URL = "https://api.manifold.markets"
API_KEY = os.getenv("MANIFOLD_API_KEY")

API_DOC_PATH = Path('api.md')
MODELS_DIR = Path('pymanifold/models')

DEPRECATED = 'deprecated'

fix_me = {
    'Username': 'UserUsername',
}


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
        self.method = mapping.get(self.endpoint, {}).get("method")
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
    model_location = MODELS_DIR / Path(mapping.get(endpoint, {}).get("model_location"))
    model_name = model_location.stem.replace('{', '').replace('}', '').capitalize()
    model_name = fix_me.get(model_name, model_name)
    module_name = str(model_location).replace("/", ".").replace(".py", "")
    print(model_name)
    print(model_location)
    print(module_name)

    try:
        client = getattr(importlib.import_module(module_name), model_name)
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


def create_mapping() -> dict[str, dict[str, str]]:
    """Create a mapping of API endpoints to Pydantic model locations."""

    with API_DOC_PATH.open('r', encoding='utf-8') as f:
        api_doc = f.read()

    md = mistune.markdown(api_doc, renderer='ast')

    endpoints: dict[str, dict] = {}
    for token in md:
        if (
            token['type'] == 'heading' and
            token['attrs']['level'] == 3 and
            token['children'][0]['type'] == 'codespan'
        ):
            if len(token['children']) > 1:
                deprecated = token['children'][1]['raw'].lower().strip('(').strip(')').strip(' ')
                if deprecated == DEPRECATED:
                    continue
            _ = token['children'][0]['raw']
            method = _.split(' ')[0]
            endpoint = _.split(' ')[1]

            endpoints[endpoint] = {
                'method': method,
            }

    def _file_to_endpoint(file_path: Path) -> tuple[str, dict]:
        return (
            '/v0/' + 
            str(file_path).replace('.py', '').replace('{', '[').replace('}', ']')
        )
    for py_file in MODELS_DIR.rglob('*.py'):
        if py_file.name == '__init__.py':
            continue
        relative_path = py_file.relative_to(MODELS_DIR)
        endpoint = _file_to_endpoint(relative_path)
        if endpoint in endpoints.keys():
            endpoints[endpoint]['model_location'] = str(relative_path)

    
    return endpoints


mapping = create_mapping()
