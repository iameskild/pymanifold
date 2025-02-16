from hatchling.builders.hooks.plugin.interface import BuildHookInterface
import subprocess
import sys
from pathlib import Path
import pkg_resources


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        """Run the model generation script before building."""
        # Ensure required dependencies are installed
        required_packages = ["mistune", "datamodel-code-generator"]
        for package in required_packages:
            try:
                pkg_resources.require(package)
            except pkg_resources.DistributionNotFound:
                print(f"Installing required dependency: {package}")
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])

        script_path = Path("scripts/make_models.py")

        if not script_path.exists():
            print(f"Warning: {script_path} not found", file=sys.stderr)
            return

        try:
            subprocess.run([sys.executable, str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error running make_models.py: {e}", file=sys.stderr)
            raise
