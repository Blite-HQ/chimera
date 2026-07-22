"""Matriz interaction × execution_profile (freeze §1 [S-F]): fail-closed al
cargar el DistributionManifest — jamás en la primera invocación."""

from __future__ import annotations

import pytest

from blite.runtime.dispatch import validate_interaction_profile


@pytest.mark.parametrize(
    ("interaction", "profile"),
    [
        ("request_response", "in-process"),
        ("request_response", "service"),
        ("job", "in-process"),
        ("job", "service"),
        ("job", "remote-job"),
    ],
)
def test_valid_cells_load_without_noise(interaction: str, profile: str) -> None:
    validate_interaction_profile(interaction, profile)


def test_stream_is_frozen_without_dispatch_semantics_in_fase_1() -> None:
    with pytest.raises(NotImplementedError, match="stream"):
        validate_interaction_profile("stream", "in-process")


def test_remote_job_override_requires_interaction_job() -> None:
    # A una capability request_response no se le puede prometer JobRef
    with pytest.raises(NotImplementedError, match="remote-job"):
        validate_interaction_profile("request_response", "remote-job")


@pytest.mark.parametrize(
    ("interaction", "profile"),
    [("rpc", "in-process"), ("job", "lambda")],
)
def test_values_outside_the_frozen_vocabulary_explode(
    interaction: str, profile: str
) -> None:
    with pytest.raises(ValueError, match="vocabulario congelado"):
        validate_interaction_profile(interaction, profile)
