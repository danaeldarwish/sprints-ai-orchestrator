"""Offline validation of operator attestations; never calls the provider.

Account authorization, billing, model entitlement and quota cannot be inferred
from public model documentation. A trusted operator supplies current project
attestations only after checking the intended project. No credential is stored.
"""
import json
from datetime import datetime,timezone
from pathlib import Path
from src.live_controls import MODEL
_REQUIRED=('model_access_confirmed','project_authorized','billing_and_quota_confirmed','standard_global_pricing_confirmed')
def validate_preflight(path:Path):
    data=json.loads(path.read_text(encoding='utf-8'))
    if data.get('model')!=MODEL or any(data.get(k) is not True for k in _REQUIRED):raise PermissionError('Project/model/quota/pricing preflight is incomplete')
    stamp=datetime.fromisoformat(data.get('checked_at_utc','').replace('Z','+00:00'))
    now=datetime.now(timezone.utc)
    if stamp.tzinfo is None or not 0<=(now-stamp).total_seconds()<=86400:raise PermissionError('Preflight must be current within24 hours')
    if data.get('input_per_million')!=0.10 or data.get('cache_write_per_million')!=0.125 or data.get('output_per_million')!=0.50:raise PermissionError('Pricing changed; revise and approve the envelope before execution')
    return data
