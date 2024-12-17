import sys
import json
import requests
import datetime
import subprocess
from pathlib import Path

from telethon import TelegramClient
from telethon.tl.types import ChannelParticipantsSearch
from telethon.tl.functions.channels import GetParticipantsRequest

from console import console
from basethon.base_thon import BaseThon
from basethon.json_converter import JsonConverter


def get_settings():
    try:
        with open("settings.json", "r") as f:
            return json.loads(f.read())
    except FileNotFoundError:
        console.log("settings.json file not found")
        return {}

def set_settings(data):
    with open("settings.json", "w") as f:
        f.write(json.dumps(data))

settings = get_settings()

def register_user():
    print("Связываемся с сервером...")
    try:
        current_machine_id = (
            str(subprocess.check_output("wmic csproduct get uuid"), "utf-8")
            .split("\n")[1]
            .strip()
        )
    except Exception as e:
        console.log(f"Error fetching machine ID: {e}")
        sys.exit("Не удалось получить ID машины.")

    admin_username = settings.get("ADMIN_USERNAME")
    script_name = settings.get("SCRIPTNAME")
    BASE_API_URL = settings.get("BASE_API_URL", "http://142.93.105.98:8000")

    try:
        db_id = requests.get(
            f"{BASE_API_URL}/api/{script_name}/{current_machine_id}/{admin_username}"
        )
        db_id = db_id.json()
        if db_id.get("message"):
            console.log("Invalid admin username")
            sys.exit("Неправильный логин")
    except requests.RequestException as e:
        console.log(f"Error contacting API: {e}")
        sys.exit("Ошибка связи с сервером.")

    file_key = settings.get("ACCESS_KEY")
    print(f"Ваш ID в системе: {db_id['id']}")
    if file_key:
        key = file_key
    else:
        key = input("Введите ваш ключ доступа: ")
    while True:
        try:
            is_correct = requests.post(
                f"{BASE_API_URL}/api/{script_name}/check/",
                data={"pk": current_machine_id, "key": key},
            ).json()["message"]
            if is_correct:
                print("Вход успешно выполнен!")
                settings["ACCESS_KEY"] = key
                set_settings(settings)
                return
            else:
                print("Неправильный ключ!")
                key = input("Введите ваш ключ доступа: ")
        except requests.RequestException as e:
            console.log(f"Error verifying access key: {e}")
            print("Ошибка связи с сервером. Повторите попытку.")

def select_status():
    statuses = {
        "1": "all",
        "2": "online",
        "3": "recently",
        "4": "yesterday",
        "5": "week",
        "6": "month",
    }
    status_names = {
        "all": "Все",
        "online": "Онлайн",
        "recently": "Недавно",
        "yesterday": "Вчера",
        "week": "За неделю",
        "month": "За месяц",
    }
    print("Выберите статус пользователей для парсинга:")
    for key, value in statuses.items():
        print(f"{key}. {status_names[value]}")
    choice = input("Введите номер: ")
    return statuses.get(choice, "all")

try:
    # register_user()

    f = open('data.txt', 'a+')
    groups = set(open('groups.txt', encoding='utf-8').read().split('\n'))

    active = select_status()
    datas_ = []
    client = TelegramClient(phone)
    client.start(phone=phone)
    now = datetime.datetime.now()
    day = int(now.day)

    async def parse_channel(client, channel):
        offset_user = 0
        limit_user = 100
        all_participants = []
        filter_user = ChannelParticipantsSearch('')

        try:
            while True:
                participants = await client(GetParticipantsRequest(channel, filter_user, offset_user, limit_user, hash=0))
                if not participants.users:
                    break
                all_participants.extend(participants.users)
                offset_user += len(participants.users)
        except Exception as e:
            console.log(f"Error fetching participants for {channel}: {e}")

        for participant in all_participants:
            try:
                if participant.username is None:
                    continue
                if active == 'online' and 'UserStatusOnline' in str(participant.status):
                    datas_.append(participant.username)
                elif active == 'recently' and 'UserStatusRecently' in str(participant.status):
                    datas_.append(participant.username)
                elif active == 'all':
                    datas_.append(participant.username)
                elif active == 'yesterday' and hasattr(participant.status, 'was_online') and participant.status.was_online.day == day - 1:
                    datas_.append(participant.username)
                elif active == 'week' and 'UserStatusLastWeek' in str(participant.status):
                    datas_.append(participant.username)
                elif active == 'month' and 'UserStatusLastMonth' in str(participant.status):
                    datas_.append(participant.username)
            except Exception as e:
                console.log(f"Error processing participant {participant.id}: {e}")

    for channel in groups:
        print(f'Парсинг {channel}')
        try:
            with client:
                client.loop.run_until_complete(parse_channel(client, channel))
        except Exception as e:
            console.log(f"Error parsing channel {channel}: {e}")

    datas = set(datas_)
    with open('data.txt', 'a+') as file:
        for data in datas:
            file.write(f'{data}\n')
    console.log('Парсинг завершен успешно')

except Exception as e:
    console.log(f"Произошла критическая ошибка: {e}")
    input("Для завершения работы нажмите Enter")


def load_session():
    session_file = 'session.session'
    json_file = 'session.json'

    basethon_session = Path(session_file)
    if not basethon_session.exists():
        console.log("Файл session.session не найден.", style='yellow')
        sys.exit(1)
        return
    sessions_count = JsonConverter().main()
    if not sessions_count:
        console.log("Нет аккаунтов в папке с сессиями!", style="yellow")
        sys.exit(1)
        return
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        console.log(f"Файл {json_file} не найден!", style="red")
        sys.exit(1)
        return        
    except json.JSONDecodeError:
        console.log(f"Ошибка чтения {json_file}! Убедитесь, что файл содержит корректный JSON.", style="red")
        sys.exit(1)
        return
    return session_file, json_data

async def main():

    try:
        telegram_search = TelegramSearch(session_file, json_data, config)
        await telegram_search.main(config)
    except Exception as e:
        console.log(f"Ошибка запуска: {e}", style="red")
