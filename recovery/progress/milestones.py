"""Parallel household and funding milestones without a universal percentage."""
from zoneinfo import ZoneInfo

from .insurance import _current
from .models import ExecutionState, Milestone, MilestoneView, ProgressInput, SignalState, SourceMode


def build_milestones(inputs: ProgressInput, results) -> MilestoneView:
    usable = {r.specialist: r for r in results if r.execution_state in (ExecutionState.COMPLETE, ExecutionState.NEEDS_INFORMATION)
              and r.source_mode == inputs.source_mode}
    def specialist(name):
        return usable[name].state if name in usable else SignalState.UNKNOWN
    def item_state(identifier):
        insurance = usable.get('insurance')
        return next((item.state for item in insurance.items if item.id == identifier), SignalState.UNKNOWN) if insurance else SignalState.UNKNOWN
    def reported(value):
        return SignalState.UNKNOWN if value is None else SignalState.GREEN if value else SignalState.YELLOW
    elapsed = (inputs.as_of.astimezone(ZoneInfo('America/New_York')).date() - inputs.recovery_started).days if inputs.recovery_started else None
    if elapsed is not None and elapsed < 0:
        elapsed = None
    elapsed_label = f'{elapsed} days since recovery started' if elapsed is not None else 'Recovery start date unknown'
    home = [Milestone(title='Current accommodation', state=specialist('housing'), detail='Current accommodation as reported; matching does not reserve a place'),
            Milestone(title='Essential utility conditions', state=specialist('utilities'), detail='Address service and drinking-water information; no home-safety certification'),
            Milestone(title='Returned home', state=reported(inputs.home_returned), detail='Explicit household report; never inferred from utilities or payment'),
            Milestone(title='Repairs completed', state=reported(inputs.repairs_complete), detail='Explicit report; a quote or work commitment does not complete repairs')]
    if inputs.insurance_applicable is False:
        decision = receipt = SignalState.NOT_APPLICABLE
        decision_detail, receipt_detail = 'No insurance reported', 'No insurance payment expected'
    elif inputs.source_mode == SourceMode.SAVED_CASE or inputs.insurance_applicable is None:
        decision = receipt = SignalState.UNKNOWN
        decision_detail = receipt_detail = 'Insurance decision and payment events are not established'
    else:
        decision = {'unknown': SignalState.UNKNOWN, 'pending': SignalState.YELLOW, 'approved': SignalState.GREEN,
                    'declined': SignalState.RED, 'not_applicable': SignalState.UNKNOWN}[inputs.funding.decision]
        decision_detail = f'Fictional decision record: {inputs.funding.decision}; not receipt of money'
        receipt = SignalState.GREEN if _current(inputs.funding.received_payment, inputs.funding.stage_id, inputs.as_of) else item_state('insurance-payment')
        receipt_detail = 'Explicit received-money record; allocation and spending are separate' if receipt == SignalState.GREEN else 'No current received-money record; approved or expected money is not available cash'
    funding = [Milestone(title='Preparation evidence', state=item_state('preparation'), detail='Selected applicable evidence links only; no approval or coverage claim'),
               Milestone(title='Funding for next stage', state=item_state('funding'), detail='Current exact stage allocation when supplied; a broad contribution band does not establish a gap'),
               Milestone(title='Insurance decision', state=decision, detail=decision_detail),
               Milestone(title='Insurance funds received', state=receipt, detail=receipt_detail)]
    synthetic = inputs.source_mode == SourceMode.SYNTHETIC
    return MilestoneView(elapsed_days=elapsed, elapsed_label=elapsed_label, home=home, funding=funding,
                         insurance_range=(inputs.insurance_timing or 'Not enough information') if synthetic else 'Not enough information',
                         recovery_range=(inputs.recovery_timing or 'Not enough information') if synthetic else 'Not enough information',
                         assumptions=inputs.timing_assumptions if synthetic else ['No defensible timing estimate is established for this saved case'])
