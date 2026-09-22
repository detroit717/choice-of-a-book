import json
import os
import re

RULES_FILE = "rules.json"

KEYWORDS = {
    "цель": {
        "развлечение": [
            "развлечься", "развлечение", "отдохнуть", "отдых", "фан", 
            "удовольствие", "почитать", "прочитать", "хочу"
        ],
        "саморазвитие": [
            "саморазвитие", "учеба", "научиться", "польза", "развитие", "узнать"
        ]
    },
    "предпочтение": {
        "технологии": [
            "технологии", "технология", "технологическое", "технологическую", 
            "роботы", "будущее", "sci-fi", "космос", "наука", "гаджеты"
        ],
        "вымышленный_мир": [
            "вымышленный", "магия", "эльфы", "драконы", "чудеса", "фэнтези", "сказка"
        ],
        "загадки": [
            "загадки", "убийство", "расследование", "детектив", "тайна", "преступление"
        ],
        "мышление": [
            "мышление", "мозг", "психология", "поведение", "мысли"
        ],
        "прошлое": [
            "прошлое", "история", "историческая", "древность", "предки"
        ]
    },
    "объем": {
        "небольшой": [
            "небольшая", "короткая", "короткую", "маленькая", "маленькую", 
            "небольшой", "небольшую", "короткий", "быстро", "мало"
        ],
        "большой": [
            "большая", "большую", "длинная", "длинную", "толстая", "толстую", 
            "большой", "длинный", "эпопея", "много"
        ]
    },
    "атмосфера": {
        "уютная": ["уютная", "уютную", "добрая", "теплая", "ламповая"],
        "мрачная": ["мрачная", "мрачную", "темная", "пугающая", "триллер", "жесткая"]
    }
}

def normalize(text: str) -> str:
    """Приводит текст к нижнему регистру, заменяет 'ё' на 'е' и пробелы на '_'."""
    text = text.strip().lower().replace("ё", "е")
    return "_".join(text.split())

def format_display(text: str) -> str:
    """Форматирует текст из базы для красивого вывода."""
    return text.replace("_", " ")

def parse_natural_language(text: str) -> dict:
    """Анализирует произвольную строку пользователя и извлекает известные факты."""
    clean_text = text.lower().replace("ё", "е")
    words = re.findall(r'\b\w+\b', clean_text)
    
    extracted = {}
    for obj, val_map in KEYWORDS.items():
        for val, kw_list in val_map.items():
            for kw in kw_list:
                if kw in words or any(kw in w for w in words):
                    extracted[obj] = val
                    break
    return extracted

