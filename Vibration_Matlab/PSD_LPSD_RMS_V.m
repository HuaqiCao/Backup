function PSD_LPSD_RMS_V()
% pcb(V) => PSD & LPSD & RMS  [aligned to v1 + console table + robust Excel]
% - Read CSV (skip 4 header rows): col1=t(s), col2=V
% - Do PSD in SI ((m/s^2)^2/Hz); convert to µg/nm only for outputs
% - Welch: seglen=fs*10, Hamming(periodic), 50% overlap, nfft=seglen
% - Bands: [1,40)  (40,1000]  [1,1000]
% - Write Excel safely; fallback to timestamp name, then CSV
% - NEW: print RMS table to command window + show saved path
% ------------------------------------------------------------
% 1) 读取多个 CSV（前4行为表头，含 time/voltage）
% 2) 电压 → 加速度 (g) → 加速度 (m/s^2) → 去均值
% 3) 使用 Welch 方法计算 PSD（单位 (m/s^2)^2/Hz）
% 4) 计算：
%       - 加速度 LPSD (g/√Hz)
%       - 位移 LPSD (nm/√Hz)
% 5) 计算 RMS（加速度 μg、位移 nm），按频段：
%       [1–40), (40–1000], [1–1000]
% 6) 绘制三张图：
%       - PSD（SI）
%       - Acc LPSD
%       - Disp LPSD
% 7) RMS 输出到命令行和 Excel（带宽表 + 长表）
% ============================================================

%% === Settings 设置 ===
time_limit_sec = Inf;   % 分析时间限制
auto_xlim      = true;  % 自动频率轴
xmin_Hz        = 0;      % 最小频率
fmin_valid     = 1.0;    % 有效频率下限（避免 1/f^2 爆炸）

%% === File selection 选择文件 ===
[fileNames, filePath] = uigetfile('*.csv', 'Select voltage-signal CSV files(V)', 'MultiSelect', 'on');
if isequal(fileNames, 0), error('❌ User canceled.'); end
if ischar(fileNames), fileNames = {fileNames}; end
numFiles = numel(fileNames);

%% === Sensor params 传感器参数 ===
sens_V_per_g = 1.000;    % 灵敏度 V/g
gain         = 100.0;    % 放大倍数
g0           = 9.80665;  % m/s^2

%% === Plot style 图形默认样式 ===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN,'defaultTextFontName',fontEN,...
    'defaultLegendFontName',fontEN,'defaultUIControlFontName',fontEN,...
    'defaultAxesFontSize',12,'defaultTextInterpreter','none',...
    'defaultLegendInterpreter','none');
figSize = [1, 1, 10, 5];   % 图窗大小（英寸）

%% === Prepare figures 创建三个图窗 ===
% PSD (SI)
fig1 = figure('Name','Acceleration PSD (SI)','Units','inches','Position',figSize,'Color','w');
ax1  = axes(fig1); hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log');
xlabel(ax1,'Frequency (Hz)'); ylabel(ax1,'PSD [ (m/s^2)^2 / Hz ]');

% Acc LPSD
fig2 = figure('Name','Acceleration LPSD','Units','inches','Position',figSize,'Color','w');
ax2  = axes(fig2); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log');
xlabel(ax2,'Frequency (Hz)'); ylabel(ax2,'LPSD [ g/√Hz ]');

% Disp LPSD
fig3 = figure('Name','Displacement LPSD','Units','inches','Position',figSize,'Color','w');
ax3  = axes(fig3); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log');
xlabel(ax3,'Frequency (Hz)'); ylabel(ax3,'LPSD [ nm/√Hz ]');

colors  = lines(numFiles);
markers = {'-','--',':','-.'};

%% === Bands 分频段（用于 RMS） ===
bands = [0 40; 40 1000; 1 1000];
band_labels = {'[1–40) Hz','(40–1000] Hz','[1–1000] Hz'};

allRMS  = cell(numFiles,1);  % 每个文件一个 RMS 结果（3×2矩阵）
fileLbl = cell(numFiles,1);

fmax_global = 0;
fmin_pos_global = Inf;
df_print = NaN;

