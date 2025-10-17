#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import threading
import time
import random
import webbrowser
import json
import os
from datetime import datetime
from flask import Flask, render_template, request, jsonify
import platform

class BashTrainerPro:
    def __init__(self):
        self.data_file = "trainer_data.json"
        self.settings_file = "trainer_settings.json"
        self.commands_file = "commands.json"
        self.commands = self.load_commands_from_file()
        self.current_reminder = None
        self.settings = self.load_settings()
        self.stats = self.load_stats()
        self.command_history = []
        self.manual_skip = False
        
    def load_commands_from_file(self):
        """Загружаем команды из JSON файла"""
        try:
            with open(self.commands_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"✅ Загружено {len(data.get('commands', []))} команд")
                return data.get('commands', [])
        except FileNotFoundError:
            print(f"❌ Файл {self.commands_file} не найден!")
            return []
        except json.JSONDecodeError:
            print(f"❌ Ошибка в формате файла {self.commands_file}!")
            return []
    
    def load_settings(self):
        """Загружаем настройки"""
        default_settings = {
            "reminder_interval": 300,  # 5 минут в секундах
            "sound_enabled": True,
            "auto_advance": True
        }
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
                # Объединяем с настройками по умолчанию
                return {**default_settings, **user_settings}
        except FileNotFoundError:
            print("⚙️  Файл настроек не найден, используются настройки по умолчанию")
            return default_settings
        except json.JSONDecodeError:
            print("❌ Ошибка в формате файла настроек!")
            return default_settings
    
    def save_settings(self):
        """Сохраняем настройки"""
        with open(self.settings_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
    
    def load_stats(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {"completed": [], "attempts": {}, "last_completion": {}}
    
    def save_stats(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, indent=2, ensure_ascii=False)
    
    def update_settings(self, new_settings):
        """Обновляем настройки"""
        self.settings.update(new_settings)
        self.save_settings()
        print("⚙️  Настройки обновлены:", self.settings)
    
    def mark_completed(self, command, play_sound=False):
        """Отметить команду как выполненную"""
        if command not in self.stats["completed"]:
            self.stats["completed"].append(command)
        
        self.stats["attempts"][command] = self.stats["attempts"].get(command, 0) + 1
        self.stats["last_completion"][command] = datetime.now().isoformat()
        self.save_stats()
        
        # После отметки как выполненной - сразу показываем новую команду
        self.get_new_reminder(play_sound=play_sound)
    
    def get_new_reminder(self, play_sound=True):
        """Получить новое задание"""
        if not self.commands:
            return None
            
        available_commands = [cmd for cmd in self.commands if cmd["command"] not in self.stats["completed"]]
        
        if not available_commands:
            # Все команды выполнены
            print("🎉 Все команды изучены! Вы великолепны!")
            self.current_reminder = {
                "command": "ПОЗДРАВЛЯЕМ!",
                "description": "Вы изучили все команды курса!",
                "example": "Можете повторить пройденное или добавить новые команды",
                "category": "Завершение",
                "difficulty": "легкая",
                "flags": "🎓",
                "output_example": "Вы стали экспертом в командах Linux!",
                "analysis": "Продолжайте практиковаться и изучать новые команды!"
            }
            return self.current_reminder
        
        # Выбираем случайную команду из доступных
        self.current_reminder = random.choice(available_commands)
        self.add_to_history(self.current_reminder)
        
        if play_sound and self.settings["sound_enabled"]:
            self.play_sound()
        
        print(f"\n🎯 НОВОЕ ЗАДАНИЕ ({datetime.now().strftime('%H:%M:%S')})")
        print(f"💻 Команда: {self.current_reminder['command']}")
        print(f"📝 Описание: {self.current_reminder['description']}")
        print(f"🔧 Категория: {self.current_reminder['category']}")
        print("-" * 60)
        
        return self.current_reminder
    
    def add_to_history(self, command):
        """Добавляем команду в историю"""
        # Убираем дубликаты
        self.command_history = [cmd for cmd in self.command_history if cmd["command"] != command["command"]]
        # Добавляем в начало
        self.command_history.insert(0, command)
        # Ограничиваем историю
        self.command_history = self.command_history[:10]
    
    def play_sound(self):
        """Кросс-платформенный звук"""
        try:
            if platform.system() == "Windows":
                import winsound
                winsound.Beep(1000, 500)
            else:
                # Для Linux/Mac
                os.system('echo -e "\\a"')
        except:
            print("\a")  # Fallback

    def start_reminders(self):
        """Запуск автоматических напоминаний"""
        def reminder_loop():
            while True:
                if self.commands and not self.manual_skip and self.settings["auto_advance"]:
                    self.get_new_reminder(play_sound=self.settings["sound_enabled"])
                
                self.manual_skip = False  # Сбрасываем флаг после ожидания
                time.sleep(self.settings["reminder_interval"])
        
        thread = threading.Thread(target=reminder_loop, daemon=True)
        thread.start()

app = Flask(__name__)
trainer = BashTrainerPro()

@app.route('/')
def index():
    # Если нет текущего задания, создаем первое
    if not trainer.current_reminder and trainer.commands:
        trainer.get_new_reminder(play_sound=False)
    
    return render_template('index.html',
                         current_reminder=trainer.current_reminder,
                         commands=trainer.commands,
                         stats=trainer.stats,
                         settings=trainer.settings,
                         command_history=trainer.command_history)

@app.route('/mark_completed', methods=['POST'])
def mark_completed():
    data = request.get_json()
    command = data['command']
    
    # Отмечаем как выполненную БЕЗ звука
    trainer.mark_completed(command, play_sound=False)
    
    return jsonify({"status": "success", "message": f"Команда {command} отмечена как выполненная"})

@app.route('/play_sound')
def play_sound():
    trainer.play_sound()
    return jsonify({"status": "sound_played"})

@app.route('/skip_reminder')
def skip_reminder():
    # Устанавливаем флаг ручного переключения
    trainer.manual_skip = True
    # Получаем новое задание БЕЗ звука
    trainer.get_new_reminder(play_sound=False)
    
    return jsonify({"status": "skipped", "message": "Новое задание загружено"})

@app.route('/update_settings', methods=['POST'])
def update_settings():
    data = request.get_json()
    
    # Конвертируем значения
    if 'reminder_interval' in data:
        data['reminder_interval'] = int(data['reminder_interval'])
    if 'sound_enabled' in data:
        data['sound_enabled'] = bool(data['sound_enabled'])
    if 'auto_advance' in data:
        data['auto_advance'] = bool(data['auto_advance'])
    
    trainer.update_settings(data)
    
    return jsonify({"status": "success", "message": "Настройки обновлены", "settings": trainer.settings})

@app.route('/reset_progress', methods=['POST'])
def reset_progress():
    """Сбросить весь прогресс"""
    trainer.stats = {"completed": [], "attempts": {}, "last_completion": {}}
    trainer.save_stats()
    trainer.get_new_reminder(play_sound=False)
    
    return jsonify({"status": "success", "message": "Прогресс сброшен"})

def main():
    # Проверяем загрузку команд
    if not trainer.commands:
        print("❌ Не удалось загрузить команды из commands.json")
        return
    
    # Запускаем автоматические напоминания
    trainer.start_reminders()
    
    print("🚀 Запуск Bash Trainer Pro...")
    print("📖 Веб-интерфейс: http://localhost:5000")
    print("📚 Всего команд для изучения:", len(trainer.commands))
    print("⚙️  Текущие настройки:")
    print(f"   • Интервал: {trainer.settings['reminder_interval']} сек ({trainer.settings['reminder_interval']//60} мин)")
    print(f"   • Звук: {'ВКЛ' if trainer.settings['sound_enabled'] else 'ВЫКЛ'}")
    print(f"   • Автопереход: {'ВКЛ' if trainer.settings['auto_advance'] else 'ВЫКЛ'}")
    print("⏹️  Для остановки: Ctrl+C")
    print("\n" + "="*50)
    
    try:
        app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()