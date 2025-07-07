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
nfft = 2^nextpow2(length(a_base)/8);
window = hamming(nfft);
overlap = round(0.5 * nfft);
[pxx, f] = pwelch(a_base, window, overlap, nfft, fs);
w = 2 * pi * f;

% === 4. 系统参数 ===
m = 12.80;  % 铜锅质量 kg
zeta = 0.05;  % 阻尼比（必须设置）

% 优化频段（可调），单位 Hz
f_band = [0, 10];
f_idx = f >= f_band(1) & f <= f_band(2);
f_opt = f(f_idx);
pxx_opt = pxx(f_idx);
w_opt = 2 * pi * f_opt;

% === 5. 搜索参数空间（带静态位移约束） ===
x_max = 0.3;                     % 最大静态压缩 (单位: m)
g = 9.81;                        % 重力加速度
k_min = m * g / x_max;          % 最小刚度限制
k_max = 1e4;                     % 最大刚度限制
k_list = logspace(log10(k_min), log10(k_max), 100);

min_ratio = inf;
best_k = NaN;
best_c = NaN;

% === 6. 主循环：优化刚度 k，自动计算阻尼 c ===
for ki = 1:length(k_list)
    k = k_list(ki);
    c = 2 * zeta * sqrt(k * m);

    wn = sqrt(k / m);
    r = w_opt / wn;
    H = 1 ./ sqrt((1 - r.^2).^2 + (2 * zeta * r).^2);

    pxx_out = (H.^2) .* pxx_opt;
    energy_in = trapz(f_opt, pxx_opt);
    energy_out = trapz(f_opt, pxx_out);
    ratio = energy_out / energy_in;

    if ratio < min_ratio
        min_ratio = ratio;
        best_k = k;
        best_c = c;
    end
end

% === 7. 最佳传递函数与 PSD 输出 ===
wn = sqrt(best_k / m);
r = w / wn;
H_best = 1 ./ sqrt((1 - r.^2).^2 + (2 * zeta * r).^2);
pxx_acc = (H_best.^2) .* pxx;

% === 8. 位移 PSD 计算 ===
pxx_disp = pxx_acc ./ (w.^4);
pxx_disp(w == 0) = 0;  % 避免除零

pxx_disp_raw = pxx ./ (w.^4);
pxx_disp_raw(w == 0) = 0;

% === 9. 输出最优参数 ===
fprintf('✅ 最优刚度 k = %.2f N/m\n', best_k);
fprintf('✅ 自动计算阻尼 c = %.2f Ns/m （基于阻尼比 ζ = %.2f）\n', best_c, zeta);
fprintf('🎯 实际阻尼比 zeta_eff = %.4f\n', best_c / (2 * sqrt(best_k * m)));
fprintf('🎯 积分频段 = [%.1f, %.1f] Hz\n', f_band(1), f_band(2));
fprintf('🔻 最小归一化输出能量比 = %.3e\n', min_ratio);

% === 10. 加速度 LPSD 对比图 ===
figure;
loglog(f, sqrt(pxx), 'k--', 'LineWidth', 1.2); hold on;
loglog(f, sqrt(pxx_acc), 'b-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('LPSD (m/s²/√Hz)');
legend('原始加速度 LPSD', '响应加速度 LPSD');
title('原始 vs 响应：加速度 LPSD');
grid on;

% === 11. 位移 LPSD 对比图 ===
figure;
loglog(f, sqrt(pxx_disp_raw), 'k--', 'LineWidth', 1.2); hold on;
loglog(f, sqrt(pxx_disp), 'r-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('LPSD (m/√Hz)');
legend('原始位移 LPSD', '响应位移 LPSD');
title('原始 vs 响应：位移 LPSD');
grid on;

% === 12. 加速度传递函数 H(f) ===
figure;
semilogx(f, H_best, 'k-', 'LineWidth', 1.5);
xlabel('频率 (Hz)');
ylabel('加速度传递率 |H(f)|');
title('加速度传递函数模值');
grid on;

% === 13. 计算位移 RMS（原始 & 响应） ===
df = mean(diff(f));
idx1 = f >= 1 & f <= 40;
idx2 = f >= 40 & f <= 1000;

rms_disp_raw_1 = sqrt(sum(pxx_disp_raw(idx1)) * df);
rms_disp_raw_2 = sqrt(sum(pxx_disp_raw(idx2)) * df);
rms_disp_resp_1 = sqrt(sum(pxx_disp(idx1)) * df);
rms_disp_resp_2 = sqrt(sum(pxx_disp(idx2)) * df);

fprintf('\n=== 位移 RMS 结果 ===\n');
fprintf('📏 原始位移 RMS [1–40 Hz] = %.3e m\n', rms_disp_raw_1);
fprintf('📏 原始位移 RMS [40–1000 Hz] = %.3e m\n', rms_disp_raw_2);
fprintf('📉 响应位移 RMS [1–40 Hz] = %.3e m\n', rms_disp_resp_1);
fprintf('📉 响应位移 RMS [40–1000 Hz] = %.3e m\n', rms_disp_resp_2);

% === 14. 保存结果 ===
fid = fopen('最优参数结果.txt','w');
fprintf(fid, '最优刚度 k = %.4f N/m\n', best_k);
fprintf(fid, '最优阻尼 c = %.4f Ns/m\n', best_c);
fprintf(fid, '最小归一化能量比 = %.3e\n', min_ratio);
fprintf(fid, '响应位移 RMS [1–40 Hz] = %.3e m\n', rms_disp_resp_1);
fprintf(fid, '响应位移 RMS [40–1000 Hz] = %.3e m\n', rms_disp_resp_2);
fclose(fid);
