%% 参数设置
Fs = 10000;
Nfft = 100000;
window = hann(Nfft);
window = window / sqrt(mean(window.^2));
overlap = Nfft / 2;
sensitivity = 1.026;
ref_resistance = 1;
g = 9.81;

% 根据实际导入的文件调整信号名称和图例
signal_names = {'Vibration_Data', 'Brass'}; % 只保留前两个信号
legend_labels = {'Vibration Input', 'c=100'}; % 只保留前两个标签
colors = {[1.0, 0.5, 0.0], [1.0, 0.85, 0.0]}; % 只保留前两个颜色

[filenames, path] = uigetfile('*.csv', '选择两个CSV文件', 'Multiselect', 'on');
if isequal(filenames, 0), disp('❌ 取消导出'); return; end
if ~iscell(filenames), filenames = {filenames}; end

% 确保只处理两个文件
if length(filenames) > 2
    filenames = filenames(1:2);
    disp('⚠️ 只处理前两个文件');
end

PSD_stack = {}; PSD_stack_voltage = {}; F_all = {};
actual_signal_names = {};  % 存储实际处理的信号名称

% 处理信号数据
for i = 1:min(length(filenames), length(signal_names))
    name = signal_names{i}; 
    if isfield(out, name)
        ts = out.(name);
        if isa(ts, 'timeseries')
            t = ts.Time; y = ts.Data;
        elseif isstruct(ts)
            t = ts.time; y = ts.signals.values;
        else
            warning('⚠️ 跳过未知结构 %s', name); continue;
        end
        
        y_v = y;
        y_g = y / sensitivity;
        [pxx_g, f] = pwelch(y_g, window, overlap, Nfft, Fs, 'psd');
        [pxx_v, ~] = pwelch(y_v, window, overlap, Nfft, Fs, 'psd');
        
        PSD_stack{end+1} = pxx_g;
        PSD_stack_voltage{end+1} = pxx_v;
        F_all{end+1} = f;
        actual_signal_names{end+1} = name;
    else
        warning('⚠️ 跳过未找到的信号: %s', name);
    end
end

num_signals = length(PSD_stack);
if num_signals == 0
    error('❌ 没有找到有效信号数据');
end

% 动态生成图例标签（只使用前两个）
row_names = legend_labels(1:num_signals);

LPSD_all = {}; LPSD_disp_all = {}; RMS_table = [];
PSD_dBm_all = {}; PSD_dBm_Watt_all = {};
LPSD_dBm_all = {}; LPSD_dBm_Watt_all = {};

% 频段边界
band_edges = [1, 40; 40, 100; 1, 100]; % 增加了 [1, 100] Hz 频段

% 计算PSD和LPSD
for i = 1:num_signals
    pxx_g = PSD_stack{i};
    pxx_v = PSD_stack_voltage{i};
    f = F_all{i};
    
    % LPSD计算
    lpsd = sqrt(pxx_g);
    lpsd_disp = g ./ ((2*pi*f).^2) .* lpsd;
    
    % dBm计算
    psd_dBm = 10 * log10(pxx_v / 1e-6);
    psd_dBm_W = 10 * log10(pxx_v / ref_resistance / 1e-3);
    lpsd_dBm = 20 * log10(sqrt(pxx_v)) - 10 * log10(ref_resistance) - 30;

    % 存储结果
    LPSD_all{i} = lpsd;
    LPSD_disp_all{i} = lpsd_disp;
    PSD_dBm_all{i} = psd_dBm;
    PSD_dBm_Watt_all{i} = psd_dBm_W;
    LPSD_dBm_all{i} = lpsd_dBm;
    LPSD_dBm_Watt_all{i} = lpsd_dBm;

    % RMS计算
    df = mean(diff(f));
    RMS_segment = zeros(1, size(band_edges,1)*2);
    for j = 1:size(band_edges,1)
        idx = f >= band_edges(j,1) & f <= band_edges(j,2);
        RMS_d = sqrt(sum(lpsd_disp(idx).^2 .* df));
        RMS_g = sqrt(sum(lpsd(idx).^2 .* df));
        RMS_segment(2*j-1) = RMS_g;
        RMS_segment(2*j) = RMS_d * 1e9;  % 转换为纳米
    end
    RMS_table = [RMS_table; RMS_segment];
end

% 创建显示表格
new_table = [RMS_table(:,1), RMS_table(:,3), RMS_table(:,5), ... % 加速度RMS
             RMS_table(:,2)/1e9, RMS_table(:,4)/1e9, RMS_table(:,6)/1e9]; % 位移RMS

