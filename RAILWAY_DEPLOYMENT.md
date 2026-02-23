# Railway Deployment Guide for MindSpring FastAPI

This guide will walk you through deploying your MindSpring FastAPI application on Railway step by step. If this is your first time deploying, don't worry - we'll cover everything!

## 📋 Prerequisites

Before you begin, make sure you have:
- A GitHub account (or GitLab/Bitbucket)
- A Railway account (sign up at [railway.app](https://railway.app))
- Your project code pushed to a Git repository (GitHub recommended)
- Basic understanding of environment variables

---

## 🚀 Step-by-Step Deployment

### Step 1: Create a Railway Account

1. Go to [railway.app](https://railway.app)
2. Click **"Start a New Project"** or **"Login"** if you already have an account
3. Sign up using your GitHub account (recommended) for easier integration

### Step 2: Create a New Project on Railway

1. Once logged in, click **"New Project"**
2. Select **"Deploy from GitHub repo"** (or your Git provider)
3. Authorize Railway to access your repositories
4. Select your `mindspring-fastapi` repository
5. Railway will automatically detect it's a Python project

### Step 3: Add PostgreSQL Database

Your application needs a PostgreSQL database with the `pgvector` extension.

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add PostgreSQL"**
3. Railway will automatically create a PostgreSQL database
4. **Important**: Note down the connection details (you'll need them later)

### Step 4: Add Redis Service

Your application also needs Redis for caching and rate limiting.

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add Redis"**
3. Railway will automatically create a Redis instance
4. Note down the connection URL

### Step 5: Configure Environment Variables

This is a crucial step! You need to set all the required environment variables.

1. In your Railway project, click on your **service** (the main app, not the databases)
2. Go to the **"Variables"** tab
3. Add the following environment variables one by one:

#### Required Database Variables

```
DATABASE_URL=postgresql://user:password@host:port/database
```

**How to get this:**
- Click on your PostgreSQL service in Railway
- Go to the **"Variables"** tab
- Copy the `DATABASE_URL` value
- Paste it into your main service's environment variables

#### Required Redis Variables

```
REDIS_URL=redis://default:password@host:port
```

**How to get this:**
- Click on your Redis service in Railway
- Go to the **"Variables"** tab
- Copy the `REDIS_URL` value
- Paste it into your main service's environment variables

#### Required Security Variables

```
SECRET_KEY=your-super-secret-key-here-generate-a-random-string
```

**Generate a secret key:**
- You can use an online generator or run this in Python:
  ```python
  import secrets
  print(secrets.token_urlsafe(32))
  ```

#### Database Configuration (Optional - defaults provided)

```
DATABASE_POOL_SIZE=50
DATABASE_POOL_OVERFLOW=30
DATABASE_POOL_TIMEOUT=10
DATABASE_ECHO=False
DATABASE_QUERY_TIMEOUT=30
```

#### Redis Configuration (Optional - defaults provided)

```
REDIS_POOL_SIZE=20
```

#### Server Configuration

```
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
DEBUG=False
```

#### API Configuration

```
API_V1_STR=/api/v1
BACKEND_CORS_ORIGINS=["*"]
```

#### Authentication Settings

```
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

#### LLM Configuration (Required if using AI features)

```
LLM_BASE_URL=https://inference.ai.neevcloud.com/v1
AI_API_ENDPOINT=https://inference.ai.neevcloud.com/v1/chat/completions
LLM_MODEL=gpt-oss-120b
NEEVCLOUD_API_KEY=your-neevcloud-api-key
```

Or if using OpenAI:

```
OPENAI_API_KEY=your-openai-api-key
EMBEDDING_ENDPOINT=https://api.openai.com/v1/embeddings
EMBEDDING_MODEL=text-embedding-ada-002
EMBEDDING_MODEL_KEY=your-openai-api-key
```

#### Storage Configuration (S3/Ceph - Optional but recommended)

```
S3_ENDPOINT_URL=your-s3-endpoint-url
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=your-bucket-name
```

Or for Ceph:

```
CEPH_ENDPOINT=your-ceph-endpoint
CEPH_ACCESS_KEY=your-ceph-access-key
CEPH_SECRET_KEY=your-ceph-secret-key
CEPH_BUCKET=your-ceph-bucket
CEPH_PUBLIC_URL=your-ceph-public-url
```

#### Email Configuration (Optional - for OTP/email features)

```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
OTP_EXPIRE_MINUTES=10
```

#### Google OAuth (Optional)

```
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=https://your-app.railway.app/api/v1/auth/google/callback
```

#### Other Optional Settings

```
EMBEDDING_DIMENSION=1536
CHUNK_SIZE_TOKENS=400
MAX_CHUNK_SIZE_TOKENS=600
VECTOR_SEARCH_THRESHOLD=0.7
MAX_SIMILARITY_RESULTS=10
TASK_TIMEOUT_SECONDS=300
DOCUMENT_PROCESSING_TIMEOUT=1800
RATE_LIMIT_DEFAULT=100/hour
RATE_LIMIT_DOCUMENT_UPLOAD=10/day
```

### Step 6: Enable pgvector Extension

PostgreSQL needs the `pgvector` extension enabled. Railway doesn't enable it automatically, so you need to do it manually.

1. Click on your **PostgreSQL** service in Railway
2. Go to the **"Data"** tab
3. Click **"Query"** or use a database client
4. Run this SQL command:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

**Alternative method using Railway CLI:**
```bash
# Install Railway CLI (if not already installed)
npm i -g @railway/cli

# Login to Railway
railway login

# Connect to your database
railway connect postgres

# Then run:
CREATE EXTENSION IF NOT EXISTS vector;
```

### Step 7: Configure Build Settings

1. In your main service, go to **"Settings"** tab
2. Under **"Build Command"**, Railway should auto-detect, but verify:
   - Build command: (leave empty or use `pip install -r requirements.txt`)
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   
   **Note**: Railway automatically sets the `PORT` environment variable, so use `$PORT` instead of `8000`

3. Under **"Root Directory"**, make sure it's set to `/` (root of your project)

### Step 8: Create a Procfile (Optional but Recommended)

Create a `Procfile` in your project root to explicitly tell Railway how to run your app:

```procfile
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Or create a `runtime.txt` to specify Python version:

```
python-3.11.0
```

### Step 9: Run Database Migrations

Before your app can work, you need to run Alembic migrations to set up your database schema.

**Option 1: Using Railway CLI (Recommended)**

1. Install Railway CLI:
   ```bash
   npm i -g @railway/cli
   ```

2. Login:
   ```bash
   railway login
   ```

3. Link to your project:
   ```bash
   railway link
   ```

4. Run migrations:
   ```bash
   railway run alembic upgrade head
   ```

**Option 2: Using Railway's Deploy Logs**

1. After deployment, check the deploy logs
2. If migrations fail, you can add a startup script

**Option 3: Add Migration to Startup (Temporary)**

You can temporarily modify your `app/main.py` to run migrations on startup (not recommended for production, but works for initial setup):

```python
# Add this in your lifespan function
from alembic.config import Config
from alembic import command

async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Run migrations
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    
    # Startup
    setup_logging()
    await init_db()
    
    yield
    
    # Shutdown
```

### Step 10: Deploy!

1. Railway will automatically deploy when you push to your connected Git repository
2. Or you can manually trigger a deployment:
   - Go to your service
   - Click **"Deploy"** → **"Redeploy"**
3. Watch the build logs to see if everything works
4. Once deployed, Railway will provide you with a URL like: `https://your-app.railway.app`

### Step 11: Verify Deployment

1. Check the health endpoint:
   ```
   https://your-app.railway.app/health
   ```
   Should return: `{"status": "healthy", "service": "mindspring-fastapi-backend"}`

2. Check the API docs:
   ```
   https://your-app.railway.app/api/v1/openapi.json
   ```
   Or interactive docs:
   ```
   https://your-app.railway.app/docs
   ```

---

## 🔧 Troubleshooting Common Issues

### Issue 1: Build Fails - "Error creating build plan with Railpack"

**Solution:**
This error occurs when Railway can't automatically detect your build configuration. We've included configuration files to fix this:

1. **Check that these files exist in your project root:**
   - `nixpacks.toml` - Explicit build configuration
   - `railway.json` - Alternative Railway configuration
   - `Procfile` - Start command specification
   - `runtime.txt` - Python version (should contain just `3.11`)

2. **If the error persists:**
   - Go to your Railway service → **Settings** → **Build**
   - Manually set:
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Save and redeploy

3. **Alternative: Use Dockerfile** (if above doesn't work):
   - A `Dockerfile` has been created in your project root
   - Railway will automatically detect and use it
   - This is often more reliable than auto-detection

### Issue 2: Build Fails - "ResolutionImpossible" or "Could not find a version that satisfies the requirement"

**Solution:**
This error means pip can't resolve dependencies due to version conflicts or unavailable packages.

1. **Check the package name and version:**
   - Verify the package exists on [PyPI](https://pypi.org)
   - Check if the version number is correct
   - Try using flexible version constraints: `package-name>=1.2.0,<2.0.0` instead of `package-name==1.2.3`

2. **Fix dependency conflicts:**
   - Beta versions (like `0.50b0`) can cause conflicts - use stable versions or flexible ranges
   - Example: Changed `opentelemetry-instrumentation-fastapi==0.50b0` to `opentelemetry-instrumentation-fastapi>=0.45.0,<1.0.0`
   - Remove unused packages that aren't actually imported in your code

3. **Update build tools in Dockerfile:**
   ```dockerfile
   RUN pip install --no-cache-dir --upgrade pip setuptools wheel
   ```
   This ensures you have the latest dependency resolver.

4. **Test locally first:**
   ```bash
   pip install -r requirements.txt
   ```

### Issue 3: Build Fails - "Module not found" or compilation errors

**Solution:**
- Make sure `requirements.txt` is in your project root
- Check that all dependencies are listed
- Railway might need a `runtime.txt` file specifying Python version
- If using Dockerfile, ensure system dependencies are installed (see Dockerfile for reference)

### Issue 4: Database Connection Error

**Solution:**
- Verify `DATABASE_URL` is set correctly in environment variables
- Make sure the PostgreSQL service is running
- Check that the database URL format is correct: `postgresql://user:password@host:port/database`

### Issue 5: pgvector Extension Not Found

**Solution:**
- Make sure you've run `CREATE EXTENSION IF NOT EXISTS vector;` in your PostgreSQL database
- Check Railway's PostgreSQL version supports pgvector (most do)

### Issue 6: Port Already in Use

**Solution:**
- Make sure you're using `$PORT` environment variable, not a hardcoded port
- Railway sets the PORT automatically

### Issue 7: Migrations Not Running

**Solution:**
- Use Railway CLI to run migrations manually: `railway run alembic upgrade head`
- Or add migration command to your Procfile as a release command

### Issue 8: Redis Connection Error

**Solution:**
- Verify `REDIS_URL` is set correctly
- Make sure Redis service is running
- Check the URL format: `redis://default:password@host:port`

### Issue 9: CORS Errors

**Solution:**
- Update `BACKEND_CORS_ORIGINS` to include your frontend URL:
  ```
  BACKEND_CORS_ORIGINS=["https://your-frontend.railway.app","https://your-frontend.com"]
  ```

---

## 📝 Additional Configuration

### Custom Domain

1. Go to your service **"Settings"**
2. Click **"Generate Domain"** or **"Custom Domain"**
3. Follow Railway's instructions to configure DNS

### Environment-Specific Settings

You can create different environments (staging, production) in Railway:
1. Click **"New Environment"** in your project
2. Deploy the same service to different environments
3. Set different environment variables for each

### Monitoring and Logs

- **Logs**: Click on your service → **"Deployments"** → Click on a deployment → View logs
- **Metrics**: Railway provides basic metrics in the dashboard
- **Alerts**: Set up alerts in Railway settings

---

## 🔐 Security Best Practices

1. **Never commit `.env` files** - Always use Railway's environment variables
2. **Use strong SECRET_KEY** - Generate a random, long string
3. **Rotate credentials regularly** - Especially API keys
4. **Limit CORS origins** - Don't use `["*"]` in production, specify your frontend domains
5. **Use HTTPS** - Railway provides this automatically
6. **Keep dependencies updated** - Regularly update `requirements.txt`

---

## 📚 Next Steps

After successful deployment:

1. **Test all endpoints** using the interactive docs at `/docs`
2. **Set up monitoring** - Consider adding error tracking (Sentry, etc.)
3. **Configure backups** - Railway provides automatic PostgreSQL backups
4. **Set up CI/CD** - Railway auto-deploys on git push, but you can customize this
5. **Scale your service** - Railway allows you to scale resources as needed

---

## 🆘 Getting Help

- **Railway Documentation**: [docs.railway.app](https://docs.railway.app)
- **Railway Discord**: [discord.gg/railway](https://discord.gg/railway)
- **Railway Support**: Available in the Railway dashboard

---

## ✅ Deployment Checklist

Before going live, make sure:

- [ ] All environment variables are set
- [ ] PostgreSQL database is created and pgvector extension is enabled
- [ ] Redis service is running
- [ ] Database migrations have been run successfully
- [ ] Health endpoint returns 200 OK
- [ ] API documentation is accessible
- [ ] CORS is configured for your frontend
- [ ] All secrets and API keys are set (not using defaults)
- [ ] DEBUG is set to `False` in production
- [ ] Custom domain is configured (if needed)
- [ ] Monitoring is set up

---

**Congratulations! 🎉** Your MindSpring FastAPI application should now be live on Railway!

If you encounter any issues not covered in this guide, check the Railway logs and the troubleshooting section above.
