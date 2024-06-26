"""Definitions of Observation and Action space."""


class ObservationSpaceNames:
    """Key names of Observation space."""

    TARGET_SOUND_WAVE = "target_sound_wave"
    GENERATED_SOUND_WAVE = "generated_sound_wave"
    TARGET_SOUND_SPECTROGRAM = "desired_goal"
    GENERATED_SOUND_SPECTROGRAM = "achieved_goal"
    FREQUENCY = "frequency"
    PITCH_SHIFT = "pitch_shift"
    TENSENESS = "tenseness"
    CURRENT_TRACT_DIAMETERS = "current_tract_diameters"
    NOSE_DIAMETERS = "nose_diameters"


class ActionSpaceNames:
    """Key names of Action space."""

    PITCH_SHIFT = "pitch_shift"
    TENSENESS = "tenseness"
    TRACHEA = "trachea"
    EPIGLOTTIS = "epiglottis"
    VELUM = "velum"
    TONGUE_INDEX = "tongue_index"
    TONGUE_DIAMETER = "tongue_diameter"
    LIPS = "lips"
