import pymongo
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()
connection = os.getenv("URL")


def create_transaction():
    try:
        client = AsyncIOMotorClient(connection)
        print("CLient Created")


        db = client["Finance"]
        print("database created")

        transaction = db["transaction"]
        print("transaction collection created")
        return transaction

    except pymongo.errors.ConnectionFailure:
        print("Connection Failure")


def create_category():
    try:
        client = AsyncIOMotorClient(connection)
        print("CLient Created")

        db = client["Finance"]
        print("database created")

        category = db["category"]
        print("transaction collection created")
        return category

    except pymongo.errors.ConnectionFailure:
        print("Connection Failure")