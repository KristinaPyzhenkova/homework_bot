class ImpermissibilityEndpoint(Exception):
    """Ошибка недоступность эндпоинта."""

    pass


class VerdictIsNone(Exception):
    """Ошибка статус неизвестен."""

    pass


class ApiAnswerError(Exception):
    """Ошибка при запросе."""

    pass