import json, uuid
from datetime import timedelta
from fastapi import FastAPI, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .db import init_db, transaction
from .security import require_admin, require_agent_token, digest, random_secret, iso, utcnow, expires_in
from .schemas import EnrollmentCreate, EnrollmentResponse, JobCreate, AgentEnroll, JobResult
from .diagnostics import ALLOWED_OPERATIONS

app=FastAPI(title="Ziroze PC Bridge",version="0.1.0")
settings=get_settings()
app.add_middleware(CORSMiddleware,allow_origins=settings.cors_origins,allow_credentials=False,allow_methods=["GET","POST","OPTIONS"],allow_headers=["Authorization","Content-Type"])
@app.on_event("startup")
def startup(): init_db()
def audit(c,actor,action,target=None,details=None):
 c.execute("INSERT INTO audit(at,actor,action,target,details_json) VALUES(?,?,?,?,?)",(iso(),actor,action,target,json.dumps(details or {})))
def device_for(c,token):
 d=c.execute("SELECT * FROM devices WHERE token_hash=?",(digest(token),)).fetchone()
 if not d or d["revoked_at"]: raise HTTPException(401,"Unknown or revoked device credential")
 return d
@app.get("/health")
def health(): return {"status":"ok","service":"ziroze-pc-bridge","version":"0.1.0"}
@app.post("/api/admin/enrollments",response_model=EnrollmentResponse,dependencies=[Depends(require_admin)])
def create_enrollment(body:EnrollmentCreate):
 code=random_secret(); expiry=expires_in(settings.bridge_enrollment_ttl_minutes)
 with transaction() as c:
  c.execute("INSERT INTO enrollments(code_hash,label,expires_at) VALUES(?,?,?)",(digest(code),body.label,expiry)); audit(c,"admin","enrollment.created",body.label,{"expires_at":expiry})
 return {"code":code,"label":body.label,"expires_at":expiry}
@app.post("/api/agent/enroll")
def enroll(body:AgentEnroll):
 token=random_secret(); did=str(uuid.uuid4())
 with transaction() as c:
  row=c.execute("SELECT * FROM enrollments WHERE code_hash=? AND used_at IS NULL",(digest(body.code),)).fetchone()
  if not row or row["expires_at"]<=iso(): raise HTTPException(400,"Invalid, expired, or used enrollment code")
  c.execute("UPDATE enrollments SET used_at=? WHERE code_hash=? AND used_at IS NULL",(iso(),digest(body.code)))
  c.execute("INSERT INTO devices(id,label,token_hash,created_at,last_seen,metadata_json) VALUES(?,?,?,?,?,?)",(did,row["label"],digest(token),iso(),iso(),json.dumps(body.metadata)))
  audit(c,"enrollment","device.enrolled",did,{"label":row["label"]})
 return {"device_id":did,"device_token":token,"poll_seconds":settings.bridge_agent_poll_seconds}
@app.get("/api/agent/jobs")
def poll(authorization:str|None=Header(default=None)):
 token=require_agent_token(authorization)
 with transaction() as c:
  d=device_for(c,token); now=utcnow(); c.execute("UPDATE devices SET last_seen=? WHERE id=?",(iso(now),d["id"]))
  cutoff=iso(now-timedelta(seconds=settings.bridge_job_lease_seconds))
  c.execute("UPDATE jobs SET status='queued',leased_at=NULL WHERE device_id=? AND status='leased' AND leased_at<?",(d["id"],cutoff))
  j=c.execute("SELECT * FROM jobs WHERE device_id=? AND status='queued' ORDER BY created_at LIMIT 1",(d["id"],)).fetchone()
  if not j:return {"jobs":[]}
  c.execute("UPDATE jobs SET status='leased',leased_at=? WHERE id=?",(iso(now),j["id"])); audit(c,d["id"],"job.leased",j["id"])
  return {"jobs":[{"id":j["id"],"operation":j["operation"],"arguments":json.loads(j["arguments_json"])}]}
@app.post("/api/agent/results")
def result(body:JobResult,authorization:str|None=Header(default=None)):
 token=require_agent_token(authorization)
 with transaction() as c:
  d=device_for(c,token); j=c.execute("SELECT * FROM jobs WHERE id=? AND device_id=?",(body.job_id,d["id"])).fetchone()
  if not j or j["status"]!="leased":raise HTTPException(404,"No active leased job")
  status="failed" if body.error else "completed"
  c.execute("UPDATE jobs SET status=?,finished_at=?,result_json=?,error=? WHERE id=?",(status,iso(),json.dumps(body.result),body.error,body.job_id))
  c.execute("UPDATE devices SET last_seen=? WHERE id=?",(iso(),d["id"])); audit(c,d["id"],"job."+status,body.job_id)
 return {"accepted":True}
