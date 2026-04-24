from __future__ import annotations

import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fate_mcp.errors import FateRegistryError
from fate_mcp.models import (
    AdapterUnitConversionRule,
    Compartment,
    FateParameterPolicy,
    FateParameterPolicyFamily,
    FateRegionProfile,
    Media,
    ModelFamily,
    ModelFamilyApplicabilityProfile,
    ModelFamilyComparisonProfile,
    ModelFamilyComparisonProfileManifest,
    ModelFamilyComparisonOutcome,
    ModelFamilyComparisonReviewChecklistTemplate,
    ModelFamilyChallengeReviewChecklistTemplate,
    ModelFamilyChallengeReviewProfile,
    ModelFamilyChallengeReviewProfileManifest,
    ModelFamilySelectionProfile,
    ModelFamilySelectionProfileManifest,
    ModelFamilySelectionReviewChecklistTemplate,
    ModelFamilySelectionStatus,
    ScientificReferenceCase,
    ScientificReferenceCaseManifest,
    ScientificReviewChecklistTemplate,
    ScientificValidationClaim,
    ScientificValidationClaimManifest,
    ScientificValidationClaimPriority,
    ScientificReviewProfile,
    ScientificReviewProfileManifest,
    RegulatoryHandoffConsumerAlias,
    RegulatoryHandoffConsumerAliasConflict,
    RegulatoryHandoffConsumerAliasManifest,
    RegulatoryHandoffReviewChecklistTemplate,
    RegulatoryHandoffProfileRecommendation,
    RegulatoryHandoffProfile,
    RegulatoryHandoffTargetMapping,
    RegulatoryHandoffTargetMatrixManifest,
    SourceReference,
)
from fate_mcp.package_metadata import DEFAULTS_VERSION


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalize_lookup_value(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def _candidate_profile_aliases(profile: RegulatoryHandoffProfile) -> list[str]:
    return [profile.target_module, profile.profile_id, *profile.consumer_hints]


@dataclass(frozen=True)
class MediaDefaults:
    compartment: Compartment
    capacity_parameter: str
    degradation_half_life_parameter: str
    unit: str
    advective_residence_time_parameter: str | None = None


@dataclass(frozen=True)
class TemperatureCorrectionPolicy:
    reference_temperature_c: float
    minimum_supported_temperature_c: float
    maximum_supported_temperature_c: float
    degradation_q10_by_medium: dict[Media, float]
    correction_strategy: str
    applicability_note: str | None = None

    def clamp_temperature(self, temperature_c: float) -> float:
        return min(
            max(temperature_c, self.minimum_supported_temperature_c),
            self.maximum_supported_temperature_c,
        )


@dataclass(frozen=True)
class ProbabilisticReviewPolicy:
    minimum_completed_iterations_for_percentiles: int
    max_failed_iteration_fraction_for_ready_review: float


@dataclass(frozen=True)
class AdapterConcentrationNormalization:
    value: float
    unit: str
    was_converted: bool
    source_basis: str | None = None
    canonical_basis: str | None = None

    @property
    def basis_conversion_applied(self) -> bool:
        return (
            self.source_basis is not None
            and self.canonical_basis is not None
            and self.source_basis != self.canonical_basis
        )


class DefaultsRegistry:
    def __init__(self, repo_root: Path, verify_defaults_manifest: bool = True) -> None:
        self.repo_root = repo_root
        self.defaults_root = repo_root / "defaults"
        self.version_root = self.defaults_root / DEFAULTS_VERSION
        self.extensions_root = self.defaults_root / "extensions"
        self.verify_defaults_manifest = verify_defaults_manifest
        if verify_defaults_manifest:
            self._verify_manifest()
        self.core_defaults = _load_json(self.version_root / "core_defaults.json")
        self.physchem_parameter_policies = _load_json(
            self.version_root / "physchem_parameter_policies.json"
        )
        self.adapter_unit_conversions = _load_json(
            self.version_root / "adapter_unit_conversions.json"
        )
        self.model_family_applicability_profiles = _load_json(
            self.version_root / "model_family_applicability_profiles.json"
        )
        self.model_family_comparison_profiles = _load_json(
            self.version_root / "model_family_comparison_profiles.json"
        )
        self.model_family_selection_profiles = _load_json(
            self.version_root / "model_family_selection_profiles.json"
        )
        self.model_family_challenge_review_profiles = _load_json(
            self.version_root / "model_family_challenge_review_profiles.json"
        )
        self.scientific_validation_claims = _load_json(
            self.version_root / "scientific_validation_claims.json"
        )
        self.scientific_reference_cases = _load_json(
            self.version_root / "scientific_reference_cases.json"
        )
        self.scientific_review_profiles = _load_json(
            self.version_root / "scientific_review_profiles.json"
        )
        self.regulatory_handoff_profiles = _load_json(
            self.version_root / "regulatory_handoff_profiles.json"
        )
        self.region_profiles = self._load_region_profiles()
        self.reconciliation_thresholds = _load_json(
            self.version_root / "reconciliation_thresholds.json"
        )

    def _verify_manifest(self) -> None:
        manifest_path = self.defaults_root / "manifest.json"
        if not manifest_path.exists():
            raise FateRegistryError(
                code="missing_defaults_manifest",
                message="Defaults manifest is missing and cannot be verified at load time.",
                suggestion=(
                    "Regenerate defaults artifacts or disable verify_defaults_manifest only while "
                    "rewriting governed defaults files."
                ),
            )
        manifest_payload = _load_json(manifest_path)
        failures: list[str] = []
        for entry in manifest_payload.get("files", []):
            relative_path = entry.get("path")
            expected_sha = entry.get("sha256")
            if not relative_path or not expected_sha:
                failures.append("defaults manifest contains an entry without path/sha256 metadata")
                continue
            target_path = self.repo_root / relative_path
            if not target_path.exists():
                failures.append(f"{relative_path}: file listed in defaults manifest is missing")
                continue
            actual_sha = _sha256(target_path)
            if actual_sha != expected_sha:
                failures.append(
                    f"{relative_path}: sha256 mismatch (expected {expected_sha}, got {actual_sha})"
                )
        if failures:
            raise FateRegistryError(
                code="defaults_manifest_verification_failed",
                message="Defaults manifest verification failed at load time.",
                suggestion=(
                    "Regenerate defaults artifacts after updating governed JSON files, or disable "
                    "verify_defaults_manifest only inside artifact regeneration flows."
                ),
                details={
                    "failureCount": len(failures),
                    "failures": failures,
                },
            )

    def _resolve_parameter_policy_payload(self, parameter: str) -> tuple[dict[str, Any], str | None] | None:
        payload = self.physchem_parameter_policies["parameters"].get(parameter)
        if not payload:
            return None
        family = payload.get("family")
        if not family:
            return dict(payload), None
        family_payload = self.physchem_parameter_policies.get("families", {}).get(family)
        if not family_payload:
            raise FateRegistryError(
                code="unknown_parameter_policy_family",
                message=f"Parameter policy {parameter} references unknown family {family}.",
                suggestion="Declare the policy family in defaults/v1/physchem_parameter_policies.json.",
            )
        resolved = dict(family_payload)
        resolved.update({key: value for key, value in payload.items() if key != "family"})
        return resolved, family

    def _load_region_profiles(self) -> dict[str, Any]:
        base_payload = _load_json(self.version_root / "region_profiles.json")
        profiles = list(base_payload["profiles"])
        if self.extensions_root.exists():
            for extension_path in sorted(self.extensions_root.glob("*.json")):
                extension_payload = _load_json(extension_path)
                profiles.extend(extension_payload.get("profiles", []))
        return {
            "defaultsVersion": base_payload.get("defaultsVersion", DEFAULTS_VERSION),
            "profiles": profiles,
        }

    def parameter_record(self, parameter: str) -> dict[str, Any]:
        try:
            return self.core_defaults["parameters"][parameter]
        except KeyError as exc:
            raise FateRegistryError(
                code="missing_default_parameter",
                message=f"Unknown default parameter: {parameter}",
                suggestion="Check the defaults manifest or add the missing parameter.",
            ) from exc

    def parameter_value(self, parameter: str) -> float:
        value = self.parameter_record(parameter)["value"]
        return float(value)

    def parameter_source_references(self, parameter: str) -> list[SourceReference]:
        record = self.parameter_record(parameter)
        source_references = record.get("sourceReferences", [])
        if source_references:
            return [SourceReference(**item) for item in source_references]
        return [
            SourceReference(
                source_id=record["sourceId"],
                title=record["title"],
                effective_date=record.get("effectiveDate"),
            )
        ]

    def parameter_source_reference(self, parameter: str) -> SourceReference:
        return self.parameter_source_references(parameter)[0]

    def parameter_evidence_tier(self, parameter: str) -> str | None:
        return self.parameter_record(parameter).get("evidenceTier")

    def parameter_derivation_metadata(self, parameter: str) -> dict[str, Any]:
        return dict(self.parameter_record(parameter).get("derivationMetadata", {}))

    def media_defaults(self, medium: Media) -> MediaDefaults:
        try:
            entry = self.core_defaults["mediaDefaults"][medium.value]
        except KeyError as exc:
            raise FateRegistryError(
                code="unsupported_medium",
                message=f"Unsupported medium: {medium.value}",
                suggestion="Use one of the declared v0.1 media values.",
            ) from exc
        return MediaDefaults(
            compartment=Compartment(entry["compartment"]),
            capacity_parameter=entry["capacityParameter"],
            degradation_half_life_parameter=entry["degradationHalfLifeParameter"],
            advective_residence_time_parameter=entry.get("advectiveResidenceTimeParameter"),
            unit=entry["unit"],
        )

    def temperature_correction_policy(self) -> TemperatureCorrectionPolicy:
        payload = self.core_defaults["temperatureCorrectionPolicy"]
        degradation_q10_by_medium = {
            Media(key): float(value)
            for key, value in payload["degradationQ10ByMedium"].items()
        }
        return TemperatureCorrectionPolicy(
            reference_temperature_c=float(payload["referenceTemperatureC"]),
            minimum_supported_temperature_c=float(payload["minimumSupportedTemperatureC"]),
            maximum_supported_temperature_c=float(payload["maximumSupportedTemperatureC"]),
            degradation_q10_by_medium=degradation_q10_by_medium,
            correction_strategy=payload["correctionStrategy"],
            applicability_note=payload.get("applicabilityNote"),
        )

    def probabilistic_review_policy(self) -> ProbabilisticReviewPolicy:
        payload = self.core_defaults["probabilisticReviewPolicy"]
        return ProbabilisticReviewPolicy(
            minimum_completed_iterations_for_percentiles=int(
                payload["minimumCompletedIterationsForPercentiles"]
            ),
            max_failed_iteration_fraction_for_ready_review=float(
                payload["maxFailedIterationFractionForReadyReview"]
            ),
        )

    def get_region_profile(self, region_id: str) -> dict[str, Any]:
        for profile in self.region_profiles["profiles"]:
            if profile["regionId"] == region_id:
                return profile
        raise FateRegistryError(
            code="unknown_region_profile",
            message=f"Unknown region profile: {region_id}",
            suggestion="Use a declared profile from defaults/v1/region_profiles.json.",
        )

    def region_scalar(self, region_id: str, compartment: Compartment) -> float:
        profile = self.get_region_profile(region_id)
        try:
            scalar = float(profile["compartmentScalars"][compartment.value])
        except KeyError as exc:
            raise FateRegistryError(
                code="unsupported_region_compartment",
                message=f"Region profile {region_id} does not define {compartment.value}",
                suggestion="Choose a compatible region profile or add an extension pack.",
            ) from exc
        if not math.isfinite(scalar) or scalar <= 0.0:
            raise FateRegistryError(
                code="invalid_region_scalar",
                message=(
                    f"Region profile {region_id} defines non-physical scalar {scalar} "
                    f"for compartment {compartment.value}."
                ),
                suggestion=(
                    "Use a finite positive compartment scalar in defaults/v1/region_profiles.json "
                    "or the relevant extension pack."
                ),
                details={
                    "regionId": region_id,
                    "compartment": compartment.value,
                    "scalar": scalar,
                },
            )
        return scalar

    def reconciliation_threshold(self, name: str) -> float:
        try:
            return float(self.reconciliation_thresholds["thresholds"][name]["value"])
        except KeyError as exc:
            raise FateRegistryError(
                code="unknown_reconciliation_threshold",
                message=f"Unknown reconciliation threshold: {name}",
                suggestion="Check defaults/v1/reconciliation_thresholds.json for declared thresholds.",
            ) from exc

    def list_region_profiles(self) -> list[FateRegionProfile]:
        profiles = []
        for profile in self.region_profiles["profiles"]:
            profiles.append(
                FateRegionProfile(
                    region_id=profile["regionId"],
                    display_name=profile["displayName"],
                    compartment_scalars=profile["compartmentScalars"],
                    known_gaps=profile.get("knownGaps", []),
                    source_pack=profile.get("sourcePack", "defaults/v1/region_profiles.json"),
                    applicability_note=profile.get("applicabilityNote"),
                )
            )
        return profiles

    def region_profile_manifest(self) -> dict[str, Any]:
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "profileCount": len(self.region_profiles["profiles"]),
            "profiles": [profile.model_dump(mode="json") for profile in self.list_region_profiles()],
        }

    def parameter_policy(self, parameter: str) -> FateParameterPolicy | None:
        resolved = self._resolve_parameter_policy_payload(parameter)
        if resolved is None:
            return None
        payload, family = resolved
        return FateParameterPolicy(
            parameter=parameter,
            family=family,
            expected_unit=payload["expectedUnit"],
            runtime_supported=bool(payload["runtimeSupported"]),
            conflict_relative_spread_threshold=float(payload["conflictRelativeSpreadThreshold"]),
            weighting_strategy=payload["weightingStrategy"],
            reconciliation_domain=payload.get("reconciliationDomain", "linear"),
            conflict_metric=payload.get("conflictMetric", "relative_spread"),
            disallow_conservative_empirical_blend=bool(
                payload.get("disallowConservativeEmpiricalBlend", False)
            ),
            source_pack=f"defaults/{DEFAULTS_VERSION}/physchem_parameter_policies.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_physchem_parameter_policies(self) -> list[FateParameterPolicy]:
        policies = []
        for parameter in sorted(self.physchem_parameter_policies["parameters"].keys()):
            policy = self.parameter_policy(parameter)
            if policy is not None:
                policies.append(policy)
        return policies

    def policy_family(self, family: str) -> FateParameterPolicyFamily | None:
        payload = self.physchem_parameter_policies.get("families", {}).get(family)
        if not payload:
            return None
        parameter_names = sorted(
            parameter
            for parameter, parameter_payload in self.physchem_parameter_policies["parameters"].items()
            if parameter_payload.get("family") == family
        )
        return FateParameterPolicyFamily(
            family=family,
            expected_unit=payload.get("expectedUnit"),
            runtime_supported=bool(payload["runtimeSupported"]),
            conflict_relative_spread_threshold=float(payload["conflictRelativeSpreadThreshold"]),
            weighting_strategy=payload["weightingStrategy"],
            reconciliation_domain=payload.get("reconciliationDomain", "linear"),
            conflict_metric=payload.get("conflictMetric", "relative_spread"),
            disallow_conservative_empirical_blend=bool(
                payload.get("disallowConservativeEmpiricalBlend", False)
            ),
            source_pack=f"defaults/{DEFAULTS_VERSION}/physchem_parameter_policies.json",
            parameter_names=parameter_names,
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_physchem_parameter_policy_families(self) -> list[FateParameterPolicyFamily]:
        families = []
        for family in sorted(self.physchem_parameter_policies.get("families", {}).keys()):
            policy_family = self.policy_family(family)
            if policy_family is not None:
                families.append(policy_family)
        return families

    def runtime_supported_parameter_units(self) -> dict[str, str]:
        return {
            policy.parameter: policy.expected_unit
            for policy in self.list_physchem_parameter_policies()
            if policy.runtime_supported
        }

    def physchem_parameter_policy_family_manifest(self) -> dict[str, Any]:
        families = self.list_physchem_parameter_policy_families()
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "familyCount": len(families),
            "families": [family.model_dump(mode="json") for family in families],
        }

    def physchem_parameter_policy_manifest(self) -> dict[str, Any]:
        policies = self.list_physchem_parameter_policies()
        families = self.list_physchem_parameter_policy_families()
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "familyCount": len(families),
            "policyCount": len(policies),
            "families": [family.model_dump(mode="json") for family in families],
            "policies": [policy.model_dump(mode="json") for policy in policies],
        }

    def adapter_unit_conversion_rule(self, compartment_code: str) -> AdapterUnitConversionRule | None:
        payload = self.adapter_unit_conversions["compartments"].get(compartment_code)
        if not payload:
            return None
        return AdapterUnitConversionRule(
            compartment_code=compartment_code,
            canonical_unit=payload["canonicalUnit"],
            canonical_basis=payload.get("canonicalBasis"),
            supported_units=sorted(payload["conversionFactorsToCanonical"].keys()),
            conversion_factors_to_canonical=payload["conversionFactorsToCanonical"],
            unit_basis_labels=payload.get("unitBasisLabels", {}),
            source_pack=f"defaults/{DEFAULTS_VERSION}/adapter_unit_conversions.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_adapter_unit_conversion_rules(self) -> list[AdapterUnitConversionRule]:
        rules = []
        for compartment_code in sorted(self.adapter_unit_conversions["compartments"].keys()):
            rule = self.adapter_unit_conversion_rule(compartment_code)
            if rule is not None:
                rules.append(rule)
        return rules

    def adapter_unit_conversion_manifest(self) -> dict[str, Any]:
        rules = self.list_adapter_unit_conversion_rules()
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "ruleCount": len(rules),
            "rules": [rule.model_dump(mode="json") for rule in rules],
        }

    def model_family_applicability_profile(
        self,
        model_family: str | ModelFamily,
    ) -> ModelFamilyApplicabilityProfile | None:
        model_family_value = (
            model_family.value if isinstance(model_family, ModelFamily) else model_family
        )
        payload = self.model_family_applicability_profiles["profiles"].get(model_family_value)
        if not payload:
            return None
        return ModelFamilyApplicabilityProfile(
            model_family=model_family_value,
            fit_for_purpose=payload.get("fitForPurpose", []),
            supported_substance_classes=payload.get("supportedSubstanceClasses", []),
            unsupported_substance_classes=payload.get("unsupportedSubstanceClasses", []),
            required_inputs=payload.get("requiredInputs", []),
            core_assumptions=payload.get("coreAssumptions", []),
            deferred_capabilities=payload.get("deferredCapabilities", []),
            review_notes=payload.get("reviewNotes", []),
            fit_score_threshold=float(payload.get("fitScoreThreshold", 0.75)),
            fit_score_penalties=payload.get("fitScorePenalties", {}),
            source_pack=f"defaults/{DEFAULTS_VERSION}/model_family_applicability_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_model_family_applicability_profiles(self) -> list[ModelFamilyApplicabilityProfile]:
        profiles = []
        for model_family in sorted(self.model_family_applicability_profiles["profiles"].keys()):
            profile = self.model_family_applicability_profile(model_family)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def model_family_applicability_manifest(self) -> dict[str, Any]:
        profiles = self.list_model_family_applicability_profiles()
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "profileCount": len(profiles),
            "profiles": [profile.model_dump(mode="json") for profile in profiles],
        }

    def scientific_validation_claim(self, claim_id: str) -> ScientificValidationClaim | None:
        payload = self.scientific_validation_claims["claims"].get(claim_id)
        if not payload:
            return None
        return ScientificValidationClaim(
            claim_id=claim_id,
            display_name=payload["displayName"],
            model_family=payload["modelFamily"],
            supported_run_modes=payload.get("supportedRunModes", []),
            fit_for_purpose=payload.get("fitForPurpose", []),
            statement=payload["statement"],
            claim_class=payload["claimClass"],
            priority=ScientificValidationClaimPriority(payload.get("priority", "high")),
            mandatory_for_release=payload.get("mandatoryForRelease", True),
            required_validation_tiers=payload.get("requiredValidationTiers", []),
            required_reference_types=payload.get("requiredReferenceTypes", []),
            source_references=[SourceReference(**item) for item in payload.get("sourceReferences", [])],
            reference_case_ids=payload.get("referenceCaseIds", []),
            methods_basis_lines=payload.get("methodsBasisLines", []),
            reference_case_lines=payload.get("referenceCaseLines", []),
            corroboration_status=payload.get("corroborationStatus", "none"),
            official_source_count=int(payload.get("officialSourceCount", 0)),
            jurisdiction_breadth=payload.get("jurisdictionBreadth", "none"),
            independent_evidence_families=payload.get("independentEvidenceFamilies", []),
            evidence_family=payload.get("evidenceFamily"),
            official_source_ids=payload.get("officialSourceIds", []),
            worksheet_artifact_path=payload.get("worksheetArtifactPath"),
            expected_output_artifact_path=payload.get("expectedOutputArtifactPath"),
            worksheet_status=payload.get("worksheetStatus"),
            last_reviewed_date=payload.get("lastReviewedDate"),
            tolerance_basis=payload.get("toleranceBasis"),
            next_corroboration_action=payload.get("nextCorroborationAction"),
            review_notes=payload.get("reviewNotes", []),
            plugin_code_references=payload.get("pluginCodeReferences", []),
            source_pack=f"defaults/{DEFAULTS_VERSION}/scientific_validation_claims.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_scientific_validation_claims(
        self,
        model_family: str | ModelFamily | None = None,
    ) -> list[ScientificValidationClaim]:
        model_family_value = None
        if model_family is not None:
            model_family_value = model_family.value if isinstance(model_family, ModelFamily) else model_family
        claims = []
        for claim_id in sorted(self.scientific_validation_claims["claims"].keys()):
            claim = self.scientific_validation_claim(claim_id)
            if claim is None:
                continue
            if model_family_value is not None and claim.model_family.value != model_family_value:
                continue
            claims.append(claim)
        return claims

    def scientific_validation_claim_manifest(self) -> ScientificValidationClaimManifest:
        claims = self.list_scientific_validation_claims()
        return ScientificValidationClaimManifest(
            claim_count=len(claims),
            mandatory_claim_count=sum(1 for claim in claims if claim.mandatory_for_release),
            claims=claims,
        )

    def scientific_reference_case(self, case_id: str) -> ScientificReferenceCase | None:
        payload = self.scientific_reference_cases["cases"].get(case_id)
        if not payload:
            return None
        return ScientificReferenceCase(
            case_id=case_id,
            display_name=payload["displayName"],
            model_families=payload.get("modelFamilies", []),
            jurisdictions=payload.get("jurisdictions", []),
            source_type=payload["sourceType"],
            evidence_family=payload.get("evidenceFamily"),
            official_source_ids=payload.get("officialSourceIds", []),
            last_reviewed_date=payload.get("lastReviewedDate"),
            summary_lines=payload.get("summaryLines", []),
            applicability_lines=payload.get("applicabilityLines", []),
            source_references=[SourceReference(**item) for item in payload.get("sourceReferences", [])],
            review_notes=payload.get("reviewNotes", []),
            source_pack=f"defaults/{DEFAULTS_VERSION}/scientific_reference_cases.json",
        )

    def list_scientific_reference_cases(
        self,
        model_family: str | ModelFamily | None = None,
    ) -> list[ScientificReferenceCase]:
        model_family_value = None
        if model_family is not None:
            model_family_value = model_family.value if isinstance(model_family, ModelFamily) else model_family
        cases = []
        for case_id in sorted(self.scientific_reference_cases["cases"].keys()):
            case = self.scientific_reference_case(case_id)
            if case is None:
                continue
            if model_family_value is not None and model_family_value not in {family.value for family in case.model_families}:
                continue
            cases.append(case)
        return cases

    def scientific_reference_case_manifest(self) -> ScientificReferenceCaseManifest:
        cases = self.list_scientific_reference_cases()
        return ScientificReferenceCaseManifest(
            case_count=len(cases),
            cases=cases,
        )

    def model_family_comparison_profile(self, profile_id: str) -> ModelFamilyComparisonProfile | None:
        payload = self.model_family_comparison_profiles["profiles"].get(profile_id)
        if not payload:
            return None
        return ModelFamilyComparisonProfile(
            profile_id=profile_id,
            display_name=payload["displayName"],
            base_model_family=payload["baseModelFamily"],
            candidate_model_family=payload["candidateModelFamily"],
            fit_for_purpose=payload.get("fitForPurpose", []),
            supported_run_modes=payload.get("supportedRunModes", []),
            material_relative_delta_threshold=float(payload["materialRelativeDeltaThreshold"]),
            material_absolute_delta_floor=float(payload["materialAbsoluteDeltaFloor"]),
            packet_template=payload.get("packetTemplate"),
            brief_template=payload.get("briefTemplate"),
            comparable_outcome_template=payload.get("comparableOutcomeTemplate"),
            divergence_outcome_template=payload.get("divergenceOutcomeTemplate"),
            review_needed_outcome_template=payload.get("reviewNeededOutcomeTemplate"),
            review_checklist=[
                ModelFamilyComparisonReviewChecklistTemplate(
                    code=item["code"],
                    prompt=item["prompt"],
                    rationale=item["rationale"],
                    evidence_hint_fields=item.get("evidenceHintFields", []),
                )
                for item in payload.get("reviewChecklist", [])
            ],
            review_packet_template=payload.get("reviewPacketTemplate"),
            review_brief_template=payload.get("reviewBriefTemplate"),
            ready_comparison_outcomes=[
                ModelFamilyComparisonOutcome(item)
                for item in payload.get("readyComparisonOutcomes", [])
            ],
            attention_outcomes=[
                ModelFamilyComparisonOutcome(item)
                for item in payload.get("attentionOutcomes", [])
            ],
            attention_if_any_checks_fail=payload.get("attentionIfAnyChecksFail", True),
            attention_if_candidate_experimental=payload.get("attentionIfCandidateExperimental", True),
            review_notes=payload.get("reviewNotes", []),
            source_pack=f"defaults/{DEFAULTS_VERSION}/model_family_comparison_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_model_family_comparison_profiles(self) -> list[ModelFamilyComparisonProfile]:
        profiles = []
        for profile_id in sorted(self.model_family_comparison_profiles["profiles"].keys()):
            profile = self.model_family_comparison_profile(profile_id)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def resolve_model_family_comparison_profile(
        self,
        base_model_family: str | ModelFamily,
        candidate_model_family: str | ModelFamily,
    ) -> ModelFamilyComparisonProfile | None:
        base_value = base_model_family.value if isinstance(base_model_family, ModelFamily) else base_model_family
        candidate_value = (
            candidate_model_family.value
            if isinstance(candidate_model_family, ModelFamily)
            else candidate_model_family
        )
        for profile in self.list_model_family_comparison_profiles():
            if (
                profile.base_model_family.value == base_value
                and profile.candidate_model_family.value == candidate_value
            ):
                return profile
        return None

    def model_family_comparison_profile_manifest(self) -> ModelFamilyComparisonProfileManifest:
        profiles = self.list_model_family_comparison_profiles()
        return ModelFamilyComparisonProfileManifest(
            profile_count=len(profiles),
            profiles=profiles,
        )

    def model_family_selection_profile(self, profile_id: str) -> ModelFamilySelectionProfile | None:
        payload = self.model_family_selection_profiles["profiles"].get(profile_id)
        if not payload:
            return None
        return ModelFamilySelectionProfile(
            profile_id=profile_id,
            display_name=payload["displayName"],
            fit_for_purpose=payload.get("fitForPurpose", []),
            supported_run_modes=payload.get("supportedRunModes", []),
            default_model_family=payload["defaultModelFamily"],
            challenge_model_family=payload["challengeModelFamily"],
            comparison_profile_id=payload["comparisonProfileId"],
            minimum_duration_days_for_challenge=float(payload.get("minimumDurationDaysForChallenge", 0.0)),
            trigger_parameter_names=payload.get("triggerParameterNames", []),
            default_recommendation_template=payload.get("defaultRecommendationTemplate"),
            challenge_recommendation_template=payload.get("challengeRecommendationTemplate"),
            review_needed_template=payload.get("reviewNeededTemplate"),
            review_checklist=[
                ModelFamilySelectionReviewChecklistTemplate(
                    code=item["code"],
                    prompt=item["prompt"],
                    rationale=item["rationale"],
                    evidence_hint_fields=item.get("evidenceHintFields", []),
                )
                for item in payload.get("reviewChecklist", [])
            ],
            review_packet_template=payload.get("reviewPacketTemplate"),
            review_brief_template=payload.get("reviewBriefTemplate"),
            ready_recommendation_statuses=[
                ModelFamilySelectionStatus(item)
                for item in payload.get("readyRecommendationStatuses", [])
            ],
            attention_statuses=[
                ModelFamilySelectionStatus(item)
                for item in payload.get("attentionStatuses", [])
            ],
            attention_if_any_checks_fail=payload.get("attentionIfAnyChecksFail", True),
            attention_if_challenge_experimental=payload.get("attentionIfChallengeExperimental", True),
            review_notes=payload.get("reviewNotes", []),
            source_pack=f"defaults/{DEFAULTS_VERSION}/model_family_selection_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_model_family_selection_profiles(self) -> list[ModelFamilySelectionProfile]:
        profiles = []
        for profile_id in sorted(self.model_family_selection_profiles["profiles"].keys()):
            profile = self.model_family_selection_profile(profile_id)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def model_family_selection_profile_manifest(self) -> ModelFamilySelectionProfileManifest:
        profiles = self.list_model_family_selection_profiles()
        return ModelFamilySelectionProfileManifest(
            profile_count=len(profiles),
            profiles=profiles,
        )

    def model_family_challenge_review_profile(
        self,
        profile_id: str,
    ) -> ModelFamilyChallengeReviewProfile | None:
        payload = self.model_family_challenge_review_profiles["profiles"].get(profile_id)
        if not payload:
            return None
        return ModelFamilyChallengeReviewProfile(
            profile_id=profile_id,
            display_name=payload["displayName"],
            selection_profile_id=payload["selectionProfileId"],
            comparison_profile_id=payload.get("comparisonProfileId"),
            fit_for_purpose=payload.get("fitForPurpose", []),
            supported_run_modes=payload.get("supportedRunModes", []),
            review_checklist=[
                ModelFamilyChallengeReviewChecklistTemplate(
                    code=item["code"],
                    prompt=item["prompt"],
                    rationale=item["rationale"],
                    evidence_hint_fields=item.get("evidenceHintFields", []),
                )
                for item in payload.get("reviewChecklist", [])
            ],
            review_packet_template=payload.get("reviewPacketTemplate"),
            review_brief_template=payload.get("reviewBriefTemplate"),
            ready_selection_review_statuses=payload.get("readySelectionReviewStatuses", []),
            ready_comparison_review_statuses=payload.get("readyComparisonReviewStatuses", []),
            attention_if_any_checks_fail=payload.get("attentionIfAnyChecksFail", True),
            attention_if_comparison_missing_when_challenge_recommended=payload.get(
                "attentionIfComparisonMissingWhenChallengeRecommended",
                True,
            ),
            ready_action_template=payload.get("readyActionTemplate"),
            attention_action_template=payload.get("attentionActionTemplate"),
            review_notes=payload.get("reviewNotes", []),
            source_pack=f"defaults/{DEFAULTS_VERSION}/model_family_challenge_review_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_model_family_challenge_review_profiles(self) -> list[ModelFamilyChallengeReviewProfile]:
        profiles = []
        for profile_id in sorted(self.model_family_challenge_review_profiles["profiles"].keys()):
            profile = self.model_family_challenge_review_profile(profile_id)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def resolve_model_family_challenge_review_profile(
        self,
        selection_profile_id: str,
        comparison_profile_id: str | None = None,
    ) -> ModelFamilyChallengeReviewProfile | None:
        for profile in self.list_model_family_challenge_review_profiles():
            if profile.selection_profile_id != selection_profile_id:
                continue
            if comparison_profile_id is not None and profile.comparison_profile_id not in {
                comparison_profile_id,
                None,
            }:
                continue
            return profile
        return None

    def model_family_challenge_review_profile_manifest(self) -> ModelFamilyChallengeReviewProfileManifest:
        profiles = self.list_model_family_challenge_review_profiles()
        return ModelFamilyChallengeReviewProfileManifest(
            profile_count=len(profiles),
            profiles=profiles,
        )

    def scientific_review_profile(
        self,
        model_family: str | ModelFamily,
    ) -> ScientificReviewProfile | None:
        model_family_value = (
            model_family.value if isinstance(model_family, ModelFamily) else model_family
        )
        payload = self.scientific_review_profiles["profiles"].get(model_family_value)
        if not payload:
            return None
        return ScientificReviewProfile(
            model_family=model_family_value,
            display_name=payload["displayName"],
            fit_for_purpose=payload.get("fitForPurpose", []),
            review_checklist=[
                ScientificReviewChecklistTemplate(
                    code=item["code"],
                    prompt=item["prompt"],
                    rationale=item["rationale"],
                    evidence_hint_fields=item.get("evidenceHintFields", []),
                )
                for item in payload.get("reviewChecklist", [])
            ],
            packet_template=payload.get("packetTemplate"),
            brief_template=payload.get("briefTemplate"),
            ready_fit_verdicts=payload.get("readyFitVerdicts", []),
            attention_outcomes=payload.get("attentionOutcomes", []),
            attention_if_any_checks_fail=payload.get("attentionIfAnyChecksFail", True),
            escalation_fit_verdicts=payload.get("escalationFitVerdicts", []),
            escalation_driver_types=payload.get("escalationDriverTypes", []),
            qualification_driver_types=payload.get("qualificationDriverTypes", []),
            warning_severity_promotes_qualification=payload.get(
                "warningSeverityPromotesQualification",
                True,
            ),
            acceptable_outcome_template=payload.get("acceptableOutcomeTemplate"),
            qualified_outcome_template=payload.get("qualifiedOutcomeTemplate"),
            escalation_outcome_template=payload.get("escalationOutcomeTemplate"),
            driver_action_templates=payload.get("driverActionTemplates", {}),
            source_pack=f"defaults/{DEFAULTS_VERSION}/scientific_review_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_scientific_review_profiles(self) -> list[ScientificReviewProfile]:
        profiles = []
        for model_family in sorted(self.scientific_review_profiles["profiles"].keys()):
            profile = self.scientific_review_profile(model_family)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def scientific_review_profile_manifest(self) -> ScientificReviewProfileManifest:
        profiles = self.list_scientific_review_profiles()
        return ScientificReviewProfileManifest(
            profile_count=len(profiles),
            profiles=profiles,
        )

    def normalize_adapter_concentration(
        self,
        compartment_code: str,
        value: float,
        unit: str,
    ) -> AdapterConcentrationNormalization:
        rule = self.adapter_unit_conversion_rule(compartment_code)
        if rule is None:
            raise FateRegistryError(
                code="missing_adapter_unit_conversion_rule",
                message=f"Missing adapter unit-conversion rule for compartment {compartment_code}.",
                suggestion="Declare the compartment in defaults/v1/adapter_unit_conversions.json.",
            )
        factor = rule.conversion_factors_to_canonical.get(unit)
        if factor is None:
            raise FateRegistryError(
                code="unsupported_adapter_unit",
                message=f"Unsupported adapter unit {unit} for compartment {compartment_code}.",
                suggestion="Use one of the governed units from defaults://adapter-unit-conversions.",
            )
        return AdapterConcentrationNormalization(
            value=value * float(factor),
            unit=rule.canonical_unit,
            was_converted=unit != rule.canonical_unit,
            source_basis=rule.unit_basis_labels.get(unit),
            canonical_basis=rule.canonical_basis,
        )

    def regulatory_handoff_profile(self, profile_id: str) -> RegulatoryHandoffProfile | None:
        payload = self.regulatory_handoff_profiles["profiles"].get(profile_id)
        if not payload:
            return None
        return RegulatoryHandoffProfile(
            profile_id=profile_id,
            display_name=payload["displayName"],
            target_module=payload["targetModule"],
            downstream_field=payload["downstreamField"],
            required_entry_fields=payload.get("requiredEntryFields", []),
            consumer_hints=payload.get("consumerHints", []),
            review_checklist=[
                RegulatoryHandoffReviewChecklistTemplate(
                    code=item["code"],
                    prompt=item["prompt"],
                    rationale=item["rationale"],
                    evidence_hint_fields=item.get("evidenceHintFields", []),
                )
                for item in payload.get("reviewChecklist", [])
            ],
            tool_request_template=payload.get("toolRequestTemplate"),
            response_summary_template=payload.get("responseSummaryTemplate"),
            review_brief_template=payload.get("reviewBriefTemplate"),
            source_pack=f"defaults/{DEFAULTS_VERSION}/regulatory_handoff_profiles.json",
            applicability_note=payload.get("applicabilityNote"),
        )

    def list_regulatory_handoff_profiles(self) -> list[RegulatoryHandoffProfile]:
        profiles = []
        for profile_id in sorted(self.regulatory_handoff_profiles["profiles"].keys()):
            profile = self.regulatory_handoff_profile(profile_id)
            if profile is not None:
                profiles.append(profile)
        return profiles

    def regulatory_handoff_profile_manifest(self) -> dict[str, Any]:
        profiles = self.list_regulatory_handoff_profiles()
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "profileCount": len(profiles),
            "profiles": [profile.model_dump(mode="json") for profile in profiles],
        }

    def regulatory_handoff_target_matrix_manifest(self) -> RegulatoryHandoffTargetMatrixManifest:
        mappings = [
            RegulatoryHandoffTargetMapping(
                profile_id=profile.profile_id,
                target_module=profile.target_module,
                consumer_hints=sorted(profile.consumer_hints),
                source_pack=profile.source_pack,
            )
            for profile in self.list_regulatory_handoff_profiles()
        ]
        return RegulatoryHandoffTargetMatrixManifest(
            mapping_count=len(mappings),
            mappings=mappings,
        )

    def recommend_regulatory_handoff_profile(
        self,
        consumer_name: str,
    ) -> RegulatoryHandoffProfileRecommendation | None:
        normalized_consumer = _normalize_lookup_value(consumer_name)
        if not normalized_consumer:
            return None

        alias_manifest = self.regulatory_handoff_consumer_alias_manifest()
        exact_matches = [
            alias for alias in alias_manifest.aliases if alias.normalized_alias == normalized_consumer
        ]
        if len({alias.profile_id for alias in exact_matches}) == 1 and exact_matches:
            alias = exact_matches[0]
            profile = self.regulatory_handoff_profile(alias.profile_id)
            if profile is None:
                return None
            matched_hint = alias.alias_variants[0] if alias.alias_variants else alias.normalized_alias
            return RegulatoryHandoffProfileRecommendation(
                consumer_name=consumer_name,
                resolved_profile_id=profile.profile_id,
                target_module=profile.target_module,
                matched_hint=matched_hint,
                confidence=1.0,
                reasoning=(
                    f"Matched consumer '{consumer_name}' exactly to governed alias '{matched_hint}' "
                    f"for target module {profile.target_module}."
                ),
                tool_request_template=profile.tool_request_template,
                response_summary_template=profile.response_summary_template,
            )

        best_score = 0.0
        best_matches: list[RegulatoryHandoffConsumerAlias] = []
        for alias in alias_manifest.aliases:
            score = 0.0
            if normalized_consumer in alias.normalized_alias or alias.normalized_alias in normalized_consumer:
                score = 0.8
            if score <= 0.0:
                continue
            if score > best_score:
                best_score = score
                best_matches = [alias]
            elif score == best_score:
                best_matches.append(alias)

        if best_score <= 0.0 or not best_matches:
            return None
        if len({alias.profile_id for alias in best_matches}) != 1:
            return None
        alias = sorted(best_matches, key=lambda item: (item.profile_id, item.normalized_alias))[0]
        profile = self.regulatory_handoff_profile(alias.profile_id)
        if profile is None:
            return None
        matched_hint = alias.alias_variants[0] if alias.alias_variants else alias.normalized_alias
        return RegulatoryHandoffProfileRecommendation(
            consumer_name=consumer_name,
            resolved_profile_id=profile.profile_id,
            target_module=profile.target_module,
            matched_hint=matched_hint,
            confidence=best_score,
            reasoning=(
                f"Matched consumer '{consumer_name}' to governed hint '{matched_hint}' "
                f"for target module {profile.target_module}."
            ),
            tool_request_template=profile.tool_request_template,
            response_summary_template=profile.response_summary_template,
        )

    def list_regulatory_handoff_consumer_aliases(self) -> list[RegulatoryHandoffConsumerAlias]:
        aliases: list[RegulatoryHandoffConsumerAlias] = []
        for profile in self.list_regulatory_handoff_profiles():
            variants_by_normalized: dict[str, set[str]] = defaultdict(set)
            for alias in _candidate_profile_aliases(profile):
                normalized_alias = _normalize_lookup_value(alias)
                if not normalized_alias:
                    continue
                variants_by_normalized[normalized_alias].add(alias)
            for normalized_alias, alias_variants in sorted(variants_by_normalized.items()):
                aliases.append(
                    RegulatoryHandoffConsumerAlias(
                        normalized_alias=normalized_alias,
                        alias_variants=sorted(alias_variants),
                        profile_id=profile.profile_id,
                        target_module=profile.target_module,
                        source_pack=profile.source_pack,
                    )
                )
        return aliases

    def regulatory_handoff_consumer_alias_manifest(self) -> RegulatoryHandoffConsumerAliasManifest:
        aliases = self.list_regulatory_handoff_consumer_aliases()
        aliases_by_normalized: dict[str, list[RegulatoryHandoffConsumerAlias]] = defaultdict(list)
        for alias in aliases:
            aliases_by_normalized[alias.normalized_alias].append(alias)

        conflicts: list[RegulatoryHandoffConsumerAliasConflict] = []
        for normalized_alias, alias_records in sorted(aliases_by_normalized.items()):
            distinct_profiles = sorted({alias.profile_id for alias in alias_records})
            if len(distinct_profiles) <= 1:
                continue
            alias_variants = sorted(
                {
                    variant
                    for alias in alias_records
                    for variant in alias.alias_variants
                }
            )
            conflicts.append(
                RegulatoryHandoffConsumerAliasConflict(
                    normalized_alias=normalized_alias,
                    alias_variants=alias_variants,
                    profile_ids=distinct_profiles,
                )
            )

        return RegulatoryHandoffConsumerAliasManifest(
            alias_count=len(aliases),
            conflict_count=len(conflicts),
            aliases=aliases,
            conflicts=conflicts,
        )

    def build_manifest(self) -> dict[str, Any]:
        files = sorted(self.version_root.glob("*.json"))
        if self.extensions_root.exists():
            files.extend(sorted(self.extensions_root.glob("*.json")))
        manifest_files = []
        for path in files:
            payload = _load_json(path)
            manifest_files.append(
                {
                    "path": str(path.relative_to(self.repo_root)),
                    "sha256": _sha256(path),
                    "defaultsVersion": payload.get("defaultsVersion", DEFAULTS_VERSION),
                }
            )
        return {
            "defaultsVersion": DEFAULTS_VERSION,
            "files": manifest_files,
        }

    def write_manifest(self) -> Path:
        manifest_path = self.defaults_root / "manifest.json"
        manifest_path.write_text(json.dumps(self.build_manifest(), indent=2) + "\n")
        return manifest_path
