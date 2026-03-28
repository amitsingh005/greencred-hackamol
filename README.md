# GreenCred 🌿
### Strava for Eco Actions — Track, earn credits, and compete to save the planet.

**Stack:** Django 4.2 + DRF · SQLite/PostgreSQL · Cloudinary · Firebase Auth · Railway · Firebase Hosting

---

## Project Structure

```
greencred_hackmol/
├── greencred/              ← Django project root (deploy this to Railway)
│   ├── greencred/          ← settings, urls, wsgi
│   ├── greencredapp/       ← models, views, serializers, business logic
│   ├── templates/          ← HTML pages (feed, login, leaderboard…)
│   ├── static/             ← CSS, JS
│   ├── manage.py
│   ├── requirements.txt
│   ├── Procfile            ← Railway start command
│   ├── railway.json        ← Railway config
│   └── nixpacks.toml       ← Railway build steps
├── firebase.json           ← Firebase Hosting config
└── .firebaseignore
```

---

## Local Development

```bash
# 1. Clone & create venv
git clone <your-repo>
cd greencred_hackmol
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
cd greencred
pip install -r requirements.txt

# 3. Run migrations
python manage.py migrate

# 4. Start server
python manage.py runserver

# 5. Open app
open http://localhost:8000/login/

# 6. Seed demo data
# Visit http://localhost:8000/seed/ and click "Seed Demo Data"
# Then log in with any demo account
```

---

## Deploy Backend → Railway

### One-time setup

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub**
3. Select your repo → set **Root Directory** to: `greencred`
4. Railway auto-detects Nixpacks and builds

### Set environment variables in Railway Dashboard → Variables

| Variable | Value |
|---|---|
| `SECRET_KEY` | Any long random string (e.g. `python -c "import secrets; print(secrets.token_hex(40))"`) |
| `DEBUG` | `False` |
| `CLOUDINARY_CLOUD_NAME` | From Cloudinary dashboard |
| `CLOUDINARY_API_KEY` | From Cloudinary dashboard |
| `CLOUDINARY_API_SECRET` | From Cloudinary dashboard |
| `FIREBASE_SERVICE_ACCOUNT` | Full JSON from serviceAccountKey.json, minified to one line |

### Get your Railway URL
After deploy: `https://greencred-production.up.railway.app`

Update `static/js/api.js` if your Railway URL is different — replace `greencred-production` with your actual subdomain.

---

## Deploy Frontend → Firebase Hosting

The Django templates are served by Railway. Firebase Hosting serves the static assets (CSS/JS) as a CDN — or you can use it for a pure-static HTML build.

```bash
# Install Firebase CLI (once)
npm install -g firebase-tools

# Login
firebase login

# Initialize (run from greencred_hackmol/ root)
firebase init hosting
# → Use existing project: greencred (your Firebase project)
# → Public directory: greencred/staticfiles
# → Single page app: NO
# → Overwrite index.html: NO

# Collect static files first
cd greencred
python manage.py collectstatic --noinput
cd ..

# Deploy
firebase deploy --only hosting
```

Live at: **https://greencred.web.app**

---

## Setup Cloudinary (Image Uploads)

1. Sign up free at [cloudinary.com](https://cloudinary.com)
2. Dashboard → copy **Cloud Name**, **API Key**, **API Secret**
3. Set these as Railway environment variables (see table above)
4. That's it — Django auto-uploads images to Cloudinary via `DEFAULT_FILE_STORAGE`

**Free tier:** 25 GB storage · 25 GB bandwidth/month · Unlimited transformations

Images are auto-transformed for cards: `c_fill,w_800,h_400,q_auto,f_auto`

---

## Setup Firebase (Google Auth)

### 1. Create project
1. [console.firebase.google.com](https://console.firebase.google.com) → **Add project** → name: `greencred`
2. Disable Google Analytics (optional) → Create project

### 2. Enable Google Sign-In
1. **Authentication** → **Get started**
2. **Sign-in method** → **Google** → Enable → set support email → Save

### 3. Add web app & get config
1. **Project Overview** (⚙️) → **Project settings** → **Your apps** → `</>` (web)
2. Register as `GreenCred Web` → copy the `firebaseConfig` object

### 4. Paste config into the app
Open `greencred/static/js/firebase-config.js`:

```js
const FIREBASE_CONFIG = {
    apiKey: "AIzaSy...",
    authDomain: "greencred.firebaseapp.com",
    projectId: "greencred",
    storageBucket: "greencred.appspot.com",
    messagingSenderId: "...",
    appId: "..."
};
const FIREBASE_CONFIGURED = true;   // ← change to true
```

### 5. Add authorized domains
**Authentication** → **Settings** → **Authorized domains** → Add:
- `localhost`
- `greencred-production.up.railway.app`
- `greencred.web.app`

### 6. Backend service account (for real token verification)
1. **Project settings** → **Service accounts** → **Generate new private key**
2. Download `serviceAccountKey.json`
3. **Local:** place in `greencred/` folder (it's .gitignored)
4. **Railway:** minify the JSON to one line and set as `FIREBASE_SERVICE_ACCOUNT` env var:
   ```bash
   # Minify JSON on Mac/Linux:
   cat serviceAccountKey.json | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin)))"
   ```

---

## Environment Variables Reference

```bash
# .env (local — never commit this)
SECRET_KEY=your-secret-key
DEBUG=True

# Railway (production)
SECRET_KEY=<random 50+ char string>
DEBUG=False
CLOUDINARY_CLOUD_NAME=greencred
CLOUDINARY_API_KEY=123456789
CLOUDINARY_API_SECRET=abc123...
FIREBASE_SERVICE_ACCOUNT={"type":"service_account","project_id":"greencred",...}
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/firebase/` | — | Login / register |
| GET | `/api/users/<uid>/` | Optional | Get user profile |
| PUT | `/api/users/<uid>/` | Required | Update profile |
| GET | `/api/actions/` | Optional | Action feed |
| POST | `/api/actions/` | Required | Log eco action |
| POST | `/api/actions/<id>/like/` | Required | Toggle like |
| GET | `/api/challenges/` | Optional | List challenges |
| POST | `/api/challenges/` | Required | Create challenge |
| POST | `/api/challenges/<id>/join/` | Required | Join/leave |
| GET | `/api/badges/` | Optional | All badges |
| GET | `/api/badges/<badge_id>/` | Optional | Badge detail |
| GET | `/api/leaderboard/` | Optional | Rankings |
| POST | `/api/seed/` | — | Seed demo data |
| DELETE | `/api/seed/` | — | Clear all data |

---

## Ranks & Credits System

| Rank | Credits Required |
|---|---|
| 🌱 Seedling | 0 – 99 |
| 🌿 Sprout | 100 – 499 |
| 🌲 Grove Keeper | 500 – 1,499 |
| 🌍 Ecosystem Builder | 1,500 – 4,999 |
| ⭐ Earth Guardian | 5,000+ |

**Streak multiplier:** 5 day streak → +10% credits · 10 days → +25% · 30+ days → +50%

---

## Badges

| Badge | Criteria |
|---|---|
| 🌱 First Seed | Log 1 action |
| 🌳 Tree Champion | Plant 5 trees |
| 🧹 Clean Streets | Complete 3 cleanups |
| 🔥 Week Warrior | 7-day streak |
| 🌍 Earth Guardian | Earn 5000+ GC |
| 🏆 Challenge Accepted | Complete 1 challenge |
| ⭐ Pioneer | First 10 users |
| 🤝 Crew Player | Join 3+ challenges |
