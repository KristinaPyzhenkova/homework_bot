import time
import logging
from http import HTTPStatus

import requests
import telegram
from telegram import Bot

from exceptions import ImpermissibilityEndpoint, ApiAnswerError, VerdictIsNone
from config import (PRACTICUM_TOKEN, TELEGRAM_TOKEN,
                    TELEGRAM_CHAT_ID, RETRY_TIME, ENDPOINT,
                    HEADERS, HOMEWORK_STATUSES)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Сообщение отправлено.')
    except Exception:
        logger.critical('Сообщение не отправлено.')
    except telegram.TelegramError:
        raise telegram.TelegramError(f'Ошибка при отправке: {message}')


def get_api_answer(current_timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    params = {'from_date': current_timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error('Недоступность эндпоинта.')
            raise ImpermissibilityEndpoint('Недоступность эндпоинта.')
        return response.json()
    except Exception:
        logger.error('Ошибка при запросе.')
        raise ApiAnswerError('Ошибка при запросе.')


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict) or response == {}:
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise TypeError('Отсутствие ожидаемых ключей в ответе API.')

    if not isinstance(response.get('homeworks'), list):
        logger.error('Отсутствие ожидаемых ключей в ответе API.')
        raise TypeError('Отсутствие ожидаемых ключей в ответе API.')

    while response.get('homeworks') == []:
        continue

    homeworks = response.get('homeworks')
    if homeworks is None:
        raise KeyError('Отсутствует ключ.')

    return homeworks


def parse_status(homework: dict):
    """Извлекает из инф. о домашней работе статус."""
    homework_status = homework.get('status')
    homework_name = homework.get('homework_name')

    if homework_status is None or homework_name is None:
        raise KeyError('Отсутствует ключ.')

    verdict = HOMEWORK_STATUSES.get(homework_status)
    if verdict is None:
        raise VerdictIsNone('Статус неизвестен.')

    message = 'Изменился статус проверки работы'
    return f'{message} "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет доступность переменных окружения."""
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


def main():
    """Основная логика работы бота."""
    current_timestamp = int(time.time())
    bot = Bot(token=TELEGRAM_TOKEN)
    status = None
    if check_tokens() is True:
        while True:
            try:
                response = get_api_answer(current_timestamp)
                homework = check_response(response)
                if status != homework[0].get('status'):
                    send_message(bot, parse_status(homework[0]))
                    status = homework[0].get('status')
                    current_timestamp = response.get('current_date')
                else:
                    logger.debug('Отсутствие в ответе новых статусов.')
                time.sleep(RETRY_TIME)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                send_message(bot, message)
                logger.error('Cбой при отправке сообщения в Telegram.')
                time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='program.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    main()
