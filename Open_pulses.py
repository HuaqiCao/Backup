import numpy as np

waveforms = np.load(r"D:\Backup\noise_waveforms.npy")

#print(waveforms.shape)        # (872, 3000)  →  872 noise waveforms, 3000 samples each

# Access a single waveform
waveforms[0]                  # first noise waveform
waveforms[43]                 # 43rd noise waveform

# Loop over all
for i, wf in enumerate(waveforms):
    print(i, wf.shape)        # (3000,)

# Plot one
import matplotlib.pyplot as plt
plt.plot(np.arange(3000) / 5000, waveforms[42])
plt.show()