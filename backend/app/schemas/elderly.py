import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ElderlyBase(BaseModel):
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=50)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    is_active: bool = True


class ElderlyCreate(ElderlyBase):
    pass


class ElderlyUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    phone: str | None = Field(default=None, max_length=50)
    emergency_contact_name: str | None = Field(default=None, max_length=150)
    emergency_contact_phone: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ElderlyResponse(ElderlyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
