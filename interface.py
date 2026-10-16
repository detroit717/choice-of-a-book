import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

from file import (
    ExpertSystem, RULES_FILE, format_display, normalize,
    parse_natural_language
)

# Главный класс приложения Tkinter, создающий графический окно и инициализирующий вкладки.
class App(tk.Tk):
    # Конструктор класса App: настраивает параметры окна, экспертную систему, стили и вкладки.
    def __init__(self):
        super().__init__()
        self.title("Подбор книг")
        self.geometry("820x600")
        self.minsize(720, 500)

        self.es = ExpertSystem(RULES_FILE)

        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", padding=6)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_infer = InferenceTab(nb, self.es)
        self.tab_backward = BackwardTab(nb, self.es)
        self.tab_rules = RulesTab(nb, self.es)
        self.tab_state = StateTab(nb, self.es)

        nb.add(self.tab_infer, text="  Подбор книги (прямой вывод)  ")
        nb.add(self.tab_backward, text="  Обратный вывод  ")
        nb.add(self.tab_rules, text="  База правил  ")
        nb.add(self.tab_state, text="  Состояние РБД  ")

        self.nb = nb
        self.nb.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    # Перехватывает переключение вкладок и обновляет данные на целевой вкладке.
    def on_tab_changed(self, event):
        current = self.nb.nametowidget(self.nb.select())
        if current is self.tab_rules:
            self.tab_rules.refresh()
        elif current is self.tab_state:
            self.tab_state.refresh()
        elif current is self.tab_backward:
            self.tab_backward.refresh_state()


# Класс вкладки «Подбор книги» для ввода текстового запроса пользователем и запуска прямого вывода.
class InferenceTab(ttk.Frame):
    # Конструктор класса InferenceTab: создает текстовые поля, кнопки управления и виджет логирования.
    def __init__(self, parent, es: ExpertSystem):
        super().__init__(parent, padding=10)
        self.es = es

        ttk.Label(self, text="Опишите, какую книгу вы хотите:").pack(anchor="w")
        ttk.Label(self, text="Пример: «Хочу длинную книгу про будущее и технологии»")\
            .pack(anchor="w", pady=(0, 6))

        self.input = scrolledtext.ScrolledText(self, height=4, wrap="word", font=("Segoe UI", 10))
        self.input.pack(fill="x")

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=8)
        ttk.Button(btns, text="Подобрать", command=self.run_inference).pack(side="left")
        ttk.Button(btns, text="Очистить", command=self.clear_all).pack(side="left", padx=6)

        self.log = scrolledtext.ScrolledText(self, wrap="word", font=("Consolas", 10), state="disabled")
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("sys",   foreground="#0a7a3a")
        self.log.tag_config("rule",  foreground="#0a5fd0")
        self.log.tag_config("fact",  foreground="#b06a00")
        self.log.tag_config("final", foreground="#b00020", font=("Consolas", 11, "bold"))
        self.log.tag_config("warn",  foreground="#c06000")

    # Добавляет форматированную строку в лог вывода с указанным тегом стиля.
    def write_log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or "")
        self.log.see("end")
        self.log.configure(state="disabled")

    # Сбрасывает введенный пользователем текст, лог вывода и очищает рабочую базу данных.
    def clear_all(self):
        self.input.delete("1.0", "end")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.es.wm = dict(self.es.initial_wm)

    # Запускает процесс распознавания фактов из текста и выполняет алгоритм прямого вывода.
    def run_inference(self):
        user_text = self.input.get("1.0", "end").strip()
        if not user_text:
            messagebox.showwarning("Пустой запрос", "Введите описание желаемой книги.")
            return

        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

        self.es.wm = dict(self.es.initial_wm)

        extracted = parse_natural_language(user_text)
        if extracted:
            self.write_log("[СИСТЕМА] Распознаны факты:", "sys")
            for k, v in extracted.items():
                self.write_log(f"   {format_display(k)} = {format_display(v)}", "fact")
                self.es.wm[k] = v
        else:
            self.write_log("[СИСТЕМА] Не удалось распознать факты из текста.", "warn")

        fired = set()
        guard = 0
        while guard < 200:
            guard += 1

            self.write_log("\n[РБД] " + (
                ", ".join(f"{format_display(k)}={format_display(v)}" for k, v in self.es.wm.items())
                or "<пусто>"), "sys")

            if "рекомендация" in self.es.wm:
                self.write_log("\n" + "=" * 50, "final")
                self.write_log(f"РЕКОМЕНДАЦИЯ: {self.es.wm['рекомендация']}", "final")
                self.write_log("=" * 50, "final")
                return

            fired_this_round = False
            for rule in self.es.rules:
                if rule["id"] in fired:
                    continue
                if all(self.es.wm.get(k) == v for k, v in rule["if"].items()):
                    self.write_log(f"\nСработало правило №{rule['id']}", "rule")
                    for tk_, tv_ in rule["then"].items():
                        self.es.wm[tk_] = tv_
                        self.write_log(
                            f"   добавлен факт: {format_display(tk_)} = {format_display(tv_)}", "fact")
                    fired.add(rule["id"])
                    fired_this_round = True
                    break

            if fired_this_round:
                continue

            self.write_log("\nНет применимых правил с текущими фактами.", "warn")
            if "жанр" in self.es.wm:
                self.write_log(f"Частичный вывод: жанр '{format_display(self.es.wm['жанр'])}'", "final")
            else:
                self.write_log("Вывод не сделан: недостаточно данных.", "final")
            return

        self.write_log("Превышен лимит шагов вывода.", "warn")


