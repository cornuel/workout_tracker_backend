from pymongo import MongoClient
from decouple import config
from bson import ObjectId
from graphene import ObjectType, String, Int, Field, List, Boolean
import graphene
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import Workout, TotalReps, WorkoutNameEnum

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
workouts_collection = db["workouts"]
exercises_collection = db["exercises"]

### CreateWorkout Mutation
class CreateWorkout(graphene.Mutation):
    class Arguments:
        exercise_id = String(required=True)
        sets = Int(required=True)
        reps = Int(required=True)
        weight = Int()
        date = String(required=True)
        done = Boolean(required=True)
        comment = String()
        user_id = String(required=True)
    
    # output of the mutation
    workout = Field(lambda: Workout)
    
    ### Create Workout
    def mutate(self, info, exercise_id, sets, reps, date, done, user_id, weight=None, comment=None):
        exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
        if not exercise:
            raise ValueError(f"Exercise with ID '{exercise_id}' not found")
        
        workout_dict = {
            "exercise": exercise,
            "sets": sets,
            "reps": reps,
            "date": date,
            "done": done,
            "user_id": ObjectId(user_id),
            "weight": weight,
            "comment": comment
        }
        
        result = workouts_collection.insert_one(workout_dict)
        workout_dict["_id"] = result.inserted_id

        workout = Workout(**workout_dict)
        return CreateWorkout(workout=workout)
    

### DeleteWorkout Mutation
class DeleteWorkout(graphene.Mutation):
    class Arguments:
        workout_id = String(required=True)
        user_id = String(required=True)

    # output of the mutation
    success = Boolean()
    
    def mutate(self, info, workout_id, user_id):
        result = workouts_collection.delete_one({"_id": ObjectId(workout_id), "user_id": ObjectId(user_id)})
        if result.deleted_count == 1:
            return DeleteWorkout(success=True)
        else:
            return DeleteWorkout(success=False)
        
        
### UpdateWorkout Mutation
class UpdateWorkout(graphene.Mutation):
    class Arguments:
        workout_id = String(required=True)
        exercise_id = String()
        sets = Int()
        reps = Int()
        weight = Int()
        date = String()
        done = Boolean()
        comment = String()
        user_id = String(required=True)
        
    # output of the mutation
    workout = Field(lambda: Workout)
    
    def mutate(self, info, workout_id, exercise_id, user_id, **kwargs):
        
        exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
        if not exercise:
            raise ValueError(f"Exercise with ID '{exercise_id}' not found")
        
        if "weight" not in kwargs:
            kwargs["weight"] = None
        
        update = {"$set": {"exercise": exercise, **kwargs}}
        
        result = workouts_collection.update_one({ "_id": ObjectId(workout_id), "user_id": ObjectId(user_id) }, update)
        
        if result.modified_count == 1:
            workout_dict = workouts_collection.find_one({"_id": ObjectId(workout_id), "user_id": ObjectId(user_id)})
            workout = Workout(**workout_dict)
            return UpdateWorkout(workout=workout)
        else:
            return UpdateWorkout(workout=None)
        

### Available Mutations
class Mutation(ObjectType):
    create_workout = CreateWorkout.Field()
    update_workout = UpdateWorkout.Field()
    delete_workout = DeleteWorkout.Field()
    

### Available Queries
class Query(ObjectType):
    workouts = List(Workout, 
                    user_id=String(required=True), 
                    date_gte=String(), 
                    date_lte=String())
    one_workout_total_reps = Field(TotalReps, 
                                user_id=String(required=True), 
                                workout_name=String(), 
                                time_range=String())
    all_workouts_total_reps = List(TotalReps, 
                                user_id=String(required=True), 
                                workout_name=String(), 
                                time_range=String())
    workouts_left_today = List(Workout, user_id=String(required=True))
    workouts_left_week = List(Workout, user_id=String(required=True))
    
    def resolve_workouts(self, info, user_id, date_gte=None, date_lte=None):
        query = {"user_id": ObjectId(user_id)}
        if date_gte and date_lte:
            query.update({"date": {"$gte": date_gte, "$lte": date_lte}})
        elif date_gte:
            query.update({"date": {"$gte": date_gte}})
        elif date_lte:
            query.update({"date": {"$lte": date_lte}})
            
        workouts = []
        for workout in workouts_collection.find(query):
            print(workout)
            workouts.append(Workout(**workout))
        return workouts
    
    def resolve_workouts_left_today(self, info, user_id):
        today = datetime.now().strftime("%Y-%m-%d")
        query = {"user_id": ObjectId(user_id), "date": today, "done": False}
        workouts = []

        for workout in workouts_collection.find(query):
            workouts.append(Workout(**workout))

        return workouts

    def resolve_workouts_left_week(self, info, user_id):
        today = datetime.now().date()
        start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        end_date = start_date + timedelta(days=6)

        query = {"user_id": ObjectId(user_id), "date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}, "done": False}
        workouts = []

        for workout in workouts_collection.find(query):
            workouts.append(Workout(**workout))

        return workouts
    
    def resolve_one_workout_total_reps(self, info, user_id, workout_name, time_range=None):
        total_reps = 0
        query = {"user_id": ObjectId(user_id), "name": workout_name}
        
        end_date = datetime.now()

        if time_range == "week":
            today = datetime.now().date()
            start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        elif time_range == "month":
            start_date = datetime(datetime.now().year, datetime.now().month, 1)
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        elif time_range == "year":
            start_date = datetime(datetime.now().year, 1, 1)
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        else:
            pass

        for workout in workouts_collection.find(query):
            total_reps += workout["sets"] * workout["reps"]
        return TotalReps(
            workout_name=workout_name, 
            total_reps=total_reps, 
            user_id=user_id
        )
            
    def resolve_all_workouts_total_reps(self, info, user_id, workout_name=None, time_range=None):
        total_reps = 0
        query = {"user_id": ObjectId(user_id)}
        
        end_date = datetime.now()

        if time_range == "week":
            today = datetime.now().date()
            start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        elif time_range == "month":
            start_date = datetime(datetime.now().year, datetime.now().month, 1)
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        elif time_range == "year":
            start_date = datetime(datetime.now().year, 1, 1)
            query.update({"date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}})
        else:
            pass

        workouts = workouts_collection.find(query)
        workout_totals = {}

        for workout in workouts:
            # print(workout)
            workout_name = workout["name"]
            total_reps = workout["sets"] * workout["reps"]
            if workout_name in workout_totals:
                workout_totals[workout_name] += total_reps
            else:
                workout_totals[workout_name] = total_reps
                
        
        print(workout_totals)

        return [TotalReps(workout_name=workout_name, total_reps=total_reps, user_id=user_id) 
                    for workout_name, total_reps in workout_totals.items()]


### Main entry point for the API
schema = graphene.Schema(query=Query, mutation=Mutation)