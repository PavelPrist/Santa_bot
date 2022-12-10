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
        return False
    else:
        return True


def add_to_db(chat_id, full_name, telephone, address, comment):
    """Добавляем нового пользователя в базу."""
    conn = sqlite3.connect('santas.db')
    cur = conn.cursor()
    cur.execute("""insert into users values (?, ?, ?, ?, ?)""", (
        chat_id, full_name, telephone, address, comment,
    ))
    conn.commit()


@dp.message_handler(commands=['start'])
async def process_start_command(message: types.Message):
    """Функция первого обращения к боту."""
    name = message.from_user.full_name
    await bot.send_message(
        message.from_user.id,
        text='Привет, {}. Предлагаю тебе побыть Тайным Сантой. '
             'Нажми кнопку "/santa" для начала процесса регистрации или '
             'введи /help для большей информации'.format(name),
    )


@dp.message_handler(commands=['santa'])
async def santa(message: types.Message):
    """Начинаем процесс регистрации."""
    if check_santa_in_base(message) is True:
        await get_data_from_db(message)
    else:
        await message.answer(
            "Полное имя получателя (в формате «Фамилия Имя Отчество») или название организации (краткое или полное):"
        )
        await SantaData.full_name.set()


@dp.message_handler(commands=['help'])
async def help_message(message: types.Message):
    """Вывод помощи."""
    await message.answer(
        """
        Здесь будет описание проекта и описание доступных команд:
        введите /santa для начала процесса регистрации,
        введите /count для вывода количества участников,
        введите /check для вывода ваших данных,
        введите /clear для очистки данных и повторной регистрации.
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
    await message.answer("Сейчас участвует {} человек".format(counter))


@dp.message_handler(commands=['check'])
async def get_data_from_db(message: types.Message):
    """Получаем данные из БД зарегестрированного пользователя."""
    chat_id = str(message.from_user.id)
    conn = sqlite3.connect('santas.db')
    conn.row_factory = sqlite3.Row
    cur = conn.execute("""SELECT * FROM users WHERE tg_id=?""", (chat_id,))
    row = cur.fetchone()
    await get_data(
        message,
        row['full_name'],
        row['telephone'],
        row['address'],
        row['comment']
    )


async def end_registration(state, message, comment):
    data = await state.get_data()
    full_name = data.get('full_name')
    telephone = data.get('telephone')
    address = data.get('address')
    add_to_db(message.from_user.id, full_name, telephone, address, comment)
    await state.reset_state(with_data=False)
    await get_data(message, full_name, telephone, address, comment)


@dp.message_handler(state=SantaData.full_name)
async def answer_full_name(message: types.Message, state: FSMContext):
    """Первое состояние. Сохранение ФИО в хранилище памяти."""
    full_name = message.text
    if not validate_full_name(full_name):
        await message.answer(f'что то не так с ФИО "{full_name}"')
        await state.set_state()

    await state.update_data(full_name=full_name)
    await message.answer("Введите ваш телефон в формате 'xxx-xxx-xx-xx' (без 8 или +7):")
    await SantaData.next()


@dp.message_handler(state=SantaData.telephone)
async def answer_telephone(message: types.Message, state: FSMContext):
    """Второе состояние. Сохранение номера телефона в хранилище памяти."""
    telephone = message.text
    if not validate_telephone(telephone):
        await message.answer(f'что то не так Номером телефона "{telephone}"')
        await state.set_state()
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
    await SantaData.next()


@dp.message_handler(state=SantaData.comment)
async def answer_comment(message: types.Message, state: FSMContext):
    """Четвертое состояние. Сохранение коммента в хранилище памяти.
    Подготовка данных для вывода."""
    comment = message.text
    await state.update_data(comment=comment)
    await message.answer('Данные сохранены.')
    await end_registration(state, message, comment)


@dp.message_handler()
async def answer(message: types.Message):
    """Ответ на все остальные текстовые сообщения."""
    await message.answer(
        'Я вас не понимаю, введите /help для вывода доступных команд'
    )


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


def main():
    executor.start_polling(dp)


if __name__ == '__main__':
    main()
