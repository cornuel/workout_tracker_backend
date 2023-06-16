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
collection = db["workouts"]

### Available Queries
class Query(ObjectType):
    user = Field(User)

    @jwt_required()
    def resolve_user(self, info):
        print(f"resolve_user")
        current_user = get_jwt_identity()
        user = collection.find_one({"_id": ObjectId(current_user)})
        return User(**user)
    
### Main entry point for the API
schema = graphene.Schema(query=Query)