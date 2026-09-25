import os
import sys
import time
import logging
import asyncio
import httpx
import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [BGP-ROUTER] %(message)s"
)
logger = logging.getLogger("bgp_router")

# Configuration for Multi-Region BGP Peering
REGION_A_IP = os.getenv("REGION_A_IP", "10.0.1.100")
REGION_B_IP = os.getenv("REGION_B_IP", "10.1.1.100")
PORT = int(os.getenv("PORT", "8000"))
ROUTER_AS = 65000

PEERS = {
    "Region_A": {
        "name": "AWS Region A (Primary Cloud)",
        "ip": REGION_A_IP,
        "port": 8000,
        "as_number": 65001,
        "local_pref": 200,  # Higher is preferred
        "status": "UP",
        "consecutive_failures": 0,
        "last_check_ms": 0.0,
        "total_requests": 0
    },
    "Region_B": {
        "name": "AWS Region B (Failover / On-Prem)",
        "ip": REGION_B_IP,
        "port": 8000,
        "as_number": 65002,
        "local_pref": 100,  # Lower preference (Backup)
        "status": "UP",
        "consecutive_failures": 0,
        "last_check_ms": 0.0,
        "total_requests": 0
    }
}

ACTIVE_ROUTE = "Region_A"
FAILOVER_COUNT = 0
FAILOVER_HISTORY = []

app = FastAPI(
    title="BGP Route Controller & Anycast ML VIP",
    description="Dynamic BGP Routing Engine with Multi-Region Model Health Checks"
)

