import sys
import subprocess
import os
from datetime import datetime

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Нумерация
existing = [f for f in os.listdir(LOG_DIR) if f.startswith("log_") and f.endswith(".txt")]
numbers = []
for f in existing:
    try:
        num = int(f.split("_")[1])
        numbers.append(num)
    except:
        pass
counter = max(numbers) + 1 if numbers else 1

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = os.path.join(LOG_DIR, f"log_{counter}_{timestamp}.log")  # лучше .txt, а не .log

print(f"=== ЗАПУСК main.py ===")
print(f"Лог сохраняется в: {log_filename}")
print("Вывод в реальном времени:\n")

# Окружение с принудительным UTF-8
env = os.environ.copy()
env["PYTHONUNBUFFERED"] = "1"           # без буферизации
env["PYTHONIOENCODING"] = "utf-8"       # КЛЮЧ: заставляем Python использовать UTF-8 для stdout/stderr
env["LANG"] = "en_US.UTF-8"             # дополнительно помогает

# Запуск процесса
process = subprocess.Popen(
    [sys.executable, "-u", "main.py"] + sys.argv[1:],  # -u = unbuffered
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    encoding="utf-8",              # читаем как UTF-8
    errors="replace",              # на случай редких ошибок — заменяем �
    bufsize=0,
    env=env
)

with open(log_filename, "w", encoding="utf-8") as log_file:
    log_file.write(f"=== Лог от {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n")
    
    try:
        for line in process.stdout:
            print(line, end="")          # в твою консоль (уже в правильной кодировке)
            log_file.write(line)
            log_file.flush()
        
        process.wait()
        return_code = process.returncode
        
    except Exception as e:
        error_msg = f"\nОШИБКА: {e}\n"
        print(error_msg)
        log_file.write(error_msg)
        return_code = -1
    
    final_msg = f"\n=== main.py завершился с кодом {return_code} ===\n"
    print(final_msg)
    log_file.write(final_msg)

print(f"\nЛог полностью сохранён: {log_filename}")