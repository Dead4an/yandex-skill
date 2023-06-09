import datetime
import random
import time
from datetime import datetime as dt
from uuid import uuid4
import pytz
from database.manage import DatabaseManager
from skill_requests.Response import Response
from .skill_buttons import (MAIN_MENU_BUTTONS, HELP_BUTTONS, HELP_BUTTONS_END,
                            ACTIVITY_TYPES, END_ACTIVITY, STATISTIC_BUTTONS, ENTRIES_BUTTONS_START,
                            ENTRIES_BUTTONS, ENTRIES_BUTTONS_END, STATISTIC_ACTIVITIES_CARD,
                            WHAT_YOU_CAN_CARD, POSSIBILITIES_BUTTONS, MAIN_MENU_CARD, HELLO_NEW_BUTTONS,
                            ACTIVITIES_CARD, DAILY_STATISTIC_CARD, STATISTIC_CARD, STATISTIC_BUTTONS_DAILY,
                            STATISTIC_BUTTONS_WEEKLY, STATISTIC_BUTTONS_ENTRIES, WEEKLY_STATISTIC_CARD,
                            WEEKLY_VIEW_BUTTONS, POSSIBILITIES_BUTTONS_STATISTIC, HELP_CARD)
from .skill_texts import TEXTS


class DialogHandler:
    """ Управляет диалогом """

    def __init__(self, user_id, command, session_state,
                 session_is_new, timezone):
        self.__user_id = user_id
        self.command = command
        self.session_state = session_state
        self.session_is_new = session_is_new
        self.user_exists = None
        self.timezone = timezone
        self.last_checkin = None
        self.activities_list = None
        self.activity_name = None
        self.result = None
        self.check_user_is_new()

    def process(self):
        """ Обработка команды """
        if self.session_is_new:
            if self.command is None:
                self.new_session()

            elif self.command == 'start':
                self.main_menu(new_session=True)

            elif self.command == 'activities':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            elif self.command == 'what_you_can':
                self.about_possibilities()

            elif self.command == 'help':
                self.help()

            elif self.command == 'back_to_menu':
                self.main_menu(new_session=True)

        elif self.command is None:
            self.command_not_found()
            return

        elif self.command == 'quit':
            self.result = Response('Удачи!', end_session=True, tts='Удачи!')

        elif self.command == 'help':
            self.help()

        elif self.command == 'what_you_can':
            self.about_possibilities()

        elif self.command == 'back_to_menu':
            self.main_menu()

        elif self.session_state == 0:
            if self.command in ['no', 'quit']:
                self.end_session()

            elif self.command == 'help':
                self.help()

            elif self.command == 'activities':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            else:
                self.about_possibilities()

        # Главное меню
        elif self.session_state == 1:
            if self.command == 'quit':
                self.end_session()

            elif self.command == 'help':
                self.help()

            elif self.command == 'activities':
                self.get_last_checkin()
                if self.last_checkin and self.last_checkin['checkin_type'] == 'start':
                    self.close_activity(confirm_state_std=True)
                    return

                self.activities()

            elif self.command == 'close_activity':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            elif self.command == 'what_you_can':
                self.about_possibilities()

        # Раздел активностей
        elif self.session_state == 2:
            self.set_activity_name(self.command)
            if self.command in ['back']:
                self.main_menu()
                return

            if self.command == 'statistic':
                self.statistic()
                return

            checkin_id = str(uuid4())

            self.add_checkin(checkin_id, 'start', self.command)
            text = (
                f'Принято! Отслеживаю активность "{self.activity_name}". '
                'Когда Вы закончите, просто сообщите об этом. '
            )

            tts = f"{text}{TEXTS['main_menu']}"
            buttons = MAIN_MENU_BUTTONS
            card = MAIN_MENU_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=1, tts=tts)

        # Завершение активности (подтверждение)
        elif self.session_state == 21:
            if self.command == 'close_activity':
                self.close_activity()

            elif self.command == 'continue_activity':
                self.main_menu()

        elif self.session_state == 22:
            if self.command == 'close_activity':
                self.get_last_checkin()
                db = DatabaseManager()
                db.delete_last_checkin(self.__user_id, self.last_checkin['id'])
                text = 'Активность не была сохранена из-за короткой продолжительности. ' \
                       'Хотите начать новую активность или посмотреть статистику?'
                card = MAIN_MENU_CARD
                card['header'].update({'text': text})
                buttons = MAIN_MENU_BUTTONS
                self.result = Response('', buttons, card, session_state=1, tts=text)

            elif self.command == 'continue_activity':
                self.main_menu()

        # Просмотр статистики
        elif self.session_state == 3:
            if self.command == 'get_entries':
                self.daily_statistic()

            elif self.command == 'get_daily_statistic':
                self.get_daily_activities_card()

            elif self.command == 'get_weekly_statistic':
                self.get_daily_activities_card(weekly=True)

            elif self.command in ['back']:
                self.main_menu()

            elif self.command == 'activities':
                self.activities()

        # Просмотр подробной статистики за день
        elif 31 <= self.session_state <= 50:
            if self.session_state == 50:
                text = 'Вы посмотрели максимально доступное количество записей за сегодня'
                tts = f'{text}. Хотите начать отслеживать новую активность или узнать статистику? ' \
                      f'Если вам нужна помощь - скажите "Помощь".'
                card = MAIN_MENU_CARD
                card['header'].update({'text': text})
                buttons = MAIN_MENU_BUTTONS
                self.result = Response('', buttons, card, session_state=1, tts=tts)

            if self.command == 'entries_continue':
                text = ''
                start = 5 * (self.session_state - 30)
                activities_card, last_page = self.get_activities_card(start)
                if last_page:
                    self.result = Response(TEXTS['main_menu'], ENTRIES_BUTTONS_END, activities_card,
                                           session_state=self.session_state + 1)
                    return
                else:
                    self.result = Response(text, ENTRIES_BUTTONS, activities_card,
                                           session_state=self.session_state + 1)

            elif self.command == 'entries_previous' and self.session_state == 32:
                text = ''
                activities_card, _ = self.get_activities_card(0)
                self.result = Response(text, ENTRIES_BUTTONS_START, activities_card,
                                       session_state=31)

            elif self.command == 'entries_previous':
                text = ''
                start = 5 * (self.session_state - 32)
                activities_card, _ = self.get_activities_card(start)
                self.result = Response(text, ENTRIES_BUTTONS, activities_card,
                                       session_state=self.session_state - 1)

            elif self.command in ['no']:
                self.main_menu()

            elif self.command == 'get_daily_statistic':
                self.get_daily_activities_card()

            elif self.command == 'get_weekly_statistic':
                self.get_activities(weekly=True)
                self.main_menu()

        # Что ты умеешь
        elif self.session_state == 4:
            if self.command in ['yes', 'entries_continue']:
                self.about_possibilities(pos_state=1)

            elif self.command in ['no']:
                self.main_menu()

            elif self.command == 'activities':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            elif self.command == 'help':
                self.help()

        elif self.session_state == 10:
            if self.command in ['yes', 'entries_continue', 'repeat']:
                self.about_possibilities()

            elif self.command in ['no']:
                self.main_menu()

            elif self.command == 'activities':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            elif self.command == 'help':
                self.help()

        # Помощь
        elif self.session_state in range(51, 55):
            if self.command in ['back', 'no']:
                self.main_menu()

            elif self.command == 'activities':
                self.activities()

            elif self.command == 'statistic':
                self.statistic()

            elif self.session_state == 51:
                if self.command in ['yes', 'entries_continue']:
                    self.help(help_state=1)

            elif self.session_state == 52:
                if self.command in ['yes', 'entries_continue']:
                    self.help(help_state=2)

            elif self.session_state == 53:
                if self.command in ['yes', 'entries_continue']:
                    self.help(help_state=3)

            elif self.session_state == 54:
                if self.command in ['yes', 'entries_continue', 'repeat']:
                    self.help()

        # Статистика за день
        elif self.session_state == 7:
            today_date = dt.strftime(dt.date(self.get_time(return_timestamp=True)), '%Y-%m-%d')
            today_date = dt.strptime(f'{today_date} 00:00:00', '%Y-%m-%d %H:%M:%S')
            delta_day = datetime.timedelta(hours=24)
            activities_cards = []

            if self.command == 'one_ago':
                self.get_activities(weekly=True)
                date = dt.strftime(today_date - delta_day, '%Y-%m-%d')
                activities_cards = self.count_activities_duration(date)

            elif self.command == 'two_ago':
                self.get_activities(weekly=True)
                date = dt.strftime(today_date - delta_day * 2, '%Y-%m-%d')
                activities_cards = self.count_activities_duration(date)

            elif self.command == 'three_ago':
                self.get_activities(weekly=True)
                date = dt.strftime(today_date - delta_day * 3, '%Y-%m-%d')
                activities_cards = self.count_activities_duration(date)

            elif self.command == 'four_ago':
                self.get_activities(weekly=True)
                date = dt.strftime(today_date - delta_day * 4, '%Y-%m-%d')
                activities_cards = self.count_activities_duration(date)

            elif self.command == 'five_ago':
                self.get_activities(weekly=True)
                date = dt.strftime(today_date - delta_day * 5, '%Y-%m-%d')
                activities_cards = self.count_activities_duration(date)

            elif self.command == 'get_entries':
                self.daily_statistic()
                return

            elif self.command == 'get_daily_statistic':
                self.get_daily_activities_card()
                return

            elif self.command == 'statistic':
                self.statistic()
                return

            card = DAILY_STATISTIC_CARD
            card.update({'items': activities_cards})
            card['header'].update({'text': 'Вот ваша статистика за этот день'})
            self.result = Response('', STATISTIC_BUTTONS_WEEKLY, card, session_state=8,
                                   tts=('Вот ваша статистика за этот день. Скажите "назад", '
                                        'чтобы посмотреть статистику за другие дни. Или вернёмся '
                                        'в главное меню?')
                                   )

        elif self.session_state == 8:
            if self.command == 'back':
                self.get_daily_activities_card(weekly=True)

    def end_session(self):
        text = 'Удачи!'
        self.result = Response(text, end_session=True, tts=text)

    def command_not_found(self):
        """ Команда не найдена """
        if self.session_state == 2:
            text = 'Извините, но я не знаю такого вида активности'
            tts = f'{text}. {TEXTS["activities"]}'
            buttons = ACTIVITY_TYPES
            card = ACTIVITIES_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=2, tts=tts)

        elif self.session_state == 3:
            text = 'Извините, я вас не поняла. Активность за какой период Вы хотите ' \
                   'посмотреть?'
            tts = text
            buttons = STATISTIC_BUTTONS
            card = STATISTIC_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=3, tts=tts)

        elif self.session_state == 4:
            text = 'Извините, я вас не поняла. Чтобы вернуться в главное меню, скажите: "Главное меню"'
            tts = TEXTS['what_you_can_activities']
            buttons = POSSIBILITIES_BUTTONS
            card = WHAT_YOU_CAN_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=4, tts=tts)

        elif self.session_state == 10:
            text = 'Извините, я вас не поняла. Чтобы вернуться в главное меню, скажите: "Главное меню"'
            tts = TEXTS['what_you_can_statistic']
            buttons = POSSIBILITIES_BUTTONS_STATISTIC
            card = WHAT_YOU_CAN_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=10, tts=tts)

        elif self.session_state in range(51, 55):
            if self.session_state == 51:
                self.help()

            elif self.session_state == 52:
                self.help(1)

            elif self.session_state == 53:
                self.help(2)

            else:
                self.help(3)

        elif self.session_state == 7:
            self.get_daily_activities_card(weekly=True, error=1)

        elif self.session_state == 8:
            text = (
                'Извините, я не поняла вас. Если хотите посмотреть активность за другие дни, '
                'скажите: "Назад". Чтобы вернуться в меню, скажите: "Главное меню"'
            )
            buttons = STATISTIC_BUTTONS_WEEKLY
            self.result = Response(text, buttons, session_state=8, tts=text)

        else:
            text = TEXTS['command_not_found']
            buttons = MAIN_MENU_BUTTONS
            card = MAIN_MENU_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=1, tts=text)

    def check_user_is_new(self):
        """ Проверка нового пользователя """
        db = DatabaseManager()
        self.user_exists = db.check_user_exists(self.__user_id)
        if not self.user_exists:
            db.insert_user(self.__user_id)

    def respond(self):
        return self.result.respond()

    # Функции диалога
    def new_session(self):
        """ Новая сессия в навыке """
        if self.user_exists:
            self.main_menu(new_session=True)

        else:
            text = TEXTS['hello_new']
            buttons = HELLO_NEW_BUTTONS
            self.result = Response(text, buttons, session_state=0)

    # Меню
    def main_menu(self, new_session=False):
        """ Главаное меню навыка """
        text = random.choice(TEXTS['hello_std'])
        tts = 'Если хотите начать или закончить активность - скажите "Активность". ' \
              'sil <[250]> Хотите узнать свою статистику? Скажите "Статистика" и я покажу её вам. ' \
              'sil <[250]> Скажите "Помощь", если хотите узнать о навыке больше'

        if new_session:
            timestamp = self.get_time(return_timestamp=True)
            timestamp = time.mktime(timestamp.timetuple())
            timestamp = self.get_time(timestamp=timestamp)

            if '00:00:00' <= timestamp <= '05:59:59':
                time_name = 'Доброй ночи! '
            elif '06:00:00' <= timestamp <= '11:59:59':
                time_name = 'Доброе утро! '
            elif '12:00:00' <= timestamp <= '17:59:59':
                time_name = 'Добрый день! '
            else:
                time_name = 'Добрый вечер! '

            text = time_name + text
            tts = time_name + tts

        buttons = MAIN_MENU_BUTTONS
        card = MAIN_MENU_CARD
        card['header'].update({'text': text})
        self.result = Response('', buttons, card,
                               session_state=1, tts=tts)

    # Что ты умеешь
    def about_possibilities(self, pos_state=0):
        """ Краткая информация о навыке """

        if pos_state == 0:
            text = 'Вот, что я могу'
            tts = TEXTS['what_you_can_activities']
            buttons = POSSIBILITIES_BUTTONS
            card = WHAT_YOU_CAN_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card,
                                   session_state=4, tts=tts)

        elif pos_state == 1:
            text = 'Вот, что я могу'
            tts = TEXTS['what_you_can_statistic']
            buttons = POSSIBILITIES_BUTTONS_STATISTIC
            card = WHAT_YOU_CAN_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card,
                                   session_state=10, tts=tts)

    # Активности
    def activities(self):
        """ Раздел активностей """
        self.get_last_checkin()
        if self.last_checkin and self.last_checkin['checkin_type'] == 'start':
            self.close_activity(confirm_state_std=True, already_observe=True)
            return

        text = random.choice(TEXTS['activities_rand'])
        tts = text + TEXTS['activities']
        buttons = ACTIVITY_TYPES
        card = ACTIVITIES_CARD
        card['header'].update({'text': text})
        self.result = Response('', buttons, card, session_state=2, tts=tts)
        return

    def statistic(self):
        latest_date = self.get_time(return_timestamp=True)
        day_delta = datetime.timedelta(hours=24)
        latest_date = dt.strftime(latest_date - day_delta * 5, '%Y-%m-%d 00:00:00')
        db = DatabaseManager()
        if not db.check_activity(self.__user_id, latest_date):
            text = 'Похоже, Вы не закончили ни одной активности за последнюю неделю'
            tts = f'{text}. Хотите начать отслеживать новую активность или получить помощь?'
            buttons = MAIN_MENU_BUTTONS
            card = MAIN_MENU_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=1, tts=tts)
            return

        tts = (
            'Вы можете посмотреть подробную статистику "за сегодня", '
            '"общую статистику за сегодня", а также статистику за неделю. '
            'Что именно Вы хотите сделать?'
        )
        card = STATISTIC_CARD
        buttons = STATISTIC_BUTTONS
        self.result = Response('', buttons, card, session_state=3, tts=tts)

    def daily_statistic(self):
        db = DatabaseManager()
        today_date = self.get_time(return_timestamp=True)
        today_date = dt.strftime(today_date, '%Y-%m-%d 00:00:00')
        if not db.check_activity(self.__user_id, today_date):
            text = 'Похоже, сегодня Вы не закончили ни одной активности'
            tts = f'{text}. Хотите начать отслеживать новую активность, узнать статистику, или получить помощь?'
            buttons = MAIN_MENU_BUTTONS
            card = MAIN_MENU_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=1, tts=tts)
            return

        text = ''
        activities_card, last_page = self.get_activities_card(0)
        buttons = STATISTIC_BUTTONS_ENTRIES
        tts = 'Вот ваша статистика за сегодня.'
        if last_page:
            self.result = Response('', buttons, activities_card, session_state=3, tts=tts)
            return

        self.result = Response(text, ENTRIES_BUTTONS_START, activities_card, session_state=31)

    def get_activities_card(self, start):
        """ Возвращает карточку со списком последних активностей """
        self.get_activities()
        activity_items = []
        entries_count = len(self.activities_list)
        last_page = False
        if entries_count <= start + 5:
            last_page = True

        for row in self.activities_list[start:start + 5]:
            activity_type = row[-2]
            self.set_activity_name(activity_type)
            start_time = dt.strptime(row[3], '%Y-%m-%d %H:%M:%S')
            start_time = dt.strftime(start_time, '%H:%M:%S')
            duration = self.get_time(timestamp=row[-3])

            if activity_type == 'activity_work':
                image_id = '213044/39799b3319bd0fb5135b'
                title = 'Работа'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'
            elif activity_type == 'activity_homework':
                image_id = '213044/1ad7f49599385016222d'
                title = 'Домашние Дела'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'
            elif activity_type == 'activity_hobby':
                image_id = '213044/b85af62b5e29b538daca'
                title = 'Хобби'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'
            elif activity_type == 'activity_sport':
                image_id = '213044/d458652c075b18128692'
                title = 'Спорт'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'
            elif activity_type == 'activity_other':
                image_id = '1030494/edca956f6dd3f17aa057'
                title = 'Прочее'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'
            else:
                image_id = '213044/40740b20816d29f6406b'
                title = 'Неизвестно'
                desctiption = f'Начало: {start_time} | Продолжительность {duration}'

            activity_item = {
                'image_id': image_id,
                'title': title,
                'description': desctiption
            }

            activity_items.append(activity_item)

        activities_card = STATISTIC_ACTIVITIES_CARD
        activities_card.update({'items': activity_items})
        return activities_card, last_page

    def get_daily_activities_card(self, weekly=None, error=None):
        """ Возвращает карточку с общей статистикой за день"""
        if weekly:
            import numpy as np
            self.get_activities(weekly=True)
            df = np.array(self.activities_list, dtype={
                'names': ('uuid', 'user_id', 'activity_id', 'start_time', 'end_time',
                          'duration', 'activity_type', 'text'),
                'formats': ['U64', 'U128', 'i4', 'U64', 'U64', 'i4', 'U64', 'U64']
            })

            def slice_date(date_to_slice: str):
                return date_to_slice[:10]

            vectorized_slice = np.vectorize(slice_date)
            df['start_time'] = vectorized_slice(df['start_time'])

            dates = np.unique(df['start_time'])[:-1]
            days = []
            day_counter = 1

            for date in dates[::-1]:
                year = date[:4]
                month = date[5:7]
                day = date[8:]

                if day_counter == 1:
                    day_name = 'Вчера'
                    image_id = '1030494/13ccbfe97e126e8743e8'
                elif day_counter == 2:
                    day_name = 'Позавчера'
                    image_id = '1652229/89f1a6409cb0bf67414f'
                elif day_counter == 3:
                    day_name = 'Три дня назад'
                    image_id = '1652229/2b1bcd8e99f5663264f3'
                elif day_counter == 4:
                    day_name = 'Четыре дня назад'
                    image_id = '1533899/60ae1bf8cc727f2d59ce'
                else:
                    day_name = 'Пять дней назад'
                    image_id = '1652229/1be311bfe2beccafe547'

                days.append({
                    'image_id': image_id,
                    'title': day_name,
                    'description': f'{day}-{month}-{year}',
                    'button': {
                        'title': day_name
                    }
                })

                day_counter += 1

            if len(days) == 0:
                card = STATISTIC_CARD
                card['header'].update({'text': 'Похоже, у Вас нет статистики за предыдущие дни'})
                buttons = STATISTIC_BUTTONS
                self.result = Response('', buttons, card, session_state=3,
                                       tts='Похоже, у вас нет статистики за предыдущие дни. '
                                           'Хотите узнать подробную или общую статистику за сегодня? '
                                           'Или же вернёмся в главное меню?')
                return

            card = WEEKLY_STATISTIC_CARD
            card.update({'items': days})
            tts = 'Статистику за какой день Вы хотели бы увидеть?'
            if error:
                text = (
                    'Извините, я не поняла вас. Что именно Вы хотите сделать?'
                )
                card['header'].update({'text': text})
                tts = (
                    'Извините, я не поняла вас. Если Вы хотите вернуться в главное меню, '
                    'скажите "Главное меню". Если Вы хотите вернуться в раздел статистики, '
                    'скажите "Статистика"'
                )

            self.result = Response('', WEEKLY_VIEW_BUTTONS, card, session_state=7,
                                   tts=tts)
            return

        self.get_activities()
        if not self.activities_list:
            text = 'Похоже, Вы ещё не закончили ни одной активности за сегодня'
            tts = f'{text}. Хотите начать отслеживать новую активность или вам нужна помощь?'
            buttons = MAIN_MENU_BUTTONS
            card = MAIN_MENU_CARD
            card['header'].update({'text': text})
            self.result = Response('', buttons, card, session_state=1, tts=tts)
            return

        activities_cards = self.count_activities_duration()
        buttons = STATISTIC_BUTTONS_DAILY
        daily_card = DAILY_STATISTIC_CARD
        daily_card.update({'items': activities_cards})
        self.result = Response('', buttons, daily_card, session_state=3,
                               tts='Вот ваша статистика за день. Хотите узнать подробную статистику '
                                   'или вернуться в главное меню?')

    def count_activities_duration(self, date=None):
        import numpy as np
        if date:
            df = np.array(self.activities_list, dtype={
                'names': ('uuid', 'user_id', 'activity_id', 'start_time', 'end_time',
                          'duration', 'activity_type', 'text'),
                'formats': ['U128', 'U128', 'U128', 'U128', 'U128', 'U128', 'U128', 'U128']
            })

            def slice_date(date_to_slice: str):
                return date_to_slice[:10]

            vectorized_slice = np.vectorize(slice_date)
            df['start_time'] = vectorized_slice(df['start_time'])

            work_duration = np.sum(
                df[np.where((df['start_time'] == date) &
                            (df['activity_type'] == 'activity_work'))]['duration'].astype(int))

            homework_duration = np.sum(df[np.where(
                (df['start_time'] == date) &
                (df['activity_type'] == 'activity_homework'))]['duration'].astype(int))

            hobby_duration = np.sum(df[np.where(
                (df['start_time'] == date) &
                (df['activity_type'] == 'activity_hobby'))]['duration'].astype(int))

            sport_duration = np.sum(df[np.where(
                (df['start_time'] == date) &
                (df['activity_type'] == 'activity_sport'))]['duration'].astype(int))

            other_duration = np.sum(df[np.where(
                (df['start_time'] == date) &
                (df['activity_type'] == 'activity_other'))]['duration'].astype(int))

        else:
            df = np.array(self.activities_list, dtype={
                'names': ('uuid', 'user_id', 'activity_id', 'start_time', 'end_time',
                          'duration', 'activity_type', 'text'),
                'formats': ['U128', 'U128', 'U128', 'U128', 'U128', 'U128', 'U128', 'U128']
            })

            work_duration = np.sum(df[np.where(df['activity_type'] == 'activity_work')]
                                   ['duration'].astype(int))

            homework_duration = np.sum(df[np.where(df['activity_type'] == 'activity_homework')]
                                       ['duration'].astype(int))

            hobby_duration = np.sum(df[np.where(df['activity_type'] == 'activity_hobby')]
                                    ['duration'].astype(int))

            sport_duration = np.sum(df[np.where(df['activity_type'] == 'activity_sport')]
                                    ['duration'].astype(int))

            other_duration = np.sum(df[np.where(df['activity_type'] == 'activity_other')]
                                    ['duration'].astype(int))

        if work_duration:
            work_duration = self.get_time(timestamp=work_duration)
        if homework_duration:
            homework_duration = self.get_time(timestamp=homework_duration)
        if hobby_duration:
            hobby_duration = self.get_time(timestamp=hobby_duration)
        if sport_duration:
            sport_duration = self.get_time(timestamp=sport_duration)
        if other_duration:
            other_duration = self.get_time(timestamp=other_duration)

        activities_cards = []
        if work_duration:
            activities_cards.append({
                'image_id': '213044/39799b3319bd0fb5135b',
                'title': 'Работа',
                'description': f'Общее время занятия работой: {work_duration}'
            })
        if homework_duration:
            activities_cards.append({
                'image_id': '213044/1ad7f49599385016222d',
                'title': 'Домашние Дела',
                'description': f'Общее время занятия домашними делами: {homework_duration}'
            })
        if hobby_duration:
            activities_cards.append({
                'image_id': '213044/b85af62b5e29b538daca',
                'title': 'Хобби',
                'description': f'Общее время занятия хобби: {hobby_duration}'
            })
        if sport_duration:
            activities_cards.append({
                'image_id': '213044/d458652c075b18128692',
                'title': 'Спорт',
                'description': f'Общее время занятия спортом: {sport_duration}'
            })
        if other_duration:
            activities_cards.append({
                'image_id': '1030494/edca956f6dd3f17aa057',
                'title': 'Прочее',
                'description': f'Общее время занятия разными делами: {other_duration}'
            })

        return activities_cards

    def add_checkin(self, checkin_id, checkin_type, activity_type):
        """ Добавление отметки о начале | конце активности """
        db = DatabaseManager()
        current_time = self.get_time()
        db.insert_checkin(checkin_id, self.__user_id, current_time, checkin_type, activity_type)

    def get_last_checkin(self):
        """ Возвращает все отметки """
        db = DatabaseManager()
        self.last_checkin = db.select_last_checkin(self.__user_id)

    def add_activity(self, general_id, activity_id, start_time, end_time,
                     duration, activity_type, text):
        """ Добавление записи об активности """
        db = DatabaseManager()
        db.insert_activity(general_id, self.__user_id, activity_id, start_time, end_time,
                           duration, activity_type, text)

    def get_activities(self, weekly=None):
        """ Возвращает все записи об активностях """
        db = DatabaseManager()

        if weekly:
            today = self.get_time(return_timestamp=True)
            day_time_delta = datetime.timedelta(hours=24)
            latest_date = today - day_time_delta * 5
            latest_date = dt.strftime(latest_date, '%Y-%m-%d 00:00:00')
            self.activities_list = db.select_activities(self.__user_id, latest_date)
            return

        today_date = dt.strftime(dt.date(self.get_time(return_timestamp=True)), '%Y-%m-%d')
        self.activities_list = db.select_activities(self.__user_id, today_date)

    def close_activity(self, confirm_state_std=False, already_observe=None):
        self.get_last_checkin()
        self.set_activity_name(self.last_checkin['activity_type'])
        db = DatabaseManager()
        last_activity_id = db.select_last_activity_id(self.__user_id)

        # UUID
        checkin_id = str(uuid4())
        general_activity_id = str(uuid4())

        # Временные преобразования
        activity_start_time = self.last_checkin['start_time']
        activity_start_time = self.get_time(activity_start_time)
        current_time = self.get_time(return_timestamp=True)
        activity_duration = current_time - activity_start_time
        activity_duration = int(activity_duration.total_seconds())
        start_time_write = dt.strftime(activity_start_time, '%Y-%m-%d %H:%M:%S')
        start_time_show = dt.strftime(activity_start_time, '%H:%M:%S')
        current_time = dt.strftime(current_time, '%Y-%m-%d %H:%M:%S')
        activity_duration_timestamp = self.get_time(timestamp=activity_duration)

        if activity_duration < 60:
            activity_duration_timestamp = 'меньше минуты'

        if confirm_state_std and already_observe:
            text = f'Похоже у вас уже есть начатая активность\n' \
                   f'Активность: {self.activity_name} \nНачало: {start_time_show}\n' \
                   f'Продолжительность: {activity_duration_timestamp}\nХотите завершить активность?"'
            buttons = END_ACTIVITY
            self.result = Response(text, buttons, session_state=21)
            return

        if confirm_state_std:
            text = f'Активность: {self.activity_name} \nНачало: {start_time_show}\n' \
                   f'Продолжительность: {activity_duration_timestamp}\nХотите завершить активность?"'
            buttons = END_ACTIVITY
            self.result = Response(text, buttons, session_state=21)
            return

        if activity_duration < 60:
            text = 'Извините, но продолжительность активности меньше минуты. ' \
                   'Если Вы завершите активность сейчас, то она не сохранится. ' \
                   'Хотите завершить активность?'
            buttons = END_ACTIVITY
            self.result = Response(text, buttons, session_state=22)
            return

        if activity_duration > 43200:
            activity_duration = 43200

        self.add_activity(general_activity_id, last_activity_id + 1, start_time_write,
                          current_time, activity_duration, self.last_checkin['activity_type'], 'text')
        self.add_checkin(checkin_id, 'stop', self.last_checkin['activity_type'])
        text = f'Активность "{self.activity_name}" была завершена!'
        buttons = MAIN_MENU_BUTTONS
        card = MAIN_MENU_CARD
        card['header'].update({'text': text})
        tts = f'Активность "{self.activity_name}" была завершена! Если хотите начать ' \
              f'новую активность - скажите "активность". Если хотите посмотреть на статистику, то ' \
              f'скажите "статистика"'
        self.result = Response('', buttons, card, session_state=1, tts=tts)
        return

    # Помощь
    def help(self, help_state=0):
        """ Помощь пользователю """
        text = 'Вот инструкция'
        buttons = HELP_BUTTONS
        card = HELP_CARD
        card['header'].update({'text': text})
        if help_state == 0:
            tts = (
                'Чтобы начать отслеживать активность, скажите: "Начать активность". '
                'В разделе активностей Вам будет предложено выбрать вид активности, которую вы '
                'хотите начать отслеживать. Навык запомнит время начала активности, а также её вид.'
                'Продолжить?'
            )
            self.result = Response('', buttons, card, session_state=51, tts=tts)

        elif help_state == 1:
            tts = (
                'Чтобы закончить активность, скажите: "Закончить активность". '
                'Вы увидите информацию об активности с просьбой подтвердить '
                'завершение активности. Чтобы завершить, скажите: "Завершить". '
                'Чтобы отменить завершение, скажите: "Отменить". Продолжить?'
            )
            self.result = Response('', buttons, card, session_state=52, tts=tts)

        elif help_state == 2:
            tts = (
                'Чтобы узнать свою статистику, скажите: "Статистика". Чтобы увидеть '
                'записи о всех активностях, в разделе статистики скажите "Подробная статистика". '
                'Для получения общей статистики за этот день, скажите: "Сегодня". Продолжить?'
            )
            self.result = Response('', buttons, card, session_state=53, tts=tts)

        else:
            buttons = HELP_BUTTONS_END
            tts = (
                'Чтобы узнать свою статистику за предыдущие дни, перейдите в раздел статистики, '
                'сказав: "Статистика". Далее скажите: "Статистика за неделю" и выберите день, '
                'статистику за который Вы хотите узнать. Хотите, чтобы я повторила?'
            )
            self.result = Response('', buttons, card, session_state=54, tts=tts)

    def get_time(self, str_time=None, return_timestamp=False, timestamp=None):
        """ Возвращает текущее время, либо преобразует str в timestamp """
        tz = pytz.timezone(self.timezone)
        if str_time:
            return dt.strptime(str_time, '%Y-%m-%d %H:%M:%S')

        if return_timestamp:
            current_time = dt.strftime(dt.now(tz), '%Y-%m-%d %H:%M:%S')
            return dt.strptime(current_time, '%Y-%m-%d %H:%M:%S')

        if timestamp:
            datetime_from_timestamp = dt.fromtimestamp(float(timestamp))
            return dt.strftime(datetime_from_timestamp, '%H:%M:%S')

        return dt.strftime(dt.now(tz), '%Y-%m-%d %H:%M:%S')

    def set_activity_name(self, activity_type):
        if activity_type == 'activity_work':
            self.activity_name = 'Работа'
        elif activity_type == 'activity_homework':
            self.activity_name = 'Домашние Дела'
        elif activity_type == 'activity_hobby':
            self.activity_name = 'Хобби'
        elif activity_type == 'activity_sport':
            self.activity_name = 'Спорт'
        elif activity_type == 'activity_other':
            self.activity_name = 'Прочее'
