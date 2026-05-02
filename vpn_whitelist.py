#!/usr/bin/env python3
description = 'Скрипт для переформатирования списка IP/доменов в фомат для популярных VPN приложений с возможностью создания списка IP адресов на основе списка доменов и наоборот.'
import requests, socket, os

FORMATS = {
    "AmneziaVPN (ips & domains)": {
        "separate_lists": False,
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname": "{domain}", "ip": "{ip}" }}',
        "line_separator": ',\n'
    },
    "AmneziaVPN (ips only)": {
        "separate_lists": True,
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname":  "", "ip": "{ip_or_domain}" }}',
        "line_separator": ',\n'
    },
    "AmneziaVPN (domains only)": {
        "separate_lists": True,
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname":  "{ip_or_domain}", "ip": "" }}',
        "line_separator": ',\n'
    },
    "v2rayNG (domains only)": {
        "separate_lists": True,
        "file_format": '[{"domain":[{all_lines}],"enabled":true,"ip":[],"locked":false,"outboundTag":"direct","remarks":"whitelist domains"}]',
        "line_format": '"{ip_or_domain}"',
        "line_separator": ','
    },
    "v2rayNG (ips only)": {
        "separate_lists": True,
        "file_format": '[{"domain":[],"enabled":true,"ip":[{all_lines}],"locked":false,"outboundTag":"direct","remarks":"whitelist ips"}]',
        "line_format": '"{ip_or_domain}"',
        "line_separator": ','
    },
    "Happ": {
        "separate_lists": True,
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": ','
    },
    "NekoBox (Windows)": {
        "separate_lists": True,
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": '\n'
    }
}

# ==============================

def open_file(path_or_url): # return: list or None
    if path_or_url == '' or not path_or_url: return None
    try:
        if path_or_url.startswith('http'):
            print(f'[i] Загрузка файла с URL {path_or_url} ... ',end="")
            response = requests.get(path_or_url, timeout=1)
            response.raise_for_status()
            result = response.text
        elif path_or_url:
            print(f'[i] Открытие файла {path_or_url} ... ',end="")
            with open(path_or_url, "r", encoding="utf-8-sig") as f:
                result = f.read()
        else: return
        print('OK')
        return [ item.strip() for line in result.splitlines() for item in line.split(",") if item.strip()]
    except FileNotFoundError: print(f'[E] Файл {path_or_url} не найден!')
    except requests.exceptions.MissingSchema as e: print(f'[E] Неверный URL: {e}')
    except requests.exceptions.HTTPError as e: print(f'[E] Неверный URL: {e}')
    except requests.exceptions.ConnectionError as e: print(f'[E] Ошибка подключения к URL: {e}')
    
def write_file(data,filename):
    counter=1
    while os.path.exists(filename):
        filename = f"{filename.rsplit(".", 1)[0]} ({counter}).{filename.rsplit(".", 1)[1]}"
        counter += 1
    print(f'[i] Запись в файл "{filename}" ... ',end="")
    with open(filename, "w") as f:
        f.write(str(data))
        print('OK')

def ip_domain(domain=None, ip=None):
    try:
        if ip is not None: 
            if not set(ip) <= set("0123456789."): return print(f'Неверный формат IP: {ip}')
            hostname, _, _ = socket.gethostbyaddr(ip)
            return ip, hostname
        elif domain is not None: 
            ip = socket.gethostbyname(domain)
            return ip, domain
        else: return None, None
    except socket.herror:
        print(f'Ошибка получения домена для IP {ip}')
        return None, None
    except socket.gaierror:
        print(f'Ошибка получения IP для домена {domain}')
        return None, None
    
