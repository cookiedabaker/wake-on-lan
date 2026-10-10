# wake-on-lan
wake-on-lan script and server to boot machines remotely.

## Server Deployment

The `wake_on_lan.py` script can be used independently as a python package, or as a server.
This particular server has been built to leverage CloudFlare's Access platform and Apache 
webserver to manage the public facing interface.
To deploy the server and endpoint, refer to the following instructions.

### 0. Copy Project

- Deploy a server/container with a user called "wakeonlan":

```bash
useradd --system --no-create-home --shell /usr/sbin/nologin wakeonlan
```

- Copy the required project files into `/opt/wol-endpoint/`:

```bash
# If needed, create the folder:
mkdir -p /opt/wol-endpoint
```

```
/opt/wol-endpoint/...

├── config.env
├── config.py
├── requirements.txt
├── wake_on_lan.py
├── wake_targets.json
└── wol_server.py
```

- Create the virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

- Copy/move `wake_on_lan.service` to `/etc/systemd/system/`.

- Set the user permissions:

```bash
# Give ownership to the 'wakeonlan' account.
chown -R root:wakeonlan /opt/wol-endpoint
chmod -R 750 /opt/wol-endpoint
chmod 640 /opt/wol-endpoint/wake_targets.json

# Lock the environment config file to root.
chown root:root /opt/wol-endpoint/config.env
chmod 600 /opt/wol-endpoint/config.env
```

### 1. Environment Variables
 
Set these wherever the Flask container gets its environment (e.g. `docker-compose.yml`,
a systemd unit's `EnvironmentFile`, or an `.env` loaded before `app.run()`):
 
| Variable            | Example                                      | Purpose                                                        |
|---------------------|----------------------------------------------|----------------------------------------------------------------|
| `CF_TEAM_DOMAIN`    | `https://yourteam.cloudflareaccess.com`      | Your Cloudflare Zero Trust team domain                         |
| `CF_POLICY_AUD`     | (from the Access app's Overview tab)         | AUD tag identifying this specific Access application           |
| `WAKE_TARGETS_FILE` | `/opt/wol-endpoint/wake_targets.json`        | Path to your real (non-example) device allowlist               |

An example environment file and systemd config is provided.

Once all variable are set, run the following commands to start the service:
```bash
systemctl daemon-reload
systemctl enable --now wake_on_lan
```

### 2. Access Application
 
1. **Zero Trust dashboard → Access → Applications → Add an application → Self-hosted.**
2. **Application domain:** your existing hostname, path `/wake` (path-based, no
   new subdomain needed). This covers `/wake` and everything under it
   (`/wake/<device>`), since Access matches by prefix.
3. **Policy:** Include rule listing the specific emails allowed to trigger this
   (yourself + anyone trusted).
4. Copy the **Application Audience (AUD) tag** into `CF_POLICY_AUD` above.

### 3. Cloudflare Authenticated Origin Pulls
 
1. **SSL/TLS → Origin Server → Authenticated Origin Pulls → toggle Global on.**
2. Confirm **SSL/TLS encryption mode** is **Full (Strict)** (required — Flexible
   won't work with AOP).
> Global AOP applies to *every* proxied hostname on this zone, not just this
> endpoint. Before enforcing it on Apache (step 4 below), confirm every vhost
> Apache serves is actually proxied through Cloudflare (orange-clouded) — a
> grey-clouded hostname sitting on the same Apache instance would break once
> `SSLVerifyClient require` is enforced.

### 4. Apache Setup & Authenticated Origin Pulls

An example Apache configuration file is included in this repository.

For basic requirements for setting up this endpoint, download the authenticated origin pull CA file:

```bash
wget https://developers.cloudflare.com/ssl/static/authenticated_origin_pull_ca.pem \
  -O /etc/apache2/ssl/cloudflare-origin-pull-ca.pem
```
 
In the SSL vhost terminating TLS for this domain:
 
```apache
SSLCACertificateFile /etc/apache2/ssl/cloudflare-origin-pull-ca.pem
```
 
Reload Apache and confirm it starts cleanly, **then** enable Global AOP in the
Cloudflare dashboard (step 3 above), and only after that's confirmed live, add:
 
```apache
SSLVerifyClient require
SSLVerifyDepth 1
```
 
Reload again. Verify by curling the origin IP directly — the TLS handshake
should now fail — while requests through the normal domain still succeed.

### 5. Apache Reverse Proxy
 
Adjust the container address/port to match your setup:
 
```apache
ProxyPreserveHost On
ProxyPass ^/wake(/.*)?$ http://localhost:5001/wake$1
ProxyPassReverse /wake/ http://localhost:5001/wake/
RequestHeader set X-Forwarded-Proto "https"
```

### Order of Operations (Troubleshooting)
 
1. Deploy `wol_server.py` + accessory files in the correct locations, with env vars set. Confirm it runs.
2. Set up the Access Application and policy (section 2) — test that visiting
   `/wake` prompts an Access login and then loads the page.
3. Add `SSLCACertificateFile` to Apache (section 4) *without* `SSLVerifyClient
   require` yet, reload, confirm no errors.
4. Enable Global AOP in the Cloudflare dashboard (section 3).
5. Add `SSLVerifyClient require` to Apache (section 4), reload.
6. Verify direct-IP requests now fail TLS, and normal domain access still works.


## Acknowledgments
* Parts of this codebase were generated or optimized using [Anthropic's Claude](https://anthropic.com).
