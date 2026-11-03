"""M3 retrieval boundary: never present placeholders as retrieved evidence."""
from domain.contracts import GuidanceResult, Household


def retrieve_guidance(query: str, phase: str, context: Household | None = None) -> GuidanceResult:
    # TODO(M3): Retrieve reviewed official excerpts; return provenance and abstain
    # on unsupported queries. Do not pass fictional text off as source material.
    return GuidanceResult(answer='I do not have verified evidence to answer this yet. Use the official information links below; the knowledge service is not connected.')
