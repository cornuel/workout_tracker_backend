from graphene import ObjectType, String, Int, Field, List

class Exercise(ObjectType):
    _id = String()
    name = String()
    description = List(String)
    muscles = List(String)
    image = String()