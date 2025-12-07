function PSD_LPSD_RMS_V()
% pcb(V) => PSD & LPSD & RMS  [aligned to v1 + console table + robust Excel]
% - Read CSV (skip 4 header rows): col1=t(s), col2=V
% - Do PSD in SI ((m/s^2)^2/Hz); convert to µg/nm only for outputs
% - Welch: seglen=fs*10, Hamming(periodic), 50% overlap, nfft=seglen
% - Bands: [1,40)  (40,1000]  [1,1000]
% - Write Excel safely; fallback to timestamp name, then CSV
% - NEW: print RMS table to command window + show saved path
% - NEW: 每个输入文件都可使用不同灵敏度(V/g)
% ============================================================

%% === Settings 设置 ===
time_limit_sec = Inf;     % 分析时间限制
auto_xlim      = true;    % 自动频率轴
xmin_Hz        = 0;       
fmin_valid     = 1.0;     % 有效频率下限

%% === File selection 选择文件 ===
[fileNames, filePath] = uigetfile('*.csv', 'Select voltage-signal CSV files(V)', 'MultiSelect', 'on');
if isequal(fileNames, 0), error('❌ User canceled.'); end
if ischar(fileNames), fileNames = {fileNames}; end
numFiles = numel(fileNames);

%% === Sensor params — gain 固定，但灵敏度每个文件不一样 ===
gain = 100.0; 
g0   = 9.80665;  % m/s^2

%%% ============================================================
%%% === NEW: 输入每个 CSV 的灵敏度 (V/g) ======================
%%% ============================================================
sens_each = zeros(numFiles,1);
for iFile = 1:numFiles
    prompt = sprintf('Input sensitivity (V/g) for file:\n%s', fileNames{iFile});
    answer = inputdlg(prompt, 'Sensitivity Input', 1, {"1.000"});
    if isempty(answer)
        error('User canceled sensitivity input.');
    end
    sens_each(iFile) = str2double(answer{1});
    if isnan(sens_each(iFile)) || sens_each(iFile)<=0
        error('Invalid sensitivity value.');
    end
end
%%% ============================================================

%% === Plot style 图形默认样式 ===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN,'defaultTextFontName',fontEN,'defaultLegendFontName',fontEN,...
    'defaultAxesFontSize',12,'defaultTextInterpreter','none','defaultLegendInterpreter','none');

figSize = [1, 1, 10, 5];

%% === Prepare figures ===
% PSD (SI)
fig1 = figure('Name','Acceleration PSD (SI)','Units','inches','Position',figSize,'Color','w');
ax1  = axes(fig1); hold(ax1,'on'); grid(ax1,'on'); set(ax1,'XScale','log','YScale','log');
xlabel(ax1,'Frequency (Hz)'); ylabel(ax1,'PSD [ (m/s^2)^2 / Hz ]');

% Acc LPSD
fig2 = figure('Name','Acceleration LPSD','Units','inches','Position',figSize,'Color','w');
ax2  = axes(fig2); hold(ax2,'on'); grid(ax2,'on'); set(ax2,'XScale','log','YScale','log');
xlabel(ax2,'Frequency (Hz)'); ylabel(ax2,'LPSD [ g/√Hz ]');

% Disp LPSD
fig3 = figure('Name','Displacement LPSD','Units','inches','Position',figSize,'Color','w');
ax3  = axes(fig3); hold(ax3,'on'); grid(ax3,'on'); set(ax3,'XScale','log','YScale','log');
xlabel(ax3,'Frequency (Hz)'); ylabel(ax3,'LPSD [ nm/√Hz ]');

colors  = lines(numFiles);
markers = {'-','--',':','-.'};

%% === Bands for RMS ===
bands = [0 40; 40 1000; 1 1000];
band_labels = {'[1–40) Hz','(40–1000] Hz','[1–1000] Hz'};

allRMS  = cell(numFiles,1);
fileLbl = cell(numFiles,1);

fmax_global = 0;
fmin_pos_global = Inf;
df_print = NaN;

