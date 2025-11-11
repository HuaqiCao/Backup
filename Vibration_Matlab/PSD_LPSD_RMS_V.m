function PSD_LPSD_RMS_V()
% pcb(V) => PSD & LPSD & RMS  [aligned to v1 + console table + robust Excel]
% - Read CSV (skip 4 header rows): col1=t(s), col2=V
% - Do PSD in SI ((m/s^2)^2/Hz); convert to µg/nm only for outputs
% - Welch: seglen=fs*10, Hamming(periodic), 50% overlap, nfft=seglen
% - Bands: [1,40)  (40,1000]  [1,1000]
% - Write Excel safely; fallback to timestamp name, then CSV
% - NEW: print RMS table to command window + show saved path

%% === Settings (aligned) ===
time_limit_sec = Inf;
auto_xlim      = true;
xmin_Hz        = 0;
fmin_valid     = 1.0;

%% === File selection ===
[fileNames, filePath] = uigetfile('*.csv', 'Select voltage-signal CSV files(V)', 'MultiSelect', 'on');
if isequal(fileNames, 0), error('❌ User canceled.'); end
if ischar(fileNames), fileNames = {fileNames}; end
numFiles = numel(fileNames);

%% === Sensor params ===
sens_V_per_g = 1.026;    % V/g
gain         = 100.0;    % amplifier gain
g0           = 9.80665;  % m/s^2

%% === Plot style ===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN,'defaultTextFontName',fontEN,...
    'defaultLegendFontName',fontEN,'defaultUIControlFontName',fontEN,...
    'defaultAxesFontSize',12,'defaultTextInterpreter','none',...
    'defaultLegendInterpreter','none');
figSize = [1, 1, 10, 5];   % inches

%% === Figures ===
fig1 = figure('Name','Acceleration PSD (SI)','Units','inches','Position',figSize,'Color','w');
ax1  = axes(fig1); hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log','FontSize',12);
xlabel(ax1,'Frequency (Hz)','FontSize',16);
ylabel(ax1,'PSD [ (m/s^2)^2 / Hz ]','FontSize',16);

fig2 = figure('Name','Acceleration LPSD','Units','inches','Position',figSize,'Color','w');
ax2  = axes(fig2); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log','FontSize',12);
xlabel(ax2,'Frequency (Hz)','FontSize',16);
ylabel(ax2,'LPSD [ g/√Hz ]','FontSize',16);

fig3 = figure('Name','Displacement LPSD','Units','inches','Position',figSize,'Color','w');
ax3  = axes(fig3); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log','FontSize',12);
xlabel(ax3,'Frequency (Hz)','FontSize',16);
ylabel(ax3,'LPSD [ nm/√Hz ]','FontSize',16);

colors  = lines(numFiles);
markers = {'-','--',':','-.'};

%% === Bands (half-open/half-closed) ===
bands = [1 40; 40 1000; 1 1000];   % Hz
band_labels = {'[1–40) Hz','(40–1000] Hz','[1–1000] Hz'};

allRMS  = cell(numFiles,1);   % [3 x 2]: [Acc_SI(m/s^2), Disp_m]
fileLbl = cell(numFiles,1);
df_print = NaN;

%% === Auto x-limit vars ===
fmax_global = 0;
fmin_pos_global = Inf;

