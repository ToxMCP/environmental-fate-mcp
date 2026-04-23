import shutil
from pathlib import Path

from pydantic import BaseModel

from fate_mcp.errors import FateValidationError
from fate_mcp.models import EnvironmentalReleaseScenario, FateModelRunOptions
from fate_mcp.plugins.external_result_adapter import ExternalEngineResultPayload, load_external_payload


class HeadlessEngineConfig(BaseModel):
    engine_id: str
    executable_name: str
    expected_version: str
    output_format: str = "csv"


class HeadlessEngineWrapper:
    def __init__(self, config: HeadlessEngineConfig):
        self.config = config

    def check_dependencies(self) -> str:
        executable_path = shutil.which(self.config.executable_name)
        if not executable_path:
            raise FateValidationError(
                code="headless_engine_missing",
                message=f"Required executable '{self.config.executable_name}' for engine '{self.config.engine_id}' was not found in PATH.",
                suggestion=f"Install {self.config.engine_id} or update the system PATH to include {self.config.executable_name}.",
                details={"engineId": self.config.engine_id, "executableName": self.config.executable_name}
            )
        return executable_path

    def run(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
        output_dir: Path,
    ) -> ExternalEngineResultPayload:
        self.check_dependencies()

        # In a real implementation, we would write scenario inputs to a native engine format
        # and invoke the executable:
        # subprocess.run([executable_path, input_path, "--out", output_dir], check=True)
        # 
        # Here we mock the behavior for the harness by looking for a pre-generated fixture
        # or raising an execution failure to demonstrate the deterministic contract.

        output_file = output_dir / f"output.{self.config.output_format}"
        
        # Mocking an execution failure if the environment variable or some condition triggers it.
        # But for deterministic testing, we just check if output_file got "created".
        if not output_file.exists():
            raise FateValidationError(
                code="headless_engine_execution_failed",
                message=f"Engine '{self.config.engine_id}' failed to produce expected output at {output_file.name}.",
                suggestion="Check engine logs and ensure scenario inputs are valid for this model family.",
                details={"engineId": self.config.engine_id, "expectedOutput": output_file.name}
            )

        try:
            return load_external_payload(output_file)
        except FateValidationError as e:
            # Wrap parse errors as bad engine output
            raise FateValidationError(
                code="headless_engine_bad_output",
                message=f"Failed to normalize output from '{self.config.engine_id}': {e.payload.message}",
                suggestion="Ensure the engine is producing the agreed-upon export format.",
                details={"engineId": self.config.engine_id, "originalError": e.payload.code}
            ) from e
