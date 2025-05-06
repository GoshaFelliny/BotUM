import logging

import nest_asyncio
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler
from text import *
from setting import TOKEN
import re
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import NoResultFound
from sqlalchemy import create_engine
from datetime import datetime
from models import Teacher
import os

from datetime import timedelta

nest_asyncio.apply()

engine = create_engine("sqlite:///teachers.db")
Session = sessionmaker(bind=engine)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

class SurveyState:
    WAITING_FOR_NAME = 1
    WAITING_FOR_CITY = 2
    WAITING_FOR_BIRTH_DATE = 3


class QState:
    WAITING_FOR_ONE = 4
    WAITING_FOR_TWO = 5
    WAITING_FOR_THREE = 6
    WAITING_FOR_FOUR = 7
    WAITING_FOR_FIVE = 8
    WAITING_FOR_SIX = 9


user_states = {}

cities = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Нижний Новгород", "Челябинск", "Омск",
    "Самара", "Ростов-на-Дону"
]


async def start_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = QState.WAITING_FOR_ONE
    await update.message.reply_text(questions[0])


# Функция для начала анкетирования
async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = SurveyState.WAITING_FOR_NAME
    await update.message.reply_text("Запишите ваше ФИО (формат: Фамилия Имя Отчество):")


async def handle_video(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id
    video_file = update.message.video.file_id

    # Создаем папку media, если она не существует
    os.makedirs('media', exist_ok=True)

    try:
        # Сохраняем видео в папку "медиа"
        new_file = await context.bot.get_file(video_file)
        await new_file.download_to_drive(f'media/{user_id}_video.mp4')  # Сохранение видео
        await update.message.reply_text("Ваше видео успешно сохранено.")
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при сохранении видео.")
        print(f"Ошибка: {e}")


async def send_reminders(app):
    session = Session()
    try:
        current_time = datetime.utcnow()
        # Получаем всех учителей, которые зарегистрировались более 1 минуты назад и не заполнили анкету
        teachers = session.query(Teacher).filter(
            Teacher.text_interview.is_(None),
            Teacher.registration_time <= current_time - timedelta(minutes=24)
        ).all()

        for teacher in teachers:
            try:
                await app.bot.send_message(
                    chat_id=teacher.id,
                    text="Напоминаем вам, что вы еще не прошли анкетирование. Пожалуйста, перейдите ко второму шагу."
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")
    finally:
        session.close()


async def handle_video_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text:
        await update.message.reply_text("Для верификации пришлите пожалуйста видео")
    user_id = update.message.from_user.id
    video_note = update.message.video_note
    context.user_data['video_note'] = f'media/{user_id}.mp4'
    if video_note:
        file = await context.bot.get_file(video_note.file_id)
        await file.download_to_drive(f'media/{user_id}.mp4')
        await handle_algorithm_explanation(update, context)


# Функция для обработки текстовых сообщений
async def handle_text(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id

    # Проверка на наличие текстового сообщения
    if update.message.text:
        text = update.message.text.strip()

        # Проверка на слово "Трудоустройство"
        if text.lower() == "трудоустройство":
            await start_survey(update, context)
            return

        if text.lower() == "зарплата":
            await update.message.reply_text("Чем меньше, тем лучше)")
            return

    # Обработка состояний анкетирования
    if user_id in user_states:
        current_state = user_states[user_id]

        if current_state == SurveyState.WAITING_FOR_NAME:
            await handle_name(update, context)
        elif current_state == SurveyState.WAITING_FOR_CITY:
            await handle_city(update, context)
        elif current_state == SurveyState.WAITING_FOR_BIRTH_DATE:
            await handle_birth_date(update, context)

        # Обработка состояний собеседования
        elif current_state == QState.WAITING_FOR_ONE:
            await handle_experience_kids(update, context)
        elif current_state == QState.WAITING_FOR_TWO:
            await handle_experience_robo(update, context)
        elif current_state == QState.WAITING_FOR_THREE:
            await handle_interview_city(update, context)
        elif current_state == QState.WAITING_FOR_FOUR:
            await handle_free_time(update, context)
        elif current_state == QState.WAITING_FOR_FIVE:
            await handle_best_skills(update, context)
        elif current_state == QState.WAITING_FOR_SIX:
            await handle_video_note(update, context)

    # Обработка видео
    if update.message.video:
        pass

    if update.message.video_note:
        pass


# Функция для обработки ФИО
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    name = update.message.text.strip()

    # Проверка формата ФИО
    if re.match(r'^[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+$', name):
        context.user_data['full_name'] = name  # Сохраняем ФИО
        user_states[user_id] = SurveyState.WAITING_FOR_CITY
        reply_markup = ReplyKeyboardMarkup(
            [[city] for city in cities],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        await update.message.reply_text(
            "Выберите город из списка:",
            reply_markup=reply_markup
        )
    else:
        await update.message.reply_text(
            "Неверный формат ФИО. Попробуйте снова:"
        )


# Функция для обработки выбора города
async def handle_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    city = update.message.text.strip()

    if city in cities:
        context.user_data['city'] = city  # Сохраняем город
        user_states[user_id] = SurveyState.WAITING_FOR_BIRTH_DATE
        await update.message.reply_text(
            "Запишите вашу дату рождения в формате ДД.ММ.ГГГГ:",
            reply_markup=None
        )
    else:
        await update.message.reply_text(
            "Город не найден в списке. Попробуйте снова:"
        )


# Функция для обработки даты рождения
async def handle_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    birth_date = update.message.text.strip()

    # Проверка формата даты
    if re.match(r'^\d{2}\.\d{2}\.\d{4}$', birth_date):
        # Создаем сессию для работы с базой данных
        session = Session()

        try:
            # Проверяем, существует ли пользователь в базе данных
            existing_teacher = session.query(Teacher).filter_by(id=user_id).one()
            await update.message.reply_text(
                "Вы уже проходили анкетирование."
            )
        except NoResultFound:
            # Если пользователя нет в базе, создаем нового
            birth_date_obj = datetime.strptime(birth_date, '%d.%m.%Y').date()

            # Получаем ФИО и город из состояния пользователя
            full_name = context.user_data.get('full_name')
            city = context.user_data.get('city')

            # Создаем экземпляр Teacher
            new_teacher = Teacher(
                id=user_id,
                full_name=full_name,
                city=city,
                birth_date=birth_date_obj
            )

            # Сохраняем данные в базу данных
            session.add(new_teacher)
            session.commit()
            await update.message.reply_text(
                "Спасибо за заполнение анкеты! Ваши данные сохранены. \n"
                "Как будете готовы к следующему этапу, введите /step2"
            )

            del user_states[user_id]  # Удаляем состояние пользователя
        finally:
            session.close()
    else:
        await update.message.reply_text(
            "Неверный формат даты. Попробуйте снова:"
        )


# Обработка ответов на вопросы собеседования
async def handle_experience_kids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    experience = update.message.text.strip()
    context.user_data['experience_kids'] = experience
    user_states[user_id] = QState.WAITING_FOR_TWO
    await update.message.reply_text(questions[1])


async def handle_experience_robo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    experience = update.message.text.strip()
    context.user_data['experience_robo'] = experience
    user_states[user_id] = QState.WAITING_FOR_THREE
    await update.message.reply_text(questions[2])


async def handle_interview_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    city_interview = update.message.text.strip()
    context.user_data['interview_city'] = city_interview
    user_states[user_id] = QState.WAITING_FOR_FOUR
    await update.message.reply_text(questions[3])


async def handle_free_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    free_time = update.message.text.strip()
    context.user_data['free_time'] = free_time
    user_states[user_id] = QState.WAITING_FOR_FIVE
    await update.message.reply_text(questions[4])


async def handle_best_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    best_skills = update.message.text.strip()
    context.user_data['best_skills'] = best_skills
    user_states[user_id] = QState.WAITING_FOR_SIX
    await update.message.reply_text(questions[5])


async def handle_algorithm_explanation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answers = (
        f"Опыт взаимодействия с младшими школьниками: {context.user_data.get('experience_kids')}\n"
        f"Опыт в робототехнике: {context.user_data.get('experience_robo')}\n"
        f"Города для работы: {context.user_data.get('interview_city')}\n"
        f"Свободное время: {context.user_data.get('free_time')}\n"
        f"Лучшие навыки: {context.user_data.get('best_skills')}\n"
    )

    context.user_data['answers'] = answers

    await update.message.reply_text("Вот ваши ответы:\n" + answers)

    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data='confirm'),
         InlineKeyboardButton("Отклонить", callback_data='reject')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Пожалуйста, подтвердите или отклоните ваши данные:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    session = Session()

    try:
        # Получаем текст интервью из user_data
        text_interview = (
            f"Опыт взаимодействия с младшими школьниками: {context.user_data.get('experience_kids')}\n"
            f"Опыт в робототехнике: {context.user_data.get('experience_robo')}\n"
            f"Города для работы: {context.user_data.get('interview_city')}\n"
            f"Свободное время: {context.user_data.get('free_time')}\n"
            f"Лучшие навыки: {context.user_data.get('best_skills')}\n"
        )

        if query.data == 'confirm':
            # Обновляем запись в базе данных
            existing_teacher = session.query(Teacher).filter_by(id=user_id).one()
            existing_teacher.text_interview = text_interview  # Сохраняем текст интервью
            existing_teacher.video_path = context.user_data['video_note']
            session.commit()  # Сохраняем изменения в базе данных

            await query.message.reply_text("Ваши данные подтверждены. Спасибо!")
        elif query.data == 'reject':
            await query.message.reply_text("Ваши данные отклонены. Пожалуйста, начните заново.")
            # Здесь можно добавить логику для сброса данных или повторного начала опроса
        del user_states[user_id]  # Удаляем состояние пользователя


    except NoResultFound:
        await query.message.reply_text("Пользователь не найден в базе данных.")
    finally:
        session.close()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        ['Зарплата', 'Трудоустройство'],
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(START_TEXT, reply_markup=reply_markup)


async def lesson1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(LESSON1_TEXT)


async def lesson2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(LESSON2_TEXT)


async def lesson3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(LESSON3_TEXT)


async def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lesson1", lesson1))
    app.add_handler(CommandHandler("step2", start_q))
    app.add_handler(CommandHandler("lesson2", lesson2))
    app.add_handler(CommandHandler("lesson3", lesson3))
    app.add_handler(MessageHandler(None, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))  # Добавляем обработчик для кнопок
    app.job_queue.run_repeating(lambda context: send_reminders(app), interval=3600, first=0)

    app.run_polling()


if __name__ == '__main__':
    import asyncio
    # Запускаем основной цикл
    asyncio.run(main())