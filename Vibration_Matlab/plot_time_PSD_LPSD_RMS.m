%% ===== 参数区 =====
gain = 100;                 % 前端放大增益
sens_g_per_V = 1.026;       % 传感器灵敏度 (g/V)
remove_dc = true;           % 是否去直流（每条曲线减均值）
zero_time_start = true;     % 是否把每条曲线时间零点对齐
g0 = 9.81;                  % 重力加速度 (m/s^2)

% RMS 频带设置（Hz）
band_edges = [1, 40; 40, 100; 1, 100];
band_names = {'[1–40] Hz', '[40–100] Hz', '[1–100] Hz'};

%% ===== 选择文件（可多选）=====
[files, path] = uigetfile('*.csv', ...
    '选择一个或多个 CSV（前4行表头：time(s), voltage(V)）', ...
    'MultiSelect','on');
if isequal(files,0), error('已取消选择'); end
if ischar(files), files = {files}; end

numFiles = numel(files);
colors = lines(max(numFiles, 7));
markers = {'-','--',':','-.'};

%% ===== 时域叠加图 =====
figT = figure('Name','Time-Domain Acceleration (g)');
axT = axes(figT); hold(axT,'on'); grid(axT,'on');
xlabel(axT,'Time (s)'); ylabel(axT,'Acceleration (g)');
title(axT,'Time-Domain Acceleration (g)');
legNames = cell(1, numFiles);
maxDuration = 0;

% 为频域结果做准备
allRMS_acc = cell(numFiles,1); % 各频带加速度 RMS（g）
allRMS_disp = cell(numFiles,1); % 各频带位移 RMS（m）
fileLabels = cell(numFiles,1);

%% ===== 频域图（PSD/LPSD）=====
figPSD  = figure('Name','加速度 PSD');  ax1 = axes(figPSD);  hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log'); xlabel(ax1,'频率 (Hz)'); ylabel(ax1,'PSD [g^2/Hz]'); title(ax1,'加速度 PSD');

figLPSD = figure('Name','加速度 LPSD'); ax2 = axes(figLPSD); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log'); xlabel(ax2,'频率 (Hz)'); ylabel(ax2,'LPSD [g/\surdHz]'); title(ax2,'加速度 LPSD');

figDLPSD = figure('Name','位移 LPSD');  ax3 = axes(figDLPSD); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log'); xlabel(ax3,'频率 (Hz)'); ylabel(ax3,'LPSD [nm/\surdHz]'); title(ax3,'位移 LPSD');

%% ===== 主循环：逐文件处理 =====
for k = 1:numFiles
    infile = fullfile(path, files{k});
    [~, nameOnly] = fileparts(files{k});
    fileLabels{k} = nameOnly;

    % --- 读取数据（跳过前4行表头） ---
    opts = detectImportOptions(infile, 'NumHeaderLines', 4);
    M = readmatrix(infile, opts);
    if size(M,2) < 2
        warning('文件 %s 列数不足，跳过。', files{k});
        continue;
    end
    t_raw = M(:,1);                 % time (s)
    v_raw = M(:,2);                 % voltage (V, 含增益)

    % --- 清洗与排序 ---
    [t_raw, idx] = sort(t_raw(:));
    v_raw = v_raw(idx);

    % --- 电压 -> 加速度（g） ---
    acc_g = v_raw ./ (gain * sens_g_per_V);   % 单位 g

    % --- 可选去直流、时间对齐 ---
    if remove_dc
        acc_g = acc_g - mean(acc_g, 'omitnan');
    end
    if zero_time_start
        t = t_raw - t_raw(1);
    else
        t = t_raw;
    end

    % --- 时域：叠加绘图 ---
    styleID = mod(k-1, numel(markers)) + 1;
    plot(axT, t, acc_g, 'LineWidth', 1.2, ...
        'Color', colors(k,:), 'LineStyle', markers{styleID});
    legNames{k} = sprintf('%s (g)', nameOnly);

    if ~isempty(t)
        maxDuration = max(maxDuration, t(end) - t(1));
    end

    % ===== 频域：PSD/LPSD/RMS =====
    % 采样率估计
    dt = median(diff(t));           % 用 median 稳健估计
    fs = 1/dt;

    % —— 自适应 Welch 参数（稳健不报错）——
    N = numel(acc_g);
    % 目标单段长度：尽量长但不超过数据长度的1/4，且为2的幂
    seg_target = max(1024, floor(N/4));
    seglen = 2^floor(log2(seg_target));
    seglen = max(512, min(seglen, N));          % 下限512，且不超过N
    nfft = max(2^nextpow2(seglen), 1024);       % nfft 至少1024
    win = hamming(seglen);
    overlap = round(0.5*seglen);

    % Welch PSD（单位：g^2/Hz），先把时间域的 acc_g 转成 m/s^2 再算？
    % 注意：我们希望最终 PSD 用 g^2/Hz 表示。直接对 acc_g（单位 g）做 pwelch，
    % 得到的 pxx_g 的单位天生就是 g^2/Hz，避免单位来回换算的混乱。
    acc_g = acc_g(:);   % 列向量
    [pxx_g, f] = pwelch(acc_g, win, overlap, nfft, fs);   % pxx_g: g^2/Hz
    df = mean(diff(f));

    % 去掉 f=0（避免位移换算时除以0）
    valid = f > 0;
    f = f(valid);
    pxx_g = pxx_g(valid);

    % LPSD（加速度）：sqrt(PSD) → g/√Hz
    lpsd_acc_g = sqrt(pxx_g);                   % g/√Hz

    % 位移 LPSD：a(ω)= (2πf)^2 * x(ω) → x = a / (2πf)^2
    % 这里 LPSD_x = LPSD_a / (2πf)^2，单位从 g/√Hz 先转为 m/s^2/√Hz 再除以(2πf)^2
    lpsd_acc_ms2 = lpsd_acc_g * g0;             % m/s^2 / √Hz
    lpsd_disp_m  = lpsd_acc_ms2 ./ ((2*pi*f).^2); % m/√Hz
    lpsd_disp_nm = lpsd_disp_m * 1e9;           % nm/√Hz

    % —— 频带 RMS 计算（按 LPSD 积分）——
    % 加速度 RMS（g）： sqrt(∫ LPSD^2 df)
    % 位移 RMS（m）：   sqrt(∫ LPSD^2 df)
    RMS_acc_g  = zeros(size(band_edges,1),1);
    RMS_disp_m = zeros(size(band_edges,1),1);
    for ib = 1:size(band_edges,1)
        f1 = band_edges(ib,1); f2 = band_edges(ib,2);
        idx = (f >= f1) & (f <= f2);
        if nnz(idx) < 2
            RMS_acc_g(ib)  = NaN;
            RMS_disp_m(ib) = NaN;
        else
            RMS_acc_g(ib)  = sqrt(sum( (lpsd_acc_g(idx)).^2 ) * df);
            RMS_disp_m(ib) = sqrt(sum( (lpsd_disp_m(idx)).^2 ) * df);
        end
    end
    allRMS_acc{k}  = RMS_acc_g;
    allRMS_disp{k} = RMS_disp_m;

    % —— 频域绘图 —— 
    plot(ax1, f, pxx_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameOnly);                           % PSD g^2/Hz
    plot(ax2, f, lpsd_acc_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameOnly);                           % g/√Hz
    plot(ax3, f, lpsd_disp_nm, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameOnly);                           % nm/√Hz
