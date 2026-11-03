from domain.contracts import AppMode, Household


def initialize(state):
    for key, value in {'page': 'Home', 'mode': AppMode.DEMO, 'location_id': 'miami', 'household': Household(), 'rr_emergency': False}.items():
        if key not in state:
            state[key] = value


def change_context(state, location_id, mode):
    if state.get('location_id') != location_id or state.get('mode') != mode:
        for key in ('alerts', 'guidance', 'resources', 'route_result'):
            state.pop(key, None)
    state['location_id'] = location_id
    state['mode'] = mode


def load_demo(state):
    for key in ('alert_mode_picker', 'alert_location_picker'):
        state.pop(key, None)
    change_context(state, 'miami', AppMode.DEMO)
    state['household'] = Household(label='The Rivera household', members=3, mobility_support=True, has_vehicle=False, pets=True)
    state['demo_started'] = True
    state['page'] = 'Protect'
    # Existing recovery cases are deliberately not overwritten by a demo restart.


def clear_recovery_view(state):
    for key in list(state):
        if key.startswith(("rr_draft", "rr_revision", "rr_reviewed", "rr_progress")):
            del state[key]
