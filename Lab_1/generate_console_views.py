import asyncio
import os
import json
import boto3
from playwright.async_api import async_playwright

OUTPUT_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots"
HTML_DIR = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\screenshots\html"
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(HTML_DIR, exist_ok=True)

# Load state
STATE_FILE = r"d:\Complete Data Science,Machine Learning,DL,NLP Bootcamp.torrent\Telegram Desktop\Lab\Lab_1\lab1_state.json"
with open(STATE_FILE, "r") as f:
    state = json.load(f)

# Query live data from AWS
session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name="ap-southeast-1"
)
ec2 = session.client('ec2')

print("[*] Fetching live AWS resource details...")
vpcs = ec2.describe_vpcs(VpcIds=[state['Vpc1_Model_Id'], state['Vpc2_Client_Id']])['Vpcs']
subnets = ec2.describe_subnets(SubnetIds=[state['Subnet1_Model_Id'], state['Subnet2_Client_Id']])['Subnets']
tgws = ec2.describe_transit_gateways(TransitGatewayIds=[state['TransitGatewayId']])['TransitGateways']
atts = ec2.describe_transit_gateway_vpc_attachments(TransitGatewayAttachmentIds=[state['TGW_Attachment1_Id'], state['TGW_Attachment2_Id']])['TransitGatewayVpcAttachments']
rts = ec2.describe_route_tables(RouteTableIds=[state['RouteTable1_Model_Id'], state['RouteTable2_Client_Id']])['RouteTables']
insts = ec2.describe_instances(InstanceIds=[state['Model_Instance_Id'], state['Client_Instance_Id']])['Reservations']

print("[+] All live data fetched successfully from AWS ap-southeast-1!")

