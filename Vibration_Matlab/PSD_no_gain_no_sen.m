% 选择多个 CSV 文件
[filenames, path] = uigetfile('*.csv', '选择多个加速度CSV文件', 'MultiSelect', 'on');
if isequal(filenames, 0)
    disp('取消选择');
    return;
end

% 参数设定
ref_resistance = 1;     % 参考电阻，单位欧姆
sensitivity = 1.026;    % V/g - 根据您的传感器规格修改
gain = 100.0;           % 放大器增益 - 根据您的系统修改
g = 9.81;               % 重力加速度 (m/s^2)

% 频段定义
band_edges = [1, 40; 40, 100; 1, 100]; % 频段边界 [Hz]
band_names = {'1-40 Hz', '40-100 Hz', '1-100 Hz'};

% 创建图形
figure_linear = figure('Name', 'PSD: g^2/Hz');
figure_dBm = figure('Name', 'PSD: dBm/Hz');
figure_lpsd_accel = figure('Name', 'LPSD: g/√Hz');
figure_lpsd_disp = figure('Name', 'LPSD: nm/√Hz');

% 初始化RMS结果存储
RMS_results = struct();

% 循环处理每个文件
for i = 1:length(filenames)
    file = fullfile(path, filenames{i});
    opts = detectImportOptions(file, 'NumHeaderLines', 4);
    data = readmatrix(file, opts);

    time = data(:,1);        % 时间（秒）
    voltage = data(:,2);     % 电压（V）
    
    % 转换为加速度值（除以增益和灵敏度）
    accel = voltage / (sensitivity * gain);
    
    % 去直流偏置
    voltage = voltage - mean(voltage);
    accel = accel - mean(accel);

    % 采样率估计
    dt = mean(diff(time));
    fs = 1 / dt;

    % Welch 方法参数
    nfft = 100000;
    window = hanning(nfft);
    overlap = nfft / 2;
    
    % 计算电压信号的PSD (V²/Hz)
    [pxx_voltage, f] = pwelch(voltage, window, overlap, nfft, fs);
    
    % 计算加速度PSD (g²/Hz)
    [pxx_accel, f] = pwelch(accel, window, overlap, nfft, fs);
    
    % 计算加速度LPSD (g/√Hz)
    lpsd_accel = sqrt(pxx_accel);
    
    % 计算位移LPSD (m/√Hz) - 使用公式: disp = accel / (2πf)^2
    % 注意：避免频率为0时除以0
    non_zero_freq = f > 0;
    lpsd_disp = zeros(size(f));
    lpsd_disp(non_zero_freq) = (g * lpsd_accel(non_zero_freq)) ./ ((2 * pi * f(non_zero_freq)).^2);
    lpsd_disp_nm = lpsd_disp * 1e9;  % 转换为nm/√Hz

    % === 图1：线性 PSD (单位 g^2/Hz) ===
    figure(figure_linear);
    loglog(f, pxx_accel, 'LineWidth', 1.5); hold on;

    % === 图2：dBm/Hz PSD ===
    pxx_watt_per_Hz = pxx_voltage / ref_resistance;
    pxx_dBm_per_Hz = 10 * log10(pxx_watt_per_Hz / 1e-3);
    figure(figure_dBm);
    semilogx(f, pxx_dBm_per_Hz, 'LineWidth', 1.5); hold on;
    
    % === 图3：加速度 LPSD (g/√Hz) ===
    figure(figure_lpsd_accel);
    loglog(f, lpsd_accel, 'LineWidth', 1.5); hold on;
    
    % === 图4：位移 LPSD (nm/√Hz) ===
    figure(figure_lpsd_disp);
    loglog(f(non_zero_freq), lpsd_disp_nm(non_zero_freq), 'LineWidth', 1.5); hold on;

    % 计算频段RMS值
    df = mean(diff(f));  % 频率分辨率
    RMS_results(i).filename = filenames{i};
    
    for b = 1:size(band_edges, 1)
        low_freq = band_edges(b, 1);
        high_freq = band_edges(b, 2);
        band_idx = f >= low_freq & f <= high_freq;
        
        % 加速度RMS (g)
        accel_rms = sqrt(sum(pxx_accel(band_idx) * df));
        RMS_results(i).(['accel_rms_' num2str(low_freq) '_' num2str(high_freq)]) = accel_rms;
        
        % 位移RMS (m) - 只在有效频率上计算
        disp_idx = band_idx & non_zero_freq;
        disp_psd = lpsd_disp(disp_idx).^2;  % PSD = (LPSD)^2
        disp_rms = sqrt(sum(disp_psd * df));
        RMS_results(i).(['disp_rms_' num2str(low_freq) '_' num2str(high_freq)]) = disp_rms;
    end

    % 打印状态
    fprintf('文件: %s，采样率 = %.2f Hz，点数 = %d\n', filenames{i}, fs, length(accel));
end

