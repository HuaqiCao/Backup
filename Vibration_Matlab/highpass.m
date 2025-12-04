%% ============================================================
% 本程序功能：从 CSV 文件读取信号，对电压执行巴特沃斯高通滤波，
% 并将过滤后的数据保存到 highpass 文件夹内（保留4行空白头）。
% ============================================================

% === 选择 CSV 文件 ===
[filename, path] = uigetfile('*.csv', 'Select CSV file');
if isequal(filename, 0)
    return;
end

% === 读取 CSV 数据 ===
data = readmatrix(fullfile(path, filename));

% === 从第 5 行开始读取有效数据 ===
time = data(5:end, 1);
volt = data(5:end, 2);

% === 设计高通巴特沃斯滤波器 ===
fs = 1 / (time(21) - time(20));   % 采样率
fc = 0.1;                         % 截止频率（Hz）
[b, a] = butter(2, fc / (fs / 2), 'high');

% === 应用高通滤波 ===
filtered_volt = filtfilt(b, a, volt);

% === 创建 highpass 目录（如果不存在）===
if ~exist('highpass', 'dir')
    mkdir('highpass');
end

% === 输出文件名 ===
new_filename = fullfile('highpass', ['highpass_' filename]);

% === 写入 4 行空白头，再写入滤波后数据 ===
fid = fopen(new_filename, 'w');
fprintf(fid, '\n\n\n\n');    % 写入 4 行空白
fclose(fid);

% === 附加写入时间 + 滤波电压 ===
writematrix([time, filtered_volt], new_filename, 'WriteMode', 'append');
