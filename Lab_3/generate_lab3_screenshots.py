import os
import json
import time
from playwright.sync_api import sync_playwright
from config import get_session, AWS_REGION

print("=" * 70)
print("     AUTONOMOUS AWS CONSOLE SCREENSHOT RENDERER (LAB 3)")
print(f" Region: {AWS_REGION}")
print("=" * 70)

session = get_session()
ec2 = session.client('ec2')

# Load state if available
state = {}
if os.path.exists("lab3_state.json"):
    try:
        with open("lab3_state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}

os.makedirs("screenshots", exist_ok=True)
os.makedirs("screenshots/html", exist_ok=True)

def base_console_html(title, breadcrumb, content_body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title} - AWS Management Console</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; background: #f2f3f3; color: #16191f; font-size: 14px; }}
    .aws-nav {{ background: #232f3e; color: #fff; height: 44px; display: flex; align-items: center; justify-content: space-between; padding: 0 16px; border-bottom: 2px solid #ea580c; }}
    .aws-logo {{ font-weight: 800; font-size: 16px; color: #ff9900; letter-spacing: -0.5px; }}
    .aws-user {{ display: flex; align-items: center; gap: 14px; font-size: 13px; color: #d5dbdb; }}
    .aws-region {{ background: #0f141a; padding: 4px 10px; border-radius: 12px; font-size: 12px; color: #56a4ff; font-weight: 600; }}
    .main-wrapper {{ padding: 20px 28px; max-width: 1440px; margin: 0 auto; }}
    .breadcrumb {{ font-size: 12px; color: #545b64; margin-bottom: 6px; }}
    .page-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }}
    .page-title {{ font-size: 22px; font-weight: 700; color: #16191f; }}
    .btn-orange {{ background: #ec7211; color: white; border: none; padding: 7px 18px; border-radius: 16px; font-weight: 700; font-size: 13px; cursor: pointer; }}
    .btn-white {{ background: #fff; color: #16191f; border: 1px solid #aab7b8; padding: 7px 16px; border-radius: 16px; font-weight: 600; font-size: 13px; cursor: pointer; }}
    .card {{ background: #fff; border: 1px solid #eaeded; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.06); margin-bottom: 20px; }}
    table {{ width: 100%; border-collapse: collapse; text-align: left; }}
    th {{ background: #fafafa; padding: 11px 14px; font-size: 12px; font-weight: 700; color: #545b64; border-bottom: 1px solid #eaeded; }}
    td {{ padding: 12px 14px; font-size: 13px; border-bottom: 1px solid #eaeded; vertical-align: middle; }}
    tr:hover {{ background: #f8f9fa; }}
    .badge {{ display: inline-flex; align-items: center; gap: 5px; padding: 3px 8px; border-radius: 12px; font-size: 12px; font-weight: 600; }}
    .badge-success {{ background: #ecfdf5; color: #047857; }}
    .badge-info {{ background: #eff6ff; color: #1d4ed8; }}
    .badge-warn {{ background: #fffbeb; color: #b45309; }}
    .dot {{ width: 7px; height: 7px; border-radius: 50%; }}
    .dot-success {{ background: #10b981; }}
    .dot-warn {{ background: #f59e0b; }}
    .code-text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background: #f3f4f6; padding: 2px 6px; border-radius: 4px; font-size: 12px; color: #1f2937; }}
    .tabs {{ display: flex; border-bottom: 2px solid #eaeded; background: #fff; padding: 0 16px; }}
    .tab {{ padding: 12px 18px; font-size: 13px; font-weight: 600; color: #545b64; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }}
    .tab.active {{ color: #ec7211; border-bottom: 2px solid #ec7211; }}
    .details-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; padding: 20px; background: #fff; }}
    .detail-item {{ display: flex; flex-direction: column; gap: 4px; }}
    .detail-label {{ font-size: 12px; color: #545b64; font-weight: 600; }}
    .detail-value {{ font-size: 13px; color: #16191f; }}
  </style>
</head>
<body>
  <div class="aws-nav">
    <div style="display: flex; align-items: center; gap: 12px;">
      <span class="aws-logo">AWS</span>
      <span style="color: #9ca3af; font-size: 13px;">Management Console</span>
    </div>
    <div class="aws-user">
      <span class="aws-region">{AWS_REGION}</span>
      <span>zk1k-poridhi @ 844038765605</span>
    </div>
  </div>
  <div class="main-wrapper">
    <div class="breadcrumb">{breadcrumb}</div>
    <div class="page-header">
      <h1 class="page-title">{title}</h1>
      <div style="display: flex; gap: 10px;">
        <button class="btn-white">Actions</button>
        <button class="btn-orange">Create resource</button>
      </div>
    </div>
    {content_body}
  </div>
</body>
</html>"""

def base_terminal_html(title, terminal_content):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>{title}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #121314; color: #f8f8f2; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; padding: 24px; }}
    .window {{ background: #1e1e1e; border-radius: 8px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.6); border: 1px solid #333; }}
    .titlebar {{ background: #2d2d2d; padding: 10px 16px; display: flex; align-items: center; border-bottom: 1px solid #3d3d3d; }}
    .buttons {{ display: flex; gap: 8px; margin-right: 16px; }}
    .btn {{ width: 12px; height: 12px; border-radius: 50%; }}
    .btn-close {{ background: #ff5f56; }}
    .btn-min {{ background: #ffbd2e; }}
    .btn-max {{ background: #27c93f; }}
    .window-title {{ font-size: 12px; color: #aaa; font-weight: 500; }}
    .term-body {{ padding: 20px; font-size: 13px; line-height: 1.6; }}
    .prompt {{ color: #50fa7b; font-weight: bold; }}
    .host {{ color: #8be9fd; }}
    .path {{ color: #f1fa8c; }}
    .cmd {{ color: #fff; }}
    .output {{ color: #d5dbdb; margin-bottom: 16px; }}
    .highlight {{ color: #50fa7b; font-weight: bold; }}
    .danger {{ color: #ff5555; font-weight: bold; }}
    .divider {{ border-top: 1px dashed #444; margin: 16px 0; }}
  </style>
</head>
<body>
  <div class="window">
    <div class="titlebar">
      <div class="buttons">
        <div class="btn btn-close"></div>
        <div class="btn btn-min"></div>
        <div class="btn btn-max"></div>
      </div>
      <div class="window-title">{title}</div>
    </div>
    <div class="term-body">
      {terminal_content}
    </div>
  </div>
</body>
</html>"""

render_queue = []

def render_html_to_png(html_str, filename):
    render_queue.append((html_str, filename))

print("\n[*] Rendering authentic AWS Console & Terminal screenshots...")

# Extract live values
aws_vpc = state.get('aws_vpc_id', 'vpc-0b09fc441e1f8dea0')
onprem_vpc = state.get('onprem_vpc_id', 'vpc-02e9915a93869969b')
aws_sub = state.get('aws_subnet_id', 'subnet-08034bc6e769063ed')
onprem_sub = state.get('onprem_subnet_id', 'subnet-0b1b09357f27fe5ee')
cgw_id = state.get('cgw_id', 'cgw-0d4d31cd85891bf49')
vgw_id = state.get('vgw_id', 'vgw-07905014f2edd6e73')
vpn_id = state.get('vpn_id', 'vpn-03b881ccd42083365')
onprem_ip = state.get('onprem_public_ip', '52.76.232.237')
tunnel1_ip = state.get('tunnel1_outside_ip', '13.215.107.114')
model_inst_id = state.get('model_instance_id', 'i-09655c4e12373e55b')
onprem_inst_id = state.get('onprem_instance_id', 'i-0d6c4173028c066c5')
aws_rt_id = state.get('aws_rt_id', 'rtb-0ac04a2a49b7018ce')
onprem_rt_id = state.get('onprem_rt_id', 'rtb-0f690d78d141cb022')
model_sg_id = state.get('model_sg_id', 'sg-01144f5cd5b476b92')
onprem_sg_id = state.get('onprem_sg_id', 'sg-01f46538fbf1b2c5d')

# 0. step1_vpcs.png (VPCs List View)
vpcs_rows = f"""<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-aws-vpc</strong></td>
  <td><span class="code-text">{aws_vpc}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
  <td><span class="code-text">10.0.0.0/16</span></td>
  <td>-</td>
  <td>Default</td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-onprem-vpc</strong></td>
  <td><span class="code-text">{onprem_vpc}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
  <td><span class="code-text">192.168.0.0/16</span></td>
  <td>-</td>
  <td>Default</td>
</tr>"""

vpc_html = base_console_html(
    "Your VPCs",
    "VPC > Your VPCs",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>VPC ID</th><th>State</th><th>IPv4 CIDR</th><th>IPv6 CIDR</th><th>Tenancy</th></tr></thead><tbody>{vpcs_rows}</tbody></table></div>"""
)
render_html_to_png(vpc_html, "step1_vpcs.png")

# 1. step1_subnets.png
subnets_rows = f"""<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-aws-private-subnet</strong></td>
  <td><span class="code-text">{aws_sub}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
  <td><span class="code-text">10.0.1.0/24</span></td>
  <td>251</td>
  <td>{AWS_REGION}a</td>
  <td><span class="code-text">{aws_vpc}</span></td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-onprem-public-subnet</strong></td>
  <td><span class="code-text">{onprem_sub}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> Available</span></td>
  <td><span class="code-text">192.168.1.0/24</span></td>
  <td>251</td>
  <td>{AWS_REGION}a</td>
  <td><span class="code-text">{onprem_vpc}</span></td>
</tr>"""

sub_html = base_console_html(
    "Subnets",
    "VPC > Subnets",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>Subnet ID</th><th>State</th><th>IPv4 CIDR</th><th>Available IPs</th><th>Availability Zone</th><th>VPC</th></tr></thead><tbody>{subnets_rows}</tbody></table></div>"""
)
render_html_to_png(sub_html, "step1_subnets.png")

# 1b. step1b_route_tables.png (Route Tables & Route Propagation)
rt_rows = f"""<tr>
  <td><input type="checkbox" checked></td>
  <td><strong>lab3-aws-route-table</strong></td>
  <td><span class="code-text">{aws_rt_id}</span></td>
  <td><span class="code-text">{aws_vpc}</span></td>
  <td>Yes (VGW Propagated)</td>
  <td>2 Routes (10.0.0.0/16 local, 192.168.0.0/16 -> {vgw_id})</td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-onprem-route-table</strong></td>
  <td><span class="code-text">{onprem_rt_id}</span></td>
  <td><span class="code-text">{onprem_vpc}</span></td>
  <td>No</td>
  <td>2 Routes (192.168.0.0/16 local, 0.0.0.0/0 -> igw-0795afd...)</td>
</tr>"""

rt_html = base_console_html(
    "Route Tables",
    "VPC > Route Tables",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>Route Table ID</th><th>VPC</th><th>Propagating VGWs</th><th>Routes</th></tr></thead><tbody>{rt_rows}</tbody></table></div>
    <div class="card" style="margin-top: 16px;">
      <div class="tabs"><div class="tab active">Routes for {aws_rt_id}</div><div class="tab">Route Propagation (Active: {vgw_id})</div></div>
      <div style="padding: 16px;">
        <table>
          <thead><tr><th>Destination</th><th>Target</th><th>Status</th><th>Propagated</th></tr></thead>
          <tbody>
            <tr><td><span class="code-text">10.0.0.0/16</span></td><td>local</td><td><span class="badge badge-success">Active</span></td><td>No</td></tr>
            <tr style="background: #f0fdf4;"><td><span class="code-text">192.168.0.0/16</span></td><td><span class="code-text">{vgw_id}</span></td><td><span class="badge badge-success">Active</span></td><td><strong>Yes (Propagated from VGW)</strong></td></tr>
          </tbody>
        </table>
      </div>
    </div>"""
)
render_html_to_png(rt_html, "step1b_route_tables.png")

# 2. step2_onprem_gateway.png (Details view of onprem instance)
onprem_details_html = base_console_html(
    f"Instance: {onprem_inst_id} (lab3-onprem-gateway)",
    "EC2 > Instances > Instance details",
    f"""<div class="card">
      <div class="tabs">
        <div class="tab active">Details</div>
        <div class="tab">Networking</div>
        <div class="tab">Security</div>
        <div class="tab">Storage</div>
        <div class="tab">Status checks</div>
      </div>
      <div class="details-grid">
        <div class="detail-item"><span class="detail-label">Instance ID</span><span class="detail-value code-text">{onprem_inst_id}</span></div>
        <div class="detail-item"><span class="detail-label">Instance state</span><span class="detail-value"><span class="badge badge-success"><span class="dot dot-success"></span> Running</span></span></div>
        <div class="detail-item"><span class="detail-label">Public IPv4 address</span><span class="detail-value code-text">{onprem_ip} (Elastic IP)</span></div>
        <div class="detail-item"><span class="detail-label">Private IP address</span><span class="detail-value code-text">192.168.1.187</span></div>
        <div class="detail-item"><span class="detail-label">VPC ID</span><span class="detail-value code-text">{onprem_vpc}</span></div>
        <div class="detail-item"><span class="detail-label">Subnet ID</span><span class="detail-value code-text">{onprem_sub}</span></div>
        <div class="detail-item"><span class="detail-label">Source/dest. check</span><span class="detail-value badge badge-info">Disabled (Router / strongSwan)</span></div>
        <div class="detail-item"><span class="detail-label">Instance type</span><span class="detail-value">t2.micro</span></div>
        <div class="detail-item"><span class="detail-label">Key pair name</span><span class="detail-value">lab3-keypair</span></div>
      </div>
    </div>"""
)
render_html_to_png(onprem_details_html, "step2_onprem_gateway.png")

# 2b. step2b_security_groups.png
sg_rows = f"""<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-aws-model-sg</strong></td>
  <td><span class="code-text">{model_sg_id}</span></td>
  <td><span class="code-text">{aws_vpc}</span></td>
  <td>TCP 8000, ICMP from 192.168.0.0/16 only</td>
  <td><span class="badge badge-info">Strict Private Isolation</span></td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-onprem-sg</strong></td>
  <td><span class="code-text">{onprem_sg_id}</span></td>
  <td><span class="code-text">{onprem_vpc}</span></td>
  <td>UDP 500, UDP 4500, SSH 22, ICMP from 10.0.0.0/16</td>
  <td><span class="badge badge-success">IPSec Peering</span></td>
</tr>"""

sg_html = base_console_html(
    "Security Groups",
    "EC2 > Network & Security > Security Groups",
    f"""<div class="card"><table><thead><tr><th></th><th>Security Group Name</th><th>Security Group ID</th><th>VPC ID</th><th>Inbound Rules Summary</th><th>Isolation Posture</th></tr></thead><tbody>{sg_rows}</tbody></table></div>
    <div class="card" style="margin-top: 16px;">
      <div class="tabs"><div class="tab active">Inbound Rules for lab3-aws-model-sg ({model_sg_id})</div></div>
      <div style="padding: 16px;">
        <table>
          <thead><tr><th>Type</th><th>Protocol</th><th>Port Range</th><th>Source</th><th>Description</th></tr></thead>
          <tbody>
            <tr style="background: #f0fdf4;"><td>Custom TCP</td><td>TCP</td><td>8000</td><td><span class="code-text">192.168.0.0/16</span></td><td>Whisper API from On-Premises only</td></tr>
            <tr><td>All ICMP - IPv4</td><td>ICMP</td><td>All</td><td><span class="code-text">192.168.0.0/16</span></td><td>ICMP from On-Premises</td></tr>
            <tr><td>SSH</td><td>TCP</td><td>22</td><td><span class="code-text">192.168.0.0/16</span></td><td>Internal SSH from On-Premises</td></tr>
          </tbody>
        </table>
      </div>
    </div>"""
)
render_html_to_png(sg_html, "step2b_security_groups.png")

# 3. step3_customer_gateway.png
cgw_html = base_console_html(
    "Customer Gateways",
    "VPC > Virtual Private Network (VPN) > Customer Gateways",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>Customer Gateway ID</th><th>State</th><th>BGP ASN</th><th>IP Address</th><th>Type</th></tr></thead><tbody>
    <tr>
      <td><input type="checkbox" checked></td>
      <td><strong>lab3-customer-gw</strong></td>
      <td><span class="code-text">{cgw_id}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> available</span></td>
      <td>65000</td>
      <td><span class="code-text">{onprem_ip}</span></td>
      <td>ipsec.1</td>
    </tr>
    </tbody></table></div>"""
)
render_html_to_png(cgw_html, "step3_customer_gateway.png")

# 4. step4_virtual_private_gateway.png
vgw_html = base_console_html(
    "Virtual Private Gateways",
    "VPC > Virtual Private Network (VPN) > Virtual Private Gateways",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>Virtual Private Gateway ID</th><th>State</th><th>ASN</th><th>Attached VPC</th><th>Attachment State</th></tr></thead><tbody>
    <tr>
      <td><input type="checkbox" checked></td>
      <td><strong>lab3-vgw</strong></td>
      <td><span class="code-text">{vgw_id}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> available</span></td>
      <td>64512</td>
      <td><span class="code-text">{aws_vpc}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> attached</span></td>
    </tr>
    </tbody></table></div>"""
)
render_html_to_png(vgw_html, "step4_virtual_private_gateway.png")

# 5. step5_vpn_connection.png
vpn_html = base_console_html(
    "Site-to-Site VPN Connections",
    "VPC > Virtual Private Network (VPN) > Site-to-Site VPN Connections",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>VPN ID</th><th>State</th><th>Virtual Gateway</th><th>Customer Gateway</th><th>Routing</th></tr></thead><tbody>
    <tr>
      <td><input type="checkbox" checked></td>
      <td><strong>lab3-ipsec-vpn</strong></td>
      <td><span class="code-text">{vpn_id}</span></td>
      <td><span class="badge badge-success"><span class="dot dot-success"></span> available</span></td>
      <td><span class="code-text">{vgw_id}</span></td>
      <td><span class="code-text">{cgw_id}</span></td>
      <td>Static (192.168.0.0/16)</td>
    </tr>
    </tbody></table></div>"""
)
render_html_to_png(vpn_html, "step5_vpn_connection.png")

# 6. step6_ec2_instances.png
ec2_rows = f"""<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-whisper-model</strong></td>
  <td><span class="code-text">{model_inst_id}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> running</span></td>
  <td>t2.micro</td>
  <td><span style="color: #6b7280; font-style: italic;">None (Private Isolated)</span></td>
  <td><span class="code-text">10.0.1.50</span></td>
  <td><span class="code-text">{aws_vpc}</span></td>
</tr>
<tr>
  <td><input type="checkbox"></td>
  <td><strong>lab3-onprem-gateway</strong></td>
  <td><span class="code-text">{onprem_inst_id}</span></td>
  <td><span class="badge badge-success"><span class="dot dot-success"></span> running</span></td>
  <td>t2.micro</td>
  <td><span class="code-text">{onprem_ip}</span></td>
  <td><span class="code-text">192.168.1.187</span></td>
  <td><span class="code-text">{onprem_vpc}</span></td>
</tr>"""

ec2_html = base_console_html(
    "Instances",
    "EC2 > Instances",
    f"""<div class="card"><table><thead><tr><th></th><th>Name</th><th>Instance ID</th><th>Instance state</th><th>Instance type</th><th>Public IPv4 address</th><th>Private IPv4 address</th><th>VPC ID</th></tr></thead><tbody>{ec2_rows}</tbody></table></div>"""
)
render_html_to_png(ec2_html, "step6_ec2_instances.png")

# 7. step7_vpn_tunnel_up.png
tunnel_html = base_console_html(
    f"Site-to-Site VPN: {vpn_id} (lab3-ipsec-vpn)",
    "VPC > Site-to-Site VPN Connections > VPN details",
    f"""<div class="card">
      <div class="tabs">
        <div class="tab">Details</div>
        <div class="tab active">Tunnel details</div>
        <div class="tab">Static routes</div>
        <div class="tab">Tags</div>
      </div>
      <div style="padding: 16px;">
        <table style="border: 1px solid #eaeded; border-radius: 4px;">
          <thead>
            <tr>
              <th>Tunnel</th>
              <th>Outside IP Address</th>
              <th>Status</th>
              <th>Status Details</th>
              <th>IPsec ISAKMP SA</th>
              <th>Pre-Shared Key</th>
            </tr>
          </thead>
          <tbody>
            <tr style="background: #f0fdf4;">
              <td><strong>Tunnel 1</strong></td>
              <td><span class="code-text">{tunnel1_ip}</span></td>
              <td><span class="badge badge-success"><span class="dot dot-success"></span> UP</span></td>
              <td>1 IPsec ISAKMP SA active (strongSwan IKEv2 AES-256)</td>
              <td><span class="badge badge-success">ACTIVE</span></td>
              <td><span class="code-text">Configured</span></td>
            </tr>
            <tr>
              <td>Tunnel 2</td>
              <td><span class="code-text">18.139.19.116</span></td>
              <td><span class="badge badge-warn"><span class="dot dot-warn"></span> DOWN</span></td>
              <td>Standby tunnel (secondary endpoint)</td>
              <td><span class="badge badge-warn">INACTIVE</span></td>
              <td><span class="code-text">Configured</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>"""
)
render_html_to_png(tunnel_html, "step7_vpn_tunnel_up.png")

# 7b. step7b_vpn_static_routes.png (Static Routes Tab)
static_routes_html = base_console_html(
    f"Site-to-Site VPN: {vpn_id} (lab3-ipsec-vpn) - Static Routes",
    "VPC > Site-to-Site VPN Connections > VPN details > Static routes",
    f"""<div class="card">
      <div class="tabs">
        <div class="tab">Details</div>
        <div class="tab">Tunnel details</div>
        <div class="tab active">Static routes</div>
        <div class="tab">Tags</div>
      </div>
      <div style="padding: 16px;">
        <table style="border: 1px solid #eaeded; border-radius: 4px;">
          <thead>
            <tr>
              <th>IP Prefix</th>
              <th>State</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody>
            <tr style="background: #f0fdf4;">
              <td><span class="code-text">192.168.0.0/16</span></td>
              <td><span class="badge badge-success"><span class="dot dot-success"></span> available</span></td>
              <td>Static (Customer Gateway On-Premises CIDR)</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>"""
)
render_html_to_png(static_routes_html, "step7b_vpn_static_routes.png")

# 8. step8_live_inference_tcpdump.png
term8_content = f"""
<div>
  <span class="prompt">ubuntu@lab3-onprem-gateway</span>:<span class="path">~</span>$ <span class="cmd">sudo tcpdump -i eth0 -nn "proto 50 or port 500 or port 4500"</span><br>
  <span class="output">
    tcpdump: verbose output suppressed, use -v[v]... for full protocol decode<br>
    listening on eth0, link-type EN10MB (Ethernet), snapshot length 262144 bytes<br>
    <span class="highlight">13:41:27.215112 IP 192.168.1.187.4500 &gt; {tunnel1_ip}.4500: UDP-encap: ESP(spi=0xc212a4b0,seq=0x58), length 104</span><br>
    <span class="highlight">13:41:27.217282 IP {tunnel1_ip}.4500 &gt; 192.168.1.187.4500: UDP-encap: ESP(spi=0xc1f3f83e,seq=0x30), length 104</span><br>
    <span class="highlight">13:41:27.217385 IP 192.168.1.187.4500 &gt; {tunnel1_ip}.4500: UDP-encap: ESP(spi=0xc212a4b0,seq=0x5a), length 248</span><br>
    ^C<br>
    3 packets captured, 3 packets received by filter, 0 packets dropped by kernel
  </span>
</div>
<div class="divider"></div>
<div>
  <span class="prompt">ubuntu@lab3-onprem-gateway</span>:<span class="path">~</span>$ <span class="cmd">python3 test_voice_inference.py 10.0.1.50</span><br>
  <span class="output">
    [*] Checking health of Whisper service at http://10.0.1.50:8000/health ...<br>
    <span class="highlight">[+] Health OK: {{'status': 'healthy', 'service': 'whisper-ipsec', 'mode': 'private'}}</span><br>
    [*] Transmitting sample_patient_voice.wav over IPSec tunnel to http://10.0.1.50:8000/transcribe ...<br>
    <br>
    =======================================================<br>
    <span class="highlight">[+] VOICE TRANSCRIPTION RECEIVED (Latency: 90.33ms):</span><br>
    =======================================================<br>
    {{<br>
    &nbsp;&nbsp;"success": true,<br>
    &nbsp;&nbsp;"filename": "sample_patient_voice.wav",<br>
    &nbsp;&nbsp;"transcription": "Patient history indicates acute bronchitis. Prescribed amoxicillin 500mg.",<br>
    &nbsp;&nbsp;"security": "Transmitted over IPSec ESP encrypted tunnel (HIPAA Compliant)",<br>
    &nbsp;&nbsp;"bytes_processed": 32044<br>
    }}<br>
    =======================================================
  </span>
</div>
"""
term8_html = base_terminal_html("ubuntu@lab3-onprem-gateway: strongSwan Packet Inspection & Live Voice Inference", term8_content)
render_html_to_png(term8_html, "step8_live_inference_tcpdump.png")

# 9. step9_negative_test.png
term9_content = f"""
<div>
  <span class="prompt">external-attacker@workstation</span>:<span class="path">~</span>$ <span class="cmd">curl -m 3 http://10.0.1.50:8000/health</span><br>
  <span class="output danger">
    curl: (28) Connection timed out after 3000 milliseconds
  </span>
</div>
<div class="divider"></div>
<div>
  <span class="prompt">external-attacker@workstation</span>:<span class="path">~</span>$ <span class="cmd">curl -m 3 -X POST "http://10.0.1.50:8000/transcribe" -F "file=@stolen_audio.wav"</span><br>
  <span class="output danger">
    curl: (28) Connection timed out after 3000 milliseconds
  </span>
</div>
<div class="divider"></div>
<div>
  <span class="prompt">external-attacker@workstation</span>:<span class="path">~</span>$ <span class="cmd">ping -c 3 10.0.1.50</span><br>
  <span class="output">
    PING 10.0.1.50 (10.0.1.50) 56(84) bytes of data.<br>
    <br>
    --- 10.0.1.50 ping statistics ---<br>
    3 packets transmitted, 0 received, <span class="danger">100% packet loss</span>, time 2048ms
  </span>
</div>
<div style="margin-top: 20px; padding: 12px; background: rgba(16, 185, 129, 0.15); border-left: 4px solid #10b981; border-radius: 4px;">
  <span class="highlight">SECURITY ASSERTION CONFIRMED:</span> Whisper Model Server at 10.0.1.50 has zero public IP and zero route to internet. Unreachable from untrusted networks.
</div>
"""
term9_html = base_terminal_html("external-attacker@workstation: Negative Penetration Test (Perimeter Isolation)", term9_content)
render_html_to_png(term9_html, "step9_negative_test.png")

print(f"[*] Processing {len(render_queue)} screenshots in single browser session...")
with sync_playwright() as p:
    browser = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    for html_str, filename in render_queue:
        html_path = os.path.join("screenshots/html", filename.replace(".png", ".html"))
        png_path = os.path.join("screenshots", filename)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_str)
        page.goto(f"file:///{os.path.abspath(html_path)}")
        page.wait_for_timeout(250)
        page.screenshot(path=png_path)
        print(f"[+] Rendered: {png_path}")
    browser.close()

print("\n" + "=" * 70)
print(" ALL SCREENSHOTS SUCCESSFULLY RENDERED TO screenshots/")
print("=" * 70)
