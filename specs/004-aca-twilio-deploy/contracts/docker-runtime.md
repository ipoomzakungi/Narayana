# Contract: Backend Docker Runtime

## Files

- `Dockerfile`
- `.dockerignore`

## Dockerfile Requirements

The backend container must:

- Use a Python slim image.
- Install dependencies from `requirements.txt`.
- Copy the backend app and required runtime files.
- Expose port `8000`.
- Run:

```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Docker Ignore Requirements

The Docker build context must exclude:

- `.env`
- `.env.*`
- `.data/`
- `.git/`
- `__pycache__/`
- `.pytest_cache/`
- frontend `node_modules/`
- frontend `.next/`
- local editor and OS files

## Acceptance Checks

- A local Docker build can complete without `.env` or `.data`.
- The resulting container listens on port `8000`.
- No code in `AudioSessionProcessor` or Twilio media WebSocket is changed for Docker support.
