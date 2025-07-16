% === 1. 文件选择 ===
[fileName, filePath] = uigetfile('*.csv', '选择加速度 CSV 文件');
if isequal(fileName, 0)
    error('❌ 用户取消了文件选择。');
end
fullFileName = fullfile(filePath, fileName);

% === 2. 读取数据（跳过前4行） ===
opts = detectImportOptions(fullFileName, 'NumHeaderLines', 4);
data = readmatrix(fullFileName, opts);
time = data(:,1);
a_base = data(:,2);
a_base = a_base - mean(a_base);  % 去偏置

dt = mean(diff(time));
fs = 1 / dt;

% === 3. PSD 计算参数 ===
nfft = 100000;
window = hamming(nfft);
overlap = round(0.5 * nfft);
[pxx, f] = pwelch(a_base, window, overlap, nfft, fs);
w = 2 * pi * f;

% === 4. 系统参数 ===
m = 2.0;  % 铜锅质量 kg

% 优化频段（可调），单位 Hz
f_band = [0.01, 10];
f_idx = f >= f_band(1) & f <= f_band(2);
f_opt = f(f_idx);
pxx_opt = pxx(f_idx);
w_opt = 2 * pi * f_opt;

% === 5. 搜索参数空间 ===
k_list = logspace(0, 4, 50);   % N/m
c_list = logspace(-1, 3, 50);  % Ns/m

min_ratio = inf;
best_k = NaN;
best_c = NaN;

% === 6. 主循环：搜索最小能量比例 ===
for ki = 1:length(k_list)
    for ci = 1:length(c_list)
        k = k_list(ki);
        c = c_list(ci);

        % 加速度传递函数模值
        H = abs(1 + (m * w_opt.^2) ./ (k - m * w_opt.^2 + 1i * c * w_opt));

        % 输出 PSD
        pxx_out = (H.^2) .* pxx_opt;

        % 频带内输入输出能量
        energy_in = trapz(f_opt, pxx_opt);
        energy_out = trapz(f_opt, pxx_out);

        % 归一化（能量比例）
        ratio = energy_out / energy_in;

        if ratio < min_ratio
            min_ratio = ratio;
            best_k = k;
            best_c = c;
        end
    end
end

% === 7. 重新计算最佳响应 ===
wn = sqrt(best_k / m);
zeta = best_c / (2 * sqrt(best_k * m));
r = w / wn;
H_best = abs(1 + (r.^2) ./ (1 - r.^2 + 1i * 2 * zeta .* r));
pxx_out_best = (H_best.^2) .* pxx;

% === 8. 输出结果 ===
fprintf('✅ 最优刚度 k = %.2f N/m\n', best_k);
fprintf('✅ 最优阻尼 c = %.2f Ns/m\n', best_c);
fprintf('🎯 积分频段 = [%.1f, %.1f] Hz\n', f_band(1), f_band(2));
fprintf('🔻 最小归一化输出能量比 = %.3e\n', min_ratio);

% === 9. 绘图：输入 vs 响应 PSD ===
figure;
loglog(f, pxx, 'b-', 'LineWidth', 1.5); hold on;
loglog(f, pxx_out_best, 'r--', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('PSD (m²/s³/Hz)');
legend('输入加速度 PSD', '铜锅响应 PSD');
title('输入 vs 响应 PSD');
grid on;

% === 10. 绘图：加速度传递率 H(f) ===
figure;
semilogx(f, H_best, 'k-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('加速度传递率 |H(f)|');
title('加速度传递函数模值');
grid on;

% === 11. 绘图：频率隔振能量比 ===
figure;
energy_ratio = (H_best.^2);
semilogx(f, energy_ratio, 'm-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('功率传递率 |H(f)|²');
title('频率响应隔振倍率');
grid on;