from typing import Literal, List, Annotated, Optional
from pydantic import BaseModel, StrictStr, StrictFloat,Field, StringConstraints, AfterValidator
from datetime import datetime, timezone


def validate_past_date(v: datetime) -> datetime:
    """
    Ensures the provided date is not set in the future.
    Converts naive datetime objects to UTC aware objects for safe comparison.
    """
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    if v > datetime.now(timezone.utc):
        raise ValueError("Date cannot be in the future")
    return v


class Transaction(BaseModel):
    """
    Schema for financial transactions with strict validation rules.
    """
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=3, max_length=100)]
    description: StrictStr = Field(..., min_length=1)
    amount: StrictFloat = Field(..., gt=0)
    type: Literal["income", "expense"]
    category: Annotated[str, StringConstraints(to_lower=True, min_length=1, strip_whitespace=True)]
    date: Annotated[datetime, AfterValidator(validate_past_date)]
    tags: List[Annotated[str, StringConstraints(max_length=30)]] = Field(..., max_length=10)
    created_at: datetime
    updated_at: datetime


class Category(BaseModel):
    """
    Schema for grouping transactions into specific categories.
    """
    name: StrictStr = Field(..., min_length=1, max_length=100)
    type: Literal["income", "expense", "both"]
    description: StrictStr = Field(..., min_length=1)
    created_at: datetime