from http import HTTPStatus
import logging

import os
import time
from xmlrpc.client import ResponseError

import requests

from telegram import Bot

from dotenv import load_dotenv

load_dotenv()


logging.basicConfig(
    level=logging.INFO,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 0

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
payload = {'from_date': 1636992730}
status = None

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    bot.send_message(TELEGRAM_CHAT_ID, message)


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Недоступность эндпоинта.')
            raise ResponseError('Недоступность эндпоинта.')
        return response.json()
    except Exception:
        logger.error('Ошибка при запросе.')
        raise ResponseError('Ошибка при запросе.')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if isinstance(response, dict):
        homework = response.get('homeworks')[0]
        return homework
    else:
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise TypeError('Отсутствие ожидаемых ключей в ответе API.')


def parse_status(homework: dict):
    """Извлекает из инф. о домашней работе статус."""
    global status
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES.get(homework_status)
    message = 'Изменился статус проверки работы'
    if verdict != status:
        status = verdict
        return f'{message} "{homework_name}". {verdict}'
    else:
        logger.debug('Отсутствие в ответе новых статусов.')
        raise AssertionError('Отсутствие в ответе новых статусов.')


def check_tokens():
    """Проверяет доступность переменных окружения."""
    try:
        if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
            return True
    except Exception:
        logger.critical('Отсутствие обязательных переменных.')
        raise AssertionError('Отсутствие обязательных переменных.')


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    # current_timestamp = int(time.time())
    while check_tokens():
        try:
            current_timestamp = 1636992730
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error('Cбой при отправке сообщения в Telegram.')
            time.sleep(RETRY_TIME)
        else:
            message = parse_status(homework)
            send_message(bot, message)
            logger.info('Сообщение отправлено.')


if __name__ == '__main__':
    main()
