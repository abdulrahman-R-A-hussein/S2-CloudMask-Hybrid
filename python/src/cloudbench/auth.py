"""Headless Earth Engine sign-in with a service account.

Adapted from D:\\dev\\VPCA+STEPWISE-REGRESSION\\config\\gee_service_account.py
(initialize_ee_service_account). The key file path comes from the environment variable
GEE_SERVICE_ACCOUNT_JSON. The key is read only by the Earth Engine client; this module never
prints or stores its contents.
"""

from __future__ import annotations

import json
import os

KEY_ENV_VAR = "GEE_SERVICE_ACCOUNT_JSON"


def init_ee(key_path: str | None = None, project: str | None = None, high_volume: bool = True) -> str:
    import ee

    key_path = key_path or os.environ.get(KEY_ENV_VAR)
    if not key_path or not os.path.isfile(key_path):
        raise RuntimeError(f"Set {KEY_ENV_VAR} to the service-account key file path.")
    with open(key_path, encoding="utf-8") as f:
        info = json.load(f)
    email, key_project = info.get("client_email"), info.get("project_id")
    creds = ee.ServiceAccountCredentials(email, key_path)
    kwargs = {"credentials": creds, "project": project or key_project}
    if high_volume:
        kwargs["opt_url"] = "https://earthengine-highvolume.googleapis.com"
    ee.Initialize(**kwargs)
    return email
