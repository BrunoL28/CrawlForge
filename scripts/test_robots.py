import asyncio
from urllib.robotparser import RobotFileParser
import httpx

async def test_robots():
    url = "https://crawler-test.com/"
    robots_url = "https://crawler-test.com/robots.txt"
    
    async with httpx.AsyncClient() as client:
        resp = await client.get(robots_url)
        print(f"Status: {resp.status_code}")
        
        rp = RobotFileParser()
        rp.parse(resp.text.splitlines())
        
        allowed = rp.can_fetch("*", url)
        print(f"Is {url} allowed for '*': {allowed}")
        
        allowed_exact = rp.can_fetch("DeepCrawl", url)
        print(f"Is {url} allowed for 'DeepCrawl': {allowed_exact}")

if __name__ == "__main__":
    asyncio.run(test_robots())
