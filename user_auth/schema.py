from bson import ObjectId
import graphene
from graphene import ObjectType, Field
from flask_jwt_extended import jwt_required, get_jwt_identity
from pymongo import MongoClient
from decouple import config

from .models import User

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
collection = db["users"]

### Available Queries
class Query(ObjectType):
    user = Field(User)

    @jwt_required()
    def resolve_user(self, info):
        # Gets current user with its jwt identity
        user = collection.find_one({"username": get_jwt_identity()})
        return User(**user)

### Main entry point for the API
schema = graphene.Schema(query=Query)