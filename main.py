import logging
import os
import re
from datetime import datetime, timedelta

import nest_asyncio
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    CallbackQueryHandler
)
from sqlalchemy import create_engine
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import sessionmaker

from models import Teacher
from setting import TOKEN
from text import *

# ============================ КОНСТАНТЫ ============================
CITIES = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Нижний Новгород", "Челябинск", "Омск",
    "Самара", "Ростов-на-Дону"
]
# ============================ НАСТРОЙКА ============================
nest_asyncio.apply()

engine = create_engine("sqlite:///teachers.db")
Session = sessionmaker(bind=engine)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# ============================ СОСТОЯНИЯ ============================


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



class LessonState:
    LES_SCRATCH = 10
    ROBO_KIT = 11
    VIDEO_LESSON = 12

user_states = {}


# ============================ ОБРАБОТЧИКИ КОМАНД ============================

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


async def start_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = QState.WAITING_FOR_ONE
    await update.message.reply_text(questions[0])


async def les_scratch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_states[user_id] = LessonState.LES_SCRATCH
    await update.message.reply_text(SCRATCH_LESSON_TEXT)


# ============================ АНКЕТИРОВАНИЕ ============================

async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = SurveyState.WAITING_FOR_NAME
    await update.message.reply_text("Запишите ваше ФИО (формат: Фамилия Имя Отчество):")


