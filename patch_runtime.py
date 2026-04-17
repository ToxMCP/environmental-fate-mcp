import re
import os

with open("src/fate_mcp/runtime.py", "r") as f:
    content = f.read()

# Add imports
if "ProbabilisticConcentrationResult" not in content:
    content = content.replace(
        "from fate_mcp.models import (",
        "from fate_mcp.models import (\n    ProbabilisticConcentrationResult,\n    ProbabilisticSurfaceSummary,"
    )
    content = "import random\nimport statistics\nimport copy\n" + content

new_method = """    def estimate_probabilistic(
        self,
        scenario: EnvironmentalReleaseScenario,
        run_options: FateModelRunOptions,
        iterations: int = 100,
        seed: int | None = None,
    ) -> ProbabilisticConcentrationResult:
        if scenario.geographic_scope.region_id != run_options.region_profile_id:
            raise FateValidationError(
                code="region_profile_mismatch",
                message="Run options region profile must match the scenario geographic scope.",
                suggestion="Align the scenario region and run options region_profile_id.",
            )
        
        plugin = self.plugins.resolve(run_options.run_mode, run_options.model_family)
        
        rng = random.Random(seed if seed is not None else 42)
        
        # Identify parameters with distributions
        dist_params = [p for p in scenario.parameter_records if p.distribution is not None]
        
        if not dist_params:
            raise FateValidationError(
                code="probabilistic_orchestration_missing_distributions",
                message="No parameter distributions found in scenario.",
                suggestion="Provide ParameterDistribution entries for uncertain parameters.",
            )
            
        completed_iterations = 0
        failed_iterations = 0
        iteration_surfaces = {} # (medium, compartment, bucket) -> list of surfaces
        
        run_summary = None
        assumptions = None
        
        for _ in range(iterations):
            # Sample parameters
            sampled_records = []
            for p in scenario.parameter_records:
                if p.distribution:
                    # Simple sampling logic for MVP
                    dist_type = p.distribution.distribution_type
                    val = p.value
                    if dist_type == "lognormal":
                        # parameters might be mu, sigma
                        mu = p.distribution.parameters.get("mu", 0.0)
                        sigma = p.distribution.parameters.get("sigma", 1.0)
                        val = rng.lognormvariate(mu, sigma)
                    elif dist_type == "normal":
                        mu = p.distribution.parameters.get("mu", p.value)
                        sigma = p.distribution.parameters.get("sigma", p.value * 0.1)
                        val = rng.gauss(mu, sigma)
                    elif dist_type == "uniform":
                        low = p.distribution.parameters.get("low", p.value * 0.5)
                        high = p.distribution.parameters.get("high", p.value * 1.5)
                        val = rng.uniform(low, high)
                        
                    # bounds check
                    if p.distribution.bounds and len(p.distribution.bounds) == 2:
                        val = max(p.distribution.bounds[0], min(p.distribution.bounds[1], val))
                        
                    new_p = p.model_copy(update={"value": val})
                    sampled_records.append(new_p)
                else:
                    sampled_records.append(p)
                    
            scenario_copy = scenario.model_copy(update={"parameter_records": sampled_records})
            
            try:
                res = plugin.run(scenario_copy, run_options)
                completed_iterations += 1
                if run_summary is None:
                    run_summary = res.run_summary
                    assumptions = res.assumptions
                    
                for s in res.surfaces:
                    key = (s.medium.value, s.compartment.value, s.time_window.bucket_label)
                    if key not in iteration_surfaces:
                        iteration_surfaces[key] = []
                    iteration_surfaces[key].append(s)
            except Exception:
                failed_iterations += 1
                
        if completed_iterations == 0:
            raise FateValidationError(
                code="probabilistic_orchestration_failed",
                message="All iterations failed.",
                suggestion="Check parameter bounds and run options.",
            )
            
        # Aggregate
        median_surfaces = []
        p90_surfaces = []
        p95_surfaces = []
        surface_summaries = []
        
        for key, surfaces in iteration_surfaces.items():
            vals = [s.concentration_value for s in surfaces]
            vals.sort()
            
            med_val = statistics.median(vals)
            p90_idx = int(len(vals) * 0.90)
            p95_idx = int(len(vals) * 0.95)
            
            # safeguard bounds
            p90_idx = min(p90_idx, len(vals) - 1)
            p95_idx = min(p95_idx, len(vals) - 1)
            
            p90_val = vals[p90_idx]
            p95_val = vals[p95_idx]
            
            # just pick the first surface as a template and overwrite value
            base = surfaces[0]
            median_surfaces.append(base.model_copy(update={"concentration_value": med_val}))
            p90_surfaces.append(base.model_copy(update={"concentration_value": p90_val}))
            p95_surfaces.append(base.model_copy(update={"concentration_value": p95_val}))
            
            surface_summaries.append(
                ProbabilisticSurfaceSummary(
                    surface_id=base.surface_id,
                    medium=base.medium,
                    compartment=base.compartment,
                    concentration_unit=base.concentration_unit,
                    median_value=med_val,
                    p90_value=p90_val,
                    p95_value=p95_val
                )
            )

        return ProbabilisticConcentrationResult(
            median_surfaces=median_surfaces,
            p90_surfaces=p90_surfaces,
            p95_surfaces=p95_surfaces,
            surface_summaries=surface_summaries,
            iteration_count=iterations,
            completed_iteration_count=completed_iterations,
            failed_iteration_count=failed_iterations,
            sampling_seed=seed,
            sampled_parameter_count=len(dist_params),
            dominant_uncertainty_drivers=[p.parameter for p in dist_params],
            uncertainty_limitation_lines=["Probabilistic orchestration completed with basic parameter sampling."],
            run_summary=run_summary,
            assumptions=assumptions
        )
"""

if "def estimate_probabilistic" not in content:
    content = content.replace("    def reconcile_release_evidence", new_method + "\n    def reconcile_release_evidence")

with open("src/fate_mcp/runtime.py", "w") as f:
    f.write(content)
print("done")
