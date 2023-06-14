from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import graphene
from graphene import ObjectType, String, Date, Int, Field, List
from bson import ObjectId
from graphene.types import Boolean
from graphql import execute
from decouple import config
import logging
from logging.handlers import RotatingFileHandler
import re

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

app = Flask(__name__)

cors = CORS(app)

# Configure logging handler
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

# Set logging level for Flask app
app.logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    app.run(debug=True)

client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
collection = db["workouts"]


#### GraphQL Workout Object
class Workout(ObjectType):
    _id = String()
    name = String()
    sets = Int()
    reps = Int()
    date = String()
    done = Boolean()
    
class TotalReps(ObjectType):
    workout_name = String()
    total_reps = Int()
    since_date = String()

    # def __init__(self, **kwargs):
    #     self._id = kwargs.get("_id", None)
    #     super().__init__(**kwargs)
    
### GraphQL Workout Mutation
class CreateWorkout(graphene.Mutation):
    class Arguments:
        name = String(required=True)
        sets = Int(required=True)
        reps = Int(required=True)
        date = String(required=True)
        done = Boolean(required=True)
    
    workout = Field(lambda: Workout)
    
    ### Create Workout
    def mutate(self, info, name, sets, reps, date, done):
        workout_dict = {
            "name": name,
            "sets": sets,
            "reps": reps,
            "date": date,
            "done": done
        }
        app.logger.debug("mutate workout_dict: %s", workout_dict)
        
        ### add mandatory mangodb _id field 
        result = collection.insert_one(workout_dict)
        workout_dict["_id"] = result.inserted_id
        
        workout = Workout(**workout_dict)
        return CreateWorkout(workout=workout)
    
class DeleteWorkout(graphene.Mutation):
    class Arguments:
        workout_id = String(required=True)

    success = Boolean()
    
    def mutate(self, info, workout_id):
        result = collection.delete_one({"_id": ObjectId(workout_id)})
        if result.deleted_count == 1:
            return DeleteWorkout(success=True)
        else:
            return DeleteWorkout(success=False)
        
class UpdateWorkout(graphene.Mutation):
    class Arguments:
        workout_id = String(required=True)
        name = String()
        sets = Int()
        reps = Int()
        date = String()
        done = Boolean()
        
    workout = Field(lambda: Workout)
    
    def mutate(self, info, workout_id, **kwargs):
        update = {"$set": kwargs}
        result = collection.update_one(
            { "_id": ObjectId(workout_id) }, update)
        if result.modified_count == 1:
            workout_dict = collection.find_one({"_id": ObjectId(workout_id)})
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
    workouts = List(Workout, date_gte=String(), date_lte=String())
    total_reps_week = Field(TotalReps, workout_name=String(required=True))
    total_reps_month = Field(TotalReps, workout_name=String(required=True))
    total_reps_year = Field(TotalReps, workout_name=String(required=True))
    total_reps_ever = Field(TotalReps, workout_name=String(required=True))
    
    def resolve_workouts(self, info, date_gte=None, date_lte=None):
        query = {}
        if date_gte and date_lte:
            query.update({"date": {"$gte": date_gte, "$lte": date_lte}})
        elif date_gte:
            query.update({"date": {"$gte": date_gte}})
        elif date_lte:
            query.update({"date": {"$lte": date_lte}})
            
        workouts = []
        for workout in collection.find(query):
            workouts.append(Workout(**workout))
        return workouts
    
    def resolve_total_reps_week(self, info, workout_name):
        today = datetime.now().date()
        start_date = datetime.combine(today - timedelta(days=today.weekday()), datetime.min.time())
        end_date = datetime.now()
        total_reps = 0
        for workout in collection.find({"name": workout_name}):
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            if start_date <= workout_date <= end_date:
                # print(f"start_date: {start_date}")
                # print(f"workout_date: {workout_date}")
                # print(f"end_date: {end_date}")
                total_reps += workout["sets"] * workout["reps"]
        return TotalReps(workout_name=workout_name, total_reps=total_reps, since_date=start_date.strftime("%Y-%m-%d"))


    def resolve_total_reps_month(self, info, workout_name):
        start_date = datetime(datetime.now().year, datetime.now().month, 1)
        end_date = datetime.now()
        total_reps = 0
        for workout in collection.find({"name": workout_name}):
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            if start_date <= workout_date <= end_date:
                # print(f"start_date: {start_date}")
                # print(f"workout_date: {workout_date}")
                # print(f"end_date: {end_date}")
                total_reps += workout["sets"] * workout["reps"]
        return TotalReps(workout_name=workout_name, total_reps=total_reps, since_date=start_date.strftime("%Y-%m-%d"))

    def resolve_total_reps_year(self, info, workout_name):
        start_date = datetime(datetime.now().year, 1, 1)
        end_date = datetime.now()
        total_reps = 0
        for workout in collection.find({"name": workout_name}):
            workout_date = datetime.strptime(workout["date"], "%Y-%m-%d")
            if start_date <= workout_date <= end_date:
                total_reps += workout["sets"] * workout["reps"]
        return TotalReps(workout_name=workout_name, total_reps=total_reps, since_date=start_date.strftime("%Y-%m-%d"))

    def resolve_total_reps_ever(self, info, workout_name):
        total_reps = 0
        for workout in collection.find({"name": workout_name}):
            total_reps += workout["sets"] * workout["reps"]
        return TotalReps(workout_name=workout_name, total_reps=total_reps, since_date=datetime(1993, 5, 8).strftime("%Y-%m-%d"))
    
### Main entry point for the API
schema = graphene.Schema(query=Query, mutation=Mutation)

@app.route("/graphql", methods=["POST"])
def graphql():
    data = request.get_json()

    query = data["query"]
    variables = data.get("variables", {})
    
    # app.logger.debug("Received query: %s", query)
    # app.logger.debug("Received variables: %s", variables)
    
    result = schema.execute(
        query,
        variable_values = variables
    )
    
    if result.errors:
        response = {"errors": [str(error) for error in result.errors]}
    else:
        response = {"data": result.data}
    return jsonify(response)

@app.route("/", methods=["GET"])
def hello_world():
    return "Hello World!"