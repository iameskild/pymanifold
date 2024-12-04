import json
from pathlib import Path
import mistune

API_DOC_PATH = Path('api.md')
MODELS_DIR = Path('pymanifold/models')
OUTPUT_FILE = Path('api_endpoint_models.json')

DEPRECATED = 'deprecated'


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

def file_to_endpoint(file_path: Path) -> tuple[str, dict]:
    return (
        '/v0/' + 
        str(file_path).replace('.py', '').replace('{', '[').replace('}', ']')
    )

for py_file in MODELS_DIR.rglob('*.py'):
    if py_file.name == '__init__.py':
        continue
    relative_path = py_file.relative_to(MODELS_DIR)
    endpoint = file_to_endpoint(relative_path)
    if endpoint in endpoints:
        endpoints[endpoint]['model_location'] = str(relative_path)


from pprint import pprint
pprint(endpoints)
