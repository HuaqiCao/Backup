%% ===== Multi-channel H_xy Denoising (CUORE-style) =====
% First dialog: select X CSV files (multi-select)
% Second dialog: select Y CSV file (single)
% Formula:
%   G_xx(f) = < X_i^*(f) X_j(f) >
%   G_xy(f) = < X_i^*(f) Y(f) >
%   H(f)    = G_xx^{-1}(f) G_xy(f)
%   y'(t)   = y(t) - sum_i h_i * x_i(t)

%% Settings
header     = 4;      % number of header lines to skip in CSV
detrend_on = true;   % remove mean
df_target  = 0.5;    % target frequency resolution (Hz)
overlap_fr = 0.95;   % Welch overlap fraction

%% ===== 1) Pick X-files (auxiliary sensors) =====
[xFiles, xPath] = uigetfile('*.csv', ...
    'Select X CSV files (auxiliary sensors)', ...
    'MultiSelect','on');
if isequal(xFiles,0)
    error('No X files selected.');
end

% Normalize to cell array
if ischar(xFiles)
    xFiles = {xFiles};
end
nX = numel(xFiles);
fprintf('Selected %d X-files.\n', nX);

%% ===== 2) Pick Y-file (bolometer) =====
[yFile, yPath] = uigetfile('*.csv','Select Y CSV file (bolometer)');
if isequal(yFile,0)
    error('No Y file selected.');
end
fprintf('Y file: %s\n', yFile);

%% ===== 3) Read all X and Y, build common time base =====
Xs_raw = cell(nX,1);
ts_raw = cell(nX,1);
Fs_list = zeros(nX,1);

% Read X files
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

    ts_raw{k}   = t;
    Xs_raw{k}   = v;
    Fs_list(k)  = 1/median(diff(t));
end

% Read Y file
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

% Unified sampling rate (approx.)
Fs = round(mean([Fs_list(:); FsY]));
fprintf('Approx. Fs = %.2f Hz\n', Fs);

% Find common time interval
t_start = zeros(nX+1,1);
t_end   = zeros(nX+1,1);
for k = 1:nX
    t_start(k) = ts_raw{k}(1);
    t_end(k)   = ts_raw{k}(end);
end
t_start(end) = tY(1);
t_end(end)   = tY(end);

t0 = max(t_start);
t1 = min(t_end);
if t1 <= t0
    error('No common time interval among all channels.');
end

t = (t0:1/Fs:t1).';
N = numel(t);
fprintf('Common duration: %.2f s (%d samples)\n', t1 - t0, N);

% Interpolate to common grid
X = zeros(N, nX);
for k = 1:nX
    X(:,k) = interp1(ts_raw{k}, Xs_raw{k}, t, 'linear', 'extrap');
end
Y = interp1(tY, Yv, t, 'linear', 'extrap');

if detrend_on
    X = detrend(X, 0);
    Y = detrend(Y, 0);
end

%% ===== 4) Welch parameters from target Δf =====
wlen = round(Fs / df_target);
wlen = min(wlen, N);      % cannot exceed signal length
wlen = max(wlen, 256);    % reasonable minimum
noverlap = min(floor(wlen*overlap_fr), wlen-1);
nfft = 2^nextpow2(max(N, wlen));
df_act = Fs / wlen;
fprintf('wlen = %d, nfft = %d, Δf ≈ %.3f Hz\n', wlen, nfft, df_act);

%% ===== 5) Compute G_xx(f) and G_xi_y(f) (Welch) =====
% G_xx(i,j,f) = < X_i^*(f) X_j(f) >
% G_xy(i,f)   = < X_i^*(f) Y(f)   >

Gxx = zeros(nX, nX, nfft/2+1);
Gxy = zeros(nX,       nfft/2+1);

win = hann(wlen);

for i = 1:nX
    % Auto-spectrum G_xi_xi
    [Sii, f] = pwelch(X(:,i), win, noverlap, nfft, Fs);
    Gxx(i,i,:) = Sii;

    % Cross-spectrum between X_i and X_j
    for j = i+1:nX
        [Sij, ~] = cpsd(X(:,i), X(:,j), win, noverlap, nfft, Fs);
        Gxx(i,j,:) = Sij;
        Gxx(j,i,:) = conj(Sij);
    end

    % Cross with Y: G_xi_y
    [Siy, ~] = cpsd(X(:,i), Y, win, noverlap, nfft, Fs);
    Gxy(i,:) = Siy;
end

nFreq = numel(f);

%% ===== 6) H(f) = G_xx^{-1}(f) * G_xy(f) =====
H = zeros(nX, nFreq);
for kf = 1:nFreq
    Gxx_k = squeeze(Gxx(:,:,kf));   % nX × nX
    gxy_k = Gxy(:,kf);              % nX × 1

    % Small diagonal regularization
    reg = 1e-6 * trace(Gxx_k) / max(nX,1);
    if ~isfinite(reg) || reg <= 0
        reg = 1e-6;
    end
    Gxx_k = Gxx_k + reg * eye(nX);

    % Solve G_xx * H = G_xy
    H(:,kf) = Gxx_k \ gxy_k;
end

%% ===== 7) Build full H(f) and compute residual y'(t) =====
H_full = zeros(nfft, nX);
for i = 1:nX
    Hi_pos = H(i,:).';          % 0..Fs/2
    H_full(1:nFreq, i) = Hi_pos;

    if mod(nfft,2) == 0
        H_full(nFreq+1:end, i) = conj(Hi_pos(end-1:-1:2));
    else
        H_full(nFreq+1:end, i) = conj(Hi_pos(end:-1:2));
    end
end

X_f = fft(X, nfft, 1);          % nfft × nX
Y_f = fft(Y, nfft, 1);          % nfft × 1 (not used directly here)

Y_hat_f = sum(X_f .* H_full, 2);
y_hat   = real(ifft(Y_hat_f));
y_hat   = y_hat(1:N);

y_res = Y - y_hat;              % residual y'(t)

%% ===== 8) PSD before / after denoising (in mV^2/Hz) =====
[Py,  f_psd] = pwelch(Y,     win, noverlap, nfft, Fs);
[Pres,~]     = pwelch(y_res, win, noverlap, nfft, Fs);

% Convert from V^2/Hz to mV^2/Hz: multiply by (1e3)^2 = 1e6
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
