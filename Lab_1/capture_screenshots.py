import asyncio
import os
import sys
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ACCOUNT_ID = "844038765605"
USERNAME = "iude-poridhi"
PASSWORD = "P1@/MMHSxAPzH9E"
REGION = "ap-southeast-1"

async def capture_all():
    async with async_playwright() as p:
        # Launch browser with standard user-agent
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[*] Navigating to AWS signin page...")
        login_url = f"https://{ACCOUNT_ID}.signin.aws.amazon.com/console"
        try:
            await page.goto(login_url, wait_until="domcontentloaded", timeout=60000)
            print("[+] Loaded signin page.")
        except Exception as e:
            print(f"[-] Navigation error: {e}")

        await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "00_login_page.png"))
        print("[+] Captured 00_login_page.png")

        print("[*] Entering credentials...")
        try:
            # Check for username input
            if await page.is_visible('#username'):
                await page.fill('#username', USERNAME)
            elif await page.is_visible('input[name="username"]'):
                await page.fill('input[name="username"]', USERNAME)

            # Check for password input
            if await page.is_visible('#password'):
                await page.fill('#password', PASSWORD)
            elif await page.is_visible('input[name="password"]'):
                await page.fill('input[name="password"]', PASSWORD)

            # Click signin button
            if await page.is_visible('#signin_button'):
                await page.click('#signin_button')
            elif await page.is_visible('button[type="submit"]'):
                await page.click('button[type="submit"]')
                
            print("[+] Clicked signin.")
        except Exception as e:
            print(f"[-] Error entering login info: {e}")

        # Wait for authentication redirect
        print("[*] Waiting for console to load...")
        await page.wait_for_timeout(12000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "01_console_home.png"))
        print("[+] Captured 01_console_home.png")

        # 1. VPCs
        print("[*] Navigating to VPCs...")
        vpc_url = f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#vpcs:"
        await page.goto(vpc_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "02_vpcs_list.png"))
        print("[+] Captured 02_vpcs_list.png")

        # 2. Transit Gateways
        print("[*] Navigating to Transit Gateways...")
        tgw_url = f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#TransitGateways:"
        await page.goto(tgw_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "03_transit_gateways.png"))
        print("[+] Captured 03_transit_gateways.png")

        # 3. Transit Gateway Attachments
        print("[*] Navigating to Transit Gateway Attachments...")
        tgw_att_url = f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#TransitGatewayAttachments:"
        await page.goto(tgw_att_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_tgw_attachments.png"))
        print("[+] Captured 04_tgw_attachments.png")

        # 4. Route Tables
        print("[*] Navigating to Route Tables...")
        rt_url = f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#RouteTables:"
        await page.goto(rt_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "05_route_tables.png"))
        print("[+] Captured 05_route_tables.png")

        # 5. EC2 Instances
        print("[*] Navigating to EC2 Instances...")
        ec2_url = f"https://{REGION}.console.aws.amazon.com/ec2/home?region={REGION}#Instances:"
        await page.goto(ec2_url, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(6000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "06_ec2_instances.png"))
        print("[+] Captured 06_ec2_instances.png")

        await browser.close()
        print("[+] ALL CONSOLE SCREENSHOTS CAPTURED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(capture_all())