%% ============================================================
%                   Main Loop 主循环
% ============================================================
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly, ~] = fileparts(fileNames{iFile});
    fileLbl{iFile} = nameOnly;

    % === 读 CSV（跳过4行）===
    data = readmatrix(fullFileName, 'NumHeaderLines', 4);
    time = data(:,1);
    volt = data(:,2);

    % === 限定时间域 ===
    if isfinite(time_limit_sec)
        t0 = time(1);
        time = time - t0;
        keep = (time <= time_limit_sec);
        if any(keep)
            time = time(keep);
            volt = volt(keep);
        end
    end

    % === 电压 → g → m/s^2，并去直流 ===
    a_g   = volt./(gain * sens_V_per_g);
    a_ms2 = a_g * g0;
    a_ms2 = a_ms2 - mean(a_ms2);

    % === 采样率 ===
    dt = median(diff(time));
    fs = 1/dt;
    N  = numel(a_ms2);

    % === Welch 参数 ===
    seglen  = min(round(fs*10), N);
    window  = hamming(seglen,'periodic');
    overlap = round(seglen/2);
    nfft    = seglen;
    N_win   = max(1, floor((N - overlap) / max(1,(seglen - overlap))));

    % === PSD (SI) ===
    [Sa_SI, f] = pwelch(a_ms2, window, overlap, nfft, fs, 'psd');
    if numel(f)>1, df = mean(diff(f)); else, df = NaN; end
    if isnan(df_print), df_print = df; end

    % === 低频有效区间 ===
    pos = f >= fmin_valid;

    % === 用于自动频率轴 ===
    if any(pos)
        fmin_pos_global = min(fmin_pos_global, min(f(pos)));
        fmax_global     = max(fmax_global, max(f(pos)));
    end

    % === 位移 PSD（从加速度 PSD 推出）===
    w = 2*pi*f;
    Sd_m2 = zeros(size(Sa_SI));
    Sd_m2(pos) = Sa_SI(pos) ./ (w(pos).^4);

    % === LPSD ===
    lpsd_acc_g   = zeros(size(Sa_SI)); lpsd_acc_g(pos)   = sqrt(Sa_SI(pos)) / g0;
    lpsd_disp_nm = zeros(size(Sd_m2)); lpsd_disp_nm(pos) = sqrt(Sd_m2(pos)) * 1e9;

    % === 各频段 RMS ===
    RMS_result = zeros(size(bands,1), 2); % [加速度 SI, 位移 m]
    for ib = 1:size(bands,1)
        if ib == 1
            idx = (f >= bands(ib,1)) & (f <  bands(ib,2));
        elseif ib == size(bands,1)
            idx = (f >= bands(ib,1)) & (f <= bands(ib,2));
        else
            idx = (f >  bands(ib,1)) & (f <= bands(ib,2));
        end
        idx = idx & pos;

        RMS_acc_SI = sqrt(trapz(f(idx), Sa_SI(idx)));
        RMS_disp_m = sqrt(trapz(f(idx), Sd_m2(idx)));

        RMS_result(ib,1) = RMS_acc_SI;
        RMS_result(ib,2) = RMS_disp_m;
    end
    allRMS{iFile} = RMS_result;

    % === 三张图上画线 ===
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f(pos), Sa_SI(pos),        'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax2, f(pos), lpsd_acc_g(pos),   'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax3, f(pos), lpsd_disp_nm(pos), 'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);

    % === 输出基本信息 ===
    fprintf('\n[%s]\n', nameOnly);
    fprintf('fs=%.3f Hz, N=%d, Δf=%.3f Hz, Welch_windows=%d\n', fs, N, df, N_win);
end

%% === 图例 & 标题 ===
legend(ax1,'show','Location','best','FontSize',16);
legend(ax2,'show','Location','best','FontSize',16);
legend(ax3,'show','Location','best','FontSize',16);
ttl_df = '';
if ~isnan(df_print), ttl_df = sprintf(' (Δf=%.1f Hz)', df_print); end
title(ax1,['Power Spectral Density (SI)' ttl_df],'FontSize',24);
title(ax2,['Acceleration LPSD' ttl_df],'FontSize',24);
title(ax3,['Displacement LPSD' ttl_df],'FontSize',24);

%% === 自动设频率范围 ===
if auto_xlim
    if ~(isfinite(fmax_global)&&fmax_global>0), fmax_global=1; end
    if ~(isfinite(xmin_Hz)&&xmin_Hz>0)
        xmin_Hz = max(0.1, min(fmin_pos_global,1));
    end
    xlim(ax1,[xmin_Hz, fmax_global]);
    xlim(ax2,[xmin_Hz, fmax_global]);
    xlim(ax3,[xmin_Hz, fmax_global]);
end

%% === 汇总 RMS 表（宽 + 长）===
rms_wide = cell(numFiles,7);
for iFile = 1:numFiles
    R = allRMS{iFile}; % (3×2)
    rms_wide{iFile,1} = fileLbl{iFile};
    rms_wide{iFile,2} = sprintf('%.2f', (R(1,1)/g0)*1e6);
    rms_wide{iFile,3} = sprintf('%.2f', (R(2,1)/g0)*1e6);
    rms_wide{iFile,4} = sprintf('%.2f', (R(3,1)/g0)*1e6);
    rms_wide{iFile,5} = sprintf('%.2f', R(1,2)*1e9);
    rms_wide{iFile,6} = sprintf('%.2f', R(2,2)*1e9);
    rms_wide{iFile,7} = sprintf('%.2f', R(3,2)*1e9);
