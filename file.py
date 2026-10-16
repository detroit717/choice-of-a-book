import json
import os
import re

RULES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")
INITIAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "initial_facts.json")
MAX_DEPTH = 50


class ProofNode:
    """Узел дерева доказательства обратной цепочки рассуждений."""

    def __init__(self, kind, text, ok=False):
        self.kind = kind   # goal | rule | fact | contra | norule | cycle
        self.text = text
        self.ok = ok
        self.children = []

    def render(self, depth=0, lines=None):
        if lines is None:
            lines = []
        mark = "+" if self.ok else "-"
        lines.append("  " * depth + f"[{mark}] {self.text}")
        for ch in self.children:
            ch.render(depth + 1, lines)
        return lines

    def has_kind(self, kind):
        if self.kind == kind:
            return True
        return any(ch.has_kind(kind) for ch in self.children)


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
            "вымышленный", "магия", "эльфы", "драконы", "чудеса", "сказка"
        ],
        "загадки": [
            "загадки", "убийство", "расследование", "тайна", "преступление"
        ],
        "мышление": [
            "мышление", "мозг", "психология", "поведение", "мысли"
        ],
        "прошлое": [
            "прошлое", "история", "историческая", "древность", "предки"
        ],
        "общество": [
            "общество", "тоталитаризм", "государство", "система", "контроль", "социум"
        ]
    },
    "жанр": {
        "научная_фантастика": ["фантастика", "фантастику", "научная фантастика"],
        "фэнтези": ["фэнтези", "фентези"],
        "детектив": ["детектив", "детективы"],
        "антиутопия": ["антиутопия", "антиутопию"],
        "история": ["исторический", "историческую"],
        "психология": ["психологическую", "психологическое"]
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
    text = text.strip().lower().replace("ё", "е")
    return "_".join(text.split())

def format_display(text: str) -> str:
    return str(text).replace("_", " ")

def parse_natural_language(text: str) -> dict:
    clean_text = text.lower().replace("ё", "е")
    words = re.findall(r'\b\w+\b', clean_text)
    
    extracted = {}
    for obj, val_map in KEYWORDS.items():
        for val, kw_list in val_map.items():
            for kw in kw_list:
                kw_norm = kw.lower().replace("ё", "е")
                if kw_norm in clean_text or kw_norm in words or any(kw_norm in w for w in words):
                    extracted[obj] = val
                    break
    return extracted

class ExpertSystem:
    def __init__(self, rules_filename=RULES_FILE):
        self.rules_filename = rules_filename
        self.rules = []
        self.wm = {}
        self.initial_wm = {}
        self.goal = {}
        self.derived = []
        self.load_rules()
        self.load_initial_state()

    def load_rules(self):
        if os.path.exists(self.rules_filename):
            try:
                with open(self.rules_filename, 'r', encoding='utf-8') as f:
                    self.rules = json.load(f)
            except Exception as e:
                print(f"Ошибка загрузки базы правил: {e}")
        else:
            self.rules = []

    def load_initial_state(self):
        """Читает начальное состояние РБД и цель по умолчанию из initial_facts.json."""
        self.initial_wm = {}
        self.goal = {}
        if os.path.exists(INITIAL_FILE):
            try:
                with open(INITIAL_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.initial_wm = dict(data.get("wm", {}))
                self.goal = dict(data.get("goal", {}))
            except Exception as e:
                print(f"Ошибка загрузки начального состояния РБД: {e}")
        self.wm = dict(self.initial_wm)

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
        print("\nФормирование условий ЕСЛИ (формат 'объект: значение', Enter — завершить ввод условий):")
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
                print("Используйте двоеточие, например: 'предпочтение: общество'")

        while True:
            raw = input("ТО (формат 'объект: значение') > ").strip()
            if ":" in raw:
                k, v = raw.split(":", 1)
                norm_k = normalize(k)
                norm_v = v.strip() if norm_k == "рекомендация" else normalize(v)
                then_dict = {norm_k: norm_v}
                break
            print("Используйте двоеточие, например: 'рекомендация: Название книги'")

        new_id = max([r['id'] for r in self.rules], default=0) + 1
        self.rules.append({"id": new_id, "if": if_dict, "then": then_dict})
        self.save_rules()

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

    def edit_rule(self, rule_id, if_dict, then_dict):
        for rule in self.rules:
            if rule['id'] == rule_id:
                rule['if'] = if_dict
                rule['then'] = then_dict
                self.save_rules()
                return True
        return False

    def show_working_memory(self):
        print("\nТЕКУЩИЕ ФАКТЫ В РБД:")
        if not self.wm:
            print(" <база данных пуста>")
        else:
            for k, v in self.wm.items():
                print(f" • {format_display(k)} = {format_display(v)}")

    def run_forward_chaining(self):
        self.wm = dict(self.initial_wm)
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
                print(f"РЕЗУЛЬТАТ: {self.wm['рекомендация']}")
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
                    norm_k = normalize(k)
                    norm_v = v.strip() if norm_k == "рекомендация" else normalize(v)
                    self.wm[norm_k] = norm_v
                else:
                    more_extracted = parse_natural_language(raw)
                    if more_extracted:
                        self.wm.update(more_extracted)
                    else:
                        print("Не удалось распознать факт. Попробуйте ввести в формате 'объект: значение'.")

    # ---------- обратная цепочка рассуждений ----------

    def book_titles(self):
        """Список всех книг, встречающихся в заключениях правил."""
        return [r['then']['рекомендация'] for r in self.rules if 'рекомендация' in r['then']]

    @staticmethod
    def _stem(word: str) -> str:
        """Грубое усечение русских окончаний для сопоставления слов."""
        for suf in ("иями", "ями", "ами", "ий", "ая", "ое", "ые", "ой", "ей",
                    "ем", "ом", "ам", "ям", "ах", "ях", "ов", "ев", "ью",
                    "ю", "я", "а", "о", "е", "у", "ы", "и", "й", "ь"):
            if word.endswith(suf) and len(word) - len(suf) >= 3:
                return word[:-len(suf)]
        return word

    def match_book(self, text: str):
        """Пытается найти книгу из базы знаний по свободному тексту. Возвращает название или None."""
        cleaned = re.sub(r"[^0-9a-zа-яё]+", " ", normalize(text))
        stems = {self._stem(t) for t in cleaned.split() if t}
        for title in self.book_titles():
            main = title.split("(")[0]
            for word in normalize(main).split("_"):
                if word and self._stem(word) in stems:
                    return title
        return None

    def parse_facts_text(self, text: str):
        """Разбирает многострочный текст с фактами: строки 'объект: значение' и свободный текст."""
        result = {}
        for line in (text or "").splitlines():
            line = line.strip()
            if not line:
                continue
            if ":" in line:
                k, v = line.split(":", 1)
                nk = normalize(k)
                result[nk] = v.strip() if nk == "рекомендация" else normalize(v)
            else:
                result.update(parse_natural_language(line))
        return result

    def parse_goal(self, raw: str):
        """Преобразует цель. Поддерживает 'объект: значение' и название книги.

        Свободный текст описания целью не считается — возвращается None,
        чтобы вызывающий код трактовал его как описание (факты).
        """
        raw = (raw or "").strip()
        if not raw:
            return None
        if ":" in raw:
            k, v = raw.split(":", 1)
            k = normalize(k)
            v = "*" if v.strip() == "*" else (v.strip() if k == "рекомендация" else normalize(v))
            return {k: v}
        book = self.match_book(raw)
        if book:
            return {"рекомендация": book}
        return None

    def _backward_candidates(self, key, value):
        return [
            r for r in self.rules
            if key in r['then'] and (value == "*" or r['then'][key] == value)
        ]

    def _backward_prove(self, key, value, depth, active):
        """Рекурсивно доказывает подцель key=value. Возвращает (ok, узел дерева)."""
        if depth > MAX_DEPTH:
            return False, ProofNode("cycle", f"Превышена глубина рекурсии ({key}={value})", False)

        node = ProofNode("goal", f"Подцель: {format_display(key)} = {format_display(value)}", False)

        # 1. Факт уже известен в РБД
        if key in self.wm:
            cur = self.wm[key]
            if value == "*" or cur == value:
                node.kind = "fact"
                node.ok = True
                node.text = f"Факт уже в РБД: {format_display(key)} = {format_display(cur)}"
                return True, node
            node.kind = "contra"
            node.text = (f"ПРОТИВОРЕЧИЕ: в РБД {format_display(key)} = {format_display(cur)}, "
                         f"а требуется {format_display(value)}")
            return False, node

        # 2. Правила, которые могут вывести эту подцель (пробуем по порядку, backtracking)
        candidates = self._backward_candidates(key, value)
        if not candidates:
            node.kind = "norule"
            node.text = f"Нет правил, выводящих {format_display(key)} = {format_display(value)}"
            return False, node

        for rule in candidates:
            if rule['id'] in active:
                node.children.append(ProofNode(
                    "cycle", f"Правило №{rule['id']} пропущено: циклическая зависимость", False))
                continue

            cond = " И ".join(f"{format_display(k)}='{format_display(v)}'" for k, v in rule['if'].items())
            conc = ", ".join(f"{format_display(k)}='{format_display(v)}'" for k, v in rule['then'].items())
            rnode = ProofNode("rule", f"Правило №{rule['id']}: ЕСЛИ {cond} -> ТО {conc}", False)

            active.add(rule['id'])
            ok = True
            for ck, cv in rule['if'].items():
                sub_ok, sub = self._backward_prove(ck, cv, depth + 1, active)
                rnode.children.append(sub)
                if not sub_ok:
                    ok = False
                    break
            active.discard(rule['id'])

            if ok:
                rnode.ok = True
                for tk, tv in rule['then'].items():
                    if tk not in self.wm:
                        self.wm[tk] = tv
                        self.derived.append((tk, tv))
                node.children.append(rnode)
                node.ok = True
                return True, node

            node.children.append(rnode)

        return False, node

    def backward_chaining(self, goal=None):
        """Доказывает/опровергает цель обратной цепочкой рассуждений.

        Возвращает (доказана: bool, статус: str, корень: ProofNode, строки: list[str]).
        """
        if goal is not None:
            self.goal = dict(goal)
        if not self.goal:
            raise ValueError("Целевая ситуация не задана")

        self.derived = []
        key, value = next(iter(self.goal.items()))
        root_text = f"ЦЕЛЬ: {format_display(key)} = {format_display(value)}"

        ok, subtree = self._backward_prove(key, value, 0, set())
        root = ProofNode("goal", root_text, ok)
        root.children.append(subtree)

        if ok:
            status = "ЦЕЛЬ ДОКАЗАНА"
        elif subtree.has_kind("contra"):
            status = "ЦЕЛЬ ОПРОВЕРГНУТА (противоречит исходным данным)"
        else:
            status = "ЦЕЛЬ НЕ ДОКАЗАНА (недостаточно фактов или правил)"

        return ok, status, root, subtree.render(1)

    def run_backward_chaining(self, facts_text="", goal=None):
        """Полный прогон обратного вывода с текстовым отчётом.

        Сбрасывает РБД к начальному состоянию, добавляет факты из facts_text
        (естественный язык или формат 'объект: значение'), доказывает цель.
        Возвращает словарь с результатами для отображения в интерфейсе.
        """
        self.wm = dict(self.initial_wm)
        if facts_text:
            self.wm.update(self.parse_facts_text(facts_text))

        ok, status, root, lines = self.backward_chaining(goal)

        result = {
            "ok": ok,
            "status": status,
            "tree": root.render(0),
            "branches": lines,
            "derived": list(self.derived),
            "wm": dict(self.wm),
        }
        return result


def main():
    es = ExpertSystem(RULES_FILE)
    while True:
        print("\n=== ЭКСПЕРТНАЯ СИСТЕМА ПОДБОРА КНИГ ===")
        print("1. Запуск вывода (Подбор книги)")
        print("2. Редактировать базу знаний")
        print("3. Показать все правила")
        print("0. Выход")
        choice = input("> ").strip()

        if choice == "1":
            es.run_forward_chaining()
        elif choice == "2":
            es.edit_rules_menu()
        elif choice == "3":
            es.show_rules()
        elif choice == "0":
            break

if __name__ == "__main__":
    main()