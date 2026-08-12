from pydantic import BaseModel
from typing import List

class IDConfigBase(BaseModel):
    id: str
    prefix: str
    separator: str
    digit: int  
    isActive: bool

    class Config:
        from_attributes = True

class CustomIDStore(BaseModel):
    EMP: List[IDConfigBase]
    DEP: List[IDConfigBase]
    CAN: List[IDConfigBase]
    INT: List[IDConfigBase]