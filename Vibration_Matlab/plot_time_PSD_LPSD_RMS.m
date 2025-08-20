%% ===== Parameter Settings =====
gain = 100;                 
sens_g_per_V = 1.026;       
remove_dc = true;           
zero_time_start = true;     
g0 = 9.81;                  

band_edges = [1, 40; 40, 100; 1, 100];
band_names = {'[1–40] Hz', '[40–100] Hz', '[1–100] Hz'};

set(0,'defaultAxesFontName','Arial');
set(0,'defaultTextInterpreter','none');    
set(0,'defaultLegendInterpreter','none');
set(0,'defaultAxesTickLabelInterpreter','none');

%% ===== Select Multiple CSV Files =====
[files, path] = uigetfile('*.csv', ...
    'Select one or more CSV files (first 4 lines are headers: time(s), voltage(V))', ...
    'MultiSelect','on');
if isequal(files,0), error('Selection canceled'); end
if ischar(files), files = {files}; end

numFiles = numel(files);
colors = lines(max(numFiles, 7));
markers = {'-','--',':','-.'};

%% ===== Initialize Figures and RMS Storage =====
figT = figure('Name','Time-Domain Acceleration (g)', 'ToolBar','none');
axT = axes(figT); hold(axT,'on'); grid(axT,'on');
xlabel(axT,'Time (s)'); ylabel(axT,'Acceleration (g)');
title(axT,'Time-Domain Acceleration (g)');
legNames = cell(1, numFiles);
maxDuration = 0;

figPSD  = figure('Name','Acceleration PSD', 'ToolBar','none');  
ax1 = axes(figPSD);  hold(ax1,'on'); grid(ax1,'on');
set(ax1,'XScale','log','YScale','log'); xlabel(ax1,'Frequency (Hz)'); ylabel(ax1,'PSD [g^2/Hz]'); title(ax1,'Acceleration PSD');
xlim(ax1, [1, 1e4]);

figLPSD = figure('Name','Acceleration LPSD', 'ToolBar','none'); 
ax2 = axes(figLPSD); hold(ax2,'on'); grid(ax2,'on');
set(ax2,'XScale','log','YScale','log'); xlabel(ax2,'Frequency (Hz)'); ylabel(ax2,'LPSD [g/sqrt(Hz)]'); title(ax2,'Acceleration LPSD');
xlim(ax2, [1, 1e4]);

figDLPSD = figure('Name','Displacement LPSD', 'ToolBar','none');  
ax3 = axes(figDLPSD); hold(ax3,'on'); grid(ax3,'on');
set(ax3,'XScale','log','YScale','log'); xlabel(ax3,'Frequency (Hz)'); ylabel(ax3,'LPSD [nm/sqrt(Hz)]'); title(ax3,'Displacement LPSD');
xlim(ax3, [1, 1e4]);

allRMS_acc = cell(numFiles,1);
allRMS_disp = cell(numFiles,1);
fileLabels = cell(numFiles,1);

