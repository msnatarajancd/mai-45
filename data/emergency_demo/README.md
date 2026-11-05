# Synthetic emergency demonstration inputs

These files contain six presentation inputs, three fictional household profiles, and nine failure-state descriptions. Every record is explicitly simulated. No record supplies an operational contact or official review approval.

Use `emergency.demo.load_scenarios()` for selector labels and `load_scenario(id, mode='demo')` for input. Pass the returned input through the same evaluator and workflow as a manual report. The loader rejects live mode and propagates missing/invalid fixture errors without substitution.

A profile's suggested county is demonstration context, not the current incident location. A danger scene does not automatically clear a persisted danger report when the user leaves it. Use a separate fictional recovery case for subsequent recovery demonstrations.

Failure scenarios describe missing/slow AI, unavailable directory, stale/revoked evidence, unknown incident county, failed danger persistence, unsupported dialer, and unusable connectivity. They are test instructions, not operational service assertions. The online-only app has no offline continuity guarantee.
