"""Application adapter for deterministic emergency routing."""
from domain.contracts import RouteResult
from emergency.models import SituationInput
from emergency.service import evaluate_situation


def route_situation(text_or_category: str) -> RouteResult:
    if isinstance(text_or_category, str) and text_or_category in {'Temporary housing', 'Supplies'}:
        return RouteResult(route='resources', urgency='ordinary',
            message='Review official assistance options. This does not establish current safety.',
            resource_categories=[text_or_category.casefold()], reason_codes=['selected_resource_category'])
    return evaluate_situation({'text': text_or_category})


def assess_situation(request: SituationInput) -> RouteResult:
    return evaluate_situation(request)
