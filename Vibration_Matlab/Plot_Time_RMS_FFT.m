%% ============================================================
% 1）读取 CSV（time, voltage）
% 2）电压 → 加速度(g)
% 3）绘制时域图
% 4）计算 1 秒 RMS 并绘图
% 5）计算 FFT（单边谱）并绘图
%% ============================================================

% === 选择 CSV 文件 ===
[fname, pathname] = uigetfile('*.csv', 'Select CSV File(V)');
if isequal(fname, 0)
    error('File selection canceled.');
end
filepath = fullfile(pathname, fname);
disp(filepath);

% === 读取 CSV 数据 ===
tic;
data = readmatrix(filepath);
fprintf('%.2f seconds - Data loaded\n', toc);

% === 检查列数 ===
[N, m] = size(data);
if m < 2
    error('CSV must have at least two columns (time and data).');
end

% === 提取时间与电压 ===
t = data(:, 1);      % 时间 (s)
x = data(:, 2);      % 电压 (V)

% === 电压 → 加速度 (g) ===
sensitivity = 1.026;   % 传感器灵敏度 (V/g)
gain = 100;            % 放大倍数
x = x / (sensitivity * gain);

% === 移除 NaN 数据点 ===
valid = ~isnan(t) & ~isnan(x);
t = t(valid);
x = x(valid);
N = length(t);
if N < 2
    error('Insufficient valid data.');
end

% === 检查时间步长是否单调 ===
dt = diff(t);
if any(dt <= 0)
    error('Time must be monotonically increasing.');
end

% === 推算采样率 Fs ===
Fs = 1 / mean(dt);
fprintf('%d samples\n', N);
fprintf('Sampling rate: %.2f Hz\n', Fs);

%% ---------------------- 时域图 ----------------------
tic;
figure(1);
plot(t, x);
xlabel('Time (s)');
ylabel('Accel (g)');
title(fname, 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - Time domain plot\n', toc);

%% ---------------------- 1秒 RMS 计算与绘图 ----------------------
tic;
w = floor(Fs);      % 每段 1 秒
steps = floor(N / w);
t_RMS = zeros(steps, 1);
x_RMS = zeros(steps, 1);

for i = 1:steps
    idx = ((i - 1) * w + 1):(i * w);   % 当前窗口的索引
    t_RMS(i) = mean(t(idx));          % 该段的平均时间
    x_RMS(i) = sqrt(mean(x(idx).^2)); % RMS 计算
end

figure(2);
plot(t_RMS, x_RMS);
xlabel('Time (s)');
ylabel('RMS Accel (g)');
title(['RMS - ' fname], 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - RMS computed and plotted\n', toc);

%% ---------------------- FFT 单边谱 ----------------------
tic;
xdft = fft(x) / N;                 % 归一化 FFT
xdft(2:end-1) = 2 * xdft(2:end-1); % 双边 → 单边谱
freq = (0:floor(N/2))' * (Fs / N); % 频率轴

figure(3);
plot(freq, abs(xdft(1:floor(N/2)+1)));
xlabel('Frequency (Hz)');
ylabel('Accel (g)');
title(['FFT - ' fname], 'Interpreter', 'none');
grid on;
fprintf('%.2f seconds - FFT computed and plotted\n', toc);
