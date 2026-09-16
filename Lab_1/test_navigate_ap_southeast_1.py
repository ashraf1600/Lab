import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        ctx = await b.new_context(
            viewport={"width": 1600, "height": 950},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await ctx.new_page()

        print("[*] 1. Logging in...")
        await page.goto("https://844038765605.signin.aws.amazon.com/console", wait_until="commit", timeout=60000)
        await page.wait_for_selector('#username', state="visible", timeout=30000)
        await page.fill('#username', 'iude-poridhi')
        await page.fill('#password', 'P1@/MMHSxAPzH9E')
        
        btn = page.locator('button:has-text("Sign in"), #signin_button')
        await btn.first.click()

        print("[*] Waiting for console redirect...")
        await page.wait_for_timeout(10000)

        # First switch console region to Singapore
        print("[*] Switching region to ap-southeast-1...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/console/home?region=ap-southeast-1", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "01_singapore_home.png"))
        print("[+] Saved 01_singapore_home.png")

        # EC2 in Singapore
        print("[*] Navigating to EC2 Instances...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/ec2/home?region=ap-southeast-1#Instances:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(10000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "02_live_ec2.png"))
        print("[+] Saved 02_live_ec2.png")

        # VPCs in Singapore
        print("[*] Navigating to VPCs...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#vpcs:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(10000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "03_live_vpcs.png"))
        print("[+] Saved 03_live_vpcs.png")

        # Transit Gateways in Singapore
        print("[*] Navigating to Transit Gateways...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#TransitGateways:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(10000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_live_tgw.png"))
        print("[+] Saved 04_live_tgw.png")

        # Route Tables in Singapore
        print("[*] Navigating to Route Tables...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#RouteTables:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(10000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "05_live_route_tables.png"))
        print("[+] Saved 05_live_route_tables.png")

        await b.close()
        print("[+] All live screenshots captured!")

if __name__ == "__main__":
    asyncio.run(run())
