from pymongo import MongoClient
from decouple import config
from graphene import ObjectType, List, String, Schema

from .models import Exercise, Poses

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
exercises_collection = db["exercises"]
poses_collection = db["poses"]

class Query(ObjectType):
    all_exercises = List(Exercise, muscles=List(String))
    all_poses = List(Poses)

    def resolve_all_exercises(self, info, muscles=List(String)):
        query = {}

        if muscles:
            query["muscles"] = {"$in": muscles}
        
        exercises = []
        for exercise in exercises_collection.find(query):
            exercises.append(Exercise(**exercise))
        return exercises
    
    def resolve_all_poses(self, info):
        poses = []
        
        for pose in poses_collection.find():
            poses.append(Poses(**pose))
        return poses
        
### Main entry point for the API
schema = Schema(query=Query)