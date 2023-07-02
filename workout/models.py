from graphene import ObjectType, String, Int, Field, List, Boolean

from workout.model_workoutNameEnum import WorkoutNameEnum
from exercise.models import Exercise

#### GraphQL Workout Object
class Workout(ObjectType):
    _id = String()
    exercise = Field(Exercise)
    sets = Int()
    reps = Int()
    weight = Int()
    date = String()
    done = Boolean()
    comment = String()
    user_id = String()
    
class TotalReps(ObjectType):
    workout_name = String(default_value="")
    total_reps = Int(default_value=0)
    date_gte = String()
    date_lte = String()
    user_id = String()