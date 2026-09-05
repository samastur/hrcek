import pytest
import sentry_sdk

from hrcek.core.telemetry import configure_sentry

# Structurally valid but unroutable; no event is ever captured, so
# nothing is sent anywhere.
FAKE_DSN = "https://publickey@localhost/1"


@pytest.fixture
def sentry_isolation():
    """Restore the global Sentry client after a test touches it."""
    yield
    client = sentry_sdk.get_client()
    if client.is_active():
        client.close(timeout=0.0)
    sentry_sdk.init(dsn=None)


def test_sentry_is_inactive_throughout_the_suite():
    assert sentry_sdk.get_client().is_active() is False


def test_configure_sentry_without_a_dsn_does_nothing():
    started = configure_sentry(
        "", environment="test", release="0.1.0", traces_sample_rate=1.0
    )
    assert started is False
    assert sentry_sdk.get_client().is_active() is False


@pytest.mark.django_db
def test_the_app_serves_requests_without_sentry(client):
    assert sentry_sdk.get_client().is_active() is False
    assert client.get("/api/health").status_code == 200


def test_configure_sentry_with_a_dsn_activates_it(sentry_isolation):
    started = configure_sentry(
        FAKE_DSN,
        environment="staging",
        release="9.9.9",
        traces_sample_rate=0.5,
    )
    assert started is True

    options = sentry_sdk.get_client().options
    assert sentry_sdk.get_client().is_active() is True
    assert options["environment"] == "staging"
    assert options["release"] == "9.9.9"
    assert options["traces_sample_rate"] == 0.5


def test_sentry_never_sends_personal_data(sentry_isolation):
    configure_sentry(
        FAKE_DSN, environment="test", release="0.1.0", traces_sample_rate=1.0
    )
    assert sentry_sdk.get_client().options["send_default_pii"] is False
