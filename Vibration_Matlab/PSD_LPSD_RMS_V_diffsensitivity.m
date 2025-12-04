% pcb(V) => PSD & LPSD(g & d) & RMS(Hz)
% ============================================================
% 1）读取多个 CSV（含 time, voltage）
% 2）电压 → 加速度(g)（考虑每个文件独立灵敏度）
% 3）计算：
%       - PSD (g^2/Hz)
%       - 加速度 LPSD (g/√Hz)
%       - 位移 LPSD (nm/√Hz)
%       - RMS（按 1–40, 40–1000, 1–1000 Hz）
% 4）绘制三张图：PSD、加速度 LPSD、位移 LPSD
% 5）导出 RMS 至 Excel（宽表 + 长表）
% ============================================================

function PSD_LPSD_RMS_no()

%% === Quick settings（快速设置）===
time_limit_sec = 510;     % 限制分析前 510 秒（Inf 表示不限制）
auto_xlim      = true;    % 自动设置频率 X 轴范围
xmin_Hz        = 0;       % X 轴最小值（log-scale 需 >0）

%% === File selection（选择 CSV 文件）===
[fileNames, filePath] = uigetfile('*.csv', 'Select voltage-signal CSV files(V)', 'MultiSelect', 'on');
if isequal(fileNames, 0), error('❌ User canceled.'); end
if ischar(fileNames), fileNames = {fileNames}; end
numFiles = numel(fileNames);

%% === Sensor params（传感器参数）===
gain = 100.0;    % 放大倍数
g    = 9.81;     % m/s^2

%% === Ask sensitivity for each file（逐文件输入灵敏度）===
sensitivity = zeros(1, numFiles);
for iFile = 1:numFiles
    fname = fileNames{iFile};
    sensitivity(iFile) = input(['Enter sensitivity (V/g) for file: ', fname, ': ']);
end

%% === Plot style（设置图像风格）===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN,'defaultTextFontName',fontEN,...
    'defaultLegendFontName',fontEN,'defaultUIControlFontName',fontEN,...
    'defaultAxesFontSize',12,'defaultTextInterpreter','none',...
    'defaultLegendInterpreter','none');

figSize = [1, 1, 10, 5];   % 图像尺寸

%% === Figures（三张图：PSD/LPSD/位移LPSD）===
% --- PSD (g^2/Hz) ---
fig1 = figure('Name','Acceleration PSD','Units','inches','Position',figSize,'Color','w');
ax1 = axes(fig1); hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log'); xlabel(ax1,'Frequency (Hz)'); ylabel(ax1,'PSD [g^2/Hz]');

% --- LPSD (g/√Hz) ---
fig2 = figure('Name','Acceleration LPSD','Units','inches','Position',figSize,'Color','w');
ax2 = axes(fig2); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log'); xlabel(ax2,'Frequency (Hz)'); ylabel(ax2,'LPSD [g/√Hz]');

% --- 位移 LPSD (nm/√Hz) ---
fig3 = figure('Name','Displacement LPSD','Units','inches','Position',figSize,'Color','w');
ax3 = axes(fig3); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log'); xlabel(ax3,'Frequency (Hz)'); ylabel(ax3,'LPSD [nm/√Hz]');

colors = lines(numFiles);
if numFiles >= 3, colors(3,:) = [0.8 0.5 0]; end
markers = {'-','--',':','-.'};

%% === RMS bands（RMS 频段）===
band_edges = [1,40; 40,1000; 1,1000];
band_names = {'[1–40] Hz','[40–1000] Hz','[1–1000] Hz'};

allRMS = cell(numFiles,1);
fileLabels = cell(numFiles,1);
df_print = NaN;

%% 自动频率范围
fmax_global = 0;
fmin_pos_global = Inf;

