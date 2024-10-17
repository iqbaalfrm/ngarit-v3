import asyncio
import random
import ssl
import json
import time
import uuid
from loguru import logger
from fake_useragent import UserAgent
import aiohttp

user_agent = UserAgent()
random_user_agent = user_agent.random

async def connect_to_wss(proxy_url, user_id):
    device_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, proxy_url))
    logger.info(f"Device ID: {device_id}")
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)  # Random delay to avoid connection burst
            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi"
            }
            
            # Set up the URI and proxy
            uri = "wss://proxy.wynd.network:4650"
            logger.info(f"Connecting to {uri} using proxy {proxy_url}")

            # Create aiohttp session for WebSocket connection
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(uri, proxy=proxy_url, headers=custom_headers, ssl=False) as websocket:
                    async def send_ping():
                        while True:
                            send_message = json.dumps({
                                "id": str(uuid.uuid4()), 
                                "version": "1.0.0", 
                                "action": "PING", 
                                "data": {}
                            })
                            logger.debug(f"Sending PING: {send_message}")
                            await websocket.send_str(send_message)
                            await asyncio.sleep(5)

                    # Start sending pings after the connection is established
                    await asyncio.sleep(1)
                    asyncio.create_task(send_ping())

                    # Handle incoming messages
                    while True:
                        response = await websocket.receive()
                        if response.type == aiohttp.WSMsgType.TEXT:
                            message = json.loads(response.data)
                            logger.info(f"Received message: {message}")

                            if message.get("action") == "AUTH":
                                auth_response = {
                                    "id": message["id"],
                                    "origin_action": "AUTH",
                                    "result": {
                                        "browser_id": device_id,
                                        "user_id": user_id,
                                        "user_agent": custom_headers['User-Agent'],
                                        "timestamp": int(time.time()),
                                        "device_type": "extension",
                                        "version": "4.20.2",
                                        "extension_id": "lkbnfiajjmbhnfledhphioinpickokdi"
                                    }
                                }
                                logger.debug(f"Sending AUTH response: {auth_response}")
                                await websocket.send_str(json.dumps(auth_response))

                            elif message.get("action") == "PONG":
                                pong_response = {"id": message["id"], "origin_action": "PONG"}
                                logger.debug(f"Sending PONG response: {pong_response}")
                                await websocket.send_str(json.dumps(pong_response))
        
        except Exception as e:
            logger.error(f"Error: {e}")
            logger.error(f"Proxy: {proxy_url}")
            await asyncio.sleep(5)  # Wait before retrying the connection

async def main():
    # Read the proxy and user ID information from a text file
    with open('data.txt', 'r') as file:
        lines = file.read().splitlines()

    user_proxies = {}
    current_user_id = None
    for line in lines:
        if not line.startswith(('http', 'socks4', 'socks5')):  # User ID line
            current_user_id = line
            user_proxies[current_user_id] = []
        else:  # Proxy URL line
            user_proxies[current_user_id].append(line)

    logger.info(f"User proxies: {user_proxies}")

    # Schedule WebSocket connection tasks for each user and proxy
    tasks = []
    for user_id, proxies in user_proxies.items():
        for proxy in proxies:
            logger.info(f"Scheduling task for user {user_id} with proxy {proxy}")
            tasks.append(asyncio.ensure_future(connect_to_wss(proxy, user_id)))

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
