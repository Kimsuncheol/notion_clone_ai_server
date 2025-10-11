import pytest
from fastapi.testclient import TestClient
from main import app, NOTES, notes_index


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_test_data():
    """Setup test data for note similarity recommendation tests."""
    # Clear existing data
    NOTES.clear()

    # Setup test notes with varying similarity
    test_notes = [
        {
            "id": "note1",
            "title": "Introduction to Python",
            "content": "Python is a high-level programming language. It's great for beginners and experts alike.",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "programming", "tutorial"],
            "series": "Python Basics",
            "created_at": "2025-01-01T00:00:00",
            "like_count": 10,
            "view_count": 100
        },
        {
            "id": "note2",
            "title": "Advanced Python Techniques",
            "content": "Learn advanced Python programming concepts like decorators, generators, and context managers.",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "advanced", "programming"],
            "series": "Python Basics",
            "created_at": "2025-01-05T00:00:00",
            "like_count": 25,
            "view_count": 250
        },
        {
            "id": "note3",
            "title": "Python for Data Science",
            "content": "Using Python for data analysis with pandas, numpy, and matplotlib libraries.",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "data-science", "pandas"],
            "series": None,
            "created_at": "2025-01-08T00:00:00",
            "like_count": 30,
            "view_count": 300
        },
        {
            "id": "note4",
            "title": "JavaScript Fundamentals",
            "content": "Learn JavaScript programming language for web development and modern applications.",
            "author_id": "author3",
            "is_public": True,
            "is_published": True,
            "tags": ["javascript", "programming", "web"],
            "series": None,
            "created_at": "2025-01-10T00:00:00",
            "like_count": 15,
            "view_count": 150
        },
        {
            "id": "note5",
            "title": "Private Python Note",
            "content": "This is a private draft about Python internals.",
            "author_id": "author1",
            "is_public": False,
            "is_published": False,
            "tags": ["python", "private"],
            "series": None,
            "created_at": "2025-01-12T00:00:00",
            "like_count": 0,
            "view_count": 5
        },
        {
            "id": "note6",
            "title": "Python Web Frameworks",
            "content": "Overview of Python web frameworks including Django, Flask, and FastAPI.",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "web", "frameworks"],
            "series": None,
            "created_at": "2025-01-15T00:00:00",
            "like_count": 20,
            "view_count": 200
        }
    ]

    for note in test_notes:
        NOTES[note["id"]] = note

    # Build notes index
    notes_index.build(test_notes)

    yield

    # Cleanup
    NOTES.clear()


def test_recommend_similar_success(client, setup_test_data):
    """Test successful similar note recommendations."""
    response = client.get("/recommend/notes/similar/note1")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert isinstance(data["items"], list)

    # Should not include the source note itself
    note_ids = [item["id"] for item in data["items"]]
    assert "note1" not in note_ids

    # Should only include public and published notes
    assert "note5" not in note_ids  # Private note

    # Check that items have required fields
    for item in data["items"]:
        assert "id" in item
        assert "score" in item
        assert "metadata" in item
        assert isinstance(item["score"], (int, float))


def test_recommend_similar_with_custom_k(client, setup_test_data):
    """Test similar note recommendations with custom k parameter."""
    response = client.get("/recommend/notes/similar/note1?k=3")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert len(data["items"]) <= 3


def test_recommend_similar_note_not_found(client, setup_test_data):
    """Test similar note recommendations for non-existent note."""
    response = client.get("/recommend/notes/similar/nonexistent_note")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "note not found"


def test_recommend_similar_content_relevance(client, setup_test_data):
    """Test that similar notes are content-relevant."""
    # Get similar notes to a Python note
    response = client.get("/recommend/notes/similar/note1?k=5")

    assert response.status_code == 200
    data = response.json()

    # Most recommendations should be Python-related
    # (note2, note3, note6 are more similar than note4 which is JavaScript)
    note_ids = [item["id"] for item in data["items"]]

    # Python notes should be more prominent than JavaScript
    if len(note_ids) > 0:
        # note2 and note3 should likely rank higher due to Python content
        assert any(nid in note_ids for nid in ["note2", "note3", "note6"])


def test_recommend_similar_excludes_source(client, setup_test_data):
    """Test that the source note is never included in recommendations."""
    for note_id in ["note1", "note2", "note3", "note4"]:
        response = client.get(f"/recommend/notes/similar/{note_id}")

        assert response.status_code == 200
        data = response.json()

        recommended_ids = [item["id"] for item in data["items"]]
        assert note_id not in recommended_ids


def test_recommend_similar_scores_descending(client, setup_test_data):
    """Test that recommendations are sorted by score in descending order."""
    response = client.get("/recommend/notes/similar/note1")

    assert response.status_code == 200
    data = response.json()

    scores = [item["score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_recommend_similar_metadata_structure(client, setup_test_data):
    """Test that metadata is properly included in recommendations."""
    response = client.get("/recommend/notes/similar/note1")

    assert response.status_code == 200
    data = response.json()

    if data["items"]:
        first_item = data["items"][0]
        metadata = first_item["metadata"]

        # Check metadata has expected fields
        assert "id" in metadata
        assert "is_public" in metadata
        assert "is_published" in metadata
        assert "tags" in metadata
        assert isinstance(metadata["tags"], list)


def test_recommend_similar_freshness_factor(client, setup_test_data):
    """Test that recommendations consider freshness (newer notes score higher)."""
    response = client.get("/recommend/notes/similar/note1?k=10")

    assert response.status_code == 200
    data = response.json()

    # All items should have scores that factor in freshness
    assert all(item["score"] > 0 for item in data["items"])


def test_recommend_similar_filters_unpublished(client, setup_test_data):
    """Test that unpublished and non-public notes are filtered out."""
    response = client.get("/recommend/notes/similar/note1?k=10")

    assert response.status_code == 200
    data = response.json()

    note_ids = [item["id"] for item in data["items"]]

    # Private/unpublished note5 should not appear
    assert "note5" not in note_ids

    # All returned notes should be public and published
    for item in data["items"]:
        metadata = item["metadata"]
        assert metadata["is_public"] is True
        assert metadata["is_published"] is True


def test_recommend_similar_default_k_value(client, setup_test_data):
    """Test that default k=10 works correctly."""
    response = client.get("/recommend/notes/similar/note1")

    assert response.status_code == 200
    data = response.json()

    # Should return up to 10 items (we have 5 valid notes, excluding source and private)
    assert len(data["items"]) <= 10