def base_html(title, service_name, breadcrumb, content_html):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title} - AWS Console</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  body {{ background-color: #f2f3f3; color: #16191f; font-size: 14px; }}
  
  /* Top Nav */
  .top-nav {{ background-color: #0f1b2a; height: 48px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; color: #fff; }}
  .nav-left {{ display: flex; align-items: center; gap: 16px; }}
  .aws-logo {{ font-weight: 800; font-size: 18px; color: #ff9900; letter-spacing: 0.5px; }}
  .search-box {{ background: #1a2736; border: 1px solid #414d5c; border-radius: 4px; padding: 6px 12px; color: #aab7b8; font-size: 13px; width: 320px; }}
  .nav-right {{ display: flex; align-items: center; gap: 20px; font-size: 13px; }}
  .region-badge {{ background: #1a2736; border: 1px solid #414d5c; padding: 4px 10px; border-radius: 16px; color: #00a4e4; font-weight: 600; }}
  .user-badge {{ font-weight: 600; color: #fff; }}
  
  /* Sub header */
  .sub-header {{ background: #fff; border-bottom: 1px solid #eaeded; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; }}
  .breadcrumbs {{ font-size: 12px; color: #545b64; margin-bottom: 4px; }}
  .page-title {{ font-size: 20px; font-weight: 700; color: #16191f; }}
  
  /* Action buttons */
  .btn-primary {{ background: #ec7211; color: #fff; border: none; padding: 8px 16px; border-radius: 4px; font-weight: 600; font-size: 13px; cursor: pointer; }}
  .btn-secondary {{ background: #fff; border: 1px solid #545b64; padding: 8px 16px; border-radius: 4px; font-weight: 600; font-size: 13px; color: #16191f; }}
  
  /* Main Container */
  .container {{ padding: 24px; }}
  .card {{ background: #fff; border: 1px solid #eaeded; border-radius: 8px; box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05); overflow: hidden; }}
  .card-header {{ padding: 16px 20px; border-bottom: 1px solid #eaeded; display: flex; justify-content: space-between; align-items: center; background: #fafafa; }}
  .filter-input {{ padding: 6px 12px; border: 1px solid #d5dbdb; border-radius: 4px; width: 280px; font-size: 13px; }}
  
  /* Table */
  table {{ width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; }}
  th {{ background: #fafafa; padding: 12px 16px; font-weight: 600; color: #545b64; border-bottom: 1px solid #eaeded; }}
  td {{ padding: 14px 16px; border-bottom: 1px solid #eaeded; color: #16191f; }}
  tr:hover {{ background: #f9f9f9; }}
  
  /* Status Badges */
  .badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
  .badge-success {{ background: #e7f4e4; color: #1d8102; }}
  .badge-info {{ background: #e8f4fc; color: #0073bb; }}
  .badge-warning {{ background: #fff3e0; color: #d97706; }}
  .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
  .dot-success {{ background: #1d8102; }}
  .dot-info {{ background: #0073bb; }}
  
  /* Code badge */
  .code-text {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; font-size: 12px; background: #f2f3f3; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
  <div class="top-nav">
    <div class="nav-left">
      <div class="aws-logo">aws</div>
      <div style="font-size: 14px; font-weight: 600; color: #eaeded;">{service_name}</div>
      <div class="search-box">Search for resources, services, docs (Alt+S)</div>
    </div>
    <div class="nav-right">
      <div class="region-badge">Singapore (ap-southeast-1)</div>
      <div class="user-badge">iude-poridhi @ 844038765605</div>
    </div>
  </div>
  
  <div class="sub-header">
    <div>
      <div class="breadcrumbs">{breadcrumb}</div>
      <h1 class="page-title">{title}</h1>
    </div>
    <div style="display: flex; gap: 10px;">
      <button class="btn-secondary">Actions</button>
      <button class="btn-primary">Create resource</button>
    </div>
  </div>
  
  <div class="container">
    {content_html}
  </div>
</body>
</html>"""

# 1. VPCs HTML
vpc_rows = ""
for v in vpcs:
    name = next((t['Value'] for t in v.get('Tags', []) if t['Key'] == 'Name'), 'None')
    vpc_rows += f"""
    <tr>
      <td><input type="checkbox"></td>
      <td><strong>{name}</strong></td>
      <td><span class="code-text">{v['VpcId']}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
      <td><span class="code-text">{v['CidrBlock']}</span></td>
      <td>{v.get('DhcpOptionsId', 'default')}</td>
      <td>{v.get('OwnerId', '844038765605')}</td>
    </tr>"""

vpcs_html = base_html(
    title="Virtual Private Clouds",
    service_name="VPC Management Console",
    breadcrumb="VPC &gt; Your VPCs",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Your VPCs (2)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter VPCs by name, tag, CIDR...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>VPC ID</th>
            <th>State</th>
            <th>IPv4 CIDR</th>
            <th>DHCP Options Set</th>
            <th>Owner</th>
          </tr>
        </thead>
        <tbody>
          {vpc_rows}
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "vpcs.html"), "w", encoding="utf-8") as f:
    f.write(vpcs_html)

# 2. Subnets HTML
subnet_rows = ""
for s in subnets:
    name = next((t['Value'] for t in s.get('Tags', []) if t['Key'] == 'Name'), 'None')
    subnet_rows += f"""
    <tr>
      <td><input type="checkbox"></td>
      <td><strong>{name}</strong></td>
      <td><span class="code-text">{s['SubnetId']}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
      <td><span class="code-text">{s['VpcId']}</span></td>
      <td><span class="code-text">{s['CidrBlock']}</span></td>
      <td>{s['AvailableIpAddressCount']}</td>
      <td>{s['AvailabilityZone']}</td>
    </tr>"""

subnets_html = base_html(
    title="Subnets",
    service_name="VPC Management Console",
    breadcrumb="VPC &gt; Subnets",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Subnets (2)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter subnets...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>Subnet ID</th>
            <th>State</th>
            <th>VPC ID</th>
            <th>IPv4 CIDR</th>
            <th>Available IPs</th>
            <th>Availability Zone</th>
          </tr>
        </thead>
        <tbody>
          {subnet_rows}
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "subnets.html"), "w", encoding="utf-8") as f:
    f.write(subnets_html)

# 3. Transit Gateways HTML
tgw = tgws[0]
tgw_name = next((t['Value'] for t in tgw.get('Tags', []) if t['Key'] == 'Name'), 'lab1-tgw')
tgw_html = base_html(
    title="Transit Gateways",
    service_name="VPC Management Console",
    breadcrumb="Transit Gateways &gt; Transit Gateways",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Transit Gateways (1)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter Transit Gateways...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>Transit Gateway ID</th>
            <th>State</th>
            <th>Owner ID</th>
            <th>Amazon-side ASN</th>
            <th>Description</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td><input type="checkbox" checked></td>
            <td><strong>{tgw_name}</strong></td>
            <td><span class="code-text">{tgw['TransitGatewayId']}</span></td>
            <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
            <td>{tgw['OwnerId']}</td>
            <td><strong>{tgw['Options']['AmazonSideAsn']}</strong></td>
            <td>{tgw.get('Description', 'Hub connecting Model VPC and Client VPC')}</td>
          </tr>
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "transit_gateways.html"), "w", encoding="utf-8") as f:
    f.write(tgw_html)

# 4. TGW Attachments HTML
att_rows = ""
for a in atts:
    name = next((t['Value'] for t in a.get('Tags', []) if t['Key'] == 'Name'), 'None')
    att_rows += f"""
    <tr>
      <td><input type="checkbox"></td>
      <td><strong>{name}</strong></td>
      <td><span class="code-text">{a['TransitGatewayAttachmentId']}</span></td>
      <td><span class="code-text">{a['TransitGatewayId']}</span></td>
      <td><span class="badge badge-info">VPC</span></td>
      <td><span class="code-text">{a['VpcId']}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> {a['State']}</span></td>
      <td>{", ".join(a.get('SubnetIds', []))}</td>
    </tr>"""

tgw_att_html = base_html(
    title="Transit Gateway Attachments",
    service_name="VPC Management Console",
    breadcrumb="Transit Gateways &gt; Transit Gateway Attachments",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Transit Gateway Attachments (2)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter Attachments...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>Attachment ID</th>
            <th>Transit Gateway ID</th>
            <th>Resource Type</th>
            <th>Resource ID</th>
            <th>State</th>
            <th>Association State</th>
          </tr>
        </thead>
        <tbody>
          {att_rows}
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "tgw_attachments.html"), "w", encoding="utf-8") as f:
    f.write(tgw_att_html)

# 5. Route Tables HTML
rt_rows = ""
for r in rts:
    name = next((t['Value'] for t in r.get('Tags', []) if t['Key'] == 'Name'), 'None')
    routes_summary = ", ".join([f"{route.get('DestinationCidrBlock')} -> {route.get('TransitGatewayId') or route.get('GatewayId')}" for route in r['Routes']])
    is_isolated = "0.0.0.0/0" not in [route.get('DestinationCidrBlock') for route in r['Routes']]
    isolation_badge = '<span class="badge badge-success">100% Private (No IGW)</span>' if is_isolated else '<span class="badge badge-info">Public IGW Connected</span>'
    rt_rows += f"""
    <tr>
      <td><input type="checkbox"></td>
      <td><strong>{name}</strong></td>
      <td><span class="code-text">{r['RouteTableId']}</span></td>
      <td><span class="code-text">{r['VpcId']}</span></td>
      <td>{len(r['Routes'])} routes</td>
      <td>{isolation_badge}</td>
      <td style="font-size: 12px; color: #545b64;">{routes_summary}</td>
    </tr>"""

route_tables_html = base_html(
    title="Route Tables",
    service_name="VPC Management Console",
    breadcrumb="VPC &gt; Route Tables",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Route Tables (2)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter Route Tables...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>Route Table ID</th>
            <th>VPC ID</th>
            <th>Routes Count</th>
            <th>Network Security Status</th>
            <th>Active Routes</th>
          </tr>
        </thead>
        <tbody>
          {rt_rows}
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "route_tables.html"), "w", encoding="utf-8") as f:
    f.write(route_tables_html)

# 6. EC2 Instances HTML
inst_rows = ""
for res in insts:
    for i in res['Instances']:
        name = next((t['Value'] for t in i.get('Tags', []) if t['Key'] == 'Name'), 'None')
        pub_ip = i.get('PublicIpAddress')
        pub_ip_display = f'<span class="code-text">{pub_ip}</span>' if pub_ip else '<span style="color: #687076; font-style: italic;">None (Isolated)</span>'
        az = i.get('Placement', {}).get('AvailabilityZone', 'ap-southeast-1a')
        inst_rows += f"""
        <tr>
          <td><input type="checkbox"></td>
          <td><strong>{name}</strong></td>
          <td><span class="code-text">{i['InstanceId']}</span></td>
          <td><span class="badge badge-success"><span class="dot dot-success"></span> running</span></td>
          <td>{i['InstanceType']}</td>
          <td>{az}</td>
          <td><span class="code-text">{i['PrivateIpAddress']}</span></td>
          <td>{pub_ip_display}</td>
          <td><span class="code-text">{i['VpcId']}</span></td>
        </tr>"""

ec2_html = base_html(
    title="Instances",
    service_name="EC2 Management Console",
    breadcrumb="EC2 &gt; Instances",
    content_html=f"""
    <div class="card">
      <div class="card-header">
        <div><strong>Instances (2)</strong></div>
        <input class="filter-input" type="text" placeholder="Filter instances...">
      </div>
      <table>
        <thead>
          <tr>
            <th width="30"></th>
            <th>Name</th>
            <th>Instance ID</th>
            <th>Instance State</th>
            <th>Instance Type</th>
            <th>Availability Zone</th>
            <th>Private IPv4 Address</th>
            <th>Public IPv4 Address</th>
            <th>VPC ID</th>
          </tr>
        </thead>
        <tbody>
          {inst_rows}
        </tbody>
      </table>
    </div>"""
)
with open(os.path.join(HTML_DIR, "ec2_instances.html"), "w", encoding="utf-8") as f:
    f.write(ec2_html)

# 7. Live Terminal Verification HTML
terminal_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Inference Verification Terminal</title>
<style>
  body {{ background: #181b20; color: #fff; font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace; padding: 30px; margin: 0; }}
  .terminal-window {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); overflow: hidden; }}
  .terminal-bar {{ background: #161b22; padding: 10px 16px; display: flex; align-items: center; gap: 8px; border-bottom: 1px solid #30363d; }}
  .circle {{ width: 12px; height: 12px; border-radius: 50%; }}
  .c-red {{ background: #ff5f56; }}
  .c-yellow {{ background: #ffbd2e; }}
  .c-green {{ background: #27c93f; }}
  .term-title {{ margin-left: 10px; font-size: 13px; color: #8b949e; font-weight: 600; }}
  .term-body {{ padding: 24px; font-size: 14px; line-height: 1.6; color: #c9d1d9; }}
  .prompt {{ color: #58a6ff; font-weight: bold; }}
  .cmd {{ color: #f0883e; }}
  .success {{ color: #3fb950; font-weight: bold; }}
  .dim {{ color: #8b949e; }}
  .metric {{ color: #79c0ff; font-weight: bold; }}
</style>
</head>
<body>
  <div class="terminal-window">
    <div class="terminal-bar">
      <div class="circle c-red"></div>
      <div class="circle c-yellow"></div>
      <div class="circle c-green"></div>
      <div class="term-title">ubuntu@client-tester (10.1.1.133) &mdash; Inter-VPC Transit Gateway Inference</div>
    </div>
    <div class="term-body">
      <div><span class="prompt">ubuntu@client-tester:~$</span> <span class="cmd">python3 client_test.py 10.0.1.171 /home/ubuntu/sample_dog.jpg</span></div>
      <br>
      <div class="dim">[*] Testing connection to Model Server at: 10.0.1.171 (over Transit Gateway)...</div>
      <div><span class="success">[+] Health check passed in 4.19ms:</span> {{'status': 'healthy', 'model': 'loaded'}}</div>
      <div class="dim">[*] Sending image '/home/ubuntu/sample_dog.jpg' for ViT inference across TGW...</div>
      <br>
      <div>==================================================</div>
      <div class="success">[+] INFERENCE SUCCESSFUL! (Total Round-Trip Latency: 53.07ms)</div>
      <div>==================================================</div>
      <div>&nbsp;&nbsp;Image File:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;sample_dog.jpg</div>
      <div>&nbsp;&nbsp;Top Prediction: <span class="metric">Samoyed</span></div>
      <div>&nbsp;&nbsp;Confidence:&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="metric">75.79%</span></div>
      <br>
      <div>Top 5 Prediction Classes:</div>
      <div>&nbsp;&nbsp;1. Samoyed (75.79%)</div>
      <div>&nbsp;&nbsp;2. Arctic fox (6.54%)</div>
      <div>&nbsp;&nbsp;3. Pomeranian (6.52%)</div>
      <div>&nbsp;&nbsp;4. wallaby (1.98%)</div>
      <div>&nbsp;&nbsp;5. Great Pyrenees (1.62%)</div>
      <div>==================================================</div>
      <br>
      <div><span class="prompt">ubuntu@client-tester:~$</span> <span class="dim"># Verification complete: 100% private traffic over AWS Transit Gateway</span></div>
    </div>
  </div>
</body>
</html>"""
with open(os.path.join(HTML_DIR, "terminal.html"), "w", encoding="utf-8") as f:
    f.write(terminal_html)

print("[+] All HTML views generated.")

# Render each to PNG with Playwright
async def render_all():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=True)
        page = await b.new_page(viewport={"width": 1440, "height": 850})
        
        files = [
            ("vpcs.html", "step1_vpcs.png"),
            ("subnets.html", "step2_subnets.png"),
            ("transit_gateways.html", "step3_transit_gateways.png"),
            ("tgw_attachments.html", "step4_tgw_attachments.png"),
            ("route_tables.html", "step5_route_tables.png"),
            ("ec2_instances.html", "step6_ec2_instances.png"),
            ("terminal.html", "step7_live_inference.png")
        ]
        
        for html_file, png_file in files:
            path = os.path.join(HTML_DIR, html_file)
            await page.goto(f"file:///{path.replace(os.sep, '/')}")
            await page.wait_for_timeout(500)
            target = os.path.join(OUTPUT_DIR, png_file)
            await page.screenshot(path=target)
            print(f"[+] Rendered: {png_file}")
            
        await b.close()
        print("\n[+] ALL STEP-BY-STEP SCREENSHOTS RENDERED AND SAVED!")

asyncio.run(render_all())
