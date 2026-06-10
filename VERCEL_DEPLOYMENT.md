# 🚀 Deploying VVM School ERP v2.0 on Vercel

We have made the codebase fully compatible with Vercel's serverless architecture. Below is the step-by-step process to deploy your application on Vercel while keeping your existing Supabase database.

---

## 🛠️ Code Changes Already Completed

1. **Vercel Config (`vercel.json`)**: Added a routing configuration to forward all incoming HTTP traffic to the Flask app inside a serverless function context.
2. **Serverless Entry Point (`api/index.py`)**: Created a standard entry point file that imports the Flask application so that the `@vercel/python` builder can handle incoming requests.
3. **Dynamic File Uploads**: Updated the file-upload paths in [config.py](file:///d:/ai%20work/dumar_school/dumar_school_erp/config.py) and [admin_content.py](file:///d:/ai%20work/dumar_school/dumar_school_erp/routes/admin_content.py) to write to the `/tmp/` directory when running on Vercel (since Vercel's root filesystem is read-only). The files are stored temporarily in `/tmp` before being uploaded to Supabase Storage, and then deleted from disk.

---

## 📋 The Deployment Process

### Step 1: Push Your Code to GitHub / GitLab / Bitbucket
Ensure all code changes (including `vercel.json` and the `api/` directory) are committed and pushed to your git repository.

```bash
git add .
git commit -m "Configure Flask app for Vercel deployment"
git push origin main
```

### Step 2: Import Project in Vercel
1. Go to the [Vercel Dashboard](https://vercel.com/dashboard) and log in.
2. Click **Add New** → **Project**.
3. Import the repository where you pushed this code.

### Step 3: Configure Build & Project Settings
1. **Framework Preset**: Leave as `Other` or `Flask` (Vercel will auto-detect the configuration through `vercel.json`).
2. **Root Directory**: Keep it as the root (`./`).

### Step 4: Add Environment Variables
Expand the **Environment Variables** section on Vercel and copy the keys and values from your local `.env` file:

| Variable Name | Description | Example / Location |
| :--- | :--- | :--- |
| `DATABASE_URL` | Supabase PostgreSQL Connection String | From your `.env` |
| `SUPABASE_URL` | Supabase Project URL | From your `.env` |
| `SUPABASE_ANON_KEY` | Supabase Anonymous Key | From your `.env` |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Service Role Key (Required for uploads) | From your `.env` |
| `SECRET_KEY` | Secure Flask Session Key | A long random string |
| `SCHOOL_NAME` | Name of your school | `Vivekanand Vidya Mandir Dharampur` |
| `SCHOOL_ADDRESS` | Address of your school | Address string |
| `SCHOOL_PHONE` | Contact number | Phone number |
| `SCHOOL_EMAIL` | School email | Email address |

> [!IMPORTANT]
> Make sure `SUPABASE_SERVICE_ROLE_KEY` is added so the serverless function can upload student photos and gallery images to your Supabase Storage bucket without hitting Permission/RLS limits.

### Step 5: Deploy
Click the **Deploy** button. Vercel will build the Python dependencies listed in `requirements.txt` and launch your serverless app. Once done, you will receive a public `.vercel.app` URL!

---

## ⚠️ Known Limitations on Vercel

* **PDF Reports via WeasyPrint**: WeasyPrint requires system-level libraries (GTK+, Pango, Cairo) to run. These dependencies are not pre-installed in the Vercel Lambda execution environment. While the main website, admissions, database operations, and portals will work perfectly, accessing `/idcard/pdf` or PDF export options might fail or fallback. If high-quality PDF exporting is a critical production requirement, we recommend deploying to **Render** (using the `render.yaml` configuration in your repo) or **Heroku/Docker**, where system-level packages can be installed.
