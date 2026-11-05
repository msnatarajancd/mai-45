"""Fixed access copy. No generated operational instructions or service promises."""
MIAMI_DADE = 'US-FL-MIAMI-DADE'
AREA_OPTIONS = ['Choose current area (optional)', 'Miami-Dade County, Florida', 'Outside Miami-Dade / not sure']
TYPE_LABELS = {
    'Flooding': 'flood',
    'Trapped / cannot get out': 'trapped',
    'Medical concern': 'medical',
    'Evacuation support': 'evacuation_support',
    'Utility hazard': 'utility_hazard',
    'Not sure': 'unknown',
}
DESKTOP_FALLBACK = 'If this device cannot place calls, use a phone to dial 911.'
NO_DISPATCH = 'ReadyRelief has not contacted or dispatched anyone. A link click does not confirm a connection or rescue.'
ALTERNATIVES_NOTICE = (
    'If you cannot call, text-to-911 may be an option. Local network and device availability vary; '
    'delivery is not guaranteed. ReadyRelief cannot send a text or contact responders. '
    'If possible, ask someone nearby to call for you.'
)
NO_CONNECTION = (
    'ReadyRelief cannot restore cellular service or a usable connection. An in-app button cannot '
    'make a call or text go through. This online-only prototype has no offline guarantee.'
)
COMMUNICATION_OPTIONS = ['Cannot speak safely', 'Hearing or speech access needs',
                         'This device cannot call', 'No usable connection']
