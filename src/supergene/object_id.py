#!/$USER_HOME/.dev/py/supergene/.venv/bin/python

from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom Pydantic field for MongoDB ObjectId"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, schema, field):
        schema.update(type="string")
        return schema