% 格式化RMS值
data_cell = cell(num_signals, 6);
for i = 1:num_signals
    data_cell{i,1} = format_rms(new_table(i,1), "acc");
    data_cell{i,2} = format_rms(new_table(i,2), "acc");
    data_cell{i,3} = format_rms(new_table(i,3), "acc");
    data_cell{i,4} = format_rms(new_table(i,4), "disp");
    data_cell{i,5} = format_rms(new_table(i,5), "disp");
    data_cell{i,6} = format_rms(new_table(i,6), "disp");
end

col_names = {'[1–40] Hz Acc','[40–100] Hz Acc','[1–100] Hz Acc',...
             '[1–40] Hz Disp','[40–100] Hz Disp','[1–100] Hz Disp'};

% 创建并保存表格图像
fig = figure('Name','RMS Table','Units','pixels','Color','w');
t = uitable('Parent', fig, ...
            'Data', data_cell, ...
            'RowName', row_names, ...
            'ColumnName', col_names, ...
            'Units', 'normalized', ...
            'Position', [0 0 1 1], ...
            'FontSize', 12, ...
            'ColumnWidth', {150}, ...
            'ColumnEditable', false(1,6));

set(t, 'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0]); 

pixel_width = 150*6 + 150;
pixel_height = 60*num_signals + 120;
set(fig, 'Position', [100, 100, pixel_width, pixel_height]);

frame = getframe(fig);
filename = fullfile(path, 'RMS_RESULT_TABLE.png');
imwrite(frame.cdata, filename);
fprintf('✅ 表格图已保存至：%s\n', filename);

% 命令行输出结果
fprintf('\n================ RMS 结果 ================\n');
fprintf('%-25s', '信号名称');
for j = 1:length(col_names)
    fprintf('%-20s', col_names{j});
end
fprintf('\n');

for i = 1:num_signals
    fprintf('%-25s', row_names{i});
    for j = 1:6
        fprintf('%-20s', data_cell{i,j});
    end
    fprintf('\n');
end
fprintf('==========================================\n\n');

%% 所有图形绘制
figure('Name','LPSD(g)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    loglog(F_all{i}, LPSD_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [g/√Hz]');
title('LPSD (g)');
legend(row_names, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); 
grid on; axis tight;
xlim([1, 1000]); % 设置一致的频率范围

figure('Name','PSD(g²)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    loglog(F_all{i}, PSD_stack{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [g²/Hz]');
title('PSD (g²)');
legend(row_names, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); 
grid on; axis tight;
xlim([1, 1000]);

figure('Name','PSD dBm(V²)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    semilogx(F_all{i}, PSD_dBm_Watt_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [dBm/Hz]');
title('PSD (V²) dBm');
legend(row_names, 'Location', 'northeast');
set(gca, 'XTick', 10.^(-2:0.5:4), 'XScale', 'log');
grid on; 
xlim([1, 1000]); % 设置一致的频率范围

figure('Name','PSD dBm(V²) loglog','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    loglog(F_all{i}, PSD_dBm_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [dBm]');
title('PSD (V²) dBm log-log');
legend(row_names, 'Location', 'northeast');
grid on; 
xlim([1, 1000]); % 设置一致的频率范围
ylim([-200, -20]); % 调整Y轴范围

figure('Name','LPSD dB(V)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    semilogx(F_all{i}, LPSD_dBm_Watt_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [dB(V/√Hz)]');
title('LPSD (V) dB');
legend(row_names, 'Location', 'northeast');
set(gca, 'XTick', 10.^(-2:0.5:4), 'XScale', 'log');
grid on; 
xlim([1, 1000]); % 设置一致的频率范围

figure('Name','LPSD dB(V) loglog','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    loglog(F_all{i}, LPSD_dBm_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [dB(V/√Hz)]');
title('LPSD (V) dB log-log');
legend(row_names, 'Location', 'northeast');
grid on; 
xlim([1, 1000]); % 设置一致的频率范围
ylim([-150, -50]); % 调整Y轴范围

figure('Name','LPSD(Displacement)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:num_signals
    loglog(F_all{i}, LPSD_disp_all{i} * 1e9, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [nm/√Hz]');
title('LPSD (Displacement)');
legend(row_names, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); 
grid on; axis tight;
xlim([1, 1000]); % 设置一致的频率范围

%% 辅助函数：格式化RMS值
function out = format_rms(val, kind)
    if strcmp(kind, "disp")
        if val >= 1e-6
            out = sprintf('%.2f μm', val * 1e6);
        elseif val >= 1e-9
            out = sprintf('%.2f nm', val * 1e9);
        else
            out = sprintf('%.2e m', val);
        end
    elseif strcmp(kind, "acc")
        if val >= 1
            out = sprintf('%.2f g', val);
        elseif val >= 1e-3
            out = sprintf('%.2f mg', val * 1e3);
        elseif val >= 1e-6
            out = sprintf('%.2f μg', val * 1e6);
        else
            out = sprintf('%.2f ng', val * 1e9);
        end
    else
        out = 'N/A';
    end
end