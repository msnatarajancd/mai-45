import pytest
from ui.capabilities import chat_routes, navigation_query, search_pages


@pytest.mark.parametrize('query,page', [
    ('weather', 'Protect'), ('tasks', 'Recover'), ('family', 'Household'),
    ('open recovery', 'Recover'), ('Please go to the family page.', 'Household'),
    ('Can you open the weather screen?', 'Protect'), ('take me to evidence', 'Evidence'),
    ('switch to assistant please', 'Assistant'), ('go to household', 'Household'),
    ('recovery progress', 'Recovery Progress'), ('dashboard', 'Recovery Progress'),
])
def test_search_and_chat_share_navigation(query, page):
    assert search_pages(query) == [page]
    assert chat_routes(query) == [page]


@pytest.mark.parametrize('query', ['How does recovery work?', 'What is Protect?', 'Where is my plan?',
    'Can you explain household preferences?', 'show my plan', 'approve my plan', 'mark my housing task completed',
    'open recovery and approve my plan', 'We have four people and no car', ''])
def test_questions_and_operations_are_not_automatic_navigation(query):
    assert chat_routes(query) == []


def test_ambiguous_routes_and_empty_search():
    assert len(chat_routes('open re')) > 1
    assert search_pages('') == []
    assert navigation_query('Please open the tasks screen!') == 'tasks'


def test_progress_feature_switch_and_grouped_destinations(monkeypatch):
    from ui.capabilities import navigation_items, progress_preview_enabled, resolve_page
    monkeypatch.delenv('READYRELIEF_PROGRESS_PREVIEW', raising=False)
    assert progress_preview_enabled()
    children = [item for item in navigation_items(progress_enabled=True) if item.group == 'Recover']
    assert [(item.label, item.page, item.focus) for item in children] == [
        ('Recovery Progress · Preview', 'Recovery Progress', None),
        ('My Recovery Plan', 'Recover', 'Continue my recovery'),
        ('Insurance & Documents', 'Recover', 'Prepare for insurance')]
    monkeypatch.setenv('READYRELIEF_PROGRESS_PREVIEW', 'off')
    assert not progress_preview_enabled()
    assert 'Recovery Progress' not in [item.page for item in navigation_items(progress_enabled=False)]
    assert search_pages('recovery progress') == []
    assert search_pages('open recovery') == ['Recover']
    assert resolve_page('Recovery Progress') == 'Recover'


@pytest.mark.parametrize('query,label,focus', [
    ('open Insurance & Documents', 'Insurance & Documents', 'Prepare for insurance'),
    ('Please go to My Recovery Plan', 'My Recovery Plan', 'Continue my recovery')])
def test_search_and_chat_preserve_explicit_recovery_destination(query, label, focus):
    from ui.capabilities import search_destinations
    assert search_pages(query) == ['Recover']
    assert [(item.label, item.page, item.focus) for item in search_destinations(query)] == [(label, 'Recover', focus)]
    assert chat_routes(query) == [label]
