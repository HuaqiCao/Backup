%% 参数设置
Fs = 10000;
Nfft = 100000;
window = hann(Nfft);
window = window / sqrt(mean(window.^2));
overlap = Nfft / 2;
sensitivity = 1.026;
ref_resistance = 1;
g = 9.81;

signal_names = {'Vibration_Data', 'Brass', 'stainless_steel'};
legend_labels = {'Vibration Input','c=100','c=50'};
colors = {[1.0, 0.5, 0.0],[1.0, 0.85, 0.0],[0.1, 0.4, 0.7]};

[filenames, path] = uigetfile('*.csv', '选择一个或多个CSV文件', 'Multiselect', 'on');
if isequal(filenames, 0), disp('❌ 取消导出'); return; end
if ~iscell(filenames), filenames = {filenames}; end

PSD_stack = {}; PSD_stack_voltage = {}; F_all = {};

for i = 1:min(length(filenames), length(signal_names))
    name = signal_names{i}; ts = out.(name);
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
    PSD_stack{i} = pxx_g;
    PSD_stack_voltage{i} = pxx_v;
    F_all{i} = f;
end

LPSD_all = {}; LPSD_disp_all = {}; RMS_table = [];
PSD_dBm_all = {}; PSD_dBm_Watt_all = {};
LPSD_dBm_all = {}; LPSD_dBm_Watt_all = {};

% 修改后的频段边界
band_edges = [1, 40; 40, 100; 1, 100]; % 增加了 [1, 100] Hz 频段

