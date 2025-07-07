% 选择CSV文件
[file, path] = uigetfile('*.csv', '选择加速度CSV文件');
if isequal(file, 0)
    disp('用户取消操作');
    return;
end
filepath = fullfile(path, file);

% 跳过前4行标题，读取数据
opts = detectImportOptions(filepath, 'NumHeaderLines', 4);
data = readmatrix(filepath, opts);

% 提取时间和信号
time = data(:, 1);      % 单位：秒
signal = data(:, 2);    % 可以是加速度、电压等

% 计算采样率
dt = mean(diff(time));  % 采样时间间隔
fs = 1 / dt;            % 采样率

% 信号长度与时长
N = length(signal);
StopTime = N / fs;      % 总时长（秒）

% 计算 FFT Length（与你代码一致：nfft = 2^nextpow2(N/8)）
nfft = 2^nextpow2(N / 8);
windowLength = nfft;    % 窗函数长度 = FFT长度（Hamming窗）

% 输出结果
fprintf('✅ Spectrum Analyzer 参数建议如下：\n');
fprintf('--------------------------------------------------\n');
fprintf('📁 文件名          : %s\n', file);
fprintf('📏 采样率 fs       : %.4f Hz\n', fs);
fprintf('⏱️  Stop Time      : %.4f 秒\n', StopTime);
fprintf('🔍  FFT Length     : %d 点\n', nfft);
fprintf('🪟  Window Length  : %d 点（建议使用 Hamming 窗）\n', windowLength);
fprintf('--------------------------------------------------\n');
