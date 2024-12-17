import sys
import json
import asyncio
import requests
import datetime
import subprocess
from pathlib import Path

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
        response = requests.get(
            f"{BASE_API_URL}/api/{script_name}/{current_machine_id}/{admin_username}"
        )
        db_id = response.json()
        if db_id.get("message"):
            console.log("Invalid admin username")
            sys.exit("Неправильный логин")
    except requests.RequestException as e:
        console.log(f"Error contacting API: {e}")
        sys.exit("Ошибка связи с сервером.")

    file_key = settings.get("ACCESS_KEY")
    print(f"Ваш ID в системе: {db_id['id']}")
    if not file_key:
        key = input("Введите ваш ключ доступа: ")
    else:
        key = file_key

    while True:
        try:
            response = requests.post(
                f"{BASE_API_URL}/api/{script_name}/check/",
                data={"pk": current_machine_id, "key": key},
            )
            if response.json().get("message"):
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

settings = get_settings()

#register_user()

class Parser(BaseThon):
    def __init__(self, item: str, json_data: dict, channels):
        super().__init__(item, json_data)
        self.channels = channels
        self.datas_ = []

    def select_status(self):
        statuses = {
            "1": ("all", "Все"),
            "2": ("online", "Онлайн"),
            "3": ("recently", "Недавно"),
            "4": ("yesterday", "Вчера"),
            "5": ("week", "За неделю"),
            "6": ("month", "За месяц"),
        }
        print("Выберите статус пользователей для парсинга:")
        for key, value in statuses.items():
            print(f"{key}. {value[1]}")
        choice = input("Введите номер: ")
        result = statuses.get(choice, "all")[0]
        return result
    
    async def parse_channel(self, channel, active):
        offset_user = 0
        limit_user = 100
        all_participants = []
        filter_user = ChannelParticipantsSearch('')

        try:
            while True:
                participants = await self.client(GetParticipantsRequest(channel, filter_user, offset_user, limit_user, hash=0))
                if not participants.users:
                    break
                all_participants.extend(participants.users)
                offset_user += len(participants.users)
        except Exception as e:
            if "Cannot find any entity corresponding" in str(e):
                console.log(f"Неверный формат группы {channel}, пропускаем", style="red")
                return
            else:
                console.log(f"Ошибка при получении участников группы {channel}: {e}", style="red")

        now = datetime.datetime.now()
        day = int(now.day)

        for participant in all_participants:
            try:
                if participant.username is None:
                    continue
                if active == 'online' and 'UserStatusOnline' in str(participant.status):
                    self.datas_.append(participant.username)
                elif active == 'recently' and 'UserStatusRecently' in str(participant.status):
                    self.datas_.append(participant.username)
                elif active == 'all':
                    self.datas_.append(participant.username)
                elif active == 'yesterday' and hasattr(participant.status, 'was_online') and participant.status.was_online.day == day - 1:
                    self.datas_.append(participant.username)
                elif active == 'week' and 'UserStatusLastWeek' in str(participant.status):
                    self.datas_.append(participant.username)
                elif active == 'month' and 'UserStatusLastMonth' in str(participant.status):
                    self.datas_.append(participant.username)
            except Exception as e:
                console.log(f"Error processing participant {participant.id}: {e}")

    async def start_parse(self):
        active = self.select_status()
        for channel in self.channels:
            console.log(f'Парсинг {channel}')
            await self.parse_channel(channel, active)

        datas = set(self.datas_)
        with open('data.txt', 'a+') as file:
            for data in datas:
                file.write(f'{data}\n')
        console.log('Парсинг завершен успешно', style="green")

    async def _main(self):
        r = await self.check()
        if "OK" not in r:
            console.log("Аккаунт разлогинен или забанен", style="red")
            return
        await self.start_parse()

def get_groups():
    try:
        groups = set(Path("groups.txt").read_text(encoding="utf-8").splitlines())
    except FileNotFoundError:
        console.log("Файл groups.txt не найден", style="red")
        sys.exit(1)
    return groups

def load_session():
    session_file = 'session.session'
    json_file = 'session.json'

    if not Path(session_file).exists():
        console.log("Файл session.session не найден.", style='yellow')
        sys.exit(1)
    if not JsonConverter().main():
        console.log("Нет аккаунтов в папке с сессиями!", style="yellow")
        sys.exit(1)
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            json_data = json.load(f)
    except FileNotFoundError:
        console.log(f"Файл {json_file} не найден!", style="red")
        sys.exit(1)
    except json.JSONDecodeError:
        console.log(f"Ошибка чтения {json_file}! Убедитесь, что файл содержит корректный JSON.", style="red")
        sys.exit(1)
    return session_file, json_data

async def main():
    session_file, json_data = load_session()
    parser = Parser(session_file, json_data, get_groups())
    await parser._main()

if __name__ == "__main__":
    asyncio.run(main())
