%% ============================================================
% 本程序用于执行“多通道 H_xy 去噪”（CUORE 风格）。
% X 通道为辅助噪声传感器，Y 通道为主信号（bolo）。
%% ============================================================

%% ===== 参数设置 =====
header     = 4;      % CSV 文件前几行表头
detrend_on = true;   % 是否去直流分量
df_target  = 0.2;    % Welch 目标频率分辨率 Δf
overlap_fr = 0.95;   % Welch 重叠率

%% ===== 1) 选择多个 X CSV 文件 =====
[xFiles, xPath] = uigetfile('*.csv', ...
    'Select X CSV files (auxiliary sensors)', ...
    'MultiSelect','on');
if isequal(xFiles,0)
    error('No X files selected.');
end

% 若只选一个文件，转换成 cell
if ischar(xFiles)
    xFiles = {xFiles};
end
nX = numel(xFiles);
fprintf('Selected %d X-files.\n', nX);

%% ===== 2) 选择 Y（bolo）文件 =====
[yFile, yPath] = uigetfile('*.csv','Select Y CSV file (bolometer)');
if isequal(yFile,0)
    error('No Y file selected.');
end
fprintf('Y file: %s\n', yFile);

%% ===== 3) 读取所有 X 与 Y =====
Xs_raw = cell(nX,1);
ts_raw = cell(nX,1);
Fs_list = zeros(nX,1);

% 读取 X
for k = 1:nX
    fname = fullfile(xPath, xFiles{k});
    opts = detectImportOptions(fname);
    opts.DataLines = [header+1, Inf];
    opts.VariableNamingRule = 'preserve';
    T = readtable(fname, opts);

    t = T{:,1};    % 时间列
    v = T{:,2};    % 数据列
    [t, idx] = sort(t(:)); v = v(idx);

    if any(isnan(t) | isnan(v))
        error('NaN found in X file: %s', xFiles{k});
    end

    ts_raw{k}   = t;
    Xs_raw{k}   = v;
    Fs_list(k)  = 1/median(diff(t));
end

% 读取 Y
optsY = detectImportOptions(fullfile(yPath,yFile));
optsY.DataLines = [header+1, Inf];
optsY.VariableNamingRule = 'preserve';
TY = readtable(fullfile(yPath,yFile), optsY);

tY = TY{:,1};
Yv = TY{:,2};
[tY, idxY] = sort(tY(:)); Yv = Yv(idxY);

if any(isnan(tY) | isnan(Yv))
    error('NaN found in Y file.');
end
FsY = 1/median(diff(tY));

%% ===== 输出输入数据统计 =====
fprintf('\n===== INPUT DATA INFORMATION =====\n');
for k = 1:nX
    Nk = numel(ts_raw{k});
    duration_k = ts_raw{k}(end) - ts_raw{k}(1);
    Fsk = Fs_list(k);
    fprintf('X%d: %d samples, duration = %.3f s, Fs = %.3f Hz\n', ...
        k, Nk, duration_k, Fsk);
end
Ny = numel(tY);
durationY = tY(end) - tY(1);
fprintf('Y:  %d samples, duration = %.3f s, Fs = %.3f Hz\n', ...
    Ny, durationY, FsY);
fprintf('=================================\n');

%% ===== 4) 选公共采样率（取最小 Fs） =====
Fs = round(min([Fs_list(:); FsY]));
fprintf('Common Fs (resample target) = %.2f Hz\n', Fs);

%% ===== 5) 求所有通道的公共时间区间（区间交集） =====
t_start = zeros(nX+1,1);
t_end   = zeros(nX+1,1);
for k = 1:nX
    t_start(k) = ts_raw{k}(1);
    t_end(k)   = ts_raw{k}(end);
end
t_start(end) = tY(1);
t_end(end)   = tY(end);

t0 = max(t_start);   % 最晚起点
t1 = min(t_end);     % 最早终点
if t1 <= t0
    error('No common time interval among all channels.');
end

fprintf('\n=== Time alignment (overlap intersection) ===\n');
fprintf('t0 = %.6f s, t1 = %.6f s, duration = %.6f s\n', ...
    t0, t1, t1 - t0);

% 公共统一时间轴
t = (t0 : 1/Fs : t1).';
N = numel(t);
fprintf('Common grid: %d samples, Fs = %.3f Hz\n', N, Fs);

%% ===== 6) 各通道插值到统一时间轴 =====
X = zeros(N, nX);
for k = 1:nX
    X(:,k) = interp1(ts_raw{k}, Xs_raw{k}, t, 'linear');
