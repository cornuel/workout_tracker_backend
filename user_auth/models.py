from graphene import ObjectType, String

#### GraphQL User Object
class User(ObjectType):
    _id = String()
    username = String()
    email = String()
    password = String()