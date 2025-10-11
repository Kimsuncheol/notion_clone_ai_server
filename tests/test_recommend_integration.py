"""
Integration tests connecting both recommendation endpoints.
Tests the workflow of user recommendations and similar note recommendations together.
"""
import pytest
from fastapi.testclient import TestClient
from main import app, NOTES, USERS, notes_index


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def setup_integrated_data():
    """Setup comprehensive test data for integration testing."""
    # Clear existing data
    NOTES.clear()
    USERS.clear()

    # Setup comprehensive notes
    test_notes = [
        {
            "id": "py_basics",
            "title": "Python Basics for Beginners",
            "content": "Start your Python journey with fundamental concepts and syntax.",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "beginner", "tutorial"],
            "series": "Python Learning Path",
            "created_at": "2025-01-01T00:00:00",
            "like_count": 50,
            "view_count": 500
        },
        {
            "id": "py_advanced",
            "title": "Advanced Python Patterns",
            "content": "Master advanced Python programming patterns and best practices.",
            "author_id": "author1",
            "is_public": True,
            "is_published": True,
            "tags": ["python", "advanced", "patterns"],
            "series": "Python Learning Path",
            "created_at": "2025-01-10T00:00:00",
            "like_count": 75,
            "view_count": 600
        },
        {
            "id": "ml_intro",
            "title": "Machine Learning Introduction",
            "content": "Get started with machine learning concepts and algorithms.",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["machine-learning", "python", "ai"],
            "series": "ML Series",
            "created_at": "2025-01-15T00:00:00",
            "like_count": 100,
            "view_count": 800
        },
        {
            "id": "dl_basics",
            "title": "Deep Learning Fundamentals",
            "content": "Understanding neural networks and deep learning techniques.",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["deep-learning", "machine-learning", "ai"],
            "series": "ML Series",
            "created_at": "2025-01-20T00:00:00",
            "like_count": 90,
            "view_count": 700
        },
        {
            "id": "web_dev",
            "title": "Modern Web Development",
            "content": "Building modern web applications with Python and JavaScript.",
            "author_id": "author3",
            "is_public": True,
            "is_published": True,
            "tags": ["web", "python", "javascript"],
            "series": None,
            "created_at": "2025-01-25T00:00:00",
            "like_count": 60,
            "view_count": 550
        },
        {
            "id": "data_science",
            "title": "Data Science with Python",
            "content": "Data analysis and visualization using pandas and matplotlib.",
            "author_id": "author2",
            "is_public": True,
            "is_published": True,
            "tags": ["data-science", "python", "pandas"],
            "series": None,
            "created_at": "2025-02-01T00:00:00",
            "like_count": 85,
            "view_count": 750
        }
    ]

    for note in test_notes:
        NOTES[note["id"]] = note

    # Build notes index
    notes_index.build(test_notes)

    # Setup test users with different preferences
    test_users = {
        "python_enthusiast": {
            "id": "python_enthusiast",
            "name": "Python Developer",
            "bio": "Passionate about Python programming and software development",
            "liked_notes": [
                {"id": "py_basics", "tags": ["python", "beginner", "tutorial"]}
            ],
            "recently_read_notes": [
                {"id": "py_basics"}
            ]
        },
        "ml_researcher": {
            "id": "ml_researcher",
            "name": "ML Researcher",
            "bio": "Machine learning researcher focusing on deep learning",
            "liked_notes": [
                {"id": "ml_intro", "tags": ["machine-learning", "python", "ai"]},
                {"id": "dl_basics", "tags": ["deep-learning", "machine-learning", "ai"]}
            ],
            "recently_read_notes": [
                {"id": "ml_intro"}
            ]
        }
    }

    USERS.update(test_users)

    yield

    # Cleanup
    NOTES.clear()
    USERS.clear()


def test_user_to_similar_notes_workflow(client, setup_integrated_data):
    """
    Test complete workflow: Get user recommendations, then find similar notes.
    """
    # Step 1: Get recommendations for a Python enthusiast
    user_response = client.get("/recommend/users/python_enthusiast?k=5")
    assert user_response.status_code == 200

    user_data = user_response.json()
    assert len(user_data["items"]) > 0

    # Step 2: Take the top recommended note and find similar notes
    top_recommendation_id = user_data["items"][0]["id"]
    similar_response = client.get(f"/recommend/notes/similar/{top_recommendation_id}?k=5")
    assert similar_response.status_code == 200

    similar_data = similar_response.json()
    assert len(similar_data["items"]) > 0

    # Step 3: Verify the similar notes are different from the source
    similar_ids = [item["id"] for item in similar_data["items"]]
    assert top_recommendation_id not in similar_ids


