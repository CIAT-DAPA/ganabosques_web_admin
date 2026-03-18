import os
from mongoengine import connect

def init_db():
    """
    Initialize the MongoDB connection using environment variables.

    Required environment variables:
    - MONGO_URI: The full MongoDB connection string.
    - MONGO_DB_NAME: The name of the database to connect to.
    """
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("MONGO_DB_NAME")
    if not uri or not db_name:
        raise EnvironmentError("MONGO_URI and MONGO_DB_NAME must be set as environment variables.")
    connect(db=db_name, host=uri)