%% ============================================================
%                   Main Loop 主循环
%% ============================================================
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly, ~] = fileparts(fileNames{iFile});
    fileLbl{iFile} = nameOnly;

    % read CSV
    data = readmatrix(fullFileName, 'NumHeaderLines', 4);
    time = data(:,1);
    volt = data(:,2);

    % 限定时间
    if isfinite(time_limit_sec)
        t0 = time(1);
        time = time - t0;
        keep = (time <= time_limit_sec);
        if any(keep)
            time = time(keep);
            volt = volt(keep);
        end
    end

    % === Voltage -> g -> m/s^2，去均值 ===
    %%%% =====================================================
    %%%% === NEW: 使用每个文件独立灵敏度 sens_each(iFile) ===
    %%%% =====================================================
    a_g   = volt ./ (gain * sens_each(iFile));
    a_ms2 = a_g * g0;
    a_ms2 = a_ms2 - mean(a_ms2);

    % sampling
    dt = median(diff(time));
    fs = 1/dt;
    N  = numel(a_ms2);

    % Welch
    seglen  = min(round(fs*10), N);
    window  = hamming(seglen,'periodic');
    overlap = round(seglen/2);
    nfft    = seglen;
    N_win   = max(1, floor((N - overlap) / max(1,(seglen - overlap))));

    [Sa_SI, f] = pwelch(a_ms2, window, overlap, nfft, fs, 'psd');
    if numel(f)>1, df = mean(diff(f)); else df = NaN; end
    if isnan(df_print), df_print=df; end

    pos = (f >= fmin_valid);

    if any(pos)
        fmin_pos_global = min(fmin_pos_global, min(f(pos)));
        fmax_global     = max(fmax_global, max(f(pos)));
    end

    % Displacement PSD
    w = 2*pi*f;
    Sd_m2 = zeros(size(Sa_SI));
    Sd_m2(pos) = Sa_SI(pos) ./ (w(pos).^4);

    % LPSD
    lpsd_acc_g   = zeros(size(Sa_SI)); lpsd_acc_g(pos)   = sqrt(Sa_SI(pos)) / g0;
    lpsd_disp_nm = zeros(size(Sd_m2)); lpsd_disp_nm(pos) = sqrt(Sd_m2(pos)) * 1e9;

    % RMS in bands
    RMS_result = zeros(size(bands,1), 2);
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

    % Plot
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f(pos), Sa_SI(pos),        'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax2, f(pos), lpsd_acc_g(pos),   'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax3, f(pos), lpsd_disp_nm(pos), 'Color',colors(iFile,:),'LineStyle',markers{styleID},'LineWidth',1.5,'DisplayName',nameOnly);

    fprintf('\n[%s]\n', nameOnly);
    fprintf('fs=%.3f Hz, N=%d, Δf=%.3f Hz, Welch_windows=%d\n', fs, N, df, N_win);
end

%% === Legend & title ===
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

%% === 汇总 RMS 表 ===
rms_wide = cell(numFiles,7);
for iFile = 1:numFiles
    R = allRMS{iFile};
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

print_rms_console(longHeader, longRows);

%% === 保存 Excel ===
[~, firstStem, ~] = fileparts(fileNames{1});
nameStem = regexprep(firstStem,'[^\w\-.]','_');
xlsxPath = fullfile(filePath, sprintf('%s_RMS_summary.xlsx', nameStem));
finalSaved = safe_write_xlsx(xlsxPath, col_names, rms_wide, longHeader, longRows);

fprintf('\nSaved summary to: %s\n', finalSaved);
end % end main


%% -------------------------------------------------------
function print_rms_console(headerCell, rowsCell)
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

%% -------------------------------------------------------
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
    ok=false; errMsg="";
    try
        writecell([col_names; rms_wide], xlsxPath,'Sheet','RMS_Wide');
        writecell([longHeader; longRows],xlsxPath,'Sheet','RMS_Long');
        ok=true;
    catch ME
        errMsg = ME.message; ok=false;
    end
end
