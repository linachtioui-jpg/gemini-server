# UE5 REST Server - Hosted on Render

Production-ready FastAPI server for UE5 VaRest plugin integration.

## Quick Start (Local Development)

### Prerequisites
- Python 3.13+
- Docker & Docker Compose (optional)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server locally
python fastapi_server.py
```

Server will be available at `http://localhost:6000`

## Docker Deployment

### Local Docker

```bash
# Build the image
docker build -t ue5-rest-server .

# Run the container
docker run -d -p 6000:10000 --name ue5-rest-server ue5-rest-server
```

### Docker Compose

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Render.com Deployment

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit: UE5 REST Server"
git remote add origin https://github.com/YOUR_USERNAME/gemini-server.git
git push -u origin main
```

### Step 2: Connect to Render

1. Go to [https://dashboard.render.com/](https://dashboard.render.com/)
2. Sign in or create an account
3. Click **"New +"** → **"Web Service"**
4. Connect your GitHub repository
5. Configure:
   - **Name:** `ue5-rest-server`
   - **Region:** Choose closest to users (oregon, frankfurt, singapore, sydney)
   - **Plan:** Free (or upgrade for production)
   - **Runtime:** Docker
   - Leave other settings as default (render.yaml will configure automatically)

### Step 3: Deploy

- Click **"Deploy"**
- Render will build and deploy your server
- You'll receive a URL like: `https://ue5-rest-server.onrender.com`

### Step 4: Update Your UE5 Project

Replace `localhost:6000` with your Render URL:

```cpp
VaRest->SetURL(TEXT("https://ue5-rest-server.onrender.com/message"));
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/message` | Main JSON message receiver |
| POST | `/data` | Alternative data endpoint |
| GET | `/health` | Server health check |
| GET | `/` | API information |

## Example UE5 VaRest Request

```cpp
FVaRestJsonObject* Json = NewObject<FVaRestJsonObject>();
Json->SetStringField(TEXT("type"), TEXT("player_position"));
Json->SetNumberField(TEXT("id"), 1);
Json->SetNumberField(TEXT("x"), 100.0f);
Json->SetNumberField(TEXT("y"), 200.0f);
Json->SetNumberField(TEXT("z"), 50.0f);

VaRest->SetVerb(EVaRestRequestVerb::POST);
VaRest->SetURL(TEXT("https://ue5-rest-server.onrender.com/message"));
VaRest->ProcessRequest();
```

## Monitoring

### View Logs
1. Go to your service dashboard on Render
2. Click **"Logs"** tab
3. View real-time logs from the running server

### Health Check
```bash
curl https://ue5-rest-server.onrender.com/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-02-08T02:48:33.380Z"
}
```

## Production Tips

1. **Environment Variables:** Add secrets in Render dashboard
2. **Auto-Deploy:** Connected GitHub repo auto-deploys on push
3. **Upgrade Plan:** Free tier has memory limits; upgrade for production
4. **Custom Domain:** Add your domain in Render settings
5. **HTTPS:** Render provides free SSL/TLS certificates

## Logging

Server logs are stored in:
- **Local:** `fastapi_server.log`
- **Render:** View in dashboard → Logs tab
- Both console and file logging enabled

## Troubleshooting

### Port Issues
- Render uses dynamic ports. The `PORT` environment variable is set automatically.
- Dockerfile is configured to respect the `PORT` env var.

### No Logs Appearing
- Check render.yaml is in root directory
- Ensure Dockerfile is present
- Verify requirements.txt has correct packages

### Connection Refused
- Wait 2-3 minutes for initial deployment
- Verify service is running: `curl https://ue5-rest-server.onrender.com/health`

## Architecture

```
UE5 Client (VaRest Plugin)
    ↓ HTTPS POST
Render.com (Containerized)
    ↓
FastAPI Server (uvicorn)
    ↓
Logging (Console + File)
```

## License

MIT

## Support

For issues or questions, check:
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Render Documentation](https://render.com/docs)
- [UE5 VaRest Plugin](https://www.unrealengine.com/marketplace/en-US/product/varest-plugin)
