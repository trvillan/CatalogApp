import sys
from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()


class User(Base):
	"""Table of Users"""

	__tablename__ = 'user'

	name = Column(String(250), nullable = False)
	id = Column(Integer, primary_key = True)
	email = Column(String(250), nullable = False)
	picture = Column(String(500))

	@property
	def serialize(self):
		#returns object data in easily serializeable format
		return {
			'username': self.name,
		}


class Activities(Base):
	"""Table of Activities that includes the id of the most recent user to edit"""

	__tablename__ = 'activities'

	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		#returns object data in easily serializeable format
		return {
			'activity_name': self.name,
			'most_recent_editor': self.user.name,
			'most_recent_editor_id': self.user_id,
		}


class Subcategories(Base):
	"""Table of Subcategories that includes the id of the most recent user to edit"""

	__tablename__ = 'subcategories'

	name = Column(String(80), nullable = False)
	id = Column(Integer, primary_key = True)
	activity_id = Column(Integer, ForeignKey('activities.id'))
	activity = relationship(Activities)
	user_id = Column(Integer, ForeignKey('user.id'))
	user = relationship(User)

	@property
	def serialize(self):
		#returns object data in easily serializeable format
		return {
			'activity_name': self.activity.name,
			'subcategory': self.name,
			'most_recent_editor': self.user.name,
			'most_recent_editor_id': self.user_id,
		}


###### insert at end of file #####

engine = create_engine(
	'sqlite:///categories.db')

Base.metadata.create_all(engine)