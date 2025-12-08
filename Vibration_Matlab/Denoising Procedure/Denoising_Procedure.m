function Hxy_denoise_windows()
%% ============================================================
% 多通道 H_xy 去噪（CUORE 风格，带窗口选择版）
%  - X 通道：多个辅助噪声传感器，用“全时段数据”估计 G_xx
%  - Y 通道：bolo 主信号，只用指定的 10 个 5 s 窗口估计 G_xy & 去噪
%
% 说明：
%   1) 先用所有 X 通道的全时段数据估计自谱/互谱 G_xx(f)
%   2) 再用 X、Y 在 10 个 5 s 窗口内的数据估计 G_xy(f)
%   3) 得到 H(f) = G_xx^{-1}(f) * G_xy(f)
%   4) 用 H(f) 对窗口拼接后的 X(t) 做滤波，得到 y_hat(t)、y_res(t)
% ============================================================

%% ===== 参数设置 =====
header     = 4;      % CSV 文件前几行表头
detrend_on = true;   % 是否去直流分量
df_target  = 0.2;    % Welch 目标频率分辨率 Δf
overlap_fr = 0.95;   % Welch 重叠率（95%）

% 指定 10 个 5 秒窗口（单位：秒）
time_windows = [
    0*60+0   0*60+5;
    0*60+10   0*60+15;
    0*60+25   0*60+30;
    0*60+50   0*60+55;
    1*60+00   1*60+05;
    1*60+05   1*60+10;
    1*60+10   1*60+15;
    1*60+20   1*60+25;
    1*60+35   1*60+40;
    1*60+45  1*60+50
];

%% ===== 1) 选择多个 X CSV 文件 =====
[xFiles, xPath] = uigetfile('*.csv', ...
    'Select X CSV files (auxiliary sensors)', ...
    'MultiSelect','on');
if isequal(xFiles,0)
    error('No X files selected.');
end

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

%% ===== 3) 读取所有 X 与 Y（原始时间轴） =====
Xs_raw   = cell(nX,1);   % 每个 X 通道的原始数据
ts_raw   = cell(nX,1);   % 每个 X 通道的时间轴
Fs_list  = zeros(nX,1);  % 每个 X 通道的采样率

% 读取 X
for k = 1:nX
    fname = fullfile(xPath, xFiles{k});
    opts = detectImportOptions(fname);
    opts.DataLines = [header+1, Inf];
    opts.VariableNamingRule = 'preserve';
    T = readtable(fname, opts);

    t = T{:,1};
    v = T{:,2};
    [t, idx] = sort(t(:)); v = v(idx);

    if any(isnan(t) | isnan(v))
        error('NaN found in X file: %s', xFiles{k});
    end

    ts_raw{k}  = t;
    Xs_raw{k}  = v;
    Fs_list(k) = 1/median(diff(t));
end

% 读取 Y（full）
optsY = detectImportOptions(fullfile(yPath,yFile));
optsY.DataLines = [header+1, Inf];
optsY.VariableNamingRule = 'preserve';
TY = readtable(fullfile(yPath,yFile), optsY);

tY_full = TY{:,1};
Yv_full = TY{:,2};
[tY_full, idxY] = sort(tY_full(:));
Yv_full = Yv_full(idxY);

if any(isnan(tY_full) | isnan(Yv_full))
    error('NaN found in Y file.');
end
FsY = 1/median(diff(tY_full));

%% ===== 输出输入数据统计 =====
fprintf('\n===== INPUT DATA INFORMATION =====\n');
for k = 1:nX
    Nk = numel(ts_raw{k});
    duration_k = ts_raw{k}(end) - ts_raw{k}(1);
    Fsk = Fs_list(k);
    fprintf('X%d: %d samples, duration = %.3f s, Fs = %.3f Hz\n', ...
        k, Nk, duration_k, Fsk);
end
Ny = numel(tY_full);
durationY = tY_full(end) - tY_full(1);
fprintf('Y(full):  %d samples, duration = %.3f s, Fs = %.3f Hz\n', ...
    Ny, durationY, FsY);
fprintf('=================================\n');