end

col_names = {'File','Acc RMS (µg) 1–40','Acc RMS (µg) 40–1000','Acc RMS (µg) 1–1000',...
    'Disp RMS (nm) 1–40','Disp RMS (nm) 40–1000','Disp RMS (nm) 1–1000'};

longHeader = {'File','Band','Acc RMS (µg)','Disp RMS (nm)'};
longRows = {};
for iFile = 1:numFiles
    R = allRMS{iFile};
    for ib = 1:3
        longRows(end+1,:) = {fileLbl{iFile}, band_labels{ib}, ...
            round((R(ib,1)/g0)*1e6,2), round(R(ib,2)*1e9,2)};
    end
end

%% === 打印 RMS 结果到控制台 ===
print_rms_console(longHeader, longRows);

%% === 保存到 Excel（强壮写入机制）===
[~, firstStem, ~] = fileparts(fileNames{1});
nameStem = regexprep(firstStem,'[^\w\-.]','_');
xlsxPath = fullfile(filePath, sprintf('%s_RMS_summary.xlsx', nameStem));
finalSaved = safe_write_xlsx(xlsxPath, col_names, rms_wide, longHeader, longRows);
fprintf('\nSaved summary to: %s\n', finalSaved);

end % ============ end main ============


%% ------------------------------------------
% 控制台打印
%% ------------------------------------------
function print_rms_console(headerCell, rowsCell)
% 本函数负责把 RMS 表以表格形式在命令行显示
    w1=26; w2=16; w3=16; w4=16;
    line=@(ch,n) repmat(ch,1,n);

    fprintf('\n=== RMS Summary (console) ===\n');
    fprintf('%s\n', line('-', w1+w2+w3+w4+5));
    fprintf(['%-' num2str(w1) 's | %-' num2str(w2) 's | %-' num2str(w3) 's | %-' num2str(w4) 's\n'], ...
        headerCell{1}, headerCell{2}, headerCell{3}, headerCell{4});
    fprintf('%s\n', line('-', w1+w2+w3+w4+5));

    for i=1:size(rowsCell,1)
        fprintf(['%-' num2str(w1) 's | %-' num2str(w2) 's | %' num2str(w3-3) '.2f µg | %' num2str(w4-4) '.2f nm\n'],...
            rowsCell{i,1},rowsCell{i,2},rowsCell{i,3},rowsCell{i,4});
    end
    fprintf('%s\n\n', line('-', w1+w2+w3+w4+5));
end

%% ------------------------------------------
% Excel 写入（robust）
%% ------------------------------------------
function finalPath = safe_write_xlsx(xlsxPath, col_names, rms_wide, longHeader, longRows)
    outDir = fileparts(xlsxPath);
    if ~isempty(outDir) && ~isfolder(outDir)
        mkdir(outDir);
    end

    [okA, ~] = try_write_once(xlsxPath, col_names, rms_wide, longHeader, longRows);
    if okA, finalPath = xlsxPath; return; end

    [p,n,~] = fileparts(xlsxPath);
    xlsxPath2 = fullfile(p, sprintf('%s_%s.xlsx', n, datestr(now,'yyyymmdd_HHMMSS_FFF')));
    [okB, ~] = try_write_once(xlsxPath2, col_names, rms_wide, longHeader, longRows);
    if okB, finalPath = xlsxPath2; return; end

    csv1 = fullfile(p, sprintf('%s_RMS_Wide.csv', n));
    csv2 = fullfile(p, sprintf('%s_RMS_Long.csv', n));
    T1 = cell2table([col_names; rms_wide]);  writetable(T1, csv1,'WriteVariableNames',false);
    T2 = cell2table([longHeader; longRows]); writetable(T2, csv2,'WriteVariableNames',false);
    finalPath = sprintf('%s & %s', csv1, csv2);
end

function [ok, errMsg] = try_write_once(xlsxPath, col_names, rms_wide, longHeader, longRows)
% 单次尝试写入 Excel，不覆盖现有文件
    ok=false; errMsg="";
    try
        writecell([col_names; rms_wide], xlsxPath,'Sheet','RMS_Wide');
        writecell([longHeader; longRows],xlsxPath,'Sheet','RMS_Long');
        ok=true;
    catch ME
        errMsg = ME.message; ok=false;
    end
end
