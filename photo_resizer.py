import os
from PIL import Image

pxl_y= 600 # ширина 
pxl_x= 600 # высота

print('Использование:\n1. Поместите этот скрипт рядом с папкой с фотографиями')
folder_name = input("2. Введите название папки с фотографиями: ").strip()
input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)

while not os.path.isdir(input_folder):
    print("[!] Ошибка: такой папки нет.")
    folder_name = input("2. Введите название папки с фотографиями: ").strip()
    input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), folder_name)

extensions = (".jpg", ".jpeg", ".png")

files = [f for f in os.listdir(input_folder) if f.lower().endswith(extensions)]
files_not_allowed = [f for f in os.listdir(input_folder) if not f.lower().endswith(extensions)]
total_files = len(files)

errors=[]

if total_files == 0:
    print(f"[!] В папке нет фото подходящих форматов {extensions}.")
    input('Для выхода нажмиите Enter ')
    exit()

print(f"3. {total_files} файлов подходящих форматов {extensions} будут подогнаны под размер {pxl_x} на {pxl_y}.")

if files_not_allowed: 
    print('\nСледующие файлы с неподходящими форматами НЕ будут обработаны:')
    for f in files_not_allowed: print(f'  {f}')

input('\nДля продолжения нажмиите Enter ')

os.makedirs(input_folder+'_resized', exist_ok=True)
# Обработка изображений
for i, filename in enumerate(files, start=1):
    file_path = os.path.join(input_folder, filename)
    try:
        with Image.open(file_path) as img: 
            if img.mode == "RGBA":  # убираем прозрачность 
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])  
                img = background
            else:
                img = img.convert("RGB")  # всегда в RGB для JPEG
            img.thumbnail((pxl_y, pxl_x), Image.LANCZOS) # уменьшаем с сохранением пропорций
            background = Image.new("RGB", (pxl_y, pxl_x), (255, 255, 255)) # создаём белый холст 
            offset = ((pxl_y - img.width) // 2, (pxl_x - img.height) // 2) # вычисляем координаты для центрирования
            background.paste(img, offset) # вставляем картинку по центру
            background.save(os.path.join(input_folder + '_resized', filename)) # сохраняем в новую папку

        print(f"[{i}/{total_files}] [OK] {filename}")
    except Exception as e:
        print(f"[{i}/{total_files}] [!] Ошибка обработки {filename}: {e}")
        errors.append(filename)
        errors.append(e)

print(f"\nОбработано {total_files} файлов подходящих форматов.")
print(f"Файлы сохранены в папке {input_folder+'_resized'} .")
if errors:
    print('\nОшибки обработки: ')
    for i, e in enumerate(errors):
        if i%2 == 0 or i==0:
            print(f'  Файл: {e} , ошибка: {errors[i+1]}')

if files_not_allowed: 
    print('\nСледующие файлы с неподходящими форматами не были обработаны:')
    for f in files_not_allowed: print(f'  {f}')

input('\nДля выхода нажмиите Enter ')