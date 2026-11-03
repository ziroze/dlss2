import argparse,time,platform,socket,getpass
import httpx
from bridge.diagnostics import run_diagnostic
def metadata():return {"hostname":socket.gethostname(),"platform":platform.platform(),"username":getpass.getuser(),"agent_version":"0.1.0"}
def run(server,code,token,interval):
 base=server.rstrip("/")
 with httpx.Client(timeout=20) as c:
  if code:
   r=c.post(base+"/api/agent/enroll",json={"code":code,"metadata":metadata()});r.raise_for_status();data=r.json();token=data["device_token"];print("Enrolled:",data["device_id"])
  if not token:raise SystemExit("Provide --code or --token")
  while True:
   try:
    h={"Authorization":"Bearer "+token};r=c.get(base+"/api/agent/jobs",headers=h);r.raise_for_status()
    for j in r.json().get("jobs",[]):
     try:b={"job_id":j["id"],"result":run_diagnostic(j["operation"],j.get("arguments") or {})}
     except Exception as e:b={"job_id":j["id"],"result":{},"error":type(e).__name__+": "+str(e)[:250]}
     c.post(base+"/api/agent/results",headers=h,json=b).raise_for_status()
   except httpx.HTTPStatusError as e:
    if e.response.status_code==401:raise SystemExit("Credential rejected/revoked; enroll again")
    print("HTTP error:",e.response.status_code)
   except httpx.HTTPError as e:print("Connection error:",str(e)[:160])
   time.sleep(interval)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--server",required=True);p.add_argument("--code");p.add_argument("--token");p.add_argument("--poll-seconds",type=int,default=5);a=p.parse_args()
 if not a.server.startswith("https://") and not a.server.startswith(("http://localhost","http://127.0.0.1")):raise SystemExit("Use HTTPS except localhost testing")
 run(a.server,a.code,a.token,a.poll_seconds)
