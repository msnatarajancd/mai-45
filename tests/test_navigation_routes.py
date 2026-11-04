import pytest
from ui.capabilities import chat_routes, navigation_query, search_pages


@pytest.mark.parametrize('query,page', [
    ('weather', 'Protect'), ('tasks', 'Recover'), ('family', 'Household'),
    ('open recovery', 'Recover'), ('Please go to the family page.', 'Household'),
    ('Can you open the weather screen?', 'Protect'), ('take me to evidence', 'Evidence'),
    ('switch to assistant please', 'Assistant'), ('go to household', 'Household'),
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
