import json
import re
from pathlib import Path
import subprocess

import mistune

SCHEMA_INPUT = Path("schema")
PYDANTIC_OUTPUT = Path("pymanifold/models")
API_DOC_PATH = Path('api.md')

DEPRECATED = 'deprecated'


def make_models():
    """
    Make Pydantic models from JSON schemas using datamodel-codegen.
    """
    ENDPOINTS: dict[str, dict[str, str]] = _get_endpoints_from_api_doc()

    for schema_file in SCHEMA_INPUT.rglob('*.json'):
        relative_path = schema_file.relative_to(SCHEMA_INPUT)
        module_path = relative_path.with_suffix('')

        ############################################################
        # Clean up and ensure valid Python module names
        # Modules with trailing underscores represent parameters in the API
        # Example: /slug/{slug}.py -> /slug/slug_.py
        # UGLY... find a better way to do this
        original_module_path_str = _file_to_endpoint(module_path)
        module_path_str = module_path.as_posix()
        module_path_str = re.sub(r'[^a-zA-Z0-9_/]', '_', module_path_str)
        module_path_str = module_path_str.replace('/_', '/')
        output_path = PYDANTIC_OUTPUT / (module_path_str + '.py')
        output_file = str(output_path).replace('_.py', '__.py')
        ############################################################

        if original_module_path_str not in ENDPOINTS.keys():
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create __init__.py files in each directory to make it a Python package
        current_dir = output_path.parent
        while current_dir != PYDANTIC_OUTPUT and current_dir != current_dir.parent:
            init_file = current_dir / '__init__.py'
            if not init_file.exists():
                init_file.touch()
            current_dir = current_dir.parent


        # Run datamodel-codegen to generate the Pydantic model
        subprocess.run([
            'datamodel-codegen',
            '--input', str(schema_file),
            '--input-file-type', 'jsonschema',
            '--output', output_file,
            '--output-model-type', 'pydantic_v2.BaseModel',
        ], check=True)

        model_name = module_path_str.replace('/', '_').replace('_', ' ').title().replace(' ', '')
        module_path = output_file.replace('.py', '').replace('pymanifold/models/', '').replace('/', '.')

        ENDPOINTS[original_module_path_str]['module_path'] = str(module_path)
        ENDPOINTS[original_module_path_str]['model_name'] = model_name

        print(f"Generated Pydantic model for {schema_file} at {output_file}")
    
    with open('../pymanifold/endpoints.json', 'w+', encoding='utf-8') as f:
        json.dump(ENDPOINTS, f)

    return ENDPOINTS


def _file_to_endpoint(file_path: Path) -> tuple[str, dict]:
    return (
        '/v0/' + 
        str(file_path).replace('.py', '').replace('{', '[').replace('}', ']')
    )


def _get_endpoints_from_api_doc(endpoints: dict[str, dict[str, str]] = {}) -> dict[str, dict[str, str]]:
    """
    Get the list of endpoints from the Manfifold API docs.
    """

    # todo: pull from github
    with API_DOC_PATH.open('r', encoding='utf-8') as f:
        api_doc = f.read()

    md = mistune.markdown(api_doc, renderer='ast')

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

    return endpoints


if __name__ == "__main__":
    make_models()

