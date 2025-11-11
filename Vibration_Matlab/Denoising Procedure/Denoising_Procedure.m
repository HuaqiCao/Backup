%% === Minimal H_xy-based denoising (PPT notation aligned) ===

%% Settings
header = 4;              % 跳过表头行
detrend_on = true;       % 去均值（建议开）
df_target  = 0.050;      % 🎯 目标频率分辨率(Hz)
overlap_fr = 0.95;       % Welch 重叠

%% Pick files (先 X1 后 X2，再 Y)
[xFile1, xPath1] = uigetfile('*.csv','请选择第一个 X 的 CSV');
if isequal(xFile1,0), error('未选X1'); end
[xFile2, xPath2] = uigetfile('*.csv','请选择第二个 X 的 CSV');
if isequal(xFile2,0), error('未选X2'); end
[yFile, yPath] = uigetfile('*.csv','请选择 Y 的 CSV');
if isequal(yFile,0), error('未选Y'); end

%% Read two columns [t, V]
optsX1 = detectImportOptions(fullfile(xPath1,xFile1)); optsX1.DataLines = [header+1, Inf];
TX1 = readtable(fullfile(xPath1,xFile1), optsX1);
tX1 = TX1{:,1}; Xv1 = TX1{:,2}; [tX1, kx1] = sort(tX1(:)); Xv1 = Xv1(kx1);

optsX2 = detectImportOptions(fullfile(xPath2,xFile2)); optsX2.DataLines = [header+1, Inf];
TX2 = readtable(fullfile(xPath2,xFile2), optsX2);
tX2 = TX2{:,1}; Xv2 = TX2{:,2}; [tX2, kx2] = sort(tX2(:)); Xv2 = Xv2(kx2);

optsY = detectImportOptions(fullfile(yPath,yFile)); optsY.DataLines = [header+1, Inf];
TY = readtable(fullfile(yPath,yFile), optsY);
tY = TY{:,1}; Yv = TY{:,2}; [tY, ky] = sort(tY(:)); Yv = Yv(ky);

if any(isnan([tX1;Xv1;tX2;Xv2;tY;Yv])), error('数据含 NaN'); end

%% Align to common time base
FsX1 = 1/median(diff(tX1)); FsX2 = 1/median(diff(tX2)); FsY = 1/median(diff(tY));
Fs  = round(mean([FsX1, FsX2, FsY]));  % 统一采样率

% 将最小时间和最大时间作为向量传入max和min函数
t0 = max([tX1(1), tX2(1), tY(1)]);  % 获取最大的起始时间
t1 = min([tX1(end), tX2(end), tY(end)]);  % 获取最小的结束时间

if t1 <= t0, error('两段数据无重叠'); end
t = (t0:1/Fs:t1).';  % 生成共同的时间向量

X1 = interp1(tX1, Xv1, t, 'linear', 'extrap');
X2 = interp1(tX2, Xv2, t, 'linear', 'extrap');
Y = interp1(tY, Yv, t, 'linear', 'extrap');
if detrend_on, X1 = detrend(X1,0); X2 = detrend(X2,0); Y = detrend(Y,0); end
N = numel(t);

%% Welch params from target Δf
wlen = round(Fs / df_target);  % 窗口长度确保分辨率符合目标
noverlap = min(floor(wlen*overlap_fr), wlen-1);
nfft = 2^nextpow2(max(N, wlen));  % 确保 ifft 不越界
df_act = Fs / wlen;

%% Compute cross/auto spectra and H_xy
[G_xx1, f] = pwelch(X1, hann(wlen), noverlap, nfft, Fs);
[G_xx2, ~] = pwelch(X2, hann(wlen), noverlap, nfft, Fs);
G_xy = cpsd(X1, Y, hann(wlen), noverlap, nfft, Fs);

H_xy1 = G_xy ./ (G_xx1 + eps);  % eps 防止除零
H_xy2 = G_xy ./ (G_xx2 + eps);  % eps 防止除零

H_xy1(~isfinite(H_xy1)) = 0;
H_xy2(~isfinite(H_xy2)) = 0;

%% Predict Y_hat via H_xy and get residual y'
H_full1 = ones(nfft, 1);
H_full1(1:numel(H_xy1)) = H_xy1;
if mod(nfft, 2) == 0
    H_full1(numel(H_xy1)+1:end) = conj(H_xy1(end-1:-1:2));
else
    H_full1(numel(H_xy1)+1:end) = conj(H_xy1(end:-1:2));
end