%% ===== Main Loop for File Processing =====
for k = 1:numFiles
    infile = fullfile(path, files{k});
    [~, nameOnly] = fileparts(files{k});

    % Clean filename for display
    nameSafe = regexprep(nameOnly, '[^\w\-.]', '_');
    fileLabels{k} = nameSafe;

    opts = detectImportOptions(infile, 'NumHeaderLines', 4);
    M = readmatrix(infile, opts);
    if size(M,2) < 2
        warning('File %s has insufficient columns and will be skipped.', files{k});
        continue;
    end
    t_raw = M(:,1);  v_raw = M(:,2);
    [t_raw, idx] = sort(t_raw(:));
    v_raw = v_raw(idx);

    acc_g = v_raw ./ (gain * sens_g_per_V);
    if remove_dc
        acc_g = acc_g - mean(acc_g, 'omitnan');
    end
    if zero_time_start
        t = t_raw - t_raw(1);
    else
        t = t_raw;
    end

    styleID = mod(k-1, numel(markers)) + 1;
    plot(axT, t, acc_g, 'LineWidth', 1.2, ...
        'Color', colors(k,:), 'LineStyle', markers{styleID});
    legNames{k} = sprintf('%s (g)', nameSafe);
    if ~isempty(t)
        maxDuration = max(maxDuration, t(end) - t(1));
    end

    dt = median(diff(t)); fs = 1/dt;
    N = numel(acc_g);
    seg_target = max(1024, floor(N/4));
    seglen = 2^floor(log2(seg_target));
    seglen = max(512, min(seglen, N));
    nfft = max(2^nextpow2(seglen), 1024);
    win = hamming(seglen);
    overlap = round(0.5*seglen);

    acc_g = acc_g(:);
    [pxx_g, f] = pwelch(acc_g, win, overlap, nfft, fs);
    df = mean(diff(f));
    valid = f > 0;
    f = f(valid);
    pxx_g = pxx_g(valid);

    lpsd_acc_g = sqrt(pxx_g);
    lpsd_acc_ms2 = lpsd_acc_g * g0;
    lpsd_disp_m  = lpsd_acc_ms2 ./ ((2*pi*f).^2);
    lpsd_disp_nm = lpsd_disp_m * 1e9;

    RMS_acc_g  = zeros(size(band_edges,1),1);
    RMS_disp_m = zeros(size(band_edges,1),1);
    for ib = 1:size(band_edges,1)
        f1 = band_edges(ib,1); f2 = band_edges(ib,2);
        idx = (f >= f1) & (f <= f2);
        if nnz(idx) < 2
            RMS_acc_g(ib)  = NaN;
            RMS_disp_m(ib) = NaN;
        else
            RMS_acc_g(ib)  = sqrt(sum((lpsd_acc_g(idx)).^2) * df);
            RMS_disp_m(ib) = sqrt(sum((lpsd_disp_m(idx)).^2) * df);
        end
    end
    allRMS_acc{k}  = RMS_acc_g;
    allRMS_disp{k} = RMS_disp_m;

    plot(ax1, f, pxx_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameSafe);
    plot(ax2, f, lpsd_acc_g, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameSafe);
    plot(ax3, f, lpsd_disp_nm, 'Color', colors(k,:), 'LineStyle', markers{styleID}, ...
        'LineWidth', 1.5, 'DisplayName', nameSafe);
end

legend(axT, legNames, 'Interpreter','none','Location','best');
if maxDuration > 0, xlim(axT, [0, maxDuration]); end
legend(ax1, 'show', 'Interpreter','none', 'Location','best');
legend(ax2, 'show', 'Interpreter','none', 'Location','best');
legend(ax3, 'show', 'Interpreter','none', 'Location','best');

%% ===== Output RMS Summary Table =====
rms_cell = cell(numFiles, 1+3+3);
for i = 1:numFiles
    rms_cell{i,1} = fileLabels{i};
    Ra = allRMS_acc{i}; Rd = allRMS_disp{i};
    for ib = 1:3
        if ~isempty(Ra) && ~isnan(Ra(ib))
            rms_cell{i,1+ib} = sprintf('%.2f ug', Ra(ib)*1e6);
        else
            rms_cell{i,1+ib} = 'N/A';
        end
        if ~isempty(Rd) && ~isnan(Rd(ib))
            rms_cell{i,1+3+ib} = sprintf('%.2f nm', Rd(ib)*1e9);
        else
            rms_cell{i,1+3+ib} = 'N/A';
        end
    end
end

figTbl = figure('Name','RMS Summary Table','Units','pixels','Color','w', 'ToolBar','none');
col_names = {'Filename', ...
    '[1–40Hz] Acc.', '[40–100Hz] Acc.', '[1–100Hz] Acc.', ...
    '[1–40Hz] Disp.', '[40–100Hz] Disp.', '[1–100Hz] Disp.'};
uitable('Parent', figTbl, ...
    'Data', rms_cell, ...
    'ColumnName', col_names, ...
    'Units','normalized', ...
    'Position',[0.05 0.05 0.9 0.9], ...
    'FontSize', 10, ...
    'FontName','Microsoft YaHei', ...
    'RowName', []);
set(figTbl, 'Position', [100, 100, 900, min(500, 100 + 28*numFiles)]);
