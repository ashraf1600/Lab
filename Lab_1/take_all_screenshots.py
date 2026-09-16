import asyncio
import os
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"
os.makedirs(OUTPUT_DIR, exist_ok=True)

ACCOUNT_ID = "844038765605"
USERNAME = "iude-poridhi"
PASSWORD = "P1@/MMHSxAPzH9E"
REGION = "ap-southeast-1"

async def run_capture():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            viewport={"width": 1600, "height": 950},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("[*] 1. Navigating to AWS sign-in...")
        await page.goto(f"https://{ACCOUNT_ID}.signin.aws.amazon.com/console", wait_until="commit", timeout=60000)

        print("[*] Waiting for #username input...")
        await page.wait_for_selector('#username', state="visible", timeout=45000)
        
        print("[*] Entering credentials...")
        await page.fill('#username', USERNAME)
        await page.fill('#password', PASSWORD)
        
        print("[*] Clicking 'Sign in' button...")
        signin_button = page.locator('button:has-text("Sign in"), input[type="submit"], #signin_button')
        await signin_button.first.click()

        print("[*] Waiting for console session...")
        try:
            await page.wait_for_url("**/console/**", timeout=45000)
            print("[+] Login confirmed! Loaded console home.")
        except Exception:
            print(f"[*] URL: {page.url}")

        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "00_console_home.png"))
        print("[+] Saved 00_console_home.png")

        # 1. VPCs
        print("\n[*] 2. Navigating to VPCs...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#vpcs:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "01_vpcs.png"))
        print("[+] Saved 01_vpcs.png")

        # 2. Subnets
        print("\n[*] 3. Navigating to Subnets...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#subnets:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "02_subnets.png"))
        print("[+] Saved 02_subnets.png")

        # 3. Route Tables
        print("\n[*] 4. Navigating to Route Tables...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#RouteTables:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "03_route_tables.png"))
        print("[+] Saved 03_route_tables.png")

        # 4. Transit Gateways
        print("\n[*] 5. Navigating to Transit Gateways...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#TransitGateways:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "04_transit_gateways.png"))
        print("[+] Saved 04_transit_gateways.png")

        # 5. Transit Gateway Attachments
        print("\n[*] 6. Navigating to Transit Gateway Attachments...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/vpcconsole/home?region={REGION}#TransitGatewayAttachments:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "05_tgw_attachments.png"))
        print("[+] Saved 05_tgw_attachments.png")

        # 6. EC2 Instances
        print("\n[*] 7. Navigating to EC2 Instances...")
        await page.goto(f"https://{REGION}.console.aws.amazon.com/ec2/home?region={REGION}#Instances:", wait_until="commit", timeout=60000)
        await page.wait_for_timeout(8000)
        await page.screenshot(path=os.path.join(OUTPUT_DIR, "06_ec2_instances.png"))
        print("[+] Saved 06_ec2_instances.png")

        await browser.close()
        print("\n[+] SUCCESS: ALL AWS CONSOLE SCREENSHOTS CAPTURED AND SAVED!")

if __name__ == "__main__":
    asyncio.run(run_capture())
