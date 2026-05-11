#!/usr/bin/env python3
# by kompot69
description = 'Скрипт для переформатирования списка IP/доменов в фомат для популярных VPN приложений с возможностью создания списка IP адресов на основе списка доменов и наоборот. '
import requests, socket, os, time

FORMATS = { # "format_need_only": 'ip' | 'domain' | 'one' | False
    "AmneziaVPN": {
        "format_need_only": 'one',
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname":  "{ip_or_domain}", "ip": "" }}',
        "line_separator": ',\n',
        "file_extension": 'json'
    },
    "AmneziaVPN (domains & ips)": {
        "format_need_only": False,
        "file_format": '[\n{all_lines}\n]',
        "line_format": '    {{ "hostname": "{domain}", "ip": "{ip}" }}',
        "line_separator": ',\n',
        "file_extension": 'json'
    },
    "v2rayNG (domains only)": {
        "format_need_only": 'domain',
        "file_format": '[{{"domain":[{all_lines}],"enabled":true,"ip":[],"locked":false,"outboundTag":"direct","remarks":"whitelist domains"}}]',
        "line_format": '"{domain}"',
        "line_separator": ',',
        "file_extension": 'txt'
    },
    "v2rayNG (ips only)": {
        "format_need_only": 'ip',
        "file_format": '[{{"domain":[],"enabled":true,"ip":[{all_lines}],"locked":false,"outboundTag":"direct","remarks":"whitelist ips"}}]',
        "line_format": '"{ip}"',
        "line_separator": ',',
        "file_extension": 'txt'
    },
    "Happ (ips only)": {
        "format_need_only": 'ip',
        "file_format": '{all_lines}',
        "line_format": '{ip}',
        "line_separator": ',',
        "file_extension": 'txt'
    },
    "NekoBox (Windows)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": '\n',
        "file_extension": 'txt'
    },
    "Простой список (через перенос строк)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": '\n',
        "file_extension": 'txt'
    },
    "Простой список (через запятую)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '{ip_or_domain}',
        "line_separator": ',',
        "file_extension": 'txt'
    },
    "Простой список (через запятую, в кавычках)": {
        "format_need_only": 'one',
        "file_format": '{all_lines}',
        "line_format": '"{ip_or_domain}"',
        "line_separator": ',',
        "file_extension": 'txt'
    }
}
IP_ALLOWED_LETTERS='0123456789.'
DOMAIN_ALLOWED_LETTERS='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.'
SUPPORTED_SEPARATORS=',;'

SUBURL_SCRIPT_PATH='subURL_parser.py'
SUBURL_PARSE_TIMEOUT_SEC=60
ACCEPT_KEYS=("y", "yes", "1", "д", "да")
# ==============================

last_print = ''
def print_from(last_point=None, start=None, ended=False):
    global last_print
    if ended == False: 
        ended = ''
        last_print += (last_point or start)
    elif ended == True: 
        ended = '\n'
        last_print = ''
    else: 
        ended = ended
        last_print = ''
    if last_point:
        print(last_point, end=ended, flush=True)
    elif start:
        print(f"\033[{len(last_print)}D{start}", end=ended, flush=True)

def open_file(path_or_url, content_type=None): # return: list or None
    if path_or_url == '' or not path_or_url: return None
    try:
        if path_or_url.startswith('http'):
            print(f'[i] Загрузка файла с URL ... ',end="", flush=True)
            response = requests.get(path_or_url, timeout=30)
            response.raise_for_status()
            result = response.text
        elif path_or_url:
            print(f'[i] Открытие файла ... ',end="", flush=True)
            with open(path_or_url, "r", encoding="utf-8-sig") as f:
                result = f.read()
        else: return
        print('OK. ',end="", flush=True)
        for sep in SUPPORTED_SEPARATORS: result = result.replace(sep, '\n')
        result = [line.strip() for line in result.splitlines() if line.strip()]
        if content_type:
            print('Проверка формата ... ',end="", flush=True)
            if content_type == 'ip': allowed = IP_ALLOWED_LETTERS
            if content_type == 'domain': allowed = DOMAIN_ALLOWED_LETTERS
            for line in result:
                if not all(c in allowed for c in line): return print(f'неверный формат! (строка: {line})')
            print('OK.')
        return result
    except FileNotFoundError: print(f'[E] Файл {path_or_url} не найден!')
    except (requests.exceptions.MissingSchema, requests.exceptions.HTTPError) as e: print(f'[E] Неверный URL: {e}')
    except requests.exceptions.ConnectionError as e: print(f'[E] Ошибка подключения к URL: {e}')
    except requests.exceptions.ReadTimeout as e: print(f'[E] Загрузка с URL прервана по таймауту')
    
