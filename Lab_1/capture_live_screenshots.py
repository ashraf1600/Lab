import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"

ACCOUNT_ID = "844038765605"
USERNAME = "iude-poridhi"
PASSWORD = "P1@/MMHSxAPzH9E"

async def run():
    async with async_playwright() as p:
        b = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = await b.new_page(
            viewport={"width": 1600, "height": 950},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        print("[*] Logging in...")
        await page.goto(f"https://{ACCOUNT_ID}.signin.aws.amazon.com/console", wait_until="commit", timeout=60000)
        await page.wait_for_selector('#username', timeout=45000)
        await page.fill('#username', USERNAME)
        await page.fill('#password', PASSWORD)
        await page.click('button:has-text("Sign in"), input[type="submit"], #signin_button')
        
        # Wait 10 seconds for session establishment
        await page.wait_for_timeout(10000)
        print("[+] Logged in! Current URL:", page.url)
        
        # Helper to dismiss popups
        async def dismiss():
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
                
        # 1. EC2 Instances
        print("[*] Navigating to EC2 in ap-southeast-1...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/ec2/home?region=ap-southeast-1#Instances:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(12000)
        await dismiss()
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "live_ec2_instances.png"))
        print("[+] Saved live_ec2_instances.png")
        
        # 2. VPCs
        print("[*] Navigating to VPCs in ap-southeast-1...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#vpcs:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(12000)
        await dismiss()
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "live_vpcs.png"))
        print("[+] Saved live_vpcs.png")

        # 3. Transit Gateways
        print("[*] Navigating to Transit Gateways in ap-southeast-1...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#TransitGateways:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(12000)
        await dismiss()
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "live_transit_gateways.png"))
        print("[+] Saved live_transit_gateways.png")

        # 4. Route Tables
        print("[*] Navigating to Route Tables in ap-southeast-1...")
        await page.goto("https://ap-southeast-1.console.aws.amazon.com/vpc/home?region=ap-southeast-1#RouteTables:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(12000)
        await dismiss()
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "live_route_tables.png"))
        print("[+] Saved live_route_tables.png")

        await b.close()
        print("[+] Finished capturing live screenshots!")

if __name__ == "__main__":
    asyncio.run(run())
