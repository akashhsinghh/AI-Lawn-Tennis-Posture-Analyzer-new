# 🚀 Deploying the AI Lawn Tennis Posture Analyzer

This is a Streamlit app that uses **MediaPipe** + **OpenCV**. It can be
deployed for free on **Render**, **Streamlit Community Cloud**, or
**Hugging Face Spaces**. Two details matter on every platform:

- `requirements.txt` uses `opencv-python-headless` (not plain `opencv-python`)
  — the "headless" build has no GUI/graphics-driver dependency, which is
  exactly what a server with no screen needs, and avoids `libGL.so.1`
  errors entirely.
- `app.py` displays images/tables through a small `_full_width(...)` helper
  instead of calling `use_container_width=True` directly. Streamlit has
  changed how "fill the container width" is requested across versions, and
  different hosts can resolve different Streamlit versions — this helper
  tries the modern way, then the older way, then falls back, so the app
  doesn't crash regardless of which version the host installs. (This is
  exactly the fix for the `TypeError: ... unexpected keyword argument
  'use_container_width'` error — see section D below if you hit it again.)

---

## A. Render (what this project is currently deployed on)

### One-time setup (skip if your service already exists)
1. Push this folder to a **GitHub repo** with `app.py`, `requirements.txt`,
   and the other files at the **top level** (not inside a sub-folder).
2. On **render.com** → **New → Web Service** → connect the repo.
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

   The `--server.port $PORT --server.address 0.0.0.0` part is required on
   Render specifically: Render assigns a random port via the `$PORT`
   environment variable and expects the app to listen on `0.0.0.0`, not
   `localhost` — Streamlit's own default doesn't do this automatically.

### Deploying an update (your situation right now)
1. Commit and push the fixed files (`app.py` at minimum) to GitHub.
2. In the Render dashboard, open your service.
3. Click **Manual Deploy** (top right) → **"Clear build cache & deploy"**
   — not just "Deploy latest commit". This forces Render to reinstall from
   `requirements.txt` fresh, instead of reusing a previously cached build.
4. Wait for the build to finish, then reload your app URL (hard refresh
   with Ctrl+Shift+R so the browser isn't showing a cached error page).

---

## B. Streamlit Community Cloud (free alternative)

1. Push the same repo to GitHub (top-level `app.py`).
2. Go to **share.streamlit.io** → sign in with GitHub →
   **Create app → Deploy a public app from GitHub**.
3. Fill in: **Repository**, **Branch:** `main`, **Main file path:** `app.py`.
4. Under **Advanced settings**, set **Python version = 3.11** (MediaPipe
   0.10.14 has no wheels for 3.12/3.13 — this step matters).
5. Click **Deploy**.

On this platform, the `packages.txt` file in this folder is read
automatically for any apt-level system libraries — useful if you ever
switch away from `opencv-python-headless`.

---

## C. Hugging Face Spaces (good alternative, more RAM)

1. Free account at **huggingface.co** → **New Space → SDK: Streamlit**.
2. Upload the same files.
3. It builds and serves automatically at `https://huggingface.co/spaces/...`.

Free CPU Spaces give more memory than the other two options, so heavier
videos cope better here.

---

## D. Troubleshooting: `TypeError: ... got an unexpected keyword argument 'use_container_width'`

This happens when the Streamlit version actually installed on the server
doesn't match what the code expects — Streamlit has been phasing this
parameter out in favour of a newer `width=` parameter, and different
versions accept different things.

**This is already fixed in `app.py`.** Every full-width display call now
goes through `_full_width(...)`, which tries the modern API, then the
older API, then a plain call — so it keeps working regardless of which
Streamlit version the host resolves.

If you push this fix and still see the same error, the host is serving a
**stale build**. On Render: **Manual Deploy → "Clear build cache & deploy"**
(see section A). On Streamlit Cloud: open the app menu (⋮) →
**Reboot app**, or delete and redeploy if rebooting doesn't help.

---

## E. Run it locally (no deployment)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open http://localhost:8501.
