from pydantic import BaseModel, HttpUrl
from typing import Optional

class ServiceBase(BaseModel):
    name: str
    description: str
    url: HttpUrl

class ServiceCreateUpdate(ServiceBase):
    pass

class ServiceInDB(ServiceBase):
    status: str
    last_checked_at: Optional[str] = None
    last_status_change: Optional[str] = None

class ServiceUpdate(BaseModel):
    description: Optional[str] = None
    url: Optional[HttpUrl] = None
