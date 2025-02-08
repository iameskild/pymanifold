import json
import re
from pathlib import Path
import subprocess
import shutil
import logging
import tempfile
from typing import Dict, Optional
import sys
import os

import mistune

SCHEMA_INPUT = Path("schemas")
PYDANTIC_OUTPUT = Path("pymanifold/models")
API_DOC_PATH = Path("docs/docs/api.md")
GENERATED_SCHEMA_SCRIPT = Path("genJsonSchema.ts")
REPO_ROOT = Path(__file__).parent.parent

DEPRECATED = "deprecated"
MANIFOLD_REPO_URL = "https://github.com/iameskild/manifold.git"

DEBUG = os.getenv("DEBUG", "").lower() == "true"

ENDPOINT_VARIATIONS = {
    # Original -> Variations
    "marketId": ["id", "contractId"],
    "marketSlug": ["slug"],
}

logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _normalize_endpoint(endpoint: str) -> list[str]:
    """
    Generate all possible variations of an endpoint.

    Args:
        endpoint: Original endpoint string

    Returns:
        List of possible endpoint variations
    """
    variations = [endpoint]

    for original, replacements in ENDPOINT_VARIATIONS.items():
        for replacement in replacements:
            # Create new variations by replacing each occurrence
            new_variations = []
            for variant in variations:
                if original in variant:
                    new_variations.append(variant.replace(original, replacement))
            variations.extend(new_variations)

    return list(set(variations))  # Remove duplicates


def _file_to_endpoint(file_path: Path) -> str:
    """Convert file path to endpoint format with all possible variations."""
    base_endpoint = "/v0/" + str(file_path).replace(".py", "").replace(
        "{", "["
    ).replace("}", "]")
    return base_endpoint


