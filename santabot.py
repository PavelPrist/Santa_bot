import logging
import os
import sqlite3

from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor

from dotenv import load_dotenv

from validation import validate_full_name, validate_telephone
load_dotenv()


TOKEN = os.getenv('TELEGRAM_TOKEN')

bot = Bot(token=str(TOKEN))
dp = Dispatcher(bot, storage=MemoryStorage())


class SantaData(StatesGroup):
    """Машина состояний"""
    full_name = State()
    telephone = State()
    address = State()
    comment = State()


def check_santa_in_base(message):
    """Проверяем пользователя на наличие в БД."""
    conn = sqlite3.connect('santas.db')
    cur = conn.cursor()
    info = cur.execute(
        """SELECT * FROM users WHERE tg_id=?""", (message.from_user.id,)
    )
    conn.commit()
    if info.fetchone() is None:
        # Делаем когда нету человека в бд
        logging.info(f'{message.from_user.id}: id Этого человека Нет в базе данных')
        return False
    else:
        return True


@dp.message_handler(commands=['check'])
async def get_data_from_db(message: types.Message):
    """Получаем данные из БД зарегестрированного пользователя."""
    chat_id = str(message.from_user.id)
    conn = sqlite3.connect('santas.db')
    conn.row_factory = sqlite3.Row
    if check_santa_in_base(message):
        cur = conn.execute("""SELECT * FROM users WHERE tg_id=?""", (chat_id,))
        row = cur.fetchone()
        await get_data(
            message,
            row['full_name'],
            row['telephone'],
            row['address'],
            row['comment']
        )
    else:
        await message.answer('Вашей Информации Пока ещё нет В нашей Базе Данных')


def add_to_db(chat_id, full_name, telephone, address, comment):
    """Добавляем нового пользователя в базу."""
    conn = sqlite3.connect('santas.db')
    cur = conn.cursor()
    cur.execute("""insert into users values (?, ?, ?, ?, ?)""", (
        chat_id, full_name, telephone, address, comment,
    ))
    logging.info('Добавляем Нового Пользователя в БД')
    conn.commit()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    """Функция первого обращения к боту."""
    name = message.from_user.full_name
    await bot.send_message(
        message.from_user.id,
        text='Привет, {}. Предлагаю тебе побыть Тайным Сантой. '
             'Нажми кнопку "/santa" для начала процесса регистрации \n\n или '
             'введи /help для большей информации \n\n'
             'ВНИМАНИЕ ваша личная информация будет передана 3 лицам \n\n'
             'Узнать подробности можно через /info.'.format(name),
    )
    logging.info('Бот Стартанул')


@dp.message_handler(commands=['help'])
async def help_message(message: types.Message):
    """Вывод помощи."""
    logging.info('Выводит Помощь')
    await message.answer(
        """
        Здесь будет описание проекта и описание доступных команд:
        введите /santa для начала процесса регистрации,
        введите /count для вывода количества участников,
        введите /check для вывода ваших данных,
        введите /clear для очистки данных и повторной регистрации.
        введите /info  для вывода информации о ваших личных данных
        """
    )


@dp.message_handler(commands=['clear'])
async def clear(message: types.Message):
    """Очистка данных для повторной регистрации."""
    conn = sqlite3.connect('santas.db')

    cur = conn.cursor()
    cur.execute(
        """DELETE FROM users 
        WHERE tg_id=?""",
        (message.from_user.id,))
    conn.commit()
    logging.info(f'Произошла очистка данных для {message.from_user.id} :id')
    await message.answer(
        "Очистка данных произведена. "
        "Введите /santa для повторной регистрации."
    )


@dp.message_handler(commands=['count'])
async def count(message: types.Message):
    """Считаем количество записей в БД"""
    conn = sqlite3.connect('santas.db')

    cur = conn.cursor()
    counter = cur.execute("""select count(tg_id) from users""")
    conn.commit()
    counter = counter.fetchone()[0]
    logging.info('Вывод количества человек')
    await message.answer("Сейчас участвует {} человек".format(counter))


async def end_registration(state, message, comment):
    data = await state.get_data()
    full_name = data.get('full_name')
    telephone = data.get('telephone')
    address = data.get('address')
    add_to_db(message.from_user.id, full_name, telephone, address, comment)
    await state.reset_state(with_data=False)
    await get_data(message, full_name, telephone, address, comment)
    logging.info('окончание Регистрации пользователя')


