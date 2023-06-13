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

app = Flask(__name__)

cors = CORS(app)

# Configure logging handler
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

# Set logging level for Flask app
app.logger.setLevel(logging.DEBUG)

app.config['DEBUG'] = True

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
    
    workout = Field(lambda: Workout)
    
    ### Create Workout
    def mutate(self, info, name, sets, reps, date):
        workout_dict = {
            "name": name,
            "sets": sets,
            "reps": reps,
            "date": date
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
### Available Mutations
class Mutation(ObjectType):
    create_workout = CreateWorkout.Field()
    delete_workout = DeleteWorkout.Field()
    
### Available Queries
class Query(ObjectType):
    workouts = List(Workout)
    
    def resolve_workouts(self, info):
        workouts = []
        for workout in collection.find():
            workouts.append(Workout(**workout))
        return workouts
    
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