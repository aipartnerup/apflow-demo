# aipartnerupflow-demo

Demo deployment of aipartnerupflow with rate limiting and pre-computed results.

This is an independent application that wraps `aipartnerupflow` as a core library, adding demo-specific features like:
- Rate limiting (per user/IP daily limits)
- Pre-computed demo results (to avoid LLM API costs)
- Demo-specific API middleware
- Usage tracking

## Architecture

This application uses `aipartnerupflow[all]` as a dependency and wraps its API with demo-specific middleware and extensions.

## Quick Start

### Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Start with docker-compose
docker-compose up

# Or run directly
python -m aipartnerupflow_demo.main
```

### Production

```bash
# Build Docker image
docker build -f docker/Dockerfile -t aipartnerupflow-demo .

# Run with docker-compose
docker-compose up -d
```

## Configuration

See `.env.example` for configuration options.

Key environment variables:
- `DEMO_MODE=true`: Enable demo mode
- `RATE_LIMIT_ENABLED=true`: Enable rate limiting
- `RATE_LIMIT_DAILY_PER_USER=10`: Daily limit per user
- `RATE_LIMIT_DAILY_PER_IP=50`: Daily limit per IP
- `REDIS_URL=redis://localhost:6379`: Redis connection

## Deployment

### Local Development

```bash
# Start with docker-compose (includes Redis)
docker-compose up

# Or run directly (requires Redis running)
python -m aipartnerupflow_demo.main
```

### Production Deployment

1. **Build Docker image**:
   ```bash
   docker build -f docker/Dockerfile -t aipartnerupflow-demo:latest .
   ```

2. **Deploy with docker-compose**:
   ```bash
   docker-compose up -d
   ```

3. **Or deploy to cloud**:
   - Update environment variables in `.env` or docker-compose.yml
   - Set `DEMO_MODE=true` and `RATE_LIMIT_ENABLED=true`
   - Configure Redis URL
   - Deploy to your cloud provider

### Integration with aipartnerupflow-webapp

1. **Deploy demo API** (this repository) to your server
2. **Deploy aipartnerupflow-webapp** and configure it to point to demo API:
   ```bash
   NEXT_PUBLIC_API_URL=https://demo-api.aipartnerup.com
   ```
3. **Add demo link** in aipartnerup-website (already configured)

## License

Apache-2.0

