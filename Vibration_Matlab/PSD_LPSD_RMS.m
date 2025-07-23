% input accleration data from multiple CSV files
% plot PSD & LPSD & RMS

function PSD_LPSD_RMS()
%% === 1. 文件选择 ===
[fileNames, filePath] = uigetfile('*.csv', '选择加速度 CSV 文件', 'MultiSelect', 'on');
if isequal(fileNames, 0)
    error('❌ 用户取消了文件选择。');
end
if ischar(fileNames)
    fileNames = {fileNames};  
end
numFiles = numel(fileNames);

%% === 2. 初始化图形 ===
% 创建三个图形窗口并开启hold on
fig1 = figure('Name','加速度 PSD','Units','inches','Position', [1, 1, 9.59, 4.22]);
ax1 = axes(fig1); hold(ax1, 'on');
xlabel(ax1, '频率 (Hz)'); ylabel(ax1, 'PSD [g²/Hz]'); title(ax1, '加速度 PSD');
grid(ax1, 'on'); set(ax1, 'XScale', 'log', 'YScale', 'log');

fig2 = figure('Name','加速度 LPSD','Units','inches','Position', [1, 1, 9.59, 4.22]);
ax2 = axes(fig2); hold(ax2, 'on');
xlabel(ax2, '频率 (Hz)'); ylabel(ax2, 'LPSD [g/√Hz]'); title(ax2, '加速度 LPSD');
grid(ax2, 'on'); set(ax2, 'XScale', 'log', 'YScale', 'log');

fig3 = figure('Name','位移 LPSD','Units','inches','Position', [1, 1, 9.59, 4.22]);
ax3 = axes(fig3); hold(ax3, 'on');
xlabel(ax3, '频率 (Hz)'); ylabel(ax3, 'LPSD [nm/√Hz]'); title(ax3, '位移 LPSD');
grid(ax3, 'on'); set(ax3, 'XScale', 'log', 'YScale', 'log');

% 颜色和标记样式循环
colors = lines(numFiles);
markers = {'-', '--', ':', '-.'};

%% === 3. 预定义参数 ===
band_edges = [1, 40; 40, 100; 1, 100];
band_names = {'[1–40] Hz', '[40–100] Hz', '[1–100] Hz'};
g = 9.81;

% 初始化结果存储
allRMS = cell(numFiles, 1);
fileLabels = cell(numFiles, 1);

%% === 4. 处理每个文件 ===
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly, ~] = fileparts(fileNames{iFile});
    fileLabels{iFile} = nameOnly;
    
    %% 读取数据
    opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
    data = readmatrix(fullFileName, opts);
    time = data(:,1);
    a_base = data(:,2);
    
    % 去直流分量
    a_base = a_base - mean(a_base);
    
    %% PSD 与 LPSD 计算
    dt = mean(diff(time));
    fs = 1 / dt;
    nfft = 100000;
    window = hamming(nfft);
    overlap = round(0.5 * nfft);
    [pxx, f] = pwelch(a_base, window, overlap, nfft, fs);
    df = mean(diff(f));
    
    % LPSD 计算
    lpsd_acc = sqrt(pxx) / g;
    lpsd_disp = g ./ ((2*pi*f).^2) .* lpsd_acc;
    
    %% RMS 计算
    RMS_result = zeros(size(band_edges,1), 2);
    for iBand = 1:size(band_edges,1)
        idx = f >= band_edges(iBand,1) & f <= band_edges(iBand,2);
        RMS_result(iBand, 1) = sqrt(sum((lpsd_acc(idx).^2) * df));
        RMS_result(iBand, 2) = sqrt(sum((lpsd_disp(idx).^2) * df));
    end
    allRMS{iFile} = RMS_result;
    
    %% 绘制图形
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f, pxx / g^2, 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);
    plot(ax2, f, lpsd_acc, 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);
    plot(ax3, f, lpsd_disp * 1e9, 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);
end

%% === 5. 添加图例 ===
legend(ax1, 'show', 'Location', 'best');
legend(ax2, 'show', 'Location', 'best');
legend(ax3, 'show', 'Location', 'best');

%% === 6. RMS 结果汇总 ===
rms_cell = cell(numFiles, 7);  

for iFile = 1:numFiles
    RMS_result = allRMS{iFile};
    rms_cell{iFile, 1} = fileLabels{iFile}; 
    
    for iBand = 1:3
        rms_cell{iFile, iBand+1} = format_rms(RMS_result(iBand,1), 'acc');
    end
    
    for iBand = 1:3
        rms_cell{iFile, iBand+4} = format_rms(RMS_result(iBand,2), 'disp');
    end
end

fig = figure('Name','RMS 对比表','Units','pixels','Color','w');
col_names = {'文件名', ...
    '「1-40Hz」加速度', '「40-100Hz」加速度', '「1-100Hz」加速度', ...
    '「1-40Hz」位移', '「40-100Hz」位移', '「1-100Hz」位移'};
t = uitable('Parent', fig, 'Data', rms_cell, 'ColumnName', col_names, ...
    'Units', 'normalized', 'Position', [0.05 0.05 0.9 0.9], ...
    'FontSize', 10, 'RowName', []);
set(fig, 'Position', [100, 100, 900, min(400, 100 + 25*numFiles)]);

%% === 7. 命令行输出 ===
fprintf('\n');
for iFile = 1:numFiles
    fprintf('%s（单位：μg / nm）\n', fileLabels{iFile});
    fprintf('%-15s%-20s%-20s\n', '频段', '加速度', '位移');
    fprintf('-----------------------------------------------\n');
    
    RMS_result = allRMS{iFile};
    for iBand = 1:size(band_edges,1)
        acc_str = format_rms(RMS_result(iBand,1), 'acc');
        disp_str = format_rms(RMS_result(iBand,2), 'disp');
        fprintf('%-15s%-20s%-20s\n', band_names{iBand}, acc_str, disp_str);
    end
    
    fprintf('===============================================\n');
end
end

% 子函数定义
function out = format_rms(val, kind)
    if strcmp(kind, "disp")
        out = sprintf('%.2f nm', val * 1e9);
    elseif strcmp(kind, "acc")
        out = sprintf('%.2f μg', val * 1e6);
    else
        out = 'N/A';
    end
end