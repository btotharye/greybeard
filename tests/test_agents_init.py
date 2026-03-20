"""Tests for agents package initialization."""

from __future__ import annotations

from greybeard import agents


class TestAgentsPackage:
    """Test suite for agents package."""

    def test_agents_module_imports(self):
        """Test that agents module can be imported."""
        assert agents is not None

    def test_agents_all_attribute_exists(self):
        """Test that agents.__all__ is defined."""
        assert hasattr(agents, "__all__")

    def test_agents_all_is_list(self):
        """Test that __all__ is a list."""
        assert isinstance(agents.__all__, list)

    def test_agents_docstring_exists(self):
        """Test that agents module has documentation."""
        assert agents.__doc__ is not None
        assert "Greybeard agents" in agents.__doc__


class TestAgentsReviewsPackage:
    """Test suite for agents.reviews package."""

    def test_agents_reviews_module_imports(self):
        """Test that agents.reviews module can be imported."""
        from greybeard.agents import reviews

        assert reviews is not None

    def test_agents_reviews_all_attribute_exists(self):
        """Test that agents.reviews.__all__ is defined."""
        from greybeard.agents import reviews

        assert hasattr(reviews, "__all__")

    def test_agents_reviews_all_is_list(self):
        """Test that reviews.__all__ is a list."""
        from greybeard.agents import reviews

        assert isinstance(reviews.__all__, list)

    def test_agents_reviews_docstring_exists(self):
        """Test that reviews module has documentation."""
        from greybeard.agents import reviews

        assert reviews.__doc__ is not None
        assert "Reviews" in reviews.__doc__ or "reviews" in reviews.__doc__
