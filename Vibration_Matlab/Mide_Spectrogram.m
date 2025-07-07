function [x_3D, y_3D, z_3D] = Mide_Spectrogram(datalist, fActual, nSlicesPerSecond)
% Mide_Spectrogram - Computes a spectrogram from time-series data
%
% Inputs:
%   datalist          - [time, signal] matrix
%   fActual           - Sampling rate (Hz)
%   nSlicesPerSecond  - Number of time slices per second
%
% Outputs:
%   x_3D - Time axis
%   y_3D - Frequency axis
%   z_3D - Spectrogram amplitude

% Get total number of samples
nPts = length(datalist(:,1));
signal = datalist(:,2);
nPointsPerSlice = floor(fActual / nSlicesPerSecond);

% Adjust slice size if invalid
if nPointsPerSlice == 0 || nPointsPerSlice > nPts
    disp('Adjusted slice size due to invalid value.');
    nPointsPerSlice = floor(nPts / 4);
end

% Truncate and reshape signal
nSlices = floor(length(signal) / nPointsPerSlice);
signal = reshape(signal(1:nSlices * nPointsPerSlice), nPointsPerSlice, []);
[fftrows, fftcols] = size(signal);

% Frequency vector (normalized)
x = 0:fftrows-1;
sliceTime = datalist(fftrows,1) - datalist(1,1);
sliceTime = sliceTime + (sliceTime / fftrows);
x = x * (1 / sliceTime);

% Hamming window
w = 0.53836 - 0.46164 * cos(2 * pi * (1:fftrows)' / (fftrows - 1));

% Apply FFT with windowing
yabs = zeros(size(signal));
for j = 1:fftcols
    windowed = signal(:,j) .* w;
    ffted = fft(windowed);
    yabs(:,j) = abs(ffted) / (0.5 * length(ffted));
    yabs(1,j) = 0; % Remove DC
end

% Select frequency range to display
nPOI = floor(nPointsPerSlice / 2);
startPOI = 1;
endPOI = min(nPOI, floor(length(x)/2));

% Spectrogram output
x_3D = (1:fftcols) / nSlicesPerSecond;
y_3D = x(startPOI+1:endPOI+1);
z_3D = yabs(startPOI+1:endPOI+1, :);
end
