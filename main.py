import urllib.request
import urllib.error
import time
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, status
from db import db
from schemas import ServiceCreateUpdate, ServiceUpdate
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    thread = threading.Thread(target=monitor_services, daemon=True)
    thread.start()
    yield

app = FastAPI(lifespan=lifespan)

@app.get("/")
def root():
    return {"service": "ServicePulse", "status": "alive"}

@app.post("/services", status_code=status.HTTP_201_CREATED)
def register_service(service: ServiceCreateUpdate):
    logger.info(f"Attempting to register service: {service.name}")

    existing = db.services.find_one({"name": service.name})

    if existing:
        logger.warning(f"Duplicate service rejected: {service.name}")
        raise HTTPException(
            status_code=400,
            detail="Service with this name already exists"
        )

    service_data = service.model_dump()
    service_data["status"] = "unknown"

    db.services.insert_one(service_data)
    
    logger.info(f"Service registered successfully: {service.name}")

    return {"message": "Service registered successfully"}

@app.put("/services/{service_name}")
def update_service(service_name: str, updated_service: ServiceUpdate):
    try:
        update_payload = updated_service.model_dump(mode="json", exclude_unset=True)
        if not update_payload:
            raise HTTPException(status_code=400, detail="No fields to update")
        result = db.services.update_one(
            {"name": service_name},
            {"$set": update_payload}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Service not found")
        return {"message": f"Service '{service_name}' updated successfully"}
    except Exception as e:
        logger.exception(f"Update failed for {service_name}: {e}")
        raise HTTPException(status_code=500, detail="Update failed")


@app.delete("/services/{service_name}")
def delete_service(service_name: str):
    result = db.services.delete_one({"name": service_name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": f"Service '{service_name}' deleted successfully"}


@app.get("/services")
def list_services():
    logger.info("Fetching all registered services")
    services = list(db.services.find({}, {"_id": 0}))
    logger.info(f"Total services found: {len(services)}")
    return services

@app.get("/health")
def health_check():
    try:
        db.command("ping")
        return {
            "status": "healthy",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service unavailable"
        )

from datetime import datetime

def monitor_services():
    logger.info("Service monitor started")

    while True:
        services = list(db.services.find({}))

        for service in services:
            old_status = service.get("status")

            try:
                with urllib.request.urlopen(service["url"], timeout=3) as response:
                    new_status = "healthy" if response.status == 200 else "unhealthy"
            except Exception:
                new_status = "unhealthy"

            update_fields = {
                "status": new_status,
                "last_checked_at": datetime.now(timezone.utc)
            }

            # Seed status on first run without emitting events
            if old_status in (None, "unknown"):
                db.services.update_one(
                    {"_id": service["_id"]},
                    {"$set": update_fields}
                )
                continue

            if old_status != new_status:
                now = datetime.now(timezone.utc)

                logger.warning(
                    f"Service '{service['name']}' changed: {old_status} → {new_status}"
                )

                event_data = {
                    "service_name": service["name"],
                    "old_status": old_status,
                    "new_status": new_status,
                    "timestamp": now
                }

                if old_status == "unhealthy" and new_status == "healthy":
                    last_outage = db.events.find_one(
                        {
                            "service_name": service["name"],
                            "new_status": "unhealthy"
                        },
                        sort=[("timestamp", -1)]
                    )
                    if last_outage:
                        downtime = (now - last_outage["timestamp"]).total_seconds()
                        event_data["downtime_seconds"] = int(downtime)

                db.events.insert_one(event_data)
                update_fields["last_status_change"] = now

            db.services.update_one(
                {"_id": service["_id"]},
                {"$set": update_fields}
            )

        time.sleep(10)

@app.get("/events")
def list_events():
    events = list(db.events.find({}, {"_id": 0}))
    return events
