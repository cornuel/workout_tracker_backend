from graphene import ObjectType, String, Int, Field, List, Boolean

#### GraphQL Workout Object
class Workout(ObjectType):
    _id = String()
    name = String()
    sets = Int()
    reps = Int()
    date = String()
    done = Boolean()
    user_id = String()
    
class TotalReps(ObjectType):
    workout_name = String(default_value="")
    total_reps = Int(default_value=0)
    date_gte = String()
    date_lte = String()
    user_id = String()