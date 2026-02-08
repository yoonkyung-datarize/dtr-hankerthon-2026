from pydantic import BaseModel, Field
from typing import Optional, Any


class DesignRequest(BaseModel):
    site_id: str = Field(alias="siteId")
    prompt: str

    model_config = {"populate_by_name": True}


class DesignGenerateData(BaseModel):
    css: str
    explanation: Optional[str] = None


class ApiResponse(BaseModel):
    code: str = "0000"
    message: str = "Success"
    data: Optional[Any] = None
