from graphene import ObjectType, String, Int, Field, List, Boolean

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