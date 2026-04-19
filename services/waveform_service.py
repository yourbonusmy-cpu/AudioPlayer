import numpy as np
from pydub import AudioSegment

class WaveformService:
    def generate(self, path, samples=400):
        audio = AudioSegment.from_file(path)
        data = np.array(audio.get_array_of_samples())

        chunk = max(1, len(data)//samples)
        wf = [int(np.max(abs(data[i:i+chunk]))) for i in range(0, len(data), chunk)]

        return wf[:samples]