# ServicePulse

ServicePulse is a lightweight service monitoring API that tracks registered services, performs periodic health checks, and records status change events.

## Features
- Register, update, list, and delete monitored services
- Background health checks with status tracking
- Event log for status changes and downtime

## Requirements
- Python 3.10+
- MongoDB

## Quick start
1) Create and activate a virtual environment
2) Install dependencies

```bash
pip install -r requirements.txt
```

3) Set your MongoDB connection (see `db.py`)
4) Run the API

```bash
uvicorn main:app --reload
```

## Docker
```bash
docker-compose up --build
```

## API summary
- `GET /` basic service status
- `GET /health` API + database health
- `POST /services` register a service
- `PUT /services/{service_name}` update a service
- `DELETE /services/{service_name}` delete a service
- `GET /services` list services
- `GET /events` list status change events

## Service payloads
Register a service:
```json
{
  "name": "Example Service",
  "url": "https://example.com/health"
}
```

Update a service:
```json
{
  "url": "https://example.com/healthz"
}
```

## Notes
- The monitor checks services every 10 seconds.
- Status changes are stored in the `events` collection.
