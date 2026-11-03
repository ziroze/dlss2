import os,tempfile
from pathlib import Path
os.environ["BRIDGE_ADMIN_TOKEN"]="test-admin-token";os.environ["BRIDGE_SECRET"]="test-bridge-secret"
_tmp=tempfile.TemporaryDirectory();os.environ["BRIDGE_DATABASE"]=str(Path(_tmp.name)/"test.sqlite3")
from fastapi.testclient import TestClient
from bridge.main import app
c=TestClient(app);h={"Authorization":"Bearer test-admin-token"}
def test_enroll_job_revoke():
 assert c.get("/health").status_code==200
 e=c.post("/api/admin/enrollments",headers=h,json={"label":"test pc"});assert e.status_code==200
 code=e.json()["code"];d=c.post("/api/agent/enroll",json={"code":code,"metadata":{}});assert d.status_code==200
 x=d.json();ah={"Authorization":"Bearer "+x["device_token"]}
 assert c.post("/api/agent/enroll",json={"code":code}).status_code==400
 j=c.post("/api/admin/jobs",headers=h,json={"device_id":x["device_id"],"operation":"system_info"});assert j.status_code==200
 jid=j.json()["job_id"];assert c.get("/api/agent/jobs",headers=ah).json()["jobs"][0]["id"]==jid
 assert c.post("/api/agent/results",headers=ah,json={"job_id":jid,"result":{"ok":True}}).status_code==200
 assert c.get("/api/admin/jobs/"+jid,headers=h).json()["status"]=="completed"
 assert c.post("/api/admin/devices/"+x["device_id"]+"/revoke",headers=h).status_code==200
 assert c.get("/api/agent/jobs",headers=ah).status_code==401
def test_admin_auth():assert c.get("/api/admin/devices").status_code==401
