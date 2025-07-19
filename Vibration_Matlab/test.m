function spring_damper_c_sweep_LPSD()
%% === 固定参数 ===
k_actual = 800;       % 弹簧刚度 N/m
M = 0.6;              % 载荷质量 kg
m_s = 0.3;             % 弹簧质量 kg
m_eq = M + (1/3) * m_s;  % 等效质量
g = 9.81;              % 重力加速度

%% === 读取加速度电压数据 ===
[fileName, filePath] = uigetfile('*.csv', '选择加速度 CSV 文件');
if isequal(fileName, 0); error('❌ 用户取消了文件选择。'); end
fullFileName = fullfile(filePath, fileName);
opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
data = readmatrix(fullFileName, opts);
time = data(:,1);
voltage = data(:,2);
voltage = voltage - mean(voltage);  % 去直流偏置

%% === 信号转换：电压 -> 加速度 ===
sensitivity = 1.026;  % V/g
gain = 100;
a_base = (voltage / (sensitivity * gain));  % 单位 m/s²

%% === PSD & LPSD 计算 ===
dt = mean(diff(time));
fs = 1 / dt;
nfft = 100000;
window = hanning(nfft);
overlap = round(0.5 * nfft);
[psd_acc, f] = pwelch(a_base, window, overlap, nfft, fs); % PSD 单位: (m/s²)²/Hz
df = mean(diff(f));

lpsd_acc = sqrt(psd_acc);  % 单位: m/s² / √Hz

%% === 频率范围控制（避免低频噪声） ===
idx_band = f >= 1 & f <= 100;  % 控制频率范围
f_opt = f(idx_band);
lpsd_acc_opt = lpsd_acc(idx_band);

% === 位移 LPSD ===
omega = 2 * pi * f_opt;
lpsd_disp_opt = (g ./ omega.^2) .* (lpsd_acc_opt / g);  % 转换为 m/√Hz

%% === 扫描阻尼系数 c，计算加权后的 RMS ===
wn = sqrt(k_actual / m_eq);  % 固有频率
c_range = linspace(1, 200, 100);  % 阻尼范围
rms_list = zeros(size(c_range));
c_values = c_range;

% 限制最大阻尼系数 (这里选择最大值为 150)
max_c = 200;  % 最大阻尼系数上限
c_range(c_range > max_c) = max_c;

avg_transmission_ratios = [];  % 用于存储每个阻尼下的平均传递比

for i = 1:length(c_range)
    c = c_range(i);
    zeta = c / (2 * sqrt(k_actual * m_eq));  % 计算阻尼比
    r = f_opt / wn;
    
    % 这里改进了传递函数以限制高阻尼对响应的影响
    if zeta > 0.5  % 高阻尼情况下进行调整，避免过大抑制
        H = r.^2 ./ sqrt((1 - r.^2).^2 + (2*zeta*r).^2 + 0.5);  % 加了调整因子
    else
        H = r.^2 ./ sqrt((1 - r.^2).^2 + (2*zeta*r).^2);  % 正常情况
    end
    
    lpsd_disp_out = H .* lpsd_disp_opt;  % 单位 m/√Hz

    % 根据 LPSD 公式计算 RMS：
    rms_list(i) = sqrt(sum(lpsd_disp_out.^2 .* df));  % 单位: m
    
    % 计算平均传递比（0到50 Hz）
    num = [c, k_actual];  % c * s + k_actual
    den = [m_eq, c, k_actual];  % m_eq * s^2 + c * s + k_actual
    
    % 计算频率响应
    [mag, ~, ~] = bode(tf(num, den), 2 * pi * f_opt);  % bode 默认用 rad/s，换成 Hz
    mag = squeeze(mag);
    
    % 计算0 到 50 Hz 的频段平均传递比
    freq_band = (f_opt >= 0.1) & (f_opt <= 50);  % 选择 0-50 Hz 的频段
    avg_mag = mean(mag(freq_band));  % 计算该频段的平均传递比
    
    avg_transmission_ratios = [avg_transmission_ratios, avg_mag];
end

% 找到最优结果
[best_rms, idx_best] = min(rms_list);
best_c = c_range(idx_best);
optimal_avg_transmission_ratio = min(avg_transmission_ratios);
optimal_c_index = find(avg_transmission_ratios == optimal_avg_transmission_ratio);
optimal_c_for_avg = c_range(optimal_c_index);

%% === 绘图 ===
figure('Name','加速度 PSD、LPSD、位移 LPSD 和 RMS (LPSD 方法)');
subplot(2,2,1);  % 加速度 PSD
plot(f_opt, psd_acc(idx_band), 'b-', 'LineWidth', 1.5); 
xlabel('频率 (Hz)');
ylabel('加速度 PSD [(m/s²)²/Hz]');
title('加速度 PSD');
grid on;

subplot(2,2,2);  % 加速度 LPSD
plot(f_opt, lpsd_acc_opt, 'g-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('加速度 LPSD [m/s²/√Hz]');
title('加速度 LPSD');
grid on;

subplot(2,2,3);  % 位移 LPSD
plot(f_opt, lpsd_disp_opt, 'r-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('位移 LPSD [m/√Hz]');
title('位移 LPSD');
grid on;

subplot(2,2,4);  % 阻尼系数 vs RMS (对数坐标)
semilogy(c_range, rms_list*1e6, 'b-', 'LineWidth', 1.5); hold on;  % 使用 semilogy 进行对数绘制
semilogy(best_c, best_rms*1e6, 'ro', 'MarkerSize', 6, 'MarkerFaceColor', 'r');
semilogy(optimal_c_for_avg, optimal_avg_transmission_ratio*1e6, 'go', 'MarkerSize', 6, 'MarkerFaceColor', 'g');
xlabel('阻尼系数 c (Ns/m)');
ylabel('RMS 位移 [μm]');
title('LPSD 方法：不同阻尼下 RMS 位移');
grid on;

disp(['最佳阻尼值 c = ', num2str(best_c)]);
disp(['该阻尼值的 RMS 位移为 ', num2str(best_rms*1e6), ' μm']);
disp(['平均传递比最小的阻尼值 c = ', num2str(optimal_c_for_avg)]);
disp(['该阻尼值的平均传递比为 ', num2str(optimal_avg_transmission_ratio), ' dB']);