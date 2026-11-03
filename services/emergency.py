"""M4 placeholder: emergency access never depends on an LLM/classifier."""
from domain.contracts import RouteResult


def route_situation(text_or_category: str) -> RouteResult:
    # TODO(M4): Replace with reviewed bounded rules + golden cases. Arbitrary
    # free text stays on the conservative route; never infer absence of danger.
    if text_or_category in {'Transportation', 'Temporary housing', 'Supplies'}:
        return RouteResult(route='resources', urgency='unassessed', message='Review official assistance options. This does not establish that your situation is safe.')
    return RouteResult(route='emergency', urgency='possible-danger', message='If you are in immediate danger, call 911. This prototype cannot assess your safety or contact responders.')
