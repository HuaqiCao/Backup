%% ================================================================
% 1）选择多个 CSV（前4行为表头），第1列时间(s)，第2列加速度(g)
% 2）对每个文件计算 Welch PSD
% 3）绘制：
%     - 线性 PSD（g^2/Hz）
%     - dBm/Hz（假设 g^2 等效为 1Ω 负载上的功率）
% ================================================================

% === 选择多个 CSV 文件 ===
[filenames, path] = uigetfile('*.csv', '选择多个加速度CSV文件', 'MultiSelect', 'on');
if isequal(filenames, 0)
    disp('取消选择');
    return;
end

% === 参数 ===
ref_resistance = 1;     % 参考电阻（用于等效功率密度），默认 1 Ω

% === 创建两个图窗 ===
figure_linear = figure('Name', 'PSD: g^2/Hz');
figure_dBm    = figure('Name', 'PSD: dBm/Hz');

% === 循环处理每个文件 ===
for i = 1:length(filenames)
    file = fullfile(path, filenames{i});

    % 读取 CSV（跳过4行表头）
    opts = detectImportOptions(file, 'NumHeaderLines', 4);
    data = readmatrix(file, opts);
    time  = data(:,1);         % 时间
    accel = data(:,2);         % 加速度(g)

    % 若需要可打开去直流
    % accel = accel - mean(accel);

    % --- 采样率 ---
    dt = mean(diff(time));
    fs = 1 / dt;

    % --- Welch PSD 参数 ---
    nfft = 100000;
    window = hanning(nfft);
    overlap = nfft / 2;        % 修正原代码笔误 Nfft → nfft
    [pxx, f] = pwelch(accel, window, overlap, nfft, fs);

    % === 图1：线性 PSD (g^2/Hz) ===
    figure(figure_linear);
    loglog(f, pxx, 'LineWidth', 1.2); hold on;

    % === 图2：等效 dBm/Hz ===
    % g^2/Hz → W/Hz（假设等效映射到 1Ω）
    pxx_watt_per_Hz = pxx / ref_resistance;  
    pxx_dBm_per_Hz = 10 * log10(pxx_watt_per_Hz / 1e-3);

    figure(figure_dBm);
    semilogx(f, pxx_dBm_per_Hz, 'LineWidth', 1.2); hold on;

    % 状态输出
    fprintf('文件: %s，采样率 = %.2f Hz，点数 = %d\n', filenames{i}, fs, length(accel));
end

% === 线性 PSD 美化 ===
figure(figure_linear);
xlabel('频率 (Hz)');
ylabel('PSD (g^2/Hz)');
title('加速度功率谱密度 (线性坐标)');
grid on;
legend(filenames, 'Interpreter', 'none');

% === dBm/Hz 图美化 ===
figure(figure_dBm);
xlabel('频率 (Hz)');
ylabel('PSD (dBm/Hz)');
title('等效功率谱密度 (dBm/Hz)');
grid on;
legend(filenames, 'Interpreter', 'none');