def write_file(data, file_name, file_ext='txt'):
    filename = f"{file_name}.{file_ext}"
    counter = 1
    while os.path.exists(filename):
        filename = f"{file_name} ({counter}).{file_ext}"
        counter += 1
    print(f'[i] Запись в файл "{filename}" ... ',end="", flush=True)
    try:
        with open(filename, "w") as f:
            f.write(str(data))
            print('OK', flush=True)
    except Exception as e: print(f'ошибка: {e}', flush=True)

def ip_domain(domain=None, ip=None):
    try:
        if ip is not None: 
            if not set(ip) <= set(IP_ALLOWED_LETTERS): 
                print(f'Неверный формат IP: {ip}', flush=True)
                return ip, domain 
            hostname, _, _ = socket.gethostbyaddr(ip)
            return ip, hostname
        elif domain is not None: 
            allowed = set(DOMAIN_ALLOWED_LETTERS)
            if not bool(domain) and all(c in allowed for c in domain): 
                print(f'Неверный формат домена: {domain}', flush=True)
                return ip, domain
            ip = socket.gethostbyname(domain)
            return ip, domain
        else: return None, None
    except socket.herror as e:
        print(f'Ошибка получения домена для IP: {e}', flush=True)
        return None, None
    except socket.gaierror as e:
        print(f'Ошибка получения IP для домена: {e}', flush=True)
        return None, None
    
def main(input_list, input_list_type, output_format, output_list_type=None, parse_subdomains=False):
    ATD = time.time()
    if parse_subdomains:
        if input_list_type != 'domain': 
            parse_subdomains=False
            print(f'[!] Парсинг зависимотей доменов отключен, т.к. формат входных данных - {input_list}', flush=True)
        else:
            try:
                import asyncio, sys, importlib.util
                spec = importlib.util.spec_from_file_location("parser_module", SUBURL_SCRIPT_PATH)
                module = importlib.util.module_from_spec(spec)
                sys.modules["parser_module"] = module
                spec.loader.exec_module(module)
            except ModuleNotFoundError: 
                parse_subdomains=False
                print(f'[!] Парсинг зависимотей доменов отключен, т.к. cкрипт парсинга ({SUBURL_SCRIPT_PATH}) не найден', flush=True)


    if not output_list_type: output_list_type = input_list_type
    list_total = len(input_list)
    print(f'\n[i] Исходные данные: список {input_list_type} ({list_total} строк), итоговый формат: список {output_list_type} для {output_format}', flush=True)
    format = FORMATS[output_format]
    if not format["format_need_only"]:
        print(f'[i] Проверка соотношения IP и доменов включена, т.к. формат {output_format} должен содержать IP и домены в одном списке', flush=True)

    output_result = []
    errors = []
    sub_errors = []
    print('[i] Обработка списка ... ',end="", flush=True)
    for number, ip_or_domain in enumerate(input_list, start=1):
        ip_or_domain = ip_or_domain.strip()
        ip = None
        domain = None
        if (not ip_or_domain) or ip_or_domain.startswith("#"): continue
        ETA = (list_total-number)*((time.time()-ATD)/number-1)
        if ETA//60>60: ETA = f"{ETA//60//60:.0f}h{ETA//60%60:.0f}m"
        elif ETA//60>1: ETA = f"{ETA//60:.0f}m{ETA%60:.0f}s"
        else: ETA = f"{ETA%60:.0f}s"
        print(f"\r{' ' * 200}\r[i] [{number}/{list_total} | {number/(list_total/100):.0f}% | ETA:{ETA}] Обработка: {ip_or_domain} ... ",end="", flush=True)

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
        elif format["format_need_only"] == 'ip':
            line = format["line_format"].format(ip=(ip or ip_or_domain))
        elif format["format_need_only"] == 'domain':
            line = format["line_format"].format(domain=(domain or ip_or_domain))
        elif format["format_need_only"] == 'one':
            if output_list_type == 'ip': line = format["line_format"].format(ip_or_domain=(ip or ip_or_domain))
            if output_list_type == 'domain':line = format["line_format"].format(ip_or_domain=(domain or ip_or_domain))

        output_result.append(line)
        print("OK.",end="", flush=True)

        if parse_subdomains:
            last_print=" Поиск зависимостей ..."
            print(last_print, end="", flush=True)
            try: 
                result = asyncio.run(module.scan(ip_or_domain, ipv6=False, without_ip=True, http=False, timeout_sec=SUBURL_PARSE_TIMEOUT_SEC))
                if not result: 
                    sub_errors.append(ip_or_domain)
                    continue

                total_subdomains=len(result["domains"])
                last_print=f"\033[{len(last_print)}D Найдено зависимостей: {total_subdomains}."
                print(last_print, end="", flush=True)
                for subnumber, subdomain in enumerate(result["domains"], start=1):
                    print(f"\033[{len(last_print)}D",end="", flush=True)
                    last_print=f' Обработка зависимостей: [{subnumber}/{total_subdomains}] {subdomain} ... '
                    print(f"{last_print}",end="", flush=True)
                    try:
                        if (not format["format_need_only"]) or format["format_need_only"]=='ip' or output_list_type=='ip':
                            subip, subdomain = ip_domain(domain=subdomain)
                            if (not subip) or (not subdomain): 
                                sub_errors.append(subdomain)
                                continue
                            
                        if not format["format_need_only"]:
                            line = format["line_format"].format(domain=subdomain, ip=subip)
                        elif format["format_need_only"] == 'ip':
                            line = format["line_format"].format(ip=subip)
                        elif format["format_need_only"] == 'domain':
                            line = format["line_format"].format(domain=subdomain)
                        elif format["format_need_only"] == 'one':
                            if output_list_type == 'ip': line = format["line_format"].format(ip_or_domain=subip)
                            if output_list_type == 'domain':line = format["line_format"].format(ip_or_domain=subdomain)
                        output_result.append(line)
                    except Exception as e: print(f'ошибка: {str(e).replace('\n',' ')}', flush=True)
            except Exception as e: print(f" ошибка: {str(e).replace('\n',' ')}", flush=True)

    ATAm = (time.time()-ATD)//60 
    ATAs = time.time()-ATD
    ATA = f"{ATAm:.0f} мин. {ATAs%60:.0f} сек." if ATAm>0 else f"{ATAs:.3f} сек."
    print(f"\r{' ' * 200}\r[i] Очистка повторяющихся значений ...", end="", flush=True)
    output_result = list(dict.fromkeys(output_result))
    errors = list(dict.fromkeys(errors))
    sub_errors = list(dict.fromkeys(sub_errors))
    print(f"\r{' ' * 200}\r[i] Обработка списка завершена за {ATA} Итого ресурсов: {len(output_result)} ")
    if errors or sub_errors: 
        if input(f'Ошибок: {len(errors)}, ошибок вторичных доменов: {len(sub_errors)}. Сохранить список? (y|n): ').strip().lower() in ACCEPT_KEYS:
            write_file([errors,sub_errors],f'whitelist {input_list_type} errors')
    result = format["file_format"].format(all_lines=format["line_separator"].join(output_result))
    return result

