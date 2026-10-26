from .conftest import authenticate


def test_health(client):
    assert client.get("/health").get_json() == {"status": "ok"}


def test_otp_profile_and_invalid_phone(client):
    assert client.post("/api/auth/request-otp", json={"telephone": "331234567"}).status_code == 400
    response = client.post("/api/auth/request-otp", json={"telephone": "77 123 45 67"})
    assert response.status_code == 201
    assert response.get_json()["dev_code"] == "1234"
    bad = client.post("/api/auth/verify-otp", json={"telephone": "771234567", "code": "0000"})
    assert bad.status_code == 401
    good = client.post("/api/auth/verify-otp", json={"telephone": "771234567", "code": "1234"})
    assert good.status_code == 200


def test_alert_lifecycle_and_permissions(client):
    author = authenticate(client)
    created = client.post("/api/alerts", json={"categorie":"eau","quartier":"Mermoz","description":"Coupure depuis ce matin","option_whatsapp":True,"latitude":14.7167,"longitude":-17.4677,"country_code":"sn"}, headers=author)
    assert created.status_code == 201
    alert_id = created.get_json()["id"]
    assert created.get_json()["whatsapp"] is None
    assert created.get_json()["latitude"] == 14.7167
    other = authenticate(client, "781234567", "Moussa", "Ouakam")
    assert client.post(f"/api/alerts/{alert_id}/confirm", headers=other).get_json()["compteur_confirmations"] == 1
    assert client.post(f"/api/alerts/{alert_id}/confirm", headers=other).status_code == 409
    assert client.post(f"/api/alerts/{alert_id}/resolve", headers=other).status_code == 403
    assert client.post(f"/api/alerts/{alert_id}/resolve", headers=author).status_code == 200
    assert client.get("/api/alerts?scope=global", headers=author).get_json()["items"] == []


def test_filters_and_validation(client):
    headers = authenticate(client)
    for category, quartier in [("eau", "Mermoz"), ("senelec", "Ouakam")]:
        assert client.post("/api/alerts", json={"categorie":category,"quartier":quartier,"description":"Incident"}, headers=headers).status_code == 201
    local = client.get("/api/alerts?scope=quartier", headers=headers).get_json()["items"]
    assert len(local) == 1 and local[0]["quartier"] == "Mermoz"
    water = client.get("/api/alerts?scope=global&categorie=eau", headers=headers).get_json()["items"]
    assert len(water) == 1 and water[0]["categorie"] == "eau"
    invalid = client.post("/api/alerts", json={"categorie":"eau","quartier":"Mermoz","description":"x"*281}, headers=headers)
    assert invalid.status_code == 400
    invalid_coordinates = client.post("/api/alerts", json={"categorie":"eau","quartier":"Mermoz","description":"Incident","latitude":200,"longitude":-17}, headers=headers)
    assert invalid_coordinates.status_code == 400


def test_backoffice_groups_assignment_and_access(client):
    regular = authenticate(client, "761234567", "Fatou", "Thiès")
    assert client.get("/api/admin/dashboard", headers=regular).status_code == 403
    admin = authenticate(client, "770000000", "Admin", "Dakar")
    group = client.post("/api/admin/groups", json={"nom":"Équipe Eau","description":"Traitement des coupures"}, headers=admin)
    assert group.status_code == 201
    group_id = group.get_json()["id"]
    alert = client.post("/api/alerts", json={"categorie":"eau","quartier":"Thiès Nord","description":"Fuite importante","option_whatsapp":True}, headers=regular).get_json()
    updated = client.patch(f"/api/admin/alerts/{alert['id']}", json={"priorite":"critique","group_id":group_id,"statut_traitement":"en_cours"}, headers=admin)
    assert updated.status_code == 200
    assert updated.get_json()["groupe"]["nom"] == "Équipe Eau"
    dashboard = client.get("/api/admin/dashboard?quartier=Thiès&priorite=critique", headers=admin).get_json()
    assert len(dashboard["items"]) == 1
    assert dashboard["items"][0]["whatsapp"] == "+221761234567"


def test_group_members_only_see_assigned_alerts_and_unique_lead(client):
    admin = authenticate(client, "770000000", "Admin", "Dakar")
    member = authenticate(client, "751111111", "Samba", "Kaolack")
    outsider = authenticate(client, "752222222", "Mariama", "Saint-Louis")
    group = client.post("/api/admin/groups", json={"nom":"Cellule Routes"}, headers=admin).get_json()
    users = client.get("/api/admin/users?q=Samba", headers=admin).get_json()["items"]
    member_id = users[0]["id"]
    membership = client.post(f"/api/admin/groups/{group['id']}/members", json={"user_id":member_id,"is_lead":True}, headers=admin)
    assert membership.status_code == 201 and membership.get_json()["is_lead"] is True
    alert = client.post("/api/alerts", json={"categorie":"inondation","quartier":"Kaolack","description":"Route coupée"}, headers=outsider).get_json()
    client.patch(f"/api/admin/alerts/{alert['id']}", json={"group_id":group["id"],"priorite":"haute"}, headers=admin)
    assigned = client.get("/api/work/alerts", headers=member).get_json()
    assert len(assigned["items"]) == 1 and assigned["items"][0]["id"] == alert["id"]
    assert client.get("/api/work/alerts", headers=outsider).get_json()["items"] == []
    assert client.patch(f"/api/work/alerts/{alert['id']}", json={"statut_traitement":"en_cours"}, headers=outsider).status_code == 403
    assert client.patch(f"/api/work/alerts/{alert['id']}", json={"statut_traitement":"en_cours"}, headers=member).status_code == 200


def test_recently_assigned_alert_moves_to_top(client):
    admin = authenticate(client, "770000000", "Admin", "Dakar")
    author = authenticate(client, "781111111", "Aminata", "Mermoz")
    group = client.post("/api/admin/groups", json={"nom":"Cellule Urgences"}, headers=admin).get_json()
    first = client.post("/api/alerts", json={"categorie":"eau","quartier":"Mermoz","description":"Première alerte"}, headers=author).get_json()
    second = client.post("/api/alerts", json={"categorie":"eau","quartier":"Mermoz","description":"Deuxième alerte"}, headers=author).get_json()
    assert client.get("/api/alerts?scope=global", headers=author).get_json()["items"][0]["id"] == second["id"]
    client.patch(f"/api/admin/alerts/{first['id']}", json={"group_id":group["id"]}, headers=admin)
    reordered = client.get("/api/alerts?scope=global", headers=author).get_json()["items"]
    assert reordered[0]["id"] == first["id"]
    assert reordered[0]["statut_traitement"] == "assigne"
    client.patch(f"/api/admin/alerts/{first['id']}", json={"statut_traitement":"traite"}, headers=admin)
    public_ids = [item["id"] for item in client.get("/api/alerts?scope=global", headers=author).get_json()["items"]]
    assert first["id"] not in public_ids
    mine = client.get("/api/alerts?scope=mine", headers=author).get_json()["items"]
    assert mine[0]["id"] == first["id"] and mine[0]["statut_traitement"] == "traite"
    oldest = client.get("/api/admin/dashboard?sort=published_asc", headers=admin).get_json()["items"]
    assert oldest[0]["id"] == first["id"]
    publication_day = first["date_publication"][:10]
    dated = client.get(f"/api/admin/dashboard?date_from={publication_day}&date_to={publication_day}", headers=admin)
    assert dated.status_code == 200 and len(dated.get_json()["items"]) == 2
