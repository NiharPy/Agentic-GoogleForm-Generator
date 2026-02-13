# app/schemas/form_snapshot.py

from pydantic import BaseModel
from typing import Dict, Any


class FormSnapshot(BaseModel):
    data: Dict[str, Any]
