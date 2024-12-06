import json
import re
from pathlib import Path
import subprocess
import os
import shutil

import mistune

SCHEMA_INPUT = Path("schemas")
PYDANTIC_OUTPUT = Path("pymanifold/models")
API_DOC_PATH = Path("docs/docs/api.md")

DEPRECATED = "deprecated"


def make_models():
    """
    Make Pydantic models from JSON schemas using datamodel-codegen.
    """
    ENDPOINTS: dict[str, dict[str, str]] = _get_endpoints_from_api_doc()

    for schema_file in SCHEMA_INPUT.rglob("*.json"):
        relative_path = schema_file.relative_to(SCHEMA_INPUT)
        module_path = relative_path.with_suffix("")

        # Clean up and ensure valid Python module names
        # Modules with trailing underscores represent parameters in the API
        # Example: /slug/{slug}.py -> /slug/slug_.py
        # UGLY... find a better way to do this
        original_module_path_str = _file_to_endpoint(module_path)
        module_path_str = module_path.as_posix()
        module_path_str = re.sub(r"[^a-zA-Z0-9_/]", "_", module_path_str)
        module_path_str = module_path_str.replace("/_", "/")
        output_path = PYDANTIC_OUTPUT / (module_path_str + ".py")
        output_file = str(output_path).replace("_.py", "__.py")

        if original_module_path_str not in ENDPOINTS.keys():
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create __init__.py files in each directory to make it a Python package
        current_dir = output_path.parent
        while current_dir != PYDANTIC_OUTPUT and current_dir != current_dir.parent:
            init_file = current_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
            current_dir = current_dir.parent

        # Run datamodel-codegen to generate the Pydantic model
        subprocess.run(
            [
                "datamodel-codegen",
                "--input",
                str(schema_file),
                "--input-file-type",
                "jsonschema",
                "--output",
                output_file,
                "--output-model-type",
                "pydantic_v2.BaseModel",
            ],
            check=True,
        )

        model_name = (
            module_path_str.replace("/", "_").replace("_", " ").title().replace(" ", "")
        )
        module_path = (
            output_file.replace(".py", "")
            .replace("pymanifold/models/", "")
            .replace("/", ".")
        )

        ENDPOINTS[original_module_path_str]["module_path"] = str(module_path)
        ENDPOINTS[original_module_path_str]["model_name"] = model_name

        print(f"Generated Pydantic model for {schema_file} at {output_file}")

    # print(f"Generated {len(ENDPOINTS)} Pydantic models!")

    with open("../pymanifold/endpoints.json", "w+", encoding="utf-8") as f:
        json.dump(ENDPOINTS, f)

    return ENDPOINTS


def _file_to_endpoint(file_path: Path) -> tuple[str, dict]:
    return "/v0/" + str(file_path).replace(".py", "").replace("{", "[").replace(
        "}", "]"
    )


def _get_endpoints_from_api_doc(
    endpoints: dict[str, dict[str, str]] = {}
) -> dict[str, dict[str, str]]:
    """
    Get the list of endpoints from the Manfifold API docs.
    """
    print("Getting endpoints from API docs...")

    api_doc_path = "manifold" / API_DOC_PATH
    if not api_doc_path.exists():
        raise FileNotFoundError(f"API docs not found at {api_doc_path}")

    with api_doc_path.open("r", encoding="utf-8") as f:
        api_doc = f.read()

    md = mistune.markdown(api_doc, renderer="ast")

    for token in md:
        if (
            token["type"] == "heading"
            and token["attrs"]["level"] == 3
            and token["children"][0]["type"] == "codespan"
        ):
            if len(token["children"]) > 1:
                deprecated = (
                    token["children"][1]["raw"].lower().strip("(").strip(")").strip(" ")
                )
                if deprecated == DEPRECATED:
                    continue
            _ = token["children"][0]["raw"]
            method = _.split(" ")[0]
            endpoint = _.split(" ")[1]

            endpoints[endpoint] = {
                "method": method,
            }

    print("Successfully got endpoints from API docs!")
    print(f"Found {len(endpoints)} endpoints")
    return endpoints


def run_command(cmd, cwd=None):
    """Run a command and return its output"""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, capture_output=True, text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command {' '.join(cmd)}")
        print(f"Error output: {e.stderr}")
        raise


def clone_manifold():
    """
    Clone the manifold repository sparsely and return the path to the common directory
    """
    # TODO: Update this to the actual repo
    repo_url = "https://github.com/iameskild/manifold.git"
    if os.path.exists("manifold"):
        print("Removing existing manifold directory...")
        shutil.rmtree("manifold")

    print("Initializing sparse clone of manifold repository...")
    os.makedirs("manifold")

    run_command(["git", "init"], cwd="manifold")
    run_command(["git", "remote", "add", "origin", repo_url], cwd="manifold")
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd="manifold")

    # Set up sparse-checkout to only include common directory
    sparse_checkout_path = os.path.join("manifold", ".git", "info", "sparse-checkout")
    with open(sparse_checkout_path, "w") as f:
        f.write("common\n")
        f.write("docs/docs/api.md\n")  # api.md
        f.write("!twitch-bot\n")  # ignore twitch-bot directory

    print("Fetching required files...")
    run_command(["git", "pull", "origin", "main"], cwd="manifold")

    print("Successfully cloned manifold/common directory!")


def create_json_schema():
    """
    Create JSON schema by copying gen-json-schema.ts and running it
    """
    # Copy gen-json-schema.ts to manifold/common
    shutil.copy("scripts/gen-json-schema.ts", "manifold/common")

    # Install required packages in manifold/common
    print("Installing required packages...")
    run_command(["yarn", "install"], cwd="manifold/common")

    # Run the schema generation script
    print("Generating JSON schema...")
    run_command(["npx", "ts-node", "gen-json-schema.ts"], cwd="manifold/common")

    print("Successfully generated JSON schema!")


if __name__ == "__main__":
    clone_manifold()
    create_json_schema()
    make_models()