%% ===== 4) 选公共采样率 Fs（取最小 Fs，四舍五入） =====
Fs = round(min([Fs_list(:); FsY]));
fprintf('Common Fs (resample target) = %.2f Hz\n', Fs);

%% ===== 5) 构建用于 G_xx 的 X 全时段统一时间轴 =====
t0_X = -Inf;
t1_X =  Inf;
for k = 1:nX
    t0_X = max(t0_X, ts_raw{k}(1));
    t1_X = min(t1_X, ts_raw{k}(end));
end
if t1_X <= t0_X
    error('No common time interval among all X channels.');
end

tX_full = (t0_X : 1/Fs : t1_X).';
NX = numel(tX_full);
fprintf('\n=== Time range for G_xx estimation (X only) ===\n');
fprintf('t0_X = %.6f s, t1_X = %.6f s, duration = %.6f s, NX = %d\n', ...
    t0_X, t1_X, t1_X - t0_X, NX);

% 插值得到 X_full
X_full = zeros(NX, nX);
for k = 1:nX
    X_full(:,k) = interp1(ts_raw{k}, Xs_raw{k}, tX_full, 'linear');
end

% 去掉插值导致的 NaN 行
maskX = ~any(isnan(X_full),2);
if ~all(maskX)
    X_full = X_full(maskX,:);
    tX_full = tX_full(maskX);
    NX = numel(tX_full);
    fprintf('After removing NaNs in X_full: NX = %d\n', NX);
end

%% ===== 6) 构造只包含 10 个窗口的 (X_win, Y_win) 数据 =====
t_win_all = [];
Y_win_all = [];
X_win_all = [];

for w = 1:size(time_windows,1)
    t0 = time_windows(w,1);
    t1 = time_windows(w,2);

    % 5 秒窗口的统一时间轴（按照 Fs 重采样）
    t_win = (t0 : 1/Fs : t1).';

    % 插值 X
    Xw = zeros(numel(t_win), nX);
    for k = 1:nX
        Xw(:,k) = interp1(ts_raw{k}, Xs_raw{k}, t_win, 'linear');
    end

    % 插值 Y
    Yw = interp1(tY_full, Yv_full, t_win, 'linear');

    % 去掉窗口内部的 NaN（可能发生在边界）
    mask = ~any(isnan([Xw, Yw]), 2);
    Xw = Xw(mask,:);
    Yw = Yw(mask);
    t_w_valid = t_win(mask);

    if isempty(Yw)
        warning('Window %d [%.2f, %.2f] s has no valid data, skipped.', w, t0, t1);
        continue;
    end

    t_win_all = [t_win_all; t_w_valid];
    Y_win_all = [Y_win_all; Yw];
    X_win_all = [X_win_all; Xw];
end

Nw = numel(t_win_all);
if Nw == 0
    error('No valid data in all specified windows for Y.');
end

fprintf('\n=== Y windows summary ===\n');
fprintf('Total concatenated window length: %.3f s, Nw = %d samples\n', ...
    t_win_all(end) - t_win_all(1), Nw);

%% ===== 7) 去直流（X_full 用于 G_xx；X_win/Y_win 用于 G_xy & 过滤） =====
if detrend_on
    X_full = detrend(X_full, 0);
    X_win_all = detrend(X_win_all, 0);
    Y_win_all = detrend(Y_win_all, 0);
end

%% ===== 8) Welch 参数（统一用于 G_xx 和 G_xy） =====
Nmin = min(NX, Nw);
wlen = round(Fs / df_target);
wlen = max(256, min(wlen, Nmin));     % 保证不过长
noverlap = min(floor(wlen*overlap_fr), wlen-1);
nfft = 2^nextpow2(max([wlen, NX, Nw]));
df_act = Fs / wlen;

fprintf('\n=== Welch parameters ===\n');
fprintf('wlen = %d, nfft = %d, overlap = %d (%.1f%%), Δf ≈ %.3f Hz\n', ...
    wlen, nfft, noverlap, overlap_fr*100, df_act);

win = hann(wlen);

%% ===== 9) 计算 G_xx（仅用 X_full，全时段） =====
Gxx = zeros(nX, nX, nfft/2+1);