@app.get("/api/admin/devices",dependencies=[Depends(require_admin)])
def devices():
 with transaction() as c:
  rows=c.execute("SELECT id,label,created_at,last_seen,revoked_at,metadata_json FROM devices ORDER BY created_at DESC").fetchall()
  return {"devices":[{**dict(r),"metadata":json.loads(r["metadata_json"])} for r in rows]}
@app.post("/api/admin/devices/{device_id}/revoke",dependencies=[Depends(require_admin)])
def revoke(device_id:str):
 with transaction() as c:
  cur=c.execute("UPDATE devices SET revoked_at=? WHERE id=? AND revoked_at IS NULL",(iso(),device_id))
  if not cur.rowcount:raise HTTPException(404,"Active device not found")
  audit(c,"admin","device.revoked",device_id)
 return {"revoked":True}
@app.post("/api/admin/jobs",dependencies=[Depends(require_admin)])
def queue_job(body:JobCreate):
 if body.operation not in ALLOWED_OPERATIONS or body.arguments:raise HTTPException(400,"Only allowlisted diagnostics without arguments are supported")
 jid=str(uuid.uuid4())
 with transaction() as c:
  if not c.execute("SELECT id FROM devices WHERE id=? AND revoked_at IS NULL",(body.device_id,)).fetchone():raise HTTPException(404,"Active device not found")
  c.execute("INSERT INTO jobs(id,device_id,operation,arguments_json,status,created_at) VALUES(?,?,?,?,?,?)",(jid,body.device_id,body.operation,"{}","queued",iso()))
  audit(c,"admin","job.created",jid,{"device_id":body.device_id,"operation":body.operation})
 return {"job_id":jid,"status":"queued"}
@app.get("/api/admin/jobs/{job_id}",dependencies=[Depends(require_admin)])
def job_status(job_id:str):
 with transaction() as c:
  r=c.execute("SELECT * FROM jobs WHERE id=?",(job_id,)).fetchone()
  if not r:raise HTTPException(404,"Job not found")
  d=dict(r);d["arguments"]=json.loads(d.pop("arguments_json"));d["result"]=json.loads(d.pop("result_json") or "{}");return d
@app.get("/api/admin/audit",dependencies=[Depends(require_admin)])
def audit_events(limit:int=100):
 if not 1<=limit<=500:raise HTTPException(400,"limit must be 1..500")
 with transaction() as c:
  rows=c.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
  return {"events":[{**dict(r),"details":json.loads(r["details_json"])} for r in rows]}
@app.post("/mcp",dependencies=[Depends(require_admin)])
async def mcp(payload:dict):
 rid=payload.get("id"); method=payload.get("method"); p=payload.get("params") or {}
 def ok(v):return {"jsonrpc":"2.0","id":rid,"result":v}
 def err(code,msg):return {"jsonrpc":"2.0","id":rid,"error":{"code":code,"message":msg}}
 if payload.get("jsonrpc")!="2.0":return err(-32600,"Invalid JSON-RPC request")
 if method=="initialize":return ok({"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"ziroze-pc-bridge","version":"0.1.0"}})
 if method=="ping":return ok({})
 if method=="notifications/initialized":return {}
 if method=="tools/list":
  return ok({"tools":[{"name":"list_devices","description":"List enrolled devices","inputSchema":{"type":"object","properties":{}}},{"name":"get_device_status","description":"Get a device status","inputSchema":{"type":"object","properties":{"device_id":{"type":"string"}},"required":["device_id"]}},{"name":"run_diagnostic","description":"Queue a safe read-only diagnostic","inputSchema":{"type":"object","properties":{"device_id":{"type":"string"},"operation":{"type":"string","enum":sorted(ALLOWED_OPERATIONS)}},"required":["device_id","operation"]}}]})
 if method=="tools/call":
  a=p.get("arguments") or {};name=p.get("name")
  try:
   if name=="list_devices":out=devices()
   elif name=="get_device_status":
    out=next((x for x in devices()["devices"] if x["id"]==a.get("device_id")),None)
    if out is None:raise HTTPException(404,"Device not found")
   elif name=="run_diagnostic":out=queue_job(JobCreate(device_id=a.get("device_id",""),operation=a.get("operation",""),arguments={}))
   else:return err(-32601,"Unknown tool")
   return ok({"content":[{"type":"text","text":json.dumps(out)}],"isError":False})
  except (HTTPException,ValueError) as e:return ok({"content":[{"type":"text","text":str(getattr(e,"detail",e))}],"isError":True})
 return err(-32601,"Method not found")
