from skill_requests.Request import Request
from skill_dialog.handler import DialogHandler
import time


def main(event, context):
    """ Точка входа в приложение """
    start = time.time()
    # Обработка запроса
    req = Request(event)
    user_id = req.get_user_id()
    command = req.get_command()
    session_state, session_is_new = req.get_session_info()
    timezone = req.get_timezone()

    # Подготовка ответа
    dialog = DialogHandler(
        user_id, command, session_state,
        session_is_new, timezone
    )
    dialog.process()
    print('Time: ', time.time() - start)
    return dialog.respond()
