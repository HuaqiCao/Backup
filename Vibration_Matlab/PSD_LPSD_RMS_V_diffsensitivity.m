% pcb(V) => PSD & LPSD(g & d) & RMS(Hz)
function PSD_LPSD_RMS_no()

%% === Quick settings ===
time_limit_sec = 510;   % limit CSV time length (s); set Inf = no limit
auto_xlim      = true;  % auto set x-axis max freq
xmin_Hz        = 0;     % x-axis min (log-scale >0)

%% === File selection ===
[fileNames, filePath] = uigetfile('*.csv', 'Select voltage-signal CSV files(V)', 'MultiSelect', 'on');
if isequal(fileNames, 0)
    error('❌ User canceled.');
end
if ischar(fileNames)
    fileNames = {fileNames};
end
numFiles = numel(fileNames);

%% === Sensor params ===
gain        = 100.0;    % gain
g           = 9.81;     % m/s^2

%% Initialize an array to store the sensitivity values for each file
sensitivity = zeros(1, numFiles);  

%% === Prompt for Sensitivity for each file ===
for iFile = 1:numFiles
    fileName = fileNames{iFile};
    sensitivity(iFile) = input(['Enter sensitivity (V/g) for file: ', fileName, ': ']);  
end

%% === Plot style ===
fontEN = 'Arial';
set(0,'defaultAxesFontName',fontEN,'defaultTextFontName',fontEN,...
    'defaultLegendFontName',fontEN,'defaultUIControlFontName',fontEN,...
    'defaultAxesFontSize',12,'defaultTextInterpreter','none',...
    'defaultLegendInterpreter','none');

figSize = [1, 1, 10, 5];   % inches

%% === Figures ===
fig1 = figure('Name','Acceleration PSD','Units','inches','Position',figSize,'Color','w');
ax1 = axes(fig1); hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log','FontSize',12);
xlabel(ax1,'Frequency (Hz)','FontSize',16);
ylabel(ax1,'PSD [g^2/Hz]','FontSize',16);

fig2 = figure('Name','Acceleration LPSD','Units','inches','Position',figSize,'Color','w');
ax2 = axes(fig2); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log','FontSize',12);
xlabel(ax2,'Frequency (Hz)','FontSize',16);
ylabel(ax2,'LPSD [g/√Hz]','FontSize',16);

fig3 = figure('Name','Displacement LPSD','Units','inches','Position',figSize,'Color','w');
ax3 = axes(fig3); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log','FontSize',12);
xlabel(ax3,'Frequency (Hz)','FontSize',16);
ylabel(ax3,'LPSD [nm/√Hz]','FontSize',16);

colors = lines(numFiles);
if numFiles >= 3, colors(3,:) = [0.8 0.5 0]; end
markers = {'-','--',':','-.'};

%% === RMS bands ===
band_edges = [1,40; 40,1000; 1,1000];
band_names = {'[1–40] Hz','[40–1000] Hz','[1–1000] Hz'};

allRMS = cell(numFiles,1);
fileLabels = cell(numFiles,1);
df_print = NaN;

%% === Auto x-limit vars ===
fmax_global = 0;
fmin_pos_global = Inf;