def make_models(temp_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Generate Pydantic models from JSON schemas using datamodel-codegen.

    Args:
        temp_dir: Path to temporary directory containing schemas
    """
    ENDPOINTS: Dict[str, Dict[str, str]] = _get_endpoints_from_api_doc(temp_dir)
    schema_dir = temp_dir / SCHEMA_INPUT

    # Create a reverse mapping of all possible variations to their original endpoints
    variation_map = {}
    for endpoint, data in ENDPOINTS.items():
        variations = _normalize_endpoint(endpoint)
        for variant in variations:
            variation_map[variant] = endpoint

    for schema_file in schema_dir.rglob("*.json"):
        relative_path = schema_file.relative_to(schema_dir)
        module_path = relative_path.with_suffix("")
        print(module_path)

        # Get the endpoint from file path and check all its variations
        file_endpoint = _file_to_endpoint(module_path)
        original_endpoint = variation_map.get(file_endpoint)

        if not original_endpoint:
            logger.debug(f"No matching endpoint found for schema: {file_endpoint}")
            continue

        # Clean up and ensure valid Python module names
        module_path_str = module_path.as_posix()
        module_path_str = re.sub(r"[^a-zA-Z0-9_/]", "_", module_path_str)
        module_path_str = module_path_str.replace("/_", "/")
        output_path = REPO_ROOT / PYDANTIC_OUTPUT / (module_path_str + ".py")
        output_file = str(output_path).replace("_.py", "__.py")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create __init__.py files in each directory
        current_dir = output_path.parent
        while (
            current_dir != (REPO_ROOT / PYDANTIC_OUTPUT)
            and current_dir != current_dir.parent
        ):
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
            output_file.replace(str(REPO_ROOT / PYDANTIC_OUTPUT / ""), "")
            .replace(".py", "")
            .replace("/", ".")
        )

        ENDPOINTS[original_endpoint]["module_path"] = module_path
        ENDPOINTS[original_endpoint]["model_name"] = model_name

        logger.info(f"Generated Pydantic model for {schema_file} at {output_file}")

    with open(REPO_ROOT / "pymanifold/endpoints.json", "w+", encoding="utf-8") as f:
        json.dump(ENDPOINTS, f)

    return ENDPOINTS


def clone_manifold(temp_dir: Path) -> None:
    """
    Perform a sparse clone of the Manifold repository.

    Args:
        temp_dir: Path to temporary directory for cloning
    """
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True, exist_ok=True)

    manifold_dir = temp_dir / "manifold"
    manifold_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Initializing sparse clone of manifold repository...")

    run_command(["git", "init"], cwd=manifold_dir, debug=DEBUG)
    run_command(
        ["git", "remote", "add", "origin", MANIFOLD_REPO_URL],
        cwd=manifold_dir,
        debug=DEBUG,
    )
    run_command(
        ["git", "config", "core.sparseCheckout", "true"], cwd=manifold_dir, debug=DEBUG
    )

    sparse_checkout_path = manifold_dir / ".git/info/sparse-checkout"
    sparse_checkout_path.parent.mkdir(parents=True, exist_ok=True)
    with open(sparse_checkout_path, "w") as f:
        f.write("common\n")
        f.write("docs/docs/api.md\n")
        f.write("!twitch-bot/common\n")

    logger.info("Fetching required files...")
    run_command(["git", "pull", "origin", "main"], cwd=manifold_dir, debug=DEBUG)
    logger.info("Successfully cloned manifold repository")


def create_json_schema(temp_dir: Path) -> None:
    """
    Generate JSON schema from TypeScript definitions.

    Args:
        temp_dir: Path to temporary directory containing manifold clone
    """
    common_dir = temp_dir / "manifold/common"
    script_source = REPO_ROOT / "scripts" / GENERATED_SCHEMA_SCRIPT
    script_dest = common_dir / GENERATED_SCHEMA_SCRIPT

    shutil.copy(script_source, script_dest)

    logger.info("Installing required packages...")
    run_command(["yarn", "install"], cwd=common_dir, debug=DEBUG)
    run_command(["yarn", "add", "typescript"], cwd=common_dir, debug=DEBUG)
    run_command(["yarn", "add", "ts-node"], cwd=common_dir, debug=DEBUG)

    logger.info("Generating JSON schema...")
    run_command(
        ["npx", "ts-node", GENERATED_SCHEMA_SCRIPT], cwd=common_dir, debug=DEBUG
    )
    logger.info("Successfully generated JSON schema")


def _get_endpoints_from_api_doc(temp_dir: Path) -> Dict[str, Dict[str, str]]:
    """
    Parse the Manifold API documentation to extract endpoint information.

    Args:
        temp_dir: Path to temporary directory containing manifold clone
    """
    logger.info("Getting endpoints from API docs...")
    endpoints: Dict[str, Dict[str, str]] = {}

    api_doc_path = temp_dir / "manifold" / API_DOC_PATH
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


def run_command(
    cmd: list[str], cwd: Optional[str | Path] = None, debug: bool = False
) -> str:
    """
    Run a command and return its output.

    Args:
        cmd: Command to run as list of strings
        cwd: Working directory for the command
        debug: If True, print command output to stdout/stderr
    """
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        output = []
        while True:
            stdout_line = process.stdout.readline()
            stderr_line = process.stderr.readline()

            if stdout_line:
                if debug:
                    print(stdout_line.rstrip())
                output.append(stdout_line)
            if stderr_line:
                if debug:
                    print(stderr_line.rstrip(), file=sys.stderr)

            if process.poll() is not None:
                # Get remaining lines
                for line in process.stdout.readlines():
                    if debug:
                        print(line.rstrip())
                    output.append(line)
                for line in process.stderr.readlines():
                    if debug:
                        print(line.rstrip(), file=sys.stderr)
                break

        return_code = process.wait()
        if return_code != 0:
            raise subprocess.CalledProcessError(return_code, cmd)

        return "".join(output)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command {' '.join(cmd)}")
        raise e


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        logger.info("### Cloning Manifold repository ###")
        clone_manifold(temp_path)
        logger.info("### Generating JSON schema ###")
        create_json_schema(temp_path)
        logger.info("### Generating Pydantic models ###")
        make_models(temp_path)
