from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import declarative_base
from datetime import date, datetime

Base = declarative_base()


# Определяем модель Преподавателя
class Teacher(Base):
    __tablename__ = 'teachers'  # Имя таблицы в базе данных

    id = Column(Integer, primary_key=True)  # Уникальный идентификатор
    full_name = Column(String, nullable=False)  # ФИО
    city = Column(String, nullable=False)  # Город
    birth_date = Column(Date, nullable=False)  # Дата рождения
    hours_per_week = Column(Integer, default=0)  # Часы в неделю (по умолчанию 0)
    registration_time = Column(DateTime, default=datetime.utcnow)  # Время регистрации
    video_path = Column(String, nullable=True)  # Путь к видеофайлу (может быть пустым)
    text_interview = Column(Text, nullable=True)  # Текст интервью
    address = Column(Text, nullable=True) # Адрес для отправки набора

    def __repr__(self):
        return (f"<Teacher(full_name='{self.full_name}', city='{self.city}', "
                f"birth_date='{self.birth_date}', hours_per_week={self.hours_per_week}, "
                f"survey_completed={self.survey_completed}, video_path='{self.video_path}')>")


# Создаем базу данных и таблицы
def create_database():
    engine = create_engine('sqlite:///teachers.db')  # Используем SQLite для примера
    Base.metadata.create_all(engine)  # Создаем таблицы


create_database()
