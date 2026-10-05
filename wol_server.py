#!/usr/bin/python
# -*- coding: utf-8 -*-
# Created on: 2024-09-08

from dotenv import load_dotenv
load_dotenv()

import os
import time
import json
import jwt
import requests
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from wake_on_lan import wakeOnLAN, formatMagicPacket
from config import WAKE_TARGETS

app = Flask(__name__)

# --- Cloudflare Access JWT verification ---
TEAM_DOMAIN = os.environ["CF_TEAM_DOMAIN"]   # e.g. https://yourteam.cloudflareaccess.com
POLICY_AUD = os.environ["CF_POLICY_AUD"]     # AUD tag from the Access application
CERTS_URL = f"{TEAM_DOMAIN}/cdn-cgi/access/certs"

_key_cache = {"keys": None, "fetched_at": 0}
_CACHE_TTL = 60 * 60  # 1 hour — keys rotate roughly every 6 weeks

def _get_public_keys():
    now = time.time()
    if _key_cache["keys"] is None or now - _key_cache["fetched_at"] > _CACHE_TTL:
        resp = requests.get(CERTS_URL, timeout=5)
        resp.raise_for_status()
        jwk_set = resp.json()
        _key_cache["keys"] = [
            jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(k))
            for k in jwk_set["keys"]
        ]
        _key_cache["fetched_at"] = now
    return _key_cache["keys"]

def require_cf_access(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = request.headers.get("Cf-Access-Jwt-Assertion")
        if not token:
            return jsonify({"error": "missing Access token"}), 403
        for key in _get_public_keys():
            try:
                jwt.decode(token, key=key, audience=POLICY_AUD, algorithms=["RS256"])
                return f(*args, **kwargs)
            except jwt.InvalidTokenError:
                continue
        return jsonify({"error": "invalid Access token"}), 403
    return wrapper

# --- Trigger page ---
PAGE = """
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Wake a device</title>
  <style>
    body { font-family: sans-serif; max-width: 400px; margin: 60px auto; padding: 0 20px; text-align: center; }
    button { font-size: 1.1em; padding: 14px; width: 100%; box-sizing: border-box; margin-top: 12px;
             background: #2563eb; color: white; border: none; border-radius: 6px; cursor: pointer; }
    button:disabled { background: #9ca3af; }
    #status { margin-top: 20px; font-weight: bold; min-height: 24px; }
    .ok { color: #16a34a; }
    .err { color: #dc2626; }
  </style>
</head>
<body>
  <h2>Wake a device</h2>
  {% for key, info in targets.items() %}
    <button onclick="trigger('{{ key }}', this)">{{ info.label }}</button>
  {% endfor %}
  <div id="status"></div>

  <script>
    async function trigger(device, btn) {
      btn.disabled = true;
      setStatus('Sending...', null);
      try {
        const res = await fetch('/wake/' + device, { method: 'POST' });
        const data = await res.json();
        if (res.ok) {
          setStatus('\u2713 ' + data.device + ' woken', true);
        } else {
          setStatus('\u2717 ' + (data.error || 'Failed'), false);
        }
      } catch (e) {
        setStatus('\u2717 Network error', false);
      } finally {
        btn.disabled = false;
      }
    }
    function setStatus(msg, ok) {
      const el = document.getElementById('status');
      el.textContent = msg;
      el.className = ok === null ? '' : (ok ? 'ok' : 'err');
    }
  </script>
</body>
</html>
"""

@app.route("/wake", methods=["GET"])
@require_cf_access
def wake_page():
    return render_template_string(PAGE, targets=WAKE_TARGETS)

@app.route("/wake/<device>", methods=["POST"])
@require_cf_access
def wake(device):
    target = WAKE_TARGETS.get(device)
    if target is None:
        return jsonify({"error": "unknown device"}), 404
    try:
        packet = formatMagicPacket(target["mac"])
        wakeOnLAN(packet)
        return jsonify({"status": "sent", "device": target["label"]}), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 500
    except OSError as e:
        return jsonify({"error": "network error", "detail": str(e)}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001)