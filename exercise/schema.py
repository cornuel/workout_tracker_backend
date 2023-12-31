from pymongo import MongoClient
from decouple import config
from bson import ObjectId
from graphene import ObjectType, List, String, Schema

from .models import Exercise, Poses

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
exercises_collection = db["exercises"]
poses_collection = db["poses"]
db_user_workouts = client["user_workouts"]

class Query(ObjectType):
    all_exercises = List(Exercise, muscles=List(String))
    all_poses = List(Poses)
    user_exercises = List(Exercise, user_id=String(required=True), muscles=List(String))

    def resolve_all_exercises(self, info, muscles=List(String)):
        pipeline = []

        # Match stage based on muscles
        if muscles:
            match_conditions = [{"muscles": muscle} for muscle in muscles]
            # Match all muscles with an AND condition
            pipeline.append({"$match": {"$and": match_conditions}})

        pipeline.append({"$sort": {"name": 1}})

        # Execute the aggregation pipeline
        exercises = list(exercises_collection.aggregate(pipeline))

        exercise_objects = [Exercise(**exercise) for exercise in exercises]

        return exercise_objects
    
    def resolve_all_poses(self, info):
        poses = []
        
        for pose in poses_collection.find():
            poses.append(Poses(**pose))
        return poses
    
    def resolve_user_exercises(self, info, user_id, muscles=List(String)):
        query = {}
        
        user_collection = db_user_workouts[f"user_{user_id}"]

        if muscles:
            query = {"exercise.muscles": {"$in": muscles}}
            
        exercises_cursor = user_collection.find(query).distinct("exercise")

        exercises = [Exercise(**exercise) for exercise in exercises_cursor]

        return exercises

        
### Main entry point for the API
schema = Schema(query=Query)