def test_ml_researcher_discovery_path(client, setup_integrated_data):
    """
    Test ML researcher discovers content through user recs and then similar notes.
    """
    # Get recommendations for ML researcher
    response = client.get("/recommend/users/ml_researcher?k=10")
    assert response.status_code == 200

    data = response.json()
    recommended_ids = [item["id"] for item in data["items"]]

    # Should not include already read note
    assert "ml_intro" not in recommended_ids

    # Should get deep learning and data science recommendations
    assert "dl_basics" not in recommended_ids or "data_science" in recommended_ids

    # Now explore similar notes to a recommended item
    if data["items"]:
        first_rec_id = data["items"][0]["id"]
        similar_response = client.get(f"/recommend/notes/similar/{first_rec_id}?k=5")
        assert similar_response.status_code == 200

        similar_data = similar_response.json()
        # Should get related content
        assert len(similar_data["items"]) > 0


def test_cross_endpoint_consistency(client, setup_integrated_data):
    """
    Test that both endpoints return consistent metadata and score structures.
    """
    # Get user recommendations
    user_response = client.get("/recommend/users/python_enthusiast")
    assert user_response.status_code == 200
    user_data = user_response.json()

    # Get similar note recommendations
    similar_response = client.get("/recommend/notes/similar/py_basics")
    assert similar_response.status_code == 200
    similar_data = similar_response.json()

    # Both should have same structure
    for item in user_data["items"] + similar_data["items"]:
        assert "id" in item
        assert "score" in item
        assert "metadata" in item
        assert isinstance(item["metadata"], dict)
        assert "tags" in item["metadata"]
        assert "is_public" in item["metadata"]
        assert "is_published" in item["metadata"]


def test_filter_consistency_across_endpoints(client, setup_integrated_data):
    """
    Test that both endpoints apply same filtering rules (public, published).
    """
    # Add a private note
    NOTES["private_note"] = {
        "id": "private_note",
        "title": "Private Content",
        "content": "This should not appear in recommendations",
        "author_id": "author1",
        "is_public": False,
        "is_published": False,
        "tags": ["python", "private"],
        "series": None,
        "created_at": "2025-02-05T00:00:00",
        "like_count": 0,
        "view_count": 0
    }

    # Rebuild index with private note
    notes_index.add_or_update([NOTES["private_note"]])

    # Check user recommendations
    user_response = client.get("/recommend/users/python_enthusiast?k=20")
    user_data = user_response.json()
    user_ids = [item["id"] for item in user_data["items"]]
    assert "private_note" not in user_ids

    # Check similar note recommendations
    similar_response = client.get("/recommend/notes/similar/py_basics?k=20")
    similar_data = similar_response.json()
    similar_ids = [item["id"] for item in similar_data["items"]]
    assert "private_note" not in similar_ids


def test_diverse_recommendations_integration(client, setup_integrated_data):
    """
    Test that user recommendations show diversity (diversify by series).
    """
    response = client.get("/recommend/users/python_enthusiast?k=10")
    assert response.status_code == 200

    data = response.json()

    # Count notes from same series
    series_counts = {}
    for item in data["items"]:
        series = item["metadata"].get("series")
        if series:
            series_counts[series] = series_counts.get(series, 0) + 1

    # Should not have too many from the same series (max_per=3 in diversify)
    for series, count in series_counts.items():
        assert count <= 3, f"Too many items from series {series}: {count}"


def test_score_ranking_consistency(client, setup_integrated_data):
    """
    Test that scores are properly ranked in both endpoints.
    """
    # User recommendations
    user_response = client.get("/recommend/users/ml_researcher")
    user_data = user_response.json()
    user_scores = [item["score"] for item in user_data["items"]]
    assert user_scores == sorted(user_scores, reverse=True)

    # Similar note recommendations
    similar_response = client.get("/recommend/notes/similar/ml_intro")
    similar_data = similar_response.json()
    similar_scores = [item["score"] for item in similar_data["items"]]
    assert similar_scores == sorted(similar_scores, reverse=True)


def test_empty_results_handling(client, setup_integrated_data):
    """
    Test behavior when recommendations might be limited.
    """
    # Create user who has read everything
    USERS["power_user"] = {
        "id": "power_user",
        "name": "Power User",
        "bio": "Has read everything",
        "liked_notes": [],
        "recently_read_notes": [
            {"id": note_id} for note_id in NOTES.keys()
        ]
    }

    response = client.get("/recommend/users/power_user")
    assert response.status_code == 200

    data = response.json()
    # Should return empty list or very few items
    assert isinstance(data["items"], list)


def test_k_parameter_consistency(client, setup_integrated_data):
    """
    Test that k parameter works consistently across both endpoints.
    """
    k_values = [1, 3, 5, 10]

    for k in k_values:
        # User recommendations
        user_response = client.get(f"/recommend/users/python_enthusiast?k={k}")
        assert user_response.status_code == 200
        user_data = user_response.json()
        assert len(user_data["items"]) <= k

        # Similar note recommendations
        similar_response = client.get(f"/recommend/notes/similar/py_basics?k={k}")
        assert similar_response.status_code == 200
        similar_data = similar_response.json()
        assert len(similar_data["items"]) <= k
