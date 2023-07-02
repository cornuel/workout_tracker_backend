from flask import Flask, request, jsonify, Blueprint
from flask_bcrypt import Bcrypt
from flask_cors import CORS, cross_origin
from flask_jwt_extended import JWTManager, jwt_required, create_access_token
from graphene.types import Boolean
import graphene
from pymongo import MongoClient
from graphql import execute
from decouple import config
import logging
from logging.handlers import RotatingFileHandler

from workout.schema import schema as workout_schema
from user_auth.schema import schema as user_auth_schema
from exercise.schema import schema as exercise_schema

# Configure MongoDBClient
client = MongoClient(config('MONGO_URI'))

db = client["workouttracker"]
collection = db["users"]

app = Flask(__name__)
bcrypt = Bcrypt(app)

# Enable CORS
cors = CORS(app)

class MergedQuery(workout_schema.query, user_auth_schema.query, exercise_schema.query):
    pass

class MergedMutation(workout_schema.mutation):
    pass

schema = graphene.Schema(query=MergedQuery, mutation=MergedMutation)

# app.add_url_rule('/graphql', view_func=GraphQLView.as_view('graphql', schema=schema, graphiql=True))

# Configure JWT
app.config["JWT_SECRET_KEY"] = config('JWT_SECRET_KEY')
jwt = JWTManager(app)

# Configure logging handler
handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=1)
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.debug = True  # Enable debug mode

# Set logging level for Flask app
app.logger.setLevel(logging.DEBUG)


if __name__ == "__main__":
    app.run(debug=True)

@app.route("/login", methods=["POST"])
@cross_origin()
def login():
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    
    user = collection.find_one({"username": username})
    
    if not user:
        return jsonify({"msg": "User not found"}), 404
    # bcrypt.check_password_hash returns true if password matches
    if not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"msg": "Incorrect password"}), 401
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token), 200

@app.route("/signup", methods=["POST"])
def signup():
    
    username = request.json.get("username", None)
    password = request.json.get("password", None)
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    email = request.json.get("email", None)

    user = collection.find_one({"username": username})
    if user:
        return jsonify({"msg": "Username already exists"}), 409

    collection.insert_one({"username": username, "password": password_hash, "email": email})
    access_token = create_access_token(identity=username)
    return jsonify(access_token=access_token)

@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    # TODO define logout
    return jsonify({"msg": "Logged out"})

@app.route("/graphql", methods=["POST"])
# @jwt_required()
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