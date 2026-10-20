"""Mock and test-data builders for isolated development.

This module supports two approaches:
- Pure Python builders (always available)
- Optional factory_boy builders when installed
"""

from dataclasses import dataclass


try:
    import factory
except ImportError:  # pragma: no cover - optional dependency
    factory = None


@dataclass
class ScreenDataBuilder:
    """Simple builder to generate fake payloads without touching the DB."""

    screen_slug: str = "dev1"
    owner: str = "Dev"
    status: str = "mock"
    title: str = "Tela isolada"

    def with_slug(self, slug: str):
        self.screen_slug = slug
        return self

    def with_owner(self, owner: str):
        self.owner = owner
        return self

    def with_status(self, status: str):
        self.status = status
        return self

    def with_title(self, title: str):
        self.title = title
        return self

    def build(self) -> dict:
        return {
            "title": self.title,
            "screen_slug": self.screen_slug,
            "owner": self.owner,
            "status": self.status,
            "header": f"{self.title} ({self.screen_slug})",
            "items": [
                {"label": "Total de registros", "value": 99},
                {"label": "Última sincronização", "value": "mock-data"},
                {"label": "Origem", "value": "builder"},
            ],
        }


if factory is not None:
    class ScreenCardFactory(factory.Factory):
        class Meta:
            model = dict

        label = factory.Sequence(lambda n: f"Métrica {n + 1}")
        value = factory.Sequence(lambda n: n * 3 + 1)


    class ScreenPayloadFactory(factory.Factory):
        class Meta:
            model = dict

        title = "Tela isolada"
        screen_slug = factory.Sequence(lambda n: f"dev{(n % 6) + 1}")
        owner = factory.Sequence(lambda n: f"Dev {(n % 6) + 1}")
        status = "mock"

        @factory.lazy_attribute
        def header(self):
            return f"{self.title} ({self.screen_slug})"

        @factory.lazy_attribute
        def items(self):
            return [ScreenCardFactory() for _ in range(3)]

else:
    ScreenPayloadFactory = None


def build_fake_screen_list(quantity: int = 6) -> list[dict]:
    """Generate quick fake cards for /__dev__/mocks/."""
    cards = []
    for idx in range(1, quantity + 1):
        cards.append(
            {
                "slug": f"dev{idx}",
                "title": f"Tela mock {idx}",
                "owner": f"Dev {idx}",
                "status": "mock-data",
                "path": f"/__dev__/mocks/telas/dev{idx}/",
            }
        )
    return cards


def build_mocked_screen_payload(screen_slug: str, use_factory: bool = False) -> dict:
    """Create screen payload with optional factory_boy fallback."""
    if use_factory and ScreenPayloadFactory is not None:
        payload = ScreenPayloadFactory(screen_slug=screen_slug)
        payload["header"] = f"{payload['title']} ({payload['screen_slug']})"
        return payload

    return (
        ScreenDataBuilder()
        .with_slug(screen_slug)
        .with_owner("Dev Mock")
        .with_status("mock-data")
        .with_title("Tela isolada de desenvolvimento")
        .build()
    )