%% ============================================================
%                       Main loop 主循环
% ============================================================
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly] = fileparts(fileNames{iFile});
    fileLabels{iFile} = nameOnly;

    % === 读取 CSV（跳过 1 行表头）===
    opts = detectImportOptions(fullFileName, 'NumHeaderLines', 1);
    data = readmatrix(fullFileName, opts);
    time = data(:,1);
    voltage = data(:,2);

    % === 时间限制 ===
    if isfinite(time_limit_sec)
        time = time - time(1);
        keep = time <= time_limit_sec;
        time = time(keep);
        voltage = voltage(keep);
    end

    % === V → g（不同文件不同灵敏度）===
    a_g = voltage / (sensitivity(iFile) * gain);
    a_g = a_g - mean(a_g);     % 去直流

    % === 检查异常值 ===
    if any(isnan(a_g)) || any(isinf(a_g))
        error('Acceleration data contains NaN/Inf.');
    end

    % === 采样率 ===
    dt = mean(diff(time));
    fs = 1/dt;
    N  = numel(time);

    % === Welch ===
    seglen  = min(round(fs*20), N);
    window  = hamming(seglen);
    overlap = round(seglen/2);
    nfft    = seglen;
    N_win   = max(1, floor((N - overlap)/(seglen - overlap)));

    [pxx_g2, f] = pwelch(a_g, window, overlap, nfft, fs);
    df = mean(diff(f));
    if isnan(df_print), df_print = df; end

    pos = f > 0;

    % === 更新频率范围 ===
    if any(pos)
        fmin_pos_global = min(fmin_pos_global, min(f(pos)));
        fmax_global     = max(fmax_global, max(f(pos)));
    end

    % === LPSD ===
    lpsd_acc = sqrt(pxx_g2);
    lpsd_disp_m = zeros(size(lpsd_acc));
    lpsd_disp_m(pos) = g ./ ((2*pi*f(pos)).^2) .* lpsd_acc(pos);

    % === RMS（g 和 m）===
    RMS_result = zeros(size(band_edges,1),2);
    for iBand = 1:size(band_edges,1)
        idx = (f >= band_edges(iBand,1)) & (f <= band_edges(iBand,2));
        RMS_result(iBand,1) = sqrt(sum((lpsd_acc(idx).^2).*df));     % g
        RMS_result(iBand,2) = sqrt(sum((lpsd_disp_m(idx).^2).*df));  % m
    end
    allRMS{iFile} = RMS_result;

    % === 绘图 ===
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f(pos), pxx_g2(pos), 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5);
    plot(ax2, f(pos), lpsd_acc(pos), 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5);
    plot(ax3, f(pos), lpsd_disp_m(pos)*1e9, 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5);

    % === 打印信息 ===
    fprintf('\n[%s]\n', nameOnly);
    fprintf('fs=%.3f Hz, N=%d, Δf=%.3f Hz, Welch=%d\n', fs, N, df, N_win);
    if isfinite(time_limit_sec)
        fprintf('Time limited to first %.1f s\n', time_limit_sec);
    end
end

%% === 图例 & 标题 ===
legend(ax1,'show'); legend(ax2,'show'); legend(ax3,'show');
title(ax1, sprintf('Power Spectral Density (Δf=%.1f Hz)', df_print));
title(ax2, sprintf('Acceleration LPSD (Δf=%.1f Hz)', df_print));
title(ax3, sprintf('Displacement LPSD (Δf=%.1f Hz)', df_print));

%% === 自动设置 X 轴范围 ===
if auto_xlim
    if ~(isfinite(fmax_global) && fmax_global>0), fmax_global=1; end
    if ~(isfinite(xmin_Hz) && xmin_Hz>0), xmin_Hz = max(0.1, min(fmin_pos_global,1)); end
    xlim(ax1,[xmin_Hz, fmax_global]);
    xlim(ax2,[xmin_Hz, fmax_global]);
    xlim(ax3,[xmin_Hz, fmax_global]);
end

%% === 导出 RMS 到 Excel（宽表 + 长表）===
rms_cell = cell(numFiles, 7);
for iFile = 1:numFiles
    R = allRMS{iFile};
    rms_cell{iFile,1} = fileLabels{iFile};
    for iBand = 1:3
        rms_cell{iFile,iBand+1} = sprintf('%.2f', R(iBand,1)*1e6);   % µg
        rms_cell{iFile,iBand+4} = sprintf('%.2f', R(iBand,2)*1e9);   % nm
    end
end

col_names = {'File','Acc RMS (µg) 1–40','Acc RMS (µg) 40–100','Acc RMS (µg) 1–100',...
             'Disp RMS (nm) 1–40','Disp RMS (nm) 40–100','Disp RMS (nm) 1–100'};

[~, firstStem] = fileparts(fileNames{1});
name = regexprep(firstStem,'[^\w\-.]','_');
xlsxPath = fullfile(filePath, sprintf('%s_RMS_summary.xlsx', name));

longHeader = {'File','Band','Acc RMS (µg)','Disp RMS (nm)'};
longRows = {};
for iFile = 1:numFiles
    R = allRMS{iFile};
    for iBand = 1:3
        longRows(end+1,:) = {fileLabels{iFile}, band_names{iBand}, ...
            round(R(iBand,1)*1e6,3), round(R(iBand,2)*1e9,3)};
    end
end

writecell([col_names; rms_cell], xlsxPath,'Sheet','RMS_Wide');
writecell([longHeader; longRows], xlsxPath,'Sheet','RMS_Long');
fprintf('RMS tables saved: %s\n', xlsxPath);

end
