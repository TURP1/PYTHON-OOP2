from __future__ import annotations

from collections import UserDict
from typing import Optional, List
from datetime import datetime, date, timedelta
from functools import wraps
import pickle


class Field:
    def __init__(self, value: str):
        self.value = value

    def __str__(self) -> str:
        return str(self.value)

    @property
    def value(self) -> str:
        return self._value

    @value.setter
    def value(self, new_value: str) -> None:
        self._value = new_value


class Name(Field):
    pass


class Phone(Field):
    @Field.value.setter
    def value(self, new_value: str) -> None:
        normalized = str(new_value).strip()
        if not (normalized.isdigit() and len(normalized) == 10):
            raise ValueError("Phone number must be 10 digits.")
        self._value = normalized


class Birthday(Field):
    @Field.value.setter
    def value(self, new_value: str) -> None:
        raw = str(new_value).strip()
        try:
            parsed = datetime.strptime(raw, "%d.%m.%Y").date()
        except ValueError:
            raise ValueError("Invalid date format. Use DD.MM.YYYY")
        self._value = parsed


class Record:
    def __init__(self, name: str):
        self.name: Name = Name(name)
        self.phones: List[Phone] = []
        self.birthday: Optional[Birthday] = None

    def add_phone(self, phone: str) -> Phone:
        phone_obj = Phone(phone)
        self.phones.append(phone_obj)
        return phone_obj

    def remove_phone(self, phone: str) -> bool:
        phone_obj = self.find_phone(phone)
        if phone_obj is None:
            return False
        self.phones.remove(phone_obj)
        return True

    def edit_phone(self, old_phone: str, new_phone: str) -> bool:
        phone_obj = self.find_phone(old_phone)
        if phone_obj is None:
            return False
        phone_obj.value = new_phone
        return True

    def find_phone(self, phone: str) -> Optional[Phone]:
        for p in self.phones:
            if p.value == phone:
                return p
        return None

    def add_birthday(self, birthday: str) -> Birthday:
        self.birthday = Birthday(birthday)
        return self.birthday

    def __str__(self) -> str:
        return (
            f"Contact name: {self.name.value}, phones: {'; '.join(p.value for p in self.phones)}"
        )


class AddressBook(UserDict):
    def add_record(self, record: Record) -> None:
        self.data[record.name.value] = record

    def find(self, name: str) -> Optional[Record]:
        return self.data.get(name)

    def delete(self, name: str) -> bool:
        if name in self.data:
            del self.data[name]
            return True
        return False

    def get_upcoming_birthdays(self) -> List[dict]:
        today = date.today()
        end_date = today + timedelta(days=7)
        upcoming: List[dict] = []

        for record in self.data.values():
            if record.birthday is None:
                continue
            bday: date = record.birthday.value

            year = today.year
            month, day = bday.month, bday.day
            try:
                bday_this_year = date(year, month, day)
            except ValueError:
                if month == 2 and day == 29:
                    bday_this_year = date(year, 2, 28)
                else:
                    continue

            candidate = bday_this_year if bday_this_year >= today else date(year + 1, month, day if not (month == 2 and day == 29) else 28)

            if today <= candidate <= end_date:
                congratulation_date = candidate
                if congratulation_date.weekday() == 5:
                    congratulation_date += timedelta(days=2)
                elif congratulation_date.weekday() == 6:
                    congratulation_date += timedelta(days=1)

                upcoming.append({
                    "name": record.name.value,
                    "congratulation_date": congratulation_date.strftime("%Y-%m-%d"),
                })

        upcoming.sort(key=lambda x: (x["congratulation_date"], x["name"]))
        return upcoming


def save_data(book, filename: str = "addressbook.pkl"):
    with open(filename, "wb") as f:
        pickle.dump(book, f)


def load_data(filename: str = "addressbook.pkl") -> "AddressBook":
    try:
        with open(filename, "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return AddressBook()


def input_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e)
        except KeyError:
            return "Contact not found."
        except IndexError:
            return "Not enough arguments."
        except Exception:
            return "An unexpected error occurred."
    return wrapper


def parse_input(user_input: str):
    parts = user_input.strip().split()
    if not parts:
        return "", []
    command = parts[0].lower()
    return command, parts[1:]


@input_error
def add_contact(args, book: AddressBook):
    name, phone, *_ = args
    record = book.find(name)
    message = "Contact updated."
    if record is None:
        record = Record(name)
        book.add_record(record)
        message = "Contact added."
    if phone:
        record.add_phone(phone)
    return message


@input_error
def change_phone(args, book: AddressBook):
    name, old_phone, new_phone, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    if record.edit_phone(old_phone, new_phone):
        return "Phone updated."
    return "Old phone not found."


@input_error
def show_phones(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    if not record.phones:
        return "No phones."
    return ", ".join(p.value for p in record.phones)


@input_error
def show_all(args, book: AddressBook):
    if not book.data:
        return "No contacts found."
    lines = []
    for record in book.data.values():
        phones = "; ".join(p.value for p in record.phones) if record.phones else "no phones"
        bday = record.birthday.value.strftime("%d.%m.%Y") if record.birthday else "N/A"
        lines.append(f"{record.name.value}: {phones}; birthday: {bday}")
    return "\n".join(lines)


@input_error
def add_birthday(args, book: AddressBook):
    name, birthday_str, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    record.add_birthday(birthday_str)
    return "Birthday added."


@input_error
def show_birthday(args, book: AddressBook):
    name, *_ = args
    record = book.find(name)
    if record is None:
        return "Contact not found."
    if record.birthday is None:
        return "Birthday not set."
    return record.birthday.value.strftime("%d.%m.%Y")


@input_error
def birthdays(args, book: AddressBook):
    upcoming = book.get_upcoming_birthdays()
    if not upcoming:
        return "No birthdays in the next week."
    grouped = {}
    for item in upcoming:
        grouped.setdefault(item["congratulation_date"], []).append(item["name"])
    lines = []
    for day in sorted(grouped.keys()):
        lines.append(f"{day}: {', '.join(sorted(grouped[day]))}")
    return "\n".join(lines)


def main():
    book = load_data()
    print("Welcome to the assistant bot!")
    while True:
        user_input = input("Enter a command: ")
        command, args = parse_input(user_input)

        if command in ["close", "exit"]:
            save_data(book)
            print("Good bye!")
            break
        elif command == "hello":
            print("How can I help you?")
        elif command == "add":
            print(add_contact(args, book))
        elif command == "change":
            print(change_phone(args, book))
        elif command == "phone":
            print(show_phones(args, book))
        elif command == "all":
            print(show_all(args, book))
        elif command == "add-birthday":
            print(add_birthday(args, book))
        elif command == "show-birthday":
            print(show_birthday(args, book))
        elif command == "birthdays":
            print(birthdays(args, book))
        else:
            print("Invalid command.")


if __name__ == "__main__":
    main()
