from typing import Literal

from pydantic import Field

from src.core.schemas import Base


class HealthCheckResponse(Base):
    status: Literal["ok"] = Field(
        "ok", description="Status of the application", examples=["ok"]
    )
