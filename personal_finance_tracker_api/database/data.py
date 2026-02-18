import pymongo
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

# Load environment variables from .env file
load_dotenv()

# Retrieve MongoDB connection string from environment variables
connection = os.getenv("URL")


def create_transaction():
    """
        Initializes a connection to the 'transaction' collection in MongoDB.
        - Uses AsyncIOMotorClient for non-blocking database operations.
        - Connects to the 'Finance' database.
        - Returns: Motor Collection object for transactions.
    """
    try:
        client = AsyncIOMotorClient(connection)
        print("Client Created")

        db = client["Finance"]
        print("database created")

        transaction = db["transaction"]
        print("transaction collection created")
        return transaction

    except pymongo.errors.ConnectionFailure:
        print("Connection Failure")


def create_category():
    """
        Initializes a connection to the 'category' collection in MongoDB.
        - Uses AsyncIOMotorClient to maintain consistency with FastAPI's async nature.
        - Returns: Motor Collection object for categories.
    """
    try:
        client = AsyncIOMotorClient(connection)
        print("Client Created")

        db = client["Finance"]
        print("database created")

        category = db["category"]
        print("transaction collection created")
        return category

    except pymongo.errors.ConnectionFailure:
        print("Connection Failure")