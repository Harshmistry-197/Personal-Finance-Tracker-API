from typing import Literal, List, Annotated, Optional
from pydantic import BaseModel, StrictStr, StrictFloat,Field, StringConstraints, AfterValidator
from fastapi import FastAPI, HTTPException, Body, status, Query
from datetime import datetime, timezone
from personal_finance_tracker_api.database import create_transaction, create_category
from bson import ObjectId
from pymongo.errors import DuplicateKeyError


app = FastAPI()

transaction_col = create_transaction()
category_col = create_category()

def validate_past_date(v: datetime) -> datetime:
    if v.tzinfo is None:
        v = v.replace(tzinfo=timezone.utc)
    if v > datetime.now(timezone.utc):
        raise ValueError("Date cannot be in the future")
    return v

class Transaction(BaseModel):
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
    name: StrictStr = Field(..., min_length=1, max_length=100)
    type: Literal["income", "expense", "both"]
    description: StrictStr = Field(..., min_length=1)
    created_at: datetime


# Transaction API
@app.post("/transactions", tags=["Transaction API"])
async def add_new_transaction(transaction: Transaction):
    try:
        transaction_data = transaction.model_dump()

        new_t = await transaction_col.insert_one(transaction_data)
        return {"id": str(new_t.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/transactions", tags=["Transaction API"])
async def list_transactions():
    try:
        data = transaction_col.find({})
        res = await data.to_list(length=100)

        if not res:
            raise HTTPException(status_code=404, detail="No transactions found")

        for doc in res:
            doc["_id"] = str(doc["_id"])

        return res

    except HTTPException as http_err:
        raise http_err
    except Exception as e:
        print(f"Database Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")



@app.get("/transactions/search", tags=["Transaction API"])
async def search_transactions(q: str):
        # # Requires text index on title/description
        # cursor = transaction_col.find({"$text": {"$search": q}})
        # res = await cursor.to_list(length=50)
        # return [dict(doc, _id=str(doc["_id"])) for doc in res]
        # Searches title OR description for the string 'q' (case-insensitive)
        # query = {
        #     "$or": [
        #         {"title": {"$regex": q, "$options": "i"}},
        #         {"description": {"$regex": q, "$options": "i"}}
        #     ]
        # }
        # cursor = transaction_col.find(query)
        # res = await cursor.to_list(length=50)
        # return [dict(doc, _id=str(doc["_id"])) for doc in res]

    try:
        query = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}}
            ]
        }
        data = transaction_col.find(query)
        res = await data.to_list(length=50)

        if not res:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No transactions found matching: {q}"
            )

        for i in res:
            i["_id"] = str(i["_id"])
        return res

    except HTTPException:
        raise
    except Exception as e:
        print(f"Search Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during the search operation"
        )


@app.get("/transactions/summary", tags=["Transaction API"])
async def monthly_report():
    try:
        pipeline = [
            {
                "$group": {
                    "_id": {"month": {"$month": "$date"}, "type": "$type"},
                    "total": {"$sum": "$amount"}
                }
            },
            {"$sort": {"_id.month": 1}}
        ]

        res = await transaction_col.aggregate(pipeline).to_list(length=None)
        if not res:
            return "No records Found"

        return res

    except Exception as e:
        print(f"Aggregation Error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary. Ensure all records have valid date objects."
        )


@app.get("/transactions/{id}", tags=["Transaction API"])
async def get_transaction(transaction_id: str):
    if not ObjectId.is_valid(transaction_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")

    try:
        doc = await transaction_col.find_one({"_id": ObjectId(transaction_id)})
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

        doc["_id"] = str(doc["_id"])
        return doc

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@app.patch("/transactions/{id}", tags=["Transaction API"])
async def update_transaction(transaction_id:str, data: dict = Body(...)):
    if not ObjectId.is_valid(transaction_id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    if not data:
        raise HTTPException(status_code=status.HTTP_204_NO_CONTENT, detail="Data not found")

    try:
        res = await transaction_col.update_one({"_id": ObjectId(transaction_id)}, {"$set": data})
        if res.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

        return {"status": "Updated", "Updated_fields": list(data.keys())}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal Server Error")


@app.delete("/transactions/bulk", tags=["Transaction API"])
async def bulk_delete(category: Optional[str] = Query(None, min_length=1)):
    try:
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category parameter is required for bulk delete to prevent accidental data loss."
            )

        result = await transaction_col.delete_many({"category": category})
        return {
            "status": "success",
            "message": f"Deleted {result.deleted_count} transactions in category '{category}'",
            "deleted_count": result.deleted_count
        }

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Bulk delete operation failed")


@app.delete("/transactions/{id}", tags=["Transaction API"])
async def delete_transaction(transaction_id: str):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=400, detail="Invalid ID format")

    try:
        result = await transaction_col.delete_one({"_id": ObjectId(transaction_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"status": "deleted", "id": id}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Delete operation failed")



# Category API
@app.post("/categories", status_code=status.HTTP_201_CREATED, tags=["Category API"])
async def create_category(c: Category):
    try:
        await category_col.insert_one(c.model_dump())
        return {"message": "Category created successfully"}

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Category '{c.name}' already exists"
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error during creation"
        )


@app.get("/categories", tags=["Category API"])
async def list_categories():
    try:
        cursor = category_col.find()
        res = await cursor.to_list(length=100)

        if not res:
            return []

        return [dict(doc, _id=str(doc["_id"])) for doc in res]

    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve categories"
        )


@app.patch("/categories/{name}", tags=["Category API"])
async def update_category(name: str, c: dict = Body(...)):
    try:
        result = await category_col.update_one(
            {"name": name},
            {"$set": c}
        )

        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{name}' not found"
            )

        return {"status": "updated", "category": list(c.keys())}

    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another category with this name already exists"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/categories/{name}", tags=["Category API"])
async def delete_category(name: str):
    try:
        result = await category_col.delete_one({"name": name})

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category '{name}' not found"
            )

        return {"status": "deleted", "message": f"Category '{name}' removed"}

    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Delete operation failed")