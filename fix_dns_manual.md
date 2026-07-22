# Fix: Docker pip Network Error on Windows

## What went wrong
The Docker builder container couldn't reach pypi.org to download Python packages.
Error: `[Errno 101] Network is unreachable`

This happens on Windows with Docker Desktop when the DNS inside build containers
doesn't resolve properly. The base images (Redis, Postgres, Kafka) pull fine because
Docker uses a different network path for image pulls vs. build-time pip installs.

---

## Fix Option A — Automated (Recommended)

Open PowerShell **as Administrator** and run:

```powershell
cd E:\DevBhumi
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\fix_and_build.ps1
```

---

## Fix Option B — Manual Steps (if Option A fails)

### Step 1: Add DNS to Docker Desktop settings

1. Open Docker Desktop
2. Click the **gear icon** (Settings) in the top right
3. Go to **Docker Engine**
4. You will see a JSON editor. Add the `dns` field:

```json
{
  "builder": { "gc": { "defaultKeepStorage": "20GB", "enabled": true } },
  "experimental": false,
  "dns": ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
}
```

> If there's already content in that JSON, just add the `"dns"` line —
> don't replace the whole thing. Make sure commas are correct.

5. Click **Apply & Restart**
6. Wait for Docker to show **"Engine running"** in the bottom left

### Step 2: Clear the failed build cache

Open PowerShell in the DevBhumi folder:

```powershell
docker builder prune -f
```

### Step 3: Rebuild

```powershell
docker compose down
docker compose up -d --build
```

---

## Fix Option C — Pre-download packages locally (Offline build)

If your internet works on the host but not inside Docker:

```powershell
# In PowerShell, from the DevBhumi folder:
cd services\auth-service

# Install pip-download tool
pip install pip-download

# Download all wheels for your platform
mkdir wheels
pip download -r requirements.txt -d wheels --platform linux_x86_64 --python-version 311 --only-binary=:all:

# Then rebuild — Docker will install from local wheels
docker compose up -d --build
```

For Option C to work, update the Dockerfile builder stage to:
```dockerfile
COPY wheels/ /tmp/wheels/
RUN pip install --no-cache-dir --user --find-links /tmp/wheels -r requirements.txt
```

---

## Verify it worked

After a successful build, run:

```powershell
docker compose ps
# All services should show (healthy)

curl http://localhost:8001/health
# {"status":"ok","service":"auth-service"}
```

---

## Still failing? Check these

1. **Corporate/university network**: Some networks block pip. Try on home WiFi.
2. **Proxy**: If you use a proxy, add to Dockerfile:
   ```dockerfile
   ENV HTTP_PROXY=http://your-proxy:port
   ENV HTTPS_PROXY=http://your-proxy:port
   ```
3. **WSL2 DNS leak**: In Docker Desktop Settings → Resources → WSL Integration,
   disable and re-enable your WSL distro, then restart Docker.
4. **VPN**: Disconnect VPN during the build, reconnect after.
