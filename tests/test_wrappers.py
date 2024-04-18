from pynktrombonegymnasium import wrappers


def test_import():
    from pynktrombonegymnasium.wrappers.action_by_acceleration import (
        ActionByAcceleration,
    )

    assert wrappers.ActionByAcceleration is ActionByAcceleration

    from pynktrombonegymnasium.wrappers.log1p_mel_spectrogram import Log1pMelSpectrogram

    assert wrappers.Log1pMelSpectrogram is Log1pMelSpectrogram