for i = 1:nX
    % 自谱
    [Sii, f] = pwelch(X_full(:,i), win, noverlap, nfft, Fs);
    Gxx(i,i,:) = Sii;

    % 互谱
    for j = i+1:nX
        [Sij, ~] = cpsd(X_full(:,i), X_full(:,j), win, noverlap, nfft, Fs);
        Gxx(i,j,:) = Sij;
        Gxx(j,i,:) = conj(Sij);
    end
end

nFreq = numel(f);

%% ===== 10) 计算 G_xy（用窗口拼接的 X_win & Y_win） =====
Gxy = zeros(nX, nFreq);
for i = 1:nX
    [Siy, ~] = cpsd(X_win_all(:,i), Y_win_all, win, noverlap, nfft, Fs);
    Gxy(i,:) = Siy;
end

%% ===== 11) 求 H(f) = G_xx^{-1} * G_xy =====
H = zeros(nX, nFreq);
for kf = 1:nFreq
    Gxx_k = squeeze(Gxx(:,:,kf));
    gxy_k = Gxy(:,kf);

    % 正则化，避免矩阵病态
    reg = 1e-6 * trace(Gxx_k) / max(nX,1);
    if ~isfinite(reg) || reg <= 0
        reg = 1e-6;
    end
    Gxx_k = Gxx_k + reg * eye(nX);

    H(:,kf) = Gxx_k \ gxy_k;
end

%% ===== 12) 构造完整频率响应 H_full (nfft×nX)，用于时域滤波 =====
H_full = zeros(nfft, nX);
for i = 1:nX
    Hi_pos = H(i,:).';
    H_full(1:nFreq, i) = Hi_pos;

    % 填负频率，保持实信号
    if mod(nfft,2) == 0
        % nfft 偶数，nFreq = nfft/2 + 1
        H_full(nFreq+1:end, i) = conj(Hi_pos(end-1:-1:2));
    else
        % nfft 奇数，nFreq = (nfft+1)/2
        H_full(nFreq+1:end, i) = conj(Hi_pos(end:-1:2));
    end
end

%% ===== 13) 在窗口数据上应用 H(f)，得到 y_hat(t) 与残差信号 =====
% 使用窗口拼接后的 X_win_all 进行滤波
Xf_win = fft(X_win_all, nfft, 1);          % nfft × nX
Yhat_f = sum(Xf_win .* H_full, 2);         % nfft × 1
y_hat  = real(ifft(Yhat_f));               % nfft × 1
y_hat  = y_hat(1:Nw);                      % 只取前 Nw 点

y_res = Y_win_all - y_hat;                 % 去噪后信号

%% ===== 14) 去噪前后 PSD（单位 mV^2/Hz） =====
[Py,  f_psd] = pwelch(Y_win_all, win, noverlap, nfft, Fs);
[Pres,~]     = pwelch(y_res,     win, noverlap, nfft, Fs);

Py_mV   = Py   * 1e6;
Pres_mV = Pres * 1e6;

figure('Color','w'); hold on; grid on; box on;
set(gca, 'XScale','log','YScale','log');
plot(f_psd, Py_mV,   'LineWidth',1.6);
plot(f_psd, Pres_mV, 'LineWidth',1.6,'LineStyle','--');
xlabel('Frequency [Hz]');
ylabel('Power Spectral Density [mV^2/Hz]');
title(sprintf('ANPS Before/After H_{xy} Denoising (10×5 s windows, \\Delta f = %.3f Hz)', df_act));
legend('Raw Y (windows only)','Denoised y_{res}','Location','best');

%% ===== 15) 时域对比图（仅拼接后的窗口时段） =====
figure('Color','w'); hold on; grid on; box on;
plot(t_win_all, Y_win_all*1e3, 'LineWidth',1.2);
plot(t_win_all, y_res*1e3,     'LineWidth',1.2);
xlabel('Time [s]');
ylabel('Amplitude [mV]');
title('Time-domain Signal Before/After H_{xy} Denoising (concatenated windows)');
legend('Raw Y (windows)','Denoised y_{res}','Location','best');

fprintf('\nDone H_xy denoising using 10 windows of Y.\n');
end
