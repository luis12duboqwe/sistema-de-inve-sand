def test_root_ok(client):
  resp = client.get('/')
  assert resp.status_code == 200
  assert resp.json().get('version') == '2.0.0'


def test_create_and_delete_location(client):
  payload = {
    "nombre": "Test Store",
    "tipo": "tienda",
    "direccion": "",
    "telefono": "",
    "activo": True
  }
  created = client.post('/api/locations', json=payload)
  assert created.status_code == 201, created.text
  loc_id = created.json()['id']

  fetched = client.get('/api/locations')
  assert fetched.status_code == 200
  assert any(loc['id'] == loc_id for loc in fetched.json())

  deleted = client.delete(f'/api/locations/{loc_id}')
  assert deleted.status_code == 204