# Background Health Checking Task
async def bgp_health_check_loop():
    global ACTIVE_ROUTE, FAILOVER_COUNT, FAILOVER_HISTORY
    async with httpx.AsyncClient(timeout=2.0) as client:
        while True:
            for peer_key in ["Region_A", "Region_B"]:
                peer = PEERS[peer_key]
                url = f"http://{peer['ip']}:{peer['port']}/health"
                t0 = time.time()
                try:
                    res = await client.get(url)
                    latency = (time.time() - t0) * 1000
                    peer["last_check_ms"] = round(latency, 2)
                    if res.status_code == 200:
                        if peer["status"] == "DOWN":
                            logger.info(f"BGP Session ESTABLISHED: {peer['name']} ({peer['ip']}) is BACK ONLINE.")
                        peer["status"] = "UP"
                        peer["consecutive_failures"] = 0
                    else:
                        peer["consecutive_failures"] += 1
                        if peer["consecutive_failures"] >= 2 and peer["status"] == "UP":
                            peer["status"] = "DOWN"
                            logger.warning(f"BGP Route WITHDRAWN: {peer['name']} ({peer['ip']}) failed health check (HTTP {res.status_code})")
                except Exception as e:
                    peer["consecutive_failures"] += 1
                    peer["last_check_ms"] = 0.0
                    if peer["consecutive_failures"] >= 2 and peer["status"] == "UP":
                        peer["status"] = "DOWN"
                        logger.warning(f"BGP Peer DOWN: {peer['name']} ({peer['ip']}) unreachable: {e}")

            # Dynamic BGP Path Selection
            # Prefer Region_A (Local Pref 200) if UP; otherwise failover to Region_B (Local Pref 100)
            previous_route = ACTIVE_ROUTE
            if PEERS["Region_A"]["status"] == "UP":
                new_route = "Region_A"
            elif PEERS["Region_B"]["status"] == "UP":
                new_route = "Region_B"
            else:
                new_route = "NONE"

            if new_route != previous_route:
                FAILOVER_COUNT += 1
                event = {
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "from": previous_route,
                    "to": new_route,
                    "reason": f"Health check state changed: Region_A={PEERS['Region_A']['status']}, Region_B={PEERS['Region_B']['status']}"
                }
                FAILOVER_HISTORY.append(event)
                logger.critical(f"🚨 BGP ROUTE FAILOVER TRIGGERED! Route changed from [{previous_route}] to [{new_route}]")
                ACTIVE_ROUTE = new_route

            await asyncio.sleep(1.5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(bgp_health_check_loop())

@app.get("/bgp/status")
def bgp_status():
    return {
        "router_as": ROUTER_AS,
        "active_route": ACTIVE_ROUTE,
        "active_backend": PEERS.get(ACTIVE_ROUTE),
        "peers": PEERS,
        "total_failovers": FAILOVER_COUNT,
        "failover_history": FAILOVER_HISTORY[-10:]
    }

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    lines = [
        "# HELP bgp_peer_status BGP Peering Session Status (1=UP, 0=DOWN)",
        "# TYPE bgp_peer_status gauge"
    ]
    for key, p in PEERS.items():
        val = 1 if p["status"] == "UP" else 0
        lines.append(f'bgp_peer_status{{peer="{key}",as="{p["as_number"]}",ip="{p["ip"]}"}} {val}')

    lines.extend([
        "# HELP bgp_active_route Currently active BGP routing target (1=active, 0=standby)",
        "# TYPE bgp_active_route gauge"
    ])
    for key in PEERS.keys():
        val = 1 if ACTIVE_ROUTE == key else 0
        lines.append(f'bgp_active_route{{peer="{key}"}} {val}')

    lines.extend([
        "# HELP bgp_local_pref BGP Local Preference value",
        "# TYPE bgp_local_pref gauge"
    ])
    for key, p in PEERS.items():
        lines.append(f'bgp_local_pref{{peer="{key}"}} {p["local_pref"]}')

    lines.extend([
        "# HELP bgp_failover_events_total Total number of BGP failover transitions",
        "# TYPE bgp_failover_events_total counter",
        f"bgp_failover_events_total {FAILOVER_COUNT}",
        "# HELP bgp_peer_rtt_milliseconds Health check round-trip time in milliseconds",
        "# TYPE bgp_peer_rtt_milliseconds gauge"
    ])
    for key, p in PEERS.items():
        lines.append(f'bgp_peer_rtt_milliseconds{{peer="{key}"}} {p["last_check_ms"]}')

    lines.extend([
        "# HELP bgp_routed_requests_total Total inference requests routed to peer",
        "# TYPE bgp_routed_requests_total counter"
    ])
    for key, p in PEERS.items():
        lines.append(f'bgp_routed_requests_total{{peer="{key}"}} {p["total_requests"]}')

    return "\n".join(lines) + "\n"

# Explicit Chaos Engineering & Admin Endpoints
@app.post("/admin/kill")
async def admin_kill(region: str = "Region_A"):
    peer = PEERS.get(region, PEERS["Region_A"])
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(f"http://{peer['ip']}:{peer['port']}/admin/kill")
        return res.json()

@app.post("/admin/restore")
async def admin_restore(region: str = "Region_A"):
    peer = PEERS.get(region, PEERS["Region_A"])
    async with httpx.AsyncClient(timeout=5.0) as client:
        res = await client.post(f"http://{peer['ip']}:{peer['port']}/admin/restore")
        return res.json()

@app.post("/admin/{region_key}/kill")
async def admin_kill_region(region_key: str):
    return await admin_kill(region=region_key)

@app.post("/admin/{region_key}/restore")
async def admin_restore_region(region_key: str):
    return await admin_restore(region=region_key)

# Anycast Reverse Proxy for ML Inference
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_inference(request: Request, path: str):
    global ACTIVE_ROUTE
    if ACTIVE_ROUTE == "NONE":
        raise HTTPException(status_code=502, detail="BGP Routing Error: All Multi-Region Model Endpoints are DOWN")

    target_peer = PEERS[ACTIVE_ROUTE]
    url = f"http://{target_peer['ip']}:{target_peer['port']}/{path}"
    
    # Read client request body & headers
    body = await request.body()
    headers = dict(request.headers)
    headers.pop("host", None)

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            target_peer["total_requests"] += 1
            res = await client.request(
                method=request.method,
                url=url,
                content=body,
                headers=headers,
                params=dict(request.query_params)
            )
            # Forward response with BGP metadata headers
            resp_headers = dict(res.headers)
            resp_headers["X-BGP-Active-Region"] = target_peer["name"]
            resp_headers["X-BGP-Peer-AS"] = str(target_peer["as_number"])
            resp_headers["X-BGP-Local-Pref"] = str(target_peer["local_pref"])
            resp_headers["X-BGP-Failover-Active"] = "true" if ACTIVE_ROUTE == "Region_B" else "false"
            return Response(content=res.content, status_code=res.status_code, headers=resp_headers)
        except Exception as err:
            logger.error(f"Inference forwarding error to {target_peer['name']}: {err}")
            raise HTTPException(status_code=504, detail=f"BGP Gateway Gateway Timeout: {err}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