# Функция для обработки ФИО
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    name = update.message.text.strip()

    # Проверка формата ФИО
    if re.match(r'^[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+\s[А-ЯЁ][а-яё]+$', name):
        context.user_data['full_name'] = name  # Сохраняем ФИО
        user_states[user_id] = SurveyState.WAITING_FOR_CITY
        reply_markup = ReplyKeyboardMarkup(
            [[city] for city in CITIES],
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

    if city in CITIES:
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




# ============================ СОБЕСЕДОВАНИЕ (ВОПРОСЫ) ============================

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
        [InlineKeyboardButton("✅ Подтвердить", callback_data="interview_confirm")],
        [InlineKeyboardButton("❌ Отклонить", callback_data="interview_reject")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Пожалуйста, подтвердите или отклоните ваши данные:", reply_markup=reply_markup)


# ============================ ОБРАБОТКА МЕДИА ============================

async def save_user_video(
    video_note,
    bot,
    folder_name: str,
    video_name: str
) -> str:
    """
    Сохраняет видео пользователя в папку media/<folder_name>/<video_name>.mp4
    :param video_note: объект video_note из update.message.video_note
    :param bot: context.bot
    :param folder_name: имя папки (например, ФИО или id пользователя)
    :param video_name: имя файла (без расширения)
    :return: путь к сохранённому видеофайлу
    """
    user_folder = os.path.join('media', folder_name.strip().replace(' ', '_'))
    os.makedirs(user_folder, exist_ok=True)
    if not video_name.lower().endswith('.mp4'):
        video_name += '.mp4'
    video_path = os.path.join(user_folder, video_name)
    if video_note:
        file = await bot.get_file(video_note.file_id)
        await file.download_to_drive(video_path)
    return video_path



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




async def handle_video_note_verification(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    video_note = update.message.video_note
    session = Session()
    teacher = session.get(Teacher, user_id)
    folder_name = teacher.full_name  # или teacher.id, или любой другой параметр
    video_name = "verification_video"  # или любое другое имя

    video_path = await save_user_video(
        video_note=video_note,
        bot=context.bot,
        folder_name=folder_name,
        video_name=video_name
    )
    context.user_data['video_note'] = video_path

    # Теперь вы можете делать что угодно дальше:
    await update.message.reply_text("Ваше видео успешно сохранено!")
    await handle_algorithm_explanation(update, context)


async def handle_video_note_lesson(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    video_note = update.message.video_note
    session = Session()
    teacher = session.get(Teacher, user_id)
    folder_name = teacher.full_name  # или teacher.id, или любой другой параметр
    video_name = "lesson_video"  # или любое другое имя

    video_path = await save_user_video(
        video_note=video_note,
        bot=context.bot,
        folder_name=folder_name,
        video_name=video_name
    )
    context.user_data['video_note'] = video_path

    # Теперь вы можете делать что угодно дальше:
    await update.message.reply_text("Ваше видео успешно сохранено!")
    await update.message.reply_text(ROBO_KIT_TEXT)
    user_states[user_id] = LessonState.ROBO_KIT



# ============================ ЭТАП ДАЛЬНЕЙШЕГО ОБУЧЕНИЯ ==============================


async def handle_adress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    address = update.message.text.strip()
    context.user_data['address'] = address  # Сохраняем адрес под ключом 'address'

    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="address_confirm")],
        [InlineKeyboardButton("✏️ Изменить", callback_data="address_edit")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Вы указали адрес:\n\n<b>{address}</b>\n\nВсе верно?",
        reply_markup=reply_markup,
        parse_mode="HTML"
    )



# ============================ ОБРАБОТКА ТЕКСТА И СОСТОЯНИЙ ============================

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
        # Здесь бот ждет видео-кружок (QState.WAITING_FOR_SIX)
        elif current_state == QState.WAITING_FOR_SIX:
            if update.message.video_note:
                await handle_video_note_verification(update, context)
            else:
                await update.message.reply_text("Пожалуйста, отправьте видео-кружок (кнопка 📹 в Telegram)!")
        # Здесь бот ждет видео-кружок для этапа Scratch
        elif current_state == LessonState.LES_SCRATCH:
            if update.message.video_note:
                await handle_video_note_lesson(update, context)
            else:
                await update.message.reply_text("Пожалуйста, отправьте видео-кружок (кнопка 📹 в Telegram) для проверки!")
        elif current_state == LessonState.ROBO_KIT:
            await handle_adress(update, context)

    # Обработка видео
    if update.message.video:
        pass

    if update.message.video_note:
        pass


# ============================ CALLBACK (КНОПКИ) ============================

# Обработчик для интервью
async def interview_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

        if query.data == 'interview_confirm':
            # Обновляем запись в базе данных
            existing_teacher = session.query(Teacher).filter_by(id=user_id).one()
            existing_teacher.text_interview = text_interview  # Сохраняем текст интервью
            existing_teacher.video_path = os.path.dirname(context.user_data['video_note'])
            session.commit()  # Сохраняем изменения в базе данных

            await query.message.reply_text("Ваши данные подтверждены. Спасибо!")
        elif query.data == 'interview_reject':
            await query.message.reply_text("Ваши данные отклонены. Пожалуйста, начните заново.")
            # Здесь можно добавить логику для сброса данных или повторного начала опроса
        if user_id in user_states:
            del user_states[user_id]  # Удаляем состояние пользователя


    except NoResultFound:
        await query.message.reply_text("Пользователь не найден в базе данных.")
    finally:
        session.close()


# Обработчик для адреса
async def address_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == 'address_confirm':
        address = context.user_data.get('address')
        if not address:
            await query.edit_message_text("Адрес не найден. Пожалуйста, введите адрес заново.")
            return

        session = Session()
        try:
            teacher = session.query(Teacher).filter_by(id=user_id).one_or_none()
            if teacher is None:
                await query.edit_message_text("Пользователь не найден в базе данных.")
                return

            teacher.address = address  # Сохраняем адрес
            session.commit()

            await query.edit_message_text(f"Адрес сохранён:\n{address}\nСпасибо!")
            # Здесь можно перейти к следующему шагу, например:
            # await query.message.reply_text("Следующий шаг...")
        except Exception as e:
            await query.edit_message_text(f"Ошибка при сохранении адреса: {e}")
        finally:
            session.close()

    elif query.data == 'address_edit':
        await query.edit_message_text("Пожалуйста, введите адрес еще раз:")
        # Можно сбросить адрес в user_data, если нужно:
        context.user_data.pop('address', None)



# ============================ НАПОМИНАНИЯ ============================

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


# ============================ MAIN ============================

async def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lesson1", lesson1))
    app.add_handler(CommandHandler("step2", start_q))
    app.add_handler(CommandHandler("step3", les_scratch))
    app.add_handler(CommandHandler("lesson2", lesson2))
    app.add_handler(CommandHandler("lesson3", lesson3))
    app.add_handler(MessageHandler(None, handle_text))
    app.add_handler(CallbackQueryHandler(interview_button_handler, pattern=r"^interview_"))
    app.add_handler(CallbackQueryHandler(address_button_handler, pattern=r"^address_"))
    app.job_queue.run_repeating(lambda context: send_reminders(app), interval=3600, first=0)

    app.run_polling()


if __name__ == '__main__':
    import asyncio

    # Запускаем основной цикл
    asyncio.run(main())
