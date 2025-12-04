%% ============================================================
% 本程序功能：
% 1）读取一个 CSV（两列：time, voltage）
% 2）按固定时间窗（window_size 秒）切片信号
% 3）根据阈值（电压振幅 ≥ 0.15 V）自动区分：
%       ● signal（有事件）窗口
%       ● baseline（纯底噪）窗口
% 4）计算 baseline 的标准差（std）并输出平均值
% 5）将 signal 与 baseline 数据分别写出 CSV 文件
%    （保存在新建文件夹 signal_rejection 中）
%% ============================================================


% === 选择 CSV 文件 ===
[filename, path] = uigetfile('*.csv', 'Select CSV file');
if isequal(filename, 0)
    return;
end

% === 读取 CSV，全列 ===
data = readmatrix(fullfile(path, filename));
time = data(:,1);
volt = data(:,2);

% === 参数设置 ===
window_size = 1;             % 每个时间窗口长度（秒）
fs = round(1 / (time(10) - time(9)));  % 采样率（从相邻点计算）
num_windows = ceil((time(end) - time(5)) / window_size);  % 窗口数量

% === 初始化存储结构 ===
signal_windows = {};         % 存 signal 电压
baseline_windows = {};       % 存 baseline 电压
signal_times = {};           % 存 signal 时间
baseline_times = {};         % 存 baseline 时间
sigamp = [];                 % signal 的最大幅度（用于统计）

% === 按时间窗口切片并分类 ===
for i = 1:num_windows
    start_idx = (i - 1) * window_size * fs + 5;      % 每个窗口起点
    end_idx = min(start_idx + window_size * fs - 1, length(time));
    
    window = volt(start_idx:end_idx);               % 电压片段
    wintime = time(start_idx:end_idx);              % 时间片段
    
    % === 判定是否为 signal（阈值 0.15 V）===
    if max(window) - min(window) >= 0.15
        signal_windows{end+1} = window;
        signal_times{end+1} = wintime;
        sigamp(end+1) = max(window);                % 保存最大幅值
    else
        baseline_windows{end+1} = window;
        baseline_times{end+1} = wintime;
    end
end

% === 计算 baseline 各窗口的标准差 ===
baseline_std = zeros(1, length(baseline_windows));
for i = 1:length(baseline_windows)
    baseline_std(i) = std(baseline_windows{i});
end
avg_baseline_std = mean(baseline_std);

% === 输出 baseline 平均标准差 ===
fprintf('Average baseline std: %.6f\n', avg_baseline_std);

% === 输出文件夹 ===
out_dir = fullfile(path, 'signal_rejection');
if ~exist(out_dir, 'dir')
    mkdir(out_dir);
end

% === 写出 signal / baseline 数据 ===
signal_data = [vertcat(signal_times{:}), vertcat(signal_windows{:})];
baseline_data = [vertcat(baseline_times{:}), vertcat(baseline_windows{:})];

writematrix(signal_data, fullfile(out_dir, ['signal_', filename]));
writematrix(baseline_data, fullfile(out_dir, ['baseline_', filename]));
