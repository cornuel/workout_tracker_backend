from pymongo import MongoClient
from decouple import config
from bson import ObjectId
from graphene import ObjectType, String, Int, Field, List, Boolean
import graphene
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import bleach

from .models import Workout, TotalReps, Exercise, MaxDuration, MaxWeight

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
        # Sanitize the comment using bleach
        sanitized_comment = bleach.clean(comment)
        
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
            "comment": sanitized_comment
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

        # Sanitize and validate the values in kwargs
        sanitized_kwargs = {}
        for key, value in kwargs.items():
            sanitized_value = bleach.clean(value)
            sanitized_kwargs[key] = sanitized_value

        update = {"$set": {"exercise": exercise, **sanitized_kwargs}}

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
    total_reps = List(TotalReps,
                            user_id=String(required=True),
                            exercise_id=String(),
                            time_range=String())
    max_duration = List(MaxDuration,
                            user_id=String(required=True),
                            exercise_id=String(),
                            time_range=String())
    max_weight = List(MaxWeight,
                            user_id=String(required=True),
                            exercise_id=String(),
                            time_range=String())
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
    
    def resolve_total_reps(self, info, user_id, exercise_id=None, time_range=None):
        maxList =[]
        total_reps = 0
        end_date = datetime.now()
        query = {}
        
        user_collection = db_user_workouts[f"user_{user_id}"]
        
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
        
        # exercise_id provided
        if exercise_id:
            exercise_query = {"_id": ObjectId(exercise_id)}
            
            query.update({"exercise._id": ObjectId(exercise_id), 
                        "done": True})
            
            workouts = user_collection.find(query)
            
            exercise = exercises_collection.find_one(exercise_query)
            
            for workout in workouts:
                repetition = workout["sets"] * workout["reps"]
                
                total_reps += repetition
                
            maxList.append(TotalReps(exercise=exercise,
                                    total_reps=total_reps))
        
        # exercise_id not provided
        else:
            query.update({"done": True})
            
            workouts = user_collection.find(query)
            
            for workout in workouts:
                
                exercise_name = workout["exercise"]["name"]
                total_reps = workout["sets"] * workout["reps"]

                exercise = Exercise(**workout["exercise"])

                existing_total_reps = next((total_reps_obj for total_reps_obj in maxList if total_reps_obj.exercise.name == exercise_name), None)

                if existing_total_reps:
                    existing_total_reps.total_reps += total_reps
                    

                else:
                    total_reps_obj = TotalReps(exercise=exercise, total_reps=total_reps)
                    maxList.append(total_reps_obj)

            maxList.reverse()
            
        return maxList
    
    def resolve_max_duration(self, info, user_id, exercise_id=None, time_range=None):
        maxList =[]
        max_duration = 0
        end_date = datetime.now()
        query = {}
        
        user_collection = db_user_workouts[f"user_{user_id}"]
        
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
        
        # exercise_id provided
        if exercise_id:
            exercise_query = {"_id": ObjectId(exercise_id)}
            
            query.update({"exercise._id": ObjectId(exercise_id), 
                        "done": True})
            
            workouts = user_collection.find(query)
            
            exercise = exercises_collection.find_one(exercise_query)
            
            for workout in workouts:
                duration = workout["duration"]
                # print(weight, duration)
                
                if duration is not None and (duration > max_duration):
                    max_duration = duration
                    # print(max_duration)
                    
            
            maxList.append(MaxDuration(exercise=exercise,
                                    max_duration=max_duration))
        
        # exercise_id not provided
        else:
            query.update({"done": True})
            
            workouts = user_collection.find(query)
            
            for workout in workouts:
                
                exercise_name = workout["exercise"]["name"]
                duration = workout["duration"]

                exercise = Exercise(**workout["exercise"])

                existing_total_reps = next((total_reps_obj for total_reps_obj in maxList if total_reps_obj.exercise.name == exercise_name), None)

                if existing_total_reps:
                    
                    # print(duration, existing_total_reps.max_duration)

                    if duration is not None and (duration > existing_total_reps.max_duration):
                        existing_total_reps.max_duration = duration
                else:
                    if duration is not None:
                        total_reps_obj = MaxDuration(exercise=exercise, max_duration=duration)
                        maxList.append(total_reps_obj)

            maxList.reverse()
            
        return maxList
    
    def resolve_max_weight(self, info, user_id, exercise_id=None, time_range=None):
        maxList =[]
        max_duration = 0
        end_date = datetime.now()
        query = {}
        
        user_collection = db_user_workouts[f"user_{user_id}"]
        
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
        
        # exercise_id provided
        if exercise_id:
            exercise_query = {"_id": ObjectId(exercise_id)}
            
            query.update({"exercise._id": ObjectId(exercise_id), 
                        "done": True})
            
            workouts = user_collection.find(query)
            
            exercise = exercises_collection.find_one(exercise_query)
            
            for workout in workouts:
                weight = workout["weight"]
                # print(weight, duration)
                
                if weight is not None and (weight > max_weight):
                    max_weight = weight
                    # print(max_duration)
                    
            
            maxList.append(MaxWeight(exercise=exercise,
                                    max_weight=max_weight))
        
        # exercise_id not provided
        else:
            query.update({"done": True})
            
            workouts = user_collection.find(query)
            
            for workout in workouts:
                
                exercise_name = workout["exercise"]["name"]
                weight = workout["weight"]

                exercise = Exercise(**workout["exercise"])

                existing_total_reps = next((total_reps_obj for total_reps_obj in maxList if total_reps_obj.exercise.name == exercise_name), None)

                if existing_total_reps:
                    
                    # print(duration, existing_total_reps.max_duration)

                    if weight is not None and (weight > existing_total_reps.max_weight):
                        existing_total_reps.max_duration = weight
                else:
                    if weight is not None:
                        total_reps_obj = MaxWeight(exercise=exercise, max_weight=weight)
                        maxList.append(total_reps_obj)

            maxList.reverse()
            
        return maxList


### Main entry point for the API
schema = graphene.Schema(query=Query, mutation=Mutation)