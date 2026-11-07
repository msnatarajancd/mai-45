"""Authored fictional examples; never an implicit fallback for saved cases."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

from pydantic import Field

from .models import (ChecklistProfile, HousingSite, Model, ProgressInput,
                     RepairProvider, ScenarioSummary, SourceMode)

_DATA = Path(__file__).with_name('data')


class CatalogVariant(Model):
    """Authoring-only settings, never a substitute for saved-case observations."""
    housing_ids: list[str] | None = None
    provider_ids: list[str] | None = None
    housing_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    provider_overrides: dict[str, dict[str, Any]] = Field(default_factory=dict)
    housing_age_hours: int = Field(default=0, ge=0, le=87600, strict=True)
    provider_age_hours: int = Field(default=0, ge=0, le=87600, strict=True)
    housing_validity_hours: int | None = Field(default=24, ge=0, le=87600, strict=True)
    provider_validity_hours: int | None = Field(default=24, ge=0, le=87600, strict=True)


def _read(name: str):
    return json.loads((_DATA / name).read_text(encoding='utf-8'))


def _catalog_rows(filename, ids, overrides, *, as_of, age, validity, model):
    rows = _read(filename)
    indexed = {row['id']: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError(f'Duplicate IDs in {filename}')
    selected = list(indexed) if ids is None else ids
    if len(selected) != len(set(selected)):
        raise ValueError(f'Duplicate catalog selections in {filename}')
    if set(selected) - indexed.keys() or overrides.keys() - set(selected):
        raise ValueError(f'Unknown or unselected catalog ID in {filename}')
    allowed_fields = model.model_fields.keys() - {'id', 'provenance'}
    observed = as_of - timedelta(hours=age)
    provenance = dict(source_mode='synthetic', source=f'Authored fictional {filename} catalog',
                      observed_at=observed, valid_until=None if validity is None else observed + timedelta(hours=validity),
                      scope='fictional service area')
    results = []
    for item_id in selected:
        changes = overrides.get(item_id, {})
        if changes.keys() - allowed_fields:
            raise ValueError(f'Invalid catalog override fields for {item_id}')
        row = deepcopy(indexed[item_id])
        row.update(deepcopy(changes))
        row['provenance'] = provenance.copy()
        results.append(model.model_validate(row))
    return results


def _load_checklists() -> tuple[ChecklistProfile, ...]:
    return tuple(ChecklistProfile.model_validate(row) for row in _read('checklists.json'))


def list_scenarios() -> tuple[ScenarioSummary, ...]:
    return tuple(ScenarioSummary(id=row['id'], label=row['label'], description=row['description'],
                                 featured=row['featured'], checkpoints=[c['id'] for c in row['checkpoints']])
                 for row in _read('scenarios.json'))


def load_scenario(scenario_id: str, checkpoint_id: str | None = None) -> ProgressInput:
    stories = {row['id']: row for row in _read('scenarios.json')}
    if scenario_id not in stories:
        raise ValueError(f'Unknown synthetic scenario: {scenario_id}')
    checkpoints = stories[scenario_id]['checkpoints']
    checkpoint_id = checkpoint_id or checkpoints[0]['id']
    selected = next((row for row in checkpoints if row['id'] == checkpoint_id), None)
    if selected is None:
        raise ValueError(f'Unknown checkpoint: {checkpoint_id}')
    facts = deepcopy(selected)
    facts.pop('id')
    variant = CatalogVariant.model_validate(facts.pop('catalog', {}))
    as_of = datetime.fromisoformat(facts['as_of'])
    facts['housing_sites'] = _catalog_rows('housing.json', variant.housing_ids, variant.housing_overrides,
        as_of=as_of, age=variant.housing_age_hours, validity=variant.housing_validity_hours, model=HousingSite)
    facts['providers'] = _catalog_rows('providers.json', variant.provider_ids, variant.provider_overrides,
        as_of=as_of, age=variant.provider_age_hours, validity=variant.provider_validity_hours, model=RepairProvider)
    facts['checklist'] = next((profile for profile in _load_checklists() if profile.id == facts['checklist_id']), None)
    return ProgressInput(context_key=f'synthetic:{scenario_id}', source_mode=SourceMode.SYNTHETIC,
                         scenario_id=scenario_id, checkpoint_id=checkpoint_id, **facts)
