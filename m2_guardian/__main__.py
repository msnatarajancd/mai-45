import argparse
import json
from .service import get_alerts, get_alerts_by_point, LOCATIONS
p = argparse.ArgumentParser(description='ReadyRelief M2 on-demand alert check')
p.add_argument('--mode', choices=['live', 'simulated'], default='simulated')
p.add_argument('--location', choices=LOCATIONS, default='miami_dade')
p.add_argument('--scenario', choices=['warning', 'no_alerts', 'unavailable'], default='warning')
p.add_argument('--latitude', type=float)
p.add_argument('--longitude', type=float)
a = p.parse_args()
if a.latitude is not None or a.longitude is not None:
    if a.latitude is None or a.longitude is None:
        p.error('Provide both --latitude and --longitude')
    try:
        result = get_alerts_by_point(a.latitude, a.longitude, a.mode, a.scenario)
    except ValueError as error:
        p.error(str(error))
else:
    result = get_alerts(a.location, a.mode, a.scenario)
print(json.dumps(result, indent=2))
