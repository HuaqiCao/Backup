%% ============================================================
% 1）选择一个加速度输入 CSV（time, voltage/acc）；
% 2）模拟 4 组不同“单级弹簧-阻尼器系统”的响应（输入为加速度）；
% 3）将每个系统的输出响应保存为 CSV（单位：g）；
% 4）计算输入及 4 个输出的 PSD（g^2/Hz）并画图；
% 5）计算位移 LPSD（m/√Hz）并画图；
% 6）计算 1–40 Hz、40–100 Hz、1–100 Hz 三个频段的加速度/位移 RMS；
% 7）将 RMS 结果打印到命令行。
%% ============================================================


% === 选择加速度输入 CSV 文件 ===
[file, path] = uigetfile('*.csv', 'Select acceleration CSV file');
if isequal(file, 0)
    disp('Cancelled');
    return;
end
input_file = fullfile(path, file);

% === 读取 CSV（跳过前 4 行表头）===
opts = detectImportOptions(input_file, 'NumHeaderLines', 4);
data = readmatrix(input_file, opts);

time = data(:,1);                   % 时间
accel_input = data(:,2);            % 加速度（或电压）
accel_input = accel_input - mean(accel_input);   % 去直流
dt = mean(diff(time));              % 采样间隔
fs = 1 / dt;                        % 采样率
t = time;

% === 创建输出文件夹 ===
out_folder = fullfile(path, '弹簧对比结果');
if ~exist(out_folder, 'dir')
    mkdir(out_folder);
end

% === 输入四组弹簧参数（k, c）===
prompt = {'k1 (N/m):', 'c1 (Ns/m):', ...
          'k2 (N/m):', 'c2 (Ns/m):', ...
          'k3 (N/m):', 'c3 (Ns/m):', ...
          'k4 (N/m):', 'c4 (Ns/m):'};
dlgtitle = 'Enter 4 sets of spring parameters';
dims = [1 35];
definput = {'82.50','0.0992','55','0.0441','66.27','0.0441','99.40','0.0992'};
options.Resize = 'on';
answer = inputdlg(prompt, dlgtitle, dims, definput, options);
if isempty(answer)
    disp('Input cancelled');
    return;
end

% === 打印参数到命令行 ===
fprintf('\n=== Input Spring Parameters ===\n');
fprintf('Spring\tk (N/m)\tc (Ns/m)\n');
for i = 1:4
    k = str2double(answer{2*i-1});
    c = str2double(answer{2*i});
    fprintf('%d\t%.4f\t%.4f\n', i, k, c);
end

% === 模拟 4 个系统的响应 ===
m = 1.025;                   % 质量
sys = cell(1,4);             % 4 个系统
responses = zeros(length(t), 4);

for i = 1:4
    k = str2double(answer{2*i-1});
    c = str2double(answer{2*i});

    % 单自由度系统传递函数（输入为加速度）
    num = [0 c k];
    den = [m c k];
    sys{i} = tf(num, den);

    % 模拟响应（输入为 m/s^2）
    responses(:,i) = lsim(sys{i}, accel_input * 9.80665, t);

    % 保存输出（单位转换回 g）
    out_data = [t responses(:,i) / 9.80665];
    out_filename = fullfile(out_folder, sprintf('Output%d.csv', i));
    writematrix(out_data, out_filename);
end

% === PSD 计算参数 ===
nfft = 100000;
window = hamming(nfft);
overlap = round(0.5 * nfft);

% === 绘制加速度 PSD 图 ===
figure_linear = figure('Name', 'PSD: g^2/Hz');
[pxx_input, f] = pwelch(accel_input, window, overlap, nfft, fs);

% 输入信号 PSD（灰色）
loglog(f, pxx_input, '--', 'Color', [0.4 0.4 0.4], 'LineWidth', 1.5); hold on;

accel_rms_table = zeros(4,3);  % 存储加速度 RMS（1-40, 40-100, 1-100）

for i = 1:4
    accel = responses(:,i) / 9.80665;         % m/s^2 → g
    [pxx, f] = pwelch(accel, window, overlap, nfft, fs);
    loglog(f, pxx, 'LineWidth', 1.2); hold on;

    % 计算 RMS（分频段）
    band1 = (f >= 1) & (f <= 40);
    band2 = (f >= 40) & (f <= 100);
    band3 = (f >= 1) & (f <= 100);
    accel_rms_table(i,1) = sqrt(trapz(f(band1), pxx(band1)));
    accel_rms_table(i,2) = sqrt(trapz(f(band2), pxx(band2)));
    accel_rms_table(i,3) = sqrt(trapz(f(band3), pxx(band3)));
end

xlabel('Frequency (Hz)');
ylabel('PSD (g^2/Hz)');
title('Power Spectral Density（g^2）');
grid on;
legend({'Input', 'Spring 1', 'Spring 2', 'Spring 3', 'Spring 4'});
saveas(figure_linear, fullfile(out_folder, 'PSD_Acceleration.png'));

% === 绘制位移 LPSD 图 ===
figure_lpsd = figure('Name', 'LPSD of Displacement (m/√Hz)');
colors = lines(4);
disp_rms_table = zeros(4,3);  % 位移 RMS
g = 9.80665;

for i = 1:4
    acc = responses(:,i);
    [pxx_acc, f_acc] = pwelch(acc, window, overlap, nfft, fs);

    f_acc(f_acc == 0) = NaN;        % 避免除零
    lpsd_a = sqrt(pxx_acc) / g;     % 加速度 LPSD（g → m/s²/√Hz）
    lpsd_d = g ./ (2 * pi * f_acc) .* lpsd_a;   % 位移 LPSD（m/√Hz）
    lpsd_d(~isfinite(lpsd_d)) = 0;

    loglog(f_acc, lpsd_d, 'Color', colors(i,:), 'LineWidth', 1.2); hold on;

    % 位移 RMS（分频段）
    band1 = (f_acc >= 1) & (f_acc <= 40);
    band2 = (f_acc >= 40) & (f_acc <= 100);
    band3 = (f_acc >= 1) & (f_acc <= 100);
    disp_rms_table(i,1) = sqrt(trapz(f_acc(band1), lpsd_d(band1).^2));
    disp_rms_table(i,2) = sqrt(trapz(f_acc(band2), lpsd_d(band2).^2));
    disp_rms_table(i,3) = sqrt(trapz(f_acc(band3), lpsd_d(band3).^2));
end

xlabel('Frequency (Hz)');
ylabel('LPSD (m/√Hz)');
title('Displacement LPSD');
grid on;
legend({'Spring 1','Spring 2','Spring 3','Spring 4'}, 'Location', 'best');
saveas(figure_lpsd, fullfile(out_folder, 'LPSD_Displacement_Ref.png'));

% === 打印 RMS 结果 ===
fprintf('\n=== Acceleration RMS (g) ===\n');
fprintf('Spring\t1-40Hz\t\t40-100Hz\t1-100Hz\n');
for i = 1:4
    fprintf('%d\t%.4e\t%.4e\t%.4e\n', i, accel_rms_table(i,1), accel_rms_table(i,2), accel_rms_table(i,3));
end

fprintf('\n=== Displacement RMS (m) [based on LPSD] ===\n');
fprintf('Spring\t1-40Hz\t\t40-100Hz\t1-100Hz\n');
for i = 1:4
    fprintf('%d\t%.4e\t%.4e\t%.4e\n', i, ...
        disp_rms_table(i,1), disp_rms_table(i,2), disp_rms_table(i,3));
end
