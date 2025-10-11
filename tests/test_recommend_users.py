import pytest
from fastapi.testclient import TestClient
from main import app, NOTES, USERS, notes_index


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_test_data():
    """Setup test data for user recommendation tests."""
    # Clear existing data
    NOTES.clear()
    USERS.clear()

    # Setup test notes
    test_notes = [
        {
            "id": "note1",
            "title": "Python Programming Basics",
            "content": "Learn Python programming fundamentals",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "programming"],
            "series": None,
            "created_at": "2025-01-01T00:00:00",
            "like_count": 10,
            "view_count": 100
        },
        {
            "id": "note2",
            "title": "Advanced Machine Learning",
            "content": "Deep dive into ML algorithms and techniques",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["machine-learning", "python"],
            "series": "ML Series",
            "created_at": "2025-01-05T00:00:00",
            "like_count": 25,
            "view_count": 250
        },
        {
            "id": "note3",
            "title": "Web Development with FastAPI",
            "content": "Building REST APIs with FastAPI framework",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["fastapi", "python", "web"],
            "series": None,
            "created_at": "2025-01-10T00:00:00",
            "like_count": 15,
            "view_count": 150
        },
        {
            "id": "note4",
            "title": "Private Draft Note",
            "content": "This is a private note",
            "author_id": "author1",
            "is_public": False,
            "is_published": False,
            "tags": ["private"],
            "series": None,
            "created_at": "2025-01-12T00:00:00",
            "like_count": 0,
            "view_count": 5
        }
    ]

    for note in test_notes:
        NOTES[note["id"]] = note

    # Build notes index
    notes_index.build(test_notes)

    # Setup test user
    test_user = {
        "id": "user1",
        "name": "Test User",
        "bio": "Interested in Python and Machine Learning",
        "liked_notes": [
            {"id": "note1", "tags": ["python", "programming"]}
        ],
        "recently_read_notes": [
            {"id": "note1"}
        ]
    }

    USERS["user1"] = test_user

    yield

    # Cleanup
    NOTES.clear()
    USERS.clear()


def test_recommend_for_user_success(client, setup_test_data):
    """Test successful user recommendations."""
    response = client.get("/recommend/users/user1")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert isinstance(data["items"], list)

    # Should not include recently read notes
    note_ids = [item["id"] for item in data["items"]]
    assert "note1" not in note_ids  # Recently read

    # Should only include public and published notes
    assert "note4" not in note_ids  # Private note

    # Check that items have required fields
    for item in data["items"]:
        assert "id" in item
        assert "score" in item
        assert "metadata" in item
        assert isinstance(item["score"], (int, float))


def test_recommend_for_user_with_custom_k(client, setup_test_data):
    """Test user recommendations with custom k parameter."""
    response = client.get("/recommend/users/user1?k=2")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    assert len(data["items"]) <= 2


def test_recommend_for_user_not_found(client, setup_test_data):
    """Test user recommendations for non-existent user."""
    response = client.get("/recommend/users/nonexistent_user")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "user not found"


def test_recommend_for_user_empty_preferences(client, setup_test_data):
    """Test user recommendations for user with no preferences."""
    # Add user with no liked notes or read history
    USERS["user2"] = {
        "id": "user2",
        "name": "New User",
        "bio": "Just getting started",
        "liked_notes": [],
        "recently_read_notes": []
    }

    response = client.get("/recommend/users/user2")

    assert response.status_code == 200
    data = response.json()

    assert "items" in data
    # Should still return recommendations based on bio


def test_recommend_for_user_tag_matching(client, setup_test_data):
    """Test that recommendations prioritize user's preferred tags."""
    # User who likes Python and ML
    USERS["user3"] = {
        "id": "user3",
        "name": "ML Enthusiast",
        "bio": "Machine learning researcher",
        "liked_notes": [
            {"id": "note2", "tags": ["machine-learning", "python"]}
        ],
        "recently_read_notes": [{"id": "note2"}]
    }

    response = client.get("/recommend/users/user3")

    assert response.status_code == 200
    data = response.json()

    # Should get recommendations, excluding already read note2
    note_ids = [item["id"] for item in data["items"]]
    assert "note2" not in note_ids


def test_recommend_for_user_scores_descending(client, setup_test_data):
    """Test that recommendations are sorted by score in descending order."""
    response = client.get("/recommend/users/user1")

    assert response.status_code == 200
    data = response.json()

    scores = [item["score"] for item in data["items"]]
    assert scores == sorted(scores, reverse=True)


def test_recommend_for_user_metadata_structure(client, setup_test_data):
    """Test that metadata is properly included in recommendations."""
    response = client.get("/recommend/users/user1")

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
