# SPDX-FileCopyrightText: Magenta ApS <https://magenta.dk>
# SPDX-License-Identifier: MPL-2.0
from unittest.mock import MagicMock
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import Response

from ..app import App
from ..fastapi import create_app


class TestFastAPIApp:
    def test_create_app(self) -> None:
        """Test that `create_app` adds an `App` instance to the FastAPI app returned"""
        # Act
        app: FastAPI = create_app()
        # Assert
        assert isinstance(app.extra["sdtoolplus"], App)

    def test_get_root(self) -> None:
        """Test that 'GET /' returns a JSON doc giving the name of this integration"""
        # Arrange
        client: TestClient = TestClient(create_app())
        # Act
        response: Response = client.get("/")
        # Assert
        assert response.status_code == 200
        assert response.json() == {"name": "sdtoolplus"}

    def test_post_trigger(self) -> None:
        """Test that 'POST /trigger' calls the expected methods on `App`, etc."""
        # Arrange
        mock_sdtoolplus_app = MagicMock(spec=App)
        with patch("sdtoolplus.fastapi.App", return_value=mock_sdtoolplus_app):
            client: TestClient = TestClient(create_app())
            # Act
            response: Response = client.post("/trigger")
            # Assert: check that we call the expected methods
            mock_sdtoolplus_app.get_tree_diff_executor.assert_called_once_with()
            mock_sdtoolplus_app.get_tree_diff_executor().execute.assert_called_once_with()
            # Assert: check status code and response
            assert response.status_code == 200
            assert response.json() == []
