from pymongo import MongoClient
from decouple import config
from bson import ObjectId
from graphene import ObjectType, String, Int, Field, List, Boolean
import graphene
from dateutil.relativedelta import relativedelta
import bleach
from datetime import datetime, timedelta

from .models import Workout, WorkoutPagination, TotalReps, Exercise, MaxDuration, MaxWeight

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
        if comment is not None:
            sanitized_comment = bleach.clean(comment)
        else:
            sanitized_comment = ''
        
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

        sanitized_kwargs = {}
        for key, value in kwargs.items():
            if key == 'comment':
                sanitized_value = bleach.clean(value)
            else:
                sanitized_value = value
            sanitized_kwargs[key] = sanitized_value

        update = {"$set": {"exercise": exercise, **sanitized_kwargs}}

        result = user_collection.update_one({ "_id": ObjectId(workout_id)}, update)

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
    workouts = Field(WorkoutPagination, 
                    user_id=String(required=True), 
                    date_gte=String(), 
                    date_lte=String(),
                    page=Int(),
                    exercise_id=String())
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
    
    def resolve_workouts(self, info, user_id, date_gte=None, date_lte=None, exercise_id=None, page=None):
        query = {}
        user_collection = db_user_workouts[f"user_{user_id}"]

        if date_gte and date_lte:
            query.update({"date": {"$gte": date_gte, "$lte": date_lte}})
        elif date_gte:
            query.update({"date": {"$gte": date_gte}})
        elif date_lte:
            query.update({"date": {"$lte": date_lte}})

        if exercise_id:
            query.update({"exercise._id": ObjectId(exercise_id)})

        
        # Count number of pages
        page_size = 12
        total_workouts = user_collection.count_documents(query)
        num_pages = (total_workouts // page_size) + (total_workouts % page_size > 0)

        workouts_cursor = user_collection.find(query)
        
        if page:
            skip = page_size * (page - 1)
            workouts_cursor = workouts_cursor.sort("date", -1).skip(skip).limit(page_size)
        else:
            workouts_cursor = workouts_cursor.sort("date", -1)

        workouts = [Workout(**workout) for workout in workouts_cursor]
            

        return WorkoutPagination(workouts=workouts, num_pages=num_pages)

    
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
        """
        Calculate and return the total number of repetitions for a user's workouts.

        Parameters:
            info (Info): The GraphQL information object.
            user_id (int): The ID of the user.
            exercise_id (str, optional): The ID of the exercise. Defaults to None.
            time_range (str, optional): The time range for filtering workouts. Can be "week", "month", or "year". Defaults to None.

        Returns:
            List[TotalReps]: A list of TotalReps objects representing the total number of repetitions for each exercise.
        """
        pipeline = []
        
        # Match stage based on time_range
        if time_range:
            today = datetime.now().date()
            start_dates = {
                "week": today - timedelta(days=today.weekday()),
                "month": datetime(today.year, today.month, 1).date(),
                "year": datetime(today.year, 1, 1).date()
            }

            start_date = start_dates.get(time_range)
            if start_date:
                pipeline.append({"$match": {"date": {"$gte": start_date.strftime('%Y-%m-%d'), "$lte": today.strftime('%Y-%m-%d')}}})

        # Match stage based on exercise_id
        if exercise_id:
            pipeline.append({"$match": {"exercise._id": ObjectId(exercise_id)}})
            
        # Match stage based on done
        pipeline.append({"$match": {"done": True}})

        # Group stage to calculate max duration for each exercise
        pipeline.append({"$group": {"_id": "$exercise", "total_reps": {"$sum": {"$multiply": ["$sets", "$reps"]}}}})
        
        # Sort stage to order by max_duration
        pipeline.append({"$sort": {"total_reps": -1}})
        
        result = db_user_workouts[f"user_{user_id}"].aggregate(pipeline)
        
        total_reps = []
        for doc in result:
            if doc["total_reps"]:
                total_reps.append(TotalReps(exercise=doc["_id"], total_reps=doc["total_reps"]))
            
        return total_reps

    def resolve_max_duration(self, info, user_id, exercise_id=None, time_range=None):
        """
        Retrieves the maximum duration for each exercise completed by a user within a specified time range and/or exercise ID.

        Args:
            info (object): The GraphQL info object.
            user_id (str): The ID of the user.
            exercise_id (str, optional): The ID of the exercise. Defaults to None.
            time_range (str, optional): The time range for which to retrieve the maximum durations. Valid values are 'week', 'month', and 'year'. Defaults to None.

        Returns:
            List[MaxDuration]: A list of MaxDuration objects, each containing the exercise ID and the maximum duration achieved for that exercise.
        """
        pipeline = []

        # Match stage based on time_range
        if time_range:
            today = datetime.now().date()
            start_dates = {
                "week": today - timedelta(days=today.weekday()),
                "month": datetime(today.year, today.month, 1).date(),
                "year": datetime(today.year, 1, 1).date()
            }

            start_date = start_dates.get(time_range)
            if start_date:
                pipeline.append({"$match": {"date": {"$gte": start_date.strftime('%Y-%m-%d'), "$lte": today.strftime('%Y-%m-%d')}}})

        # Match stage based on exercise_id
        if exercise_id:
            pipeline.append({"$match": {"exercise._id": ObjectId(exercise_id)}})
            
        # Match stage based on done
        pipeline.append({"$match": {"done": True}})

        # Group stage to calculate max duration for each exercise
        pipeline.append({"$group": {"_id": "$exercise", "max_duration": {"$max": "$duration"}}})
        
        # Sort stage to order by max_duration
        pipeline.append({"$sort": {"max_duration": -1}})
        
        result = db_user_workouts[f"user_{user_id}"].aggregate(pipeline)
        
        max_durations = []
        for doc in result:
            if doc["max_duration"]:
                max_durations.append(MaxDuration(exercise=doc["_id"], max_duration=doc["max_duration"]))
            
        return max_durations

    def resolve_max_weight(self, info, user_id, exercise_id=None, time_range=None):
        """
        Retrieves the maximum weight for each exercise completed by a user within a specified time range and/or exercise ID.

        Args:
            info (object): The GraphQL info object.
            user_id (str): The ID of the user.
            exercise_id (str, optional): The ID of the exercise. Defaults to None.
            time_range (str, optional): The time range for which to retrieve the maximum durations. Valid values are 'week', 'month', and 'year'. Defaults to None.

        Returns:
            List[MaxWeight]: A list of MaxWeight objects, each containing the exercise ID and the maximum weight achieved for that exercise.
        """
        pipeline = []

        # Match stage based on time_range
        if time_range:
            today = datetime.now().date()
            start_dates = {
                "week": today - timedelta(days=today.weekday()),
                "month": datetime(today.year, today.month, 1).date(),
                "year": datetime(today.year, 1, 1).date()
            }

            start_date = start_dates.get(time_range)
            if start_date:
                pipeline.append({"$match": {"date": {"$gte": start_date.strftime('%Y-%m-%d'), "$lte": today.strftime('%Y-%m-%d')}}})

        # Match stage based on exercise_id
        if exercise_id:
            pipeline.append({"$match": {"exercise._id": ObjectId(exercise_id)}})
            
        # Match stage based on done
        pipeline.append({"$match": {"done": True}})

        # Group stage to calculate max duration for each exercise
        pipeline.append({"$group": {"_id": "$exercise", "max_weight": {"$max": "$weight"}}})
        
        # Sort stage to order by max_duration
        pipeline.append({"$sort": {"max_weight": -1}})
        
        result = db_user_workouts[f"user_{user_id}"].aggregate(pipeline)
        
        max_weights = []
        for doc in result:
            if doc["max_weight"]:
                max_weights.append(MaxWeight(exercise=doc["_id"], max_weight=doc["max_weight"]))
            
        return max_weights


### Main entry point for the API
schema = graphene.Schema(query=Query, mutation=Mutation)