%% === Main loop ===
for iFile = 1:numFiles
    fullFileName = fullfile(filePath, fileNames{iFile});
    [~, nameOnly, ~] = fileparts(fileNames{iFile});
    fileLabels{iFile} = nameOnly;

    % Set import options and skip the header row
    opts = detectImportOptions(fullFileName, 'NumHeaderLines', 1);  % Skip the first header row
    data = readmatrix(fullFileName, opts);
    time = data(:,1);
    voltage = data(:,2);

    % --- time limit ---
    if isfinite(time_limit_sec)
        t0 = time(1);
        time = time - t0;
        keep = time <= time_limit_sec;
        if any(keep)
            time = time(keep);
            voltage = voltage(keep);
        end
    end

    % --- convert voltage to accel ---
    a_g = voltage / (sensitivity(iFile) * gain);  % Use file-specific sensitivity
    a_g = a_g - mean(a_g);  % Detrend the data

    % Check for NaN or Inf values
    if any(isnan(a_g)) || any(isinf(a_g))
        error('Acceleration data contains NaN or Inf values.');
    end

    dt = mean(diff(time));
    fs = 1/dt;
    N  = numel(time);

    % --- Welch method ---
    seglen  = min(round(fs*20), N);
    window  = hamming(seglen);
    overlap = round(seglen/2);
    nfft    = seglen;
    N_win   = max(1, floor((N - overlap)/(seglen - overlap)));

    [pxx_g2, f] = pwelch(a_g, window, overlap, nfft, fs);
    df = mean(diff(f));
    if isnan(df_print), df_print = df; end

    pos = f > 0;

    % --- record freq range ---
    if any(pos)
        fmin_pos_global = min(fmin_pos_global, min(f(pos)));
        fmax_global     = max(fmax_global, max(f(pos)));
    end

    % --- LPSD (acc & disp) ---
    lpsd_acc = sqrt(pxx_g2);
    lpsd_disp_m = zeros(size(lpsd_acc));
    lpsd_disp_m(pos) = g ./ ((2*pi*f(pos)).^2) .* lpsd_acc(pos);

    % --- RMS calc ---
    RMS_result = zeros(size(band_edges,1),2);
    for iBand = 1:size(band_edges,1)
        idx = (f >= band_edges(iBand,1)) & (f <= band_edges(iBand,2));
        RMS_result(iBand,1) = sqrt(sum((lpsd_acc(idx).^2).*df));      % Acc RMS [g]
        RMS_result(iBand,2) = sqrt(sum((lpsd_disp_m(idx).^2).*df));   % Disp RMS [m]
    end
    allRMS{iFile} = RMS_result;

    % --- plots ---
    styleID = mod(iFile-1, numel(markers)) + 1;
    plot(ax1, f(pos), pxx_g2(pos), 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);
    plot(ax2, f(pos), lpsd_acc(pos), 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);
    plot(ax3, f(pos), lpsd_disp_m(pos) * 1e9, 'Color', colors(iFile,:), 'LineStyle', markers{styleID}, 'LineWidth', 1.5, 'DisplayName', nameOnly);

    fprintf('\n[%s]\n', nameOnly);
    fprintf('fs=%.3f Hz, N=%d, Δf=%.3f Hz, Welch windows=%d\n', fs, N, df, N_win);
    if isfinite(time_limit_sec)
        fprintf('Time limited to first %.1f s\n', time_limit_sec);
    end
end

%% === Legend & titles ===
legend(ax1, 'show', 'Location', 'best', 'FontSize', 16);
legend(ax2, 'show', 'Location', 'best', 'FontSize', 16);
legend(ax3, 'show', 'Location', 'best', 'FontSize', 16);
title(ax1, sprintf('Power Spectral Density (Δf=%.1f Hz)', df_print), 'FontSize', 24);
title(ax2, sprintf('Acceleration LPSD (Δf=%.1f Hz)', df_print), 'FontSize', 24);
title(ax3, sprintf('Displacement LPSD (Δf=%.1f Hz)', df_print), 'FontSize', 24);

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

%% === Export RMS to Excel ===
rms_cell = cell(numFiles, 7);
for iFile = 1:numFiles
    R = allRMS{iFile};
    rms_cell{iFile, 1} = fileLabels{iFile};
    for iBand = 1:3
        rms_cell{iFile, iBand+1} = sprintf('%.2f', R(iBand, 1) * 1e6);
    end
    for iBand = 1:3
        rms_cell{iFile, iBand+4} = sprintf('%.2f', R(iBand, 2) * 1e9);
    end
end
col_names = {'File', ...
    'Acc RMS (µg) 1–40Hz', 'Acc RMS (µg) 40–100Hz', 'Acc RMS (µg) 1–100Hz', ...
    'Disp RMS (nm) 1–40Hz', 'Disp RMS (nm) 40–100Hz', 'Disp RMS (nm) 1–100Hz'};

[~, firstStem, ~] = fileparts(fileNames{1});
name = regexprep(firstStem, '[^\w\-.]', '_');
xlsxPath = fullfile(filePath, sprintf('%s_RMS_summary.xlsx', name));

longHeader = {'File', 'Band', 'Acc RMS (µg)', 'Disp RMS (nm)'};
longRows = {};
for iFile = 1:numFiles
    R = allRMS{iFile};
    for iBand = 1:size(band_edges, 1)
        longRows(end+1, :) = {fileLabels{iFile}, band_names{iBand}, ...
            round(R(iBand, 1) * 1e6, 3), round(R(iBand, 2) * 1e9, 3)};
    end
end
writecell([col_names; rms_cell], xlsxPath, 'Sheet', 'RMS_Wide');
writecell([longHeader; longRows], xlsxPath, 'Sheet', 'RMS_Long');
fprintf('RMS tables saved: %s\n', xlsxPath);

end