end

% 时域图图例 & x 轴上限
legend(axT, legNames, 'Interpreter','none','Location','best');
if maxDuration > 0, xlim(axT, [0, maxDuration]); end

% 频域图图例
legend(ax1, 'show','Location','best');
legend(ax2, 'show','Location','best');
legend(ax3, 'show','Location','best');

%% ===== RMS 结果表（μg / nm）=====
rms_cell = cell(numFiles, 1+3+3); % 文件名 + 3个加速度 + 3个位移
for i = 1:numFiles
    rms_cell{i,1} = fileLabels{i};
    Ra = allRMS_acc{i};   % g
    Rd = allRMS_disp{i};  % m
    for ib = 1:3
        if ~isempty(Ra) && ~isnan(Ra(ib))
            rms_cell{i, 1+ib} = sprintf('%.2f μg', Ra(ib)*1e6);
        else
            rms_cell{i, 1+ib} = 'N/A';
        end
    end
    for ib = 1:3
        if ~isempty(Rd) && ~isnan(Rd(ib))
            rms_cell{i, 1+3+ib} = sprintf('%.2f nm', Rd(ib)*1e9);
        else
            rms_cell{i, 1+3+ib} = 'N/A';
        end
    end
end

figTbl = figure('Name','RMS 对比表','Units','pixels','Color','w');
col_names = {'文件名', ...
    '「1–40Hz」加速度', '「40–100Hz」加速度', '「1–100Hz」加速度', ...
    '「1–40Hz」位移',   '「40–100Hz」位移',   '「1–100Hz」位移'};
uitable('Parent', figTbl, 'Data', rms_cell, 'ColumnName', col_names, ...
    'Units','normalized', 'Position',[0.05 0.05 0.9 0.9], ...
    'FontSize',10, 'RowName', []);
set(figTbl, 'Position', [100, 100, 900, min(500, 100 + 28*numFiles)]);

%% ===== 命令行汇总输出 =====
fprintf('\n===== RMS 汇总（单位：μg / nm）=====\n');
for i = 1:numFiles
    fprintf('%s\n', fileLabels{i});
    fprintf('%-12s | %-16s | %-16s\n','频段','加速度 RMS','位移 RMS');
    fprintf('-----------------------------------------------\n');
    Ra = allRMS_acc{i};  Rd = allRMS_disp{i};
    for ib = 1:size(band_edges,1)
        if ~isempty(Ra) && ~isnan(Ra(ib)),  acc_str = sprintf('%.2f μg', Ra(ib)*1e6);
        else,                               acc_str = 'N/A'; end
        if ~isempty(Rd) && ~isnan(Rd(ib)),  dsp_str = sprintf('%.2f nm', Rd(ib)*1e9);
        else,                               dsp_str = 'N/A'; end
        fprintf('%-12s | %-16s | %-16s\n', band_names{ib}, acc_str, dsp_str);
    end
    fprintf('===============================================\n');
end
