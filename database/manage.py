import os
import ydb
import ydb.iam


INSERT_CHECKIN = """
DECLARE $id AS Utf8;
DECLARE $user_id AS Utf8;
DECLARE $start_time AS Utf8; 
DECLARE $type AS Utf8; 
DECLARE $checkin_type AS Utf8; 
UPSERT INTO checkins (id, user_id, start_time, type, checkin_type) 
VALUES ($id, $user_id, $start_time, $type, $checkin_type);"""

SELECT_CHECKINS = """
DECLARE $user_id AS Utf8;
DECLARE $today_date AS Utf8;
SELECT id, start_time, type, checkin_type FROM checkins 
WHERE user_id=$user_id and start_time > $today_date
ORDER BY start_time DESC;"""

DELETE_LAST_CHECKIN = """
DECLARE $user_id AS Utf8;
DECLARE $id AS Utf8;
DELETE FROM checkins
WHERE user_id=$user_id 
AND id=$id"""

INSERT_ACTIVITY = """
DECLARE $id AS Utf8; 
DECLARE $user_id AS Utf8;
DECLARE $activity_id AS Uint64; 
DECLARE $start_time AS Utf8; 
DECLARE $end_time AS Utf8; 
DECLARE $duration AS Uint64; 
DECLARE $activity_type AS Utf8; 
DECLARE $text AS Utf8; 
UPSERT INTO activities (id, user_id, activity_id, start_time, end_time, duration, activity_type, text) 
VALUES ($id, $user_id, $activity_id, $start_time, $end_time, $duration, $activity_type, $text);"""

SELECT_ACTIVITIES = """
DECLARE $user_id AS Utf8;
DECLARE $today_date AS Utf8;
SELECT id, user_id, activity_id, start_time, end_time, duration, activity_type, text  
FROM activities WHERE user_id=$user_id AND start_time > $today_date 
ORDER BY start_time DESC;"""

INSERT_USER = """
DECLARE $id AS Utf8;
DECLARE $name AS Utf8;
UPSERT INTO users (id, name) VALUES ($id, $name);"""

USER_EXISTS = """
DECLARE $id AS Utf8;
SELECT 1 FROM users WHERE id=$id LIMIT 1;"""

CHECK_ACTIVITIES = """
DECLARE $user_id AS Utf8;
SELECT 1 FROM activities WHERE user_id=$user_id LIMIT 1;"""

SELECT_LAST_ACTIVITY_ID = """
DECLARE $user_id AS Utf8;
DECLARE $today_date AS Utf8;
SELECT activity_id, start_time
FROM activities WHERE user_id=$user_id AND start_time > $today_date 
ORDER BY start_time DESC
LIMIT 1;"""


class DatabaseManager:
    @staticmethod
    def execute(query, params):
        with ydb.Driver(
            endpoint=os.getenv('ENDPOINT'),
            database=os.getenv('DATABASE'),
            credentials=ydb.iam.MetadataUrlCredentials(),
        ) as driver:
            try:
                driver.wait(fail_fast=True, timeout=5)
            except TimeoutError:
                print('Connect failed to YDB | TIMEOUT')
                print(driver.discovery_debug_details())
                return None

            try:
                session = driver.table_client.session().create()
                prepared_query = session.prepare(query)

                return session.transaction(ydb.SerializableReadWrite()).execute(
                    prepared_query,
                    params,
                    commit_tx=True
                )
            except Exception as _ex:
                print(f'\n\n===\n{_ex}\n===\n\n')

    # Работа с отметками
    def insert_checkin(self, id, user_id, start_time, type, checkin_type):
        """ Загружает отметку в базу данных """
        query = INSERT_CHECKIN
        params = {
            '$id': id, '$user_id': user_id, '$start_time': start_time,
            '$type': type, '$checkin_type': checkin_type
        }

        self.execute(query, params)

    def select_checkins(self, user_id, today_date):
        """ Возвращает отметки пользователя """
        query = SELECT_CHECKINS
        params = {'$user_id': user_id, '$today_date': today_date}

        result_set = self.execute(query, params)
        if not result_set or not result_set[0].rows:
            return None

        # print(result_set[0].rows) [{col0: {val1, val2}}]
        checkins_list = []
        for row in result_set[0].rows:
            checkins_list.append(list(row.values()))

        return checkins_list

    def delete_last_checkin(self, user_id, checkin_id):
        """ Удаление последней отметки """
        query = DELETE_LAST_CHECKIN
        params = {'$user_id': user_id, '$id': checkin_id}
        self.execute(query, params)

    # Работа с активностями
    def insert_activity(self, id, user_id, activity_id, start_time, end_time,
                        duration, activity_type, text):
        """ Добавляет запись об активности в базу данных """
        query = INSERT_ACTIVITY
        params = {
            '$user_id': user_id, '$activity_id': activity_id, '$start_time': start_time,
            '$end_time': end_time, '$duration': duration, '$activity_type': activity_type,
            '$text': text, '$id': id
        }

        self.execute(query, params)

    def select_activities(self, user_id, today_date):
        """ Возвращает активности пользователя """
        query = SELECT_ACTIVITIES
        params = {'$user_id': user_id, '$today_date': today_date}

        result_set = self.execute(query, params)
        if not result_set or not result_set[0].rows:
            return None

        activities_list = []
        for row in result_set[0].rows:
            activities_list.append(list(row.values()))

        return activities_list

    def select_last_activity_id(self, user_id, today_date):
        """ Возвращает id последней активности """
        query = SELECT_LAST_ACTIVITY_ID
        params = {'$user_id': user_id, "$today_date": today_date}
        result_set = self.execute(query, params)

        if not result_set or not result_set[0].rows:
            return 0

        return result_set[0].rows[0][0]

    def check_activity(self, user_id):
        """ Проверяет наличие хотя бы одной активности у пользователя """
        query = CHECK_ACTIVITIES
        params = {'$user_id': user_id}
        result_set = self.execute(query, params)

        if not result_set or not result_set[0].rows:
            return None

        return True

    # Работа с пользователями
    def insert_user(self, user_id, name):
        query = INSERT_USER
        params = {'$id': user_id, '$name': name}
        self.execute(query, params)

    def check_user_exists(self, user_id):
        """ Проверяет наличие пользователя в базе данных """
        query = USER_EXISTS
        params = {'$id': user_id}
        result_set = self.execute(query, params)
        if not result_set or not result_set[0].rows:
            return None

        return result_set[0]
