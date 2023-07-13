from pymongo import MongoClient
from decouple import config
from bson import ObjectId
from graphene import ObjectType, String, Int, Field, List, Boolean
import graphene
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from .models import Workout, TotalReps, Exercise

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
workouts_collection = db["workouts"]
exercises_collection = db["exercises"]
db_user_workouts = client["user_workouts"]

### CreateWorkout Mutation
class CreateWorkout(graphene.Mutation):
    class Arguments:
        exercise_id = String(required=True)
        sets = Int(required=True)
        reps = Int(required=True)
        weight = Int()
        duration = Int()
        date = String(required=True)
        done = Boolean(required=True)
        comment = String()
        user_id = String(required=True)
    
    # output of the mutation
    workout = Field(lambda: Workout)
    
    ### Create Workout
    def mutate(self, info, exercise_id, sets, reps, date, done, user_id, weight=None, duration=None, comment=None):
        user_collection = db_user_workouts[f"user_{user_id}"]
        
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
            "duration": duration,
            "comment": comment
        }
        
        result = user_collection.insert_one(workout_dict)
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
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        result = user_collection.delete_one({"_id": ObjectId(workout_id)})
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
        duration = Int()
        date = String()
        done = Boolean()
        comment = String()
        user_id = String(required=True)
        
    # output of the mutation
    workout = Field(lambda: Workout)
    
    def mutate(self, info, workout_id, exercise_id, user_id, **kwargs):
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        exercise = exercises_collection.find_one({"_id": ObjectId(exercise_id)})
        
        if not exercise:
            raise ValueError(f"Exercise with ID '{exercise_id}' not found")
        
        if "weight" not in kwargs:
            kwargs["weight"] = None
            
        if "duration" not in kwargs:
            kwargs["duration"] = None
        
        update = {"$set": {"exercise": exercise, **kwargs}}
        
        result = user_collection.update_one({ "_id": ObjectId(workout_id)}, update)
        
        print(result)
        
        if result.modified_count == 1:
            workout_dict = user_collection.find_one({"_id": ObjectId(workout_id)})
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
    all_workouts_total_reps = List(TotalReps, 
                                user_id=String(required=True), 
                                time_range=String())
    workout_max = List(TotalReps,
                            user_id=String(required=True),
                            exercise_id=String())
    workouts_left_today = List(Workout, user_id=String(required=True))
    workouts_left_week = List(Workout, user_id=String(required=True))
    
    def resolve_workouts(self, info, user_id, date_gte=None, date_lte=None):
        query = {}
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        if date_gte and date_lte:
            query.update({"date": {"$gte": date_gte, "$lte": date_lte}})
        elif date_gte:
            query.update({"date": {"$gte": date_gte}})
        elif date_lte:
            query.update({"date": {"$lte": date_lte}})
            
        workouts = []
        for workout in user_collection.find(query):
            workouts.append(Workout(**workout))
        return workouts
    
    def resolve_workouts_left_today(self, info, user_id):
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        today = datetime.now().strftime("%Y-%m-%d")
        query = {"user_id": ObjectId(user_id), "date": today, "done": False}
        workouts = []

        for workout in user_collection.find(query):
            workouts.append(Workout(**workout))

        return workouts

    def resolve_workouts_left_week(self, info, user_id):
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        today = datetime.now().date()
        start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        end_date = start_date + timedelta(days=6)

        query = {"user_id": ObjectId(user_id), "date": {"$gte": start_date.strftime("%Y-%m-%d"), "$lte": end_date.strftime("%Y-%m-%d")}, "done": False}
        workouts = []

        for workout in user_collection.find(query):
            workouts.append(Workout(**workout))

        return workouts
    
    def resolve_all_workouts_total_reps(self, info, user_id, time_range=None):
        exercises_totals = []

        query = {"user_id": ObjectId(user_id), "done": True}
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
            exercise_name = workout["exercise"]["name"]
            total_reps = workout["sets"] * workout["reps"]

            exercise = Exercise(**workout["exercise"])

            existing_total_reps = next((total_reps_obj for total_reps_obj in exercises_totals if total_reps_obj.exercise.name == exercise_name), None)
            
            if existing_total_reps:
                existing_total_reps.total_reps += total_reps
            else:
                total_reps_obj = TotalReps(exercise=exercise, total_reps=total_reps)
                exercises_totals.append(total_reps_obj)

        sorted_exercises_totals = sorted(exercises_totals, key=lambda x: x.exercise.name)

        return sorted_exercises_totals

    def resolve_workout_max(self, info, user_id, exercise_id=None):
        maxList =[]
        max_weight, max_duration, total_reps = 0, 0, 0
        
        user_collection = db_user_workouts[f"user_{user_id}"]
        
        # exercise_id provided
        if exercise_id:
            print("ok")
            workouts_query = {"exercise._id": ObjectId(exercise_id), 
                            "done": True}
            exercise_query = {"_id": ObjectId(exercise_id)}
            
            workouts = user_collection.find(workouts_query)
            
            exercise = exercises_collection.find_one(exercise_query)
            
            for workout in workouts:
                weight = workout["weight"]
                duration = workout["duration"]
                repetition = workout["sets"] * workout["reps"]
                # print(weight, duration)
                
                total_reps += repetition
                
                if weight is not None and (weight > max_weight):
                    max_weight = weight
                    # print(max_weight)
                    
                if duration is not None and (duration > max_duration):
                    max_duration = duration
                    # print(max_duration)
                    
            
            maxList.append(TotalReps(exercise=exercise,
                                    total_reps=total_reps,
                                    max_weight=max_weight,
                                    max_duration=max_duration))
        
        # exercise_id not provided
        else:
            workouts = user_collection.find({"done": True})
            
            for workout in workouts:
                exercise_name = workout["exercise"]["name"]
                total_reps = workout["sets"] * workout["reps"]
                weight = workout["weight"]
                duration = workout["duration"]

                exercise = Exercise(**workout["exercise"])

                existing_total_reps = next((total_reps_obj for total_reps_obj in maxList if total_reps_obj.exercise.name == exercise_name), None)

                if existing_total_reps:
                    existing_total_reps.total_reps += total_reps
                    
                    print(weight, existing_total_reps.max_weight)
                    print(duration, existing_total_reps.max_duration)

                    if weight is not None and (weight > existing_total_reps.max_weight):
                        existing_total_reps.max_weight = weight

                    if duration is not None and (duration > existing_total_reps.max_duration):
                        existing_total_reps.max_duration = duration
                else:
                    total_reps_obj = TotalReps(exercise=exercise, total_reps=total_reps, max_weight=weight, max_duration=duration)
                    maxList.append(total_reps_obj)

            maxList.reverse()
            
        return maxList



### Main entry point for the API
schema = graphene.Schema(query=Query, mutation=Mutation)