def main(input_list, input_list_type, output_format, output_list_type=None, check_ip_domain=False):
    if not output_list_type: output_list_type = input_list_type
    list_total = len(input_list)
    print(f'\n[i] Исходные данные: список {input_list_type} ({list_total} строк), итоговый формат: список {output_list_type} для {output_format}')

    if input_list_type == output_list_type:
        print(f'[i] Форматирование исходных данных в формат {output_format}')
        if check_ip_domain: 
            print(f'[!] Проверка соотношения IP и доменов принудительно отключена, т.к. итоговый формат ({output_list_type}) совпадает с исходным ({input_list_type})')
            check_ip_domain = False
    else:
        print(f'[i] Преобразование списка {input_list_type} в список {output_list_type} с форматом {output_format}')
        if not check_ip_domain:
            print(f'[!] Проверка соотношения IP и доменов принудительно включена, т.к. итоговый формат ({output_list_type}) отличается от исходного ({input_list_type})')
            check_ip_domain = True

    format = FORMATS[output_format]
    if not format["separate_lists"] and not check_ip_domain:
        print(f'[!] Проверка соотношения IP и доменов принудительно включена, т.к. формат {output_format} должен содержать IP и домены в одном списке')
        check_ip_domain = True

    output_result = []
    errors = []
    print('[i] Обработка списка ... ',end="")
    for number, ip_or_domain in enumerate(input_list, start=1):
        ip_or_domain = ip_or_domain.strip()
        if (not ip_or_domain) or ip_or_domain.startswith("#"): continue
        print(f"\r{' ' * 90}\r[i] [{number}/{list_total}] обработка: {ip_or_domain} ... ",end="")

        if check_ip_domain:
            if input_list_type == 'ip': 
                ip, domain = ip_domain(ip=ip_or_domain)
            elif input_list_type == 'domains': 
                ip, domain = ip_domain(domain=ip_or_domain)
            if (not ip) or (not domain): 
                errors.append(ip_or_domain)
                continue
            if format["separate_lists"]:
                if output_list_type == 'ip':
                    line = format["line_format"].format(ip_or_domain=ip)
                if output_list_type == 'domains':
                    line = format["line_format"].format(ip_or_domain=domain)
            else: line = format["line_format"].format( domain=domain, ip=ip )
        else: line = format["line_format"].format(ip_or_domain=ip_or_domain)
        output_result.append(line)
    
    print(f"\r{' ' * 50}\r[i] Обработка списка завершена")
    if errors: 
        if input(f'Ошибок: {len(errors)}. Сохранить список? (y|n): ').strip().lower() in ("y", "yes", "1", "д", "да"):
            write_file(errors,f'whitelist {input_list_type} errors.txt')
    result = format["file_format"].format(all_lines=format["line_separator"].join(output_result))
    return result

if __name__ == "__main__":
    print(description,'\n')
    input_ip_list = None
    input_domain_list = None

    while not (input_ip_list or input_domain_list): 
        input_ip_list = open_file(input("Список IP адресов (URL|PATH|None): "))
        input_domain_list = open_file(input("Список доменов (URL|PATH|None): "))
        if not (input_ip_list or input_domain_list): print('[i] Введите хотя бы один источник данных!',end="\n\n")
    
    output_format = 0
    output_formats = list(FORMATS.keys())
    while isinstance(output_format, int): 
        print('')
        for i, name in enumerate(output_formats, start=1): print(f" {i} : {name}")
        output_format = int(input("Выберите итоговый формат: "))
        if output_format < 1 or output_format > len(output_formats): print("[E] Неверное значение!")
        else: output_format = output_formats[output_format - 1]

    cross_check = input('\nСоздать ли список IP на основе списка доменов и/или список доменов на основе списка IP (y|n): ').strip().lower() in ("y", "yes", "1", "д", "да")

    if input_ip_list: 
        result = main(input_ip_list, 'ip', output_format)
        write_file(result, f'whitelist ip for {output_format}.txt')
        if cross_check: 
            result = main(input_ip_list, 'ip', output_format, 'domains')
            write_file(result, f'whitelist domains (ip based) for {output_format}.txt')

    if input_domain_list: 
        result = main(input_domain_list, 'domains', output_format)
        write_file(result, f'whitelist domains for {output_format}.txt')
        if cross_check: 
            result = main(input_domain_list, 'domains', output_format, 'ip')
            write_file(result, f'whitelist ip (domains based) for {output_format}.txt')

    print('[i] Завершено!')
