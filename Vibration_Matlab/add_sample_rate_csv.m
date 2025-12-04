%% ============================================================
% 本程序功能：
% 1）批量选择多个 CSV 文件（含 time, value 两列）；
% 2）自动计算每个文件的采样率 fs；
% 3）将采样率写入文件名并保存新的 CSV 文件；
%    示例：original.csv → original_fs10000Hz.csv
% 4）在命令行打印每个文件的采样率。
%% ============================================================


% === 选择多个 CSV 文件 ===
[fileNames, folderPath] = uigetfile('*.csv', 'Select CSV files', 'MultiSelect', 'on');

if isequal(fileNames, 0)
    disp('❌ Selection cancelled.');
    return;
end

% 确保 fileNames 是 cell 数组
if ischar(fileNames)
    fileNames = {fileNames};
end

for i = 1:length(fileNames)
    fullPath = fullfile(folderPath, fileNames{i});

    % === 读取 CSV，跳过前 4 行表头 ===
    opts = detectImportOptions(fullPath);
    opts.DataLines = [5, Inf];
    data = readmatrix(fullPath, opts);

    % === 从 time 列计算采样率 ===
    time = data(:, 1);
    dt = mean(diff(time), 'omitnan');   % 平均采样间隔
    fs = 1 / dt;                        % 采样率

    % === 打印采样率 ===
    fprintf('📁 File: %s\n', fileNames{i});
    fprintf('📊 Sampling rate: %.2f Hz\n', fs);

    % === 保存包含 fs 的新文件名 ===
    [~, name, ~] = fileparts(fileNames{i});
    newName = sprintf('%s_fs%.0fHz.csv', name, fs);   % 文件名添加采样率
    newPath = fullfile(folderPath, newName);
    writematrix(data, newPath);

    fprintf('✅ Saved to: %s\n\n', newPath);
end
