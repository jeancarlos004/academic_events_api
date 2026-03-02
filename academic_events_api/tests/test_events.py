def test_list_events_public(client, sample_event):
    res = client.get("/api/v1/events")
    assert res.status_code == 200
    data = res.json()
    assert "results" in data
    assert data["total"] >= 1


def test_get_event_by_id(client, sample_event):
    res = client.get(f"/api/v1/events/{sample_event.id}")
    assert res.status_code == 200
    assert res.json()["titulo"] == "Evento de Prueba"


def test_get_event_not_found(client):
    res = client.get("/api/v1/events/9999")
    assert res.status_code == 404


def test_create_event_as_admin(client, admin_token):
    res = client.post("/api/v1/events", json={
        "titulo": "Nuevo Taller",
        "descripcion": "Descripción",
        "fecha": "2026-07-01",
        "hora": "09:00",
        "lugar": "Aula 101",
        "cupos": 30,
        "tipo": "taller"
    }, headers={"Authorization": f"Bearer {admin_token}"})
    assert res.status_code == 201
    assert res.json()["titulo"] == "Nuevo Taller"


def test_create_event_as_user_forbidden(client, user_token):
    res = client.post("/api/v1/events", json={
        "titulo": "Intento fallido",
        "descripcion": "x",
        "fecha": "2026-07-01",
        "hora": "09:00",
        "lugar": "Aula",
        "cupos": 10,
        "tipo": "taller"
    }, headers={"Authorization": f"Bearer {user_token}"})
    assert res.status_code == 403


def test_register_and_cancel(client, user_token, sample_event):
    # Inscribirse
    res = client.post(
        f"/api/v1/events/{sample_event.id}/register",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res.status_code == 201

    # Doble inscripción
    res2 = client.post(
        f"/api/v1/events/{sample_event.id}/register",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res2.status_code == 409

    # Cancelar
    res3 = client.delete(
        f"/api/v1/events/{sample_event.id}/register",
        headers={"Authorization": f"Bearer {user_token}"}
    )
    assert res3.status_code == 200


def test_delete_event_as_admin(client, admin_token, sample_event):
    res = client.delete(
        f"/api/v1/events/{sample_event.id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 204