end
Y = interp1(tY, Yv, t, 'linear');

% 去掉插值边界 NaN
mask = ~any(isnan([X Y]),2);
if ~all(mask)
    X = X(mask,:);
    Y = Y(mask);
    t = t(mask);
    N = numel(t);
    fprintf('After removing NaNs at edges: N = %d samples\n', N);
end

% 去直流
if detrend_on
    X = detrend(X, 0);
    Y = detrend(Y, 0);
end

%% ===== 7) Welch 参数（根据目标 Δf 设置窗长） =====
wlen = round(Fs / df_target);
wlen = min(wlen, N);
wlen = max(wlen, 256);
noverlap = min(floor(wlen*overlap_fr), wlen-1);
nfft = 2^nextpow2(max(N, wlen));
df_act = Fs / wlen;
fprintf('wlen = %d, nfft = %d, Δf ≈ %.3f Hz\n', wlen, nfft, df_act);

%% ===== 8) 计算自谱 G_xx 和互谱 G_xy =====
Gxx = zeros(nX, nX, nfft/2+1);
Gxy = zeros(nX,       nfft/2+1);

win = hann(wlen);

for i = 1:nX
    % 自谱
    [Sii, f] = pwelch(X(:,i), win, noverlap, nfft, Fs);
    Gxx(i,i,:) = Sii;

    % X_i 与 X_j 的互谱
    for j = i+1:nX
        [Sij, ~] = cpsd(X(:,i), X(:,j), win, noverlap, nfft, Fs);
        Gxx(i,j,:) = Sij;
        Gxx(j,i,:) = conj(Sij);
    end

    % X_i 与 Y 的互谱
    [Siy, ~] = cpsd(X(:,i), Y, win, noverlap, nfft, Fs);
    Gxy(i,:) = Siy;
end

nFreq = numel(f);

%% ===== 9) 计算 H(f) = G_xx^{-1} * G_xy =====
H = zeros(nX, nFreq);
for kf = 1:nFreq
    Gxx_k = squeeze(Gxx(:,:,kf));
    gxy_k = Gxy(:,kf);

    % 小正则项，避免矩阵病态
    reg = 1e-6 * trace(Gxx_k) / max(nX,1);
    if ~isfinite(reg) || reg <= 0
        reg = 1e-6;
    end
    Gxx_k = Gxx_k + reg * eye(nX);

    % 求解 H
    H(:,kf) = Gxx_k \ gxy_k;
end

%% ===== 10) 构造完整频域滤波器，回时域得到 y'(t) =====
H_full = zeros(nfft, nX);
for i = 1:nX
    Hi_pos = H(i,:).';
    H_full(1:nFreq, i) = Hi_pos;

    % 填充负频率
    if mod(nfft,2) == 0
        H_full(nFreq+1:end, i) = conj(Hi_pos(end-1:-1:2));
    else
        H_full(nFreq+1:end, i) = conj(Hi_pos(end:-1:2));
    end
end

X_f = fft(X, nfft, 1);
Y_hat_f = sum(X_f .* H_full, 2);
y_hat   = real(ifft(Y_hat_f));
y_hat   = y_hat(1:N);

y_res = Y - y_hat;   % 去噪后信号

%% ===== 11) 去噪前后 PSD（单位 mV^2/Hz） =====
[Py,  f_psd] = pwelch(Y,     win, noverlap, nfft, Fs);
[Pres,~]     = pwelch(y_res, win, noverlap, nfft, Fs);

Py_mV   = Py   * 1e6;
Pres_mV = Pres * 1e6;

figure('Color','w'); hold on; grid on; box on;
set(gca, 'XScale','log','YScale','log');
plot(f_psd, Py_mV,   'LineWidth',1.6);
plot(f_psd, Pres_mV, 'LineWidth',1.6,'LineStyle','--');
xlabel('Frequency [Hz]');
ylabel('Power Spectral Density [mV^2/Hz]');
title(sprintf('Average ANPS Before and After Denoising (\\Delta f = %.3f Hz)', df_act));
legend('Raw ANPS','Denoised ANPS','Location','best');

fprintf('Done.\n');

%% ===== 12) 新图：时域对比 =====
figure('Color','w'); hold on; grid on; box on;
plot(t, Y*1e3, 'LineWidth',1.2);
plot(t, y_res*1e3, 'LineWidth',1.2);
xlabel('Time [s]');
ylabel('Amplitude [mV]');
title('Time-domain Signal Before and After H_{xy} Denoising');
legend('Raw Y(t)', 'Denoised y''(t)', 'Location', 'best');