% 图像美化（线性PSD图）
figure(figure_linear);
xlabel('频率 (Hz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('PSD (g^2/Hz)', 'FontSize', 12, 'FontWeight', 'bold');
title('加速度功率谱密度 (线性坐标)', 'FontSize', 14, 'FontWeight', 'bold');
grid on;
legend(filenames, 'Interpreter', 'none', 'Location', 'best');
set(gca, 'FontSize', 10, 'XScale', 'log', 'YScale', 'log');
axis tight; % 让数据填充整个坐标轴区域
set(gcf, 'Color', 'w'); % 设置背景为白色

% 图像美化（dBm/Hz图）
figure(figure_dBm);
xlabel('频率 (Hz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('PSD (dBm/Hz)', 'FontSize', 12, 'FontWeight', 'bold');
title('等效功率谱密度 (dBm/Hz)', 'FontSize', 14, 'FontWeight', 'bold');
grid on;
legend(filenames, 'Interpreter', 'none', 'Location', 'best');
set(gca, 'FontSize', 10, 'XScale', 'log');
axis tight; % 让数据填充整个坐标轴区域
set(gcf, 'Color', 'w'); % 设置背景为白色

% 图像美化（加速度LPSD图）
figure(figure_lpsd_accel);
xlabel('频率 (Hz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('LPSD (g/√Hz)', 'FontSize', 12, 'FontWeight', 'bold');
title('加速度线性功率谱密度', 'FontSize', 14, 'FontWeight', 'bold');
grid on;
legend(filenames, 'Interpreter', 'none', 'Location', 'best');
set(gca, 'FontSize', 10, 'XScale', 'log', 'YScale', 'log');
axis tight; % 让数据填充整个坐标轴区域
set(gcf, 'Color', 'w'); % 设置背景为白色

% 图像美化（位移LPSD图）
figure(figure_lpsd_disp);
xlabel('频率 (Hz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('LPSD (nm/√Hz)', 'FontSize', 12, 'FontWeight', 'bold');
title('位移线性功率谱密度', 'FontSize', 14, 'FontWeight', 'bold');
grid on;
legend(filenames, 'Interpreter', 'none', 'Location', 'best');
set(gca, 'FontSize', 10, 'XScale', 'log', 'YScale', 'log');
axis tight; % 让数据填充整个坐标轴区域
set(gcf, 'Color', 'w'); % 设置背景为白色

% 创建RMS结果表格图形
figure_rms = figure('Name', 'RMS结果表', 'Color', 'white', 'Position', [100, 100, 1200, 400]);

% 准备表格数据
row_names = {};
data_cell = cell(length(RMS_results), 6); % 3个频段 × 2个值（加速度+位移）

for i = 1:length(RMS_results)
    row_names{end+1} = RMS_results(i).filename;
    
    for b = 1:size(band_edges, 1)
        low_freq = band_edges(b, 1);
        high_freq = band_edges(b, 2);
        
        accel_rms = RMS_results(i).(['accel_rms_' num2str(low_freq) '_' num2str(high_freq)]);
        disp_rms = RMS_results(i).(['disp_rms_' num2str(low_freq) '_' num2str(high_freq)]);
        
        % 格式化加速度RMS值
        if accel_rms < 1e-3
            accel_str = sprintf('%.2f µg', accel_rms * 1e6);
        else
            accel_str = sprintf('%.4f mg', accel_rms * 1e3);
        end
        
        % 格式化位移RMS值
        if disp_rms < 1e-9
            disp_str = sprintf('%.2f pm', disp_rms * 1e12);
        else
            disp_str = sprintf('%.2f nm', disp_rms * 1e9);
        end
        
        % 将结果放入表格单元格
        data_cell{i, (b-1)*2+1} = accel_str;
        data_cell{i, (b-1)*2+2} = disp_str;
    end
end

% 设置列名
col_names = {'[1–40] Hz Acc','[1–40] Hz Disp','[40–100] Hz Acc','[40–100] Hz Disp','[1–100] Hz Acc','[1–100] Hz Disp'};

% 创建表格
t = uitable(figure_rms, 'Data', data_cell, ...
            'RowName', row_names, ...
            'ColumnName', col_names, ...
            'Units', 'normalized', ...
            'Position', [0.05, 0.05, 0.9, 0.9], ...
            'FontSize', 12, ...
            'ColumnWidth', num2cell(repmat(150, 1, 6)), ...
            'ColumnEditable', false(1, 6));

% 设置表格样式
set(t, 'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0]);
set(t, 'RowStriping', 'on'); % 启用行条纹

% 设置表格标题
annotation(figure_rms, 'textbox', [0.05, 0.95, 0.9, 0.05], ...
           'String', 'RMS结果表', ...
           'FontSize', 14, 'FontWeight', 'bold', ...
           'HorizontalAlignment', 'center', ...
           'EdgeColor', 'none');

% 显示RMS结果（命令行）
fprintf('\n================ RMS 结果 ================\n');
fprintf('%-30s', '文件名');
for b = 1:length(band_names)
    fprintf('%-20s %-20s', [band_names{b} ' Acc RMS'], [band_names{b} ' Disp RMS']);
end
fprintf('\n');

for i = 1:length(RMS_results)
    fprintf('%-30s', RMS_results(i).filename);
    for b = 1:size(band_edges, 1)
        low_freq = band_edges(b, 1);
        high_freq = band_edges(b, 2);
        
        accel_rms = RMS_results(i).(['accel_rms_' num2str(low_freq) '_' num2str(high_freq)]);
        disp_rms = RMS_results(i).(['disp_rms_' num2str(low_freq) '_' num2str(high_freq)]);
        
        % 格式化输出
        if accel_rms < 1e-3
            accel_str = sprintf('%.2f µg', accel_rms * 1e6);
        else
            accel_str = sprintf('%.4f mg', accel_rms * 1e3);
        end
        
        if disp_rms < 1e-9
            disp_str = sprintf('%.2f pm', disp_rms * 1e12);
        else
            disp_str = sprintf('%.2f nm', disp_rms * 1e9);
        end
        
        fprintf('%-20s %-20s', accel_str, disp_str);
    end
    fprintf('\n');
end
fprintf('==========================================\n');