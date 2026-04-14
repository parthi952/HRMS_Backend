from pydantic import BaseModel
from typing import List, Optional


class OptionItemBase(BaseModel):
    label: str
    value: str
    symbol: Optional[str] = None


class OptionItemResponse(OptionItemBase):
    id: int

    class Config:
        from_attributes = True


class OptionCategoryCreate(BaseModel):
    id: Optional[int] = None
    key: str
    options: List[OptionItemBase]


# ✅ THIS IS MISSING IN YOUR FILE
class OptionCategoryResponse(BaseModel):
    id: int
    key: str
    options: List[OptionItemResponse]

    class Config:
        from_attributes = True


class OptionCategoryUpsert(BaseModel):
    options: List[OptionItemBase]