# Класс вкладки «Обратный вывод» для доказательства/опровержения цели обратной цепочкой рассуждений.
class BackwardTab(ttk.Frame):
    # Конструктор класса BackwardTab: создаёт поля ввода описания и цели, кнопки и журнал вывода.
    def __init__(self, parent, es: ExpertSystem):
        super().__init__(parent, padding=10)
        self.es = es

        ttk.Label(self, text="Подбор книги обратной цепочкой рассуждений")\
            .pack(anchor="w")
        ttk.Label(self, text="Опишите словами, какую книгу вы хотите (свободным текстом).\n"
                             "Например: «хочу книгу про общество» / "
                             "«интересная книга про загадки и расследования».")\
            .pack(anchor="w", pady=(0, 4))

        self.facts_input = scrolledtext.ScrolledText(self, height=3, wrap="word", font=("Segoe UI", 10))
        self.facts_input.pack(fill="x")

        goal_row = ttk.Frame(self)
        goal_row.pack(fill="x", pady=(6, 4))
        ttk.Label(goal_row, text="Цель (необязательно, пусто → любая подходящая книга):").pack(side="left")
        self.goal_entry = ttk.Entry(goal_row)
        self.goal_entry.pack(side="left", fill="x", expand=True, padx=6)
        ttk.Label(self, text="Цель можно задать названием книги (например: 1984), свободным текстом "
                             "или в формате «объект: значение» (для любого значения — '*').",
                  foreground="#666666").pack(anchor="w")

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=6)
        ttk.Button(btns, text="Подобрать (обратный вывод)", command=self.run_backward).pack(side="left")
        ttk.Button(btns, text="Сбросить к начальным фактам", command=self.reset_facts).pack(side="left", padx=6)
        ttk.Button(btns, text="Очистить журнал", command=self.clear_log).pack(side="left")

        self.log = scrolledtext.ScrolledText(self, wrap="word", font=("Consolas", 10), state="disabled")
        self.log.pack(fill="both", expand=True)

        self.log.tag_config("sys",   foreground="#0a7a3a")
        self.log.tag_config("tree",  foreground="#333333")
        self.log.tag_config("ok",    foreground="#0a7a3a", font=("Consolas", 10, "bold"))
        self.log.tag_config("fail",  foreground="#b00020", font=("Consolas", 10, "bold"))
        self.log.tag_config("fact",  foreground="#b06a00")
        self.log.tag_config("warn",  foreground="#c06000")

    # Добавляет строку в журнал вывода с указанным стилем.
    def write_log(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag or "")
        self.log.see("end")
        self.log.configure(state="disabled")

    # Очищает журнал вывода.
    def clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    # Сбрасывает поле описания и восстанавливает начальное состояние РБД.
    def reset_facts(self):
        self.facts_input.delete("1.0", "end")
        self.es.wm = dict(self.es.initial_wm)
        self.write_log("[СИСТЕМА] РБД сброшена к начальным фактам.", "sys")
        self.refresh_state()

    # Показывает текущее состояние РБД на вкладке обратного вывода.
    def refresh_state(self):
        self.write_log("\n[РБД] " + (
            ", ".join(f"{format_display(k)}={format_display(v)}" for k, v in self.es.wm.items())
            or "<пусто>"), "sys")

    # Запускает обратный вывод: разбирает описание и цель, строит дерево доказательства.
    def run_backward(self):
        facts_text = self.facts_input.get("1.0", "end").strip()
        goal_raw = self.goal_entry.get().strip()

        extra_facts = ""
        goal = None
        if goal_raw:
            goal = self.es.parse_goal(goal_raw)
            if goal is None:
                # текст не распознан как цель (объект:значение или название книги) —
                # считаем его дополнительным описанием, а целью будет любая книга
                extra_facts = goal_raw

        if goal is None:
            goal = dict(self.es.goal) or {"рекомендация": "*"}

        combined_facts = "\n".join(p for p in (facts_text, extra_facts) if p)

        self.clear_log()
        self.write_log("[СИСТЕМА] Запуск обратной цепочки рассуждений.", "sys")

        parsed = self.es.parse_facts_text(combined_facts)
        if parsed:
            self.write_log("[СИСТЕМА] Распознанные факты из описания:", "sys")
            for k, v in parsed.items():
                self.write_log(f"   {format_display(k)} = {format_display(v)}", "fact")
        elif combined_facts:
            self.write_log("[СИСТЕМА] Факты не распознаны, используются начальные.", "warn")
        else:
            self.write_log("[СИСТЕМА] Используются начальные факты из initial_facts.json:", "sys")
            for k, v in self.es.initial_wm.items():
                self.write_log(f"   {format_display(k)} = {format_display(v)}", "fact")

        self.write_log("[СИСТЕМА] Цель: " + ", ".join(
            f"{format_display(k)} = {format_display(v)}" for k, v in goal.items()), "sys")

        result = self.es.run_backward_chaining(facts_text=combined_facts, goal=goal)

        self.write_log("\n[РБД] " + (
            ", ".join(f"{format_display(k)}={format_display(v)}" for k, v in result["wm"].items())
            or "<пусто>"), "sys")

        self.write_log("\n--- ДЕРЕВО ДОКАЗАТЕЛЬСТВА ---", "sys")
        for line in result["tree"]:
            self.write_log(line, "tree")

        if result["derived"]:
            self.write_log("\n--- ВЫВЕДЕННЫЕ ФАКТЫ ---", "sys")
            for k, v in result["derived"]:
                self.write_log(f"   + {format_display(k)} = {format_display(v)}", "fact")

        tag = "ok" if result["ok"] else "fail"
        self.write_log("\n" + "=" * 50, tag)
        self.write_log(f"РЕЗУЛЬТАТ: {result['status']}", tag)
        if result["ok"] and "рекомендация" in result["wm"]:
            self.write_log(f"Ответ: {result['wm']['рекомендация']}", tag)
        self.write_log("=" * 50, tag)