if __name__ == "__main__":
    print(description,'\n')
    input_ip_list = None
    input_domain_list = None
    try:
        while not (input_ip_list or input_domain_list): 
            input_ip_list = open_file(input("Список IP адресов (URL|PATH|None): "),'ip')
            input_domain_list = open_file(input("Список доменов (URL|PATH|None): "),'domain')
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
            create_domain_list_based_on_ip = input('\nСоздать ли список доменов на основе списка IP (не рекомендуется) (y|n): ').strip().lower() in ACCEPT_KEYS
        if input_domain_list: 
            create_ip_list_based_on_domain = input('\nСоздать ли список IP на основе списка доменов (y|n): ').strip().lower() in ACCEPT_KEYS
            parse_subdomains = input(f'\nСканировать ли зависимости для доменов (долго, нужен скрипт {SUBURL_SCRIPT_PATH}) (y|n): ').strip().lower() in ACCEPT_KEYS

        if input_ip_list: 
            if format["format_need_only"] != 'domain':
                result = main(input_ip_list, 'ip', output_format)
                write_file(result, f'whitelist ip for {output_format}', format['file_extension'])
            if format["format_need_only"] == 'one' or format["format_need_only"] == 'domain':
                if create_domain_list_based_on_ip:
                    result = main(input_ip_list, 'ip', output_format, 'domain')
                    write_file(result, f'whitelist domains (ip based) for {output_format}', format['file_extension'])

        if input_domain_list: 
            if format["format_need_only"] != 'ip':
                result = main(input_domain_list, 'domain', output_format, parse_subdomains=parse_subdomains)
                write_file(result, f'whitelist domains for {output_format}', format['file_extension'])
            if format["format_need_only"] == 'one' or format["format_need_only"] == 'ip':
                if create_ip_list_based_on_domain:
                    result = main(input_domain_list, 'domain', output_format, 'ip', parse_subdomains=parse_subdomains)
                    write_file(result, f'whitelist ip (domains based) for {output_format}', format['file_extension'])

        print('\n[i] Завершено!')
    except KeyboardInterrupt: print('\n[!] Прервано. (KeyboardInterrupt)')
    
