from graphene import ObjectType, String, Int, Field, List, Boolean

from exercise.models import Exercise

#### GraphQL Workout Object
class Workout(ObjectType):
    _id = String()
    exercise = Field(Exercise)
    sets = Int()
    reps = Int()
    weight = Int()
    duration = Int()
    date = String()
    done = Boolean()
    comment = String()
    user_id = String()
    
class TotalReps(ObjectType):
    exercise = Field(Exercise)
    total_reps = Int(default_value=0)
    time_range = String()
    
# class TotalDuration(ObjectType):
#     exercise = Field(Exercise)
#     total_duration = Int(default_value=0)
#     date_gte = String()
#     date_lte = String()
    
class MaxWeight(ObjectType):
    exercise = Field(Exercise)
    max_weight = Int(default_value=0)
    time_range = String()
    
class MaxDuration(ObjectType):
    exercise = Field(Exercise)
    max_duration = Int(default_value=0)
    time_range = String()