class ExpertSystem:
    def __init__(self, rules_filename):
        self.rules_filename = rules_filename
        self.rules = []
        self.wm = {}
        self.load_rules()

    def load_rules(self):
        if os.path.exists(self.rules_filename):
            try:
                with open(self.rules_filename, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки базы правил: {e}")

    def save_rules(self):
        try:
            with open(self.rules_filename, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
            print("База правил успешно сохранена.")
        except Exception as e:
            print(f"Ошибка сохранения: {e}")

    def show_rules(self):
        if not self.rules:
            print("База правил пуста.")
            return
        print("\n--- ТЕКУЩАЯ БАЗА ПРАВИЛ ---")
        for r in self.rules:
            if_c = " И ".join([f"{format_display(k)}='{format_display(v)}'" for k, v in r['if'].items()])
            then_c = ", ".join([f"{format_display(k)}='{format_display(v)}'" for k, v in r['then'].items()])
            print(f"Правило №{r['id']}: ЕСЛИ {if_c} ТО {then_c}")

    def edit_rules_menu(self):
        while True:
            print("\n1. Просмотр | 2. Добавить правило | 3. Удалить | 0. Назад")
            c = input("> ").strip()
            if c == "1":
                self.show_rules()
            elif c == "2":
                self.add_rule()
            elif c == "3":
                self.delete_rule()
            elif c == "0":
                break

    def add_rule(self):
        if_dict = {}
        print("\nФормирование условий ЕСЛИ (формат 'объект: значение', Enter — завершить):")
        while True:
            raw = input("ЕСЛИ > ").strip()
            if not raw:
                if not if_dict:
                    print("Правило должно содержать хотя бы одно условие!")
                    continue
                break
            if ":" in raw:
                k, v = raw.split(":", 1)
                if_dict[normalize(k)] = normalize(v)
            else:
                print("Используйте двоеточие, например: 'цель: развлечение'")

        while True:
            raw = input("ТО (формат 'объект: значение') > ").strip()
            if ":" in raw:
                k, v = raw.split(":", 1)
                then_dict = {normalize(k): v.strip()}
                break
            print("Используйте двоеточие.")

        new_id = max([r['id'] for r in self.rules], default=0) + 1
        self.rules.append({"id": new_id, "if": if_dict, "then": then_dict})
        self.save_rules()

    def edit_rule(self, rule_id, new_if, new_then):
        """Изменяет существующее правило по ID и сохраняет файл."""
        for rule in self.rules:
            if rule["id"] == rule_id:
                rule["if"] = new_if
                rule["then"] = new_then
                self.save_rules()
                return True
        return False

    def delete_rule(self):
        self.show_rules()
        if not self.rules:
            return
        try:
            r_id = int(input("\nID для удаления: "))
            self.rules = [r for r in self.rules if r['id'] != r_id]
            self.save_rules()
        except ValueError:
            print("Некорректный ID.")

    def show_working_memory(self):
        print("\nТЕКУЩИЕ ФАКТЫ В РБД:")
        if not self.wm:
            print(" <база данных пуста>")
        else:
            for k, v in self.wm.items():
                print(f" • {format_display(k)} = {format_display(v)}")

    def run_forward_chaining(self):
        self.wm = {}
        print("\nОпишите, какую книгу вы хотите (произвольным предложением):")
        user_input = input("> ").strip()
        
        if user_input:
            extracted = parse_natural_language(user_input)
            if extracted:
                self.wm.update(extracted)
                print("\n[СИСТЕМА] Из вашего запроса распознаны следующие факты:")
                for k, v in extracted.items():
                    print(f" -> {format_display(k)}: {format_display(v)}")
            else:
                print("\n[СИСТЕМА] Не удалось автоматически распознать факты из текста.")

        fired_rules = set()

        while True:
            self.show_working_memory()

            if "рекомендация" in self.wm:
                print(f"\n==========================================")
                print(f"РЕЗУЛЬТАТ: {self.wm['рекомендация']}")
                print(f"==========================================")
                break

            rule_fired = False

            for rule in self.rules:
                if rule['id'] in fired_rules:
                    continue

                if all(self.wm.get(k) == v for k, v in rule['if'].items()):
                    print(f"\n-> Сработало правило №{rule['id']}")
                    for tk, tv in rule['then'].items():
                        self.wm[tk] = tv
                        print(f"   Добавлен факт: {format_display(tk)} = {format_display(tv)}")
                    fired_rules.add(rule['id'])
                    rule_fired = True
                    break

            if not rule_fired:
                print("\n[ИНФО] Нет применимых правил с текущими фактами.")
                print("Уточните запрос предложением или в формате 'объект: значение' (Enter — закончить):")
                raw = input("+ ").strip()
                if not raw:
                    if "жанр" in self.wm:
                        print(f"\nЧАСТИЧНЫЙ ВЫВОД: жанр '{format_display(self.wm['жанр'])}'")
                    else:
                        print("\nВЫВОД НЕ СДЕЛАН: недостаточно данных.")
                    break
                
                if ":" in raw:
                    k, v = raw.split(":", 1)
                    self.wm[normalize(k)] = normalize(v)
                else:
                    more_extracted = parse_natural_language(raw)
                    if more_extracted:
                        self.wm.update(more_extracted)
                    else:
                        print("Не удалось распознать факт.")

#def main():
#    es = ExpertSystem(RULES_FILE)
#    while True:
#        print("\n=== ЭКСПЕРТНАЯ СИСТЕМА ПОДБОРА КНИГ ===")
#        print("1. Запуск вывода (Подбор книги)")
#        print("2. Редактировать базу знаний")
#        print("3. Показать все правила")
#        print("0. Выход")
#        choice = input("> ").strip()

#        if choice == "1":
#            es.run_forward_chaining()
#        elif choice == "2":
#            es.edit_rules_menu()
#        elif choice == "3":
#            es.show_rules()
#        elif choice == "0":
#            break

#if __name__ == "__main__":
#    main()