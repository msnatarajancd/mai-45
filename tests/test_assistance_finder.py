"""Offline pathway filtering and integrated UI; no model or live resource calls."""
import pytest
from services import resources
from test_recovery_landing import app, button
from test_recovery_records import saved, dump
from test_pending_danger import app_for, assert_emergency


def links(app):
    return [w.label for w in app.get('link_button')]


def test_housing_and_utility_discovery_are_independent():
    housing = resources.find_resources('housing', 'Miami-Dade')
    utilities = resources.find_resources('utilities', 'Miami-Dade')
    assert len(housing) == 2 and {r.category for r in housing} == {'Housing'}
    assert {r.category for r in utilities} == {'Electricity', 'Water'}
    assert resources.find_resources('insurance') == []
    assert len({r.url for r in resources.PATHWAYS}) == len(resources.PATHWAYS)
    for r in resources.PATHWAYS:
        assert r.last_checked == '2026-11-04'
        assert r.organization and r.purpose and r.geography and r.caveat


@pytest.mark.parametrize('county', [None, '', 'Broward'])
def test_unknown_or_unsupported_county_excludes_local_pathways(county):
    found = resources.find_resources('housing disaster utilities', county)
    assert {r.geography for r in found} == {'US', 'Florida'}
    assert resources.find_resources('water', county) == []


def test_finder_no_plan_model_or_persistence_needed(app, monkeypatch):
    from recovery.llm_client import NebiusClient
    from ui import recovery_page
    monkeypatch.setattr(NebiusClient, 'complete', lambda *a, **k: pytest.fail('no model needed'))
    path = __import__('os').environ['READYRELIEF_DB_PATH']
    before = dump(path)
    button(app, 'Find assistance').click().run()
    assert not app.exception
    assert 'rr_case_id' not in app.session_state
    assert 'Open official page: Housing and shelter after a disaster' in links(app)
    assert 'Open official page: Water and Sewer service contacts' not in links(app)
    assert any('County is unknown' in w.value for w in app.caption)
    assert any('not M3-reviewed guidance' in w.value for w in app.caption)
    assert 'Call 911' in links(app)
    assert "I can't call 911" in [w.label for w in app.button]
    assert dump(path) == before


def test_confirmed_county_is_used_and_progress_unchanged(saved, monkeypatch):
    path, repo, case = saved
    records = repo.get_recovery_records(case.case_id)
    records.reported_county = 'Miami-Dade'
    repo.save_recovery_records(records, expected_version=0, explicitly_confirmed=True)
    before = dump(path)
    app = app_for(path, case, monkeypatch).run()
    button(app, 'Find assistance').click().run()
    assert not app.exception
    assert any('Using confirmed Miami-Dade' in w.value for w in app.caption)
    assert 'Open official page: Water and Sewer service contacts' in links(app)
    next(w for w in app.multiselect if w.label == 'What assistance would you like to find?').set_value(['Electricity']).run()
    assert 'Open official page: Find your utility service territories' in links(app)
    assert 'Open official page: Housing and shelter after a disaster' not in links(app)
    assert dump(path) == before


@pytest.mark.parametrize('failure', [False, True])
def test_missing_directory_is_honest_and_emergency_accessible(app, monkeypatch, failure):
    def missing(*args, **kwargs):
        if failure:
            raise OSError('synthetic directory unavailable')
        return []
    monkeypatch.setattr(resources, 'find_resources', missing)
    button(app, 'Find assistance').click().run()
    assert not app.exception
    assert any('does not mean assistance is unavailable' in w.value for w in app.info)
    assert 'Call 911' in links(app)
    assert "I can't call 911" in [w.label for w in app.button]
    assert not app.success


@pytest.mark.parametrize('pending', [True, False])
def test_danger_blocks_finder_without_changing_recovery(saved, monkeypatch, pending):
    path, repo, case = saved
    if not pending:
        repo.report_immediate_danger(case.case_id)
    app = app_for(path, case, monkeypatch)
    app.session_state['rr_focus'] = 'Find assistance'
    if pending:
        app.session_state['rr_pending_danger'] = [str(case.case_id)]
    records, plan = repo.get_recovery_records(case.case_id), repo.get_active_plan(case.case_id)
    app.run()
    assert not app.exception
    assert 'Open official page: Housing and shelter after a disaster' not in links(app)
    assert 'Call 911' in links(app)
    assert "I can't call 911" in [w.label for w in app.button]
    assert repo.get_case(case.case_id).intake.immediate_danger is True
    assert repo.get_recovery_records(case.case_id) == records
    assert repo.get_active_plan(case.case_id) == plan


def test_pathways_do_not_claim_current_operational_facts():
    all_text = ' '.join(r.caveat for r in resources.PATHWAYS)
    for limitation in ['No open shelter', 'no eligibility', 'no current evacuation order',
                       'Confirm your provider', 'No restoration time']:
        assert limitation in all_text
    assert not any(hasattr(r, 'verified') or hasattr(r, 'reviewed') for r in resources.PATHWAYS)
