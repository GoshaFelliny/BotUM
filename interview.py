from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, CallbackQueryHandler
from text import *
from setting import TOKEN
import re
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime
from models import Teacher

# Настройка базы данных
engine = create_engine('sqlite:///teachers.db')
Session = sessionmaker(bind=engine)


# Состояния для анкетирования
class SurveyState:
    WAITING_FOR_NAME = 1
    WAITING_FOR_CITY = 2
    WAITING_FOR_BIRTH_DATE = 3


# Состояния для собеседования
class QState:
    WAITING_FOR_ONE = 1
    WAITING_FOR_TWO = 2
    WAITING_FOR_THREE = 3
    WAITING_FOR_FOUR = 4
    WAITING_FOR_FIVE = 5
    WAITING_FOR_SIX = 6


user_states = {}

cities = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Нижний Новгород", "Челябинск", "Омск",
    "Самара", "Ростов-на-Дону"
]



# Функция для начала анкетирования
async def start_survey(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = SurveyState.WAITING_FOR_NAME
    await update.message.reply_text("Запишите ваше ФИО (формат: Фамилия Имя Отчество):")


# Функция для обработки текстовых сообщений
async def handle_text(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    # Проверка на слово "Трудоустройство"
    if text.lower() == "трудоустройство":
        await start_survey(update, context)
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
    else:
        await update.message.reply_text("Введите 'Трудоустройство' для начала анкетирования.")


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
        await update.message.reply_text("Выберите город из списка:", reply_markup=reply_markup)
    else:
        await update.message.reply_text("Неверный формат ФИО. Попробуйте снова:")


# Функция для обработки выбора города
async def handle_city(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id
    city = update.message.text.strip()

    if city in cities:
        context.user_data['city'] = city  # Сохраняем город
        user_states[user_id] = SurveyState.WAITING_FOR_BIRTH_DATE
        await update.message.reply_text("Запишите вашу дату рождения в формате ДД.ММ.ГГГГ:")
    else:
        await update.message.reply_text("Город не найден в списке. Попробуйте снова:")


# Функция для обработки даты рождения
async def handle_birth_date(update: Update, context: ContextTypes) -> None:
    user_id = update.message.from_user.id
    birth_date = update.message.text.strip()

    # Проверка формата даты
    if re.match(r'^\d{2}\.\d{2}\.\d{4}$', birth_date):
        birth_date_obj = datetime.strptime(birth_date, '%d.%m.%Y').date()
        full_name = context.user_data.get('full_name')
        city = context.user_data.get('city')

        new_teacher = Teacher(full_name=full_name, city=city, birth_date=birth_date_obj)
        session = Session()
        session.add(new_teacher)
        session.commit()
        session.close()

        await update.message.reply_text("Спасибо за заполнение анкеты! Ваши данные сохранены.")
        del user_states[user_id]  # Удаляем состояние пользователя
    else:
        await update.message.reply_text("Неверный формат даты. Попробуйте снова:")


# Функция для начала собеседования
async def start_q(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user_states[user_id] = QState.WAITING_FOR_ONE
    await update.message.reply_text(questions[0])


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
    user_id = update.message.from_user.id
    algorithm_explanation = update.message.text.strip()
    context.user_data['algorithm_explanation'] = algorithm_explanation

    answers = (
        f"Опыт взаимодействия с младшими школьниками: {context.user_data.get('experience_kids')}\n"
        f"Опыт в робототехнике: {context.user_data.get('experience_robo')}\n"
        f"Города для работы: {context.user_data.get('interview_city')}\n"
        f"Свободное время: {context.user_data.get('free_time')}\n"
        f"Лучшие навыки: {context.user_data.get('best_skills')}\n"
        f"Объяснение алгоритма: {context.user_data.get('algorithm_explanation')}\n"
    )

    await update.message.reply_text("Вот ваши ответы:\n" + answers)

    keyboard = [
        [InlineKeyboardButton("Подтвердить", callback_data='confirm'),
         InlineKeyboardButton("Отклонить", callback_data='reject')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Пожалуйста, подтвердите или отклоните ваши данные:", reply_markup=reply_markup)
    del user_states[user_id]  # Удаляем состояние пользователя


# Обработка нажатий на кнопки
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm':
        await query.message.reply_text("Ваши данные подтверждены. Спасибо!")
        # Здесь можно добавить логику для сохранения данных в базу данных или другую обработку
    elif query.data == 'reject':
        await query.message.reply_text("Ваши данные отклонены. Пожалуйста, начните заново.")
        # Здесь можно добавить логику для сброса данных или повторного начала опроса


# Обновление функции main для добавления обработчиков
def main() -> None:
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_q))

    app.add_handler(MessageHandler(None, handle_text))
    app.add_handler(CallbackQueryHandler(button_handler))  # Добавляем обработчик кнопок

    app.run_polling()


if __name__ == '__main__':
    main()
