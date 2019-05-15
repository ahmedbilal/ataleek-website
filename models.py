from peewee import *

db = SqliteDatabase('database.db')
db.connect()


# Models
class Mentor(Model):
    username = TextField(unique=True, null=False)
    status = CharField(choices=[("verified", "Verified",
                                 "pending", "Verification Pending",
                                 "rejected", "Rejected")], null=False)
    profile_link = TextField(unique=True, null=False)
    status_reason = CharField()

    class Meta:
        database = db


class User(Model):
    github_access_token = CharField(null=False)

    class Meta:
        database = db


class Solution(Model):
    url = CharField(unique=True, null=False)
    username = CharField(null=False)

    class Meta:
        database = db


db.create_tables([Mentor, User, Solution])
