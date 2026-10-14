# Reproducción HMAC aislada

Ejecutada en scratch con dependencias exactas instaladas;12 assertions aprobadas. Ajustar sys.path a checkout del SHA auditado. Base SQLite temporal sólo para construir engine; dependencia NoDB impide consultas, eventos vacíos y sin lifespan. No usar credenciales ni canales de negocio.

```python
import os,sys,json,hmac,hashlib
os.environ.update(ENVIRONMENT='testing',DEBUG='true',DATABASE_URL='sqlite:////tmp/softmobile-hmac-audit.sqlite',LOG_TO_FILES='false',ENABLE_AI_FEATURES='false',SENTRY_DISABLED='true',CORS_ORIGINS='http://testserver',ALLOWED_HOSTS='*')
sys.path.insert(0,'/workspace/scratch/3c50ebd6a1c0/softmobile-audit/backend')
from app.main import app
from app.database import get_db
from app.config_production import prod_settings
from fastapi.testclient import TestClient
class NoDB:
 def __getattr__(self,name):raise AssertionError('DB forbidden in empty-event HMAC probe: '+name)
app.dependency_overrides[get_db]=lambda:NoDB()
prod_settings.META_APP_SECRET='synthetic-audit-secret'
raw=b'{"entry":[]}'
sig='sha256='+hmac.new(prod_settings.META_APP_SECRET.encode(),raw,hashlib.sha256).hexdigest()
result=[]
client=TestClient(app)
for ch in ['whatsapp','messenger','instagram']:
 for case,body,signature in [('valid',raw,sig),('missing',raw,None),('invalid',raw,'sha256='+'0'*64),('tampered',raw+b' ',sig)]:
  headers={'content-type':'application/json'}
  if signature:headers['X-Hub-Signature-256']=signature
  r=client.post('/api/channels/'+ch+'/webhook',content=body,headers=headers)
  result.append({'channel':ch,'case':case,'status':r.status_code,'body':r.json()})
print(json.dumps(result,ensure_ascii=False,indent=2))
assert all(x['status']==(200 if x['case']=='valid' else 401) for x in result)

```
