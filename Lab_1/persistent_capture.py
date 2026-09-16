import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"
PROFILE_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\.browser_profile"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)

ACCOUNT_ID = "844038765605"
USERNAME = "iude-poridhi"
PASSWORD = "P1@/MMHSxAPzH9E"
REGION = "ap-southeast-1"

async def run():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=True,
            viewport={"width": 1600, "height": 950},
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        print("[*] 1. Checking AWS Console access...")
        await page.goto("https://console.aws.amazon.com/console/home", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(6000)

        # If not logged in, go to signin
        if "signin" in page.url or "oauth" in page.url:
            print("[*] Not logged in yet. Going to sign-in page...")
            await page.goto(f"https://{ACCOUNT_ID}.signin.aws.amazon.com/console", wait_until="commit", timeout=60000)
            await page.wait_for_timeout(5000)

            # Check if skip button exists
            skip_btn = page.locator('button:has-text("Skip for now")')
            if await skip_btn.count() > 0:
                await skip_btn.first.click()
                await page.wait_for_timeout(3000)

            # Check for username
            user_inp = page.locator('#username, input[name="username"]')
            if await user_inp.count() > 0:
                print("[*] Entering username and password...")
                await user_inp.first.fill(USERNAME)
                pwd_inp = page.locator('#password, input[name="password"]')
                await pwd_inp.first.fill(PASSWORD)
                btn = page.locator('button:has-text("Sign in"), #signin_button')
                await btn.first.click()
                print("[*] Clicked Sign in. Waiting for session...")
                await page.wait_for_timeout(10000)

        print(f"[+] Current URL: {page.url}")
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "00_console_home.png"))
        print("[+] Saved 00_console_home.png")

        # Now navigate to each service page in ap-southeast-1
        services = [
            ("01_vpcs.png", f"https://console.aws.amazon.com/vpc/home?region={REGION}#vpcs:"),
            ("02_subnets.png", f"https://console.aws.amazon.com/vpc/home?region={REGION}#subnets:"),
            ("03_route_tables.png", f"https://console.aws.amazon.com/vpc/home?region={REGION}#RouteTables:"),
            ("04_transit_gateways.png", f"https://console.aws.amazon.com/vpc/home?region={REGION}#TransitGateways:"),
            ("05_tgw_attachments.png", f"https://console.aws.amazon.com/vpc/home?region={REGION}#TransitGatewayAttachments:"),
            ("06_ec2_instances.png", f"https://console.aws.amazon.com/ec2/home?region={REGION}#Instances:")
        ]

        for filename, url in services:
            print(f"\n[*] Navigating to {filename} ({url})...")
            await page.goto(url, wait_until="commit", timeout=60000)
            # Wait for data table to render
            await page.wait_for_timeout(8000)
            try:
                await page.keyboard.press("Escape")
            except Exception:
                pass
            target_path = os.path.join(OUTPUT_DIR, filename)
            await page.screenshot(path=target_path)
            print(f"[+] Captured {filename}!")

        await context.close()
        print("\n[+] SUCCESS: ALL AWS CONSOLE SCREENSHOTS CAPTURED!")

if __name__ == "__main__":
    asyncio.run(run())
