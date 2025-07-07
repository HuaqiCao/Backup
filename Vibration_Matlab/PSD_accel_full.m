% 选择多个 CSV 文件
[filenames, path] = uigetfile('*.csv', '选择多个加速度CSV文件', 'MultiSelect', 'on');
if isequal(filenames, 0)
    disp('取消选择');
    return;
end

% 保证 filenames 是 cell 数组
if ~iscell(filenames)
    filenames = {filenames};
end

% 参数设定
ref_resistance = 1;  % 参考电阻，单位欧姆，用于等效功率计算（默认1Ω）

% 图像句柄
figure_linear = figure('Name', 'PSD: g^2/Hz');
figure_dBm = figure('Name', 'PSD: dBm/Hz');

% 循环处理每个文件
for i = 1:length(filenames)
    file = fullfile(path, filenames{i});
    opts = detectImportOptions(file, 'NumHeaderLines', 4);
    data = readmatrix(file, opts);

    time = data(:,1);        % 时间（秒）
    accel = data(:,2);       % 加速度（g）

    % 去直流偏置
    accel = accel - mean(accel);

    % 采样率估计
    dt = mean(diff(time));
    fs = 1 / dt;

    % Welch 方法参数
    nfft = 2^nextpow2(length(accel)/8);
    window = hamming(nfft);
    overlap = round(0.5 * nfft);
    [pxx, f] = pwelch(accel, window, overlap, nfft, fs);

    % === 图1：线性 PSD (单位 g^2/Hz) ===
    figure(figure_linear);
    loglog(f, pxx, 'LineWidth', 1.2); hold on;

    % === 图2：dBm/Hz PSD ===
    % 将 g^2/Hz → 视为功率密度 (W/Hz)，再换算为 dBm
    % 1. g^2/Hz → "等效功率密度"（此处直接假设为 W/Hz）
    pxx_watt_per_Hz = pxx / ref_resistance; % "g^2" → W 假定映射
    pxx_dBm_per_Hz = 10 * log10(pxx_watt_per_Hz / 1e-3); % 转换为 dBm/Hz

    figure(figure_dBm);
    semilogx(f, pxx_dBm_per_Hz, 'LineWidth', 1.2); hold on;

    % 打印状态
    fprintf('文件: %s，采样率 = %.2f Hz，点数 = %d\n', filenames{i}, fs, length(accel));
end

% 图像美化（线性图）
figure(figure_linear);
xlabel('频率 (Hz)');
ylabel('PSD (g^2/Hz)');
title('加速度功率谱密度 (线性坐标)');
grid on;
legend(filenames, 'Interpreter', 'none');

% 图像美化（dBm/Hz 图）
figure(figure_dBm);
xlabel('频率 (Hz)');
ylabel('PSD (dBm/Hz)');
title('等效功率谱密度 (dBm/Hz)');
grid on;
legend(filenames, 'Interpreter', 'none');
