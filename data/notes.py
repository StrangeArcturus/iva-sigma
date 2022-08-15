import sqlalchemy
from .db_session import SqlAlchemyBase


class Notes(SqlAlchemyBase):
    __tablename__ = "notices"

    id = sqlalchemy.Column(
        sqlalchemy.Integer,
        autoincrement=True,
        primary_key=True
    )

    text = sqlalchemy.Column(
        sqlalchemy.String
    )