H_full2 = ones(nfft, 1);
H_full2(1:numel(H_xy2)) = H_xy2;
if mod(nfft, 2) == 0
    H_full2(numel(H_xy2)+1:end) = conj(H_xy2(end-1:-1:2));
else
    H_full2(numel(H_xy2)+1:end) = conj(H_xy2(end:-1:2));
end

X_f = fft(X1, nfft);
Y_hat_f1 = X_f .* H_full1;
y_hat1 = real(ifft(Y_hat_f1));  y_hat1 = y_hat1(1:N);

X_f2 = fft(X2, nfft);
Y_hat_f2 = X_f2 .* H_full2;
y_hat2 = real(ifft(Y_hat_f2));  y_hat2 = y_hat2(1:N);

y_prime = Y - (y_hat1 + y_hat2);  % y' = Y - ˆy

%% ---------- Plots (clean aesthetics) ----------

lw = 1.6; fs = 14;

% ① Time domain: y vs y'
figure('Color','w'); hold on; grid on; box on;
plot(t, Y, 'LineWidth', lw);
plot(t, y_prime, 'LineWidth', lw, 'LineStyle', '--');
xlabel('Time (s)', 'FontSize', fs); ylabel('Voltage (V)', 'FontSize', fs);
title('Time Domain: y vs. y''', 'FontSize', fs+2);
legend('y (original)', 'y'' (residual)', 'Location', 'best', 'FontSize', fs);
set(gca, 'FontSize', fs);  % 设置坐标轴字体大小

% ② PSD(x) vs PSD(y) and PSD(y') [log-log]
[Px, ~] = pwelch(X1, hann(wlen), noverlap, nfft, Fs);  % 计算 x1 的 PSD
[Py, f_psd] = pwelch(Y, hann(wlen), noverlap, nfft, Fs);  % 计算 y 的 PSD
[PyP, ~] = pwelch(y_prime, hann(wlen), noverlap, nfft, Fs);  % 计算去噪后的 PSD

% 优化 PSD 图
figure('Color','w'); hold on; grid on; box on;
set(gca, 'XScale', 'log', 'YScale', 'log', 'FontSize', fs);
plot(f_psd, Px, 'LineWidth', lw, 'Color', [0, 1, 0]);  % 设置 x 的 PSD 为绿色
plot(f_psd, Py, 'LineWidth', lw, 'Color', [0, 0, 1]);  % 设置 y 的 PSD 为蓝色
plot(f_psd, PyP, 'LineWidth', lw, 'LineStyle', '--', 'Color', [1, 0.5, 0]);  % 设置去噪后的 PSD 为橙色
xlabel('Frequency (Hz)', 'FontSize', fs);
ylabel('PSD (V^2/Hz)', 'FontSize', fs);
title(sprintf('PSD: x, y and y'' (Δf = %.3f Hz)', df_act), 'FontSize', fs+2);
legend('x1 (original)', 'y (original)', 'y'' (residual)', 'Location', 'best', 'FontSize', fs);

% 设置 x 轴范围，从 10^-1 开始
xlim([10^-1, max(f_psd)]);  % 将横轴从 10^-1 到最大频率

% ③ |H_xy(f)| and ∠H_xy(f)
figure('Color', 'w');
subplot(2, 1, 1); hold on; grid on; box on;
semilogx(f, 20*log10(abs(H_xy1)+eps), 'LineWidth', lw, 'Color', [0, 0, 1]);
ylabel('|H_{xy1}(f)| (dB)', 'FontSize', fs);
title('Transfer Function Magnitude', 'FontSize', fs+2);

subplot(2, 1, 2); hold on; grid on; box on;
semilogx(f, unwrap(angle(H_xy1)), 'LineWidth', lw, 'Color', [0, 0, 1]);
xlabel('Frequency (Hz)', 'FontSize', fs);
ylabel('\angle H_{xy1}(f) (rad)', 'FontSize', fs); % 结束字符向量
title('Transfer Function Phase', 'FontSize', fs+2);

% 输出图片时提高分辨率，保证高质量
exportgraphics(gcf, fullfile(yPath, [xFile1(1:end-4), '_PSD_compare_highres.png']), 'Resolution', 300);
exportgraphics(gcf, fullfile(yPath, [xFile1(1:end-4), '_Transfer_Function.png']), 'Resolution', 300);

fprintf('Done. Δf_target=%.3f Hz, Δf_actual=%.3f Hz, Fs=%g Hz, wlen=%d.\n', df_target, df_act, Fs, wlen);
