# Recommendation System Tests

This directory contains comprehensive tests for the recommendation endpoints.

## Test Files

### 1. `test_recommend_users.py`
Tests for the `/recommend/users/{user_id}` endpoint.

**Test Coverage:**
- Successful user recommendations
- Custom k parameter handling
- User not found error handling
- Empty user preferences handling
- Tag matching and preference prioritization
- Score sorting validation
- Metadata structure verification

**Run:**
```bash
pytest tests/test_recommend_users.py -v
```

### 2. `test_recommend_notes.py`
Tests for the `/recommend/notes/similar/{note_id}` endpoint.

**Test Coverage:**
- Successful similar note recommendations
- Custom k parameter handling
- Note not found error handling
- Content relevance validation
- Source note exclusion
- Score sorting validation
- Freshness factor verification
- Published/public filtering
- Metadata structure verification

**Run:**
```bash
pytest tests/test_recommend_notes.py -v
```

### 3. `test_recommend_integration.py`
Integration tests connecting both recommendation endpoints.

**Test Coverage:**
- Complete user-to-similar-notes workflow
- ML researcher discovery path
- Cross-endpoint consistency
- Filter consistency across endpoints
- Diverse recommendations
- Score ranking consistency
- Empty results handling
- K parameter consistency

**Run:**
```bash
pytest tests/test_recommend_integration.py -v
```

### 4. `conftest.py`
Shared pytest configuration and fixtures.

**Provides:**
- `clean_state`: Ensures clean state before each test
- `test_client`: FastAPI test client
- `sample_notes`: Sample notes data
- `sample_users`: Sample users data

## Running Tests

### Run all tests:
```bash
pytest tests/ -v
```

### Run specific test file:
```bash
pytest tests/test_recommend_users.py -v
```

### Run specific test:
```bash
pytest tests/test_recommend_users.py::test_recommend_for_user_success -v
```

### Run with coverage:
```bash
pytest tests/ --cov=. --cov-report=html
```

### Run tests matching pattern:
```bash
pytest tests/ -k "user" -v
```

## Test Requirements

Make sure you have the testing dependencies installed:
```bash
pip install pytest pytest-cov httpx
```

## Test Data Structure

Tests use realistic mock data including:
- Multiple notes with varying content and metadata
- Users with different preferences and reading history
- Public/private and published/unpublished notes
- Various tags and series associations

## Key Testing Principles

1. **Isolation**: Each test has its own clean state via fixtures
2. **Realistic Data**: Test data mirrors production data structures
3. **Edge Cases**: Tests cover error conditions and boundary cases
4. **Integration**: Integration tests verify end-to-end workflows
5. **Consistency**: Tests verify consistent behavior across endpoints
