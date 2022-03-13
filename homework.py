import os
import time
import logging
import sys

import requests

from http import HTTPStatus
from xmlrpc.client import ResponseError

import telegram
from telegram import Bot

from dotenv import load_dotenv

load_dotenv()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600

ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    sent_message = bot.send_message(TELEGRAM_CHAT_ID, message)
    if not sent_message:
        raise telegram.TelegramError(f'Ошибка при отправке: {message}')
    else:
        logger.info('Сообщение отправлено.')


class Impermissibility_Endpoint(Exception):
    """Ошибка недоступность эндпоинта."""

    pass


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Недоступность эндпоинта.')
            raise Impermissibility_Endpoint('Недоступность эндпоинта.')
        return response.json()
    except Exception:
        logger.error('Ошибка при запросе.')
        raise ResponseError('Ошибка при запросе.')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if isinstance(response, list) or response == {}:
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise TypeError('Отсутствие ожидаемых ключей в ответе API.')
    if isinstance(response.get('homeworks'), dict):
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise TypeError('Отсутствие ожидаемых ключей в ответе API.')

    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Отсутствует ключ.')

    return homeworks


class Verdict_is_none(Exception):
    """Ошибка статус неизвестен."""

    pass


def parse_status(homework: dict):
    """Извлекает из инф. о домашней работе статус."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')

    if homework_status is None or homework_name is None:
        raise KeyError('Отсутствует ключ.')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise Verdict_is_none('Статус неизвестен.')

    message = 'Изменился статус проверки работы'
    return f'{message} "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    try:
        return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])
    except Exception:
        logger.critical('Отсутствие обязательных переменных.')
        sys.exit('Отсутствие обязательных переменных.')


def main():
    """Основная логика работы бота."""
    bot = Bot(token=TELEGRAM_TOKEN)
    status = None
    two_week = 86400 * 14
    current_timestamp = int(time.time()) - two_week
    while check_tokens():
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            if status != homework[0].get('status'):
                send_message(bot, parse_status(homework[0]))
                status = homework[0].get('status')
            else:
                logger.debug('Отсутствие в ответе новых статусов.')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error('Cбой при отправке сообщения в Telegram.')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
