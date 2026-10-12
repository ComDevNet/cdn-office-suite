"""Preserve explicit service ports across installer reruns."""
import json
from pathlib import Path
import re
from urllib.parse import urlparse

KEYS = ('port', 'oc4dPort', 'mailPort')
DEFAULTS = {'port': 8769, 'oc4dPort': 3000, 'mailPort': 2000}


def validate_ports(config):
    if any(type(config.get(k)) is not int or not 1024 <= config[k] <= 65535 for k in KEYS):
        raise ValueError('All service ports must be integers between 1024 and 65535')
    if len({config[k] for k in KEYS}) != 3:
        raise ValueError('Office, OC4D and mail must use distinct ports')
    return {k: config[k] for k in KEYS}


def saved_ports(data, module):
    record = data / 'installation.json'
    if record.exists():
        return validate_ports(json.loads(record.read_text()))
    settings = module / 'settings.js'
    if not settings.exists():
        if (data / 'service.env').exists():
            raise ValueError('Existing port configuration is missing; restore it before reinstalling')
        return None
    text = settings.read_text()
    match = re.search(r'window\.OFFICE_CONFIG\s*=\s*(\{[^;]+\})\s*;', text)
    if not match:
        raise ValueError('Existing launcher port configuration is unreadable; restore it before reinstalling')
    config = json.loads(match[1])
    if 'oc4dPort' not in config:
        env = (data / 'service.env').read_text()
        url = next((line.split('=', 1)[1] for line in env.splitlines() if line.startswith('OC4D_BASE_URL=')), '')
        config['oc4dPort'] = urlparse(url).port
    return validate_ports(config)


def resolve_ports(saved, port=None, oc4d_port=None, mail_port=None):
    result = dict(saved or DEFAULTS)
    for key, value in zip(KEYS, (port, oc4d_port, mail_port)):
        if value is not None:
            result[key] = value
    return validate_ports(result)
