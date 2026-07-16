from fastapi.testclient import TestClient
from fastapi_backend.main import app

client = TestClient(app)

def test_valid_csv_returns_predictions():
    csv_content = b"text\nWin a free prize now!\nHey are we still on for lunch?\n"
    response = client.post(
        "/bulk-predict",
        files={"file": ("test.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_messages"] == 2
    assert len(data["results"]) == 2

def test_no_file_returns_400():
    response = client.post("/bulk-predict")
    assert response.status_code == 400

def test_empty_file_returns_400():
    response = client.post(
        "/bulk-predict",
        files={"file": ("empty.csv", b"", "text/csv")},
    )
    assert response.status_code == 400

def test_missing_column_returns_400():
    response = client.post(
        "/bulk-predict",
        files={"file": ("bad.csv", b"foo\nbar\n", "text/csv")},
    )
    assert response.status_code == 400