import sqlalchemy
from .db_session import SqlAlchemyBase


class Notices(SqlAlchemyBase):
    __tablename__ = "notices"

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        primary_key=True,
        autoincrement=True
    )

    text = sqlalchemy.Column(
        sqlalchemy.String,
        primary_key=True
    )
