clear;

% Select CSV file
[fname, pathname] = uigetfile('*.csv', 'Select CSV File');
if isequal(fname, 0)
    error('File selection canceled.');
end
filepath = fullfile(pathname, fname);
disp(filepath);

% Load CSV data
tic;
data = readmatrix(filepath);
fprintf('%.2f seconds - Data loaded\n', toc);

% Check data size
[N, m] = size(data);
if m < 2
    error('CSV must have at least two columns (time and data).');
end

% Extract time and signal
t = data(:, 1);
x = data(:, 2);

% Remove NaNs
valid = ~isnan(t) & ~isnan(x);
t = t(valid);
x = x(valid);
N = length(t);
if N < 2
    error('Insufficient valid data.');
end

% Check time increment
dt = diff(t);
if any(dt <= 0)
    error('Time must be monotonically increasing.');
end

% Calculate sampling rate
Fs = 1 / mean(dt);
fprintf('%d samples\n', N);
fprintf('Sampling rate: %.2f Hz\n', Fs);

%% ----- Time Domain Plot -----
tic;
figure(1);
plot(t, x);
xlabel('Time (s)');
ylabel('Accel (g)');
title(fname, 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - Time domain plot\n', toc);

%% ----- RMS Computation & Plot -----
tic;
w = floor(Fs); % 1-second window
steps = floor(N / w);
t_RMS = zeros(steps, 1);
x_RMS = zeros(steps, 1);

for i = 1:steps
    idx = ((i - 1) * w + 1):(i * w);
    t_RMS(i) = mean(t(idx));
    x_RMS(i) = sqrt(mean(x(idx).^2));
end

figure(2);
plot(t_RMS, x_RMS);
xlabel('Time (s)');
ylabel('RMS Accel (g)');
title(['RMS - ' fname], 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - RMS computed and plotted\n', toc);

%% ----- FFT Computation & Plot -----
tic;
xdft = fft(x) / N;
xdft(2:end-1) = 2 * xdft(2:end-1); % Convert to single-sided spectrum
freq = (0:floor(N/2))' * (Fs / N);

figure(3);
plot(freq, abs(xdft(1:floor(N/2)+1)));
xlabel('Frequency (Hz)');
ylabel('Accel (g)');
title(['FFT - ' fname], 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - FFT computed and plotted\n', toc);


