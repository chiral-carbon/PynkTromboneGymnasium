import copy
import math
from collections import OrderedDict
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
)

import gymnasium as gym
import numpy as np
from gymnasium import spaces
from pynktrombone import Voc

from . import spectrogram as spct
from .renderer import Renderer
from .spaces import ActionSpaceNames as ASN
from .spaces import ObservationSpaceNames as OSN

RenderFrame = TypeVar("RenderFrame", np.ndarray, Any)


class PynkTrombone(gym.Env):
    r"""The vocal tract environment for speech generation.

    The main API methods that users of this class need to know are:
    - :meth:`__init__`  - Constructor of this enviroment.
    - :meth:`set_target_sound_files` - You must call `reset` method after this method.
    - :meth:`initialize_state` - Initialize internal environment state.
    - :meth:`get_current_observation` - Returns current observation values.
    - :meth:`reset` - Gym API. Reset this environment state.
    - :meth:`step` - Gym API. Step this environment.
    - :meth:`render` - Gym API. render this environment state.

    And set the following attributes:
    - :attr:`target_sound_files` - The list of paths to the target sound file.
    - :attr:`sample_rate` - The generating resolution of this vocal tract model.
    - :attr:`generate_chunk` - Length generated in 1 :meth:`step`.
    - :attr:`stft_window_size` - Window size of stft.
    - :attr:`stft_hop_length` - Hopping length of stft.
    - :attr:`target_sound_wave` - Current target sound wave array.
    - :attr:`generated_sound_wave` - Generated current sound wave array.
    - :attr:`done` - Whether this environment has done or not.
    - :attr:`max_steps` - The number of limit that we can call :meth:`step`.
    - :attr:`current_step` - The number of times :meth:`step` has been called.
    - :attr:`voc` - The vocal tract model class.
    - :attr:`renderer` - The renderer class does internal process of :meth:`render`

    And other Gym API attrs and methods are available.
    """

    def __init__(
        self,
        target_sound_files: Sequence[str],
        sample_rate: int = 44100,
        default_frequency: float = 400.0,
        generate_chunk: int = 1024,
        stft_window_size: int = 1024,
        stft_hop_length: int = None,
        rendering_figure_size: tuple[float, float] = (6.4, 4.8),
        render_mode:str = "rgb_array",
    ):
        """Contructs environment. Setup `Voc`, deine spaces, and reset environment.

        Args:
            target_sound_files (Sequence[str]): Target sounds to imitate by vocal tract model.
            sample_rate (int): Resolution of sound wave.
                Target sounds and generation wave frequency are set to this.
            default_frequency (float): Base of glottis frequency.
            generate_chunk (int): Length generated in 1 step.
            stft_window_size (int): Window size of stft.
            stft_hop_length (int): Hop length of stft.
            rendering_figure_size (tuple[float, float]): The figure size of rendering image. [Inch]
        """

        self.set_target_sound_files(target_sound_files)
        self.sample_rate = sample_rate
        self.default_frequency = default_frequency
        self.generate_chunk = generate_chunk
        self.stft_window_size = stft_window_size
        if stft_hop_length is None:
            stft_hop_length = int(stft_window_size / 4)
        self.stft_hop_length = stft_hop_length

        self.initialize_state()

        self.renderer = Renderer(self.voc, rendering_figure_size)

        self.action_space = self.define_action_space()
        self.observation_space = self.define_observation_space()
        self.reward_range = self.define_reward_range()
        self.render_mode = render_mode

    @property
    def target_sound_wave(self) -> np.ndarray:
        """Returns sliced `target_sound_wave_full` at `current_step`"""
        wave = self.target_sound_wave_full[
            self.current_step * self.generate_chunk : (self.current_step + 1) * self.generate_chunk
        ]
        return spct.pad_tail(wave, self.generate_chunk)

    @property
    def generated_sound_wave(self) -> np.ndarray:
        """Returns generated sound wave at `current_step`"""
        return self._generated_sound_wave_2chunks[-self.generate_chunk :]

    def set_target_sound_files(self, file_paths: Sequence[str]) -> None:
        """Set `file_paths` to `self.target_sound_files`
        Args:
            file_paths (Iterable[str]): Paths to target sound files.
        Raises:
            ValueError: When empty file paths are provieded.
        """
        if len(file_paths) == 0:
            raise ValueError("Provided target sound files are empty!")
        self.target_sound_files = file_paths

    def initialize_state(self) -> None:
        """Initialize this enviroment state."""
        self.current_step = 0
        self.target_sound_wave_full = self.load_sound_wave_randomly()
        self._generated_sound_wave_2chunks = np.zeros(self.generate_chunk * 2, dtype=np.float32)
        self.voc = Voc(self.sample_rate, self.generate_chunk, default_freq=self.default_frequency)
        self._rendered_rgb_arrays: List[np.ndarray] = []

    action_space: spaces.Box

    def define_action_space(self) -> spaces.Box:
        """Defines action space of this environment."""
        self.dict_action_space = spaces.Dict(
            {
                ASN.PITCH_SHIFT: spaces.Box(-1.0, 1.0),
                ASN.TENSENESS: spaces.Box(0.0, 1.0),
                ASN.TRACHEA: spaces.Box(0, 3.5),
                ASN.EPIGLOTTIS: spaces.Box(0, 3.5),
                ASN.VELUM: spaces.Box(0, 3.5),
                ASN.TONGUE_INDEX: spaces.Box(12, 40, dtype=np.float32),  # Float type is correct.
                ASN.TONGUE_DIAMETER: spaces.Box(0, 3.5),
                ASN.LIPS: spaces.Box(0, 1.5),
            }
        )
        
        # return self.dict_action_space
        
        # lower_bounds = np.array([
        #     -1.0,  # PITCH_SHIFT
        #     0.0,   # TENSENESS
        #     0.0,   # TRACHEA
        #     0.0,   # EPIGLOTTIS
        #     0.0,   # VELUM
        #     12.0,  # TONGUE_INDEX
        #     0.0,   # TONGUE_DIAMETER
        #     0.0,   # LIPS
        # ])

        # # Define the upper bounds for each action space
        # upper_bounds = np.array([
        #     1.0,  # PITCH_SHIFT
        #     1.0,  # TENSENESS
        #     3.5,  # TRACHEA
        #     3.5,  # EPIGLOTTIS
        #     3.5,  # VELUM
        #     40.0, # TONGUE_INDEX
        #     3.5,  # TONGUE_DIAMETER
        #     1.5,  # LIPS
        # ])
        
        lower_bounds = np.array([
            -1.0,  # PITCH_SHIFT
            -1.0,  # TENSENESS
            -1.0,  # TRACHEA
            -1.0,  # EPIGLOTTIS
            -1.0,  # VELUM
            -1.0,  # TONGUE_INDEX
            -1.0,  # TONGUE_DIAMETER
            -1.0,  # LIPS
        ])

        # Define the upper bounds for each action space
        upper_bounds = np.array([
            1.0,  # PITCH_SHIFT
            1.0,  # TENSENESS
            1.0,  # TRACHEA
            1.0,  # EPIGLOTTIS
            1.0,  # VELUM
            1.0,  # TONGUE_INDEX
            1.0,  # TONGUE_DIAMETER
            1.0,  # LIPS
        ])

        # Create the combined Box space
        combined_action_space = spaces.Box(low=lower_bounds, high=upper_bounds, dtype=np.float32)
        return combined_action_space

    observation_space: spaces.Dict

    def define_observation_space(self) -> spaces.Dict:
        """Defines observation space of this enviroment."""

        spct_shape = (
            spct.calc_rfft_channel_num(self.stft_window_size),
            spct.calc_target_sound_spectrogram_length(self.generate_chunk, self.stft_window_size, self.stft_hop_length),
        )

        observation_space = spaces.Dict(
            {
                OSN.TARGET_SOUND_WAVE: spaces.Box(-1.0, 1.0, (self.generate_chunk,)),
                OSN.GENERATED_SOUND_WAVE: spaces.Box(-1.0, 1.0, (self.generate_chunk,)),
                OSN.TARGET_SOUND_SPECTROGRAM: spaces.Box(0, float("inf"), spct_shape),
                OSN.GENERATED_SOUND_SPECTROGRAM: spaces.Box(0, float("inf"), spct_shape),
                OSN.FREQUENCY: spaces.Box(0, self.sample_rate // 2),
                OSN.PITCH_SHIFT: spaces.Box(-1.0, 1.0),
                OSN.TENSENESS: spaces.Box(0.0, 1.0),
                OSN.CURRENT_TRACT_DIAMETERS: spaces.Box(0.0, 5.0, (self.voc.tract_size,)),
                OSN.NOSE_DIAMETERS: spaces.Box(0.0, 5.0, (self.voc.nose_size,)),
            }
        )

        return observation_space

    def define_reward_range(self) -> Tuple[float, float]:
        """Define reward range of this environment.
        Reward is computed by measuring MSE between
        target_sound_spectrogram and generated_sound, and times -1.

        Range: [-inf, 0]
        """
        reward_range = (-float("inf"), 0.0)
        return reward_range

    def load_sound_wave_randomly(self) -> np.ndarray:
        """Load sound file randomly.

        Return:
            waveform (ndarray): 1d numpy array, dtype is float32,
        """

        file_index = np.random.randint(0, len(self.target_sound_files))
        wave = spct.load_sound_file(self.target_sound_files[file_index], self.sample_rate)
        return wave

    def get_target_sound_spectrogram(self) -> np.ndarray:
        """Slice target sound full wave and convert it to spectrogram.

        Returns:
            spectrogram (ndarray): Sliced target sound wave spectrogram.
                Shape -> (C, L)
                Dtype -> float32
        """
        if self.current_step == 0:
            wave = self.target_sound_wave_full[: self.generate_chunk]
            wave = spct.pad_tail(wave, self.generate_chunk)
        else:
            wave = self.target_sound_wave_full[
                (self.current_step - 1) * self.generate_chunk : (self.current_step + 1) * self.generate_chunk
            ]
            wave = spct.pad_tail(wave, 2 * self.generate_chunk)

        length = spct.calc_target_sound_spectrogram_length(
            self.generate_chunk, self.stft_window_size, self.stft_hop_length
        )
        spect = spct.stft(wave, self.stft_window_size, self.stft_hop_length)[-length:]
        spect = np.abs(spect).T.astype(np.float32)
        return spect

    def get_generated_sound_spectrogram(self) -> np.ndarray:
        """Convert generated sound wave to spectrogram

        There is `_generated_sound_wave_2chunks` as private variable,
        it contains previous and current generated wave for computing
        stft naturally.

        Returns:
            spectrogram (ndarray): A spectrogram of generated sound wave.
                Shape -> (C, L)
                Dtype -> float32
        """
        length = spct.calc_target_sound_spectrogram_length(
            self.generate_chunk, self.stft_window_size, self.stft_hop_length
        )

        spect = spct.stft(self._generated_sound_wave_2chunks, self.stft_window_size, self.stft_hop_length)
        spect = np.abs(spect[-length:]).T.astype(np.float32)
        return spect

    def get_current_observation(self) -> OrderedDict:
        """Return current observation.

        Return:
            observation (OrdereDict): observation.
        """
        target_sound_wave = self.target_sound_wave.astype(np.float32)
        generated_sound_wave = self.generated_sound_wave.astype(np.float32)
        target_sound_spectrogram = self.get_target_sound_spectrogram().astype(np.float32)
        generated_sound_spectrogram = self.get_generated_sound_spectrogram().astype(np.float32)
        frequency = np.array([self.voc.frequency], dtype=np.float32)
        pitch_shift = np.log2(frequency / self.default_frequency, dtype=np.float32)
        tenseness = np.array([self.voc.tenseness], dtype=np.float32)
        tract_diameters = self.voc.current_tract_diameters.astype(np.float32)
        nose_diameters = self.voc.nose_diameters.astype(np.float32)

        obs = OrderedDict(
            {
                OSN.TARGET_SOUND_WAVE: target_sound_wave,
                OSN.GENERATED_SOUND_WAVE: generated_sound_wave,
                OSN.TARGET_SOUND_SPECTROGRAM: target_sound_spectrogram,
                OSN.GENERATED_SOUND_SPECTROGRAM: generated_sound_spectrogram,
                OSN.FREQUENCY: frequency,
                OSN.PITCH_SHIFT: pitch_shift,
                OSN.TENSENESS: tenseness,
                OSN.CURRENT_TRACT_DIAMETERS: tract_diameters,
                OSN.NOSE_DIAMETERS: nose_diameters,
            }
        )

        return obs

    def reset(
        self, seed: Optional[int] = None, options: Optional[dict] = None
    ) -> Tuple[OrderedDict, dict]:
        """Reset this enviroment.
        Choice sound file randomly and load it as waveform.
        Internal vocal tract model `Voc` is reconstructed too.

        Returns:
            observation (OrderedDict): Initial observation of this enviroment.
        """
        super().reset(seed=seed, options=options)

        self.initialize_state()
        obs = self.get_current_observation()
        return obs, {}

    def compute_reward(self, target, generated, info={}) -> float:
        """Compute current reward.
        Measure 'minus' MSE between target and generated.

        Returns:
            reward (float):  Computed reward value.
        """

        return -mean_squared_error(generated, target)

    @property
    def done(self) -> bool:
        """Check if enviroment has done."""
        return self.current_step * self.generate_chunk >= len(self.target_sound_wave_full)

    @property
    def max_steps(self) -> int:
        """Returns max step number of this environment."""
        return math.ceil(len(self.target_sound_wave_full) / self.generate_chunk)

    def step(self, action: Mapping) -> Tuple[OrderedDict, float, bool, dict]:
        """Step this enviroment by action.

        Args:
            action (OrderedDict): Dict of action values.

        Returns:
            observation (OrderedDict): Next step observation.
            reward (float): Reward of current step.
            done (bool): Whether the environment has been finished or not.
            info (dict): Debug informations.

        Raises:
            RuntimeError: If done is True, raises runtime error.
                Please call `reset` method of this enviroment.
        """
        mapped_actions = {}
        if isinstance(action, dict):
            mapped_actions = action
        elif isinstance(action, (np.ndarray,list)):
            for i, key in enumerate(sorted(self.dict_action_space.spaces.keys())):
                mapped_actions[key] = action[i]
        else:
            raise ValueError(f"Unexpected action type: {type(action)}")
        
        # De-Normalize action values to the environment's range
        mapped_actions = {
            ASN.PITCH_SHIFT: mapped_actions[ASN.PITCH_SHIFT],
            ASN.TENSENESS: (mapped_actions[ASN.TENSENESS] + 1) * 0.5,
            ASN.TRACHEA: (mapped_actions[ASN.TRACHEA] + 1) * 1.75,
            ASN.EPIGLOTTIS: (mapped_actions[ASN.EPIGLOTTIS] + 1) * 1.75,
            ASN.VELUM: (mapped_actions[ASN.VELUM] + 1)* 1.75,
            ASN.TONGUE_INDEX: (mapped_actions[ASN.TONGUE_INDEX]+1)*28+12,
            ASN.TONGUE_DIAMETER: (mapped_actions[ASN.TONGUE_DIAMETER]+1)*1.75,
            ASN.LIPS: (mapped_actions[ASN.LIPS]+1)*0.75
        }

        if self.done:
            raise RuntimeError("This environment has been finished. Please call `reset` method.")

        info: Dict[Any, Any] = dict()

        pitch_shift: np.ndarray = mapped_actions[ASN.PITCH_SHIFT]
        tenseness: np.ndarray = mapped_actions[ASN.TENSENESS]
        trachea: np.ndarray = mapped_actions[ASN.TRACHEA]
        epiglottis: np.ndarray = mapped_actions[ASN.EPIGLOTTIS]
        velum: np.ndarray = mapped_actions[ASN.VELUM]
        tongue_index: np.ndarray = mapped_actions[ASN.TONGUE_INDEX]
        tongue_diameter: np.ndarray = mapped_actions[ASN.TONGUE_DIAMETER]
        lips: np.ndarray = mapped_actions[ASN.LIPS]

        self.voc.frequency = self.default_frequency * (2 ** pitch_shift.item())
        self.voc.tenseness = tenseness.item()
        self.voc.set_tract_parameters(
            trachea.item(),
            epiglottis.item(),
            velum.item(),
            tongue_index.item(),
            tongue_diameter.item(),
            lips.item(),
        )

        generated_wave = self.voc.play_chunk()
        self._generated_sound_wave_2chunks = np.concatenate([self.generated_sound_wave, generated_wave])


        ##### Next step #####
        self.current_step += 1
        done = self.done
        obs = self.get_current_observation()
        target = obs[OSN.TARGET_SOUND_SPECTROGRAM]
        generated = obs[OSN.GENERATED_SOUND_SPECTROGRAM]
        reward = self.compute_reward(target, generated, {})  # Minus error between generated and 'current' target.

        truncated = False
        return obs, reward, done, truncated, info

    def render(
        self, mode: Optional[Literal["rgb_arrays", "single_rgb_array"]] = None
    ) -> Optional[Union[RenderFrame, List[RenderFrame]]]:
        """Render a figure of current Vocal Tract diameters and etc.

        Args:
            mode (Optional[Literal]): Rendering mode.
                - None: Render rgb_array and store it.
                - "rgb_arrays": Return all rendered array. (NOT render new image.)
                - "single_rgb_array": Return all rgb array of figure.
                Note: "rgb_arrays" mode returns all stored figures and clear list.

        Returns:
            image (Optional[Union[RenderFrame, List[RenderFrame]]]): Renderd image or images.

        Raises:
            NotImplementedError: When mode is unexpected value.
        """
        if mode == "rgb_arrays":
            arrays = copy.copy(self._rendered_rgb_arrays)
            self._rendered_rgb_arrays.clear()
            return arrays

        self.renderer.update_values()
        rgb_array = self.renderer.render_rgb_array()
        if mode is None:
            self._rendered_rgb_arrays.append(rgb_array)
            return None
        elif mode == "single_rgb_array":
            return rgb_array
        else:
            raise NotImplementedError(f"Render mode {mode} is not implemented!")

    def close(self):
        self.renderer.close()
        return super().close()


def mean_squared_error(output: np.ndarray, target: np.ndarray) -> Union[float, np.ndarray]:
    """Compute mse.
    Output and Target must have same shape.

    Args:
        output (ndarray): The output of model.
        target (ndarray): Target of output

    Returns:
        mse (float): Mean Squared Error.
    """
    delta = output - target
    if delta.ndim == 2:
        delta = np.expand_dims(delta, axis=0)
    mse = np.mean(delta * delta, axis=(1,2))
    mse = np.round(mse, 4)

    if mse.shape[0] == 1:
        mse = float(mse[0])
    return mse
