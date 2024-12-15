import asyncio
import random
import sys
from datetime import datetime
from time import time

import cloudscraper
from aiocfscrape import CloudflareScraper
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from bot.config import settings

from bot.utils import logger
from bot.exceptions import InvalidSession
from .agents import get_sec_ch_ua
from .headers import headers

from random import randint

from ..utils.tg_manager.TGSession import TGSession


def get_random_api_id():
    return f":::{str(random.random())}"

class Tapper:
    def __init__(self, tg_session: TGSession):
        self.tg_session = tg_session
        self.session_name = tg_session.session_name
        self.auth_token = None
        self.boosts = None

    async def login(self, http_client: cloudscraper.CloudScraper, tg_web_data: str, retry=0):
        try:
            invite_hash = f'invite_hash={self.tg_session.start_param}' if self.tg_session.start_param is not None else ''
            response = http_client.post(f'https://api.onetime.dog/join?{invite_hash}', data=tg_web_data)
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            if retry < 3:
                logger.warning(f"{self.session_name} | Can't logging | Retry attempt: {retry}")
                await asyncio.sleep(delay=randint(5, 10))
                await self.login(http_client, tg_web_data=tg_web_data, retry=retry + 1)

            logger.error(f"{self.session_name} | Unknown error when logging: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_visit(self, http_client: cloudscraper.CloudScraper):
        try:
            response = http_client.get(f'https://api.onetime.dog/advent/calendar/first-visit?'
                                       f'user_id={self.tg_session.tg_id}')
            response.raise_for_status()
            response_json = response.json()
            return response_json['FirstVisit']
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when checking visit: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def set_first_visit(self, http_client: cloudscraper.CloudScraper):
        try:
            response = http_client.post(f'https://api.onetime.dog/advent/calendar/first-visit/set?'
                                        f'user_id={self.tg_session.tg_id}')
            response.raise_for_status()
            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when setting first visit: {error}")
            await asyncio.sleep(delay=randint(3, 7))
            return False

    async def get_frens(self, http_client: cloudscraper.CloudScraper, reference: str):
        try:
            response = http_client.get(f'https://api.onetime.dog/frens?user_id={self.tg_session.tg_id}'
                                       f'&reference={reference}')
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting frens info: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_leaderboard(self, http_client: cloudscraper.CloudScraper):
        try:
            response = http_client.get(f'https://api.onetime.dog/leaderboard?user_id={self.tg_session.tg_id}')
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting leaderboard: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_rewards(self, http_client: cloudscraper.CloudScraper):
        try:
            response = http_client.get(f'https://api.onetime.dog/rewards?user_id={self.tg_session.tg_id}')
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting rewards: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def get_calendar_data(self, http_client: cloudscraper.CloudScraper):
        try:
            response = http_client.get(f'https://api.onetime.dog/advent/calendar?user_id={self.tg_session.tg_id}')
            if response.status_code == 404:
                logger.warning(f'{self.session_name} | Wallet not found | Link your wallet before use!')
                return None
            response.raise_for_status()
            response_json = response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when getting calendar info: {error}")
            await asyncio.sleep(delay=randint(3, 7))

    async def check_calendar(self, http_client: cloudscraper.CloudScraper, day: int):
        try:
            response = http_client.post(f'https://api.onetime.dog/advent/calendar/check?'
                                        f'user_id={self.tg_session.tg_id}&day={day}')
            response.raise_for_status()
            return True
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when checking calendar: {error}")
            await asyncio.sleep(delay=randint(3, 7))
            return False

    async def check_proxy(self, http_client: cloudscraper.CloudScraper, proxy: str) -> None:
        try:
            response = http_client.get(url='https://ipinfo.io/ip', timeout=20)
            ip = response.text
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, user_agent: str, proxy: str | None) -> None:
        access_token_created_time = 0
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None
        headers["User-Agent"] = user_agent
        headers['Sec-Ch-Ua'] = get_sec_ch_ua(user_agent)

        http_client = CloudflareScraper(headers=headers, connector=proxy_conn, trust_env=True,
                                        auto_decompress=False)
        scraper = cloudscraper.create_scraper()
        if proxy:
            proxies = {
                'http': proxy,
                'https': proxy,
                'socks5': proxy
            }
            scraper.proxies.update(proxies)
            await self.check_proxy(http_client=scraper, proxy=proxy)

        token_live_time = randint(3500, 3600)
        scraper.headers = http_client.headers.copy()
        while True:
            try:
                sleep_time = randint(settings.SLEEP_TIME[0], settings.SLEEP_TIME[1])
                if time() - access_token_created_time >= token_live_time:
                    tg_web_data = await self.tg_session.get_tg_web_data()
                    if tg_web_data is None:
                        continue

                    login_data = await self.login(http_client=scraper, tg_web_data=tg_web_data)
                    reference = login_data['reference']
                    logger.info(f'{self.session_name} | Balance: <e>{login_data["balance"]}</e>')
                    access_token_created_time = time()
                    token_live_time = 7200
                    is_first_visit = await self.check_visit(http_client=scraper)
                    frens = await self.get_frens(http_client=scraper, reference=reference)
                    calendar_data = await self.get_calendar_data(http_client=scraper)
                    if calendar_data is None:
                        return
                    leaderboard = await self.get_leaderboard(http_client=scraper)
                    rewards = await self.get_rewards(http_client=scraper)
                    if is_first_visit:
                        await asyncio.sleep(delay=randint(5, 10))
                        result = await self.set_first_visit(http_client=scraper)
                        if result:
                            logger.success(f'{self.session_name} | Set first visit')
                    current_progress = 'Calendar progress in days: '
                    day_progress = []
                    for day in calendar_data:
                        if day['IsCurrent']:
                            if day['IsAvailable'] and not day['IsChecked']:
                                await asyncio.sleep(delay=randint(5, 10))
                                result = await self.check_calendar(http_client=scraper, day=day['ID'])
                                if result:
                                    day_progress.append(f'<g>{day["ID"]}</g>')
                                    logger.success(f'{self.session_name} | Day <lc>{day["ID"]}</lc> successfully checked')
                                else:
                                    day_progress.append(f'<r>{day["ID"]}</r>')
                            elif day['IsChecked']:
                                day_progress.append(f'<g>{day["ID"]}</g>')
                            break
                        day_progress.append(f'<g>{day["ID"]}</g>' if day['IsChecked'] else f'<r>{day["ID"]}</r>')
                    current_progress += ', '.join(day_progress)
                    logger.info(f'{self.session_name} | {current_progress}')

                logger.info(f"{self.session_name} | Sleep <y>{round(sleep_time / 60, 1)}</y> min")
                await asyncio.sleep(delay=sleep_time)

            except InvalidSession as error:
                raise error

            except Exception as error:
                logger.error(f"{self.session_name} | Unknown error: {error}")
                await asyncio.sleep(delay=randint(60, 120))

            except KeyboardInterrupt:
                logger.warning("<r>Bot stopped by user...</r>")
            finally:
                if scraper is not None:
                    await http_client.close()
                    scraper.close()


async def run_tapper(tg_session: TGSession, user_agent: str, proxy: str | None):
    try:
        await Tapper(tg_session=tg_session).run(user_agent=user_agent, proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_session.session_name} | Invalid Session")
