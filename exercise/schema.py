from pymongo import MongoClient
from decouple import config
from graphene import ObjectType, List, String, Schema

from .models import Exercise

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
collection = db["exercises"]

class Query(ObjectType):
    all_exercises = List(Exercise)
    exercises_per_muscles = List(Exercise, muscles=List(String))

    def resolve_exercises_per_muscles(self, info, muscles=List(String)):
        query = {}

        if muscles:
            query["muscles"] = {"$in": muscles}

        exercises = []
        for exercise in collection.find(query):
            exercises.append(Exercise(**exercise))
        return exercises
        
    def resolve_all_exercises(self, info):

        exercises = collection.find()
        
        exercises = []
        for exercise in collection.find():
            exercises.append(Exercise(**exercise))
        return exercises
        
### Main entry point for the API
schema = Schema(query=Query)