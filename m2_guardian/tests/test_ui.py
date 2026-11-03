"""Streamlit interaction tests; requires requirements-m2.txt."""
from pathlib import Path
import unittest
from unittest.mock import patch
try:
    from streamlit.testing.v1 import AppTest
except ImportError:
    AppTest = None

@unittest.skipIf(AppTest is None, 'Install Streamlit to run UI tests')
class GuardianUITests(unittest.TestCase):
    def start(self):
        return AppTest.from_file(str(Path(__file__).parents[2] / 'app_m2.py')).run()

    def test_simulated_warning_and_raw_details(self):
        at = self.start()
        self.assertFalse(at.exception)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn('SIMULATED', at.warning[0].value)
        self.assertEqual(at.subheader[0].value, 'Fictional Flood Warning')
        self.assertEqual(at.session_state['guardian_result']['status'], 'alerts')

    def test_empty_and_unavailable(self):
        at = self.start()
        at.selectbox[1].select('no_alerts').run()
        at.button[0].click().run()
        self.assertIn('does not mean', at.warning[0].value)
        at.selectbox[1].select('unavailable').run()
        self.assertEqual(len(at.warning), 0)
        at.button[0].click().run()
        self.assertEqual(at.session_state['guardian_result']['status'], 'unavailable')
        self.assertFalse(at.exception)

    def test_location_and_mode_clear_previous_warning(self):
        at = self.start()
        at.button[0].click().run()
        at.selectbox[0].select('miami_point').run()
        self.assertEqual(len(at.warning), 0)
        at.button[0].click().run()
        at.radio[0].set_value('LIVE CHECK').run()
        self.assertEqual(len(at.warning), 0)
        self.assertFalse(at.exception)

    def test_live_failure_is_not_demo(self):
        at = self.start()
        at.radio[0].set_value('LIVE CHECK').run()
        # Patch the actual bound transport, retaining the service behavior.
        from m2_guardian.service import GuardianService
        original = GuardianService.__init__
        def init(instance, **kwargs):
            def fail(*args): raise TimeoutError('test outage')
            original(instance, transport=fail, **kwargs)
        with patch.object(GuardianService, '__init__', init):
            at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertNotIn('SIMULATED', at.warning[0].value)
        self.assertEqual(at.session_state['guardian_result']['mode'], 'live')
        self.assertEqual(len(at.subheader), 0)

    def test_user_requested_explanation_and_recheck_clear(self):
        at = self.start()
        at.button[0].click().run()
        explain = next(b for b in at.button if b.label == 'Understand this alert')
        explain.click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state['guardian_explanation']['guidance_status'], 'simulation_only')
        at.button[0].click().run()
        self.assertNotIn('guardian_explanation', at.session_state)

    def test_manual_coordinates_and_change_clear_result(self):
        at = self.start()
        at.selectbox[0].select('custom_point').run()
        self.assertEqual(len(at.number_input), 2)
        at.button[0].click().run()
        self.assertEqual(at.session_state['guardian_result']['location_id'], 'custom_point')
        at.number_input[0].set_value(25.8).run()
        self.assertEqual(len(at.warning), 0)
        self.assertNotIn('guardian_result', at.session_state)
        self.assertFalse(at.exception)

    def test_coordinates_change_clears_explanation(self):
        at = self.start()
        at.selectbox[0].select('custom_point').run()
        at.button[0].click().run()
        next(b for b in at.button if b.label == 'Understand this alert').click().run()
        at.number_input[1].set_value(-80.2).run()
        self.assertNotIn('guardian_explanation', at.session_state)
        self.assertFalse(at.exception)
