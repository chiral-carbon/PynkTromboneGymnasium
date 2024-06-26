"""Generation Test of PynkTromboneGym"""
import glob
import math
import os
from typing import Callable, Mapping

import gym
import numpy as np
import soundfile
from pynktrombonegymnasium import environment
from pynktrombonegymnasium.spaces import ActionSpaceNames as ASN
from pynktrombonegymnasium.spaces import ObservationSpaceNames as OSN

target_sound_files = glob.glob("data/sample_target_sounds/*.wav")
output_dir = "data/test_results/generated_sounds"
sound_seconds = 5.0

if not os.path.exists(output_dir):
    os.makedirs(output_dir)


def generate_sound(environment: gym.Env, action_fn: Callable, file_name: str, generate_chunk: int, sample_rate) -> None:
    """Generate sound wave with environment and action_fn

    Args:
        enviroment (env.PynkTrombone): Vocal tract environment.
        action_fn (Callable): Return action for generating waves with environment.
            This funcion must be able receive `PynkTrombone` environment and
            return action.
            Ex:
            >>> def update_fn(environment: env.PynkTrombone):
            ...     return action

        file_name (str): The file name of generated sound.

    Returns:
        wave (np.ndarray): Generated wave. 1d array.
    """

    roop_num = math.ceil(sound_seconds / (generate_chunk / sample_rate))
    generated_waves = []
    environment.reset()
    done = False
    for _ in range(roop_num):
        if done:
            environment.reset()

        action = action_fn(environment)
        obs, _, done, _ = environment.step(action)  # type: ignore
        generated_sound_wave = obs[OSN.GENERATED_SOUND_WAVE]
        generated_waves.append(generated_sound_wave)

    generated_sound_wave = np.concatenate(generated_waves).astype(np.float32)

    path = os.path.join(output_dir, file_name)
    soundfile.write(path, generated_sound_wave, sample_rate)


def test_do_nothing():
    dflt = environment.PynkTrombone(target_sound_files)

    def action_fn(e: environment.PynkTrombone) -> Mapping:

        act = {
            ASN.PITCH_SHIFT: np.array([0.0]),
            ASN.TENSENESS: np.array([0.0]),
            ASN.TRACHEA: np.array([0.6]),
            ASN.EPIGLOTTIS: np.array([1.1]),
            ASN.VELUM: np.array([0.01]),
            ASN.TONGUE_INDEX: np.array([20]),
            ASN.TONGUE_DIAMETER: np.array([2.0]),
            ASN.LIPS: np.array([1.5]),
        }
        return act

    generate_sound(dflt, action_fn, f"{__name__}.test_do_nothing.wav", dflt.generate_chunk, dflt.sample_rate)


def test_randomly():
    dflt = environment.PynkTrombone(target_sound_files)

    def action_fn(e: environment.PynkTrombone) -> Mapping:
        return e.action_space.sample()

    generate_sound(dflt, action_fn, f"{__name__}.test_randomly.wav", dflt.generate_chunk, dflt.sample_rate)
