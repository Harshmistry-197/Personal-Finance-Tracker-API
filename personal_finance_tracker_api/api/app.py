from typing import Optional
from fastapi import FastAPI, HTTPException, Body, status, Query
from personal_finance_tracker_api.database import create_transaction, create_category
from bson import ObjectId
from pymongo.errors import DuplicateKeyError
from .schemas import Transaction, Category


app = FastAPI()

# Initialize database collections
transaction_col = create_transaction()
category_col = create_category()


# Transaction API Endpoints
# Transaction API
@app.post("/transactions", tags=["Transaction API"])
async def add_new_transaction(transaction: Transaction):
    """
        Create a new financial transaction.
        - transaction: Validated Transaction data (Title, Amount, Type, etc.)
        - Returns: The unique ID of the inserted transaction.
    """
    try:
        transaction_data = transaction.model_dump()

        new_t = await transaction_col.insert_one(transaction_data)
        return {"id": str(new_t.inserted_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/transactions", tags=["Transaction API"])
async def list_transactions():
    """
        Fetch a list of the last 100 transactions.
        - Returns: A list of transaction objects with stringified ObjectIDs.
    """
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
    """
        Perform a case-insensitive search across transaction titles and descriptions.
        - q: Search keyword (Query Parameter)
        - Uses: MongoDB $regex for partial matching.
    """

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
    """
       Generate a report of total income vs expenses grouped by month.
       - Logic: Uses MongoDB Aggregation to sum amounts.
       - Requirement: 'date' field must be a valid ISODate object.
    """
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
    """
        Retrieve a specific transaction by its unique hex ID.
    """
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
    """
        Partially update an existing transaction.
        - data: A dictionary of fields to change (e.g., {"category": "rent"}).
    """
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
    """
        Delete multiple transactions belonging to a specific category.
    """
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
    """
        Permanently remove a single transaction by ID.
    """
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


# Category API Endpoints
# Category API
@app.post("/categories", status_code=status.HTTP_201_CREATED, tags=["Category API"])
async def create_category(c: Category):
    """
       Register a new category for transaction sorting.
       - Note: Requires a Unique Index on 'name' in MongoDB to trigger DuplicateKeyError.
    """
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
    """
        Retrieve all registered categories.
    """
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
    """
        Update category details by name.
    """
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
    """
        Permanently delete a category by its name.
        - name: The unique name of the category to be removed.
        - Returns: A success message if deleted, or 404 if the name does not exist.
    """
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