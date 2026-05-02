#!/usr/bin/env python3
description = 'Скрипт для переформатирования списка IP/доменов в фомат для популярных VPN приложений с возможностью создания списка IP адресов на основе списка доменов и наоборот.'
import requests, socket, os

FORMATS = { # "format_need_only": 'ip' | 'domain' | 'one' | False
    "AmneziaVPN": {
        "format_need_only": 'one',
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname":  "{ip_or_domain}", "ip": "" }}',
        "line_separator": ',\n'
    },
    "AmneziaVPN (domains & ips)": {
        "format_need_only": False,
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname": "{domain}", "ip": "{ip}" }}',
        "line_separator": ',\n'
    },
    "v2rayNG (domains only)": {
        "format_need_only": 'domain',
        "file_format": '[{{"domain":[{all_lines}],"enabled":true,"ip":[],"locked":false,"outboundTag":"direct","remarks":"whitelist domains"}}]',
        "line_format": '"{domain}"',
        "line_separator": ','
    },
    "v2rayNG (ips only)": {
        "format_need_only": 'ip',
        "file_format": '[{{"domain":[],"enabled":true,"ip":[{all_lines}],"locked":false,"outboundTag":"direct","remarks":"whitelist ips"}}]',
        "line_format": '"{ip}"',
        "line_separator": ','
    },
    "Happ (ips only)": {
        "format_need_only": 'ip',
        "file_format": '{all_lines}',
        "line_format": '{ip}',
        "line_separator": ','
    },
    "NekoBox (Windows)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": '\n'
    },
    "Простой список (через перенос строк)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": '\n'
    },
    "Простой список (через запятую)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": ','
    },
    "Простой список (через запятую, в кавычках)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '"{ip_or_domain}"',
        "line_separator": ','
    }
}

# ==============================

def open_file(path_or_url): # return: list or None
    if path_or_url == '' or not path_or_url: return None
    try:
        if path_or_url.startswith('http'):
            print(f'[i] Загрузка файла с URL {path_or_url} ... ',end="")
            response = requests.get(path_or_url, timeout=30)
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
    except requests.exceptions.ReadTimeout as e: print(f'[E] Загрузка с URL прервана по таймауту')
    
def write_file(data,filename):
    file_name, file_ext = os.path.splitext(filename)
    counter = 1
    while os.path.exists(filename):
        filename = f"{file_name} ({counter}){file_ext}"
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
            allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.")
            if not bool(domain) and all(c in allowed for c in domain): return ip, domain
            ip = socket.gethostbyname(domain)
            return ip, domain
        else: return None, None
    except socket.herror as e:
        print(f'Ошибка получения домена для IP {ip} : {e}')
        return None, None
    except socket.gaierror as e:
        print(f'Ошибка получения IP для домена {domain} : {e}')
        return None, None
    
def main(input_list, input_list_type, output_format, output_list_type=None):
    if not output_list_type: output_list_type = input_list_type
    list_total = len(input_list)
    print(f'\n[i] Исходные данные: список {input_list_type} ({list_total} строк), итоговый формат: список {output_list_type} для {output_format}')
    format = FORMATS[output_format]
    if not format["format_need_only"]:
        print(f'[i] Проверка соотношения IP и доменов включена, т.к. формат {output_format} должен содержать IP и домены в одном списке')

    output_result = []
    errors = []
    print('[i] Обработка списка ... ',end="")
    for number, ip_or_domain in enumerate(input_list, start=1):
        ip_or_domain = ip_or_domain.strip()
        ip = None
        domain = None
        if (not ip_or_domain) or ip_or_domain.startswith("#"): continue
        print(f"\r{' ' * 90}\r[i] [{number}/{list_total}] обработка: {ip_or_domain} ... ",end="")

        if not format["format_need_only"] or input_list_type != output_list_type:
            if input_list_type == 'ip': 
                ip, domain = ip_domain(ip=ip_or_domain)
            elif input_list_type == 'domain': 
                ip, domain = ip_domain(domain=ip_or_domain)
            if (not ip) or (not domain): 
                errors.append(ip_or_domain)
                continue
        if not format["format_need_only"]:
            line = format["line_format"].format(domain=domain, ip=ip)
        elif format["format_need_only"] == 'ip' or ():
            line = format["line_format"].format(ip=(ip or ip_or_domain))
        elif format["format_need_only"] == 'domain':
            line = format["line_format"].format(domain=(domain or ip_or_domain))
        elif format["format_need_only"] == 'one':
            if output_list_type == 'ip': line = format["line_format"].format(ip_or_domain=(ip or ip_or_domain))
            if output_list_type == 'domain':line = format["line_format"].format(ip_or_domain=(domain or ip_or_domain))

        output_result.append(line)
    
    print(f"\r{' ' * 100}\r[i] Обработка списка завершена")
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

    format = FORMATS[output_format]

    if input_ip_list: 
        if format["format_need_only"] != 'domain':
            result = main(input_ip_list, 'ip', output_format)
            write_file(result, f'whitelist ip for {output_format}.txt')
        if format["format_need_only"] == 'one' or format["format_need_only"] == 'domain':
            if input('\nСоздать ли список доменов на основе списка IP (y|n): ').strip().lower() in ("y", "yes", "1", "д", "да"):
                result = main(input_ip_list, 'ip', output_format, 'domain')
                write_file(result, f'whitelist domains (ip based) for {output_format}.txt')

    if input_domain_list: 
        if format["format_need_only"] != 'ip':
            result = main(input_domain_list, 'domain', output_format)
            write_file(result, f'whitelist domains for {output_format}.txt')
        if format["format_need_only"] == 'one' or format["format_need_only"] == 'ip':
            if input('\nСоздать ли список IP на основе списка доменов (y|n): ').strip().lower() in ("y", "yes", "1", "д", "да"):
                result = main(input_domain_list, 'domain', output_format, 'ip')
                write_file(result, f'whitelist ip (domains based) for {output_format}.txt')

    print('\n[i] Завершено!')
