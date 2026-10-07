# Useful Tools — Flask Full-Stack Multi-Tool Website

A complete Python Flask website inspired by the **multi-tool website concept** of the reference you provided, but with original UI/code.

## Included

- 50+ tool pages
- Flask frontend + backend
- Responsive desktop/mobile design
- Search and category filtering
- Dark mode
- Text utilities
- Developer utilities
- Image processing with Pillow
- PDF merge/split/rotate/info/text extraction with pypdf
- QR generation
- Calculators
- SEO utilities
- Secure random generators
- 25 MB upload limit
- Render deployment files
- Gunicorn production server
- `/health` endpoint

## Run locally on Windows

1. Open PowerShell in this folder.
2. Create a virtual environment:

```powershell
py -m venv .venv
```

3. Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

4. Install:

```powershell
python -m pip install -r requirements.txt
```

5. Start:

```powershell
python app.py
```

6. Open:

http://127.0.0.1:5000

## Deploy on Render

### Method A — GitHub + Render

1. Create a new GitHub repository, for example `usefultools`.
2. Extract this ZIP.
3. Upload all files/folders into the repository.
4. Push/commit the files.
5. Open Render.
6. Select **New → Web Service**.
7. Connect the GitHub repository.
8. Runtime: **Python**.
9. Build command:

```text
pip install -r requirements.txt
```

10. Start command:

```text
gunicorn app:app
```

11. Create the service and wait for the deployment.
12. Render will give you a public `onrender.com` URL.

The included `render.yaml` can also be used with Render Blueprint deployment.

## Important production note

This project uses temporary server storage for processing uploaded files and returns generated files directly. That is appropriate for a starter utility site. For a large public service, add object storage, rate limiting, antivirus scanning, authentication/admin controls and background jobs.

## Tool architecture

Most text/calculator/developer tools are handled directly by Flask routes. Image tools use Pillow. PDF tools use pypdf. QR generation uses qrcode.

## Add more tools

Add a new entry to `TOOLS` in `app.py`, then add its form and processing branch in `templates/tool.html` and `handle_tool()`.

## Health check

Open:

`/health`

Expected JSON:

```json
{"service":"Useful Tools","status":"ok"}
```


## Mobile / PWA
This version is responsive for Android, iPhone/iPad, desktop and tablet browsers. It includes a web app manifest, service worker, install prompt and app icons. On supported mobile browsers, users can choose **Add to Home Screen / Install App**.

The PWA does not turn the Python backend into a native app: Flask and file-processing tools still run on Render. Browser-only features can work offline when cached, while server-side PDF/image processing requires an internet connection.