@dp.message_handler(commands=['santa'])
async def santa(message: types.Message):
    """Начинаем процесс регистрации."""
    if check_santa_in_base(message) is True:
        logging.info('Пользователь есть в БД "выводится его информация"')
        await get_data_from_db(message)
    else:
        logging.info('Бот спрашивает Фамилия Имя Отчество')
        await message.answer(
            "Полное имя получателя (в формате «Фамилия Имя Отчество») или название организации (краткое или полное):"
        )
        await SantaData.full_name.set()


@dp.message_handler(state=SantaData.full_name)
async def answer_full_name(message: types.Message, state: FSMContext):
    """Первое состояние. Сохранение ФИО в хранилище памяти."""
    full_name = message.text
    if not validate_full_name(full_name):
        await message.answer(f'Ваш ввод "{full_name}" не прошёл Валидацию  \n'
                             f'Полное имя получателя (в формате «Фамилия Имя Отчество»)'
                             f'или название организации (краткое - полное):')
        logging.info(f'Это Фио "{full_name}" не прошло Валидацию')
        await SantaData.full_name.set()
        return
    await state.update_data(full_name=full_name)
    await message.answer("Введите ваш Номер телефона, Он будет указан при отправке посылки:")
    await SantaData.next()
    logging.info('Успешно введено Фио')


@dp.message_handler(state=SantaData.telephone)
async def answer_telephone(message: types.Message, state: FSMContext):
    """Второе состояние. Сохранение номера телефона в хранилище памяти."""
    telephone = message.text
    if not validate_telephone(telephone):
        await message.answer(f"Ваш ввод \"{telephone}\" не прошёл Валидацию\n"
                             f"Введите ваш Номер телефона, Он будет указан при отправке посылки:")
        logging.info(f'что то не так Номером телефона "{telephone}"')
        await SantaData.telephone.set()
        return
    await state.update_data(telephone=telephone)
    await message.answer("""
                         Введите ваш адрес:
                         В адресе указывают:
                         Название страны;
                         Название населенного пункта;
                         Название района, области, края или республики;
                         Название улицы, номер дома, номер квартиры;
                         Почтовый индекс по образцу:
                         Образец :
                         россия п Октябрьский район Борский
                         Ул Победы д 20 кв 29 606408
                         """
                         )
    await SantaData.next()
    logging.info('Успешно введен Номер')


@dp.message_handler(state=SantaData.address)
async def answer_address(message: types.Message, state: FSMContext):
    """Третье состояние. Сохранение адреса в хранилище памяти."""
    address = message.text
    await state.update_data(address=address)
    await message.answer(
        """
        Ну а теперь напиши Свои пожелания К подарку:
        или какие то дополнения к предыдущим полям
        """
    )
    logging.info('Успешно введен Адрес')
    await SantaData.next()


@dp.message_handler(state=SantaData.comment)
async def answer_comment(message: types.Message, state: FSMContext):
    """Четвертое состояние. Сохранение коммента в хранилище памяти.
    Подготовка данных для вывода."""
    comment = message.text
    await state.update_data(comment=comment)
    await message.answer('Данные сохранены.')
    logging.info('Успешно введен комментарий')
    await end_registration(state, message, comment)


@dp.message_handler()
async def answer(message: types.Message):
    """Ответ на все остальные текстовые сообщения."""
    await message.answer(
        'Я вас не понимаю, введите /help для вывода доступных команд'
    )
    logging.info('Неизвестное Сообщение')


async def get_data(
        message: types.Message,
        full_name,
        telephone,
        address,
        comment
):
    """Функция вывода введенных данных"""
    await message.answer(
        f'Ваши данные:\n'
        f'ФИО: {full_name},\n'
        f'Телефон: {telephone},\n'
        f'Адрес: {address},\n'
        f'Комментарий: {comment}'
    )
    await message.answer(
        "Если какие-то данные не верны, вы можете ввести команду "
        "/clear для очистки данных и повторной регистрации"
    )
    logging.info('Успешно введены данные пользователю')


def main():
    executor.start_polling(dp)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='main.log',
        filemode='w',
        format='%(asctime)s - %(name)s - %(message)s - %(levelname)s',
    )
    main()