# Класс вкладки «База правил» для просмотра, добавления, редактирования и удаления правил экспертной системы.
class RulesTab(ttk.Frame):
    # Конструктор класса RulesTab: инициализирует таблицу правил и форму ввода с кнопками действий.
    def __init__(self, parent, es: ExpertSystem):
        super().__init__(parent, padding=10)
        self.es = es

        ttk.Label(self, text=f"База правил (файл: {os.path.basename(RULES_FILE)})").pack(anchor="w")
        self.count_label = ttk.Label(self, text="")
        self.count_label.pack(anchor="w")

        cols = ("id", "if", "then")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=14)
        self.tree.heading("id",   text="ID")
        self.tree.heading("if",   text="ЕСЛИ")
        self.tree.heading("then", text="ТО")
        self.tree.column("id",   width=50, anchor="center")
        self.tree.column("if",   width=400)
        self.tree.column("then", width=300)
        self.tree.pack(fill="both", expand=True, pady=(6, 10))

        form = ttk.LabelFrame(self, text="Управление правилом", padding=8)
        form.pack(fill="x")

        ttk.Label(form, text="ЕСЛИ (через запятую, формат объект: значение):").grid(row=0, column=0, sticky="w")
        self.if_entry = ttk.Entry(form, width=80)
        self.if_entry.grid(row=1, column=0, columnspan=4, sticky="we", pady=(0, 6))

        ttk.Label(form, text="ТО (формат объект: значение):").grid(row=2, column=0, sticky="w")
        self.then_entry = ttk.Entry(form, width=80)
        self.then_entry.grid(row=3, column=0, columnspan=4, sticky="we", pady=(0, 6))

        ttk.Button(form, text="Добавить", command=self.add_rule).grid(row=4, column=0, sticky="w")
        ttk.Button(form, text="Изменить выбранное", command=self.edit_selected).grid(row=4, column=1, sticky="w", padx=6)
        ttk.Button(form, text="Удалить выбранное", command=self.delete_selected).grid(row=4, column=2, sticky="w", padx=6)
        ttk.Button(form, text="Обновить", command=self.refresh).grid(row=4, column=3, sticky="w")

        self.refresh()

    # Перезагружает и отображает актуальный список правил из базы в таблице Treeview.
    def refresh(self):
        self.es.load_rules()
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        for r in self.es.rules:
            if_str = " И ".join(f"{format_display(k)}='{format_display(v)}'" for k, v in r["if"].items())
            then_str = ", ".join(f"{format_display(k)}='{format_display(v)}'" for k, v in r["then"].items())
            self.tree.insert("", "end", values=(r["id"], if_str, then_str))
        self.count_label.config(text=f"Правил в базе: {len(self.es.rules)}")
        if not self.es.rules:
            self.tree.insert("", "end", values=("-", "База правил пуста или файл не найден", str(RULES_FILE)))

    # Парсит и валидирует тексты из полей ввода 'ЕСЛИ' и 'ТО', преобразуя их в словари.
    def _parse_inputs(self):
        raw_if = self.if_entry.get().strip()
        raw_then = self.then_entry.get().strip()

        if not raw_if or not raw_then:
            messagebox.showwarning("Заполните поля", "Нужно указать и условие ЕСЛИ, и вывод ТО.")
            return None, None

        if_dict = {}
        for part in raw_if.split(","):
            part = part.strip()
            if not part:
                continue
            if ":" not in part:
                messagebox.showerror("Ошибка формата", f"Во фрагменте «{part}» нет двоеточия.")
                return None, None
            k, v = part.split(":", 1)
            if_dict[normalize(k)] = normalize(v)

        if not if_dict:
            messagebox.showerror("Ошибка", "Условие ЕСЛИ пустое.")
            return None, None

        if ":" not in raw_then:
            messagebox.showerror("Ошибка формата", "Поле ТО должно быть в формате «объект: значение».")
            return None, None
        k, v = raw_then.split(":", 1)
        then_dict = {normalize(k): v.strip()}

        return if_dict, then_dict

    # Считывает введенные параметры, создает новое правило с уникальным ID и сохраняет его в файл.
    def add_rule(self):
        if_dict, then_dict = self._parse_inputs()
        if if_dict is None:
            return

        new_id = max([r["id"] for r in self.es.rules], default=0) + 1
        self.es.rules.append({"id": new_id, "if": if_dict, "then": then_dict})
        self.es.save_rules()

        self.if_entry.delete(0, "end")
        self.then_entry.delete(0, "end")
        self.refresh()
        messagebox.showinfo("Готово", f"Правило №{new_id} добавлено.")

    def edit_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Не выбрано", "Выберите правило в таблице для редактирования.")
            return

        rule_id = int(self.tree.item(sel[0], "values")[0])

        if_dict, then_dict = self._parse_inputs()
        if if_dict is None:
            return

        if self.es.edit_rule(rule_id, if_dict, then_dict):
            self.if_entry.delete(0, "end")
            self.then_entry.delete(0, "end")
            self.refresh()
            messagebox.showinfo("Готово", f"Правило №{rule_id} успешно изменено.")

    def delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Не выбрано", "Выберите правило в таблице для удаления.")
            return
        rule_id = int(self.tree.item(sel[0], "values")[0])
        if not messagebox.askyesno("Удаление", f"Удалить правило №{rule_id}?"):
            return
        self.es.rules = [r for r in self.es.rules if r["id"] != rule_id]
        self.es.save_rules()
        self.refresh()


# Класс вкладки «Состояние РБД» для отображения списка текущих фактов в рабочей базе данных.
class StateTab(ttk.Frame):
    # Конструктор класса StateTab: настраивает таблицу отображения объектов и их значений из РБД.
    def __init__(self, parent, es: ExpertSystem):
        super().__init__(parent, padding=10)
        self.es = es

        ttk.Label(self, text="Текущие факты в рабочей базе данных (РБД):").pack(anchor="w", pady=(0, 6))

        cols = ("object", "value")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=15)
        self.tree.heading("object", text="Объект")
        self.tree.heading("value", text="Значение")
        self.tree.column("object", width=350)
        self.tree.column("value", width=350)
        self.tree.pack(fill="both", expand=True)

        ttk.Button(self, text="Обновить состояние", command=self.refresh).pack(anchor="e", pady=8)
        self.refresh()

    # Заполняет таблицу (парами объект-значение) из рабочей памяти системы.
    def refresh(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        if not self.es.wm:
            self.tree.insert("", "end", values=("<база пуста>", "<нет данных>"))
        else:
            for k, v in self.es.wm.items():
                self.tree.insert("", "end", values=(format_display(k), format_display(v)))    

if __name__ == "__main__":
    App().mainloop()