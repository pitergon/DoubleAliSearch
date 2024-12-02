from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, func
from sqlalchemy.dialects.postgresql import ARRAY, JSON, TIMESTAMP
from sqlalchemy.orm import relationship
from app.services.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    disabled = Column(Boolean, default=False)

    searches = relationship('Search', back_populates='user')


class Search(Base):
    __tablename__ = 'searches'

    id = Column(Integer, primary_key=True)
    uuid = Column(String, unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    names_list1 = Column(String, nullable=False)
    names_list2 = Column(String, nullable=False)
    messages = Column(ARRAY(String), nullable=False)
    results = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    user = relationship('User', back_populates='searches')