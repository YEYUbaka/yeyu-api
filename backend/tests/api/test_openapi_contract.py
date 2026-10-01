from app.core.config import settings
from app.main import app


def test_catalog_routes_are_registered_without_public_auth_requirement() -> None:
    schema = app.openapi()
    catalog_path = f"{settings.API_V1_STR}/catalog"
    detail_path = f"{catalog_path}/{{slug}}"
    admin_path = f"{settings.API_V1_STR}/admin/catalog/{{slug}}"

    assert catalog_path in schema["paths"]
    assert detail_path in schema["paths"]
    assert admin_path in schema["paths"]

    assert "security" not in schema["paths"][catalog_path]["get"]
    assert "security" not in schema["paths"][detail_path]["get"]
    assert schema["paths"][admin_path]["post"]["security"]
    assert schema["paths"][admin_path]["patch"]["security"]
    assert schema["paths"][admin_path]["delete"]["security"]


def test_catalog_openapi_exposes_documentation_shapes_and_no_executor_scheme() -> None:
    schema = app.openapi()
    schemas = schema["components"]["schemas"]

    assert "CatalogPage" in schemas
    assert "ApiDetail" in schemas
    assert schemas["ApiDetail"]["properties"]["auth"]["$ref"].endswith(
        "/ApiAuth"
    )
    assert not any(
        name.casefold() in {"apikey", "api_key"}
        for name in schema["components"].get("securitySchemes", {})
    )
