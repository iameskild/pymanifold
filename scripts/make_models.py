import json
import re
from pathlib import Path
import subprocess
import os
import shutil
import logging
from typing import Dict, Optional

import mistune

SCHEMA_INPUT = Path("schemas")
PYDANTIC_OUTPUT = Path("pymanifold/models")
API_DOC_PATH = Path("docs/docs/api.md")
GENERATED_SCHEMA_SCRIPT = Path("genJsonSchema.ts")

DEPRECATED = "deprecated"
MANIFOLD_REPO_URL = "https://github.com/iameskild/manifold.git"


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def make_models() -> Dict[str, Dict[str, str]]:
    """
    Generate Pydantic models from JSON schemas using datamodel-codegen.

    Reads JSON schema files from the schemas directory and generates corresponding
    Pydantic models in the pymanifold/models directory. Also creates a mapping of
    API endpoints to their corresponding module paths and model names.

    Returns:
        Dict[str, Dict[str, str]]: Mapping of endpoints to their metadata including
            module paths and endpoint methods.
    """
    ENDPOINTS: Dict[str, Dict[str, str]] = _get_endpoints_from_api_doc()

    for schema_file in SCHEMA_INPUT.rglob("*.json"):
        relative_path = schema_file.relative_to(SCHEMA_INPUT)
        module_path = relative_path.with_suffix("")

        # Clean up and ensure valid Python module names
        original_module_path_str = _file_to_endpoint(module_path)
        module_path_str = module_path.as_posix()
        module_path_str = re.sub(r"[^a-zA-Z0-9_/]", "_", module_path_str)
        module_path_str = module_path_str.replace("/_", "/")
        output_path = PYDANTIC_OUTPUT / (module_path_str + ".py")
        output_file = str(output_path).replace("_.py", "__.py")

        if original_module_path_str not in ENDPOINTS.keys():
            continue

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create __init__.py files in each directory
        current_dir = output_path.parent
        while current_dir != PYDANTIC_OUTPUT and current_dir != current_dir.parent:
            init_file = current_dir / "__init__.py"
            if not init_file.exists():
                init_file.touch()
            current_dir = current_dir.parent

        # Generate the Pydantic model
        run_command(
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

        logger.info(f"Generated Pydantic model for {schema_file} at {output_file}")

    with open("../pymanifold/endpoints.json", "w+", encoding="utf-8") as f:
        json.dump(ENDPOINTS, f)

    return ENDPOINTS


def clone_manifold() -> None:
    """
    Perform a sparse clone of the Manifold repository.
    """
    if os.path.exists("manifold"):
        logger.info("Removing existing manifold directory...")
        shutil.rmtree("manifold")

    logger.info("Initializing sparse clone of manifold repository...")
    os.makedirs("manifold")

    run_command(["git", "init"], cwd="manifold")
    run_command(["git", "remote", "add", "origin", MANIFOLD_REPO_URL], cwd="manifold")
    run_command(["git", "config", "core.sparseCheckout", "true"], cwd="manifold")

    sparse_checkout_path = os.path.join("manifold", ".git", "info", "sparse-checkout")
    with open(sparse_checkout_path, "w") as f:
        f.write("common\n")
        f.write("docs/docs/api.md\n")
        f.write("!twitch-bot\n")

    logger.info("Fetching required files...")
    run_command(["git", "pull", "origin", "main"], cwd="manifold")
    logger.info("Successfully cloned manifold repository")


def create_json_schema() -> None:
    """
    Generate JSON schema from TypeScript definitions.

    Copies the schema generation script to the manifold/common directory,
    installs required dependencies, and runs the schema generation script.
    """
    dir = Path("manifold/common")
    shutil.copy(f"scripts/{GENERATED_SCHEMA_SCRIPT}", dir)

    logger.info("Installing required packages...")
    run_command(["yarn", "install"], cwd=dir)

    logger.info("Generating JSON schema...")
    run_command(["npx", "ts-node", GENERATED_SCHEMA_SCRIPT], cwd=dir)
    logger.info("Successfully generated JSON schema")


def _file_to_endpoint(file_path: Path) -> str:
    return "/v0/" + str(file_path).replace(".py", "").replace("{", "[").replace(
        "}", "]"
    )


def _get_endpoints_from_api_doc() -> Dict[str, Dict[str, str]]:
    """
    Parse the Manifold API documentation to extract endpoint information.

    Reads the API documentation markdown file and extracts endpoint paths and their
    HTTP methods, excluding deprecated endpoints.

    Returns:
        Dict[str, Dict[str, str]]: Mapping of endpoints to their metadata
    """
    logger.info("Getting endpoints from API docs...")
    endpoints: Dict[str, Dict[str, str]] = {}

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

    logger.info(f"Found {len(endpoints)} endpoints in API documentation")
    return endpoints


def run_command(cmd: list[str], cwd: Optional[str] = None) -> str:
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, check=True, capture_output=True, text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command {' '.join(cmd)}")
        logger.error(f"Error output: {e.stderr}")
        raise


if __name__ == "__main__":
    logger.info("### Cloning Manifold repository ###")
    clone_manifold()
    logger.info("### Generating JSON schema ###")
    create_json_schema()
    logger.info("### Generating Pydantic models ###")
    make_models()