for i = 1:length(PSD_stack)
    pxx_g = PSD_stack{i};
    pxx_v = PSD_stack_voltage{i};
    f = F_all{i};
    lpsd = sqrt(pxx_g);
    lpsd_disp = g ./ ((2*pi*f).^2) .* lpsd;
    psd_dBm = 10 * log10(pxx_v / 1e-6);
    psd_dBm_W = 10 * log10(pxx_v / ref_resistance / 1e-3);
    lpsd_dBm = 20 * log10(sqrt(pxx_v)) - 10 * log10(ref_resistance) - 30;

    LPSD_all{i} = lpsd;
    LPSD_disp_all{i} = lpsd_disp;
    PSD_dBm_all{i} = psd_dBm;
    PSD_dBm_Watt_all{i} = psd_dBm_W;
    LPSD_dBm_all{i} = lpsd_dBm;
    LPSD_dBm_Watt_all{i} = lpsd_dBm;

    df = mean(diff(f));
    RMS_segment = zeros(size(band_edges,1)*2, 1);
    for j = 1:size(band_edges,1)
        idx = f >= band_edges(j,1) & f <= band_edges(j,2);
        RMS_d = sqrt(sum(lpsd_disp(idx).^2 .* df));
        RMS_g = sqrt(sum(lpsd(idx).^2 .* df));
        RMS_segment(2*j-1) = RMS_g;
        RMS_segment(2*j) = RMS_d * 1e9;
    end
    RMS_table = [RMS_table; RMS_segment(:)'];
end

row_names = legend_labels;
row_num = numel(row_names);
rms_g_1_40 = RMS_table(:, 1);
rms_d_1_40 = RMS_table(:, 2);
rms_g_40_100 = RMS_table(:, 3);
rms_d_40_100 = RMS_table(:, 4);
rms_g_1_100 = RMS_table(:, 5); % 新增位移频段
rms_d_1_100 = RMS_table(:, 6); % 新增位移频段

new_table = [rms_g_1_40, rms_g_40_100, rms_g_1_100, rms_d_1_40/1e9, rms_d_40_100/1e9, rms_d_1_100/1e9];
data_cell = cell(row_num, 6);
for i = 1:row_num
    data_cell{i,1} = format_rms(new_table(i,1), "acc");
    data_cell{i,2} = format_rms(new_table(i,2), "acc");
    data_cell{i,3} = format_rms(new_table(i,3), "acc");
    data_cell{i,4} = format_rms(new_table(i,4), "disp");
    data_cell{i,5} = format_rms(new_table(i,5), "disp");
    data_cell{i,6} = format_rms(new_table(i,6), "disp");
end

col_names = {'[1–40] Hz Acc','[40–100] Hz Acc','[1–100] Hz Acc','[1–40] Hz Disp','[40–100] Hz Disp','[1–100] Hz Disp'};

fig = figure('Name','RMS Table','Units','pixels','Color','w');
t = uitable('Parent', fig, ...
            'Data', data_cell, ...
            'RowName', row_names, ...
            'ColumnName', col_names, ...
            'Units', 'normalized', ...
            'Position', [0 0 1 1], ...
            'FontSize', 12, ...
            'ColumnWidth', {150, 150, 150, 150, 150, 150}, ...
            'ColumnEditable', false(1,6));

set(t, 'BackgroundColor', [1 1 1], 'ForegroundColor', [0 0 0]); 

pixel_width = 150*6 + 150;
pixel_height = 60*row_num + 120;
set(fig, 'Position', [100, 100, pixel_width, pixel_height]);

frame = getframe(fig);
filename = fullfile(path, 'RMS_RESULT_TABLE.png');
imwrite(frame.cdata, filename);
fprintf('✅ 表格图已保存至：%s\n', filename);

fprintf('\n================ RMS 结果 ================\n');
fprintf('%-25s', '信号名称');
for j = 1:length(col_names)
    fprintf('%-20s', col_names{j});
end
fprintf('\n');

for i = 1:row_num
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
for i = 1:length(LPSD_all)
    loglog(F_all{i}, LPSD_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [g/√Hz]');
title('LPSD (g)');
legend(legend_labels, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); grid on; axis tight;

figure('Name','PSD(g²)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(PSD_stack)
    loglog(F_all{i}, PSD_stack{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [g²/Hz]');
title('PSD (g²)');
legend(legend_labels, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); grid on; axis tight;

figure('Name','PSD dBm(V²)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(PSD_dBm_Watt_all)
    semilogx(F_all{i}, PSD_dBm_Watt_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [dBm/Hz]');
title('PSD (V²) dBm');
legend(legend_labels, 'Location', 'northeast');
set(gca, 'XTick', 10.^(-2:0.5:4), 'XScale', 'log');
grid on; xlim([0, max(F_all{1})]);

figure('Name','PSD dBm(V²) loglog','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(PSD_dBm_all)
    loglog(F_all{i}, PSD_dBm_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('PSD [dBm]');
title('PSD (V²) dBm log-log');
legend(legend_labels, 'Location', 'northeast');
grid on; xlim([1e-3, 1e3]); ylim([-280, -20]);

figure('Name','LPSD dB(V)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(LPSD_dBm_Watt_all)
    semilogx(F_all{i}, LPSD_dBm_Watt_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [dB(V/√Hz)]');
title('LPSD (V) dB');
legend(legend_labels, 'Location', 'northeast');
set(gca, 'XTick', 10.^(-2:0.5:4), 'XScale', 'log');
grid on; xlim([0, max(F_all{1})]);

figure('Name','LPSD dB(V) loglog','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(LPSD_dBm_all)
    loglog(F_all{i}, LPSD_dBm_all{i}, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [dB(V/√Hz)]');
title('LPSD (V) dB log-log');
legend(legend_labels, 'Location', 'northeast');
grid on; xlim([1, 1e3]);

figure('Name','LPSD(Displacement)','Units','inches','Position', [1, 1, 9.59, 4.22]); 
hold on;
for i = 1:length(LPSD_disp_all)
    loglog(F_all{i}, LPSD_disp_all{i} * 1e9, 'Color', colors{i}, 'LineWidth', 1.5);
end
xlabel('Frequency [Hz]'); ylabel('LPSD [nm/√Hz]');
title('LPSD (Displacement)');
legend(legend_labels, 'Location', 'northeast');
set(gca, 'XScale', 'log', 'YScale', 'log'); grid on; axis tight;

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
        if val >= 1e-6
            out = sprintf('%.2f μg', val * 1e6);
        elseif val >= 1e-9
            out = sprintf('%.2f ng', val * 1e9);
        else
            out = sprintf('%.2e g', val);
        end
    else
        out = 'N/A';
    end
end
