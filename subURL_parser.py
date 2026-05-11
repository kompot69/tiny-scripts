#!/usr/bin/env python3
# by kompot69
description = 'Скрипт для получения списка доменов и/или IP, которые используются при загрузке определенного ресурса. Создан для использования со скриптом vpn_whitelist.py'
import sys, asyncio, json, socket, aiodns
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import playwright._impl._errors as pw_errors

async def scan(url: str, ipv6: bool, without_ip: bool, http=False, timeout_sec=30,):
    try:
        visited_domains = set()
        visited_ips = set()
        dns_tasks = []
        resolver = aiodns.DNSResolver()

        async def resolve_domain(domain: str):
            try:
                result = await resolver.getaddrinfo(domain, family=socket.AF_UNSPEC, port=0)
                for node in result.nodes:
                    ip = node.addr[0]
                    if isinstance(ip, bytes): ip = ip.decode("utf-8")
                    if ":" in ip and not ipv6: continue
                    visited_ips.add(ip)
            except Exception: pass
        async def add_domain(url):
            try:
                parsed = urlparse(url)
                domain = parsed.hostname
                if not domain: return
                if domain not in visited_domains:
                    visited_domains.add(domain)
                    if not without_ip:
                        task = asyncio.create_task(resolve_domain(domain))
                        dns_tasks.append(task)
            except Exception: pass
        def handle_event(url=None, request=None): 
            if url: asyncio.create_task(add_domain(url))
            if request: 
                asyncio.create_task(add_domain(request.url))
                if request.redirected_from: asyncio.create_task(add_domain(request.redirected_from.url))            

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            context.on("request", lambda r: handle_event(r.url))
            context.on("response", lambda r: handle_event(r.url))
            context.on("requestfinished", lambda r: handle_event(r.url))
            context.on("request", lambda r: handle_event(request=r))
            page = await context.new_page()
            page.on("websocket", lambda ws: handle_event(ws.url))
            
            if not url.startswith("http"): url = ("http://" if http else "https://") + url

            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_sec*1000)
            await page.mouse.move(100, 100)
            await page.click("body")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

            last_count = 0
            for _ in range(timeout_sec):
                await asyncio.sleep(2)
                if len(visited_domains) == last_count: break
                last_count = len(visited_domains)

        if dns_tasks: await asyncio.gather(*dns_tasks, return_exceptions=True)
        await resolver.close()
        return {"domains": sorted(visited_domains),"ips": sorted(visited_ips),}

    except pw_errors.Error as e: 
        if 'Looks like Playwright was just installed or updated' in str(e): 
            print(' Необходимо установить Playwright командой "playwright install" перед началом работы (около 450 Мб)', flush=True)
        elif ': net::ERR_' in str(e):     
            error = str(e)
            start = error.find('net::ERR_')
            if start != -1:
                end = error.find(' ', start)
                if end == -1: end = len(error)
                error = error[start+9:end]
            print(f" ошибка: {error}", flush=True)
        elif ': Timeout' in str(e): print(f" ошибка: Timeout", flush=True)
        elif ': Download is starting' in str(e): print(f" ошибка: не является веб-страницей", flush=True)
        else: return print(f" ошибка: {e}", flush=True)
    finally: 
        await resolver.close()
        await browser.close()
    

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"{description}\nИспользование: python {sys.argv[0]} <url> [--ipv6|--json|--noip|--http]")
        sys.exit(1)
    url = sys.argv[1]
    json_mode = "--json" in sys.argv
    ipv6_mode = "--ipv6" in sys.argv
    noip_mode = "--noip" in sys.argv
    http_mode = "--http" in sys.argv

    result = asyncio.run(scan(url, ipv6_mode, noip_mode, http_mode))

    if json_mode: print(json.dumps(result))
    else:
        print("\n=== DOMAINS ===")
        for d in result["domains"]: print(d)
        print("\n=== IPS ===")
        for ip in result["ips"]: print(ip)