%% === Main loop ===
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly, ~] = fileparts(fileNames{iFile});
    fileLbl{iFile} = nameOnly;

    % read CSV (skip 4 headers)
    data = readmatrix(fullFileName, 'NumHeaderLines', 4);
    time = data(:,1);
    volt = data(:,2);

    % optional time limit
    if isfinite(time_limit_sec)
        t0 = time(1);
        time = time - t0;
        keep = time <= time_limit_sec;
        if any(keep)
            time = time(keep);
            volt = volt(keep);
        end
    end

    % V -> g -> m/s^2; remove DC after converting
    a_g   = volt./(gain * sens_V_per_g);
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

    % PSD of acceleration in SI: (m/s^2)^2/Hz
    [Sa_SI, f] = pwelch(a_ms2, window, overlap, nfft, fs, 'psd');
    if numel(f)>1, df = mean(diff(f)); else, df = NaN; end
    if isnan(df_print), df_print = df; end

    % low-frequency cutoff
    pos = f >= fmin_valid;

    % for auto x-limits
    if any(pos)
        fmin_pos_global = min(fmin_pos_global, min(f(pos)));
        fmax_global     = max(fmax_global, max(f(pos)));
    end

    % displacement PSD from acceleration PSD
    w = 2*pi*f;
    Sd_m2 = zeros(size(Sa_SI));                  % m^2/Hz
    Sd_m2(pos) = Sa_SI(pos) ./ (w(pos).^4);

    % LPSD for plots
    lpsd_acc_g  = zeros(size(Sa_SI));   lpsd_acc_g(pos)  = sqrt(Sa_SI(pos)) / g0;
    lpsd_disp_nm= zeros(size(Sd_m2));   lpsd_disp_nm(pos)= sqrt(Sd_m2(pos)) * 1e9;

    % Band-wise RMS via trapz on SI PSDs
    RMS_result = zeros(size(bands,1), 2); % [Acc_SI, Disp_m]
    for ib = 1:size(bands,1)
        if ib == 1
            idx = (f >= bands(ib,1)) & (f <  bands(ib,2));   % [1,40)
        elseif ib == size(bands,1)
            idx = (f >= bands(ib,1)) & (f <= bands(ib,2));   % [1,1000]
        else
            idx = (f >  bands(ib,1)) & (f <= bands(ib,2));   % (40,1000]
        end
        idx = idx & pos;

        RMS_acc_SI  = sqrt(trapz(f(idx), Sa_SI(idx))); % m/s^2
        RMS_disp_m  = sqrt(trapz(f(idx), Sd_m2(idx))); % m

        RMS_result(ib,1) = RMS_acc_SI;
        RMS_result(ib,2) = RMS_disp_m;
    end
    allRMS{iFile} = RMS_result;

    % plots
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f(pos), Sa_SI(pos),        'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax2, f(pos), lpsd_acc_g(pos),   'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth',1.5,'DisplayName',nameOnly);
    plot(ax3, f(pos), lpsd_disp_nm(pos), 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth',1.5,'DisplayName',nameOnly);

    fprintf('\n[%s]\n', nameOnly);
    fprintf('fs=%.3f Hz, N=%d, Δf=%.3f Hz, Welch windows=%d\n', fs, N, df, N_win);
end

%% === Legend & titles ===
legend(ax1,'show','Location','best','FontSize',16);
legend(ax2,'show','Location','best','FontSize',16);
legend(ax3,'show','Location','best','FontSize',16);
ttl_df = '';
if ~isnan(df_print), ttl_df = sprintf(' (Δf=%.1f Hz)', df_print); end
title(ax1,['Power Spectral Density (SI)' ttl_df],'FontSize',24);
title(ax2,['Acceleration LPSD' ttl_df],'FontSize',24);
title(ax3,['Displacement LPSD' ttl_df],'FontSize',24);

%% === Auto x-limits ===
if auto_xlim
    if ~(isfinite(fmax_global) && fmax_global > 0), fmax_global = 1; end
    if ~(isfinite(xmin_Hz) && xmin_Hz > 0)
        xmin_Hz = max(0.1, min(fmin_pos_global, 1));
    end
    xlim(ax1, [xmin_Hz, fmax_global]);
    xlim(ax2, [xmin_Hz, fmax_global]);
    xlim(ax3, [xmin_Hz, fmax_global]);
end

%% === Assemble tables ===
% Wide table for Excel
rms_wide = cell(numFiles,7);
for iFile = 1:numFiles
    R = allRMS{iFile}; % [3 x 2] (Acc_SI, Disp_m)
    rms_wide{iFile,1} = fileLbl{iFile};
    % Acc µg
    rms_wide{iFile,2} = sprintf('%.2f', (R(1,1)/g0)*1e6);   % 1–40
    rms_wide{iFile,3} = sprintf('%.2f', (R(2,1)/g0)*1e6);   % 40–1000
    rms_wide{iFile,4} = sprintf('%.2f', (R(3,1)/g0)*1e6);   % 1–1000
    % Disp nm
    rms_wide{iFile,5} = sprintf('%.2f', R(1,2)*1e9);
    rms_wide{iFile,6} = sprintf('%.2f', R(2,2)*1e9);
    rms_wide{iFile,7} = sprintf('%.2f', R(3,2)*1e9);
end
col_names = {'File', ...
    'Acc RMS (µg) 1–40', 'Acc RMS (µg) 40–1000', 'Acc RMS (µg) 1–1000', ...
    'Disp RMS (nm) 1–40','Disp RMS (nm) 40–1000','Disp RMS (nm) 1–1000'};

% Long table for Excel and console print
longHeader = {'File','Band','Acc RMS (µg)','Disp RMS (nm)'};
longRows   = {};
for iFile = 1:numFiles
    R = allRMS{iFile};
    for ib = 1:size(bands,1)
        longRows(end+1,:) = {fileLbl{iFile}, band_labels{ib}, ...
            round((R(ib,1)/g0)*1e6, 2), round(R(ib,2)*1e9, 2)};
    end
end

%% === Print RMS table to console ===
print_rms_console(longHeader, longRows);

%% === Export (robust) ===
[~, firstStem, ~] = fileparts(fileNames{1});
nameStem = regexprep(firstStem,'[^\w\-.]','_');
xlsxPath = fullfile(filePath, sprintf('%s_RMS_summary.xlsx', nameStem));
finalSaved = safe_write_xlsx(xlsxPath, col_names, rms_wide, longHeader, longRows);

% also echo where the Excel/CSV lives
fprintf('\nSaved summary to: %s\n', finalSaved);

end  % ======= end of main =======


%% ===== Console pretty-printer =====
function print_rms_console(headerCell, rowsCell)
% Minimal pretty print for command window
% headerCell: 1x4, rowsCell: Nx4
    % column widths
    w1 = 26; w2 = 16; w3 = 16; w4 = 16;
    line = @(ch,n) repmat(ch,1,n);

    fprintf('\n=== RMS Summary (console) ===\n');
    fprintf('%s\n', line('-', w1+w2+w3+w4+5));
    fprintf(['%-' num2str(w1) 's | %-' num2str(w2) 's | %-' num2str(w3) 's | %-' num2str(w4) 's\n'], ...
        headerCell{1}, headerCell{2}, headerCell{3}, headerCell{4});
    fprintf('%s\n', line('-', w1+w2+w3+w4+5));

    for i=1:size(rowsCell,1)
        fprintf(['%-' num2str(w1) 's | %-' num2str(w2) 's | %' num2str(w3-3) '.2f µg | %' num2str(w4-4) '.2f nm\n'], ...
            rowsCell{i,1}, rowsCell{i,2}, rowsCell{i,3}, rowsCell{i,4});
    end
    fprintf('%s\n\n', line('-', w1+w2+w3+w4+5));
end


%% ===== Robust Excel writer (silent, returns final path) =====
function finalPath = safe_write_xlsx(xlsxPath, col_names, rms_wide, longHeader, longRows)
    % Ensure dir exists
    outDir = fileparts(xlsxPath);
    if ~isempty(outDir) && ~isfolder(outDir)
        mkdir(outDir);
    end

    % Try original path (no delete/overwrite)
    [okA, ~] = try_write_once(xlsxPath, col_names, rms_wide, longHeader, longRows);
    if okA
        finalPath = xlsxPath;
        return;
    end

    % Timestamp fallback
    [p,n,~] = fileparts(xlsxPath);
    xlsxPath2 = fullfile(p, sprintf('%s_%s.xlsx', n, datestr(now,'yyyymmdd_HHMMSS_FFF')));
    [okB, ~] = try_write_once(xlsxPath2, col_names, rms_wide, longHeader, longRows);
    if okB
        finalPath = xlsxPath2;
        return;
    end

    % CSV fallback (two files for two sheets)
    csv1 = fullfile(p, sprintf('%s_RMS_Wide.csv', n));
    csv2 = fullfile(p, sprintf('%s_RMS_Long.csv', n));
    T1 = cell2table([col_names; rms_wide]);
    writetable(T1, csv1, 'WriteVariableNames', false);
    T2 = cell2table([longHeader; longRows]);
    writetable(T2, csv2, 'WriteVariableNames', false);
    finalPath = sprintf('%s & %s', csv1, csv2);
end

function [ok, errMsg] = try_write_once(xlsxPath, col_names, rms_wide, longHeader, longRows)
% Single attempt to write Excel (no delete, no overwrite).
    ok = false; errMsg = "";
    try
        writecell([col_names; rms_wide], xlsxPath, 'Sheet', 'RMS_Wide');
        writecell([longHeader; longRows], xlsxPath, 'Sheet', 'RMS_Long');
        ok = true;
    catch ME
        errMsg = ME.message; 
        ok = false;
    end
end
