"""Placeholder test so pytest collection succeeds before real tests land."""


def test_package_importable() -> None:
    """The napoleon package imports and exposes its module name."""
    import custom_components.napoleon_efire as pkg

    assert pkg.__name__ == "custom_components.napoleon_efire"
